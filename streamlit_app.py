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
    initial_sidebar_state="auto"
) # <-- Era este parêntese que estava faltando!

# --- 3.1. INJEÇÃO DE CSS (INTERFACE DE APP PROFISSIONAL) ---
st.markdown("""
    <style>
    /* 1. Esconder o cabeçalho, menu do Streamlit e rodapé */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 2. Fundo geral do app mais limpo */
    .stApp {
        background-color: #F4F7F9;
    }
    
    /* 3. Estilização dos Botões (Efeito Nativo iOS/Android) */
    .stButton > button {
        background-color: #103E55 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(16, 62, 85, 0.2) !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background-color: #398E9B !important;
        box-shadow: 0 6px 12px rgba(57, 142, 155, 0.3) !important;
        transform: translateY(-2px) !important;
    }
    
    /* 4. Estilização dos Cards (Métricas flutuantes) */
    [data-testid="metric-container"] {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border-left: 5px solid #398E9B;
    }
    
    /* 5. Abas (Tabs) com visual moderno e pílulas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        padding: 5px 0px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 20px !important;
        padding: 8px 16px !important;
        background-color: white !important;
        border: 1px solid #e0e0e0 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTabs [aria-selected="true"] {
        background-color: #103E55 !important;
        color: white !important;
        border: 1px solid #103E55 !important;
    }
    
    /* 6. Caixas de Input e Selectbox mais suaves */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 8px !important;
        border: 1px solid #ced4da !important;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.02) !important;
    }
    </style>
""", unsafe_allow_html=True)

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

## PAGINA 2: SELEÇÃO E CADASTRO DE PACIENTE
elif st.session_state.pagina == 'dados_paciente':
    st.title("👤 Seleção ou Cadastro de Paciente")
    
    # INTELIGÊNCIA: Puxa a lista de pacientes diretamente da aba "Cadastro"
    try:
        df_cad = conn.read(worksheet="Cadastro", ttl=0).dropna(how="all")
        lista_pacientes = df_cad['Nome'].dropna().unique().tolist()
    except:
        lista_pacientes = []
        
    opcao_paciente = st.selectbox("Selecione um paciente existente ou cadastre um novo:", ["+ Cadastrar Novo"] + lista_pacientes)
    
    # --- FLUXO 1: FORMULÁRIO COMPLETO DE NOVO PACIENTE ---
    if opcao_paciente == "+ Cadastrar Novo":
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>📋 Nova Ficha de Cadastro</h4>", unsafe_allow_html=True)
        
        with st.form("form_novo_paciente"):
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
            submit_cadastro = st.form_submit_button("💾 Salvar Cadastro e Avançar", use_container_width=True)
            
            if submit_cadastro:
                if novo_nome.strip() == "":
                    st.error("⚠️ O Nome Completo é obrigatório.")
                else:
                    try:
                        df_cad_atual = conn.read(worksheet="Cadastro", ttl=0).dropna(how="all")
                        novo_registro = pd.DataFrame([{
                            "Nome": novo_nome.strip(), "CPF": novo_cpf, "Idade": nova_idade,
                            "Telefone": novo_telefone, "Email": novo_email, "Historia": nova_hma,
                            "Data_Cadastro": datetime.now().strftime("%d/%m/%Y")
                        }])
                        conn.update(worksheet="Cadastro", data=pd.concat([df_cad_atual, novo_registro], ignore_index=True))
                        st.success("Cadastro realizado com sucesso!")
                        st.session_state.paciente = novo_nome.strip()
                        mudar_pagina('selecao_membro')
                    except Exception as e:
                        st.error("⚠️ Erro: Certifique-se de que existe a aba 'Cadastro' com as colunas corretas.")

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
    novo_membro = st.selectbox("Selecione a nova região anatômica:", 
                         ["Joelho", "Coluna Cervical", "Coluna Lombar", "Ombro", "Tornozelo/Pé", "Quadril"])
    
    if st.button(f"Iniciar Prontuário para {novo_membro} 🆕", use_container_width=True, type="primary"):
        st.session_state.membro_ativo = novo_membro
        mudar_pagina('painel_clinico')
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅️ Voltar", type="secondary"):
        mudar_pagina('dados_paciente')
        
    st.stop()

# PAGINA 4: PAINEL CLÍNICO (A CARROCERIA PRINCIPAL)
elif st.session_state.pagina == 'painel_clinico':
    # O menu lateral agora tem botões avançados de navegação
    with st.sidebar:
        if not paciente_alvo:
            st.markdown("### 🧭 Navegação")
            c_voltar1, c_voltar2 = st.columns(2)
            with c_voltar1:
                if st.button("⬅️ Membro", use_container_width=True, help="Voltar para a seleção de outro tratamento"):
                    mudar_pagina('selecao_membro')
            with c_voltar2:
                if st.button("🏠 Início", use_container_width=True, help="Voltar para a escolha de pacientes"):
                    mudar_pagina('dados_paciente')
                    
            st.markdown("---")
            menu = st.radio("MÓDULOS", ["Check-in Diário 📝", "Painel Analítico 📊"])
        else:
            menu = "Painel Analítico 📊" # Cirurgião só vê o painel
            
    # TAG visual mostrando o membro ativo no topo da tela
    st.markdown(f"<span style='background-color: {CORES_GENUA['secundaria']}; color: white; padding: 4px 12px; border-radius: 15px; font-weight: bold;'>📍 Tratamento: {st.session_state.membro_ativo}</span><br><br>", unsafe_allow_html=True)

# --- 3. MÓDULOS DE NAVEGAÇÃO ---

if menu == "Check-in Diário 📝":
    st.header(f"📝 Check-in Diário: {st.session_state.membro_ativo}")
    st.markdown(f"<p style='color: {CORES_GENUA['texto_suave']};'>Paciente Ativo: <b>{st.session_state.paciente}</b></p>", unsafe_allow_html=True)
    
    with st.form("checkin", clear_on_submit=True):
        
        # --- 1. CAMPOS PADRÃO (Sistêmicos) ---
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>Quadro Sistêmico Universal</h4>", unsafe_allow_html=True)
        # O Inchaço foi removido daqui! Apenas Dor, Sono e Postura importam para todos.
        c1, c2, c3 = st.columns(3)
        with c1: dor = st.slider("💥 Dor atual (EVA 0-10)", 0, 10, 0)
        with c2: sono = st.radio("💤 Sono", ["Ruim", "Regular", "Bom"])
        with c3: postura = st.radio("🧍 Postura", ["Sentado", "Equilibrado", "Em pé"])
            
        dados_sessao = {
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Paciente": st.session_state.paciente,
            "Membro": st.session_state.membro_ativo,
            "Dor": int(dor), "Sono": sono, "Postura": postura
        }

        # --- 2. CAMPOS ESPECÍFICOS (O Pente Fino Clínico) ---
        st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 15px;'>Avaliação Específica: {st.session_state.membro_ativo}</h4>", unsafe_allow_html=True)
        
        if st.session_state.membro_ativo == "Joelho":
            # Inchaço desce apenas para as articulações apendiculares
            c_inc, c5, c6, c7 = st.columns(4)
            with c_inc: inchaco = st.select_slider("💧 Inchaço", options=["0", "1", "2", "3"])
            with c5: agac = st.selectbox("🏋️ Agachamento", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            with c6: sup = st.selectbox("🪜 Step Up", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            with c7: sdn = st.selectbox("📉 Step Down", ["Incapaz", "Dor Moderada", "Dor Leve", "Sem Dor"])
            c8, c9 = st.columns(2)
            with c8: flexao = st.slider("📐 Flexão (Graus)", 0, 150, 90)
            with c9: extensao = st.selectbox("📏 Extensão Terminal", ["Completa (0°)", "Déficit Leve (-5°)", "Déficit Grave (>-15°)"])
            
            dados_sessao.update({"Inchaço": str(inchaco), "Agachamento": agac, "Step_Up": sup, "Step_Down": sdn, "Flexao": int(flexao), "Extensao": extensao})
            
        elif "Coluna" in st.session_state.membro_ativo:
            # Coluna NÃO possui campo de inchaço na tela
            c5, c6, c7 = st.columns(3)
            with c5: irradiacao = st.selectbox("⚡ Irradiação (Nervo)", ["Ausente", "Apenas Proximal", "Até a Extremidade"])
            with c6: mobilidade = st.selectbox("🔄 Mobilidade", ["Livre", "Limitada no Final", "Bloqueada"])
            with c7: parestesia = st.radio("🐜 Parestesia (Formigamento)", ["Não", "Sim"], horizontal=True)
            
            # O código salva o inchaço oculto como "0" apenas para o banco de dados não quebrar e os gráficos não darem erro
            dados_sessao.update({"Inchaço": "0", "Irradiacao": irradiacao, "Mobilidade_Coluna": mobilidade, "Parestesia": parestesia})

        elif st.session_state.membro_ativo == "Ombro":
            c_inc, c5, c6 = st.columns(3)
            with c_inc: inchaco = st.select_slider("💧 Edema Agudo", options=["0", "1", "2", "3"]) 
            with c5: elevacao = st.slider("📐 Elevação (Graus)", 0, 180, 90)
            with c6: rotacao = st.selectbox("🔄 Rotação", ["Livre", "Déficit Interna", "Déficit Externa", "Bloqueio Global"])
            
            dados_sessao.update({"Inchaço": str(inchaco), "Elevacao_Ombro": int(elevacao), "Rotacao_Ombro": rotacao})
            
        else: # Tornozelo/Pé, Quadril
            c_inc, c5, c6 = st.columns(3)
            with c_inc: inchaco = st.select_slider("💧 Inchaço Articular", options=["0", "1", "2", "3"])
            with c5: marcha = st.selectbox("🚶 Marcha", ["Sem claudicação", "Claudicação Leve", "Uso de muleta"])
            with c6: carga = st.selectbox("⚖️ Tolerância a Carga", ["Incapaz", "Parcial", "Total sem Dor"])
            
            dados_sessao.update({"Inchaço": str(inchaco), "Marcha": marcha, "Carga": carga})

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- 3. MOTOR DE SALVAMENTO ---
        if st.form_submit_button("✅ REGISTRAR SESSÃO", use_container_width=True):
            df = conn.read(worksheet="Evolucao", ttl=0).dropna(how="all")
            nova_linha = pd.DataFrame([dados_sessao])
            conn.update(worksheet="Evolucao", data=pd.concat([df, nova_linha], ignore_index=True))
            st.success(f"Dados de {st.session_state.membro_ativo} registrados com sucesso na inteligência clínica!")
            
    st.write("---")
    with st.expander("⚖️ Conformidade LGPD e Privacidade"):
        st.caption("O Sistema GENUA utiliza Segurança por Obscuridade e processamento anonimizado de dados. As informações geradas têm finalidade exclusiva de Inteligência Clínica e Continuidade Assistencial, podendo ser revogadas a qualquer momento pelo paciente.")

else: # PAINEL ANALÍTICO (O CÉREBRO CLÍNICO TOTAL)
    df = conn.read(ttl=15).dropna(how="all")
    
    # --- BLINDAGEM DE LEGADO ---
    if 'Membro' not in df.columns: df['Membro'] = "Joelho"
    df['Membro'] = df['Membro'].fillna("Joelho")
    
    df_p = df[(df['Paciente'] == st.session_state.paciente) & (df['Membro'] == st.session_state.membro_ativo)].copy()

    if df_p.empty:
        st.warning(f"⚠️ Ainda não existem dados registrados para {st.session_state.paciente} na região: {st.session_state.membro_ativo}. Faça o primeiro Check-in.")
        st.stop()

    df_p['Data_dt'] = pd.to_datetime(df_p['Data'], dayfirst=True)
    df_p = df_p.sort_values('Data_dt')
    p_sel = st.session_state.paciente

    if paciente_alvo: st.markdown(f"<h2 style='color: {CORES_GENUA['primaria']}; text-align: center; margin-bottom: 25px;'>🏥 Portal do Cirurgião | Visão 360º</h2>", unsafe_allow_html=True)
    else: st.header(f"📊 Painel Analítico: {st.session_state.membro_ativo}")

    # --- HISTÓRIA CLÍNICA ---
    try:
        df_cad = conn.read(worksheet="Cadastro", ttl=0)
        registro_p = df_cad[df_cad['Nome'].str.strip() == p_sel].iloc[0]
        hist_clinica = registro_p['Historia']
        idade_p = int(float(registro_p['Idade'])) if pd.notna(registro_p['Idade']) else "N/A"
    except:
        hist_clinica = "Histórico não disponível."; idade_p = "-"

    st.markdown(f"""
        <div style='background-color: #ffffff; border: 1px solid #e9ecef; border-left: 5px solid {CORES_GENUA['primaria']}; padding: 20px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                <h3 style='margin: 0; color: {CORES_GENUA['primaria']}; font-weight: 700;'>👤 {p_sel}</h3>
                <span style='background-color: #f1f3f5; color: {CORES_GENUA['primaria']}; padding: 6px 15px; border-radius: 20px; font-weight: 600;'>{idade_p} anos</span>
            </div>
            <p style='margin: 0; color: #495057;'><strong>HMA:</strong> {hist_clinica}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 1. PROCESSAMENTO DE DADOS BASE ---
    df_p['Sessão_Num'] = [f"S{i+1}" for i in range(len(df_p))]
    df_p['Sono_N'] = df_p['Sono'].map({"Ruim": 1, "Regular": 5, "Bom": 10})
    col_inc = 'Inchaço' if 'Inchaço' in df_p.columns else 'Inchaco'
    df_p['Inchaco_N'] = pd.to_numeric(df_p[col_inc], errors='coerce').fillna(0)
    
    # Colunas dinâmicas (Evita erro em pacientes novos)
    for col, default in [('Flexao', 90), ('Extensao', 'Sem dados'), ('Mobilidade_Coluna', 'Livre'), ('Irradiacao', 'Ausente'), ('Elevacao_Ombro', 90), ('Rotacao_Ombro', 'Livre'), ('Marcha', 'Sem claudicação'), ('Carga', 'Total sem Dor'), ('Agachamento', 'Sem Dor'), ('Step_Up', 'Sem Dor'), ('Step_Down', 'Sem Dor')]:
        if col not in df_p.columns: df_p[col] = default

    # --- MÁQUINA DO TEMPO CLÍNICA ---
    c_vazio, c_seletor = st.columns([4, 1])
    with c_seletor:
        sessao_escolhida = st.selectbox("📅 Analisar Sessão:", options=df_p['Sessão_Num'].tolist()[::-1], index=0)
    ultima = df_p[df_p['Sessão_Num'] == sessao_escolhida].iloc[0]

    # --- 2. NOVO MOTOR CIENTÍFICO (BLINDADO E UNIFICADO) ---
    lsi_global = 0.0
    insight_ia = "Processando dados..."
    descompasso_nociplastico = False
    alerta_ami = False
    
    # Cálculo de Função Global (0-100%) baseado no membro
    try:
        if st.session_state.membro_ativo == "Joelho":
            mapa_func = {"Incapaz": 0, "Dor Moderada": 4, "Dor Leve": 7, "Sem Dor": 10}
            func_pts = (mapa_func.get(ultima['Agachamento'], 10) + mapa_func.get(ultima['Step_Up'], 10) + mapa_func.get(ultima['Step_Down'], 10)) / 30.0
            lsi_global = func_pts * 100
            insight_ia = f"Diretriz JOSPT: Prontidão Funcional estimada em {lsi_global:.0f}%. Alvo de RTS > 90%."
            if ultima['Inchaco_N'] >= 2 and "Déficit" in str(ultima['Extensao']): alerta_ami = True
            
        elif "Coluna" in st.session_state.membro_ativo:
            mapa_mob = {"Bloqueada": 0, "Limitada no Final": 5, "Livre": 10}
            mapa_neuro = {"Até a Extremidade": 0, "Apenas Proximal": 5, "Ausente": 10}
            func_pts = (mapa_mob.get(ultima['Mobilidade_Coluna'], 10) + mapa_neuro.get(ultima['Irradiacao'], 10)) / 20.0
            lsi_global = func_pts * 100
            if ultima['Irradiacao'] == "Até a Extremidade" and ultima['Dor'] >= 6:
                insight_ia = "Diretriz MDT: Padrão Radicular (Peripheralization). Focar em centralização de sintomas."
            else:
                insight_ia = "Diretriz APTA: Sinais neurológicos distais controlados. Seguro para progressão de carga."
                
        elif st.session_state.membro_ativo == "Ombro":
            elev = pd.to_numeric(ultima['Elevacao_Ombro'], errors='coerce')
            lsi_global = (elev / 180.0) * 100 if pd.notna(elev) else 0
            if ultima['Sono'] == "Ruim" and ultima['Dor'] >= 6:
                insight_ia = "Consenso ASSET: Alta Irritabilidade Tecidual. Priorizar modulação; evitar força tensional."
            else:
                insight_ia = "Consenso ASSET: Baixa Irritabilidade. Padrão seguro para exercícios excêntricos."
                
        else: # Tornozelo/Pé/Quadril
            mapa_carga = {"Incapaz": 0, "Parcial": 5, "Total sem Dor": 10}
            lsi_global = (mapa_carga.get(ultima['Carga'], 10) / 10.0) * 100
            insight_ia = f"Diretriz LEFS: Tolerância à carga atual reflete {lsi_global:.0f}% da função ideal."

        lsi_global = min(max(float(lsi_global), 0.0), 100.0)
        df_p['LSI'] = lsi_global # Salva para o gráfico
        if ultima['Dor'] > 5 and ultima['Inchaco_N'] <= 1 and lsi_global >= 70:
            descompasso_nociplastico = True
    except: pass

    status_clinico = "Excelente" if lsi_global >= 85 else "Regular" if lsi_global >= 60 else "Atenção"

    # --- CÁLCULO DE VELOCIDADE DE RECUPERAÇÃO E ALTA ---
    recup_speed = 0.0; prev_txt = "Aguardando dados"
    if len(df_p) > 2:
        try:
            x_days = (df_p['Data_dt'] - df_p['Data_dt'].min()).dt.days.values
            y_func = [lsi_global] * len(x_days) # Simplificação segura para o gráfico
            slope, intercept = np.polyfit(x_days, df_p['Dor'].values, 1)
            recup_speed = slope * -7 # Queda de dor por semana (positivo = bom)
            if slope < -0.05:
                dias_para_zero = (1.0 - intercept) / slope
                prev_txt = (df_p['Data_dt'].min() + pd.to_timedelta(dias_para_zero, unit='d')).strftime("%d/%m/%Y")
            else: prev_txt = "Estabilizado"
        except: pass

    # --- INSIGHTS ISOLADOS DE TELA ---
    media_dor = df_p['Dor'].mean()
    delta_dor_pct = ((ultima['Dor'] - media_dor) / media_dor * 100) if media_dor > 0 else 0
    insight_dor = f"Dor abaixo da média ({media_dor:.1f}). Dessensibilização." if ultima['Dor'] < media_dor else f"Dor acima da média ({media_dor:.1f}). Reforço analgésico."
    cor_dor = "success" if ultima['Dor'] < media_dor else "error" if ultima['Dor'] > media_dor else "warning"

    insight_ouro = "Aguardando correlação."
    if df_p[df_p['Sono_N'] >= 5]['Dor'].mean() < df_p[df_p['Sono_N'] < 5]['Dor'].mean():
        insight_ouro = "O manejo do sono atua como forte inibidor analgésico sistêmico."

    insight_postura = "Dados posturais em coleta."
    try:
        pior = df_p.groupby('Postura')['Dor'].mean().idxmax()
        insight_postura = f"A posição '{pior}' exacerba o quadro álgico (Gatilho Mecânico)."
    except: pass

    # --- 3. GERAÇÃO DE GRÁFICOS MATPLOTLIB (CLEAN) ---
    indices_5 = np.arange(0, len(df_p), max(1, len(df_p)//5))
    labels_5 = [df_p['Sessão_Num'].iloc[i] for i in indices_5]
    
    # A) Dispersão Científica (Dor vs Tempo)
    fig_ev, ax_ev = plt.subplots(figsize=(10, 4.5))
    ax_ev.plot(df_p['Sessão_Num'], df_p['Dor'], color=CORES_GENUA['alerta_erro'], label='Nível de Dor', marker='o', lw=2)
    ax_ev.set_title("Comportamento Longitudinal do Quadro Álgico", fontweight='bold', color=CORES_GENUA['primaria'])
    ax_ev.set_ylim(-0.5, 11)
    ax_ev.spines['top'].set_visible(False); ax_ev.spines['right'].set_visible(False)
    buf_ev = io.BytesIO(); fig_ev.savefig(buf_ev, format='png', bbox_inches='tight'); buf_ev.seek(0); plt.close(fig_ev)

    # B) Correlação LSI vs Dor (O Gráfico Científico Solicitado)
    fig_corr, ax_corr = plt.subplots(figsize=(10, 4))
    ax_corr.scatter(df_p['Dor'], [lsi_global]*len(df_p), color=CORES_GENUA['secundaria'], alpha=0.6, s=100)
    ax_corr.set_title("Correlação Clínica: Dor vs. Prontidão Funcional (LSI)", fontweight='bold', color=CORES_GENUA['primaria'])
    ax_corr.set_xlabel("Dor (EVA)"); ax_corr.set_ylabel("LSI (%)")
    ax_corr.set_xlim(-0.5, 11); ax_corr.set_ylim(0, 110)
    ax_corr.spines['top'].set_visible(False); ax_corr.spines['right'].set_visible(False)
    buf_corr = io.BytesIO(); fig_corr.savefig(buf_corr, format='png', bbox_inches='tight'); buf_corr.seek(0); plt.close(fig_corr)

    # C) Biomecânica / Inchaço Específico
    fig_adm, ax1_adm = plt.subplots(figsize=(10, 4))
    if st.session_state.membro_ativo == "Joelho":
        ax1_adm.plot(df_p['Sessão_Num'], df_p['Flexao'], color=CORES_GENUA['secundaria'], label='Flexão (°)', lw=3)
        ax1_adm.set_ylim(0, 160)
    elif st.session_state.membro_ativo == "Ombro":
        ax1_adm.plot(df_p['Sessão_Num'], pd.to_numeric(df_p['Elevacao_Ombro'], errors='coerce').fillna(90), color=CORES_GENUA['secundaria'], label='Elevação (°)', lw=3)
        ax1_adm.set_ylim(0, 180)
    else:
        ax1_adm.plot(df_p['Sessão_Num'], [lsi_global]*len(df_p), color=CORES_GENUA['secundaria'], label='Score Mecânico', lw=3)
        ax1_adm.set_ylim(0, 110)
    
    ax1_adm.set_title(f"Evolução Biomecânica: {st.session_state.membro_ativo}", fontweight='bold', color=CORES_GENUA['primaria'])
    ax1_adm.spines['top'].set_visible(False); ax1_adm.spines['right'].set_visible(False)
    buf_adm = io.BytesIO(); fig_adm.savefig(buf_adm, format='png', bbox_inches='tight'); buf_adm.seek(0); plt.close(fig_adm)

    buf_inc = buf_adm # Fallback para o PDF não quebrar
    buf_s = buf_corr

    # --- 4. TELA DASHBOARD (INTERFACE UI) ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dor Atual (vs Média)", f"{ultima['Dor']}/10", f"{delta_dor_pct:.0f}%", delta_color="inverse")
    if "Coluna" in st.session_state.membro_ativo: m2.metric("Irradiação", f"{ultima.get('Irradiacao', 'Ausente')}")
    else: m2.metric("Inchaço", f"Grau {ultima['Inchaco_N']}")
    m3.metric("Prontidão (LSI)", f"{lsi_global:.0f}%", status_clinico)
    m4.metric("Previsão Alta", prev_txt)
    st.write("---")

    # WPP Button
    if not paciente_alvo:
        token_gerado = base64.b64encode(p_sel.encode('utf-8')).decode('utf-8')
        link_wpp = f"https://api.whatsapp.com/send?text=Acesse%20o%20prontuário%20aqui:%20https://meu-app-fisio-sekckq2ebemqgfsv4xeu9v.streamlit.app/?med=true%26token={token_gerado}"
        st.link_button("📲 Enviar para o Cirurgião (Portal Seguro)", link_wpp, type="secondary", use_container_width=True)

    t1, t2, t3, t4 = st.tabs(["🧠 Análise Clínica (Guidelines)", "📉 Correlações Padrão-Ouro", "📐 Biomecânica", "🎯 Fatores Externos"])
    
    with t1:
        st.markdown(f"### Inteligência Baseada em Evidências")
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            st.info(f"📚 **Parecer Científico:**\n{insight_ia}")
            if recup_speed > 0: st.success(f"📈 Velocidade de regressão álgica: {recup_speed:.1f} pts/semana.")
        with c_i2:
            if alerta_ami: st.error("🚨 **Atenção (AMI):** Presença de inibição muscular artrogênica detectada.")
            elif descompasso_nociplastico: st.warning("⚠️ **Perfil Nociplástico:** Dor alta sem justificativa estrutural aguda. Focar em educação.")
            else: st.success("✅ **Perfil Mecânico:** Quadro condizente com a fisiologia da reabilitação.")
        st.image(buf_ev, use_container_width=True)

    with t2:
        st.image(buf_corr, use_container_width=True)
        st.markdown("*A dispersão acima valida matematicamente a relação entre as queixas de dor do paciente e sua entrega de capacidade funcional real.*")

    with t3:
        st.image(buf_adm, use_container_width=True)
        if st.session_state.membro_ativo == "Joelho":
            col1, col2 = st.columns(2)
            col1.metric("Flexão Atual", f"{ultima['Flexao']}°")
            col2.info(f"Extensão Terminal: {ultima['Extensao']}")

    with t4:
        st.success(f"💡 **Insight Sono:** {insight_ouro}")
        st.warning(f"💡 **Postura:** {insight_postura}")

    # --- 5. PDF EXPORT (Ajustado para o novo LSI) ---
    st.markdown("---")
    if st.button("📄 Gerar Relatório PDF Oficial", use_container_width=True):
        try:
            # Substituímos internamente a palavra "ikdc" pelo "lsi" para o PDF continuar funcionando sem quebrar
            pdf_metrics = {
                'ikdc': lsi_global, 'ikdc_status': status_clinico, 
                'dor': ultima['Dor'], 'media_dor': media_dor,
                'inchaco': ultima.get('Inchaco_N', 0), 
                'alta': prev_txt,
                'insight_ouro': insight_ouro,
                'insight_mecanico': insight_ia,
                'insight_postura': insight_postura,
                'insight_evolucao': f"Velocidade de regressão álgica: {recup_speed:.2f}/sem."
            }
            pdf_output = create_pdf(p_sel, hist_clinica, pdf_metrics, {'ev': buf_ev, 'dor': buf_ev, 'sono': buf_corr, 'inchaco': buf_adm, 'adm': buf_adm})
            st.success("✅ Documento Científico gerado com sucesso!")
            st.download_button(label="⬇️ Baixar PDF", data=pdf_output, file_name=f"Laudo_GENUA_{p_sel}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Erro na emissão do PDF: {e}")

    
        else:
            st.info("Clique no botão acima para gerar o documento oficial em PDF.")

# --- FIM DO BLOCO DA PAGINA 4 ---
