"""
GENUA | Gerador de Laudo Clínico Executivo (Clean Light GENUA + Interativo Editável)
====================================================================================
Exporta:
 - gerar_laudo_html(): Laudo executivo Clean Light nas cores oficiais GENUA (#103E55 / #2E8B9A)
   com Resumo Executivo Semafórico Dinâmico, Gráficos Clean em 300 DPI (últimas 10 sessões com Data/S#),
   Velocímetro SVG de ADM, Renderização Condicional Estrita (só exibe o que foi preenchido),
   Força Muscular vinculada EXCLUSIVAMENTE à Dinamometria (kgf) com LSI + Razão I:Q,
   Objetivos centrados em SANE & GROC (-7 a +7) sem PSFS, Checklist dos 6 Pontos de Alta (Gatekeepers PBE)
   e Conclusões Automáticas PBE 100% Editáveis ao clique (contenteditable) antes de imprimir.
 - gerar_laudo(): Gerador em bytes via FPDF2 para retrocompatibilidade.

Dependências: fpdf2, matplotlib, numpy, io, os, base64, datetime
"""
import io
import os
import base64
import html
import math
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF


# ============================================================
# PALETA DE CORES OFICIAL GENUA (CLEAN LIGHT CLINICAL DESIGN)
# ============================================================
AZUL_PROFUNDO = (10, 37, 64)
AZUL_GENUA = (16, 62, 85)       # #103E55 (Primária GENUA)
TEAL_GENUA = (46, 139, 154)     # #2E8B9A (Secundária GENUA)
TEAL_VIVO = (0, 180, 197)
CINZA_GELO = (245, 245, 247)
VERDE_VIVO = (22, 163, 74)      # #16A34A
VERMELHO_VIVO = (220, 38, 38)   # #DC2626
AMBAR_VIVO = (217, 119, 6)      # #D97706
INDIGO_VIVO = (99, 102, 241)
PRETO_TEXTO = (29, 29, 31)
CINZA_TEXTO = (100, 116, 139)
CINZA_BORDA = (226, 232, 240)
BRANCO = (255, 255, 255)


# ============================================================
# HELPERS DE SEGURANÇA, CONVERSÃO E PARSERS
# ============================================================
def _safe_float(valor, padrao=0.0):
    """Converte qualquer entrada para float de forma segura."""
    if valor is None or valor == "" or valor == "-":
        return padrao
    try:
        s = str(valor).replace(",", ".").replace("%", "").replace("°", "").replace("cm", "").strip()
        return float(s)
    except (ValueError, TypeError):
        return padrao


def _tem_valor_util(valor) -> bool:
    """Verifica se um campo textual ou numérico foi efetivamente preenchido pelo clínico."""
    if valor is None:
        return False
    s = str(valor).strip().lower()
    termos_vazios = {
        "", "—", "-", "não relatado", "nao relatado", "não especificado",
        "nao especificado", "não informado", "nao informado", "nenhum",
        "nenhuma", "n/a", "none", "nan"
    }
    return s not in termos_vazios


def _limpar_texto(texto):
    """Sanitiza caracteres para FPDF (latin-1)."""
    if texto is None:
        return ""
    s = str(texto)
    try:
        return s.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return s.encode('ascii', 'replace').decode('ascii')


def _esc(texto):
    """Escapa strings para renderização segura em HTML."""
    if texto is None or str(texto).strip() == "":
        return "—"
    return html.escape(str(texto))


def _carregar_logo_b64():
    """Tenta carregar a logo oficial da Genua em Base64 para o cabeçalho do PDF."""
    caminhos = ["logo_genua_novo_v2.png", "logo_genua.png"]
    for c in caminhos:
        if os.path.exists(c):
            try:
                with open(c, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass
    return None


def _extrair_chave_str(texto_bruto, prefixo: str, default: float = 0.0) -> float:
    """Extrai float de strings como 'Ext:35.0 Flex:20.0' ou 'Dir:125.0 Esq:135.0'."""
    if texto_bruto is None or texto_bruto == "":
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


def _extrair_def_extensao_graus(val_ext) -> float:
    """Converte string ou número de extensão ('Completa (0°)', 'Déficit de -5°', etc.) em graus numéricos."""
    if val_ext is None or val_ext == "":
        return 0.0
    if isinstance(val_ext, (int, float)):
        return abs(float(val_ext))
    s = str(val_ext).lower()
    if "10" in s:
        return 10.0
    if "5" in s:
        return 5.0
    if "completa" in s or "0" in s:
        return 0.0
    return abs(_safe_float(s, 0.0))


def _mapear_inchaco_grau(val) -> int:
    """Converte o texto de inchaço/derrame ('Nenhum', 'Leve (+)', etc.) para escala numérica 0 a 3."""
    if val is None or val == "":
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


def _mapa_func_dor_equivalente(resultado_texto, dor_num_override=None):
    """
    Mapeia a resposta do teste funcional para escala de dificuldade/dor (0 a 10),
    priorizando o valor exato da barra deslizante de dor (0 a 10) quando disponível.
    """
    if dor_num_override is not None and str(dor_num_override).strip() != "":
        try:
            return float(max(0.0, min(10.0, float(dor_num_override))))
        except Exception:
            pass
    if resultado_texto is None:
        return None
    if isinstance(resultado_texto, (int, float)):
        return float(max(0.0, min(10.0, float(resultado_texto))))
    s = str(resultado_texto).strip()
    mapa = {
        "Sem Dor (0)": 0.0, "Sem Dor": 0.0,
        "Dor Leve (1 - 3)": 2.0, "Dor Leve": 2.0,
        "Dor Moderada (4 - 7)": 5.5, "Dor Moderada": 5.5,
        "Dor Grave (8 - 10)": 8.5, "Dor Grave": 8.5,
        "Incapaz (Não realiza)": 10.0, "Incapaz (Nao realiza)": 10.0, "Incapaz": 10.0,
    }
    return mapa.get(s)


def _normalizar_entradas(dados_aval, historico):
    """Garante que dados_aval seja dict e historico seja list[dict] ordenada cronologicamente."""
    if hasattr(dados_aval, 'to_dict'):
        records = dados_aval.to_dict('records')
        dados_aval = records[-1] if records else {}
    elif isinstance(dados_aval, list):
        dados_aval = dados_aval[-1] if dados_aval else {}
    elif not isinstance(dados_aval, dict):
        dados_aval = {}

    if hasattr(historico, 'to_dict'):
        historico = historico.to_dict('records')
    elif not isinstance(historico, list):
        historico = []

    hist_limpo = [h for h in historico if isinstance(h, dict)]
    hist_ord = sorted(hist_limpo, key=lambda x: str(x.get('Data', '')))
    return dados_aval, hist_ord


def _fig_to_base64(fig, dpi=300, facecolor='#FFFFFF'):
    """Converte figura Matplotlib em string Base64 PNG a 300 DPI."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor=facecolor)
    buf.seek(0)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def _formatar_data_curta(data_raw) -> str:
    """Formata string de data YYYY-MM-DD ou DD/MM/YYYY para DD/MM."""
    if not data_raw:
        return ""
    s = str(data_raw).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m")
        except Exception:
            pass
    return s[:5]


def _selecionar_ultimas_sessoes(hist: list, max_sessoes: int = 10) -> list:
    """
    Seleciona até as últimas `max_sessoes` (padrão: 10 sessões) mantendo a numeração real
    da sessão (S1, S2... Sn) e a data curta (DD/MM) para os gráficos longitudinais.
    """
    n = len(hist)
    if n == 0:
        return []
    inicio = max(0, n - max_sessoes)
    selecionadas = []
    for idx in range(inicio, n):
        ev = hist[idx]
        dt_curta = _formatar_data_curta(ev.get("Data", ""))
        label_grafico = f"S{idx + 1}\n{dt_curta}" if dt_curta else f"S{idx + 1}"
        label_card = f"S{idx + 1} ({dt_curta})" if dt_curta else f"S{idx + 1}"
        selecionadas.append((label_grafico, ev, label_card))
    return selecionadas


# ============================================================
# GERADORES DE GRÁFICOS CLEAN LIGHT GENUA (ATÉ 10 SESSÕES)
# ============================================================
def _gerar_grafico_dor_clean_b64(hist):
    """Gera gráfico Clean Light de evolução da dor (EVA) para até 10 sessões com Data/S#."""
    marcos = _selecionar_ultimas_sessoes(hist, max_sessoes=10)
    if not marcos:
        return ""
    labels = [m[0] for m in marcos]
    evs = [m[1] for m in marcos]
    x_idx = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(9.0, 2.8))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    tem_bilateral = any(bool(e.get('Registro_Bilateral')) for e in evs)

    if tem_bilateral:
        dores_d = [_safe_float(e.get('Dor_Dir', e.get('Dor', 0))) for e in evs]
        dores_e = [_safe_float(e.get('Dor_Esq', e.get('Dor', 0))) for e in evs]
        ax.plot(x_idx, dores_d, color='#103E55', lw=2.5, marker='o', markersize=6.5, label='EVA Joelho D', zorder=4)
        ax.plot(x_idx, dores_e, color='#16A34A', lw=2.5, marker='o', markersize=6.5, label='EVA Joelho E', zorder=4)
        for i in range(len(x_idx)):
            ax.annotate(f"{dores_d[i]:.1f}".replace(".", ","), (x_idx[i], dores_d[i]),
                        textcoords="offset points", xytext=(-8, -13), ha='center',
                        fontsize=8, fontweight='bold', color='#103E55')
            ax.annotate(f"{dores_e[i]:.1f}".replace(".", ","), (x_idx[i], dores_e[i]),
                        textcoords="offset points", xytext=(8, 7), ha='center',
                        fontsize=8, fontweight='bold', color='#16A34A')
        ax.legend(loc='upper right', frameon=False, fontsize=8.5, ncol=2)
    else:
        dores = [_safe_float(e.get('Dor', 0)) for e in evs]
        ax.fill_between(x_idx, dores, color='#2E8B9A', alpha=0.08)
        ax.plot(x_idx, dores, color='#103E55', lw=2.6, marker='o', markersize=7.0,
                markerfacecolor='#FFFFFF', markeredgecolor='#103E55', markeredgewidth=2.1,
                label='Dor (EVA 0–10)', zorder=4)
        for i, v in enumerate(dores):
            ax.annotate(f"{v:.1f}".replace(".", ","), (x_idx[i], v),
                        textcoords="offset points", xytext=(0, 8), ha='center',
                        fontsize=8.5, fontweight='bold', color='#103E55')

    ax.set_xticks(x_idx)
    ax.set_xticklabels(labels, fontsize=8.5, fontweight='bold', color='#475569')
    ax.set_yticks([0, 5, 10])
    ax.set_yticklabels(['0', '5', '10'], fontsize=9, color='#64748B')
    ax.set_ylim(-1.0, 11.5)
    ax.set_xlim(-0.35, max(1, len(labels) - 1) + 0.35)
    ax.grid(True, axis='y', linestyle='-', color='#E2E8F0', linewidth=0.9)
    ax.grid(False, axis='x')

    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#CBD5E1')
    ax.tick_params(axis='both', length=0)

    fig.tight_layout()
    return _fig_to_base64(fig, dpi=300, facecolor='#FFFFFF')


def _gerar_grafico_testes_clean_b64(hist):
    """
    Gera gráfico Clean Light de evolução dos Testes Funcionais Específicos (até 10 sessões)
    suportando a barra deslizante de dor (0 a 10) e retorna:
    (b64_img, lista_conclusoes_testes, qtd_testes_melhoraram, total_testes_validos).
    """
    marcos = _selecionar_ultimas_sessoes(hist, max_sessoes=10)
    if not marcos:
        return "", [], 0, 0

    labels = [m[0] for m in marcos]
    evs = [m[1] for m in marcos]
    x_idx = np.arange(len(labels))

    nomes_testes = []
    for e in evs:
        tf = e.get('Testes_Funcionais', {})
        tf_num = e.get('Testes_Funcionais_Dor_Num', {})
        if isinstance(tf, dict):
            for k, val_resp in tf.items():
                dor_num_k = tf_num.get(k) if isinstance(tf_num, dict) else None
                if _mapa_func_dor_equivalente(val_resp, dor_num_k) is not None and k not in nomes_testes:
                    nomes_testes.append(k)

    if not nomes_testes:
        return "", [], 0, 0

    cores_linhas = ['#103E55', '#16A34A', '#D97706', '#2E8B9A', '#6366F1']
    fig, ax = plt.subplots(figsize=(9.0, 2.9))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    conclusoes_testes = []
    melhoraram = 0
    testes_plotados = 0

    for idx_t, t_nome in enumerate(nomes_testes[:4]):
        cor_t = cores_linhas[idx_t % len(cores_linhas)]
        valores_y = []
        textos_raw = []
        for e in evs:
            tf = e.get('Testes_Funcionais', {})
            tf_num = e.get('Testes_Funcionais_Dor_Num', {})
            resp = tf.get(t_nome) if isinstance(tf, dict) else None
            dor_num_k = tf_num.get(t_nome) if isinstance(tf_num, dict) else None
            sc_dor = _mapa_func_dor_equivalente(resp, dor_num_k)
            valores_y.append(sc_dor if sc_dor is not None else np.nan)
            if dor_num_k is not None and "Incapaz" not in str(resp):
                textos_raw.append(f"Dor {int(float(dor_num_k))}/10")
            else:
                textos_raw.append(resp)

        arr_y = np.array(valores_y, dtype=float)
        mask = ~np.isnan(arr_y)
        if mask.sum() >= 1:
            testes_plotados += 1
            ax.plot(x_idx[mask], arr_y[mask], color=cor_t, lw=2.4, marker='o', markersize=6.5, label=t_nome, zorder=3 + idx_t)
            for xi, yi in zip(x_idx[mask], arr_y[mask]):
                ax.annotate(f"{yi:.1f}".replace(".", ","), (xi, yi),
                            textcoords="offset points", xytext=(0, 7), ha='center',
                            fontsize=8, fontweight='bold', color=cor_t)

            v_ini = arr_y[mask][0]
            v_fim = arr_y[mask][-1]
            r_ini_str = textos_raw[int(np.where(mask)[0][0])] or "—"
            r_fim_str = textos_raw[int(np.where(mask)[0][-1])] or "—"

            if v_fim < v_ini:
                melhoraram += 1
                pct_red = ((v_ini - v_fim) / max(1.0, v_ini)) * 100.0
                conclusoes_testes.append((
                    "verde",
                    f"Melhora clínica significativa de {pct_red:.0f}% na tolerância ao movimento {t_nome} ({r_ini_str} → {r_fim_str}, dor {v_ini:.1f} → {v_fim:.1f})."
                ))
            elif v_fim == v_ini:
                if v_fim == 0:
                    melhoraram += 1
                    conclusoes_testes.append((
                        "verde",
                        f"Movimento {t_nome} realizado com capacidade plena e sem dor ({r_fim_str}) ao longo do período."
                    ))
                else:
                    conclusoes_testes.append((
                        "neutro",
                        f"Movimento {t_nome} estável no período (dor {v_ini:.1f} → {v_fim:.1f} · {r_fim_str})."
                    ))
            else:
                conclusoes_testes.append((
                    "laranja",
                    f"Oscilação de sensibilidade mecânica no movimento {t_nome} ({v_ini:.1f} → {v_fim:.1f} · {r_fim_str}). Ajustar controle de carga."
                ))

    if testes_plotados == 0:
        plt.close(fig)
        return "", [], 0, 0

    ax.set_xticks(x_idx)
    ax.set_xticklabels(labels, fontsize=8.5, fontweight='bold', color='#475569')
    ax.set_yticks([0, 5, 10])
    ax.set_yticklabels(['0', '5', '10'], fontsize=9, color='#64748B')
    ax.set_ylim(-1.0, 11.8)
    ax.set_xlim(-0.35, max(1, len(labels) - 1) + 0.35)
    ax.grid(True, axis='y', linestyle='-', color='#E2E8F0', linewidth=0.9)
    ax.grid(False, axis='x')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=min(4, testes_plotados), frameon=False, fontsize=8.2)

    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#CBD5E1')
    ax.tick_params(axis='both', length=0)

    fig.tight_layout()
    return _fig_to_base64(fig, dpi=300, facecolor='#FFFFFF'), conclusoes_testes, melhoraram, testes_plotados


def _gerar_grafico_sane_clean_b64(hist, sane_base: float):
    """Gera gráfico Clean Light da evolução do Objetivo do Paciente (SANE %) para até 10 sessões."""
    marcos = _selecionar_ultimas_sessoes(hist, max_sessoes=10)
    if marcos:
        labels = [m[0] for m in marcos]
        valores = [_safe_float(m[1].get('SANE_Pct'), sane_base) for m in marcos]
        if len(hist) <= 10 and len(valores) >= 1 and marcos[0][1].get('SANE_Pct') is None:
            valores[0] = sane_base
    else:
        labels = ["Aval."]
        valores = [sane_base]

    x_idx = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(8.8, 2.4))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    ax.axhline(y=85, color='#16A34A', linestyle='--', lw=1.2, alpha=0.7, label='Meta Alta Subjetiva (85%)')
    ax.fill_between(x_idx, valores, color='#2E8B9A', alpha=0.12)
    ax.plot(x_idx, valores, color='#103E55', lw=2.5, marker='o', markersize=6.5, zorder=4, label='Capacidade Percebida (SANE %)')
    for i, v in enumerate(valores):
        ax.annotate(f"{v:.0f}%", (x_idx[i], v), textcoords="offset points",
                    xytext=(0, 7), ha='center', fontsize=8, fontweight='bold', color='#103E55')

    ax.set_xticks(x_idx)
    ax.set_xticklabels(labels, fontsize=8.5, fontweight='bold', color='#475569')
    ax.set_yticks([0, 50, 85, 100])
    ax.set_yticklabels(['0%', '50%', '85%', '100%'], fontsize=8, color='#64748B')
    ax.set_ylim(-6, 116)
    ax.set_xlim(-0.35, max(1, len(labels) - 1) + 0.35)
    ax.grid(True, axis='y', linestyle='-', color='#E2E8F0', linewidth=0.8)
    ax.grid(False, axis='x')
    ax.legend(loc='upper left', frameon=False, fontsize=8)
    for s in ['top', 'right', 'left']:
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#CBD5E1')
    ax.tick_params(axis='both', length=0)

    fig.tight_layout()
    return _fig_to_base64(fig, dpi=300, facecolor='#FFFFFF')


# ============================================================
# COMPONENTES VISUAIS SVG (GAUGE DE FLEXÃO + DONUT DE EXTENSÃO)
# ============================================================
def _construir_svg_gauge_flexao(flex_atual: float, flex_ref: float = 135.0) -> str:
    """Constrói o Velocímetro Semicircular (Gauge SVG) da Flexão de Joelho."""
    pct = max(0.0, min(1.0, flex_atual / flex_ref)) if flex_ref > 0 else 0.0
    pct_exib = round((flex_atual / flex_ref) * 100.0) if flex_ref > 0 else 0

    raio = 80.0
    perimetro = math.pi * raio
    dash_offset = perimetro * (1.0 - pct)

    ang = pct * math.pi
    cx_dot = 100.0 - raio * math.cos(ang)
    cy_dot = 100.0 - raio * math.sin(ang)

    cor_arco = "#16A34A" if flex_atual >= 125 else ("#2E8B9A" if flex_atual >= 105 else ("#D97706" if flex_atual >= 80 else "#DC2626"))

    return f"""
    <div style="text-align:center; padding: 6px 0 2px 0;">
        <svg viewBox="0 0 200 122" style="width:100%; max-width:250px; height:auto; overflow:visible;">
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#E2E8F0" stroke-width="14" stroke-linecap="round"/>
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="{cor_arco}" stroke-width="14" stroke-linecap="round"
                  stroke-dasharray="{perimetro:.2f}" stroke-dashoffset="{dash_offset:.2f}"/>
            <circle cx="{cx_dot:.2f}" cy="{cy_dot:.2f}" r="7.5" fill="{cor_arco}" stroke="#FFFFFF" stroke-width="2.5"/>
            <text x="100" y="78" text-anchor="middle" font-size="30" font-weight="800" fill="#103E55" font-family="Inter, sans-serif">{flex_atual:.0f}°</text>
            <text x="100" y="96" text-anchor="middle" font-size="10.5" font-weight="700" fill="#2E8B9A" font-family="Inter, sans-serif">{pct_exib}% da referência</text>
            <text x="20" y="118" text-anchor="middle" font-size="10.5" font-weight="800" fill="#475569" font-family="Inter, sans-serif">0°</text>
            <text x="180" y="114" text-anchor="middle" font-size="10.5" font-weight="800" fill="#103E55" font-family="Inter, sans-serif">{flex_ref:.0f}°</text>
            <text x="180" y="124" text-anchor="middle" font-size="7.5" font-weight="700" fill="#2E8B9A" font-family="Inter, sans-serif">REFERÊNCIA</text>
        </svg>
    </div>
    """


def _construir_svg_donut_extensao(def_ext_atual: float) -> str:
    """Constrói o anel circular (Donut SVG) de Extensão Terminal de Joelho (Meta 0°)."""
    cor_anel = "#16A34A" if def_ext_atual == 0 else ("#D97706" if def_ext_atual <= 5 else "#DC2626")
    txt_sub = "Completa (0°)" if def_ext_atual == 0 else f"Déficit de {def_ext_atual:.0f}°"
    return f"""
    <svg viewBox="0 0 110 110" style="width:105px; height:105px; flex-shrink:0;">
        <circle cx="55" cy="55" r="44" fill="none" stroke="#E2E8F0" stroke-width="9"/>
        <circle cx="55" cy="55" r="44" fill="none" stroke="{cor_anel}" stroke-width="9"
                stroke-dasharray="276.46" stroke-dashoffset="{0 if def_ext_atual == 0 else 75}"/>
        <text x="55" y="54" text-anchor="middle" font-size="22" font-weight="800" fill="#103E55" font-family="Inter, sans-serif">{def_ext_atual:.0f}°</text>
        <text x="55" y="70" text-anchor="middle" font-size="8.5" font-weight="700" fill="{cor_anel}" font-family="Inter, sans-serif">{txt_sub}</text>
    </svg>
    """


def _box_conclusao_editavel(cor_status: str, texto_conclusao: str) -> str:
    """Renderiza a pílula/box de Conclusão com borda semafórica e atributo contenteditable='true'."""
    mapa_cores = {
        "verde":    {"borda": "#16A34A", "bg": "#F0FDF4", "dot": "#16A34A"},
        "amarelo":  {"borda": "#EAB308", "bg": "#FEFCE8", "dot": "#EAB308"},
        "laranja":  {"borda": "#F97316", "bg": "#FFF7ED", "dot": "#F97316"},
        "vermelho": {"borda": "#DC2626", "bg": "#FEF2F2", "dot": "#DC2626"},
        "neutro":   {"borda": "#94A3B8", "bg": "#F8FAFC", "dot": "#64748B"},
    }
    c = mapa_cores.get(cor_status, mapa_cores["verde"])
    return f"""
    <div class="conclusion-box" style="border-left-color: {c['borda']}; background: {c['bg']};">
        <div class="conclusion-content" contenteditable="true" spellcheck="false">
            <span class="status-dot" style="background: {c['dot']};"></span>
            <strong>Conclusão:</strong> {_esc(texto_conclusao)}
        </div>
        <span class="edit-badge no-print" title="Clique no texto ao lado para editar livremente">EDITAR</span>
    </div>
    """


# ============================================================
# FUNÇÃO PRINCIPAL: gerar_laudo_html() — CLEAN LIGHT GENUA
# ============================================================
def gerar_laudo_html(paciente_nome, dados_aval=None, historico=None, insights=None, fenotipo=None, *args, **kwargs):
    """
    Gera o Laudo de Evolução Clínica no padrão Clean Light GENUA:
    - Gráficos com até 10 sessões rotuladas com S# e Data (DD/MM).
    - Força Muscular vinculada EXCLUSIVAMENTE à Dinamometria (kgf) com LSI e Razão I:Q.
    - Objetivos centrados em SANE (0-100%) e GROC (-7 a +7), sem PSFS.
    - Checklist dos 6 Pontos de Objetivo para Atingir (Gatekeepers PBE de Alta Funcional).
    """
    dados_aval, hist = _normalizar_entradas(dados_aval, historico)
    n_sessoes = len(hist)
    ultimas_10 = _selecionar_ultimas_sessoes(hist, max_sessoes=10)

    # --- 1. METADADOS DO CABEÇALHO ---
    dx_raw = dados_aval.get('Diagnostico_Clinico') or dados_aval.get('Diagnostico_Cadastro')
    idade_raw = dados_aval.get('Idade') or dados_aval.get('Idade_Cadastro')
    ocupacao_raw = dados_aval.get('Ocupacao_Esporte') or dados_aval.get('Ocupacao')
    lado_acom = dados_aval.get('Lado_Acometido') or 'Joelho'
    medico_raw = dados_aval.get('Medico_Indicador')
    data_emissao = datetime.now().strftime("%d/%m/%Y")

    if n_sessoes >= 2:
        d_ini = _formatar_data_curta(hist[0].get('Data', '')) or str(hist[0].get('Data', ''))[:10]
        d_fim = _formatar_data_curta(hist[-1].get('Data', '')) or str(hist[-1].get('Data', ''))[:10]
        try:
            d_ini = datetime.strptime(str(hist[0].get('Data', ''))[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            d_fim = datetime.strptime(str(hist[-1].get('Data', ''))[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass
        periodo_avaliado = f"{d_ini} a {d_fim} ({n_sessoes} sessões)"
    elif n_sessoes == 1:
        periodo_avaliado = f"1 sessão registrada ({_formatar_data_curta(hist[0].get('Data', ''))})"
    else:
        periodo_avaliado = dados_aval.get("Data_Avaliacao", data_emissao)

    paciente_label = f"{paciente_nome} ({idade_raw} anos)" if _tem_valor_util(idade_raw) else str(paciente_nome)
    meta_items_html = f"""
        <div class="meta-item">
            <span class="meta-lbl">Paciente</span>
            <span class="meta-val" contenteditable="true">{_esc(paciente_label)}</span>
        </div>
    """
    if _tem_valor_util(dx_raw):
        meta_items_html += f"""
        <div class="meta-item">
            <span class="meta-lbl">Diagnóstico Clínico</span>
            <span class="meta-val" contenteditable="true">{_esc(dx_raw)}</span>
        </div>
        """
    if _tem_valor_util(medico_raw):
        meta_items_html += f"""
        <div class="meta-item">
            <span class="meta-lbl">Indicação</span>
            <span class="meta-val" contenteditable="true">{_esc(medico_raw)}</span>
        </div>
        """
    meta_items_html += f"""
        <div class="meta-item">
            <span class="meta-lbl">Data do Relatório</span>
            <span class="meta-val" contenteditable="true">{_esc(data_emissao)}</span>
        </div>
        <div class="meta-item">
            <span class="meta-lbl">Jornada / Membro</span>
            <span class="meta-val" contenteditable="true">Joelho ({_esc(lado_acom)})</span>
        </div>
    """
    if _tem_valor_util(ocupacao_raw):
        meta_items_html += f"""
        <div class="meta-item">
            <span class="meta-lbl">Esporte / Atividade</span>
            <span class="meta-val" contenteditable="true">{_esc(ocupacao_raw)}</span>
        </div>
        """
    meta_items_html += f"""
        <div class="meta-item" style="grid-column: span 2;">
            <span class="meta-lbl">Período Avaliado</span>
            <span class="meta-val" contenteditable="true">{_esc(periodo_avaliado)}</span>
        </div>
    """

    exec_pills_list = []

    # --- 2. EVOLUÇÃO DA DOR (EVA) ---
    tem_dor_preenchida = any(h.get('Dor') is not None for h in hist)
    html_secao_dor = ""
    dor_atual = 0.0

    if tem_dor_preenchida and n_sessoes >= 1:
        dor_inicial = _safe_float(hist[0].get('Dor', 0))
        dor_atual = _safe_float(hist[-1].get('Dor', 0))
        delta_dor = dor_inicial - dor_atual
        pct_dor = ((delta_dor / dor_inicial) * 100.0) if dor_inicial > 0 else 0.0

        if delta_dor > 0:
            cor_kpi_dor = "#16A34A" if (delta_dor >= 2 or dor_atual <= 2) else "#D97706"
            icone_kpi_dor = "↓"
            txt_kpi_dor = f"↓ {pct_dor:.0f}%" if dor_inicial > 0 else f"↓ {delta_dor:.0f} pts"
            sub_kpi_dor = f"({dor_inicial:.1f} → {dor_atual:.1f})".replace(".", ",")
            status_conc_dor = "verde" if (delta_dor >= 2 or dor_atual <= 2) else "amarelo"
            conc_dor_txt = (
                f"Redução clinicamente significativa da dor em {pct_dor:.0f}% ({dor_inicial:.1f} → {dor_atual:.1f} na escala EVA), "
                f"indicando excelente modulação inflamatória/álgica e aumento da tolerância à carga mecânica."
            ).replace(".", ",")
        elif delta_dor == 0:
            cor_kpi_dor = "#16A34A" if dor_atual <= 2 else "#D97706"
            icone_kpi_dor = "="
            txt_kpi_dor = "Estável"
            sub_kpi_dor = f"({dor_inicial:.1f} → {dor_atual:.1f})".replace(".", ",")
            status_conc_dor = "verde" if dor_atual <= 2 else "amarelo"
            conc_dor_txt = (
                f"Quadro álgico mantido em nível controlado ({dor_atual:.1f}/10 na EVA) durante a progressão de demanda funcional."
                if dor_atual <= 2 else
                f"Estabilidade álgica ({dor_inicial:.1f} → {dor_atual:.1f} na EVA). Mantido controle de carga conforme irritabilidade tecidual."
            ).replace(".", ",")
        else:
            cor_kpi_dor = "#DC2626"
            icone_kpi_dor = "↑"
            txt_kpi_dor = f"+{abs(delta_dor):.0f} pts"
            sub_kpi_dor = f"({dor_inicial:.1f} → {dor_atual:.1f})".replace(".", ",")
            status_conc_dor = "laranja"
            conc_dor_txt = (
                f"Oscilação reativa da dor ({dor_inicial:.1f} → {dor_atual:.1f} na EVA). Ajustado volume mecânico para respeitar a janela de reatividade de 24h."
            ).replace(".", ",")

        exec_pills_list.append(f"""
            <div class="exec-pill">
                <div class="exec-icon" style="background:{cor_kpi_dor};">{icone_kpi_dor}</div>
                <div class="exec-info" contenteditable="true">
                    <span class="exec-lbl">DOR (EVA)</span>
                    <span class="exec-main" style="color:{cor_kpi_dor};">{_esc(txt_kpi_dor)}</span>
                    <span class="exec-sub">{_esc(sub_kpi_dor)}</span>
                </div>
            </div>
        """)

        b64_dor = _gerar_grafico_dor_clean_b64(hist)
        html_secao_dor = f"""
        <div class="section-card">
            <div class="section-title">EVOLUÇÃO DA DOR · EVA (0 A 10) — ÚLTIMAS {len(ultimas_10)} SESSÕES</div>
            <img class="chart-img" src="data:image/png;base64,{b64_dor}" alt="Evolução da Dor EVA" />
            {_box_conclusao_editavel(status_conc_dor, conc_dor_txt)}
        </div>
        """

    # --- 3. TESTES FUNCIONAIS ESPECÍFICOS (RELACIONAL FUNCIONAL COM BARRA DE DOR 0-10) ---
    b64_testes, conclusoes_testes, qtd_melhorou, total_testes = (
        _gerar_grafico_testes_clean_b64(hist) if n_sessoes >= 1 else ("", [], 0, 0)
    )
    html_secao_testes = ""
    if b64_testes and total_testes > 0:
        cor_kpi_func = "#16A34A" if qtd_melhorou >= max(1, total_testes // 2) else "#D97706"
        txt_kpi_func = f"{qtd_melhorou}/{total_testes} gestos"
        sub_kpi_func = "em evolução positiva"

        exec_pills_list.append(f"""
            <div class="exec-pill">
                <div class="exec-icon" style="background:{cor_kpi_func};">↑</div>
                <div class="exec-info" contenteditable="true">
                    <span class="exec-lbl">FUNÇÃO × DOR</span>
                    <span class="exec-main" style="color:{cor_kpi_func};">{_esc(txt_kpi_func)}</span>
                    <span class="exec-sub">{_esc(sub_kpi_func)}</span>
                </div>
            </div>
        """)

        boxes_conclusao_testes_html = "".join([
            _box_conclusao_editavel(cor_st, txt_c) for cor_st, txt_c in conclusoes_testes
        ])
        html_secao_testes = f"""
        <div class="section-card">
            <div class="section-title">RELACIONAL FUNCIONAL (DOR 0–10 DURANTE O GESTO) — ÚLTIMAS {len(ultimas_10)} SESSÕES</div>
            <img class="chart-img" src="data:image/png;base64,{b64_testes}" alt="Testes Funcionais" />
            {boxes_conclusao_testes_html}
        </div>
        """

    # --- 4. AMPLITUDE DE MOVIMENTO (ADM) ---
    adm_fl_d_av = _extrair_chave_str(dados_aval.get("ADM_Joelho_Flexao", ""), "Dir", 0.0)
    adm_fl_e_av = _extrair_chave_str(dados_aval.get("ADM_Joelho_Flexao", ""), "Esq", 0.0)
    lado_str_low = str(lado_acom).lower()
    adm_base_aval = adm_fl_e_av if "esquerdo" in lado_str_low else adm_fl_d_av

    tem_adm_preenchida = (adm_fl_d_av > 0 or adm_fl_e_av > 0) or any(_safe_float(h.get('Flexao', 0)) > 0 for h in hist)
    html_secao_adm = ""
    flex_atual = 0.0
    ext_atu_deg = 0.0

    if tem_adm_preenchida:
        flex_inicial = _safe_float(hist[0].get('Flexao', 0)) if hist else adm_base_aval
        if flex_inicial <= 0 and adm_base_aval > 0:
            flex_inicial = adm_base_aval
        flex_atual = _safe_float(hist[-1].get('Flexao', flex_inicial)) if hist else flex_inicial
        ganho_flex = flex_atual - flex_inicial

        if flex_atual >= 125:
            significado_flex = "liberando a cinemática necessária para agachamento profundo, corrida e gestos esportivos sem restrição articular"
        elif flex_atual >= 110:
            significado_flex = "atingindo o arco biomecânico necessário para descer escadas de forma recíproca, pedalar e agachar até a paralela sem compensações"
        elif flex_atual >= 95:
            significado_flex = "permitindo sentar e levantar com conforto e realizar marcha no plano sem compensação em rotação de quadril"
        else:
            significado_flex = "em fase de ganho progressivo de mobilidade articular para restabelecer as atividades de vida diária"

        if ganho_flex > 0:
            cor_kpi_adm = "#16A34A"
            icone_kpi_adm = "↑"
            txt_kpi_adm = f"+{ganho_flex:.0f}° ganho"
            sub_kpi_adm = f"({flex_inicial:.0f}° → {flex_atual:.0f}°)"
            status_conc_flex = "verde"
            conc_flex_txt = (
                f"Ganho de +{ganho_flex:.0f}° na flexão de joelho ao longo das sessões ({flex_inicial:.0f}° → {flex_atual:.0f}°), "
                f"{significado_flex}."
            )
        elif flex_atual >= 125:
            cor_kpi_adm = "#16A34A"
            icone_kpi_adm = "✓"
            txt_kpi_adm = f"{flex_atual:.0f}° plena"
            sub_kpi_adm = "amplitude funcional"
            status_conc_flex = "verde"
            conc_flex_txt = (
                f"Amplitude de flexão de joelho preservada em nível de excelência ({flex_atual:.0f}° / ref. 135°), "
                f"{significado_flex}."
            )
        else:
            cor_kpi_adm = "#D97706"
            icone_kpi_adm = "="
            txt_kpi_adm = f"{flex_atual:.0f}° atual"
            sub_kpi_adm = "(Meta: 135°)"
            status_conc_flex = "amarelo"
            conc_flex_txt = (
                f"Flexão de joelho em {flex_atual:.0f}° (referência clínica: 135°), {significado_flex}."
            )

        exec_pills_list.append(f"""
            <div class="exec-pill">
                <div class="exec-icon" style="background:{cor_kpi_adm};">{icone_kpi_adm}</div>
                <div class="exec-info" contenteditable="true">
                    <span class="exec-lbl">ADM JOELHO</span>
                    <span class="exec-main" style="color:{cor_kpi_adm};">{_esc(txt_kpi_adm)}</span>
                    <span class="exec-sub">{_esc(sub_kpi_adm)}</span>
                </div>
            </div>
        """)

        ext_ini_deg = _extrair_def_extensao_graus(hist[0].get('Extensao', '0')) if hist else 0.0
        ext_atu_deg = _extrair_def_extensao_graus(hist[-1].get('Extensao', '0')) if hist else 0.0
        if ext_atu_deg == 0:
            status_conc_ext = "verde"
            conc_ext_txt = (
                f"Extensão terminal completa atingida ({ext_ini_deg:.0f}° → 0°), eliminando o mecanismo de inibição artrogênica "
                f"do quadríceps e garantindo destravamento eficiente na fase de apoio da marcha."
            )
        else:
            status_conc_ext = "amarelo" if ext_atu_deg <= 5 else "laranja"
            conc_ext_txt = (
                f"Extensão de Joelho ({ext_ini_deg:.0f}° → {ext_atu_deg:.0f}°) · déficit residual de {ext_atu_deg:.0f}°. "
                f"Priorizada mobilização em extensão terminal para otimizar o recrutamento do quadríceps."
            )

        cards_sessoes_flex_html = ""
        cards_sessoes_ext_html = ""
        for _, ev_m, lbl_card in ultimas_10:
            fl_m = _safe_float(ev_m.get('Flexao', flex_atual))
            ex_m = _extrair_def_extensao_graus(ev_m.get('Extensao', 0))
            cards_sessoes_flex_html += f"""
            <div class="stage-pill">
                <span class="stage-lbl">{_esc(lbl_card)}</span>
                <span class="stage-val">{fl_m:.0f}°</span>
            </div>
            """
            cards_sessoes_ext_html += f"""
            <div class="stage-pill">
                <span class="stage-lbl">{_esc(lbl_card)}</span>
                <span class="stage-val">{ex_m:.0f}°</span>
            </div>
            """

        svg_gauge_flex = _construir_svg_gauge_flexao(flex_atual, 135.0)
        svg_donut_ext = _construir_svg_donut_extensao(ext_atu_deg)

        html_secao_adm = f"""
        <div class="section-card">
            <div class="section-title">AMPLITUDE DE MOVIMENTO (ADM) AO LONGO DAS SESSÕES</div>
            <div class="grid-2">
                <div class="sub-card" style="margin-bottom:0;">
                    <div class="sub-card-header">
                        <span class="sub-card-title">Flexão de Joelho</span>
                        <span class="sub-card-meta">Atual: {flex_atual:.0f}° · Inicial: {flex_inicial:.0f}°</span>
                    </div>
                    {svg_gauge_flex}
                    <div class="stages-grid">
                        {cards_sessoes_flex_html}
                    </div>
                    <div class="ref-banner">
                        <span>Referência angular funcional</span>
                        <strong>135°</strong>
                    </div>
                    {_box_conclusao_editavel(status_conc_flex, conc_flex_txt)}
                </div>

                <div class="sub-card" style="margin-bottom:0;">
                    <div class="sub-card-header">
                        <span class="sub-card-title">Extensão de Joelho</span>
                        <span class="sub-card-meta">Déficit atual: {ext_atu_deg:.0f}°</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:16px; margin: 14px 0;">
                        {svg_donut_ext}
                        <div style="flex:1;">
                            <div class="ref-banner" style="margin-bottom:8px;">
                                <span>Meta clínica</span>
                                <strong>0° (Completa)</strong>
                            </div>
                            <p style="font-size:11px; color:#64748B; margin:0; line-height:1.45;">
                                Para a extensão terminal do joelho, a referência de <strong>0°</strong> é tratada como alvo biomecânico absoluto para destravamento articular e ativação plena do quadríceps.
                            </p>
                        </div>
                    </div>
                    <div class="stages-grid">
                        {cards_sessoes_ext_html}
                    </div>
                    <div class="ref-banner">
                        <span>Referência angular terminal</span>
                        <strong>0°</strong>
                    </div>
                    {_box_conclusao_editavel(status_conc_ext, conc_ext_txt)}
                </div>
            </div>
        </div>
        """

    # --- 5. QUESTIONÁRIOS / PROMs ---
    catalogo_proms = {
        "LEFS": {
            "sub": "Escala Funcional da Extremidade Inferior",
            "val": _safe_float(dados_aval.get("LEFS_Pts_80") or (float(dados_aval.get("LEFS_Pct", 0) or 0) * 0.8), 0.0),
            "pct": _safe_float(dados_aval.get("LEFS_Pct", 0), 0.0),
            "melhor_ref": "80,0 pts (100%)",
            "pior_ref": "0,0 pts",
            "un": "pts",
            "interp": dados_aval.get("Interpretacao_LEFS", "Boa capacidade funcional"),
            "default_falso": 0.0,
        },
        "VISA-P": {
            "sub": "Tendinopatia Patelar (Jumper's Knee)",
            "val": _safe_float(dados_aval.get("VISA_P_Pts", 0), 0.0),
            "pct": _safe_float(dados_aval.get("VISA_P_Pts", 0), 0.0),
            "melhor_ref": "100,0 pts",
            "pior_ref": "0,0 pts",
            "un": "pts",
            "interp": dados_aval.get("Interpretacao_VISA_P", "Em evolução"),
            "default_falso": 50.0,
        },
        "Lysholm": {
            "sub": "Escore Funcional Ligamentar e Meniscal",
            "val": _safe_float(dados_aval.get("Lysholm_Pts", 0), 0.0),
            "pct": _safe_float(dados_aval.get("Lysholm_Pts", 0), 0.0),
            "melhor_ref": "100,0 pts",
            "pior_ref": "0,0 pts",
            "un": "pts",
            "interp": dados_aval.get("Interpretacao_Lysholm", "Em evolução"),
            "default_falso": 100.0,
        },
        "WOMAC": {
            "sub": "Índice Funcional de Osteoartrite",
            "val": _safe_float(dados_aval.get("WOMAC_Pct", 0), 0.0),
            "pct": _safe_float(dados_aval.get("WOMAC_Pct", 0), 0.0),
            "melhor_ref": "100,0%",
            "pior_ref": "0,0%",
            "un": "%",
            "interp": dados_aval.get("Interpretacao_WOMAC", "Em evolução"),
            "default_falso": 100.0,
        },
        "KOOS": {
            "sub": "Knee Injury and Osteoarthritis Outcome Score",
            "val": _safe_float(dados_aval.get("KOOS_Pct", 0), 0.0),
            "pct": _safe_float(dados_aval.get("KOOS_Pct", 0), 0.0),
            "melhor_ref": "100,0%",
            "pior_ref": "0,0%",
            "un": "%",
            "interp": "Score Global de Joelho",
            "default_falso": 100.0,
        },
        "IKDC": {
            "sub": "International Knee Documentation Committee",
            "val": _safe_float(dados_aval.get("IKDC_Pct", 0), 0.0),
            "pct": _safe_float(dados_aval.get("IKDC_Pct", 0), 0.0),
            "melhor_ref": "100,0%",
            "pior_ref": "0,0%",
            "un": "%",
            "interp": "Avaliação Subjetiva de Joelho",
            "default_falso": 75.0,
        },
    }

    if "PROMs_Selecionados" in dados_aval and isinstance(dados_aval["PROMs_Selecionados"], list):
        proms_escolhidos = [
            p for p in dados_aval["PROMs_Selecionados"]
            if p in catalogo_proms and catalogo_proms[p]["val"] > 0
        ]
    else:
        proms_escolhidos = [
            k_p for k_p, info_p in catalogo_proms.items()
            if info_p["val"] > 0 and round(info_p["val"], 1) != info_p["default_falso"]
        ][:1]

    html_secao_prom = ""
    if proms_escolhidos:
        cards_prom_inner = ""
        kpi_prom_adicionado = False
        for nome_p in proms_escolhidos:
            p_info = catalogo_proms[nome_p]
            val_exib = f"{p_info['val']:.1f}".replace(".", ",")
            pct_p = max(0.0, min(100.0, p_info["pct"]))
            cor_p = "#16A34A" if pct_p >= 70 else ("#D97706" if pct_p >= 45 else "#DC2626")
            status_p = "verde" if pct_p >= 70 else ("amarelo" if pct_p >= 45 else "laranja")
            interp_limpa = str(p_info["interp"]).replace("⭐ ", "").replace("🟢 ", "").replace("🟡 ", "").replace("🚨 ", "")

            if not kpi_prom_adicionado:
                exec_pills_list.append(f"""
                    <div class="exec-pill">
                        <div class="exec-icon" style="background:{cor_p};">Q</div>
                        <div class="exec-info" contenteditable="true">
                            <span class="exec-lbl">{_esc(nome_p)}</span>
                            <span class="exec-main" style="color:#103E55;">{_esc(f"{val_exib} {p_info['un']}")}</span>
                            <span class="exec-sub">{_esc(interp_limpa)}</span>
                        </div>
                    </div>
                """)
                kpi_prom_adicionado = True

            conc_prom_txt = (
                f"Pontuação de {val_exib} {p_info['un']} no questionário {nome_p} ({p_info['sub']}), "
                f"compatível com {interp_limpa.lower()}."
            )

            cards_prom_inner += f"""
            <div class="sub-card">
                <div class="sub-card-header">
                    <div>
                        <span class="sub-card-title">{_esc(nome_p)}</span>
                        <span class="sub-card-caption"> · {_esc(p_info['sub'])}</span>
                    </div>
                    <span class="sub-card-meta">Evolução funcional · melhor no topo</span>
                </div>
                <div style="display:grid; grid-template-columns: 1.5fr 1fr; gap:16px; align-items:center; margin: 12px 0;">
                    <div>
                        <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:700; color:#475569; margin-bottom:6px;">
                            <span>Capacidade Funcional Relatada</span>
                            <span style="color:{cor_p}; font-size:15px; font-weight:800;">{pct_p:.0f}%</span>
                        </div>
                        <div class="bar-track" style="height:14px;">
                            <div class="bar-fill" style="width:{pct_p:.1f}%; background:{cor_p};"></div>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#64748B; margin-top:6px;">
                            <span>0% (Incapacidade)</span>
                            <span>100% (Capacidade Máxima)</span>
                        </div>
                    </div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
                        <div class="stage-pill">
                            <span class="stage-lbl">MELHOR REF.</span>
                            <span class="stage-val" style="color:#16A34A; font-size:13px;">{_esc(p_info['melhor_ref'])}</span>
                        </div>
                        <div class="stage-pill">
                            <span class="stage-lbl">PIOR REF.</span>
                            <span class="stage-val" style="color:#DC2626; font-size:13px;">{_esc(p_info['pior_ref'])}</span>
                        </div>
                        <div class="stage-pill" style="grid-column: span 2; background:#F0F9FF; border-color:#BAE6FD;">
                            <span class="stage-lbl" style="color:#103E55;">PONTUAÇÃO ATUAL ({_esc(nome_p)})</span>
                            <span class="stage-val" style="color:#103E55; font-size:17px;">{val_exib} {_esc(p_info['un'])}</span>
                        </div>
                    </div>
                </div>
                {_box_conclusao_editavel(status_p, conc_prom_txt)}
            </div>
            """

        html_secao_prom = f"""
        <div class="section-card">
            <div class="section-title">QUESTIONÁRIO VALIDADO / PROM APLICADO</div>
            {cards_prom_inner}
        </div>
        """

    # --- 6. OBJETIVOS DO PACIENTE (SANE & GROC -7 A +7 — SEM PSFS) ---
    obj_raw = dados_aval.get('Objetivo_Paciente')
    tem_sane_historico = any(h.get('SANE_Pct') is not None for h in hist)
    tem_obj_preenchido = _tem_valor_util(obj_raw) or tem_sane_historico

    html_secao_sane = ""
    sane_base = _safe_float(dados_aval.get('SANE_Baseline_Pct', 30.0), 30.0)
    sane_atual = _safe_float(hist[-1].get('SANE_Pct', sane_base), sane_base) if hist else sane_base
    groc_ult = hist[-1].get('GROC_Score') if hist else None

    if tem_obj_preenchido:
        obj_paciente = obj_raw if _tem_valor_util(obj_raw) else "Retorno à função e esporte sem dor"
        ganho_sane = sane_atual - sane_base
        b64_sane = _gerar_grafico_sane_clean_b64(hist, sane_base)

        groc_str_sub = ""
        if groc_ult is not None and str(groc_ult).strip() != "":
            try:
                groc_int = int(float(groc_ult))
                groc_str_sub = f" & Mudança Global GROC ({groc_int:+d} em -7/+7)"
            except Exception:
                pass

        status_sane = "verde" if (sane_atual >= 80 or ganho_sane >= 15) else "amarelo"
        conc_sane_txt = (
            f"Evolução de {ganho_sane:+.0f} pontos percentuais na percepção de capacidade funcional para '{obj_paciente}' "
            f"desde o início do tratamento ({sane_base:.0f}% → {sane_atual:.0f}% na escala SANE){groc_str_sub}."
        )

        html_secao_sane = f"""
        <div class="section-card">
            <div class="section-title">OBJETIVO FUNCIONAL DO PACIENTE · SANE & GROC (-7 A +7) — ÚLTIMAS {max(1, len(ultimas_10))} SESSÕES</div>
            <div class="sub-card" style="margin-bottom:0;">
                <div class="sub-card-header">
                    <div>
                        <span class="sub-card-title">🎯 {_esc(obj_paciente)}</span>
                        <span class="sub-card-caption"> · Escala SANE (0–100% · Marco Zero: {sane_base:.0f}%){_esc(groc_str_sub)}</span>
                    </div>
                    <span class="sub-card-meta">Meta Final: 100% (Alta Subjetiva ≥ 85%)</span>
                </div>
                <img class="chart-img" style="max-height:210px; object-fit:contain;" src="data:image/png;base64,{b64_sane}" alt="Evolução do Objetivo" />
                {_box_conclusao_editavel(status_sane, conc_sane_txt)}
            </div>
        </div>
        """

    # --- 7. FORÇA MUSCULAR — DINAMOMETRIA (kgf) + LSI + RAZÃO I:Q ---
    din_d_str = dados_aval.get('Dinamometria_Dir', '')
    din_e_str = dados_aval.get('Dinamometria_Esq', '')

    grupos_forca = [
        ("Extensão Joelho (Quadríceps)", "Ext"),
        ("Flexão Joelho (Isquiotibiais)", "Flex"),
        ("Abdução Quadril (Glúteo Médio)", "Abd"),
        ("Adução Quadril (Adutores)", "Add"),
    ]

    grupos_din_preenchidos = []
    for nome_g, pref_g in grupos_forca:
        vd = _extrair_chave_str(din_d_str, pref_g, 0.0)
        ve = _extrair_chave_str(din_e_str, pref_g, 0.0)
        if vd > 0 or ve > 0:
            grupos_din_preenchidos.append((nome_g, pref_g, vd, ve))

    tem_dinamometria = len(grupos_din_preenchidos) > 0
    html_secao_forca = ""
    lsi_quad_din = None

    if tem_dinamometria:
        cards_forca_html = ""
        deficit_ref_resumo = 0.0
        ext_d_val = _extrair_chave_str(din_d_str, "Ext", 0.0)
        ext_e_val = _extrair_chave_str(din_e_str, "Ext", 0.0)
        flex_d_val = _extrair_chave_str(din_d_str, "Flex", 0.0)
        flex_e_val = _extrair_chave_str(din_e_str, "Flex", 0.0)

        for idx_g, (nome_g, pref_g, vd, ve) in enumerate(grupos_din_preenchidos):
            max_v = max(vd, ve, 0.1)
            lsi_tec = (min(vd, ve) / max_v) * 100.0
            deficit_pct = max(0.0, 100.0 - lsi_tec)
            lado_def = "D" if vd < ve else ("E" if ve < vd else "")

            if pref_g == "Ext" or idx_g == 0:
                deficit_ref_resumo = deficit_pct
                if pref_g == "Ext":
                    lsi_quad_din = lsi_tec

            if deficit_pct <= 10.0:
                cor_def = "#16A34A"
                badge_def = "normal / simétrico"
                st_forca = "verde"
                conc_f_txt = f"Simetria isométrica adequada em {nome_g} na dinamometria ({vd:.1f} kgf vs {ve:.1f} kgf · Déficit de {deficit_pct:.0f}% ≤ 10%, LSI de {lsi_tec:.0f}%)."
            elif deficit_pct <= 20.0:
                cor_def = "#EAB308"
                badge_def = "déficit discreto"
                st_forca = "amarelo"
                conc_f_txt = f"Déficit discreto de {deficit_pct:.0f}% do lado {lado_def} em {nome_g} ({vd:.1f} kgf vs {ve:.1f} kgf · LSI: {lsi_tec:.0f}% · meta ≥ 90%)."
            elif deficit_pct <= 30.0:
                cor_def = "#F97316"
                badge_def = "déficit moderado"
                st_forca = "laranja"
                conc_f_txt = f"Déficit moderado de {deficit_pct:.0f}% do lado {lado_def} em {nome_g} ({vd:.1f} kgf vs {ve:.1f} kgf · LSI: {lsi_tec:.0f}%). Intensificar fortalecimento unilateral."
            else:
                cor_def = "#DC2626"
                badge_def = "déficit importante"
                st_forca = "vermelho"
                conc_f_txt = f"Déficit importante de {deficit_pct:.0f}% do lado {lado_def} em {nome_g} ({vd:.1f} kgf vs {ve:.1f} kgf · LSI: {lsi_tec:.0f}%). Prioridade máxima na reabilitação."

            w_d = (vd / max_v) * 100.0
            w_e = (ve / max_v) * 100.0
            cor_bar_d = cor_def if vd < ve else "#16A34A"
            cor_bar_e = cor_def if ve < vd else "#16A34A"

            cards_forca_html += f"""
            <div class="sub-card" style="margin-bottom:0;">
                <div class="sub-card-header">
                    <span class="sub-card-title">{_esc(nome_g)}</span>
                    <span class="sub-card-meta">Dinamometria (kgf) · Déficit {deficit_pct:.0f}% {lado_def}</span>
                </div>
                <div class="ref-banner">
                    <span>Referência clínica PBE (Handheld Dynamometer)</span>
                    <strong>≤ 10% de diferença entre os membros (LSI ≥ 90%)</strong>
                </div>
                <div style="display:grid; grid-template-columns: 1.35fr 1fr; gap:14px; align-items:center; margin: 12px 0;">
                    <div>
                        <div style="font-size:11px; font-weight:800; color:#103E55; margin-bottom:8px;">Pico de Força Isométrica (kgf)</div>
                        <div class="force-row">
                            <span class="force-lbl">Direito</span>
                            <div class="bar-track"><div class="bar-fill" style="width:{w_d:.1f}%; background:{cor_bar_d};"></div></div>
                            <span class="force-val">{vd:.1f} kgf</span>
                        </div>
                        <div class="force-row">
                            <span class="force-lbl">Esquerdo</span>
                            <div class="bar-track"><div class="bar-fill" style="width:{w_e:.1f}%; background:{cor_bar_e};"></div></div>
                            <span class="force-val">{ve:.1f} kgf</span>
                        </div>
                        <div style="font-size:10.5px; color:#64748B; margin-top:6px;">
                            {deficit_pct:.0f}% {lado_def} · {_esc(badge_def)}
                        </div>
                    </div>
                    <div class="deficit-box">
                        <span class="deficit-lbl">DÉFICIT ENTRE OS MEMBROS</span>
                        <div class="deficit-big" style="color:{cor_def};">{deficit_pct:.0f}% {lado_def}</div>
                        <span class="deficit-pill" style="background:{cor_def};">{_esc(badge_def)}</span>
                        <span class="deficit-sub">LSI: {lsi_tec:.0f}% · ref. ≥ 90%</span>
                    </div>
                </div>
                {_box_conclusao_editavel(st_forca, conc_f_txt)}
            </div>
            """

        # Banner de Razão Isquiotibiais : Quadríceps (I:Q Ratio)
        banner_iq_html = ""
        iq_d = (flex_d_val / ext_d_val * 100.0) if (ext_d_val > 0 and flex_d_val > 0) else None
        iq_e = (flex_e_val / ext_e_val * 100.0) if (ext_e_val > 0 and flex_e_val > 0) else None
        if iq_d is not None or iq_e is not None:
            txt_iq_d = f"Direito: {iq_d:.0f}% ({iq_d/100:.2f})" if iq_d is not None else "Direito: N/D"
            txt_iq_e = f"Esquerdo: {iq_e:.0f}% ({iq_e/100:.2f})" if iq_e is not None else "Esquerdo: N/D"
            banner_iq_html = f"""
            <div class="ref-banner" style="margin-top:14px; margin-bottom:0; background:#F0F9FF; border-color:#BAE6FD;">
                <span style="color:#103E55; font-weight:700;">⚖️ Equilíbrio Agonista:Antagonista — Razão Isquiotibiais : Quadríceps (I:Q Ratio)</span>
                <strong style="color:#103E55;" contenteditable="true">{_esc(txt_iq_d)} · {_esc(txt_iq_e)} (Alvo PBE: 55% a 65%)</strong>
            </div>
            """

        cor_kpi_forca = "#16A34A" if deficit_ref_resumo <= 10 else ("#D97706" if deficit_ref_resumo <= 20 else "#DC2626")
        txt_kpi_forca = f"{deficit_ref_resumo:.0f}% déficit" if deficit_ref_resumo > 0 else "Simétrico"
        sub_kpi_forca = f"LSI Dinamometria: {100.0 - deficit_ref_resumo:.0f}%"

        exec_pills_list.append(f"""
            <div class="exec-pill">
                <div class="exec-icon" style="background:{cor_kpi_forca};">⚖</div>
                <div class="exec-info" contenteditable="true">
                    <span class="exec-lbl">DINAMOMETRIA (LSI)</span>
                    <span class="exec-main" style="color:{cor_kpi_forca};">{_esc(txt_kpi_forca)}</span>
                    <span class="exec-sub">{_esc(sub_kpi_forca)}</span>
                </div>
            </div>
        """)

        grid_class_forca = "grid-2" if len(grupos_din_preenchidos) > 1 else ""
        html_secao_forca = f"""
        <div class="section-card">
            <div class="section-title">FORÇA MUSCULAR ISOMÉTRICA (DINAMOMETRIA · KGF) · LSI & RAZÃO I:Q</div>
            <div class="{grid_class_forca}">
                {cards_forca_html}
            </div>
            {banner_iq_html}
        </div>
        """

    # --- 8. OS 6 PONTOS DE OBJETIVO PARA ATINGIR (GATEKEEPERS PBE DE ALTA FUNCIONAL) ---
    html_secao_gatekeepers = ""
    if n_sessoes >= 1 or tem_dinamometria or tem_adm_preenchida:
        ult_sessao = hist[-1] if hist else {}
        inchaco_raw = ult_sessao.get('Inchaço', ult_sessao.get('Inchaco', dados_aval.get('Derrame', 'Ausente')))
        inchaco_grau = _mapear_inchaco_grau(inchaco_raw)

        pass_val = ult_sessao.get('PASS_Atingido')
        if pass_val is None:
            pass_str = str(ult_sessao.get('PASS_Satisfacao', '') or '')
            pass_bool = pass_str.startswith("👍") or "sim" in pass_str.lower()
        else:
            pass_bool = bool(pass_val) if isinstance(pass_val, bool) else str(pass_val).strip().lower() in ["true", "1", "sim"]

        crit_1_ok = (dor_atual <= 2.0) and (tem_dor_preenchida or n_sessoes >= 1)
        crit_2_ok = (inchaco_grau <= 1)
        crit_3_ok = (ext_atu_deg == 0.0) and tem_adm_preenchida
        crit_4_ok = (flex_atual >= 125.0) and tem_adm_preenchida
        crit_5_ok = (lsi_quad_din is not None and lsi_quad_din >= 90.0)
        crit_6_ok = (sane_atual >= 85.0 and pass_bool)

        criterios_6_pontos = [
            (
                "1. Controle Álgico (EVA ≤ 2/10)",
                crit_1_ok,
                f"Atual: {dor_atual:.0f}/10 na EVA" if tem_dor_preenchida else "Não avaliado",
                "Salaffi et al., 2004"
            ),
            (
                "2. Efusão Articular Controlada (Grau ≤ 1/3)",
                crit_2_ok,
                f"Atual: Grau {inchaco_grau}/3 ({inchaco_raw or 'Ausente'})",
                "Stroke Test PBE"
            ),
            (
                "3. Extensão Terminal Completa (0°)",
                crit_3_ok,
                f"Atual: {'Completa (0°)' if ext_atu_deg == 0 else f'Déficit de {ext_atu_deg:.0f}°'}" if tem_adm_preenchida else "Não avaliada",
                "Shelbourne et al., 1997"
            ),
            (
                "4. Amplitude de Flexão Funcional (≥ 125°)",
                crit_4_ok,
                f"Atual: {flex_atual:.0f}° (Ref: 135°)" if tem_adm_preenchida else "Não avaliada",
                "Diretriz Pós-Op Joelho"
            ),
            (
                "5. Simetria de Força de Quadríceps (LSI ≥ 90%)",
                crit_5_ok if lsi_quad_din is not None else None,
                f"Atual: LSI {lsi_quad_din:.0f}% (Dinamometria kgf)" if lsi_quad_din is not None else "Opcional / Aguardando Dinamometria",
                "Grindem et al., 2016"
            ),
            (
                "6. Meta Subjetiva Atingida (SANE ≥ 85% + PASS Sim)",
                crit_6_ok,
                f"SANE: {sane_atual:.0f}% · PASS: {'Satisfeito (Sim)' if pass_bool else 'Em evolução'}",
                "Shelbourne 2009 / Tubach 2005"
            ),
        ]

        total_atingidos = sum(1 for _, st_ok, _, _ in criterios_6_pontos if st_ok is True)
        pct_6_pontos = (total_atingidos / 6.0) * 100.0
        cor_barra_6 = "#16A34A" if total_atingidos >= 5 else ("#2E8B9A" if total_atingidos >= 3 else "#D97706")

        cards_6_html = ""
        for titulo_c, st_ok, valor_c, ref_c in criterios_6_pontos:
            if st_ok is True:
                borda_c = "#16A34A"
                bg_c = "#F0FDF4"
                icone_c = "✓"
                cor_icone = "#16A34A"
                tag_status = "ATINGIDO"
            elif st_ok is None:
                borda_c = "#94A3B8"
                bg_c = "#F8FAFC"
                icone_c = "—"
                cor_icone = "#64748B"
                tag_status = "OPCIONAL / PENDENTE"
            else:
                borda_c = "#F59E0B"
                bg_c = "#FFFBEB"
                icone_c = "⏳"
                cor_icone = "#D97706"
                tag_status = "EM CONSTRUÇÃO"

            cards_6_html += f"""
            <div style="border-left: 4px solid {borda_c}; background: {bg_c}; border-radius: 10px; padding: 10px 14px; border-top: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="font-size:12px; font-weight:800; color:#103E55;" contenteditable="true">{_esc(titulo_c)}</span>
                    <span style="background:{cor_icone}; color:#FFFFFF; font-size:9px; font-weight:800; padding:2px 8px; border-radius:99px; white-space:nowrap;">{icone_c} {tag_status}</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:baseline; font-size:11px; color:#334155;" contenteditable="true">
                    <strong>{_esc(valor_c)}</strong>
                    <span style="font-size:9.5px; color:#64748B;">Ref: {_esc(ref_c)}</span>
                </div>
            </div>
            """

        html_secao_gatekeepers = f"""
        <div class="section-card">
            <div class="section-title">METAS CLÍNICAS PARA ALTA FUNCIONAL · 6 CRITÉRIOS PBE (GATEKEEPERS)</div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:12.5px; font-weight:800; color:#103E55;" contenteditable="true">
                    Progresso Global nos Critérios de Alta: {total_atingidos} de 6 metas atingidas ({pct_6_pontos:.0f}%)
                </span>
                <span style="font-size:11px; font-weight:700; color:#64748B;">Meta para liberação plena: 6/6 (100%)</span>
            </div>
            <div class="bar-track" style="height:12px; margin-bottom:14px;">
                <div class="bar-fill" style="width:{pct_6_pontos:.1f}%; background:{cor_barra_6};"></div>
            </div>
            <div class="grid-2" style="gap:10px;">
                {cards_6_html}
            </div>
        </div>
        """

    html_resumo_executivo = ""
    if exec_pills_list:
        ncols_exec = len(exec_pills_list)
        html_resumo_executivo = f"""
        <div class="section-card">
            <div class="section-title">RESUMO EXECUTIVO DOS INDICADORES AVALIADOS</div>
            <div class="exec-grid" style="grid-template-columns: repeat({ncols_exec}, 1fr);">
                {''.join(exec_pills_list)}
            </div>
            <div class="no-print" style="font-size:10.5px; color:#64748B; margin-top:10px;">
                Clique nos indicadores do resumo ou nas conclusões abaixo para personalizar o texto antes de exportar/imprimir.
            </div>
        </div>
        """

    # --- 9. CONCLUSÃO FINAL E RECOMENDAÇÕES DO FISIOTERAPEUTA ---
    conclusao_livre = dados_aval.get("Conclusao_Final_Fisio", "")
    if not _tem_valor_util(conclusao_livre):
        partes_sintese = []
        if tem_dor_preenchida:
            partes_sintese.append(f"dor em {dor_atual:.0f}/10 na EVA")
        if tem_adm_preenchida:
            partes_sintese.append(f"flexão de joelho de {flex_atual:.0f}°")
        if tem_obj_preenchido:
            partes_sintese.append(f"capacidade funcional percebida (SANE) em {sane_atual:.0f}%")
        if lsi_quad_din is not None:
            partes_sintese.append(f"LSI de quadríceps na dinamometria em {lsi_quad_din:.0f}%")

        resumo_metricas = ", ".join(partes_sintese) if partes_sintese else "boa resposta clínica"
        conclusao_livre = (
            f"Paciente apresenta evolução clínica e biomecânica consistente no período avaliado ({resumo_metricas}). "
            f"Recomendamos manutenção da progressão de carga específica até o cumprimento integral das 6 metas funcionais de alta (PBE)."
        )

    logo_b64 = _carregar_logo_b64()
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="GENUA" style="max-height:66px; width:auto; border-radius:10px;" />'
    else:
        logo_html = '<div style="font-size:26px; font-weight:900; letter-spacing:1px; color:#FFFFFF;">GENUA</div><div style="font-size:10px; color:#A5F3FC; letter-spacing:1.2px;">FISIOTERAPIA ESPORTIVA</div>'

    # ============================================================
    # MONTAGEM DO DOCUMENTO HTML5 CLEAN LIGHT GENUA
    # ============================================================
    html_completo = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relatório de Evolução GENUA - {_esc(paciente_nome)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
    :root {{
        --genua-primary: #103E55;
        --genua-secondary: #2E8B9A;
        --bg-page: #F4F6F8;
        --bg-card: #FFFFFF;
        --bg-subtle: #F8FAFC;
        --border-color: #E2E8F0;
        --text-dark: #1E293B;
        --text-muted: #64748B;
    }}
    * {{
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }}
    body {{
        margin: 0;
        padding: 20px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: var(--bg-page);
        color: var(--text-dark);
        line-height: 1.45;
    }}
    .container {{
        max-width: 980px;
        margin: 0 auto;
    }}
    .action-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #FFFFFF;
        border: 1px solid var(--border-color);
        padding: 12px 18px;
        border-radius: 14px;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(16, 62, 85, 0.05);
    }}
    .btn-print {{
        background: linear-gradient(135deg, #103E55 0%, #2E8B9A 100%);
        color: #FFFFFF;
        border: none;
        padding: 10px 22px;
        border-radius: 99px;
        font-weight: 700;
        font-size: 13px;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(16, 62, 85, 0.2);
    }}
    .btn-print:hover {{
        filter: brightness(1.08);
    }}

    /* HEADER INSTITUCIONAL GENUA */
    .header-banner {{
        background: linear-gradient(135deg, #0D3246 0%, #103E55 60%, #1B5E7A 100%);
        color: #FFFFFF;
        border-radius: 18px;
        padding: 24px 28px;
        margin-bottom: 18px;
        display: grid;
        grid-template-columns: 210px 1fr;
        gap: 24px;
        align-items: center;
        box-shadow: 0 8px 24px rgba(16, 62, 85, 0.14);
    }}
    .brand-col {{
        display: flex;
        flex-direction: column;
        gap: 8px;
        border-right: 1px solid rgba(255, 255, 255, 0.15);
        padding-right: 20px;
    }}
    .logo-box {{
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 14px;
        padding: 12px;
        text-align: center;
    }}
    .header-pill {{
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.18);
        color: #E2E8F0;
        font-size: 11px;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 99px;
        text-align: center;
    }}
    .meta-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px 18px;
    }}
    .meta-item {{
        display: flex;
        flex-direction: column;
    }}
    .meta-lbl {{
        font-size: 10.5px;
        color: #94A3B8;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.4px;
        margin-bottom: 2px;
    }}
    .meta-val {{
        font-size: 13.5px;
        font-weight: 800;
        color: #FFFFFF;
    }}

    /* SEÇÕES E RESUMO EXECUTIVO */
    .section-card {{
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 20px 22px;
        margin-bottom: 18px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
    }}
    .section-title {{
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 0.8px;
        color: var(--genua-primary);
        text-transform: uppercase;
        margin-bottom: 14px;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 8px;
    }}
    .exec-grid {{
        display: grid;
        gap: 10px;
    }}
    .exec-pill {{
        background: var(--bg-subtle);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 12px 10px;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .exec-icon {{
        width: 34px;
        height: 34px;
        border-radius: 50%;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        font-size: 15px;
        flex-shrink: 0;
    }}
    .exec-info {{
        overflow: hidden;
    }}
    .exec-lbl {{
        font-size: 9.5px;
        font-weight: 800;
        color: var(--text-muted);
        text-transform: uppercase;
        display: block;
    }}
    .exec-main {{
        font-size: 13px;
        font-weight: 800;
        display: block;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .exec-sub {{
        font-size: 10.5px;
        font-weight: 600;
        color: var(--text-muted);
        display: block;
    }}

    /* SUB-CARDS E GRIDS */
    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
    }}
    .sub-card {{
        background: #FFFFFF;
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 12px;
    }}
    .sub-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 10px;
        gap: 8px;
    }}
    .sub-card-title {{
        font-size: 13.5px;
        font-weight: 800;
        color: var(--genua-primary);
    }}
    .sub-card-caption {{
        font-size: 11.5px;
        color: var(--text-muted);
        font-weight: 500;
    }}
    .sub-card-meta {{
        font-size: 10.5px;
        color: var(--text-muted);
        font-weight: 600;
        text-align: right;
    }}
    .chart-img {{
        width: 100%;
        height: auto;
        display: block;
        margin: 4px 0 10px 0;
    }}

    /* MINI-CARDS DE SESSÕES (ATÉ 10 SESSÕES COMPACTAS) */
    .stages-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(72px, 1fr));
        gap: 6px;
        margin: 10px 0;
    }}
    .stage-pill {{
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 9px;
        padding: 6px 8px;
        text-align: center;
    }}
    .stage-lbl {{
        font-size: 9px;
        color: var(--text-muted);
        font-weight: 700;
        display: block;
    }}
    .stage-val {{
        font-size: 13px;
        font-weight: 800;
        color: var(--text-dark);
    }}
    .ref-banner {{
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 6px 12px;
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: var(--text-muted);
        margin-bottom: 10px;
    }}
    .ref-banner strong {{
        color: var(--text-dark);
    }}

    /* FORÇA ISOMÉTRICA (DINAMOMETRIA D x E) */
    .force-row {{
        display: grid;
        grid-template-columns: 58px 1fr 54px;
        align-items: center;
        gap: 8px;
        margin-bottom: 7px;
        font-size: 11.5px;
    }}
    .force-lbl {{
        color: var(--text-dark);
        font-weight: 600;
    }}
    .force-val {{
        font-weight: 800;
        color: var(--text-dark);
        text-align: right;
    }}
    .bar-track {{
        width: 100%;
        height: 9px;
        background: #E2E8F0;
        border-radius: 99px;
        overflow: hidden;
    }}
    .bar-fill {{
        height: 100%;
        border-radius: 99px;
    }}
    .deficit-box {{
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px 8px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
    }}
    .deficit-lbl {{
        font-size: 8.5px;
        font-weight: 800;
        color: var(--text-muted);
        text-transform: uppercase;
    }}
    .deficit-big {{
        font-size: 24px;
        font-weight: 900;
        line-height: 1.1;
    }}
    .deficit-pill {{
        color: #FFFFFF;
        font-size: 9.5px;
        font-weight: 800;
        padding: 2px 10px;
        border-radius: 99px;
    }}
    .deficit-sub {{
        font-size: 9px;
        color: var(--text-muted);
        font-weight: 600;
    }}

    /* BOX DE CONCLUSÃO AUTOMÁTICA + EDITÁVEL */
    .conclusion-box {{
        border-left: 4px solid #16A34A;
        background: #F0FDF4;
        border-radius: 10px;
        padding: 10px 14px;
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
    }}
    .conclusion-content {{
        font-size: 12px;
        color: #1E293B;
        line-height: 1.45;
        flex: 1;
        outline: none;
        padding: 2px 4px;
        border-radius: 6px;
        transition: background 0.15s;
    }}
    .conclusion-content:hover, .conclusion-content:focus {{
        background: rgba(255, 255, 255, 0.85);
        box-shadow: 0 0 0 2px rgba(46, 139, 154, 0.35);
    }}
    .status-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 5px;
        vertical-align: middle;
    }}
    .edit-badge {{
        font-size: 9.5px;
        font-weight: 800;
        color: #94A3B8;
        letter-spacing: 0.5px;
        user-select: none;
        flex-shrink: 0;
    }}

    /* CONCLUSÃO FINAL E LEGENDA */
    .final-textarea {{
        width: 100%;
        min-height: 76px;
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        padding: 12px 14px;
        font-size: 12.5px;
        color: var(--text-dark);
        background: #F8FAFC;
        outline: none;
        line-height: 1.5;
    }}
    .final-textarea:focus {{
        background: #FFFFFF;
        border-color: var(--genua-secondary);
        box-shadow: 0 0 0 3px rgba(46, 139, 154, 0.15);
    }}
    .legend-bar {{
        background: #FFFFFF;
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 12px 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 11.5px;
        font-weight: 700;
        color: var(--text-dark);
    }}
    .legend-item {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .legend-dot {{
        width: 11px;
        height: 11px;
        border-radius: 50%;
    }}

    @media print {{
        .no-print {{ display: none !important; }}
        body {{ padding: 0; background: #FFFFFF !important; }}
        .section-card, .sub-card, .header-banner {{ break-inside: avoid; box-shadow: none !important; }}
    }}
    @media (max-width: 768px) {{
        .header-banner {{ grid-template-columns: 1fr; }}
        .brand-col {{ border-right: none; border-bottom: 1px solid rgba(255,255,255,0.15); padding-right: 0; padding-bottom: 14px; }}
        .meta-grid {{ grid-template-columns: 1fr 1fr; }}
        .exec-grid {{ grid-template-columns: 1fr 1fr !important; }}
        .grid-2 {{ grid-template-columns: 1fr; }}
    }}
</style>
</head>
<body>
<div class="container">

    <!-- BARRA DE AÇÃO INTERATIVA (OCULTA NA IMPRESSÃO) -->
    <div class="action-bar no-print">
        <div style="font-size:12px; color:#475569;">
            💡 <strong>Laudo Interativo GENUA:</strong> Clique em qualquer caixa de <strong>Conclusão</strong>, <strong>Meta</strong> ou no <strong>Resumo Executivo</strong> abaixo para editar o texto antes de imprimir.
        </div>
        <button class="btn-print" onclick="window.print()">🖨️ Imprimir / Salvar PDF</button>
    </div>

    <!-- 1. CABEÇALHO INSTITUCIONAL GENUA -->
    <div class="header-banner">
        <div class="brand-col">
            <div class="logo-box">
                {logo_html}
            </div>
            <div class="header-pill">Relatório de Evolução Clínica</div>
            <div class="header-pill" style="color:#A5F3FC; border-color:rgba(165,243,252,0.3);">Genua Evolution Report</div>
        </div>
        <div class="meta-grid">
            {meta_items_html}
        </div>
    </div>

    <!-- 2. RESUMO EXECUTIVO DINÂMICO -->
    {html_resumo_executivo}

    <!-- 3. EVOLUÇÃO DA DOR (EVA) — ÚLTIMAS 10 SESSÕES -->
    {html_secao_dor}

    <!-- 4. RELACIONAL FUNCIONAL (DOR 0-10) — ÚLTIMAS 10 SESSÕES -->
    {html_secao_testes}

    <!-- 5. AMPLITUDE DE MOVIMENTO (ADM) -->
    {html_secao_adm}

    <!-- 6. QUESTIONÁRIO / PROM APLICADO -->
    {html_secao_prom}

    <!-- 7. OBJETIVO DO PACIENTE (SANE & GROC -7 A +7) — ÚLTIMAS 10 SESSÕES -->
    {html_secao_sane}

    <!-- 8. FORÇA MUSCULAR (SOMENTE SE DINAMOMETRIA > 0 KGF) -->
    {html_secao_forca}

    <!-- 9. CHECKLIST DOS 6 PONTOS DE OBJETIVO PARA ATINGIR (GATEKEEPERS PBE) -->
    {html_secao_gatekeepers}

    <!-- 10. CONCLUSÃO FINAL E RECOMENDAÇÕES -->
    <div class="section-card">
        <div class="section-title">CONCLUSÃO FINAL E RECOMENDAÇÕES CLÍNICAS</div>
        <div class="final-textarea" contenteditable="true" spellcheck="false">
            {_esc(conclusao_livre)}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px; padding-top:12px; border-top:1px solid #F1F5F9; font-size:11.5px; color:#64748B;">
            <div><strong>GENUA Instituto de Fisioterapia Esportiva</strong> · Prática Baseada em Evidência</div>
            <div contenteditable="true">Fisioterapeuta Responsável · Data: {_esc(data_emissao)}</div>
        </div>
    </div>

    <!-- LEGENDA SEMAFÓRICA DE INTERPRETAÇÃO -->
    <div class="legend-bar">
        <span style="color:#103E55; font-weight:800;">Legenda de Interpretação</span>
        <div class="legend-item"><span class="legend-dot" style="background:#16A34A;"></span> Normal / Favorável (Meta atingida)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#EAB308;"></span> Déficit ou melhora discreta</div>
        <div class="legend-item"><span class="legend-dot" style="background:#F97316;"></span> Déficit moderado / Atenção</div>
        <div class="legend-item"><span class="legend-dot" style="background:#DC2626;"></span> Déficit importante / Alerta</div>
    </div>

</div>
</body>
</html>"""
    return html_completo


# ============================================================
# FUNÇÃO 2: gerar_laudo() — RETROCOMPATIBILIDADE FPDF (BYTES)
# ============================================================
class LaudoGenua(FPDF):
    """PDF FPDF com identidade visual Genua."""

    def header(self):
        self.set_fill_color(*AZUL_GENUA)
        self.rect(0, 0, 140, 4, 'F')
        self.set_fill_color(*TEAL_GENUA)
        self.rect(140, 0, 70, 4, 'F')
        self.set_y(8)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 7)
        self.set_text_color(*CINZA_TEXTO)
        self.cell(0, 10, f'GENUA Fisioterapia Esportiva - Pagina {self.page_no()}/{{nb}}', 0, 0, 'C')


def gerar_laudo(paciente_nome, dados_aval=None, historico=None, insights=None, fenotipo=None, *args, **kwargs):
    """Mantém geração direta de bytes PDF via FPDF2 caso chamada por rotas legadas."""
    dados_aval, hist = _normalizar_entradas(dados_aval, historico)
    pdf = LaudoGenua()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_fill_color(*AZUL_GENUA)
    pdf.rect(10, 10, 190, 22, 'F')
    pdf.set_xy(15, 15)
    pdf.set_font('Arial', 'B', 15)
    pdf.set_text_color(*BRANCO)
    pdf.cell(0, 6, f'RELATORIO DE EVOLUCAO GENUA - {_limpar_texto(paciente_nome).upper()}', 0, 1, 'L')
    pdf.set_x(15)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*TEAL_VIVO)
    pdf.cell(0, 5, f'Emitido em {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'L')

    pdf.set_y(38)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(*PRETO_TEXTO)
    dx = dados_aval.get('Diagnostico_Clinico', '-')
    lado = dados_aval.get('Lado_Acometido', '-')
    med = dados_aval.get('Medico_Indicador', '-')
    obj = dados_aval.get('Objetivo_Paciente', '-')
    sane_b = dados_aval.get('SANE_Baseline_Pct', 30)
    pdf.cell(0, 6, f'Diagnostico: {_limpar_texto(dx)} | Lado: {_limpar_texto(lado)} | Indicacao: {_limpar_texto(med)}', 0, 1, 'L')
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 6, f'Objetivo Funcional (SANE Inicial {sane_b}%): {_limpar_texto(obj)}', 0, 1, 'L')

    try:
        saida = pdf.output(dest='S')
        if isinstance(saida, str):
            return saida.encode('latin-1')
        return bytes(saida)
    except Exception:
        return bytes(pdf.output())
