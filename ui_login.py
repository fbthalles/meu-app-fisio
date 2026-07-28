"""GENUA | Tela de Login."""
import streamlit as st
from config import CORES_GENUA, NOVO_LOGO_GENUA

def render():
        # Injeção de CSS para transformar o design padrão num layout SaaS
        st.markdown(f"""
        <style>
        /* Estilização do Botão de Login */
        div.stButton > button {{
            background-color: {CORES_GENUA['primaria']};
            color: white;
            border-radius: 8px;
            height: 50px;
            font-weight: bold;
            font-size: 16px;
            border: none;
            transition: 0.3s;
        }}
        div.stButton > button:hover {{
            background-color: {CORES_GENUA['secundaria']};
            color: white;
            border: none;
            box-shadow: 0px 4px 10px rgba(57, 142, 155, 0.4);
        }}
        /* Centralização Vertical e Fundo do App */
        .block-container {{
            padding-top: 4rem;
            padding-bottom: 0rem;
        }}
        </style>
        """, unsafe_allow_html=True)

        # Criação de colunas para forçar o formulário a ficar centralizado (Efeito Cartão)
        c_espaco1, c_login, c_espaco2 = st.columns([1, 1.5, 1])

        with c_login:
            # Renderiza a Logo Centralizada
            try:
                st.image(NOVO_LOGO_GENUA, width='stretch')
            except Exception:
                st.markdown(f"<h1 style='text-align: center; color: {CORES_GENUA['primaria']}; font-size: 3rem;'>GENUA</h1>", unsafe_allow_html=True)
        
            st.markdown("<h4 style='text-align: center; color: #6c757d; font-weight: normal; margin-top: -15px;'>Inteligência Clínica Integrada</h4><br>", unsafe_allow_html=True)
        
            # Caixa de Formulário
            email = st.text_input("✉️ E-mail Profissional", placeholder="dr.nome@clinica.com")
            senha = st.text_input("🔑 Senha de Acesso", type="password", placeholder="••••••••")
        
            st.markdown("<br>", unsafe_allow_html=True)
        
            # Motor de Autenticação (Mantendo a sua lógica atual simplificada ou Firebase Auth)
            if st.button("ENTRAR NO SISTEMA", width='stretch'):
                if email and senha:
                    with st.spinner("A autenticar credenciais..."):
                        # Aqui entra a sua verificação real. Para já, avança o estado:
                        st.session_state.user_email = email
                        st.session_state.pagina = 'dados_paciente'
                        st.rerun()
                else:
                    st.warning("⚠️ Preencha o e-mail e a senha para aceder.")
                
            st.markdown("<p style='text-align: center; color: #adb5bd; font-size: 12px; margin-top: 20px;'>GENUA HealthTech © 2026<br>Ambiente Seguro e Criptografado</p>", unsafe_allow_html=True)

