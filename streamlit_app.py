import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt

# --- 1. CONFIGURAÇÃO E TEMA ---
st.set_page_config(page_title="GENUA Clinical Support", layout="wide", page_icon="🏥")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #1f1f1f !important; }
    h1, h2, h3, h4, p, label { color: #008091 !important; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #008091 !important; color: white !important; font-weight: bold; height: 3.5em; border: none; }
    [data-testid="stMetric"] { background-color: #f8fcfd !important; border: 1px solid #008091; border-radius: 15px; padding: 15px; }
    .clinical-box { background-color: #f0f9fa; padding: 20px; border-left: 5px solid #008091; border-radius: 5px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Erro de conexão.")
    st.stop()

# --- 3. LOGO E NAVEGAÇÃO ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, use_container_width=True)
    except:
        st.subheader("GENUA Instituto")
    st.write("---")
    menu = st.radio("MENU", ["Check-in Paciente 📝", "Análise de Guidelines 📊"])

# --- MÓDULO 1: CHECK-IN (Foco em Agilidade no Tablet) ---
if "Check-in" in menu:
    st.header("Entrada de Dados Clínicos")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: José Silva")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Nível de Dor (EVA)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais (Guidelines JOSPT)")
            agachar = st.selectbox("Agachamento Profundo", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up (Força Concêntrica)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down (Controle Excêntrico)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("REGISTRAR AVALIAÇÃO"):
            if paciente:
                df_h = conn.read(ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente, "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
                conn.update(data=pd.concat([df_h, nova_linha], ignore_index=True))
                st.success(f"Dados de {paciente} integrados ao dashboard!")
                st.balloons()

# --- MÓDULO 2: PAINEL DE GUIDELINES (O "Raciocínio" Novo) ---
else:
    st.header("📊 Painel de Decisão Baseada em Evidências")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # Mapeamento PBE (0 a 10)
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        
        ultima = df_p.iloc[-1]
        
        # --- SEÇÃO 1: MÉTRICAS E STATUS ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Atual", f"{ultima['Dor']}/10")
        c2.metric("Capacidade Funcional",
