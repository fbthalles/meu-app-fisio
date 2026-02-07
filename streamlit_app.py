import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configurações de interface
st.set_page_config(page_title="KneeTech Dashboard", layout="wide", page_icon="🏥")

# Estilo visual moderno
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; height: 3.5em; font-weight: bold; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# Inicialização da conexão
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("⚠️ Erro de conexão. Verifique as 'Secrets' no Streamlit Cloud.")
    st.stop()

st.title("🏥 KneeTech: Inteligência Clínica")

# Menu lateral
menu = st.sidebar.selectbox("Navegação", ["Check-in Paciente", "Painel do Fisioterapeuta"])

# --- MÓDULO 1: CHECK-IN DO PACIENTE ---
if menu == "Check-in Paciente":
    st.header("Bom dia! Vamos registrar sua evolução?")
    
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome completo do paciente")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Estado Geral")
            dor = st.select_slider("Nível de dor no joelho agora (0-10)", options=list(range(11)))
            sono = st.radio("Como foi seu sono hoje?", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura predominante hoje", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)

        with col2:
            st.subheader("Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up (Subir degrau)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down (Descer degrau)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        submit_button = st.form_submit_button(label="ENVIAR CHECK-IN")

        if submit_button:
            if paciente:
                try:
                    # 1. LER DADOS ATUAIS (ttl=0 força a leitura do Google, ignorando o cache)
                    df_historico = conn.read(ttl=0)
                    
                    # 2. LIMPEZA DE SEGURANÇA (Remove linhas totalmente vazias)
                    df_historico = df_historico.dropna(how="all")

                    # 3. PREPARAÇÃO DA NOVA LINHA
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
                    
                    # 4. CONCATENAR E SALVAR
                    df_final = pd.concat([df_historico, nova_entrada], ignore_index=True)
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
        df = conn.read(ttl=0)
        df = df.dropna(how="all")
        
        if df.empty:
            st.info("Aguardando os primeiros registros de pacientes.")
        else:
            paciente_selecionado = st.selectbox("Selecione o paciente", df['Paciente'].unique())
            df_p = df[df['Paciente'] == paciente_selecionado].copy()
            
            # Gráfico de evolução de dor
            st.subheader(f"Evolução da Dor: {paciente_selecionado}")
            st.line_chart(df_p.set_index('Data')['Dor'])
            
            # Métricas da última sessão
            ultima = df_p.iloc[-1]
            st.divider()
            st.subheader("Último Check-in")
            c1, c2, c3 = st.columns(3)
            c1.metric("Dor", f"{ultima['Dor']}/10")
            c2.metric("Sono", ultima['Sono'])
            c3.metric("Postura", ultima['Postura'])

            # Alertas baseados em evidência (PhysioTech)
            if int(ultima['Dor']) >= 7 and ultima['Sono'] == "Ruim":
                st.error("🚨 Alerta: Possível sensibilização central detectada.")

    except Exception as e:
        st.error(f"Erro ao carregar o painel: {e}")
