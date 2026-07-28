"""GENUA | Roteamento: portal do cirurgião (deep-link) e estado inicial."""
import base64
import streamlit as st

def aplicar_roteamento():
    """Lê query params e inicializa session_state. Retorna (paciente_alvo, menu_inicial)."""
    query_params = st.query_params
    is_medico = query_params.get("med", None)
    token_paciente = query_params.get("token", None)
    paciente_alvo = None

    if is_medico == "true" and token_paciente:
        try:
            paciente_alvo = base64.b64decode(token_paciente.encode('utf-8')).decode('utf-8')
            # Esconde menu lateral e barra superior do Streamlit para o médico
            st.markdown("""
                <style>
                    [data-testid="collapsedControl"] {display: none;}
                    [data-testid="stSidebar"] {display: none;}
                    header {display: none;}
                </style>
            """, unsafe_allow_html=True)
        except:
            pass

    # ==========================================
    # --- NOVA LÓGICA DE NAVEGAÇÃO (ESTADO DO APP) ---
    # ==========================================
    if 'pagina' not in st.session_state:
        st.session_state.pagina = 'login'
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

    def mudar_pagina(nome_pagina):
        st.session_state.pagina = nome_pagina
        st.rerun()

    # TRAVA DE SEGURANÇA: Se o cirurgião acessar via link, pula o login e vai direto para o painel
    if paciente_alvo:
        st.session_state.autenticado = True
        st.session_state.paciente = paciente_alvo
        st.session_state.membro_ativo = "Acesso Médico"
        st.session_state.pagina = 'painel_clinico'
        menu = "Painel Analítico 📊"
    return paciente_alvo, (menu if paciente_alvo else None)
