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

# --- 1. FUNÇÕES DE SUPORTE E PDF (REVISÃO DE PORTUGUÊS) ---

def limpar_texto_pdf(txt):
    """Remove caracteres incompatíveis com a codificação padrão do PDF."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def obter_emoji_status(valor, tipo="score"):
    """Retorna um emoji baseado no desempenho clínico."""
    if tipo == "score":
        if valor >= 80: return "Excelente (90)"
        if valor >= 50: return "Bom (74)"
        return "Regular (52)"
    if tipo == "dor":
        if valor <= 3: return "Baixa (74)"
        if valor <= 6: return "Moderada (52)"
        return "Elevada (90)"
    return ""

def create_pdf(p_name, hist, metrics, imgs):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho Institucional
    try: pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except: 
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, "GENUA - INSTITUTO DO JOELHO", ln=True, align='C')
    
    pdf.ln(18)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, limpar_texto_pdf("PARECER TÉCNICO DE EVOLUÇÃO CLÍNICA"), ln=True, align='C')
    pdf.ln(5)

    # 1. Identificação e Anamnese
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf(f" PACIENTE: {p_name.upper()}"), ln=True, fill=True)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 7, limpar_texto_pdf(f"Histórico Clínico: {hist}")); pdf.ln(3)

    # 2. Resumo de Métricas (Português Revisado)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf(" MÉTRICAS DE DESEMPENHO ATUAIS"), ln=True, fill=True)
    pdf.set_font("helvetica", '', 10)
    
    # Limpando cada linha para evitar o erro de codificação
    linha_dor = limpar_texto_pdf(f"- Dor (EVA): {metrics['dor']}/10 ({metrics['dor_status']})")
    linha_inc = limpar_texto_pdf(f"- Inchaço (Stroke): Grau {metrics['inchaco']} ({metrics['inc_status']})")
    linha_ikdc = limpar_texto_pdf(f"- Score IKDC: {metrics['ikdc']}/100 ({metrics['ikdc_status']})")
    linha_alta = limpar_texto_pdf(f"- Previsão de Alta: {metrics['alta']}")

    pdf.cell(95, 7, linha_dor, ln=0); pdf.cell(95, 7, linha_inc, ln=1)
    pdf.cell(95, 7, linha_ikdc, ln=0); pdf.cell(95, 7, linha_alta, ln=1)
    pdf.ln(5)

    # 3. Gráficos (Evolução e Inflamação)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf(" ANÁLISE TEMPORAL: CAPACIDADE VS DOR"), ln=True, fill=True, align='C')
    pdf.image(imgs['ev'], x=15, y=pdf.get_y() + 2, w=175); pdf.set_y(pdf.get_y() + 85)
    
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf(" HISTÓRICO DE EFUSÃO ARTICULAR (INCHAÇO)"), ln=True, fill=True, align='C')
    pdf.image(imgs['inchaco'], x=15, y=pdf.get_y() + 2, w=175)
    
    # Segunda Página: Biopsicossocial e Capacidade
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf(" PERFIL DE CAPACIDADE POR TESTE FUNCIONAL"), ln=True, fill=True, align='C')
    pdf.image(imgs['cap'], x=30, y=pdf.get_y() + 10, w=140)
    
    pdf.set_y(pdf.get_y() + 105)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf(" CORRELAÇÃO BIOPSICOSSOCIAL: SONO VS DOR"), ln=True, fill=True, align='C')
    pdf.image(imgs['sono'], x=15, y=pdf.get_y() + 5, w=175)

    return bytes(pdf.output())

# --- 2. INTERFACE E CONEXÃO ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide", page_icon="🏥")
conn = st.connection("gsheets", type=GSheetsConnection)

with st.sidebar:
    try: st.image("Ativo-1.png", width=220)
    except: st.header("GENUA")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação IKDC 📋", "Painel Analítico 📊"])

# --- 3. MÓDULOS DE ENTRADA ---
if menu == "Check-in Diário 📝":
    st.header("Check-in Diário de Evolução")
    with st.form("checkin", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente")
        c1, c2 = st.columns(2)
        with c1:
            dor = st.select_slider("Nível de Dor Atual (0-10)", options=list(range(11)))
            sono = st.radio("Qualidade do Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura Predominante", ["Sentado", "Equilibrado", "Em pé"], horizontal=True)
        with c2:
            agac = st.selectbox("Agachamento", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sup = st.selectbox("Step Up (Subida)", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            sdn = st.selectbox("Step Down (Descida)", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            inchaco = st.select_slider("Inchaço Articular (Stroke Test)", options=["0", "1", "2", "3"])
        if st.form_submit_button("REGISTRAR SESSÃO"):
            df = conn.read(ttl=0).dropna(how="all")
            nova = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Inchaço": str(inchaco), "Sono": sono, "Postura": postura, "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn}])
            conn.update(data=pd.concat([df, nova], ignore_index=True))
            st.success("Sessão registrada com sucesso!")

elif menu == "Avaliação IKDC 📋":
    st.header("Score Científico IKDC")
    with st.form("ikdc"):
        p_ikdc = st.text_input("Nome do Paciente")
        nota = st.slider("Nota Global de Função (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR SCORE"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("Score IKDC atualizado com sucesso!")

# --- 4. PAINEL ANALÍTICO (O CÉREBRO) ---
else:
    st.header("📊 Inteligência Clínica & Business Analytics")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente para Análise", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # Numeração de Sessões (X-axis)
        df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]
        
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Função'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        df_p['Sono_N'] = df_p['Sono'].map({"Ruim": 1, "Regular": 5, "Bom": 10})
        
        col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
        df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)
        ultima = df_p.iloc[-1]

        # IA: Previsão de Alta
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Função'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
        except: prev_txt = "Em análise"

        # Métricas na Tela
        status_dor = obter_emoji_status(ultima['Dor'], "dor")
        status_inc = "✅ Estável" if ultima['Inchaco_N'] <= 1 else "🚨 Irritado"
        
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            status_ikdc = obter_emoji_status(u_ikdc, "score")
        except: u_ikdc = 0; status_ikdc = "Pendente"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dor Atual", f"{ultima['Dor']}/10", status_dor)
        m2.metric("Inchaço", f"Grau {ultima[col_inc]}", status_inc)
        m3.metric("IKDC", f"{u_ikdc:.0f}/100", status_ikdc)
        m4.metric("Previsão de Alta", prev_txt)

        # --- GERAÇÃO DE GRÁFICOS (MATPLOTLIB) ---
        
        # A) Evolução: Capacidade vs Dor (0-10)
        fig_ev, ax_ev = plt.subplots(figsize=(10, 4))
        ax_ev.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', label='Dor (EVA)', marker='o', linewidth=2)
        ax_ev.plot(df_p['Sessão_Num'], df_p['Score_Função'], color='#008091', label='Capacidade Funcional', marker='s', linewidth=3)
        ax_ev.set_title("Evolução Clínica: Capacidade vs Nível de Dor", fontweight='bold')
        ax_ev.set_ylim(0, 10); ax_ev.set_ylabel("Escala (0-10)"); ax_ev.legend(loc='upper right'); ax_ev.grid(True, alpha=0.2)
        buf_ev = io.BytesIO(); plt.savefig(buf_ev, format='png', bbox_inches='tight'); plt.close(fig_ev)

        # B) Linha do Tempo: Inchaço (0-3)
        fig_inc, ax_inc = plt.subplots(figsize=(10, 3))
        ax_inc.bar(df_p['Sessão_Num'].tail(15), df_p['Inchaco_N'].tail(15), color='#008091', alpha=0.8, label='Inchaço (Stroke Test)')
        ax_inc.set_title("Histórico de Efusão Articular (Inchaço)", fontweight='bold')
        ax_inc.set_ylim(0, 3); ax_inc.set_ylabel("Grau (0-3)"); ax_inc.legend(); ax_inc.grid(axis='y', alpha=0.2)
        buf_inc = io.BytesIO(); plt.savefig(buf_inc, format='png', bbox_inches='tight'); plt.close(fig_inc)

        # C) Perfil de Capacidade (BARRAS EM VEZ DE TEIA)
        fig_cap, ax_cap = plt.subplots(figsize=(8, 5))
        testes = ['Agachamento', 'Step Up', 'Step Down']
        valores = [mapa[ultima['Agachamento']], mapa[ultima['Step_Up']], mapa[ultima['Step_Down']]]
        ax_cap.bar(testes, valores, color='#008091')
        ax_cap.set_title("Capacidade Funcional por Teste", fontweight='bold')
        ax_cap.set_ylim(0, 10); ax_cap.set_ylabel("Nota (0-10)"); ax_cap.grid(axis='y', alpha=0.2)
        buf_cap = io.BytesIO(); plt.savefig(buf_cap, format='png', bbox_inches='tight'); plt.close(fig_cap)

        # D) Sono vs Dor
        fig_s, ax_s = plt.subplots(figsize=(10, 3))
        ax_s.fill_between(df_p['Sessão_Num'], df_p['Sono_N'], color='#008091', alpha=0.2, label='Qualidade do Sono')
        ax_s.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', marker='o', label='Dor (EVA)')
        ax_s.set_title("Análise Biopsicossocial: Impacto do Sono na Dor", fontweight='bold'); ax_s.legend()
        buf_s = io.BytesIO(); plt.savefig(buf_s, format='png', bbox_inches='tight'); plt.close(fig_s)

        # Exibição no Tablet
        st.pyplot(fig_ev)
        st.write("---")
        
        # Download do PDF
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: hist = "Anamnese não cadastrada."

        pdf_metrics = {
            'dor': ultima['Dor'], 'dor_status': status_dor,
            'inchaco': ultima[col_inc], 'inc_status': status_inc,
            'ikdc': f"{u_ikdc:.0f}", 'ikdc_status': status_ikdc,
            'alta': prev_txt
        }
        
        pdf_bytes = create_pdf(p_sel, hist, pdf_metrics, {'ev': buf_ev, 'sono': buf_s, 'cap': buf_cap, 'inchaco': buf_inc})
        st.download_button("📥 BAIXAR PARECER TÉCNICO (PDF)", data=pdf_bytes, file_name=f"Laudo_GENUA_{p_sel}.pdf")
    else: st.info("Aguardando dados disponíveis.")
