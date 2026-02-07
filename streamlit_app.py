import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO FORÇADA DE TEMA ---
st.set_page_config(page_title="KneeTech Dashboard", layout="wide", page_icon="🦵")

# CSS "Blindado" para evitar o fundo branco com letra branca
st.markdown("""
    <style>
    /* Força o fundo e a cor do texto global */
    .stApp {
        background-color: #FFFFFF !important;
        color: #262730 !important;
    }
    
    /* Garante que os títulos fiquem escuros */
    h1, h2, h3, h4, h5, h6, p, label {
        color: #1f1f1f !important;
    }

    /* Estilização dos Botões */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        background-color: #007bff !important;
        color: white !important;
        font-weight: bold;
        border: none;
        height: 3.5em;
    }

    /* Estilização das Métricas (Cards) */
    [data-testid="stMetric"] {
        background-color: #f0f2f6 !important;
        border-radius: 15px;
        padding: 15px;
        border: 1px solid #d1d1d1;
    }
    
    /* Corrige visibilidade de inputs */
    .stTextInput>div>div>input {
        color: #1f1f1f !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Conexão
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Erro de conexão.")
    st.stop()

st.title("🏥 KneeTech: Inteligência Clínica")

# Navegação Lateral
menu = st.sidebar.radio("Navegação", ["Check-in Paciente 📝", "Painel do Fisioterapeuta 📊"])

if "Check-in" in menu:
    st.header("Bom dia! Vamos registrar sua evolução?")
    
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome completo do paciente", placeholder="Digite seu nome aqui...")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🌡️ Estado Geral")
            dor = st.select_slider("Nível de dor no joelho (0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do sono hoje", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura de hoje", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)

        with col2:
            st.markdown("### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("ENVIAR CHECK-IN"):
            if paciente:
                df_h = conn.read(ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Paciente": paciente,
                    "Dor": int(dor),
                    "Sono": sono,
                    "Postura": postura,
                    "Agachamento": agachar,
                    "Step_Up": step_up,
                    "Step_Down": step_down
                }])
                df_f = pd.concat([df_h, nova_linha], ignore_index=True)
                conn.update(data=df_f)
                st.success(f"Dados salvos para {paciente}!")
                st.balloons()
            else:
                st.warning("Preencha o nome.")

else:
    st.header("📊 Painel de Análise")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel]
        
        st.subheader(f"Evolução: {p_sel}")
        m1, m2 = st.columns(2)
        m1.metric("Última Dor", f"{df_p.iloc[-1]['Dor']}/10")
        m2.metric("Total de Check-ins", len(df_p))
        
        st.line_chart(df_p.set_index('Data')['Dor'])
