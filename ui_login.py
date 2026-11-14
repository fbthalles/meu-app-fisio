"""Entrada do profissional no prontuário GENUA."""
import streamlit as st
from config import ASSETS, NOVO_LOGO_GENUA
from routing import codificar_sessao_url


def render():
    with st.container(key="acesso_genua", border=True):
        foto, formulario = st.columns([1.05, 1], gap="large", vertical_alignment="center")
        with foto:
            st.image(str(ASSETS / "fisioterapia-esportiva.jpg"), width="stretch")
        with formulario:
            with st.container(key="formulario_acesso"):
                st.image(NOVO_LOGO_GENUA, width=108)
                st.header("Acesso profissional")
                with st.form("login", border=False):
                    email = st.text_input("E-mail profissional", placeholder="nome@clinica.com", key="login_email")
                    senha = st.text_input("Senha", type="password", key="login_senha")
                    entrar = st.form_submit_button("Entrar no GENUA", type="primary", width="stretch")
                if entrar:
                    if email and senha:
                        email_limpo = email.strip()
                        st.session_state.user_email = email_limpo
                        st.session_state.autenticado = True
                        st.session_state.pagina = "dados_paciente"
                        st.query_params["auth"] = codificar_sessao_url(email_limpo)
                        st.rerun()
                    else:
                        st.warning("Preencha o e-mail e a senha para entrar.")
