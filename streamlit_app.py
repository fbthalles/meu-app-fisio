import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt
import numpy as np
from fpdf import FPDF

# --- 1. FUNÇÕES DE SUPORTE (PDF SEM EMOJIS) ---

def limpar_texto_pdf(txt):
    """Remove caracteres especiais (emojis) que quebram o PDF."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, dor_at, func_at, ikdc_at, prev_alta):
    """Gera o laudo médico formatado em bytes."""
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except:
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "RELATORIO DE EVOLUCAO CLINICA", ln=True, align='C')
    pdf.set_font("helvetica", '', 12)
    pdf.cell(0, 10, f"Paciente: {limpar_texto_pdf(p_name).upper()}", ln=True, align='C')
    pdf.ln(10)
    
    # Seções do PDF
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 1. Historia Pregressa e Diagnostico", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 8, limpar_texto_pdf(hist))
    pdf.ln(5)
    
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 2. Metricas de Desempenho (PBE)", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"- Dor Atual (EVA): {dor_at}/10", ln=True)
    pdf.cell(0, 8, f"- Capacidade Funcional Estimada: {func_at:.1f}/10", ln=True)
    pdf.cell(0, 8, f"- Score Funcional IKDC: {ikdc_at}", ln=True)
    pdf.ln(5)

    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 3. Prognostico e Previsao de Alta", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"- Data Estimada para atingir 90% de funcao: {prev_alta}", ln=True)
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'I', 8)
    pdf.multi_cell(0, 5, "Documento gerado via GENUA Intelligence System.")
    
    return bytes(pdf.output())

# --- 2. CONFIGURAÇÃO DE INTERFACE ---

st.set_page_config(page_title="GENUA Clinical Intelligence", layout="wide", page_icon="🏥")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, h4, p, label { color: #008091 !important; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #008091 !important; color: white !important; font-weight: bold; }
    [data-testid="stMetric"] { background-color: #f8fcfd !important; border: 1px solid #008091; border-radius: 15px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- 4. BARRA LATERAL ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, width=250)
    except:
        st.subheader("GENUA Instituto")
    st.write("---")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação IKDC (Mensal) 📋", "Painel Analítico 📊"])

# --- MÓDULO 1: CHECK-IN DIÁRIO (RESTAURADO COMPLETO) ---
if menu == "Check-in Diário 📝":
    st.header("Entrada de Dados Diários")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Dor agora (EVA 0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante hoje", ["Sentado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
        if st.form_submit_button("REGISTRAR NO SISTEMA"):
            df_h = conn.read(ttl=0).dropna(how="all")
            nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
            conn.update(data=pd.concat([df_h, nova_linha], ignore_index=True))
            st.success("Check-in salvo!")

# --- MÓDULO 2: IKDC (RESTAURADO COMPLETO) ---
elif menu == "Avaliação IKDC (Mensal) 📋":
    st.header("📋 Questionário IKDC (Score Funcional)")
    with st.form(key="ikdc_form", clear_on_submit=True):
        paciente_ikdc = st.text_input("Nome do Paciente")
        st.markdown("##### Dificuldade para subir/descer escadas?")
        p2 = st.select_slider("Escadas", options=["Extrema", "Muita", "Moderada", "Leve", "Nenhuma"])
        st.markdown("##### Nota global da função do joelho (0-100)?")
        p4 = st.slider("Nota", 0, 100, 50)
        if st.form_submit_button("SALVAR SCORE CIENTÍFICO"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": paciente_ikdc.strip(), "Score_IKDC": p4}])], ignore_index=True))
            st.success("IKDC Salvo!")

# --- MÓDULO 3: PAINEL ANALÍTICO (O "CÉREBRO" RESTAURADO) ---
else:
    st.header("📊 Painel de Decisão Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        df['Paciente'] = df['Paciente'].str.strip()
        p_sel = st.selectbox("Selecione o Paciente para Análise", df['Paciente'].unique())

        # 1. História Clínica
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            historia = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
            st.info(f"📝 **História Clínica:** {historia}")
        except:
            historia = "Não cadastrada."

        # 2. Processamento
        df_p = df[df['Paciente'] == p_sel].copy()
        mapa_f = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa_f) + df_p['Step_Up'].map(mapa_f) + df_p['Step_Down'].map(mapa_f)) / 3
        ultima = df_p.iloc[-1]

        # 3. Previsão de Alta (IA)
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_previsao = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_previsao.strftime("%d/%m/%Y")
            st.success(f"🔮 **Previsão de Alta (90%):** {prev_txt}")
        except:
            prev_txt = "Em análise"

        # 4. Métricas e IKDC
        m1, m2, m3 = st.columns(3)
        m1.metric("Dor Atual", f"{ultima['Dor']}/10")
        try:
            df_ikdc_all = conn.read(worksheet="IKDC", ttl=0)
            u_score = df_ikdc_all[df_ikdc_all['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            status = "🔴 Severo" if u_score < 40 else "🟡 Regular" if u_score < 65 else "🟢 Bom" if u_score < 85 else "🏆 Excelente"
            m2.metric("Score IKDC", f"{u_score:.0f}/100", delta=status)
        except:
            u_score = "N/A"
            m2.metric("Score IKDC", "N/A")
        m3.metric("Eficiência de Carga", f"{(ultima['Score_Funcao']*10):.0f}%")

        # 5. Gráficos e Tabs
        t1, t2 = st.tabs(["📈 Evolução", "🧬 Correlações"])
        with t1:
            st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])
        with t2:
            col_a, col_b = st.columns(2)
            with col_a:
                sono_pain = df_p.groupby('Sono')['Dor'].mean().reset_index()
                st.altair_chart(alt.Chart(sono_pain).mark_bar(color='#008091').encode(x='Sono', y='Dor'), use_container_width=True)
            with col_b:
                post_func = df_p.groupby('Postura')['Score_Funcao'].mean().reset_index()
                st.altair_chart(alt.Chart(post_func).mark_bar(color='#008091').encode(x='Postura', y='Score_Funcao'), use_container_width=True)

        # 6. Raciocínio Clínico (PBE)
        st.write("---")
        c_m, c_b = st.columns(2)
        with c_m:
            st.markdown("**Análise Mecânica**")
            if "Dor" in ultima['Step_Down']: st.warning("⚠️ Déficit Excêntrico detectado.")
        with c_b:
            st.markdown("**Análise Biopsicossocial**")
            if ultima['Sono'] == "Ruim": st.error("🚨 Alerta de Sensibilização Central.")

        # 7. ZenFisio e PDF
        st.write("---")
        texto_zen = f"Evolução {p_sel}: Dor {ultima['Dor']}/10, Score Funcional {ultima['Score_Funcao']:.1f}/10."
        st.text_area("Copie para o ZenFisio:", value=texto_zen)
        
        st.subheader("📄 Relatório para Médico")
        ikdc_pdf = f"{u_score:.0f}/100" if u_score != "N/A" else "N/A"
        pdf_bytes = create_pdf(p_sel, historia, ultima['Dor'], ultima['Score_Funcao'], ikdc_pdf, prev_txt)
        st.download_button("📥 BAIXAR RELATÓRIO PDF", data=pdf_bytes, file_name=f"Relatorio_GENUA_{p_sel}.pdf", mime="application/pdf")
    else:
        st.info("Aguardando dados.")
