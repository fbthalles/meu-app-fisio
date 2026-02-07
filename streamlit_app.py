import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL ---
st.set_page_config(
    page_title="KneeTech Dashboard",
    layout="wide",
    page_icon="🦵",
    initial_sidebar_state="expanded"
)

# CSS Personalizado para dar o visual "PhysioTech"
st.markdown("""
    <style>
    /* Fundo geral mais limpo */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Estilo dos Botões Principais (Azul Profissional) */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        background-color: #0056b3; /* Azul mais sóbrio */
        color: white;
        height: 3.8em;
        font-weight: 600;
        font-size: 16px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #004494;
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
    
    /* Estilo dos Cards de Métricas (Painel do Fisio) */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #0056b3;
    }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        text-align: center;
    }
    
    /* Estilo da Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }
    
    /* Títulos e Cabeçalhos */
    h1, h2, h3 {
        color: #2c3e50;
        font-family: 'Helvetica Neue', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# Conexão
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("⚠️ Erro crítico de conexão. Verifique as Secrets.")
    st.stop()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🦵 KneeTech")
    st.caption("Inteligência em Fisioterapia")
    st.write("---")
    menu = st.radio("Navegação", ["Check-in Paciente 📝", "Painel do Fisioterapeuta 📊"])
    st.write("---")
    st.info("💡 **Dica:** Preencha diariamente para melhores resultados.")

# --- MÓDULO 1: CHECK-IN DO PACIENTE (VISUAL GAMIFICADO) ---
if "Check-in Paciente" in menu:
    st.title("Bom dia! Vamos registrar sua evolução? 🚀")
    
    # Barra de progresso visual
    progress_bar = st.progress(0)
    st.caption("Etapa 1 de 2: Identificação e Estado Geral")

    with st.form(key="checkin_form", clear_on_submit=True):
        st.subheader("👤 Quem é você?")
        paciente = st.text_input("Nome completo", placeholder="Ex: João Silva")
        
        st.write("---")
        st.subheader("🌡️ Como você está hoje?")
        
        with st.container():
            col1, col2 = st.columns(2, gap="large")
            with col1:
                st.markdown("##### Nível de Dor no Joelho")
                # Slider com emoji visual
                dor = st.select_slider(
                    "Arraste para selecionar (0 = Sem dor, 10 = Pior dor)",
                    options=list(range(11)),
                    value=3,
                    format_func=lambda x: f"{x} {'😀' if x<4 else '😐' if x<7 else '😫'}"
                )
            with col2:
                st.markdown("##### Qualidade do Sono e Postura")
                sono = st.radio("Como você dormiu?", ["😴 Ruim/Pouco", "😐 Regular", "😃 Bom/Muito bem"])
                postura = st.radio("Postura predominante ontem?", ["🪑 Muito tempo sentado", "⚖️ Equilibrado", "🧍 Muito tempo em pé"])

        st.write("---")
        st.caption("Etapa 2 de 2: Testes Funcionais Rápidos")
        progress_bar.progress(50)
        
        st.subheader("🏋️‍♀️ Testes Funcionais (Sentiu dor ao fazer?)")
        with st.container():
            c_aga, c_up, c_down = st.columns(3, gap="medium")
            with c_aga:
                st.markdown("**1. Agachamento**")
                agachar = st.selectbox("Select:", ["✅ Sem Dor", "⚠️ Dor Leve", "🟠 Dor Moderada", "❌ Incapaz"], key="s1")
            with c_up:
                st.markdown("**2. Step Up (Subir)**")
                step_up = st.selectbox("Select:", ["✅ Sem Dor", "⚠️ Dor Leve", "🟠 Dor Moderada", "❌ Incapaz"], key="s2")
            with c_down:
                st.markdown("**3. Step Down (Descer)**")
                step_down = st.selectbox("Select:", ["✅ Sem Dor", "⚠️ Dor Leve", "🟠 Dor Moderada", "❌ Incapaz"], key="s3")

        st.write("")
        submit_button = st.form_submit_button(label="✅ ENVIAR CHECK-IN")

        if submit_button:
            if paciente:
                progress_bar.progress(100)
                with st.spinner("Salvando seus dados..."):
                    try:
                        df_historico = conn.read(ttl=0).dropna(how="all")
                        
                        # Limpando os emojis dos dados antes de salvar
                        sono_limpo = sono.split(" ", 1)[1]
                        postura_limpa = postura.split(" ", 1)[1]
                        agachar_limpo = agachar.split(" ", 1)[1]
                        step_up_limpo = step_up.split(" ", 1)[1]
                        step_down_limpo = step_down.split(" ", 1)[1]

                        nova_entrada = pd.DataFrame([{
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Paciente": paciente,
                            "Dor": int(dor),
                            "Sono": sono_limpo,
                            "Postura": postura_limpa,
                            "Agachamento": agachar_limpo,
                            "Step_Up": step_up_limpo,
                            "Step_Down": step_down_limpo
                        }])
                        
                        df_final = pd.concat([df_historico, nova_entrada], ignore_index=True)
                        conn.update(data=df_final)
                        time.sleep(1) # Pausa dramática para sensação de processamento
                        st.success(f"✨ Excelente, {paciente}! Dados salvos com sucesso.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("⚠️ Por favor, preencha o seu nome antes de enviar.")

# --- MÓDULO 2: PAINEL DO FISIOTERAPEUTA (VISUAL PROFISSIONAL) ---
else:
    st.title("📊 Central de Inteligência Clínica")
    st.caption("Visão geral e insights baseados em evidência.")
    
    try:
        with st.spinner("Carregando dados dos pacientes..."):
            df = conn.read(ttl=0).dropna(how="all")
        
        if df.empty:
            st.info("📭 Aguardando os primeiros registros. Envie o link para seus pacientes!")
        else:
            st.write("---")
            col_sel, col_vazio = st.columns([2,1])
            with col_sel:
                paciente_sel = st.selectbox("🔎 Selecione o Paciente para Análise Detalhada:", df['Paciente'].unique())
            
            df_p = df[df['Paciente'] == paciente_sel].copy()
            ultima = df_p.iloc[-1]

            # Seção de Métricas Principais com Cards Visuais
            st.subheader(f"📌 Status Atual: {paciente_sel}")
            
            met1, met2, met3 = st.columns(3, gap="medium")
            with met1:
                st.metric("Nível de Dor (0-10)", f"{ultima['Dor']}", help="Escala Visual Analógica")
            with met2:
                # Adiciona emoji baseado no texto do dado
                sono_emoji = "😴" if "Ruim" in ultima['Sono'] else "😐" if "Regular" in ultima['Sono'] else "😃"
                st.metric("Qualidade do Sono", f"{sono_emoji} {ultima['Sono']}")
            with met3:
                postura_emoji = "🪑" if "sentado" in ultima['Postura'].lower() else "🧍" if "em pé" in ultima['Postura'].lower() else "⚖️"
                st.metric("Postura Predominante", f"{postura_emoji} {ultima['Postura']}")

            # Seção de Insights Clínicos (Alertas Visuais)
            st.write("---")
            st.subheader("🧠 Insights Clínicos (PBE)")
            
            col_alerts, col_charts = st.columns([2, 3], gap="large")
            
            with col_alerts:
                st.caption("Alertas automáticos baseados em regras de decisão.")
                alertas_ativos = 0
                
                if int(ultima['Dor']) >= 7 and "Ruim" in ultima['Sono']:
                    st.error("🚨 **Alerta de Sensibilização Central:** Dor alta (>7) associada a sono ruim. Considere estratégias de modulação de dor e higiene do sono antes de carga alta.")
                    alertas_ativos += 1
                    
                if "sentado" in ultima['Postura'].lower() and ("Dor" in ultima['Agachamento'] or "Incapaz" in ultima['Agachamento']):
                    st.warning("⚠️ **Risco de Sobrecarga Patelofemoral:** Muito tempo sentado pode estar gerando 'Sinal do Cinema' e prejudicando o agachamento. Orientar pausas ativas.")
                    alertas_ativos += 1
                    
                if "Incapaz" in [ultima['Step_Up'], ultima['Step_Down']]:
                    st.info("ℹ️ **Déficit Funcional Importante:** Incapacidade em degraus sugere déficit de controle motor ou força excêntrica de quadríceps. Foco da sessão.")
                    alertas_ativos += 1
                    
                if alertas_ativos == 0:
                    st.success("✅ **Nenhum alerta crítico hoje.** Paciente estável segundo os parâmetros monitorados.")

            with col_charts:
                st.subheader("📈 Evolução Visual")
                tab1, tab2 = st.tabs(["Tendência da Dor", "Capacidade Funcional"])
                
                with tab1:
                    st.line_chart(df_p.set_index('Data')['Dor'], color="#d62728")
                    st.caption("Histórico de dor (Vermelho = Alerta)")

                with tab2:
                    # Mapeamento para gráfico visual
                    mapa_funcao = {"Sem Dor": 3, "Dor Leve": 2, "Dor Moderada": 1, "Incapaz": 0}
                    df_p['Função_Geral'] = (df_p['Agachamento'].map(mapa_funcao) + df_p['Step_Down'].map(mapa_funcao)) / 2
                    st.area_chart(df_p.set_index('Data')['Função_Geral'], color="#2ca02c")
                    st.caption("Índice Funcional Combinado (Quanto mais alto, melhor)")

    except Exception as e:
        st.error(f"Erro no painel: {e}")
