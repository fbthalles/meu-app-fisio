import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="GENUA - KneeTech", layout="wide", page_icon="🦵")

# --- ESTILO VISUAL "GENUA PREMIUM" (Blindado contra fundo branco) ---
st.markdown("""
    <style>
    /* Força o tema claro para evitar erro de visibilidade */
    .stApp {
        background-color: #FFFFFF !important;
        color: #1f1f1f !important;
    }
    
    /* Cores da Marca GENUA (Azul Petróleo) */
    h1, h2, h3, h4, p, label, .stMarkdown {
        color: #008091 !important; /* Tom extraído da logo */
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Botão Principal */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        background-color: #008091 !important;
        color: white !important;
        font-weight: bold;
        height: 3.5em;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Cards de Métricas */
    [data-testid="stMetric"] {
        background-color: #f8fcfd !important;
        border: 1px solid #008091;
        border-radius: 15px;
        padding: 15px;
    }

    /* Inputs e Selects (Preto para visibilidade) */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Conexão com Banco de Dados
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Erro de conexão. Verifique as Secrets.")
    st.stop()

# --- BARRA LATERAL COM LOGO GENUA ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, use_container_width=True)
    except:
        st.subheader("GENUA Instituto")
    
    st.write("---")
    menu = st.radio("MENU PRINCIPAL", ["Check-in Paciente 📝", "Painel do Fisioterapeuta 📊"])
    st.write("---")
    st.caption("v1.2 - Powered by KneeTech AI")

# --- MÓDULO 1: CHECK-IN ---
if "Check-in" in menu:
    st.header("Avaliação Diária de Evolução")
    
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome Completo do Paciente", placeholder="Ex: Jonas Hugo")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Nível de dor agora (0-10)", options=list(range(11)))
            sono = st.radio("Como você dormiu?", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura de hoje", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)

        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("ENVIAR PARA O FISIOTERAPEUTA"):
            if paciente:
                try:
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
                    st.success(f"✨ Dados enviados com sucesso, {paciente}!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Por favor, preencha o nome do paciente.")

# --- MÓDULO 2: PAINEL ---
else:
    st.header("📊 Painel de Controle GENUA")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        p_sel = st.selectbox("Filtrar Paciente", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel]
        
        st.subheader(f"Evolução Clínica: {p_sel}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Dor Atual", f"{df_p.iloc[-1]['Dor']}/10")
        m2.metric("Qualidade Sono", df_p.iloc[-1]['Sono'])
        m3.metric("Postura", df_p.iloc[-1]['Postura'])
        
        st.line_chart(df_p.set_index('Data')['Dor'])
