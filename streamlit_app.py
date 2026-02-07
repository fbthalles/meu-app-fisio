import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="GENUA - Intelligence", layout="wide", page_icon="🦵")

# --- 2. CSS "GENUA PREMIUM" (Blindado contra fundo branco) ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #1f1f1f !important; }
    h1, h2, h3, h4, p, label, .stMarkdown { color: #008091 !important; }
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

# --- 3. CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Erro de conexão.")
    st.stop()

# --- 4. BARRA LATERAL (LOGO) ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, use_container_width=True)
    except:
        st.subheader("GENUA Instituto")
    st.write("---")
    menu = st.radio("MENU", ["Check-in Paciente 📝", "Painel do Fisioterapeuta 📊"])

# --- MÓDULO 1: CHECK-IN (IGUAL AO ANTERIOR) ---
if "Check-in" in menu:
    st.header("Avaliação Diária de Evolução")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome Completo do Paciente", placeholder="Ex: Jonas Hugo")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Nível de dor agora (0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura de hoje", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("ENVIAR PARA A PLANILHA"):
            if paciente:
                df_h = conn.read(ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente, "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
                df_f = pd.concat([df_h, nova_linha], ignore_index=True)
                conn.update(data=df_f)
                st.success(f"Check-in de {paciente} concluído!")
                st.balloons()

# --- MÓDULO 2: PAINEL DO FISIOTERAPEUTA (NOVA INTELIGÊNCIA) ---
else:
    st.header("📊 Painel de Controle e Evolução")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente para Análise", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # --- LÓGICA DE CORRELAÇÃO DOR X FUNÇÃO ---
        # Mapeamento para transformar texto em número (0 a 10)
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        
        # Criando o Índice Funcional Genua (Média dos 3 testes)
        df_p['Score_Funcao'] = (
            df_p['Agachamento'].map(mapa) + 
            df_p['Step_Up'].map(mapa) + 
            df_p['Step_Down'].map(mapa)
        ) / 3
        
        # Invertendo a dor para o gráfico de correlação (para visualização de "melhora")
        # Mas vamos plotar a dor real para você ver o cruzamento
        
        st.subheader(f"Análise Biomecânica: {p_sel}")
        
        # Métricas de Capacidade
        c1, c2, c3 = st.columns(3)
        ultima_dor = df_p.iloc[-1]['Dor']
        ultima_funcao = df_p.iloc[-1]['Score_Funcao']
        
        c1.metric("Dor Atual", f"{ultima_dor}/10", delta=int(ultima_dor - df_p.iloc[-2]['Dor']) if len(df_p)>1 else 0, delta_color="inverse")
        c2.metric("Capacidade Funcional", f"{ultima_funcao:.1f}/10")
        
        # Cálculo de Eficiência (O quanto a dor está limitando a função)
        eficiencia = (ultima_funcao * 10) # Transforma em %
        c3.metric("Eficiência de Carga", f"{eficiencia:.0f}%")

        st.write("---")
        st.markdown("### 📉 Correlação: Dor (Vermelho) vs Função (Verde)")
        st.caption("O objetivo clínico é ver a linha verde subir e a vermelha descer.")
        
        # Preparando dados para o gráfico comparativo
        chart_data = df_p[['Data', 'Dor', 'Score_Funcao']].copy()
        chart_data = chart_data.set_index('Data')
        
        # Gráfico de Linhas Comparativo
        st.line_chart(chart_data, color=["#FF4B4B", "#008091"]) # Vermelho para Dor, Azul Genua para Função

        # --- INSIGHTS AUTOMÁTICOS ---
        st.write("---")
        st.subheader("💡 Conclusão Clínica")
        if ultima_dor > 5 and ultima_funcao < 5:
            st.error(f"**Quadro de Alta Irritabilidade:** A dor de {p_sel} está limitando severamente a função. Focar em estratégias de alívio e evitar testes de carga hoje.")
        elif ultima_dor <= 3 and ultima_funcao > 7:
            st.success(f"**Janela de Oportunidade:** Baixa dor e alta função. Ótimo momento para progredir carga e exercícios desafiadores.")
        else:
            st.warning(f"**Quadro Intermediário:** Monitorar a resposta aos exercícios. A função está estável, mas a dor ainda presente.")

    else:
        st.info("Aguardando dados para gerar o Dashboard.")
