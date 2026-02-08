import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt
import numpy as np
from fpdf import FPDF
import base64

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="GENUA Clinical Intelligence", layout="wide", page_icon="🏥")

# CSS Customizado para identidade visual e contraste no tablet
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

def create_pdf(p_name, hist, dor_atual, func_atual, ikdc_atual, previsao_alta):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho com Logo (se existir o arquivo)
    try:
        pdf.image("Ativo-1.png", x=10, y=8, w=33)
    except:
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"RELATÓRIO DE EVOLUÇÃO CLÍNICA - {p_name.upper()}", ln=True, align='C')
    pdf.ln(10)
    
    # História Pregressa
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "História Clínica:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, hist)
    pdf.ln(5)
    
    # Métricas Atuais
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Métricas de Desempenho (PBE):", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"- Dor Atual (EVA): {dor_atual}/10", ln=True)
    pdf.cell(0, 8, f"- Capacidade Funcional: {func_atual:.1f}/10", ln=True)
    pdf.cell(0, 8, f"- Score IKDC: {ikdc_atual if ikdc_atual != 'N/A' else 'Pendente'}", ln=True)
    pdf.cell(0, 8, f"- Previsão Estimada de Alta: {previsao_alta}", ln=True)
    pdf.ln(10)
    
    # Nota Técnica
    pdf.set_font("Arial", 'I', 10)
    resumo = "Este relatório utiliza diretrizes da JOSPT e OARSI para análise de progressão de carga e função."
    pdf.multi_cell(0, 8, resumo)
    
    return pdf.output()

# --- 2. CONEXÃO COM GOOGLE SHEETS ---
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
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação IKDC (Mensal) 📋", "Painel Analítico 📊"])
    st.write("---")
    st.caption("Fisioterapia Baseada em Evidências")

# --- MÓDULO 1: CHECK-IN DIÁRIO ---
if "Check-in" in menu:
    st.header("Entrada de Dados Diários")
    with st.form(key="checkin_form", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente", placeholder="Ex: Jonas Hugo")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌡️ Estado Geral")
            dor = st.select_slider("Dor agora (EVA 0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante hoje", ["Sentado", "Em pé"], horizontal=True)
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
                st.success(f"Check-in de {paciente} salvo!")
                st.balloons()

# --- MÓDULO 2: AVALIAÇÃO IKDC (CIENTÍFICA) ---
elif "Avaliação IKDC" in menu:
    st.header("📋 Questionário IKDC (Score Funcional)")
    with st.form(key="ikdc_form", clear_on_submit=True):
        paciente_ikdc = st.text_input("Nome do Paciente")
        
        st.markdown("##### 1. Nível mais alto de atividade sem dor?")
        p1 = st.selectbox("Atividade", ["Incapaz", "Atividade Leve", "Atividade Moderada", "Atividade Intensa"])
        
        st.markdown("##### 2. Dificuldade para subir/descer escadas?")
        p2 = st.select_slider("Escadas", options=["Extrema", "Muita", "Moderada", "Leve", "Nenhuma"])
        
        st.markdown("##### 3. Dificuldade para agachar?")
        p3 = st.select_slider("Agachar", options=["Extrema", "Muita", "Moderada", "Leve", "Nenhuma"])
        
        st.markdown("##### 4. Nota global da função do joelho (0-100)?")
        p4 = st.slider("Nota", 0, 100, 50)

        if st.form_submit_button("SALVAR SCORE CIENTÍFICO"):
            if paciente_ikdc:
                mapa_ikdc = {"Incapaz": 0, "Atividade Leve": 33, "Atividade Moderada": 66, "Atividade Intensa": 100,
                             "Extrema": 0, "Muita": 25, "Moderada": 50, "Leve": 75, "Nenhuma": 100}
                score = (mapa_ikdc.get(p1, 0) + mapa_ikdc.get(p2, 0) + mapa_ikdc.get(p3, 0) + p4) / 4
                
                try:
                    df_ikdc = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
                    novo_reg = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": paciente_ikdc.strip(), "Score_IKDC": score}])
                    conn.update(worksheet="IKDC", data=pd.concat([df_ikdc, novo_reg], ignore_index=True))
                    st.success(f"Score de {score:.1f} registrado!")
                except:
                    st.error("Erro: Crie a aba 'IKDC' no Sheets (Data, Paciente, Score_IKDC).")

# --- MÓDULO 3: PAINEL ANALÍTICO (O "CÉREBRO" DO APP) ---
else:
    st.header("📊 Painel de Decisão Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        df['Paciente'] = df['Paciente'].str.strip()
        p_sel = st.selectbox("Selecione o Paciente para Análise", df['Paciente'].unique())

        # 1. História Clínica (Aba Cadastro)
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            df_cad['Nome'] = df_cad['Nome'].str.strip()
            historia = df_cad[df_cad['Nome'] == p_sel]['Historia'].values[0]
            st.info(f"📝 **História Clínica:** {historia}")
        except:
            st.warning("História não cadastrada na aba 'Cadastro'.")

        # 2. Processamento de Dados
        df_p = df[df['Paciente'] == p_sel].copy()
        mapa_f = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa_f) + df_p['Step_Up'].map(mapa_f) + df_p['Step_Down'].map(mapa_f)) / 3
        ultima = df_p.iloc[-1]

        # --- NOVO: MOTOR DE PREVISÃO DE ALTA (IA/ESTATÍSTICA) ---
        st.write("---")
        st.subheader("🔮 Previsão de Alta (Forecasting GENUA)")
        
        try:
            # Prepara dados para regressão (Dias x Função)
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            X = df_p['Dias'].values
            y = df_p['Score_Funcao'].values

            # Calcula a linha de tendência (y = ax + b)
            z = np.polyfit(X, y, 1)
            p = np.poly1d(z)
            
            # Projeta quando o Score_Funcao atingirá 9.0 (90%)
            # 9.0 = z[0] * dia_alvo + z[1]  => dia_alvo = (9.0 - z[1]) / z[0]
            if z[0] > 0:  # Só calcula se houver melhora
                dia_alvo = (9.0 - z[1]) / z[0]
                data_previsao = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
                semanas_restantes = max(0, (data_previsao - datetime.now()).days // 7)
                
                col_ia1, col_ia2 = st.columns(2)
                with col_ia1:
                    st.metric("Previsão de Alta", data_previsao.strftime("%d/%m/%Y"))
                with col_ia2:
                    st.metric("Semanas Estimadas", f"{semanas_restantes} sem")
                
                st.info(f"💡 **Análise Predictiva:** Mantendo o ritmo atual de evolução, o paciente atingirá 90% de capacidade funcional em aproximadamente {semanas_restantes} semanas.")
            else:
                st.warning("⚠️ **Alerta de Platô:** A velocidade de melhora atual é nula ou negativa. Ajuste a carga ou investigue fatores biopsicossociais.")
        
        except Exception as e:
            st.write("Dados insuficientes para gerar previsão de alta.")

        # 3. Métricas Principais
        m1, m2, m3 = st.columns(3)
        m1.metric("Dor Atual", f"{ultima['Dor']}/10")
        
        try:
            df_ikdc_all = conn.read(worksheet="IKDC", ttl=0)
            historico_ikdc = df_ikdc_all[df_ikdc_all['Paciente'].str.strip() == p_sel]
            ultimo_score = historico_ikdc['Score_IKDC'].values[-1]
            
            # --- NOVO: LÓGICA DE PARECER CLÍNICO IKDC ---
            if ultimo_score < 40:
                parecer_ikdc = "🔴 Severo: Foco em modulação de dor."
            elif ultimo_score < 65:
                parecer_ikdc = "🟡 Regular: Evolução de carga funcional."
            elif ultimo_score < 85:
                parecer_ikdc = "🟢 Bom: Iniciar pliometria/agilidade."
            else:
                parecer_ikdc = "🏆 Excelente: Critério de Alta/Esporte."
            
            m2.metric("Score IKDC", f"{ultimo_score:.1f}/100", help=parecer_ikdc)
            st.write(f"**Parecer Funcional:** {parecer_ikdc}")

            # Lógica de Comparação (MCID)
            if len(historico_ikdc) > 1:
                evolucao = ultimo_score - historico_ikdc['Score_IKDC'].values[-2]
                if evolucao >= 11.5:
                    st.success(f"📈 Melhora significativa! (+{evolucao:.1f} pts)")
                elif evolucao < 0:
                    st.error(f"📉 Alerta: Queda de função. ({evolucao:.1f} pts)")

        except:
            m2.metric("Score IKDC", "N/A")

        # 4. Gráficos de Evolução e Correlação
        st.write("---")
        t1, t2 = st.tabs(["📈 Evolução Temporal", "🧬 Correlações (Sono/Postura)"])
        
        with t1:
            st.subheader("Evolução: Dor (Vermelho) vs Função (Azul)")
            chart_data = df_p.set_index('Data')[['Dor', 'Score_Funcao']]
            st.line_chart(chart_data, color=["#FF4B4B", "#008091"])

        with t2:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("##### 😴 Sono vs Dor")
                sono_pain = df_p.groupby('Sono')['Dor'].mean().reset_index()
                st.altair_chart(alt.Chart(sono_pain).mark_bar(color='#008091').encode(x=alt.X('Sono', sort=['Ruim', 'Regular', 'Bom']), y='Dor'), use_container_width=True)
            with col_b:
                st.markdown("##### 🪑 Postura vs Função")
                post_func = df_p.groupby('Postura')['Score_Funcao'].mean().reset_index()
                st.altair_chart(alt.Chart(post_func).mark_bar(color='#008091').encode(x='Postura', y='Score_Funcao'), use_container_width=True)

        # 5. Raciocínio Clínico (Guidelines)
        
        st.write("---")
        st.subheader("💡 Suporte à Decisão Baseada em Evidências")
        c_m, c_b = st.columns(2)
        with c_m:
            st.markdown("**Análise Mecânica (JOSPT)**")
            if "Dor" in ultima['Step_Down'] or "Incapaz" in ultima['Step_Down']:
                st.warning("⚠️ **Déficit Excêntrico:** Dor no Step Down sugere necessidade de foco em controle de glúteo médio e quadril.")
            if ultima['Postura'] == "Sentado" and ultima['Dor'] > 4:
                st.info("ℹ️ **Sinal do Cinema:** Correlação entre postura sentada e dor sugere irritabilidade patelofemoral.")
        with c_b:
            st.markdown("**Análise Biopsicossocial (OARSI)**")
            if ultima['Sono'] == "Ruim":
                st.error("🚨 **Alerta de Sensibilização:** Sono ruim detectado. Reduzir carga e focar em educação em dor nesta sessão.")
            elif ultima['Score_Funcao'] > 8:
                st.success("✅ **Janela de Alta:** Alta funcionalidade detectada. Iniciar protocolos de retorno ao esporte.")

        # 6. Resumo ZenFisio
        st.write("---")
        texto_zen = f"Evolução {p_sel}: Dor {ultima['Dor']}/10, Score Funcional {ultima['Score_Funcao']:.1f}/10. Sono {ultima['Sono']} e Postura {ultima['Postura']}."
        st.text_area("Copie para o ZenFisio:", value=texto_zen)

    else:
        st.info("Aguardando dados para análise.")

# --- NOVO: BOTÃO DE EXPORTAÇÃO DE LAUDO ---
        st.write("---")
        st.subheader("📄 Relatório para Médico/Convênio")
        
        # Preparar dados para o PDF
        previsao_txt = data_previsao.strftime("%d/%m/%Y") if 'data_previsao' in locals() else "Em análise"
        ikdc_val = f"{ultimo_score:.1f}/100" if 'ultimo_score' in locals() else "N/A"
        
        pdf_bytes = create_pdf(p_sel, historia, ultima['Dor'], ultima['Score_Funcao'], ikdc_val, previsao_txt)
        
        st.download_button(
            label="📥 BAIXAR RELATÓRIO PDF",
            data=pdf_bytes,
            file_name=f"Relatorio_GENUA_{p_sel}.pdf",
            mime="application/pdf",
        )
