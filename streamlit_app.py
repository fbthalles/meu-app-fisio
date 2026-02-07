import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="KneeTech Dashboard", layout="wide")

# Estilo Customizado (Clean & Health)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007bff; color: white; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 KneeTech: Evolução Clínica")

# --- BARRA LATERAL (Navegação) ---
menu = st.sidebar.selectbox("Menu", ["Check-in Paciente", "Painel do Fisioterapeuta"])

# --- MÓDULO 1: CHECK-IN DO PACIENTE ---
if menu == "Check-in Paciente":
    st.header("Bom dia! Como você está hoje?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dor = st.select_slider("Nível de Dor (0-10)", options=list(range(11)))
        sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
        postura = st.radio("Como passou a maior parte do dia?", ["Muito tempo sentado", "Equilibrado", "Muito tempo em pé"], horizontal=True)

    with col2:
        st.subheader("Testes Funcionais (Dor ao realizar)")
        agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
        step_up = st.selectbox("Step Up (Subir degrau)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
        step_down = st.selectbox("Step Down (Descer degrau)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

    if st.button("Enviar Check-in"):
        st.success("Dados enviados com sucesso! Bom treino.")
        # Aqui no futuro conectamos com o Google Sheets

# --- MÓDULO 2: PAINEL DO FISIOTERAPEUTA ---
else:
    st.header("Painel de Controle Clínico")
    
    # Simulação de Alertas baseados em Evidência
    st.subheader("⚠️ Alertas de Decisão (PBE)")
    
    # Lógica de decisão (Baseada no que discutimos)
    # Aqui simulamos um dado que viria do banco
    temp_dor = 8
    temp_sono = "Ruim"
    
    if temp_dor > 7 and temp_sono == "Ruim":
        st.error("🚨 ATENÇÃO: Possível Sensibilização Central. Modular carga e focar em educação em dor hoje.")
    
    col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
    col_metrics1.metric("Evolução ADM", "110°", "+5°")
    col_metrics2.metric("Força Quadríceps", "85%", "+10%")
    col_metrics3.metric("Risco de Queda (TUG)", "11s", "-1s")

    st.divider()
    st.subheader("Histórico de Evolução")
    # Gráfico Simulado
    chart_data = pd.DataFrame({
        'Sessão': [1, 2, 3, 4, 5],
        'Dor': [9, 8, 6, 7, 4],
        'Função': [2, 3, 5, 5, 8]
    })
    st.line_chart(chart_data.set_index('Sessão'))
