"""GENUA | Módulo 3: Painel Analítico (Cérebro Clínico — Joelho) — Estilo Apple Health.

Performance: matplotlib fica em lazy import dentro de render(),
para não pesar o startup do app quando o utilizador ainda não abriu o painel.
"""
import streamlit as st
import pandas as pd
import numpy as np
from config import CORES_GENUA, titulo, secao, toast, aplicar_tema_matplotlib
from firebase_client import conn
from ia_clinica import analisar_paciente, renderizar_insights, normalizar_diagnostico


def _mapear_inchaco(val) -> int:
    """Converte o texto de inchaço do Check-in ('Leve (+)', etc.) ou número para escala 0 a 3."""
    if pd.isna(val):
        return 0
    s = str(val).strip().lower()
    if "+++" in s or "intenso" in s or "grave" in s or s == "3":
        return 3
    if "++" in s or "moderado" in s or s == "2":
        return 2
    if "+" in s or "leve" in s or s == "1":
        return 1
    try:
        return int(float(s))
    except Exception:
        return 0


def _score_funcional_item(texto_resp) -> float:
    """Converte a resposta textual do teste funcional para score numérico de 0 a 10."""
    if texto_resp is None or pd.isna(texto_resp):
        return None
    s = str(texto_resp).strip()
    mapa = {
        "Sem Dor (0)": 10.0, "Sem Dor": 10.0,
        "Dor Leve (1 - 3)": 7.0, "Dor Leve": 7.0,
        "Dor Moderada (4 - 7)": 4.0, "Dor Moderada": 4.0,
        "Dor Grave (8 - 10)": 1.0, "Dor Grave": 1.0,
        "Incapaz (Não realiza)": 0.0, "Incapaz": 0.0,
        "Não testado": None,
    }
    return mapa.get(s)


def render():
    # Lazy import do Matplotlib + Aplicação do Tema Apple Health
    import matplotlib.pyplot as plt
    aplicar_tema_matplotlib(plt)

    p_sel = st.session_state.paciente

    # --- A. RESGATE DO CADASTRO ---
    try:
        df_cad = conn.read("Cadastro")
        registro_p = df_cad[df_cad['Nome'].astype(str).str.strip() == p_sel].iloc[-1]
        idade_p = int(float(registro_p.get('Idade', 0))) if pd.notna(registro_p.get('Idade')) else "—"
        dx_clinico_base = registro_p.get('Diagnostico_Clinico', 'Não especificado') or 'Não especificado'
    except (KeyError, IndexError, ValueError, AttributeError):
        idade_p = "—"
        dx_clinico_base = "Não especificado"

    # --- B. RESGATE DA AVALIAÇÃO BASE (BILATERAL, METAS, TESTES E FLAGS) ---
    av_p = {}
    tem_av = False
    try:
        df_av = conn.read_paciente("Avaliacao_Inicial", p_sel)
        if not df_av.empty:
            if "Data_Avaliacao" in df_av.columns:
                df_av["_dt"] = pd.to_datetime(df_av["Data_Avaliacao"], format="mixed", dayfirst=True, errors="coerce")
                df_av = df_av.sort_values("_dt")
            av_p = df_av.iloc[-1].to_dict()
            tem_av = True
    except Exception:
        tem_av = False

    av_data = av_p.get('Data_Avaliacao', 'N/A') if tem_av else 'N/A'
    av_qp = av_p.get('QP', 'Não registrada') if tem_av else 'Não registrada'
    av_lado = av_p.get('Lado_Acometido', 'Não especificado') if tem_av else 'Não especificado'
    av_objetivo = av_p.get('Objetivo_Paciente', 'Não especificado') if tem_av else 'Não especificado'
    try:
        sane_base_av = float(av_p.get('SANE_Baseline_Pct', 30.0) or 30.0) if tem_av else 30.0
    except (ValueError, TypeError):
        sane_base_av = 30.0
    try:
        psfs_base_av = int(float(av_p.get('PSFS_Baseline', 3) or 3)) if tem_av else 3
    except (ValueError, TypeError):
        psfs_base_av = 3

    # 1. CARD HEADER DO PACIENTE (Estilo Apple Health Profile)
    with st.container(border=True):
        st.markdown(f"""
            <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;'>
                <div>
                    <span style='font-size: 0.76rem; font-weight: 700; text-transform: uppercase;
                                 letter-spacing: 0.06em; color: {CORES_GENUA['secundaria']};'>
                        Painel Analítico Longitudinal · Joelho ({av_lado})
                    </span>
                    <h2 style='margin: 2px 0 4px 0; color: {CORES_GENUA['texto_escuro']};'>
                        👤 {p_sel}
                    </h2>
                    <p style='margin: 0; color: {CORES_GENUA['texto_suave']}; font-size: 0.92rem;'>
                        <b>Diagnóstico de Triagem:</b> {dx_clinico_base} &nbsp;|&nbsp;
                        <b>Objetivo (PSFS):</b> {av_objetivo}
                    </p>
                </div>
                <div style='display: flex; gap: 8px; align-items: center;'>
                    <span style='background: rgba(57, 142, 155, 0.12); color: {CORES_GENUA['secundaria']};
                                 padding: 6px 14px; border-radius: 980px; font-weight: 700; font-size: 0.84rem;'>
                        🦵 Lado: {av_lado}
                    </span>
                    <span style='background: rgba(16, 62, 85, 0.08); color: {CORES_GENUA['primaria']};
                                 padding: 6px 14px; border-radius: 980px; font-weight: 700; font-size: 0.86rem;'>
                        {idade_p} anos
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 2. EXPANDER DE AVALIAÇÃO FÍSICA BASELINE (COM SEPARAÇÃO DIREITO x ESQUERDO)
    if tem_av:
        with st.expander(f"📋 Consultar Ficha de Avaliação Inicial Bilateral (Baseline: {av_data})", expanded=False):
            t_resumo, t_fisico, t_funcional, t_proms = st.tabs([
                "🗣️ Resumo & Meta", "📐 Físico (Dir × Esq)", "💪 Funcional & Força", "📊 Scores (PROMs)"
            ])

            with t_resumo:
                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    st.markdown("**Anamnese, Lateralidade e Dor:**")
                    st.markdown(f"- **Lado Acometido Principal:** {av_lado}")
                    st.markdown(f"- **QP:** {av_qp}")
                    st.markdown(f"- **Origem / Mecanismo:** {av_p.get('Origem_Dor', 'N/A')}")
                    st.markdown(f"- **Tipo de Dor:** {av_p.get('Class_Dor', 'Não avaliada')}")
                    st.markdown(f"- **Zonas de Dor:** {av_p.get('Zonas_Dor', 'N/A')}")
                    st.markdown(f"- **Red Flags:** {av_p.get('Red_Flags', 'Nenhuma')}")
                with c_r2:
                    st.markdown("**Objetivo do Paciente (PSFS / SANE) & Exames:**")
                    st.markdown(f"- **Objetivo Principal:** {av_objetivo}")
                    st.markdown(f"- **PSFS Inicial:** {psfs_base_av}/10 pts *(MCID: 2,0 pts)*")
                    st.markdown(f"- **SANE Inicial (Quão perto da meta):** {sane_base_av:.0f}% *(Distância inicial: {100 - sane_base_av:.0f}%)*")
                    st.markdown(f"- **Exames Apresentados:** {av_p.get('Exames_Apresentados', 'Nenhum')}")
                    st.markdown(f"- **Laudo Principal:** {av_p.get('Laudo_Exames', 'Não relatado')}")

            with t_fisico:
                st.markdown(f"**🚶 Padrão de Marcha Global:** {av_p.get('Marcha', 'N/A')} &nbsp;|&nbsp; **Alterações Cutâneas:** {av_p.get('Pele', 'Normal')}")
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

                c_fd, c_fe = st.columns(2)
                with c_fd:
                    st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-bottom: 6px;'>🦵 Membro DIREITO</h4>", unsafe_allow_html=True)
                    st.markdown(f"- **Derrame Articular:** {av_p.get('Derrame_Dir', av_p.get('Derrame', 'N/A'))}")
                    st.markdown(f"- **Alinhamento Estático:** {av_p.get('Alinhamento_Dir', av_p.get('Alinhamento', 'N/A'))}")
                    st.markdown(f"- **Trofismo Muscular:** {av_p.get('Trofismo_Dir', av_p.get('Trofismo', 'N/A'))}")
                    perim_d_val = av_p.get('Perimetria_Dir_cm')
                    st.markdown(f"- **Perimetria de Coxa:** {f'{perim_d_val} cm' if perim_d_val else av_p.get('Perimetria', 'N/A')}")
                    st.markdown(f"- **Palpação Dolorosa:** {av_p.get('Palpacao_Dir', av_p.get('Palpacao', 'N/A'))}")
                    st.markdown(f"- **Godet / Temperatura:** {av_p.get('Godet_Dir', av_p.get('Godet', 'N/A'))} / {av_p.get('Temperatura_Dir', av_p.get('Temperatura', 'N/A'))}")
                    st.markdown("**Testes Especiais Positivos (Direito):**")
                    st.markdown(f"- **Ligamentares:** {av_p.get('Testes_Ligamentares_Dir', av_p.get('Testes_Ligamentares', 'Nenhum'))}")
                    st.markdown(f"- **Meniscais:** {av_p.get('Testes_Meniscais_Dir', av_p.get('Testes_Meniscais', 'Nenhum'))}")
                    st.markdown(f"- **Femoropatelar/Tendão:** {av_p.get('Testes_Femoropatelar_Dir', av_p.get('Testes_Femoropatelar', 'Nenhum'))}")

                with c_fe:
                    st.markdown(f"<h4 style='color: {CORES_GENUA['secundaria']}; margin-bottom: 6px;'>🦵 Membro ESQUERDO</h4>", unsafe_allow_html=True)
                    st.markdown(f"- **Derrame Articular:** {av_p.get('Derrame_Esq', av_p.get('Derrame', 'N/A'))}")
                    st.markdown(f"- **Alinhamento Estático:** {av_p.get('Alinhamento_Esq', av_p.get('Alinhamento', 'N/A'))}")
                    st.markdown(f"- **Trofismo Muscular:** {av_p.get('Trofismo_Esq', av_p.get('Trofismo', 'N/A'))}")
                    perim_e_val = av_p.get('Perimetria_Esq_cm')
                    st.markdown(f"- **Perimetria de Coxa:** {f'{perim_e_val} cm' if perim_e_val else av_p.get('Perimetria', 'N/A')}")
                    st.markdown(f"- **Palpação Dolorosa:** {av_p.get('Palpacao_Esq', av_p.get('Palpacao', 'N/A'))}")
                    st.markdown(f"- **Godet / Temperatura:** {av_p.get('Godet_Esq', av_p.get('Godet', 'N/A'))} / {av_p.get('Temperatura_Esq', av_p.get('Temperatura', 'N/A'))}")
                    st.markdown("**Testes Especiais Positivos (Esquerdo):**")
                    st.markdown(f"- **Ligamentares:** {av_p.get('Testes_Ligamentares_Esq', 'Nenhum')}")
                    st.markdown(f"- **Meniscais:** {av_p.get('Testes_Meniscais_Esq', 'Nenhum')}")
                    st.markdown(f"- **Femoropatelar/Tendão:** {av_p.get('Testes_Femoropatelar_Esq', 'Nenhum')}")

            with t_funcional:
                c_fun1, c_fun2 = st.columns(2)
                with c_fun1:
                    st.caption("FORÇA (OXFORD) & DINAMOMETRIA (KGF)")
                    st.markdown(f"- **Oxford (Direito):** {av_p.get('Forca_Geral_Dir', 'N/A')}")
                    st.markdown(f"- **Oxford (Esquerdo):** {av_p.get('Forca_Geral_Esq', 'N/A')}")
                    st.markdown(f"- **Dinamometria (Direito):** {av_p.get('Dinamometria_Dir', 'N/A')}")
                    st.markdown(f"- **Dinamometria (Esquerdo):** {av_p.get('Dinamometria_Esq', 'N/A')}")
                    st.markdown(f"- **Controle Motor (Dir):** {av_p.get('CM_Membro_Dir', 'N/A')}")
                    st.markdown(f"- **Controle Motor (Esq):** {av_p.get('CM_Membro_Esq', 'N/A')}")
                with c_fun2:
                    st.caption("MOBILIDADE ARTICULAR (GONIOMETRIA) & FLEXIBILIDADE")
                    st.markdown(f"- **ADM Flexão (Dir / Esq):** {av_p.get('ADM_Joelho_Flexao', 'N/A')}")
                    st.markdown(f"- **ADM Extensão (Dir / Esq):** {av_p.get('ADM_Joelho_Extensao', 'N/A')}")
                    st.markdown(f"- **Lunge Test (Dir / Esq):** {av_p.get('Lunge_Test', 'N/A')}")
                    st.markdown(f"- **Flexibilidade (Direito):** {av_p.get('Flexibilidade_Dir', av_p.get('Flexibilidade', 'Normal'))}")
                    st.markdown(f"- **Flexibilidade (Esquerdo):** {av_p.get('Flexibilidade_Esq', av_p.get('Flexibilidade', 'Normal'))}")

            with t_proms:
                c_p1, c_p2, c_p3, c_p4, c_p5, c_p6 = st.columns(6)
                c_p1.metric("LEFS", f"{float(av_p.get('LEFS_Pct', 0) or 0):.1f}%")
                c_p2.metric("Lysholm", f"{av_p.get('Lysholm_Pts', 0)} pts")
                c_p3.metric("VISA-P", f"{av_p.get('VISA_P_Pts', 0)} pts")
                c_p4.metric("WOMAC", f"{float(av_p.get('WOMAC_Pct', 0) or 0):.1f}%")
                c_p5.metric("KOOS", f"{float(av_p.get('KOOS_Pct', 0) or 0):.1f}%")
                c_p6.metric("IKDC", f"{float(av_p.get('IKDC_Pct', 0) or 0):.1f}%")
    else:
        st.info("⚠️ Nenhuma Avaliação Inicial registada para este paciente.")

    # --- C. MOTOR DE EVOLUÇÃO (CHECK-INS) ---
    df_p = conn.read_paciente("Evolucao", p_sel)
    if df_p.empty:
        st.warning("⚠️ O paciente ainda não possui sessões de Check-in diário registadas.")
        st.stop()

    if 'Membro' not in df_p.columns:
        df_p['Membro'] = "Joelho"
    else:
        df_p['Membro'] = df_p['Membro'].fillna("Joelho")

    df_p = df_p[df_p['Membro'] == "Joelho"].copy()
    if df_p.empty:
        st.warning("⚠️ O paciente ainda não possui sessões de Check-in diário para Joelho.")
        st.stop()

    # Parser seguro para datas ISO (YYYY-MM-DD) ou BR (DD/MM/YYYY)
    df_p['Data_dt'] = pd.to_datetime(df_p['Data'], format="mixed", dayfirst=False, errors="coerce")
    df_p = df_p.sort_values('Data_dt')
    df_p['Sessão_Num'] = [
        f"S{i+1} ({d.strftime('%d/%m') if pd.notna(d) else '?'})"
        for i, d in enumerate(df_p['Data_dt'])
    ]

    if 'Dor' not in df_p.columns:
        df_p['Dor'] = 0
    df_p['Dor'] = pd.to_numeric(df_p['Dor'], errors='coerce').fillna(0)

    col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
    if col_inc not in df_p.columns:
        df_p[col_inc] = "Nenhum"
    df_p['Inchaco_N'] = df_p[col_inc].apply(_mapear_inchaco)

    for col, default in [
        ('Flexao', 90), ('Extensao', 'Completa (0°)'),
        ('Agachamento', 'Sem Dor (0)'), ('Step_Up', 'Sem Dor (0)'), ('Step_Down', 'Sem Dor (0)')
    ]:
        if col not in df_p.columns:
            df_p[col] = default

    # Normaliza SANE_Pct ao longo das sessões (para gráfico de Distância do Objetivo)
    if 'SANE_Pct' not in df_p.columns:
        df_p['SANE_Pct'] = np.nan
    df_p['SANE_Pct_Num'] = pd.to_numeric(df_p['SANE_Pct'], errors='coerce')

    # Calcula Score Funcional (0-10) e Prontidão Funcional (0-100%) por sessão
    func_scores = []
    lsi_scores = []
    testes_nomes = set()

    for _, row in df_p.iterrows():
        testes = row.get('Testes_Funcionais', {})
        scores_sessao = []
        if isinstance(testes, dict) and testes:
            for t_nome, resultado in testes.items():
                testes_nomes.add(t_nome)
                sc = _score_funcional_item(resultado)
                if sc is not None:
                    scores_sessao.append(sc)
        else:
            for col_legado in ['Agachamento', 'Step_Up', 'Step_Down']:
                sc = _score_funcional_item(row.get(col_legado))
                if sc is not None:
                    scores_sessao.append(sc)

        media_10 = (sum(scores_sessao) / len(scores_sessao)) if scores_sessao else None
        func_scores.append(media_10)
        lsi_scores.append(min(max(float(media_10 * 10.0), 0.0), 100.0) if media_10 is not None else 100.0)

    df_p['Func_Score'] = func_scores
    df_p['LSI'] = lsi_scores

    # --- SELETOR DE SESSÃO E KPIS PRINCIPAIS ---
    c_titulo_kpi, c_seletor = st.columns([3, 1.2])
    with c_titulo_kpi:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        titulo("📈 Indicadores de Prontidão, Carga e Satisfação (PBE)")
    with c_seletor:
        sessao_escolhida = st.selectbox(
            "📅 Sessão em Análise:",
            options=df_p['Sessão_Num'].tolist()[::-1],
            index=0
        )

    ultima = df_p[df_p['Sessão_Num'] == sessao_escolhida].iloc[0]

    # --- O CÉREBRO CLÍNICO BAYESIANO ---
    dor_atual = int(ultima.get('Dor', 0))
    inchaco_atual = int(ultima.get('Inchaco_N', 0))
    sono_atual = ultima.get('Sono', 'Bem')
    lsi_atual = float(ultima.get('LSI', 0))
    media_dor = float(df_p['Dor'].mean())

    # Extração segura de SANE, GROC e PASS da sessão selecionada
    sane_sessao = ultima.get('SANE_Pct_Num')
    if pd.isna(sane_sessao):
        sane_sessao = sane_base_av
    else:
        sane_sessao = float(sane_sessao)
    dist_meta_sessao = max(0.0, 100.0 - sane_sessao)
    ganho_sane_sessao = sane_sessao - sane_base_av

    groc_sessao_val = ultima.get('GROC_Score')
    try:
        groc_sessao_int = int(float(groc_sessao_val)) if pd.notna(groc_sessao_val) else None
    except (ValueError, TypeError):
        groc_sessao_int = None

    pass_sessao_str = str(ultima.get('PASS_Satisfacao', 'Não registado') or 'Não registado')
    pass_bool = ultima.get('PASS_Atingido')
    if pd.isna(pass_bool) or pass_bool is None:
        pass_bool = pass_sessao_str.startswith("👍")

    testes_ult = ultima.get('Testes_Funcionais', {}) if isinstance(ultima.get('Testes_Funcionais'), dict) else {}
    agach_str = str(testes_ult.get('Agachamento Bipodal', ultima.get('Agachamento', 'Sem Dor')))
    step_down_str = str(
        testes_ult.get('Step Down')
        or testes_ult.get('Step Down (D)')
        or testes_ult.get('Step Down (E)')
        or ultima.get('Step_Down', 'Sem Dor')
    )
    ext_str = str(ultima.get('Extensao', 'Completa (0°)'))

    if "Incapaz" in agach_str and inchaco_atual >= 2 and dor_atual >= 8:
        fenotipo = "🚨 Risco Estrutural (Sinal de Alerta)"
        diretriz = "Incapacidade de descarga de peso + Edema Agudo. Indicação de avaliação médica/imagem e proteção de carga."
    elif ("Incapaz" in step_down_str or "Moderada" in step_down_str or "Grave" in step_down_str) and inchaco_atual <= 1:
        fenotipo = "🟣 Provável Sobrecarga Femoropatelar"
        diretriz = "Dor na desaceleração excêntrica. Foco em fortalecimento póstero-lateral de anca e controlo de vetor em cadeia fechada (0-45°)."
    elif ("Déficit" in ext_str) and inchaco_atual >= 2:
        fenotipo = "🟤 Bloqueio Articular / Derangement"
        diretriz = "Défice de extensão terminal associado a derrame articular. Priorizar ganho de extensão passiva/ativa e controlo de efusão."
    elif ("Incapaz" in agach_str or "Moderada" in agach_str) and "Completa" in ext_str and inchaco_atual == 0:
        fenotipo = "🟠 Perfil Tendinopático Reativo"
        diretriz = "Dor em armazenamento/libertação de energia elástica sem derrame articular. Modular carga excêntrica e aplicar isometria analgésica."
    elif dor_atual <= 3 and inchaco_atual <= 1 and lsi_atual >= 80:
        fenotipo = "🟢 Fase de Remodelamento Funcional"
        diretriz = "Alta tolerância mecânica. Progressão segura para desaceleração rápida, pliometria e gesto desportivo."
    else:
        fenotipo = "🔵 Acomodação de Carga"
        diretriz = "Sinais reativos mistos. Modular volume e intensidade conforme irritabilidade tecidual (regra das 24h)."

    status_clinico = "Excelente" if lsi_atual >= 85 else "Regular" if lsi_atual >= 60 else "Atenção"

    # --- 3. DASHBOARD DE MÉTRICAS VISUAIS (Apple Health KPIs + GROC/PASS/SANE) ---
    m1, m2, m3, m4, m5 = st.columns(5)
    delta_pct = ((dor_atual - media_dor) / media_dor * 100) if media_dor > 0 else 0
    m1.metric("Dor Atual (vs Média)", f"{dor_atual}/10", f"{delta_pct:+.0f}%", delta_color="inverse")
    m2.metric("Efusão / Inchaço", f"Grau {inchaco_atual}/3")
    m3.metric("Prontidão Funcional", f"{lsi_atual:.0f}%", status_clinico)
    m4.metric(
        "Distância da Meta",
        f"{dist_meta_sessao:.0f}%",
        f"SANE: {sane_sessao:.0f}% ({ganho_sane_sessao:+.0f}%)"
    )
    m5.metric(
        "Satisfação (PASS/GROC)",
        "Satisfeito 👍" if pass_bool else "Em Evolução",
        f"GROC: {groc_sessao_int:+d} pts" if groc_sessao_int is not None else fenotipo.split()[1]
    )

    # Se a sessão foi registada em Modo Bilateral no Check-in, exibe resumo D x E da sessão
    if bool(ultima.get("Registro_Bilateral")):
        with st.container(border=True):
            st.caption("🦵 COMPARATIVO BILATERAL DA SESSÃO SELECIONADA (DIREITO × ESQUERDO)")
            cb1, cb2, cb3, cb4 = st.columns(4)
            cb1.metric("EVA (Dir | Esq)", f"{ultima.get('Dor_Dir', 0)}/10 | {ultima.get('Dor_Esq', 0)}/10")
            cb2.metric("Flexão (Dir | Esq)", f"{ultima.get('Flexao_Dir', 90)}° | {ultima.get('Flexao_Esq', 90)}°")
            cb3.metric("Extensão (Dir | Esq)", f"{ultima.get('Extensao_Dir', '-')} | {ultima.get('Extensao_Esq', '-')}")
            cb4.metric("Derrame (Dir | Esq)", f"{ultima.get('Inchaco_Dir', '-')} | {ultima.get('Inchaco_Esq', '-')}")

    # Dupla Barra de Progresso: Prontidão Funcional vs Progresso rumo ao Objetivo do Paciente (SANE)
    with st.container(border=True):
        c_prog1, c_prog2 = st.columns(2, gap="large")
        with c_prog1:
            st.markdown(f"**🎯 Índice de Prontidão nos Testes Alvo: {lsi_atual:.0f}%** *(Meta PBE: ≥ 90%)*")
            st.progress(min(max(lsi_atual / 100.0, 0.0), 1.0))
        with c_prog2:
            st.markdown(
                f"**🏆 Progresso rumo ao Objetivo do Paciente (SANE): {sane_sessao:.0f}%** "
                f"*(Faltam {dist_meta_sessao:.0f}% para a meta)*"
            )
            st.progress(min(max(sane_sessao / 100.0, 0.0), 1.0))

    # --- 4. SEPARADORES GRÁFICOS DE ALTA PERFORMANCE (Apple Health Charts) ---
    t1, t2, t_ic = st.tabs([
        "📊 Correlação Dor × Função",
        "📉 Evolução Biomecânica & Meta (SANE)",
        "🧠 Inteligência Clínica"
    ])

    with t1:
        with st.container(border=True):
            secao(
                "📊 Correlação Dor × Função ao Longo do Tratamento",
                "Quando a linha de Dor (coral) cai e a de Função (verde) sobe, o cruzamento confirma eficácia terapêutica."
            )

            fig1, ax1 = plt.subplots(figsize=(10, 4.2), dpi=120)

            cor_dor = CORES_GENUA['alerta_erro']
            ax1.plot(
                df_p['Sessão_Num'], df_p['Dor'],
                color=cor_dor, marker='o', markersize=7, lw=2.8,
                label="Dor (EVA 0-10)", zorder=4
            )
            ax1.fill_between(range(len(df_p)), df_p['Dor'], alpha=0.10, color=cor_dor)
            ax1.set_ylabel("Dor (EVA 0-10)", color=cor_dor, fontweight='600')
            ax1.set_ylim(-0.5, 10.5)

            cor_func = CORES_GENUA['alerta_sucesso']
            ax1b = ax1.twinx()
            ax1b.grid(False)
            func_plot = df_p['Func_Score'].interpolate() if df_p['Func_Score'].notna().sum() > 1 else df_p['Func_Score']
            ax1b.plot(
                df_p['Sessão_Num'], func_plot,
                color=cor_func, marker='s', markersize=6.5, lw=2.6,
                linestyle='--', label="Função (Score 0-10)", zorder=3
            )
            ax1b.fill_between(range(len(df_p)), func_plot.fillna(0), alpha=0.08, color=cor_func)
            ax1b.set_ylabel("Função (0-10)", color=cor_func, fontweight='600')
            ax1b.set_ylim(-0.5, 10.5)

            ax1.spines['top'].set_visible(False)
            ax1b.spines['top'].set_visible(False)
            plt.setp(ax1.get_xticklabels(), rotation=25, ha='right', fontsize=9)

            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax1b.get_legend_handles_labels()
            ax1.legend(
                lines1 + lines2, labels1 + labels2,
                loc='upper center', bbox_to_anchor=(0.5, 1.14),
                ncol=2, frameon=False, fontsize=9.5
            )

            fig1.tight_layout()
            st.pyplot(fig1)

            if testes_nomes:
                st.markdown("<hr style='margin: 16px 0;'>", unsafe_allow_html=True)
                st.markdown("**🎯 Evolução por Movimento Alvo (1ª Sessão → Atual)**")
                cols_t = st.columns(min(len(testes_nomes), 3))
                for idx_t, teste_nome in enumerate(sorted(testes_nomes)):
                    valores_teste = []
                    for _, row in df_p.iterrows():
                        testes = row.get('Testes_Funcionais', {})
                        if isinstance(testes, dict) and teste_nome in testes:
                            valores_teste.append(testes.get(teste_nome, "—"))
                    primeira = valores_teste[0] if valores_teste else "—"
                    ultima_val = valores_teste[-1] if valores_teste else "—"
                    with cols_t[idx_t % len(cols_t)]:
                        st.caption(f"🏃 {teste_nome.upper()}")
                        st.markdown(f"**{primeira}** → **{ultima_val}**")

        # Card do Gráfico de Dispersão
        with st.container(border=True):
            secao(
                "🔬 Dispersão: Tolerância à Carga (Dor × Prontidão Funcional)",
                "Relação inversa esperada entre nível álgico e capacidade funcional."
            )
            fig1b, ax1c = plt.subplots(figsize=(10, 3.2), dpi=120)
            ax1c.scatter(
                df_p['Dor'], df_p['LSI'],
                color=CORES_GENUA['secundaria'], s=110, alpha=0.85,
                edgecolors='white', linewidth=2, zorder=4
            )
            if len(df_p) > 2 and df_p['Dor'].nunique() > 1:
                z = np.polyfit(df_p['Dor'], df_p['LSI'], 1)
                p = np.poly1d(z)
                x_vals = np.linspace(df_p['Dor'].min(), df_p['Dor'].max(), 50)
                ax1c.plot(x_vals, p(x_vals), color=CORES_GENUA['primaria'], linestyle='--', lw=1.6, alpha=0.7)
            ax1c.set_xlabel("Dor (EVA 0-10)", fontweight='600')
            ax1c.set_ylabel("Prontidão (%)", fontweight='600')
            ax1c.set_xlim(-0.5, 10.5)
            ax1c.set_ylim(-5, 105)
            ax1c.spines['top'].set_visible(False)
            ax1c.spines['right'].set_visible(False)
            fig1b.tight_layout()
            st.pyplot(fig1b)

    with t2:
        with st.container(border=True):
            secao(
                "📉 Evolução Longitudinal (Contextual ao Fenótipo)",
                "O eixo secundário adapta-se automaticamente às métricas prioritárias do diagnóstico."
            )

            try:
                fen = normalizar_diagnostico(dx_clinico_base)
                metricas = fen.get("metricas_relevantes", ["Dor", "Flexao"])
                st.caption(f"🎯 Fenótipo detetado: **{fen['label']}** · Métricas priorizadas: `{', '.join(metricas)}`")
            except Exception:
                metricas = ["Dor", "Flexao"]

            fig2, ax2 = plt.subplots(figsize=(10, 4.2), dpi=120)

            ax2.plot(
                df_p['Sessão_Num'], df_p['Dor'],
                color=CORES_GENUA['alerta_erro'], marker='o', markersize=7, lw=2.8, label="Dor (EVA)"
            )
            ax2.set_ylabel("Dor (EVA 0-10)", color=CORES_GENUA['alerta_erro'], fontweight='600')
            ax2.set_ylim(-0.5, 10.5)

            ax3 = ax2.twinx()
            ax3.grid(False)

            if "Flexao" in metricas:
                ax3.plot(
                    df_p['Sessão_Num'], df_p['Flexao'],
                    color=CORES_GENUA['secundaria'], marker='s', markersize=6.5, lw=2.5, linestyle=':', label="Flexão (°)"
                )
                ax3.set_ylabel("Flexão (°)", color=CORES_GENUA['secundaria'], fontweight='600')
                ax3.set_ylim(0, 160)
            elif "Carga_Excentrica" in metricas or "Testes_Funcionais" in metricas:
                func_data = df_p['Func_Score'].interpolate() if df_p['Func_Score'].notna().sum() > 1 else df_p['Func_Score']
                ax3.plot(
                    df_p['Sessão_Num'], func_data,
                    color=CORES_GENUA['alerta_sucesso'], marker='s', markersize=6.5, lw=2.5, linestyle=':', label="Função (Score)"
                )
                ax3.set_ylabel("Função (0-10)", color=CORES_GENUA['alerta_sucesso'], fontweight='600')
                ax3.set_ylim(-0.5, 10.5)
            else:
                ax3.plot(
                    df_p['Sessão_Num'], df_p['Flexao'],
                    color=CORES_GENUA['secundaria'], marker='s', markersize=6.5, lw=2.5, linestyle=':', label="Flexão (°)"
                )
                ax3.set_ylabel("Flexão (°)", color=CORES_GENUA['secundaria'], fontweight='600')
                ax3.set_ylim(0, 160)

            ax2.spines['top'].set_visible(False)
            ax3.spines['top'].set_visible(False)
            plt.setp(ax2.get_xticklabels(), rotation=25, ha='right', fontsize=9)

            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax3.get_legend_handles_labels()
            ax2.legend(
                lines1 + lines2, labels1 + labels2,
                loc='upper center', bbox_to_anchor=(0.5, 1.14),
                ncol=2, frameon=False, fontsize=9.5
            )

            fig2.tight_layout()
            st.pyplot(fig2)

        # Novo Card Gráfico: Curva de Aproximação ao Objetivo do Paciente (SANE %)
        if df_p['SANE_Pct_Num'].notna().any():
            with st.container(border=True):
                secao(
                    "🏆 Evolução rumo ao Objetivo do Paciente (SANE % — PBE)",
                    f"Objetivo registado: '{av_objetivo}' · Linha tracejada indica limiar de alta subjetiva (≥ 85% | Shelbourne et al., 2009)."
                )
                fig_sane, ax_s = plt.subplots(figsize=(10, 3.2), dpi=120)
                sane_serie = df_p['SANE_Pct_Num'].fillna(sane_base_av)
                ax_s.axhline(y=85, color=CORES_GENUA['alerta_sucesso'], linestyle='--', lw=1.6, alpha=0.8, label="Limiar de Alta (85%)")
                ax_s.axhline(y=sane_base_av, color=CORES_GENUA['texto_suave'], linestyle=':', lw=1.4, alpha=0.7, label=f"Marco Zero ({sane_base_av:.0f}%)")
                ax_s.plot(
                    df_p['Sessão_Num'], sane_serie,
                    color=CORES_GENUA['primaria'], marker='o', markersize=7, lw=2.8, label="SANE (% do Objetivo)"
                )
                ax_s.fill_between(range(len(df_p)), sane_serie, alpha=0.10, color=CORES_GENUA['secundaria'])
                ax_s.set_ylabel("Progresso da Meta (%)", fontweight='600', color=CORES_GENUA['primaria'])
                ax_s.set_ylim(-5, 105)
                ax_s.spines['top'].set_visible(False)
                ax_s.spines['right'].set_visible(False)
                plt.setp(ax_s.get_xticklabels(), rotation=25, ha='right', fontsize=9)
                ax_s.legend(loc='lower right', frameon=False, fontsize=9)
                fig_sane.tight_layout()
                st.pyplot(fig_sane)

    with t_ic:
        # Camada 1: Motor de IA Baseado em Evidência (MCID, LSI, GROC/PASS/SANE, Bandeiras)
        with st.container(border=True):
            try:
                with st.spinner("🧠 A executar análise clínica baseada em evidência..."):
                    insights = analisar_paciente(st.session_state.paciente)
                renderizar_insights(insights, CORES_GENUA)
            except Exception as e:
                toast(f"Erro ao gerar insights: {e}", "error")
                st.caption("Verifique se o paciente possui avaliação inicial e sessões de check-in registadas.")

        # Camada 2 & 3: Raciocínio Clínico e Gatilhos Bio-Psico-Sociais
        with st.container(border=True):
            secao(
                "🔬 Raciocínio Clínico & Modulação de Carga",
                "Síntese algorítmica cruzando derrame articular, resposta a carga excêntrica/elástica e mobilidade."
            )
            st.markdown(f"- **Classificação da Sessão Atual:** {fenotipo}")
            st.markdown(f"- **Diretriz Clínica PBE:** {diretriz}")

            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            col_b1.metric("Amplitude de Flexão", f"{ultima.get('Flexao', 90)}°")
            col_b2.metric("Extensão Terminal", f"{ultima.get('Extensao', 'Completa (0°)')}")
            col_b3.metric("Padrão de Sono", f"{sono_atual}")
            col_b4.metric("Estado Aceitável (PASS)", "Sim (Satisfeito)" if pass_bool else "Não (Em evolução)")

    # --- 5. CARD DE EXPORTAÇÃO DO LAUDO VISUAL APPLE DARK ---
    with st.container(border=True):
        secao(
            "📄 Exportação de Laudo Clínico Avançado (Apple Dark Mode)",
            "Gera um relatório visual completo com KPIs, gráficos em alta resolução, PROMs e referências científicas. Abra o ficheiro transferido e prima Ctrl+P (ou Cmd+P no Mac) para guardar em PDF."
        )

        if st.button("⚙️ GERAR LAUDO VISUAL COMPLETO", width='stretch', type="primary"):
            with st.spinner("🧠 A compilar laudo clínico com gráficos de alta resolução e análise de IA..."):
                try:
                    import streamlit.components.v1 as components
                    from pdf_laudo import gerar_laudo_html
                    from ia_clinica import analisar_paciente as _analisar, normalizar_diagnostico as _normalizar

                    dados_aval = av_p if tem_av else {}
                    historico = df_p.to_dict("records")

                    insights_l = _analisar(st.session_state.paciente)
                    fenotipo_l = _normalizar(dados_aval.get('Diagnostico_Clinico', '') if dados_aval else dx_clinico_base)

                    laudo_html = gerar_laudo_html(
                        paciente_nome=st.session_state.paciente,
                        dados_aval=dados_aval,
                        historico=historico,
                        insights=insights_l,
                        fenotipo=fenotipo_l
                    )

                    st.download_button(
                        label="📥 TRANSFERIR LAUDO (HTML / PDF) — Abrir e usar Cmd+P / Ctrl+P",
                        data=laudo_html.encode('utf-8'),
                        file_name=f"Laudo_GENUA_{st.session_state.paciente.replace(' ', '_')}.html",
                        mime="text/html",
                        type="primary",
                        width='stretch'
                    )
                    toast("Laudo gerado com sucesso! Confira a pré-visualização abaixo.", "success")
                    components.html(laudo_html, height=1350, scrolling=True)

                except Exception as e:
                    toast(f"Erro ao gerar o laudo: {e}", "error")
                    st.caption("Verifique se o paciente possui avaliação inicial e sessões de check-in registadas.")
