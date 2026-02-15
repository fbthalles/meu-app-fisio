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

# 1. CORES DA MARCA (Extraídas do seu Logo Oficial GENUA)
CORES_GENUA = {
    'primaria': '#5CA4D7',      # Azul claro do fundo do seu logo (Primária)
    'secundaria': '#33CFC4',    # Turquesa/Verde-água das letras "GENUA"
    'fundo_claro': '#F4F7F9',   # Um cinza/azul beeeeem clarinho para o fundo do app ficar chique
    'texto_escuro': '#2B3A4A',  # Azul marinho muito escuro para o texto (melhor que preto puro)
    'texto_suave': '#6c757d',   # Cinza médio
    'alerta_sucesso': '#28a745',# Verde
    'alerta_aviso': '#ffc107',  # Amarelo
    'alerta_erro': '#dc3545',   # Vermelho
}

# 2. CAMINHO DO NOVO LOGOTIPO
# ATENÇÃO THALLES: Troque o nome abaixo para o nome EXATO do arquivo que você fez upload!
# Exemplo: Se o arquivo chama "Logo_Genua.jpg", escreva "Logo_Genua.jpg" entre as aspas.
NOVO_LOGO_GENUA = "logo_genua_novo_v2.png" 

# 3. CONFIGURAÇÃO INICIAL DA PÁGINA 
st.set_page_config(
    page_title="GENUA | Inteligência Clínica",
    page_icon=NOVO_LOGO_GENUA, 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 4. APLICAÇÃO DO TEMA GLOBAL (CSS INJETADO)
st.markdown(f"""
    <style>
        .stApp {{
            background-color: {CORES_GENUA['fundo_claro']};
            color: {CORES_GENUA['texto_escuro']};
        }}
        h1, h2, h3 {{
            color: {CORES_GENUA['primaria']} !important;
        }}
        .stButton>button {{
            background-color: {CORES_GENUA['primaria']} !important;
            color: white !important;
            border: none;
            border-radius: 8px;
            font-weight: bold;
        }}
    </style>
""", unsafe_allow_html=True)

# 5. INJEÇÃO DO LOGO NA INTERFACE (BARRA LATERAL)
st.sidebar.image(NOVO_LOGO_GENUA, use_container_width=True)
st.sidebar.markdown("---") # Cria uma linha divisória elegante abaixo do logo

# ==========================================

# --- 1. FUNÇÕES DE SUPORTE E PDF ---

def limpar_texto_pdf(txt):
    """Garante que o PDF aceite acentuação e caracteres especiais do PT-BR."""
    if not isinstance(txt, str): return str(txt)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(p_name, hist, metrics, imgs):
    from fpdf import FPDF
    from datetime import datetime
    import io
    from PIL import Image
    
    def hex_to_rgb(hex_code):
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        
    cor_primaria_rgb = hex_to_rgb(CORES_GENUA['primaria'])

    class PDF_GENUA(FPDF):
        def footer(self):
            self.set_y(-15) 
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            hoje = datetime.now().strftime("%d/%m/%Y às %H:%M")
            self.cell(0, 10, f'GENUA Instituto | Inteligência Clínica | Emitido em {hoje} | Página {self.page_no()}', 0, 0, 'C')

    pdf = PDF_GENUA()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    azul_genua = cor_primaria_rgb 
    cinza_bg = (245, 245, 245) 
    cinza_txt = (80, 80, 80)
    
    # 1. CORES DAS CAIXAS DE INSIGHT
    bg_azul_claro = (209, 236, 241); txt_azul_escuro = (12, 84, 96)
    bg_amarelo_claro = (255, 243, 205); txt_amarelo_escuro = (133, 100, 4)
    bg_vermelho_claro = (248, 215, 218); txt_vermelho_escuro = (114, 28, 36)
    bg_verde_claro = (212, 237, 218); txt_verde_escuro = (21, 87, 36)

    # --- PARECERES CLÍNICOS DINÂMICOS ---
    if metrics['ikdc_status'] == 'Bom': par_ikdc = "Parecer Clínico: Excelente evolução. O paciente apresenta alta percepção de funcionalidade."
    elif metrics['ikdc_status'] == 'Regular': par_ikdc = "Parecer Clínico: Evolução moderada. Apresenta ganhos reais, mas demanda atenção fisioterapêutica."
    else: par_ikdc = "Parecer Clínico: Baixa funcionalidade percebida. Focar intensamente na modulação de sintomas."
        
    if metrics['alta'] not in ["Em análise", "Estabilizado"]: par_ev = f"Parecer Clínico: Cruzamento demonstra melhora. Projeção matemática de alta para {metrics['alta']}."
    else: par_ev = "Parecer Clínico: O gráfico mapeia a janela de tolerância. Foco atual em afastar a curva de função da curva de dor."

    grau_inc = int(float(metrics['inchaco']))
    if grau_inc <= 1: par_inc = "Parecer Clínico: Articulação estável (Grau 0-1). Cenário totalmente seguro para progressão."
    elif grau_inc == 2: par_inc = "Parecer Clínico: Presença de inchaço moderado (Alerta Amarelo). Recomendável estabilizar volume de treino."
    else: par_inc = "Parecer Clínico: Derrame articular importante (Alerta Vermelho). Imperativo regredir a sobrecarga mecânica."

    # LÓGICA DO INSIGHT ÁLGICO (DOR) RECUPERADO
    dor_atual = float(metrics['dor'])
    media_dor = float(metrics['media_dor'])
    
    if dor_atual < media_dor:
        par_dor = f"Parecer Clínico: A dor atual ({int(dor_atual)}) está abaixo da média ({media_dor:.1f}), indicando dessensibilização efetiva."
        insight_dor_texto = "Quadro álgico em regressão. O paciente responde bem às estratégias analgésicas e a tolerância mecânica está aumentando."
        cor_bg_dor = bg_verde_claro; cor_txt_dor = txt_verde_escuro
    elif dor_atual == media_dor:
        par_dor = f"Parecer Clínico: Quadro álgico estabilizado na média ({media_dor:.1f}). Foco em romper o platô de sintomas."
        insight_dor_texto = "O paciente encontra-se em platô álgico. Necessário reavaliar variáveis de carga ou introduzir novos estímulos analgésicos."
        cor_bg_dor = bg_amarelo_claro; cor_txt_dor = txt_amarelo_escuro
    else:
        par_dor = f"Parecer Clínico: A dor atual ({int(dor_atual)}) encontra-se acima da média ({media_dor:.1f}). Recomenda-se reforço analgésico."
        insight_dor_texto = "Alerta de Hiperalgesia. A dor superou a média histórica do tratamento. Priorizar modulação de sintomas imediatamente."
        cor_bg_dor = bg_vermelho_claro; cor_txt_dor = txt_vermelho_escuro

    def get_img_height(img_buffer, pdf_width):
        img_buffer.seek(0)
        with Image.open(img_buffer) as im: return pdf_width * (im.height / im.width)

    def desenhar_caixa_insight(titulo, texto, cor_bg, cor_txt):
        pdf.ln(3)
        pdf.set_fill_color(*cor_bg); pdf.set_text_color(*cor_txt)
        pdf.set_font("helvetica", 'B', 9)
        texto_limpo = str(texto).replace("Parecer Biopsicossocial: ", "").replace("Evolução Ideal: ", "")
        pdf.cell(0, 6, limpar_texto_pdf(f" {titulo} "), ln=True, fill=True)
        pdf.set_font("helvetica", '', 9)
        pdf.multi_cell(0, 5, limpar_texto_pdf(f" {texto_limpo} "), fill=True)
        pdf.ln(3)

    # ==========================================
    # --- PÁGINA 1: SNAPSHOT EXECUTIVO E EVOLUÇÃO ---
    # ==========================================
    pdf.add_page()
    try:
        img_logo = Image.open(NOVO_LOGO_GENUA).convert("RGBA")
        fundo_branco = Image.new("RGBA", img_logo.size, "WHITE")
        fundo_branco.paste(img_logo, (0, 0), img_logo)
        buf_logo = io.BytesIO()
        fundo_branco.convert('RGB').save(buf_logo, format="PNG")
        buf_logo.seek(0)
        pdf.image(buf_logo, x=10, y=8, w=35) 
    except Exception as e: 
        pdf.set_font("helvetica", 'B', 14); pdf.cell(0, 10, "GENUA INSTITUTO", ln=True, align='C')
    
    pdf.ln(12)
    pdf.set_font("helvetica", 'B', 13)
    pdf.cell(0, 8, limpar_texto_pdf("RELATÓRIO DE INTELIGÊNCIA CLÍNICA"), ln=True, align='C')
    
    pdf.set_font("helvetica", 'B', 10); pdf.set_text_color(*azul_genua)
    pdf.cell(0, 6, limpar_texto_pdf(f"PACIENTE: {p_name.upper()}"), ln=True, align='C')
    pdf.set_font("helvetica", 'I', 9); pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, limpar_texto_pdf(f"Anamnese Base: {hist}"), align='C')
    pdf.ln(6)

    # GRID EXECUTIVO
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 9)
    w_col = 47.5 
    pdf.cell(w_col, 7, limpar_texto_pdf("DOR ATUAL"), border=1, fill=True, align='C')
    pdf.cell(w_col, 7, limpar_texto_pdf("INCHAÇO"), border=1, fill=True, align='C')
    pdf.cell(w_col, 7, limpar_texto_pdf("IKDC (FUNÇÃO)"), border=1, fill=True, align='C')
    pdf.cell(w_col, 7, limpar_texto_pdf("PREVISÃO ALTA"), border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_fill_color(*cinza_bg); pdf.set_text_color(0, 0, 0); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{int(dor_atual)}/10"), border=1, fill=True, align='C')
    pdf.cell(w_col, 8, limpar_texto_pdf(f"Grau {grau_inc}"), border=1, fill=True, align='C')
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{int(float(metrics['ikdc']))}/100"), border=1, fill=True, align='C')
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{metrics['alta']}"), border=1, fill=True, align='C')
    pdf.ln(10)

    # 1. EVOLUÇÃO CLÍNICA
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 1. EVOLUÇÃO CLÍNICA (FUNÇÃO VS. DOR)"), ln=True, fill=True, align='C')
    y_ev = pdf.get_y() + 4
    pdf.image(imgs['ev'], x=20, y=y_ev, w=170) 
    
    margem_y = max(125, get_img_height(imgs['ev'], 170))
    pdf.set_y(y_ev + margem_y + 2) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_ev), align='C')
    
    desenhar_caixa_insight("💡 INSIGHT EVOLUTIVO", metrics['insight_evolucao'], bg_azul_claro, txt_azul_escuro)

    # ==========================================
    # --- PÁGINA 2: DOR ISOLADA (Página Própria) ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 2. COMPORTAMENTO DA DOR"), ln=True, fill=True, align='C')
    y_dor = pdf.get_y() + 4
    pdf.image(imgs['dor'], x=20, y=y_dor, w=170)
    
    margem_y = max(125, get_img_height(imgs['dor'], 170))
    pdf.set_y(y_dor + margem_y + 2) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_dor), align='C')
    
    # Injeção do Insight Álgico Faltante
    desenhar_caixa_insight("🧠 INSIGHT ÁLGICO", insight_dor_texto, cor_bg_dor, cor_txt_dor)

    # ==========================================
    # --- PÁGINA 3: INCHAÇO (Página Própria para não vazar) ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 3. MONITORAMENTO DE INCHAÇO"), ln=True, fill=True, align='C')
    y_inc = pdf.get_y() + 4
    pdf.image(imgs['inchaco'], x=20, y=y_inc, w=170)
    
    margem_y = max(125, get_img_height(imgs['inchaco'], 170))
    pdf.set_y(y_inc + margem_y + 2) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_inc), align='C')
    
    desenhar_caixa_insight("⚠️ INSIGHT MECÂNICO", metrics['insight_mecanico'], bg_amarelo_claro, txt_amarelo_escuro)

    # ==========================================
    # --- PÁGINA 4: BIOPSICOSSOCIAL E FATORES EXTERNOS ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 4. ANÁLISE BIOPSICOSSOCIAL E FATORES EXTERNOS"), ln=True, fill=True, align='C')
    y_sono = pdf.get_y() + 4
    pdf.image(imgs['sono'], x=20, y=y_sono, w=170)
    
    margem_y = max(125, get_img_height(imgs['sono'], 170))
    pdf.set_y(y_sono + margem_y + 2) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf("Parecer Clínico: O gráfico acima ilustra a interação do sono com a dor. Abaixo, os diagnósticos cruzados da Inteligência Artificial sobre fatores modificáveis."), align='C')
    
    desenhar_caixa_insight("💤 INSIGHT DO SONO", metrics['insight_ouro'], bg_verde_claro, txt_verde_escuro)
    
    # Texto de Postura agora separado e contextualizado
    desenhar_caixa_insight("🔴 INSIGHT POSTURAL (GATILHO BIOMECÂNICO)", metrics['insight_postura'], bg_vermelho_claro, txt_vermelho_escuro)

    return bytes(pdf.output())

# --- 2. INTERFACE E CONEXÃO ---
st.set_page_config(page_title="GENUA Intelligence", layout="wide", page_icon="🏥")
conn = st.connection("gsheets", type=GSheetsConnection)

with st.sidebar:
    try: st.image("NOVO_LOGO_GENUA", width=220)
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

else: # PAINEL ANALÍTICO (O CÉREBRO CLÍNICO TOTAL)
    st.header("📊 Painel Analítico & Clinical Intelligence")
    df = conn.read(ttl=0).dropna(how="all")
    
    if not df.empty:
        lista_pacientes = df['Paciente'].dropna().unique()
        
        p_sel = st.selectbox(
            "🔍 Buscar Paciente:", 
            options=lista_pacientes,
            index=None, 
            placeholder="Digite 3 letras do nome..."
        )
        
        if p_sel is None:
            st.info("👆 Por favor, digite o nome ou selecione um paciente acima para carregar a inteligência.")
            st.stop()
            
        df_p = df[df['Paciente'] == p_sel].copy()
        
        # 1. PROCESSAMENTO DE DADOS E EIXO X (DE 5 EM 5 SESSÕES)
        df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]
        mapa_func = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        df_p['Score_Função'] = (df_p['Agachamento'].map(mapa_func) + df_p['Step_Up'].map(mapa_func) + df_p['Step_Down'].map(mapa_func)) / 3
        df_p['Sono_N'] = df_p['Sono'].map({"Ruim": 1, "Regular": 5, "Bom": 10})
        col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
        df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)
        ultima = df_p.iloc[-1]

        # Intervalos de 5 sessões para o Eixo X em todos os gráficos
        indices_5 = np.arange(0, len(df_p), 5)
        labels_5 = [df_p['Sessão_Num'].iloc[i] for i in indices_5]

        # CÁLCULO DE TENDÊNCIA E PREVISÃO DE ALTA
        try:
            df_p['Data_DT'] = pd.to_datetime(df_p['Data'], dayfirst=True)
            df_p['Dias'] = (df_p['Data_DT'] - df_p['Data_DT'].min()).dt.days
            z = np.polyfit(df_p['Dias'].values, df_p['Score_Função'].values, 1)
            trend_line = z[0] * df_p['Dias'].values + z[1]
            dia_estimado_alta = (9.0 - z[1]) / z[0] if z[0] > 0 else 0
            prev_txt = (df_p['Data_DT'].min() + pd.to_timedelta(dia_estimado_alta, unit='d')).strftime("%d/%m/%Y") if dia_estimado_alta > 0 else "Estabilizado"
        except: 
            trend_line = []
            prev_txt = "Em análise"

        # SCORE CIENTÍFICO IKDC
        try:
            df_ikdc = conn.read(worksheet="IKDC", ttl=0)
            u_ikdc = float(df_ikdc[df_ikdc['Paciente'].str.strip() == p_sel]['Score_IKDC'].values[-1])
            status_clinico = "Bom" if u_ikdc > 70 else "Regular" if u_ikdc > 45 else "Severo"
            emoji_ikdc = "🏆" if status_clinico == "Bom" else "🟢" if status_clinico == "Regular" else "🔴"
        except: 
            u_ikdc = 0; emoji_ikdc = "⚪"; status_clinico = "Pendente"

        # 2. GERAÇÃO DE GRÁFICOS (FIX ABSOLUTO DE LEGENDAS E VISIBILIDADE)
        
        # A) Evolução Clínica
        fig_ev, ax_ev = plt.subplots(figsize=(10, 5))
        ax_ev.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', label='Nível de Dor (EVA)', marker='o', linewidth=2)
        ax_ev.plot(df_p['Sessão_Num'], df_p['Score_Função'], color='#008091', label='Capacidade Funcional', marker='s', linewidth=3)
        if len(trend_line) > 0:
            ax_ev.plot(df_p['Sessão_Num'], trend_line, '--', color='#5D6D7E', alpha=0.5, label='Tendência de Alta')
        
        ax_ev.set_title("Evolução Clínica: Capacidade Funcional vs. Dor", fontweight='bold')
        ax_ev.set_ylim(-0.5, 11)
        ax_ev.set_xticks(indices_5)
        ax_ev.set_xticklabels(labels_5)
        
        lgd_ev = ax_ev.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
        buf_ev = io.BytesIO()
        fig_ev.savefig(buf_ev, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_ev,), dpi=150)
        buf_ev.seek(0); plt.close(fig_ev)

        # B) Novo Gráfico: Dor Isolada (Preenchimento Visual Vermelho)
        fig_dor, ax_dor = plt.subplots(figsize=(10, 3.5))
        # fill_between cria uma "área" colorida abaixo da linha, muito visual para o paciente
        ax_dor.fill_between(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', alpha=0.2)
        ax_dor.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', label='Nível de Dor (EVA)', marker='o', linewidth=2)
        ax_dor.set_title("Comportamento Isolado da Dor (Quadro Álgico)", fontweight='bold')
        ax_dor.set_ylim(-0.5, 11)
        ax_dor.set_xticks(indices_5)
        ax_dor.set_xticklabels(labels_5)
        
        lgd_dor = ax_dor.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), frameon=False, fontsize=9)
        buf_dor = io.BytesIO()
        fig_dor.savefig(buf_dor, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_dor,), dpi=150)
        buf_dor.seek(0); plt.close(fig_dor)

        # C) Inchaço Articular (Cores de Alerta e Legenda Customizada)
        fig_inc, ax_inc = plt.subplots(figsize=(10, 3.5))
        cores_inc = ['#D32F2F' if x == 3 else '#FFB300' if x == 2 else '#008091' for x in df_p['Inchaco_N']]
        ax_inc.bar(df_p['Sessão_Num'], df_p['Inchaco_N'], color=cores_inc, alpha=0.8)
        
        ax_inc.set_title("Linha do Tempo: Inchaço Articular", fontweight='bold')
        ax_inc.set_ylim(0, 3.5)
        ax_inc.set_xticks(indices_5)
        ax_inc.set_xticklabels(labels_5)
        
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#D32F2F', alpha=0.8, label='Grau 3 (Grave)'),
            Patch(facecolor='#FFB300', alpha=0.8, label='Grau 2 (Moderado)'),
            Patch(facecolor='#008091', alpha=0.8, label='Grau 0-1 (Estável)')
        ]
        lgd_inc = ax_inc.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=3, frameon=False, fontsize=9)
        
        buf_inc = io.BytesIO()
        fig_inc.savefig(buf_inc, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_inc,), dpi=150)
        buf_inc.seek(0); plt.close(fig_inc)

        # D) Sono vs Dor
        fig_s, ax_s = plt.subplots(figsize=(10, 4))
        ax_s.fill_between(df_p['Sessão_Num'], df_p['Sono_N'], color='#008091', alpha=0.2, label='Qualidade do Sono')
        ax_s.plot(df_p['Sessão_Num'], df_p['Dor'], color='#FF4B4B', marker='o', label='Nível de Dor')
        
        ax_s.set_title("Impacto Biopsicossocial: Sono vs Dor", fontweight='bold')
        ax_s.set_ylim(-0.5, 11)
        ax_s.set_xticks(indices_5)
        ax_s.set_xticklabels(labels_5)
        
        lgd_s = ax_s.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
        buf_s = io.BytesIO(); fig_s.savefig(buf_s, format='png', bbox_inches='tight', bbox_extra_artists=(lgd_s,), dpi=150); buf_s.seek(0); plt.close(fig_s)

        # 3. MOTORES MATEMÁTICOS DE CRUZAMENTO E INSIGHTS
        media_dor = df_p['Dor'].mean()
        delta_dor_pct = ((ultima['Dor'] - media_dor) / media_dor * 100) if media_dor > 0 else (100 if ultima['Dor'] > 0 else 0)
        
        media_inc = df_p['Inchaco_N'].mean()
        delta_inc_pct = ((ultima['Inchaco_N'] - media_inc) / media_inc * 100) if media_inc > 0 else (100 if ultima['Inchaco_N'] > 0 else 0)

        # Insight 1: Sono vs Dor (Biopsicossocial)
        try:
            media_sono = df_p['Sono_N'].mean()
            dor_sono_bom = df_p[df_p['Sono_N'] >= media_sono]['Dor'].mean()
            dor_sono_ruim = df_p[df_p['Sono_N'] < media_sono]['Dor'].mean()
            if pd.notna(dor_sono_bom) and pd.notna(dor_sono_ruim) and dor_sono_ruim > 0 and dor_sono_bom < dor_sono_ruim:
                queda_pct = ((dor_sono_ruim - dor_sono_bom) / dor_sono_ruim) * 100
                insight_ouro = f"Parecer Biopsicossocial: Quando o paciente relata um sono superior à sua média, o nível de dor cai em {queda_pct:.0f}%. O manejo do sono atua como forte inibidor analgésico."
            else:
                insight_ouro = "Parecer Biopsicossocial: A correlação entre qualidade do sono e percepção de dor mantém-se dentro do desvio padrão esperado, sem discrepâncias agudas."
        except:
            insight_ouro = "Monitoramento contínuo em andamento para estabelecer correlação álgica com o sono."

        # Insight 2: Inchaço vs Função (Inibição Mecânica)
        try:
            func_inc_alto = df_p[df_p['Inchaco_N'] >= 2]['Score_Função'].mean()
            func_inc_baixo = df_p[df_p['Inchaco_N'] <= 1]['Score_Função'].mean()
            if pd.notna(func_inc_alto) and pd.notna(func_inc_baixo) and func_inc_baixo > 0 and func_inc_alto < func_inc_baixo:
                queda_func = ((func_inc_baixo - func_inc_alto) / func_inc_baixo) * 100
                insight_mecanico = f"A presença de inchaço moderado/grave reduz a capacidade funcional em {queda_func:.0f}%. A resolução do derrame articular é o principal limitante para progressão de carga."
            else:
                insight_mecanico = "O paciente demonstra capacidade de manter sua funcionalidade de forma independente das flutuações de efusão articular."
        except:
            insight_mecanico = "Aguardando mais avaliações para correlacionar o impacto do inchaço na função."

        # Insight 3: Postura vs Dor (Gatilho Biomecânico)
        try:
            if 'Postura' in df_p.columns and not df_p['Postura'].empty:
                pior_postura = df_p.groupby('Postura')['Dor'].mean().idxmax()
                dor_pior = df_p.groupby('Postura')['Dor'].mean().max()
                dor_outras = df_p[df_p['Postura'] != pior_postura]['Dor'].mean()
                if pd.notna(dor_pior) and pd.notna(dor_outras) and dor_outras > 0 and dor_pior > dor_outras:
                    aumento_pct = ((dor_pior - dor_outras) / dor_outras) * 100
                    insight_postura = f"A postura '{pior_postura}' atua como gatilho biomecânico primário, elevando o quadro álgico em {aumento_pct:.0f}% em relação às demais posições da rotina."
                else:
                    insight_postura = "Não há evidências de um gatilho postural isolado que exacerbe drasticamente os sintomas."
            else:
                insight_postura = "Dados posturais insuficientes para análise biomecânica."
        except:
            insight_postura = "Aguardando volume de dados para mapeamento de gatilho postural."

        # Insight 4: Evolução Clínica (Função vs Dor)
        try:
            dor_ini = df_p['Dor'].iloc[0]
            dor_atu = ultima['Dor']
            func_ini = df_p['Score_Função'].iloc[0]
            func_atu = ultima['Score_Função']
            
            if func_atu > func_ini and dor_atu < dor_ini:
                ganho_f = ((func_atu - func_ini) / func_ini * 100) if func_ini > 0 else 100
                queda_d = ((dor_ini - dor_atu) / dor_ini * 100) if dor_ini > 0 else 100
                insight_evolucao = f"Evolução Ideal: O paciente aumentou sua capacidade funcional em {ganho_f:.0f}% enquanto reduziu a dor em {queda_d:.0f}%. Ganhos reais de tolerância mecânica."
            elif func_atu > func_ini and dor_atu >= dor_ini:
                insight_evolucao = "Atenção: Houve ganho funcional, mas com custo álgico. O paciente pode estar operando no limite ou acima da sua janela de tolerância atual."
            elif func_atu <= func_ini and dor_atu < dor_ini:
                insight_evolucao = "Fase Analgésica: O tratamento reduziu a dor com sucesso, porém a capacidade funcional ainda não apresenta progressão em relação ao início."
            else:
                insight_evolucao = "Alerta Clínico: Sem progressão funcional e sem alívio da dor comparado ao início do tratamento. Recomenda-se reavaliar o plano terapêutico."
        except:
            insight_evolucao = "Aguardando volume de dados para calcular o ganho percentual de função vs. dor."

        # Insight 5: Comportamento Isolado da Dor (Inteligência de Cores para o Painel)
        dor_atual = ultima['Dor']
        if dor_atual < media_dor:
            insight_dor = f"A dor atual ({int(dor_atual)}) está abaixo da média histórica ({media_dor:.1f}), indicando dessensibilização efetiva."
            cor_dor = "success"
        elif dor_atual == media_dor:
            insight_dor = f"O quadro álgico encontra-se estabilizado na média ({media_dor:.1f}). Foco em romper o platô de sintomas."
            cor_dor = "warning"
        else:
            insight_dor = f"A dor atual ({int(dor_atual)}) encontra-se acima da média ({media_dor:.1f}). Recomenda-se reforço analgésico."
            cor_dor = "error"

        # 4. DASHBOARD TELA
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dor Atual (vs Média)", f"{ultima['Dor']}/10", f"{delta_dor_pct:.0f}%", delta_color="inverse")
        m2.metric("Inchaço (vs Média)", f"Grau {ultima[col_inc]}", f"{delta_inc_pct:.0f}%", delta_color="inverse")
        m3.metric("IKDC", f"{int(u_ikdc)}/100", status_clinico)
        m4.metric("Previsão Alta", prev_txt)

        st.write("---")
        t1, t2, t3, t4 = st.tabs(["📈 Evolução & IA", "🩸 Dor Isolada", "🌊 Inchaço", "🎯 Fatores Externos"])
        
        with t1: 
            st.image(buf_ev, use_container_width=True)
            st.success(f"🔮 **Inteligência GENUA:** Alta estimada para **{prev_txt}**.")
            st.info(f"💡 **Insight Evolutivo:** {insight_evolucao}")
            
        with t2:
            st.image(buf_dor, use_container_width=True)
            # Injeção dinâmica do alerta com base na cor/gravidade calculada
            if cor_dor == "success": st.success(f"💡 **Insight Álgico:** {insight_dor}")
            elif cor_dor == "warning": st.warning(f"💡 **Insight Álgico:** {insight_dor}")
            else: st.error(f"💡 **Insight Álgico:** {insight_dor}")
            
        with t3: 
            st.image(buf_inc, use_container_width=True)
            st.warning(f"💡 **Insight Mecânico:** {insight_mecanico}")
            
        with t4: 
            st.image(buf_s, use_container_width=True)
            st.info(f"💡 **Insight do Sono:** {insight_ouro.replace('Parecer Biopsicossocial: ', '')}")
            
            st.write("**Análise de Postura vs. Dor**")
            st.altair_chart(alt.Chart(df_p).mark_bar(color='#008091').encode(
                x=alt.X('Postura', title='Postura'),
                y=alt.Y('mean(Dor)', title='Média de Dor'),
                tooltip=['Postura', 'mean(Dor)']
            ), use_container_width=True)
            st.error(f"💡 **Insight Postural:** {insight_postura}")

        # 5. PREPARAÇÃO E DOWNLOAD DO PDF
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            hist_clinica = df_cad[df_cad['Nome'].str.strip() == p_sel]['Historia'].values[0]
        except: 
            hist_clinica = "Anamnese não cadastrada no sistema."

        pdf_metrics = {
            'ikdc': u_ikdc, 'ikdc_status': status_clinico, 
            'dor': ultima['Dor'], 'media_dor': media_dor,
            'inchaco': ultima[col_inc], 'alta': prev_txt,
            'insight_ouro': insight_ouro,
            'insight_mecanico': insight_mecanico,
            'insight_postura': insight_postura,
            'insight_evolucao': insight_evolucao
        }
        
        pdf_bytes = create_pdf(p_sel, hist_clinica, pdf_metrics, {
            'ev': buf_ev, 'dor': buf_dor, 'sono': buf_s, 'inchaco': buf_inc
        })
        
        st.download_button("📥 BAIXAR RELATÓRIO MASTER (PDF)", data=pdf_bytes, file_name=f"Relatorio_GENUA_{p_sel}.pdf")
        st.info(f"📝 ZenFisio: {p_sel} - Dor {ultima['Dor']}, IKDC {int(u_ikdc)}, Alta est. {prev_txt}.")
    else:
        st.info("Aguardando entrada de dados na planilha.")
