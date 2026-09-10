"""
GENUA | Gerador de Laudo Clínico Completo (PDF)
================================================
Gera um laudo profissional que reflete TODOS os dados preenchidos no app:
cadastro, avaliação inicial completa, evolução (check-ins), PROMs e IA.

Design: identidade visual GENUA (azul-petróleo + teal), tipografia consistente,
tabelas com cabeçalho colorido, KPIs e gráficos em alta resolução.

Robustez (nível produção):
  - Toda escrita de texto passa por helpers que respeitam a largura útil da
    página (never "Not enough horizontal space").
  - Larguras de coluna sempre normalizadas para caber na área útil.
  - Strings compostas do Firestore (ex.: "Ext:0 Flex:0 Abd:0") são parseadas
    e exibidas de forma legível.
  - Campos ausentes/vazios são omitidos ou exibidos como "-", nunca quebram.

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
# PALETA GENUA (RGB)
# ============================================================
AZUL = (16, 62, 85)        # #103E55 primária
TEAL = (57, 142, 155)      # #398E9B secundária
CINZA = (108, 117, 125)    # texto suave
CINZA_CLARO = (244, 247, 249)
CINZA_MEDIO = (210, 218, 224)
VERDE = (40, 167, 69)
AMARELO = (200, 150, 0)
VERMELHO = (220, 53, 69)
BRANCO = (255, 255, 255)
PRETO = (26, 37, 44)

# Geometria da página A4 (mm)
MARGEM_ESQ = 10
MARGEM_DIR = 10
LARGURA_PAGINA = 210
LARGURA_UTIL = LARGURA_PAGINA - MARGEM_ESQ - MARGEM_DIR  # 190 mm


# ============================================================
# HELPERS DE DADOS
# ============================================================
def _txt(valor):
    """Converte para string ASCII-safe (FPDF core fonts = latin-1)."""
    if valor is None:
        return ""
    return str(valor).encode('latin-1', 'replace').decode('latin-1')


def _vazio(valor):
    """True se o valor é vazio/nulo/placeholder."""
    if valor is None:
        return True
    s = str(valor).strip().lower()
    return s in ("", "-", "n/a", "na", "none", "nan")


def _fmt(valor, default="-"):
    """Valor limpo para exibição, com default se vazio."""
    return _txt(valor) if not _vazio(valor) else default


def _num(valor, default=0.0):
    """Converte para float com segurança."""
    try:
        return float(valor)
    except (ValueError, TypeError):
        return default


def _parse_composto(texto):
    """
    Converte "Ext:0.0 Flex:12.5 Abd:3.0 Add:1.0" em
    [("Ext", "0.0"), ("Flex", "12.5"), ...].
    """
    if _vazio(texto):
        return []
    pares = []
    for token in str(texto).replace("|", " ").split():
        if ":" in token:
            chave, _, val = token.partition(":")
            pares.append((chave.strip(), val.strip()))
    return pares


def _parse_bilateral(texto):
    """Converte 'Dir:5.0 Esq:4.5' em (dir, esq)."""
    pares = dict(_parse_composto(texto))
    return pares.get("Dir", "-"), pares.get("Esq", "-")


def _mapa_func_score(resultado_texto):
    """Converte texto do teste funcional em score 0-10 (maior = melhor função)."""
    mapa = {
        "Sem Dor (0)": 10, "Sem Dor": 10,
        "Dor Leve (1 - 3)": 7, "Dor Leve": 7,
        "Dor Moderada (4 - 7)": 4, "Dor Moderada": 4,
        "Dor Grave (8 - 10)": 1, "Dor Grave": 1,
        "Incapaz (Não realiza)": 0, "Incapaz": 0, "Não testado": None,
    }
    return mapa.get(resultado_texto)


def _fig_to_bytes(fig, dpi=200):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def _norm_larguras(col_widths):
    """
    Normaliza a lista de larguras para somar exatamente LARGURA_UTIL,
    garantindo que nenhuma tabela estoure a página.
    """
    total = sum(col_widths)
    if total <= 0:
        return [LARGURA_UTIL / len(col_widths)] * len(col_widths)
    fator = LARGURA_UTIL / total
    return [w * fator for w in col_widths]


# ============================================================
# CLASSE PDF
# ============================================================
class LaudoGenua(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_margins(MARGEM_ESQ, 12, MARGEM_DIR)
        self.set_auto_page_break(auto=True, margin=18)

    # ---------- Cabeçalho / Rodapé ----------
    def header(self):
        self.set_y(6)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*TEAL)
        self.cell(LARGURA_UTIL / 2, 5, 'GENUA | Inteligencia Clinica', 0, 0, 'L')
        self.set_font('Arial', '', 8)
        self.set_text_color(*CINZA)
        self.cell(LARGURA_UTIL / 2, 5, datetime.now().strftime('%d/%m/%Y %H:%M'), 0, 1, 'R')
        self.set_draw_color(*TEAL)
        self.set_line_width(0.4)
        self.line(MARGEM_ESQ, 12, LARGURA_PAGINA - MARGEM_DIR, 12)
        self.set_y(16)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*CINZA_MEDIO)
        self.set_line_width(0.2)
        self.line(MARGEM_ESQ, self.get_y(), LARGURA_PAGINA - MARGEM_DIR, self.get_y())
        self.set_y(-11)
        self.set_font('Arial', 'I', 7)
        self.set_text_color(*CINZA)
        self.cell(0, 6, _txt(f'GENUA HealthTech - Documento confidencial (LGPD) - Pagina {self.page_no()}/{{nb}}'), 0, 0, 'C')

    # ---------- Blocos de layout ----------
    def titulo_secao(self, texto):
        """Faixa de título de seção."""
        if self.get_y() > 250:
            self.add_page()
        self.set_font('Arial', 'B', 11)
        self.set_fill_color(*AZUL)
        self.set_text_color(*BRANCO)
        self.set_x(MARGEM_ESQ)
        self.cell(LARGURA_UTIL, 8, _txt('  ' + texto), 0, 1, 'L', fill=True)
        self.ln(2)

    def subtitulo(self, texto):
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*TEAL)
        self.set_x(MARGEM_ESQ)
        self.cell(LARGURA_UTIL, 5, _txt(texto), 0, 1, 'L')

    def paragrafo(self, texto, cor=PRETO, tam=9, estilo=''):
        self.set_font('Arial', estilo, tam)
        self.set_text_color(*cor)
        self.set_x(MARGEM_ESQ)
        self.multi_cell(LARGURA_UTIL, 4.5, _txt(texto))

    def campo(self, label, valor, label_w=48):
        """Linha 'Label: valor' com quebra automática no valor."""
        if _vazio(valor):
            return
        y0 = self.get_y()
        self.set_x(MARGEM_ESQ)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*AZUL)
        self.multi_cell(label_w, 5, _txt(label), 0, 'L')
        y1 = self.get_y()
        self.set_xy(MARGEM_ESQ + label_w, y0)
        self.set_font('Arial', '', 9)
        self.set_text_color(*PRETO)
        self.multi_cell(LARGURA_UTIL - label_w, 5, _fmt(valor))
        self.set_y(max(y1, self.get_y()))

    def kpi(self, x, y, w, h, label, valor, sub="", cor=AZUL):
        """Cartão de KPI (nunca estoura: usa área interna fixa)."""
        self.set_draw_color(*cor)
        self.set_line_width(0.6)
        self.set_fill_color(*BRANCO)
        self.rect(x, y, w, h, 'D')
        self.set_fill_color(*cor)
        self.rect(x, y, 2.5, h, 'F')
        iw = w - 7
        self.set_xy(x + 5, y + 2.5)
        self.set_font('Arial', '', 7.5)
        self.set_text_color(*CINZA)
        self.cell(iw, 4, _txt(label)[:34], 0, 2)
        self.set_font('Arial', 'B', 18)
        self.set_text_color(*cor)
        self.cell(iw, 9, _txt(valor)[:18], 0, 2)
        if sub:
            self.set_font('Arial', '', 6.5)
            self.set_text_color(*CINZA)
            self.cell(iw, 4, _txt(sub)[:42], 0, 2)

    def tabela(self, headers, rows, larguras=None, alt=True, fonte=8):
        """
        Tabela robusta: larguras normalizadas para LARGURA_UTIL,
        texto truncado por coluna para nunca faltar espaço horizontal.
        """
        n = len(headers)
        if not larguras:
            larguras = [1] * n
        larguras = _norm_larguras(larguras)

        # Cabeçalho
        self.set_x(MARGEM_ESQ)
        self.set_font('Arial', 'B', fonte)
        self.set_fill_color(*AZUL)
        self.set_text_color(*BRANCO)
        for i, h in enumerate(headers):
            max_chars = max(4, int(larguras[i] / 1.7))
            self.cell(larguras[i], 7, _txt(h)[:max_chars], 1, 0, 'C', fill=True)
        self.ln()

        # Linhas
        self.set_font('Arial', '', fonte)
        self.set_text_color(*PRETO)
        for r, row in enumerate(rows):
            # quebra de página preservando cabeçalho
            if self.get_y() > 262:
                self.add_page()
                self.set_x(MARGEM_ESQ)
                self.set_font('Arial', 'B', fonte)
                self.set_fill_color(*AZUL)
                self.set_text_color(*BRANCO)
                for i, h in enumerate(headers):
                    max_chars = max(4, int(larguras[i] / 1.7))
                    self.cell(larguras[i], 7, _txt(h)[:max_chars], 1, 0, 'C', fill=True)
                self.ln()
                self.set_font('Arial', '', fonte)
                self.set_text_color(*PRETO)
            self.set_x(MARGEM_ESQ)
            if alt and r % 2 == 0:
                self.set_fill_color(*CINZA_CLARO)
            else:
                self.set_fill_color(*BRANCO)
            for i, val in enumerate(row):
                max_chars = max(4, int(larguras[i] / 1.7))
                self.cell(larguras[i], 6, _txt(str(val))[:max_chars], 1, 0, 'C', fill=True)
            self.ln()
        self.ln(2)

    def badge(self, texto, cor):
        """Rótulo colorido (status)."""
        self.set_x(MARGEM_ESQ)
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(*cor)
        self.set_text_color(*BRANCO)
        w = self.get_string_width(_txt(texto)) + 6
        self.cell(w, 6, _txt(texto), 0, 1, 'C', fill=True)


# ============================================================
# SEÇÕES DO LAUDO
# ============================================================
def _pagina_capa(pdf, paciente_nome, dados_aval, hist, fenotipo):
    pdf.add_page()
    n_sessoes = len(hist)

    pdf.set_font('Arial', 'B', 22)
    pdf.set_text_color(*AZUL)
    pdf.set_x(MARGEM_ESQ)
    pdf.cell(LARGURA_UTIL, 12, 'Laudo de Evolucao Clinica', 0, 1, 'C')
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(LARGURA_UTIL, 6, 'Fisioterapia Baseada em Evidencia', 0, 1, 'C')
    pdf.ln(6)

    # Ficha do paciente
    y = pdf.get_y()
    pdf.set_fill_color(*CINZA_CLARO)
    pdf.rect(MARGEM_ESQ, y, LARGURA_UTIL, 26, 'F')
    pdf.set_xy(MARGEM_ESQ + 4, y + 3)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*PRETO)
    pdf.cell(LARGURA_UTIL / 2, 6, _txt(f'Paciente: {paciente_nome}'), 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(LARGURA_UTIL / 2 - 4, 6, datetime.now().strftime('Emissao: %d/%m/%Y'), 0, 1, 'R')

    idade = dados_aval.get('Idade', '-') if dados_aval else '-'
    membro = dados_aval.get('Membro', 'Joelho') if dados_aval else 'Joelho'
    dx = dados_aval.get('Diagnostico_Clinico', '') if dados_aval else ''
    pdf.set_x(MARGEM_ESQ + 4)
    pdf.set_font('Arial', '', 10)
    pdf.cell(LARGURA_UTIL / 2, 6, _txt(f'Idade: {idade}   |   Membro: {membro}'), 0, 0)
    pdf.cell(LARGURA_UTIL / 2 - 4, 6, _txt(f'Sessoes: {n_sessoes}'), 0, 1, 'R')
    if not _vazio(dx):
        pdf.set_x(MARGEM_ESQ + 4)
        pdf.cell(LARGURA_UTIL - 4, 6, _txt(f'Diagnostico de Triagem: {dx}'), 0, 1)
    pdf.set_y(y + 30)

    # Fenótipo
    if fenotipo and fenotipo.get('fenotipo') not in (None, 'generico'):
        pdf.set_font('Arial', 'I', 9)
        pdf.set_text_color(*TEAL)
        tempo = fenotipo.get('tempo_esperado_semanas', '?')
        pdf.set_x(MARGEM_ESQ)
        pdf.cell(LARGURA_UTIL, 6, _txt(f"Fenotipo: {fenotipo.get('label','-')} | Reabilitacao esperada: {tempo} semanas"), 0, 1, 'C')
    pdf.ln(3)

    # KPIs
    pdf.titulo_secao('SUMARIO EXECUTIVO')
    if hist:
        dor_ini = _num(hist[0].get('Dor', 0))
        dor_atu = _num(hist[-1].get('Dor', 0))
        d_dor = dor_ini - dor_atu
        flex_ini = _num(hist[0].get('Flexao', 0))
        flex_atu = _num(hist[-1].get('Flexao', 0))
        d_flex = flex_atu - flex_ini

        yk = pdf.get_y()
        w_kpi = (LARGURA_UTIL - 8) / 3
        cor_dor = VERDE if d_dor > 0 else VERMELHO if d_dor < 0 else CINZA
        pdf.kpi(MARGEM_ESQ, yk, w_kpi, 26, 'REDUCAO DA DOR (EVA)',
                f'{dor_ini:.0f} -> {dor_atu:.0f}', f'{d_dor:+.0f} pontos', cor_dor)
        cor_flex = VERDE if d_flex > 0 else VERMELHO if d_flex < 0 else CINZA
        pdf.kpi(MARGEM_ESQ + w_kpi + 4, yk, w_kpi, 26, 'FLEXAO (ADM)',
                f'{flex_atu:.0f} graus', f'{d_flex:+.0f} graus', cor_flex)
        periodo = f"{hist[0].get('Data','?')[:10]} a {hist[-1].get('Data','?')[:10]}"
        pdf.kpi(MARGEM_ESQ + 2 * (w_kpi + 4), yk, w_kpi, 26, 'SESSOES',
                str(len(hist)), periodo, AZUL)
        pdf.set_y(yk + 32)
    else:
        pdf.paragrafo('Ainda nao ha sessoes de evolucao registradas para este paciente.', cor=CINZA, estilo='I')


def _pagina_avaliacao(pdf, dados_aval):
    """Página(s) com TODOS os campos da avaliação inicial."""
    if not dados_aval:
        return
    pdf.add_page()
    pdf.titulo_secao('AVALIACAO INICIAL - ANAMNESE')
    pdf.campo('Queixa Principal (QP)', dados_aval.get('QP'))
    pdf.campo('Historia (HMA)', dados_aval.get('HMA'))
    pdf.campo('Sinais e Sintomas', dados_aval.get('Sinais_Sintomas'))
    pdf.campo('Fatores de Alivio', dados_aval.get('Fatores_Alivio'))
    pdf.campo('Fatores de Piora', dados_aval.get('Fatores_Piora'))
    pdf.campo('Tratamentos Previos', dados_aval.get('Tratamentos_Previos'))
    pdf.campo('Comorbidades', dados_aval.get('Comorbidades'))
    pdf.campo('Fatores Sociais', dados_aval.get('Fatores_Sociais'))
    pdf.campo('Qualidade do Sono', dados_aval.get('Sono'))
    pdf.ln(1)

    pdf.titulo_secao('CARACTERIZACAO DA DOR')
    pdf.campo('Classificacao', dados_aval.get('Class_Dor'))
    pdf.campo('Origem', dados_aval.get('Origem_Dor'))
    pdf.campo('Zonas de Dor', dados_aval.get('Zonas_Dor'))
    pdf.campo('Mapa de Dor', dados_aval.get('Mapa_Dor'))
    pdf.ln(1)

    pdf.titulo_secao('BANDEIRAS (TRIAGEM DE RISCO)')
    pdf.campo('Bandeiras Vermelhas', dados_aval.get('Red_Flags'))
    pdf.campo('Bandeiras Amarelas', dados_aval.get('Yellow_Cog'))
    pdf.ln(1)

    pdf.titulo_secao('EXAME FISICO - INSPECAO E PALPACAO')
    pdf.campo('Derrame Articular', dados_aval.get('Derrame'))
    pdf.campo('Sinal de Godet', dados_aval.get('Godet'))
    pdf.campo('Temperatura', dados_aval.get('Temperatura'))
    pdf.campo('Pele', dados_aval.get('Pele'))
    pdf.campo('Alinhamento', dados_aval.get('Alinhamento'))
    pdf.campo('Marcha', dados_aval.get('Marcha'))
    pdf.campo('Trofismo', dados_aval.get('Trofismo'))
    pdf.campo('Perimetria', dados_aval.get('Perimetria'))
    pdf.campo('Palpacao', dados_aval.get('Palpacao'))
    pdf.campo('Flexibilidade', dados_aval.get('Flexibilidade'))


def _pagina_exame_fisico(pdf, dados_aval):
    """Goniometria, força, dinamometria, testes especiais e controle motor — em tabelas."""
    if not dados_aval:
        return
    pdf.add_page()

    # --- Goniometria (ADM) ---
    pdf.titulo_secao('MOBILIDADE ARTICULAR (GONIOMETRIA)')
    flex_d, flex_e = _parse_bilateral(dados_aval.get('ADM_Joelho_Flexao'))
    ext_d, ext_e = _parse_bilateral(dados_aval.get('ADM_Joelho_Extensao'))
    lunge_d, lunge_e = _parse_bilateral(dados_aval.get('Lunge_Test'))
    pdf.tabela(
        ['Medida', 'Direito', 'Esquerdo'],
        [
            ['Flexao (graus)', flex_d, flex_e],
            ['Extensao (graus)', ext_d, ext_e],
            ['Lunge Test (cm)', lunge_d, lunge_e],
        ],
        larguras=[2, 1.3, 1.3]
    )

    # --- Força Geral e Dinamometria ---
    pdf.titulo_secao('FORCA MUSCULAR')
    fg_d = dict(_parse_composto(dados_aval.get('Forca_Geral_Dir')))
    fg_e = dict(_parse_composto(dados_aval.get('Forca_Geral_Esq')))
    din_d = dict(_parse_composto(dados_aval.get('Dinamometria_Dir')))
    din_e = dict(_parse_composto(dados_aval.get('Dinamometria_Esq')))
    movimentos = [('Ext', 'Extensao'), ('Flex', 'Flexao'), ('Abd', 'Abducao'), ('Add', 'Aducao')]
    if any(fg_d) or any(din_d):
        rows = []
        for chave, nome in movimentos:
            rows.append([
                nome,
                fg_d.get(chave, '-'), fg_e.get(chave, '-'),
                din_d.get(chave, '-'), din_e.get(chave, '-'),
            ])
        pdf.tabela(
            ['Movimento', 'Grau Dir', 'Grau Esq', 'Dinam. Dir', 'Dinam. Esq'],
            rows,
            larguras=[1.6, 1, 1, 1, 1], fonte=8
        )
        pdf.paragrafo('Grau = forca manual (0-5); Dinam. = dinamometria (kgf).', cor=CINZA, tam=7, estilo='I')

    # --- Testes Especiais ---
    pdf.titulo_secao('TESTES ESPECIAIS ORTOPEDICOS')
    pdf.campo('Ligamentares', dados_aval.get('Testes_Ligamentares'))
    pdf.campo('Meniscais', dados_aval.get('Testes_Meniscais'))
    pdf.campo('Femoropatelar', dados_aval.get('Testes_Femoropatelar'))
    pdf.ln(1)

    # --- Controle Motor ---
    pdf.titulo_secao('CONTROLE MOTOR')
    pdf.campo('Globais', dados_aval.get('CM_Globais'), label_w=30)
    pdf.campo('Membro Direito', dados_aval.get('CM_Membro_Dir'), label_w=30)
    pdf.campo('Membro Esquerdo', dados_aval.get('CM_Membro_Esq'), label_w=30)


def _pagina_proms(pdf, dados_aval):
    if not dados_aval:
        return
    pdf.add_page()
    pdf.titulo_secao('METRICAS BASEADAS EM EVIDENCIA (PROMs)')
    pdf.paragrafo('Patient-Reported Outcome Measures: questionarios validados que medem a '
                  'perspectiva do paciente. MCID = menor diferenca clinicamente relevante.',
                  cor=CINZA, tam=8)
    pdf.ln(1)

    proms = [
        ("LEFS", "Funcao Geral MMII", dados_aval.get("LEFS_Pct"), "%", "9 pts (Binkley 1999)", dados_aval.get("Interpretacao_LEFS")),
        ("VISA-P", "Tendinopatia Patelar", dados_aval.get("VISA_P_Pts"), "pts", "13 pts (Hernandez 2014)", dados_aval.get("Interpretacao_VISA_P")),
        ("Lysholm", "Ligamento/Menisco", dados_aval.get("Lysholm_Pts"), "pts", "10 pts (Briggs 2009)", dados_aval.get("Interpretacao_Lysholm")),
        ("WOMAC", "Osteoartrite", dados_aval.get("WOMAC_Pct"), "%", "~12% (Angst 2001)", dados_aval.get("Interpretacao_WOMAC")),
        ("KOOS", "Score Agregado", dados_aval.get("KOOS_Pct"), "%", "8-10 pts (Roos 2003)", None),
        ("IKDC", "Subjetivo Joelho", dados_aval.get("IKDC_Pct"), "%", "9 pts (Irrgang 2006)", None),
    ]
    rows = []
    for nome, indic, score, un, mcid, interp in proms:
        if _num(score) > 0:
            rows.append([nome, indic, f'{_num(score):.0f}{un}', mcid, _fmt(interp)])
    if rows:
        pdf.tabela(['PROM', 'Indicacao', 'Score', 'MCID', 'Interpretacao'],
                   rows, larguras=[1.1, 1.9, 1, 1.9, 2.1], fonte=8)
    else:
        pdf.paragrafo('Nenhum PROM preenchido nesta avaliacao.', cor=CINZA, estilo='I')

    # Exames de imagem
    pdf.ln(1)
    pdf.titulo_secao('EXAMES COMPLEMENTARES')
    pdf.campo('Exames Apresentados', dados_aval.get('Exames_Apresentados'))
    pdf.campo('Laudo dos Exames', dados_aval.get('Laudo_Exames'))


def _pagina_evolucao(pdf, hist):
    """Gráficos de evolução: dor, dor x função, e tabela completa de sessões."""
    if not hist or len(hist) < 1:
        return
    pdf.add_page()

    datas = [ev.get('Data', '')[5:] if ev.get('Data') else '?' for ev in hist]
    dores = [_num(ev.get('Dor', 0)) for ev in hist]

    # --- Gráfico 1: Evolução da Dor ---
    pdf.titulo_secao('CURVA DE EVOLUCAO DA DOR (EVA)')
    if len(hist) >= 2:
        fig, ax = plt.subplots(figsize=(7, 2.8))
        ax.plot(datas, dores, marker='o', color='#103E55', lw=2.5, ms=6, zorder=3)
        ax.fill_between(range(len(datas)), dores, alpha=0.1, color='#103E55')
        dor_ini = dores[0]
        if dor_ini > 2:
            ax.axhline(y=dor_ini - 2, color='#28a745', ls='--', lw=1.3, alpha=0.7, label='Meta MCID (-2)')
            ax.legend(fontsize=8, loc='upper right')
        ax.set_ylabel('Dor (EVA 0-10)', fontweight='bold', fontsize=9)
        ax.set_ylim(-0.5, 10.5)
        ax.grid(True, ls='--', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.xticks(rotation=35, ha='right', fontsize=7)
        pdf.image(_fig_to_bytes(fig), x=MARGEM_ESQ, w=LARGURA_UTIL)
        pdf.ln(2)
    else:
        pdf.paragrafo('Minimo de 2 sessoes necessario para gerar o grafico de evolucao.', cor=CINZA, estilo='I')

    # --- Gráfico 2: Dor x Função ---
    func_scores = []
    testes_evol = {}
    for ev in hist:
        testes = ev.get('Testes_Funcionais', {})
        if isinstance(testes, dict) and testes:
            scores = []
            for nome, res in testes.items():
                s = _mapa_func_score(res)
                if s is not None:
                    scores.append(s)
                testes_evol.setdefault(nome, []).append(res)
            func_scores.append(sum(scores) / len(scores) if scores else np.nan)
        else:
            func_scores.append(np.nan)

    tem_funcao = any(not np.isnan(f) for f in func_scores)
    if len(hist) >= 2 and tem_funcao:
        pdf.titulo_secao('CORRELACAO DOR x FUNCAO')
        pdf.paragrafo('Quando a dor cai e a funcao sobe, as linhas se cruzam: sinal de eficacia terapeutica.',
                      cor=CINZA, tam=8)
        fig2, ax1 = plt.subplots(figsize=(7, 2.9))
        ax1.plot(datas, dores, color='#dc3545', marker='o', lw=2.5, label='Dor (EVA)', zorder=3)
        ax1.set_ylabel('Dor (EVA)', color='#dc3545', fontweight='bold', fontsize=9)
        ax1.set_ylim(-0.5, 10.5)
        ax2 = ax1.twinx()
        arr = np.array(func_scores, dtype=float)
        mask = ~np.isnan(arr)
        if mask.sum() >= 2:
            interp = np.interp(range(len(arr)), np.where(mask)[0], arr[mask])
            ax2.plot(datas, interp, color='#28a745', marker='s', lw=2.5, ls='--', label='Funcao', zorder=3)
        ax2.set_ylabel('Funcao (0-10)', color='#28a745', fontweight='bold', fontsize=9)
        ax2.set_ylim(-0.5, 10.5)
        l1, lab1 = ax1.get_legend_handles_labels()
        l2, lab2 = ax2.get_legend_handles_labels()
        ax1.legend(l1 + l2, lab1 + lab2, loc='upper center', ncol=2, fontsize=8)
        ax1.spines['top'].set_visible(False)
        ax2.spines['top'].set_visible(False)
        plt.xticks(rotation=35, ha='right', fontsize=7)
        pdf.image(_fig_to_bytes(fig2), x=MARGEM_ESQ, w=LARGURA_UTIL)
        pdf.ln(2)

        # Tabela evolução por teste
        if testes_evol:
            rows = []
            for nome, res_list in testes_evol.items():
                ini, fim = res_list[0], res_list[-1]
                si, sf = _mapa_func_score(ini), _mapa_func_score(fim)
                var = f'{sf - si:+.0f} pts' if (si is not None and sf is not None) else '-'
                rows.append([nome, ini, fim, var])
            pdf.subtitulo('Evolucao por Teste Funcional')
            pdf.tabela(['Teste', 'Inicio', 'Atual', 'Variacao'],
                       rows, larguras=[2, 1.6, 1.6, 1], fonte=8)

    # --- Tabela completa de sessões ---
    pdf.titulo_secao('HISTORICO COMPLETO DE SESSOES')
    headers = ['Data', 'Dor', 'EVA Sem', 'Flexao', 'Extensao', 'Inchaco', 'Sono']
    rows = []
    for ev in hist:
        rows.append([
            ev.get('Data', '-')[:10],
            ev.get('Dor', '-'),
            ev.get('EVA_Semanal', '-'),
            ev.get('Flexao', '-'),
            _fmt(ev.get('Extensao'), '-'),
            _fmt(ev.get('Inchaço', ev.get('Inchaco')), '-'),
            _fmt(ev.get('Sono'), '-'),
        ])
    pdf.tabela(headers, rows, larguras=[1.6, 0.8, 1, 1, 1.6, 1.4, 1.4], fonte=7.5)


def _pagina_ia(pdf, insights):
    if not insights:
        return
    pdf.add_page()
    pdf.titulo_secao('ANALISE DE INTELIGENCIA CLINICA (IA)')
    pdf.paragrafo('Analise automatizada por regras clinicas validadas na literatura. '
                  'Transparente e auditavel; a decisao final e do fisioterapeuta.',
                  cor=CINZA, tam=8)
    pdf.ln(1)

    est = insights.get('estagnacao')
    if est and est.get('status') not in ('insuficiente', None):
        mapa = {'estagnacao': ('ESTAGNACAO DETECTADA', AMARELO),
                'melhora': ('EVOLUCAO POSITIVA', VERDE),
                'piora': ('PIORA CLINICA', VERMELHO)}
        rotulo, cor = mapa.get(est['status'], ('ANALISE', AZUL))
        pdf.badge(rotulo, cor)
        pdf.paragrafo(est.get('racional', ''))
        pdf.paragrafo(f"Ref: {est.get('referencia', '')}", cor=CINZA, tam=7, estilo='I')
        pdf.ln(1)

    lsi = insights.get('lsi')
    if lsi and lsi.get('valor') is not None:
        pdf.subtitulo(f"Limb Symmetry Index (LSI): {lsi['valor']}%")
        pdf.paragrafo(lsi.get('acao', ''))
        pdf.paragrafo(f"Ref: {lsi.get('referencia', '')}", cor=CINZA, tam=7, estilo='I')
        pdf.ln(1)

    bandeiras = insights.get('bandeiras', [])
    if bandeiras:
        pdf.subtitulo('Bandeiras Clinicas Ativas')
        for b in bandeiras:
            tipo = str(b.get('tipo', 'info')).upper()
            cor = VERMELHO if tipo == 'VERMELHA' else AMARELO if tipo == 'AMARELA' else AZUL
            pdf.set_x(MARGEM_ESQ)
            pdf.set_font('Arial', 'B', 9)
            pdf.set_text_color(*cor)
            pdf.multi_cell(LARGURA_UTIL, 5, _txt(f"[{tipo}] {b.get('gatilho', '')}"))
            pdf.paragrafo(f"Acao: {b.get('acao', '')}", tam=8)
            pdf.paragrafo(f"Ref: {b.get('referencia', '')}", cor=CINZA, tam=7, estilo='I')
            pdf.ln(1)
    else:
        pdf.paragrafo('Nenhuma bandeira clinica ativa. Perfil de baixo risco.', cor=VERDE)


def _pagina_assinatura(pdf, dados_aval):
    pdf.add_page()
    pdf.ln(15)
    pdf.paragrafo('Este laudo foi gerado pelo sistema GENUA de Inteligencia Clinica. As analises '
                  'baseiam-se em regras clinicas validadas pela literatura cientifica citada. O '
                  'diagnostico e a conduta sao de responsabilidade exclusiva do fisioterapeuta responsavel.',
                  cor=CINZA)
    pdf.ln(20)
    prof = dados_aval.get('Profissional_ID', '') if dados_aval else ''
    pdf.set_draw_color(*PRETO)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())
    pdf.ln(2)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*PRETO)
    pdf.set_x(MARGEM_ESQ)
    pdf.cell(LARGURA_UTIL, 6, 'Fisioterapeuta Responsavel', 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    if not _vazio(prof):
        pdf.cell(LARGURA_UTIL, 5, _txt(prof), 0, 1, 'C')
    pdf.cell(LARGURA_UTIL, 5, 'GENUA Instituto de Fisioterapia Esportiva', 0, 1, 'C')
    pdf.cell(LARGURA_UTIL, 5, _txt(f'CREFITO: ____________   |   Data: {datetime.now().strftime("%d/%m/%Y")}'), 0, 1, 'C')


# ============================================================
# FUNÇÃO PÚBLICA
# ============================================================
def gerar_laudo(paciente_nome, dados_aval, historico, insights=None, fenotipo=None):
    """
    Monta o laudo completo em PDF e retorna os bytes.

    Args:
        paciente_nome: str
        dados_aval: dict da última Avaliacao_Inicial (ou {})
        historico: list[dict] das sessões de Evolucao
        insights: dict de ia_clinica.analisar_paciente (ou None)
        fenotipo: dict de ia_clinica.normalizar_diagnostico (ou None)

    Returns:
        bytes do PDF
    """
    dados_aval = dados_aval or {}
    hist = sorted(historico, key=lambda x: x.get('Data', '')) if historico else []

    pdf = LaudoGenua()
    pdf.alias_nb_pages()

    _pagina_capa(pdf, paciente_nome, dados_aval, hist, fenotipo)
    _pagina_avaliacao(pdf, dados_aval)
    _pagina_exame_fisico(pdf, dados_aval)
    _pagina_proms(pdf, dados_aval)
    _pagina_evolucao(pdf, hist)
    _pagina_ia(pdf, insights)
    _pagina_assinatura(pdf, dados_aval)

    saida = pdf.output()
    # fpdf2 retorna bytearray; normaliza para bytes
    if isinstance(saida, (bytes, bytearray)):
        return bytes(saida)
    return saida.encode('latin-1')
