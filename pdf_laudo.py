"""
GENUA | Gerador de Laudo Clínico Avançado (PDF) - High-Impact Visual Edition
============================================================================
Gera relatório profissional de alto impacto visual para dois públicos:
 - PACIENTE: visual moderno, cores vivas, barras de progresso e clareza
 - MÉDICO: científico, PROMs com MCID, LSI e referências auditáveis

Dependências: fpdf2, matplotlib, numpy, io, datetime
"""
import io
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF


# ============================================================
# PALETA DE CORES GENUA + CORES VIVAS (UI/UX HEALTHTECH)
# ============================================================
# Cores Institucionais Genua
AZUL_PROFUNDO = (10, 37, 64)       # #0A2540 - Hero Banner e Títulos Fortes
AZUL_GENUA = (16, 62, 85)          # #103E55 - Primária Oficial Genua
TEAL_GENUA = (57, 142, 155)        # #398E9B - Secundária Oficial Genua
CINZA_GELO = (244, 247, 249)       # #F4F7F9 - Fundo Oficial Genua

# Cores Vivas de Destaque e Semáforo Clínico
TEAL_VIVO = (0, 180, 197)          # #00B4C5 - Ciano vibrante para destaques
FUNDO_TEAL_SUAVE = (224, 247, 250) # #E0F7FA - Fundo de destaque clínico

VERDE_VIVO = (16, 185, 129)        # #10B981 - Esmeralda vivo (Sucesso / MCID / LSI >= 90%)
FUNDO_VERDE_SUAVE = (209, 250, 229)# #D1FAE5 - Fundo suave positivo

VERMELHO_VIVO = (239, 68, 68)      # #EF4444 - Coral vivo (Alerta / Red Flag / LSI < 85%)
FUNDO_VERMELHO_SUAVE = (254, 226, 226) # #FEE2E2 - Fundo suave de risco

AMBAR_VIVO = (245, 158, 11)        # #F59E0B - Âmbar vivo (Atenção / Yellow Flag / LSI 85-89%)
FUNDO_AMBAR_SUAVE = (254, 243, 199)# #FEF3C7 - Fundo suave de atenção

INDIGO_VIVO = (99, 102, 241)       # #6366F1 - Índigo vivo para métricas de sessões/volume
FUNDO_INDIGO_SUAVE = (224, 231, 255) # #E0E7FF - Fundo suave índigo

# Neutros de Alto Contraste
PRETO_TEXTO = (15, 23, 42)         # #0F172A - Slate 900 para leitura nítida
CINZA_TEXTO = (71, 85, 105)        # #475569 - Slate 600 para subtítulos
CINZA_BORDA = (203, 213, 225)      # #CBD5E1 - Slate 300 para linhas divisórias
BRANCO = (255, 255, 255)


def _limpar_texto(texto):
    """Converte caracteres especiais para latin-1/ASCII seguro no FPDF padrão."""
    if texto is None:
        return ""
    s = str(texto)
    # Tenta codificar em latin-1 (suporta acentos em português nas fontes core do FPDF)
    try:
        return s.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return s.encode('ascii', 'replace').decode('ascii')


def _fig_to_bytes(fig, dpi=300):
    """Converte matplotlib figure para buffer PNG em alta resolução (300 DPI)."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def _mapa_func_score(resultado_texto):
    """Converte texto do teste funcional para score numérico de 0 a 10."""
    mapa = {
        "Sem Dor (0)": 10, "Sem Dor": 10,
        "Dor Leve (1 - 3)": 7, "Dor Leve": 7,
        "Dor Moderada (4 - 7)": 4, "Dor Moderada": 4,
        "Dor Grave (8 - 10)": 1, "Dor Grave": 1,
        "Incapaz (Não realiza)": 0, "Incapaz (Nao realiza)": 0, "Incapaz": 0,
    }
    return mapa.get(resultado_texto)


# ============================================================
# CLASSE PRINCIPAL DO PDF (DESIGN SYSTEM MODERNO)
# ============================================================
class LaudoGenua(FPDF):
    """PDF com cabeçalho, rodapé e componentes gráficos de alta vivacidade."""

    def header(self):
        # Barra superior dupla (Azul Profundo + Teal Vivo)
        self.set_fill_color(*AZUL_PROFUNDO)
        self.rect(0, 0, 140, 4, 'F')
        self.set_fill_color(*TEAL_VIVO)
        self.rect(140, 0, 70, 4, 'F')

        if self.page_no() > 1:
            self.set_y(7)
            self.set_font('Arial', 'B', 10)
            self.set_text_color(*AZUL_PROFUNDO)
            self.cell(38, 5, 'GENUA', 0, 0, 'L')
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*TEAL_VIVO)
            self.cell(60, 5, '| Inteligencia Clinica PBE', 0, 0, 'L')

            self.set_font('Arial', '', 8)
            self.set_text_color(*CINZA_TEXTO)
            self.cell(0, 5, f'Emitido em {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'R')

            self.set_draw_color(*TEAL_VIVO)
            self.set_line_width(0.4)
            self.line(10, 14, 200, 14)
            self.ln(5)
        else:
            self.set_y(6)

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(*CINZA_BORDA)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)

        self.set_font('Arial', 'B', 7)
        self.set_text_color(*AZUL_GENUA)
        self.cell(65, 5, 'GENUA HealthTech | Fisioterapia Baseada em Evidencia', 0, 0, 'L')

        self.set_font('Arial', '', 7)
        self.set_text_color(*CINZA_TEXTO)
        self.cell(60, 5, 'Documento Clinico Confidencial (LGPD)', 0, 0, 'C')

        self.set_font('Arial', 'B', 8)
        self.set_text_color(*TEAL_VIVO)
        self.cell(65, 5, f'Pagina {self.page_no()}/{{nb}}', 0, 0, 'R')

    def secao(self, titulo, subtitulo=""):
        """Bloco de título de seção com marcador lateral colorido vivo."""
        y_atual = self.get_y()
        # Marcador vertical Teal Vivo
        self.set_fill_color(*TEAL_VIVO)
        self.rect(10, y_atual, 3.5, 8 if not subtitulo else 12, 'F')

        # Fundo suave na faixa do título
        self.set_fill_color(*CINZA_GELO)
        self.rect(13.5, y_atual, 186.5, 8 if not subtitulo else 12, 'F')

        self.set_xy(17, y_atual + 1)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(*AZUL_PROFUNDO)
        self.cell(0, 6, _limpar_texto(titulo).upper(), 0, 1, 'L')

        if subtitulo:
            self.set_x(17)
            self.set_font('Arial', '', 8)
            self.set_text_color(*CINZA_TEXTO)
            self.cell(0, 4, _limpar_texto(subtitulo), 0, 1, 'L')

        self.set_y(y_atual + (11 if not subtitulo else 15))

    def kpi_box(self, x, y, w, h, label, valor, subtexto="", cor_principal=TEAL_VIVO, cor_fundo=FUNDO_TEAL_SUAVE):
        """Renderiza um Card de KPI colorido (Tinted Card) com destaque de alto impacto."""
        # Fundo suave colorido do card
        self.set_fill_color(*cor_fundo)
        self.set_draw_color(*cor_principal)
        self.set_line_width(0.4)
        self.rect(x, y, w, h, 'DF')

        # Faixa superior viva
        self.set_fill_color(*cor_principal)
        self.rect(x, y, w, 3, 'F')

        inner_w = max(10, w - 8)

        # Label do KPI
        self.set_xy(x + 4, y + 5)
        self.set_font('Arial', 'B', 7.5)
        self.set_text_color(*AZUL_PROFUNDO)
        self.cell(inner_w, 4, _limpar_texto(str(label)).upper()[:28], 0, 2, 'L')

        # Valor Principal Grande
        self.set_x(x + 4)
        self.set_font('Arial', 'B', 20)
        self.set_text_color(*cor_principal)
        self.cell(inner_w, 11, _limpar_texto(str(valor))[:18], 0, 2, 'L')

        # Badge/Subtexto inferior
        if subtexto:
            self.set_x(x + 4)
            self.set_font('Arial', 'B', 7.5)
            self.set_text_color(*CINZA_TEXTO)
            self.cell(inner_w, 5, _limpar_texto(str(subtexto))[:35], 0, 2, 'L')

    def barra_progresso(self, x, y, w, h, percentual, cor_barra=VERDE_VIVO):
        """Desenha uma barra de progresso horizontal moderna em FPDF."""
        pct_limpo = max(0.0, min(100.0, float(percentual)))
        w_preenchido = w * (pct_limpo / 100.0)

        # Trilho de fundo
        self.set_fill_color(226, 232, 240)
        self.rect(x, y, w, h, 'F')

        # Barra ativa colorida
        if w_preenchido > 0:
            self.set_fill_color(*cor_barra)
            self.rect(x, y, w_preenchido, h, 'F')

    def tabela_simples(self, headers, rows, col_widths=None, col_destaque=None):
        """Renderiza tabela moderna com cabeçalho Azul Profundo, zebra suave e destaque."""
        if not col_widths:
            col_widths = [190 // len(headers)] * len(headers)

        self.set_x(10)

        # Cabeçalho da Tabela
        self.set_font('Arial', 'B', 8.5)
        self.set_fill_color(*AZUL_PROFUNDO)
        self.set_text_color(*BRANCO)
        self.set_draw_color(*AZUL_PROFUNDO)
        self.set_line_width(0.3)

        for i, h in enumerate(headers):
            w = col_widths[i]
            max_chars = max(4, int(w * 0.55))
            txt = _limpar_texto(h)[:max_chars]
            self.cell(w, 8, txt, 1, 0, 'C', fill=True)
        self.ln()

        # Linha viva sob o cabeçalho
        self.set_draw_color(*TEAL_VIVO)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 10 + sum(col_widths), self.get_y())

        # Linhas de Dados
        self.set_line_width(0.2)
        self.set_draw_color(*CINZA_BORDA)

        for r_idx, row in enumerate(rows):
            self.set_x(10)
            if r_idx % 2 == 0:
                self.set_fill_color(*BRANCO)
            else:
                self.set_fill_color(*CINZA_GELO)

            for i, cell_val in enumerate(row):
                w = col_widths[i]
                max_chars = max(4, int(w * 0.55))
                txt = _limpar_texto(str(cell_val))[:max_chars]

                # Colorização semântica para colunas de variação/score
                if col_destaque is not None and i == col_destaque:
                    self.set_font('Arial', 'B', 8)
                    if '+' in txt or 'Sem Dor' in txt:
                        self.set_text_color(*VERDE_VIVO)
                    elif '-' in txt and txt.strip() != '-':
                        self.set_text_color(*VERMELHO_VIVO)
                    else:
                        self.set_text_color(*AZUL_PROFUNDO)
                else:
                    self.set_font('Arial', '', 8)
                    self.set_text_color(*PRETO_TEXTO)

                self.cell(w, 7, txt, 'B', 0, 'C', fill=True)
            self.ln()
        self.ln(2)


# ============================================================
# FUNÇÃO PRINCIPAL: gerar_laudo()
# ============================================================
def gerar_laudo(paciente_nome, dados_aval, historico, insights=None, fenotipo=None):
    """
    Gera o PDF completo do laudo clínico com visual moderno e cores vivas.

    Args:
        paciente_nome: str
        dados_aval: dict (última Avaliacao_Inicial)
        historico: list[dict] (sessões de Evolucao, cronológico)
        insights: dict (resultado de ia_clinica.analisar_paciente) ou None
        fenotipo: dict (resultado de ia_clinica.normalizar_diagnostico) ou None

    Returns:
        bytes do PDF pronto para download
    """
    pdf = LaudoGenua()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Ordena histórico cronologicamente
    hist = sorted(historico, key=lambda x: x.get('Data', '')) if historico else []
    n_sessoes = len(hist)

    # Dados derivados com tratamento de segurança para float
    try:
        dor_inicial = float(hist[0].get('Dor', 0)) if hist else 0.0
    except (ValueError, TypeError):
        dor_inicial = 0.0

    try:
        dor_atual = float(hist[-1].get('Dor', 0)) if hist else 0.0
    except (ValueError, TypeError):
        dor_atual = 0.0

    delta_dor = dor_inicial - dor_atual

    try:
        flex_inicial = float(hist[0].get('Flexao', 0)) if hist else 0.0
    except (ValueError, TypeError):
        flex_inicial = 0.0

    try:
        flex_atual = float(hist[-1].get('Flexao', 0)) if hist else 0.0
    except (ValueError, TypeError):
        flex_atual = 0.0

    delta_flex = flex_atual - flex_inicial
    dx_texto = dados_aval.get('Diagnostico_Clinico', 'Nao informado') if dados_aval else 'Nao informado'
    fen_label = fenotipo.get('label', 'Geral / Musculoesqueletico') if fenotipo else 'Geral / Musculoesqueletico'

    # ==================================================================
    # PÁGINA 1: HERO BANNER + IDENTIFICAÇÃO + SUMÁRIO EXECUTIVO VIVO
    # ==================================================================
    pdf.add_page()

    # Hero Banner Colorido (Topo da Capa)
    pdf.set_fill_color(*AZUL_PROFUNDO)
    pdf.rect(10, 10, 190, 28, 'F')
    # Faixa decorativa lateral Teal Vivo no Banner
    pdf.set_fill_color(*TEAL_VIVO)
    pdf.rect(10, 10, 5, 28, 'F')

    pdf.set_xy(20, 14)
    pdf.set_font('Arial', 'B', 18)
    pdf.set_text_color(*BRANCO)
    pdf.cell(120, 8, 'LAUDO DE EVOLUCAO CLINICA', 0, 0, 'L')

    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(*TEAL_VIVO)
    pdf.cell(55, 8, 'GENUA HEALTHTECH', 0, 1, 'R')

    pdf.set_xy(20, 23)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(203, 213, 225)
    pdf.cell(120, 6, 'Monitoramento Biomecanico e Pratica Baseada em Evidencias (PBE)', 0, 0, 'L')

    pdf.set_font('Arial', '', 8.5)
    pdf.cell(55, 6, f'Emissao: {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'R')

    pdf.set_y(43)

    # Card de Identificação do Paciente
    pdf.set_fill_color(*CINZA_GELO)
    pdf.set_draw_color(*CINZA_BORDA)
    pdf.set_line_width(0.3)
    pdf.rect(10, pdf.get_y(), 190, 24, 'DF')

    y_pac = pdf.get_y()
    pdf.set_xy(15, y_pac + 3)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*AZUL_PROFUNDO)
    pdf.cell(110, 6, f'PACIENTE: {_limpar_texto(paciente_nome).upper()}', 0, 0, 'L')

    idade = dados_aval.get('Idade', '-') if dados_aval else '-'
    pdf.set_font('Arial', 'B', 9.5)
    pdf.set_text_color(*TEAL_GENUA)
    pdf.cell(70, 6, f'Idade: {_limpar_texto(idade)} anos', 0, 1, 'R')

    pdf.set_xy(15, y_pac + 10)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(*CINZA_TEXTO)
    pdf.cell(25, 6, 'Diagnostico:', 0, 0, 'L')
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*PRETO_TEXTO)
    pdf.cell(155, 6, _limpar_texto(str(dx_texto))[:85], 0, 1, 'L')

    # Badge de Fenótipo Clínico
    if fenotipo and fenotipo.get('fenotipo') != 'generico':
        tempo = fenotipo.get('tempo_esperado_semanas', '?')
        pdf.set_xy(15, y_pac + 16.5)
        pdf.set_font('Arial', 'B', 8.5)
        pdf.set_text_color(*TEAL_VIVO)
        pdf.cell(0, 5, f'FENOTIPO CLINICO: {_limpar_texto(fen_label).upper()}  |  JANELA PROGNOSTICA: {tempo} SEMANAS', 0, 1, 'L')

    pdf.set_y(y_pac + 30)

    # Sumário Executivo (3 KPIs Vivos)
    pdf.secao('Sumario Executivo de Performance', 'Indicadores chave de resposta terapeutica acumulada')
    y_kpi = pdf.get_y() + 1
    w_kpi = 60
    gap = 5

    # KPI 1: Dor (EVA)
    sinal_dor = f'Reducao de {delta_dor:.0f} pts (MCID >= 2)' if delta_dor >= 2 else (
        f'Variacao: {-delta_dor:+.0f} pts na EVA' if delta_dor != 0 else 'Estavel no periodo'
    )
    if delta_dor >= 2:
        cor_dor, bg_dor = VERDE_VIVO, FUNDO_VERDE_SUAVE
    elif delta_dor > 0:
        cor_dor, bg_dor = TEAL_VIVO, FUNDO_TEAL_SUAVE
    elif delta_dor < 0:
        cor_dor, bg_dor = VERMELHO_VIVO, FUNDO_VERMELHO_SUAVE
    else:
        cor_dor, bg_dor = AMBAR_VIVO, FUNDO_AMBAR_SUAVE

    pdf.kpi_box(10, y_kpi, w_kpi, 30, 'MODULACAO DA DOR (EVA)',
                f'{dor_inicial:.0f} -> {dor_atual:.0f}', sinal_dor, cor_dor, bg_dor)

    # KPI 2: ADM Flexão
    sinal_flex = f'Ganho de {delta_flex:+.0f} graus' if delta_flex > 0 else (
        f'Variacao de {delta_flex:+.0f} graus' if delta_flex < 0 else 'ADM mantida'
    )
    if delta_flex > 0:
        cor_flex, bg_flex = VERDE_VIVO, FUNDO_VERDE_SUAVE
    elif delta_flex < 0:
        cor_flex, bg_flex = VERMELHO_VIVO, FUNDO_VERMELHO_SUAVE
    else:
        cor_flex, bg_flex = TEAL_VIVO, FUNDO_TEAL_SUAVE

    pdf.kpi_box(10 + w_kpi + gap, y_kpi, w_kpi, 30, 'AMPLITUDE DE FLEXAO',
                f'{flex_atual:.0f} graus', sinal_flex, cor_flex, bg_flex)

    # KPI 3: Volume de Sessões
    periodo_txt = f'{hist[0].get("Data", "?")[:10]} a {hist[-1].get("Data", "?")[:10]}' if hist else 'Sem sessoes'
    pdf.kpi_box(10 + (w_kpi + gap) * 2, y_kpi, w_kpi, 30, 'SESSOES REALIZADAS',
                f'{n_sessoes} sessoes', periodo_txt, INDIGO_VIVO, FUNDO_INDIGO_SUAVE)

    pdf.set_y(y_kpi + 37)

    # Tabela Resumo das Últimas 5 Sessões
    if hist:
        pdf.secao('Monitoramento Recente (Check-ins)', 'Registro cronologico das ultimas 5 sessoes avaliadas')
        headers = ['Data', 'Dor (EVA)', 'Flexao (graus)', 'Extensao', 'Edema/Inchaco', 'Qualidade Sono']
        rows = []
        for ev in hist[-5:]:
            rows.append([
                ev.get('Data', '-')[:10],
                f"{ev.get('Dor', '-')}/10",
                f"{ev.get('Flexao', '-')}",
                str(ev.get('Extensao', '-'))[:14],
                str(ev.get('Inchaço', ev.get('Inchaco', '-')))[:14],
                str(ev.get('Sono', '-'))[:14]
            ])
        pdf.tabela_simples(headers, rows, [28, 24, 28, 36, 37, 37], col_destaque=1)

    # ==================================================================
    # PÁGINA 2: EVOLUÇÃO DA DOR (GRÁFICO DE ALTA DEFINIÇÃO + MCID)
    # ==================================================================
    if hist and n_sessoes >= 2:
        pdf.add_page()
        pdf.secao('Curva de Evolucao da Dor (EVA)', 'Analise longitudinal da dor versus Diferenca Minima Clinicamente Importante (MCID)')

        datas = [ev.get('Data', '')[:5] for ev in hist]
        dores = []
        for ev in hist:
            try:
                dores.append(float(ev.get('Dor', 0)))
            except (ValueError, TypeError):
                dores.append(0.0)

        fig, ax = plt.subplots(figsize=(8.2, 3.6))
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#F8FAFC')

        x_idx = np.arange(len(datas))

        # Zona sombreada de sucesso MCID (Salaffi 2004: -2 pontos)
        if dor_inicial >= 2:
            meta_mcid = max(0.0, dor_inicial - 2.0)
            ax.axhspan(0, meta_mcid, color='#10B981', alpha=0.10, label='Zona de Sucesso Clinico (MCID >= -2 pts)')
            ax.axhline(y=meta_mcid, color='#10B981', linestyle='--', linewidth=2, alpha=0.9)

        # Preenchimento duplo e linha viva
        ax.fill_between(x_idx, dores, color='#00B4C5', alpha=0.18)
        ax.plot(x_idx, dores, color='#0A2540', linewidth=3, marker='o', markersize=8,
                markerfacecolor='#00B4C5', markeredgecolor='white', markeredgewidth=2,
                label='Dor Relatada (EVA 0-10)', zorder=4)

        # Anotação direta nos pontos inicial e final
        ax.annotate(f'{dores[0]:.0f}', (x_idx[0], dores[0]), textcoords="offset points",
                    xytext=(0, 10), ha='center', fontsize=9, fontweight='bold', color='#0A2540')
        ax.annotate(f'{dores[-1]:.0f}', (x_idx[-1], dores[-1]), textcoords="offset points",
                    xytext=(0, 10), ha='center', fontsize=9, fontweight='bold', color='#00B4C5')

        ax.set_xticks(x_idx)
        ax.set_xticklabels(datas, rotation=30, ha='right', fontsize=8.5, color='#334155')
        ax.set_ylabel('Intensidade da Dor (EVA)', fontweight='bold', fontsize=9.5, color='#0A2540')
        ax.set_ylim(-0.5, 10.8)
        ax.set_yticks(range(0, 11, 2))
        ax.grid(True, axis='y', linestyle=':', color='#CBD5E1', alpha=0.8)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#CBD5E1')
        ax.spines['bottom'].set_color('#CBD5E1')
        ax.legend(loc='upper right', fontsize=8.5, frameon=True, facecolor='white', edgecolor='#E2E8F0')
        fig.tight_layout()

        buf = _fig_to_bytes(fig)
        pdf.image(buf, x=10, w=190, h=82)
        pdf.ln(4)

        # Card de Interpretação Clínica PBE
        if delta_dor >= 2:
            cor_card, bg_card = VERDE_VIVO, FUNDO_VERDE_SUAVE
            titulo_interp = "ATINGIU SIGNIFICANCIA CLINICA (MCID POSITIVO)"
            txt_interp = (f"Reducao expressiva de {delta_dor:.0f} pontos na escala visual analogica. "
                          "Supera o limiar de Diferenca Minima Clinicamente Importante (MCID = 2 pontos; Salaffi et al., 2004), "
                          "confirmando eficacia analgesica real do plano terapeutico.")
        elif delta_dor > 0:
            cor_card, bg_card = TEAL_VIVO, FUNDO_TEAL_SUAVE
            titulo_interp = "MELHORA SINTOMATICA EM CURSO (ABAIXO DO MCID)"
            txt_interp = (f"Reducao de {delta_dor:.0f} ponto(s) na EVA. Embora positiva, a variacao ainda nao atingiu "
                          "o corte de 2 pontos (Salaffi et al., 2004). Manter progressao controlada de carga.")
        elif delta_dor == 0:
            cor_card, bg_card = AMBAR_VIVO, FUNDO_AMBAR_SUAVE
            titulo_interp = "ESTABILIDADE SINTOMATICA (PLATÔ)"
            txt_interp = ("Ausencia de variacao liquida na dor entre o inicio e a ultima sessao. "
                          "Recomenda-se auditar volume de carga, cinesiofobia ou fatores psicossociais.")
        else:
            cor_card, bg_card = VERMELHO_VIVO, FUNDO_VERMELHO_SUAVE
            titulo_interp = "ALERTA DE REATIVIDADE / PIORA ALGESICA"
            txt_interp = (f"Aumento de {abs(delta_dor):.0f} ponto(s) na EVA. Investigar imediatamente sobrecarga aguda "
                          "nas ultimas 48h, adesao domiciliar ou sinais de bandeira vermelha.")

        y_box = pdf.get_y()
        pdf.set_fill_color(*bg_card)
        pdf.set_draw_color(*cor_card)
        pdf.set_line_width(0.4)
        pdf.rect(10, y_box, 190, 22, 'DF')
        pdf.set_fill_color(*cor_card)
        pdf.rect(10, y_box, 4, 22, 'F')

        pdf.set_xy(17, y_box + 2.5)
        pdf.set_font('Arial', 'B', 9.5)
        pdf.set_text_color(*cor_card)
        pdf.cell(0, 5, titulo_interp, 0, 1, 'L')

        pdf.set_x(17)
        pdf.set_font('Arial', '', 8.5)
        pdf.set_text_color(*PRETO_TEXTO)
        pdf.multi_cell(178, 4.5, _limpar_texto(txt_interp))

    # ==================================================================
    # PÁGINA 3: CORRELAÇÃO DOR × FUNÇÃO
    # ==================================================================
    if hist and n_sessoes >= 2:
        pdf.add_page()
        pdf.secao('Correlacao Dinamica: Dor vs. Capacidade Funcional',
                  'Cruzamento de curvas: eficacia comprovada quando a dor cai (vermelho) e a funcao sobe (verde)')

        datas = [ev.get('Data', '')[:5] for ev in hist]
        dores = []
        for ev in hist:
            try:
                dores.append(float(ev.get('Dor', 0)))
            except (ValueError, TypeError):
                dores.append(0.0)

        func_scores = []
        testes_evolucao = {}
        for ev in hist:
            testes = ev.get('Testes_Funcionais', {})
            if isinstance(testes, dict) and testes:
                scores = []
                for nome, resultado in testes.items():
                    s = _mapa_func_score(resultado)
                    if s is not None:
                        scores.append(s)
                    if nome not in testes_evolucao:
                        testes_evolucao[nome] = []
                    testes_evolucao[nome].append(resultado)
                func_scores.append(sum(scores) / len(scores) if scores else None)
            else:
                func_scores.append(None)

        fig, ax1 = plt.subplots(figsize=(8.2, 3.6))
        fig.patch.set_facecolor('white')
        ax1.set_facecolor('#F8FAFC')
        x_idx = np.arange(len(datas))

        # Eixo 1: Dor (Vermelho Coral Vivo)
        ax1.plot(x_idx, dores, color='#EF4444', marker='o', markersize=7,
                 markeredgecolor='white', markeredgewidth=1.5, lw=2.8, label='Sintoma: Dor (EVA 0-10)', zorder=3)
        ax1.fill_between(x_idx, dores, color='#EF4444', alpha=0.10)
        ax1.set_ylabel('Dor (EVA 0-10)', color='#EF4444', fontweight='bold', fontsize=9.5)
        ax1.set_ylim(-0.5, 10.8)
        ax1.set_xticks(x_idx)
        ax1.set_xticklabels(datas, rotation=30, ha='right', fontsize=8.5, color='#334155')
        ax1.grid(True, axis='y', linestyle=':', color='#CBD5E1', alpha=0.8)

        # Eixo 2: Função (Verde Esmeralda Vivo)
        ax2 = ax1.twinx()
        func_clean = [v if v is not None else np.nan for v in func_scores]
        func_arr = np.array(func_clean, dtype=float)
        mask = ~np.isnan(func_arr)

        if mask.sum() >= 2:
            func_interp = np.interp(range(len(func_arr)), np.where(mask)[0], func_arr[mask])
            ax2.plot(x_idx, func_interp, color='#10B981', marker='s', markersize=7,
                     markeredgecolor='white', markeredgewidth=1.5, lw=2.8, linestyle='-',
                     label='Capacidade Funcional (0-10)', zorder=4)
            ax2.fill_between(x_idx, func_interp, color='#10B981', alpha=0.12)

        ax2.set_ylabel('Score Funcional (0-10)', color='#10B981', fontweight='bold', fontsize=9.5)
        ax2.set_ylim(-0.5, 10.8)

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center',
                   bbox_to_anchor=(0.5, 1.14), ncol=2, fontsize=8.5, frameon=True, facecolor='white')

        ax1.spines['top'].set_visible(False)
        ax2.spines['top'].set_visible(False)
        fig.tight_layout()

        buf = _fig_to_bytes(fig)
        pdf.image(buf, x=10, w=190, h=82)
        pdf.ln(4)

        if testes_evolucao:
            pdf.secao('Evolucao Analitica por Teste Funcional', 'Comparativo direto entre a avaliacao de base e o status atual')
            headers = ['Teste Funcional', 'Status Inicial', 'Status Atual', 'Ganho Funcional']
            rows = []
            for nome, resultados in testes_evolucao.items():
                primeiro = resultados[0] if resultados else '-'
                ultimo = resultados[-1] if resultados else '-'
                s_primeiro = _mapa_func_score(primeiro)
                s_ultimo = _mapa_func_score(ultimo)
                if s_primeiro is not None and s_ultimo is not None:
                    delta = s_ultimo - s_primeiro
                    var_text = f'{delta:+.0f} pts' if delta != 0 else 'Mantido'
                else:
                    var_text = '-'
                rows.append([
                    _limpar_texto(nome)[:32],
                    _limpar_texto(str(primeiro))[:22],
                    _limpar_texto(str(ultimo))[:22],
                    var_text
                ])
            pdf.tabela_simples(headers, rows, [65, 45, 45, 35], col_destaque=3)

    # ==================================================================
    # PÁGINA 4: PROMs COM BARRAS VISUAIS + AVALIAÇÃO INICIAL
    # ==================================================================
    if dados_aval:
        pdf.add_page()
        pdf.secao('Questionarios Validados (PROMs)',
                  'Patient-Reported Outcome Measures com barras visuais e corte de significancia (MCID)')

        proms_data = [
            ("LEFS", "Funcao Geral MMII", dados_aval.get("LEFS_Pct", 0), "%", "9 pts (Binkley 1999)", dados_aval.get("Interpretacao_LEFS", "-")),
            ("VISA-P", "Tendinopatia Patelar", dados_aval.get("VISA_P_Pts", 0), "pts", "13 pts (Hernandez 2014)", dados_aval.get("Interpretacao_VISA_P", "-")),
            ("Lysholm", "Ligamentar / Meniscal", dados_aval.get("Lysholm_Pts", 0), "pts", "10 pts (Briggs 2009)", dados_aval.get("Interpretacao_Lysholm", "-")),
            ("WOMAC", "Osteoartrite", dados_aval.get("WOMAC_Pct", 0), "%", "12% (Angst 2001)", dados_aval.get("Interpretacao_WOMAC", "-")),
            ("KOOS", "Score Global Joelho", dados_aval.get("KOOS_Pct", 0), "%", "8-10 pts (Roos 2003)", "-"),
            ("IKDC", "Subjetivo de Joelho", dados_aval.get("IKDC_Pct", 0), "%", "9 pts (Irrgang 2006)", "-"),
        ]

        proms_ativos = []
        for nome, indicacao, score, un, mcid, interp in proms_data:
            try:
                score_f = float(score)
            except (ValueError, TypeError):
                score_f = 0.0
            if score_f > 0:
                proms_ativos.append((nome, indicacao, score_f, un, mcid, interp))

        if proms_ativos:
            for nome, indicacao, score_f, un, mcid, interp in proms_ativos:
                y_p = pdf.get_y()
                pdf.set_fill_color(*CINZA_GELO)
                pdf.set_draw_color(*CINZA_BORDA)
                pdf.rect(10, y_p, 190, 15, 'DF')

                # Nome e Indicação
                pdf.set_xy(14, y_p + 2)
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(*AZUL_PROFUNDO)
                pdf.cell(25, 5, _limpar_texto(nome), 0, 0, 'L')

                pdf.set_font('Arial', '', 8.5)
                pdf.set_text_color(*CINZA_TEXTO)
                pdf.cell(55, 5, _limpar_texto(indicacao), 0, 0, 'L')

                # Valor e Barra de Progresso
                cor_p = VERDE_VIVO if score_f >= 75 else (AMBAR_VIVO if score_f >= 50 else VERMELHO_VIVO)
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(*cor_p)
                pdf.cell(25, 5, f'{score_f:.1f} {un}', 0, 0, 'R')

                pdf.barra_progresso(120, y_p + 3, 75, 3.5, score_f, cor_p)

                # Sub-linha com MCID e Interpretação
                pdf.set_xy(14, y_p + 8.5)
                pdf.set_font('Arial', 'I', 7.5)
                pdf.set_text_color(*TEAL_GENUA)
                pdf.cell(80, 4, f'Referencia MCID: {_limpar_texto(mcid)}', 0, 0, 'L')

                pdf.set_font('Arial', 'B', 7.5)
                pdf.set_text_color(*PRETO_TEXTO)
                pdf.cell(100, 4, f'Classificacao: {_limpar_texto(str(interp))[:48]}', 0, 1, 'R')

                pdf.set_y(y_p + 17)
        else:
            pdf.set_font('Arial', 'I', 9)
            pdf.set_text_color(*CINZA_TEXTO)
            pdf.cell(0, 8, 'Nenhum escore PROM (> 0) registrado na avaliacao inicial.', 0, 1)

        pdf.ln(3)
        pdf.secao('Sintese da Avaliacao Clinica Inicial', 'Dados basais coletados na anamnese e exame fisico')

        campos = [
            ("Queixa Principal (QP)", dados_aval.get("QP", "-")),
            ("Classificacao da Dor", dados_aval.get("Class_Dor", "-")),
            ("Derrame Articular", dados_aval.get("Derrame", "-")),
            ("Comorbidades", dados_aval.get("Comorbidades", "-")),
            ("Alinhamento / Biomecanica", dados_aval.get("Alinhamento", "-")),
            ("Exames Complementares", dados_aval.get("Exames_Apresentados", "-")),
        ]

        for idx_c, (label, valor) in enumerate(campos):
            bg_c = BRANCO if idx_c % 2 == 0 else CINZA_GELO
            pdf.set_fill_color(*bg_c)
            pdf.set_x(10)
            pdf.set_font('Arial', 'B', 8.5)
            pdf.set_text_color(*AZUL_PROFUNDO)
            pdf.cell(52, 7, f'  {_limpar_texto(label)}:', 'B', 0, 'L', fill=True)

            pdf.set_font('Arial', '', 8.5)
            pdf.set_text_color(*PRETO_TEXTO)
            pdf.cell(138, 7, _limpar_texto(str(valor))[:85], 'B', 1, 'L', fill=True)

    # ==================================================================
    # PÁGINA 5: INSIGHTS IA + LSI GAUGE + BANDEIRAS COLORIDAS
    # ==================================================================
    if insights:
        pdf.add_page()
        pdf.secao('Motor de Inteligencia Clinica (Regras PBE)',
                  'Auditoria automatizada deterministica baseada em literatura cientifica revisada por pares')

        # 1. Card de Status de Evolução / Estagnação
        est = insights.get('estagnacao')
        if est and est.get('status') not in ('insuficiente', None):
            st_est = est.get('status')
            if st_est == 'melhora':
                cor_e, bg_e, tit_e = VERDE_VIVO, FUNDO_VERDE_SUAVE, 'EVOLUCAO CLINICA POSITIVA'
            elif st_est == 'estagnacao':
                cor_e, bg_e, tit_e = AMBAR_VIVO, FUNDO_AMBAR_SUAVE, 'ALERTA: ESTAGNACAO TERAPEUTICA DETECTADA'
            else:
                cor_e, bg_e, tit_e = VERMELHO_VIVO, FUNDO_VERMELHO_SUAVE, 'ALERTA CRITICO: PIORA CLINICA'

            y_e = pdf.get_y()
            pdf.set_fill_color(*bg_e)
            pdf.set_draw_color(*cor_e)
            pdf.set_line_width(0.4)
            pdf.rect(10, y_e, 190, 22, 'DF')
            pdf.set_fill_color(*cor_e)
            pdf.rect(10, y_e, 4, 22, 'F')

            pdf.set_xy(17, y_e + 2)
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(*cor_e)
            pdf.cell(0, 5, tit_e, 0, 1, 'L')

            pdf.set_x(17)
            pdf.set_font('Arial', '', 8.5)
            pdf.set_text_color(*PRETO_TEXTO)
            pdf.multi_cell(178, 4.5, _limpar_texto(est.get('racional', '')))

            pdf.set_xy(17, y_e + 16.5)
            pdf.set_font('Arial', 'I', 7.5)
            pdf.set_text_color(*CINZA_TEXTO)
            pdf.cell(0, 4, f'Base Cientifica: {_limpar_texto(est.get("referencia", ""))}', 0, 1, 'L')
            pdf.set_y(y_e + 26)

        # 2. Card Visual de Limb Symmetry Index (LSI) com Barra Gauge
        lsi_data = insights.get('lsi')
        if lsi_data and lsi_data.get('valor') is not None:
            try:
                val_lsi = float(lsi_data['valor'])
            except (ValueError, TypeError):
                val_lsi = 0.0

            # Thresholds de Grindem et al. (2016)
            if val_lsi >= 90:
                cor_lsi, bg_lsi, status_lsi = VERDE_VIVO, FUNDO_VERDE_SUAVE, 'APTO PARA ALTA / RETORNO AO ESPORTE (>= 90%)'
            elif val_lsi >= 85:
                cor_lsi, bg_lsi, status_lsi = AMBAR_VIVO, FUNDO_AMBAR_SUAVE, 'ZONA DE ATENCAO BIOMECANICA (85% a 89%)'
            else:
                cor_lsi, bg_lsi, status_lsi = VERMELHO_VIVO, FUNDO_VERMELHO_SUAVE, 'ALTO RISCO DE RE-LESAO (< 85%)'

            y_l = pdf.get_y()
            pdf.set_fill_color(*bg_lsi)
            pdf.set_draw_color(*cor_lsi)
            pdf.rect(10, y_l, 190, 28, 'DF')
            pdf.set_fill_color(*cor_lsi)
            pdf.rect(10, y_l, 4, 28, 'F')

            pdf.set_xy(17, y_l + 2.5)
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(*AZUL_PROFUNDO)
            pdf.cell(95, 6, f'LIMB SYMMETRY INDEX (LSI): {val_lsi:.1f}%', 0, 0, 'L')

            pdf.set_font('Arial', 'B', 8.5)
            pdf.set_text_color(*cor_lsi)
            pdf.cell(85, 6, status_lsi, 0, 1, 'R')

            # Barra de Progresso do LSI
            pdf.barra_progresso(17, y_l + 10, 178, 4, val_lsi, cor_lsi)

            pdf.set_xy(17, y_l + 16)
            pdf.set_font('Arial', '', 8.5)
            pdf.set_text_color(*PRETO_TEXTO)
            pdf.cell(178, 5, _limpar_texto(lsi_data.get('acao', ''))[:105], 0, 1, 'L')

            pdf.set_xy(17, y_l + 22)
            pdf.set_font('Arial', 'I', 7.5)
            pdf.set_text_color(*CINZA_TEXTO)
            pdf.cell(0, 4, f'Referencia: {_limpar_texto(lsi_data.get("referencia", "Grindem et al., BJSM 2016"))}', 0, 1, 'L')
            pdf.set_y(y_l + 32)

        # 3. Rastreio de Bandeiras Clínicas (Red / Yellow / Blue / Black Flags)
        pdf.secao('Rastreio de Bandeiras Clinicas (Flags)', 'Monitoramento de sinais de alerta biologicos e psicossociais')
        bandeiras = insights.get('bandeiras', [])
        if bandeiras:
            for b in bandeiras:
                tipo = str(b.get('tipo', 'INFO')).upper()
                if 'VERMELH' in tipo or 'RED' in tipo:
                    cor_b, bg_b = VERMELHO_VIVO, FUNDO_VERMELHO_SUAVE
                elif 'AMAREL' in tipo or 'YELLOW' in tipo:
                    cor_b, bg_b = AMBAR_VIVO, FUNDO_AMBAR_SUAVE
                else:
                    cor_b, bg_b = TEAL_VIVO, FUNDO_TEAL_SUAVE

                y_b = pdf.get_y()
                pdf.set_fill_color(*bg_b)
                pdf.set_draw_color(*cor_b)
                pdf.rect(10, y_b, 190, 18, 'DF')
                pdf.set_fill_color(*cor_b)
                pdf.rect(10, y_b, 4, 18, 'F')

                pdf.set_xy(17, y_b + 2)
                pdf.set_font('Arial', 'B', 9)
                pdf.set_text_color(*cor_b)
                pdf.cell(0, 5, f'BANDEIRA {tipo}: {_limpar_texto(b.get("gatilho", ""))}', 0, 1, 'L')

                pdf.set_x(17)
                pdf.set_font('Arial', '', 8.5)
                pdf.set_text_color(*PRETO_TEXTO)
                pdf.cell(0, 5, f'Conduta Recomendada: {_limpar_texto(b.get("acao", ""))}', 0, 1, 'L')

                pdf.set_x(17)
                pdf.set_font('Arial', 'I', 7)
                pdf.set_text_color(*CINZA_TEXTO)
                pdf.cell(0, 4, f'Ref: {_limpar_texto(b.get("referencia", ""))}', 0, 1, 'L')
                pdf.set_y(y_b + 21)
        else:
            y_ok = pdf.get_y()
            pdf.set_fill_color(*FUNDO_VERDE_SUAVE)
            pdf.set_draw_color(*VERDE_VIVO)
            pdf.rect(10, y_ok, 190, 12, 'DF')
            pdf.set_xy(16, y_ok + 3.5)
            pdf.set_font('Arial', 'B', 9)
            pdf.set_text_color(*VERDE_VIVO)
            pdf.cell(0, 5, 'NENHUMA BANDEIRA CLINICA ATIVA DETECTADA - PERFIL SEGURO PARA PROGRESSAO', 0, 1, 'L')

    # ==================================================================
    # ÚLTIMA PÁGINA: VALIDAÇÃO E ASSINATURA PROFISSIONAL
    # ==================================================================
    pdf.add_page()
    pdf.ln(15)

    # Caixa de Declaração Científica e Responsabilidade Técnica
    pdf.set_fill_color(*CINZA_GELO)
    pdf.set_draw_color(*TEAL_VIVO)
    pdf.set_line_width(0.4)
    pdf.rect(15, pdf.get_y(), 180, 28, 'DF')

    pdf.set_xy(20, pdf.get_y() + 4)
    pdf.set_font('Arial', 'B', 9.5)
    pdf.set_text_color(*AZUL_PROFUNDO)
    pdf.cell(0, 5, 'NOTA METODOLOGICA E RESPONSABILIDADE CLINICA', 0, 1, 'C')

    pdf.set_x(20)
    pdf.set_font('Arial', '', 8.5)
    pdf.set_text_color(*CINZA_TEXTO)
    pdf.multi_cell(
        170, 4.5,
        'Este laudo analitico foi processado pela plataforma GENUA Inteligencia Clinica. '
        'Todos os parametros de corte (MCID e LSI) obedecem a diretrizes cientificas internacionais revisadas por pares. '
        'A interpretacao soberana dos achados e a prescricao da conduta fisioterapeutica sao prerrogativas exclusivas '
        'do fisioterapeuta responsavel.',
        align='C'
    )

    pdf.ln(35)

    # Bloco de Assinatura
    y_ass = pdf.get_y()
    pdf.set_draw_color(*AZUL_PROFUNDO)
    pdf.set_line_width(0.5)
    pdf.line(50, y_ass, 160, y_ass)

    pdf.set_fill_color(*TEAL_VIVO)
    pdf.rect(90, y_ass - 0.5, 30, 1.2, 'F')

    pdf.ln(4)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*AZUL_PROFUNDO)
    pdf.cell(0, 6, 'Fisioterapeuta Responsavel', 0, 1, 'C')

    pdf.set_font('Arial', 'B', 9.5)
    pdf.set_text_color(*TEAL_GENUA)
    pdf.cell(0, 5, 'GENUA Instituto de Fisioterapia Esportiva', 0, 1, 'C')

    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*CINZA_TEXTO)
    pdf.cell(0, 5, f'CREFITO: _______________________   |   Data: {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')

    # Geração segura de bytes para download no Streamlit
    try:
        saida = pdf.output(dest='S')
        if isinstance(saida, str):
            return saida.encode('latin-1')
        return bytes(saida)
    except Exception:
        return bytes(pdf.output())
