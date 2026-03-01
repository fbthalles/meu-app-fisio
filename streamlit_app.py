import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
import numpy as np
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt
import io

# 1. CORES DA MARCA (Extraídas do novo Logo GENUA Transparente)
CORES_GENUA = {
    'primaria': '#103E55',      # Azul-Petróleo Escuro (Cor das letras GENUA, traz autoridade e seriedade)
    'secundaria': '#398E9B',    # Verde-Água/Teal Claro (Destaques do joelho, traz frescor e modernidade)
    'fundo_claro': '#F4F7F9',   # Cinza Gelo levemente azulado para um fundo clínico e limpo
    'texto_escuro': '#1A252C',  # Um cinza-chumbo profundo (muito mais elegante que o preto puro)
    'texto_suave': '#6c757d',   # Cinza médio para legendas discretas
    'alerta_sucesso': '#28a745',# Verde padrão (positivo)
    'alerta_aviso': '#ffc107',  # Amarelo padrão (atenção)
    'alerta_erro': '#dc3545',   # Vermelho padrão (alerta grave)
}

# 2. CAMINHO DO NOVO LOGOTIPO

NOVO_LOGO_GENUA = "logo_genua_novo_v2.png" 

# 3. CONFIGURAÇÃO INICIAL DA PÁGINA 
st.set_page_config(
    page_title="GENUA | Inteligência Clínica",
    page_icon=NOVO_LOGO_GENUA, 
    layout="wide",
    initial_sidebar_state="expanded" # <-- FORÇA A BARRA ABRIR POR PADRÃO
)

# --- 3.1 E 4. INJEÇÃO DE CSS UNIFICADA (UX PREMIUM E APP NAVIGATION) ---
st.markdown(f"""
    <style>
    /* 1. Tipografia e Reset */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
    
    /* 2. Remoção do Branding */
    #MainMenu, footer, .stDeployButton, .stStatusWidget {{ display: none !important; }}
    header {{ background-color: transparent !important; }}

    /* 3. Container Principal */
    .stApp {{
        background: linear-gradient(180deg, {CORES_GENUA['fundo_claro']} 0%, #FFFFFF 100%);
        color: {CORES_GENUA['texto_escuro']};
    }}
    [data-testid="block-container"] {{
        padding-top: 3.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 5% !important;
        padding-right: 5% !important;
        max-width: 1200px !important;
    }}
    
    h1, h2, h3, h4 {{ color: {CORES_GENUA['primaria']} !important; }}

    /* 4. Correção de Cortes em Inputs e Selectboxes */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox [data-baseweb="select"] {{
        border-radius: 12px !important;
        border: 1px solid #E2E8F0 !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
        padding: 10px 14px !important;
        line-height: 1.5 !important;
        min-height: 48px !important;
    }}

    /* 5. Botões Nativos (Primários vs Navegação) */
    .stButton > button {{
        background: linear-gradient(135deg, {CORES_GENUA['primaria']} 0%, #1A5473 100%) !important;
        color: white !important;
        border-radius: 14px !important;
        border: none !important;
        padding: 14px 24px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 10px rgba(16, 62, 85, 0.2) !important;
        width: 100% !important;
        min-height: 50px !important;
        transition: all 0.2s ease-in-out !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px rgba(16, 62, 85, 0.3) !important;
    }}
    
    /* Botão Voltar (Estilo Link App Nativo) */
    .stButton > button[kind="secondary"] {{
        background: transparent !important;
        color: {CORES_GENUA['texto_suave']} !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        padding: 8px 16px !important;
        min-height: 40px !important;
        width: auto !important;
        font-weight: 600 !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        color: {CORES_GENUA['primaria']} !important;
        background-color: #F1F5F9 !important;
        transform: translateX(-4px) !important; /* Animação de voltar */
    }}

    /* 6. Cards e Abas (Tabs) */
    [data-testid="metric-container"] {{
        background-color: #FFFFFF; border-radius: 16px; padding: 24px 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.05); border: 1px solid #F0F4F8;
        border-left: 6px solid {CORES_GENUA['secundaria']}; margin-bottom: 10px;
    }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 15px; border-bottom: none !important; }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 30px !important; padding: 12px 24px !important;
        background-color: #F4F7F9 !important; color: #6C757D !important; font-weight: 600 !important;
    }}
    .stTabs [aria-selected="true"] {{ background-color: {CORES_GENUA['primaria']} !important; color: white !important; }}
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
    import os
    from PIL import Image
    import urllib.request
    import urllib.parse
    
    def hex_to_rgb(hex_code):
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        
    cor_primaria_rgb = hex_to_rgb(CORES_GENUA['primaria'])

    # 1. ENGENHARIA DO LOGO: Cria uma versão segura (sem transparência) para o FPDF repetir em todas as páginas
    logo_pdf_path = "temp_logo_pdf.jpg"
    try:
        img_logo = Image.open(NOVO_LOGO_GENUA).convert("RGBA")
        fundo_branco = Image.new("RGBA", img_logo.size, "WHITE")
        fundo_branco.paste(img_logo, (0, 0), img_logo)
        fundo_branco.convert('RGB').save(logo_pdf_path, format="JPEG", quality=95)
    except:
        logo_pdf_path = None

    class PDF_GENUA(FPDF):
        def footer(self):
            self.set_y(-15) 
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            hoje = datetime.now().strftime("%d/%m/%Y às %H:%M")
            self.cell(0, 10, f'GENUA Instituto | Inteligência Clínica | Emitido em {hoje} | Página {self.page_no()}', 0, 0, 'C')
            
            # UX VISUAL: Injeta o logo no canto inferior direito de TODAS as páginas como chancela
            if logo_pdf_path:
                try:
                    self.image(logo_pdf_path, x=175, y=self.get_y() + 1, w=22)
                except:
                    pass

    pdf = PDF_GENUA()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    azul_genua = cor_primaria_rgb 
    cinza_bg = (245, 245, 245) 
    cinza_txt = (80, 80, 80)
    
    # 2. CORES DAS CAIXAS DE INSIGHT
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

    # LÓGICA DO INSIGHT ÁLGICO (DOR)
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
    
    if logo_pdf_path:
        pdf.image(logo_pdf_path, x=10, y=8, w=35)
    else:
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
    pdf.cell(w_col, 7, limpar_texto_pdf("PRONTIDÃO (LSI)"), border=1, fill=True, align='C')
    pdf.cell(w_col, 7, limpar_texto_pdf("PREVISÃO ALTA"), border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_fill_color(*cinza_bg); pdf.set_text_color(0, 0, 0); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{int(dor_atual)}/10"), border=1, fill=True, align='C')
    pdf.cell(w_col, 8, limpar_texto_pdf(f"Grau {grau_inc}"), border=1, fill=True, align='C')
    
    # Extrai o valor do LSI (que agora transita na variável ikdc internamente) e formata com %
    try:
        valor_lsi = float(metrics.get('ikdc', 0))
    except:
        valor_lsi = 0.0
        
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{valor_lsi:.0f}%"), border=1, fill=True, align='C')
    pdf.cell(w_col, 8, limpar_texto_pdf(f"{metrics.get('alta', 'Em análise')}"), border=1, fill=True, align='C')
    pdf.ln(10)

    # 1. EVOLUÇÃO CLÍNICA
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 1. EVOLUÇÃO CLÍNICA (FUNÇÃO VS. DOR)"), ln=True, fill=True, align='C')
    y_ev = pdf.get_y() + 4
    pdf.image(imgs['ev'], x=20, y=y_ev, w=170) 
    
    pdf.set_y(y_ev + get_img_height(imgs['ev'], 170) + 5) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_ev), align='C')
    desenhar_caixa_insight("💡 INSIGHT EVOLUTIVO", metrics['insight_evolucao'], bg_azul_claro, txt_azul_escuro)

    # ==========================================
    # --- PÁGINA 2: DOR ISOLADA ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 2. COMPORTAMENTO DA DOR"), ln=True, fill=True, align='C')
    y_dor = pdf.get_y() + 4
    pdf.image(imgs['dor'], x=20, y=y_dor, w=170)
    
    pdf.set_y(y_dor + get_img_height(imgs['dor'], 170) + 5) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_dor), align='C')
    desenhar_caixa_insight("🧠 INSIGHT ÁLGICO", insight_dor_texto, cor_bg_dor, cor_txt_dor)

    # ==========================================
    # --- PÁGINA 3: INCHAÇO ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 3. MONITORAMENTO DE INCHAÇO"), ln=True, fill=True, align='C')
    y_inc = pdf.get_y() + 4
    pdf.image(imgs['inchaco'], x=20, y=y_inc, w=170)
    
    pdf.set_y(y_inc + get_img_height(imgs['inchaco'], 170) + 5) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf(par_inc), align='C')
    desenhar_caixa_insight("⚠️ INSIGHT MECÂNICO", metrics['insight_mecanico'], bg_amarelo_claro, txt_amarelo_escuro)

    # ==========================================
    # --- PÁGINA 4: BIOPSICOSSOCIAL E QR CODE ---
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, limpar_texto_pdf(" 4. ANÁLISE BIOPSICOSSOCIAL E FATORES EXTERNOS"), ln=True, fill=True, align='C')
    y_sono = pdf.get_y() + 4
    pdf.image(imgs['sono'], x=20, y=y_sono, w=170)
    
    pdf.set_y(y_sono + get_img_height(imgs['sono'], 170) + 5) 
    
    pdf.set_text_color(*cinza_txt); pdf.set_font("helvetica", 'I', 9)
    pdf.multi_cell(0, 5, limpar_texto_pdf("Parecer Clínico: O gráfico acima ilustra a interação do sono com a dor. Abaixo, os diagnósticos cruzados da Inteligência Artificial sobre fatores modificáveis."), align='C')
    
    desenhar_caixa_insight("💤 INSIGHT DO SONO", metrics['insight_ouro'], bg_verde_claro, txt_verde_escuro)
    desenhar_caixa_insight("🔴 INSIGHT POSTURAL (GATILHO BIOMECÂNICO)", metrics['insight_postura'], bg_vermelho_claro, txt_vermelho_escuro)

    # ==========================================
    # --- PÁGINA 5: CRUZAMENTO BIOMECÂNICO (ADM) ---
    # ==========================================
    if 'adm' in imgs:
        pdf.add_page()
        pdf.set_fill_color(*azul_genua); pdf.set_text_color(255, 255, 255); pdf.set_font("helvetica", 'B', 10)
        pdf.cell(0, 7, limpar_texto_pdf(" 5. CRUZAMENTO BIOMECÂNICO (ADM x DOR x INCHAÇO)"), ln=True, fill=True, align='C')
        y_adm = pdf.get_y() + 4
        pdf.image(imgs['adm'], x=20, y=y_adm, w=170)
        
        pdf.set_y(y_adm + get_img_height(imgs['adm'], 170) + 5)
        desenhar_caixa_insight("📐 PARECER BIOMECÂNICO", metrics['insight_mecanico'], bg_azul_claro, txt_azul_escuro)

    # --- NOVO: BLOCO DE ASSINATURA E QR CODE ---
    pdf.ln(10)
    y_assinatura = pdf.get_y()
    
    # Gerador de QR Code Seguro (Via API)
    try:
        # ATENÇÃO: Substitua o número abaixo pelo WhatsApp da sua clínica
        link_agendamento = "https://wa.me/+5511933660220?text=Olá,%20gostaria%20de%20agendar%20meu%20retorno."
        url_qr = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link_agendamento)}"
        
        req = urllib.request.Request(url_qr, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            buf_qr = io.BytesIO(response.read())
            
        pdf.image(buf_qr, x=20, y=y_assinatura, w=28)
    except:
        pass # Se a internet falhar, o PDF é gerado normalmente sem quebrar o app
        
    pdf.set_y(y_assinatura + 4)
    pdf.set_x(52)
    pdf.set_font("helvetica", 'B', 11)
    pdf.set_text_color(*azul_genua)
    pdf.cell(0, 5, limpar_texto_pdf("DR. THALLES - FISIOTERAPIA ESPORTIVA"), ln=True)
    
    pdf.set_x(52)
    pdf.set_font("helvetica", '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, limpar_texto_pdf("Especialista em Reabilitação e Inteligência Clínica"), ln=True)
    
    pdf.set_x(52)
    pdf.set_font("helvetica", 'I', 8)
    pdf.cell(0, 5, limpar_texto_pdf("Aponte a câmera do celular para o QR Code ao lado para agendar seu retorno,"), ln=True)
    pdf.set_x(52)
    pdf.cell(0, 5, limpar_texto_pdf("acessar sua cartilha de exercícios ou falar diretamente com nossa equipe."), ln=True)

    # Faxina de sistema: Remove o arquivo temporário gerado
    try:
        if os.path.exists(logo_pdf_path):
            os.remove(logo_pdf_path)
    except:
        pass 
    return bytes(pdf.output())

# --- 2. INTERFACE E CONEXÃO (ARQUITETURA FIREBASE) ---
import json
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred_dict = json.loads(st.secrets["FIREBASE_JSON"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    
db = firestore.client()

class FirebaseAdapter:
    def read(self, worksheet="Evolucao", ttl=0):
        # Lê os documentos do banco NoSQL e os converte instantaneamente para o formato Pandas
        docs = db.collection(worksheet).stream()
        dados = [d.to_dict() for d in docs]
        return pd.DataFrame(dados) if dados else pd.DataFrame()

    def update(self, worksheet="Evolucao", data=None):
        # Engenharia de performance: Captura apenas o último registro do DataFrame e injeta no banco
        novo_registro = data.iloc[-1].dropna().to_dict()
        db.collection(worksheet).add(novo_registro)

conn = FirebaseAdapter()

# ==========================================
# --- ROTEAMENTO SEGURANÇA (PORTAL DO CIRURGIÃO) ---
# ==========================================
import base64
import urllib.parse

query_params = st.query_params
is_medico = query_params.get("med", None)
token_paciente = query_params.get("token", None)
paciente_alvo = None

if is_medico == "true" and token_paciente:
    try:
        paciente_alvo = base64.b64decode(token_paciente.encode('utf-8')).decode('utf-8')
        # Esconde menu lateral e barra superior do Streamlit para o médico
        st.markdown("""
            <style>
                [data-testid="collapsedControl"] {display: none;}
                [data-testid="stSidebar"] {display: none;}
                header {display: none;}
            </style>
        """, unsafe_allow_html=True)
    except:
        pass

# ==========================================
# --- NOVA LÓGICA DE NAVEGAÇÃO (ESTADO DO APP) ---
# ==========================================
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'login'
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def mudar_pagina(nome_pagina):
    st.session_state.pagina = nome_pagina
    st.rerun()

# TRAVA DE SEGURANÇA: Se o cirurgião acessar via link, pula o login e vai direto para o painel
if paciente_alvo:
    st.session_state.autenticado = True
    st.session_state.paciente = paciente_alvo
    st.session_state.membro_ativo = "Acesso Médico"
    st.session_state.pagina = 'painel_clinico'
    menu = "Painel Analítico 📊"

# --- TELAS DO SISTEMA MVP ---

# PAGINA 1: LOGIN (ARQUITETURA DE IDENTIDADE GOOGLE)
if st.session_state.pagina == 'login':
    st.markdown(f"<h2 style='color: {CORES_GENUA['primaria']}; text-align: center;'>🔐 GENUA | Acesso Profissional</h2>", unsafe_allow_html=True)
    c_vazio1, c_login, c_vazio2 = st.columns([1, 2, 1])
    
    with c_login:
        user = st.text_input("E-mail Profissional")
        password = st.text_input("Senha de Acesso", type="password")
        
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("Entrar", use_container_width=True):
                # Lógica Híbrida: Mantém o teste mas prepara o Firebase Auth
                if user == "admin" and password == "1234":
                    st.session_state.autenticado = True
                    st.session_state.user_email = user
                    mudar_pagina('dados_paciente')
                else:
                    st.error("Credenciais não localizadas no cofre Google.")
        with c_btn2:
            st.button("Criar Conta", type="secondary", use_container_width=True, help="Funcionalidade em migração para Google Cloud.")
            
    st.stop()

## PAGINA 2: SELEÇÃO E CADASTRO DE PACIENTE (FIREBASE READY)
elif st.session_state.pagina == 'dados_paciente':
    st.markdown(f"<h2 style='color: {CORES_GENUA['primaria']};'>👤 Gestão de Pacientes</h2>", unsafe_allow_html=True)
    
    # Busca lista atualizada do Google Cloud
    df_cad = conn.read(worksheet="Cadastro")
    lista_pacientes = df_cad['Nome'].tolist() if not df_cad.empty else []
        
    opcao_paciente = st.selectbox("Selecione um paciente ou cadastre novo:", ["+ Cadastrar Novo"] + lista_pacientes)
    
    # --- FLUXO 1: FORMULÁRIO COMPLETO DE NOVO PACIENTE ---
    if opcao_paciente == "+ Cadastrar Novo":
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>📋 Nova Ficha de Cadastro</h4>", unsafe_allow_html=True)
        
        # Chave única adicionada para evitar o StreamlitAPIException
        with st.form(key="form_cadastro_firebase"):
            c1, c2 = st.columns(2)
            with c1:
                novo_nome = st.text_input("Nome Completo *", placeholder="Ex: João da Silva")
                novo_cpf = st.text_input("CPF")
                nova_idade = st.number_input("Idade", min_value=0, max_value=120, step=1)
            with c2:
                novo_telefone = st.text_input("WhatsApp / Telefone")
                novo_email = st.text_input("E-mail")
                nova_hma = st.text_area("HMA (História Clínica / Cirurgia)", height=68, placeholder="Ex: Pós-operatório de LCA...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_cadastro = st.form_submit_button("💾 Salvar no Google Cloud", use_container_width=True)
            
            if submit_cadastro:
                if novo_nome.strip() == "":
                    st.error("⚠️ O Nome Completo é obrigatório.")
                else:
                    novo_registro = pd.DataFrame([{
                        "Nome": novo_nome.strip(), "CPF": novo_cpf, "Idade": nova_idade,
                        "Telefone": novo_telefone, "Email": novo_email, "Historia": nova_hma,
                        "Data_Cadastro": datetime.now().strftime("%d/%m/%Y")
                    }])
                    conn.update(worksheet="Cadastro", data=novo_registro)
                    st.success("Cadastro realizado com sucesso!")
                    st.session_state.paciente = novo_nome.strip()
                    mudar_pagina('selecao_membro')

    # --- FLUXO 2: PACIENTE JÁ EXISTENTE ---
    else:
        st.success(f"Paciente selecionado: **{opcao_paciente}**")
        if st.button("Próximo: Selecionar Tratamento ➡️", use_container_width=True):
            st.session_state.paciente = opcao_paciente
            mudar_pagina('selecao_membro')
            
    st.stop()

# PAGINA 3: SELEÇÃO DE MEMBRO INTELIGENTE
elif st.session_state.pagina == 'selecao_membro':
    st.title("🎯 Área de Reabilitação")
    st.markdown(f"Paciente Ativo: **{st.session_state.paciente}**")
    
    # INTELIGÊNCIA: Verifica quais membros este paciente já tratou no passado
    try:
        df_ev = conn.read(worksheet="Evolucao", ttl=0).dropna(how="all")
        if 'Membro' not in df_ev.columns: df_ev['Membro'] = "Joelho" # Blindagem de legado
        df_ev['Membro'] = df_ev['Membro'].fillna("Joelho")
        
        membros_existentes = df_ev[df_ev['Paciente'] == st.session_state.paciente]['Membro'].unique().tolist()
    except:
        membros_existentes = []

    st.markdown("### 🔄 Continuar Tratamento Existente")
    if membros_existentes:
        for m in membros_existentes:
            if st.button(f"Abrir Prontuário: {m} 📊", use_container_width=True):
                st.session_state.membro_ativo = m
                mudar_pagina('painel_clinico')
    else:
        st.info("Nenhum tratamento anterior encontrado para este paciente. Inicie um abaixo.")

    st.markdown("---")
    st.markdown("### ➕ Iniciar Novo Tratamento")
    # Foco absoluto do MVP: Joelho
    novo_membro = "Joelho" 
    
    if st.button(f"Iniciar Prontuário para {novo_membro} 🆕", use_container_width=True, type="primary"):
        st.session_state.membro_ativo = novo_membro
        mudar_pagina('painel_clinico')
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅️ Voltar", type="secondary"):
        mudar_pagina('dados_paciente')
        
    st.stop()

# PAGINA 4: PAINEL CLÍNICO (UX ESTILO APP NATIVO)
elif st.session_state.pagina == 'painel_clinico':
    # 1. Menu Lateral Limpo (Funciona como a "Tab Bar" de um aplicativo)
    with st.sidebar:
        if not st.session_state.get('paciente_alvo', False): 
            st.markdown(f"<h3 style='color: {CORES_GENUA['primaria']}; text-align: center;'>👤 {st.session_state.paciente}</h3>", unsafe_allow_html=True)
            
            # NOVO BOTÃO DE NAVEGAÇÃO: Voltar para a lista de pacientes
            if st.button("⬅️ Trocar Paciente", use_container_width=True):
                mudar_pagina('dados_paciente')
                
            st.markdown("---")
            menu = st.radio("MÓDULOS DE ATENDIMENTO", ["Avaliação Inicial 🔎", "Check-in Diário 📝", "Painel Analítico 📊"])
        else:
            menu = "Painel Analítico 📊"

        with st.expander("⚙️ Admin: Injetar Pacientes"):
            st.warning("Criará 10 pacientes e 200 sessões no banco Firebase.")
            if st.button("💉 Gerar Dados GENUA", use_container_width=True):
                import numpy as np
                from datetime import timedelta
                
                pacientes_mock = [
                    {"Nome": "Carlos Eduardo", "Idade": 28, "Dx": "LCA", "Dor_Ini": 8, "Inc_Ini": 3, "HMA": "Entorse jogando futebol, estalo audível. Reconstrução LCA há 4 semanas."},
                    {"Nome": "Mariana Silva", "Idade": 34, "Dx": "SFP", "Dor_Ini": 6, "Inc_Ini": 0, "HMA": "Dor anterior no joelho há 6 meses, piora ao descer escadas. Corredora amadora."},
                    {"Nome": "Roberto Alves", "Idade": 55, "Dx": "Artrose", "Dor_Ini": 7, "Inc_Ini": 2, "HMA": "Dor crônica e rigidez matinal intensa. Raio-X com redução de espaço articular."},
                    {"Nome": "Fernanda Lima", "Idade": 22, "Dx": "Tendinopatia", "Dor_Ini": 5, "Inc_Ini": 0, "HMA": "Dor no polo inferior da patela após treinos de vôlei. Piora com saltos."},
                    {"Nome": "João Pedro", "Idade": 41, "Dx": "Menisco", "Dor_Ini": 7, "Inc_Ini": 2, "HMA": "Dor medial aguda após agachamento profundo. Travamentos ocasionais."},
                    {"Nome": "Ana Beatriz", "Idade": 29, "Dx": "SFP", "Dor_Ini": 8, "Inc_Ini": 0, "HMA": "Dor difusa, sensibilidade extrema. Sono muito ruim devido à dor noturna."},
                    {"Nome": "Lucas Moura", "Idade": 31, "Dx": "LCA Conservador", "Dor_Ini": 6, "Inc_Ini": 1, "HMA": "Lesão parcial de LCA. Optou por tratamento conservador. Falseios leves."},
                    {"Nome": "Camila Rocha", "Idade": 45, "Dx": "Condromalácia", "Dor_Ini": 5, "Inc_Ini": 0, "HMA": "Crepitação patelofemoral. Dor ao ficar muito tempo sentada (Sinal do Cinema)."},
                    {"Nome": "Tiago Santos", "Idade": 38, "Dx": "Menisco Degenerativo", "Dor_Ini": 6, "Inc_Ini": 1, "HMA": "Dor progressiva na interlinha medial, sem trauma específico."},
                    {"Nome": "Juliana Costa", "Idade": 26, "Dx": "Tendinopatia", "Dor_Ini": 7, "Inc_Ini": 0, "HMA": "Praticante de Crossfit. Dor forte no tendão patelar em treinos de LPO."}
                ]

                data_hoje = datetime.now()

                with st.spinner("Injetando dados via rota direta no Firebase..."):
                    for p in pacientes_mock:
                        # 1. Injetar Cadastro Direto
                        db.collection("Cadastro").add({
                            "Nome": p["Nome"], "Idade": p["Idade"], "Historia": p["HMA"]
                        })

                        # 2. Injetar Avaliação Inicial Direta
                        db.collection("Avaliacao_Inicial").add({
                            "Data_Avaliacao": (data_hoje - timedelta(days=70)).strftime("%d/%m/%Y"),
                            "Paciente": p["Nome"], "Membro": "Joelho",
                            "HMA": p["HMA"], "HMP": "Sem comorbidades relevantes.", "Ocupacao": "Ativo", "Objetivo": "Retorno ao esporte/função",
                            "Trauma": "Sim" if "LCA" in p["Dx"] or "Entorse" in p["HMA"] else "Não",
                            "Falseio": "Sim, frequentes" if "LCA" in p["Dx"] else "Não",
                            "Rigidez": "Mais de 30 min" if p["Dx"] == "Artrose" else "Ausente",
                            "Travamento": "Sim" if "Menisco" in p["Dx"] else "Não",
                            "Quadriceps_Forca": "Déficit Leve", "Isquio_Forca": "Déficit Leve", "Quadril_Forca": "Déficit Leve",
                            "Tornozelo_ADM": "Normal (>10cm)", "Core_Controle": "Estável",
                            "Agachamento_Uni": "Valgo Dinâmico Leve", "Step_Down_Qualidade": "Estratégia de Quadril Pobre",
                            "IKDC_Inicial": 35.0, "LEFS_Inicial": 40.0, "Profissional_ID": "admin"
                        })

                        # 3. Injetar 20 Sessões Diretas
                        dor_atual = p["Dor_Ini"]
                        inc_atual = p["Inc_Ini"]
                        
                        for sessao in range(20):
                            dias_atras = (20 - sessao) * 3.5
                            data_sessao = data_hoje - timedelta(days=dias_atras)
                            
                            if sessao % 4 == 0 and dor_atual > 1: dor_atual -= 1 
                            if sessao % 5 == 0 and inc_atual > 0: inc_atual -= 1 
                            
                            sono = "Bom" if dor_atual < 4 else ("Regular" if dor_atual < 7 else "Ruim")
                            agac = "Sem Dor" if dor_atual < 3 else ("Dor Leve" if dor_atual < 6 else "Dor Moderada")
                            sdn = "Sem Dor" if dor_atual < 4 else ("Dor Moderada" if "SFP" in p["Dx"] else "Dor Leve")
                            ext = "Completa (0°)" if sessao > 10 else "Déficit Leve (-5°)"
                            flex = min(140, 90 + (sessao * 2.5)) 
                            
                            db.collection("Evolucao").add({
                                "Data": data_sessao.strftime("%d/%m/%Y %H:%M"), "Paciente": p["Nome"], "Membro": "Joelho",
                                "Dor": dor_atual, "Sono": sono, "Inchaço": str(inc_atual), "Postura": "Não avaliada",
                                "Agachamento": agac, "Step_Up": agac, "Step_Down": sdn, "Flexao": int(flex), "Extensao": ext,
                                "Profissional_ID": "admin"
                            })

                st.success("✅ Lote completo processado! Todos os 10 pacientes estão no Firebase.")

    # 2. App Header (Barra Superior de Navegação Nativa)
    if not paciente_alvo:
        c_back, c_title, c_vazio = st.columns([1, 4, 1])
        with c_back:
            # Botão Voltar utilizando o novo estilo CSS "secondary" transparente
            if st.button("⬅️ Voltar", type="secondary", use_container_width=False, help="Voltar para seleção de região"):
                mudar_pagina('selecao_membro')
        with c_title:
            st.markdown(f"<h3 style='text-align: center; color: {CORES_GENUA['primaria']}; margin-top: 5px; font-size: 1.6rem;'>{st.session_state.membro_ativo}</h3>", unsafe_allow_html=True)
        st.markdown("<hr style='margin-top: -5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

    # --- MÓDULO 1: AVALIAÇÃO INICIAL (O MARCO ZERO) ---
    if menu == "Avaliação Inicial 🔎":
        # Cabeçalho limpo sem repetição de tags, pois o membro já está no topo (App Header)
        st.markdown(f"<p style='color: {CORES_GENUA['texto_suave']}; margin-top: -10px; text-align: center;'>Primeira Consulta | Estabelecimento de Baseline Clínica</p><br>", unsafe_allow_html=True)

        # (MANTENHA O SEU CÓDIGO INTACTO A PARTIR DAQUI)
        with st.form(key="form_avaliacao_inicial_firebase"):
            a1, a2, a3, a4 = st.tabs(["🗣️ Anamnese", "🚨 Red Flags", "📐 Físico & Testes", "📝 Questionários"])

            with a1:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Histórico e Contexto</h4>", unsafe_allow_html=True)
                hma = st.text_area("HMA (História da Moléstia Atual) *", placeholder="Mecanismo de lesão, tempo de dor, comportamento dos sintomas...")
                hmp = st.text_area("HMP (Histórico Médico Pregresso)", placeholder="Cirurgias anteriores, comorbidades, medicações em uso...")
                c_a1, c_a2 = st.columns(2)
                with c_a1: ocupacao = st.text_input("Profissão / Esporte")
                with c_a2: objetivo = st.text_input("Objetivo Principal do Paciente", placeholder="Ex: Voltar a correr 5km sem dor")

            with a2:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Rastreio de Risco (Joelho)</h4>", unsafe_allow_html=True)
                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    trauma = st.radio("Trauma Direto Recente?", ["Não", "Sim"])
                    falseio = st.radio("Falseios Francos / Falha da Articulação?", ["Não", "Sim, frequentes", "Apenas sensação de insegurança"])
                with c_r2:
                    rigidez_matinal = st.radio("Rigidez Matinal Articular", ["Ausente", "Menos de 30 min", "Mais de 30 min (Sinal Inflamatório)"])
                    travamento = st.radio("Bloqueio/Travamento Articular Verdadeiro?", ["Não", "Sim (Possível lesão meniscal/corpo livre)"])

            with a3:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Força e Interdependência Regional</h4>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns(3)
                with c_f1: quadriceps_forca = st.selectbox("Força Quadríceps", ["Preservada", "Déficit Leve", "Fraqueza Importante (< Grau 3)"])
                with c_f2: isquio_forca = st.selectbox("Força Isquiotibiais", ["Preservada", "Déficit Leve", "Fraqueza Importante (< Grau 3)"])
                with c_f3: quadril_forca = st.selectbox("Força Glúteo Médio", ["Preservada", "Déficit Leve", "Fraqueza Importante (< Grau 3)"])
                
                c_f4, c_f5 = st.columns(2)
                with c_f4: tornozelo_adm = st.selectbox("Dorsiflexão Tornozelo (Lunge)", ["Normal (>10cm)", "Restrita (<10cm)", "Assimétrica"])
                with c_f5: core_controle = st.selectbox("Controle Pélvico / Core", ["Estável", "Queda Pélvica (Trendelenburg)"])

                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Testes Funcionais e Biomecânica</h4>", unsafe_allow_html=True)
                c_fn1, c_fn2 = st.columns(2)
                with c_fn1: agachamento_uni = st.selectbox("Agachamento Unipodal", ["Bom Alinhamento", "Valgo Dinâmico Leve", "Valgo Dinâmico Severo", "Incapaz por Dor"])
                with c_fn2: step_down_qualidade = st.selectbox("Step Down (Qualidade)", ["Movimento Fluido", "Estratégia de Quadril Pobre", "Dor Femoropatelar Aguda", "Incapaz"])

                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Filtro de Testes Ortopédicos (Apenas Positivos)</h4>", unsafe_allow_html=True)
                st.caption("Selecione apenas os testes que apresentaram sinal positivo.")
                
                testes_ligamentares = st.multiselect("LCA, LCP, LCL, LCM e CPL", ["Lachman", "Gaveta Anterior", "Gaveta Posterior", "Pivot Shift", "Estresse Valgo", "Estresse Varo", "Dial Test (CPL)"])
                testes_meniscais = st.multiselect("Meniscos e Cartilagem", ["McMurray", "Apley Compressão", "Thessaly (20°)", "Sinal de Rabot (Crepitação)"])
                testes_femoropatelar = st.multiselect("SFP, Tendinopatias e Trato Iliotibial", ["Sinal de Clarke", "Apreensão Patelar", "Decline Squat (Tendinopatia Patelar)", "Teste de Noble (Trato Iliotibial)"])

            with a4:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>PROMs (Métricas de Desfecho)</h4>", unsafe_allow_html=True)
                st.info("Insira o score inicial do paciente para balizar a alta futura.")
                c_q1, c_q2 = st.columns(2)
                with c_q1: ikdc_score = st.number_input("Score IKDC (0-100)", min_value=0.0, max_value=100.0, step=1.0, value=0.0)
                with c_q2: lefs_score = st.number_input("Score LEFS (0-80)", min_value=0, max_value=80, step=1, value=0)

            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("💾 SALVAR AVALIAÇÃO INICIAL", use_container_width=True):
                if hma.strip() == "":
                    st.error("A HMA é obrigatória para registrar a avaliação.")
                else:
                    dados_avaliacao = {
                        "Data_Avaliacao": datetime.now().strftime("%d/%m/%Y"),
                        "Paciente": st.session_state.paciente,
                        "Membro": st.session_state.membro_ativo,
                        "HMA": hma, "HMP": hmp, "Ocupacao": ocupacao, "Objetivo": objetivo,
                        "Trauma": trauma, "Falseio": falseio, "Rigidez": rigidez_matinal, "Travamento": travamento,
                        "Quadriceps_Forca": quadriceps_forca, "Isquio_Forca": isquio_forca, "Quadril_Forca": quadril_forca, 
                        "Tornozelo_ADM": tornozelo_adm, "Core_Controle": core_controle,
                        "Agachamento_Uni": agachamento_uni, "Step_Down_Qualidade": step_down_qualidade,
                        "Testes_Ligamentares": ", ".join(testes_ligamentares),
                        "Testes_Meniscais": ", ".join(testes_meniscais),
                        "Testes_Femoropatelar": ", ".join(testes_femoropatelar),
                        "IKDC_Inicial": ikdc_score, "LEFS_Inicial": lefs_score,
                        "Profissional_ID": st.session_state.get("user_email", "admin")
                    }
                    
                    df_av = conn.read(worksheet="Avaliacao_Inicial", ttl=0)
                    nova_linha_av = pd.DataFrame([dados_avaliacao])
                    if df_av.empty:
                        df_av = nova_linha_av
                    else:
                        df_av = pd.concat([df_av, nova_linha_av], ignore_index=True)
                        
                    conn.update(worksheet="Avaliacao_Inicial", data=df_av)
                    st.success("✅ Avaliação Inicial registrada com sucesso!")

    # --- MÓDULO 2: CHECK-IN DIÁRIO (EXCLUSIVO JOELHO) ---
    elif menu == "Check-in Diário 📝":
        with st.form(key="form_checkin_diario_firebase", clear_on_submit=True):
            st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Quadro Sistêmico Universal</h4>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: dor = st.slider("💥 Dor atual (EVA 0-10)", 0, 10, 0)
            with c2: sono = st.radio("💤 Sono", ["Ruim", "Regular", "Bom"], horizontal=True)
                
            dados_sessao = {
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Paciente": st.session_state.paciente,
                "Membro": "Joelho", "Dor": int(dor), "Sono": sono, "Postura": "Não avaliada",
                "Profissional_ID": st.session_state.get("user_email", "admin")
            }

            st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Avaliação Específica: Joelho</h4>", unsafe_allow_html=True)
            
            c_inc, c5, c6, c7 = st.columns(4)
            with c_inc: inchaco = st.select_slider("💧 Inchaço", options=["0", "1", "2", "3"])
            with c5: agac = st.selectbox("🏋️ Agachamento", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            with c6: sup = st.selectbox("🪜 Step Up", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            with c7: sdn = st.selectbox("📉 Step Down", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            
            c8, c9 = st.columns(2)
            with c8: flexao = st.slider("📐 Flexão (Graus)", 0, 150, 90)
            with c9: extensao = st.selectbox("📏 Extensão Terminal", ["Completa (0°)", "Déficit Leve (-5°)", "Déficit Grave (>-15°)"])
            
            dados_sessao.update({
                "Inchaço": str(inchaco), "Agachamento": agac, "Step_Up": sup, 
                "Step_Down": sdn, "Flexao": int(flexao), "Extensao": extensao
            })

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("✅ REGISTRAR SESSÃO", use_container_width=True):
                df = conn.read(worksheet="Evolucao", ttl=0).dropna(how="all")
                nova_linha = pd.DataFrame([dados_sessao])
                conn.update(worksheet="Evolucao", data=pd.concat([df, nova_linha], ignore_index=True))
                st.success(f"Dados do Joelho registrados com sucesso!")
                
        st.write("---")
        with st.expander("⚖️ Conformidade LGPD e Privacidade"):
            st.caption("Processamento anonimizado de dados para finalidade exclusiva de Inteligência Clínica.")

    # --- MÓDULO 3: PAINEL ANALÍTICO (CÉREBRO EXCLUSIVO JOELHO) ---
    elif menu == "Painel Analítico 📊":
        p_sel = st.session_state.paciente
        
        # --- A. RESGATE DO CADASTRO (HMA E IDADE) ---
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            registro_p = df_cad[df_cad['Nome'].str.strip() == p_sel].iloc[-1]
            hist_clinica = registro_p.get('Historia', 'Histórico não cadastrado.')
            idade_p = int(float(registro_p.get('Idade', 0))) if pd.notna(registro_p.get('Idade')) else "N/A"
        except:
            hist_clinica = "Histórico não disponível."; idade_p = "-"

        # --- B. RESGATE DA AVALIAÇÃO BASE (TESTES E FORÇA) ---
        try:
            df_av = conn.read(worksheet="Avaliacao_Inicial", ttl=0)
            av_p = df_av[df_av['Paciente'].str.strip() == p_sel].iloc[-1]
            av_data = av_p.get('Data_Avaliacao', 'N/A')
            av_quad = av_p.get('Quadriceps_Forca', 'Não testado')
            av_isq = av_p.get('Isquio_Forca', 'Não testado')
            av_glut = av_p.get('Quadril_Forca', 'Não testado')
            av_agac = av_p.get('Agachamento_Uni', 'Não avaliado')
            av_step = av_p.get('Step_Down_Qualidade', 'Não avaliado')
            av_tlig = av_p.get('Testes_Ligamentares', '')
            av_tmen = av_p.get('Testes_Meniscais', '')
            av_tfp = av_p.get('Testes_Femoropatelar', '')
            tem_av = True
        except:
            tem_av = False

        st.header(f"📊 Painel Analítico: Joelho")

        # 1. HEADER DO PACIENTE
        st.markdown(f"""
            <div style='background-color: #ffffff; border: 1px solid #e9ecef; border-left: 5px solid {CORES_GENUA['primaria']}; padding: 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                    <h3 style='margin: 0; color: {CORES_GENUA['primaria']}; font-weight: 700;'>👤 {p_sel}</h3>
                    <span style='background-color: #f1f3f5; color: {CORES_GENUA['primaria']}; padding: 6px 15px; border-radius: 20px; font-weight: 600;'>{idade_p} anos</span>
                </div>
                <p style='margin: 0; color: #495057;'><strong>HMA:</strong> {hist_clinica}</p>
            </div>
        """, unsafe_allow_html=True)

        # 2. CARD DE AVALIAÇÃO FÍSICA (Expander para não poluir a tela)
        if tem_av:
            with st.expander(f"📋 Consultar Ficha de Avaliação Base (Data: {av_data})"):
                c_av1, c_av2 = st.columns(2)
                with c_av1:
                    st.markdown("**💪 Força Muscular:**")
                    st.markdown(f"- Quadríceps: {av_quad}\n- Isquiotibiais: {av_isq}\n- Glúteo Médio: {av_glut}")
                    st.markdown("**⚙️ Biomecânica Dinâmica:**")
                    st.markdown(f"- Agachamento Unipodal: {av_agac}\n- Step Down: {av_step}")
                with c_av2:
                    st.markdown("**🔬 Testes Ortopédicos (Positivos):**")
                    st.markdown(f"- Ligamentares: {av_tlig if av_tlig else 'Nenhum achado'}")
                    st.markdown(f"- Meniscais: {av_tmen if av_tmen else 'Nenhum achado'}")
                    st.markdown(f"- Femoropatelar: {av_tfp if av_tfp else 'Nenhum achado'}")
        else:
            st.info("⚠️ Nenhuma Avaliação Inicial rica registrada no sistema para este paciente.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- C. MOTOR DE EVOLUÇÃO (CHECK-INS) ---
        df = conn.read(worksheet="Evolucao", ttl=0).dropna(how="all")
        if df.empty or 'Paciente' not in df.columns:
            st.warning("⚠️ O paciente ainda não possui sessões de Check-in diário registradas.")
            st.stop()
        
        df['Membro'] = df.get('Membro', "Joelho").fillna("Joelho")
        df_p = df[(df['Paciente'] == p_sel) & (df['Membro'] == "Joelho")].copy()

        if df_p.empty:
            st.warning("⚠️ O paciente ainda não possui sessões de Check-in diário registradas.")
            st.stop()

        df_p['Data_dt'] = pd.to_datetime(df_p['Data'], dayfirst=True)
        df_p = df_p.sort_values('Data_dt')
        df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]

        if 'Dor' not in df_p.columns: df_p['Dor'] = 0
        df_p['Dor'] = pd.to_numeric(df_p['Dor'], errors='coerce').fillna(0)
        
        col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
        if col_inc not in df_p.columns: df_p[col_inc] = 0
        df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)

        for col, default in [('Flexao', 90), ('Extensao', 'Sem dados'), ('Agachamento', 'Sem Dor'), ('Step_Up', 'Sem Dor'), ('Step_Down', 'Sem Dor')]:
            if col not in df_p.columns: df_p[col] = default

        c_vazio, c_seletor = st.columns([4, 1])
        with c_seletor:
            sessao_escolhida = st.selectbox("📅 Analisar Sessão:", options=df_p['Sessão_Num'].tolist()[::-1], index=0)
        ultima = df_p[df_p['Sessão_Num'] == sessao_escolhida].iloc[0]

        dor_atual = int(ultima.get('Dor', 0))
        inchaco_atual = int(ultima.get('Inchaco_N', 0))
        sono_atual = ultima.get('Sono', 'Regular')
        media_dor = df_p['Dor'].mean()

        mapa_func = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
        func_pts = (mapa_func.get(ultima.get('Agachamento', 'Sem Dor'), 10) +
                    mapa_func.get(ultima.get('Step_Up', 'Sem Dor'), 10) +
                    mapa_func.get(ultima.get('Step_Down', 'Sem Dor'), 10)) / 30.0
        lsi_global = min(max(float(func_pts * 100), 0.0), 100.0)

        # Motor de IA
        if ultima.get('Agachamento') == 'Incapaz' and inchaco_atual >= 2 and dor_atual >= 8:
            fenotipo = "🚨 Red Flag / Risco Estrutural"
            diretriz = "Critérios de Ottawa: Incapacidade de carga + Edema Agudo. Indicação de imagem."
        elif ultima.get('Step_Down') in ['Incapaz', 'Dor Moderada'] and inchaco_atual <= 1:
            fenotipo = "🟣 Síndrome Femoropatelar (SFP)"
            diretriz = "Cinemática: Exacerbação na desaceleração excêntrica. Foco em modulação e isometria de glúteo."
        elif ultima.get('Extensao') in ['Déficit Grave (>-15°)', 'Déficit Leve (-5°)'] and inchaco_atual >= 2:
            fenotipo = "🟤 Bloqueio Articular / Meniscal"
            diretriz = "Déficit de extensão + Derrame. Restrição absoluta de carga axial no momento."
        elif ultima.get('Agachamento') in ['Incapaz', 'Dor Moderada'] and ultima.get('Extensao') == 'Completa (0°)' and inchaco_atual == 0:
            fenotipo = "🟠 Tendinopatia Patelar"
            diretriz = "Dor em fase de armazenamento elástico. Isometria pesada para analgesia aguda."
        elif dor_atual >= 6 and inchaco_atual == 0 and sono_atual == "Ruim":
            fenotipo = "🟡 Sensibilização Central"
            diretriz = "Descompasso Clínico: Dor desproporcional. Foco em educação em dor e higiene do sono."
        elif dor_atual <= 3 and inchaco_atual <= 1 and lsi_global >= 80:
            fenotipo = "🟢 Fase de Remodelamento"
            diretriz = "Seguro para progressão de pliometria e exercícios de mudança de direção."
        else:
            fenotipo = "🔵 Acomodação de Carga"
            diretriz = "Sinais mistos. Focar no controle do sintoma mecânico mais limitante na sessão."

        status_clinico = "Excelente" if lsi_global >= 85 else "Regular" if lsi_global >= 60 else "Atenção"

        # Métricas na Tela
        m1, m2, m3, m4 = st.columns(4)
        delta_pct = ((dor_atual - media_dor) / media_dor * 100) if media_dor > 0 else 0
        m1.metric("Dor Atual", f"{dor_atual}/10", f"{delta_pct:.0f}%", delta_color="inverse")
        m2.metric("Inchaço", f"Grau {inchaco_atual}")
        m3.metric("Prontidão (LSI)", f"{lsi_global:.0f}%", status_clinico)
        m4.metric("Fenótipo IA", fenotipo.split()[-1])
        st.write("---")

        st.markdown(f"**Progresso para Alta Clínica: {lsi_global:.0f}%**")
        st.progress(lsi_global / 100)

        t1, t2, t3, t4 = st.tabs(["🧠 Inteligência Artificial", "📈 Gráfico de Evolução", "📐 Biomecânica", "🎯 Fatores"])
        
        with t1:
            st.info("A IA atua como uma ferramenta de segunda opinião algorítmica. **O raciocínio clínico final é seu.**")
            c_i1, c_i2 = st.columns(2)
            c_i1.markdown(f"**🔬 {fenotipo}**\n\n💡 *Diretriz:* {diretriz}")
            c_i2.markdown(f"**⚙️ Biomecânica Atual:**\n- Flexão: {ultima.get('Flexao', 90)}°\n- Extensão: {ultima.get('Extensao', 'Sem dados')}")
        
        with t2:
            fig, ax = plt.subplots(figsize=(10, 3.5))
            ax.plot(df_p['Sessão_Num'], df_p['Dor'], marker='o', color=CORES_GENUA['alerta_erro'], lw=2)
            ax.set_title("Regressão Álgica Longitudinal", color=CORES_GENUA['primaria'])
            ax.set_ylim(-0.5, 11)
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            st.pyplot(fig)
            buf_ev = io.BytesIO(); fig.savefig(buf_ev, format='png', bbox_inches='tight'); buf_ev.seek(0)
            buf_corr = buf_ev

        with t3:
            col1, col2 = st.columns(2)
            col1.metric("Flexão Atual", f"{ultima.get('Flexao', 90)}°")
            col2.info(f"Extensão Terminal: {ultima.get('Extensao', 'Sem dados')}")
            buf_adm = buf_ev

        with t4:
            st.success(f"💡 **Insight Sono:** O padrão de sono na última sessão foi relatado como '{sono_atual}'.")
            st.caption("Aguardando volume maior de sessões para cruzar novos gatilhos biomecânicos e posturais.")

        # --- 5. PDF EXPORT (Blindado contra variáveis ausentes) ---
        st.markdown("---")
        if st.button("📄 Gerar Relatório PDF Oficial", use_container_width=True):
            try:
                pdf_metrics = {
                    'ikdc': lsi_global, 'ikdc_status': status_clinico, 
                    'dor': dor_atual, 'media_dor': media_dor,
                    'inchaco': inchaco_atual, 
                    'alta': "Acompanhamento Ativo", 
                    'insight_ouro': f"Qualidade do Sono: {sono_atual}",
                    'insight_mecanico': diretriz, 
                    'insight_postura': "Variável em calibração",
                    'insight_evolucao': "Curva de regressão álgica disponível no painel."
                }
                pdf_output = create_pdf(p_sel, hist_clinica, pdf_metrics, {'ev': buf_ev, 'dor': buf_ev, 'sono': buf_corr, 'inchaco': buf_adm, 'adm': buf_adm})
                st.success("✅ Documento Científico gerado com sucesso!")
                st.download_button(label="⬇️ Baixar PDF", data=pdf_output, file_name=f"Laudo_GENUA_{p_sel}.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Erro na emissão do PDF. Verifique o layout base FPDF: {e}")


