import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt
import numpy as np
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="GENUA Clinical Intelligence", layout="wide", page_icon="🏥")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #1f1f1f !important; }
    h1, h2, h3, h4, p, label { color: #008091 !important; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #008091 !important; color: white !important; font-weight: bold; height: 3.5em; border: none; }
    [data-testid="stMetric"] { background-color: #f8fcfd !important; border: 1px solid #008091; border-radius: 15px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- 3. FUNÇÃO DO LAUDO PDF ---
def create_pdf(p_name, hist, dor_at, func_at, ikdc_at, prev_alta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "GENUA INSTITUTO DO JOELHO", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, f"RELATORIO CLINICO: {p_name.upper()}", ln=True)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 8, f"Historia: {hist}")
    pdf.ln(5)
    pdf.cell(0, 8, f"- Dor Atual: {dor_at}/10", ln=True)
    pdf.cell(0, 8, f"- Capacidade Funcional: {func_at:.1f}/10", ln=True)
    pdf.cell(0, 8, f"- Score IKDC: {ikdc_at}", ln=True)
    pdf.cell(0, 8, f"- Previsao Estimada de Alta: {prev_alta}", ln=True)
    return pdf.output()

# --- 4. BARRA LATERAL ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, use_container_width=True)
    except:
        st.subheader("GENUA Instituto")
    st.write("---")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação IKDC (Mensal) 📋", "Painel Analítico 📊"])

# --- MÓDULO 1: CHECK-IN ---
if "Check-in" in menu:
    st.header("Entrada de Dados Diários")
    with st.form(key="checkin_form", clear_on_submit=True):
        p_nome = st.text_input("Nome do Paciente")
        col1, col2 = st.columns(2)
        with col1:
            dor = st.select_slider("Dor agora (0-10)", options=list(range(11)))
            sono = st.radio("Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            post = st.radio("Postura", ["Sentado", "Em pé"], horizontal=True)
        with col2:
            agac = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            sup = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            sdn = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
        if st.form_submit_button("SALVAR CHECK-IN"):
            df_h = conn.read(ttl=0).dropna(how="all")
            nova_l = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": p_nome.strip(), "Dor": int(dor), "Sono": sono, "Postura": post, "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn}])
            conn.update(data=pd.concat([df_h, nova_l], ignore_index=True))
            st.success("Salvo!")

# --- MÓDULO 2: IKDC ---
elif "IKDC" in menu:
    st.header("📋 Questionário IKDC")
    with st.form(key="ikdc_form"):
        p_ikdc = st.text_input("Paciente")
        nota = st.slider("Nota Global (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            nova_i = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])
            conn.update(worksheet="IKDC", data=pd.concat([df_i, nova_i], ignore_index=True))
            st.success("IKDC Salvo!")

# --- MÓDULO 3: PAINEL ANALÍTICO ---
else:
    st.header("📊 Painel de Decisão Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Paciente", df['Paciente'].unique())
        
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            historia = df_cad[df_cad['Nome'].str.strip() == p_sel.strip()]['Historia'].values[0]
            st.info(f"📝 **História:** {historia}")
        except:
            historia = "Não cadastrada."
            st.warning("História não encontrada.")

        df_p = df[df['Paciente'] == p_sel].copy()
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        ultima = df_p.iloc[-1]

        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Atual", f"{ultima['Dor']}/10")
        
        try:
            df_ikdc_all = conn.read(worksheet="IKDC", ttl=0)
            u_score = df_ikdc_all[df_ikdc_all['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            status = "🔴 Severo" if u_score < 40 else "🟡 Regular" if u_score < 65 else "🟢 Bom" if u_score < 85 else "🏆 Excelente"
            # CORREÇÃO DO PARÊNTESE NA LINHA ABAIXO
            c2.metric("Score IKDC", f"{u_score:.0f}/100", delta=status)
        except:
            u_score = "N/A"
            c2.metric("Score IKDC", "N/A")
        
        c3.metric("Eficiência de Carga", f"{(ultima['Score_Funcao']*10):.0f}%")

        st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])
        
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
            st.success(f"🔮 **Previsão de Alta (90% de Função):** {prev_txt}")
        except:
            prev_txt = "Em análise"

        pdf_bytes = create_pdf(p_sel, historia, ultima['Dor'], ultima['Score_Funcao'], str(u_score), prev_txt)
        st.download_button("📥 BAIXAR LAUDO PDF", data=pdf_bytes, file_name=f"Laudo_{p_sel}.pdf", mime="application/pdf")
