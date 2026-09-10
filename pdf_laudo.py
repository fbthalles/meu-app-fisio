"""
GENUA | Laudo Clínico (PDF) — Estilo Clássico-Apple
====================================================
Documento sério para médico e paciente, com refinamento visual:
fundo branco, muito respiro, tipografia limpa, hierarquia clara,
detalhes em cor da marca. Captura TODOS os dados preenchidos no app.

Design:
  - Muito espaço em branco (margens largas, ar entre blocos)
  - Régua fina de cor da marca como assinatura visual das seções
  - KPIs sem caixa pesada: número grande + label discreto
  - Tabelas limpas (linhas horizontais sutis, sem grade pesada)
  - Cinzas suaves para texto secundário

Robustez (produção):
  - Toda escrita respeita a largura útil (nunca "horizontal space")
  - Larguras de coluna normalizadas
  - Campos ausentes são omitidos, nunca quebram

Dependências: fpdf2, matplotlib
"""
import io
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF


# ============================================================
# PALETA (cores da marca + neutros Apple)
# ============================================================
AZUL = (16, 62, 85)
TEAL = (57, 142, 155)
TINTA = (29, 37, 43)
GRAFITE = (90, 100, 108)
CINZA = (140, 150, 158)
LINHA = (228, 232, 236)
GELO = (247, 249, 251)
VERDE = (52, 168, 92)
AMBAR = (200, 150, 0)
CORAL = (214, 70, 70)
BRANCO = (255, 255, 255)

PAG_W = 210.0
PAG_H = 297.0
MARGEM = 16.0
UTIL = PAG_W - 2 * MARGEM   # 178 mm


# ============================================================
# HELPERS DE DADOS
# ============================================================
def _txt(v):
    if v is None:
        return ""
    return str(v).encode('latin-1', 'replace').decode('latin-1')


def _vazio(v):
    if v is None:
        return True
    return str(v).strip().lower() in ("", "-", "n/a", "na", "none", "nan", "nenhum", "nenhuma")


def _fmt(v, default="-"):
    return _txt(v) if not _vazio(v) else default


def _num(v, default=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _pares(texto):
    if _vazio(texto):
        return []
    out = []
    for tk in str(texto).replace("|", " ").split():
        if ":" in tk:
            k, _, val = tk.partition(":")
            out.append((k.strip(), val.strip()))
    return out


def _bilateral(texto):
    d = dict(_pares(texto))
    return d.get("Dir", "-"), d.get("Esq", "-")


def _func_score(t):
    return {
        "Sem Dor (0)": 10, "Sem Dor": 10,
        "Dor Leve (1 - 3)": 7, "Dor Leve": 7,
        "Dor Moderada (4 - 7)": 4, "Dor Moderada": 4,
        "Dor Grave (8 - 10)": 1, "Dor Grave": 1,
        "Incapaz (Não realiza)": 0, "Incapaz": 0, "Não testado": None,
    }.get(t)


def _norm(ws):
    total = sum(ws)
    if total <= 0:
        return [UTIL / len(ws)] * len(ws)
    f = UTIL / total
    return [w * f for w in ws]


def _fig(fig, dpi=200):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf


def _estilo_ax(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#C8D0D6')
    ax.spines['bottom'].set_color('#C8D0D6')
    ax.tick_params(colors='#5A646C', labelsize=8)
    ax.grid(True, axis='y', ls='-', lw=0.5, alpha=0.25, color='#8C969E')
    ax.set_axisbelow(True)


# ============================================================
# CLASSE PDF
# ============================================================
class Laudo(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_margins(MARGEM, 20, MARGEM)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_y(10)
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(*AZUL)
        self.cell(UTIL / 2, 4, 'GENUA', 0, 0, 'L')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*CINZA)
        self.cell(UTIL / 2, 4, 'Laudo de Evolucao Clinica', 0, 1, 'R')
        self.set_draw_color(*LINHA)
        self.set_line_width(0.2)
        self.line(MARGEM, 15, PAG_W - MARGEM, 15)
        self.set_y(22)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*LINHA)
        self.set_line_width(0.2)
        self.line(MARGEM, self.get_y(), PAG_W - MARGEM, self.get_y())
        self.set_y(-11)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(*CINZA)
        self.cell(UTIL / 2, 6, _txt('GENUA HealthTech  -  Documento confidencial (LGPD)'), 0, 0, 'L')
        self.cell(UTIL / 2, 6, _txt(f'{self.page_no()} / {{nb}}'), 0, 0, 'R')

    def secao(self, numero, titulo):
        if self.get_y() > 255:
            self.add_page()
        self.ln(3)
        y = self.get_y()
        self.set_fill_color(*TEAL)
        self.rect(MARGEM, y + 0.5, 1.2, 6, 'F')
        self.set_xy(MARGEM + 5, y)
        self.set_font('Helvetica', 'B', 12.5)
        self.set_text_color(*AZUL)
        rotulo = f'{numero}   {titulo}' if numero else titulo
        self.cell(UTIL - 5, 7, _txt(rotulo), 0, 1, 'L')
        self.ln(1.5)

    def rotulo(self, texto):
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(*TEAL)
        self.set_x(MARGEM)
        self.cell(UTIL, 5, _txt(texto.upper()), 0, 1, 'L')

    def paragrafo(self, texto, cor=TINTA, tam=9.5, estilo=''):
        self.set_font('Helvetica', estilo, tam)
        self.set_text_color(*cor)
        self.set_x(MARGEM)
        self.multi_cell(UTIL, 5, _txt(texto))

    def campo(self, label, valor, lw=52):
        if _vazio(valor):
            return
        y0 = self.get_y()
        self.set_x(MARGEM)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(*GRAFITE)
        self.multi_cell(lw, 5.5, _txt(label))
        y1 = self.get_y()
        self.set_xy(MARGEM + lw, y0)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*TINTA)
        self.multi_cell(UTIL - lw, 5.5, _fmt(valor))
        self.set_y(max(y1, self.get_y()) + 0.5)

    def kpi(self, x, y, w, label, valor, sub="", cor=AZUL):
        self.set_xy(x, y)
        self.set_font('Helvetica', '', 7.5)
        self.set_text_color(*CINZA)
        self.cell(w, 4, _txt(label.upper())[:32], 0, 2)
        self.set_font('Helvetica', 'B', 21)
        self.set_text_color(*cor)
        self.cell(w, 10, _txt(valor)[:16], 0, 2)
        if sub:
            self.set_font('Helvetica', '', 7.5)
            self.set_text_color(*GRAFITE)
            self.cell(w, 4, _txt(sub)[:34], 0, 2)

    def tabela(self, headers, rows, larguras=None, fonte=8.5):
        n = len(headers)
        larguras = _norm(larguras or [1] * n)
        self.set_x(MARGEM)
        self.set_font('Helvetica', 'B', fonte)
        self.set_text_color(*AZUL)
        self.set_fill_color(*GELO)
        for i, h in enumerate(headers):
            mc = max(4, int(larguras[i] / 1.7))
            al = 'L' if i == 0 else 'C'
            self.cell(larguras[i], 8, _txt(h)[:mc], 0, 0, al, fill=True)
        self.ln()
        self.set_draw_color(*TEAL)
        self.set_line_width(0.3)
        self.line(MARGEM, self.get_y(), MARGEM + sum(larguras), self.get_y())
        self.set_font('Helvetica', '', fonte)
        for row in rows:
            if self.get_y() > 262:
                self.add_page()
            self.set_x(MARGEM)
            for i, v in enumerate(row):
                mc = max(4, int(larguras[i] / 1.7))
                al = 'L' if i == 0 else 'C'
                self.set_text_color(*(TINTA if i == 0 else GRAFITE))
                self.set_font('Helvetica', 'B' if i == 0 else '', fonte)
                self.cell(larguras[i], 7, _txt(str(v))[:mc], 0, 0, al)
            self.ln()
            self.set_draw_color(*LINHA)
            self.set_line_width(0.15)
            self.line(MARGEM, self.get_y(), MARGEM + sum(larguras), self.get_y())
        self.ln(3)

    def status_chip(self, texto, cor):
        self.set_font('Helvetica', 'B', 8)
        w = self.get_string_width(_txt(texto)) + 8
        self.set_fill_color(*cor)
        self.set_text_color(*BRANCO)
        self.cell(w, 6, _txt(texto), 0, 1, 'C', fill=True)


# ============================================================
# PÁGINAS
# ============================================================
def _capa(pdf, paciente, aval, hist, fen, insights):
    pdf.add_page()
    pdf.ln(6)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*TEAL)
    pdf.set_x(MARGEM)
    pdf.cell(UTIL, 5, 'GENUA  -  INTELIGENCIA CLINICA', 0, 1, 'L')
    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 26)
    pdf.set_text_color(*AZUL)
    pdf.set_x(MARGEM)
    pdf.cell(UTIL, 13, 'Laudo de Evolucao Clinica', 0, 1, 'L')
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(*GRAFITE)
    pdf.set_x(MARGEM)
    pdf.cell(UTIL, 7, 'Fisioterapia esportiva baseada em evidencia', 0, 1, 'L')
    pdf.ln(6)
    pdf.set_draw_color(*LINHA)
    pdf.set_line_width(0.3)
    pdf.line(MARGEM, pdf.get_y(), PAG_W - MARGEM, pdf.get_y())
    pdf.ln(7)

    idade = aval.get('Idade', '-') if aval else '-'
    membro = aval.get('Membro', 'Joelho') if aval else 'Joelho'
    dx = aval.get('Diagnostico_Clinico', '') if aval else ''
    prof = aval.get('Profissional_ID', '') if aval else ''
    periodo = f"{hist[0].get('Data','?')[:10]} a {hist[-1].get('Data','?')[:10]}" if hist else '-'

    linhas = [
        ('Paciente', paciente, 'Emissao', datetime.now().strftime('%d/%m/%Y')),
        ('Segmento', membro, 'Idade', f'{idade} anos' if idade != '-' else '-'),
        ('Diagnostico de triagem', dx or '-', 'Periodo avaliado', periodo),
        ('Fisioterapeuta', prof or '-', 'Sessoes', str(len(hist)) if hist else '0'),
    ]
    for l_esq, v_esq, l_dir, v_dir in linhas:
        y = pdf.get_y()
        pdf.set_xy(MARGEM, y)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*CINZA)
        pdf.cell(UTIL / 2 - 4, 4.5, _txt(l_esq.upper()), 0, 2)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*TINTA)
        pdf.cell(UTIL / 2 - 4, 6, _fmt(v_esq), 0, 0)
        pdf.set_xy(MARGEM + UTIL / 2, y)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*CINZA)
        pdf.cell(UTIL / 2, 4.5, _txt(l_dir.upper()), 0, 2)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*TINTA)
        pdf.cell(UTIL / 2, 6, _fmt(v_dir), 0, 1)
        pdf.ln(4)

    if fen and fen.get('fenotipo') not in (None, 'generico'):
        pdf.ln(2)
        y = pdf.get_y()
        pdf.set_fill_color(*GELO)
        pdf.rect(MARGEM, y, UTIL, 12, 'F')
        pdf.set_fill_color(*TEAL)
        pdf.rect(MARGEM, y, 1.2, 12, 'F')
        pdf.set_xy(MARGEM + 5, y + 2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*AZUL)
        pdf.cell(UTIL - 6, 4, _txt(f"Fenotipo clinico: {fen.get('label','-')}"), 0, 2)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*GRAFITE)
        tempo = fen.get('tempo_esperado_semanas', '?')
        pdf.cell(UTIL - 6, 4, _txt(f"Tempo esperado de reabilitacao: {tempo} semanas"), 0, 1)
        pdf.set_y(y + 12)

    pdf.ln(8)
    pdf.set_draw_color(*LINHA)
    pdf.line(MARGEM, pdf.get_y(), PAG_W - MARGEM, pdf.get_y())
    pdf.ln(6)
    pdf.rotulo('Sumario executivo')
    pdf.ln(2)

    if hist:
        dor_i, dor_a = _num(hist[0].get('Dor')), _num(hist[-1].get('Dor'))
        d_dor = dor_i - dor_a
        flex_a = _num(hist[-1].get('Flexao'))
        flex_d = flex_a - _num(hist[0].get('Flexao'))
        lsi = insights.get('lsi') if insights else None
        yk = pdf.get_y()
        w = UTIL / 3
        cor_dor = VERDE if d_dor > 0 else CORAL if d_dor < 0 else GRAFITE
        pdf.kpi(MARGEM, yk, w, 'Reducao da dor', f'{dor_i:.0f} -> {dor_a:.0f}', f'{d_dor:+.0f} pts na EVA', cor_dor)
        cor_flex = VERDE if flex_d > 0 else CORAL if flex_d < 0 else GRAFITE
        pdf.kpi(MARGEM + w, yk, w, 'Flexao (ADM)', f'{flex_a:.0f}', f'{flex_d:+.0f} graus', cor_flex)
        if lsi and lsi.get('valor') is not None:
            v = lsi['valor']
            cor_lsi = VERDE if v >= 90 else AMBAR if v >= 85 else CORAL
            pdf.kpi(MARGEM + 2 * w, yk, w, 'Simetria (LSI)', f'{v:.0f}%', 'Ref: >=90%', cor_lsi)
        else:
            pdf.kpi(MARGEM + 2 * w, yk, w, 'Sessoes', str(len(hist)), 'no periodo', AZUL)
        pdf.set_y(yk + 22)
    else:
        pdf.paragrafo('Ainda nao ha sessoes de evolucao registradas.', cor=CINZA, estilo='I')


def _anamnese(pdf, aval):
    if not aval:
        return
    pdf.add_page()
    pdf.secao('01', 'Anamnese')
    pdf.campo('Queixa principal', aval.get('QP'))
    pdf.campo('Historia (HMA)', aval.get('HMA'))
    pdf.campo('Sinais e sintomas', aval.get('Sinais_Sintomas'))
    pdf.campo('Fatores de alivio', aval.get('Fatores_Alivio'))
    pdf.campo('Fatores de piora', aval.get('Fatores_Piora'))
    pdf.campo('Tratamentos previos', aval.get('Tratamentos_Previos'))
    pdf.campo('Comorbidades', aval.get('Comorbidades'))
    pdf.campo('Fatores sociais', aval.get('Fatores_Sociais'))
    pdf.campo('Qualidade do sono', aval.get('Sono'))

    pdf.secao('02', 'Caracterizacao da dor')
    pdf.campo('Classificacao', aval.get('Class_Dor'))
    pdf.campo('Origem', aval.get('Origem_Dor'))
    pdf.campo('Zonas de dor', aval.get('Zonas_Dor'))
    pdf.campo('Mapa de dor', aval.get('Mapa_Dor'))

    pdf.secao('03', 'Bandeiras (triagem de risco)')
    pdf.campo('Bandeiras vermelhas', aval.get('Red_Flags'))
    pdf.campo('Bandeiras amarelas', aval.get('Yellow_Cog'))


def _exame(pdf, aval):
    if not aval:
        return
    pdf.add_page()
    pdf.secao('04', 'Exame fisico')
    pdf.rotulo('Inspecao e palpacao')
    pdf.ln(1)
    pdf.campo('Derrame articular', aval.get('Derrame'))
    pdf.campo('Sinal de Godet', aval.get('Godet'))
    pdf.campo('Temperatura', aval.get('Temperatura'))
    pdf.campo('Pele', aval.get('Pele'))
    pdf.campo('Alinhamento', aval.get('Alinhamento'))
    pdf.campo('Marcha', aval.get('Marcha'))
    pdf.campo('Trofismo', aval.get('Trofismo'))
    pdf.campo('Perimetria', aval.get('Perimetria'))
    pdf.campo('Palpacao', aval.get('Palpacao'))
    pdf.campo('Flexibilidade', aval.get('Flexibilidade'))

    pdf.secao('05', 'Mobilidade articular (goniometria)')
    fd, fe = _bilateral(aval.get('ADM_Joelho_Flexao'))
    ed, ee = _bilateral(aval.get('ADM_Joelho_Extensao'))
    ld, le = _bilateral(aval.get('Lunge_Test'))
    pdf.tabela(['Medida', 'Direito', 'Esquerdo'],
               [['Flexao (graus)', fd, fe],
                ['Extensao (graus)', ed, ee],
                ['Lunge Test (cm)', ld, le]],
               larguras=[2, 1.3, 1.3])

    fg_d = dict(_pares(aval.get('Forca_Geral_Dir')))
    fg_e = dict(_pares(aval.get('Forca_Geral_Esq')))
    din_d = dict(_pares(aval.get('Dinamometria_Dir')))
    din_e = dict(_pares(aval.get('Dinamometria_Esq')))
    if any(fg_d) or any(din_d):
        pdf.secao('06', 'Forca muscular')
        movs = [('Ext', 'Extensao'), ('Flex', 'Flexao'), ('Abd', 'Abducao'), ('Add', 'Aducao')]
        rows = [[nome, fg_d.get(k, '-'), fg_e.get(k, '-'), din_d.get(k, '-'), din_e.get(k, '-')]
                for k, nome in movs]
        pdf.tabela(['Movimento', 'Grau D', 'Grau E', 'Dinam. D', 'Dinam. E'],
                   rows, larguras=[1.6, 1, 1, 1, 1], fonte=8.5)
        pdf.paragrafo('Grau = forca manual (0-5)   -   Dinam. = dinamometria (kgf)',
                      cor=CINZA, tam=7.5, estilo='I')

    pdf.secao('07', 'Testes especiais ortopedicos')
    pdf.campo('Ligamentares', aval.get('Testes_Ligamentares'))
    pdf.campo('Meniscais', aval.get('Testes_Meniscais'))
    pdf.campo('Femoropatelar', aval.get('Testes_Femoropatelar'))

    pdf.secao('08', 'Controle motor')
    pdf.campo('Globais', aval.get('CM_Globais'), lw=34)
    pdf.campo('Membro direito', aval.get('CM_Membro_Dir'), lw=34)
    pdf.campo('Membro esquerdo', aval.get('CM_Membro_Esq'), lw=34)


def _proms(pdf, aval):
    if not aval:
        return
    pdf.add_page()
    pdf.secao('09', 'Metricas baseadas em evidencia (PROMs)')
    pdf.paragrafo('Questionarios validados que medem a perspectiva do paciente. '
                  'MCID = menor diferenca clinicamente relevante.', cor=GRAFITE, tam=8.5)
    pdf.ln(2)
    proms = [
        ("LEFS", "Funcao geral MMII", aval.get("LEFS_Pct"), "%", "9 pts (Binkley 1999)", aval.get("Interpretacao_LEFS")),
        ("VISA-P", "Tendinopatia patelar", aval.get("VISA_P_Pts"), "pts", "13 pts (Hernandez 2014)", aval.get("Interpretacao_VISA_P")),
        ("Lysholm", "Ligamento / menisco", aval.get("Lysholm_Pts"), "pts", "10 pts (Briggs 2009)", aval.get("Interpretacao_Lysholm")),
        ("WOMAC", "Osteoartrite", aval.get("WOMAC_Pct"), "%", "~12% (Angst 2001)", aval.get("Interpretacao_WOMAC")),
        ("KOOS", "Score agregado", aval.get("KOOS_Pct"), "%", "8-10 (Roos 2003)", None),
        ("IKDC", "Subjetivo joelho", aval.get("IKDC_Pct"), "%", "9 pts (Irrgang 2006)", None),
    ]
    rows = [[n, ind, f'{_num(s):.0f}{u}', mc, _fmt(itp)]
            for n, ind, s, u, mc, itp in proms if _num(s) > 0]
    if rows:
        pdf.tabela(['PROM', 'Indicacao', 'Score', 'MCID', 'Interpretacao'],
                   rows, larguras=[1.1, 1.9, 1, 1.9, 2.1], fonte=8.5)
    else:
        pdf.paragrafo('Nenhum PROM preenchido nesta avaliacao.', cor=CINZA, estilo='I')

    pdf.secao('10', 'Exames complementares')
    pdf.campo('Exames apresentados', aval.get('Exames_Apresentados'))
    pdf.campo('Laudo dos exames', aval.get('Laudo_Exames'))


def _evolucao(pdf, hist):
    if not hist:
        return
    pdf.add_page()
    datas = [ev.get('Data', '')[5:] or '?' for ev in hist]
    dores = [_num(ev.get('Dor')) for ev in hist]

    pdf.secao('11', 'Evolucao da dor (EVA)')
    if len(hist) >= 2:
        fig, ax = plt.subplots(figsize=(7.2, 2.7))
        ax.plot(datas, dores, marker='o', color='#103E55', lw=2.4, ms=5,
                mfc='#103E55', mec='white', mew=1.2, zorder=3)
        ax.fill_between(range(len(datas)), dores, alpha=0.07, color='#103E55')
        if dores[0] > 2:
            ax.axhline(dores[0] - 2, color='#34A85C', ls=(0, (4, 3)), lw=1.2, alpha=.8, label='Meta MCID (-2)')
            ax.legend(fontsize=8, loc='upper right', frameon=False)
        ax.set_ylabel('EVA (0-10)', fontsize=9, color='#1D252B', fontweight='bold')
        ax.set_ylim(-0.5, 10.5)
        _estilo_ax(ax)
        plt.xticks(fontsize=7.5)
        pdf.image(_fig(fig), x=MARGEM, w=UTIL)
        pdf.ln(3)

    func, testes_evol = [], {}
    for ev in hist:
        t = ev.get('Testes_Funcionais', {})
        if isinstance(t, dict) and t:
            ss = []
            for nome, res in t.items():
                s = _func_score(res)
                if s is not None:
                    ss.append(s)
                testes_evol.setdefault(nome, []).append(res)
            func.append(sum(ss) / len(ss) if ss else np.nan)
        else:
            func.append(np.nan)

    if len(hist) >= 2 and any(not np.isnan(f) for f in func):
        pdf.secao('12', 'Correlacao dor x funcao')
        pdf.paragrafo('Quando a dor cai e a funcao sobe, as linhas se cruzam: sinal de eficacia.',
                      cor=GRAFITE, tam=8.5)
        pdf.ln(1)
        fig2, ax1 = plt.subplots(figsize=(7.2, 2.8))
        ax1.plot(datas, dores, color='#D64646', marker='o', lw=2.4, ms=5,
                 mec='white', mew=1.2, label='Dor (EVA)', zorder=3)
        ax1.set_ylabel('Dor (EVA)', color='#D64646', fontsize=9, fontweight='bold')
        ax1.set_ylim(-0.5, 10.5)
        ax2 = ax1.twinx()
        arr = np.array(func, dtype=float)
        m = ~np.isnan(arr)
        if m.sum() >= 2:
            it = np.interp(range(len(arr)), np.where(m)[0], arr[m])
            ax2.plot(datas, it, color='#34A85C', marker='s', lw=2.4, ms=5,
                     mec='white', mew=1.2, ls=(0, (5, 2)), label='Funcao', zorder=3)
        ax2.set_ylabel('Funcao (0-10)', color='#34A85C', fontsize=9, fontweight='bold')
        ax2.set_ylim(-0.5, 10.5)
        _estilo_ax(ax1)
        ax2.spines['top'].set_visible(False)
        ax2.tick_params(labelsize=8, colors='#5A646C')
        l1, la1 = ax1.get_legend_handles_labels()
        l2, la2 = ax2.get_legend_handles_labels()
        ax1.legend(l1 + l2, la1 + la2, loc='upper center', ncol=2, fontsize=8, frameon=False)
        plt.xticks(fontsize=7.5)
        pdf.image(_fig(fig2), x=MARGEM, w=UTIL)
        pdf.ln(3)

        if testes_evol:
            rows = []
            for nome, rl in testes_evol.items():
                ini, fim = rl[0], rl[-1]
                si, sf = _func_score(ini), _func_score(fim)
                var = f'{sf - si:+.0f}' if (si is not None and sf is not None) else '-'
                rows.append([nome, ini, fim, var])
            pdf.rotulo('Evolucao por teste funcional')
            pdf.ln(1)
            pdf.tabela(['Teste', 'Inicio', 'Atual', 'Delta'], rows,
                       larguras=[2, 1.6, 1.6, 0.8], fonte=8.5)

    pdf.secao('13', 'Historico completo de sessoes')
    rows = [[ev.get('Data', '-')[:10], ev.get('Dor', '-'), ev.get('EVA_Semanal', '-'),
             ev.get('Flexao', '-'), _fmt(ev.get('Extensao')),
             _fmt(ev.get('Inchaço', ev.get('Inchaco'))), _fmt(ev.get('Sono'))] for ev in hist]
    pdf.tabela(['Data', 'Dor', 'EVA Sem', 'Flexao', 'Extensao', 'Inchaco', 'Sono'],
               rows, larguras=[1.6, 0.8, 1, 1, 1.6, 1.4, 1.4], fonte=8)


def _ia(pdf, insights):
    if not insights:
        return
    pdf.add_page()
    pdf.secao('14', 'Analise de inteligencia clinica')
    pdf.paragrafo('Analise por regras clinicas validadas na literatura, transparente e auditavel. '
                  'A decisao final e do fisioterapeuta.', cor=GRAFITE, tam=8.5)
    pdf.ln(2)

    est = insights.get('estagnacao')
    if est and est.get('status') not in ('insuficiente', None):
        mapa = {'estagnacao': ('ESTAGNACAO DETECTADA', AMBAR),
                'melhora': ('EVOLUCAO POSITIVA', VERDE),
                'piora': ('PIORA CLINICA', CORAL)}
        rot, cor = mapa.get(est['status'], ('ANALISE', AZUL))
        pdf.set_x(MARGEM)
        pdf.status_chip(rot, cor)
        pdf.ln(1)
        pdf.paragrafo(est.get('racional', ''))
        pdf.paragrafo(f"Referencia: {est.get('referencia', '')}", cor=CINZA, tam=7.5, estilo='I')
        pdf.ln(2)

    lsi = insights.get('lsi')
    if lsi and lsi.get('valor') is not None:
        pdf.rotulo(f"Limb Symmetry Index - {lsi['valor']}%")
        pdf.ln(1)
        pdf.paragrafo(lsi.get('acao', ''))
        pdf.paragrafo(f"Referencia: {lsi.get('referencia', '')}", cor=CINZA, tam=7.5, estilo='I')
        pdf.ln(2)

    band = insights.get('bandeiras', [])
    if band:
        pdf.rotulo('Bandeiras clinicas ativas')
        pdf.ln(1)
        for b in band:
            tipo = str(b.get('tipo', 'info')).upper()
            cor = CORAL if tipo == 'VERMELHA' else AMBAR if tipo == 'AMARELA' else TEAL
            pdf.set_x(MARGEM)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(*cor)
            pdf.multi_cell(UTIL, 5, _txt(f"[{tipo}]  {b.get('gatilho', '')}"))
            pdf.paragrafo(f"Conduta sugerida: {b.get('acao', '')}", tam=8.5)
            pdf.paragrafo(f"Referencia: {b.get('referencia', '')}", cor=CINZA, tam=7.5, estilo='I')
            pdf.ln(1.5)
    else:
        pdf.paragrafo('Nenhuma bandeira clinica ativa - perfil de baixo risco.', cor=VERDE)


def _assinatura(pdf, aval):
    pdf.add_page()
    pdf.ln(12)
    pdf.paragrafo('Este laudo foi gerado pelo sistema GENUA de Inteligencia Clinica. As analises '
                  'baseiam-se em regras clinicas validadas pela literatura citada. O diagnostico e a '
                  'conduta sao de responsabilidade exclusiva do fisioterapeuta responsavel.',
                  cor=GRAFITE, tam=9)
    pdf.ln(24)
    prof = aval.get('Profissional_ID', '') if aval else ''
    pdf.set_draw_color(*TINTA)
    pdf.set_line_width(0.3)
    cx = PAG_W / 2
    pdf.line(cx - 55, pdf.get_y(), cx + 55, pdf.get_y())
    pdf.ln(2)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*TINTA)
    pdf.set_x(MARGEM)
    pdf.cell(UTIL, 6, 'Fisioterapeuta responsavel', 0, 1, 'C')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*GRAFITE)
    if not _vazio(prof):
        pdf.cell(UTIL, 5, _txt(prof), 0, 1, 'C')
    pdf.cell(UTIL, 5, 'GENUA Instituto de Fisioterapia Esportiva', 0, 1, 'C')
    pdf.cell(UTIL, 5, _txt(f'CREFITO: _______________     Data: {datetime.now().strftime("%d/%m/%Y")}'), 0, 1, 'C')


# ============================================================
# FUNÇÃO PÚBLICA
# ============================================================
def gerar_laudo(paciente_nome, dados_aval, historico, insights=None, fenotipo=None):
    """Monta o laudo completo (estilo clássico-Apple) e retorna bytes do PDF."""
    aval = dados_aval or {}
    hist = sorted(historico, key=lambda x: x.get('Data', '')) if historico else []

    pdf = Laudo()
    pdf.alias_nb_pages()

    _capa(pdf, paciente_nome, aval, hist, fenotipo, insights)
    _anamnese(pdf, aval)
    _exame(pdf, aval)
    _proms(pdf, aval)
    _evolucao(pdf, hist)
    _ia(pdf, insights)
    _assinatura(pdf, aval)

    saida = pdf.output()
    return bytes(saida) if isinstance(saida, (bytes, bytearray)) else saida.encode('latin-1')
