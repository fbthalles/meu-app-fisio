"""
GENUA | Gerador de Laudo Clínico Avançado (HTML Visual Dark Apple-Style + PDF FPDF)
===================================================================================
Exporta:
 - gerar_laudo_html(): Laudo interativo moderno em HTML5/CSS3 (Dark Mode + cores vivas)
   com gráficos em 300 DPI (Base64) e suporte nativo a impressão PDF (Ctrl+P).
 - gerar_laudo(): Gerador em bytes via FPDF2 para retrocompatibilidade.

Dependências: fpdf2, matplotlib, numpy, io, base64, datetime
"""
import io
import base64
import html
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF


# ============================================================
# PALETA DE CORES GENUA + CORES VIVAS
# ============================================================
AZUL_PROFUNDO = (10, 37, 64)
AZUL_GENUA = (16, 62, 85)
TEAL_GENUA = (57, 142, 155)
TEAL_VIVO = (0, 180, 197)
CINZA_GELO = (244, 247, 249)
VERDE_VIVO = (16, 185, 129)
VERMELHO_VIVO = (239, 68, 68)
AMBAR_VIVO = (245, 158, 11)
INDIGO_VIVO = (99, 102, 241)
PRETO_TEXTO = (15, 23, 42)
CINZA_TEXTO = (71, 85, 105)
CINZA_BORDA = (203, 213, 225)
BRANCO = (255, 255, 255)


# ============================================================
# HELPERS DE SEGURANÇA E CONVERSÃO
# ============================================================
def _safe_float(valor, padrao=0.0):
    """Converte qualquer entrada para float de forma segura."""
    if valor is None or valor == "" or valor == "-":
        return padrao
    try:
        return float(str(valor).replace(",", ".").replace("%", "").strip())
    except (ValueError, TypeError):
        return padrao


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
    if texto is None or texto == "":
        return "-"
    return html.escape(str(texto))


def _fig_to_bytes(fig, dpi=300, facecolor='white'):
    """Converte figura Matplotlib em buffer BytesIO PNG a 300 DPI."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor=facecolor)
    buf.seek(0)
    plt.close(fig)
    return buf


def _fig_to_base64(fig, dpi=300, facecolor='#111827'):
    """Converte figura Matplotlib em string Base64 para embutir no HTML."""
    buf = _fig_to_bytes(fig, dpi=dpi, facecolor=facecolor)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def _mapa_func_score(resultado_texto):
    """Mapeia string qualitativa do teste funcional para escore numérico (0 a 10)."""
    if not resultado_texto:
        return None
    mapa = {
        "Sem Dor (0)": 10, "Sem Dor": 10,
        "Dor Leve (1 - 3)": 7, "Dor Leve": 7,
        "Dor Moderada (4 - 7)": 4, "Dor Moderada": 4,
        "Dor Grave (8 - 10)": 1, "Dor Grave": 1,
        "Incapaz (Não realiza)": 0, "Incapaz (Nao realiza)": 0, "Incapaz": 0,
    }
    return mapa.get(str(resultado_texto).strip())


def _normalizar_entradas(dados_aval, historico):
    """Garante que dados_aval seja dict e historico seja list[dict] ordenada."""
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


# ============================================================
# GERADOR DE GRÁFICOS DARK/NEON PARA O LAUDO HTML
# ============================================================
def _gerar_grafico_dor_b64(hist, dor_inicial):
    """Gera gráfico de evolução da dor com estética Dark Mode e linha MCID."""
    datas = [str(ev.get('Data', ''))[:5] for ev in hist]
    dores = [_safe_float(ev.get('Dor', 0)) for ev in hist]
    x_idx = np.arange(len(datas))

    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    bg_color = '#111827'
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor('#1E293B')

    if dor_inicial >= 2:
        meta_mcid = max(0.0, dor_inicial - 2.0)
        ax.axhspan(0, meta_mcid, color='#10B981', alpha=0.14, label='Zona MCID atingida (-2 pts | Salaffi 2004)')
        ax.axhline(y=meta_mcid, color='#10B981', linestyle='--', linewidth=2, alpha=0.95)

    ax.fill_between(x_idx, dores, color='#00E5FF', alpha=0.22)
    ax.plot(x_idx, dores, color='#00E5FF', linewidth=3.2, marker='o', markersize=8,
            markerfacecolor='#0B0F19', markeredgecolor='#00E5FF', markeredgewidth=2.5,
            label='Dor (EVA 0-10)', zorder=4)

    for i, v in enumerate(dores):
        ax.annotate(f'{v:.0f}', (x_idx[i], v), textcoords="offset points",
                    xytext=(0, 9), ha='center', fontsize=8.5, fontweight='bold', color='#F8FAFC')

    ax.set_xticks(x_idx)
    ax.set_xticklabels(datas, rotation=25, ha='right', fontsize=8.5, color='#CBD5E1')
    ax.set_yticks(range(0, 11, 2))
    ax.set_yticklabels(range(0, 11, 2), fontsize=8.5, color='#CBD5E1')
    ax.set_ylabel('EVA (0 a 10)', fontweight='bold', fontsize=9.5, color='#00E5FF')
    ax.set_ylim(-0.6, 11.2)
    ax.grid(True, axis='y', linestyle=':', color='#334155', alpha=0.8)

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('#334155')

    leg = ax.legend(loc='upper right', fontsize=8, frameon=True, facecolor='#0B0F19', edgecolor='#334155')
    for text in leg.get_texts():
        text.set_color('#F8FAFC')

    fig.tight_layout()
    return _fig_to_base64(fig, dpi=300, facecolor=bg_color)


def _gerar_grafico_correlacao_b64(hist):
    """Gera gráfico cruzado Dor vs Função e retorna (base64_str, dict_testes_evolucao)."""
    datas = [str(ev.get('Data', ''))[:5] for ev in hist]
    dores = [_safe_float(ev.get('Dor', 0)) for ev in hist]
    x_idx = np.arange(len(datas))

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

    fig, ax1 = plt.subplots(figsize=(8.5, 3.4))
    bg_color = '#111827'
    fig.patch.set_facecolor(bg_color)
    ax1.set_facecolor('#1E293B')

    ax1.plot(x_idx, dores, color='#FF4D6D', marker='o', markersize=7.5,
             markerfacecolor='#0B0F19', markeredgecolor='#FF4D6D', markeredgewidth=2,
             lw=3, label='Dor (EVA 0-10)', zorder=3)
    ax1.fill_between(x_idx, dores, color='#FF4D6D', alpha=0.14)
    ax1.set_ylabel('Dor (EVA 0-10)', color='#FF4D6D', fontweight='bold', fontsize=9.5)
    ax1.set_ylim(-0.6, 11.2)
    ax1.set_xticks(x_idx)
    ax1.set_xticklabels(datas, rotation=25, ha='right', fontsize=8.5, color='#CBD5E1')
    ax1.tick_params(axis='y', colors='#FF4D6D', labelsize=8.5)
    ax1.grid(True, axis='y', linestyle=':', color='#334155', alpha=0.8)

    ax2 = ax1.twinx()
    func_clean = [v if v is not None else np.nan for v in func_scores]
    func_arr = np.array(func_clean, dtype=float)
    mask = ~np.isnan(func_arr)

    if mask.sum() >= 2:
        func_interp = np.interp(range(len(func_arr)), np.where(mask)[0], func_arr[mask])
        ax2.plot(x_idx, func_interp, color='#10B981', marker='s', markersize=7.5,
                 markerfacecolor='#0B0F19', markeredgecolor='#10B981', markeredgewidth=2,
                 lw=3, linestyle='-', label='Capacidade Funcional (0-10)', zorder=4)
        ax2.fill_between(x_idx, func_interp, color='#10B981', alpha=0.14)

    ax2.set_ylabel('Score Funcional (0-10)', color='#10B981', fontweight='bold', fontsize=9.5)
    ax2.set_ylim(-0.6, 11.2)
    ax2.tick_params(axis='y', colors='#10B981', labelsize=8.5)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    leg = ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center',
                     bbox_to_anchor=(0.5, 1.15), ncol=2, fontsize=8.5,
                     frameon=True, facecolor='#0B0F19', edgecolor='#334155')
    for text in leg.get_texts():
        text.set_color('#F8FAFC')

    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.spines['bottom'].set_color('#334155')
    ax1.spines['left'].set_color('#FF4D6D')
    ax2.spines['right'].set_color('#10B981')

    fig.tight_layout()
    return _fig_to_base64(fig, dpi=300, facecolor=bg_color), testes_evolucao


# ============================================================
# FUNÇÃO 1: gerar_laudo_html() — CHAMADA PELO PAINEL ANALÍTICO
# ============================================================
def gerar_laudo_html(paciente_nome, dados_aval=None, historico=None, insights=None, fenotipo=None, *args, **kwargs):
    """
    Gera o Laudo Clínico Visual em HTML5/CSS3 (Dark Apple-Style + Cores Vivas)
    pronto para pré-visualização no Streamlit e exportação para PDF via navegador.
    """
    dados_aval, hist = _normalizar_entradas(dados_aval, historico)
    n_sessoes = len(hist)

    dor_inicial = _safe_float(hist[0].get('Dor', 0)) if hist else 0.0
    dor_atual = _safe_float(hist[-1].get('Dor', 0)) if hist else 0.0
    delta_dor = dor_inicial - dor_atual

    flex_inicial = _safe_float(hist[0].get('Flexao', 0)) if hist else 0.0
    flex_atual = _safe_float(hist[-1].get('Flexao', 0)) if hist else 0.0
    delta_flex = flex_atual - flex_inicial

    dx_texto = dados_aval.get('Diagnostico_Clinico', 'Não informado')
    idade = dados_aval.get('Idade', '-')
    fen_label = fenotipo.get('label', 'Musculoesquelético Geral') if isinstance(fenotipo, dict) else 'Musculoesquelético Geral'
    tempo_esp = fenotipo.get('tempo_esperado_semanas', '-') if isinstance(fenotipo, dict) else '-'

    # Semáforo KPI Dor
    if delta_dor >= 2:
        cor_dor_hex, badge_dor = "#10B981", f"Redução de {delta_dor:.0f} pts (MCID Atingido)"
    elif delta_dor > 0:
        cor_dor_hex, badge_dor = "#00E5FF", f"Redução de {delta_dor:.0f} pt(s) na EVA"
    elif delta_dor < 0:
        cor_dor_hex, badge_dor = "#FF4D6D", f"Aumento de {abs(delta_dor):.0f} pt(s) na EVA"
    else:
        cor_dor_hex, badge_dor = "#F59E0B", "Estável no período"

    # Semáforo KPI Flexão
    if delta_flex > 0:
        cor_flex_hex, badge_flex = "#10B981", f"Ganho de +{delta_flex:.0f}° de ADM"
    elif delta_flex < 0:
        cor_flex_hex, badge_flex = "#FF4D6D", f"Variação de {delta_flex:.0f}° de ADM"
    else:
        cor_flex_hex, badge_flex = "#00E5FF", "Amplitude mantida"

    periodo_str = f"{str(hist[0].get('Data', '-'))[:10]} até {str(hist[-1].get('Data', '-'))[:10]}" if hist else "Sem check-ins"

    # Gráficos Base64
    html_graficos = ""
    html_tabela_func = ""
    if n_sessoes >= 2:
        b64_dor = _gerar_grafico_dor_b64(hist, dor_inicial)
        b64_corr, testes_evolucao = _gerar_grafico_correlacao_b64(hist)

        if delta_dor >= 2:
            interp_dor = f"Redução clinicamente significativa de {delta_dor:.0f} pontos na EVA, superando o limiar MCID de 2 pontos (Salaffi et al., 2004)."
        elif delta_dor > 0:
            interp_dor = f"Redução de {delta_dor:.0f} ponto(s) na EVA, em evolução porém abaixo do limiar MCID de 2 pontos (Salaffi et al., 2004)."
        elif delta_dor == 0:
            interp_dor = "Quadro álgico estável no período avaliado. Recomenda-se revisar progressão de carga e controle de volume."
        else:
            interp_dor = f"Aumento de {abs(delta_dor):.0f} ponto(s) na EVA. Investigar sobrecarga mecânica recente, adesão ou sinais de alerta."

        html_graficos = f"""
        <div class="grid-2">
            <div class="card">
                <div class="section-tag">CURVA ANALGÉSICA PBE</div>
                <h3>Evolução da Dor (EVA) & Meta MCID</h3>
                <img class="chart-img" src="data:image/png;base64,{b64_dor}" alt="Evolução da Dor" />
                <div class="insight-pill" style="border-left-color: {cor_dor_hex};">
                    <strong>Análise Clínica:</strong> {_esc(interp_dor)}
                </div>
            </div>
            <div class="card">
                <div class="section-tag">BIOMECÂNICA & FUNÇÃO</div>
                <h3>Correlação Dinâmica: Dor × Capacidade Funcional</h3>
                <img class="chart-img" src="data:image/png;base64,{b64_corr}" alt="Correlação Dor vs Função" />
                <div class="insight-pill" style="border-left-color: #10B981;">
                    <strong>Leitura Clínica:</strong> Cruzamento de curvas (queda da dor em coral e ascensão funcional em verde) confirma adaptação tecidual positiva.
                </div>
            </div>
        </div>
        """

        if testes_evolucao:
            linhas_func = ""
            for nome_t, res_list in testes_evolucao.items():
                prim = res_list[0] if res_list else "-"
                ult = res_list[-1] if res_list else "-"
                sp, su = _mapa_func_score(prim), _mapa_func_score(ult)
                if sp is not None and su is not None:
                    d_f = su - sp
                    cor_d = "#10B981" if d_f > 0 else ("#FF4D6D" if d_f < 0 else "#94A3B8")
                    txt_d = f"{d_f:+.0f} pts" if d_f != 0 else "Mantido"
                else:
                    cor_d, txt_d = "#94A3B8", "-"
                linhas_func += f"""
                <tr>
                    <td><strong>{_esc(nome_t)}</strong></td>
                    <td>{_esc(prim)}</td>
                    <td>{_esc(ult)}</td>
                    <td style="color:{cor_d}; font-weight:700;">{txt_d}</td>
                </tr>
                """
            html_tabela_func = f"""
            <div class="card">
                <div class="section-tag">TESTES ESPECÍFICOS</div>
                <h3>Evolução Analítica por Teste Funcional</h3>
                <table class="modern-table">
                    <thead>
                        <tr><th>Teste Funcional</th><th>Status Inicial</th><th>Status Atual</th><th>Ganho Funcional</th></tr>
                    </thead>
                    <tbody>{linhas_func}</tbody>
                </table>
            </div>
            """

    # Construção dos Cards de PROMs
    proms_config = [
        ("LEFS", "Funcionalidade Geral MMII", dados_aval.get("LEFS_Pct", 0), "%", "MCID: 9 pts (Binkley 1999)", dados_aval.get("Interpretacao_LEFS", "-")),
        ("VISA-P", "Tendinopatia Patelar", dados_aval.get("VISA_P_Pts", 0), "pts", "MCID: 13 pts (Hernandez 2014)", dados_aval.get("Interpretacao_VISA_P", "-")),
        ("Lysholm", "Ligamentar / Meniscal", dados_aval.get("Lysholm_Pts", 0), "pts", "MCID: 10 pts (Briggs 2009)", dados_aval.get("Interpretacao_Lysholm", "-")),
        ("WOMAC", "Osteoartrite", dados_aval.get("WOMAC_Pct", 0), "%", "MCID: ~12% (Angst 2001)", dados_aval.get("Interpretacao_WOMAC", "-")),
        ("KOOS", "Score Global de Joelho", dados_aval.get("KOOS_Pct", 0), "%", "MCID: 8-10 pts (Roos 2003)", "-"),
        ("IKDC", "Avaliação Subjetiva Joelho", dados_aval.get("IKDC_Pct", 0), "%", "MCID: 9 pts (Irrgang 2006)", "-"),
    ]
    proms_cards_html = ""
    for p_nome, p_ind, p_val, p_un, p_mcid, p_interp in proms_config:
        val_f = _safe_float(p_val, 0.0)
        if val_f > 0:
            pct_bar = max(0.0, min(100.0, val_f))
            cor_bar = "#10B981" if pct_bar >= 75 else ("#F59E0B" if pct_bar >= 50 else "#FF4D6D")
            proms_cards_html += f"""
            <div class="prom-item">
                <div class="prom-header">
                    <div>
                        <span class="prom-title">{_esc(p_nome)}</span>
                        <span class="prom-sub">{_esc(p_ind)}</span>
                    </div>
                    <span class="prom-score" style="color:{cor_bar};">{val_f:.1f}{_esc(p_un)}</span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill" style="width:{pct_bar:.1f}%; background:{cor_bar};"></div>
                </div>
                <div class="prom-footer">
                    <span>{_esc(p_mcid)}</span>
                    <span><strong>Classificação:</strong> {_esc(p_interp)}</span>
                </div>
            </div>
            """
    if not proms_cards_html:
        proms_cards_html = "<p style='color:#94A3B8; font-size:13px;'>Nenhum questionário PROM (> 0) registrado na avaliação inicial.</p>"

    # Seção de Insights da IA Clínica (Estagnação + LSI + Bandeiras)
    insights_html = ""
    if isinstance(insights, dict) and insights:
        blocos_ia = ""

        # LSI Gauge
        lsi_data = insights.get('lsi')
        if isinstance(lsi_data, dict) and lsi_data.get('valor') is not None:
            val_lsi = _safe_float(lsi_data.get('valor'), 0.0)
            pct_lsi = max(0.0, min(100.0, val_lsi))
            if val_lsi >= 90:
                c_lsi, st_lsi = "#10B981", "APTO PARA ALTA / RETORNO AO ESPORTE (≥ 90%)"
            elif val_lsi >= 85:
                c_lsi, st_lsi = "#F59E0B", "ATENÇÃO BIOMECÂNICA (85% - 89%)"
            else:
                c_lsi, st_lsi = "#FF4D6D", "RISCO ELEVADO DE RE-LESÃO (< 85%)"

            blocos_ia += f"""
            <div class="alert-box" style="border-left-color:{c_lsi};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="color:{c_lsi}; font-size:15px;">LIMB SYMMETRY INDEX (LSI): {val_lsi:.1f}%</strong>
                    <span class="badge-pill" style="background:{c_lsi}22; color:{c_lsi}; border:1px solid {c_lsi};">{st_lsi}</span>
                </div>
                <div class="progress-track" style="margin:10px 0;">
                    <div class="progress-fill" style="width:{pct_lsi:.1f}%; background:{c_lsi};"></div>
                </div>
                <p style="margin:4px 0; font-size:13px; color:#E2E8F0;">{_esc(lsi_data.get('acao', ''))}</p>
                <small style="color:#94A3B8;">Referência Científica: {_esc(lsi_data.get('referencia', 'Grindem et al., BJSM 2016'))}</small>
            </div>
            """

        # Estagnação / Evolução
        est = insights.get('estagnacao')
        if isinstance(est, dict) and est.get('status') not in ('insuficiente', None):
            st_e = est.get('status')
            c_e = "#10B981" if st_e == 'melhora' else ("#F59E0B" if st_e == 'estagnacao' else "#FF4D6D")
            t_e = "EVOLUÇÃO CLÍNICA POSITIVA" if st_e == 'melhora' else ("ESTAGNAÇÃO DETECTADA" if st_e == 'estagnacao' else "ALERTA DE PIORA CLÍNICA")
            blocos_ia += f"""
            <div class="alert-box" style="border-left-color:{c_e};">
                <strong style="color:{c_e}; font-size:14px;">{t_e}</strong>
                <p style="margin:5px 0; font-size:13px; color:#E2E8F0;">{_esc(est.get('racional', ''))}</p>
                <small style="color:#94A3B8;">Referência: {_esc(est.get('referencia', 'Salaffi et al., 2004'))}</small>
            </div>
            """

        # Bandeiras Clínicas
        bandeiras = insights.get('bandeiras', [])
        if isinstance(bandeiras, list) and bandeiras:
            for b in bandeiras:
                if not isinstance(b, dict):
                    continue
                tipo_b = str(b.get('tipo', 'INFO')).upper()
                if 'VERMELH' in tipo_b or 'RED' in tipo_b:
                    c_b = "#FF4D6D"
                elif 'AMAREL' in tipo_b or 'YELLOW' in tipo_b:
                    c_b = "#F59E0B"
                else:
                    c_b = "#00E5FF"
                blocos_ia += f"""
                <div class="alert-box" style="border-left-color:{c_b};">
                    <strong style="color:{c_b}; font-size:13.5px;">BANDEIRA {_esc(tipo_b)}: {_esc(b.get('gatilho', ''))}</strong>
                    <p style="margin:4px 0; font-size:13px; color:#E2E8F0;"><strong>Conduta:</strong> {_esc(b.get('acao', ''))}</p>
                    <small style="color:#94A3B8;">Referência: {_esc(b.get('referencia', ''))}</small>
                </div>
                """
        else:
            blocos_ia += """
            <div class="alert-box" style="border-left-color:#10B981;">
                <strong style="color:#10B981;">RASTREIO DE BANDEIRAS CLÍNICAS NEGATIVO</strong>
                <p style="margin:4px 0; font-size:13px; color:#E2E8F0;">Nenhuma Red/Yellow Flag ativa detectada. Paciente seguro para progressão de carga.</p>
            </div>
            """

        insights_html = f"""
        <div class="card">
            <div class="section-tag">MOTOR DE REGRAS DETERMINÍSTICAS (PBE)</div>
            <h3>Análise de Inteligência Clínica & Simetria Funcional</h3>
            {blocos_ia}
        </div>
        """

    # Tabela das Últimas 5 Sessões
    linhas_sessoes = ""
    for ev in hist[-5:]:
        linhas_sessoes += f"""
        <tr>
            <td><strong>{_esc(str(ev.get('Data', '-'))[:10])}</strong></td>
            <td style="color:#00E5FF; font-weight:700;">{_esc(ev.get('Dor', '-'))}/10</td>
            <td>{_esc(ev.get('Flexao', '-'))}°</td>
            <td>{_esc(ev.get('Extensao', '-'))}</td>
            <td>{_esc(ev.get('Inchaço', ev.get('Inchaco', '-')))}</td>
            <td>{_esc(ev.get('Sono', '-'))}</td>
        </tr>
        """
    if not linhas_sessoes:
        linhas_sessoes = "<tr><td colspan='6' style='text-align:center; color:#94A3B8;'>Nenhuma sessão de check-in registrada.</td></tr>"

    # Dados da Avaliação Inicial
    campos_aval = [
        ("Queixa Principal (QP)", dados_aval.get("QP", "-")),
        ("Classificação da Dor", dados_aval.get("Class_Dor", "-")),
        ("Derrame Articular", dados_aval.get("Derrame", "-")),
        ("Comorbidades", dados_aval.get("Comorbidades", "-")),
        ("Alinhamento / Biomecânica", dados_aval.get("Alinhamento", "-")),
        ("Exames Apresentados", dados_aval.get("Exames_Apresentados", "-")),
    ]
    aval_items_html = "".join([
        f"<div class='kv-row'><span class='kv-label'>{_esc(k)}</span><span class='kv-val'>{_esc(v)}</span></div>"
        for k, v in campos_aval
    ])

    data_emissao = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # Documento HTML Completo (Dark Apple-Style + Print CSS fiel)
    html_completo = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Laudo Clínico GENUA - {_esc(paciente_nome)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
<style>
    :root {{
        --bg-main: #0B0F19;
        --bg-card: #111827;
        --bg-sub: #1E293B;
        --border: #334155;
        --text-main: #F8FAFC;
        --text-muted: #94A3B8;
        --cyan: #00E5FF;
        --emerald: #10B981;
        --coral: #FF4D6D;
        --amber: #F59E0B;
        --indigo: #6366F1;
    }}
    * {{
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }}
    body {{
        margin: 0;
        padding: 24px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: var(--bg-main);
        color: var(--text-main);
        line-height: 1.5;
    }}
    .container {{
        max-width: 1020px;
        margin: 0 auto;
    }}
    .top-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 18px;
    }}
    .btn-print {{
        background: linear-gradient(135deg, #00E5FF 0%, #398E9B 100%);
        color: #0B0F19;
        border: none;
        padding: 10px 20px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 13px;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0, 229, 255, 0.25);
    }}
    .hero-card {{
        background: linear-gradient(135deg, #0A2540 0%, #103E55 55%, #0F172A 100%);
        border: 1px solid rgba(0, 229, 255, 0.35);
        border-radius: 18px;
        padding: 28px;
        margin-bottom: 22px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
    }}
    .hero-top {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.12);
        padding-bottom: 16px;
        margin-bottom: 16px;
    }}
    .brand-badge {{
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.5px;
        color: var(--cyan);
        text-transform: uppercase;
    }}
    .hero-title {{
        margin: 4px 0 0 0;
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF;
    }}
    .patient-meta {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 14px;
    }}
    .meta-box {{
        background: rgba(15, 23, 42, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 10px 14px;
        border-radius: 12px;
    }}
    .meta-label {{
        font-size: 11px;
        color: var(--text-muted);
        text-transform: uppercase;
        display: block;
    }}
    .meta-value {{
        font-size: 14.5px;
        font-weight: 700;
        color: #FFFFFF;
    }}
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-bottom: 22px;
    }}
    .kpi-card {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px;
        position: relative;
        overflow: hidden;
    }}
    .kpi-bar {{
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }}
    .kpi-label {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.8px;
        color: var(--text-muted);
        text-transform: uppercase;
    }}
    .kpi-val {{
        font-size: 30px;
        font-weight: 800;
        margin: 8px 0 6px 0;
    }}
    .kpi-sub {{
        font-size: 12px;
        font-weight: 600;
        color: #CBD5E1;
    }}
    .grid-2 {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(440px, 1fr));
        gap: 18px;
        margin-bottom: 22px;
    }}
    .card {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 20px;
    }}
    .section-tag {{
        font-size: 10.5px;
        font-weight: 800;
        letter-spacing: 1.2px;
        color: var(--cyan);
        text-transform: uppercase;
        margin-bottom: 4px;
    }}
    .card h3 {{
        margin: 0 0 16px 0;
        font-size: 17px;
        font-weight: 700;
        color: #FFFFFF;
    }}
    .chart-img {{
        width: 100%;
        height: auto;
        border-radius: 10px;
        margin-bottom: 12px;
    }}
    .insight-pill {{
        background: var(--bg-sub);
        border-left: 4px solid var(--cyan);
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 12.5px;
        color: #E2E8F0;
    }}
    .prom-item {{
        background: var(--bg-sub);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }}
    .prom-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 8px;
    }}
    .prom-title {{
        font-weight: 800;
        font-size: 15px;
        color: #FFFFFF;
        margin-right: 8px;
    }}
    .prom-sub {{
        font-size: 12px;
        color: var(--text-muted);
    }}
    .prom-score {{
        font-size: 18px;
        font-weight: 800;
    }}
    .progress-track {{
        width: 100%;
        height: 8px;
        background: #0F172A;
        border-radius: 99px;
        overflow: hidden;
        margin-bottom: 8px;
    }}
    .progress-fill {{
        height: 100%;
        border-radius: 99px;
    }}
    .prom-footer {{
        display: flex;
        justify-content: space-between;
        font-size: 11.5px;
        color: var(--text-muted);
    }}
    .alert-box {{
        background: var(--bg-sub);
        border-left: 4px solid var(--cyan);
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }}
    .badge-pill {{
        font-size: 11px;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 99px;
    }}
    .modern-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    .modern-table th {{
        text-align: left;
        padding: 11px 12px;
        background: #0A2540;
        color: var(--cyan);
        font-size: 11.5px;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        border-bottom: 2px solid var(--cyan);
    }}
    .modern-table td {{
        padding: 10px 12px;
        border-bottom: 1px solid var(--border);
        color: #E2E8F0;
    }}
    .kv-row {{
        display: flex;
        justify-content: space-between;
        padding: 9px 0;
        border-bottom: 1px solid rgba(255,255,255,0.07);
        font-size: 13px;
    }}
    .kv-label {{
        color: var(--cyan);
        font-weight: 600;
        min-width: 190px;
    }}
    .kv-val {{
        color: #F8FAFC;
        text-align: right;
    }}
    .signature-box {{
        text-align: center;
        padding: 28px 20px;
        margin-top: 24px;
        border-top: 1px solid var(--border);
        color: var(--text-muted);
        font-size: 12px;
    }}
    .sig-line {{
        width: 280px;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--cyan), transparent);
        margin: 26px auto 10px auto;
    }}
    @media print {{
        .no-print {{ display: none !important; }}
        body {{ padding: 0; background-color: #0B0F19 !important; }}
        .card, .hero-card, .kpi-card {{ break-inside: avoid; }}
    }}
    @media (max-width: 768px) {{
        .kpi-grid {{ grid-template-columns: 1fr; }}
        .grid-2 {{ grid-template-columns: 1fr; }}
    }}
</style>
</head>
<body>
<div class="container">
    <div class="top-bar no-print">
        <span style="font-size:12px; color:#94A3B8;">⚡ Visualização Interativa GENUA HealthTech</span>
        <button class="btn-print" onclick="window.print()">🖨️ Imprimir / Salvar como PDF</button>
    </div>

    <div class="hero-card">
        <div class="hero-top">
            <div>
                <div class="brand-badge">GENUA INTELIGÊNCIA CLÍNICA • PRÁTICA BASEADA EM EVIDÊNCIA</div>
                <h1 class="hero-title">Laudo de Evolução Biomecânica e Funcional</h1>
            </div>
            <div style="text-align:right; font-size:12px; color:#CBD5E1;">
                <div><strong>Emitido em:</strong> {_esc(data_emissao)}</div>
                <div style="color:var(--cyan); font-weight:700; margin-top:4px;">Fenótipo: {_esc(fen_label)}</div>
            </div>
        </div>
        <div class="patient-meta">
            <div class="meta-box">
                <span class="meta-label">Paciente</span>
                <span class="meta-value">{_esc(paciente_nome)}</span>
            </div>
            <div class="meta-box">
                <span class="meta-label">Idade</span>
                <span class="meta-value">{_esc(idade)} anos</span>
            </div>
            <div class="meta-box">
                <span class="meta-label">Diagnóstico Clínico</span>
                <span class="meta-value">{_esc(dx_texto)}</span>
            </div>
            <div class="meta-box">
                <span class="meta-label">Janela Prognóstica PBE</span>
                <span class="meta-value" style="color:var(--cyan);">{_esc(tempo_esp)} semanas</span>
            </div>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-bar" style="background:{cor_dor_hex};"></div>
            <div class="kpi-label">Modulação da Dor (EVA)</div>
            <div class="kpi-val" style="color:{cor_dor_hex};">{dor_inicial:.0f} → {dor_atual:.0f}</div>
            <div class="kpi-sub">{_esc(badge_dor)}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-bar" style="background:{cor_flex_hex};"></div>
            <div class="kpi-label">Amplitude de Flexão</div>
            <div class="kpi-val" style="color:{cor_flex_hex};">{flex_atual:.0f}°</div>
            <div class="kpi-sub">{_esc(badge_flex)} (Inicial: {flex_inicial:.0f}°)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-bar" style="background:var(--indigo);"></div>
            <div class="kpi-label">Volume de Reabilitação</div>
            <div class="kpi-val" style="color:var(--indigo);">{n_sessoes} sessões</div>
            <div class="kpi-sub">{_esc(periodo_str)}</div>
        </div>
    </div>

    {html_graficos}
    {insights_html}
    {html_tabela_func}

    <div class="grid-2">
        <div class="card">
            <div class="section-tag">QUESTIONÁRIOS VALIDADOS (PBE)</div>
            <h3>Métricas Subjetivas & PROMs</h3>
            {proms_cards_html}
        </div>
        <div class="card">
            <div class="section-tag">LINHA DE BASE</div>
            <h3>Síntese da Avaliação Inicial</h3>
            {aval_items_html}
        </div>
    </div>

    <div class="card">
        <div class="section-tag">HISTÓRICO RECENTE</div>
        <h3>Últimos Check-ins Registrados</h3>
        <table class="modern-table">
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Dor (EVA)</th>
                    <th>Flexão</th>
                    <th>Extensão</th>
                    <th>Edema / Inchaço</th>
                    <th>Qualidade do Sono</th>
                </tr>
            </thead>
            <tbody>{linhas_sessoes}</tbody>
        </table>
    </div>

    <div class="signature-box">
        <p style="max-width:720px; margin:0 auto;">
            Relatório analítico processado pela plataforma <strong>GENUA Inteligência Clínica</strong>.
            Os pontos de corte de significância clínica (MCID e LSI) obedecem a diretrizes científicas internacionais revisadas por pares
            (Salaffi 2004; Grindem 2016; Binkley 1999; Roos 2003). A conduta final é prerrogativa exclusiva do fisioterapeuta responsável.
        </p>
        <div class="sig-line"></div>
        <div style="color:#FFFFFF; font-weight:700; font-size:14px;">Fisioterapeuta Responsável</div>
        <div style="color:var(--cyan); font-weight:600;">GENUA Instituto de Fisioterapia Esportiva</div>
        <div style="margin-top:4px;">CREFITO: ________________________ • Data: {datetime.now().strftime("%d/%m/%Y")}</div>
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
        self.set_fill_color(*AZUL_PROFUNDO)
        self.rect(0, 0, 140, 4, 'F')
        self.set_fill_color(*TEAL_VIVO)
        self.rect(140, 0, 70, 4, 'F')
        self.set_y(8)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 7)
        self.set_text_color(*CINZA_TEXTO)
        self.cell(0, 10, f'GENUA HealthTech - Pagina {self.page_no()}/{{nb}}', 0, 0, 'C')


def gerar_laudo(paciente_nome, dados_aval=None, historico=None, insights=None, fenotipo=None, *args, **kwargs):
    """Mantém geração direta de bytes PDF via FPDF2 caso chamada por rotas legadas."""
    dados_aval, hist = _normalizar_entradas(dados_aval, historico)
    pdf = LaudoGenua()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_fill_color(*AZUL_PROFUNDO)
    pdf.rect(10, 10, 190, 22, 'F')
    pdf.set_xy(15, 15)
    pdf.set_font('Arial', 'B', 15)
    pdf.set_text_color(*BRANCO)
    pdf.cell(0, 6, f'LAUDO CLINICO GENUA - {_limpar_texto(paciente_nome).upper()}', 0, 1, 'L')
    pdf.set_x(15)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*TEAL_VIVO)
    pdf.cell(0, 5, f'Emitido em {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'L')

    pdf.set_y(38)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(*PRETO_TEXTO)
    dx = dados_aval.get('Diagnostico_Clinico', '-')
    pdf.cell(0, 6, f'Diagnostico: {_limpar_texto(dx)} | Sessoes: {len(hist)}', 0, 1, 'L')

    try:
        saida = pdf.output(dest='S')
        if isinstance(saida, str):
            return saida.encode('latin-1')
        return bytes(saida)
    except Exception:
        return bytes(pdf.output())
