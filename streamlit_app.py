"""
GENUA | Inteligência Clínica
Entrypoint: orquestra roteamento e renderização das telas.
"""
import streamlit as st

# 1) Configuração visual (set_page_config DEVE ser o 1º comando Streamlit)
import config  # noqa: F401  — efeitos colaterais: page config + CSS + sidebar logo
from config import CORES_GENUA

# 2) Conexão Firebase
from firebase_client import conn, db  # noqa: F401

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

    # 1. Menu Lateral Limpo e Unificado
    with st.sidebar:
        if not paciente_alvo: 
            st.markdown(f"<h3 style='color: {CORES_GENUA['primaria']}; text-align: center;'>👤 {st.session_state.paciente}</h3>", unsafe_allow_html=True)
        
            # Expansor de Navegação Rápida
            with st.expander("🔄 Trocar Paciente Ativo"):
                try:
                    docs = db.collection("Cadastro").stream()
                    todos_pacientes = list(set([doc.to_dict().get("Nome") for doc in docs if doc.to_dict().get("Nome")]))
                
                    if todos_pacientes:
                        idx_atual = todos_pacientes.index(st.session_state.paciente) if st.session_state.get('paciente') in todos_pacientes else 0
                        paciente_selecionado = st.selectbox("Selecione:", todos_pacientes, index=idx_atual, label_visibility="collapsed")
                        if st.button("Carregar Prontuário", width='stretch'):
                            st.session_state.paciente = paciente_selecionado
                            st.session_state.pagina = 'painel_clinico'
                            st.rerun()
                    else:
                        st.caption("Nenhum paciente encontrado.")
                except Exception as e:
                    st.caption("Erro ao carregar lista de pacientes.")

            st.markdown("---")
            # MENU COMPLETO E PROTEGIDO
            menu = st.radio("MÓDULOS DE ATENDIMENTO", ["Avaliação Inicial 🔎", "Check-in Diário 📝", "Painel Analítico 📊"])
        else:
            menu = "Painel Analítico 📊"

    # 2. App Header (Barra Superior de Navegação Nativa)
    if not paciente_alvo:
        c_back, c_title, c_vazio = st.columns([1, 4, 1])
        with c_back:
            # BOTÃO VOLTAR COM ROTA CORRIGIDA
            if st.button("⬅️ Voltar", type="secondary", width='content', help="Voltar para seleção de pacientes"):
                st.session_state.pagina = 'dados_paciente'
                st.session_state.paciente = None
                st.rerun()
        with c_title:
            membro = st.session_state.get('membro_ativo', 'Joelho')
            st.markdown(f"<h3 style='text-align: center; color: {CORES_GENUA['primaria']}; margin-top: 5px; font-size: 1.6rem;'>{membro}</h3>", unsafe_allow_html=True)
        st.markdown("<hr style='margin-top: -5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

    # Despacha módulo conforme menu selecionado
    if menu == "Avaliação Inicial 🔎":
        modulo_avaliacao.render()
    elif menu == "Check-in Diário 📝":
        modulo_checkin.render()
    elif menu == "Painel Analítico 📊":
        modulo_painel.render()

# ============================================================
# Fail-safe: tela branca
# ============================================================
# --- SISTEMA DE PROTEÇÃO GLOBAL CONTRA TELA BRANCA (FAIL-SAFE) ---
# Se o aplicativo se perder na navegação, este escudo força o retorno à tela de pacientes.
paginas_validas = ['login', 'dados_paciente', 'painel_clinico']
if st.session_state.get('pagina') not in paginas_validas:
    st.session_state.pagina = 'dados_paciente'
    st.rerun()



