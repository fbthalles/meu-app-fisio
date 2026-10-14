"""GENUA | Módulo 2: Check-in Diário (O Mutante) — Estilo Apple HIG (1-Tap Touch UI)."""
import streamlit as st
from datetime import datetime
from config import CORES_GENUA, secao
from firebase_client import db, invalidar_cache


def _seletor_ios(label: str, opcoes: list, valor_atual: str, key: str):
    """Renderiza st.pills (botões de toque único estilo iOS) com fallback seguro."""
    padrao = valor_atual if valor_atual in opcoes else opcoes[0]
    if hasattr(st, "pills"):
        escolha = st.pills(
            label,
            opcoes,
            default=padrao,
            selection_mode="single",
            key=key,
        )
        # Se o usuário clicar novamente na pílula ativa (retornando None), mantém o padrão seguro
        return escolha if escolha in opcoes else padrao
    else:
        idx = opcoes.index(padrao)
        return st.selectbox(label, opcoes, index=idx, key=key)


def render():
    # Cabeçalho limpo estilo Apple Health
    st.markdown(f"""
        <div style='margin-bottom: 20px;'>
            <h2 style='margin-bottom: 4px;'>📝 Check-in Diário e Evolução</h2>
            <p style='color: {CORES_GENUA['texto_suave']}; font-size: 0.94rem; margin: 0;'>
                Registro rápido de carga de dor, mobilidade articular e resposta aos testes funcionais alvo.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 1. CARD DE CONTROLE DE SESSÃO (Novo x Editar sessão existente)
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

    with st.container(border=True):
        col_modo1, col_modo2 = st.columns([2.5, 1])
        with col_modo1:
            if sessoes_existentes:
                opcoes = ["➕ Nova Sessão"] + [
                    f"✏️ {s['data'].get('Data', '?')} — Dor: {s['data'].get('Dor', '?')}/10 | Flexão: {s['data'].get('Flexao', '?')}°"
                    for s in sessoes_existentes
                ]
                escolha = st.selectbox(
                    "🎯 Modo de Registro:",
                    opcoes,
                    key="seletor_checkin",
                    help="Crie uma nova sessão para hoje ou selecione uma sessão anterior para corrigir."
                )
            else:
                st.info("ℹ️ Nenhuma sessão de check-in registrada ainda. Este será o primeiro registro.")
                escolha = "➕ Nova Sessão"
                opcoes = ["➕ Nova Sessão"]

        with col_modo2:
            if sessoes_existentes and escolha != "➕ Nova Sessão":
                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Excluir Sessão", type="secondary", width="stretch"):
                    st.session_state['confirmar_exclusao_chk'] = True

        # Confirmação de exclusão dentro do Card
        if st.session_state.get('confirmar_exclusao_chk'):
            st.warning("⚠️ Tem certeza? Esta sessão será removida do histórico permanentemente.")
            cc1, cc2, _ = st.columns([1, 1, 2])
            with cc1:
                if st.button("✅ Sim, excluir", type="primary", key="conf_del_chk", width="stretch"):
                    try:
                        idx = opcoes.index(escolha) - 1
                        doc_id = sessoes_existentes[idx]["id"]
                        db.collection("Evolucao").document(doc_id).delete()
                        invalidar_cache("Evolucao")
                        st.session_state['confirmar_exclusao_chk'] = False
                        st.success("Sessão excluída com sucesso.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
            with cc2:
                if st.button("❌ Cancelar", type="secondary", key="cancel_del_chk", width="stretch"):
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

    # ============================================================
    # 2. RESGATE DOS TESTES DEFINIDOS NA AVALIAÇÃO INICIAL
    # ============================================================
    testes_para_hoje = ["Agachamento Bipodal"]
    try:
        docs_aval = db.collection("Avaliacao_Inicial").where("Paciente", "==", st.session_state.paciente).stream()
        lista_aval = [doc.to_dict() for doc in docs_aval]
        if lista_aval:
            ultima_aval = sorted(lista_aval, key=lambda x: x.get('Data_Avaliacao', ''))[-1]
            testes_salvos = ultima_aval.get("Testes_Alvo")
            if testes_salvos and isinstance(testes_salvos, list):
                testes_para_hoje = testes_salvos
    except Exception:
        pass

    # ============================================================
    # 3. CARD DE SINAIS E MOBILIDADE DO DIA
    # ============================================================
    with st.container(border=True):
        secao(
            "📊 Sinais Clínicos & Mobilidade da Sessão",
            "Ajuste a intensidade álgica (EVA), amplitude articular e marcadores de recuperação."
        )

        c_chk1, c_chk2 = st.columns(2, gap="large")

        with c_chk1:
            if modo_edicao_chk and dados.get("Data"):
                try:
                    data_default = datetime.strptime(dados["Data"], "%Y-%m-%d")
                except Exception:
                    data_default = datetime.now()
            else:
                data_default = datetime.now()

            data_sessao = st.date_input("📅 Data da Sessão", data_default, format="DD/MM/YYYY")

            eva_diaria = st.slider(
                "🔥 EVA Diária (Dor Hoje: 0 a 10)",
                0, 10,
                int(dados.get("Dor", 0)) if modo_edicao_chk else 0
            )
            eva_semanal = st.slider(
                "📉 EVA Semanal (Média da Semana: 0 a 10)",
                0, 10,
                int(dados.get("EVA_Semanal", 0)) if modo_edicao_chk else 0
            )

            opts_inchaco = ["Nenhum", "Leve (+)", "Moderado (++)", "Intenso (+++)"]
            inchaco_default = dados.get("Inchaço", "Nenhum") if modo_edicao_chk else "Nenhum"
            inchaco_atual = _seletor_ios(
                "💧 Inchaço / Derrame Articular",
                opts_inchaco,
                inchaco_default,
                key="pill_inchaco"
            )

        with c_chk2:
            adm_flex_atual = st.number_input(
                "📐 Flexão Máxima Atingida (Graus °)",
                min_value=0, max_value=160, step=5,
                value=int(dados.get("Flexao", 90)) if modo_edicao_chk else 90
            )

            opts_ext = ["Completa (0°)", "Déficit de -5°", "Déficit de -10° ou pior"]
            ext_default = dados.get("Extensao", "Completa (0°)") if modo_edicao_chk else "Completa (0°)"
            adm_ext_atual = _seletor_ios(
                "📏 Extensão Terminal",
                opts_ext,
                ext_default,
                key="pill_extensao"
            )

            opts_sono = ["Bem", "Acordou com dor", "Insônia"]
            sono_default = dados.get("Sono", "Bem") if modo_edicao_chk else "Bem"
            sono_atual = _seletor_ios(
                "🌙 Qualidade do Sono (Última Noite)",
                opts_sono,
                sono_default,
                key="pill_sono"
            )

    # ============================================================
    # 4. CARD DE TESTES FUNCIONAIS (Toque Rápido por Pills)
    # ============================================================
    with st.container(border=True):
        secao(
            "🎯 Relacional Funcional (Testes Alvo)",
            "Toque na resposta que descreve a relação dor × função em cada movimento avaliado hoje."
        )

        opcoes_escala = [
            "Sem Dor (0)",
            "Dor Leve (1 - 3)",
            "Dor Moderada (4 - 7)",
            "Dor Grave (8 - 10)",
            "Incapaz (Não realiza)"
        ]

        testes_antigos = dados.get("Testes_Funcionais", {}) if modo_edicao_chk else {}
        resultados_testes = {}

        for i, teste in enumerate(testes_para_hoje):
            default_teste = (
                testes_antigos.get(teste, opcoes_escala[0])
                if isinstance(testes_antigos, dict)
                else opcoes_escala[0]
            )
            resposta = _seletor_ios(
                f"🏃 {teste}",
                opcoes_escala,
                default_teste,
                key=f"chk_pill_{i}_{teste}"
            )
            resultados_testes[teste] = resposta

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # ============================================================
    # 5. MOTOR DE SALVAMENTO / ATUALIZAÇÃO
    # ============================================================
    texto_botao = "🔄 ATUALIZAR SESSÃO" if modo_edicao_chk else "💾 REGISTRAR SESSÃO DIÁRIA"

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

        with st.spinner("Sincronizando sessão com a nuvem..."):
            try:
                if modo_edicao_chk:
                    db.collection("Evolucao").document(st.session_state.doc_id_checkin).update(dados_sessao)
                    invalidar_cache("Evolucao")
                    st.success("🔄 Sessão atualizada com sucesso!")
                else:
                    db.collection("Evolucao").add(dados_sessao)
                    invalidar_cache("Evolucao")
                    st.success("✅ Check-in diário registrado com sucesso! Os gráficos e o laudo já foram atualizados.")
            except Exception as e:
                st.error(f"❌ Erro ao guardar os dados: {e}")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    with st.expander("⚖️ Conformidade LGPD e Privacidade"):
        st.caption("Processamento seguro de dados clínicos para finalidade exclusiva de acompanhamento fisioterapêutico e Inteligência Clínica.")
