import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import altair as alt
import numpy as np
from fpdf import FPDF

# --- 1. FUNÇÕES DE SUPORTE (PDF E LIMPEZA) ---

def limpar_texto_pdf(txt):
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, dor_at, func_at, ikdc_at, prev_alta, inchaco_at, hist_inchaco):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except:
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, "GENUA INSTITUTO DO JOELHO", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "RELATORIO DE EVOLUCAO CLINICA", ln=True, align='C')
    pdf.set_font("helvetica", '', 12)
    pdf.cell(0, 10, f"Paciente: {limpar_texto_pdf(p_name).upper()}", ln=True, align='C')
    pdf.ln(10)
    
    # 1. História
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 1. Historia e Contexto Clinico", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 8, limpar_texto_pdf(hist))
    pdf.ln(5)
    
    # 2. Métricas
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 2. Metricas de Desempenho e Efusao", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"- Dor Atual: {dor_at}/10 | Inchaco Atual: {inchaco_at}", ln=True)
    pdf.cell(0, 8, f"- Historico Recente de Inchaco: {hist_inchaco}", ln=True)
    pdf.cell(0, 8, f"- Capacidade Funcional: {func_at:.1f}/10 | IKDC: {ikdc_at}", ln=True)
    pdf.ln(5)

    # 3. Prognóstico
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, " 3. Prognostico de Alta", ln=True, fill=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"- Previsao de 90% de funcao: {prev_alta}", ln=True)
    
    pdf.ln(15)
    pdf.set_font("helvetica", 'I', 8)
    pdf.multi_cell(0, 5, "Documento gerado via GENUA Intelligence System baseada em diretrizes PBE.")
    
    return bytes(pdf.output())

# --- 2. CONFIGURAÇÃO ---
st.set_page_config(page_title="GENUA Clinical Intelligence", layout="wide", page_icon="🏥")

# --- 3. CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro de conexao: {e}")
    st.stop()

# --- 4. BARRA LATERAL ---
with st.sidebar:
    try:
        st.image("Ativo-1.png", width=250)
    except:
        st.subheader("GENUA")
    menu = st.radio("NAVEGACAO", ["Check-in Diário 📝", "Avaliação IKDC 📋", "Painel Analítico 📊"])

# --- 5. MÓDULOS ---

if menu == "Check-in Diário 📝":
    st.header("Check-in de Evolução")
    with st.form("form_checkin", clear_on_submit=True):
        paciente = st.text_input("Nome do Paciente")
        c1, c2 = st.columns(2)
        with c1:
            dor = st.select_slider("Dor (0-10)", options=list(range(11)))
            sono = st.radio("Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
            postura = st.radio("Postura", ["Sentado", "Em pé"], horizontal=True)
        with c2:
            st.markdown("#### 🏋️ Funcional e Inchaço")
            agac = st.selectbox("Agachamento", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            sup = st.selectbox("Step Up", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            sdn = st.selectbox("Step Down", ["Sem Dor", "Dor Leve", "Dor Moderada", "Incapaz"])
            inchaco = st.select_slider("Inchaço (Stroke)", options=["0", "1", "2", "3"])
        
        if st.form_submit_button("REGISTRAR NO SISTEMA"):
            df_h = conn.read(ttl=0).dropna(how="all")
            novo = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": paciente.strip(), "Dor": int(dor), "Inchaco": str(inchaco), "Sono": sono, "Postura": postura, "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn}])
            conn.update(data=pd.concat([df_h, novo], ignore_index=True))
            st.success("Dados salvos!")

elif menu == "Avaliação IKDC 📋":
    st.header("Score Científico IKDC")
    with st.form("form_ikdc"):
        p_ikdc = st.text_input("Paciente")
        nota = st.slider("Nota Global (0-100)", 0, 100, 50)
        if st.form_submit_button("SALVAR"):
            df_i = conn.read(worksheet="IKDC", ttl=0).dropna(how="all")
            conn.update(worksheet="IKDC", data=pd.concat([df_i, pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Paciente": p_ikdc.strip(), "Score_IKDC": nota}])], ignore_index=True))
            st.success("IKDC Salvo!")

else: # PAINEL ANALÍTICO
    st.header("📊 Painel de Decisão Clínica")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente", df['Paciente'].unique())
        
        # 1. Dados e História
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist = df_cad[df_cad['Nome'].str.strip() == p_sel.strip()]['Historia'].values[0]
            st.info(f"📝 **História:** {hist}")
        except:
            hist = "Nao cadastrada."

        df_p = df[df['Paciente'] == p_sel].copy()
        mapa = {"Sem Dor": 10, "Dor Leve": 7, "Dor Moderada": 4, "Incapaz": 0}
        df_p['Score_Funcao'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        ultima = df_p.iloc[-1]

        # 2. IA: Previsão de Alta
        try:
            df_p['Dias'] = (pd.to_datetime(df_p['Data'], dayfirst=True) - pd.to_datetime(df_p['Data'], dayfirst=True).min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Funcao'].values, 1)
            dia_alvo = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            data_p = pd.to_datetime(df_p['Data'], dayfirst=True).min() + pd.to_timedelta(dia_alvo, unit='d')
            prev_txt = data_p.strftime("%d/%m/%Y")
            st.success(f"🔮 **Previsão de Alta (90%):** {prev_txt}")
        except:
            prev_txt = "Em analise"

        # 3. Métricas Principais
        m1, m2, m3 = st.columns(3)
        m1.metric("Dor Atual", f"{ultima['Dor']}/10")
        m2.metric("Inchaço Atual", f"Grau {ultima.get('Inchaco', '0')}")
        m3.metric("Eficiência", f"{(ultima['Score_Funcao']*10):.0f}%")

        # --- 4. NOVO: GRÁFICO COMPARATIVO DE INCHAÇO ---
        st.write("---")
        st.subheader("🧬 Evolução do Inchaço (Últimas 5 Sessões)")
        
        # Prepara dados do inchaço (converte para numérico para o gráfico)
        df_p['Inchaco_Num'] = pd.to_numeric(df_p['Inchaco'], errors='coerce').fillna(0)
        recent_df = df_p.tail(5)
        
        chart_inchaco = alt.Chart(recent_df).mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
            x=alt.X('Data:O', title='Data da Sessão'),
            y=alt.Y('Inchaco_Num:Q', title='Grau do Inchaço (0-3)', scale=alt.Scale(domain=[0, 3])),
            color=alt.condition(
                alt.datum.Inchaco_Num > 1, 
                alt.value('#FF4B4B'), # Vermelho se inchaço alto
                alt.value('#008091')  # Azul GENUA se controlado
            )
        ).properties(height=300)
        
        st.altair_chart(chart_inchaco, use_container_width=True)

        # 5. Outros Gráficos
        t1, t2 = st.tabs(["📊 Dor vs Função", "🌙 Fatores Externos"])
        with t1:
            st.line_chart(df_p.set_index('Data')[['Dor', 'Score_Funcao']], color=["#FF4B4B", "#008091"])
        with t2:
            ca, cb = st.columns(2)
            with ca: st.altair_chart(alt.Chart(df_p).mark_bar(color='#008091').encode(x='Sono', y='mean(Dor)'), use_container_width=True)
            with cb: st.altair_chart(alt.Chart(df_p).mark_bar(color='#008091').encode(x='Postura', y='mean(Score_Funcao)'), use_container_width=True)

        # 6. Laudo Médico
        st.write("---")
        st.subheader("📄 Relatório Médico Profissional")
        
        # Pega os últimos 3 inchaços para o texto do PDF
        ultimos_3_inchacos = " -> ".join([str(x) for x in recent_df['Inchaco_Num'].tail(3).tolist()])
        
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            ikdc_val = f"{df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]:.0f}/100"
        except:
            ikdc_val = "N/A"

        pdf_bytes = create_pdf(p_sel, hist, ultima['Dor'], ultima['Score_Funcao'], ikdc_val, prev_txt, f"Grau {ultima['Inchaco']}", ultimos_3_inchacos)
        st.download_button("📥 BAIXAR RELATORIO PDF", data=pdf_bytes, file_name=f"Laudo_GENUA_{p_sel}.pdf", mime="application/pdf")
    else:
        st.info("Aguardando dados.")
