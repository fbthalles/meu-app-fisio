"""
GENUA | Gerador de Laudo Clínico Avançado (PDF)
================================================
Gera relatório profissional para dois públicos:
  - PACIENTE: visual, mostra progresso, gera confiança
  - MÉDICO: científico, PROMs com MCID, referências

Estrutura (5-6 páginas):
  P1. Capa + Sumário Executivo (KPIs grandes)
  P2. Evolução da Dor (gráfico + MCID)
  P3. Correlação Dor × Função (linhas cruzadas)
  P4. PROMs e Scores (tabela comparativa)
  P5. Insights IA + Bandeiras + LSI
  P6. Assinatura

Dependências: fpdf2, matplotlib, io, datetime
"""
import io
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF


# ============================================================
# CORES GENUA (RGB)
# ============================================================
AZUL = (16, 62, 85)
TEAL = (57, 142, 155)
CINZA = (100, 100, 100)
CINZA_CLARO = (240, 244, 248)
VERDE = (40, 167, 69)
VERMELHO = (220, 53, 69)
BRANCO = (255, 255, 255)
PRETO = (26, 37, 44)


def _limpar_texto(texto):
    """Remove caracteres não-ASCII para evitar crash do FPDF."""
    if not texto:
        return ""
    return str(texto).encode('ascii', 'replace').decode('ascii')


def _fig_to_bytes(fig, dpi=200):
    """Converte matplotlib figure para bytes PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf


def _mapa_func_score(resultado_texto):
    """Converte texto do teste funcional pra score 0-10."""
    mapa = {
        "Sem Dor (0)": 10, "Sem Dor": 10,
        "Dor Leve (1 - 3)": 7, "Dor Leve": 7,
        "Dor Moderada (4 - 7)": 4, "Dor Moderada": 4,
        "Dor Grave (8 - 10)": 1, "Dor Grave": 1,
        "Incapaz (Não realiza)": 0, "Incapaz": 0,
    }
    return mapa.get(resultado_texto)


# ============================================================
# CLASSE PRINCIPAL DO PDF
# ============================================================
class LaudoGenua(FPDF):
    """PDF com cabeçalho e rodapé customizados."""

    def header(self):
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*TEAL)
        self.cell(0, 5, 'GENUA | Inteligencia Clinica Integrada', 0, 0, 'L')
        self.set_font('Arial', '', 8)
        self.set_text_color(*CINZA)
        self.cell(0, 5, f'Emitido em {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'R')
        self.set_draw_color(*TEAL)
        self.line(10, 12, 200, 12)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(*CINZA_CLARO)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font('Arial', 'I', 7)
        self.set_text_color(*CINZA)
        self.cell(0, 10, f'GENUA HealthTech - Documento confidencial - Pagina {self.page_no()}/{{nb}}', 0, 0, 'C')

    def secao(self, titulo, cor_fundo=CINZA_CLARO):
        """Bloco de título de seção estilizado."""
        self.set_font('Arial', 'B', 12)
        self.set_text_color(*AZUL)
        self.set_fill_color(*cor_fundo)
        self.cell(0, 9, f'  {titulo}', 0, 1, fill=True)
        self.ln(2)

    def kpi_box(self, x, y, w, h, label, valor, subtexto="", cor=AZUL):
        """Renderiza uma caixa de KPI com label, valor grande e subtexto."""
        self.set_xy(x, y)
        self.set_draw_color(*cor)
        self.set_line_width(0.8)
        self.rect(x, y, w, h)
        # Barra lateral colorida
        self.set_fill_color(*cor)
        self.rect(x, y, 3, h, 'F')
        # Label
        inner_w = w - 8
        if inner_w < 10:
            inner_w = 10
        self.set_xy(x + 5, y + 2)
        self.set_font('Arial', '', 8)
        self.set_text_color(*CINZA)
        self.cell(inner_w, 4, _limpar_texto(str(label))[:30], 0, 2)
        # Valor grande
        self.set_font('Arial', 'B', 20)
        self.set_text_color(*cor)
        self.cell(inner_w, 11, _limpar_texto(str(valor))[:20], 0, 2)
        # Subtexto
        if subtexto:
            self.set_font('Arial', '', 6)
            self.set_text_color(*CINZA)
            self.cell(inner_w, 4, _limpar_texto(str(subtexto))[:40], 0, 2)

    def tabela_simples(self, headers, rows, col_widths=None):
        """Renderiza tabela com header azul e linhas alternadas."""
        if not col_widths:
            col_widths = [190 // len(headers)] * len(headers)

        # Garante que x começa na margem esquerda
        self.set_x(10)

        # Header
        self.set_font('Arial', 'B', 8)
        self.set_fill_color(*AZUL)
        self.set_text_color(*BRANCO)
        for i, h in enumerate(headers):
            w = col_widths[i]
            # Trunca texto ao tamanho máximo que cabe na célula (~2 chars por mm)
            max_chars = max(3, int(w * 0.5))
            txt = _limpar_texto(h)[:max_chars]
            self.cell(w, 7, txt, 1, 0, 'C', fill=True)
        self.ln()

        # Rows
        self.set_font('Arial', '', 7)
        self.set_text_color(*PRETO)
        for r_idx, row in enumerate(rows):
            self.set_x(10)
            if r_idx % 2 == 0:
                self.set_fill_color(*CINZA_CLARO)
            else:
                self.set_fill_color(*BRANCO)
            for i, cell_val in enumerate(row):
                w = col_widths[i]
                max_chars = max(3, int(w * 0.5))
                txt = _limpar_texto(str(cell_val))[:max_chars]
                self.cell(w, 6, txt, 1, 0, 'C', fill=True)
            self.ln()


# ============================================================
# FUNÇÃO PRINCIPAL: gerar_laudo()
# ============================================================
def gerar_laudo(paciente_nome, dados_aval, historico, insights=None, fenotipo=None):
    """
    Gera o PDF completo do laudo clínico.

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

    # Ordena histórico
    hist = sorted(historico, key=lambda x: x.get('Data', '')) if historico else []
    n_sessoes = len(hist)

    # Dados derivados
    dor_inicial = float(hist[0].get('Dor', 0)) if hist else 0
    dor_atual = float(hist[-1].get('Dor', 0)) if hist else 0
    delta_dor = dor_inicial - dor_atual
    flex_inicial = float(hist[0].get('Flexao', 0)) if hist else 0
    flex_atual = float(hist[-1].get('Flexao', 0)) if hist else 0
    dx_texto = dados_aval.get('Diagnostico_Clinico', '') if dados_aval else ''
    fen_label = fenotipo.get('label', 'Nao especificado') if fenotipo else 'Nao especificado'

    # ==================================================================
    # PÁGINA 1: CAPA + SUMÁRIO EXECUTIVO
    # ==================================================================
    pdf.add_page()

    # Título grande
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 15, 'Laudo de Evolucao Clinica', 0, 1, 'C')
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 6, 'Fisioterapia Baseada em Evidencia', 0, 1, 'C')
    pdf.ln(8)

    # Dados do paciente
    pdf.set_draw_color(*CINZA_CLARO)
    pdf.set_fill_color(*CINZA_CLARO)
    pdf.rect(10, pdf.get_y(), 190, 22, 'F')
    pdf.set_xy(14, pdf.get_y() + 3)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*PRETO)
    pdf.cell(90, 6, f'Paciente: {_limpar_texto(paciente_nome)}', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(90, 6, f'Data: {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'R')
    pdf.set_x(14)
    idade = dados_aval.get('Idade', '-') if dados_aval else '-'
    pdf.cell(90, 6, f'Idade: {idade} anos', 0, 0)
    pdf.cell(90, 6, f'Dx: {_limpar_texto(str(dx_texto)[:60])}', 0, 1, 'R')
    pdf.ln(8)

    # Fenótipo (se identificado)
    if fenotipo and fenotipo.get('fenotipo') != 'generico':
        pdf.set_font('Arial', 'I', 9)
        pdf.set_text_color(*TEAL)
        tempo = fenotipo.get('tempo_esperado_semanas', '?')
        pdf.cell(0, 5, f'Fenotipo Clinico: {_limpar_texto(fen_label)} | Tempo esperado: {tempo} semanas', 0, 1, 'C')
        pdf.ln(3)

    # KPIs grandes (3 caixas)
    pdf.secao('SUMARIO EXECUTIVO')
    y_kpi = pdf.get_y() + 2
    w_kpi = 58

    sinal_dor = f'{delta_dor:+.0f} pts' if delta_dor != 0 else 'Sem variacao'
    cor_dor = VERDE if delta_dor > 0 else VERMELHO if delta_dor < 0 else CINZA
    pdf.kpi_box(12, y_kpi, w_kpi, 28, 'REDUCAO DA DOR',
                f'{dor_inicial:.0f} -> {dor_atual:.0f}', sinal_dor, cor_dor)

    delta_flex = flex_atual - flex_inicial
    sinal_flex = f'{delta_flex:+.0f} graus' if delta_flex != 0 else 'Sem variacao'
    cor_flex = VERDE if delta_flex > 0 else VERMELHO if delta_flex < 0 else CINZA
    pdf.kpi_box(75, y_kpi, w_kpi, 28, 'ADM FLEXAO',
                f'{flex_atual:.0f} graus', sinal_flex, cor_flex)

    pdf.kpi_box(138, y_kpi, w_kpi, 28, 'SESSOES REALIZADAS',
                str(n_sessoes), f'{hist[0].get("Data", "?")[:10]} a {hist[-1].get("Data", "?")[:10]}' if hist else '', AZUL)

    pdf.set_xy(10, y_kpi + 35)

    # Tabela resumo últimas 5 sessões
    if hist:
        pdf.secao('ULTIMAS SESSOES')
        headers = ['Data', 'Dor (EVA)', 'Flexao', 'Extensao', 'Inchaco', 'Sono']
        rows = []
        for ev in hist[-5:]:
            rows.append([
                ev.get('Data', '-')[:10],
                str(ev.get('Dor', '-')),
                str(ev.get('Flexao', '-')),
                str(ev.get('Extensao', '-'))[:12],
                str(ev.get('Inchaço', ev.get('Inchaco', '-')))[:10],
                str(ev.get('Sono', '-'))[:10]
            ])
        pdf.tabela_simples(headers, rows, [30, 25, 25, 35, 35, 40])

    # ==================================================================
    # PÁGINA 2: EVOLUÇÃO DA DOR
    # ==================================================================
    if hist and n_sessoes >= 2:
        pdf.add_page()
        pdf.secao('CURVA DE EVOLUCAO DA DOR (EVA)')

        datas = [ev.get('Data', '')[:5] for ev in hist]
        dores = [float(ev.get('Dor', 0)) for ev in hist]

        fig, ax = plt.subplots(figsize=(7, 3))
        ax.plot(datas, dores, marker='o', color='#103E55', linewidth=2.5, markersize=6, zorder=3)
        ax.fill_between(range(len(datas)), dores, alpha=0.1, color='#103E55')

        # Linha MCID (2 pontos)
        if dor_inicial > 2:
            ax.axhline(y=dor_inicial - 2, color='#28a745', linestyle='--', lw=1.5, alpha=0.7, label='Meta MCID (-2 pts)')
            ax.legend(fontsize=8, loc='upper right')

        ax.set_ylabel('Dor (EVA 0-10)', fontweight='bold')
        ax.set_ylim(-0.5, 10.5)
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.xticks(rotation=35, ha='right', fontsize=8)
        fig.tight_layout()

        buf = _fig_to_bytes(fig)
        pdf.image(buf, x=10, w=190, h=65)
        pdf.ln(2)

        # Interpretação textual
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(*PRETO)
        if delta_dor >= 2:
            pdf.multi_cell(0, 5, f'Interpretacao: Reducao clinicamente significativa de {delta_dor:.0f} pontos na EVA (MCID = 2 pts, Salaffi 2004). Evolucao positiva.')
        elif delta_dor > 0:
            pdf.multi_cell(0, 5, f'Interpretacao: Reducao de {delta_dor:.0f} ponto(s) na EVA, porem abaixo do limiar de significancia clinica (MCID = 2 pts, Salaffi 2004).')
        elif delta_dor == 0:
            pdf.multi_cell(0, 5, 'Interpretacao: Dor estavel ao longo do periodo. Considerar revisao do plano terapeutico.')
        else:
            pdf.multi_cell(0, 5, f'Interpretacao: Piora de {abs(delta_dor):.0f} ponto(s) na EVA. Investigar adesao, sobrecarga ou novo trauma.')

    # ==================================================================
    # PÁGINA 3: CORRELAÇÃO DOR × FUNÇÃO
    # ==================================================================
    if hist and n_sessoes >= 2:
        pdf.add_page()
        pdf.secao('CORRELACAO DOR x FUNCAO')
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(*CINZA)
        pdf.multi_cell(0, 4, 'Este grafico mostra se a reducao da dor foi acompanhada de melhora funcional. Quando as linhas se cruzam (dor caindo, funcao subindo), o tratamento esta sendo eficaz.')
        pdf.ln(3)

        datas = [ev.get('Data', '')[:5] for ev in hist]
        dores = [float(ev.get('Dor', 0)) for ev in hist]

        # Calcula score funcional por sessão
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

        fig, ax1 = plt.subplots(figsize=(7, 3.2))
        ax1.plot(datas, dores, color='#dc3545', marker='o', lw=2.5, label='Dor (EVA)', zorder=3)
        ax1.fill_between(range(len(datas)), dores, alpha=0.08, color='#dc3545')
        ax1.set_ylabel('Dor (EVA 0-10)', color='#dc3545', fontweight='bold')
        ax1.set_ylim(-0.5, 10.5)

        ax2 = ax1.twinx()
        # Interpola valores None
        func_clean = []
        for v in func_scores:
            func_clean.append(v if v is not None else np.nan)
        func_arr = np.array(func_clean, dtype=float)
        mask = ~np.isnan(func_arr)
        if mask.sum() >= 2:
            func_interp = np.interp(range(len(func_arr)), np.where(mask)[0], func_arr[mask])
            ax2.plot(datas, func_interp, color='#28a745', marker='s', lw=2.5, linestyle='--', label='Funcao', zorder=3)
            ax2.fill_between(range(len(datas)), func_interp, alpha=0.08, color='#28a745')

        ax2.set_ylabel('Funcao (0-10)', color='#28a745', fontweight='bold')
        ax2.set_ylim(-0.5, 10.5)

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center', ncol=2, fontsize=8, framealpha=0.9)

        ax1.spines['top'].set_visible(False)
        ax2.spines['top'].set_visible(False)
        plt.xticks(rotation=35, ha='right', fontsize=8)
        fig.tight_layout()

        buf = _fig_to_bytes(fig)
        pdf.image(buf, x=10, w=190, h=70)
        pdf.ln(3)

        # Tabela evolução por teste funcional
        if testes_evolucao:
            pdf.secao('EVOLUCAO POR TESTE FUNCIONAL')
            headers = ['Teste', 'Inicio', 'Atual', 'Variacao']
            rows = []
            for nome, resultados in testes_evolucao.items():
                primeiro = resultados[0] if resultados else '-'
                ultimo = resultados[-1] if resultados else '-'
                s_primeiro = _mapa_func_score(primeiro)
                s_ultimo = _mapa_func_score(ultimo)
                if s_primeiro is not None and s_ultimo is not None:
                    delta = s_ultimo - s_primeiro
                    var_text = f'{delta:+.0f} pts' if delta != 0 else 'Igual'
                else:
                    var_text = '-'
                rows.append([_limpar_texto(nome)[:25], _limpar_texto(str(primeiro))[:20],
                             _limpar_texto(str(ultimo))[:20], var_text])
            pdf.tabela_simples(headers, rows, [55, 50, 50, 35])

    # ==================================================================
    # PÁGINA 4: PROMs E SCORES
    # ==================================================================
    if dados_aval:
        pdf.add_page()
        pdf.secao('METRICAS BASEADAS EM EVIDENCIA (PROMs)')
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(*CINZA)
        pdf.multi_cell(0, 4, 'Patient-Reported Outcome Measures (PROMs) sao questionarios validados cientificamente para mensurar a perspectiva do paciente sobre sua condicao.')
        pdf.ln(3)

        proms_data = [
            ("LEFS", "Funcionalidade Geral MMII", dados_aval.get("LEFS_Pct", 0), "%", "9 pts (Binkley 1999)", dados_aval.get("Interpretacao_LEFS", "-")),
            ("VISA-P", "Tendinopatia Patelar", dados_aval.get("VISA_P_Pts", 0), "pts", "13 pts (Hernandez 2014)", dados_aval.get("Interpretacao_VISA_P", "-")),
            ("Lysholm", "Lesao Ligamentar/Meniscal", dados_aval.get("Lysholm_Pts", 0), "pts", "10 pts (Briggs 2009)", dados_aval.get("Interpretacao_Lysholm", "-")),
            ("WOMAC", "Osteoartrite", dados_aval.get("WOMAC_Pct", 0), "%", "~12% (Angst 2001)", dados_aval.get("Interpretacao_WOMAC", "-")),
            ("KOOS", "Score Agregado Joelho", dados_aval.get("KOOS_Pct", 0), "%", "8-10 pts (Roos 2003)", "-"),
            ("IKDC", "Subjetivo Joelho", dados_aval.get("IKDC_Pct", 0), "%", "9 pts (Irrgang 2006)", "-"),
        ]

        headers = ['PROM', 'Indicacao', 'Score', 'MCID', 'Interpretacao']
        rows = []
        for nome, indicacao, score, un, mcid, interp in proms_data:
            try:
                score_f = float(score)
            except (ValueError, TypeError):
                score_f = 0
            if score_f > 0:
                rows.append([nome, indicacao[:25], f'{score_f:.1f}{un}', mcid[:20], _limpar_texto(str(interp))[:30]])

        if rows:
            pdf.tabela_simples(headers, rows, [22, 50, 25, 42, 51])
        else:
            pdf.set_font('Arial', 'I', 9)
            pdf.cell(0, 6, 'Nenhum PROM com valor > 0 registrado nesta avaliacao.', 0, 1)

        # Avaliação inicial: dados complementares
        pdf.ln(5)
        pdf.secao('DADOS DA AVALIACAO INICIAL')
        campos = [
            ("Queixa Principal", dados_aval.get("QP", "-")),
            ("Classificacao da Dor", dados_aval.get("Class_Dor", "-")),
            ("Derrame Articular", dados_aval.get("Derrame", "-")),
            ("Comorbidades", dados_aval.get("Comorbidades", "-")),
            ("Alinhamento", dados_aval.get("Alinhamento", "-")),
            ("Exames", dados_aval.get("Exames_Apresentados", "-")),
        ]
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(*PRETO)
        for label, valor in campos:
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(50, 5, f'{label}:', 0, 0)
            pdf.set_font('Arial', '', 9)
            pdf.multi_cell(0, 5, _limpar_texto(str(valor))[:80])

    # ==================================================================
    # PÁGINA 5: INSIGHTS IA + LSI + BANDEIRAS
    # ==================================================================
    if insights:
        pdf.add_page()
        pdf.secao('ANALISE DE INTELIGENCIA CLINICA (IA)')
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(*CINZA)
        pdf.multi_cell(0, 4, 'Analise automatizada baseada em regras clinicas validadas pela literatura. Toda regra e auditavel e transparente.')
        pdf.ln(3)

        # Estagnação
        est = insights.get('estagnacao')
        if est and est.get('status') not in ('insuficiente', None):
            pdf.set_font('Arial', 'B', 10)
            if est['status'] == 'estagnacao':
                pdf.set_text_color(*VERMELHO)
                pdf.cell(0, 6, 'ESTAGNACAO DETECTADA', 0, 1)
            elif est['status'] == 'melhora':
                pdf.set_text_color(*VERDE)
                pdf.cell(0, 6, 'EVOLUCAO POSITIVA', 0, 1)
            elif est['status'] == 'piora':
                pdf.set_text_color(*VERMELHO)
                pdf.cell(0, 6, 'PIORA CLINICA', 0, 1)
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(*PRETO)
            pdf.multi_cell(0, 5, _limpar_texto(est.get('racional', '')))
            pdf.set_font('Arial', 'I', 7)
            pdf.set_text_color(*CINZA)
            pdf.cell(0, 4, f'Ref: {_limpar_texto(est.get("referencia", ""))}', 0, 1)
            pdf.ln(3)

        # LSI
        lsi_data = insights.get('lsi')
        if lsi_data and lsi_data.get('valor') is not None:
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(*AZUL)
            pdf.cell(0, 6, f'LIMB SYMMETRY INDEX (LSI): {lsi_data["valor"]}%', 0, 1)
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(*PRETO)
            pdf.multi_cell(0, 5, _limpar_texto(lsi_data.get('acao', '')))
            pdf.set_font('Arial', 'I', 7)
            pdf.set_text_color(*CINZA)
            pdf.cell(0, 4, f'Ref: {_limpar_texto(lsi_data.get("referencia", ""))}', 0, 1)
            pdf.ln(3)

        # Bandeiras
        bandeiras = insights.get('bandeiras', [])
        if bandeiras:
            pdf.secao('BANDEIRAS CLINICAS ATIVAS')
            for b in bandeiras:
                tipo = str(b.get('tipo', 'info')).upper()
                if tipo == 'VERMELHA':
                    pdf.set_text_color(*VERMELHO)
                elif tipo == 'AMARELA':
                    pdf.set_text_color(200, 150, 0)
                else:
                    pdf.set_text_color(*AZUL)
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(0, 5, f'BANDEIRA {tipo}: {_limpar_texto(b.get("gatilho", ""))}', 0, 1)
                pdf.set_font('Arial', '', 8)
                pdf.set_text_color(*PRETO)
                pdf.cell(0, 4, f'Acao: {_limpar_texto(b.get("acao", ""))}', 0, 1)
                pdf.set_font('Arial', 'I', 7)
                pdf.set_text_color(*CINZA)
                pdf.cell(0, 4, f'Ref: {_limpar_texto(b.get("referencia", ""))}', 0, 1)
                pdf.ln(2)
        else:
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(*VERDE)
            pdf.cell(0, 6, 'Nenhuma bandeira clinica ativa. Perfil de baixo risco.', 0, 1)

    # ==================================================================
    # ÚLTIMA PÁGINA: ASSINATURA
    # ==================================================================
    pdf.add_page()
    pdf.ln(20)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*CINZA)
    pdf.multi_cell(0, 5, 'Este laudo foi gerado automaticamente pelo sistema GENUA de Inteligencia Clinica. '
                         'As analises sao baseadas em regras clinicas validadas pela literatura cientifica (referencias citadas). '
                         'O diagnostico e a conduta final sao de responsabilidade exclusiva do fisioterapeuta responsavel.')
    pdf.ln(20)

    # Linha de assinatura
    pdf.set_draw_color(*PRETO)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(3)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*PRETO)
    pdf.cell(0, 6, 'Fisioterapeuta Responsavel', 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 5, 'GENUA Instituto de Fisioterapia Esportiva', 0, 1, 'C')
    pdf.cell(0, 5, f'CREFITO: ____________  |  Data: {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')

    pdf.ln(15)
    pdf.set_font('Arial', 'I', 7)
    pdf.set_text_color(*CINZA)
    pdf.cell(0, 4, 'GENUA HealthTech (c) 2026 | Ambiente seguro | Dados confidenciais protegidos pela LGPD', 0, 1, 'C')

    # Gera bytes
    try:
        return pdf.output(dest='S').encode('latin-1')
    except Exception:
        return bytes(pdf.output())
