import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="KneeTech Dashboard", layout="wide")

# Conexão com o Google Sheets
# No Streamlit Cloud, você colará o link da planilha nas 'Secrets'
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🏥 KneeTech: Evolução Clínica")

menu = st.sidebar.selectbox("Menu", ["Check-in Paciente", "Painel do Fisioterapeuta"])

if menu == "Check-in Paciente":
    st.header("Bom dia! Como você está hoje?")
    
    with st.form(key="checkin_form"):
        paciente = st.text_input("Nome do Paciente")
        col1, col2 = st.columns(2)
        
        with col1:
            dor = st.select_slider("Nível de Dor (0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)

        with col2:
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        submit_button = st.form_submit_button(label="Enviar Check-in")

        if submit_button:
            if paciente:
                # Cria a linha de dados
                novo_dado = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Paciente": paciente,
                    "Dor": dor,
                    "Sono": sono,
                    "Postura": postura,
                    "Agachamento": agachar,
                    "Step_Up": step_up,
                    "Step_Down": step_down
                }])
                
                # Lê os dados existentes e adiciona o novo
                dados_atuais = conn.read()
                dados_atualizados = pd.concat([dados_atuais, novo_dado], ignore_index=True)
                
                # Salva na planilha
                conn.update(data=dados_atualizados)
                st.success(f"Check-in de {paciente} salvo com sucesso!")
            else:
                st.warning("Por favor, digite o nome do paciente.")

else:
    st.header("Painel de Controle Clínico")
    try:
        df = conn.read()
        st.dataframe(df) # Mostra a tabela de todos os atendimentos
        
        if not df.empty:
            st.subheader("Tendência de Dor por Paciente")
            st.line_chart(df, x="Data", y="Dor")
    except:
        st.info("Ainda não há dados registrados na planilha.")
