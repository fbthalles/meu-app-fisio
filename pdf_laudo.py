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
from services.medidas import lados_dinamometria, lsi_dinamometria, nota_dor_gesto
import io
import os
import base64
import html
import re
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


def _medida(valor, minimo, maximo):
    numero = _safe_float(valor, float("nan"))
    return numero if minimo <= numero <= maximo else float("nan")


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
    texto = str(val_ext).strip().lower()
    if "completa" in texto:
        return 0.0
    numero = re.search(r"[-+]?\d+(?:[.,]\d+)?", texto)
    return abs(_safe_float(numero.group())) if numero else float("nan")


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
    hist_ord = sorted(hist_limpo, key=lambda registro: _data_sessao(registro.get('Data')) or datetime.min)
    return dados_aval, hist_ord


def _fig_to_base64(fig, dpi=300, facecolor='#FFFFFF'):
    """Converte figura Matplotlib em string Base64 PNG a 300 DPI."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor=facecolor)
    buf.seek(0)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def _data_sessao(valor):
    texto = str(valor or "").strip()[:10]
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def _formatar_data_curta(data_raw) -> str:
    data = _data_sessao(data_raw)
    return data.strftime("%d/%m") if data else ""


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
        dores_d = [_medida(e.get('Dor_Dir'), 0, 10) for e in evs]
        dores_e = [_medida(e.get('Dor_Esq'), 0, 10) for e in evs]
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
        dores = [_medida(e.get('Dor'), 0, 10) for e in evs]
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
        tf = tf if isinstance(tf, dict) else {}
        tf_num = tf_num if isinstance(tf_num, dict) else {}
        for nome in dict.fromkeys([*tf, *tf_num]):
            if nome not in nomes_testes and nota_dor_gesto(tf.get(nome), tf_num.get(nome)) is not None:
                nomes_testes.append(nome)

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
        for e in evs:
            tf = e.get('Testes_Funcionais', {})
            tf_num = e.get('Testes_Funcionais_Dor_Num', {})
            resp = tf.get(t_nome) if isinstance(tf, dict) else None
            dor_num_k = tf_num.get(t_nome) if isinstance(tf_num, dict) else None
            sc_dor = nota_dor_gesto(resp, dor_num_k)
            valores_y.append(sc_dor if sc_dor is not None else np.nan)

        arr_y = np.array(valores_y, dtype=float)
        mask = ~np.isnan(arr_y)
        if mask.sum() >= 1:
            testes_plotados += 1
            ax.plot(x_idx, arr_y, color=cor_t, lw=2.4, marker='o', markersize=6.5, label=t_nome, zorder=3 + idx_t)
            for xi, yi in zip(x_idx[mask], arr_y[mask]):
                ax.annotate(f"{yi:.1f}".replace(".", ","), (xi, yi),
                            textcoords="offset points", xytext=(0, 7), ha='center',
                            fontsize=8, fontweight='bold', color=cor_t)

            v_ini = arr_y[mask][0]
            v_fim = arr_y[mask][-1]
            indices = np.flatnonzero(mask)
            primeira = marcos[indices[0]][2]
            ultima = marcos[indices[-1]][2]
            if len(indices) == 1:
                texto = f"{t_nome}: registro único de {v_fim:g}/10 em {ultima}."
            else:
                texto = f"{t_nome}: dor de {v_ini:g}/10 em {primeira} e {v_fim:g}/10 em {ultima}."
            if v_fim < v_ini:
                melhoraram += 1
            conclusoes_testes.append(("neutro", texto))

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
        valores = [_medida(m[1].get('SANE_Pct'), 0, 100) for m in marcos]
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
def _mostrador_adm(valor, limite, legenda, cor):
    """Mesma geometria para os dois arcos; cada legenda identifica sua escala."""
    if not np.isfinite(valor):
        return '<span>Não avaliada</span>'
    fracao = min(max(valor / limite, 0), 1)
    angulo = math.pi * fracao
    x = 100 - 80 * math.cos(angulo)
    y = 100 - 80 * math.sin(angulo)
    return f"""
    <svg viewBox="0 0 200 125" role="img" aria-label="{valor:g} graus · {legenda}">
        <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="#E2E8F0" stroke-width="12"/>
        <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="{cor}" stroke-width="12"
              pathLength="100" stroke-dasharray="{100 * fracao:.2f} 101"/>
        <circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="{cor}" stroke="white" stroke-width="2"/>
        <text x="100" y="82" text-anchor="middle" font-size="29" font-weight="800">{valor:g}°</text>
        <text x="100" y="102" text-anchor="middle" font-size="11">{legenda}</text>
        <text x="20" y="120" text-anchor="middle" font-size="10">0°</text>
        <text x="180" y="120" text-anchor="middle" font-size="10">{limite}°{'+' if limite == 10 else ''}</text>
    </svg>"""


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
    sessao_atual = hist[-1] if hist else {}
    dor_atual = _medida(sessao_atual.get("Dor"), 0, 10)
    dor_inicial = _medida(hist[0].get("Dor"), 0, 10) if hist else float("nan")
    tem_dor_preenchida = bool(np.isfinite(dor_atual))
    html_secao_dor = ""

    if tem_dor_preenchida or any(np.isfinite(_medida(h.get("Dor"), 0, 10)) for h in hist):
        txt_kpi_dor = f"{dor_atual:g}/10" if tem_dor_preenchida else "Não avaliada"
        sub_kpi_dor = "Sessão selecionada"
        conc_dor_txt = f"EVA na sessão selecionada: {txt_kpi_dor}."
        status_conc_dor = "amarelo"
        cor_kpi_dor = "#103E55"
        icone_kpi_dor = "EVA"
        if n_sessoes > 1 and tem_dor_preenchida and np.isfinite(dor_inicial):
            sub_kpi_dor = f"{dor_inicial:g} → {dor_atual:g}/10"
            conc_dor_txt = f"EVA inicial de {dor_inicial:g}/10 e atual de {dor_atual:g}/10."

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
        sub_kpi_func = "com redução da dor na janela exibida"

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
            <p>Dor de 0 a 10. Registros antigos por faixa de dor usam valores aproximados.</p>
            {boxes_conclusao_testes_html}
        </div>
        """

    # --- 4. AMPLITUDE DE MOVIMENTO (ADM) ---
    adm_fl_d_av = _extrair_chave_str(dados_aval.get("ADM_Joelho_Flexao", ""), "Dir", 0.0)
    adm_fl_e_av = _extrair_chave_str(dados_aval.get("ADM_Joelho_Flexao", ""), "Esq", 0.0)
    lado_str_low = str(lado_acom).lower()
    adm_base_aval = adm_fl_e_av if "esquerdo" in lado_str_low else adm_fl_d_av

    flex_atual = _medida(sessao_atual.get("Flexao"), 0, 180) if hist else adm_base_aval
    tem_adm_preenchida = bool(np.isfinite(flex_atual)) if hist else adm_base_aval > 0
    ext_raw = sessao_atual.get("Extensao")
    ext_atu_deg = _extrair_def_extensao_graus(ext_raw)
    tem_extensao = bool(np.isfinite(ext_atu_deg))
    html_secao_adm = ""
    if tem_adm_preenchida or tem_extensao:
        data_adm = _data_sessao(sessao_atual.get("Data")) if hist else _data_sessao(dados_aval.get("Data_Avaliacao"))
        origem_adm = data_adm.strftime("%d/%m/%Y") if data_adm else ""
        grafico_flex = _mostrador_adm(flex_atual if tem_adm_preenchida else float("nan"), 135, "Referência 135°", "#103E55")
        grafico_ext = _mostrador_adm(ext_atu_deg, 10, "Completa" if ext_atu_deg == 0 else "Déficit de extensão", "#2E8B9A")
        html_secao_adm = f"""
        <div class="section-card"><div class="section-title">Amplitude de movimento</div>
        <p>{_esc(origem_adm)}</p>
        <div class="adm-medidas"><div><strong>Flexão</strong>{grafico_flex}</div><div><strong>Extensão</strong>{grafico_ext}</div></div>
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

    html_secao_sane = ""
    sane_base = _medida(dados_aval.get("SANE_Baseline_Pct"), 0, 100)
    sane_atual = _medida(sessao_atual.get("SANE_Pct"), 0, 100)
    groc_ult = hist[-1].get('GROC_Score') if hist else None

    if np.isfinite(sane_atual) and np.isfinite(sane_base):
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
            <div class="section-title">OBJETIVO FUNCIONAL DO PACIENTE · EVOLUÇÃO DO SANE (%) — ÚLTIMAS {max(1, len(ultimas_10))} SESSÕES</div>
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
        vd = vd if np.isfinite(vd) and vd > 0 else 0.0
        ve = ve if np.isfinite(ve) and ve > 0 else 0.0
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
            if min(vd, ve) <= 0:
                lado, valor = ("Direito", vd) if vd > 0 else ("Esquerdo", ve)
                cards_forca_html += f"<p><strong>{nome_g}</strong> · {lado}: {valor:g} kgf · LSI indisponível (medida unilateral).</p>"
                continue
            max_v = max(vd, ve)
            avaliado, referencia = lados_dinamometria(vd, ve, lado_acom)
            lsi_tec = lsi_dinamometria(avaliado, referencia)
            deficit_pct = 100.0 * (1 - min(vd, ve) / max_v)
            lado_def = "D" if vd < ve else ("E" if ve < vd else "")

            if pref_g == "Ext" or idx_g == 0:
                deficit_ref_resumo = deficit_pct
                if pref_g == "Ext":
                    lsi_quad_din = lsi_tec

            if lsi_tec > 100:
                cor_def = "#2E8B9A"
                badge_def = "maior força no lado acometido"
                st_forca = "neutro"
                conc_f_txt = f"{nome_g}: lado acometido {avaliado:g} kgf, contralateral {referencia:g} kgf (LSI {lsi_tec:g}%)."
            elif deficit_pct <= 10.0:
                cor_def = "#16A34A"
                badge_def = "normal / simétrico"
                st_forca = "verde"
                conc_f_txt = f"Simetria isométrica adequada em {nome_g} na dinamometria ({vd:.1f} kgf vs {ve:.1f} kgf · Déficit de {deficit_pct:.0f}% ≤ 10%, LSI de {lsi_tec:g}%)."
            elif deficit_pct <= 20.0:
                cor_def = "#EAB308"
                badge_def = "déficit discreto"
                st_forca = "amarelo"
                conc_f_txt = f"Déficit discreto de {deficit_pct:.0f}% do lado {lado_def} em {nome_g} ({vd:.1f} kgf vs {ve:.1f} kgf · LSI: {lsi_tec:g}% · meta ≥ 90%)."
            elif deficit_pct <= 30.0:
                cor_def = "#F97316"
                badge_def = "déficit moderado"
                st_forca = "laranja"
                conc_f_txt = f"Déficit moderado de {deficit_pct:.0f}% do lado {lado_def} em {nome_g} ({vd:.1f} kgf vs {ve:.1f} kgf · LSI: {lsi_tec:g}%). Intensificar fortalecimento unilateral."
            else:
                cor_def = "#DC2626"
                badge_def = "déficit importante"
                st_forca = "vermelho"
                conc_f_txt = f"Déficit importante de {deficit_pct:.0f}% do lado {lado_def} em {nome_g} ({vd:.1f} kgf vs {ve:.1f} kgf · LSI: {lsi_tec:g}%). Prioridade máxima na reabilitação."

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
                    <strong>LSI = força do lado avaliado ÷ força de referência × 100</strong>
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
                        <span class="deficit-sub">LSI: {lsi_tec:g}% · ref. ≥ 90%</span>
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

        if lsi_quad_din is not None:
            cor_kpi_forca = "#16A34A" if deficit_ref_resumo <= 10 else ("#D97706" if deficit_ref_resumo <= 20 else "#DC2626")
            txt_kpi_forca = f"{deficit_ref_resumo:.0f}% déficit" if deficit_ref_resumo > 0 else "Simétrico"
            if lsi_quad_din > 100:
                cor_kpi_forca = "#2E8B9A"
                txt_kpi_forca = "Maior força no lado acometido"
            sub_kpi_forca = f"LSI Dinamometria: {lsi_quad_din:g}%"

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
        inchaco_raw = ult_sessao.get('Inchaço', ult_sessao.get('Inchaco', None))
        inchaco_grau = _mapear_inchaco_grau(inchaco_raw)

        pass_val = ult_sessao.get('PASS_Atingido')
        if pass_val is None:
            pass_str = str(ult_sessao.get('PASS_Satisfacao', '') or '')
            pass_bool = pass_str.startswith("👍") or "sim" in pass_str.lower()
        else:
            pass_bool = bool(pass_val) if isinstance(pass_val, bool) else str(pass_val).strip().lower() in ["true", "1", "sim"]

        crit_1_ok = (dor_atual <= 2.0) if tem_dor_preenchida else None
        crit_2_ok = (inchaco_grau <= 1) if _tem_valor_util(inchaco_raw) and str(inchaco_raw).lower() != "nan" else None
        crit_3_ok = (ext_atu_deg == 0.0) if tem_extensao else None
        crit_4_ok = (flex_atual >= 125.0) if tem_adm_preenchida else None
        crit_5_ok = (lsi_quad_din is not None and lsi_quad_din >= 90.0)
        crit_6_ok = (sane_atual >= 85.0 and pass_bool) if np.isfinite(sane_atual) and (pass_val is not None or ult_sessao.get("PASS_Satisfacao")) else None

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
                f"Atual: Grau {inchaco_grau}/3 ({inchaco_raw})" if crit_2_ok is not None else "Não avaliado",
                "Stroke Test PBE"
            ),
            (
                "3. Extensão Terminal Completa (0°)",
                crit_3_ok,
                f"Atual: {'Completa (0°)' if ext_atu_deg == 0 else f'Déficit de {ext_atu_deg:.0f}°'}" if tem_extensao else "Não avaliada",
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
                f"Atual: LSI {lsi_quad_din:g}% (Dinamometria kgf)" if lsi_quad_din is not None else "Opcional / Aguardando Dinamometria",
                "Grindem et al., 2016"
            ),
            (
                "6. Meta Subjetiva Atingida (SANE ≥ 85% + PASS Sim)",
                crit_6_ok,
                f"SANE: {sane_atual:.0f}% · PASS: {'Satisfeito (Sim)' if pass_bool else 'Em evolução'}" if crit_6_ok is not None else 'Avaliação incompleta',
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
        if np.isfinite(sane_atual):
            partes_sintese.append(f"capacidade funcional percebida (SANE) em {sane_atual:.0f}%")
        if lsi_quad_din is not None:
            partes_sintese.append(f"LSI de quadríceps na dinamometria em {lsi_quad_din:g}%")

        conclusao_livre = ("Medidas registradas: " + ", ".join(partes_sintese) + "."
                           if partes_sintese else "Dados insuficientes para resumir a evolução.")

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
    .adm-medidas svg {{ width:100%; max-width:160px; display:block; margin:6px auto; fill:#103E55; }}
    .adm-medidas {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); align-items:center; text-align:center; break-inside:avoid; }}
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
