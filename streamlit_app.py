import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import numpy as np
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt
import io

# --- 1. FUNÇÃO DE PDF AMPLIADA ---

def create_pdf(p_name, hist, metrics, img_evolucao, img_radar, img_sono):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    try: pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except: pdf.set_font("helvetica", 'B', 16); pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "RELATÓRIO DE INTELIGÊNCIA CLÍNICA", ln=True, align='C')
    pdf.ln(5)

    # Identificação
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, f" PACIENTE: {p_name.upper()}", ln=True, fill=True)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 7, f"Anamnese: {hist}")
    pdf.ln(5)

    # Gráficos: Disposição Vertical
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, " ANÁLISE DE EVOLUÇÃO E FATORES BIOPSICOSSOCIAIS", ln=True, fill=True)
    
    # 1. Evolução Geral
    pdf.image(img_evolucao, x=15, y=pdf.get_y() + 5, w=175)
    pdf.set_y(pdf.get_y() + 85)
    
    # 2. Sono vs Dor (Área)
    pdf.image(img_sono, x=15, y=pdf.get_y(), w=175)
    pdf.set_y(pdf.get_y() + 75)
    
    # 3. Radar Funcional
    pdf.add_page() # Nova página para o Radar e Conclusão
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, " PERFIL DE CAPACIDADE FUNCIONAL", ln=True, fill=True)
    pdf.image(img_radar, x=30, y=pdf.get_y() + 10, w=140)
    
    return bytes(pdf.output())

# --- 2. CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. PAINEL ANALÍTICO ATUALIZADO ---
if st.sidebar.radio("NAVEGAÇÃO", ["Check-in 📝", "IKDC 📋", "Painel Analítico 📊"]) == "Painel Analítico 📊":
    st.header("📊 Clinical Business Intelligence")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # Tratamento de Dados
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        mapa_sono = {"Ruim": 1, "Regular": 5, "Bom": 10}
        
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        df_p['Sono_N'] = df_p['Sono'].map(mapa_sono)
        ultima = df_p.iloc[-1]

        # --- GERAÇÃO DE IMAGENS (MATPLOTLIB) ---
        
        # A) Gráfico de Área: Sono vs Dor
        fig_sono, ax_sono = plt.subplots(figsize=(10, 4))
        ax_sono.fill_between(df_p['Data'], df_p['Sono_N'], color='#008091', alpha=0.3, label='Qualidade do Sono')
        ax_sono.plot(df_p['Data'], df_p['Dor'], color='#FF4B4B', linewidth=2, marker='o', label='Picos de Dor')
        ax_sono.set_title("Correlação: Sono (Área) vs Dor (Linha)")
        ax_sono.legend(loc='upper right')
        plt.xticks(rotation=45, fontsize=8)
        
        buf_sono = io.BytesIO()
        plt.savefig(buf_sono, format='png', bbox_inches='tight'); plt.close(fig_sono)

        # B) Evolução Geral
        fig_ev, ax_ev = plt.subplots(figsize=(10, 4))
        ax_ev.plot(df_p['Data'], df_p['Score_Funcao'], color='#008091', linewidth=3, label='Função')
        ax_ev.set_title("Evolução da Capacidade Funcional")
        plt.xticks(rotation=45, fontsize=8)
        buf_ev = io.BytesIO()
        plt.savefig(buf_ev, format='png', bbox_inches='tight'); plt.close(fig_ev)

        # C) Radar (Reutilizando lógica v8.0)
        labels = ['Agacho', 'Step Up', 'Step Down']
        stats = [df_p['Agachamento'].map(mapa).iloc[-1], df_p['Step_Up'].map(mapa).iloc[-1], df_p['Step_Down'].map(mapa).iloc[-1]]
        angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
        stats += stats[:1]; angles += angles[:1]
        fig_radar, ax_radar = plt.subplots(figsize=(5, 4), subplot_kw=dict(polar=True))
        ax_radar.fill(angles, stats, color='#008091', alpha=0.25)
        ax_radar.set_xticklabels(labels)
        buf_radar = io.BytesIO()
        plt.savefig(buf_radar, format='png', bbox_inches='tight'); plt.close(fig_radar)

        # --- EXIBIÇÃO ---
        st.write("---")
        t1, t2 = st.tabs(["🌙 Análise Biopsicossocial", "🎯 Perfil de Capacidade"])
        with t1:
            st.pyplot(fig_sono)
            st.info("💡 A área azul representa a qualidade do sono. Quedas na área azul costumam preceder picos na linha vermelha (Dor).")
        with t2:
            st.pyplot(fig_radar)

        # Download
        st.write("---")
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: hist = "Não cadastrada."
        
        pdf_bytes = create_pdf(p_sel, hist, {}, buf_ev, buf_radar, buf_sono)
        st.download_button("📥 EXPORTAR PARECER CIENTÍFICO", data=pdf_bytes, file_name=f"Parecer_{p_sel}.pdf")

else:
    st.info("App pronto. Selecione o Painel Analítico para visualizar.")
