"""GENUA | Módulo 2: Check-in Diário (O Mutante) — com edição de sessões."""
import streamlit as st
from datetime import datetime
from config import CORES_GENUA, titulo
from firebase_client import conn, db, invalidar_cache


def render():
    st.markdown(
        f"<h3 style='color: {CORES_GENUA['primaria']};'>📝 Check-in Diário e Evolução</h3>",
        unsafe_allow_html=True,
    )

    # ============================================================
    # 1. SELETOR DE MODO: Novo x Editar sessão existente
    # ============================================================
    st.session_state.setdefault('doc_id_checkin', None)
    st.session_state.setdefault('dados_checkin_antigos', None)

    sessoes_existentes = []
    try:
        docs = db.collection("Evolucao").where("Paciente", "==", st.session_state.paciente).stream()
        sessoes_existentes = [{"id": d.id, "data": d.to_dict()} for d in docs]
        sessoes_existentes.sort(
            key=lambda x: x["data"].get("Data", "0000-00-00"),
            reverse=True
        )
    except Exception:
        sessoes_existentes = []

    with st.container():
        col_modo1, col_modo2 = st.columns([2, 1])
        with col_modo1:
            if sessoes_existentes:
                opcoes = ["➕ Nova Sessão"] + [
                    f"✏️ {s['data'].get('Data', '?')} — Dor: {s['data'].get('Dor', '?')}/10"
                    for s in sessoes_existentes
                ]
                escolha = st.selectbox(
                    "🎯 Modo:",
                    opcoes,
                    key="seletor_checkin",
                    help="Nova sessão para hoje ou selecione uma antiga para corrigir/editar."
                )
            else:
                st.info("ℹ️ Nenhuma sessão de check-in registrada ainda. Este será o primeiro.")
                escolha = "➕ Nova Sessão"
                opcoes = ["➕ Nova Sessão"]

        with col_modo2:
            if sessoes_existentes and escolha != "➕ Nova Sessão":
                if st.button("🗑️ Excluir esta sessão", type="secondary"):
                    st.session_state['confirmar_exclusao_chk'] = True

        # Confirmação de exclusão
        if st.session_state.get('confirmar_exclusao_chk'):
            st.warning("⚠️ Tem certeza? Esta sessão será removida do histórico permanentemente.")
            cc1, cc2, _ = st.columns([1, 1, 3])
            with cc1:
                if st.button("✅ Sim, excluir", type="primary", key="conf_del_chk"):
                    try:
                        idx = opcoes.index(escolha) - 1
                        doc_id = sessoes_existentes[idx]["id"]
                        db.collection("Evolucao").document(doc_id).delete()
                        invalidar_cache("Evolucao")
                        st.session_state['confirmar_exclusao_chk'] = False
                        st.success("Sessão excluída.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
            with cc2:
                if st.button("❌ Cancelar", key="cancel_del_chk"):
                    st.session_state['confirmar_exclusao_chk'] = False
                    st.rerun()

    # Define modo e dados carregados
    if escolha == "➕ Nova Sessão":
        st.session_state.doc_id_checkin = None
        st.session_state.dados_checkin_antigos = None
        dados = {}
    else:
        idx = opcoes.index(escolha) - 1
        st.session_state.dados_checkin_antigos = sessoes_existentes[idx]["data"]
        st.session_state.doc_id_checkin = sessoes_existentes[idx]["id"]
        dados = st.session_state.dados_checkin_antigos

    modo_edicao_chk = st.session_state.doc_id_checkin is not None

    st.markdown("---")

    # ============================================================
    # 2. TESTES DEFINIDOS NA AVALIAÇÃO INICIAL
    # ============================================================
    testes_para_hoje = ["Agachamento Bipodal"]
    try:
        docs_aval = db.collection("Avaliacao_Inicial").where("Paciente", "==", st.session_state.paciente).stream()
        lista_aval = [doc.to_dict() for doc in docs_aval]
        if lista_aval:
            ultima_aval = sorted(lista_aval, key=lambda x: x.get('Data_Avaliacao', ''))[-1]
            testes_para_hoje = ultima_aval.get("Testes_Alvo", ["Agachamento Bipodal"])
    except Exception:
        pass

    # ============================================================
    # 3. DADOS BASAIS DA SESSÃO (com valores carregados se em edição)
    # ============================================================
    c_chk1, c_chk2 = st.columns(2)
    with c_chk1:
        if modo_edicao_chk and dados.get("Data"):
            try:
                data_default = datetime.strptime(dados["Data"], "%Y-%m-%d")
            except Exception:
                data_default = datetime.now()
        else:
            data_default = datetime.now()
        data_sessao = st.date_input("Data da Sessão", data_default)

        eva_diaria = st.slider(
            "EVA Diária (Dor Hoje)", 0, 10,
            int(dados.get("Dor", 0)) if modo_edicao_chk else 0
        )
        eva_semanal = st.slider(
            "EVA Semanal (Média da Semana)", 0, 10,
            int(dados.get("EVA_Semanal", 0)) if modo_edicao_chk else 0
        )

        opts_inchaco = ["Nenhum", "Leve (+)", "Moderado (++)", "Intenso (+++)"]
        inchaco_default = dados.get("Inchaço", "Nenhum") if modo_edicao_chk else "Nenhum"
        idx_inc = opts_inchaco.index(inchaco_default) if inchaco_default in opts_inchaco else 0
        inchaco_atual = st.selectbox("Inchaço / Derrame Articular", opts_inchaco, index=idx_inc)

    with c_chk2:
        adm_flex_atual = st.number_input(
            "Flexão Máxima Atingida (Graus)",
            min_value=0, max_value=160,
            value=int(dados.get("Flexao", 90)) if modo_edicao_chk else 90
        )

        opts_ext = ["Completa (0°)", "Déficit de -5°", "Déficit de -10° ou pior"]
        ext_default = dados.get("Extensao", "Completa (0°)") if modo_edicao_chk else "Completa (0°)"
        idx_ext = opts_ext.index(ext_default) if ext_default in opts_ext else 0
        adm_ext_atual = st.selectbox("Extensão Terminal", opts_ext, index=idx_ext)

        opts_sono = ["Bem", "Acordou com dor", "Insônia"]
        sono_default = dados.get("Sono", "Bem") if modo_edicao_chk else "Bem"
        idx_sono = opts_sono.index(sono_default) if sono_default in opts_sono else 0
        sono_atual = st.selectbox("Como dormiu esta noite?", opts_sono, index=idx_sono)

    # ============================================================
    # 4. TESTES FUNCIONAIS
    # ============================================================
    st.markdown("---")
    titulo("🎯 Relacional Funcional")
    st.caption("Classifique a relação entre dor e função para os testes definidos como alvo.")

    opcoes_escala = [
        "Sem Dor (0)",
        "Dor Leve (1 - 3)",
        "Dor Moderada (4 - 7)",
        "Dor Grave (8 - 10)",
        "Incapaz (Não realiza)"
    ]

    testes_antigos = dados.get("Testes_Funcionais", {}) if modo_edicao_chk else {}
    resultados_testes = {}
    for teste in testes_para_hoje:
        default_teste = testes_antigos.get(teste, opcoes_escala[0])
        idx_teste = opcoes_escala.index(default_teste) if default_teste in opcoes_escala else 0
        resposta = st.selectbox(
            f"Desempenho no {teste}:",
            opcoes_escala,
            index=idx_teste,
            key=f"chk_{teste}"
        )
        resultados_testes[teste] = resposta

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================================
    # 5. MOTOR DE SALVAMENTO / ATUALIZAÇÃO
    # ============================================================
    texto_botao = "🔄 ATUALIZAR SESSÃO" if modo_edicao_chk else "💾 REGISTAR SESSÃO DIÁRIA"

    if st.button(texto_botao, width='stretch', type="primary"):
        texto_agachamento = list(resultados_testes.values())[0] if resultados_testes else "Não testado"

        dados_sessao = {
            "Data": data_sessao.strftime("%Y-%m-%d"),
            "Paciente": st.session_state.paciente,
            "Dor": eva_diaria,
            "EVA_Semanal": eva_semanal,
            "Flexao": adm_flex_atual,
            "Extensao": adm_ext_atual,
            "Inchaço": inchaco_atual,
            "Sono": sono_atual,
            "Testes_Funcionais": resultados_testes,
            "Agachamento": texto_agachamento,
            "Profissional_ID": st.session_state.get("user_email", "admin"),
            "Membro": st.session_state.get("membro_ativo", "Joelho"),
        }

        with st.spinner("Sincronizando com a nuvem..."):
            try:
                if modo_edicao_chk:
                    db.collection("Evolucao").document(st.session_state.doc_id_checkin).update(dados_sessao)
                    invalidar_cache("Evolucao")
                    st.success("🔄 Sessão atualizada com sucesso!")
                else:
                    db.collection("Evolucao").add(dados_sessao)
                    invalidar_cache("Evolucao")
                    st.success("✅ Check-in diário registado com sucesso! Os gráficos e o PDF já foram atualizados.")
            except Exception as e:
                st.error(f"❌ Erro ao guardar os dados: {e}")

    st.write("---")
    with st.expander("⚖️ Conformidade LGPD e Privacidade"):
        st.caption("Processamento anonimizado de dados para finalidade exclusiva de Inteligência Clínica.")
