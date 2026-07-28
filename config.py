"""GENUA | Configuração visual: cores, logo, CSS responsivo e helpers de UI."""
import streamlit as st


# ============================================================
# 1. CORES DA MARCA
# ============================================================
CORES_GENUA = {
    'primaria': '#103E55',       # Azul-Petróleo Escuro
    'secundaria': '#398E9B',     # Verde-Água/Teal Claro
    'fundo_claro': '#F4F7F9',    # Cinza Gelo levemente azulado
    'texto_escuro': '#1A252C',   # Cinza-chumbo profundo
    'texto_suave': '#6c757d',    # Cinza médio para legendas
    'alerta_sucesso': '#28a745', # Verde positivo
    'alerta_aviso': '#ffc107',   # Amarelo atenção
    'alerta_erro': '#dc3545',    # Vermelho alerta
}

# ============================================================
# 2. LOGO
# ============================================================
NOVO_LOGO_GENUA = "logo_genua_novo_v2.png"

# ============================================================
# 3. CONFIGURAÇÃO DE PÁGINA (deve ser o 1º comando Streamlit)
# ============================================================
st.set_page_config(
    page_title="GENUA | Inteligência Clínica",
    page_icon=NOVO_LOGO_GENUA,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 4. CSS UNIFICADO E RESPONSIVO (Mobile / Tablet / Desktop)
# ============================================================
st.markdown(f"""
    <style>
    /* Viewport para mobile (Streamlit não inclui por padrão) */
    @viewport {{ width: device-width; initial-scale: 1; }}

    /* ===== TIPOGRAFIA ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif !important;
        -webkit-text-size-adjust: 100%;  /* impede zoom acidental em iOS */
    }}

    /* Fontes fluidas: encolhem em mobile, crescem em desktop */
    h1 {{ font-size: clamp(1.5rem, 4vw, 2.25rem) !important; }}
    h2 {{ font-size: clamp(1.3rem, 3.2vw, 1.875rem) !important; }}
    h3 {{ font-size: clamp(1.15rem, 2.6vw, 1.5rem) !important; }}
    h4 {{ font-size: clamp(1rem, 2.2vw, 1.25rem) !important; }}
    body, p, label, .stMarkdown {{
        font-size: clamp(0.9rem, 1.6vw, 1rem) !important;
        line-height: 1.55 !important;
    }}

    /* ===== REMOÇÃO DE BRANDING STREAMLIT ===== */
    #MainMenu, footer, .stDeployButton, .stStatusWidget {{ display: none !important; }}
    header {{ background-color: transparent !important; }}

    /* ===== CONTAINER PRINCIPAL ===== */
    .stApp {{
        background: linear-gradient(180deg, {CORES_GENUA['fundo_claro']} 0%, #FFFFFF 100%);
        color: {CORES_GENUA['texto_escuro']};
    }}
    [data-testid="block-container"] {{
        padding-top: clamp(1rem, 3vw, 3.5rem) !important;
        padding-bottom: clamp(1rem, 3vw, 3rem) !important;
        padding-left: clamp(0.75rem, 5vw, 5%) !important;
        padding-right: clamp(0.75rem, 5vw, 5%) !important;
        max-width: 1200px !important;
    }}

    h1, h2, h3, h4 {{ color: {CORES_GENUA['primaria']} !important; }}

    /* ===== INPUTS (com touch target ≥ 48px) ===== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    .stSelectbox [data-baseweb="select"],
    .stDateInput > div > div > input {{
        border-radius: 12px !important;
        border: 1px solid #E2E8F0 !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
        padding: 10px 14px !important;
        line-height: 1.5 !important;
        min-height: 48px !important;
        font-size: 16px !important;  /* iOS não dá zoom se >= 16px */
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: {CORES_GENUA['secundaria']} !important;
        box-shadow: 0 0 0 3px rgba(57, 142, 155, 0.15) !important;
    }}

    /* ===== SLIDERS (EVA, ADM — fundamentais no app) ===== */
    .stSlider [data-baseweb="slider"] {{
        padding: 10px 0 !important;
    }}
    .stSlider [role="slider"] {{
        height: 28px !important;
        width: 28px !important;  /* touch target maior pra dedo */
    }}

    /* ===== RADIO E CHECKBOX ===== */
    .stRadio > div {{ gap: 8px !important; }}
    .stRadio label, .stCheckbox label {{
        padding: 8px 4px !important;
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
    }}

    /* ===== BOTÕES PRIMÁRIOS ===== */
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
        font-size: 16px !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px rgba(16, 62, 85, 0.3) !important;
    }}
    .stButton > button:active {{
        transform: translateY(0) !important;
        box-shadow: 0 2px 6px rgba(16, 62, 85, 0.2) !important;
    }}

    /* Botão Voltar / Secundário */
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
        transform: translateX(-4px) !important;
    }}

    /* ===== CARDS (st.metric) ===== */
    [data-testid="metric-container"] {{
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: clamp(14px, 2vw, 24px) clamp(12px, 1.8vw, 20px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.05);
        border: 1px solid #F0F4F8;
        border-left: 6px solid {CORES_GENUA['secundaria']};
        margin-bottom: 10px;
    }}

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: none !important;
        flex-wrap: wrap !important;  /* essencial em mobile */
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 30px !important;
        padding: 10px 18px !important;
        background-color: #F4F7F9 !important;
        color: #6C757D !important;
        font-weight: 600 !important;
        min-height: 44px !important;
        white-space: nowrap;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {CORES_GENUA['primaria']} !important;
        color: white !important;
    }}

    /* ===== EXPANDERS ===== */
    .streamlit-expanderHeader {{
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #F0F4F8 !important;
        padding: 14px 18px !important;
        font-weight: 600 !important;
    }}

    /* ===== ALERTAS (success/info/warning/error) ===== */
    .stAlert {{
        border-radius: 12px !important;
        padding: 14px 18px !important;
        border-left-width: 6px !important;
    }}

    /* ===== TOAST CUSTOMIZADO ===== */
    .genua-toast {{
        padding: 14px 20px;
        border-radius: 12px;
        font-weight: 600;
        margin: 12px 0;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }}
    .genua-toast.success {{ background: #E8F5E9; color: #1B5E20; border-left: 5px solid {CORES_GENUA['alerta_sucesso']}; }}
    .genua-toast.warning {{ background: #FFF8E1; color: #7A5A00; border-left: 5px solid {CORES_GENUA['alerta_aviso']}; }}
    .genua-toast.error   {{ background: #FDECEA; color: #7A1F1F; border-left: 5px solid {CORES_GENUA['alerta_erro']}; }}
    .genua-toast.info    {{ background: #E3F2FD; color: #0B3B66; border-left: 5px solid {CORES_GENUA['secundaria']}; }}

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {{
        background-color: #FFFFFF !important;
        border-right: 1px solid #F0F4F8 !important;
    }}

    /* =================================================== */
    /* ===== BREAKPOINT MOBILE (≤ 768px) ===== */
    /* =================================================== */
    @media (max-width: 768px) {{
        [data-testid="block-container"] {{
            padding-top: 1rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }}

        /* st.columns vira coluna única em mobile */
        [data-testid="column"] {{
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }}

        /* Tabs com scroll horizontal em vez de quebrar */
        .stTabs [data-baseweb="tab-list"] {{
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch;
        }}

        /* Sidebar ocupa tela cheia quando aberta */
        [data-testid="stSidebar"] {{ width: 85vw !important; }}

        /* Botões maiores em mobile (mais fáceis de tocar) */
        .stButton > button {{ min-height: 54px !important; }}

        /* Cards menos altos em mobile */
        [data-testid="metric-container"] {{ padding: 14px 12px !important; }}
    }}

    /* =================================================== */
    /* ===== BREAKPOINT TABLET (769–1024px) ===== */
    /* =================================================== */
    @media (min-width: 769px) and (max-width: 1024px) {{
        [data-testid="block-container"] {{
            padding-left: 3% !important;
            padding-right: 3% !important;
        }}
    }}

    /* Prefers reduced motion (acessibilidade) */
    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            animation-duration: 0.01ms !important;
            transition-duration: 0.01ms !important;
        }}
    }}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 5. LOGO NA SIDEBAR
# ============================================================
st.sidebar.image(NOVO_LOGO_GENUA, width='stretch')
st.sidebar.markdown("---")


# ============================================================
# 6. HELPERS DE UI
# ============================================================
def titulo(texto: str):
    """Renderiza um título de seção padronizado (azul Genua)."""
    st.markdown(
        f"<h4 style='color: {CORES_GENUA['primaria']};'>{texto}</h4>",
        unsafe_allow_html=True,
    )


def toast(mensagem: str, tipo: str = "info"):
    """Toast visual (success/warning/error/info). Mais bonito que st.success."""
    icones = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
    icone = icones.get(tipo, "ℹ️")
    st.markdown(
        f"<div class='genua-toast {tipo}'>{icone}<span>{mensagem}</span></div>",
        unsafe_allow_html=True,
    )


def secao(titulo_texto: str, descricao: str = None):
    """Bloco de seção com título + subtítulo opcional, espaçamento padrão."""
    titulo(titulo_texto)
    if descricao:
        st.markdown(
            f"<p style='color: {CORES_GENUA['texto_suave']}; "
            f"margin-top: -8px; margin-bottom: 16px;'>{descricao}</p>",
            unsafe_allow_html=True,
        )
