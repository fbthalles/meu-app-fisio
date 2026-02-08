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
    """Remove emojis e caracteres que travam o PDF (padrão Latin-1)."""
    if not isinstance(txt, str): 
        return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, dor_at, func_at, ikdc_at, prev_alta):
    """Gera o laudo médico formatado."""
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
    pdf.ln(10)
    
    # Seção 1: História
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 1. Historia Pregressa e Diagnostico", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 8, limpar_texto_pdf(hist))
    pdf.ln(5)
    
    # Seção 2: Métricas
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 2. Metricas de Desempenho (PBE)", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"- Nivel de Dor Atual (EVA): {dor_at}/10", ln=True)
    pdf.cell(0, 8, f"- Capacidade Funcional Estimada: {func_at:.1f}/10", ln=True)
    pdf.cell(0, 8, f"- Score Funcional IKDC: {ikdc_at}", ln=True)
    pdf.ln(5)

    # Seção 3: Prognóstico
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 3. Prognostico e Previsao de Alta", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"- Data Estimada para atingir 90% de funcao: {prev_alta}", ln=True)
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'I', 8)
    pdf.multi_cell(0, 5, "Este documento e um suporte a decisao clinica baseado nos guidelines JOSPT e OARSI. Dados gerados via GENUA Intelligence System.")
    
    return pdf.output()

# --- 2. CONFIGURAÇÃO DE INTERFACE ---

st.set_page_config(page_title="GENUA Clinical Intelligence", layout="wide", page_icon="🏥")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #1f1f1f !important; }
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

# --- 5. MÓDULOS DO SISTEMA ---

if menu == "Check-in Diário 📝":
    st.header("Entrada de Dados Diários")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente")
        col1, col2 = st.columns(2)
        with col1:
            dor = st.select_slider("Dor agora (0-10)", options=list(range(11)))
            sono = st.radio("Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura hoje", ["Sentado", "Em pé"], horizontal=True)
        with col2:
            agac = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            sup = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            sdn = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
        if st.form_submit_button("REGISTRAR NO SISTEMA"):
            df_h = conn.read(ttl=0).dropna(how="all")
            nova_l = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn}])
            conn.update(data=pd.concat([df_h, nova_l], ignore_index=True))
            st.success("Check-in salvo!")

elif menu == "Avaliação IKDC (Mensal) 📋":
    st.header("Questionário IKDC (Score Funcional)")
    with st.form(key="ikdc_form"):
        p_ikdc = st.text_input("Paciente")
        nota = st.slider("Função Global (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR SCORE CIENTÍFICO"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("IKDC Registrado!")

else: # PAINEL ANALÍTICO (O CÉREBRO)
    st.header("📊 Painel de Decisão Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        
        # 1. Busca História
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            historia = df_cad[df_cad['Nome'].str.strip() == p_sel.strip()]['Historia'].values[0]
            st.info(f"📝 **História:** {historia}")
        except:
            historia = "Não cadastrada."
        
        # 2. Cálculos de Função
        df_p = df[df['Paciente'] == p_sel].copy()
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        ultima = df_p.iloc[-1]

        # 3. Previsão de Alta (IA)
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
            st.success(f"🔮 **Previsão de Alta (90% de Função):** {prev_txt}")
        except:
            prev_txt = "Em análise"

        # 4. Métricas e IKDC
        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Atual", f"{ultima['Dor']}/10")
        try:
            df_ikdc_all = conn.read(worksheet="IKDC", ttl=0)
            u_score = df_ikdc_all[df_ikdc_all['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            status = "🔴 Severo" if u_score < 40 else "🟡 Regular" if u_score < 65 else "🟢 Bom" if u_score < 85 else "🏆 Excelente"
            c2.metric("Score IKDC", f"{u_score:.0f}/100", delta=status)
        except:
            u_score = "N/A"
            c2.metric("Score IKDC", "N/A")
        c3.metric("Função Diária", f"{(ultima['Score_Funcao']*10):.0f}%")

        # 5. Gráficos
        st.write("---")
        st.subheader("Evolução: Dor (Vermelho) vs Função (Azul)")
        st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])

        # 6. Raciocínio Clínico
        st.write("---")
        st.subheader("💡 Raciocínio Baseado em Evidências")
        col_m, col_b = st.columns(2)
        with col_m:
            if "Dor" in ultima['Step_Down']: st.warning("⚠️ **Foco Excêntrico:** Dor no Step Down indica déficit de controle motor e força proximal.")
            if ultima['Postura'] == "Sentado" and ultima['Dor'] > 4: st.info("ℹ️ **Sinal do Cinema:** Postura sentada agravando a dor sugere irritabilidade patelofemoral.")
        with col_b:
            if ultima['Sono'] == "Ruim": st.error("🚨 **Sensibilização:** Sono ruim detectado. Reduzir intensidade hoje para evitar picos de dor.")
        
        # 7. Geração do Laudo PDF
        st.write("---")
        texto_zen = f"Evolução {p_sel}: Dor {ultima['Dor']}/10, Score Funcional {ultima['Score_Funcao']:.1f}/10. Sono {ultima['Sono']} e Postura {ultima['Postura']}."
        st.text_area("Copie para o ZenFisio:", value=texto_zen)

        # --- EXPORTAÇÃO DE LAUDO PDF (DENTRO DA IDENTAÇÃO) ---
        st.write("---")
        st.subheader("📄 Relatório para Médico/Convênio")
        
        try:
            prev_txt = data_previsao.strftime("%d/%m/%Y")
        except:
            prev_txt = "Em análise"
            
        try:
            ikdc_txt = f"{ultimo_score:.1f}/100"
        except:
            ikdc_txt = "N/A"
        
        # Gera os bytes do PDF
        pdf_bytes = create_pdf(p_sel, historia, ultima['Dor'], ultima['Score_Funcao'], ikdc_txt, prev_txt)
        
        # O botão de download deve estar aqui, indentado!
        st.download_button(
            label="📥 BAIXAR RELATÓRIO PDF",
            data=pdf_bytes,
            file_name=f"Relatorio_GENUA_{p_sel}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Aguardando dados para análise.")

# FIM DO ARQUIVO - NÃO COLOQUE MAIS NADA ABAIXO DESTA LINHA!
