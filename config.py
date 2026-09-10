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
    /* ============================================================ */
    /* GENUA DESIGN SYSTEM  -  Linguagem visual iOS / Apple          */
    /* ============================================================ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {{
        --genua-primaria: {CORES_GENUA['primaria']};
        --genua-secundaria: {CORES_GENUA['secundaria']};
        --genua-fundo: {CORES_GENUA['fundo_claro']};
        --raio-card: 22px;
        --raio-input: 14px;
        --raio-btn: 16px;
        --sombra-suave: 0 1px 2px rgba(16,62,85,.04), 0 4px 16px rgba(16,62,85,.06);
        --sombra-media: 0 4px 12px rgba(16,62,85,.08), 0 12px 32px rgba(16,62,85,.10);
        --transicao: all .25s cubic-bezier(.4,0,.2,1);
    }}

    /* ===== BASE ===== */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif !important;
        -webkit-text-size-adjust: 100%;
        -webkit-font-smoothing: antialiased;
        letter-spacing: -0.01em;
    }}

    .stApp {{
        background:
            radial-gradient(1200px 600px at 100% -10%, rgba(57,142,155,.06), transparent 60%),
            radial-gradient(1000px 500px at -10% 10%, rgba(16,62,85,.05), transparent 55%),
            linear-gradient(180deg, #FBFCFD 0%, #F4F7F9 100%);
        color: {CORES_GENUA['texto_escuro']};
    }}

    /* Tipografia fluida com pesos iOS */
    h1 {{ font-size: clamp(1.6rem, 4vw, 2.4rem) !important; font-weight: 800 !important; letter-spacing:-.03em !important; }}
    h2 {{ font-size: clamp(1.3rem, 3.2vw, 1.9rem) !important; font-weight: 700 !important; letter-spacing:-.02em !important; }}
    h3 {{ font-size: clamp(1.15rem, 2.6vw, 1.5rem) !important; font-weight: 700 !important; letter-spacing:-.02em !important; }}
    h4 {{ font-size: clamp(1rem, 2.2vw, 1.2rem) !important; font-weight: 600 !important; }}
    body, p, label, .stMarkdown {{ font-size: clamp(.92rem, 1.6vw, 1rem) !important; line-height: 1.6 !important; }}
    h1, h2, h3, h4 {{ color: {CORES_GENUA['primaria']} !important; }}

    /* Esconde chrome do Streamlit */
    #MainMenu, footer, .stDeployButton, .stStatusWidget {{ display: none !important; }}
    header {{ background: transparent !important; }}

    [data-testid="block-container"] {{
        padding-top: clamp(1rem, 3vw, 2.5rem) !important;
        padding-bottom: clamp(2rem, 4vw, 3rem) !important;
        padding-left: clamp(1rem, 5vw, 4%) !important;
        padding-right: clamp(1rem, 5vw, 4%) !important;
        max-width: 1180px !important;
    }}

    /* ===== INPUTS (estilo iOS: pill suave, foco com halo) ===== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox [data-baseweb="select"] > div {{
        border-radius: var(--raio-input) !important;
        border: 1px solid rgba(16,62,85,.10) !important;
        background: rgba(255,255,255,.85) !important;
        backdrop-filter: blur(8px) !important;
        box-shadow: var(--sombra-suave) !important;
        padding: 12px 16px !important;
        min-height: 50px !important;
        font-size: 16px !important;
        transition: var(--transicao) !important;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: {CORES_GENUA['secundaria']} !important;
        box-shadow: 0 0 0 4px rgba(57,142,155,.15) !important;
        background: #fff !important;
    }}

    /* ===== SLIDERS (trilha teal, thumb grande) ===== */
    .stSlider [data-baseweb="slider"] {{ padding: 12px 0 !important; }}
    .stSlider [role="slider"] {{
        height: 30px !important; width: 30px !important;
        box-shadow: 0 2px 8px rgba(16,62,85,.25) !important;
        border: 3px solid #fff !important;
    }}
    .stSlider [data-baseweb="slider"] > div > div {{
        background: linear-gradient(90deg, {CORES_GENUA['secundaria']}, {CORES_GENUA['primaria']}) !important;
    }}

    /* ===== RADIO / CHECKBOX (touch-friendly) ===== */
    .stRadio > div {{ gap: 10px !important; }}
    .stRadio label, .stCheckbox label {{
        padding: 10px 6px !important; min-height: 46px !important;
        display: flex !important; align-items: center !important;
        border-radius: 12px !important; transition: var(--transicao) !important;
    }}
    .stRadio label:hover {{ background: rgba(57,142,155,.06) !important; }}

    /* ===== BOTÕES (iOS: pill, gradiente, elevação no hover) ===== */
    .stButton > button {{
        background: linear-gradient(135deg, {CORES_GENUA['primaria']} 0%, #16506E 100%) !important;
        color: #fff !important;
        border-radius: var(--raio-btn) !important;
        border: none !important;
        padding: 15px 26px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        letter-spacing: -.01em !important;
        width: 100% !important;
        min-height: 52px !important;
        box-shadow: 0 4px 14px rgba(16,62,85,.22) !important;
        transition: var(--transicao) !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) scale(1.005) !important;
        box-shadow: 0 8px 22px rgba(16,62,85,.30) !important;
        filter: brightness(1.05) !important;
    }}
    .stButton > button:active {{ transform: translateY(0) scale(.99) !important; }}

    .stButton > button[kind="secondary"] {{
        background: rgba(255,255,255,.7) !important;
        color: {CORES_GENUA['primaria']} !important;
        border: 1px solid rgba(16,62,85,.12) !important;
        box-shadow: var(--sombra-suave) !important;
        backdrop-filter: blur(8px) !important;
        min-height: 44px !important;
        width: auto !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background: #fff !important;
        transform: translateX(-3px) !important;
    }}
    /* Download button = verde de sucesso */
    .stDownloadButton > button {{
        background: linear-gradient(135deg, {CORES_GENUA['secundaria']} 0%, #2E7D8A 100%) !important;
        color:#fff !important; border:none !important;
        border-radius: var(--raio-btn) !important; min-height:52px !important;
        font-weight:600 !important; box-shadow:0 4px 14px rgba(57,142,155,.28) !important;
        transition: var(--transicao) !important;
    }}
    .stDownloadButton > button:hover {{ transform: translateY(-2px) !important; filter:brightness(1.05) !important; }}

    /* ===== CARDS / MÉTRICAS (cantos suaves, glass, elevação) ===== */
    [data-testid="stMetric"] {{
        background: rgba(255,255,255,.75) !important;
        backdrop-filter: blur(12px) !important;
        border-radius: var(--raio-card) !important;
        padding: 20px 22px !important;
        box-shadow: var(--sombra-media) !important;
        border: 1px solid rgba(255,255,255,.6) !important;
        transition: var(--transicao) !important;
    }}
    [data-testid="stMetric"]:hover {{ transform: translateY(-3px) !important; box-shadow: 0 12px 40px rgba(16,62,85,.14) !important; }}
    [data-testid="stMetricValue"] {{ font-weight: 800 !important; letter-spacing:-.03em !important; color: {CORES_GENUA['primaria']} !important; }}
    [data-testid="stMetricLabel"] {{ font-weight: 500 !important; color: {CORES_GENUA['texto_suave']} !important; }}

    /* ===== TABS (segmented control iOS) ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px; background: rgba(16,62,85,.05); padding: 6px;
        border-radius: 16px !important; border: none !important; flex-wrap: wrap !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 12px !important; padding: 9px 18px !important;
        background: transparent !important; color: {CORES_GENUA['texto_suave']} !important;
        font-weight: 600 !important; min-height: 42px !important; white-space: nowrap;
        transition: var(--transicao) !important; border: none !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: #fff !important; color: {CORES_GENUA['primaria']} !important;
        box-shadow: 0 2px 8px rgba(16,62,85,.12) !important;
    }}

    /* ===== EXPANDERS (card suave) ===== */
    .stExpander, [data-testid="stExpander"] {{
        border-radius: var(--raio-card) !important;
        border: 1px solid rgba(16,62,85,.08) !important;
        background: rgba(255,255,255,.7) !important;
        backdrop-filter: blur(8px) !important;
        box-shadow: var(--sombra-suave) !important;
        overflow: hidden !important;
    }}
    .streamlit-expanderHeader {{ font-weight: 600 !important; padding: 16px 20px !important; }}

    /* ===== ALERTAS (cantos suaves) ===== */
    .stAlert {{ border-radius: 16px !important; padding: 16px 20px !important; border: none !important; box-shadow: var(--sombra-suave) !important; }}

    /* ===== TOAST GENUA ===== */
    .genua-toast {{
        padding: 16px 22px; border-radius: 16px; font-weight: 600; margin: 14px 0;
        display: flex; align-items: center; gap: 14px; box-shadow: var(--sombra-media);
        animation: toastIn .4s cubic-bezier(.4,0,.2,1);
    }}
    @keyframes toastIn {{ from {{ opacity:0; transform: translateY(-8px); }} to {{ opacity:1; transform: translateY(0); }} }}
    .genua-toast.success {{ background: linear-gradient(135deg,#E8F8EF,#F0FBF4); color:#136B36; }}
    .genua-toast.warning {{ background: linear-gradient(135deg,#FFF7E6,#FFFBF0); color:#8A6300; }}
    .genua-toast.error   {{ background: linear-gradient(135deg,#FDECEA,#FEF4F3); color:#8A1F1F; }}
    .genua-toast.info    {{ background: linear-gradient(135deg,#E9F4FB,#F2F9FD); color:#0B3B66; }}

    /* ===== SIDEBAR (glass claro) ===== */
    [data-testid="stSidebar"] {{
        background: rgba(255,255,255,.82) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(16,62,85,.06) !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{ min-height: 46px !important; }}

    /* Divisores mais leves */
    hr {{ border-color: rgba(16,62,85,.08) !important; }}

    /* ===== MOBILE ===== */
    @media (max-width: 768px) {{
        [data-testid="block-container"] {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
        [data-testid="column"] {{ min-width: 100% !important; flex: 1 1 100% !important; }}
        .stTabs [data-baseweb="tab-list"] {{ overflow-x: auto !important; flex-wrap: nowrap !important; -webkit-overflow-scrolling: touch; }}
        [data-testid="stSidebar"] {{ width: 86vw !important; }}
        .stButton > button {{ min-height: 54px !important; }}
    }}
    @media (min-width: 769px) and (max-width: 1024px) {{
        [data-testid="block-container"] {{ padding-left: 3% !important; padding-right: 3% !important; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{ animation-duration:.01ms !important; transition-duration:.01ms !important; }}
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
