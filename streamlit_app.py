import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="GENUA Clinical Support", layout="wide", page_icon="🏥")

# CSS "Blindado": Garante contraste no tablet e usa as cores da GENUA
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
    .stTextInput>div>div>input { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO COM BANCO DE DADOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- 3. BARRA LATERAL (LOGO E NAVEGAÇÃO) ---
with st.sidebar:
    try:
        logo = Image.open("Ativo-1.png")
        st.image(logo, use_container_width=True)
    except:
        st.subheader("GENUA Instituto")
    
    st.write("---")
    menu = st.radio("MENU PRINCIPAL", ["Check-in Paciente 📝", "Painel Analítico 📊"])
    st.write("---")
    st.caption("v2.0 - Clinical Decision Support")

# --- MÓDULO 1: CHECK-IN DIÁRIO (NO TABLET) ---
if "Check-in" in menu:
    st.header("Entrada de Dados Clínicos")
    
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: José Silva")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral (Biopsicossocial)")
            dor = st.select_slider("Nível de Dor Atual (EVA 0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono (OARSI)", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante hoje", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)

        with col2:
            st.markdown("#### 🏋️ Testes Funcionais (JOSPT)")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up (Força)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down (Controle)", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("REGISTRAR AVALIAÇÃO"):
            if paciente:
                try:
                    # Lê histórico ignorando cache para evitar sobrescrever dados
                    df_h = conn.read(ttl=0).dropna(how="all")
                    
                    nova_linha = pd.DataFrame([{
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Paciente": paciente,
                        "Dor": int(dor),
                        "Sono": sono,
                        "Postura": postura,
                        "Agachamento": agachar,
                        "Step_Up": step_up,
                        "Step_Down": step_down
                    }])
                    
                    conn.update(data=pd.concat([df_h, nova_linha], ignore_index=True))
                    st.success(f"Check-in de {paciente} concluído!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Por favor, insira o nome do paciente.")

# --- MÓDULO 2: PAINEL ANALÍTICO (RACIOCÍNIO CLÍNICO) ---
else:
    st.header("📊 Inteligência de Dados e Guidelines")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        # Dicionário de Histórias Clínicas dos Pacientes de Teste
        historias = {
            "José Silva": "👨‍🦳 **Caso:** Pós-operatório de LCA (10ª semana). Atleta amador. Foco: Retorno ao esporte e ganho de força explosiva.",
            "Maria Oliveira": "👩‍ **Caso:** Osteoartrite de joelho grau II. Teve um episódio de 'flare-up' (crise de dor) na 6ª semana.",
            "Antônio Santos": "👨‍💼 **Caso:** Dor Patelofemoral Crônica + Sensibilização Central. Quadro influenciado por estresse e privação de sono.",
            "Francisca Costa": "🏃‍♀️ **Caso:** Corredora de rua. Dor leve, mas com déficit de controle motor excêntrico (valgo dinâmico) no Step Down.",
            "Ricardo Biondi": "💻 **Caso:** Programador. Dor mecânica exacerbada pela postura sentada prolongada (Sinal do Cinema)."
        }

        p_sel = st.selectbox("Selecione o Paciente para Análise Detalhada", df['Paciente'].unique())
        
        # Exibição da História Clínica
        st.info(historias.get(p_sel, "📜 Paciente novo. História clínica não registrada."))

        df_p = df[df['Paciente'] == p_sel].copy()
        
        # Processamento PBE (Mapeamento Funcional)
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        
        ultima = df_p.iloc[-1]
        
        # --- SEÇÃO 1: MÉTRICAS ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Atual", f"{ultima['Dor']}/10")
        c2.metric("Capacidade Funcional", f"{ultima['Score_Funcao']:.1f}/10")
        c3.metric("Eficiência de Carga", f"{(ultima['Score_Funcao']*10):.0f}%")

        # --- SEÇÃO 2: GRÁFICO DE CORRELAÇÃO ---
        st.write("---")
        st.subheader("🧬 Cruzamento: Dor (Vermelho) vs Função (Verde)")
        chart_data = df_p.set_index('Data')[['Dor', 'Score_Funcao']]
        st.line_chart(chart_data, color=["#FF4B4B", "#008091"])

        # --- SEÇÃO 3: DASHBOARD DE DIRETRIZES (JOSPT/OARSI) ---
        st.write("---")
        st.subheader("💡 Suporte à Decisão Clínica")
        col_mecanico, col_bio = st.columns(2)
        
        with col_mecanico:
            st.markdown("##### 📏 Fatores Mecânicos (JOSPT)")
            if "Dor" in ultima['Step_Down'] or "Incapaz" in ultima['Step_Down']:
                st.warning("**Déficit Excêntrico:** Dor no Step Down sugere foco em fortalecimento proximal (quadril) e controle de valgo.")
            if ultima['Postura'] == "Sentado" and ultima['Dor'] > 5:
                st.info("**Sobrecarga Estática:** A dor elevada correlacionada à postura sentada indica possível Sinal do Cinema.")

        with col_bio:
            st.markdown("##### 🧠 Fatores Biopsicossociais (OARSI)")
            if ultima['Sono'] == "Ruim" and ultima['Dor'] >= 7:
                st.error("**Alerta de Sensibilização:** Sono ruim correlacionado a dor alta. Recomenda-se modulação de carga e educação em dor.")
            elif ultima['Score_Funcao'] > 8 and ultima['Dor'] <= 2:
                st.success("**Janela de Alta:** Paciente apresenta alta funcionalidade e baixa irritabilidade. Considerar progressão final.")

        # --- SEÇÃO 4: EVOLUÇÃO PARA ZENFISIO ---
        st.write("---")
        resumo_zen = f"Evolução {p_sel}: Dor {ultima['Dor']}/10, Função {ultima['Score_Funcao']:.1f}/10. Sono {ultima['Sono']} e Postura {ultima['Postura']}."
        st.text_area("Copie para o ZenFisio:", value=resumo_zen, height=70)

    else:
        st.info("Aguardando os primeiros dados para gerar os gráficos.")
