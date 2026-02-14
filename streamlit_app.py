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

# --- 1. FUNÇÕES DE PDF E LIMPEZA ---
def limpar_texto_pdf(txt):
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, metrics, imgs):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except: pdf.set_font("helvetica", 'B', 16); pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "RELATÓRIO DE INTELIGÊNCIA CLÍNICA AVANÇADA", ln=True, align='C')
    pdf.ln(5)

    # Dados e História
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, f" PACIENTE: {p_name.upper()}", ln=True, fill=True)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 7, f"Anamnese: {hist}"); pdf.ln(5)

    # Tabela de Métricas
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, " MÉTRICAS CIENTÍFICAS E PBE", ln=True, fill=True)
    pdf.set_font("helvetica", '', 10)
    pdf.cell(95, 7, f"- Dor (EVA): {metrics['dor']}/10", ln=0); pdf.cell(95, 7, f"- Inchaço (Stroke): {metrics['inchaco']}", ln=1)
    pdf.cell(95, 7, f"- IKDC Score: {metrics['ikdc']}", ln=0); pdf.cell(95, 7, f"- Previsão de Alta: {metrics['alta']}", ln=1)
    pdf.ln(5)

    # Gráficos
    pdf.image(imgs['ev'], x=15, y=pdf.get_y(), w=175); pdf.set_y(pdf.get_y() + 85)
    pdf.image(imgs['sono'], x=15, y=pdf.get_y(), w=175)
    
    pdf.add_page()
    pdf.image(imgs['radar'], x=45, y=20, w=120)
    return bytes(pdf.output())

# --- 2. INTERFACE ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide", page_icon="🏥")
conn = st.connection("gsheets", type=GSheetsConnection)

with st.sidebar:
    try: st.image("Ativo-1.png", width=220)
    except: st.header("GENUA")
    menu = st.radio("NAVEGAÇÃO", ["Check-in Diário 📝", "IKDC (Mensal) 📋", "Painel Analítico 📊"])

# --- 3. MÓDULOS DE ENTRADA (RESTAURADOS) ---
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

# --- 4. PAINEL ANALÍTICO (O CÉREBRO) ---
else:
    st.header("📊 Inteligência Clínica & BI")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # Cruzamento de Dados e Cálculos
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        mapa_sono = {"Ruim": 1, "Regular": 5, "Bom": 10}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        df_p['Sono_N'] = df_p['Sono'].map(mapa_sono)
        ultima = df_p.iloc[-1]

        # IA: Previsão de Alta (Regressão Linear)
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_prev = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_prev.strftime("%d/%m/%Y")
        except: prev_txt = "Em análise"

        # Métricas no Topo
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dor Atual", f"{ultima['Dor']}/10")
        m2.metric("Inchaço", f"Grau {ultima.get('Inchaco', '0')}")
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            status = "🔴 Severo" if u_ikdc < 45 else "🟡 Regular" if u_ikdc < 70 else "🟢 Bom"
            m3.metric("IKDC Científico", f"{u_ikdc:.0f}/100", delta=status)
        except: u_ikdc = "N/A"; m3.metric("IKDC", "Pendente")
        m4.metric("Eficiência de Carga", f"{(ultima['Score_Funcao']*10):.0f}%")

        # --- GERAÇÃO DE GRÁFICOS (MATPLOTLIB PARA PDF) ---
        # A) Evolução Geral
        fig_ev, ax_ev = plt.subplots(figsize=(10, 4))
        ax_ev.plot(df_p['Data'], df_p['Dor'], color='#FF4B4B', label='Dor (EVA)', marker='o')
        ax_ev.plot(df_p['Data'], df_p['Score_Funcao'], color='#008091', label='Função (Score)', linewidth=3)
        ax_ev.set_title("Evolução: Dor vs Capacidade Funcional"); ax_ev.legend(); plt.xticks(rotation=45, fontsize=8)
        buf_ev = io.BytesIO(); plt.savefig(buf_ev, format='png', bbox_inches='tight'); plt.close(fig_ev)

        # B) Biopsicossocial: Sono vs Dor
        fig_sono, ax_sono = plt.subplots(figsize=(10, 3))
        ax_sono.fill_between(df_p['Data'], df_p['Sono_N'], color='#008091', alpha=0.3, label='Qualidade do Sono')
        ax_sono.step(df_p['Data'], df_p['Dor'], color='#FF4B4B', where='post', label='Picos de Dor')
        ax_sono.set_title("Análise Biopsicossocial: Sono vs Dor"); ax_sono.legend(); plt.xticks(rotation=45, fontsize=8)
        buf_sono = io.BytesIO(); plt.savefig(buf_sono, format='png', bbox_inches='tight'); plt.close(fig_sono)

        # C) Radar Funcional
        lbls = ['Agacho', 'Step Up', 'Step Down']; stats = [ultima['Agachamento'], ultima['Step_Up'], ultima['Step_Down']]
        stats_n = [mapa[s] for s in stats]; angles = np.linspace(0, 2*np.pi, len(lbls), endpoint=False).tolist()
        stats_n += stats_n[:1]; angles += angles[:1]
        fig_r, ax_r = plt.subplots(figsize=(5, 4), subplot_kw=dict(polar=True))
        ax_r.fill(angles, stats_n, color='#008091', alpha=0.25); ax_r.set_xticklabels(lbls)
        buf_radar = io.BytesIO(); plt.savefig(buf_radar, format='png', bbox_inches='tight'); plt.close(fig_r)

        # Exibição das Abas
        st.write("---")
        t1, t2, t3 = st.tabs(["📈 Evolução & IA", "🌙 Biopsicossocial", "🎯 Perfil de Capacidade"])
        with t1:
            st.pyplot(fig_ev)
            st.success(f"🔮 **Prognóstico de Alta:** De acordo com a regressão linear, o paciente atingirá 90% de função em **{prev_txt}**.")
        with t2:
            st.pyplot(fig_sono)
            st.write("**Análise de Postura vs Dor:**")
            st.altair_chart(alt.Chart(df_p).mark_bar(color='#008091').encode(x='Postura', y='mean(Dor)'), use_container_width=True)
        with t3:
            c_l, c_r = st.columns(2)
            with c_l: st.pyplot(fig_r)
            with c_r:
                st.markdown("#### 💡 Insights Clínicos (PBE)")
                if "Incapaz" in str(ultima['Step_Down']) or "Moderada" in str(ultima['Step_Down']):
                    st.warning("⚠️ **Déficit Excêntrico:** Baixo controle no Step Down indica necessidade de focar em freio motor.")
                if int(ultima.get('Inchaco', '0')) >= 2:
                    st.error("🔥 **Joelho Irritado:** Inchaço Grau 2+. Priorizar controle de efusão e reduzir pliometria.")
                if ultima['Sono'] == "Ruim":
                    st.info("🚨 **Sensibilização:** Sono ruim detectado. Possível aumento da percepção de dor sem dano tecidual novo.")

        # ZenFisio e PDF
        st.write("---")
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: hist = "Não cadastrada."
        
        txt_zen = f"Evolução {p_sel}: Dor {ultima['Dor']}/10, Inchaço {ultima.get('Inchaco', '0')}, Score Funcional {ultima['Score_Funcao']:.1f}/10. Previsão de Alta: {prev_txt}."
        st.text_area("Copie para o ZenFisio:", value=txt_zen)
        
        pdf_bytes = create_pdf(p_sel, hist, {'dor': ultima['Dor'], 'inchaco': ultima.get('Inchaco', '0'), 'ikdc': u_ikdc, 'alta': prev_txt}, {'ev': buf_ev, 'sono': buf_sono, 'radar': buf_radar})
        st.download_button("📥 EXPORTAR PARECER COMPLETO (PDF)", data=pdf_bytes, file_name=f"GENUA_Report_{p_sel}.pdf")
    else: st.info("Sem dados disponíveis.")
