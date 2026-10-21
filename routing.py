"""GENUA | Roteamento: portal do cirurgião (deep-link) e persistência anti-logout mobile."""
import base64
import streamlit as st


def codificar_sessao_url(email: str) -> str:
    """Codifica o e-mail do profissional em Base64 URL-safe para persistência mobile."""
    if not email:
        return ""
    return base64.urlsafe_b64encode(email.strip().encode("utf-8")).decode("utf-8")


def decodificar_sessao_url(token_b64: str) -> str:
    """Decodifica o token de sessão da URL de forma segura."""
    if not token_b64:
        return ""
    try:
        return base64.urlsafe_b64decode(token_b64.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def aplicar_roteamento():
    """
    Lê query params, restaura a sessão caso o celular tenha apagado a tela
    e inicializa o session_state sem deslogar o profissional.
    Retorna (paciente_alvo, menu_inicial).
    """
    query_params = st.query_params
    is_medico = query_params.get("med", None)
    token_paciente = query_params.get("token", None)
    auth_token = query_params.get("auth", None)
    pac_salvo_url = query_params.get("pac", None)
    mod_salvo_url = query_params.get("mod", None)
    paciente_alvo = None

    # 1. Portal do Cirurgião (Deep-Link Externo)
    if is_medico == "true" and token_paciente:
        try:
            paciente_alvo = base64.b64decode(token_paciente.encode("utf-8")).decode("utf-8")
            st.markdown(
                """
                <style>
                    [data-testid="collapsedControl"] {display: none;}
                    [data-testid="stSidebar"] {display: none;}
                    header {display: none;}
                </style>
                """,
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    # 2. Recuperação Automática de Sessão Mobile (Anti-Logout quando a tela apaga)
    if "user_email" not in st.session_state and auth_token:
        email_recuperado = decodificar_sessao_url(auth_token)
        if email_recuperado:
            st.session_state.user_email = email_recuperado
            st.session_state.autenticado = True

    if st.session_state.get("user_email"):
        st.session_state.autenticado = True
        # Garante que o token continue na URL mesmo após reruns
        token_esperado = codificar_sessao_url(st.session_state.user_email)
        if query_params.get("auth") != token_esperado:
            st.query_params["auth"] = token_esperado

        # Se o celular reconectou e tinha um paciente aberto, restaura direto no prontuário
        if "paciente" not in st.session_state and pac_salvo_url:
            st.session_state.paciente = pac_salvo_url
            st.session_state.membro_ativo = "Joelho"
            st.session_state.pagina = "painel_clinico"
            if mod_salvo_url in ["Avaliação Inicial 🔎", "Check-in Diário 📝", "Painel Analítico 📊"]:
                st.session_state.modulo_ativo = mod_salvo_url
        elif "pagina" not in st.session_state:
            st.session_state.pagina = "painel_clinico" if st.session_state.get("paciente") else "dados_paciente"

    # 3. Inicialização Padrão (Apenas se realmente não estiver logado)
    if "pagina" not in st.session_state:
        st.session_state.pagina = "login"
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    # Sincroniza o paciente ativo na URL para proteção contínua
    if st.session_state.get("paciente") and not paciente_alvo:
        if query_params.get("pac") != st.session_state.paciente:
            st.query_params["pac"] = st.session_state.paciente
    if st.session_state.get("modulo_ativo") and not paciente_alvo:
        if query_params.get("mod") != st.session_state.modulo_ativo:
            st.query_params["mod"] = st.session_state.modulo_ativo

    # 4. Trava de Segurança: Acesso Direto do Cirurgião
    if paciente_alvo:
        st.session_state.autenticado = True
        st.session_state.paciente = paciente_alvo
        st.session_state.membro_ativo = "Acesso Médico"
        st.session_state.pagina = "painel_clinico"
        menu = "Painel Analítico 📊"

    return paciente_alvo, (menu if paciente_alvo else None)
