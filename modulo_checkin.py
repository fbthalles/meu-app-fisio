"""GENUA | Módulo 2: Check-in Diário (O Mutante) — Estilo Apple HIG."""
import hashlib
import json
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from config import CORES_GENUA, titulo, secao, toast
from firebase_client import conn, db, invalidar_cache


def _injetar_wake_lock_checkin():
    """Mantém a tela do smartphone acesa e o WebSocket ativo durante o Check-in."""
    components.html(
        """
        <script>
        (function() {
            async function ativarWakeLock() {
                try {
                    if ('wakeLock' in navigator) {
                        await navigator.wakeLock.request('screen');
                    }
                } catch (e) {}
            }
            ativarWakeLock();
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible') ativarWakeLock();
            });
            setInterval(() => {
                if (document.visibilityState === 'visible') {
                    window.dispatchEvent(new Event('resize'));
                }
            }, 25000);
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _parse_data_segura(data_val) -> datetime:
    """Converte string de data (YYYY-MM-DD ou DD/MM/YYYY) em datetime para ordenação cronológica exata."""
    if not data_val:
        return datetime(2000, 1, 1)
    s = str(data_val).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return datetime(2000, 1, 1)


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
        return escolha if escolha in opcoes else padrao
    else:
        idx = opcoes.index(padrao)
        return st.selectbox(label, opcoes, index=idx, key=key)


# Mapa PBE completo para a Escala GROC de -7 a +7 (Jaeschke 1989 / Kamper et al., JOSPT 2009)
MAPA_GROC_LABELS = {
    -7: "🔴 Muitíssimo Pior (-7)",
    -6: "🔴 Muito Pior (-6)",
    -5: "🔴 Significativamente Pior (-5)",
    -4: "🟠 Moderadamente Pior (-4)",
    -3: "🟠 Um Pouco Pior (-3)",
    -2: "🟡 Levemente Pior (-2)",
    -1: "🟡 Quase Igual / Mínima Piora (-1)",
    0: "⚪ Igual / Sem Mudança (0)",
    1: "🔵 Quase Igual / Mínima Melhora (+1)",
    2: "🔵 Levemente Melhor (+2)",
    3: "🟢 Um Pouco Melhor (+3)",
    4: "🟢 Moderadamente Melhor (+4)",
    5: "🟢 Significativamente Melhor (+5)",
    6: "⭐ Muito Melhor (+6)",
    7: "⭐ Muitíssimo Melhor / Recuperado (+7)",
}


def _dor_num_para_categoria_compat(dor_val: int, incapaz: bool = False) -> str:
    """Converte a nota da barra deslizante (0-10) para a categoria compatível com o Painel e PDF."""
    if incapaz:
        return "Incapaz (Não realiza)"
    if dor_val <= 0:
        return "Sem Dor (0)"
    if dor_val <= 3:
        return "Dor Leve (1 - 3)"
    if dor_val <= 7:
        return "Dor Moderada (4 - 7)"
    return "Dor Grave (8 - 10)"


def _categoria_antiga_para_dor_num(valor_salvo) -> tuple:
    """Extrai (nota_0_a_10, bool_incapaz) de sessões antigas ou novas."""
    if isinstance(valor_salvo, (int, float)):
        return int(max(0, min(10, valor_salvo))), False
    s = str(valor_salvo or "").strip()
    if "Incapaz" in s:
        return 10, True
    if "Grave" in s:
        return 8, False
    if "Moderada" in s:
        return 5, False
    if "Leve" in s:
        return 2, False
    return 0, False


@st.fragment(run_every="5s")
def _fragmento_autosave_checkin():
    """Salva automaticamente em background se uma sessão existente estiver sendo editada ou se o auto-save estiver ativo."""
    payload = st.session_state.get("_payload_checkin_atual")
    if not payload or not isinstance(payload, dict):
        return
    if not st.session_state.get("autosave_checkin_ativo", False):
        return

    serializado = json.dumps(payload, sort_keys=True, default=str)
    hash_atual = hashlib.md5(serializado.encode("utf-8")).hexdigest()
    ultimo_hash = st.session_state.get("_ultimo_hash_autosave_chk", "")

    if hash_atual != ultimo_hash:
        try:
            doc_id = st.session_state.get("doc_id_checkin")
            if doc_id:
                db.collection("Evolucao").document(doc_id).set(payload, merge=True)
            else:
                _, doc_ref = db.collection("Evolucao").add(payload)
                st.session_state.doc_id_checkin = doc_ref.id
            invalidar_cache("Evolucao")
            st.session_state["_ultimo_hash_autosave_chk"] = hash_atual
            st.session_state["_horario_autosave_chk"] = datetime.now().strftime("%H:%M:%S")
        except Exception:
            pass

    hora = st.session_state.get("_horario_autosave_chk")
    if hora:
        st.caption(f"🟢 **Check-in salvo automaticamente às {hora}**")


def render():
    _injetar_wake_lock_checkin()

    # Cabeçalho limpo estilo Apple Health
    st.markdown(f"""
        <div style='margin-bottom: 20px;'>
            <h2 style='margin-bottom: 4px;'>📝 Check-in Diário e Evolução</h2>
            <p style='color: {CORES_GENUA['texto_suave']}; font-size: 0.94rem; margin: 0;'>
                Registro rápido de carga de dor, mobilidade articular, relação funcional com dor (0–10) e evolução percebida (GROC -7 a +7 / SANE).
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 1. CARD DE CONTROLE DE SESSÃO (Novo x Editar sessão existente)
    # ============================================================
    st.session_state.setdefault("doc_id_checkin", None)
    st.session_state.setdefault("dados_checkin_antigos", None)

    sessoes_existentes = []
    try:
        df_evo = conn.read_paciente("Evolucao", st.session_state.paciente)
        if not df_evo.empty:
            for _, row in df_evo.iterrows():
                row_dict = row.dropna().to_dict()
                doc_id = row_dict.pop("_doc_id", None)
                if doc_id:
                    sessoes_existentes.append({"id": doc_id, "data": row_dict})
            sessoes_existentes.sort(
                key=lambda x: _parse_data_segura(x["data"].get("Data", "2000-01-01")),
                reverse=True,
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
                    help="Crie uma nova sessão para hoje ou selecione uma sessão anterior para corrigir.",
                )
            else:
                st.info("ℹ️ Nenhuma sessão de check-in registrada ainda. Este será o primeiro registro.")
                escolha = "➕ Nova Sessão"
                opcoes = ["➕ Nova Sessão"]

        with col_modo2:
            if sessoes_existentes and escolha != "➕ Nova Sessão":
                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Excluir Sessão", type="secondary", width="stretch"):
                    st.session_state["confirmar_exclusao_chk"] = True

        if st.session_state.get("confirmar_exclusao_chk"):
            st.warning("⚠️ Tem certeza? Esta sessão será removida do histórico permanentemente.")
            cc1, cc2, _ = st.columns([1, 1, 2])
            with cc1:
                if st.button("✅ Sim, excluir", type="primary", key="conf_del_chk", width="stretch"):
                    try:
                        idx = opcoes.index(escolha) - 1
                        doc_id = sessoes_existentes[idx]["id"]
                        db.collection("Evolucao").document(doc_id).delete()
                        invalidar_cache("Evolucao")
                        st.session_state["confirmar_exclusao_chk"] = False
                        toast("Sessão excluída com sucesso.", "success")
                        st.rerun()
                    except Exception as e:
                        toast(f"Erro ao excluir: {e}", "error")
            with cc2:
                if st.button("❌ Cancelar", type="secondary", key="cancel_del_chk", width="stretch"):
                    st.session_state["confirmar_exclusao_chk"] = False
                    st.rerun()

    if escolha == "➕ Nova Sessão":
        if st.session_state.get("_ultima_escolha_chk") != "➕ Nova Sessão":
            st.session_state.doc_id_checkin = None
            st.session_state.dados_checkin_antigos = None
            st.session_state["autosave_checkin_ativo"] = False
        st.session_state["_ultima_escolha_chk"] = "➕ Nova Sessão"
        dados = {}
    else:
        idx = opcoes.index(escolha) - 1
        st.session_state.dados_checkin_antigos = sessoes_existentes[idx]["data"]
        st.session_state.doc_id_checkin = sessoes_existentes[idx]["id"]
        st.session_state["_ultima_escolha_chk"] = escolha
        st.session_state["autosave_checkin_ativo"] = True
        dados = st.session_state.dados_checkin_antigos

    modo_edicao_chk = st.session_state.doc_id_checkin is not None

    # ============================================================
    # 2. RESGATE DA AVALIAÇÃO INICIAL (COM SUPORTE A PÓS-OP E SEM PSFS)
    # ============================================================
    testes_da_avaliacao = []
    lado_acometido_base = "Direito"
    objetivo_paciente_base = "Retorno à função sem dor"
    sane_baseline = 30
    fenotipo_avaliacao = ""

    try:
        df_aval = conn.read_paciente("Avaliacao_Inicial", st.session_state.paciente)
        if not df_aval.empty:
            lista_aval = df_aval.to_dict("records")
            ultima_aval = sorted(
                lista_aval,
                key=lambda x: _parse_data_segura(x.get("Data_Avaliacao", "01/01/2000")),
            )[-1]

            fenotipo_avaliacao = str(ultima_aval.get("Fenotipo_Clinico", "") or "")
            testes_salvos = ultima_aval.get("Testes_Alvo")
            if testes_salvos is not None:
                if isinstance(testes_salvos, list):
                    testes_da_avaliacao = [t for t in testes_salvos if t]
                elif isinstance(testes_salvos, str):
                    testes_da_avaliacao = [t.strip() for t in testes_salvos.split(",") if t.strip() and t.strip() not in ("Nenhum", "Nenhuma")]
            elif "Pós-Operatório Agudo" not in fenotipo_avaliacao:
                testes_da_avaliacao = ["Agachamento Bipodal"]

            lado_acometido_base = str(ultima_aval.get("Lado_Acometido", "Direito") or "Direito")
            objetivo_paciente_base = str(ultima_aval.get("Objetivo_Paciente", "Retorno à função sem dor") or "Retorno à função sem dor")
            sane_baseline = int(float(ultima_aval.get("SANE_Baseline_Pct", 30) or 30))
    except Exception:
        testes_da_avaliacao = ["Agachamento Bipodal"]

    sane_ultimo_registrado = sane_baseline
    if sessoes_existentes and not modo_edicao_chk:
        try:
            sane_ultimo_registrado = int(float(sessoes_existentes[0]["data"].get("SANE_Pct", sane_baseline)))
        except (ValueError, TypeError):
            sane_ultimo_registrado = sane_baseline

    # ============================================================
    # 3. CARD DE SINAIS E MOBILIDADE DO DIA (Unilateral ou Bilateral)
    # ============================================================
    with st.container(border=True):
        secao(
            "📊 Sinais Clínicos & Mobilidade da Sessão",
            "Ajuste a intensidade álgica (EVA), amplitude articular e marcadores de recuperação."
        )

        c_top1, c_top2 = st.columns([1.3, 2])
        with c_top1:
            if modo_edicao_chk and dados.get("Data"):
                data_default = _parse_data_segura(dados["Data"])
            else:
                data_default = datetime.now()

            data_sessao = st.date_input("📅 Data da Sessão", data_default, format="DD/MM/YYYY")

        with c_top2:
            op_modo_lado = [
                f"Membro Alvo Principal ({lado_acometido_base})",
                "Comparativo Bilateral (Direito × Esquerdo)",
            ]
            default_modo_lado = (
                op_modo_lado[1]
                if (modo_edicao_chk and dados.get("Registro_Bilateral")) or ("Bilateral" in lado_acometido_base)
                else op_modo_lado[0]
            )
            modo_lado_sessao = _seletor_ios(
                "🦵 Escopo de Registro Articular da Sessão",
                op_modo_lado,
                default_modo_lado,
                key="pill_modo_lado_chk",
            )

        eh_bilateral_chk = modo_lado_sessao == op_modo_lado[1]

        st.markdown("<hr style='margin: 14px 0;'>", unsafe_allow_html=True)

        opts_inchaco = ["Nenhum", "Leve (+)", "Moderado (++)", "Intenso (+++)"]
        opts_ext = ["Completa (0°)", "Déficit de -5°", "Déficit de -10° ou pior"]
        opts_sono = ["Bem", "Acordou com dor", "Insônia"]

        if not eh_bilateral_chk:
            c_chk1, c_chk2 = st.columns(2, gap="large")

            with c_chk1:
                eva_diaria = st.slider(
                    f"🔥 EVA Diária — Dor Hoje ({lado_acometido_base}: 0 a 10)",
                    0,
                    10,
                    int(float(dados.get("Dor", 0))) if modo_edicao_chk else 0,
                )
                eva_semanal = st.slider(
                    "📉 EVA Semanal (Média da Semana: 0 a 10)",
                    0,
                    10,
                    int(float(dados.get("EVA_Semanal", 0))) if modo_edicao_chk else 0,
                )

                inchaco_default = dados.get("Inchaço", "Nenhum") if modo_edicao_chk else "Nenhum"
                inchaco_atual = _seletor_ios(
                    "💧 Inchaço / Derrame Articular",
                    opts_inchaco,
                    inchaco_default,
                    key="pill_inchaco",
                )

            with c_chk2:
                adm_flex_atual = st.number_input(
                    "📐 Flexão Máxima Atingida (Graus °)",
                    min_value=0,
                    max_value=160,
                    step=5,
                    value=int(float(dados.get("Flexao", 90))) if modo_edicao_chk else 90,
                )

                ext_default = dados.get("Extensao", "Completa (0°)") if modo_edicao_chk else "Completa (0°)"
                adm_ext_atual = _seletor_ios(
                    "📏 Extensão Terminal",
                    opts_ext,
                    ext_default,
                    key="pill_extensao",
                )

                sono_default = dados.get("Sono", "Bem") if modo_edicao_chk else "Bem"
                sono_atual = _seletor_ios(
                    "🌙 Qualidade do Sono (Última Noite)",
                    opts_sono,
                    sono_default,
                    key="pill_sono",
                )

            if "Esquerdo" in lado_acometido_base:
                dor_d, dor_e = 0, eva_diaria
                flex_d, flex_e = 135, adm_flex_atual
                ext_d, ext_e = "Completa (0°)", adm_ext_atual
                inc_d, inc_e = "Nenhum", inchaco_atual
            else:
                dor_d, dor_e = eva_diaria, 0
                flex_d, flex_e = adm_flex_atual, 135
                ext_d, ext_e = adm_ext_atual, "Completa (0°)"
                inc_d, inc_e = inchaco_atual, "Nenhum"

        else:
            col_d, col_e = st.columns(2, gap="large")

            with col_d:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-bottom: 6px;'>🦵 Joelho DIREITO</h4>", unsafe_allow_html=True)
                dor_d = st.slider(
                    "🔥 EVA Diária — Direito (0 a 10)",
                    0,
                    10,
                    int(float(dados.get("Dor_Dir", dados.get("Dor", 0)))) if modo_edicao_chk else 0,
                    key="sl_dor_d",
                )
                flex_d = st.number_input(
                    "📐 Flexão Máxima — Direito (°)",
                    min_value=0,
                    max_value=160,
                    step=5,
                    value=int(float(dados.get("Flexao_Dir", dados.get("Flexao", 90)))) if modo_edicao_chk else 90,
                    key="num_flex_d",
                )
                ext_d = _seletor_ios(
                    "📏 Extensão Terminal — Direito",
                    opts_ext,
                    dados.get("Extensao_Dir", dados.get("Extensao", "Completa (0°)")) if modo_edicao_chk else "Completa (0°)",
                    key="pill_ext_d",
                )
                inc_d = _seletor_ios(
                    "💧 Inchaço / Derrame — Direito",
                    opts_inchaco,
                    dados.get("Inchaco_Dir", dados.get("Inchaço", "Nenhum")) if modo_edicao_chk else "Nenhum",
                    key="pill_inc_d",
                )

            with col_e:
                st.markdown(f"<h4 style='color: {CORES_GENUA['secundaria']}; margin-bottom: 6px;'>🦵 Joelho ESQUERDO</h4>", unsafe_allow_html=True)
                dor_e = st.slider(
                    "🔥 EVA Diária — Esquerdo (0 a 10)",
                    0,
                    10,
                    int(float(dados.get("Dor_Esq", dados.get("Dor", 0)))) if modo_edicao_chk else 0,
                    key="sl_dor_e",
                )
                flex_e = st.number_input(
                    "📐 Flexão Máxima — Esquerdo (°)",
                    min_value=0,
                    max_value=160,
                    step=5,
                    value=int(float(dados.get("Flexao_Esq", dados.get("Flexao", 90)))) if modo_edicao_chk else 90,
                    key="num_flex_e",
                )
                ext_e = _seletor_ios(
                    "📏 Extensão Terminal — Esquerdo",
                    opts_ext,
                    dados.get("Extensao_Esq", dados.get("Extensao", "Completa (0°)")) if modo_edicao_chk else "Completa (0°)",
                    key="pill_ext_e",
                )
                inc_e = _seletor_ios(
                    "💧 Inchaço / Derrame — Esquerdo",
                    opts_inchaco,
                    dados.get("Inchaco_Esq", dados.get("Inchaço", "Nenhum")) if modo_edicao_chk else "Nenhum",
                    key="pill_inc_e",
                )

            st.markdown("<hr style='margin: 14px 0;'>", unsafe_allow_html=True)
            c_glob1, c_glob2 = st.columns(2, gap="large")
            with c_glob1:
                eva_semanal = st.slider(
                    "📉 EVA Semanal (Média Geral da Semana: 0 a 10)",
                    0,
                    10,
                    int(float(dados.get("EVA_Semanal", max(dor_d, dor_e)))) if modo_edicao_chk else max(dor_d, dor_e),
                )
            with c_glob2:
                sono_default = dados.get("Sono", "Bem") if modo_edicao_chk else "Bem"
                sono_atual = _seletor_ios(
                    "🌙 Qualidade do Sono (Última Noite)",
                    opts_sono,
                    sono_default,
                    key="pill_sono_bi",
                )

            eva_diaria = max(dor_d, dor_e)
            adm_flex_atual = min(flex_d, flex_e)
            adm_ext_atual = ext_d if opts_ext.index(ext_d) >= opts_ext.index(ext_e) else ext_e
            inchaco_atual = inc_d if opts_inchaco.index(inc_d) >= opts_inchaco.index(inc_e) else inc_e

    # ============================================================
    # 4. CARD DE RELACIONAL FUNCIONAL (OPCIONAL PÓS-OP + BARRA DESLIZANTE DE DOR 0-10)
    # ============================================================
    with st.container(border=True):
        secao(
            "🎯 Relacional Funcional (Parametrizável & Barra Deslizante de Dor 0–10)",
            "Defina o que entra no check-in de hoje (opcional para Pós-Op) e deslize a barra de dor (0 a 10) para cada movimento realizado."
        )

        catalogo_testes_chk = [
            "Marcha sem Muletas",
            "Extensão Ativa Terminal",
            "Agachamento Bipodal",
            "Agachamento Unipodal (D)",
            "Agachamento Unipodal (E)",
            "Step Up (D)",
            "Step Up (E)",
            "Step Down (D)",
            "Step Down (E)",
            "Lunge / Afundo",
            "Salto (Hop Test)",
            "Corrida",
        ]

        testes_antigos_dict = dados.get("Testes_Funcionais", {}) if (modo_edicao_chk and isinstance(dados.get("Testes_Funcionais"), dict)) else {}
        testes_num_antigos = dados.get("Testes_Funcionais_Dor_Num", {}) if (modo_edicao_chk and isinstance(dados.get("Testes_Funcionais_Dor_Num"), dict)) else {}

        default_ativos_hoje = list(testes_antigos_dict.keys()) if modo_edicao_chk and testes_antigos_dict else testes_da_avaliacao
        for t_custom in default_ativos_hoje:
            if t_custom not in catalogo_testes_chk:
                catalogo_testes_chk.append(t_custom)

        testes_ativos_hoje = st.multiselect(
            "⚙️ Definir o que vai entrar no Check-in de hoje (Remova testes que não se aplicam ao Pós-Op atual):",
            options=catalogo_testes_chk,
            default=default_ativos_hoje,
            help="Em Pós-Operatório imediato, você pode deixar apenas Marcha/Extensão ou deixar vazio se nenhum teste funcional de carga for realizado.",
        )

        resultados_testes = {}
        resultados_testes_num = {}

        if not testes_ativos_hoje:
            st.info("🛡️ Nenhum teste funcional de carga selecionado para hoje (Modo Pós-Operatório / Proteção Tecidual).")
        else:
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            for i, teste in enumerate(testes_ativos_hoje):
                if teste in testes_num_antigos:
                    val_dor_init = int(float(testes_num_antigos[teste]))
                    incapaz_init = "Incapaz" in str(testes_antigos_dict.get(teste, ""))
                elif teste in testes_antigos_dict:
                    val_dor_init, incapaz_init = _categoria_antiga_para_dor_num(testes_antigos_dict[teste])
                else:
                    val_dor_init, incapaz_init = 0, False

                c_sl, c_inc = st.columns([3.2, 1.0], vertical_alignment="center")
                with c_inc:
                    nao_realiza = st.checkbox(
                        "Incapaz / Não realiza",
                        value=incapaz_init,
                        key=f"chk_inc_{i}_{teste}",
                    )
                with c_sl:
                    dor_teste = st.slider(
                        f"🏃 **{teste}** — Dor durante o movimento (0 = Sem Dor | 10 = Dor Máxima)",
                        min_value=0,
                        max_value=10,
                        value=val_dor_init,
                        disabled=nao_realiza,
                        key=f"chk_slider_dor_{i}_{teste}",
                    )

                cat_compat = _dor_num_para_categoria_compat(dor_teste, incapaz=nao_realiza)
                resultados_testes[teste] = cat_compat
                resultados_testes_num[teste] = 10 if nao_realiza else dor_teste

    # ============================================================
    # 5. CARD PBE: ESCALA GROC (-7 a +7), SATISFAÇÃO (PASS) E SANE (SEM PSFS)
    # ============================================================
    with st.container(border=True):
        secao(
            "🧭 Percepção de Evolução (GROC -7 a +7), Satisfação (PASS) & Meta Funcional (SANE)",
            "Métricas centradas no paciente: GROC (-7 a +7 | Kamper et al., JOSPT 2009), PASS (Tubach et al., 2005) e SANE (0% a 100% | Shelbourne et al., 2009)."
        )

        st.markdown(f"""
            <div style='background: rgba(16, 62, 85, 0.06); border-left: 4px solid {CORES_GENUA['secundaria']};
                        padding: 10px 14px; border-radius: 8px; margin-bottom: 14px; font-size: 0.9rem;'>
                <strong style='color: {CORES_GENUA['primaria']};'>🏆 Objetivo Principal do Paciente (Marco Zero):</strong>
                {objetivo_paciente_base}
                <span style='color: {CORES_GENUA['texto_suave']}; font-size: 0.82rem; margin-left: 8px;'>
                    (Baseline inicial: SANE {sane_baseline}%)
                </span>
            </div>
        """, unsafe_allow_html=True)

        # Escala GROC de -7 a +7
        if modo_edicao_chk and dados.get("GROC_Score") is not None:
            try:
                groc_init = max(-7, min(7, int(float(dados.get("GROC_Score", 0)))))
            except Exception:
                groc_init = 0
        else:
            groc_init = 3 if len(sessoes_existentes) >= 3 else 2

        groc_score_num = st.select_slider(
            "📈 Escala GROC (-7 a +7) — Em comparação ao início do tratamento, como o paciente sente o joelho hoje?",
            options=list(range(-7, 8)),
            value=groc_init,
            format_func=lambda x: f"{x:+d}" if x != 0 else "0",
            key="slider_groc_7",
        )
        groc_escolhido = MAPA_GROC_LABELS.get(groc_score_num, "⚪ Igual / Sem Mudança (0)")
        st.caption(f"Classificação GROC selecionada: **{groc_escolhido}**")

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

        c_pass, c_sane = st.columns([1.3, 1.7], gap="large")

        with c_pass:
            opcoes_pass = [
                "👍 Sim — Satisfeito com o estado atual",
                "👎 Não — Ainda insatisfeito / Precisa evoluir",
            ]
            pass_default = (
                dados.get("PASS_Satisfacao", opcoes_pass[1])
                if modo_edicao_chk
                else opcoes_pass[1]
            )
            pass_escolhido = _seletor_ios(
                "🤝 PASS — Se o joelho permanecesse como está hoje, o paciente estaria satisfeito?",
                opcoes_pass,
                pass_default,
                key="pill_pass",
            )
            pass_atingido_bool = pass_escolhido.startswith("👍")

        with c_sane:
            sane_val_default = (
                int(float(dados.get("SANE_Pct", sane_ultimo_registrado)))
                if modo_edicao_chk
                else sane_ultimo_registrado
            )
            sane_hoje = st.slider(
                "🎯 Quão perto do objetivo final o paciente se sente hoje? (SANE: 0% a 100%)",
                min_value=0,
                max_value=100,
                step=5,
                value=max(0, min(100, sane_val_default)),
                help="0% = Estaca zero | 100% = Objetivo da fisioterapia 100% alcançado.",
            )

        distancia_meta_hoje = 100 - sane_hoje
        ganho_sane = sane_hoje - sane_baseline

        k1, k2, k3 = st.columns(3)
        k1.metric(
            "Progresso rumo ao Objetivo (SANE)",
            f"{sane_hoje}%",
            f"{ganho_sane:+d}% vs Marco Zero",
        )
        k2.metric(
            "Distância Restante da Meta",
            f"{distancia_meta_hoje}%",
            "Meta Atingida!" if distancia_meta_hoje <= 10 else "Em construção",
            delta_color="normal" if distancia_meta_hoje <= 10 else "off",
        )
        k3.metric(
            "Mudança Global (GROC -7 a +7)",
            f"{groc_score_num:+d} pts",
            "MCID Atingido (≥ +3)" if groc_score_num >= 3 else ("Alerta de Piora" if groc_score_num < 0 else "Sub-limiar"),
            delta_color="normal" if groc_score_num >= 3 else ("inverse" if groc_score_num < 0 else "off"),
        )

    # ============================================================
    # 6. PAYLOAD DA SESSÃO, AUTO-SAVE E BOTÃO DE REGISTRO
    # ============================================================
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
        "Testes_Funcionais_Dor_Num": resultados_testes_num,
        "Agachamento": texto_agachamento,
        "Registro_Bilateral": eh_bilateral_chk,
        "Lado_Referencia": lado_acometido_base,
        "Dor_Dir": dor_d,
        "Dor_Esq": dor_e,
        "Flexao_Dir": flex_d,
        "Flexao_Esq": flex_e,
        "Extensao_Dir": ext_d,
        "Extensao_Esq": ext_e,
        "Inchaco_Dir": inc_d,
        "Inchaco_Esq": inc_e,
        "GROC_Label": groc_escolhido,
        "GROC_Score": groc_score_num,
        "PASS_Satisfacao": pass_escolhido,
        "PASS_Atingido": pass_atingido_bool,
        "SANE_Pct": sane_hoje,
        "Distancia_Objetivo_Pct": distancia_meta_hoje,
        "Ganho_SANE_Pct": ganho_sane,
        "Profissional_ID": st.session_state.get("user_email", "admin"),
        "Membro": st.session_state.get("membro_ativo", "Joelho"),
    }

    st.session_state["_payload_checkin_atual"] = dados_sessao
    _fragmento_autosave_checkin()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    texto_botao = "🔄 ATUALIZAR SESSÃO" if st.session_state.get("doc_id_checkin") else "💾 REGISTRAR SESSÃO DIÁRIA"

    if st.button(texto_botao, width="stretch", type="primary"):
        with st.spinner("Sincronizando sessão com a nuvem..."):
            try:
                if st.session_state.get("doc_id_checkin"):
                    db.collection("Evolucao").document(st.session_state.doc_id_checkin).set(dados_sessao, merge=True)
                    invalidar_cache("Evolucao")
                    toast("Sessão atualizada com sucesso!", "success")
                else:
                    _, novo_chk_ref = db.collection("Evolucao").add(dados_sessao)
                    st.session_state.doc_id_checkin = novo_chk_ref.id
                    st.session_state["autosave_checkin_ativo"] = True
                    invalidar_cache("Evolucao")
                    toast("Check-in diário registrado com sucesso! Auto-save ativado para edições.", "success")
            except Exception as e:
                toast(f"Erro ao guardar os dados: {e}", "error")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    with st.expander("⚖️ Conformidade LGPD e Privacidade"):
        st.caption("Processamento seguro de dados clínicos para finalidade exclusiva de acompanhamento fisioterapêutico e Inteligência Clínica.")
