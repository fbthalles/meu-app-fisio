"""GENUA | Módulo 3: Painel Analítico (Cérebro Clínico) — Estilo Apple Health."""
from services.medidas import lados_dinamometria, lsi_dinamometria, nota_dor_gesto
import streamlit as st
import pandas as pd
import numpy as np
from config import CORES_GENUA, titulo, secao, toast, aplicar_tema_matplotlib
from firebase_client import conn
from ia_clinica import analisar_paciente, renderizar_insights, normalizar_diagnostico, _sane_valido, _groc_valido
from modulo_avaliacao import gerar_pdf_somente_avaliacao


# ============================================================
# HELPERS MATEMÁTICOS E PARSERS BLINDADOS (RETROCOMPATÍVEIS)
# ============================================================
def _mapear_inchaco(val) -> int:
    """Converte o texto de inchaço do Check-in ('Leve (+)', etc.) ou número para escala 0 a 3."""
    if pd.isna(val):
        return 0
    s = str(val).strip().lower()
    if "+++" in s or "intenso" in s or "grave" in s or "3+" in s or s == "3":
        return 3
    if "++" in s or "moderado" in s or "2+" in s or s == "2":
        return 2
    if "+" in s or "leve" in s or "vestígio" in s or "onda" in s or s == "1":
        return 1
    try:
        return int(float(s))
    except Exception:
        return 0


def _score_funcional_item(texto_resp, dor_num_override=None):
    if str(texto_resp).startswith("Incapaz"):
        return 0.0
    dor = nota_dor_gesto(texto_resp, dor_num_override)
    return 10 - dor if dor is not None else None


def _medidas_gestos(sessao):
    categorias = sessao.get("Testes_Funcionais")
    notas = sessao.get("Testes_Funcionais_Dor_Num")
    categorias = categorias if isinstance(categorias, dict) else {}
    notas = notas if isinstance(notas, dict) else {}
    medidas = {}
    for nome in dict.fromkeys([*categorias, *notas]):
        resposta = categorias.get(nome)
        score = _score_funcional_item(resposta, notas.get(nome))
        if score is not None:
            descricao = "Incapaz" if str(resposta).startswith("Incapaz") else (
                f"Dor {10 - score:g}/10" if nome in notas or isinstance(resposta, (float, int)) else resposta
            )
            medidas[nome] = (score, descricao)
    return medidas


def _extrair_chave_str(texto_bruto, prefixo: str, default: float = 0.0) -> float:
    """Extrai float de strings padronizadas do Firestore como 'Ext:35.0 Flex:20.0'."""
    if texto_bruto is None or pd.isna(texto_bruto):
        return default
    if isinstance(texto_bruto, (int, float)):
        return float(texto_bruto)
    try:
        partes = str(texto_bruto).replace("|", " ").split()
        for p in partes:
            if p.lower().startswith(prefixo.lower() + ":"):
                val_str = p.split(":", 1)[1].replace("cm", "").replace("°", "").replace(",", ".").strip()
                return float(val_str)
    except Exception:
        pass
    return default


def _calcular_lsi_seguro(val_d: float, val_e: float, lado_acometido: str) -> tuple:
    """
    Retorna (lsi_pct, val_lesado, val_saudavel, status_cor).
    Fórmula: (Lado Lesado / Lado Saudável) * 100 (Grindem et al., 2016).
    """
    val_d = pd.to_numeric(val_d, errors="coerce")
    val_e = pd.to_numeric(val_e, errors="coerce")
    if pd.isna(val_d) or pd.isna(val_e) or not np.isfinite(val_d) or not np.isfinite(val_e) or val_d < 0 or val_e < 0:
        return None, 0.0, 0.0, "⚪"
    lesado, saudavel = lados_dinamometria(val_d, val_e, lado_acometido)
    lsi = lsi_dinamometria(lesado, saudavel)
    if lsi is None:
        return None, lesado, saudavel, "⚪"
    cor = "🟢" if lsi >= 90.0 else ("🟡" if lsi >= 85.0 else "🔴")
    return round(lsi, 1), round(lesado, 1), round(saudavel, 1), cor


def _detectar_proms_preenchidos(av_p: dict, prom_fenotipo: str = "KOOS") -> list:
    """Detecta quais questionários foram preenchidos na Avaliação Inicial."""
    if not av_p:
        return []

    if isinstance(av_p.get("PROMs_Aplicados"), list):
        return av_p.get("PROMs_Aplicados")

    lefs_v = float(av_p.get("LEFS_Pct", 0) or 0)
    visap_v = float(av_p.get("VISA_P_Pts", 0) or 0)
    lysh_v = float(av_p.get("Lysholm_Pts", 0) or 0)
    womac_v = float(av_p.get("WOMAC_Pct", 0) or 0)
    koos_v = float(av_p.get("KOOS_Pct", 0) or 0)
    ikdc_v = float(av_p.get("IKDC_Pct", 0) or 0)

    candidatos = []
    if koos_v > 0 and round(koos_v, 1) != 100.0:
        candidatos.append("KOOS")
    if ikdc_v > 0 and round(ikdc_v, 1) != 75.0:
        candidatos.append("IKDC")
    if lefs_v > 0:
        candidatos.append("LEFS")
    if visap_v > 0 and round(visap_v, 1) != 50.0:
        candidatos.append("VISA-P")
    if lysh_v > 0 and round(lysh_v, 1) != 100.0:
        candidatos.append("Lysholm")
    if womac_v > 0 and round(womac_v, 1) != 100.0:
        candidatos.append("WOMAC")

    return candidatos[:2] if candidatos else []


def _calcular_curva_prognostica_sane(
    df_completo: pd.DataFrame,
    df_janela: pd.DataFrame,
    sane_base: float,
    semanas_esperadas: int = None
) -> dict:
    """Calcula a trajetória prognóstica esperada (PBE) vs. evolução real do paciente na escala SANE (0-100%)."""
    w_esp = float(semanas_esperadas) if (semanas_esperadas and semanas_esperadas > 0) else 16.0
    s0 = float(np.clip(sane_base, 0.0, 100.0))
    meta_alta = max(85.0, s0)

    dt_inicio = df_completo['Data_dt'].iloc[0] if (not df_completo.empty and 'Data_dt' in df_completo.columns) else pd.NaT

    tempos_semanas = []
    esperado_vals = []

    for idx_row, row in df_janela.iterrows():
        dt_atual = row.get('Data_dt', pd.NaT)
        try:
            matches = df_completo.index[df_completo['Sessão_Num'] == row['Sessão_Num']].tolist()
            pos_global = matches[0] if matches else idx_row
        except Exception:
            pos_global = idx_row

        if pd.notna(dt_inicio) and pd.notna(dt_atual):
            dias = max(0.0, float((dt_atual - dt_inicio).days))
            t_sem = dias / 7.0
            if t_sem == 0.0 and pos_global > 0:
                t_sem = pos_global * 0.5
        else:
            t_sem = pos_global * 0.5

        tau = min(1.0, max(0.0, t_sem / w_esp))
        val_esp = s0 + (meta_alta - s0) * (tau ** 0.75)

        tempos_semanas.append(round(t_sem, 1))
        esperado_vals.append(round(float(val_esp), 1))

    sane_real_serie = df_janela['SANE_Pct_Num'].tolist()
    real_atual = float(sane_real_serie[-1]) if sane_real_serie else s0
    esp_atual = float(esperado_vals[-1]) if esperado_vals else s0
    desvio = round(real_atual - esp_atual, 1)

    if not np.isfinite(desvio):
        status, cor, resumo = "incompleto", "⚪", "Falta medida de SANE para comparar a sessão com o marco zero."
    elif desvio >= 5.0:
        status = "acima"
        cor = "🟢"
        resumo = (
            f"Paciente está **{desvio:+.1f}% acima** da curva prognóstica esperada para a semana "
            f"{tempos_semanas[-1] if tempos_semanas else 0:.1f} (Real: **{real_atual:.0f}%** vs. Esperado PBE: **{esp_atual:.0f}%**)."
        )
    elif desvio >= -10.0:
        status = "dentro"
        cor = "🔵"
        resumo = (
            f"Paciente evolui **dentro da janela prognóstica esperada** pela literatura na semana "
            f"{tempos_semanas[-1] if tempos_semanas else 0:.1f} (Real: **{real_atual:.0f}%** vs. Esperado PBE: **{esp_atual:.0f}%** · Δ {desvio:+.1f}%)."
        )
    else:
        status = "abaixo"
        cor = "🔴"
        resumo = (
            f"Paciente encontra-se **{abs(desvio):.1f}% abaixo** da trajetória esperada na semana "
            f"{tempos_semanas[-1] if tempos_semanas else 0:.1f} (Real: **{real_atual:.0f}%** vs. Esperado PBE: **{esp_atual:.0f}%**). "
            f"Revisar barreiras biopsicossociais, adesão ou dosagem de carga."
        )

    return {
        "semanas_janela": int(w_esp),
        "tempos_semanas": tempos_semanas,
        "esperado": esperado_vals,
        "real": sane_real_serie,
        "real_atual": round(real_atual, 1),
        "esp_atual": round(esp_atual, 1),
        "desvio": desvio,
        "status": status,
        "cor": cor,
        "resumo": resumo,
    }


def render():
    import matplotlib.pyplot as plt
    aplicar_tema_matplotlib(plt)

    p_sel = st.session_state.paciente

    # ============================================================
    # A. RESGATE DO CADASTRO
    # ============================================================
    idade_p = "—"
    dx_clinico_base = "Não especificado"
    ocupacao_p = "Não informada"
    indicacao_cad = ""
    try:
        df_cad = conn.read("Cadastro")
        if not df_cad.empty and "Nome" in df_cad.columns:
            filtro_cad = df_cad[df_cad['Nome'].astype(str).str.strip() == p_sel]
            if not filtro_cad.empty:
                registro_p = filtro_cad.iloc[-1]
                idade_p = int(float(registro_p.get('Idade', 0))) if pd.notna(registro_p.get('Idade')) else "—"
                dx_clinico_base = registro_p.get('Diagnostico_Clinico') or registro_p.get('Historia') or 'Não especificado'
                ocupacao_p = registro_p.get('Ocupacao') or 'Não informada'
                indicacao_cad = str(registro_p.get('Medico_Indicador', '') or '')
    except Exception:
        pass

    # ============================================================
    # B. RESGATE DA AVALIAÇÃO INICIAL (MARCO ZERO)
    # ============================================================
    df_p = conn.read_paciente("Evolucao", p_sel)
    if 'Membro' not in df_p.columns:
        df_p['Membro'] = "Joelho"
    else:
        df_p['Membro'] = df_p['Membro'].fillna("Joelho")

    df_p = df_p[df_p['Membro'] == "Joelho"].copy()
    df_p['Data_dt'] = pd.to_datetime(df_p.get('Data', pd.Series(index=df_p.index, dtype=str)), format="mixed", dayfirst=True, errors="coerce")
    df_p = df_p.sort_values('Data_dt').reset_index(drop=True)
    df_p['Sessão_Num'] = [
        f"S{i+1} ({d.strftime('%d/%m') if pd.notna(d) else '?'})"
        for i, d in enumerate(df_p['Data_dt'])
    ]

    for coluna in ("Dor", "EVA_Semanal", "Flexao", "SANE_Pct"):
        df_p[coluna] = pd.to_numeric(df_p.get(coluna), errors="coerce")
        df_p[coluna] = df_p[coluna].replace([np.inf, -np.inf], np.nan)
    df_p["SANE_Pct_Num"] = df_p["SANE_Pct"]
    inchaco = df_p.get("Inchaço", df_p.get("Inchaco", pd.Series(index=df_p.index, dtype=str)))
    df_p["Inchaco_N"] = inchaco.map(_mapear_inchaco, na_action="ignore").astype(float)

    if not df_p.empty:
        c_titulo_kpi, c_seletor = st.columns([3, 1.2])
        with c_titulo_kpi:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            titulo("📈 Indicadores Executivos de Carga, Simetria e Evolução (PBE)")
        with c_seletor:
            opcoes_sessoes = df_p['Sessão_Num'].tolist()
            sessao_escolhida = st.selectbox(
                "📅 Sessão em Análise:",
                options=opcoes_sessoes[::-1],
                index=0
            )

        idx_sel = df_p[df_p['Sessão_Num'] == sessao_escolhida].index[0]
        df_p = df_p.iloc[:idx_sel + 1].copy()
    av_p = {}
    tem_av = False
    try:
        df_av = conn.read_paciente("Avaliacao_Inicial", p_sel)
        if not df_av.empty:
            if "Data_Avaliacao" in df_av.columns:
                df_av["_dt"] = pd.to_datetime(df_av["Data_Avaliacao"], format="mixed", dayfirst=True, errors="coerce")
                df_av = df_av.sort_values("_dt")
            if not df_p.empty:
                df_av = df_av[df_av["_dt"] <= df_p.iloc[-1]["Data_dt"]] if "_dt" in df_av else df_av.iloc[:0]
            if not df_av.empty:
                av_p = df_av.iloc[-1].to_dict()
                tem_av = True
    except Exception:
        tem_av = False

    av_data = av_p.get('Data_Avaliacao', 'N/A') if tem_av else 'N/A'
    av_qp = av_p.get('QP', 'Não registrada') if tem_av else 'Não registrada'
    av_hma = av_p.get('HMA', 'Não registrada') if tem_av else 'Não registrada'
    av_lado = av_p.get('Lado_Acometido') or 'Não informado'
    av_objetivo = av_p.get('Objetivo_Paciente', 'Retorno à função sem dor') if tem_av else 'Retorno à função sem dor'
    av_fenotipo_salvo = av_p.get('Fenotipo_Clinico', '') if tem_av else ''

    texto_fenotipo_busca = dx_clinico_base if dx_clinico_base != "Não especificado" else f"{av_fenotipo_salvo} {av_hma} {av_qp}"
    fen_info = normalizar_diagnostico(texto_fenotipo_busca)
    label_fenotipo_exib = av_fenotipo_salvo if av_fenotipo_salvo else fen_info['label']

    try:
        sane_base_av = _sane_valido(av_p.get('SANE_Baseline_Pct'), np.nan)
    except (ValueError, TypeError):
        sane_base_av = np.nan

    red_flags_str = str(av_p.get('Red_Flags', 'Nenhuma') or 'Nenhuma')
    yellow_flags_str = str(av_p.get('Yellow_Cog', av_p.get('Yellow_Flags', 'Nenhum')) or 'Nenhum')
    blue_flags_str = str(av_p.get('Fatores_Sociais', 'Nenhum') or 'Nenhum')

    # ============================================================
    # EXTRAÇÃO DE FORÇA: LSI + RAZÃO I:Q
    # ============================================================
    modo_forca_av = av_p.get('Modo_Avaliacao_Forca', 'Dinamometria Isométrica (kgf)')
    din_d_str = av_p.get('Dinamometria_Dir', '')
    din_e_str = av_p.get('Dinamometria_Esq', '')
    oxf_d_str = av_p.get('Forca_Geral_Dir', '')
    oxf_e_str = av_p.get('Forca_Geral_Esq', '')

    grupos_musculares = [
        ("Quadríceps (Extensão)", "Ext"),
        ("Isquiotibiais (Flexão)", "Flex"),
        ("Glúteo Médio (Abdução)", "Abd"),
        ("Adutores (Adução)", "Add"),
    ]
    dados_forca_bilateral = []
    usa_dinamometria = False

    for label_m, pref in grupos_musculares:
        vd = _extrair_chave_str(din_d_str, pref, 0.0)
        ve = _extrair_chave_str(din_e_str, pref, 0.0)
        if vd > 0 or ve > 0:
            usa_dinamometria = True
        lsi_m, les_m, sau_m, cor_m = _calcular_lsi_seguro(vd, ve, av_lado)
        dados_forca_bilateral.append({
            "Grupo Muscular": label_m,
            "Direito": f"{vd:.1f} kgf" if vd > 0 else "Não medido",
            "Esquerdo": f"{ve:.1f} kgf" if ve > 0 else "Não medido",
            "val_d": vd,
            "val_e": ve,
            "LSI (%)": f"{cor_m} {lsi_m:g}%" if lsi_m is not None else "⚪ N/D",
            "lsi_num": lsi_m
        })

    lsi_quad_num = dados_forca_bilateral[0]["lsi_num"]
    lsi_isquio_num = dados_forca_bilateral[1]["lsi_num"]
    cor_lsi_quad = dados_forca_bilateral[0]["LSI (%)"].split()[0] if lsi_quad_num is not None else "⚪"

    adm_flex_d_av = _extrair_chave_str(av_p.get("ADM_Joelho_Flexao", ""), "Dir", 0.0)
    adm_flex_e_av = _extrair_chave_str(av_p.get("ADM_Joelho_Flexao", ""), "Esq", 0.0)
    adm_ext_d_av = _extrair_chave_str(av_p.get("ADM_Joelho_Extensao", ""), "Dir", 0.0)
    adm_ext_e_av = _extrair_chave_str(av_p.get("ADM_Joelho_Extensao", ""), "Esq", 0.0)
    lunge_d_av = _extrair_chave_str(av_p.get("Lunge_Test", ""), "Dir", 0.0)
    lunge_e_av = _extrair_chave_str(av_p.get("Lunge_Test", ""), "Esq", 0.0)
    perim_d_av = float(av_p.get("Perimetria_Dir_cm", 0.0) or 0.0)
    perim_e_av = float(av_p.get("Perimetria_Esq_cm", 0.0) or 0.0)

    proms_detectados = _detectar_proms_preenchidos(av_p, fen_info.get("prom_principal", "KOOS"))

    # ============================================================
    # 1. HEADER EXECUTIVO DO PACIENTE (Sem PSFS, Com SANE + Fenótipo)
    # ============================================================
    with st.container(border=True):
        st.markdown(f"""
            <div style='display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;'>
                <div>
                    <span style='font-size: 0.76rem; font-weight: 700; text-transform: uppercase;
                                 letter-spacing: 0.06em; color: {CORES_GENUA['secundaria']};'>
                        Cockpit Analítico PBE · Fenótipo: {label_fenotipo_exib}
                    </span>
                    <h2 style='margin: 2px 0 6px 0; color: {CORES_GENUA['texto_escuro']};'>
                        👤 {p_sel}
                    </h2>
                    <p style='margin: 0; color: {CORES_GENUA['texto_suave']}; font-size: 0.92rem;'>
                        <b>Dx / HMA:</b> {dx_clinico_base if dx_clinico_base != 'Não especificado' else av_hma[:90]} &nbsp;|&nbsp;
                        <b>Objetivo Funcional (SANE Base {sane_base_av:.0f}%):</b> {av_objetivo}
                    </p>
                </div>
                <div style='display: flex; gap: 8px; align-items: center; flex-wrap: wrap;'>
                    <span style='background: rgba(46, 139, 154, 0.12); color: {CORES_GENUA['secundaria']};
                                 padding: 6px 14px; border-radius: 980px; font-weight: 700; font-size: 0.84rem;'>
                        🦵 Lado: {av_lado}
                    </span>
                    <span style='background: rgba(16, 62, 85, 0.08); color: {CORES_GENUA['primaria']};
                                 padding: 6px 14px; border-radius: 980px; font-weight: 700; font-size: 0.84rem;'>
                        🏃 {ocupacao_p} · {idade_p} anos
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    tem_red_flag = red_flags_str.lower() not in ["nenhuma", "nenhum", "não", "nao", "", "none"]
    tem_yellow_flag = yellow_flags_str.lower() not in ["nenhuma", "nenhum", "não", "nao", "", "none", "['nenhum']"]
    if tem_red_flag:
        toast(f"🚨 ALERTA DE RED FLAG REGISTRADA NA AVALIAÇÃO: {red_flags_str} — Verificar necessidade de parecer médico.", "error")
    elif tem_yellow_flag:
        toast(f"🟡 Atenção Psicossocial (Yellow Flag): {yellow_flags_str} — Associar educação em dor e exposição graduada.", "warning")

    # ============================================================
    # 2. EXPANDER DE AVALIAÇÃO FÍSICA BASELINE + DOWNLOAD DO PDF DA AVALIAÇÃO
    # ============================================================
    if tem_av:
        with st.expander(f"📋 Ficha Completa da Avaliação Inicial (Marco Zero: {av_data}) + PDF da Avaliação", expanded=False):
            t_resumo, t_fisico, t_funcional, t_proms = st.tabs([
                "🗣️ Anamnese & Objetivo", "📐 Exame Físico & Perimetria", "💪 Força (LSI / I:Q) & Controle", "📊 PROMs & PDF"
            ])

            with t_resumo:
                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    st.markdown("**Histórico Clínico e Comportamento da Dor:**")
                    st.markdown(f"- **Queixa Principal (QP):** {av_qp}")
                    st.markdown(f"- **Fenótipo Clínico:** {label_fenotipo_exib}")
                    st.markdown(f"- **HMA:** {av_hma}")
                    st.markdown(f"- **Sinais Associados:** {av_p.get('Sinais_Sintomas', 'Não relatado')}")
                    st.markdown(f"- **Tipo / Origem da Dor:** {av_p.get('Class_Dor', 'N/A')} ({av_p.get('Origem_Dor', 'N/A')})")
                    st.markdown(f"- **🟢 Alívio / 🔴 Piora:** {av_p.get('Fatores_Alivio', '—')} / {av_p.get('Fatores_Piora', '—')}")
                with c_r2:
                    st.markdown("**Objetivo Funcional (SANE), Bandeiras e Imagem:**")
                    st.markdown(f"- **Objetivo Principal:** {av_objetivo} *(SANE Inicial: **{sane_base_av:.0f}%**)*")
                    st.markdown(f"- **Red / Yellow Flags:** {red_flags_str} / {yellow_flags_str}")
                    st.markdown(f"- **Blue Flags / Comorbidades:** {blue_flags_str} / {av_p.get('Comorbidades', 'Nenhuma')}")
                    st.markdown(f"- **Exames Apresentados:** {av_p.get('Exames_Apresentados', 'Nenhum')}")
                    st.markdown(f"- **Laudo de Imagem:** {av_p.get('Laudo_Exames', 'Não relatado')}")
                    st.markdown(f"- **Conduta Inicial:** {av_p.get('Conduta_Avaliacao', 'Não relatada')}")

            with t_fisico:
                st.markdown(f"**🚶 Marcha Global:** {av_p.get('Marcha', 'N/A')} &nbsp;|&nbsp; **Cicatrizes/Pele:** {av_p.get('Pele', 'Normal')}")
                st.markdown(f"**📏 Perimetria Coxa (+5/+10/+15/+20cm):** `{av_p.get('Perimetria_Coxa_Resumo', av_p.get('Perimetria', 'N/A'))}`")
                st.markdown(f"**📏 Perimetria Panturrilha (-5/-10/-15cm):** `{av_p.get('Perimetria_Perna_Resumo', 'N/A')}`")
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                c_fd, c_fe = st.columns(2)
                with c_fd:
                    st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-bottom: 6px;'>🦵 Membro DIREITO</h4>", unsafe_allow_html=True)
                    st.markdown(f"- **Derrame / Godet:** {av_p.get('Derrame_Dir', 'N/A')} / {av_p.get('Godet_Dir', 'N/A')}")
                    st.markdown(f"- **Hipotrofismo (Quad | Isq | Tríceps):** {av_p.get('Hipotrofismo_Detalhado_Dir', av_p.get('Trofismo_Dir', 'Normal'))}")
                    st.markdown(f"- **Estruturas Dolorosas (Palpação):** {av_p.get('Palpacao_Dir', 'Sem dor')}")
                    st.markdown(f"- **Testes Ligamentares / Meniscais (+):** {av_p.get('Testes_Ligamentares_Dir', 'Nenhum')} | {av_p.get('Testes_Meniscais_Dir', 'Nenhum')}")
                    st.markdown(f"- **Femoropatelares / Compressão Patelar (+):** {av_p.get('Testes_Femoropatelar_Dir', 'Nenhum')}")
                with c_fe:
                    st.markdown(f"<h4 style='color: {CORES_GENUA['secundaria']}; margin-bottom: 6px;'>🦵 Membro ESQUERDO</h4>", unsafe_allow_html=True)
                    st.markdown(f"- **Derrame / Godet:** {av_p.get('Derrame_Esq', 'N/A')} / {av_p.get('Godet_Esq', 'N/A')}")
                    st.markdown(f"- **Hipotrofismo (Quad | Isq | Tríceps):** {av_p.get('Hipotrofismo_Detalhado_Esq', av_p.get('Trofismo_Esq', 'Normal'))}")
                    st.markdown(f"- **Estruturas Dolorosas (Palpação):** {av_p.get('Palpacao_Esq', 'Sem dor')}")
                    st.markdown(f"- **Testes Ligamentares / Meniscais (+):** {av_p.get('Testes_Ligamentares_Esq', 'Nenhum')} | {av_p.get('Testes_Meniscais_Esq', 'Nenhum')}")
                    st.markdown(f"- **Femoropatelares / Compressão Patelar (+):** {av_p.get('Testes_Femoropatelar_Esq', 'Nenhum')}")

            with t_funcional:
                c_fun1, c_fun2 = st.columns(2)
                with c_fun1:
                    st.caption("MÓDULO DE FORÇA MUSCULAR (OPCIONAL POR FENÓTIPO)")
                    st.markdown(f"- **Modalidade Escolhida:** `{modo_forca_av}`")
                    st.markdown(f"- **Oxford Qualitativo (Dir | Esq):** `{oxf_d_str or 'N/A'}` | `{oxf_e_str or 'N/A'}`")
                    st.markdown(f"- **Dinamometria (Dir | Esq):** `{din_d_str if usa_dinamometria else 'Omitida / Pós-Op'}` | `{din_e_str if usa_dinamometria else 'Omitida / Pós-Op'}`")
                    st.markdown(f"- **Resumo LSI & Razão I:Q:** `{av_p.get('Resumo_LSI_IQ', 'N/A')}`")
                with c_fun2:
                    st.caption("MOBILIDADE, FLEXIBILIDADE & CONTROLE MOTOR (DOR)")
                    st.markdown(f"- **ADM Flexão / Extensão:** `{av_p.get('ADM_Joelho_Flexao', 'N/A')}` / `{av_p.get('ADM_Joelho_Extensao', 'N/A')}`")
                    st.markdown(f"- **Lunge Test (Tornozelo):** `{av_p.get('Lunge_Test', 'N/A')}`")
                    st.markdown(f"- **Flexibilidade (Glúteo/Adutores/etc.):** `{av_p.get('Flexibilidade', 'Normal')}`")
                    st.markdown(f"- **Controle Motor (Relação Funcional × Dor):** `{av_p.get('Resumo_Controle_Motor', av_p.get('CM_Globais', 'Opcional'))}`")

            with t_proms:
                c_p1, c_p2, c_p3, c_p4, c_p5, c_p6 = st.columns(6)
                c_p1.metric("KOOS", f"{float(av_p.get('KOOS_Pct', 0) or 0):.1f}%" if "KOOS" in proms_detectados else "Não aplic.")
                c_p2.metric("IKDC", f"{float(av_p.get('IKDC_Pct', 0) or 0):.1f}%" if "IKDC" in proms_detectados else "Não aplic.")
                c_p3.metric("LEFS", f"{float(av_p.get('LEFS_Pct', 0) or 0):.1f}%" if "LEFS" in proms_detectados else "Não aplic.")
                c_p4.metric("Lysholm", f"{av_p.get('Lysholm_Pts', 0)} pts" if "Lysholm" in proms_detectados else "Não aplic.")
                c_p5.metric("VISA-P", f"{av_p.get('VISA_P_Pts', 0)} pts" if "VISA-P" in proms_detectados else "Não aplic.")
                c_p6.metric("WOMAC", f"{float(av_p.get('WOMAC_Pct', 0) or 0):.1f}%" if "WOMAC" in proms_detectados else "Não aplic.")

                try:
                    bytes_pdf_so_aval = gerar_pdf_somente_avaliacao(av_p)
                    st.download_button(
                        label="📄 Baixar PDF Exclusivo da Avaliação Inicial",
                        data=bytes_pdf_so_aval,
                        file_name=f"Avaliacao_GENUA_{p_sel.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        type="secondary",
                        width="stretch",
                        key="btn_pdf_so_aval_painel"
                    )
                except Exception:
                    pass
    else:
        st.info("⚠️ Nenhuma Avaliação Inicial registrada para este paciente.")

    # ============================================================
    # C. MOTOR DE EVOLUÇÃO LONGITUDINAL (CHECK-INS DIÁRIOS)
    # ============================================================
    if df_p.empty:
        st.info("Nenhum check-in de joelho registrado.")
        return


    # ============================================================
    # 3. SELETOR DE SESSÃO, REATIVIDADE 24H E 6 KPIS EXECUTIVOS
    # ============================================================
    ultima = df_p.loc[idx_sel]
    anterior = df_p.loc[idx_sel - 1] if idx_sel > 0 else None

    gestos = [_medidas_gestos(sessao) for sessao in df_p.to_dict("records")]
    df_p["Tolerancia"] = [
        10 * sum(score for score, _ in medidas.values()) / len(medidas) if medidas else np.nan
        for medidas in gestos
    ]
    inicio_janela = max(0, idx_sel - 9)
    df_janela = df_p.loc[inicio_janela:idx_sel].copy().reset_index(drop=True)

    dor_atual = ultima["Dor"]
    flex_atual = ultima["Flexao"]
    tol_atual = df_p.at[idx_sel, "Tolerancia"]
    inchaco_atual = ultima["Inchaco_N"]
    ext_str = str(ultima.get("Extensao") or "Não avaliada")
    sono_atual = str(ultima.get("Sono") or "Não avaliado")
    delta_dor = dor_atual - anterior["Dor"] if anterior is not None else np.nan
    if anterior is not None and pd.notna(ultima["Data_dt"]) and pd.notna(anterior["Data_dt"]):
        dias = (ultima["Data_dt"].date() - anterior["Data_dt"].date()).days
        motivos = []
        if delta_dor >= 2:
            motivos.append(f"dor aumentou {delta_dor:g} pontos")
        if inchaco_atual >= 2 and inchaco_atual > anterior["Inchaco_N"]:
            motivos.append(f"derrame aumentou para grau {inchaco_atual:g}")
        if motivos:
            intervalo = "em dias consecutivos" if dias == 1 else f"com intervalo de {dias} dias"
            st.warning(f"Comparação entre sessões {intervalo}: " + " e ".join(motivos) + ".")

    sane_sessao = ultima.get('SANE_Pct_Num')
    sane_sessao = _sane_valido(sane_sessao, np.nan)
    dist_meta_sessao = max(0.0, 100.0 - sane_sessao)
    ganho_sane_sessao = sane_sessao - sane_base_av

    groc_sessao_val = ultima.get('GROC_Score')
    try:
        groc_sessao_int = _groc_valido(groc_sessao_val)
    except (ValueError, TypeError):
        groc_sessao_int = None

    pass_sessao_str = str(ultima.get('PASS_Satisfacao', 'Não registrado') or 'Não registrado')
    pass_bool = ultima.get('PASS_Atingido')
    if pd.isna(pass_bool) or pass_bool is None:
        pass_bool = pass_sessao_str.startswith("👍")

    testes_ult = ultima.get('Testes_Funcionais', {}) if isinstance(ultima.get('Testes_Funcionais'), dict) else {}
    agach_str = str(testes_ult.get('Agachamento Bipodal', ''))
    step_down_str = str(
        testes_ult.get('Step Down')
        or testes_ult.get('Step Down (D)')
        or testes_ult.get('Step Down (E)')
        or ''
    )

    if pd.isna(dor_atual) or pd.isna(inchaco_atual) or pd.isna(tol_atual):
        fenotipo_sessao = "Dados insuficientes"
        diretriz = "Verifique os registros de dor, derrame e testes funcionais desta sessão."
    elif "Incapaz" in agach_str and inchaco_atual >= 2 and dor_atual >= 8:
        fenotipo_sessao = "🚨 Dor e derrame com limitação no agachamento"
        diretriz = "Agachamento bipodal registrado como incapaz, com EVA ≥ 8 e derrame grau ≥ 2. Conferir a capacidade de apoio no exame."
    elif ("Incapaz" in step_down_str or "Moderada" in step_down_str or "Grave" in step_down_str) and inchaco_atual <= 1:
        fenotipo_sessao = "🟣 Sobrecarga Femoropatelar"
        diretriz = "Dor na desaceleração excêntrica. Foco em fortalecimento póstero-lateral de quadril e controle de vetor em cadeia fechada (0-45°)."
    elif ("Déficit" in ext_str) and inchaco_atual >= 2:
        fenotipo_sessao = "🟤 Bloqueio / Artrogênico"
        diretriz = "Déficit de extensão terminal associado a derrame articular (inibição artrogênica do quadríceps). Priorizar ganho de extensão 0° e controle de efusão."
    elif ("Incapaz" in agach_str or "Moderada" in agach_str) and "Completa" in ext_str and inchaco_atual == 0:
        fenotipo_sessao = "🟠 Tendinopático Reativo"
        diretriz = "Dor em armazenamento/liberação de energia elástica sem derrame articular. Modular carga excêntrica e aplicar isometria analgésica (Rio et al., 2015)."
    else:
        fenotipo_sessao = "🔵 Acomodação de Carga"
        diretriz = "Sinais reativos mistos. Modular volume e intensidade conforme irritabilidade tecidual (regra das 24h)."

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(
        "Dor Hoje (EVA)",
        f"{dor_atual:g}/10" if pd.notna(dor_atual) else "Não avaliada",
        f"{delta_dor:+g} pts vs anterior" if pd.notna(delta_dor) else None,
        delta_color="inverse"
    )
    k2.metric(
        "Reatividade / Derrame",
        f"Grau {inchaco_atual:g}/3" if pd.notna(inchaco_atual) else "Não avaliado",
        f"Sono: {sono_atual}",
        delta_color="off"
    )
    k3.metric(
        "ADM (Flex / Ext)",
        f"{flex_atual:.0f}°" if pd.notna(flex_atual) else "Não avaliada",
        ext_str,
        delta_color="normal" if "Completa" in ext_str and flex_atual >= 120 else "off"
    )
    k4.metric("Tolerância Funcional", f"{tol_atual:.0f}%" if pd.notna(tol_atual) else "Sem testes registrados")
    k5.metric(
        f"{cor_lsi_quad} LSI Dinamometria",
        f"{lsi_quad_num:g}%" if (usa_dinamometria and lsi_quad_num is not None) else "Sem medida bilateral",
        f"Isquios: {lsi_isquio_num:g}%" if (usa_dinamometria and lsi_isquio_num is not None) else "Meta Alta: ≥90%",
        delta_color="normal" if (usa_dinamometria and (lsi_quad_num or 0) >= 90) else "off"
    )
    k6.metric(
        "Meta (SANE / GROC)",
        f"{sane_sessao:.0f}%" if np.isfinite(sane_sessao) else "Não avaliado",
        f"GROC: {groc_sessao_int:+d} (-7/+7)" if groc_sessao_int is not None else f"{ganho_sane_sessao:+.0f}% vs Base" if np.isfinite(ganho_sane_sessao) else None,
        delta_color="normal" if pass_bool else "off"
    )

    if ultima.get("Registro_Bilateral") == True:
        with st.container(border=True):
            st.caption("🦵 COMPARATIVO BILATERAL DA SESSÃO SELECIONADA (DIREITO × ESQUERDO)")
            cb1, cb2, cb3, cb4 = st.columns(4)
            cb1.metric("EVA (Dir | Esq)", f"{ultima.get('Dor_Dir') if pd.notna(ultima.get('Dor_Dir')) else '—'}/10 | {ultima.get('Dor_Esq') if pd.notna(ultima.get('Dor_Esq')) else '—'}/10")
            cb2.metric("Flexão (Dir | Esq)", f"{ultima.get('Flexao_Dir') if pd.notna(ultima.get('Flexao_Dir')) else '—'}° | {ultima.get('Flexao_Esq') if pd.notna(ultima.get('Flexao_Esq')) else '—'}°")
            cb3.metric("Extensão (Dir | Esq)", f"{ultima.get('Extensao_Dir', '-')} | {ultima.get('Extensao_Esq', '-')}")
            cb4.metric("Derrame (Dir | Esq)", f"{ultima.get('Inchaco_Dir', '-')} | {ultima.get('Inchaco_Esq', '-')}")

    with st.container(border=True):
        c_prog1, c_prog2 = st.columns(2, gap="large")
        with c_prog1:
            if pd.notna(tol_atual):
                st.markdown(f"**Tolerância nos gestos avaliados: {tol_atual:.0f}%**")
                st.progress(tol_atual / 100)
            st.caption("Cada gesto realizado pontua 10 menos a dor. Incapaz pontua zero. A média é apresentada em percentual.")
        with c_prog2:
            if np.isfinite(sane_sessao):
                st.markdown(
                    f"**🏆 Progresso rumo ao Objetivo do Paciente (SANE): {sane_sessao:.0f}%** "
                    f"*(Faltam {dist_meta_sessao:.0f}% para a meta · GROC (-7 a +7): {f'{groc_sessao_int:+d}' if groc_sessao_int is not None else 'N/D'})*"
                )
                st.progress(min(max(sane_sessao / 100.0, 0.0), 1.0))
            else:
                st.caption("SANE não registrado na sessão.")

    # ============================================================
    # 4. NAVEGAÇÃO ANALÍTICA EM 3 ABAS
    # ============================================================
    t1, t2, t_ic = st.tabs([
        "📊 1. Carga, Dor & Reatividade (24h)",
        "📐 2. Biomecânica, Simetria (LSI / I:Q) & Metas",
        "🧠 3. Inteligência Clínica & Critérios de Alta"
    ])

    # ABA 1: CARGA, DOR, FUNÇÃO E REATIVIDADE ARTICULAR
    with t1:
        with st.container(border=True):
            secao(
                f"📊 Curva de Resposta Terapêutica: Dor (EVA) × Tolerância Funcional (Últimas {len(df_janela)} sessões)",
                "A curva de tolerância resume os gestos avaliados em cada sessão."
            )

            fig1, ax1 = plt.subplots(figsize=(10, 4.0), dpi=120)
            ax1.axhspan(0, 3.0, color=CORES_GENUA['alerta_sucesso'], alpha=0.07, label="EVA ≤ 3")

            cor_dor = CORES_GENUA['alerta_erro']
            ax1.plot(
                df_janela['Sessão_Num'], df_janela['Dor'],
                color=cor_dor, marker='o', markersize=7, lw=2.8,
                label="Dor Diária (EVA 0-10)", zorder=4
            )
            if (df_janela['EVA_Semanal'] != df_janela['Dor']).any():
                ax1.plot(
                    df_janela['Sessão_Num'], df_janela['EVA_Semanal'],
                    color=CORES_GENUA['alerta_aviso'], marker='^', markersize=5, lw=1.6,
                    linestyle=':', label="EVA Média Semanal", zorder=3
                )
            ax1.set_ylabel("Dor (EVA 0-10)", color=cor_dor, fontweight='600')
            ax1.set_ylim(-0.5, 10.5)

            ax_tol = ax1.twinx()
            ax_tol.grid(False)
            ax_tol.plot(df_janela["Sessão_Num"], df_janela["Tolerancia"], color=CORES_GENUA["secundaria"],
                        marker="s", linestyle="--", label="Tolerância nos gestos (%)")
            ax_tol.set_ylabel("Tolerância nos gestos (%)")
            ax_tol.set_ylim(-5, 105)
            linhas, nomes = ax1.get_legend_handles_labels()
            ax1.legend(linhas + ax_tol.lines[:], nomes + ["Tolerância nos gestos (%)"], fontsize=8)
            fig1.tight_layout()
            st.pyplot(fig1)
            plt.close(fig1)

            historico_gestos = {}
            for sessao, medidas in zip(df_p["Sessão_Num"], gestos):
                for nome, (_, descricao) in medidas.items():
                    historico_gestos.setdefault(nome, []).append(f"{sessao} · {descricao}")
            if historico_gestos:
                st.markdown("**Evolução por movimento alvo**")
                tabela = [{"Movimento": nome, "Primeiro registro": serie[0],
                           "Último registro": serie[-1] if len(serie) > 1 else "Registro único"}
                          for nome, serie in historico_gestos.items()]
                st.dataframe(tabela, hide_index=True, width="stretch")

        with st.container(border=True):
            secao(
                f"💧 Rastreador de Irritabilidade Tecidual: Derrame × Dor × Sono (Últimas {len(df_janela)} sessões)",
                "Diferenciação clínica: Picos de dor acompanhados de aumento do derrame indicam sobrecarga mecânica; picos de dor sem derrame após noite de 'Insônia/Acordou com dor' sugerem amplificação central (Finan et al., 2013)."
            )
            fig_reat, ax_r1 = plt.subplots(figsize=(10, 3.3), dpi=120)
            x_idx = np.arange(len(df_janela))

            ax_r1.bar(
                x_idx, df_janela['Inchaco_N'], width=0.42,
                color=CORES_GENUA['secundaria'], alpha=0.35, label="Derrame Articular (Grau 0-3)"
            )
            ax_r1.set_ylabel("Derrame (Grau 0-3)", color=CORES_GENUA['secundaria'], fontweight='600')
            ax_r1.set_ylim(0, 3.6)
            ax_r1.set_yticks([0, 1, 2, 3])
            ax_r1.set_xticks(x_idx)
            ax_r1.set_xticklabels(df_janela['Sessão_Num'], rotation=25, ha='right', fontsize=9)

            ax_r2 = ax_r1.twinx()
            ax_r2.grid(False)
            ax_r2.plot(
                x_idx, df_janela['Dor'], color=CORES_GENUA['alerta_erro'],
                marker='o', lw=2.2, label="Dor (EVA 0-10)"
            )
            legenda_sono_adicionada = False
            for i_s, row_s in df_janela.iterrows():
                sono_s = str(row_s.get('Sono', 'Bem')).lower()
                if "insônia" in sono_s or "dor" in sono_s or "ruim" in sono_s:
                    ax_r2.scatter(
                        i_s, row_s['Dor'], color=CORES_GENUA['alerta_aviso'],
                        s=160, zorder=6, edgecolors='#1D1D1F', linewidth=1.5,
                        label="Sono Ruim / Acordou c/ Dor" if not legenda_sono_adicionada else "_nolegend_"
                    )
                    legenda_sono_adicionada = True
            ax_r2.set_ylabel("Dor (EVA 0-10)", color=CORES_GENUA['alerta_erro'], fontweight='600')
            ax_r2.set_ylim(-0.5, 10.5)
            ax_r1.spines['top'].set_visible(False)
            ax_r2.spines['top'].set_visible(False)

            l_r1, lb_r1 = ax_r1.get_legend_handles_labels()
            l_r2, lb_r2 = ax_r2.get_legend_handles_labels()
            ax_r1.legend(l_r1 + l_r2, lb_r1 + lb_r2, loc='upper right', frameon=False, fontsize=8.8)
            fig_reat.tight_layout()
            st.pyplot(fig_reat)
            plt.close(fig_reat)

    # ABA 2: BIOMECÂNICA, SIMETRIA BILATERAL (LSI + RAZÃO I:Q) & METAS (SANE)
    with t2:
        with st.container(border=True):
            secao(
                f"⚖️ Matriz de Simetria Bilateral (LSI) & Equilíbrio Isquiotibiais:Quadríceps (Razão I:Q — Lado: {av_lado})",
                "O cálculo do Índice de Simetria (LSI ≥ 90%) e da Razão I:Q (55% a 65%) utiliza exclusivamente a Dinamometria Isométrica (kgf)."
            )

            c_sim1, c_sim2 = st.columns([1.45, 1.55], gap="large")
            with c_sim1:
                st.caption("💪 FORÇA MUSCULAR ISOMÉTRICA (DINAMOMETRIA — KGF)")
                if usa_dinamometria:
                    df_tabela_forca = pd.DataFrame(dados_forca_bilateral)[["Grupo Muscular", "Direito", "Esquerdo", "LSI (%)"]]
                    st.dataframe(df_tabela_forca, hide_index=True, width="stretch")

                    ext_d_v, flex_d_v = dados_forca_bilateral[0]["val_d"], dados_forca_bilateral[1]["val_d"]
                    ext_e_v, flex_e_v = dados_forca_bilateral[0]["val_e"], dados_forca_bilateral[1]["val_e"]
                    iq_d = (flex_d_v / ext_d_v * 100.0) if (ext_d_v > 0 and flex_d_v > 0) else None
                    iq_e = (flex_e_v / ext_e_v * 100.0) if (ext_e_v > 0 and flex_e_v > 0) else None
                    if iq_d is not None or iq_e is not None:
                        st.markdown(
                            f"**⚖️ Razão Isquiotibiais : Quadríceps (I:Q Ratio):** "
                            f"Direito: **{f'{iq_d:.0f}% ({iq_d/100:.2f})' if iq_d else 'N/D'}** | "
                            f"Esquerdo: **{f'{iq_e:.0f}% ({iq_e/100:.2f})' if iq_e else 'N/D'}** "
                            f"*(Alvo PBE: 55% a 65% — Kyritsis et al., 2016)*"
                        )
                else:
                    st.info(
                        f"ℹ️ **Modalidade de Força na Avaliação: `{modo_forca_av}`.**\n\n"
                        "O cálculo de LSI e Razão I:Q permanece oculto quando a força é omitida (Pós-Op Agudo) ou avaliada apenas por Oxford."
                    )

            with c_sim2:
                st.caption("📐 SIMETRIA DE MOBILIDADE ARTICULAR & PERIMETRIA")
                linhas_mob = [
                    {
                        "Parâmetro": "Flexão de Joelho (°)",
                        "Direito": f"{adm_flex_d_av:.0f}°" if adm_flex_d_av > 0 else "N/D",
                        "Esquerdo": f"{adm_flex_e_av:.0f}°" if adm_flex_e_av > 0 else "N/D",
                        "Diferença (Δ)": f"{abs(adm_flex_d_av - adm_flex_e_av):.0f}° ({'🟢 Normal' if abs(adm_flex_d_av - adm_flex_e_av) < 10 else '🟡 Assimetria ≥10°'})" if (adm_flex_d_av > 0 or adm_flex_e_av > 0) else "N/D"
                    },
                    {
                        "Parâmetro": "Extensão Terminal (°)",
                        "Direito": f"{adm_ext_d_av:.0f}°",
                        "Esquerdo": f"{adm_ext_e_av:.0f}°",
                        "Diferença (Δ)": "🟢 Completa (0°)" if (adm_ext_d_av <= 0 and adm_ext_e_av <= 0) else "🔴 Déficit de Extensão"
                    },
                    {
                        "Parâmetro": "Lunge Test — Tornozelo (cm)",
                        "Direito": f"{lunge_d_av:.1f} cm" if lunge_d_av > 0 else "N/D",
                        "Esquerdo": f"{lunge_e_av:.1f} cm" if lunge_e_av > 0 else "N/D",
                        "Diferença (Δ)": f"{abs(lunge_d_av - lunge_e_av):.1f} cm ({'🟢 Simétrico' if abs(lunge_d_av - lunge_e_av) < 1.5 else '🟡 Restrição ≥1.5cm'})" if (lunge_d_av > 0 or lunge_e_av > 0) else "N/D"
                    },
                    {
                        "Parâmetro": "Perimetria Coxa +10cm (cm)",
                        "Direito": f"{perim_d_av:.1f} cm" if perim_d_av > 0 else "N/D",
                        "Esquerdo": f"{perim_e_av:.1f} cm" if perim_e_av > 0 else "N/D",
                        "Diferença (Δ)": f"{abs(perim_d_av - perim_e_av):.1f} cm ({'🟢 Normal' if abs(perim_d_av - perim_e_av) < 1.5 else '🔴 Hipotrofia ≥1.5cm'})" if (perim_d_av > 0 and perim_e_av > 0) else "N/D"
                    }
                ]
                st.dataframe(pd.DataFrame(linhas_mob), hide_index=True, width="stretch")

        with st.container(border=True):
            secao(
                f"📉 Evolução Longitudinal de Amplitude Articular (Flexão °) × Dor (Últimas {len(df_janela)} sessões)",
                f"Fenótipo ativo: {label_fenotipo_exib} · Linha tracejada indica meta funcional de flexão (≥ 125°)."
            )

            fig2, ax2 = plt.subplots(figsize=(10, 3.8), dpi=120)
            ax2.plot(
                df_janela['Sessão_Num'], df_janela['Dor'],
                color=CORES_GENUA['alerta_erro'], marker='o', markersize=7, lw=2.6, label="Dor (EVA)"
            )
            ax2.set_ylabel("Dor (EVA 0-10)", color=CORES_GENUA['alerta_erro'], fontweight='600')
            ax2.set_ylim(-0.5, 10.5)

            ax3 = ax2.twinx()
            ax3.grid(False)
            ax3.axhline(y=125, color=CORES_GENUA['secundaria'], linestyle='--', lw=1.3, alpha=0.6, label="Meta Flexão (125°)")
            ax3.plot(
                df_janela['Sessão_Num'], df_janela['Flexao'],
                color=CORES_GENUA['secundaria'], marker='s', markersize=6.5, lw=2.5, linestyle='-', label="Flexão Atingida (°)"
            )
            ax3.set_ylabel("Flexão de Joelho (°)", color=CORES_GENUA['secundaria'], fontweight='600')
            ax3.set_ylim(0, 160)

            ax2.spines['top'].set_visible(False)
            ax3.spines['top'].set_visible(False)
            plt.setp(ax2.get_xticklabels(), rotation=25, ha='right', fontsize=9)

            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax3.get_legend_handles_labels()
            ax2.legend(
                lines1 + lines2, labels1 + labels2,
                loc='upper center', bbox_to_anchor=(0.5, 1.15),
                ncol=3, frameon=False, fontsize=9
            )
            fig2.tight_layout()
            st.pyplot(fig2)
            plt.close(fig2)

        with st.container(border=True):
            prog_data = _calcular_curva_prognostica_sane(
                df_completo=df_p,
                df_janela=df_janela,
                sane_base=sane_base_av,
                semanas_esperadas=fen_info.get("tempo_esperado_semanas")
            )

            secao(
                f"🏆 Prognóstico por Fenótipo: Trajetória Esperada (PBE) × Evolução Real SANE (Últimas {len(df_janela)} sessões)",
                f"Fenótipo: {label_fenotipo_exib} (Janela PBE: {prog_data['semanas_janela']} semanas) · "
                f"Objetivo: '{av_objetivo}' · Limiar de Alta ≥ 85% (Shelbourne et al., 2009)."
            )

            fig_sane, ax_s = plt.subplots(figsize=(10, 3.8), dpi=120)
            x_prog = np.arange(len(df_janela))
            sane_serie = np.array(prog_data["real"], dtype=float)
            esp_serie = np.array(prog_data["esperado"], dtype=float)

            faixa_inf = np.clip(esp_serie - 10.0, 0.0, 100.0)
            faixa_sup = np.clip(esp_serie + 5.0, 0.0, 100.0)
            ax_s.fill_between(
                x_prog, faixa_inf, faixa_sup,
                color=CORES_GENUA['secundaria'], alpha=0.11,
                label="Janela Fisiológica Esperada (-10% a +5%)"
            )

            ax_s.plot(
                x_prog, esp_serie,
                color=CORES_GENUA['secundaria'], linestyle='--', marker='^', markersize=5.5,
                lw=2.2, alpha=0.9, label=f"Trajetória Esperada PBE ({prog_data['semanas_janela']} sem)"
            )

            ax_s.plot(
                x_prog, sane_serie,
                color=CORES_GENUA['primaria'], linestyle='-', marker='o', markersize=7.5,
                lw=3.0, zorder=5, label="Paciente — SANE Real (%)"
            )

            ax_s.axhline(y=85, color=CORES_GENUA['alerta_sucesso'], linestyle=':', lw=1.5, alpha=0.85, label="Critério de Alta (85%)")
            if np.isfinite(sane_base_av):
                ax_s.axhline(y=sane_base_av, color=CORES_GENUA['texto_suave'], linestyle=':', lw=1.1, alpha=0.6, label=f"Marco Zero ({sane_base_av:.0f}%)")

            ax_s.set_xticks(x_prog)
            labels_eixo_x = [
                f"{sess}\n(Sem {sem:.1f})"
                for sess, sem in zip(df_janela['Sessão_Num'], prog_data['tempos_semanas'])
            ]
            ax_s.set_xticklabels(labels_eixo_x, rotation=20, ha='right', fontsize=8.5)
            ax_s.set_ylabel("Capacidade Funcional — SANE (%)", fontweight='600', color=CORES_GENUA['primaria'])
            ax_s.set_ylim(-5, 108)
            ax_s.spines['top'].set_visible(False)
            ax_s.spines['right'].set_visible(False)
            ax_s.legend(
                loc='upper center',
                bbox_to_anchor=(0.5, 1.18),
                ncol=3,
                frameon=False,
                fontsize=8.3
            )
            fig_sane.tight_layout()
            st.pyplot(fig_sane)
            plt.close(fig_sane)

            if prog_data["status"] == "incompleto":
                st.info(prog_data["resumo"])
            elif prog_data["status"] == "acima":
                st.success(f"{prog_data['cor']} **PROGNÓSTICO ACIMA DO ESPERADO** — {prog_data['resumo']}")
            elif prog_data["status"] == "dentro":
                st.info(f"{prog_data['cor']} **DENTRO DA CURVA PROGNÓSTICA PBE** — {prog_data['resumo']}")
            else:
                st.warning(f"{prog_data['cor']} **ABAIXO DA CURVA ESPERADA PELA LITERATURA** — {prog_data['resumo']}")

    # ABA 3: INTELIGÊNCIA CLÍNICA & CHECKLIST DE ALTA
    with t_ic:
        with st.container(border=True):
            secao(
                "🚦 Checklist de Critérios Objetivos para Alta Funcional (6 Gatekeepers PBE)",
                "Estes 6 critérios compõem o painel de metas do Laudo PDF. O critério 5 exige medição por Dinamometria (kgf)."
            )

            crit_dor = dor_atual <= 2
            crit_derrame = inchaco_atual <= 1
            crit_ext = "Completa" in ext_str
            crit_flex = flex_atual >= 125
            crit_lsi = (usa_dinamometria and lsi_quad_num is not None and lsi_quad_num >= 90.0)
            crit_sane_pass = (sane_sessao >= 85.0 and pass_bool)

            criterios_lista = [
                ("1. Controle Álgico (EVA ≤ 2/10)", crit_dor, f"Atual: {dor_atual}/10" if pd.notna(dor_atual) else "Não avaliado", "Salaffi 2004"),
                ("2. Efusão Articular Controlada (Grau ≤ 1/3)", crit_derrame, f"Atual: Grau {inchaco_atual}/3" if pd.notna(inchaco_atual) else "Não avaliado", "Stroke Test PBE"),
                ("3. Extensão Terminal Completa (0°)", crit_ext, f"Atual: {ext_str}", "Shelbourne 1997"),
                ("4. Amplitude de Flexão Funcional (≥ 125°)", crit_flex, f"Atual: {flex_atual:.0f}°" if pd.notna(flex_atual) else "Não avaliado", "Diretriz Pós-Op Joelho"),
                (
                    "5. Simetria de Força de Quadríceps (LSI ≥ 90%)",
                    crit_lsi,
                    f"Atual: {f'{lsi_quad_num:g}% (Dinamometria kgf)' if (usa_dinamometria and lsi_quad_num is not None) else 'Opcional / Aguardando Dinamometria'}",
                    "Grindem 2016"
                ),
                ("6. Meta Subjetiva Atingida (SANE ≥ 85% + PASS Sim)", crit_sane_pass, f"SANE: {sane_sessao:.0f}% | PASS: {'Sim' if pass_bool else 'Não'}", "Shelbourne 2009 / Tubach 2005"),
            ]

            total_cumpridos = sum(1 for _, ok, _, _ in criterios_lista if ok)
            pct_gatekeeper = (total_cumpridos / len(criterios_lista)) * 100.0

            st.markdown(f"**📊 Score de Critérios de Alta Cumpridos: {total_cumpridos}/{len(criterios_lista)} ({pct_gatekeeper:.0f}%)**")
            st.progress(pct_gatekeeper / 100.0)

            cg1, cg2 = st.columns(2)
            for idx_c, (nome_c, ok_c, valor_c, ref_c) in enumerate(criterios_lista):
                icone_c = "✅" if ok_c else ("⏳" if "Aguardando" in valor_c or "Opcional" in valor_c else "❌")
                cor_borda = CORES_GENUA['alerta_sucesso'] if ok_c else CORES_GENUA['alerta_aviso']
                with (cg1 if idx_c < 3 else cg2):
                    st.markdown(
                        f"<div style='border-left: 4px solid {cor_borda}; background: {CORES_GENUA['fundo_claro']}; "
                        f"padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;'>"
                        f"<strong>{icone_c} {nome_c}</strong><br>"
                        f"<span style='font-size: 0.88rem; color: {CORES_GENUA['texto_escuro']};'>{valor_c}</span> "
                        f"<small style='color: {CORES_GENUA['texto_suave']};'>({ref_c})</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        with st.container(border=True):
            try:
                with st.spinner("🧠 Executando análise clínica baseada em evidência..."):
                    insights = analisar_paciente(p_sel, df_p, pd.DataFrame([av_p]) if tem_av else pd.DataFrame())
                renderizar_insights(insights, CORES_GENUA)
            except Exception as e:
                toast(f"Erro ao gerar insights: {e}", "error")
                st.caption("Verifique se o paciente possui avaliação inicial e sessões de check-in registradas.")

        with st.container(border=True):
            secao(
                "🔬 Diretriz de Conduta Imediata (Sessão Selecionada)",
                "Síntese algorítmica cruzando derrame articular, resposta a carga excêntrica/elástica e mobilidade."
            )
            st.markdown(f"- **Classificação Funcional da Sessão ({sessao_escolhida}):** {fenotipo_sessao}")
            st.markdown(f"- **Conduta Recomendada (PBE):** {diretriz}")

    # ============================================================
    # 5. CARD DE EXPORTAÇÃO DO LAUDO DE EVOLUÇÃO (CLEAN LIGHT GENUA)
    # ============================================================
    with st.container(border=True):
        secao(
            "📄 Exportação de Laudo de Evolução Clínica (Clean Light GENUA)",
            "Gera o relatório executivo longitudinal com as últimas 10 sessões, Velocímetro de ADM, Força por Dinamometria (kgf), os 6 Critérios de Alta e Conclusões Editáveis."
        )

        opcoes_prom_laudo = ["KOOS", "IKDC", "LEFS", "VISA-P", "Lysholm", "WOMAC"]

        c_cfg1, c_cfg2 = st.columns([1.4, 1.6], gap="large")
        with c_cfg1:
            medico_laudo = st.text_input(
                "🤝 Indicação",
                value=av_p.get("Medico_Indicador", indicacao_cad) if tem_av else indicacao_cad,
                placeholder="Ex: Dr. Felipe / Indicação Clínica",
                key="input_medico_laudo"
            )
        with c_cfg2:
            prom_selecionado = st.multiselect(
                "📋 Questionário(s) Aplicado(s) para Exibir no Laudo",
                options=opcoes_prom_laudo,
                default=proms_detectados,
                help="Se nenhum questionário foi aplicado, deixe vazio e a seção não aparecerá no PDF."
            )

        conclusao_livre_fisio = st.text_area(
            "✍️ Conclusão Final e Recomendações (Opcional — Também editável direto no Laudo)",
            value="",
            placeholder="Digite aqui o parecer final e recomendações de conduta, ou edite diretamente nos boxes interativos do laudo abaixo antes de imprimir...",
            height=80,
            key="input_conclusao_livre_laudo"
        )

        if st.button("⚙️ GERAR LAUDO EXECUTIVO DE EVOLUÇÃO", width='stretch', type="primary"):
            with st.spinner("🧠 Compilando laudo clínico Clean Light com 10 sessões, 6 metas de alta e conclusões editáveis..."):
                try:
                    import streamlit.components.v1 as components
                    from pdf_laudo import gerar_laudo_html
                    from ia_clinica import analisar_paciente as _analisar, normalizar_diagnostico as _normalizar

                    dados_aval = dict(av_p) if tem_av else {}
                    dados_aval["Medico_Indicador"] = medico_laudo.strip()
                    dados_aval["Ocupacao_Esporte"] = ocupacao_p if ocupacao_p != "Não informada" else ""
                    dados_aval["Idade_Cadastro"] = idade_p if idade_p != "—" else ""
                    dados_aval["Diagnostico_Cadastro"] = dx_clinico_base if dx_clinico_base != "Não especificado" else ""
                    dados_aval["PROMs_Selecionados"] = prom_selecionado
                    dados_aval["Conclusao_Final_Fisio"] = conclusao_livre_fisio.strip()

                    historico = df_p.loc[:idx_sel].to_dict("records")

                    insights_l = _analisar(p_sel, df_p, pd.DataFrame([av_p]) if tem_av else pd.DataFrame())
                    fenotipo_l = _normalizar(dados_aval.get('Diagnostico_Clinico', '') if dados_aval.get('Diagnostico_Clinico') else texto_fenotipo_busca)

                    laudo_html = gerar_laudo_html(
                        paciente_nome=st.session_state.paciente,
                        dados_aval=dados_aval,
                        historico=historico,
                        insights=insights_l,
                        fenotipo=fenotipo_l
                    )

                    st.download_button(
                        label="📥 BAIXAR LAUDO DE EVOLUÇÃO (HTML / PDF) — Abrir ou usar o botão 'Imprimir / PDF' abaixo",
                        data=laudo_html.encode('utf-8'),
                        file_name=f"Laudo_GENUA_{st.session_state.paciente.replace(' ', '_')}.html",
                        mime="text/html",
                        type="primary",
                        width='stretch'
                    )
                    toast("Laudo gerado! Clique em qualquer 'Conclusão' ou 'Meta' dentro da pré-visualização abaixo para editar o texto ao vivo antes de salvar em PDF.", "success")
                    components.html(laudo_html, height=1450, scrolling=True)

                except Exception as e:
                    toast(f"Erro ao gerar o laudo: {e}", "error")
                    st.caption("Verifique se o paciente possui avaliação inicial e sessões de check-in registradas.")
