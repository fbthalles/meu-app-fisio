import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="GENUA Clinical Support", layout="wide", page_icon="🏥")

# CSS GENUA Premium
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
    menu = st.radio("NAVEGAÇÃO", ["Check-in Paciente 📝", "Painel Analítico 📊"])

# --- MÓDULO 1: CHECK-IN ---
if "Check-in" in menu:
    st.header("Entrada de Dados Clínicos")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: Gabriel Medeiros")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Dor agora (EVA 0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with col2:
            st.markdown("#### 🏋️ Testes Funcionais")
            agachar = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_up = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            step_down = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])

        if st.form_submit_button("REGISTRAR NO SISTEMA"):
            if paciente:
                df_h = conn.read(ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Sono": sono, "Postura": postura, "Agachamento": agachar, "Step_Up": step_up, "Step_Down": step_down}])
                conn.update(data=pd.concat([df_h, nova_linha], ignore_index=True))
                st.success("Dados registrados com sucesso!")
                st.balloons()

# --- MÓDULO 2: PAINEL ANALÍTICO (RACIOCÍNIO CLÍNICO EXPANDIDO) ---
else:
    st.header("📊 Painel de Decisão Baseada em Evidências")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        df['Paciente'] = df['Paciente'].str.strip()
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())

        # Busca História na aba Cadastro
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            df_cad['Nome'] = df_cad['Nome'].str.strip()
            historia_txt = df_cad[df_cad['Nome'] == p_sel]['Historia'].values[0]
            st.info(f"📝 **História Clínica:** {historia_txt}")
        except:
            st.warning("⚠️ História não encontrada na aba 'Cadastro'.")

        df_p = df[df['Paciente'] == p_sel].copy()
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        
        ultima = df_p.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Dor Atual", f"{ultima['Dor']}/10")
        c2.metric("Capacidade Funcional", f"{ultima['Score_Funcao']:.1f}/10")
        c3.metric("Eficiência de Carga", f"{(ultima['Score_Funcao']*10):.0f}%")

        st.write("---")
        st.subheader("🧬 Evolução: Dor vs Função")
        st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])

        # --- SEÇÃO DE RACIOCÍNIO CLÍNICO EXPANDIDA ---
        st.write("---")
        st.subheader("💡 Suporte à Decisão Clínica (PBE)")
        
        col_mecanico, col_bio = st.columns(2)
        
        with col_mecanico:
            st.markdown("##### 📏 Análise de Guidelines (JOSPT/AAOS)")
            
            # Caso 1: Déficit Excêntrico (Step Down)
            if "Dor" in ultima['Step_Down'] or "Incapaz" in ultima['Step_Down']:
                st.warning("**Foco: Controle Motor Excêntrico.** Dor no Step Down indica necessidade de fortalecimento proximal (quadril) e controle de valgo dinâmico.")
            
            # Caso 2: Alta Funcionalidade (LCA/Retorno)
            if ultima['Score_Funcao'] >= 9 and ultima['Dor'] <= 1:
                st.success("**Critério de Retorno ao Esporte:** Paciente atinge níveis de simetria funcional sugeridos para retorno seguro. Iniciar testes de LSI (Limb Symmetry Index).")
            
            # Caso 3: Osteoartrite Estável
            if "Neusa" in p_sel or (ultima['Dor'] >= 4 and ultima['Dor'] <= 6):
                st.info("**Manejo de OA:** Quadro estável. Priorizar exercícios aeróbicos de baixo impacto e fortalecimento progressivo de quadríceps.")

        with col_bio:
            st.markdown("##### 🧠 Fatores Biopsicossociais (OARSI)")
            
            # Caso 4: Sensibilização por Sono
            if ultima['Sono'] == "Ruim" and ultima['Dor'] >= 6:
                st.error("**Alerta de Sensibilização Central:** Sono ruim correlacionado a dor alta. Priorizar educação em dor e evitar excesso de carga mecânica hoje.")
            
            # Caso 5: Impacto Postural (Sinal do Cinema)
            if ultima['Postura'] == "Sentado" and ultima['Dor'] > 5:
                st.warning("**Fator Postural Detectado:** Piora da dor correlacionada à postura sentada prolongada. Prescrever pausas ativas e exercícios de extensão.")
                
            # Caso 6: Janela de Oportunidade
            if ultima['Sono'] == "Bom" and ultima['Dor'] <= 3:
                st.success("**Janela de Carga:** Baixa irritabilidade e sono restaurador. Momento ideal para progressão de carga e exercícios desafiadores.")

        st.write("---")
        resumo_zen = f"Evolução {p_sel}: Dor {ultima['Dor']}/10, Função {ultima['Score_Funcao']:.1f}/10. Predomínio de postura {ultima['Postura']} e sono {ultima['Sono']}."
        st.text_area("Copie para o ZenFisio:", value=resumo_zen)

    else:
        st.info("Aguardando dados.")
