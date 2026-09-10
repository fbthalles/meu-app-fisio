"""
GENUA | Laudo Clínico (HTML) — Estilo Dark / Vanguarda
=======================================================
Gera um relatório visual dark-mode, no estilo da referência da clínica:
KPIs grandes coloridos, cards com cantos arredondados, gráficos SVG,
tabelas limpas. Zero dependência de bibliotecas de PDF.

Como vira PDF:
  O HTML é exibido/baixado e o usuário salva como PDF pelo navegador
  (Ctrl+P -> Salvar como PDF). O CSS já traz regras @media print para
  o resultado impresso sair perfeito.

Por que HTML e não FPDF:
  FPDF não faz dark-mode, gradiente, cantos arredondados nem tipografia
  fina. HTML/CSS entrega exatamente o visual "estilo Apple" desejado.

Uso:
  html = gerar_laudo_html(paciente, dados_aval, historico, insights, fenotipo)
  st.download_button("Baixar", html, "laudo.html", "text/html")
  # ou components.html(html, height=...) para pré-visualizar
"""
from datetime import datetime
from html import escape


# ============================================================
# PALETA (cores da marca em tema escuro)
# ============================================================
CORES = {
    "bg": "#0B1F2A",          # fundo geral (azul-petróleo bem escuro)
    "card": "#0F2836",        # cards
    "card2": "#13303F",       # cards elevados
    "borda": "#1E3D4D",
    "primaria": "#103E55",
    "teal": "#3FB5C4",        # teal vibrante para dark
    "teal_soft": "#5FD0DE",
    "texto": "#EAF2F5",
    "texto2": "#9FB3BD",      # secundário
    "verde": "#34D399",
    "ambar": "#FBBF24",
    "coral": "#F87171",
    "roxo": "#A78BFA",
    "rosa": "#F472B6",
}


# ============================================================
# HELPERS
# ============================================================
def _e(v, default="—"):
    if v is None:
        return default
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "none", "n/a", "-"):
        return default
    return escape(s)


def _num(v, d=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return d


def _vazio(v):
    if v is None:
        return True
    return str(v).strip().lower() in ("", "-", "n/a", "na", "none", "nan", "nenhum", "nenhuma")


def _pares(t):
    if _vazio(t):
        return {}
    d = {}
    for tk in str(t).replace("|", " ").split():
        if ":" in tk:
            k, _, val = tk.partition(":")
            d[k.strip()] = val.strip()
    return d


def _bilateral(t):
    d = _pares(t)
    return d.get("Dir", "—"), d.get("Esq", "—")


def _func_score(t):
    return {
        "Sem Dor (0)": 10, "Sem Dor": 10,
        "Dor Leve (1 - 3)": 7, "Dor Leve": 7,
        "Dor Moderada (4 - 7)": 4, "Dor Moderada": 4,
        "Dor Grave (8 - 10)": 1, "Dor Grave": 1,
        "Incapaz (Não realiza)": 0, "Incapaz": 0, "Não testado": None,
    }.get(t)


# ============================================================
# GERADORES DE GRÁFICO (SVG puro, sem libs)
# ============================================================
def _svg_linha(series, labels, w=640, h=220, ymax=10):
    """
    Gráfico de linhas em SVG.
    series: lista de dicts {nome, cor, valores:[...], dashed:bool}
    """
    pad_l, pad_r, pad_t, pad_b = 40, 20, 20, 34
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    n = max(len(labels), 1)
    step = plot_w / max(n - 1, 1)

    def x(i):
        return pad_l + i * step

    def y(v):
        return pad_t + plot_h - (v / ymax) * plot_h

    svg = [f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet" '
           f'style="display:block">']

    # grid horizontal
    for g in range(0, ymax + 1, max(1, ymax // 5)):
        yy = y(g)
        svg.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{w-pad_r}" y2="{yy:.1f}" '
                   f'stroke="{CORES["borda"]}" stroke-width="0.8" opacity="0.5"/>')
        svg.append(f'<text x="{pad_l-8}" y="{yy+3:.1f}" fill="{CORES["texto2"]}" '
                   f'font-size="10" text-anchor="end">{g}</text>')

    # labels do eixo x
    for i, lab in enumerate(labels):
        svg.append(f'<text x="{x(i):.1f}" y="{h-12}" fill="{CORES["texto2"]}" '
                   f'font-size="9.5" text-anchor="middle">{escape(str(lab))}</text>')

    # linhas + área + pontos
    for s in series:
        vals = s["valores"]
        cor = s["cor"]
        pts = [(x(i), y(v)) for i, v in enumerate(vals) if v is not None]
        if len(pts) < 1:
            continue
        d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        dash = 'stroke-dasharray="6 4"' if s.get("dashed") else ""
        # área sob a curva
        if s.get("area"):
            area = (f'M{pts[0][0]:.1f},{y(0):.1f} '
                    + " ".join(f"L{px:.1f},{py:.1f}" for px, py in pts)
                    + f' L{pts[-1][0]:.1f},{y(0):.1f} Z')
            svg.append(f'<path d="{area}" fill="{cor}" opacity="0.10"/>')
        svg.append(f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="2.4" '
                   f'stroke-linejoin="round" stroke-linecap="round" {dash}/>')
        for px, py in pts:
            svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.6" fill="{CORES["bg"]}" '
                       f'stroke="{cor}" stroke-width="2"/>')

    svg.append('</svg>')
    return "".join(svg)


def _svg_barras(cats, series, w=640, h=240, ymax=None):
    """
    Barras agrupadas. series: [{nome, cor, valores:[...]}]
    """
    pad_l, pad_r, pad_t, pad_b = 40, 16, 20, 46
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    n = max(len(cats), 1)
    grupo_w = plot_w / n
    n_series = max(len(series), 1)
    barra_w = (grupo_w * 0.62) / n_series

    if ymax is None:
        allv = [v for s in series for v in s["valores"] if v is not None]
        ymax = max(allv) * 1.15 if allv else 10
    ymax = max(ymax, 1)

    def y(v):
        return pad_t + plot_h - (v / ymax) * plot_h

    svg = [f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet" style="display:block">']

    # grid
    grid_step = ymax / 4
    for k in range(5):
        g = grid_step * k
        yy = y(g)
        svg.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{w-pad_r}" y2="{yy:.1f}" '
                   f'stroke="{CORES["borda"]}" stroke-width="0.8" opacity="0.5"/>')
        svg.append(f'<text x="{pad_l-8}" y="{yy+3:.1f}" fill="{CORES["texto2"]}" '
                   f'font-size="10" text-anchor="end">{g:.0f}</text>')

    for gi, cat in enumerate(cats):
        base_x = pad_l + gi * grupo_w + grupo_w * 0.19
        for si, s in enumerate(series):
            v = s["valores"][gi] if gi < len(s["valores"]) else None
            if v is None:
                continue
            bx = base_x + si * barra_w
            by = y(v)
            bh = pad_t + plot_h - by
            svg.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{barra_w-2:.1f}" height="{bh:.1f}" '
                       f'rx="3" fill="{s["cor"]}"/>')
        svg.append(f'<text x="{pad_l + gi*grupo_w + grupo_w/2:.1f}" y="{h-24}" '
                   f'fill="{CORES["texto2"]}" font-size="9" text-anchor="middle">{escape(str(cat)[:14])}</text>')

    svg.append('</svg>')
    return "".join(svg)


def _legenda(series):
    itens = "".join(
        f'<span class="leg"><i style="background:{s["cor"]}"></i>{escape(s["nome"])}</span>'
        for s in series
    )
    return f'<div class="legenda">{itens}</div>'


# ============================================================
# COMPONENTES DE LAYOUT
# ============================================================
def _kpi(label, valor, sub, cor):
    return f'''
    <div class="kpi">
      <div class="kpi-label">{escape(label)}</div>
      <div class="kpi-valor" style="color:{cor}">{valor}</div>
      <div class="kpi-sub">{sub}</div>
    </div>'''


def _card(titulo, corpo, num=""):
    n = f'<span class="card-num">{num}</span>' if num else ""
    return f'''
    <section class="card">
      <h2 class="card-titulo">{n}{escape(titulo)}</h2>
      {corpo}
    </section>'''


def _campos(pares):
    linhas = ""
    for label, valor in pares:
        if _vazio(valor):
            continue
        linhas += f'<div class="linha"><span class="lbl">{escape(label)}</span><span class="val">{_e(valor)}</span></div>'
    return f'<div class="campos">{linhas}</div>' if linhas else '<p class="vazio">Sem dados registrados.</p>'


def _tabela(headers, rows):
    th = "".join(f'<th>{escape(h)}</th>' for h in headers)
    tr = ""
    for row in rows:
        tds = "".join(
            f'<td class="{"td-key" if i==0 else ""}">{_e(c)}</td>'
            for i, c in enumerate(row)
        )
        tr += f'<tr>{tds}</tr>'
    return f'<table class="tab"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def _barra_progresso(pct, cor):
    pct = max(0, min(100, pct))
    return f'''<div class="prog"><div class="prog-fill" style="width:{pct:.0f}%;background:{cor}"></div></div>'''


# ============================================================
# CSS
# ============================================================
def _css():
    c = CORES
    return f'''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
        font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
        background:{c["bg"]}; color:{c["texto"]};
        -webkit-font-smoothing:antialiased; letter-spacing:-.01em;
        padding:0; line-height:1.55;
    }}
    .page {{ max-width:820px; margin:0 auto; padding:32px 28px 60px; }}

    /* Cabeçalho */
    .top {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:28px; }}
    .brand {{ display:flex; align-items:center; gap:14px; }}
    .logo {{
        width:52px; height:52px; border-radius:15px;
        background:linear-gradient(135deg,{c["teal"]},{c["primaria"]});
        display:flex; align-items:center; justify-content:center;
        font-weight:800; font-size:26px; color:#fff;
        box-shadow:0 8px 24px rgba(63,181,196,.25);
    }}
    .brand h1 {{ font-size:19px; font-weight:800; letter-spacing:.02em; }}
    .brand p {{ font-size:11px; color:{c["texto2"]}; font-weight:500; letter-spacing:.06em; text-transform:uppercase; }}
    .status-chip {{
        background:rgba(52,211,153,.12); color:{c["verde"]};
        border:1px solid rgba(52,211,153,.3);
        padding:7px 15px; border-radius:20px; font-size:11px; font-weight:700;
        letter-spacing:.05em; text-transform:uppercase;
    }}
    .top-data {{ font-size:11px; color:{c["texto2"]}; margin-top:8px; text-align:right; }}

    /* Ficha do paciente */
    .ficha {{
        background:{c["card"]}; border:1px solid {c["borda"]};
        border-radius:20px; padding:22px 24px; margin-bottom:24px;
        display:grid; grid-template-columns:repeat(3,1fr); gap:18px 24px;
    }}
    .ficha .item .k {{ font-size:10px; color:{c["texto2"]}; text-transform:uppercase; letter-spacing:.06em; font-weight:600; margin-bottom:4px; }}
    .ficha .item .v {{ font-size:15px; font-weight:700; color:{c["texto"]}; }}

    /* KPIs */
    .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:26px; }}
    .kpi {{
        background:{c["card"]}; border:1px solid {c["borda"]};
        border-radius:18px; padding:18px 18px 16px;
        transition:transform .2s;
    }}
    .kpi-label {{ font-size:10.5px; color:{c["texto2"]}; text-transform:uppercase; letter-spacing:.05em; font-weight:600; }}
    .kpi-valor {{ font-size:32px; font-weight:800; letter-spacing:-.03em; margin:6px 0 2px; line-height:1; }}
    .kpi-sub {{ font-size:11px; color:{c["texto2"]}; font-weight:500; }}

    /* Cards */
    .card {{
        background:{c["card"]}; border:1px solid {c["borda"]};
        border-radius:22px; padding:24px 26px; margin-bottom:20px;
    }}
    .card-titulo {{ font-size:15px; font-weight:700; margin-bottom:18px; display:flex; align-items:center; gap:11px; letter-spacing:-.01em; }}
    .card-num {{
        background:linear-gradient(135deg,{c["teal"]},{c["primaria"]});
        color:#fff; font-size:11px; font-weight:800;
        width:26px; height:26px; border-radius:9px;
        display:inline-flex; align-items:center; justify-content:center;
    }}
    .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}

    /* Campos label:valor */
    .campos {{ display:flex; flex-direction:column; gap:0; }}
    .linha {{ display:flex; justify-content:space-between; gap:20px; padding:9px 0; border-bottom:1px solid {c["borda"]}; }}
    .linha:last-child {{ border-bottom:none; }}
    .lbl {{ color:{c["texto2"]}; font-size:12.5px; font-weight:500; flex-shrink:0; }}
    .val {{ color:{c["texto"]}; font-size:12.5px; font-weight:600; text-align:right; }}
    .vazio {{ color:{c["texto2"]}; font-size:12px; font-style:italic; }}

    /* Tabelas */
    .tab {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
    .tab th {{
        text-align:center; color:{c["teal_soft"]}; font-size:10.5px; font-weight:700;
        text-transform:uppercase; letter-spacing:.04em; padding:8px 10px;
        border-bottom:2px solid {c["borda"]};
    }}
    .tab th:first-child {{ text-align:left; }}
    .tab td {{ text-align:center; padding:9px 10px; border-bottom:1px solid {c["borda"]}; color:{c["texto2"]}; }}
    .tab td.td-key {{ text-align:left; color:{c["texto"]}; font-weight:600; }}
    .tab tbody tr:last-child td {{ border-bottom:none; }}

    /* Gráfico */
    .chart {{ margin-top:6px; }}
    .chart-desc {{ font-size:11.5px; color:{c["texto2"]}; margin-bottom:12px; }}
    .legenda {{ display:flex; gap:18px; justify-content:center; margin-top:12px; flex-wrap:wrap; }}
    .leg {{ display:flex; align-items:center; gap:7px; font-size:11px; color:{c["texto2"]}; font-weight:500; }}
    .leg i {{ width:14px; height:4px; border-radius:2px; display:inline-block; }}

    /* Barra de progresso */
    .prog {{ background:{c["borda"]}; border-radius:10px; height:9px; overflow:hidden; margin-top:5px; }}
    .prog-fill {{ height:100%; border-radius:10px; }}

    /* Chip status IA */
    .chip {{ display:inline-block; padding:6px 13px; border-radius:20px; font-size:11px; font-weight:700; letter-spacing:.03em; }}
    .chip.v {{ background:rgba(52,211,153,.14); color:{c["verde"]}; }}
    .chip.a {{ background:rgba(251,191,36,.14); color:{c["ambar"]}; }}
    .chip.c {{ background:rgba(248,113,113,.14); color:{c["coral"]}; }}
    .ia-bloco {{ padding:14px 0; border-bottom:1px solid {c["borda"]}; }}
    .ia-bloco:last-child {{ border-bottom:none; }}
    .ia-racional {{ font-size:13px; margin:8px 0 4px; color:{c["texto"]}; }}
    .ia-ref {{ font-size:10.5px; color:{c["texto2"]}; font-style:italic; }}
    .fenotipo {{
        background:linear-gradient(135deg,rgba(63,181,196,.10),rgba(16,62,85,.10));
        border:1px solid rgba(63,181,196,.25); border-radius:14px;
        padding:14px 18px; margin-bottom:22px;
    }}
    .fenotipo .ft {{ font-size:13.5px; font-weight:700; color:{c["teal_soft"]}; }}
    .fenotipo .fs {{ font-size:11.5px; color:{c["texto2"]}; margin-top:3px; }}

    /* Assinatura */
    .assina {{ margin-top:44px; text-align:center; }}
    .assina .rule {{ width:230px; height:1px; background:{c["borda"]}; margin:0 auto 10px; }}
    .assina .nome {{ font-size:14px; font-weight:700; }}
    .assina .info {{ font-size:11.5px; color:{c["texto2"]}; margin-top:3px; }}

    /* Rodapé */
    .foot {{ margin-top:34px; padding-top:16px; border-top:1px solid {c["borda"]};
             font-size:10px; color:{c["texto2"]}; display:flex; justify-content:space-between; }}

    .disclaimer {{ font-size:11px; color:{c["texto2"]}; margin-bottom:22px; line-height:1.6; }}

    /* IMPRESSÃO (Ctrl+P -> Salvar PDF) */
    @media print {{
        body {{ background:{c["bg"]} !important; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
        .page {{ max-width:100%; padding:12px 14px; }}
        .card, .kpi, .ficha {{ break-inside:avoid; }}
        .card {{ margin-bottom:12px; }}
        @page {{ margin:8mm; size:A4; }}
    }}
    </style>'''


# ============================================================
# FUNÇÃO PÚBLICA
# ============================================================
def gerar_laudo_html(paciente_nome, dados_aval, historico, insights=None, fenotipo=None):
    """
    Gera o laudo completo em HTML (dark, estilo Apple) e retorna a string HTML.
    """
    aval = dados_aval or {}
    hist = sorted(historico, key=lambda x: x.get('Data', '')) if historico else []
    ins = insights or {}
    c = CORES

    # ---- Métricas de topo ----
    dor_i = _num(hist[0].get('Dor')) if hist else 0
    dor_a = _num(hist[-1].get('Dor')) if hist else 0
    d_dor = dor_i - dor_a
    flex_a = _num(hist[-1].get('Flexao')) if hist else 0
    lsi = ins.get('lsi') or {}
    lsi_val = lsi.get('valor')

    blocos = []

    # ===== CABEÇALHO =====
    blocos.append(f'''
    <div class="top">
      <div class="brand">
        <div class="logo">G</div>
        <div><h1>GENUA · Relatório de Evolução</h1>
        <p>Fisioterapia esportiva &amp; performance baseada em evidências</p></div>
      </div>
      <div>
        <span class="status-chip">Jornada em andamento</span>
        <div class="top-data">Emitido em {datetime.now().strftime("%d/%m/%Y")}</div>
      </div>
    </div>''')

    # ===== FICHA =====
    periodo = f"{hist[0].get('Data','?')[:10]} a {hist[-1].get('Data','?')[:10]}" if hist else "—"
    dx = aval.get('Diagnostico_Clinico', '')
    blocos.append(f'''
    <div class="ficha">
      <div class="item"><div class="k">Paciente</div><div class="v">{_e(paciente_nome)}</div></div>
      <div class="item"><div class="k">Condição / HD</div><div class="v">{_e(dx)}</div></div>
      <div class="item"><div class="k">Segmento</div><div class="v">{_e(aval.get("Membro","Joelho"))}</div></div>
      <div class="item"><div class="k">Fisioterapeuta</div><div class="v">{_e(aval.get("Profissional_ID"))}</div></div>
      <div class="item"><div class="k">Idade</div><div class="v">{_e(aval.get("Idade"))} anos</div></div>
      <div class="item"><div class="k">Período avaliado</div><div class="v">{_e(periodo)}</div></div>
    </div>''')

    # ===== FENÓTIPO =====
    if fenotipo and fenotipo.get('fenotipo') not in (None, 'generico'):
        blocos.append(f'''
        <div class="fenotipo">
          <div class="ft">🎯 Fenótipo clínico: {_e(fenotipo.get("label"))}</div>
          <div class="fs">Tempo esperado de reabilitação: {_e(fenotipo.get("tempo_esperado_semanas"))} semanas</div>
        </div>''')

    # ===== KPIs =====
    cor_dor = c["verde"] if d_dor > 0 else c["coral"] if d_dor < 0 else c["texto2"]
    kpis = _kpi("Redução de Dor (EVA)", f'{d_dor:+.0f} pts',
                f'Atual: {dor_a:.0f}/10', cor_dor)
    if lsi_val is not None:
        cor_lsi = c["verde"] if lsi_val >= 90 else c["ambar"] if lsi_val >= 85 else c["coral"]
        kpis += _kpi("Simetria Muscular (LSI)", f'{lsi_val:.0f}%', 'Ref: ≥90%', cor_lsi)
    else:
        kpis += _kpi("Flexão (ADM)", f'{flex_a:.0f}°', 'Amplitude atual', c["teal_soft"])
    # PROM principal
    lefs = _num(aval.get("LEFS_Pct"))
    kpis += _kpi("Escore Funcional", f'{lefs:.0f}%' if lefs > 0 else "—", 'LEFS', c["teal_soft"])
    kpis += _kpi("Sessões", str(len(hist)), 'no período', c["roxo"])
    blocos.append(f'<div class="kpis">{kpis}</div>')

    # ===== GRÁFICO 1: DOR SEMANAL =====
    if len(hist) >= 2:
        labels = [ev.get('Data', '')[5:] or f'S{i+1}' for i, ev in enumerate(hist)]
        dores = [_num(ev.get('Dor')) for ev in hist]
        s1 = {"nome": "Dor (EVA)", "cor": c["teal"], "valores": dores, "area": True}
        svg = _svg_linha([s1], labels)
        corpo = f'<div class="chart-desc">Evolução da intensidade de dor sessão a sessão (0–10).</div><div class="chart">{svg}</div>{_legenda([s1])}'
        blocos.append(_card("Dor Semanal (Escala Visual Analógica)", corpo, "1"))

    # ===== GRÁFICO 2: DOR x FUNÇÃO =====
    func = []
    testes_evol = {}
    for ev in hist:
        t = ev.get('Testes_Funcionais', {})
        if isinstance(t, dict) and t:
            ss = []
            for nome, res in t.items():
                s = _func_score(res)
                if s is not None:
                    ss.append(s)
                testes_evol.setdefault(nome, []).append(res)
            func.append(sum(ss) / len(ss) if ss else None)
        else:
            func.append(None)

    if len(hist) >= 2 and any(f is not None for f in func):
        labels = [ev.get('Data', '')[5:] or f'S{i+1}' for i, ev in enumerate(hist)]
        dores = [_num(ev.get('Dor')) for ev in hist]
        s_dor = {"nome": "Dor (EVA)", "cor": c["coral"], "valores": dores}
        s_fun = {"nome": "Função", "cor": c["verde"], "valores": func, "dashed": True}
        svg = _svg_linha([s_dor, s_fun], labels)
        corpo = f'<div class="chart-desc">Quando a dor cai e a função sobe, as linhas se cruzam — sinal de eficácia terapêutica.</div><div class="chart">{svg}</div>{_legenda([s_dor, s_fun])}'
        # tabela evolução por teste
        if testes_evol:
            rows = []
            for nome, rl in testes_evol.items():
                si, sf = _func_score(rl[0]), _func_score(rl[-1])
                delta = f'{sf-si:+.0f}' if (si is not None and sf is not None) else '—'
                rows.append([nome, rl[0], rl[-1], delta])
            corpo += _tabela(["Teste Provocativo", "Início", "Atual", "Δ"], rows)
        blocos.append(_card("Testes Relacionais-Funcionais", corpo, "2"))

    # ===== ADM (barras de progresso) =====
    fd, fe = _bilateral(aval.get('ADM_Joelho_Flexao'))
    ed, ee = _bilateral(aval.get('ADM_Joelho_Extensao'))
    if not (_vazio(fd) and _vazio(ed)):
        flex_pct = min(100, _num(fd) / 135 * 100) if not _vazio(fd) else 0
        corpo = f'''
        <div class="linha"><span class="lbl">Flexão de Joelho (Dir)</span><span class="val">{_e(fd)}° / ref 135°</span></div>
        {_barra_progresso(flex_pct, c["verde"] if flex_pct>=90 else c["ambar"])}
        <div style="height:14px"></div>
        <div class="linha"><span class="lbl">Extensão de Joelho (Dir)</span><span class="val">{_e(ed)}°</span></div>
        <div style="margin-top:14px" class="grid2">
          <div><div class="lbl" style="margin-bottom:6px">Lado Esquerdo — Flexão</div><span class="val">{_e(fe)}°</span></div>
          <div><div class="lbl" style="margin-bottom:6px">Lado Esquerdo — Extensão</div><span class="val">{_e(ee)}°</span></div>
        </div>'''
        blocos.append(_card("Amplitude de Movimento (Goniometria)", corpo, "3"))

    # ===== FORÇA (barras agrupadas) =====
    fg_d = _pares(aval.get('Dinamometria_Dir'))
    fg_e = _pares(aval.get('Dinamometria_Esq'))
    if fg_d or fg_e:
        movs = [("Ext", "Extensão"), ("Flex", "Flexão"), ("Abd", "Abdução"), ("Add", "Adução")]
        cats = [nome for k, nome in movs if (k in fg_d or k in fg_e)]
        vd = [_num(fg_d.get(k)) for k, nome in movs if (k in fg_d or k in fg_e)]
        ve = [_num(fg_e.get(k)) for k, nome in movs if (k in fg_d or k in fg_e)]
        s1 = {"nome": "Direito (kgf)", "cor": c["verde"], "valores": vd}
        s2 = {"nome": "Esquerdo (kgf)", "cor": c["teal"], "valores": ve}
        svg = _svg_barras(cats, [s1, s2])
        # tabela LSI por grupo
        rows = []
        for k, nome in movs:
            if k in fg_d or k in fg_e:
                dd, ei = _num(fg_d.get(k)), _num(fg_e.get(k))
                mn, mx = min(dd, ei), max(dd, ei)
                lsi_g = (mn / mx * 100) if mx > 0 else 0
                status = "✓ Simétrico" if lsi_g >= 90 else "Déficit"
                rows.append([nome, f'{dd:.0f}', f'{ei:.0f}', f'{lsi_g:.0f}%', status])
        corpo = f'<div class="chart">{svg}</div>{_legenda([s1, s2])}'
        if rows:
            corpo += _tabela(["Grupo Muscular", "Dir", "Esq", "LSI", "Status"], rows)
        blocos.append(_card("Força Isométrica e Índice de Simetria (LSI)", corpo, "4"))

    # ===== PROMs =====
    proms = [
        ("LEFS", aval.get("LEFS_Pct"), "%", aval.get("Interpretacao_LEFS")),
        ("VISA-P", aval.get("VISA_P_Pts"), "pts", aval.get("Interpretacao_VISA_P")),
        ("Lysholm", aval.get("Lysholm_Pts"), "pts", aval.get("Interpretacao_Lysholm")),
        ("WOMAC", aval.get("WOMAC_Pct"), "%", aval.get("Interpretacao_WOMAC")),
        ("KOOS", aval.get("KOOS_Pct"), "%", None),
        ("IKDC", aval.get("IKDC_Pct"), "%", None),
    ]
    rows = [[n, f'{_num(s):.0f}{u}', _e(itp)] for n, s, u, itp in proms if _num(s) > 0]
    if rows:
        blocos.append(_card("Escalas Funcionais (PROMs)",
                            _tabela(["Instrumento", "Score", "Interpretação"], rows), "5"))

    # ===== IA CLÍNICA =====
    ia_corpo = ""
    est = ins.get('estagnacao')
    if est and est.get('status') not in ('insuficiente', None):
        mapa = {'estagnacao': ('Estagnação detectada', 'a'),
                'melhora': ('Evolução positiva', 'v'),
                'piora': ('Piora clínica', 'c')}
        rot, cls = mapa.get(est['status'], ('Análise', 'a'))
        ia_corpo += f'<div class="ia-bloco"><span class="chip {cls}">{rot}</span><div class="ia-racional">{_e(est.get("racional"))}</div><div class="ia-ref">Ref: {_e(est.get("referencia"))}</div></div>'
    if lsi_val is not None:
        ia_corpo += f'<div class="ia-bloco"><div class="ia-racional"><b>LSI: {lsi_val:.0f}%</b> — {_e(lsi.get("acao"))}</div><div class="ia-ref">Ref: {_e(lsi.get("referencia"))}</div></div>'
    for b in ins.get('bandeiras', []):
        tipo = str(b.get('tipo', '')).lower()
        cls = 'c' if 'verm' in tipo else 'a' if 'amar' in tipo else 'v'
        ia_corpo += f'<div class="ia-bloco"><span class="chip {cls}">Bandeira {escape(tipo)}</span><div class="ia-racional">{_e(b.get("gatilho"))}</div><div class="ia-ref">Conduta: {_e(b.get("acao"))} · {_e(b.get("referencia"))}</div></div>'
    if not ia_corpo:
        ia_corpo = '<p class="vazio">Nenhum alerta clínico ativo — perfil de baixo risco.</p>'
    blocos.append(_card("Análise de Inteligência Clínica", ia_corpo, "6"))

    # ===== CONCLUSÃO =====
    blocos.append(_card("Conclusão Clínica e Recomendações", f'''
    <div class="grid2">
      <div>
        <div class="lbl" style="margin-bottom:8px;text-transform:uppercase;font-size:10px;letter-spacing:.05em">Síntese de evolução</div>
        <p style="font-size:13px;color:{c["texto"]}">Evolução clínica {'favorável' if d_dor >= 0 else 'a monitorar'} conforme dados tabulados.</p>
      </div>
      <div>
        <div class="lbl" style="margin-bottom:8px;text-transform:uppercase;font-size:10px;letter-spacing:.05em">Próximos passos &amp; conduta</div>
        <p style="font-size:13px;color:{c["texto"]}">Continuidade do protocolo com progressão de intensidade conforme tolerância.</p>
      </div>
    </div>''', "7"))

    # ===== ASSINATURA =====
    blocos.append(f'''
    <div class="assina">
      <div class="rule"></div>
      <div class="nome">Fisioterapeuta Responsável</div>
      <div class="info">{_e(aval.get("Profissional_ID"))}</div>
      <div class="info">GENUA Instituto de Fisioterapia Esportiva</div>
      <div class="info">CREFITO: _______________ · {datetime.now().strftime("%d/%m/%Y")}</div>
    </div>''')

    # ===== RODAPÉ =====
    blocos.append(f'''
    <div class="foot">
      <span>GENUA HealthTech © 2026 · Documento confidencial (LGPD)</span>
      <span>Relatório gerado eletronicamente</span>
    </div>''')

    corpo_html = "\n".join(blocos)
    return f'''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Laudo GENUA — {escape(paciente_nome)}</title>
{_css()}
</head><body><div class="page">{corpo_html}</div></body></html>'''
