import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="GENUA Clinical Support", layout="wide", page_icon="🏥")

# CSS para manter o visual GENUA e evitar letras brancas no tablet
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
    menu = st.radio("MENU", ["Check-in Paciente 📝", "Painel Analítico 📊"])

# --- MÓDULO 1: CHECK-IN ---
if "Check-in" in menu:
    st.header("Entrada de Dados Clínicos")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: Jonas Hugo")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Dor agora (EVA 0-10)", options=list(range(11)))
            sono = st.radio("Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("REGISTRAR"):
            if paciente:
                df_h = conn.read(ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
                conn.update(data=pd.concat([df_h, nova_linha], ignore_index=True))
                st.success("Dados salvos!")
                st.balloons()

# --- MÓDULO 2: PAINEL ANALÍTICO ---
else:
    st.header("📊 Inteligência Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        # Dicionário atualizado com os nomes da sua planilha
        historias = {
            "Jonas Hugo": "👨‍🦳 **Caso:** Pós-operatório de LCA. Foco em ganho de força explosiva e retorno ao esporte.",
            "Joshua Leandro": "🏃‍♂️ **Caso:** Dor Patelofemoral Crônica. Apresenta 'Sinal do Cinema' após longos períodos sentado.",
            "Ricardo Biondi": "💻 **Caso:** Programador com dor mecânica crônica influenciada por postura e sono.",
            "José Silva": "👨‍🦳 **Caso:** Osteoartrite de joelho grau II em fase de progressão de carga.",
            "Maria Oliveira": "👩‍ **Caso:** Condropatia patelar com episódios frequentes de flare-up."
        }

        # Remove espaços dos nomes para garantir o cruzamento
        df['Paciente'] = df['Paciente'].str.strip()
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        
        # Exibição da História
        st.info(historias.get(p_sel, f"📜 História clínica não cadastrada para {p_sel}."))

        df_p = df[df['Paciente'] == p_sel].copy()
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        
        ultima = df_p.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Atual", f"{ultima['Dor']}/10")
        c2.metric("Capacidade Funcional", f"{ultima['Score_Funcao']:.1f}/10")
        c3.metric("Eficiência de Carga", f"{(ultima['Score_Funcao']*10):.0f}%")

        st.write("---")
        st.subheader("🧬 Evolução: Dor (Vermelho) vs Função (Verde)")
        st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])

        # Raciocínio Clínico
        st.subheader("💡 Suporte à Decisão")
        if ultima['Sono'] == "Ruim" and ultima['Dor'] >= 6:
            st.error("🚨 **Alerta de Sensibilização:** Sono ruim correlacionado a dor alta. Recomenda-se modulação de carga.")
        elif ultima['Score_Funcao'] > 8:
            st.success("✅ **Alta Funcionalidade:** Paciente pronto para progressão final ou alta clínica.")

    else:
        st.info("Aguardando dados.")
