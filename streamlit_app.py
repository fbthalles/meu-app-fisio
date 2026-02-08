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
    .stButton>button { 
        width: 100%; border-radius: 12px; background-color: #008091 !important; 
        color: white !important; font-weight: bold; height: 3.5em; border: none; 
    }
    [data-testid="stMetric"] { 
        background-color: #f8fcfd !important; border: 1px solid #008091; 
        border-radius: 15px; padding: 15px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- 3. BARRA LATERAL ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, use_container_width=True)
    except:
        st.subheader("GENUA Instituto")
    st.write("---")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Paciente 📝", "Painel Analítico 📊"])

# --- MÓDULO 1: CHECK-IN DIÁRIO ---
if "Check-in" in menu:
    st.header("Entrada de Dados Clínicos")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: Jonas Hugo")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Dor agora (EVA 0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("REGISTRAR NO SISTEMA"):
            if paciente:
                try:
                    df_h = conn.read(ttl=0).dropna(how="all")
                    nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
                    conn.update(data=pd.concat([df_h, nova_linha], ignore_index=True))
                    st.success(f"Check-in de {paciente} salvo!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

# --- MÓDULO 2: PAINEL ANALÍTICO (DINÂMICO) ---
else:
    st.header("📊 Inteligência Clínica GENUA")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        df['Paciente'] = df['Paciente'].str.strip()
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())

        # --- NOVA LÓGICA: BUSCA HISTÓRIA NA PLANILHA ---
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            df_cad['Nome'] = df_cad['Nome'].str.strip()
            # Busca o texto da história para o nome selecionado
            historia_txt = df_cad[df_cad['Nome'] == p_sel]['Historia'].values[0]
            st.info(f"📝 **História Clínica:** {historia_txt}")
        except:
            st.warning("⚠️ História não encontrada na aba 'Cadastro' para este paciente.")

        df_p = df[df['Paciente'] == p_sel].copy()
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        
        ultima = df_p.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Atual", f"{ultima['Dor']}/10")
        c2.metric("Capacidade Funcional", f"{ultima['Score_Funcao']:.1f}/10")
        c3.metric("Eficiência de Carga", f"{(ultima['Score_Funcao']*10):.0f}%")

        st.write("---")
        st.subheader("🧬 Correlação: Dor (Vermelho) vs Função (Verde)")
        st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])

        # --- INSIGHTS AUTOMÁTICOS ---
        st.subheader("💡 Raciocínio Clínico")
        if ultima['Sono'] == "Ruim" and ultima['Dor'] >= 6:
            st.error("🚨 **Alerta de Sensibilização:** Sono ruim correlacionado a dor alta. Modular carga hoje.")
        elif ultima['Score_Funcao'] > 8:
            st.success("✅ **Critério de Progressão:** Alta funcionalidade detectada. Apto para novos desafios.")

    else:
        st.info("Aguardando dados para gerar o painel.")
