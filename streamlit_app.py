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

# --- 1. FUNÇÕES DE SUPORTE (PDF E GRÁFICOS) ---

def limpar_texto_pdf(txt):
    """Garante que o PDF não trave com emojis ou acentos."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, dor_at, func_at, ikdc_at, prev_alta, inchaco_at, img_evolucao, img_inchaco):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho com Logo
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
    pdf.ln(5)
    
    # 1. História Clínica
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, " 1. HISTORIA E CONTEXTO", ln=True, fill=True)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 7, limpar_texto_pdf(hist))
    pdf.ln(5)
    
    # 2. Métricas Atuais
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, " 2. METRICAS DE DESEMPENHO ATUAIS", ln=True, fill=True)
    pdf.set_font("helvetica", '', 10)
    pdf.cell(95, 7, f"- Dor (EVA): {dor_at}/10", ln=0)
    pdf.cell(95, 7, f"- Inchaco (Stroke): {inchaco_at}", ln=1)
    pdf.cell(95, 7, f"- IKDC: {ikdc_at}", ln=0)
    pdf.cell(95, 7, f"- Alta Estimada: {prev_alta}", ln=1)
    pdf.ln(5)

    # 3. Gráficos de Evolução
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, " 3. ANALISE GRAFICA DE EVOLUCAO", ln=True, fill=True)
    
    # Imagem 1: Curva de Dor vs Função
    pdf.image(img_evolucao, x=15, y=pdf.get_y() + 5, w=170)
    pdf.set_y(pdf.get_y() + 90) # Pula o espaço do gráfico
    
    # Imagem 2: Histórico de Inchaço
    pdf.image(img_inchaco, x=15, y=pdf.get_y(), w=170)
    
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

        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
            st.info(f"📋 **História Clínica:** {hist}")
        except:
            hist = "Não cadastrada."

        df_p = df[df['Paciente'] == p_sel].copy()
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        ultima = df_p.iloc[-1]

        # Métricas na Tela
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

        # Gráficos na Tela (Altair)
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

        # Previsão de Alta
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
            st.success(f"🔮 **Previsão de Alta (90% de função):** {prev_txt}")
        except:
            prev_txt = "Em análise"

        # --- GERAÇÃO DE IMAGENS PARA O PDF (Matplotlib) ---
        
        # 1. Gráfico de Evolução
        fig_ev, ax_ev = plt.subplots(figsize=(8, 4))
        ax_ev.plot(df_p['Data'], df_p['Dor'], color='#FF4B4B', label='Dor (EVA)', marker='o', linewidth=2)
        ax_ev.plot(df_p['Data'], df_p['Score_Funcao'], color='#008091', label='Funcao (Score)', marker='s', linewidth=2)
        ax_ev.set_title("Evolucao: Dor vs Funcao", fontsize=12, fontweight='bold')
        ax_ev.legend()
        plt.xticks(rotation=45, fontsize=8)
        buf_ev = io.BytesIO()
        plt.savefig(buf_ev, format='png', bbox_inches='tight')
        plt.close(fig_ev)

        # 2. Gráfico de Inchaço
        fig_in, ax_in = plt.subplots(figsize=(8, 3))
        cores = ['#FF4B4B' if int(x) > 1 else '#008091' for x in df_p['Inchaco'].tail(10)]
        ax_in.bar(df_p['Data'].tail(10), pd.to_numeric(df_p['Inchaco'].tail(10)), color=cores)
        ax_in.set_title("Historico de Inchaco (Stroke Test)", fontsize=12, fontweight='bold')
        ax_in.set_ylim(0, 3)
        plt.xticks(rotation=45, fontsize=8)
        buf_in = io.BytesIO()
        plt.savefig(buf_in, format='png', bbox_inches='tight')
        plt.close(fig_in)

        # Botão de Download
        st.write("---")
        pdf_bytes = create_pdf(
            p_sel, hist, ultima['Dor'], ultima['Score_Funcao'], 
            u_ikdc, prev_txt, ultima.get('Inchaco', '0'), buf_ev, buf_in
        )
        st.download_button("📥 BAIXAR RELATÓRIO COMPLETO (PDF)", data=pdf_bytes, file_name=f"Laudo_GENUA_{p_sel}.pdf", mime="application/pdf")
    else:
        st.info("Aguardando dados.")
