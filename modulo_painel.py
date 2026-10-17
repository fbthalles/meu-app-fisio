"""GENUA | Módulo 3: Painel Analítico (Cérebro Clínico — Joelho) — Estilo Apple Health.

Performance: matplotlib fica em lazy import dentro de render(),
para não pesar o startup do app quando o utilizador ainda não abriu o painel.
"""
import streamlit as st
import pandas as pd
import numpy as np
from config import CORES_GENUA, titulo, secao, toast, aplicar_tema_matplotlib
from firebase_client import conn
from ia_clinica import analisar_paciente, renderizar_insights, normalizar_diagnostico, MCID


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


def _extrair_chave_str(texto_bruto, prefixo: str, default: float = 0.0) -> float:
    """
    Extrai float de strings padronizadas do Firestore como:
    'Ext:35.0 Flex:20.0 Abd:15.0 Add:15.0' ou 'Dir:130.0 Esq:140.0'.
    """
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
    lado_str = str(lado_acometido or "").lower()
    if "direito" in lado_str or "dir > esq" in lado_str:
        lesado, saudavel = val_d, val_e
    elif "esquerdo" in lado_str or "esq > dir" in lado_str:
        lesado, saudavel = val_e, val_d
    else:
        lesado, saudavel = min(val_d, val_e), max(val_d, val_e)

    if saudavel <= 0:
        return None, lesado, saudavel, "⚪"

    lsi = (lesado / saudavel) * 100.0
    cor = "🟢" if lsi >= 90.0 else ("🟡" if lsi >= 85.0 else "🔴")
    return round(lsi, 1), round(lesado, 1), round(saudavel, 1), cor


def _detectar_prom_preenchido(av_p: dict, prom_fenotipo: str = "LEFS") -> list:
    """
    Detecta de forma inteligente qual questionário foi realmente preenchido na Avaliação Inicial,
    filtrando os valores 'default' automáticos dos sliders do modulo_avaliacao.py.
    Retorna lista com 1 questionário principal sugerido.
    """
    if not av_p:
        return []

    lefs_v = float(av_p.get("LEFS_Pct", 0) or 0)
    visap_v = float(av_p.get("VISA_P_Pts", 0) or 0)
    lysh_v = float(av_p.get("Lysholm_Pts", 0) or 0)
    womac_v = float(av_p.get("WOMAC_Pct", 0) or 0)
    koos_v = float(av_p.get("KOOS_Pct", 0) or 0)
    ikdc_v = float(av_p.get("IKDC_Pct", 0) or 0)

    candidatos = []
    # LEFS começa em 0 por padrão; se > 0, foi mexido pelo fisioterapeuta
    if lefs_v > 0:
        candidatos.append("LEFS")
    # VISA-P começa em 50 por padrão nos sliders não tocados
    if visap_v > 0 and visap_v != 50.0:
        candidatos.append("VISA-P")
    # Lysholm começa em 100 por padrão nos selectboxes não tocados
    if lysh_v > 0 and lysh_v != 100.0:
        candidatos.append("Lysholm")
    # WOMAC começa em 100% por padrão
    if womac_v > 0 and round(womac_v, 1) != 100.0:
        candidatos.append("WOMAC")
    # KOOS começa em 100% por padrão
    if koos_v > 0 and round(koos_v, 1) != 100.0:
        candidatos.append("KOOS")
    # IKDC começa em 75% por padrão
    if ikdc_v > 0 and round(ikdc_v, 1) != 75.0:
        candidatos.append("IKDC")

    if candidatos:
        # Prioriza o primeiro detectado ou o que bate com o fenótipo
        mapa_fen = {"VISA_P": "VISA-P", "Lysholm": "Lysholm", "WOMAC": "WOMAC", "KOOS": "KOOS", "IKDC": "IKDC", "LEFS": "LEFS"}
        alvo_fen = mapa_fen.get(prom_fenotipo, "LEFS")
        if alvo_fen in candidatos:
            return [alvo_fen]
        return [candidatos[0]]

    # Fallback se todos estiverem nos defaults: se LEFS > 0 usa LEFS, senão lista vazia
    return ["LEFS"] if lefs_v > 0 else []


def render():
    # Lazy import do Matplotlib + Aplicação do Tema Apple Health
    import matplotlib.pyplot as plt
    aplicar_tema_matplotlib(plt)

    p_sel = st.session_state.paciente

    # ============================================================
    # A. RESGATE DO CADASTRO (COM FALLBACK PARA HMA / DIAGNÓSTICO)
    # ============================================================
    idade_p = "—"
    dx_clinico_base = "Não especificado"
    ocupacao_p = "Não informada"
    medico_cad = ""
    try:
        df_cad = conn.read("Cadastro")
        if not df_cad.empty and "Nome" in df_cad.columns:
            filtro_cad = df_cad[df_cad['Nome'].astype(str).str.strip() == p_sel]
            if not filtro_cad.empty:
                registro_p = filtro_cad.iloc[-1]
                idade_p = int(float(registro_p.get('Idade', 0))) if pd.notna(registro_p.get('Idade')) else "—"
                dx_clinico_base = registro_p.get('Diagnostico_Clinico') or registro_p.get('Historia') or 'Não especificado'
                ocupacao_p = registro_p.get('Ocupacao') or 'Não informada'
                medico_cad = str(registro_p.get('Medico_Indicador', '') or '')
    except Exception:
        pass

    # ============================================================
    # B. RESGATE DA AVALIAÇÃO INICIAL (MARCO ZERO)
    # ============================================================
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
    av_hma = av_p.get('HMA', 'Não registrada') if tem_av else 'Não registrada'
    av_lado = av_p.get('Lado_Acometido', 'Direito') if tem_av else 'Direito'
    av_objetivo = av_p.get('Objetivo_Paciente', 'Retorno à função sem dor') if tem_av else 'Retorno à função sem dor'

    # Se o diagnóstico no Cadastro estiver genérico, tenta enriquecer com HMA/QP para o detector de fenótipo
    texto_fenotipo_busca = dx_clinico_base if dx_clinico_base != "Não especificado" else f"{av_hma} {av_qp}"
    fen_info = normalizar_diagnostico(texto_fenotipo_busca)

    try:
        sane_base_av = float(av_p.get('SANE_Baseline_Pct', 30.0) or 30.0) if tem_av else 30.0
    except (ValueError, TypeError):
        sane_base_av = 30.0
    try:
        psfs_base_av = int(float(av_p.get('PSFS_Baseline', 3) or 3)) if tem_av else 3
    except (ValueError, TypeError):
        psfs_base_av = 3

    # Extração de Bandeiras e Força Bilateral da Avaliação Inicial
    red_flags_str = str(av_p.get('Red_Flags', 'Nenhuma') or 'Nenhuma')
    yellow_flags_str = str(av_p.get('Yellow_Cog', av_p.get('Yellow_Flags', 'Nenhum')) or 'Nenhum')
    blue_flags_str = str(av_p.get('Fatores_Sociais', 'Nenhum') or 'Nenhum')

    # Extração de Dinamometria (kgf) com fallback para Escala de Oxford (0-5)
    din_d_str = av_p.get('Dinamometria_Dir', '')
    din_e_str = av_p.get('Dinamometria_Esq', '')
    oxf_d_str = av_p.get('Forca_Geral_Dir', '')
    oxf_e_str = av_p.get('Forca_Geral_Esq', '')

    ext_kg_d = _extrair_chave_str(din_d_str, "Ext", 0.0)
    ext_kg_e = _extrair_chave_str(din_e_str, "Ext", 0.0)
    usa_dinamometria = (ext_kg_d > 0 or ext_kg_e > 0)
    unidade_forca = "kgf" if usa_dinamometria else "grau Oxford (0-5)"
    fonte_d = din_d_str if usa_dinamometria else oxf_d_str
    fonte_e = din_e_str if usa_dinamometria else oxf_e_str

    grupos_musculares = [
        ("Quadríceps (Extensão)", "Ext"),
        ("Isquiotibiais (Flexão)", "Flex"),
        ("Glúteo Médio (Abdução)", "Abd"),
        ("Adutores (Adução)", "Add"),
    ]
    dados_forca_bilateral = []
    for label_m, pref in grupos_musculares:
        vd = _extrair_chave_str(fonte_d, pref, 0.0)
        ve = _extrair_chave_str(fonte_e, pref, 0.0)
        lsi_m, les_m, sau_m, cor_m = _calcular_lsi_seguro(vd, ve, av_lado)
        dados_forca_bilateral.append({
            "Grupo Muscular": label_m,
            "Direito": f"{vd:.1f} {unidade_forca}",
            "Esquerdo": f"{ve:.1f} {unidade_forca}",
            "val_d": vd,
            "val_e": ve,
            "LSI (%)": f"{cor_m} {lsi_m:.0f}%" if lsi_m is not None else "⚪ N/D",
            "lsi_num": lsi_m
        })

    lsi_quad_num = dados_forca_bilateral[0]["lsi_num"]
    cor_lsi_quad = dados_forca_bilateral[0]["LSI (%)"].split()[0] if lsi_quad_num is not None else "⚪"

    # Extração de Goniometria e Perimetria da Avaliação Inicial
    adm_flex_d_av = _extrair_chave_str(av_p.get("ADM_Joelho_Flexao", ""), "Dir", 0.0)
    adm_flex_e_av = _extrair_chave_str(av_p.get("ADM_Joelho_Flexao", ""), "Esq", 0.0)
    adm_ext_d_av = _extrair_chave_str(av_p.get("ADM_Joelho_Extensao", ""), "Dir", 0.0)
    adm_ext_e_av = _extrair_chave_str(av_p.get("ADM_Joelho_Extensao", ""), "Esq", 0.0)
    lunge_d_av = _extrair_chave_str(av_p.get("Lunge_Test", ""), "Dir", 0.0)
    lunge_e_av = _extrair_chave_str(av_p.get("Lunge_Test", ""), "Esq", 0.0)
    perim_d_av = float(av_p.get("Perimetria_Dir_cm", 0.0) or 0.0)
    perim_e_av = float(av_p.get("Perimetria_Esq_cm", 0.0) or 0.0)

    # ============================================================
    # 1. HEADER EXECUTIVO DO PACIENTE (Apple Health Profile)
    # ============================================================
    with st.container(border=True):
        st.markdown(f"""
            <div style='display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;'>
                <div>
                    <span style='font-size: 0.76rem; font-weight: 700; text-transform: uppercase;
                                 letter-spacing: 0.06em; color: {CORES_GENUA['secundaria']};'>
                        Cockpit Analítico PBE · Fenótipo: {fen_info['label']}
                    </span>
                    <h2 style='margin: 2px 0 6px 0; color: {CORES_GENUA['texto_escuro']};'>
                        👤 {p_sel}
                    </h2>
                    <p style='margin: 0; color: {CORES_GENUA['texto_suave']}; font-size: 0.92rem;'>
                        <b>Dx / HMA:</b> {dx_clinico_base if dx_clinico_base != 'Não especificado' else av_hma[:90]} &nbsp;|&nbsp;
                        <b>Objetivo (PSFS {psfs_base_av}/10):</b> {av_objetivo}
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

    # BANNER DE SEGURANÇA IMEDIATO (SE HOUVER RED OU YELLOW FLAGS NA AVALIAÇÃO)
    tem_red_flag = red_flags_str.lower() not in ["nenhuma", "nenhum", "não", "nao", "", "none"]
    tem_yellow_flag = yellow_flags_str.lower() not in ["nenhuma", "nenhum", "não", "nao", "", "none", "['nenhum']"]
    if tem_red_flag:
        toast(f"🚨 ALERTA DE RED FLAG REGISTRADA NA AVALIAÇÃO: {red_flags_str} — Verificar necessidade de parecer médico.", "error")
    elif tem_yellow_flag:
        toast(f"🟡 Atenção Psicossocial (Yellow Flag): {yellow_flags_str} — Associar educação em dor e exposição graduada.", "warning")

    # ============================================================
    # 2. EXPANDER DE AVALIAÇÃO FÍSICA BASELINE (MARCO ZERO)
    # ============================================================
    if tem_av:
        with st.expander(f"📋 Ficha Completa da Avaliação Inicial (Marco Zero: {av_data})", expanded=False):
            t_resumo, t_fisico, t_funcional, t_proms = st.tabs([
                "🗣️ Anamnese & Metas", "📐 Exame Físico (Dir × Esq)", "💪 Força, ADM & Controle", "📊 PROMs & MCID"
            ])

            with t_resumo:
                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    st.markdown("**Histórico Clínico e Comportamento da Dor:**")
                    st.markdown(f"- **Queixa Principal (QP):** {av_qp}")
                    st.markdown(f"- **HMA:** {av_hma}")
                    st.markdown(f"- **Sinais Associados:** {av_p.get('Sinais_Sintomas', 'Não relatado')}")
                    st.markdown(f"- **Tipo / Origem da Dor:** {av_p.get('Class_Dor', 'N/A')} ({av_p.get('Origem_Dor', 'N/A')})")
                    st.markdown(f"- **Zonas Álgicas:** {av_p.get('Zonas_Dor', 'N/A')}")
                    st.markdown(f"- **🟢 Alívio / 🔴 Piora:** {av_p.get('Fatores_Alivio', '—')} / {av_p.get('Fatores_Piora', '—')}")
                with c_r2:
                    st.markdown("**Metas (PSFS/SANE), Biopsicossocial e Imagem:**")
                    st.markdown(f"- **Objetivo Principal:** {av_objetivo}")
                    st.markdown(f"- **Baseline Subjetivo:** PSFS **{psfs_base_av}/10** | SANE **{sane_base_av:.0f}%**")
                    st.markdown(f"- **Red / Yellow Flags:** {red_flags_str} / {yellow_flags_str}")
                    st.markdown(f"- **Contexto Social / Comorbidades:** {blue_flags_str} / {av_p.get('Comorbidades', 'Nenhuma')}")
                    st.markdown(f"- **Exames Apresentados:** {av_p.get('Exames_Apresentados', 'Nenhum')}")
                    st.markdown(f"- **Laudo de Imagem:** {av_p.get('Laudo_Exames', 'Não relatado')}")

            with t_fisico:
                st.markdown(f"**🚶 Marcha Global:** {av_p.get('Marcha', 'N/A')} &nbsp;|&nbsp; **Cicatrizes/Pele:** {av_p.get('Pele', 'Normal')}")
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                c_fd, c_fe = st.columns(2)
                with c_fd:
                    st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-bottom: 6px;'>🦵 Membro DIREITO</h4>", unsafe_allow_html=True)
                    st.markdown(f"- **Derrame / Godet:** {av_p.get('Derrame_Dir', av_p.get('Derrame', 'N/A'))} / {av_p.get('Godet_Dir', av_p.get('Godet', 'N/A'))}")
                    st.markdown(f"- **Alinhamento / Trofismo:** {av_p.get('Alinhamento_Dir', av_p.get('Alinhamento', 'N/A'))} / {av_p.get('Trofismo_Dir', av_p.get('Trofismo', 'N/A'))}")
                    st.markdown(f"- **Perimetria Coxa:** {f'{perim_d_av} cm' if perim_d_av > 0 else av_p.get('Perimetria', 'N/A')}")
                    st.markdown(f"- **Palpação:** {av_p.get('Palpacao_Dir', av_p.get('Palpacao', 'Sem dor'))}")
                    st.markdown(f"- **Testes Ligamentares (+):** {av_p.get('Testes_Ligamentares_Dir', av_p.get('Testes_Ligamentares', 'Nenhum'))}")
                    st.markdown(f"- **Testes Meniscais (+):** {av_p.get('Testes_Meniscais_Dir', av_p.get('Testes_Meniscais', 'Nenhum'))}")
                    st.markdown(f"- **Femoropatelar/Tendão (+):** {av_p.get('Testes_Femoropatelar_Dir', av_p.get('Testes_Femoropatelar', 'Nenhum'))}")
                with c_fe:
                    st.markdown(f"<h4 style='color: {CORES_GENUA['secundaria']}; margin-bottom: 6px;'>🦵 Membro ESQUERDO</h4>", unsafe_allow_html=True)
                    st.markdown(f"- **Derrame / Godet:** {av_p.get('Derrame_Esq', av_p.get('Derrame', 'N/A'))} / {av_p.get('Godet_Esq', av_p.get('Godet', 'N/A'))}")
                    st.markdown(f"- **Alinhamento / Trofismo:** {av_p.get('Alinhamento_Esq', av_p.get('Alinhamento', 'N/A'))} / {av_p.get('Trofismo_Esq', av_p.get('Trofismo', 'N/A'))}")
                    st.markdown(f"- **Perimetria Coxa:** {f'{perim_e_av} cm' if perim_e_av > 0 else av_p.get('Perimetria', 'N/A')}")
                    st.markdown(f"- **Palpação:** {av_p.get('Palpacao_Esq', av_p.get('Palpacao', 'Sem dor'))}")
                    st.markdown(f"- **Testes Ligamentares (+):** {av_p.get('Testes_Ligamentares_Esq', 'Nenhum')}")
                    st.markdown(f"- **Testes Meniscais (+):** {av_p.get('Testes_Meniscais_Esq', 'Nenhum')}")
                    st.markdown(f"- **Femoropatelar/Tendão (+):** {av_p.get('Testes_Femoropatelar_Esq', 'Nenhum')}")

            with t_funcional:
                c_fun1, c_fun2 = st.columns(2)
                with c_fun1:
                    st.caption("FORÇA (OXFORD 0-5) & DINAMOMETRIA (KGF)")
                    st.markdown(f"- **Oxford (Dir):** `{oxf_d_str or 'N/A'}`")
                    st.markdown(f"- **Oxford (Esq):** `{oxf_e_str or 'N/A'}`")
                    st.markdown(f"- **Dinamometria (Dir):** `{din_d_str or 'N/A'}`")
                    st.markdown(f"- **Dinamometria (Esq):** `{din_e_str or 'N/A'}`")
                    st.markdown(f"- **Controle Motor Global:** `{av_p.get('CM_Globais', 'N/A')}`")
                with c_fun2:
                    st.caption("MOBILIDADE (GONIOMETRIA) & CONTROLE MOTOR UNIPODAL")
                    st.markdown(f"- **ADM Flexão / Extensão:** `{av_p.get('ADM_Joelho_Flexao', 'N/A')}` / `{av_p.get('ADM_Joelho_Extensao', 'N/A')}`")
                    st.markdown(f"- **Lunge Test (Tornozelo):** `{av_p.get('Lunge_Test', 'N/A')}`")
                    st.markdown(f"- **Flexibilidade:** `{av_p.get('Flexibilidade', 'Normal')}`")
                    st.markdown(f"- **Controle Motor (Dir):** `{av_p.get('CM_Membro_Dir', 'N/A')}`")
                    st.markdown(f"- **Controle Motor (Esq):** `{av_p.get('CM_Membro_Esq', 'N/A')}`")

            with t_proms:
                st.caption("SCORES FUNCIONAIS DE BASELINE E METAS DE MUDANÇA MÍNIMA CLINICAMENTE IMPORTANTE (MCID)")
                c_p1, c_p2, c_p3, c_p4, c_p5, c_p6 = st.columns(6)
                c_p1.metric("LEFS", f"{float(av_p.get('LEFS_Pct', 0) or 0):.1f}%", "MCID: +9 pts", delta_color="off")
                c_p2.metric("Lysholm", f"{av_p.get('Lysholm_Pts', 0)} pts", "MCID: +10 pts", delta_color="off")
                c_p3.metric("VISA-P", f"{av_p.get('VISA_P_Pts', 0)} pts", "MCID: +13 pts", delta_color="off")
                c_p4.metric("WOMAC", f"{float(av_p.get('WOMAC_Pct', 0) or 0):.1f}%", "MCID: +12%", delta_color="off")
                c_p5.metric("KOOS", f"{float(av_p.get('KOOS_Pct', 0) or 0):.1f}%", "MCID: +8-10 pts", delta_color="off")
                c_p6.metric("IKDC", f"{float(av_p.get('IKDC_Pct', 0) or 0):.1f}%", "MCID: +9 pts", delta_color="off")
    else:
        st.info("⚠️ Nenhuma Avaliação Inicial registrada para este paciente. Preencha o módulo Avaliação Inicial para habilitar o LSI e o Baseline.")

    # ============================================================
    # C. MOTOR DE EVOLUÇÃO LONGITUDINAL (CHECK-INS DIÁRIOS)
    # ============================================================
    df_p = conn.read_paciente("Evolucao", p_sel)
    if df_p.empty:
        st.warning("⚠️ O paciente ainda não possui sessões de Check-in diário registradas.")
        st.stop()

    if 'Membro' not in df_p.columns:
        df_p['Membro'] = "Joelho"
    else:
        df_p['Membro'] = df_p['Membro'].fillna("Joelho")

    df_p = df_p[df_p['Membro'] == "Joelho"].copy()
    if df_p.empty:
        st.warning("⚠️ O paciente ainda não possui sessões de Check-in diário para Joelho.")
        st.stop()

    df_p['Data_dt'] = pd.to_datetime(df_p['Data'], format="mixed", dayfirst=False, errors="coerce")
    df_p = df_p.sort_values('Data_dt').reset_index(drop=True)
    df_p['Sessão_Num'] = [
        f"S{i+1} ({d.strftime('%d/%m') if pd.notna(d) else '?'})"
        for i, d in enumerate(df_p['Data_dt'])
    ]

    if 'Dor' not in df_p.columns:
        df_p['Dor'] = 0
    df_p['Dor'] = pd.to_numeric(df_p['Dor'], errors='coerce').fillna(0)

    if 'EVA_Semanal' not in df_p.columns:
        df_p['EVA_Semanal'] = df_p['Dor']
    df_p['EVA_Semanal'] = pd.to_numeric(df_p['EVA_Semanal'], errors='coerce').fillna(df_p['Dor'])

    col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
    if col_inc not in df_p.columns:
        df_p[col_inc] = "Nenhum"
    df_p['Inchaco_N'] = df_p[col_inc].apply(_mapear_inchaco)

    for col, default in [
        ('Flexao', 90), ('Extensao', 'Completa (0°)'),
        ('Sono', 'Bem'), ('Agachamento', 'Sem Dor (0)'),
        ('Step_Up', 'Sem Dor (0)'), ('Step_Down', 'Sem Dor (0)')
    ]:
        if col not in df_p.columns:
            df_p[col] = default

    df_p['Flexao'] = pd.to_numeric(df_p['Flexao'], errors='coerce').fillna(90)

    if 'SANE_Pct' not in df_p.columns:
        df_p['SANE_Pct'] = np.nan
    df_p['SANE_Pct_Num'] = pd.to_numeric(df_p['SANE_Pct'], errors='coerce')

    # Calcula Score de Tolerância Funcional (0-10) e Índice Funcional (0-100%) por sessão
    func_scores = []
    tol_func_pct = []
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
        tol_func_pct.append(min(max(float(media_10 * 10.0), 0.0), 100.0) if media_10 is not None else 100.0)

    df_p['Func_Score'] = func_scores
    df_p['LSI'] = tol_func_pct  # Mantém nome de coluna 'LSI' no DataFrame p/ compatibilidade com pdf_laudo.py

    # ============================================================
    # 3. SELETOR DE SESSÃO, REATIVIDADE 24H E 6 KPIS EXECUTIVOS
    # ============================================================
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
    ultima = df_p.loc[idx_sel]
    anterior = df_p.loc[idx_sel - 1] if idx_sel > 0 else None

    dor_atual = int(ultima.get('Dor', 0))
    dor_ant = int(anterior.get('Dor', dor_atual)) if anterior is not None else int(df_p.iloc[0].get('Dor', dor_atual))
    delta_dor_24h = dor_atual - dor_ant

    inchaco_atual = int(ultima.get('Inchaco_N', 0))
    inchaco_ant = int(anterior.get('Inchaco_N', inchaco_atual)) if anterior is not None else inchaco_atual
    sono_atual = str(ultima.get('Sono', 'Bem'))
    tol_atual = float(ultima.get('LSI', 0))
    flex_atual = float(ultima.get('Flexao', 90))
    ext_str = str(ultima.get('Extensao', 'Completa (0°)'))

    # Regra das 24h de Irritabilidade Tecidual (Silbernagel et al., 2007)
    if idx_sel > 0 and (delta_dor_24h >= 2 or (inchaco_atual > inchaco_ant and inchaco_atual >= 2)):
        toast(
            f"⚠️ Alerta de Reatividade 24h (Silbernagel 2007): Aumento de dor (+{delta_dor_24h} pts na EVA) ou efusão "
            f"(Grau {inchaco_atual}/3) em relação à sessão anterior. Sugestão: Regredir carga mecânica em 20-30% hoje.",
            "warning"
        )

    # SANE, GROC e PASS da sessão selecionada
    sane_sessao = ultima.get('SANE_Pct_Num')
    sane_sessao = float(sane_sessao) if pd.notna(sane_sessao) else sane_base_av
    dist_meta_sessao = max(0.0, 100.0 - sane_sessao)
    ganho_sane_sessao = sane_sessao - sane_base_av

    groc_sessao_val = ultima.get('GROC_Score')
    try:
        groc_sessao_int = int(float(groc_sessao_val)) if pd.notna(groc_sessao_val) else None
    except (ValueError, TypeError):
        groc_sessao_int = None

    pass_sessao_str = str(ultima.get('PASS_Satisfacao', 'Não registrado') or 'Não registrado')
    pass_bool = ultima.get('PASS_Atingido')
    if pd.isna(pass_bool) or pass_bool is None:
        pass_bool = pass_sessao_str.startswith("👍")

    # Árvore de Decisão Fenotípica da Sessão
    testes_ult = ultima.get('Testes_Funcionais', {}) if isinstance(ultima.get('Testes_Funcionais'), dict) else {}
    agach_str = str(testes_ult.get('Agachamento Bipodal', ultima.get('Agachamento', 'Sem Dor')))
    step_down_str = str(
        testes_ult.get('Step Down')
        or testes_ult.get('Step Down (D)')
        or testes_ult.get('Step Down (E)')
        or ultima.get('Step_Down', 'Sem Dor')
    )

    if "Incapaz" in agach_str and inchaco_atual >= 2 and dor_atual >= 8:
        fenotipo_sessao = "🚨 Risco Estrutural (Alerta)"
        diretriz = "Incapacidade de descarga de peso + Edema Agudo. Indicação de avaliação médica/imagem e proteção de carga."
    elif ("Incapaz" in step_down_str or "Moderada" in step_down_str or "Grave" in step_down_str) and inchaco_atual <= 1:
        fenotipo_sessao = "🟣 Sobrecarga Femoropatelar"
        diretriz = "Dor na desaceleração excêntrica. Foco em fortalecimento póstero-lateral de quadril e controle de vetor em cadeia fechada (0-45°)."
    elif ("Déficit" in ext_str) and inchaco_atual >= 2:
        fenotipo_sessao = "🟤 Bloqueio / Artrogênico"
        diretriz = "Déficit de extensão terminal associado a derrame articular (inibição artrogênica do quadríceps). Priorizar ganho de extensão 0° e crioterapia/controle de efusão."
    elif ("Incapaz" in agach_str or "Moderada" in agach_str) and "Completa" in ext_str and inchaco_atual == 0:
        fenotipo_sessao = "🟠 Tendinopático Reativo"
        diretriz = "Dor em armazenamento/liberação de energia elástica sem derrame articular. Modular carga excêntrica e aplicar isometria analgésica (Rio et al., 2015)."
    elif dor_atual <= 3 and inchaco_atual <= 1 and tol_atual >= 80:
        fenotipo_sessao = "🟢 Remodelamento Funcional"
        diretriz = "Alta tolerância mecânica. Progressão segura para desaceleração rápida, pliometria e gesto esportivo específico."
    else:
        fenotipo_sessao = "🔵 Acomodação de Carga"
        diretriz = "Sinais reativos mistos. Modular volume e intensidade conforme irritabilidade tecidual (regra das 24h)."

    # 6 KPIs Executivos Apple Health
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(
        "Dor Hoje (EVA)",
        f"{dor_atual}/10",
        f"{delta_dor_24h:+d} pts vs anterior" if idx_sel > 0 else f"Semanal: {int(ultima.get('EVA_Semanal', dor_atual))}/10",
        delta_color="inverse"
    )
    k2.metric(
        "Reatividade / Derrame",
        f"Grau {inchaco_atual}/3",
        f"Sono: {sono_atual}",
        delta_color="off"
    )
    k3.metric(
        "ADM (Flex / Ext)",
        f"{flex_atual:.0f}°",
        ext_str,
        delta_color="normal" if "Completa" in ext_str and flex_atual >= 120 else "off"
    )
    k4.metric(
        "Tolerância Funcional",
        f"{tol_atual:.0f}%",
        "Alta Tolerância" if tol_atual >= 85 else ("Moderada" if tol_atual >= 60 else "Baixa"),
        delta_color="normal" if tol_atual >= 85 else "off"
    )
    k5.metric(
        f"{cor_lsi_quad} LSI Força (Quad)",
        f"{lsi_quad_num:.0f}%" if lsi_quad_num is not None else "N/D",
        f"Meta Alta: ≥90% ({unidade_forca})",
        delta_color="normal" if (lsi_quad_num or 0) >= 90 else "off"
    )
    k6.metric(
        "Meta (SANE / PASS)",
        f"{sane_sessao:.0f}%",
        f"{'👍 PASS Sim' if pass_bool else '⏳ PASS Não'} ({ganho_sane_sessao:+.0f}%)",
        delta_color="normal" if pass_bool else "off"
    )

    # Se a sessão foi registrada em Modo Bilateral no Check-in, exibe resumo D x E da sessão
    if bool(ultima.get("Registro_Bilateral")):
        with st.container(border=True):
            st.caption("🦵 COMPARATIVO BILATERAL DA SESSÃO SELECIONADA (DIREITO × ESQUERDO)")
            cb1, cb2, cb3, cb4 = st.columns(4)
            cb1.metric("EVA (Dir | Esq)", f"{ultima.get('Dor_Dir', 0)}/10 | {ultima.get('Dor_Esq', 0)}/10")
            cb2.metric("Flexão (Dir | Esq)", f"{ultima.get('Flexao_Dir', 90)}° | {ultima.get('Flexao_Esq', 90)}°")
            cb3.metric("Extensão (Dir | Esq)", f"{ultima.get('Extensao_Dir', '-')} | {ultima.get('Extensao_Esq', '-')}")
            cb4.metric("Derrame (Dir | Esq)", f"{ultima.get('Inchaco_Dir', '-')} | {ultima.get('Inchaco_Esq', '-')}")

    # Dupla Barra de Progresso Executiva
    with st.container(border=True):
        c_prog1, c_prog2 = st.columns(2, gap="large")
        with c_prog1:
            st.markdown(f"**🎯 Tolerância sem Dor nos Movimentos Alvo: {tol_atual:.0f}%** *(Meta PBE: ≥ 90%)*")
            st.progress(min(max(tol_atual / 100.0, 0.0), 1.0))
        with c_prog2:
            st.markdown(
                f"**🏆 Progresso rumo ao Objetivo do Paciente (SANE): {sane_sessao:.0f}%** "
                f"*(Faltam {dist_meta_sessao:.0f}% para a meta · GROC: {f'{groc_sessao_int:+d}' if groc_sessao_int is not None else 'N/D'})*"
            )
            st.progress(min(max(sane_sessao / 100.0, 0.0), 1.0))

    # ============================================================
    # 4. NAVEGAÇÃO ANALÍTICA EM 3 ABAS DE ALTA DENSIDADE INFORMATIVA
    # ============================================================
    t1, t2, t_ic = st.tabs([
        "📊 1. Carga, Dor & Reatividade (24h)",
        "📐 2. Biomecânica, Simetria (LSI) & Metas",
        "🧠 3. Inteligência Clínica & Critérios de Alta"
    ])

    # ------------------------------------------------------------
    # ABA 1: CARGA, DOR, FUNÇÃO E REATIVIDADE ARTICULAR (SONO/DERRAME)
    # ------------------------------------------------------------
    with t1:
        with st.container(border=True):
            secao(
                "📊 Curva de Resposta Terapêutica: Dor (EVA) × Tolerância Funcional",
                "A faixa verde (EVA ≤ 3) delimita a zona de carga segura (Silbernagel et al., 2007). O cruzamento das curvas confirma ganho real de função."
            )

            fig1, ax1 = plt.subplots(figsize=(10, 4.0), dpi=120)

            # Zona de Carga Segura (EVA 0 a 3)
            ax1.axhspan(0, 3.0, color=CORES_GENUA['alerta_sucesso'], alpha=0.07, label="Zona de Carga Segura (EVA ≤ 3)")

            cor_dor = CORES_GENUA['alerta_erro']
            ax1.plot(
                df_p['Sessão_Num'], df_p['Dor'],
                color=cor_dor, marker='o', markersize=7, lw=2.8,
                label="Dor Diária (EVA 0-10)", zorder=4
            )
            if (df_p['EVA_Semanal'] != df_p['Dor']).any():
                ax1.plot(
                    df_p['Sessão_Num'], df_p['EVA_Semanal'],
                    color=CORES_GENUA['alerta_aviso'], marker='^', markersize=5, lw=1.6,
                    linestyle=':', label="EVA Média Semanal", zorder=3
                )
            ax1.set_ylabel("Dor (EVA 0-10)", color=cor_dor, fontweight='600')
            ax1.set_ylim(-0.5, 10.5)

            cor_func = CORES_GENUA['alerta_sucesso']
            ax1b = ax1.twinx()
            ax1b.grid(False)
            func_plot = df_p['Func_Score'].interpolate() if df_p['Func_Score'].notna().sum() > 1 else df_p['Func_Score']
            ax1b.plot(
                df_p['Sessão_Num'], func_plot,
                color=cor_func, marker='s', markersize=6.5, lw=2.6,
                linestyle='--', label="Tolerância Funcional (0-10)", zorder=3
            )
            ax1b.set_ylabel("Função nos Testes (0-10)", color=cor_func, fontweight='600')
            ax1b.set_ylim(-0.5, 10.5)

            ax1.spines['top'].set_visible(False)
            ax1b.spines['top'].set_visible(False)
            plt.setp(ax1.get_xticklabels(), rotation=25, ha='right', fontsize=9)

            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax1b.get_legend_handles_labels()
            ax1.legend(
                lines1 + lines2, labels1 + labels2,
                loc='upper center', bbox_to_anchor=(0.5, 1.16),
                ncol=3, frameon=False, fontsize=8.8
            )

            fig1.tight_layout()
            st.pyplot(fig1)

            # Matriz de Evolução de cada Teste Funcional Alvo (1ª Sessão vs Sessão Atual)
            if testes_nomes:
                st.markdown("<hr style='margin: 14px 0;'>", unsafe_allow_html=True)
                st.markdown("**🎯 Matriz de Evolução por Movimento Alvo (1ª Sessão → Sessão Selecionada)**")
                cols_t = st.columns(min(len(testes_nomes), 3))
                for idx_t, teste_nome in enumerate(sorted(testes_nomes)):
                    valores_teste = []
                    for _, row in df_p.loc[:idx_sel].iterrows():
                        testes = row.get('Testes_Funcionais', {})
                        if isinstance(testes, dict) and teste_nome in testes:
                            valores_teste.append(testes.get(teste_nome, "—"))
                    primeira = valores_teste[0] if valores_teste else "—"
                    ultima_val = valores_teste[-1] if valores_teste else "—"
                    sc_ini = _score_funcional_item(primeira) or 0
                    sc_fim = _score_funcional_item(ultima_val) or 0
                    badge = "🟢 Melhorou" if sc_fim > sc_ini else ("🔴 Piorou" if sc_fim < sc_ini else "⚪ Estável")
                    with cols_t[idx_t % len(cols_t)]:
                        st.caption(f"🏃 {teste_nome.upper()} · {badge}")
                        st.markdown(f"`{primeira}` ➔ **`{ultima_val}`**")

        # NOVO GRÁFICO PBE: Reatividade Articular (Derrame) & Modulação pelo Sono
        with st.container(border=True):
            secao(
                "💧 Rastreador de Irritabilidade Tecidual (Derrame Articular × Dor × Sono)",
                "Diferenciação clínica: Picos de dor acompanhados de aumento do derrame indicam sobrecarga mecânica; picos de dor sem derrame após noite de 'Insônia/Acordou com dor' sugerem amplificação central (Finan et al., 2013)."
            )
            fig_reat, ax_r1 = plt.subplots(figsize=(10, 3.3), dpi=120)
            x_idx = np.arange(len(df_p))

            # Barras de Inchaço/Derrame (0 a 3)
            ax_r1.bar(
                x_idx, df_p['Inchaco_N'], width=0.42,
                color=CORES_GENUA['secundaria'], alpha=0.35, label="Derrame Articular (Grau 0-3)"
            )
            ax_r1.set_ylabel("Derrame (Grau 0-3)", color=CORES_GENUA['secundaria'], fontweight='600')
            ax_r1.set_ylim(0, 3.6)
            ax_r1.set_yticks([0, 1, 2, 3])
            ax_r1.set_xticks(x_idx)
            ax_r1.set_xticklabels(df_p['Sessão_Num'], rotation=25, ha='right', fontsize=9)

            ax_r2 = ax_r1.twinx()
            ax_r2.grid(False)
            ax_r2.plot(
                x_idx, df_p['Dor'], color=CORES_GENUA['alerta_erro'],
                marker='o', lw=2.2, label="Dor (EVA 0-10)"
            )
            # Marca em laranja/amarelo as sessões onde o paciente dormiu mal
            for i_s, row_s in df_p.iterrows():
                sono_s = str(row_s.get('Sono', 'Bem')).lower()
                if "insônia" in sono_s or "dor" in sono_s or "ruim" in sono_s:
                    ax_r2.scatter(
                        i_s, row_s['Dor'], color=CORES_GENUA['alerta_aviso'],
                        s=160, zorder=6, edgecolors='#1D1D1F', linewidth=1.5,
                        label="🌙 Sono Ruim / Acordou c/ Dor" if i_s == df_p.index[0] else "_nolegend_"
                    )
            ax_r2.set_ylabel("Dor (EVA 0-10)", color=CORES_GENUA['alerta_erro'], fontweight='600')
            ax_r2.set_ylim(-0.5, 10.5)
            ax_r1.spines['top'].set_visible(False)
            ax_r2.spines['top'].set_visible(False)

            l_r1, lb_r1 = ax_r1.get_legend_handles_labels()
            l_r2, lb_r2 = ax_r2.get_legend_handles_labels()
            ax_r1.legend(l_r1 + l_r2, lb_r1 + lb_r2, loc='upper right', frameon=False, fontsize=8.8)
            fig_reat.tight_layout()
            st.pyplot(fig_reat)

    # ------------------------------------------------------------
    # ABA 2: BIOMECÂNICA, SIMETRIA BILATERAL (LSI) & METAS (SANE)
    # ------------------------------------------------------------
    with t2:
        # Card 1: Matriz de Simetria Bilateral (Direito vs Esquerdo)
        with st.container(border=True):
            secao(
                f"⚖️ Matriz de Simetria Bilateral (LSI — Lado Acometido: {av_lado})",
                f"Comparativo quantitativo extraído da Avaliação Inicial ({unidade_forca}). Critério de alta PBE: LSI ≥ 90% (Grindem et al., 2016)."
            )

            c_sim1, c_sim2 = st.columns([1.45, 1.55], gap="large")
            with c_sim1:
                st.caption(f"💪 FORÇA MUSCULAR POR GRUPO ({unidade_forca.upper()})")
                df_tabela_forca = pd.DataFrame(dados_forca_bilateral)[["Grupo Muscular", "Direito", "Esquerdo", "LSI (%)"]]
                st.dataframe(df_tabela_forca, hide_index=True, use_container_width=True)

                # Cálculo da Relação Isquiotibiais / Quadríceps (I:Q Ratio)
                ext_d_v, flex_d_v = dados_forca_bilateral[0]["val_d"], dados_forca_bilateral[1]["val_d"]
                ext_e_v, flex_e_v = dados_forca_bilateral[0]["val_e"], dados_forca_bilateral[1]["val_e"]
                iq_d = (flex_d_v / ext_d_v * 100.0) if ext_d_v > 0 else None
                iq_e = (flex_e_v / ext_e_v * 100.0) if ext_e_v > 0 else None
                if iq_d is not None or iq_e is not None:
                    st.caption(
                        f"⚙️ **Relação Isquiotibiais/Quadríceps (I:Q Ratio):** "
                        f"Direito: **{f'{iq_d:.0f}%' if iq_d else 'N/D'}** | "
                        f"Esquerdo: **{f'{iq_e:.0f}%' if iq_e else 'N/D'}** *(Faixa normativa: 55% a 75% — Kyritsis et al., 2016)*"
                    )

            with c_sim2:
                st.caption("📐 SIMETRIA DE MOBILIDADE ARTICULAR & TROFISMO DE COXA")
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
                        "Parâmetro": "Perimetria Supra-patelar (cm)",
                        "Direito": f"{perim_d_av:.1f} cm" if perim_d_av > 0 else "N/D",
                        "Esquerdo": f"{perim_e_av:.1f} cm" if perim_e_av > 0 else "N/D",
                        "Diferença (Δ)": f"{abs(perim_d_av - perim_e_av):.1f} cm ({'🟢 Normal' if abs(perim_d_av - perim_e_av) < 1.5 else '🔴 Hipotrofia ≥1.5cm'})" if (perim_d_av > 0 and perim_e_av > 0) else "N/D"
                    }
                ]
                st.dataframe(pd.DataFrame(linhas_mob), hide_index=True, use_container_width=True)

        # Card 2: Evolução Longitudinal de Mobilidade (Flexão vs Dor)
        with st.container(border=True):
            secao(
                "📉 Evolução Longitudinal de Amplitude Articular (Flexão °) × Dor",
                f"Fenótipo ativo: {fen_info['label']} · Linha tracejada indica meta funcional de flexão (≥ 125°)."
            )

            fig2, ax2 = plt.subplots(figsize=(10, 3.8), dpi=120)
            ax2.plot(
                df_p['Sessão_Num'], df_p['Dor'],
                color=CORES_GENUA['alerta_erro'], marker='o', markersize=7, lw=2.6, label="Dor (EVA)"
            )
            ax2.set_ylabel("Dor (EVA 0-10)", color=CORES_GENUA['alerta_erro'], fontweight='600')
            ax2.set_ylim(-0.5, 10.5)

            ax3 = ax2.twinx()
            ax3.grid(False)
            ax3.axhline(y=125, color=CORES_GENUA['secundaria'], linestyle='--', lw=1.3, alpha=0.6, label="Meta Flexão (125°)")
            ax3.plot(
                df_p['Sessão_Num'], df_p['Flexao'],
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

        # Card 3: Curva de Aproximação ao Objetivo do Paciente (SANE %) — LEGENDA NO TOPO SEM SOBREPOSIÇÃO
        with st.container(border=True):
            secao(
                "🏆 Trajetória Rumo ao Objetivo do Paciente (SANE % — Shelbourne et al., 2009)",
                f"Objetivo: '{av_objetivo}' · MCID do SANE = +15% · Limiar de Alta Subjetiva ≥ 85%."
            )
            fig_sane, ax_s = plt.subplots(figsize=(10, 3.5), dpi=120)
            sane_serie = df_p['SANE_Pct_Num'].fillna(sane_base_av)
            ax_s.axhline(y=85, color=CORES_GENUA['alerta_sucesso'], linestyle='--', lw=1.6, alpha=0.85, label="Limiar de Alta (85%)")
            ax_s.axhline(y=min(100.0, sane_base_av + 15.0), color=CORES_GENUA['alerta_aviso'], linestyle='-.', lw=1.3, alpha=0.75, label=f"Meta MCID (+15% = {min(100.0, sane_base_av + 15.0):.0f}%)")
            ax_s.axhline(y=sane_base_av, color=CORES_GENUA['texto_suave'], linestyle=':', lw=1.3, alpha=0.7, label=f"Marco Zero ({sane_base_av:.0f}%)")
            ax_s.plot(
                df_p['Sessão_Num'], sane_serie,
                color=CORES_GENUA['primaria'], marker='o', markersize=7, lw=2.8, label="SANE Atual (%)"
            )
            ax_s.fill_between(range(len(df_p)), sane_serie, alpha=0.10, color=CORES_GENUA['secundaria'])
            ax_s.set_ylabel("Capacidade Percebida (%)", fontweight='600', color=CORES_GENUA['primaria'])
            ax_s.set_ylim(-5, 108)
            ax_s.spines['top'].set_visible(False)
            ax_s.spines['right'].set_visible(False)
            plt.setp(ax_s.get_xticklabels(), rotation=25, ha='right', fontsize=9)
            ax_s.legend(
                loc='upper center',
                bbox_to_anchor=(0.5, 1.18),
                ncol=4,
                frameon=False,
                fontsize=8.6
            )
            fig_sane.tight_layout()
            st.pyplot(fig_sane)

    # ------------------------------------------------------------
    # ABA 3: INTELIGÊNCIA CLÍNICA & CHECKLIST DE ALTA (GATEKEEPERS)
    # ------------------------------------------------------------
    with t_ic:
        # Card 0: Checklist Determinístico de Critérios de Progressão e Alta (Gatekeepers PBE)
        with st.container(border=True):
            secao(
                "🚦 Checklist de Critérios Objetivos para Alta Funcional (Gatekeepers PBE)",
                "A liberação para retorno ao esporte/alta exige o cumprimento simultâneo dos critérios clínicos, biomecânicos e subjetivos abaixo."
            )

            crit_dor = dor_atual <= 2
            crit_derrame = inchaco_atual <= 1
            crit_ext = "Completa" in ext_str
            crit_flex = flex_atual >= 125
            crit_lsi = (lsi_quad_num is not None and lsi_quad_num >= 90.0)
            crit_sane_pass = (sane_sessao >= 85.0 and pass_bool)

            criterios_lista = [
                ("1. Controle Álgico (EVA ≤ 2/10)", crit_dor, f"Atual: {dor_atual}/10", "Salaffi 2004"),
                ("2. Efusão Articular Controlada (Grau ≤ 1/3)", crit_derrame, f"Atual: Grau {inchaco_atual}/3", "Stroke Test PBE"),
                ("3. Extensão Terminal Completa (0°)", crit_ext, f"Atual: {ext_str}", "Shelbourne 1997"),
                ("4. Amplitude de Flexão Funcional (≥ 125°)", crit_flex, f"Atual: {flex_atual:.0f}°", "Diretriz Pós-Op Joelho"),
                ("5. Simetria de Força de Quadríceps (LSI ≥ 90%)", crit_lsi, f"Atual: {f'{lsi_quad_num:.0f}%' if lsi_quad_num is not None else 'N/D'} ({unidade_forca})", "Grindem 2016"),
                ("6. Meta Subjetiva Atingida (SANE ≥ 85% + PASS Sim)", crit_sane_pass, f"SANE: {sane_sessao:.0f}% | PASS: {'Sim' if pass_bool else 'Não'}", "Shelbourne 2009 / Tubach 2005"),
            ]

            total_cumpridos = sum(1 for _, ok, _, _ in criterios_lista if ok)
            pct_gatekeeper = (total_cumpridos / len(criterios_lista)) * 100.0

            st.markdown(f"**📊 Score de Critérios de Alta Cumpridos: {total_cumpridos}/{len(criterios_lista)} ({pct_gatekeeper:.0f}%)**")
            st.progress(pct_gatekeeper / 100.0)

            cg1, cg2 = st.columns(2)
            for idx_c, (nome_c, ok_c, valor_c, ref_c) in enumerate(criterios_lista):
                icone_c = "✅" if ok_c else "❌"
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

        # Camada 1: Motor de IA Baseado em Evidência (MCID, LSI, GROC/PASS/SANE, Bandeiras)
        with st.container(border=True):
            try:
                with st.spinner("🧠 Executando análise clínica baseada em evidência..."):
                    insights = analisar_paciente(st.session_state.paciente)
                renderizar_insights(insights, CORES_GENUA)
            except Exception as e:
                toast(f"Erro ao gerar insights: {e}", "error")
                st.caption("Verifique se o paciente possui avaliação inicial e sessões de check-in registradas.")

        # Camada 2: Síntese de Modulação de Carga da Sessão Selecionada
        with st.container(border=True):
            secao(
                "🔬 Diretriz de Conduta Imediata (Sessão Selecionada)",
                "Síntese algorítmica cruzando derrame articular, resposta a carga excêntrica/elástica e mobilidade."
            )
            st.markdown(f"- **Classificação Funcional da Sessão ({sessao_escolhida}):** {fenotipo_sessao}")
            st.markdown(f"- **Conduta Recomendada (PBE):** {diretriz}")

    # ============================================================
    # 5. CARD DE EXPORTAÇÃO DO LAUDO VISUAL (CLEAN LIGHT GENUA)
    # ============================================================
    with st.container(border=True):
        secao(
            "📄 Exportação de Laudo de Evolução Clínica (Clean Light GENUA)",
            "Gera o relatório executivo para médico e paciente com Resumo Semafórico, Velocímetro de ADM, Força Bilateral e Conclusões Interativas Editáveis."
        )

        opcoes_prom_laudo = ["LEFS", "VISA-P", "Lysholm", "WOMAC", "KOOS", "IKDC"]
        default_prom_laudo = _detectar_prom_preenchido(av_p, fen_info.get("prom_principal", "LEFS"))

        c_cfg1, c_cfg2 = st.columns([1.4, 1.6], gap="large")
        with c_cfg1:
            medico_laudo = st.text_input(
                "👨‍⚕️ Médico Assistente / Quem Indicou",
                value=av_p.get("Medico_Indicador", medico_cad) if tem_av else medico_cad,
                placeholder="Ex: Dr. Felipe (CRM) / Indicação Clínica",
                key="input_medico_laudo"
            )
        with c_cfg2:
            prom_selecionado = st.multiselect(
                "📋 Questionário(s) Aplicado(s) para Exibir no Laudo",
                options=opcoes_prom_laudo,
                default=default_prom_laudo,
                help="Apenas o questionário selecionado aqui aparecerá no PDF (evita exibir questionários não aplicados)."
            )

        conclusao_livre_fisio = st.text_area(
            "✍️ Conclusão Final e Recomendações ao Médico / Paciente (Opcional — Também editável direto no Laudo)",
            value="",
            placeholder="Digite aqui o parecer final e recomendações de conduta, ou edite diretamente nos boxes interativos do laudo abaixo antes de imprimir...",
            height=80,
            key="input_conclusao_livre_laudo"
        )

        if st.button("⚙️ GERAR LAUDO EXECUTIVO INTERATIVO", width='stretch', type="primary"):
            with st.spinner("🧠 Compilando laudo clínico Clean Light com conclusões automáticas editáveis..."):
                try:
                    import streamlit.components.v1 as components
                    from pdf_laudo import gerar_laudo_html
                    from ia_clinica import analisar_paciente as _analisar, normalizar_diagnostico as _normalizar

                    dados_aval = dict(av_p) if tem_av else {}
                    dados_aval["Medico_Indicador"] = medico_laudo.strip() or "—"
                    dados_aval["Ocupacao_Esporte"] = ocupacao_p
                    dados_aval["Idade_Cadastro"] = idade_p
                    dados_aval["Diagnostico_Cadastro"] = dx_clinico_base
                    dados_aval["PROMs_Selecionados"] = prom_selecionado
                    dados_aval["Conclusao_Final_Fisio"] = conclusao_livre_fisio.strip()

                    historico = df_p.to_dict("records")

                    insights_l = _analisar(st.session_state.paciente)
                    fenotipo_l = _normalizar(dados_aval.get('Diagnostico_Clinico', '') if dados_aval.get('Diagnostico_Clinico') else texto_fenotipo_busca)

                    laudo_html = gerar_laudo_html(
                        paciente_nome=st.session_state.paciente,
                        dados_aval=dados_aval,
                        historico=historico,
                        insights=insights_l,
                        fenotipo=fenotipo_l
                    )

                    st.download_button(
                        label="📥 BAIXAR LAUDO (HTML / PDF) — Abrir ou usar o botão 'Imprimir / PDF' abaixo",
                        data=laudo_html.encode('utf-8'),
                        file_name=f"Laudo_GENUA_{st.session_state.paciente.replace(' ', '_')}.html",
                        mime="text/html",
                        type="primary",
                        width='stretch'
                    )
                    toast("Laudo gerado! Clique em qualquer 'Conclusão' dentro da pré-visualização abaixo para editar o texto ao vivo antes de salvar em PDF.", "success")
                    components.html(laudo_html, height=1450, scrolling=True)

                except Exception as e:
                    toast(f"Erro ao gerar o laudo: {e}", "error")
                    st.caption("Verifique se o paciente possui avaliação inicial e sessões de check-in registradas.")
