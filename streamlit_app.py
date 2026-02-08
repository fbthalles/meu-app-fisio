import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="GENUA Clinical Support", layout="wide", page_icon="🏥")

# CSS para garantir contraste e identidade visual GENUA
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
except:
    st.error("Erro de conexão. Verifique as 'Secrets'.")
    st.stop()

# --- 3. BARRA LATERAL (LOGO GENUA) ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, use_container_width=True)
    except:
        st.subheader("GENUA Instituto")
    st.write("---")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Paciente 📝", "Painel de Guidelines 📊"])

# --- MÓDULO 1: CHECK-IN DIÁRIO ---
if "Check-in" in menu:
    st.header("Entrada de Dados Clínicos")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: José Silva")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Fatores Moduladores")
            dor = st.select_slider("Dor agora (EVA 0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono (OARSI)", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes de Capacidade (JOSPT)")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up (Concêntrico)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down (Excêntrico)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("REGISTRAR NO SISTEMA"):
            if paciente:
                df_h = conn.read(ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente, "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
                conn.update(data=pd.concat([df_h, nova_linha], ignore_index=True))
                st.success(f"Dados de {paciente} salvos!")
                st.balloons()

# --- MÓDULO 2: PAINEL DE DIRETRIZES CLÍNICAS ---
else:
    st.header("📊 Painel de Decisão Baseada em Evidências")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # Mapeamento para Score Funcional
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        
        ultima = df_p.iloc[-1]
        
        # --- MÉTRICAS PRINCIPAIS ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Atual", f"{ultima['Dor']}/10")
        c2.metric("Capacidade Funcional", f"{ultima['Score_Funcao']:.1f}/10") # ERRO CORRIGIDO AQUI!
        c3.metric("Eficiência de Carga", f"{(ultima['Score_Funcao']*10):.0f}%")

        # --- GRÁFICO DE CORRELAÇÃO MULTI-VARIÁVEL ---
        st.write("---")
        st.subheader("🧬 Correlação Cruzada: Dor vs Função")
        chart_data = df_p.set_index('Data')[['Dor', 'Score_Funcao']]
        st.line_chart(chart_data, color=["#FF4B4B", "#008091"])

        # --- ANÁLISE DE GUIDELINES (JOSPT / OARSI) ---
        st.write("---")
        st.subheader("💡 Raciocínio Clínico Integrado")
        
        col_jospt, col_oarsi = st.columns(2)
        
        with col_jospt:
            st.markdown("##### 📏 Guideline JOSPT (Mecânico)")
            if "Dor" in ultima['Step_Down'] or "Incapaz" in ultima['Step_Down']:
                st.warning("**Déficit de Controle Excêntrico:** Alta irritabilidade em Step Down sugere foco em fortalecimento de glúteo médio e controle de valgo dinâmico.")
            if "Sentado" in ultima['Postura'] and "Dor" in ultima['Agachamento']:
                st.info("**Sobrecarga Estática:** A correlação entre postura sentada e dor ao agachar indica possível compressão patelofemoral prolongada.")

        with col_oarsi:
            st.markdown("##### 🧠 Guideline OARSI (Biopsicossocial)")
            if ultima['Sono'] == "Ruim" and ultima['Dor'] >= 6:
                st.error("**Alerta de Sensibilização:** Sono ruim correlacionado a dor alta. Guideline recomenda educação em dor e modulação de carga para evitar flare-ups.")
            elif ultima['Sono'] == "Bom" and ultima['Dor'] <= 3:
                st.success("**Janela de Progressão:** Paciente com sono restaurador e baixa dor. Momento ideal para progressão de carga (PBE).")

        # --- EXPORTAÇÃO PARA ZENFISIO ---
        st.write("---")
        resumo = f"Evolução {p_sel}: Dor {ultima['Dor']}/10, Função {ultima['Score_Funcao']:.1f}/10. Predomínio de postura {ultima['Postura']} com sono {ultima['Sono']}."
        st.text_area("Copie para o ZenFisio:", value=resumo)

    else:
        st.info("Aguardando os primeiros dados para gerar o painel.")
