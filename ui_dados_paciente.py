"""GENUA | Tela de Cadastro/Seleção de Paciente."""
import streamlit as st
from datetime import datetime
from config import CORES_GENUA, titulo
from firebase_client import conn, db, invalidar_cache

def render():
        st.header("👤 Gestão de Pacientes")
    
        # 1. LEITURA DIRETA E NATIVA (Imune a falhas de formatação Pandas)
        try:
            docs = db.collection("Cadastro").stream()
            lista = list(set([doc.to_dict().get("Nome") for doc in docs if doc.to_dict().get("Nome")]))
        except:
            lista = []
        
        paciente = st.selectbox("Selecione um paciente existente ou adicione um novo:", ["+ Novo Paciente"] + lista)
    
        if paciente == "+ Novo Paciente":
            # 2. CONTAINER LIVRE (Sem camisas de força de formulários)
            with st.container():
                titulo("Identificação do Paciente")
                nome = st.text_input("Nome Completo *")
            
                c_cad1, c_cad2, c_cad3 = st.columns(3)
                with c_cad1: 
                    data_padrao = datetime(2000, 1, 1)
                    data_minima = datetime(datetime.now().year - 100, 1, 1)
                    dt_nasc = st.date_input("Data de Nascimento *", value=data_padrao, min_value=data_minima, max_value=datetime.today(), format="DD/MM/YYYY")
                with c_cad2: cpf = st.text_input("CPF")
                with c_cad3: telefone = st.text_input("Telefone (WhatsApp)")
            
                c_cad4, c_cad5, c_cad6 = st.columns(3)
                with c_cad4: email = st.text_input("E-mail")
                with c_cad5: cidade = st.text_input("Cidade e Estado")
                with c_cad6: ocupacao = st.text_input("Atividade Ocupacional")
            
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Diagnóstico Clinico (Triagem)</h4>", unsafe_allow_html=True)
                dx_clinico = st.text_input("Diagnóstico Clínico/Médico", placeholder="Ex: LCA, Condropatia, Tendinopatia...")
            
                st.markdown("<br>", unsafe_allow_html=True)
            
                # 3. BOTÃO REATIVO DE COMUNICAÇÃO NATIVA
                if st.button("💾 Salvar Cadastro", width='stretch', type="primary"):
                    if nome.strip() == "":
                        st.error("⚠️ O Nome é obrigatório para abrir o prontuário.")
                    else:
                        with st.spinner("🔄 Injetando dados diretamente no núcleo do Firebase..."):
                            try:
                                idade_calc = (datetime.now().date() - dt_nasc).days // 365
                                novo_cad = {
                                    "Nome": nome.strip(), "Data_Nascimento": dt_nasc.strftime("%d/%m/%Y"), 
                                    "Idade": idade_calc, "CPF": cpf, "Telefone": telefone, 
                                    "Email": email, "Cidade_Estado": cidade, "Ocupacao": ocupacao, 
                                    "Diagnostico_Clinico": dx_clinico, "Historia": "" 
                                }
                            
                                # O COMANDO DE SALVAMENTO ABSOLUTO
                                db.collection("Cadastro").add(novo_cad)
                                invalidar_cache("Cadastro")
                            
                                st.session_state.paciente = nome.strip()
                                st.session_state.membro_ativo = "Joelho" 
                                st.session_state.pagina = 'painel_clinico'
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"❌ Falha crítica reportada pelo servidor: {e}")
        else:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Abrir Prontuário", width='stretch', type="primary"):
                st.session_state.paciente = paciente
                st.session_state.membro_ativo = "Joelho"
                st.session_state.pagina = 'painel_clinico'
                st.rerun()

