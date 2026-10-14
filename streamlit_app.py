"""
GENUA | Inteligência Clínica
Entrypoint: orquestra roteamento, barra de navegação estilo Apple (HIG) e renderização das telas.
"""
import streamlit as st

# 1) Configuração visual (set_page_config DEVE ser o 1º comando Streamlit)
import config  # noqa: F401  — efeitos colaterais: page config + CSS + sidebar logo
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

    # 1. Menu Lateral Limpo e Unificado (Estilo macOS Sidebar)
    with st.sidebar:
        if not paciente_alvo:
            # Mini-Card de Perfil do Paciente na Sidebar
            st.markdown(f"""
                <div style='background: rgba(16, 62, 85, 0.05); border: 1px solid rgba(16, 62, 85, 0.08);
                            padding: 14px 16px; border-radius: 16px; margin-bottom: 14px;'>
                    <div style='font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
                                letter-spacing: 0.06em; color: {CORES_GENUA['secundaria']}; margin-bottom: 2px;'>
                        Prontuário Ativo
                    </div>
                    <div style='font-size: 1.05rem; font-weight: 700; color: {CORES_GENUA['texto_escuro']};
                                white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                        👤 {st.session_state.paciente}
                    </div>
                    <div style='font-size: 0.80rem; color: {CORES_GENUA['texto_suave']}; margin-top: 2px;'>
                        Segmento: <b>{st.session_state.get('membro_ativo', 'Joelho')}</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Expansor de Navegação Rápida (Otimizado com Cache)
            with st.expander("🔄 Trocar Paciente Ativo"):
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
                            "Selecione:",
                            todos_pacientes,
                            index=idx_atual,
                            label_visibility="collapsed"
                        )
                        if st.button("Carregar Prontuário", width='stretch', type="primary"):
                            st.session_state.paciente = paciente_selecionado
                            st.session_state.pagina = 'painel_clinico'
                            st.rerun()
                    else:
                        st.caption("Nenhum paciente encontrado.")
                except Exception:
                    st.caption("Erro ao carregar lista de pacientes.")

            st.markdown("---")

            # Menu Lateral sincronizado com o estado global
            menu_sidebar = st.radio(
                "MÓDULOS DE ATENDIMENTO",
                opcoes_modulos,
                index=opcoes_modulos.index(st.session_state.modulo_ativo),
            )
            if menu_sidebar != st.session_state.modulo_ativo:
                st.session_state.modulo_ativo = menu_sidebar
                st.rerun()

            st.markdown("---")
            if st.button("⬅️ Todos os Pacientes", type="secondary", width='stretch'):
                st.session_state.pagina = 'dados_paciente'
                st.session_state.paciente = None
                st.rerun()

        else:
            st.session_state.modulo_ativo = "Painel Analítico 📊"

    # 2. App Header (Barra Superior de Navegação Estilo iPadOS)
    if not paciente_alvo:
        with st.container(border=True):
            c_back, c_info, c_nav = st.columns([1.1, 2.2, 3.2])

            with c_back:
                if st.button("⬅️ Pacientes", type="secondary", width='content', help="Voltar para a seleção de pacientes"):
                    st.session_state.pagina = 'dados_paciente'
                    st.session_state.paciente = None
                    st.rerun()

            with c_info:
                membro = st.session_state.get('membro_ativo', 'Joelho')
                st.markdown(f"""
                    <div style='display: flex; align-items: center; gap: 10px; padding-top: 4px;'>
                        <span style='font-size: 1.25rem; font-weight: 800; color: {CORES_GENUA['texto_escuro']}; letter-spacing: -0.02em;'>
                            {st.session_state.paciente}
                        </span>
                        <span style='background: rgba(46, 139, 154, 0.12); color: {CORES_GENUA['primaria']};
                                     padding: 4px 12px; border-radius: 980px; font-size: 0.78rem; font-weight: 700;'>
                            🦿 {membro}
                        </span>
                    </div>
                """, unsafe_allow_html=True)

            with c_nav:
                # Seletor rápido no topo estilo Segmented Control do iOS
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

    menu = st.session_state.modulo_ativo if not paciente_alvo else "Painel Analítico 📊"

    # 3. Despacha módulo conforme menu selecionado
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
