"""GENUA | Tela de Login (Estilo Apple iCloud / HIG)."""
import streamlit as st
from config import CORES_GENUA, NOVO_LOGO_GENUA

def render():
    # Criação de colunas simétricas para centralizar o cartão de login (Efeito Card Apple)
    _, c_login, _ = st.columns([1, 1.4, 1])

    with c_login:
        st.markdown("<div style='height: 4vh;'></div>", unsafe_allow_html=True)
        
        # Container com borda e fundo elevado (Card Apple)
        with st.container(border=True):
            
            # Renderização da Logo Centralizada
            st.markdown("<div style='text-align: center; padding-top: 10px;'>", unsafe_allow_html=True)
            try:
                st.image(NOVO_LOGO_GENUA, width=120)
            except Exception:
                st.markdown(f"<h1 style='color: {CORES_GENUA['primaria']}; font-size: 2.5rem; margin-bottom: 0;'>GENUA</h1>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
            st.markdown(f"""
                <div style='text-align: center; margin-bottom: 28px;'>
                    <h3 style='color: {CORES_GENUA['primaria']}; margin-bottom: 4px; font-size: 1.5rem;'>Entrar no Sistema</h3>
                    <p style='color: {CORES_GENUA['texto_suave']}; font-size: 0.9rem; margin: 0;'>Inteligência Clínica Integrada</p>
                </div>
            """, unsafe_allow_html=True)
        
            # Campos de Formulário com espaçamento limpo
            email = st.text_input("✉️ E-mail Profissional", placeholder="dr.nome@clinica.com", key="login_email")
            senha = st.text_input("🔑 Senha de Acesso", type="password", placeholder="••••••••", key="login_senha")
        
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
            # Motor de Autenticação
            if st.button("ENTRAR NO SISTEMA", use_container_width=True, type="primary"):
                if email and senha:
                    with st.spinner("Autenticando credenciais..."):
                        # Simulação / Estado de Autenticação
                        st.session_state.user_email = email
                        st.session_state.pagina = 'dados_paciente'
                        st.rerun()
                else:
                    st.warning("⚠️ Preencha o e-mail e a senha para aceder.")
                
            st.markdown(f"""
                <div style='text-align: center; color: {CORES_GENUA['texto_suave']}; font-size: 0.78rem; margin-top: 24px; border-top: 1px solid rgba(0,0,0,0.06); padding-top: 16px;'>
                    GENUA HealthTech © 2026<br>Ambiente Seguro e Criptografado (LGPD)
                </div>
            """, unsafe_allow_html=True)
