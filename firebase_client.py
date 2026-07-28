"""GENUA | Conexão Firebase/Firestore e adapter de leitura."""
import re
import json
import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        # Tenta carregar o JSON de forma tradicional
        cred_dict = json.loads(st.secrets["FIREBASE_JSON"])
    except Exception as e:
        # MECANISMO DE AUTOCURA INTERNO
        # Se houver quebras de linha corrompidas no Secrets, o sistema reconstrói o dicionário nativamente.
        raw_text = st.secrets["FIREBASE_JSON"]
        
        proj_id_match = re.search(r'"project_id":\s*"([^"]+)"', raw_text)
        email_match = re.search(r'"client_email":\s*"([^"]+)"', raw_text)
        pk_match = re.search(r'"private_key":\s*"(.*?)"', raw_text, re.DOTALL)
        
        if proj_id_match and email_match and pk_match:
            pk_content = pk_match.group(1).replace("\\n", "\n")
            while "\n\n" in pk_content:
                pk_content = pk_content.replace("\n\n", "\n")
                
            cred_dict = {
                "type": "service_account",
                "project_id": proj_id_match.group(1),
                "private_key": pk_content.strip(),
                "client_email": email_match.group(1),
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        else:
            st.error("❌ Erro crítico: As credenciais do Firebase contidas no Secrets estão ilegíveis.")
            st.stop()

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    
db = firestore.client()

class FirebaseAdapter:
    def read(self, worksheet="Evolucao", ttl=0):
        # Lê os documentos do banco NoSQL e os converte instantaneamente para o formato Pandas
        docs = db.collection(worksheet).stream()
        dados = [d.to_dict() for d in docs]
        return pd.DataFrame(dados) if dados else pd.DataFrame()

    def update(self, worksheet="Evolucao", data=None):
        # Engenharia de performance: Captura apenas o último registro do DataFrame e injeta no banco
        novo_registro = data.iloc[-1].dropna().to_dict()
        db.collection(worksheet).add(novo_registro)

conn = FirebaseAdapter()
