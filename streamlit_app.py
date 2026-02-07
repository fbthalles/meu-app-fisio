import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt

# --- 1. CONFIGURAÇÃO E TEMA ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide", page_icon="🦵")

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
    menu = st.radio("MENU", ["Check-in Paciente 📝", "Painel Analítico 📊"])

# --- MÓDULO 1: CHECK-IN ---
if "Check-in" in menu:
    st.header("Avaliação Diária de Evolução")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: José Silva")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Dor agora (0-10)", options=list(range(11)))
            sono = st.radio("Sono de hoje", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura de hoje", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("REGISTRAR NO TABLET"):
            if paciente:
                df_h = conn.read(ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente, "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
                df_f = pd.concat([df_h, nova_linha], ignore_index=True)
                conn.update(data=df_f)
                st.success(f"Check-in de {paciente} salvo!")
                st.balloons()

# --- MÓDULO 2: PAINEL ANALÍTICO (CORRELAÇÕES) ---
else:
    st.header("📊 Inteligência de Dados GENUA")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        pacientes = df['Paciente'].unique()
        p_sel = st.selectbox("Selecione o Paciente para Correlação", pacientes)
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # --- PROCESSAMENTO DE DADOS ---
        mapa_funcao = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa_funcao) + df_p['Step_Up'].map(mapa_funcao) + df_p['Step_Down'].map(mapa_funcao)) / 3
        
        # --- DASHBOARD VISUAL ---
        tab_evolucao, tab_correlacao = st.tabs(["📈 Evolução Temporal", "🧬 Correlações Clínicas"])
        
        with tab_evolucao:
            st.subheader(f"Evolução de {p_sel}")
            st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])
            st.caption("Linha Vermelha: Dor | Linha Azul: Função")

        with tab_correlacao:
            st.subheader("Análise Multi-Fatorial")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("##### 😴 Impacto do Sono na Dor")
                # Gráfico de barras: Sono vs Média de Dor
                sono_pain = df_p.groupby('Sono')['Dor'].mean().reset_index()
                chart_sono = alt.Chart(sono_pain).mark_bar(color='#008091').encode(
                    x=alt.X('Sono', sort=['Ruim', 'Regular', 'Bom']),
                    y='Dor',
                    tooltip=['Sono', 'Dor']
                ).properties(height=300)
                st.altair_chart(chart_sono, use_container_width=True)
                st.caption("Média de dor para cada qualidade de sono.")

            with col_b:
                st.markdown("##### 🪑 Postura vs Função")
                # Gráfico de barras: Postura vs Score Funcional
                postura_func = df_p.groupby('Postura')['Score_Funcao'].mean().reset_index()
                chart_postura = alt.Chart(postura_func).mark_bar(color='#008091').encode(
                    x=alt.X('Postura', sort=['Sentado', 'Equilibrado', 'Em pé']),
                    y='Score_Funcao',
                    tooltip=['Postura', 'Score_Funcao']
                ).properties(height=300)
                st.altair_chart(chart_postura, use_container_width=True)
                st.caption("Quanto a postura afeta a capacidade de agachar/subir degraus.")

            st.write("---")
            st.markdown("#### 💡 Insights de Cruzamento de Dados")
            
            # Lógica de correlação automática
            worst_sleep_pain = df_p[df_p['Sono'] == 'Ruim']['Dor'].mean()
            best_sleep_pain = df_p[df_p['Sono'] == 'Bom']['Dor'].mean()
            
            if worst_sleep_pain > best_sleep_pain + 2:
                st.warning(f"🔎 **Fator Biopsicossocial Detectado:** {p_sel} apresenta dor significativamente maior após noites de sono ruim. Priorizar higiene do sono.")
            
            sitting_function = df_p[df_p['Postura'] == 'Sentado']['Score_Funcao'].mean()
            standing_function = df_p[df_p['Postura'] == 'Em pé']['Score_Funcao'].mean()
            
            if sitting_function < standing_function - 2:
                st.info(f"🔎 **Fator Mecânico Detectado:** A função cai quando o paciente passa o dia sentado. Orientar pausas ativas a cada 50 minutos.")

    else:
        st.info("Aguardando preenchimento para gerar correlações.")
