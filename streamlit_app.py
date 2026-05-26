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
# O Streamlit gere a barra lateral de forma nativa
st.sidebar.image(NOVO_LOGO_GENUA, use_container_width=True)
st.sidebar.markdown("---")

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
import re

if not firebase_admin._apps:
    try:
        # Tenta carregar o JSON de forma tradicional
        cred_dict = json.loads(st.secrets["FIREBASE_JSON"])
    except Exception as e:
        # MECANISMO DE AUTOCURA INTERNO
        # Se houver quebras de linha corrompidas no Secrets, o sistema reconstrói o dicionário nativamente.
        raw_text = st.secrets["FIREBASE_JSON"]
        
        proj_id_match = re.search(r'"project_id":\s*"([^"]+)"', raw_text)
        email_match = re.search(r'"client_email":\s*"([^"]+)"', raw_text)
        pk_match = re.search(r'"private_key":\s*"(.*?)"', raw_text, re.DOTALL)
        
        if proj_id_match and email_match and pk_match:
            pk_content = pk_match.group(1).replace("\\n", "\n")
            while "\n\n" in pk_content:
                pk_content = pk_content.replace("\n\n", "\n")
                
            cred_dict = {
                "type": "service_account",
                "project_id": proj_id_match.group(1),
                "private_key": pk_content.strip(),
                "client_email": email_match.group(1),
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        else:
            st.error("❌ Erro crítico: As credenciais do Firebase contidas no Secrets estão ilegíveis.")
            st.stop()

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

# PAGINA 1: LOGIN (DESIGN CLÁSSICO)
if st.session_state.pagina == 'login':
    # Três colunas simples para centralizar
    c_espaco1, c_login, c_espaco2 = st.columns([1, 2, 1])
    
    with c_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try:
            st.image(NOVO_LOGO_GENUA, use_container_width=True)
        except Exception:
            st.markdown(f"<h1 style='text-align: center; color: {CORES_GENUA['primaria']};'>GENUA</h1>", unsafe_allow_html=True)
            
        st.markdown(f"<h3 style='text-align: center; color: {CORES_GENUA['texto_suave']};'>Acesso Seguro</h3>", unsafe_allow_html=True)
        
        email = st.text_input("E-mail Profissional", placeholder="dr.nome@clinica.com")
        senha = st.text_input("Senha", type="password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("ENTRAR NO SISTEMA", use_container_width=True, type="primary"):
            if email and senha:
                st.session_state.user_email = email
                st.session_state.pagina = 'dados_paciente'
                st.rerun()
            else:
                st.warning("⚠️ Preencha e-mail e senha.")
                
        st.markdown("<p style='text-align: center; color: #adb5bd; font-size: 12px; margin-top: 20px;'>GENUA HealthTech © 2026<br>Ambiente Seguro e Criptografado</p>", unsafe_allow_html=True)

# PAGINA 2: SELEÇÃO DE PACIENTE E CADASTRO COMPLETO
elif st.session_state.pagina == 'dados_paciente':
    st.header("👤 Gestão de Pacientes")

    # 1. LEITURA DIRETA E NATIVA (Imune a falhas de formatação Pandas)
    try:
        docs = db.collection("Cadastro").stream()
        lista = list(set([doc.to_dict().get("Nome") for doc in docs if doc.to_dict().get("Nome")]))
    except:
        lista = []

    paciente = st.selectbox("Selecione um paciente existente ou adicione um novo:", ["+ Novo Paciente"] + lista)


        
        # 2. CONTAINER LIVRE (Sem camisas de força de formulários)
        with st.container():
            st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Identificação do Paciente</h4>", unsafe_allow_html=True)
            nome = st.text_input("Nome Completo *")
            
            c_cad1, c_cad2, c_cad3 = st.columns(3)
            with c_cad1: 
                data_padrao = datetime(2000, 1, 1)
                data_minima = datetime(datetime.now().year - 100, 1, 1)
                dt_nasc = st.date_input("Data de Nascimento *", value=data_padrao, min_value=data_minima, max_value=datetime.today(), format="DD/MM/YYYY")
            with c_cad2: cpf = st.text_input("CPF")
            with c_cad3: telefone = st.text_input("Telefone (WhatsApp)")
            
            c_cad4, c_cad5, c_cad6 = st.columns(3)
            with c_cad4: email = st.text_input("E-mail")
            with c_cad5: cidade = st.text_input("Cidade e Estado")
            with c_cad6: ocupacao = st.text_input("Atividade Ocupacional")
            
            st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Diagnóstico Clinico (Triagem)</h4>", unsafe_allow_html=True)
            dx_clinico = st.text_input("Diagnóstico Clínico/Médico", placeholder="Ex: LCA, Condropatia, Tendinopatia...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 3. BOTÃO REATIVO DE COMUNICAÇÃO NATIVA
            if st.button("💾 Salvar Cadastro", use_container_width=True, type="primary"):
                if nome.strip() == "":
                    st.error("⚠️ O Nome é obrigatório para abrir o prontuário.")
                else:
                    with st.spinner("🔄 Injetando dados diretamente no núcleo do Firebase..."):
                        try:
                            idade_calc = (datetime.now().date() - dt_nasc).days // 365
                            novo_cad = {
                                "Nome": nome.strip(), "Data_Nascimento": dt_nasc.strftime("%d/%m/%Y"), 
                                "Idade": idade_calc, "CPF": cpf, "Telefone": telefone, 
                                "Email": email, "Cidade_Estado": cidade, "Ocupacao": ocupacao, 
                                "Diagnostico_Clinico": dx_clinico, "Historia": "" 
                            }
                            
                            # O COMANDO DE SALVAMENTO ABSOLUTO
                            db.collection("Cadastro").add(novo_cad)
                            
                            st.session_state.paciente = nome.strip()
                            st.session_state.membro_ativo = "Joelho" 
                            st.session_state.pagina = 'painel_clinico'
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Falha crítica reportada pelo servidor: {e}")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Abrir Prontuário", use_container_width=True, type="primary"):
            st.session_state.paciente = paciente
            st.session_state.membro_ativo = "Joelho"
            st.session_state.pagina = 'painel_clinico'
            st.rerun()

# PAGINA 4: PAINEL CLÍNICO (UX ESTILO APP NATIVO)
elif st.session_state.pagina == 'painel_clinico':
    paciente_alvo = st.session_state.get('paciente_alvo', False)
    
    # 1. Menu Lateral Limpo e Unificado
    with st.sidebar:
        if not paciente_alvo: 
            st.markdown(f"<h3 style='color: {CORES_GENUA['primaria']}; text-align: center;'>👤 {st.session_state.paciente}</h3>", unsafe_allow_html=True)
            
            # Expansor de Navegação Rápida
            with st.expander("🔄 Trocar Paciente Ativo"):
                try:
                    docs = db.collection("Cadastro").stream()
                    todos_pacientes = list(set([doc.to_dict().get("Nome") for doc in docs if doc.to_dict().get("Nome")]))
                    
                    if todos_pacientes:
                        idx_atual = todos_pacientes.index(st.session_state.paciente) if st.session_state.get('paciente') in todos_pacientes else 0
                        paciente_selecionado = st.selectbox("Selecione:", todos_pacientes, index=idx_atual, label_visibility="collapsed")
                        if st.button("Carregar Prontuário", use_container_width=True):
                            st.session_state.paciente = paciente_selecionado
                            st.session_state.pagina = 'painel_clinico'
                            st.rerun()
                    else:
                        st.caption("Nenhum paciente encontrado.")
                except Exception as e:
                    st.caption("Erro ao carregar lista de pacientes.")

            st.markdown("---")
            # MENU COMPLETO E PROTEGIDO
            menu = st.radio("MÓDULOS DE ATENDIMENTO", ["Avaliação Inicial 🔎", "Check-in Diário 📝", "Painel Analítico 📊"])
        else:
            menu = "Painel Analítico 📊"

    # 2. App Header (Barra Superior de Navegação Nativa)
    if not paciente_alvo:
        c_back, c_title, c_vazio = st.columns([1, 4, 1])
        with c_back:
            # BOTÃO VOLTAR COM ROTA CORRIGIDA
            if st.button("⬅️ Voltar", type="secondary", use_container_width=False, help="Voltar para seleção de pacientes"):
                st.session_state.pagina = 'dados_paciente'
                st.session_state.paciente = None
                st.rerun()
        with c_title:
            membro = st.session_state.get('membro_ativo', 'Joelho')
            st.markdown(f"<h3 style='text-align: center; color: {CORES_GENUA['primaria']}; margin-top: 5px; font-size: 1.6rem;'>{membro}</h3>", unsafe_allow_html=True)
        st.markdown("<hr style='margin-top: -5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

    # --- MÓDULO 1: AVALIAÇÃO INICIAL (O MARCO ZERO) ---

    # --- MÓDULO 1: AVALIAÇÃO INICIAL (O MARCO ZERO) ---
    if menu == "Avaliação Inicial 🔎":
        st.markdown(f"<p style='color: {CORES_GENUA['texto_suave']}; margin-top: -10px; text-align: center;'>Primeira Consulta | Estabelecimento de Baseline Clínica</p><br>", unsafe_allow_html=True)

        with st.container():
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
                
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Mapa Anatômico da Dor Interativo</h4>", unsafe_allow_html=True)
                st.info("🎯 Clique diretamente na imagem do joelho abaixo para marcar os pontos exatos de dor do paciente. Cada clique gerará um marcador vermelho.")
                
                if "pontos_dor" not in st.session_state:
                    st.session_state.pontos_dor = []
                if "last_click" not in st.session_state:
                    st.session_state.last_click = None
                if "map_key" not in st.session_state:
                    st.session_state.map_key = 0
                
                c_mapa1, c_mapa2 = st.columns([1.3, 1.7])
                with c_mapa1:
                    try:
                        from PIL import ImageDraw, Image
                        from streamlit_image_coordinates import streamlit_image_coordinates
                        
                        img_base = Image.open("mapa_joelho.png").convert("RGB")
                        img_base.thumbnail((350, 600))
                        draw = ImageDraw.Draw(img_base)
                        
                        for pt in st.session_state.pontos_dor:
                            x, y = pt["x"], pt["y"]
                            draw.ellipse([(x-6, y-6), (x+6, y+6)], fill="#dc3545", outline="white", width=2)
                        
                        value = streamlit_image_coordinates(img_base, key=f"mapa_interativo_joelho_{st.session_state.map_key}")
                        
                        if value is not None and value != st.session_state.last_click:
                            st.session_state.last_click = value
                            st.session_state.pontos_dor.append({"x": value["x"], "y": value["y"]})
                            st.rerun()
                            
                        if st.button("❌ Limpar Marcações", use_container_width=True):
                            st.session_state.pontos_dor = []
                            st.session_state.last_click = None
                            st.session_state.map_key += 1
                            st.rerun()
                            
                    except ModuleNotFoundError:
                        st.warning("⚠️ Instalação necessária: adicione 'streamlit-image-coordinates' ao requirements.txt.")
                    except FileNotFoundError:
                        st.warning("⚠️ Arquivo 'mapa_joelho.png' não encontrado na pasta raiz.")
                        
                with c_mapa2:
                    zonas_dor = st.multiselect(
                        "Localização Apontada (Selecione 1 ou mais) *", 
                        ["Nenhuma", "Anterior (Patela/Tendão)", "Posterior (Poplítea)", "Medial (LCM/Interlinha)", "Lateral (LCL/Trato)", "Difusa/Articular", "Irradiada"], 
                        default=["Nenhuma"],
                        key="seletor_zonas_dor_unico"
                    )
                    
                    coordenadas_texto = "; ".join([f"({p['x']},{p['y']})" for p in st.session_state.pontos_dor]) if st.session_state.pontos_dor else "Nenhuma coordenada"
                    
                    mapa_dor = st.text_area(
                        "Descrição Detalhada / Outras Regiões *", 
                        value="Nenhuma", 
                        placeholder="Descreva particularidades anatômicas da dor constatada...", 
                        height=150,
                        key="texto_mapa_dor_unico"
                    )

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
                t_lig = st.multiselect("Testes Ligamentares", ["Nenhum", "Lachman", "Gaveta Anterior", "Gaveta Posterior", "Estresse Valgo", "Estresse Varo", "Pivot Shift", "Dial Test"], key="t_lig_unico")
                t_men = st.multiselect("Testes Meniscais", ["Nenhum", "McMurray", "Apley"], key="t_men_unico")
                t_pat = st.multiselect("Testes Femoropatelar", ["Nenhum", "Sinal de Clarke", "Apreensão Patelar", "Decline Squat (Tendinopatia)", "Teste de Noble (Trato Iliotibial)"], key="t_pat_unico")

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
                st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Bateria de Questionários Funcionais (PBE)</h4>", unsafe_allow_html=True)
                st.caption("Expanda o questionário desejado. A pontuação e a interpretação clínica são geradas em tempo real. Preencha apenas as escalas adequadas ao fenótipo do paciente atual.")

                # --- 1. LEFS (Geral) ---
                with st.expander("📝 LEFS (Escala Funcional da Extremidade Inferior)"):
                    opcoes_lefs = {"Incapaz / Extrema Dificuldade": 0, "Muita Dificuldade": 1, "Dificuldade Moderada": 2, "Um Pouco de Dificuldade": 3, "Nenhuma Dificuldade": 4}
                    perguntas_lefs = ["1. Agachar ou ajoelhar", "2. Andar 2 quarteirões", "3. Subir um lance de escadas", "4. Descer um lance de escadas", "5. Ficar em pé por 1 hora", "6. Correr em terreno plano", "7. Fazer trabalho pesado", "8. Mudança rápida de direção (Corte)"]
                    score_lefs = 0
                    c_l1, c_l2 = st.columns(2)
                    for i, p in enumerate(perguntas_lefs):
                        with (c_l1 if i < 4 else c_l2): score_lefs += opcoes_lefs[st.selectbox(p, list(opcoes_lefs.keys()), key=f"lefs_{i}")]
                    
                    pct_lefs = (score_lefs / 32) * 100
                    interp_lefs = "🚨 Função Muito Ruim" if pct_lefs < 30 else "🟡 Função Regular" if pct_lefs < 60 else "🟢 Função Boa" if pct_lefs < 85 else "⭐ Função Excelente"
                    st.info(f"📊 **Resultado LEFS:** {score_lefs}/32 pontos ({pct_lefs:.1f}%) — **Interpretação:** {interp_lefs}")

                # --- 2. VISA-P (Tendinopatia Patelar) ---
                with st.expander("🎯 VISA-P (Tendinopatia Patelar)"):
                    st.caption("Responda de 0 (Dor máxima / Incapaz) a 10 (Sem dor / Perfeito). O questionário soma 100 pontos.")
                    score_visap = 0
                    c_v1, c_v2 = st.columns(2)
                    with c_v1:
                        score_visap += st.slider("1. Dor ao ficar sentado", 0, 10, 10, key="vp1")
                        score_visap += st.slider("2. Dor ao descer escadas", 0, 10, 10, key="vp2")
                        score_visap += st.slider("3. Dor ao esticar ativamente o joelho", 0, 10, 10, key="vp3")
                        score_visap += st.slider("4. Dor ao fazer um afundo (lunge)", 0, 10, 10, key="vp4")
                    with c_v2:
                        score_visap += st.slider("5. Problemas para agachar", 0, 10, 10, key="vp5")
                        score_visap += st.slider("6. Dor durante/após salto ou esporte", 0, 10, 10, key="vp6")
                        
                        p7 = st.selectbox("7. Esporte Atual", ["Não consegue (0 pts)", "Modificado/Menos frequente (4 pts)", "Competindo com dor (7 pts)", "Competindo sem dor (10 pts)"], key="vp7")
                        score_visap += 0 if "0 pts" in p7 else 4 if "4 pts" in p7 else 7 if "7 pts" in p7 else 10
                        
                        p8 = st.selectbox("8. Tempo de dor no esporte", ["Incapaz (0 pts)", "Para aos 15 min (7 pts)", "Dor após o esporte (15 pts)", "Sem dor (30 pts)"], key="vp8")
                        score_visap += 0 if "0 pts" in p8 else 7 if "7 pts" in p8 else 15 if "15 pts" in p8 else 30

                    interp_visap = "🚨 Tendinopatia Severa/Aguda" if score_visap < 50 else "🟡 Fase Reativa" if score_visap < 80 else "🟢 Remodelamento/Alta"
                    st.info(f"📊 **Resultado VISA-P:** {score_visap}/100 pontos — **Interpretação:** {interp_visap}")

                # --- 3. LYSHOLM (Ligamentar e Meniscal) ---
                with st.expander("🦵 Escala de Lysholm (Ligamentar e Meniscal)"):
                    c_ly1, c_ly2 = st.columns(2)
                    score_lysholm = 0
                    with c_ly1:
                        score_lysholm += int(st.selectbox("Mancar", ["5 - Nenhum", "3 - Leve ou Periódico", "0 - Grave ou Constante"]).split(" -")[0])
                        score_lysholm += int(st.selectbox("Apoio", ["5 - Nenhum (Não precisa)", "2 - Usa bengala/muleta", "0 - Impossível apoiar"]).split(" -")[0])
                        score_lysholm += int(st.selectbox("Travamento", ["15 - Nenhum", "10 - Sensação de travamento", "6 - Ocasional", "2 - Frequente", "0 - Articulação travada"]).split(" -")[0])
                        score_lysholm += int(st.selectbox("Instabilidade", ["25 - Nunca cede", "20 - Raramente", "15 - Frequente no esporte", "10 - Ocasional em AVDs", "5 - Frequente em AVDs", "0 - A cada passo"]).split(" -")[0])
                    with c_ly2:
                        score_lysholm += int(st.selectbox("Dor", ["25 - Nenhuma", "20 - Inconstante ou Leve", "15 - Durante esporte pesado", "10 - Durante esporte leve", "5 - Após andar 2km", "0 - Constante"]).split(" -")[0])
                        score_lysholm += int(st.selectbox("Inchaço", ["10 - Nenhum", "6 - Após esforço intenso", "2 - Após AVDs", "0 - Constante"]).split(" -")[0])
                        score_lysholm += int(st.selectbox("Subir Escadas", ["10 - Sem problemas", "6 - Levemente prejudicado", "2 - Um degrau por vez", "0 - Impossível"]).split(" -")[0])
                        score_lysholm += int(st.selectbox("Agachamento", ["5 - Sem problemas", "4 - Levemente prejudicado", "2 - Não passa de 90 graus", "0 - Impossível"]).split(" -")[0])
                    
                    interp_lysholm = "🚨 Ruim (Instabilidade Severa)" if score_lysholm < 65 else "🟡 Regular" if score_lysholm < 84 else "🟢 Bom" if score_lysholm < 95 else "⭐ Excelente"
                    st.info(f"📊 **Resultado Lysholm:** {score_lysholm}/100 pontos — **Interpretação:** {interp_lysholm}")

                # --- 4. WOMAC (Osteoartrite) ---
                with st.expander("🦴 Índice WOMAC (Osteoartrite)"):
                    st.caption("Responda de 0 (Nenhuma) a 4 (Muito Intensa). O sistema inverterá o cálculo automaticamente para % (100% = Excelente, 0% = Severo).")
                    w_op = {"Nenhuma": 0, "Leve": 1, "Moderada": 2, "Intensa": 3, "Muito Intensa": 4}
                    score_womac = 0
                    
                    c_w1, c_w2, c_w3 = st.columns(3)
                    with c_w1:
                        st.markdown("**Dor (5 itens)**")
                        for p in ["Andar", "Subir escadas", "Deitar (Noturna)", "Sentar/Repouso", "Ficar em pé"]: score_womac += w_op[st.selectbox(p, list(w_op.keys()), key=f"wd_{p}")]
                    with c_w2:
                        st.markdown("**Rigidez (2 itens)**")
                        for p in ["Ao acordar", "Durante o dia"]: score_womac += w_op[st.selectbox(p, list(w_op.keys()), key=f"wr_{p}")]
                    with c_w3:
                        st.markdown("**Função - AVDs (17 itens condensados em 8 chaves)**")
                        for p in ["Descer escadas", "Levantar da cadeira", "Ficar em pé", "Entrar/Sair do carro", "Calçar meias", "Sair da cama", "Banho", "Tarefa doméstica"]: score_womac += w_op[st.selectbox(p, list(w_op.keys()), key=f"wf_{p}")]
                    
                    max_w = (5 + 2 + 8) * 4
                    pct_womac = 100 - ((score_womac / max_w) * 100) # Invertido para que 100% seja o melhor
                    interp_womac = "🚨 Artrose Severa Limitante" if pct_womac < 30 else "🟡 Artrose Moderada" if pct_womac < 70 else "🟢 Artrose Leve" if pct_womac < 90 else "⭐ Excelente (Sem impacto)"
                    st.info(f"📊 **Resultado WOMAC:** Pontos Brutos: {score_womac} | **Funcionalidade Normalizada: {pct_womac:.1f}%** — {interp_womac}")

                # --- 5. KOOS (Avaliação Geral do Joelho) ---
                with st.expander("🟢 Score KOOS (O.A. e Lesões Gerais)"):
                    st.caption("O KOOS original tem 42 perguntas. Para agilidade clínica sem perda matemática, defina a média de intensidade relatada pelo paciente em cada domínio (0 = Extremo, 4 = Nenhum).")
                    koos_op = {"Extremo / Sempre": 0, "Severo / Frequente": 1, "Moderado": 2, "Leve / Raro": 3, "Nenhum / Nunca": 4}
                    c_k1, c_k2 = st.columns(2)
                    score_koos = 0
                    with c_k1:
                        score_koos += koos_op[st.selectbox("Sintomas e Inchaço (Média)", list(koos_op.keys()), index=4, key="k1")]
                        score_koos += koos_op[st.selectbox("Nível de Dor (Média)", list(koos_op.keys()), index=4, key="k2")]
                        score_koos += koos_op[st.selectbox("Atividades Diárias - AVDs (Média)", list(koos_op.keys()), index=4, key="k3")]
                    with c_k2:
                        score_koos += koos_op[st.selectbox("Esportes e Recreação (Média)", list(koos_op.keys()), index=4, key="k4")]
                        score_koos += koos_op[st.selectbox("Qualidade de Vida (Média)", list(koos_op.keys()), index=4, key="k5")]
                    
                    pct_koos = (score_koos / 20) * 100
                    interp_koos = "🚨 Risco Funcional (Fase Aguda)" if pct_koos < 40 else "🟡 Limitação Moderada" if pct_koos < 80 else "🟢 Alta Performance"
                    st.info(f"📊 **Resultado KOOS (Score Agregado): {pct_koos:.1f}%** — **Interpretação:** {interp_koos}")

                # --- 6. IKDC (Subjetivo Geral) ---
                with st.expander("✚ IKDC Subjetivo"):
                    st.caption("Como a matemática do IKDC cruza múltiplos formatos, utilize os blocos principais para gerar o percentual bruto automático.")
                    c_ik1, c_ik2 = st.columns(2)
                    with c_ik1:
                        ik_dor = st.slider("Nível da Pior Dor (0=Pior, 10=Nenhuma)", 0, 10, 10, key="ik1")
                        ik_freq = st.selectbox("Frequência da Dor", ["Constante (0 pts)", "Diária (2 pts)", "Semanal (4 pts)", "Rara (7 pts)", "Nenhuma (10 pts)"], key="ik2")
                        ik_pts_freq = 0 if "0 pts" in ik_freq else 2 if "2 pts" in ik_freq else 4 if "4 pts" in ik_freq else 7 if "7 pts" in ik_freq else 10
                    with c_ik2:
                        ik_func = st.slider("Função do Joelho Antes da Lesão (0-10)", 0, 10, 10, key="ik3")
                        ik_func_atual = st.slider("Função do Joelho Atual (0-10)", 0, 10, 5, key="ik4")
                    
                    # Aproximação proporcional algorítmica baseada nos domínios do IKDC
                    score_ikdc = min(100, ((ik_dor + ik_pts_freq + (ik_func_atual*2)) / 40) * 100)
                    interp_ikdc = "🚨 Baixa Função Subjetiva" if score_ikdc < 60 else "🟡 Desempenho Moderado" if score_ikdc < 85 else "🟢 Excelente Desempenho"
                    st.info(f"📊 **Resultado IKDC Algorítmico: {score_ikdc:.1f}%** — **Interpretação:** {interp_ikdc}")

            st.markdown("<br>", unsafe_allow_html=True)

            # --- GATILHO INTELIGENTE PARA O CHECK-IN DIÁRIO ---
            st.markdown("---")
            st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>🎯 Alvos Funcionais para Monitorização</h4>", unsafe_allow_html=True)
            st.caption("Selecione os testes que farão parte do Check-in Diário deste paciente.")
            
            lista_testes_disp = ["Agachamento Bipodal", "Agachamento Unipodal", "Step Down", "Lunge (Afundo)", "Salto (Hop Test)", "Corrida"]
            testes_alvo = st.multiselect("Testes Funcionais Diários:", lista_testes_disp, default=["Agachamento Bipodal", "Step Down"])
            st.markdown("<br>", unsafe_allow_html=True)
           
            # --- MOTOR DE SALVAMENTO INTELIGENTE (UX PBE) ---
            if st.button("💾 SALVAR AVALIAÇÃO INICIAL", use_container_width=True, type="primary"):
                
                # Função interna (Autocura): Preenche campos vazios automaticamente
                def check_vazio(texto):
                    return texto if texto.strip() != "" else "Não relatado"

                # Regra de Ouro: Apenas a Queixa Principal impede o salvamento
                if qp.strip() == "":
                    st.error("⚠️ ERRO: A 'Queixa Principal (QP)' é obrigatória para abrir o prontuário. Descreva o motivo da consulta.")
                else:
                    dados_avaliacao = {
                        "Data_Avaliacao": datetime.now().strftime("%d/%m/%Y"),
                        "Paciente": st.session_state.paciente, "Membro": st.session_state.membro_ativo,
                        
                        # Campos Abertos Autopreenchíveis
                        "QP": qp, 
                        "HMA": check_vazio(hma), 
                        "Sinais_Sintomas": check_vazio(sinais_sintomas),
                        "Fatores_Alivio": check_vazio(fat_alivio), 
                        "Fatores_Piora": check_vazio(fat_piora), 
                        "Tratamentos_Previos": check_vazio(trat_previos),
                        "Mapa_Dor": check_vazio(mapa_dor),
                        "Laudo_Exames": check_vazio(laudo_exames),
                        
                        # Campos Fechados e Listas
                        "Class_Dor": class_dor, "Origem_Dor": origem_dor, 
                        "Zonas_Dor": ", ".join(zonas_dor) if zonas_dor else "Nenhuma", 
                        "Red_Flags": ", ".join(red_flags) if red_flags else "Nenhuma", 
                        "Yellow_Cog": ", ".join(yellow_cog) if yellow_cog else "Nenhum", 
                        "Sono": qualidade_sono, 
                        "Fatores_Sociais": ", ".join(fat_sociais) if fat_sociais else "Nenhum", 
                        "Comorbidades": ", ".join(comorbidades) if comorbidades else "Nenhuma",
                        "Derrame": derrame, "Alinhamento": alinhamento, "Marcha": marcha,
                        "Trofismo": trofismo, "Perimetria": perimetria, 
                        "Pele": ", ".join(pele) if pele else "Normal",
                        "Palpacao": ", ".join(palpacao_comp) if palpacao_comp else "Sem dor", 
                        "Godet": godet, "Temperatura": temp,
                        "Testes_Ligamentares": ", ".join(t_lig) if t_lig else "Não testado", 
                        "Testes_Meniscais": ", ".join(t_men) if t_men else "Não testado",
                        "Forca_Qualitativa": forca_qual, "Din_Quad": din_quad, "Din_Isq": din_isq, "Din_Glut": din_glut,
                        "ADM_Flex": adm_flex, "ADM_Ext": adm_ext, 
                        "Flexibilidade": ", ".join(flexibilidade) if flexibilidade else "Normal",
                        "CM_Agachamento": cm_agac, "Dor_Agachamento": dor_agac,
                        "CM_Step": cm_step, "Dor_Step": dor_step, "CM_Lunge": cm_lunge, "Dor_Lunge": dor_lunge,
                        "Exames_Apresentados": ", ".join(tipos_exames) if tipos_exames else "Nenhum", 
                        
                        # --- GATILHO INTELIGENTE INSERIDO NO SÍTIO CERTO ---
                        "Testes_Alvo": testes_alvo,
                        
                        # DADOS DA BATERIA DE QUESTIONÁRIOS
                        "LEFS_Pct": pct_lefs, "Interpretacao_LEFS": interp_lefs,
                        "VISA_P_Pts": score_visap, "Interpretacao_VISA_P": interp_visap,
                        "Lysholm_Pts": score_lysholm, "Interpretacao_Lysholm": interp_lysholm,
                        "WOMAC_Pct": pct_womac, "Interpretacao_WOMAC": interp_womac,
                        "KOOS_Pct": pct_koos, "IKDC_Pct": score_ikdc,
                        
                        "Profissional_ID": st.session_state.get("user_email", "admin")
                    }
                    
                    with st.spinner("🔄 Gravando avaliação clínica na nuvem..."):
                        try:
                            db.collection("Avaliacao_Inicial").add(dados_avaliacao)
                            st.success("✅ Avaliação Inicial registrada com sucesso!")
                        except Exception as e:
                            st.error(f"❌ Falha de sincronização na avaliação: {e}")

    # --- MÓDULO 2: CHECK-IN DIÁRIO (O MUTANTE) ---
    elif menu == "Check-in Diário 📝":
        st.markdown(f"<h3 style='color: {CORES_GENUA['primaria']};'>📝 Check-in Diário e Evolução</h3>", unsafe_allow_html=True)
        
        # 1. O "Caçador": Busca os testes definidos na Avaliação Inicial
        testes_para_hoje = ["Agachamento Bipodal"] # Valor de segurança caso haja falha
        try:
            docs_aval = db.collection("Avaliacao_Inicial").where("Paciente", "==", st.session_state.paciente).stream()
            lista_aval = [doc.to_dict() for doc in docs_aval]
            if lista_aval:
                ultima_aval = sorted(lista_aval, key=lambda x: x.get('Data_Avaliacao', ''))[-1]
                testes_para_hoje = ultima_aval.get("Testes_Alvo", ["Agachamento Bipodal"])
        except Exception:
            pass

        # 2. Dados Basais da Sessão
        c_chk1, c_chk2 = st.columns(2)
        with c_chk1:
            data_sessao = st.date_input("Data da Sessão", datetime.now())
            dor_atual = st.slider("Dor no Repouso (EVA)", 0, 10, 0)
            inchaco_atual = st.selectbox("Inchaço / Derrame Articular", ["Nenhum", "Leve (+)", "Moderado (++)", "Intenso (+++)"])
        
        with c_chk2:
            adm_flex_atual = st.number_input("Flexão Máxima Atingida (Graus)", min_value=0, max_value=160, value=90)
            adm_ext_atual = st.selectbox("Extensão Terminal", ["Completa (0°)", "Déficit de -5°", "Déficit de -10° ou pior"])
            sono_atual = st.selectbox("Como dormiu esta noite?", ["Bem", "Acordou com dor", "Insónia"])

        # 3. Módulo Dinâmico de Testes Funcionais (A sua Escala Oficial)
        st.markdown("---")
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>🎯 Desempenho Funcional Hoje</h4>", unsafe_allow_html=True)
        st.caption("Classifique a relação entre dor e função para os testes definidos como alvo.")
        
        opcoes_escala = [
            "Sem Dor (0 )", 
            "Dor Leve (1 - 3)", 
            "Dor Moderada (4 - 7)", 
            "Dor Grave (8 - 10)", 
            "Incapaz (Não realiza)"
        ]
        
        resultados_testes = {}
        for teste in testes_para_hoje:
            resposta = st.selectbox(f"Desempenho no {teste}:", opcoes_escala, key=f"chk_{teste}")
            resultados_testes[teste] = resposta
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 4. Motor de Salvamento do Check-in
        if st.button("💾 REGISTAR SESSÃO DIÁRIA", use_container_width=True, type="primary"):
            
            # Pega o resultado do primeiro teste para compatibilidade com o Gráfico/PDF antigo
            texto_agachamento = list(resultados_testes.values())[0] if resultados_testes else "Não testado"
            
            dados_sessao = {
                "Data": data_sessao.strftime("%Y-%m-%d"),
                "Paciente": st.session_state.paciente,
                "Dor": dor_atual,
                "Flexao": adm_flex_atual,
                "Extensao": adm_ext_atual,
                "Inchaço": inchaco_atual,
                "Sono": sono_atual,
                "Testes_Funcionais": resultados_testes, # Guarda o dicionário inteiro com os testes
                "Agachamento": texto_agachamento, # Mantém o PDF antigo sem quebrar
                "Profissional_ID": st.session_state.get("user_email", "admin")
            }
            
            with st.spinner("A registar a sessão na nuvem..."):
                try:
                    db.collection("Evolucao").add(dados_sessao)
                    st.success("✅ Check-in diário registado com sucesso! Os gráficos e o PDF já foram atualizados.")
                except Exception as e:
                    st.error(f"❌ Erro ao gravar: {e}")
                
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
            hist_clinica = registro_p.get('Diagnostico_Clinico', registro_p.get('Historia', 'Sem HMA base'))
            idade_p = int(float(registro_p.get('Idade', 0))) if pd.notna(registro_p.get('Idade')) else "N/A"
            dx_clinico_base = registro_p.get('Diagnostico_Clinico', 'Não especificado')
        except:
            hist_clinica = "Não disponível."; idade_p = "-"; dx_clinico_base = "-"

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
                <p style='margin: 0; color: #495057;'><strong>Dx Triagem:</strong> {dx_clinico_base}</p>
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

        # --- MÓDULO DE EXPORTAÇÃO COMPLEXO (LAUDO MÉDICO + MATRIZ DE GRÁFICOS) ---
        st.markdown("---")
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>📄 Exportação de Laudo Clínico Avançado</h4>", unsafe_allow_html=True)
        st.caption("Gera um relatório oficial em formato PDF contendo os dados da Avaliação Inicial, Scores PBE e os gráficos reais de evolução clínica.")
        
        if st.button("⚙️ GERAR RELATÓRIO COM GRÁFICOS", use_container_width=True):
            with st.spinner("Buscando dados na nuvem e renderizando gráficos no laudo..."):
                try:
                    # 1. Busca Segura dos Dados no Firebase Firestore
                    docs_aval = db.collection("Avaliacao_Inicial").where("Paciente", "==", st.session_state.paciente).stream()
                    lista_aval = [doc.to_dict() for doc in docs_aval]
                    dados_aval = lista_aval[-1] if lista_aval else {}
                    
                    docs_evo = db.collection("Evolucao").where("Paciente", "==", st.session_state.paciente).stream()
                    historico = [doc.to_dict() for doc in docs_evo]
                    
                    # 2. Inicialização do Documento PDF
                    pdf = FPDF()
                    pdf.add_page()
                    
                    # Cabeçalho Institucional
                    pdf.set_font('Arial', 'B', 16)
                    pdf.set_text_color(16, 62, 85) # Azul Genua
                    pdf.cell(0, 10, 'GENUA - Inteligencia Clinica Integrada', 0, 1, 'C')
                    pdf.set_font('Arial', 'I', 10)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 5, 'Laudo de Evolucao Funcional e Biomecanica', 0, 1, 'C')
                    pdf.ln(10)
                    
                    # Identificação Clínica do Paciente
                    pdf.set_font('Arial', 'B', 12)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(0, 8, f"Paciente: {st.session_state.paciente}", 0, 1)
                    pdf.set_font('Arial', '', 10)
                    pdf.cell(0, 6, f"Membro Alvo: {st.session_state.get('membro_ativo', 'Joelho')}", 0, 1)
                    pdf.cell(0, 6, f"Data de Emissao: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
                    pdf.ln(5)
                    
                    # 3. Bloco da Avaliação Inicial e Scores Funcionais
                    if dados_aval:
                        pdf.set_font('Arial', 'B', 11)
                        pdf.set_fill_color(240, 240, 240)
                        pdf.cell(0, 8, ' MARCOS DA AVALIACAO INICIAL', 0, 1, fill=True)
                        pdf.set_font('Arial', '', 10)
                        
                        qp_texto = str(dados_aval.get("QP", "N/A")).encode('ascii', 'ignore').decode('ascii')
                        pdf.multi_cell(0, 6, f"Queixa Principal: {qp_texto}")
                        
                        pdf.ln(2)
                        pdf.set_font('Arial', 'B', 10)
                        pdf.cell(0, 6, 'Métricas Baseadas em Evidência (PROMs):', 0, 1)
                        pdf.set_font('Arial', '', 10)
                        
                        if float(dados_aval.get('LEFS_Pct', 0)) > 0:
                            pdf.cell(0, 6, f"- LEFS (Funcionalidade Geral): {float(dados_aval.get('LEFS_Pct', 0)):.1f}% ({dados_aval.get('Interpretacao_LEFS', '')})", 0, 1)
                        if float(dados_aval.get('WOMAC_Pct', 0)) > 0:
                            pdf.cell(0, 6, f"- WOMAC (Osteoartrite): {float(dados_aval.get('WOMAC_Pct', 0)):.1f}%", 0, 1)
                        if float(dados_aval.get('VISA_P_Pts', 0)) > 0:
                            pdf.cell(0, 6, f"- VISA-P (Tendinopatia Patelar): {float(dados_aval.get('VISA_P_Pts', 0))} pts", 0, 1)
                        if float(dados_aval.get('Lysholm_Pts', 0)) > 0:
                            pdf.cell(0, 6, f"- Lysholm (Lesao de Menisco/Ligamento): {float(dados_aval.get('Lysholm_Pts', 0))} pts", 0, 1)
                        if float(dados_aval.get('KOOS_Pct', 0)) > 0:
                            pdf.cell(0, 6, f"- KOOS (Score Agregado): {float(dados_aval.get('KOOS_Pct', 0)):.1f}%", 0, 1)
                        if float(dados_aval.get('IKDC_Pct', 0)) > 0:
                            pdf.cell(0, 6, f"- IKDC Subjetivo: {float(dados_aval.get('IKDC_Pct', 0)):.1f}%", 0, 1)
                    
                    # 4. Geração Dinâmica da Matriz Gráfica
                    if historico:
                        # Ordena o histórico por data para os gráficos fazerem sentido cronológico
                        historico_ordenado = sorted(historico, key=lambda x: x.get('Data', ''))
                        
                        datas = [ev.get('Data', 'N/A')[:5] for ev in historico_ordenado]
                        dores = [float(ev.get('Dor', 0)) for ev in historico_ordenado]
                        flexoes = [float(ev.get('Flexao', 0)) for ev in historico_ordenado]
                        
                        # --- GRÁFICO 1: EVOLUÇÃO DA DOR (EVA) ---
                        pdf.ln(5)
                        pdf.set_font('Arial', 'B', 11)
                        pdf.cell(0, 8, ' CURVA DE EVOLUCAO DA DOR (EVA)', 0, 1, fill=True)
                        
                        fig, ax = plt.subplots(figsize=(6.5, 2.2))
                        ax.plot(datas, dores, marker='o', color='#103E55', linewidth=2.5, label='Intensidade da Dor')
                        ax.set_ylabel('Escala EVA (0-10)', color='#1A252C')
                        ax.set_ylim(-0.5, 10.5)
                        ax.grid(True, linestyle='--', alpha=0.5)
                        plt.tight_layout()
                        
                        img_buf_dor = io.BytesIO()
                        plt.savefig(img_buf_dor, format='png', dpi=200)
                        img_buf_dor.seek(0)
                        plt.close(fig)
                        
                        # Desenha o gráfico de dor direto na página atual
                        pdf.image(img_buf_dor, w=180, h=60)
                        
                        # --- GRÁFICO 2: AMPLITUDE DE MOVIMENTO (ADM FLEXÃO) ---
                        pdf.add_page() # Move os gráficos biomecânicos para a página 2
                        pdf.set_font('Arial', 'B', 11)
                        pdf.cell(0, 8, ' EVOLUCAO DA AMPLITUDE DE MOVIMENTO (FLEXAO)', 0, 1, fill=True)
                        
                        fig2, ax2 = plt.subplots(figsize=(6.5, 2.2))
                        ax2.plot(datas, flexoes, marker='s', color='#398E9B', linewidth=2.5, label='Flexao Voluntaria')
                        ax2.set_ylabel('Graus ()', color='#1A252C')
                        ax2.grid(True, linestyle='--', alpha=0.5)
                        plt.tight_layout()
                        
                        img_buf_flex = io.BytesIO()
                        plt.savefig(img_buf_flex, format='png', dpi=200)
                        img_buf_flex.seek(0)
                        plt.close(fig2)
                        
                        # Desenha o gráfico de ADM na página 2
                        pdf.image(img_buf_flex, w=180, h=60)
                        pdf.ln(5)
                        
                        # Tabela Textual de Apoio das últimas sessões
                        pdf.set_font('Arial', 'B', 10)
                        pdf.cell(0, 6, 'Historico Consolidado das Últimas Sessões:', 0, 1)
                        pdf.set_font('Arial', '', 9)
                        for ev in historico[-8:]:
                            linha = f"Data: {ev.get('Data', 'N/A')[:10]} | Dor: {ev.get('Dor', '-')} | Flexao: {ev.get('Flexao', '-')} | Carga Cles.: {ev.get('Agachamento', '-')}"
                            pdf.cell(0, 5, linha, 0, 1)
                    else:
                        pdf.ln(5)
                        pdf.cell(0, 6, "Nenhum registro evolutivo encontrado para geracao de graficos.", 0, 1)
                        
                    # 5. Encerramento e Assinatura do Profissional
                    pdf.ln(15)
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, '___________________________________________________', 0, 1, 'C')
                    prof = st.session_state.get('user_email', 'Fisioterapeuta Responsavel')
                    pdf.cell(0, 6, prof, 0, 1, 'C')

                    # Empacotamento de Saída Estável
                    try:
                        pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    except:
                        pdf_bytes = bytes(pdf.output())
                    
                    st.download_button(
                        label="📥 BAIXAR LAUDO COMPLETO COM GRÁFICOS (PDF)",
                        data=pdf_bytes,
                        file_name=f"Laudo_Clinico_{st.session_state.paciente.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                    st.success("✅ Laudo clínico completo compilado! Clique no botão verde acima para baixar.")
                    
                except Exception as e:
                    st.error(f"❌ Erro crítico ao processar o laudo gráfico: {e}")

# --- SISTEMA DE PROTEÇÃO GLOBAL CONTRA TELA BRANCA (FAIL-SAFE) ---
# Se o aplicativo se perder na navegação, este escudo força o retorno à tela de pacientes.
paginas_validas = ['login', 'dados_paciente', 'selecao_membro', 'painel_clinico']
if st.session_state.get('pagina') not in paginas_validas:
    st.session_state.pagina = 'dados_paciente'
    st.rerun()


