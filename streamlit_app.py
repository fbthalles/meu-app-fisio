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

# --- 1. FUNÇÕES DE SUPORTE E PDF ---

def limpar_texto_pdf(txt):
    """Garante compatibilidade de caracteres no PDF."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, metrics, imgs):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho Profissional
    try: pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except: 
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, "GENUA - INSTITUTO DO JOELHO", ln=True, align='C')
    
    pdf.ln(18)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "RELATÓRIO DE EVOLUÇÃO CLÍNICA E PBE", ln=True, align='C')
    pdf.ln(5)

    # 1. Identificação e História
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, f" PACIENTE: {p_name.upper()}", ln=True, fill=True)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 7, f"História Clínica: {limpar_texto_pdf(hist)}"); pdf.ln(3)

    # 2. Quadro de Métricas com Emojis
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " SUMÁRIO DE MÉTRICAS ATUAIS", ln=True, fill=True)
    pdf.set_font("helvetica", '', 10)
    pdf.cell(95, 7, f"- Dor (EVA): {metrics['dor']}/10", ln=0)
    pdf.cell(95, 7, f"- Inchaço (Stroke): {metrics['inchaco_txt']}", ln=1)
    pdf.cell(95, 7, f"- IKDC Score: {metrics['ikdc_txt']}", ln=0)
    pdf.cell(95, 7, f"- Previsão de Alta: {metrics['alta']}", ln=1)
    pdf.ln(5)

    # 3. Gráficos: Capacidade vs Dor e Histórico de Inchaço
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " EVOLUÇÃO: CAPACIDADE VS DOR", ln=True, fill=True, align='C')
    pdf.image(imgs['ev'], x=15, y=pdf.get_y() + 2, w=175); pdf.set_y(pdf.get_y() + 85)
    
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " LINHA DO TEMPO: ESTADO INFLAMATÓRIO (INCHAÇO)", ln=True, fill=True, align='C')
    pdf.image(imgs['inchaco'], x=15, y=pdf.get_y() + 2, w=175)
    
    # Segunda Página: Perfil de Testes e Biopsicossocial
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " PERFIL DE CAPACIDADE POR TESTE FUNCIONAL", ln=True, fill=True, align='C')
    pdf.image(imgs['radar'], x=30, y=pdf.get_y() + 10, w=140)
    
    pdf.set_y(pdf.get_y() + 105)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " ANÁLISE BIOPSICOSSOCIAL (SONO VS DOR)", ln=True, fill=True, align='C')
    pdf.image(imgs['sono'], x=15, y=pdf.get_y() + 5, w=175)

    return bytes(pdf.output())

# --- 2. INTERFACE ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide", page_icon="🏥")
conn = st.connection("gsheets", type=GSheetsConnection)

with st.sidebar:
    try: st.image("Ativo-1.png", width=220)
    except: st.header("GENUA")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "IKDC (Mensal) 📋", "Painel Analítico 📊"])

# --- 3. MÓDULOS DE ENTRADA ---
if menu == "Check-in Diário 📝":
    st.header("Entrada de Dados Diários")
    with st.form("checkin", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente")
        c1, c2 = st.columns(2)
        with c1:
            dor = st.select_slider("Dor atual (0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with c2:
            agac = st.selectbox("Agachamento", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sup = st.selectbox("Step Up", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sdn = st.selectbox("Step Down", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            inchaco = st.select_slider("Inchaço (Stroke Test)", options=["0", "1", "2", "3"])
        if st.form_submit_button("REGISTRAR SESSÃO"):
            df = conn.read(ttl=0).dropna(how="all")
            nova = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Inchaço": str(inchaco), "Sono": sono, "Postura": postura, "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn}])
            conn.update(data=pd.concat([df, nova], ignore_index=True))
            st.success("Dados registrados com sucesso!")

elif menu == "IKDC (Mensal) 📋":
    st.header("Avaliação IKDC (Subjetiva)")
    with st.form("ikdc"):
        p_ikdc = st.text_input("Paciente")
        nota = st.slider("Score Global (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR SCORE"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("Score IKDC atualizado!")

# --- 4. PAINEL ANALÍTICO ---
else:
    st.header("📊 Inteligência Clínica & Business Analytics")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente para Análise", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # Numeração de Sessões (X-axis)
        df_p['Sessao'] = [f"S{i+1}" for i in range(len(df_p))]
        
        # Mapeamento de Capacidade
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        df_p['Sono_N'] = df_p['Sono'].map({"Ruim": 1, "Regular": 5, "Bom": 10})
        df_p['Inchaco_N'] = pd.to_numeric(df_p['Inchaço'], errors='coerce').fillna(0)
        ultima = df_p.iloc[-1]

        # IA: Previsão de Alta
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
        except: prev_txt = "Em análise estatística"

        # Emojis Dinâmicos para Métricas
        status_dor = "✅ Controlada" if ultima['Dor'] <= 3 else "⚠️ Atenção" if ultima['Dor'] <= 6 else "🚨 Elevada"
        status_inc = "✅ Estável" if ultima['Inchaco_N'] <= 1 else "⚠️ Irritado"
        
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            status_ikdc = "🟢 Bom" if u_ikdc > 70 else "🟡 Regular" if u_ikdc > 45 else "🔴 Severo"
        except: u_ikdc = 0; status_ikdc = "Pendente ⚪"

        # Métricas no Topo
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dor Atual", f"{ultima['Dor']}/10", status_dor)
        m2.metric("Inchaço", f"Grau {ultima['Inchaço']}", status_inc)
        m3.metric("IKDC", f"{u_ikdc:.0f}/100", status_ikdc)
        m4.metric("Alta Estimada", prev_txt)

        # --- GERAÇÃO DE GRÁFICOS (MATPLOTLIB) ---
        
        # A) Evolução: Função vs Dor (Escala 0-10)
        fig_ev, ax_ev = plt.subplots(figsize=(10, 4))
        ax_ev.plot(df_p['Sessao'], df_p['Dor'], color='#FF4B4B', label='Dor (EVA)', marker='o', linewidth=2)
        ax_ev.plot(df_p['Sessao'], df_p['Score_Funcao'], color='#008091', label='Capacidade Funcional', marker='s', linewidth=3)
        ax_ev.set_title("Evolução Clínica: Capacidade Funcional vs Dor", fontweight='bold')
        ax_ev.set_ylim(0, 10); ax_ev.set_ylabel("Escala (0-10)"); ax_ev.legend(); ax_ev.grid(True, alpha=0.3)
        buf_ev = io.BytesIO(); plt.savefig(buf_ev, format='png', bbox_inches='tight'); plt.close(fig_ev)

        # B) Histórico de Inchaço (Escala 0-3)
        fig_inc, ax_inc = plt.subplots(figsize=(10, 3))
        ax_inc.bar(df_p['Sessao'].tail(15), df_p['Inchaco_N'].tail(15), color='#008091', alpha=0.8)
        ax_inc.set_title("Monitoramento de Inchaço (Stroke Test)", fontweight='bold')
        ax_inc.set_ylim(0, 3); ax_inc.set_ylabel("Grau (0-3)"); ax_inc.grid(axis='y', alpha=0.3)
        buf_inc = io.BytesIO(); plt.savefig(buf_inc, format='png', bbox_inches='tight'); plt.close(fig_inc)

        # C) Perfil de Capacidade (Substituindo Teia por Barras Individuais)
        fig_cap, ax_cap = plt.subplots(figsize=(8, 5))
        testes = ['Agachamento', 'Step Up', 'Step Down']
        valores = [mapa[ultima['Agachamento']], mapa[ultima['Step_Up']], mapa[ultima['Step_Down']]]
        bars = ax_cap.bar(testes, valores, color=['#008091', '#00A8B8', '#00C8D8'])
        ax_cap.set_title("Perfil de Capacidade por Teste Funcional", fontweight='bold')
        ax_cap.set_ylim(0, 10); ax_cap.set_ylabel("Capacidade (0-10)")
        for bar in bars:
            height = bar.get_height()
            ax_cap.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')
        buf_radar = io.BytesIO(); plt.savefig(buf_radar, format='png', bbox_inches='tight'); plt.close(fig_cap)

        # D) Sono vs Dor
        fig_s, ax_s = plt.subplots(figsize=(10, 3))
        ax_s.fill_between(df_p['Sessao'], df_p['Sono_N'], color='#008091', alpha=0.2, label='Qualidade do Sono')
        ax_s.plot(df_p['Sessao'], df_p['Dor'], color='#FF4B4B', marker='o', label='Dor')
        ax_s.set_title("Análise Biopsicossocial: Impacto do Sono na Dor"); ax_s.legend()
        buf_s = io.BytesIO(); plt.savefig(buf_s, format='png', bbox_inches='tight'); plt.close(fig_s)

        # Exibição no Tablet
        st.write("---")
        t1, t2, t3 = st.tabs(["📈 Evolução & IA", "🌊 Inchaço & Sono", "🎯 Perfil Funcional"])
        with t1: st.pyplot(fig_ev); st.success(f"🔮 **Previsão Clínica:** O paciente atingirá 90% de função em {prev_txt}.")
        with t2: st.pyplot(fig_inc); st.pyplot(fig_s)
        with t3: st.pyplot(fig_cap)

        # Download do PDF
        st.write("---")
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: hist = "História clínica não cadastrada."

        pdf_metrics = {
            'dor': ultima['Dor'], 
            'inchaco_txt': f"Grau {ultima['Inchaço']} ({status_inc})",
            'ikdc_txt': f"{u_ikdc:.0f}/100 ({status_ikdc})", 
            'alta': prev_txt
        }
        
        pdf_bytes = create_pdf(p_sel, hist, pdf_metrics, {'ev': buf_ev, 'sono': buf_s, 'radar': buf_radar, 'inchaco': buf_inc})
        st.download_button("📥 EXPORTAR PARECER TÉCNICO FINAL (PDF)", data=pdf_bytes, file_name=f"Laudo_GENUA_{p_sel}.pdf")
    else: st.info("Aguardando entrada de dados na planilha.")
