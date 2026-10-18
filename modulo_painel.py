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
    respeitando primeiro a lista explícita `PROMs_Aplicados` e usando fallback contra defaults antigos.
    """
    if not av_p:
        return []

    if isinstance(av_p.get("PROMs_Aplicados"), list):
        return [p for p in av_p["PROMs_Aplicados"] if p]

    lefs_v = float(av_p.get("LEFS_Pct", 0) or 0)
    visap_v = float(av_p.get("VISA_P_Pts", 0) or 0)
    lysh_v = float(av_p.get("Lysholm_Pts", 0) or 0)
    womac_v = float(av_p.get("WOMAC_Pct", 0) or 0)
    koos_v = float(av_p.get("KOOS_Pct", 0) or 0)
    ikdc_v = float(av_p.get("IKDC_Pct", 0) or 0)

    candidatos = []
    if lefs_v > 0:
        candidatos.append("LEFS")
    if visap_v > 0 and visap_v != 50.0:
        candidatos.append("VISA-P")
    if lysh_v > 0 and lysh_v != 100.0:
        candidatos.append("Lysholm")
    if womac_v > 0 and round(womac_v, 1) != 100.0:
        candidatos.append("WOMAC")
    if koos_v > 0 and round(koos_v, 1) != 100.0:
        candidatos.append("KOOS")
    if ikdc_v > 0 and round(ikdc_v, 1) != 75.0:
        candidatos.append("IKDC")

    if candidatos:
        mapa_fen = {"VISA_P": "VISA-P", "Lysholm": "Lysholm", "WOMAC": "WOMAC", "KOOS": "KOOS", "IKDC": "IKDC", "LEFS": "LEFS"}
        alvo_fen = mapa_fen.get(prom_fenotipo, "LEFS")
        if alvo_fen in candidatos:
            return [alvo_fen]
        return [candidatos[0]]

    return ["LEFS"] if lefs_v > 0 else []


def render():
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

    red_flags_str = str(av_p.get('Red_Flags', 'Nenhuma') or 'Nenhuma')
    yellow_flags_str = str(av_p.get('Yellow_Cog', av_p.get('Yellow_Flags', 'Nenhum')) or 'Nenhum')
    blue_flags_str = str(av_p.get('Fatores_Sociais', 'Nenhum') or 'Nenhum')

    # CORREÇÃO PBE: Força Muscular para cálculo de LSI vinculada EXCLUSIVAMENTE à Dinamometria (kgf).
    # Escala de Oxford (0-5) fica restrita à visualização qualitativa na ficha da Avaliação Inicial.
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
                "Direito": f"{vd:.1f} kgf",
                "Esquerdo": f"{ve:.1f} kgf",
                "val_d": vd,
                "val_e": ve,
                "LSI (%)": f"{cor_m} {lsi_m:.0f}%" if lsi_m is not None else "⚪ N/D",
                "lsi_num": lsi_m
            })
        else:
            dados_forca_bilateral.append({
                "Grupo Muscular": label_m,
                "Direito": "Não medido",
                "Esquerdo": "Não medido",
                "val_d": 0.0,
                "val_e": 0.0,
                "LSI (%)": "⚪ Sem Dinamometria",
                "lsi_num": None
            })

    lsi_quad_num = dados_forca_bilateral[0]["lsi_num"]
    cor_lsi_quad = dados_forca_bilateral[0]["LSI (%)"].split()[0] if lsi_quad_num is not None else "⚪"

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

    tem_red_flag = red_flags_str.lower() not
