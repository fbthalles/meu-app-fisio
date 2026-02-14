import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt  # IMPORT CORRIGIDO AQUI
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
    pdf.add_page()
    
    # Cabeçalho Institucional
    try: pdf.image("Ativo-1.png", x=10, y=8, w=35)
    except: 
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, "GENUA - INSTITUTO DO JOELHO", ln=True, align='C')
    
    pdf.ln(18)
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, limpar_texto_pdf("RELATÓRIO DE INTELIGÊNCIA CLÍNICA E EVOLUÇÃO"), ln=True, align='C')
    pdf.ln(5)

    # 1. Identificação e Anamnese
    pdf.set_fill_color(240, 249, 250)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf(f" PACIENTE: {p_name.upper()}"), ln=True, fill=True)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 7, limpar_texto_pdf(f"História Clínica: {hist}")); pdf.ln(3)

    # 2. SEÇÃO IKDC - CENTRALIZAÇÃO COM DESTAQUE (MOLDURA)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf("AVALIAÇÃO CIENTÍFICA IKDC (SUBJETIVA)"), ln=True, fill=True, align='C')
    pdf.set_font("helvetica", 'I', 9)
    txt_ikdc = "O IKDC é o padrão ouro internacional para avaliação funcional. <45 (Severo), 45-70 (Regular), >70 (Bom)."
    pdf.multi_cell(0, 5, limpar_texto_pdf(txt_ikdc), align='C')
    
    pdf.ln(2)
    pdf.set_fill_color(0, 128, 145) # Azul GENUA
    pdf.set_text_color(255, 255, 255) # Texto Branco
    pdf.set_font("helvetica", 'B', 14)
    
    # Cálculo para centralizar a moldura de 75mm no meio da página
    pdf.set_x((pdf.w - 75) / 2)
    pdf.cell(75, 12, limpar_texto_pdf(f"RESULTADO: {metrics['ikdc']}/100 {metrics['ikdc_emoji']}"), ln=True, fill=True, align='C')
    
    pdf.set_text_color(0, 0, 0) # Retorna ao preto padrão
    pdf.ln(5)

    # 3. Gráficos (Evolução e Inchaço)
    pdf.image(imgs['ev'], x=15, y=pdf.get_y(), w=175); pdf.set_y(pdf.get_y() + 85)
    pdf.image(imgs['inchaco'], x=15, y=pdf.get_y(), w=175)
    
    # Página 2 - Perfil de Capacidade e Biopsicossocial
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf("PERFIL DE CAPACIDADE POR TESTE FUNCIONAL"), ln=True, fill=True, align='C')
    pdf.image(imgs['cap'], x=30, y=pdf.get_y() + 5, w=145)
    
    pdf.set_y(pdf.get_y() + 105)
    pdf.set_font("helvetica", 'B', 11); pdf.cell(0, 8, limpar_texto_pdf("ANÁLISE BIOPSICOSSOCIAL: SONO VS. DOR"), ln=True, fill=True, align='C')
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

# --- 4. PAINEL ANALÍTICO (O CÉREBRO CLÍNICO) ---
else:
    st.header("📊 Painel Analítico & Clinical Intelligence")
    df = conn.read(ttl=0).dropna(how="all")
    if not df.empty:
        p_sel = st.selectbox("Selecione o Paciente para Análise", df['Paciente'].unique())
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # Numeração de Sessões
        df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]
        
        # Mapeamento de Capacidade
        mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Função'] = (df_p['Agachamento'].map(mapa) + df_p['Step_Up'].map(mapa) + df_p['Step_Down'].map(mapa)) / 3
        df_p['Sono_N'] = df_p['Sono'].map({"Ruim": 1, "Regular": 5, "Bom": 10})
        
        # Segurança de Coluna para Inchaço
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

        # Métricas IKDC com Emojis
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1]
            emoji_ikdc = "🏆" if u_ikdc >= 85 else "🟢" if u_ikdc >= 70 else "🟡" if u_ikdc >= 45 else "🔴"
        except: u_ikdc = 0; emoji_ikdc = "⚪"

        # --- GERAÇÃO DE GRÁFICOS (MATPLOTLIB) ---
        
        # --- GERAÇÃO DE GRÁFICOS (REVISÃO DE ESPAÇAMENTO E LEGENDAS EXTERNAS) ---
        
        # 1. Gráfico de Evolução: Capacidade vs. Dor
        fig_ev, ax_ev = plt.subplots(figsize=(10, 5))
        ax_ev.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', label='Nível de Dor (EVA)', marker='o', linewidth=2)
        ax_ev.plot(df_p['Sessão_Num'], df_p['Score_Função'], color='#008091', label='Capacidade Funcional', marker='s', linewidth=3)
        
        ax_ev.set_title("Evolução Clínica: Capacidade Funcional vs. Dor", fontweight='bold', pad=15)
        ax_ev.set_ylim(-0.5, 11) # Margem para evitar que a linha toque na borda superior
        ax_ev.set_ylabel("Escala (0-10)")
        
        # AJUSTE DA LEGENDA: Fora do gráfico (abaixo) para não obstruir dados
        ax_ev.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
        
        # ESPAÇAMENTO DO EIXO X: Mostra sessões de 10 em 10 (S1, S11, S21...)
        indices = np.arange(0, len(df_p), 10)
        ax_ev.set_xticks(indices)
        ax_ev.set_xticklabels([df_p['Sessão_Num'].iloc[i] for i in indices], rotation=0)
        ax_ev.grid(True, alpha=0.1)
        
        plt.subplots_adjust(bottom=0.25) # Espaço extra para a legenda e rótulos
        buf_ev = io.BytesIO(); plt.savefig(buf_ev, format='png', bbox_inches='tight'); plt.close(fig_ev)

        # 2. Histórico de Inchaço (Stroke Test)
        fig_inc, ax_inc = plt.subplots(figsize=(10, 3.5))
        ax_inc.bar(df_p['Sessão_Num'].tail(20), df_p['Inchaco_N'].tail(20), color='#008091', alpha=0.8)
        ax_inc.set_title("Linha do Tempo: Inchaço Articular (Stroke Test)", fontweight='bold', pad=10)
        ax_inc.set_ylim(0, 3.5); ax_inc.set_ylabel("Grau (0-3)")
        ax_inc.grid(axis='y', alpha=0.1)
        buf_inc = io.BytesIO(); plt.savefig(buf_inc, format='png', bbox_inches='tight'); plt.close(fig_inc)

        # 3. Perfil de Capacidade Funcional (Barras)
        fig_cap, ax_cap = plt.subplots(figsize=(8, 5))
        testes = ['Agachamento', 'Step Up', 'Step Down']
        valores = [mapa[ultima['Agachamento']], mapa[ultima['Step_Up']], mapa[ultima['Step_Down']]]
        ax_cap.bar(testes, valores, color='#008091')
        ax_cap.set_title("Capacidade Funcional por Teste (Sessão Atual)", fontweight='bold', pad=10)
        ax_cap.set_ylim(0, 10.5); ax_cap.set_ylabel("Nota (0-10)")
        buf_cap = io.BytesIO(); plt.savefig(buf_cap, format='png', bbox_inches='tight'); plt.close(fig_cap)

        # 4. Análise do Sono vs. Dor (Área)
        fig_s, ax_s = plt.subplots(figsize=(10, 4))
        ax_s.fill_between(df_p['Sessão_Num'], df_p['Sono_N'], color='#008091', alpha=0.2, label='Qualidade do Sono')
        ax_s.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', marker='o', label='Nível de Dor')
        
        ax_s.set_title("Impacto Biopsicossocial: Qualidade do Sono vs. Dor", fontweight='bold', pad=15)
        ax_s.set_ylim(-0.5, 11)
        
        # AJUSTE DA LEGENDA: Abaixo do gráfico para não cobrir as crises de dor
        ax_s.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
        
        ax_s.set_xticks(indices)
        ax_s.set_xticklabels([df_p['Sessão_Num'].iloc[i] for i in indices])
        
        plt.subplots_adjust(bottom=0.3)
        buf_s = io.BytesIO(); plt.savefig(buf_s, format='png', bbox_inches='tight'); plt.close(fig_s)

        # Download PDF Master
        st.write("---")
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist_clinica = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: hist_clinica = "Anamnese não cadastrada."

        pdf_metrics = {'dor': ultima['Dor'], 'inchaco': ultima[col_inc], 'ikdc': u_ikdc, 'ikdc_emoji': emoji_ikdc, 'alta': prev_txt}
        pdf_bytes = create_pdf(p_sel, hist_clinica, pdf_metrics, {'ev': buf_ev, 'sono': buf_s, 'cap': buf_cap, 'inchaco': buf_inc})
        
        st.download_button("📥 BAIXAR RELATÓRIO CLÍNICO MASTER (PDF)", data=pdf_bytes, file_name=f"Relatorio_GENUA_{p_sel}.pdf")
        
        # ZenFisio Text
        st.info(f"Cópia ZenFisio: Evolução {p_sel} - Dor {ultima['Dor']}/10, Inchaço Grau {ultima[col_inc]}, IKDC {u_ikdc:.0f}/100.")
    else: st.info("Aguardando entrada de dados na planilha.")
