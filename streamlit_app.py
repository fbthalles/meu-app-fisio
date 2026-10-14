"""
GENUA | Inteligência Clínica
Entrypoint: orquestra roteamento e Top Navigation Bar estilo Apple (Sem Sidebar).
"""
import streamlit as st

# 1) Configuração visual (set_page_config DEVE ser o 1º comando Streamlit)
import config  # noqa: F401
from config import CORES_GENUA

# 2) Conexão Firebase (com cache de 60s)
from firebase_client import db, conn  # noqa: F401

# 3) Roteamento (portal cirurgião + session_state inicial)
from routing import aplicar_roteamento
paciente_alvo, menu_forcado = aplicar_roteamento()

# 4) Telas
import ui_login
import ui_dados_paciente
import modulo_avaliacao
import modulo_checkin
import modulo_painel

# ============================================================
# Oculta a Sidebar globalmente para visual Full-Screen Apple
# ============================================================
st.markdown("""
    <style>
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# Despacho de telas
# ============================================================
if st.session_state.pagina == 'login':
    ui_login.render()

elif st.session_state.pagina == 'dados_paciente':
    ui_dados_paciente.render()

elif st.session_state.pagina == 'painel_clinico':
    paciente_alvo = st.session_state.get('paciente_alvo', False)
    opcoes_modulos = ["Avaliação Inicial 🔎", "Check-in Diário 📝", "Painel Analítico 📊"]

    # Inicializa o módulo ativo na sessão
    if "modulo_ativo" not in st.session_state or st.session_state.modulo_ativo not in opcoes_modulos:
        st.session_state.modulo_ativo = opcoes_modulos[0]

    # Top Navigation Bar Unificada (Estilo iPadOS / macOS Sonoma)
    if not paciente_alvo:
        with st.container(border=True):
            c_acoes, c_info, c_nav = st.columns([1.35, 2.45, 2.8], vertical_alignment="center")

            with c_acoes:
                b1, b2 = st.columns([1.15, 1])
                with b1:
                    if st.button("⬅️ Pacientes", type="secondary", width="stretch", help="Voltar para a lista de pacientes"):
                        st.session_state.pagina = 'dados_paciente'
                        st.session_state.paciente = None
                        st.rerun()
                with b2:
                    # Popover flutuante estilo iOS para trocar de paciente sem precisar de Sidebar
                    with st.popover("🔄 Trocar", help="Trocar rapidamente de paciente ativo"):
                        st.caption("SELECIONAR OUTRO PRONTUÁRIO")
                        try:
                            df_cad = conn.read("Cadastro")
                            if not df_cad.empty and "Nome" in df_cad.columns:
                                todos_pacientes = sorted(
                                    list(set(df_cad["Nome"].dropna().astype(str).str.strip().tolist()))
                                )
                                todos_pacientes = [p for p in todos_pacientes if p]
                            else:
                                todos_pacientes = []

                            if todos_pacientes:
                                idx_atual = (
                                    todos_pacientes.index(st.session_state.paciente)
                                    if st.session_state.get('paciente') in todos_pacientes
                                    else 0
                                )
                                paciente_selecionado = st.selectbox(
                                    "Paciente:",
                                    todos_pacientes,
                                    index=idx_atual,
                                    label_visibility="collapsed"
                                )
                                if st.button("Abrir Prontuário", width="stretch", type="primary"):
                                    st.session_state.paciente = paciente_selecionado
                                    st.session_state.pagina = 'painel_clinico'
                                    st.rerun()
                            else:
                                st.caption("Nenhum paciente encontrado.")
                        except Exception:
                            st.caption("Erro ao carregar pacientes.")

            with c_info:
                membro = st.session_state.get('membro_ativo', 'Joelho')
                st.markdown(f"""
                    <div style='display: flex; align-items: center; gap: 10px; flex-wrap: nowrap; overflow: hidden;'>
                        <span style='font-size: 1.18rem; font-weight: 800; color: {CORES_GENUA['texto_escuro']};
                                     letter-spacing: -0.02em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                            👤 {st.session_state.paciente}
                        </span>
                        <span style='background: rgba(46, 139, 154, 0.12); color: {CORES_GENUA['primaria']};
                                     padding: 4px 12px; border-radius: 980px; font-size: 0.78rem; font-weight: 700;
                                     white-space: nowrap; flex-shrink: 0;'>
                            🦿 {membro}
                        </span>
                    </div>
                """, unsafe_allow_html=True)

            with c_nav:
                if hasattr(st, "segmented_control"):
                    escolha_topo = st.segmented_control(
                        "Módulo",
                        opcoes_modulos,
                        default=st.session_state.modulo_ativo,
                        label_visibility="collapsed",
                        key="nav_topo_segmented"
                    )
                    if escolha_topo and escolha_topo != st.session_state.modulo_ativo:
                        st.session_state.modulo_ativo = escolha_topo
                        st.rerun()
                else:
                    escolha_radio = st.radio(
                        "Módulo",
                        opcoes_modulos,
                        index=opcoes_modulos.index(st.session_state.modulo_ativo),
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    if escolha_radio != st.session_state.modulo_ativo:
                        st.session_state.modulo_ativo = escolha_radio
                        st.rerun()

    menu = st.session_state.modulo_ativo if not paciente_alvo else "Painel Analítico 📊"

    # Despacha módulo conforme menu selecionado
    if menu == "Avaliação Inicial 🔎":
        modulo_avaliacao.render()
    elif menu == "Check-in Diário 📝":
        modulo_checkin.render()
    elif menu == "Painel Analítico 📊":
        modulo_painel.render()

# ============================================================
# Fail-safe: proteção global contra tela branca
# ============================================================
paginas_validas = ['login', 'dados_paciente', 'painel_clinico']
if st.session_state.get('pagina') not in paginas_validas:
    st.session_state.pagina = 'dados_paciente'
    st.rerun()
