import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import numpy as np
from fpdf import FPDF
from PIL import Image

# --- 1. FUNÇÕES DE SUPORTE (PDF E LIMPEZA) ---
def limpar_texto_pdf(txt):
    """Garante que o PDF não trave com emojis ou acentos."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, dor_at, func_at, ikdc_at, prev_alta, inchaco_at, hist_inchaco):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except:
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, "GENUA INSTITUTO DO JOELHO", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "RELATORIO DE EVOLUCAO CLINICA", ln=True, align='C')
    pdf.set_font("helvetica", '', 12)
    pdf.cell(0, 10, f"Paciente: {limpar_texto_pdf(p_name).upper()}", ln=True, align='C')
    pdf.ln(10)
    
    # Seções do Laudo
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 1. Historia e Contexto Clinico", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 8, limpar_texto_pdf(hist))
    pdf.ln(5)
    
    pdf.cell(0, 10, " 2. Metricas e Sinais Clinicos", ln=True, fill=True)
    pdf.cell(0, 8, f"- Dor (EVA): {dor_at}/10 | Inchaco (Stroke): {inchaco_at}", ln=True)
    pdf.cell(0, 8, f"- Tendencia Recente de Inchaco: {hist_inchaco}", ln=True)
    pdf.cell(0, 8, f"- Score Funcional Estimado: {func_at:.1f}/10 | IKDC: {ikdc_at}", ln=True)
    pdf.ln(5)

    pdf.cell(0, 10, " 3. Prognostico e Previsao de Alta", ln=True, fill=True)
    pdf.cell(0, 8, f"- Data Estimada para atingir 90% de funcao: {prev_alta}", ln=True)
    
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
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 4. NAVEGAÇÃO ---
with st.sidebar:
    try:
        st.image("Ativo-1.png", width=250)
    except:
        st.header("GENUA")
    menu = st.radio("MENU", ["Check-in 📝", "IKDC 📋", "Painel Analítico 📊"])

# --- 5. MÓDULOS ---

if menu == "Check-in 📝":
    st.header("Entrada de Dados Diários")
    with st.form("checkin", clear_on_submit=True):
        paciente = st.text_input("Paciente")
        c1, c2 = st.columns(2)
        with c1:
            dor = st.select_slider("Dor (0-10)", options=list(range(11)))
            sono = st.radio("Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura", ["Sentado", "Em pé", "Equilibrado"], horizontal=True)
        with c2:
            agac = st.selectbox("Agachamento", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sup = st.selectbox("Step Up", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sdn = st.selectbox("Step Down", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            inchaco = st.select_slider("Inchaço", options=["0", "1", "2", "3"])
        
        if st.form_submit_button("REGISTRAR"):
            df = conn.read(ttl=0).dropna(how="all")
            nova = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Inchaco": str(inchaco), "Sono": sono, "Postura": postura, "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn}])
            conn.update(data=pd.concat([df, nova], ignore_index=True))
            st.success("Salvo!")

elif menu == "IKDC 📋":
    st.header("Score Científico IKDC")
    with st.form("ikdc"):
        p_ikdc = st.text_input("Paciente")
        nota = st.slider("Nota (0-100)", 0, 100, 50)
        if st.form_submit_button("REGISTRAR SCORE"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("IKDC Salvo!")

else: # PAINEL ANALÍTICO
    st.header("📊 Inteligência Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        df['Paciente'] = df['Paciente'].str.strip()
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())

        # 1. Cadastro/História
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
            st.info(f"📋 **História Clínica:** {hist}")
        except:
            hist = "Não cadastrada."

        # 2. Processamento (Score Funcional GENUA)
        df_p = df[df['Paciente'] == p_sel].copy()
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        ultima = df_p.iloc[-1]

        # 3. Métricas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dor", f"{ultima['Dor']}/10")
        m2.metric("Inchaço", f"Grau {ultima.get('Inchaco', '0')}")
        
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            m3.metric("IKDC", f"{u_ikdc:.0f}/100")
        except:
            u_ikdc = "Pendente"; m3.metric("IKDC", "N/A")
            
        m4.metric("Eficiência", f"{(ultima['Score_Funcao']*10):.0f}%")

        # 4. Gráficos
        t1, t2 = st.tabs(["📈 Evolução", "🌊 Inchaço"])
        with t1:
            st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])
        with t2:
            df_p['Inchaco_N'] = pd.to_numeric(df_p['Inchaco'], errors='coerce').fillna(0)
            c_inchaco = alt.Chart(df_p.tail(10)).mark_bar().encode(
                x='Data:O', y=alt.Y('Inchaco_N:Q', scale=alt.Scale(domain=[0, 3])),
                color=alt.condition(alt.datum.Inchaco_N > 1, alt.value('#FF4B4B'), alt.value('#008091'))
            ).properties(height=300)
            st.altair_chart(c_inchaco, use_container_width=True)

        # 5. IA: Previsão de Alta
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
            st.success(f"🔮 **Previsão de Alta (90% de função):** {prev_txt}")
        except:
            prev_txt = "Em análise"

        # 6. Laudo Médico
        st.write("---")
        tendencia = " -> ".join([str(int(x)) for x in df_p['Inchaco_N'].tail(3).tolist()])
        pdf_bytes = create_pdf(p_sel, hist, ultima['Dor'], ultima['Score_Funcao'], u_ikdc, prev_txt, ultima.get('Inchaco', '0'), tendencia)
        st.download_button("📥 BAIXAR RELATÓRIO PDF", data=pdf_bytes, file_name=f"Laudo_{p_sel}.pdf", mime="application/pdf")
    else:
        st.info("Aguardando dados.")
