"""GENUA | Módulo 3: Painel Analítico (Cérebro Clínico — Joelho).

Performance: matplotlib, FPDF e PIL ficam em lazy import dentro de render(),
para não pesar o startup do app quando o usuário ainda não abriu o painel.
"""
import io
import base64
import urllib.parse
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from config import CORES_GENUA, titulo
from firebase_client import conn, db, invalidar_cache
from ia_clinica import analisar_paciente, renderizar_insights

def render():
    # Lazy imports — só carregam quando o painel é realmente aberto
    import matplotlib.pyplot as plt
    from fpdf import FPDF
    from PIL import Image

    p_sel = st.session_state.paciente

    # --- A. RESGATE DO CADASTRO ---
    try:
        df_cad = conn.read(worksheet="Cadastro", ttl=0)
        registro_p = df_cad[df_cad['Nome'].str.strip() == p_sel].iloc[-1]
        hist_clinica = registro_p.get('Diagnostico_Clinico', registro_p.get('Historia', 'Sem HMA base'))
        idade_p = int(float(registro_p.get('Idade', 0))) if pd.notna(registro_p.get('Idade')) else "N/A"
        dx_clinico_base = registro_p.get('Diagnostico_Clinico', 'Não especificado')
    except:
        hist_clinica = "Não disponível."; idade_p = "-"; dx_clinico_base = "-"

    # --- B. RESGATE DA AVALIAÇÃO BASE (TESTES E FLAGS) ---
    try:
        df_av = conn.read(worksheet="Avaliacao_Inicial", ttl=0)
        av_p = df_av[df_av['Paciente'].str.strip() == p_sel].iloc[-1]
        av_data = av_p.get('Data_Avaliacao', 'N/A')
        av_qp = av_p.get('QP', 'Não registrada')
        av_classdor = av_p.get('Class_Dor', 'Não avaliada')
        av_red = av_p.get('Red_Flags', 'Nenhuma')
        av_derrame = av_p.get('Derrame', 'Não avaliado')
        av_tlig = av_p.get('Testes_Ligamentares', '')
        av_tmen = av_p.get('Testes_Meniscais', '')
        tem_av = True
    except:
        tem_av = False

    st.header(f"📊 Painel Analítico: Joelho")

    # 1. HEADER DO PACIENTE
    st.markdown(f"""
        <div style='background-color: #ffffff; border: 1px solid #e9ecef; border-left: 5px solid {CORES_GENUA['primaria']}; padding: 20px; border-radius: 8px; margin-bottom: 15px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                <h3 style='margin: 0; color: {CORES_GENUA['primaria']}; font-weight: 700;'>👤 {p_sel}</h3>
                <span style='background-color: #f1f3f5; color: {CORES_GENUA['primaria']}; padding: 6px 15px; border-radius: 20px; font-weight: 600;'>{idade_p} anos</span>
            </div>
            <p style='margin: 0; color: #495057;'><strong>Dx Triagem:</strong> {dx_clinico_base}</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. CARD DE AVALIAÇÃO FÍSICA
    if tem_av:
        with st.expander(f"📋 Consultar Ficha de Avaliação Base (Data: {av_data})", expanded=False):
        
            # Criando abas internas para organizar a informação sem alongar a tela
            t_resumo, t_fisico, t_funcional, t_proms = st.tabs(["🗣️ Resumo", "📐 Físico", "💪 Funcional", "📊 Scores (PROMs)"])

            with t_resumo:
                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    st.markdown("**Anamnese e Dor:**")
                    st.markdown(f"- **QP:** {av_qp}")
                    st.markdown(f"- **Origem:** {av_p.get('Origem_Dor', 'N/A')}")
                    st.markdown(f"- **Tipo de Dor:** {av_classdor}")
                    st.markdown(f"- **Red Flags:** {av_red}")
                with c_r2:
                    st.markdown("**Exames de Imagem:**")
                    st.markdown(f"- **Apresentados:** {av_p.get('Exames_Apresentados', 'Nenhum')}")
                    st.markdown(f"- **Laudo Principal:** {av_p.get('Laudo_Exames', 'Não relatado')}")

            with t_fisico:
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    st.markdown("**Inspeção:**")
                    st.markdown(f"- **Derrame Articular:** {av_derrame}")
                    st.markdown(f"- **Alinhamento:** {av_p.get('Alinhamento', 'N/A')}")
                    st.markdown(f"- **Marcha:** {av_p.get('Marcha', 'N/A')}")
                with c_f2:
                    st.markdown("**Testes Especiais:**")
                    st.markdown(f"- **Ligamentares:** {av_tlig if av_tlig and av_tlig != 'Nenhum' else 'Nenhum achado'}")
                    st.markdown(f"- **Meniscais:** {av_tmen if av_tmen and av_tmen != 'Nenhum' else 'Nenhum achado'}")
                    st.markdown(f"- **Femoropatelar:** {av_p.get('Testes_Femoropatelar', 'Não testado')}")

            with t_funcional:
                st.markdown("**Força e Mobilidade:**")
                c_fun1, c_fun2 = st.columns(2)
                with c_fun1:
                    st.caption("Dinamometria")
                    st.markdown(f"- **Direita:** {av_p.get('Dinamometria_Dir', 'N/A')}")
                    st.markdown(f"- **Esquerda:** {av_p.get('Dinamometria_Esq', 'N/A')}")
                with c_fun2:
                    st.caption("Mobilidade (Lunge Test)")
                    st.markdown(f"- **Dir / Esq:** {av_p.get('Lunge_Test', 'N/A')}")

            with t_proms:
                st.markdown("**Questionários de Desfecho (Baseline):**")
                c_p1, c_p2, c_p3, c_p4 = st.columns(4)
            
                # Usa st.metric para um visual de "Dashboard" moderno
                c_p1.metric("LEFS", f"{av_p.get('LEFS_Pct', 0):.1f}%")
                c_p2.metric("Lysholm", f"{av_p.get('Lysholm_Pts', 0)} pts")
                c_p3.metric("VISA-P", f"{av_p.get('VISA_P_Pts', 0)} pts")
                c_p4.metric("WOMAC", f"{av_p.get('WOMAC_Pct', 0):.1f}%")
    else:
        st.info("⚠️ Nenhuma Avaliação Inicial rica registrada no sistema para este paciente.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- C. MOTOR DE EVOLUÇÃO (CHECK-INS) ---
    df = conn.read(worksheet="Evolucao", ttl=0).dropna(how="all")
    if df.empty or 'Paciente' not in df.columns:
        st.warning("⚠️ O paciente ainda não possui sessões de Check-in diário registradas.")
        st.stop()

    df['Membro'] = df.get('Membro', "Joelho").fillna("Joelho")
    df_p = df[(df['Paciente'] == p_sel) & (df['Membro'] == "Joelho")].copy()

    if df_p.empty:
        st.warning("⚠️ O paciente ainda não possui sessões de Check-in diário registradas.")
        st.stop()

    df_p['Data_dt'] = pd.to_datetime(df_p['Data'], dayfirst=True)
    df_p = df_p.sort_values('Data_dt')
    # --- 1. PROCESSAMENTO LONGITUDINAL (PREPARAÇÃO PARA GRÁFICOS) ---
    df_p['Sessão_Num'] = [f"S{i+1} ({d.strftime('%d/%m')})" for i, d in enumerate(df_p['Data_dt'])]

    if 'Dor' not in df_p.columns: df_p['Dor'] = 0
    df_p['Dor'] = pd.to_numeric(df_p['Dor'], errors='coerce').fillna(0)

    col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
    if col_inc not in df_p.columns: df_p[col_inc] = 0
    df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)

    for col, default in [('Flexao', 90), ('Extensao', 'Sem dados'), ('Agachamento', 'Sem Dor'), ('Step_Up', 'Sem Dor'), ('Step_Down', 'Sem Dor')]:
        if col not in df_p.columns: df_p[col] = default

    # Função PBE: Calcula a Função Geral (LSI) para TODAS as sessões do histórico
    def calcular_lsi(row):
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        pts = (mapa.get(row.get('Agachamento', 'Sem Dor'), 10) +
               mapa.get(row.get('Step_Up', 'Sem Dor'), 10) +
               mapa.get(row.get('Step_Down', 'Sem Dor'), 10)) / 30.0
        return min(max(float(pts * 100), 0.0), 100.0)
    
    df_p['LSI'] = df_p.apply(calcular_lsi, axis=1)

    # Seleção da Sessão Atual
    c_vazio, c_seletor = st.columns([4, 1])
    with c_seletor:
        sessao_escolhida = st.selectbox("📅 Analisar Sessão:", options=df_p['Sessão_Num'].tolist()[::-1], index=0)
    ultima = df_p[df_p['Sessão_Num'] == sessao_escolhida].iloc[0]

    # --- 2. O CÉREBRO CLÍNICO BAYESIANO ---
    dor_atual = int(ultima.get('Dor', 0))
    inchaco_atual = int(ultima.get('Inchaco_N', 0))
    sono_atual = ultima.get('Sono', 'Regular')
    lsi_atual = ultima['LSI']
    media_dor = df_p['Dor'].mean()

    # Árvore de Decisão PBE
    if ultima.get('Agachamento') == 'Incapaz' and inchaco_atual >= 2 and dor_atual >= 8:
        fenotipo = "🚨 Risco Estrutural (Sinal de Alerta)"
        diretriz = "Incapacidade de descarga de peso + Edema Agudo. Indicação de imagem e restrição de carga."
    elif ultima.get('Step_Down') in ['Incapaz', 'Dor Moderada'] and inchaco_atual <= 1:
        fenotipo = "🟣 Provável Síndrome Femoropatelar"
        diretriz = "Dor na desaceleração excêntrica. O foco é fortalecimento póstero-lateral do quadril e isometria (0-45°)."
    elif ultima.get('Extensao') in ['Déficit Grave (>-15°)', 'Déficit Leve (-5°)'] and inchaco_atual >= 2:
        fenotipo = "🟤 Bloqueio Articular / Derangement"
        diretriz = "Déficit de extensão terminal associado a derrame. Possível bloqueio meniscal. Priorizar mobilidade acessória."
    elif ultima.get('Agachamento') in ['Incapaz', 'Dor Moderada'] and ultima.get('Extensao') == 'Completa (0°)' and inchaco_atual == 0:
        fenotipo = "🟠 Perfil Tendinopático"
        diretriz = "Dor em armazenamento/liberação elástica (Pliometria). Aplicação de isometria pesada para efeito analgésico."
    elif dor_atual <= 3 and inchaco_atual <= 1 and lsi_atual >= 80:
        fenotipo = "🟢 Fase de Remodelamento"
        diretriz = "Alta tolerância mecânica. Progressão segura para exercícios de mudança de direção e retorno ao esporte."
    else:
        fenotipo = "🔵 Acomodação de Carga"
        diretriz = "Sinais inflamatórios mistos. Modular volume e intensidade conforme o sintoma limitante."

    status_clinico = "Excelente" if lsi_atual >= 85 else "Regular" if lsi_atual >= 60 else "Atenção"

    # --- 3. DASHBOARD DE MÉTRICAS VISUAIS ---
    m1, m2, m3, m4 = st.columns(4)
    delta_pct = ((dor_atual - media_dor) / media_dor * 100) if media_dor > 0 else 0
    m1.metric("Dor Atual (vs Média)", f"{dor_atual}/10", f"{delta_pct:.0f}%", delta_color="inverse")
    m2.metric("Inchaço", f"Grau {inchaco_atual}")
    m3.metric("Prontidão (LSI)", f"{lsi_atual:.0f}%", status_clinico)
    m4.metric("Diagnóstico IA", fenotipo.split()[1])
    st.write("---")

    st.markdown(f"**Progresso Base para Alta: {lsi_atual:.0f}%**")
    st.progress(lsi_atual / 100)

    # --- 4. ABAS GRÁFICAS DE ALTA PERFORMANCE (MATPLOTLIB) ---
    t1, t2, t_ic = st.tabs(["📊 Correlação Dor x Função", "📉 Evolução Biomecânica", "🧠 Inteligência Clínica"])

    with t1:
        # ============================================================
        # GRÁFICO 1: DOR × FUNÇÃO (Linhas Cruzadas — o que Edgar pediu)
        # Se a dor cai e a função melhora, as linhas se cruzam = sucesso terapêutico
        # ============================================================
        st.markdown("**📊 Correlação Dor × Função ao Longo do Tratamento**")
        st.caption("Se as linhas se cruzam (dor caindo, função subindo), o tratamento está funcionando.")

        # Converte Testes_Funcionais para score numérico (0-10)
        mapa_func_score = {
            "Sem Dor (0)": 10, "Sem Dor": 10,
            "Dor Leve (1 - 3)": 7, "Dor Leve": 7,
            "Dor Moderada (4 - 7)": 4, "Dor Moderada": 4,
            "Dor Grave (8 - 10)": 1, "Dor Grave": 1,
            "Incapaz (Não realiza)": 0, "Incapaz": 0, "Não testado": None
        }

        # Extrai score funcional por sessão (média dos testes registrados)
        func_scores = []
        testes_nomes = set()
        for _, row in df_p.iterrows():
            testes = row.get('Testes_Funcionais', {})
            if isinstance(testes, dict) and testes:
                scores_sessao = []
                for teste_nome, resultado in testes.items():
                    testes_nomes.add(teste_nome)
                    score = mapa_func_score.get(resultado)
                    if score is not None:
                        scores_sessao.append(score)
                func_scores.append(sum(scores_sessao) / len(scores_sessao) if scores_sessao else None)
            else:
                func_scores.append(None)

        df_p['Func_Score'] = func_scores

        fig1, ax1 = plt.subplots(figsize=(10, 4.5))

        # Linha de Dor (vermelha, caindo = bom)
        ax1.plot(df_p['Sessão_Num'], df_p['Dor'], color=CORES_GENUA['alerta_erro'],
                 marker='o', lw=2.5, label="Dor (EVA)", zorder=3)
        ax1.fill_between(range(len(df_p)), df_p['Dor'], alpha=0.08, color=CORES_GENUA['alerta_erro'])
        ax1.set_ylabel("Dor (EVA 0-10)", color=CORES_GENUA['alerta_erro'], fontweight='bold')
        ax1.set_ylim(-0.5, 10.5)

        # Linha de Função (verde/teal, subindo = bom) — eixo secundário
        ax1b = ax1.twinx()
        func_plot = df_p['Func_Score'].interpolate() if df_p['Func_Score'].notna().sum() > 1 else df_p['Func_Score']
        ax1b.plot(df_p['Sessão_Num'], func_plot, color='#28a745',
                  marker='s', lw=2.5, linestyle='--', label="Função (média testes)", zorder=3)
        ax1b.fill_between(range(len(df_p)), func_plot.fillna(0), alpha=0.08, color='#28a745')
        ax1b.set_ylabel("Função (0-10)", color='#28a745', fontweight='bold')
        ax1b.set_ylim(-0.5, 10.5)

        ax1.spines['top'].set_visible(False)
        ax1b.spines['top'].set_visible(False)
        plt.setp(ax1.get_xticklabels(), rotation=35, ha='right', fontsize=9)

        # Legenda combinada
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1b.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center', ncol=2, framealpha=0.9, fontsize=9)

        fig1.tight_layout()
        st.pyplot(fig1)

        # Mini-tabela: evolução por teste funcional individual
        if testes_nomes:
            st.markdown("---")
            st.markdown("**Detalhamento por Teste Funcional**")
            for teste_nome in sorted(testes_nomes):
                valores_teste = []
                for _, row in df_p.iterrows():
                    testes = row.get('Testes_Funcionais', {})
                    if isinstance(testes, dict):
                        valores_teste.append(testes.get(teste_nome, "—"))
                    else:
                        valores_teste.append("—")
                primeira = valores_teste[0] if valores_teste else "—"
                ultima_val = valores_teste[-1] if valores_teste else "—"
                st.caption(f"**{teste_nome}:** {primeira} → {ultima_val}")

        # Scatter Dor vs LSI (mantém o original)
        st.markdown("---")
        st.markdown("**Dispersão: Tolerância ao Movimento (Dor × Prontidão)**")
        fig1b, ax1c = plt.subplots(figsize=(10, 3.5))
        ax1c.scatter(df_p['Dor'], df_p['LSI'], color=CORES_GENUA['secundaria'], s=100, alpha=0.8, edgecolors='white')
        if len(df_p) > 2:
            z = np.polyfit(df_p['Dor'], df_p['LSI'], 1)
            p = np.poly1d(z)
            ax1c.plot(df_p['Dor'], p(df_p['Dor']), color=CORES_GENUA['primaria'], linestyle='--', lw=1)
        ax1c.set_xlabel("Dor (EVA 0-10)"); ax1c.set_ylabel("Prontidão (LSI %)")
        ax1c.set_xlim(-0.5, 10.5); ax1c.set_ylim(-5, 105)
        ax1c.spines['top'].set_visible(False); ax1c.spines['right'].set_visible(False)
        fig1b.tight_layout()
        st.pyplot(fig1b)

    with t2:
        # ============================================================
        # GRÁFICO 2: EVOLUÇÃO CONTEXTUAL (adapta ao diagnóstico)
        # Se o fenótipo for tendinopatia, não mostra Flexão.
        # Se for Pós-LCA, mostra Flexão + Extensão.
        # ============================================================
        st.markdown("**📉 Evolução Longitudinal (Contextual ao Diagnóstico)**")

        # Detecta fenótipo via ia_clinica
        try:
            from ia_clinica import normalizar_diagnostico
            fen = normalizar_diagnostico(dx_clinico_base)
            metricas = fen.get("metricas_relevantes", ["Dor", "Flexao"])
            st.caption(f"🎯 Fenótipo: **{fen['label']}** — Métricas priorizadas: {', '.join(metricas)}")
        except Exception:
            metricas = ["Dor", "Flexao"]

        fig2, ax2 = plt.subplots(figsize=(10, 4.5))

        # Sempre mostra Dor
        ax2.plot(df_p['Sessão_Num'], df_p['Dor'], color=CORES_GENUA['alerta_erro'],
                 marker='o', lw=2.5, label="Dor (EVA)")
        ax2.set_ylabel("Dor (EVA 0-10)", color=CORES_GENUA['alerta_erro'], fontweight='bold')
        ax2.set_ylim(-0.5, 10.5)

        # Eixo secundário: adapta ao fenótipo
        ax3 = ax2.twinx()

        if "Flexao" in metricas:
            ax3.plot(df_p['Sessão_Num'], df_p['Flexao'], color=CORES_GENUA['secundaria'],
                     marker='s', lw=2, linestyle=':', label="Flexão (°)")
            ax3.set_ylabel("Flexão (°)", color=CORES_GENUA['secundaria'], fontweight='bold')
            ax3.set_ylim(0, 160)
        elif "Carga_Excentrica" in metricas or "Testes_Funcionais" in metricas:
            # Para tendinopatias e condromalácia: mostra score funcional
            if 'Func_Score' in df_p.columns:
                func_data = df_p['Func_Score'].interpolate() if df_p['Func_Score'].notna().sum() > 1 else df_p['Func_Score']
                ax3.plot(df_p['Sessão_Num'], func_data, color='#28a745',
                         marker='s', lw=2, linestyle=':', label="Função (Score)")
                ax3.set_ylabel("Função (0-10)", color='#28a745', fontweight='bold')
                ax3.set_ylim(-0.5, 10.5)
        else:
            # Default: mostra Flexão
            ax3.plot(df_p['Sessão_Num'], df_p['Flexao'], color=CORES_GENUA['secundaria'],
                     marker='s', lw=2, linestyle=':', label="Flexão (°)")
            ax3.set_ylabel("Flexão (°)", color=CORES_GENUA['secundaria'], fontweight='bold')
            ax3.set_ylim(0, 160)

        ax2.spines['top'].set_visible(False)
        ax3.spines['top'].set_visible(False)
        plt.setp(ax2.get_xticklabels(), rotation=35, ha='right', fontsize=9)

        # Legenda combinada
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax3.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right', framealpha=0.9, fontsize=9)

        fig2.tight_layout()
        st.pyplot(fig2)

    with t_ic:
        # ============================================================
        # 🧠 INTELIGÊNCIA CLÍNICA — Central única de insights
        # Combina 3 camadas complementares:
        #   1) Análise Automatizada (motor Fase 2, baseado em evidência)
        #   2) Raciocínio Clínico (interpretação da IA sobre fenótipo/conduta)
        #   3) Gatilhos Bio-Psico-Sociais (sono, sensibilização central)
        # ============================================================

        # ---------- CAMADA 1: Motor de IA baseado em evidência ----------
        try:
            with st.spinner("🧠 Executando análise clínica baseada em evidência..."):
                insights = analisar_paciente(st.session_state.paciente)
            renderizar_insights(insights, CORES_GENUA)
        except Exception as e:
            st.error(f"❌ Erro ao gerar insights: {e}")
            st.caption("Verifique se o paciente possui avaliação inicial e sessões de check-in registradas.")

        st.markdown("---")

        # ---------- CAMADA 2: Raciocínio Clínico narrativo ----------
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>🔬 Raciocínio Clínico do Algoritmo</h4>", unsafe_allow_html=True)
        st.info("A Inteligência Artificial cruza inchaço, dor em padrões de carga elástica/excêntrica e déficits articulares. **O diagnóstico final pertence ao Fisioterapeuta.**")
        st.markdown(f"**🔬 Análise do Algoritmo:** {fenotipo}")
        st.markdown(f"**💡 Conduta Baseada em Evidência:** {diretriz}")

        col_b1, col_b2 = st.columns(2)
        col_b1.metric("Amplitude de Flexão", f"{ultima.get('Flexao', 90)}°")
        col_b2.info(f"Extensão Terminal Atual: {ultima.get('Extensao', 'Sem dados')}")

        st.markdown("---")

        # ---------- CAMADA 3: Gatilhos Bio-Psico-Sociais ----------
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>🎯 Gatilhos Bio-Psico-Sociais</h4>", unsafe_allow_html=True)
        st.success(f"💡 **Variável Bio-Psico-Social (Sono):** Paciente apresentou padrão predominante '{sono_atual}' na avaliação.")
        st.caption("O sistema rastreia oscilações de dor que não respondem à carga mecânica para deduzir possível Sensibilização Central baseada no sono.")

    # --- MÓDULO DE EXPORTAÇÃO COMPLEXO (LAUDO MÉDICO + MATRIZ DE GRÁFICOS) ---
    st.markdown("---")
    titulo("📄 Exportação de Laudo Clínico Avançado")
    st.caption("Gera um relatório oficial em formato PDF contendo os dados da Avaliação Inicial, Scores PBE e os gráficos reais de evolução clínica.")

    if st.button("⚙️ GERAR RELATÓRIO COM GRÁFICOS", width='stretch'):
        with st.spinner("Buscando dados na nuvem e renderizando gráficos no laudo..."):
            try:
                # 1. Busca Segura dos Dados no Firebase Firestore
                docs_aval = db.collection("Avaliacao_Inicial").where("Paciente", "==", st.session_state.paciente).stream()
                lista_aval = [doc.to_dict() for doc in docs_aval]
                dados_aval = lista_aval[-1] if lista_aval else {}
            
                docs_evo = db.collection("Evolucao").where("Paciente", "==", st.session_state.paciente).stream()
                historico = [doc.to_dict() for doc in docs_evo]
            
                # 2. Inicialização do Documento PDF
                pdf = FPDF()
                pdf.add_page()
            
                # Cabeçalho Institucional
                pdf.set_font('Arial', 'B', 16)
                pdf.set_text_color(16, 62, 85) # Azul Genua
                pdf.cell(0, 10, 'GENUA - Inteligencia Clinica Integrada', 0, 1, 'C')
                pdf.set_font('Arial', 'I', 10)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, 'Laudo de Evolucao Funcional e Biomecanica', 0, 1, 'C')
                pdf.ln(10)
            
                # Identificação Clínica do Paciente
                pdf.set_font('Arial', 'B', 12)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 8, f"Paciente: {st.session_state.paciente}", 0, 1)
                pdf.set_font('Arial', '', 10)
                pdf.cell(0, 6, f"Membro Alvo: {st.session_state.get('membro_ativo', 'Joelho')}", 0, 1)
                pdf.cell(0, 6, f"Data de Emissao: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
                pdf.ln(5)
            
                # 3. Bloco da Avaliação Inicial e Scores Funcionais
                if dados_aval:
                    pdf.set_font('Arial', 'B', 11)
                    pdf.set_fill_color(240, 240, 240)
                    pdf.cell(0, 8, ' MARCOS DA AVALIACAO INICIAL', 0, 1, fill=True)
                    pdf.set_font('Arial', '', 10)
                
                    qp_texto = str(dados_aval.get("QP", "N/A")).encode('ascii', 'ignore').decode('ascii')
                    pdf.multi_cell(0, 6, f"Queixa Principal: {qp_texto}")
                
                    pdf.ln(2)
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, 'Métricas Baseadas em Evidência (PROMs):', 0, 1)
                    pdf.set_font('Arial', '', 10)
                
                    if float(dados_aval.get('LEFS_Pct', 0)) > 0:
                        pdf.cell(0, 6, f"- LEFS (Funcionalidade Geral): {float(dados_aval.get('LEFS_Pct', 0)):.1f}% ({dados_aval.get('Interpretacao_LEFS', '')})", 0, 1)
                    if float(dados_aval.get('WOMAC_Pct', 0)) > 0:
                        pdf.cell(0, 6, f"- WOMAC (Osteoartrite): {float(dados_aval.get('WOMAC_Pct', 0)):.1f}%", 0, 1)
                    if float(dados_aval.get('VISA_P_Pts', 0)) > 0:
                        pdf.cell(0, 6, f"- VISA-P (Tendinopatia Patelar): {float(dados_aval.get('VISA_P_Pts', 0))} pts", 0, 1)
                    if float(dados_aval.get('Lysholm_Pts', 0)) > 0:
                        pdf.cell(0, 6, f"- Lysholm (Lesao de Menisco/Ligamento): {float(dados_aval.get('Lysholm_Pts', 0))} pts", 0, 1)
                    if float(dados_aval.get('KOOS_Pct', 0)) > 0:
                        pdf.cell(0, 6, f"- KOOS (Score Agregado): {float(dados_aval.get('KOOS_Pct', 0)):.1f}%", 0, 1)
                    if float(dados_aval.get('IKDC_Pct', 0)) > 0:
                        pdf.cell(0, 6, f"- IKDC Subjetivo: {float(dados_aval.get('IKDC_Pct', 0)):.1f}%", 0, 1)
            
                # 4. Geração Dinâmica da Matriz Gráfica
                if historico:
                    # Ordena o histórico por data para os gráficos fazerem sentido cronológico
                    historico_ordenado = sorted(historico, key=lambda x: x.get('Data', ''))
                
                    datas = [ev.get('Data', 'N/A')[:5] for ev in historico_ordenado]
                    dores = [float(ev.get('Dor', 0)) for ev in historico_ordenado]
                    flexoes = [float(ev.get('Flexao', 0)) for ev in historico_ordenado]
                
                    # --- GRÁFICO 1: EVOLUÇÃO DA DOR (EVA) ---
                    pdf.ln(5)
                    pdf.set_font('Arial', 'B', 11)
                    pdf.cell(0, 8, ' CURVA DE EVOLUCAO DA DOR (EVA)', 0, 1, fill=True)
                
                    fig, ax = plt.subplots(figsize=(6.5, 2.2))
                    ax.plot(datas, dores, marker='o', color='#103E55', linewidth=2.5, label='Intensidade da Dor')
                    ax.set_ylabel('Escala EVA (0-10)', color='#1A252C')
                    ax.set_ylim(-0.5, 10.5)
                    ax.grid(True, linestyle='--', alpha=0.5)
                    plt.tight_layout()
                
                    img_buf_dor = io.BytesIO()
                    plt.savefig(img_buf_dor, format='png', dpi=200)
                    img_buf_dor.seek(0)
                    plt.close(fig)
                
                    # Desenha o gráfico de dor direto na página atual
                    pdf.image(img_buf_dor, w=180, h=60)
                
                    # --- GRÁFICO 2: AMPLITUDE DE MOVIMENTO (ADM FLEXÃO) ---
                    pdf.add_page() # Move os gráficos biomecânicos para a página 2
                    pdf.set_font('Arial', 'B', 11)
                    pdf.cell(0, 8, ' EVOLUCAO DA AMPLITUDE DE MOVIMENTO (FLEXAO)', 0, 1, fill=True)
                
                    fig2, ax2 = plt.subplots(figsize=(6.5, 2.2))
                    ax2.plot(datas, flexoes, marker='s', color='#398E9B', linewidth=2.5, label='Flexao Voluntaria')
                    ax2.set_ylabel('Graus ()', color='#1A252C')
                    ax2.grid(True, linestyle='--', alpha=0.5)
                    plt.tight_layout()
                
                    img_buf_flex = io.BytesIO()
                    plt.savefig(img_buf_flex, format='png', dpi=200)
                    img_buf_flex.seek(0)
                    plt.close(fig2)
                
                    # Desenha o gráfico de ADM na página 2
                    pdf.image(img_buf_flex, w=180, h=60)
                    pdf.ln(5)
                
                    # Tabela Textual de Apoio das últimas sessões
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, 'Historico Consolidado das Últimas Sessões:', 0, 1)
                    pdf.set_font('Arial', '', 9)
                    for ev in historico[-8:]:
                        linha = f"Data: {ev.get('Data', 'N/A')[:10]} | Dor: {ev.get('Dor', '-')} | Flexao: {ev.get('Flexao', '-')} | Carga Cles.: {ev.get('Agachamento', '-')}"
                        pdf.cell(0, 5, linha, 0, 1)
                else:
                    pdf.ln(5)
                    pdf.cell(0, 6, "Nenhum registro evolutivo encontrado para geracao de graficos.", 0, 1)
                
                # 5. Encerramento e Assinatura do Profissional
                pdf.ln(15)
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 6, '___________________________________________________', 0, 1, 'C')
                prof = st.session_state.get('user_email', 'Fisioterapeuta Responsavel')
                pdf.cell(0, 6, prof, 0, 1, 'C')

                # Empacotamento de Saída Estável
                try:
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                except:
                    pdf_bytes = bytes(pdf.output())
            
                st.download_button(
                    label="📥 BAIXAR LAUDO COMPLETO COM GRÁFICOS (PDF)",
                    data=pdf_bytes,
                    file_name=f"Laudo_Clinico_{st.session_state.paciente.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    width='stretch'
                )
                st.success("✅ Laudo clínico completo compilado! Clique no botão verde acima para baixar.")
            
            except Exception as e:
                st.error(f"❌ Erro crítico ao processar o laudo gráfico: {e}")
