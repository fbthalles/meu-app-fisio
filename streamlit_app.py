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

# --- 1. FUNÇÕES DE PDF E LIMPEZA (CORRIGIDA) ---
def limpar_texto_pdf(txt):
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, metrics, imgs):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho Profissional
    try: pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except: pdf.set_font("helvetica", 'B', 16); pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(18)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "RELATORIO DE INTELIGENCIA CLINICA E PBE", ln=True, align='C')
    pdf.ln(5)

    # 1. Identificação e História
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, f" PACIENTE: {p_name.upper()}", ln=True, fill=True)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 7, f"Anamnese: {limpar_texto_pdf(hist)}"); pdf.ln(3)

    # 2. Score IKDC Explicado e Score do Paciente (FIX AQUI)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " QUESTIONARIO IKDC (SUBJETIVO)", ln=True, fill=True)
    pdf.set_font("helvetica", 'I', 9)
    txt_ikdc = "O International Knee Documentation Committee (IKDC) e um score de 0-100. Interpretacao: <45 (Severo), 45-70 (Regular), >70 (Bom)."
    pdf.multi_cell(0, 5, limpar_texto_pdf(txt_ikdc))
    
    # Linha de destaque para o Score
    pdf.set_font("helvetica", 'B', 11)
    pdf.set_text_color(0, 128, 145) # Azul GENUA
    pdf.cell(0, 8, f"SCORE ATUAL DO PACIENTE: {metrics['ikdc']}/100", ln=True)
    pdf.set_text_color(0, 0, 0) # Volta para preto
    pdf.ln(4)

    # 3. Gráficos: Evolução e Inchaço
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " EVOLUCAO CLINICA E LINHA DO TEMPO DE INCHACO", ln=True, fill=True)
    pdf.image(imgs['ev'], x=15, y=pdf.get_y() + 2, w=175); pdf.set_y(pdf.get_y() + 82)
    pdf.image(imgs['inchaco'], x=15, y=pdf.get_y(), w=175)
    
    # Segunda Página: Radar e Biopsicossocial
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " PERFIL DE CAPACIDADE FUNCIONAL (RADAR)", ln=True, fill=True)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, "Analise do equilibrio entre os testes de agachamento e degrau. Desequilibrios indicam deficits especificos em controle motor ou forca excentrica.")
    pdf.image(imgs['radar'], x=45, y=pdf.get_y() + 5, w=120)
    
    pdf.set_y(pdf.get_y() + 115)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " ANALISE BIOPSICOSSOCIAL (SONO vs DOR)", ln=True, fill=True)
    pdf.image(imgs['sono'], x=15, y=pdf.get_y() + 5, w=175)

    return bytes(pdf.output())

# --- 2. RESTANTE DO CÓDIGO (DASHBOARD E PROCESSAMENTO) ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide", page_icon="🏥")
conn = st.connection("gsheets", type=GSheetsConnection)

with st.sidebar:
    try: st.image("Ativo-1.png", width=220)
    except: st.header("GENUA")
    menu = st.radio("NAVEGACAO", ["Check-in Diário 📝", "IKDC (Mensal) 📋", "Painel Analítico 📊"])

if menu == "Check-in Diário 📝":
    st.header("Entrada de Dados Diários")
    with st.form("checkin", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente")
        c1, c2 = st.columns(2)
        with c1:
            dor = st.select_slider("Dor (0-10)", options=list(range(11)))
            sono = st.radio("Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with c2:
            agac = st.selectbox("Agachamento", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sup = st.selectbox("Step Up", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sdn = st.selectbox("Step Down", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            inchaco = st.select_slider("Inchaço (Stroke)", options=["0", "1", "2", "3"])
        if st.form_submit_button("REGISTRAR SESSÃO"):
            df = conn.read(ttl=0).dropna(how="all")
            nova = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Inchaco": str(inchaco), "Sono": sono, "Postura": postura, "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn}])
            conn.update(data=pd.concat([df, nova], ignore_index=True))
            st.success("Sessão Registrada!")

elif menu == "IKDC (Mensal) 📋":
    st.header("Score Científico IKDC")
    with st.form("ikdc"):
        p_ikdc = st.text_input("Paciente")
        nota = st.slider("Nota Global (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR IKDC"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("IKDC Atualizado!")

else:
    st.header("📊 Inteligência Clínica & BI")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        mapa_sono = {"Ruim": 1, "Regular": 5, "Bom": 10}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        df_p['Sono_N'] = df_p['Sono'].map(mapa_sono)
        df_p['Inchaco_N'] = pd.to_numeric(df_p['Inchaco'], errors='coerce').fillna(0)
        ultima = df_p.iloc[-1]

        # IA: Previsão de Alta
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
        except: prev_txt = "Em análise"

        # Métricas na Tela
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc_val = df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            status_ikdc = f"{u_ikdc_val:.0f}"
        except: u_ikdc_val = 0; status_ikdc = "Pendente"

        # --- GERAÇÃO DE GRÁFICOS (FIXADOS) ---
        # A) Evolução
        fig_ev, ax_ev = plt.subplots(figsize=(10, 4))
        ax_ev.plot(df_p['Data'], df_p['Dor'], color='#FF4B4B', label='Dor (EVA)', marker='o')
        ax_ev.plot(df_p['Data'], df_p['Score_Funcao'], color='#008091', label='Funcao', linewidth=3)
        ax_ev.set_title("Evolucao Clinica"); ax_ev.legend(); plt.xticks(rotation=45, fontsize=8)
        buf_ev = io.BytesIO(); plt.savefig(buf_ev, format='png', bbox_inches='tight'); plt.close(fig_ev)

        # B) Linha do Tempo Inchaço
        fig_inc, ax_inc = plt.subplots(figsize=(10, 3))
        ax_inc.bar(df_p['Data'].tail(15), df_p['Inchaco_N'].tail(15), color='#008091')
        ax_inc.set_title("Historico de Inchaco (Stroke)"); ax_inc.set_ylim(0,3)
        plt.xticks(rotation=45, fontsize=8)
        buf_inc = io.BytesIO(); plt.savefig(buf_inc, format='png', bbox_inches='tight'); plt.close(fig_inc)

        # C) Radar (Limpo)
        lbls = ['Agacho', 'Step Up', 'Step Down']; stats = [mapa[ultima['Agachamento']], mapa[ultima['Step_Up']], mapa[ultima['Step_Down']]]
        angles = np.linspace(0, 2*np.pi, len(lbls), endpoint=False).tolist(); stats += stats[:1]; angles += angles[:1]
        fig_r, ax_r = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
        ax_r.fill(angles, stats, color='#008091', alpha=0.3); ax_r.set_ylim(0, 10)
        ax_r.set_xticks(angles[:-1]); ax_r.set_xticklabels(lbls)
        buf_radar = io.BytesIO(); plt.savefig(buf_radar, format='png', bbox_inches='tight'); plt.close(fig_r)

        # D) Sono
        fig_s, ax_s = plt.subplots(figsize=(10, 3))
        ax_s.fill_between(df_p['Data'], df_p['Sono_N'], color='#008091', alpha=0.3)
        ax_s.plot(df_p['Data'], df_p['Dor'], color='#FF4B4B'); plt.xticks(rotation=45, fontsize=8)
        buf_s = io.BytesIO(); plt.savefig(buf_s, format='png', bbox_inches='tight'); plt.close(fig_s)

        # Tabs e Exibição
        st.pyplot(fig_ev)
        st.write("---")
        
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: hist = "Não cadastrada."
        
        pdf_bytes = create_pdf(p_sel, hist, {'dor': ultima['Dor'], 'inchaco': ultima.get('Inchaco', '0'), 'ikdc': status_ikdc, 'alta': prev_txt}, {'ev': buf_ev, 'sono': buf_s, 'radar': buf_radar, 'inchaco': buf_inc})
        st.download_button("📥 EXPORTAR RELATORIO PREMIUM (PDF)", data=pdf_bytes, file_name=f"GENUA_Report_{p_sel}.pdf")
    else: st.info("Sem dados disponíveis.")
