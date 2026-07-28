"""GENUA | Configuração visual: cores, logo, CSS e helper de UI."""
import streamlit as st

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
st.sidebar.image(NOVO_LOGO_GENUA, width='stretch')
st.sidebar.markdown("---") # Cria uma linha divisória elegante abaixo do logo

# --- Helper de UI: título de seção padrão (reduz repetição de markdown) ---
def titulo(texto):
    st.markdown(f"<h4 style='color: {CORES_GENUA['primaria']};'>{texto}</h4>", unsafe_allow_html=True)
