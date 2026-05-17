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

# PAGINA 2: SELEÇÃO DE PACIENTE E CADASTRO COMPLETO
elif st.session_state.pagina == 'dados_paciente':
    st.header("👤 Gestão de Pacientes")
    
    try:
        df_cad = conn.read("Cadastro", ttl=0)
        lista = df_cad['Nome'].dropna().unique().tolist() if not df_cad.empty else []
    except:
        lista = []
        
    paciente = st.selectbox("Selecione um paciente existente ou adicione um novo:", ["+ Novo Paciente"] + lista)
    
    if paciente == "+ Novo Paciente":
        with st.form("cad_novo"):
            st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Identificação do Paciente</h4>", unsafe_allow_html=True)
            nome = st.text_input("Nome Completo *")
            
            c_cad1, c_cad2, c_cad3 = st.columns(3)
            with c_cad1: 
                # Define um valor padrão estável e expande o limite mínimo para até 100 anos atrás
                data_padrao = datetime(2000, 1, 1)
                data_minima = datetime(datetime.now().year - 100, 1, 1)
                dt_nasc = st.date_input(
                    "Data de Nascimento *", 
                    value=data_padrao,
                    min_value=data_minima,
                    max_value=datetime.today(),
                    format="DD/MM/YYYY"
                )
            with c_cad2: cpf = st.text_input("CPF")
            with c_cad3: telefone = st.text_input("Telefone (WhatsApp)")
            
            c_cad4, c_cad5, c_cad6 = st.columns(3)
            with c_cad4: email = st.text_input("E-mail")
            with c_cad5: cidade = st.text_input("Cidade e Estado")
            with c_cad6: ocupacao = st.text_input("Atividade Ocupacional")
            
            st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Diagnóstico Clínico (Triagem)</h4>", unsafe_allow_html=True)
            dx_rapido = st.text_input("Diagnóstico Clínico/Médico", placeholder="Ex: LCA, Condropatia, Tendinopatia...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("💾 Salvar Cadastro", use_container_width=True):
                if nome.strip() == "":
                    st.error("O Nome é obrigatório.")
                else:
                    idade_calc = (datetime.now().date() - dt_nasc).days // 365
                    novo_cad = {
                        "Nome": nome, "Data_Nascimento": dt_nasc.strftime("%d/%m/%Y"), 
                        "Idade": idade_calc, "CPF": cpf, "Telefone": telefone, 
                        "Email": email, "Cidade_Estado": cidade, "Ocupação": ocupação, 
                        "Diagnostico_Rapido": dx_rapido, "Historia": "" 
                    }
                    
                    df_banco_cad = conn.read("Cadastro", ttl=0)
                    if df_banco_cad.empty: conn.update("Cadastro", pd.DataFrame([novo_cad]))
                    else: conn.update("Cadastro", pd.concat([df_banco_cad, pd.DataFrame([novo_cad])], ignore_index=True))
                    
                    st.session_state.paciente = nome
                    st.session_state.membro_ativo = "Joelho" # <-- FORÇA O FOCO NO MVP
                    st.success("✅ Paciente registrado com sucesso!")
                    mudar_pagina('painel_clinico') # <-- ROTEAMENTO DIRETO
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Abrir Prontuário", use_container_width=True, type="primary"):
            st.session_state.paciente = paciente
            st.session_state.membro_ativo = "Joelho" # <-- FORÇA O FOCO NO MVP
            mudar_pagina('painel_clinico') # <-- ROTEAMENTO DIRETO

# PAGINA 4: PAINEL CLÍNICO (UX ESTILO APP NATIVO)
elif st.session_state.pagina == 'painel_clinico':
    # 1. Menu Lateral Limpo e Unificado
    with st.sidebar:
        if not st.session_state.get('paciente_alvo', False): 
            st.markdown(f"<h3 style='color: {CORES_GENUA['primaria']}; text-align: center;'>👤 {st.session_state.paciente}</h3>", unsafe_allow_html=True)
            
            # --- CORREÇÃO DE ROTA: BOTÃO VOLTAR BLINDADO ---
            if st.button("⬅️ Voltar para Pacientes", use_container_width=True):
                st.session_state.pagina = 'dados_paciente'
                st.rerun()
            
            # Expansor de Navegação Rápida
            with st.expander("🔄 Trocar Paciente Ativo"):
                try:
                    df_lista_pacientes = conn.read("Cadastro", ttl=0)
                    if not df_lista_pacientes.empty:
                        todos_pacientes = df_lista_pacientes['Nome'].unique().tolist()
                        idx_atual = todos_pacientes.index(st.session_state.paciente) if st.session_state.paciente in todos_pacientes else 0
                        paciente_selecionado = st.selectbox("Selecione:", todos_pacientes, index=idx_atual, label_visibility="collapsed")
                        if st.button("Carregar Prontuário", use_container_width=True):
                            st.session_state.paciente = paciente_selecionado
                            st.rerun()
                except:
                    st.caption("Nenhum paciente extra encontrado.")

            st.markdown("---")
            menu = st.radio("MÓDULOS DE ATENDIMENTO", ["Avaliação Inicial 🔎", "Check-in Diário 📝", "Painel Analítico 📊"])
        else:
            menu = "Painel Analítico 📊"

        # --- FERRAMENTA ADMIN: INJEÇÃO DE DADOS CIENTÍFICOS (PBE) ---
        st.markdown("---")
        with st.expander("⚙️ Admin: Injetar Casos Reais (PBE)"):
            st.warning("Injetará 4 Fenótipos Clínicos reais com alta fidelidade biomecânica.")
            if st.button("💉 Gerar Casos PBE", use_container_width=True):
                import numpy as np
                from datetime import timedelta
                
                pacientes_mock = [
                    {
                        "Nome": "Carlos (Pós-Op LCA)", "Idade": 28, "Dx": "LCA", "Dor_Ini": 8, "Inc_Ini": 3,
                        "HMA": "Entorse em valgo dinâmico e rotação externa há 4 semanas. Relata estalido audível seguido de hemartrose imediata. Pós-operatório recente de reconstrução do LCA (Enxerto Patelar).",
                        "T_Lig": "Lachman (+), Gaveta Anterior (+), Pivot Shift (+)", "T_Men": "Nenhum achado", "T_FP": "Apreensão Patelar (+)",
                        "F_Quad": "Fraqueza Importante (< Grau 3)", "F_Isq": "Déficit Leve", "F_Glut": "Déficit Leve",
                        "ADM_Torn": "Restrita (<10cm)", "Agac": "Incapaz por Dor", "Step": "Incapaz"
                    },
                    {
                        "Nome": "Mariana (SFP)", "Idade": 34, "Dx": "SFP", "Dor_Ini": 6, "Inc_Ini": 0,
                        "HMA": "Dor anterior no joelho, caráter difuso, há 6 meses. Piora ao descer escadas (excêntrico) e sinal do cinema positivo. Aumento súbito de volume de corrida.",
                        "T_Lig": "Nenhum achado", "T_Men": "Nenhum achado", "T_FP": "Sinal de Clarke (+), Teste de Noble (+)",
                        "F_Quad": "Preservada", "F_Isq": "Preservada", "F_Glut": "Fraqueza Importante (< Grau 3)",
                        "ADM_Torn": "Restrita (<10cm)", "Agac": "Valgo Dinâmico Severo", "Step": "Estratégia de Quadril Pobre"
                    },
                    {
                        "Nome": "Roberto (Artrose/Menisco)", "Idade": 55, "Dx": "Artrose", "Dor_Ini": 7, "Inc_Ini": 2,
                        "HMA": "Dor crônica medial e rigidez matinal > 30 min. Episódios de falseio mecânico e limitação em agachamento profundo. Raio-X indica redução do espaço articular.",
                        "T_Lig": "Nenhum achado", "T_Men": "McMurray (+), Thessaly (20°) (+), Apley Compressão (+)", "T_FP": "Sinal de Rabot (Crepitação) (+)",
                        "F_Quad": "Déficit Leve", "F_Isq": "Déficit Leve", "F_Glut": "Déficit Leve",
                        "ADM_Torn": "Normal (>10cm)", "Agac": "Incapaz por Dor", "Step": "Dor Femoropatelar Aguda"
                    },
                    {
                        "Nome": "Fernanda (Tendinopatia)", "Idade": 24, "Dx": "Tendinopatia", "Dor_Ini": 7, "Inc_Ini": 0,
                        "HMA": "Atleta de vôlei. Dor focal no polo inferior da patela aguda após treinos de pliometria. Piora clara na fase de armazenamento de energia (saltos).",
                        "T_Lig": "Nenhum achado", "T_Men": "Nenhum achado", "T_FP": "Decline Squat (Tendinopatia Patelar) (+)",
                        "F_Quad": "Preservada", "F_Isq": "Déficit Leve", "F_Glut": "Preservada",
                        "ADM_Torn": "Assimétrica", "Agac": "Bom Alinhamento", "Step": "Movimento Fluido"
                    }
                ]

                data_hoje = datetime.now()
                with st.spinner("Gerando banco de dados científico..."):
                    for p in pacientes_mock:
                        db.collection("Cadastro").add({"Nome": p["Nome"], "Idade": p["Idade"], "Historia": p["HMA"]})
                        db.collection("Avaliacao_Inicial").add({
                            "Data_Avaliacao": (data_hoje - timedelta(days=70)).strftime("%d/%m/%Y"),
                            "Paciente": p["Nome"], "Membro": "Joelho", "HMA": p["HMA"], "HMP": "Nega comorbidades prévias.",
                            "Quadriceps_Forca": p["F_Quad"], "Isquio_Forca": p["F_Isq"], "Quadril_Forca": p["F_Glut"], 
                            "Tornozelo_ADM": p["ADM_Torn"], "Agachamento_Uni": p["Agac"], "Step_Down_Qualidade": p["Step"],
                            "Testes_Ligamentares": p["T_Lig"], "Testes_Meniscais": p["T_Men"], "Testes_Femoropatelar": p["T_FP"],
                            "IKDC_Inicial": 35.0, "Profissional_ID": "admin"
                        })

                        dor_atual = p["Dor_Ini"]
                        inc_atual = p["Inc_Ini"]
                        
                        for sessao in range(20):
                            dias_atras = (20 - sessao) * 3.5
                            data_sessao = data_hoje - timedelta(days=dias_atras)
                            
                            if sessao % 3 == 0 and dor_atual > 1: dor_atual -= 1 
                            if sessao % 6 == 0 and inc_atual > 0: inc_atual -= 1 
                            
                            if p["Dx"] == "LCA":
                                flex = min(135, 60 + (sessao * 4.0))
                                ext = "Déficit Grave (>-15°)" if sessao < 5 else ("Déficit Leve (-5°)" if sessao < 12 else "Completa (0°)")
                            else:
                                flex = min(140, 110 + (sessao * 1.5))
                                ext = "Completa (0°)" if p["Dx"] != "Artrose" else ("Déficit Leve (-5°)" if sessao < 15 else "Completa (0°)")

                            func_nivel = "Incapaz" if dor_atual > 6 else ("Dor Moderada" if dor_atual > 4 else ("Dor Leve" if dor_atual > 2 else "Sem Dor"))
                            
                            db.collection("Evolucao").add({
                                "Data": data_sessao.strftime("%d/%m/%Y %H:%M"), "Paciente": p["Nome"], "Membro": "Joelho",
                                "Dor": dor_atual, "Sono": "Bom" if dor_atual < 4 else "Ruim", "Inchaço": str(inc_atual), 
                                "Agachamento": func_nivel, "Step_Up": func_nivel, "Step_Down": func_nivel, 
                                "Flexao": int(flex), "Extensao": ext, "Profissional_ID": "admin"
                            })

                st.success("✅ Casos Clínicos PBE injetados! Acesse a lista para visualizar.")

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
        st.markdown(f"<p style='color: {CORES_GENUA['texto_suave']}; margin-top: -10px; text-align: center;'>Primeira Consulta | Estabelecimento de Baseline Clínica</p><br>", unsafe_allow_html=True)

        with st.form(key="form_avaliacao_inicial_firebase"):
            # Estrutura expandida com as duas novas abas
            t_anamnese, t_dor, t_flags, t_fisico, t_funcional, t_exames, t_quest = st.tabs(["🗣️ Anamnese", "💥 Dor", "🚩 Bandeiras", "📐 Físico", "🏃 Funcional", "🩻 Exames", "📋 Questionários"])
            
            with t_anamnese:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Histórico e Contexto</h4>", unsafe_allow_html=True)
                qp = st.text_input("Queixa Principal (QP) *", placeholder="O que você deixou de fazer devido à dor?")
                hma = st.text_area("História da Moléstia Atual (HMA) *", placeholder="Descrição detalhada do início e evolução do quadro...")
                sinais_sintomas = st.text_input("Sinais e Sintomas (Localização / Mapa Corporal)", placeholder="Ex: Dor na interlinha medial, estalos...")
                
                c_an1, c_an2 = st.columns(2)
                with c_an1: fat_alivio = st.text_input("Fatores de Alívio", placeholder="Ex: Repouso, decúbito, gelo...")
                with c_an2: fat_piora = st.text_input("Fatores de Piora", placeholder="Ex: Descer escadas, agachar, carga mecânica...")
                
                trat_previos = st.text_area("Tratamentos Anteriores", placeholder="Intervenções médicas e fisioterapêuticas prévias...")

            with t_dor:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Classificação e Origem</h4>", unsafe_allow_html=True)
                c_dor1, c_dor2 = st.columns(2)
                with c_dor1: class_dor = st.selectbox("Classificação da Dor *", ["Nociceptiva (Mecânica/Inflamatória)", "Neuropática (Irradiação/Queimação)", "Nociplástica (Sensibilização Central)", "Não Aplicável"])
                with c_dor2: origem_dor = st.selectbox("Origem *", ["Traumática", "Insidiosa / Sobrecarga", "Pós-operatória", "Degenerativa", "Não Aplicável"])
                
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Mapa Anatômico da Dor</h4>", unsafe_allow_html=True)
                st.info("Observe a referência visual e selecione as zonas de dor correspondentes.")
                
                c_mapa1, c_mapa2 = st.columns([1, 2])
                with c_mapa1:
                    # Inserindo uma imagem clínica de referência para o Joelho
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Knee_diagram.svg/400px-Knee_diagram.svg.png", caption="Zonas Articulares", use_container_width=True)
                with c_mapa2:
                    zonas_dor = st.multiselect("Localização Apontada (Selecione 1 ou mais) *", 
                        ["Nenhuma", "Anterior (Patela/Tendão)", "Posterior (Poplítea)", "Medial (LCM/Interlinha)", "Lateral (LCL/Trato)", "Difusa/Articular", "Irradiada"], default=["Nenhuma"])
                    mapa_dor = st.text_area("Descrição Detalhada / Outras Regiões *", value="Nenhuma", placeholder="Descreva se houver dor em outra região (Lombar, Tornozelo), ou mantenha 'Nenhuma'.")

            with t_flags:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Identificação de Risco e Fatores Biopsicossociais</h4>", unsafe_allow_html=True)
                red_flags = st.multiselect("🚨 Red Flags (Sinais de Alerta para Encaminhamento) *", 
                    ["Nenhum", "Trauma significativo recente", "Cirurgia recente", "Sinais de infecção", "Suspeita de fratura", "Dor constante/noturna intensa", "Histórico de câncer", "Sinais de TVP", "Deformidade visível"], default=["Nenhum"])
                
                yellow_cog = st.multiselect("🟡 Yellow Flags (Cognitivo-Emocionais) *", 
                    ["Nenhum", "Cinesiofobia", "Catastrofização", "Crenças limitantes", "Estresse", "Ansiedade"], default=["Nenhum"])
                
                c_fl1, c_fl2 = st.columns(2)
                with c_fl1: qualidade_sono = st.selectbox("Qualidade do Sono (Comportamental) *", ["Normal/Restaurador", "Irregular", "Ruim (Insônia/Acorda com dor)"])
                with c_fl2: 
                    # Substituído para Multi-seleção padronizada
                    fat_sociais = st.multiselect("Fatores Contextuais e Sociais *", 
                        ["Nenhum", "Problemas no trabalho", "Conflitos familiares", "Afastamento INSS", "Isolamento social", "Dificuldade financeira"], default=["Nenhum"])
                
                # Substituído para Multi-seleção padronizada
                comorbidades = st.multiselect("Comorbidades Associadas *", 
                    ["Nenhuma", "Hipertensão Arterial", "Diabetes Mellitus", "Obesidade", "Doença Reumatológica", "Cardiopatia", "Distúrbio Tireoidiano", "Asma/DPOC", "Doença Neurológica"], default=["Nenhuma"])

            with t_fisico:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Inspeção Estática e Dinâmica</h4>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns(3)
                with c_f1: derrame = st.selectbox("Derrame Articular", ["Ausente", "Leve", "Moderado", "Grave"])
                with c_f2: alinhamento = st.selectbox("Alinhamento Postural", ["Normal", "Valgo", "Varo", "Recurvatum", "Flexo"])
                with c_f3: marcha = st.selectbox("Padrão de Marcha (Estrutural)", ["Normal", "Antálgica", "Claudicante", "Uso de dispositivo"])
                
                c_f4, c_f5 = st.columns(2)
                with c_f4: 
                    trofismo = st.selectbox("Trofismo Muscular", ["Normal", "Hipotrófico"])
                    perimetria = st.text_input("Perimetria (Se hipotrófico)", placeholder="Ex: -2cm no VMO direito")
                with c_f5: 
                    pele = st.multiselect("Alterações Cutâneas", ["Nenhuma", "Equimose", "Hematoma", "Cicatrizes", "Fístulas"])
                
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Palpação</h4>", unsafe_allow_html=True)
                c_p1, c_p2, c_p3 = st.columns(3)
                with c_p1: palpacao_comp = st.multiselect("Estruturas Dolorosas", ["Anterior", "Medial", "Lateral", "Posterior", "Nenhuma"])
                with c_p2: godet = st.radio("Sinal de Godet (Edema)", ["Negativo", "Positivo"])
                with c_p3: temp = st.radio("Temperatura", ["Normal", "Aumentada", "Diminuída"])

                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Testes Especiais Ortopédicos (Positivos)</h4>", unsafe_allow_html=True)
                t_lig = st.multiselect("Testes Ligamentares", ["Nenhum", "Lachman", "Gaveta Anterior", "Gaveta Posterior", "Estresse Valgo", "Estresse Varo", "Pivot Shift", "Dial Test"])
                t_men = st.multiselect("Testes Meniscais", ["Nenhum", "McMurray", "Apley"])

            with t_funcional:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Força Muscular e Dinamometria</h4>", unsafe_allow_html=True)
                forca_qual = st.selectbox("Força Geral (Qualitativa 0 a 5)", ["Grau 5 (Normal)", "Grau 4 (Boa)", "Grau 3 (Razoável)", "Grau 2 (Fraca)", "Grau 1 (Traço)", "Grau 0 (Nula)"])
                
                st.caption("Insira os valores em kgf ou N da dinamometria isométrica:")
                c_din1, c_din2, c_din3 = st.columns(3)
                with c_din1: din_quad = st.number_input("Quadríceps", min_value=0.0, step=1.0)
                with c_din2: din_isq = st.number_input("Isquiotibiais", min_value=0.0, step=1.0)
                with c_din3: din_glut = st.number_input("Glúteo Médio", min_value=0.0, step=1.0)
                
                # Motor de cálculo em tempo real
                if din_quad > 0 and din_isq > 0:
                    st.info(f"📊 **Razão Isquios/Quadríceps (I/Q):** {(din_isq/din_quad)*100:.1f}%")

                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Mobilidade Articular (Goniometria)</h4>", unsafe_allow_html=True)
                c_adm1, c_adm2 = st.columns(2)
                with c_adm1: adm_flex = st.number_input("Flexão Máxima (Graus)", min_value=0, max_value=160, value=130)
                with c_adm2: adm_ext = st.number_input("Extensão Máxima (Graus)", min_value=-20, max_value=20, value=0)

                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Controle Motor e Testes Relacionais</h4>", unsafe_allow_html=True)
                c_cm1, c_cm2 = st.columns(2)
                with c_cm1: 
                    cm_agac = st.selectbox("Agachamento (Bi/Unipodal)", ["Bom controle", "Valgo dinâmico", "Estratégia pobre de quadril", "Incapaz"])
                    dor_agac = st.slider("Dor no Agachamento (0-10)", 0, 10, 0)
                with c_cm2:
                    cm_step = st.selectbox("Subir/Descer Escadas", ["Bom controle", "Valgo dinâmico", "Estratégia pobre", "Incapaz"])
                    dor_step = st.slider("Dor no Step (0-10)", 0, 10, 0)
                
                c_cm3, c_cm4 = st.columns(2)
                with c_cm3:
                    cm_lunge = st.selectbox("Afundo (Lunge) *", ["Bom controle", "Desvio de tronco", "Valgo dinâmico", "Incapaz", "Não avaliado"])
                    dor_lunge = st.slider("Dor no Afundo (0-10) *", 0, 10, 0)
                with c_cm4:
                    # Substituído para Multi-seleção de testes padronizados
                    flexibilidade = st.multiselect("Flexibilidade / Retrações (Testes Positivos) *", 
                        ["Nenhuma", "Thomas (+) - Iliopsoas", "Thomas (+) - Reto Femoral", "Ely (+) - Reto Femoral", "Ober (+) - Trato Iliotibial", "Sentar e Alcançar (Isquios)"], default=["Nenhuma"])

            with t_exames:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Exames Complementares e Imagem</h4>", unsafe_allow_html=True)
                tipos_exames = st.multiselect("Exames Apresentados *", 
                    ["Nenhum", "Raio-X", "Ressonância Magnética (RM)", "Tomografia Computadorizada (TC)", "Ultrassonografia (USG)", "Eletroneuromiografia"], default=["Nenhum"])
                
                laudo_exames = st.text_area("Laudo / Achados Importantes *", value="Nenhum", 
                    placeholder="Descreva os achados relevantes ou mantenha 'Nenhum' se não houver exames de imagem.")

            with t_quest:
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Escala Funcional (LEFS - Adaptada para Joelho)</h4>", unsafe_allow_html=True)
                st.caption("Selecione o grau de dificuldade do paciente para as seguintes atividades hoje (0 = Incapaz, 4 = Sem dificuldade):")
                
                opcoes_resp = {"Incapaz / Extrema Dificuldade": 0, "Muita Dificuldade": 1, "Dificuldade Moderada": 2, "Um Pouco de Dificuldade": 3, "Nenhuma Dificuldade": 4}
                perguntas_lefs = [
                    "1. Agachar ou ajoelhar", "2. Andar 2 quarteirões", "3. Subir um lance de escadas", 
                    "4. Descer um lance de escadas", "5. Ficar em pé por 1 hora", "6. Correr em terreno plano",
                    "7. Fazer trabalho pesado", "8. Mudança rápida de direção (Corte)"
                ]
                
                score_lefs = 0
                c_q1, c_q2 = st.columns(2)
                for i, p in enumerate(perguntas_lefs):
                    col = c_q1 if i < 4 else c_q2
                    with col:
                        # O Streamlit guarda a resposta e somamos o valor correspondente (0 a 4)
                        resp = st.selectbox(p, list(opcoes_resp.keys()), key=f"lefs_{i}")
                        score_lefs += opcoes_resp[resp]
                
                score_max = len(perguntas_lefs) * 4
                pct_funcional = (score_lefs / score_max) * 100
                
                # Motor de Interpretação Automática
                if pct_funcional < 30: interp = "🚨 Função Muito Ruim (Alta dependência mecânica / Fase Aguda)"
                elif pct_funcional < 60: interp = "🟡 Função Regular (Limitação funcional moderada)"
                elif pct_funcional < 85: interp = "🟢 Função Boa (Independência nas AVDs)"
                else: interp = "⭐ Função Excelente (Apto para transição desportiva)"
                    
                st.info(f"📊 **Resultado Automático:** {score_lefs}/{score_max} pontos ({pct_funcional:.1f}%) — **Interpretação:** {interp}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("💾 SALVAR AVALIAÇÃO INICIAL", use_container_width=True):
                # Adicionamos 'laudo_exames' na validação rigorosa
                campos_texto = [qp, hma, sinais_sintomas, fat_alivio, fat_piora, trat_previos, mapa_dor, laudo_exames]
                if any(campo.strip() == "" for campo in campos_texto):
                    st.error("⚠️ ERRO: Todos os campos abertos são obrigatórios. Se não houver dado clínico, preencha com 'Nenhum' ou 'N/A'.")
                else:
                    dados_avaliacao = {
                        "Data_Avaliacao": datetime.now().strftime("%d/%m/%Y"),
                        "Paciente": st.session_state.paciente, "Membro": st.session_state.membro_ativo,
                        "QP": qp, "HMA": hma, "Sinais_Sintomas": sinais_sintomas,
                        "Fatores_Alivio": fat_alivio, "Fatores_Piora": fat_piora, "Tratamentos_Previos": trat_previos,
                        "Class_Dor": class_dor, "Origem_Dor": origem_dor, 
                        "Zonas_Dor": ", ".join(zonas_dor), "Mapa_Dor": mapa_dor,
                        "Red_Flags": ", ".join(red_flags), "Yellow_Cog": ", ".join(yellow_cog), 
                        "Sono": qualidade_sono, "Fatores_Sociais": ", ".join(fat_sociais), "Comorbidades": ", ".join(comorbidades),
                        "Derrame": derrame, "Alinhamento": alinhamento, "Marcha": marcha,
                        "Trofismo": trofismo, "Perimetria": perimetria, "Pele": ", ".join(pele),
                        "Palpacao": ", ".join(palpacao_comp), "Godet": godet, "Temperatura": temp,
                        "Testes_Ligamentares": ", ".join(t_lig), "Testes_Meniscais": ", ".join(t_men),
                        "Forca_Qualitativa": forca_qual, "Din_Quad": din_quad, "Din_Isq": din_isq, "Din_Glut": din_glut,
                        "ADM_Flex": adm_flex, "ADM_Ext": adm_ext, "Flexibilidade": ", ".join(flexibilidade),
                        "CM_Agachamento": cm_agac, "Dor_Agachamento": dor_agac,
                        "CM_Step": cm_step, "Dor_Step": dor_step, "CM_Lunge": cm_lunge, "Dor_Lunge": dor_lunge,
                        "Exames_Apresentados": ", ".join(tipos_exames), "Laudo_Exames": laudo_exames, # <- Novos dados de Exame
                        "Score_LEFS_Pts": score_lefs, "Score_LEFS_Pct": pct_funcional, "Interpretacao_LEFS": interp, # <- Novos dados do Questionário
                        "Profissional_ID": st.session_state.get("user_email", "admin")
                    }
                    
                    df_av = conn.read(worksheet="Avaliacao_Inicial", ttl=0)
                    nova_linha_av = pd.DataFrame([dados_avaliacao])
                    if df_av.empty: df_av = nova_linha_av
                    else: df_av = pd.concat([df_av, nova_linha_av], ignore_index=True)
                        
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
        
        # --- A. RESGATE DO CADASTRO ---
        try:
            df_cad = conn.read(worksheet="Cadastro", ttl=0)
            registro_p = df_cad[df_cad['Nome'].str.strip() == p_sel].iloc[-1]
            hist_clinica = registro_p.get('Diagnostico_Rapido', registro_p.get('Historia', 'Sem HMA base'))
            idade_p = int(float(registro_p.get('Idade', 0))) if pd.notna(registro_p.get('Idade')) else "N/A"
            dx_rapido_base = registro_p.get('Diagnostico_Rapido', 'Não especificado')
        except:
            hist_clinica = "Não disponível."; idade_p = "-"; dx_rapido_base = "-"

        # --- B. RESGATE DA AVALIAÇÃO BASE (TESTES E FLAGS) ---
        try:
            df_av = conn.read(worksheet="Avaliacao_Inicial", ttl=0)
            av_p = df_av[df_av['Paciente'].str.strip() == p_sel].iloc[-1]
            av_data = av_p.get('Data_Avaliacao', 'N/A')
            av_qp = av_p.get('QP', 'Não registrada')
            av_classdor = av_p.get('Class_Dor', 'Não avaliada')
            av_red = av_p.get('Red_Flags', 'Nenhuma')
            av_derrame = av_p.get('Derrame', 'Não avaliado')
            av_tlig = av_p.get('Testes_Ligamentares', '')
            av_tmen = av_p.get('Testes_Meniscais', '')
            tem_av = True
        except:
            tem_av = False

        st.header(f"📊 Painel Analítico: Joelho")

        # 1. HEADER DO PACIENTE
        st.markdown(f"""
            <div style='background-color: #ffffff; border: 1px solid #e9ecef; border-left: 5px solid {CORES_GENUA['primaria']}; padding: 20px; border-radius: 8px; margin-bottom: 15px;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                    <h3 style='margin: 0; color: {CORES_GENUA['primaria']}; font-weight: 700;'>👤 {p_sel}</h3>
                    <span style='background-color: #f1f3f5; color: {CORES_GENUA['primaria']}; padding: 6px 15px; border-radius: 20px; font-weight: 600;'>{idade_p} anos</span>
                </div>
                <p style='margin: 0; color: #495057;'><strong>Dx Triagem:</strong> {dx_rapido_base}</p>
            </div>
        """, unsafe_allow_html=True)

        # 2. CARD DE AVALIAÇÃO FÍSICA
        if tem_av:
            with st.expander(f"📋 Consultar Ficha de Avaliação Base (Data: {av_data})"):
                c_av1, c_av2 = st.columns(2)
                with c_av1:
                    st.markdown("**🗣️ Anamnese e Dor:**")
                    st.markdown(f"- **QP:** {av_qp}")
                    st.markdown(f"- **Tipo de Dor:** {av_classdor}")
                    st.markdown(f"- **Red Flags:** {av_red}")
                with c_av2:
                    st.markdown("**🔬 Exame Físico e Testes:**")
                    st.markdown(f"- **Derrame Articular:** {av_derrame}")
                    st.markdown(f"- **Ligamentares:** {av_tlig if av_tlig and av_tlig != 'Nenhum' else 'Nenhum achado'}")
                    st.markdown(f"- **Meniscais:** {av_tmen if av_tmen and av_tmen != 'Nenhum' else 'Nenhum achado'}")
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
        # --- 1. PROCESSAMENTO LONGITUDINAL (PREPARAÇÃO PARA GRÁFICOS) ---
        df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]
        
        if 'Dor' not in df_p.columns: df_p['Dor'] = 0
        df_p['Dor'] = pd.to_numeric(df_p['Dor'], errors='coerce').fillna(0)
        
        col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
        if col_inc not in df_p.columns: df_p[col_inc] = 0
        df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)

        for col, default in [('Flexao', 90), ('Extensao', 'Sem dados'), ('Agachamento', 'Sem Dor'), ('Step_Up', 'Sem Dor'), ('Step_Down', 'Sem Dor')]:
            if col not in df_p.columns: df_p[col] = default

        # Função PBE: Calcula a Função Geral (LSI) para TODAS as sessões do histórico
        def calcular_lsi(row):
            mapa = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
            pts = (mapa.get(row.get('Agachamento', 'Sem Dor'), 10) +
                   mapa.get(row.get('Step_Up', 'Sem Dor'), 10) +
                   mapa.get(row.get('Step_Down', 'Sem Dor'), 10)) / 30.0
            return min(max(float(pts * 100), 0.0), 100.0)
            
        df_p['LSI'] = df_p.apply(calcular_lsi, axis=1)

        # Seleção da Sessão Atual
        c_vazio, c_seletor = st.columns([4, 1])
        with c_seletor:
            sessao_escolhida = st.selectbox("📅 Analisar Sessão:", options=df_p['Sessão_Num'].tolist()[::-1], index=0)
        ultima = df_p[df_p['Sessão_Num'] == sessao_escolhida].iloc[0]

        # --- 2. O CÉREBRO CLÍNICO BAYESIANO ---
        dor_atual = int(ultima.get('Dor', 0))
        inchaco_atual = int(ultima.get('Inchaco_N', 0))
        sono_atual = ultima.get('Sono', 'Regular')
        lsi_atual = ultima['LSI']
        media_dor = df_p['Dor'].mean()

        # Árvore de Decisão PBE
        if ultima.get('Agachamento') == 'Incapaz' and inchaco_atual >= 2 and dor_atual >= 8:
            fenotipo = "🚨 Risco Estrutural (Sinal de Alerta)"
            diretriz = "Incapacidade de descarga de peso + Edema Agudo. Indicação de imagem e restrição de carga."
        elif ultima.get('Step_Down') in ['Incapaz', 'Dor Moderada'] and inchaco_atual <= 1:
            fenotipo = "🟣 Provável Síndrome Femoropatelar"
            diretriz = "Dor na desaceleração excêntrica. O foco é fortalecimento póstero-lateral do quadril e isometria (0-45°)."
        elif ultima.get('Extensao') in ['Déficit Grave (>-15°)', 'Déficit Leve (-5°)'] and inchaco_atual >= 2:
            fenotipo = "🟤 Bloqueio Articular / Derangement"
            diretriz = "Déficit de extensão terminal associado a derrame. Possível bloqueio meniscal. Priorizar mobilidade acessória."
        elif ultima.get('Agachamento') in ['Incapaz', 'Dor Moderada'] and ultima.get('Extensao') == 'Completa (0°)' and inchaco_atual == 0:
            fenotipo = "🟠 Perfil Tendinopático"
            diretriz = "Dor em armazenamento/liberação elástica (Pliometria). Aplicação de isometria pesada para efeito analgésico."
        elif dor_atual <= 3 and inchaco_atual <= 1 and lsi_atual >= 80:
            fenotipo = "🟢 Fase de Remodelamento"
            diretriz = "Alta tolerância mecânica. Progressão segura para exercícios de mudança de direção e retorno ao esporte."
        else:
            fenotipo = "🔵 Acomodação de Carga"
            diretriz = "Sinais inflamatórios mistos. Modular volume e intensidade conforme o sintoma limitante."

        status_clinico = "Excelente" if lsi_atual >= 85 else "Regular" if lsi_atual >= 60 else "Atenção"

        # --- 3. DASHBOARD DE MÉTRICAS VISUAIS ---
        m1, m2, m3, m4 = st.columns(4)
        delta_pct = ((dor_atual - media_dor) / media_dor * 100) if media_dor > 0 else 0
        m1.metric("Dor Atual (vs Média)", f"{dor_atual}/10", f"{delta_pct:.0f}%", delta_color="inverse")
        m2.metric("Inchaço", f"Grau {inchaco_atual}")
        m3.metric("Prontidão (LSI)", f"{lsi_atual:.0f}%", status_clinico)
        m4.metric("Diagnóstico IA", fenotipo.split()[1])
        st.write("---")

        st.markdown(f"**Progresso Base para Alta: {lsi_atual:.0f}%**")
        st.progress(lsi_atual / 100)

        # --- 4. ABAS GRÁFICAS DE ALTA PERFORMANCE (MATPLOTLIB) ---
        t1, t2, t3, t4 = st.tabs(["📊 Correlação Dor x Função", "📉 Evolução Biomecânica", "🧠 Raciocínio Clínico", "🎯 Gatilhos"])
        
        with t1:
            st.markdown("**Gráfico de Dispersão: Tolerância ao Movimento**")
            st.caption("Verifica se a redução da dor resultou em ganhos reais de funcionalidade (LSI).")
            fig1, ax1 = plt.subplots(figsize=(10, 4))
            ax1.scatter(df_p['Dor'], df_p['LSI'], color=CORES_GENUA['secundaria'], s=100, alpha=0.8, edgecolors='white')
            
            # Tendência Linar (Regressão)
            if len(df_p) > 2:
                z = np.polyfit(df_p['Dor'], df_p['LSI'], 1)
                p = np.poly1d(z)
                ax1.plot(df_p['Dor'], p(df_p['Dor']), color=CORES_GENUA['primaria'], linestyle='--', lw=1)
                
            ax1.set_xlabel("Dor (EVA 0-10)"); ax1.set_ylabel("Prontidão (LSI %)")
            ax1.set_xlim(-0.5, 10.5); ax1.set_ylim(-5, 105)
            ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
            st.pyplot(fig1)

        with t2:
            st.markdown("**Evolução Longitudinal de Sintomas e Mobilidade**")
            fig2, ax2 = plt.subplots(figsize=(10, 4))
            
            # Eixo Duplo: Dor (Esquerda) e Flexão (Direita)
            ax2.plot(df_p['Sessão_Num'], df_p['Dor'], color=CORES_GENUA['alerta_erro'], marker='o', lw=2, label="Dor")
            ax2.set_ylabel("Dor", color=CORES_GENUA['alerta_erro'], fontweight='bold')
            ax2.set_ylim(-0.5, 10.5)
            
            ax3 = ax2.twinx()
            ax3.plot(df_p['Sessão_Num'], df_p['Flexao'], color=CORES_GENUA['secundaria'], marker='s', lw=2, linestyle=':', label="Flexão (°)")
            ax3.set_ylabel("Flexão (°)", color=CORES_GENUA['secundaria'], fontweight='bold')
            ax3.set_ylim(0, 160)
            
            ax2.spines['top'].set_visible(False); ax3.spines['top'].set_visible(False)
            st.pyplot(fig2)

        with t3:
            st.info("A Inteligência Artificial cruza inchaço, dor em padrões de carga elástica/excêntrica e déficits articulares. **O diagnóstico final pertence ao Fisioterapeuta.**")
            st.markdown(f"**🔬 Análise do Algoritmo:** {fenotipo}")
            st.markdown(f"**💡 Conduta Baseada em Evidência:** {diretriz}")
            
            st.markdown("---")
            col_b1, col_b2 = st.columns(2)
            col_b1.metric("Amplitude de Flexão", f"{ultima.get('Flexao', 90)}°")
            col_b2.info(f"Extensão Terminal Atual: {ultima.get('Extensao', 'Sem dados')}")

        with t4:
            st.success(f"💡 **Variável Bio-Psico-Social (Sono):** Paciente apresentou padrão predominante '{sono_atual}' na avaliação.")
            st.caption("O sistema rastreia oscilações de dor que não respondem à carga mecânica para deduzir possível Sensibilização Central baseada no sono.")

        # Gerador PDF de Segurança
        st.markdown("---")
        if st.button("📄 Exportar Evolução em PDF"):
            st.info("Módulo de PDF em reestruturação para suportar a nova matriz de gráficos em alta resolução.")

# --- SISTEMA DE PROTEÇÃO GLOBAL CONTRA TELA BRANCA (FAIL-SAFE) ---
# Se o aplicativo se perder na navegação, este escudo força o retorno à tela de pacientes.
paginas_validas = ['login', 'dados_paciente', 'selecao_membro', 'painel_clinico']
if st.session_state.get('pagina') not in paginas_validas:
    st.session_state.pagina = 'dados_paciente'
    st.rerun()


