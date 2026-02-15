import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import numpy as np
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt
import io

# --- 1. FUNÇÕES DE SUPORTE E PDF ---

def limpar_texto_pdf(txt):
    """Garante que o PDF aceite acentuação e caracteres especiais do PT-BR."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, metrics, imgs):
    pdf = FPDF()
    azul_genua = (0, 128, 145)
    cinza_txt = (80, 80, 80)
    
    # --- PARECERES CLÍNICOS DINÂMICOS ---
    if metrics['ikdc_status'] == 'Bom': 
        par_ikdc = "Parecer Clínico: Excelente evolução. O paciente apresenta alta percepção de funcionalidade, validando a eficácia da progressão de carga e a tolerância mecânica do joelho."
    elif metrics['ikdc_status'] == 'Regular': 
        par_ikdc = "Parecer Clínico: Evolução moderada. O paciente apresenta ganhos reais, mas ainda demanda atenção fisioterapêutica para déficits de força ou controle neuromuscular residual."
    else: 
        par_ikdc = "Parecer Clínico: Baixa funcionalidade percebida. Sugere-se reavaliar o volume de carga atual e focar intensamente na modulação de sintomas álgicos."
        
    if metrics['alta'] not in ["Em análise", "Estabilizado"]: 
        par_ev = f"Parecer Clínico: O cruzamento das curvas demonstra melhora significativa. A dor está controlada sob demanda funcional, com projeção matemática de alta para {metrics['alta']}."
    else: 
        par_ev = "Parecer Clínico: O gráfico mapeia a janela de tolerância do paciente. O foco atual é afastar a curva de função da curva de dor para garantir progressão segura."

    grau_inc = int(float(metrics['inchaco']))
    if grau_inc <= 1: 
        par_inc = "Parecer Clínico: Articulação estável e sem inchaço clinicamente relevante (Grau 0-1). Cenário totalmente seguro para aumento de intensidade no treinamento."
    elif grau_inc == 2: 
        par_inc = "Parecer Clínico: Presença de inchaço moderado (Alerta Amarelo). Recomendável estabilizar o volume de treino e monitorar a resposta articular nas próximas 48h."
    else: 
        par_inc = "Parecer Clínico: Derrame articular importante (Alerta Vermelho). É imperativo regredir a sobrecarga mecânica e priorizar recursos de drenagem e crioterapia."

    par_sono = "Parecer Clínico: A análise biopsicossocial destaca a influência da qualidade do sono na hiperalgesia. Noites reparadoras correlacionam-se com menor percepção de dor articular."

    # LÓGICA DE ESPAÇAMENTO COMPACTO
    def get_img_height(img_buffer, pdf_width):
        img_buffer.seek(0)
        with Image.open(img_buffer) as im:
            return pdf_width * (im.height / im.width)

    # ==========================================
    # --- PÁGINA 1: DADOS E EVOLUÇÃO ---
    # ==========================================
    pdf.add_page()
    try: 
        pdf.image("Ativo-1.png", x=10, y=8, w=30)
    except: 
        pdf.set_font("helvetica", 'B', 14)
        pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(15)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 8, limpar_texto_pdf("RELATÓRIO DE INTELIGÊNCIA CLÍNICA E EVOLUÇÃO"), ln=True, align='C')
    pdf.ln(3)

    # 1. Identificação
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 1. IDENTIFICAÇÃO E ANAMNESE"), ln=True, fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("helvetica", '', 9); pdf.ln(2)
    pdf.multi_cell(0, 5, limpar_texto_pdf(f"Paciente: {p_name.upper()}\nHistória Clínica: {hist}")); pdf.ln(3)

    # 2. IKDC
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 2. AVALIAÇÃO CIENTÍFICA IKDC (SUBJETIVA)"), ln=True, fill=True, align='C')
    
    pdf.ln(3)
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 12)
    pdf.set_x((pdf.w - 100) / 2) 
    score_val = int(float(metrics['ikdc']))
    pdf.cell(100, 10, limpar_texto_pdf(f"RESULTADO: {score_val}/100 - {metrics['ikdc_status'].upper()}"), ln=True, fill=True, align='C')
    
    pdf.ln(6) 
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_ikdc), align='C')
    pdf.ln(6)

    # 3. Evolução
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 3. EVOLUÇÃO CLÍNICA (FUNÇÃO VS. DOR)"), ln=True, fill=True, align='C')
    
    y_ev = pdf.get_y() + 4
    pdf.image(imgs['ev'], x=20, y=y_ev, w=170) 
    
    h_ev = get_img_height(imgs['ev'], 170)
    pdf.set_y(y_ev + h_ev + 2) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_ev), align='C')

    # ==========================================
    # --- PÁGINA 2: INCHAÇO E BIOPSICOSSOCIAL ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)

    # 4. Inchaço
    pdf.cell(0, 7, limpar_texto_pdf(" 4. MONITORAMENTO DE INCHAÇO ARTICULAR"), ln=True, fill=True, align='C')
    
    y_inc = pdf.get_y() + 4
    pdf.image(imgs['inchaco'], x=20, y=y_inc, w=170)
    
    h_inc = get_img_height(imgs['inchaco'], 170)
    pdf.set_y(y_inc + h_inc + 2) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_inc), align='C')

    # Salto matemático para separar o parecer do Inchaço do título do Sono
    pdf.ln(10)

    # 5. Sono vs Dor (Aglutinado na mesma página)
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 5. ANÁLISE BIOPSICOSSOCIAL (SONO VS. DOR)"), ln=True, fill=True, align='C')
    
    y_sono = pdf.get_y() + 4
    pdf.image(imgs['sono'], x=20, y=y_sono, w=170)

    h_sono = get_img_height(imgs['sono'], 170)
    pdf.set_y(y_sono + h_sono + 2) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_sono), align='C')

    return bytes(pdf.output())

# --- 2. INTERFACE E CONEXÃO ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide", page_icon="🏥")
conn = st.connection("gsheets", type=GSheetsConnection)

with st.sidebar:
    try: st.image("Ativo-1.png", width=220)
    except: st.header("GENUA")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação IKDC 📋", "Painel Analítico 📊"])

# --- 3. MÓDULOS DE NAVEGAÇÃO ---

if menu == "Check-in Diário 📝":
    st.header("Check-in Diário de Evolução")
    with st.form("checkin", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente")
        c1, c2 = st.columns(2)
        with c1:
            dor = st.select_slider("Dor atual (0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with c2:
            agac = st.selectbox("Agachamento", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sup = st.selectbox("Step Up", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sdn = st.selectbox("Step Down", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            inchaco = st.select_slider("Inchaço (Stroke Test)", options=["0", "1", "2", "3"])
        if st.form_submit_button("REGISTRAR SESSÃO"):
            df = conn.read(ttl=0).dropna(how="all")
            nova = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Inchaço": str(inchaco), "Sono": sono, "Postura": postura, "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn}])
            conn.update(data=pd.concat([df, nova], ignore_index=True))
            st.success("Dados registrados com sucesso!")

elif menu == "Avaliação IKDC 📋":
    st.header("Score Científico IKDC")
    with st.form("ikdc"):
        p_ikdc = st.text_input("Nome do Paciente")
        nota = st.slider("Nota Global de Função (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR SCORE"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("Score IKDC registrado!")

else: # PAINEL ANALÍTICO (O CÉREBRO CLÍNICO TOTAL)
    st.header("📊 Painel Analítico & Clinical Intelligence")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente para Análise", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # 1. PROCESSAMENTO DE DADOS E EIXO X (DE 5 EM 5 SESSÕES)
        df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]
        mapa_func = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Função'] = (df_p['Agachamento'].map(mapa_func) + df_p['Step_Up'].map(mapa_func) + df_p['Step_Down'].map(mapa_func)) / 3
        df_p['Sono_N'] = df_p['Sono'].map({"Ruim": 1, "Regular": 5, "Bom": 10})
        col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
        df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)
        ultima = df_p.iloc[-1]

        # Intervalos de 5 sessões para o Eixo X em todos os gráficos
        indices_5 = np.arange(0, len(df_p), 5)
        labels_5 = [df_p['Sessão_Num'].iloc[i] for i in indices_5]

        # CÁLCULO DE TENDÊNCIA E PREVISÃO DE ALTA
        try:
            df_p['Data_DT'] = pd.to_datetime(df_p['Data'], dayfirst=True)
            df_p['Dias'] = (df_p['Data_DT'] - df_p['Data_DT'].min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Função'].values, 1)
            trend_line = z[0] * df_p['Dias'].values + z[1]
            dia_estimado_alta = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            prev_txt = (df_p['Data_DT'].min() + pd.to_timedelta(dia_estimado_alta, unit='d')).strftime("%d/%m/%Y") if dia_estimado_alta > 0 else "Estabilizado"
        except: 
            trend_line = []
            prev_txt = "Em análise"

        # SCORE CIENTÍFICO IKDC
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = float(df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1])
            status_clinico = "Bom" if u_ikdc > 70 else "Regular" if u_ikdc > 45 else "Severo"
            emoji_ikdc = "🏆" if status_clinico == "Bom" else "🟢" if status_clinico == "Regular" else "🔴"
        except: 
            u_ikdc = 0; emoji_ikdc = "⚪"; status_clinico = "Pendente"

        # 2. GERAÇÃO DE GRÁFICOS (FIX ABSOLUTO DE LEGENDAS E VISIBILIDADE)
        
        # A) Evolução Clínica
        fig_ev, ax_ev = plt.subplots(figsize=(10, 5))
        ax_ev.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', label='Nível de Dor (EVA)', marker='o', linewidth=2)
        ax_ev.plot(df_p['Sessão_Num'], df_p['Score_Função'], color='#008091', label='Capacidade Funcional', marker='s', linewidth=3)
        if len(trend_line) > 0:
            ax_ev.plot(df_p['Sessão_Num'], trend_line, '--', color='#5D6D7E', alpha=0.5, label='Tendência de Alta')
        
        ax_ev.set_title("Evolução Clínica: Capacidade Funcional vs. Dor", fontweight='bold')
        ax_ev.set_ylim(-0.5, 11)
        ax_ev.set_xticks(indices_5)
        ax_ev.set_xticklabels(labels_5)
        
        lgd_ev = ax_ev.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
        buf_ev = io.BytesIO()
        fig_ev.savefig(buf_ev, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_ev,), dpi=150)
        buf_ev.seek(0); plt.close(fig_ev)

        # B) Inchaço Articular (Cores de Alerta e Legenda Customizada)
        fig_inc, ax_inc = plt.subplots(figsize=(10, 3.5))
        cores_inc = ['#D32F2F' if x == 3 else '#FFB300' if x == 2 else '#008091' for x in df_p['Inchaco_N']]
        
        # O 'label' foi retirado daqui, pois criaremos a legenda manualmente
        ax_inc.bar(df_p['Sessão_Num'], df_p['Inchaco_N'], color=cores_inc, alpha=0.8)
        
        ax_inc.set_title("Linha do Tempo: Inchaço Articular", fontweight='bold')
        ax_inc.set_ylim(0, 3.5)
        ax_inc.set_xticks(indices_5)
        ax_inc.set_xticklabels(labels_5)
        
        # Criação de Legenda Customizada com as Cores Exatas
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#D32F2F', alpha=0.8, label='Grau 3 (Alerta/Grave)'),
            Patch(facecolor='#FFB300', alpha=0.8, label='Grau 2 (Moderado)'),
            Patch(facecolor='#008091', alpha=0.8, label='Grau 0-1 (Estável)')
        ]
        
        # A legenda agora terá 3 colunas e mostrará as 3 cores
        lgd_inc = ax_inc.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=3, frameon=False, fontsize=9)
        
        buf_inc = io.BytesIO()
        fig_inc.savefig(buf_inc, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_inc,), dpi=150)
        buf_inc.seek(0); plt.close(fig_inc)

        # C) Sono vs Dor (O Gráfico de Capacidade foi removido daqui)
        fig_s, ax_s = plt.subplots(figsize=(10, 4))
        ax_s.fill_between(df_p['Sessão_Num'], df_p['Sono_N'], color='#008091', alpha=0.2, label='Qualidade do Sono')
        ax_s.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', marker='o', label='Nível de Dor')
        
        ax_s.set_title("Impacto Biopsicossocial: Sono vs Dor", fontweight='bold')
        ax_s.set_ylim(-0.5, 11)
        ax_s.set_xticks(indices_5)
        ax_s.set_xticklabels(labels_5)
        
        lgd_s = ax_s.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
        buf_s = io.BytesIO(); fig_s.savefig(buf_s, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_s,), dpi=150); buf_s.seek(0); plt.close(fig_s)

        # 3. MÉTRICAS E DASHBOARD COMPLETO
        media_dor = df_p['Dor'].mean()
        # Cálculo do delta em % (com proteção contra divisão por zero)
        delta_dor_pct = ((ultima['Dor'] - media_dor) / media_dor * 100) if media_dor > 0 else (100 if ultima['Dor'] > 0 else 0)
        
        media_inc = df_p['Inchaco_N'].mean()
        # Cálculo do delta em % (com proteção contra divisão por zero)
        delta_inc_pct = ((ultima['Inchaco_N'] - media_inc) / media_inc * 100) if media_inc > 0 else (100 if ultima['Inchaco_N'] > 0 else 0)

        m1, m2, m3, m4 = st.columns(4)
        # O delta_color="inverse" garante que % negativas (menos dor) fiquem verdes, e % positivas (mais dor) fiquem vermelhas
        m1.metric("Dor Atual (vs Média)", f"{ultima['Dor']}/10", f"{delta_dor_pct:.0f}%", delta_color="inverse", help=f"A média histórica deste paciente é {media_dor:.1f}/10")
        m2.metric("Inchaço (vs Média)", f"Grau {ultima[col_inc]}", f"{delta_inc_pct:.0f}%", delta_color="inverse", help=f"A média histórica de inchaço é Grau {media_inc:.1f}")
        m3.metric("IKDC", f"{int(u_ikdc)}/100", status_clinico)
        m4.metric("Previsão Alta", prev_txt)

        st.write("---")
        # Aba de Capacidade removida, mantendo Evolução, Inchaço e Biopsicossocial
        t1, t2, t3 = st.tabs(["📈 Evolução & IA", "🌊 Inchaço", "🎯 Biopsicossocial"])
        
        with t1: 
            st.image(buf_ev, use_container_width=True)
            st.success(f"🔮 **Inteligência GENUA:** A linha pontilhada indica a tendência de recuperação. Alta estimada: **{prev_txt}**.")
            
        with t2: 
            st.image(buf_inc, use_container_width=True)
            
        with t3: 
            st.image(buf_s, use_container_width=True)
            st.write("**Análise de Postura vs. Dor**")
            st.altair_chart(alt.Chart(df_p).mark_bar(color='#008091').encode(
                x=alt.X('Postura', title='Postura'),
                y=alt.Y('mean(Dor)', title='Média de Dor'),
                tooltip=['Postura', 'mean(Dor)']
            ), use_container_width=True)

        # 4. PREPARAÇÃO E DOWNLOAD DO PDF
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist_clinica = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: 
            hist_clinica = "Anamnese não cadastrada no sistema."

        pdf_metrics = {
            'ikdc': u_ikdc, 
            'ikdc_status': status_clinico, 
            'dor': ultima['Dor'], 
            'inchaco': ultima[col_inc], 
            'alta': prev_txt
        }
        
        # Removemos a imagem 'cap' do envio para o PDF
        pdf_bytes = create_pdf(p_sel, hist_clinica, pdf_metrics, {
            'ev': buf_ev, 
            'sono': buf_s, 
            'inchaco': buf_inc
        })
        
        st.download_button("📥 BAIXAR RELATÓRIO MASTER (PDF)", data=pdf_bytes, file_name=f"Relatorio_GENUA_{p_sel}.pdf")
        st.info(f"📝 ZenFisio: {p_sel} - Dor {ultima['Dor']}, IKDC {int(u_ikdc)}, Alta est. {prev_txt}.")
    else:
        st.info("Aguardando entrada de dados na planilha.")
