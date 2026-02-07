import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="KneeTech Dashboard", layout="wide", page_icon="🏥")

# Estilo para deixar os cards e botões com cara de app profissional
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; height: 3em; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# Tenta estabelecer a conexão com o Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro na conexão com o Banco de Dados. Verifique as 'Secrets' no painel do Streamlit.")
    st.stop()

st.title("🏥 KneeTech: Inteligência em Fisioterapia")

# Navegação lateral
menu = st.sidebar.selectbox("Navegação", ["Check-in Paciente", "Painel do Fisioterapeuta"])

# --- MÓDULO 1: CHECK-IN DO PACIENTE ---
if menu == "Check-in Paciente":
    st.header("Bom dia! Vamos registrar sua evolução?")
    
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do paciente")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Estado Geral")
            dor = st.select_slider("Nível de dor no joelho (0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do sono hoje", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura predominante no dia", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)

        with col2:
            st.subheader("Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up (Subir degrau)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down (Descer degrau)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        submit_button = st.form_submit_button(label="Enviar Dados")

        if submit_button:
            if paciente:
                try:
                    # Coleta os dados em um DataFrame
                    nova_entrada = pd.DataFrame([{
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Paciente": paciente,
                        "Dor": int(dor),
                        "Sono": sono,
                        "Postura": postura,
                        "Agachamento": agachar,
                        "Step_Up": step_up,
                        "Step_Down": step_down
                    }])
                    
                    # Lê os dados atuais para não sobrescrever o histórico
                    df_historico = conn.read()
                    df_final = pd.concat([df_historico, nova_entrada], ignore_index=True)
                    
                    # Atualiza a planilha
                    conn.update(data=df_final)
                    
                    st.success(f"Excelente, {paciente}! Dados salvos com sucesso.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Por favor, preencha o nome do paciente.")

# --- MÓDULO 2: PAINEL DO FISIOTERAPEUTA ---
else:
    st.header("🔍 Central de Evolução Clínica")
    
    try:
        df = conn.read()
        
        if df.empty:
            st.info("Ainda não há dados registrados.")
        else:
            paciente_sel = st.selectbox("Selecione o paciente", df['Paciente'].unique())
            df_p = df[df['Paciente'] == paciente_sel].copy()
            
            # Formatação de métricas e alertas baseados em evidência
            st.subheader(f"Status Atual: {paciente_sel}")
            ultima = df_p.iloc[-1]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Dor", f"{ultima['Dor']}/10")
            m2.metric("Sono", ultima['Sono'])
            m3.metric("Postura", ultima['Postura'])
            
            st.divider()
            # Lógica clínica automática
            if int(ultima['Dor']) >= 7 and ultima['Sono'] == "Ruim":
                st.error("🚨 **Alerta de Sensibilização:** Dor alta e sono ruim. Reduzir carga e focar em analgesia hoje.")
            
            st.subheader("Gráfico de Dor")
            st.line_chart(df_p.set_index('Data')['Dor'])
            
    except Exception as e:
        st.error(f"Erro ao carregar o painel: {e}")

# No momento de criar o DataFrame, garanta que os nomes sejam estes:
nova_linha = pd.DataFrame([{
    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
    "Paciente": paciente,
    "Dor": int(dor),
    "Sono": sono,
    "Postura": postura,
    "Agachamento": agachar,
    "Step_Up": step_up,
    "Step_Down": step_down  # Verifique se no formulário a variável é 'step_down'
}])


if submit_button:
            if paciente:
                try:
                    # 1. LER OS DADOS MAIS RECENTES (ttl=0 evita o cache)
                    df_historico = conn.read(ttl=0)
                    
                    # 2. PREPARAR A NOVA LINHA (Nomes de colunas idênticos aos da planilha)
                    nova_entrada = pd.DataFrame([{
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Paciente": paciente,
                        "Dor": int(dor),
                        "Sono": sono,
                        "Postura": postura,
                        "Agachamento": agachar,
                        "Step_Up": step_up,
                        "Step_Down": step_down # Sem o ponto final aqui!
                    }])
                    
                    # 3. JUNTAR E ATUALIZAR
                    df_final = pd.concat([df_historico, nova_entrada], ignore_index=True)
                    conn.update(data=df_final)
                    
                    st.success(f"Excelente, {paciente}! Dados salvos.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
