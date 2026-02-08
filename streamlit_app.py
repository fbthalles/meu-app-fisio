import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt

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

# --- 3. BARRA LATERAL ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, use_container_width=True)
    except:
        st.subheader("GENUA Instituto")
    st.write("---")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação Mensal (IKDC) 📋", "Painel Analítico 📊"])

# --- MÓDULO 1: CHECK-IN DIÁRIO ---
if "Check-in" in menu:
    st.header("Check-in de Evolução Diária")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: Gabriel Medeiros")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Dor agora (0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("REGISTRAR CHECK-IN"):
            if paciente:
                df_h = conn.read(ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
                conn.update(data=pd.concat([df_h, nova_linha], ignore_index=True))
                st.success("Dados de check-in salvos!")
                st.balloons()

# --- MÓDULO 2: QUESTIONÁRIO IKDC SIMPLIFICADO ---
elif "Avaliação Mensal" in menu:
    st.header("📋 Questionário Funcional IKDC (Simplificado)")
    st.info("Esta avaliação deve ser feita mensalmente para medir o ganho de função global.")
    
    with st.form(key="ikdc_form", clear_on_submit=True):
        paciente_ikdc = st.text_input("Nome do Paciente para IKDC")
        
        st.markdown("##### 1. Qual o nível mais alto de atividade que você consegue realizar sem dor?")
        p1 = st.selectbox("Atividade", ["Incapaz", "Atividade Leve (Caminhar)", "Atividade Moderada (Trabalho)", "Atividade Intensa (Esporte)"])
        
        st.markdown("##### 2. Nos últimos 7 dias, quão difícil foi subir ou descer escadas?")
        p2 = st.select_slider("Dificuldade Escadas", options=["Extrema", "Muita", "Moderada", "Leve", "Nenhuma"])
        
        st.markdown("##### 3. Nos últimos 7 dias, quão difícil foi agachar?")
        p3 = st.select_slider("Dificuldade Agachar", options=["Extrema", "Muita", "Moderada", "Leve", "Nenhuma"])
        
        st.markdown("##### 4. Como você avalia a função do seu joelho hoje? (0 é incapaz, 100 é perfeito)")
        p4 = st.slider("Nota de 0 a 100", 0, 100, 50)

        if st.form_submit_button("SALVAR AVALIAÇÃO CIENTÍFICA"):
            # Lógica simples de Score IKDC (0-100)
            mapa_ikdc = {"Incapaz": 0, "Atividade Leve": 33, "Atividade Moderada": 66, "Atividade Intensa": 100,
                         "Extrema": 0, "Muita": 25, "Moderada": 50, "Leve": 75, "Nenhuma": 100}
            
            score_final = (mapa_ikdc.get(p1, 50) + mapa_ikdc.get(p2, 50) + mapa_ikdc.get(p3, 50) + p4) / 4
            
            # Salvar em uma aba separada chamada 'IKDC'
            try:
                df_ikdc = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
                novo_ikdc = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": paciente_ikdc.strip(), "Score_IKDC": score_final}])
                conn.update(worksheet="IKDC", data=pd.concat([df_ikdc, novo_ikdc], ignore_index=True))
                st.success(f"Score IKDC de {score_final:.1f} registrado para {paciente_ikdc}!")
            except:
                st.error("Crie uma aba chamada 'IKDC' na sua planilha do Google com os títulos: Data, Paciente, Score_IKDC")

# --- MÓDULO 3: PAINEL ANALÍTICO ---
else:
    st.header("📊 Inteligência Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        df['Paciente'] = df['Paciente'].str.strip()
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())

        # História Clínica (da aba Cadastro)
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            historia_txt = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
            st.info(f"📝 **História:** {historia_txt}")
        except:
            st.warning("⚠️ História não cadastrada.")

        # Dashboards de Evolução
        df_p = df[df['Paciente'] == p_sel].copy()
        ultima = df_p.iloc[-1]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Diária", f"{ultima['Dor']}/10")
        
        # Busca último IKDC se existir
        try:
            df_ikdc_all = conn.read(worksheet="IKDC", ttl=0)
            ultimo_ikdc = df_ikdc_all[df_ikdc_all['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            c2.metric("Score IKDC (Mês)", f"{ultimo_ikdc:.1f}/100")
        except:
            c2.metric("Score IKDC", "N/A")
            
        c3.metric("Postura", ultima['Postura'])

        st.write("---")
        st.subheader("🧬 Gráfico de Evolução Dor vs Função Diária")
        st.line_chart(df_p.set_index('Data')[['Dor']])
