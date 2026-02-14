import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt
import numpy as np
from fpdf import FPDF

# --- 1. FUNÇÕES DE SUPORTE (PDF E LIMPEZA) ---

def limpar_texto_pdf(txt):
    """Remove caracteres especiais (emojis) que quebram o PDF."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, dor_at, func_at, ikdc_at, prev_alta, inchaco_at):
    """Gera o laudo médico formatado e retorna bytes."""
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
    
    # Seção 1: História
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 1. Historia e Contexto Clinico", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 8, limpar_texto_pdf(hist))
    pdf.ln(5)
    
    # Seção 2: Métricas PBE
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 2. Metricas de Desempenho (PBE)", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"- Dor Atual (EVA): {dor_at}/10", ln=True)
    pdf.cell(0, 8, f"- Inchaco (Grau Stroke): {inchaco_at}", ln=True)
    pdf.cell(0, 8, f"- Capacidade Funcional: {func_at:.1f}/10", ln=True)
    pdf.cell(0, 8, f"- Score IKDC: {ikdc_at}", ln=True)
    pdf.ln(5)

    # Seção 3: Prognóstico
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 3. Prognostico e Previsao de Alta", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"- Data Estimada para 90% de funcao: {prev_alta}", ln=True)
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'I', 8)
    pdf.multi_cell(0, 5, "Este documento e um suporte a decisao clinica gerado via GENUA Intelligence System.")
    
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
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação IKDC 📋", "Painel Analítico 📊"])

# --- 5. MÓDULOS DO SISTEMA ---

if menu == "Check-in Diário 📝":
    st.header("Entrada de Dados Diários")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Dor agora (EVA 0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            sup = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            sdn = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            
            # --- SEÇÃO INCHAÇO (LINGUAGEM ACESSÍVEL) ---
            st.markdown("#### 🌊 Inchaço do Joelho")
            inchaco = st.select_slider(
                "Nível de Inchaço (Stroke Test)", 
                options=["0", "1", "2", "3"], 
                help="Grau 0: Sem inchaço | Grau 3: Inchaço severo"
            )

        if st.form_submit_button("REGISTRAR NO SISTEMA"):
            df_h = conn.read(ttl=0).dropna(how="all")
            nova_l = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), 
                "Paciente": paciente.strip(), 
                "Dor": int(dor), 
                "Inchaco": inchaco, 
                "Sono": sono, 
                "Postura": postura, 
                "Agachamento": agachar, 
                "Step_Up": sup, 
                "Step_Down": sdn
            }])
            conn.update(data=pd.concat([df_h, nova_l], ignore_index=True))
            st.success(f"Check-in de {paciente} salvo!")

elif menu == "Avaliação IKDC 📋":
    st.header("📋 Questionário IKDC")
    with st.form(key="ikdc_form"):
        paciente_ikdc = st.text_input("Nome do Paciente")
        p4 = st.slider("Nota global da função (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR SCORE CIENTÍFICO"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": paciente_ikdc.strip(), "Score_IKDC": p4}])], ignore_index=True))
            st.success("IKDC Salvo!")

else: # PAINEL ANALÍTICO
    st.header("📊 Painel de Decisão Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        df['Paciente'] = df['Paciente'].str.strip()
        p_sel = st.selectbox("Paciente para Análise", df['Paciente'].unique())

        # 1. História Clínica
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            historia = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
            st.info(f"📝 **História:** {historia}")
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
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
            st.success(f"🔮 **Previsão de Alta (90%):** {prev_txt}")
        except:
            prev_txt = "Em análise"

        # 4. Métricas Principais
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dor Atual", f"{ultima['Dor']}/10")
        m2.metric("Inchaço (Grau)", f"{ultima.get('Inchaco', '0')}")
        try:
            df_ikdc_all = conn.read(worksheet="IKDC", ttl=0)
            u_score = df_ikdc_all[df_ikdc_all['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            m3.metric("Score IKDC", f"{u_score:.0f}/100")
        except:
            u_score = "N/A"
            m3.metric("Score IKDC", "N/A")
        m4.metric("Eficiência", f"{(ultima['Score_Funcao']*10):.0f}%")

        # 5. Gráficos e Tabs
        t1, t2 = st.tabs(["📈 Evolução", "🧬 Biopsicossocial"])
        with t1:
            st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])
        with t2:
            c_a, c_b = st.columns(2)
            with c_a:
                st.write("😴 Sono vs Dor")
                st.altair_chart(alt.Chart(df_p).mark_bar(color='#008091').encode(x='Sono', y='mean(Dor)'), use_container_width=True)
            with c_b:
                st.write("🪑 Postura vs Função")
                st.altair_chart(alt.Chart(df_p).mark_bar(color='#008091').encode(x='Postura', y='mean(Score_Funcao)'), use_container_width=True)

        # 6. Alertas e ZenFisio
        st.write("---")
        if "2" in str(ultima.get('Inchaco', '')) or "3" in str(ultima.get('Inchaco', '')):
            st.error("🚨 **Alerta de Irritabilidade:** Inchaço significativo detectado. Reduzir carga hoje.")
        
        texto_zen = f"Evolução {p_sel}: Dor {ultima['Dor']}/10, Inchaço {ultima.get('Inchaco', '0')}/3, Score Funcional {ultima['Score_Funcao']:.1f}/10."
        st.text_area("Copie para o ZenFisio:", value=texto_zen)
        
        # 7. Laudo PDF
        st.subheader("📄 Relatório para Médico")
        ikdc_pdf = f"{u_score:.0f}/100" if u_score != "N/A" else "N/A"
        inchaco_pdf = f"Grau {ultima.get('Inchaco', '0')}"
        
        pdf_bytes = create_pdf(p_sel, historia, ultima['Dor'], ultima['Score_Funcao'], ikdc_pdf, prev_txt, inchaco_pdf)
        st.download_button("📥 BAIXAR RELATÓRIO PDF", data=pdf_bytes, file_name=f"Relatorio_GENUA_{p_sel}.pdf", mime="application/pdf")
    else:
        st.info("Aguardando dados para análise.")
