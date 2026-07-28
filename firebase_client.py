"""GENUA | Conexão Firebase/Firestore e adapter de leitura.

Performance: leituras passam por @st.cache_data com TTL de 60s.
Após qualquer escrita, o cache da coleção afetada é invalidado.
"""
import re
import json
import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================================
# INICIALIZAÇÃO DO FIREBASE (com autocura de credenciais)
# ============================================================
if not firebase_admin._apps:
    try:
        cred_dict = json.loads(st.secrets["FIREBASE_JSON"])
    except Exception:
        # Autocura: se houver quebras de linha corrompidas no Secrets,
        # reconstrói o dicionário nativamente.
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
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        else:
            st.error("❌ Erro crítico: As credenciais do Firebase contidas no Secrets estão ilegíveis.")
            st.stop()

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ============================================================
# LEITURA COM CACHE (TTL 60s) — reduz drasticamente travamentos
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def _ler_colecao_cached(worksheet: str) -> pd.DataFrame:
    """Lê uma coleção inteira do Firestore. Cache de 60s por coleção."""
    docs = db.collection(worksheet).stream()
    dados = [d.to_dict() for d in docs]
    return pd.DataFrame(dados) if dados else pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def _ler_paciente_cached(worksheet: str, paciente: str) -> pd.DataFrame:
    """Lê documentos de uma coleção filtrados por paciente. Cache de 60s."""
    docs = db.collection(worksheet).where("Paciente", "==", paciente).stream()
    dados = [{**d.to_dict(), "_doc_id": d.id} for d in docs]
    return pd.DataFrame(dados) if dados else pd.DataFrame()


def invalidar_cache(worksheet: str = None):
    """Limpa o cache. Se worksheet=None, limpa tudo.

    Chame esta função após CADA escrita (add/update) para que a próxima
    leitura traga os dados frescos.
    """
    _ler_colecao_cached.clear()
    _ler_paciente_cached.clear()


# ============================================================
# ADAPTER DE COMPATIBILIDADE (mantém API antiga conn.read/conn.update)
# ============================================================
class FirebaseAdapter:
    def read(self, worksheet: str = "Evolucao", ttl: int = 0) -> pd.DataFrame:
        """Lê coleção. O parâmetro ttl é mantido por compatibilidade
        mas o cache real é controlado pelo decorator (60s)."""
        return _ler_colecao_cached(worksheet)

    def read_paciente(self, worksheet: str, paciente: str) -> pd.DataFrame:
        """Lê só os documentos de um paciente (mais rápido que filtrar depois)."""
        return _ler_paciente_cached(worksheet, paciente)

    def update(self, worksheet: str = "Evolucao", data: pd.DataFrame = None):
        """Insere o último registro do DataFrame e invalida o cache."""
        novo_registro = data.iloc[-1].dropna().to_dict()
        db.collection(worksheet).add(novo_registro)
        invalidar_cache(worksheet)


conn = FirebaseAdapter()
