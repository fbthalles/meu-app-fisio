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
    """Garante que o PDF aceite acentuação e caracteres especiais do PT-BR."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, metrics, imgs):
    pdf = FPDF()
    azul_genua = (0, 128, 145)
    
    # --- PÁGINA 1 ---
    pdf.add_page()
    try: pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except: pdf.set_font("helvetica", 'B', 16); pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(18)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, limpar_texto_pdf("RELATÓRIO DE INTELIGÊNCIA CLÍNICA E EVOLUÇÃO"), ln=True, align='C')
    pdf.ln(5)

    # 1. Identificação
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, limpar_texto_pdf(" 1. IDENTIFICAÇÃO E ANAMNESE"), ln=True, fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("helvetica", '', 10); pdf.ln(2)
    pdf.multi_cell(0, 7, limpar_texto_pdf(f"Paciente: {p_name.upper()}\nHistória Clínica: {hist}")); pdf.ln(3)

    # 2. Avaliação IKDC (Com Legenda de Score)
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, limpar_texto_pdf(" 2. AVALIAÇÃO CIENTÍFICA IKDC (SUBJETIVA)"), ln=True, fill=True, align='C')
    pdf.set_text_color(0, 0, 0); pdf.set_font("helvetica", 'I', 9); pdf.ln(1)
    pdf.multi_cell(0, 5, limpar_texto_pdf("Legenda Score: <45 (Severo), 45-70 (Regular), >70 (Bom)."), align='C')
    
    # Resultado Centralizado
    pdf.ln(2); pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 13)
    pdf.set_x((pdf.w - 115) / 2) 
    score_val = int(float(metrics['ikdc']))
    status_msg = f"RESULTADO: {score_val}/100 - {metrics['ikdc_status'].upper()}"
    pdf.cell(115, 12, limpar_texto_pdf(status_msg), ln=True, fill=True, align='C')
    
    pdf.set_text_color(0, 0, 0); pdf.ln(5)

    # 3. Evolução e Inchaço (Espaço para Legendas)
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 8, limpar_texto_pdf(" 3. MONITORAMENTO DE EVOLUÇÃO E INCHAÇO"), ln=True, fill=True, align='C')
    
    # Gráfico 1: Evolução (Sobe para dar espaço à legenda em baixo)
    pdf.image(imgs['ev'], x=15, y=pdf.get_y() + 5, w=175)
    pdf.set_y(pdf.get_y() + 110) # Salto maior para não cortar a legenda
    
    # Gráfico 2: Inchaço
    pdf.image(imgs['inchaco'], x=15, y=pdf.get_y(), w=175)
    
    # --- PÁGINA 2 ---
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, limpar_texto_pdf(" 4. PERFIL DE CAPACIDADE FUNCIONAL POR TESTE"), ln=True, fill=True, align='C')
    pdf.image(imgs['cap'], x=30, y=pdf.get_y() + 10, w=145)
    
    pdf.set_y(pdf.get_y() + 115)
    pdf.cell(0, 8, limpar_texto_pdf(" 5. ANÁLISE BIOPSICOSSOCIAL (SONO VS. DOR)"), ln=True, fill=True, align='C')
    pdf.image(imgs['sono'], x=15, y=pdf.get_y() + 10, w=175)

    return bytes(pdf.output())

# --- 2. INTERFACE E CONEXÃO ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide", page_icon="🏥")
conn = st.connection("gsheets", type=GSheetsConnection)

with st.sidebar:
    try: st.image("Ativo-1.png", width=220)
    except: st.header("GENUA")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "Avaliação IKDC 📋", "Painel Analítico 📊"])

# --- 3. MÓDULOS DE NAVEGAÇÃO ---

if menu == "Check-in Diário 📝":
    st.header("Check-in Diário de Evolução")
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

elif menu == "Avaliação IKDC 📋":
    st.header("Score Científico IKDC")
    with st.form("ikdc"):
        p_ikdc = st.text_input("Nome do Paciente")
        nota = st.slider("Nota Global de Função (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR SCORE"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("Score IKDC registrado!")

else: # PAINEL ANALÍTICO (V18.8 - FOCO EM VISIBILIDADE E LEGENDA PDF)
    st.header("📊 Painel Analítico & Clinical Intelligence")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente para Análise", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # 1. Processamento e Previsão de Alta
        df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]
        mapa_func = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Função'] = (df_p['Agachamento'].map(mapa_func) + df_p['Step_Up'].map(mapa_func) + df_p['Step_Down'].map(mapa_func)) / 3
        df_p['Sono_N'] = df_p['Sono'].map({"Ruim": 1, "Regular": 5, "Bom": 10})
        col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
        df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)
        ultima = df_p.iloc[-1]

        try:
            df_p['Data_DT'] = pd.to_datetime(df_p['Data'], dayfirst=True)
            df_p['Dias'] = (df_p['Data_DT'] - df_p['Data_DT'].min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Função'].values, 1)
            trend_line = z[0] * df_p['Dias'].values + z[1]
            prev_txt = (df_p['Data_DT'].min() + pd.to_timedelta((9.0 - z[1]) / z[0], unit='d')).strftime("%d/%m/%Y") if z[0] > 0 else "Estável"
        except: trend_line = []; prev_txt = "Calculando..."

        # 2. Score IKDC
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = float(df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1])
            status_clinico = "Bom" if u_ikdc > 70 else "Regular" if u_ikdc > 45 else "Severo"
            emoji_ikdc = "🏆" if status_clinico == "Bom" else "🟢" if status_clinico == "Regular" else "🔴"
        except: u_ikdc = 0; emoji_ikdc = "⚪"; status_clinico = "Pendente"

        # 3. GERAÇÃO DE GRÁFICOS (FIX DEFINITIVO DE LEGENDA E VISIBILIDADE)
        indices_5 = np.arange(0, len(df_p), 5)
        labels_5 = [df_p['Sessão_Num'].iloc[i] for i in indices_5]

        # A) Evolução + Tendência (Capture a legenda!)
        fig_ev, ax_ev = plt.subplots(figsize=(10, 5))
        ax_ev.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', label='Nível de Dor (EVA)', marker='o')
        ax_ev.plot(df_p['Sessão_Num'], df_p['Score_Função'], color='#008091', label='Capacidade Funcional', marker='s')
        if len(trend_line) > 0:
            ax_ev.plot(df_p['Sessão_Num'], trend_line, '--', color='#5D6D7E', alpha=0.5, label='Tendência de Alta')
        ax_ev.set_ylim(-0.5, 11); ax_ev.set_xticks(indices_5); ax_ev.set_xticklabels(labels_5)
        lgd_ev = ax_ev.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
        
        buf_ev = io.BytesIO()
        fig_ev.savefig(buf_ev, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_ev,), dpi=150)
        buf_ev.seek(0) # O SEGREDO: Faz a imagem aparecer no tablet!
        plt.close(fig_ev)

        # B) Inchaço
        fig_inc, ax_inc = plt.subplots(figsize=(10, 3.5))
        cores_inc = ['#D32F2F' if x == 3 else '#FFB300' if x == 2 else '#008091' for x in df_p['Inchaco_N']]
        ax_inc.bar(df_p['Sessão_Num'], df_p['Inchaco_N'], color=cores_inc, alpha=0.8, label='Grau de Inchaço (Stroke Test)')
        ax_inc.set_ylim(0, 3.5); ax_inc.set_xticks(indices_5); ax_inc.set_xticklabels(labels_5)
        lgd_inc = ax_inc.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), frameon=False)
        
        buf_inc = io.BytesIO()
        fig_inc.savefig(buf_inc, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_inc,), dpi=150)
        buf_inc.seek(0) # Faz a imagem aparecer no tablet!
        plt.close(fig_inc)

        # C) Perfil e D) Sono (Seguindo o mesmo padrão de segurança)
        fig_cap, ax_cap = plt.subplots(figsize=(8, 5))
        testes = ['Agachamento', 'Step Up', 'Step Down']
        valores = [mapa_func[ultima['Agachamento']], mapa_func[ultima['Step_Up']], mapa_func[ultima['Step_Down']]]
        barras = ax_cap.bar(testes, valores, color='#008091')
        ax_cap.bar_label(barras, padding=3, fmt='%.1f', fontweight='bold')
        buf_cap = io.BytesIO(); fig_cap.savefig(buf_cap, format='png', bbox_inches='tight', dpi=150); buf_cap.seek(0); plt.close(fig_cap)

        fig_s, ax_s = plt.subplots(figsize=(10, 4))
        ax_s.fill_between(df_p['Sessão_Num'], df_p['Sono_N'], color='#008091', alpha=0.2, label='Qualidade do Sono')
        ax_s.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', marker='o', label='Nível de Dor')
        lgd_s = ax_s.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
        buf_s = io.BytesIO(); fig_s.savefig(buf_s, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_s,), dpi=150); buf_s.seek(0); plt.close(fig_s)

        # 4. EXIBIÇÃO DASHBOARD (RESTAURADA)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dor Atual", f"{ultima['Dor']}/10")
        m2.metric("Inchaço", f"Grau {ultima[col_inc]}")
        m3.metric("IKDC", f"{int(u_ikdc)}/100", status_clinico)
        m4.metric("Previsão Alta", prev_txt)

        st.write("---")
        t1, t2, t3 = st.tabs(["📈 Evolução", "🌊 Inchaço", "🎯 Capacidade"])
        with t1: st.image(buf_ev, use_container_width=True)
        with t2: st.image(buf_inc, use_container_width=True)
        with t3: st.image(buf_cap, use_container_width=True); st.image(buf_s, use_container_width=True)

        # 5. DOWNLOAD PDF (MÉTRICAS COMPLETAS)
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist_clinica = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: hist_clinica = "Anamnese não cadastrada."

        pdf_metrics = {'ikdc': u_ikdc, 'ikdc_status': status_clinico, 'dor': ultima['Dor'], 'inchaco': ultima[col_inc], 'alta': prev_txt}
        pdf_bytes = create_pdf(p_sel, hist_clinica, pdf_metrics, {'ev': buf_ev, 'sono': buf_s, 'cap': buf_cap, 'inchaco': buf_inc})
        st.download_button("📥 BAIXAR RELATÓRIO MASTER (PDF)", data=pdf_bytes, file_name=f"Relatorio_{p_sel}.pdf")
        st.info(f"📝 ZenFisio: {p_sel} - Dor {ultima['Dor']}, IKDC {int(u_ikdc)}, Alta est. {prev_txt}.")
    else: st.info("Aguardando entrada de dados na planilha.")
