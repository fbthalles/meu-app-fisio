"""GENUA | Configuração visual: cores, logo, CSS responsivo (Apple HIG) e helpers de UI."""
import streamlit as st


# ============================================================
# 1. CORES DA MARCA (Padrão Apple Clinical HIG + Identidade GENUA)
# ============================================================
CORES_GENUA = {
    'primaria': '#103E55',       # Azul-Petróleo Profundo (Identidade GENUA)
    'secundaria': '#2E8B9A',     # Teal Clínico Vibrante (Destaques e Foco)
    'accent_ios': '#0071E3',     # Azul Interativo Apple (Links e Micro-interações)
    'fundo_claro': '#F5F5F7',    # Apple System Gray 6 (Fundo acetinado)
    'card_bg': '#FFFFFF',        # Superfície elevada pura
    'texto_escuro': '#1D1D1F',   # Apple SF Charcoal (Leitura de alto contraste)
    'texto_suave': '#86868B',    # Apple SF Secondary Label (Legendas e subtítulos)
    'alerta_sucesso': '#34C759', # Apple System Green
    'alerta_aviso': '#FF9F0A',   # Apple System Orange/Amber
    'alerta_erro': '#FF3B30',    # Apple System Red
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
# 4. CSS UNIFICADO E RESPONSIVO (Apple iOS / iPadOS / macOS Design System)
# ============================================================
st.markdown(f"""
    <style>
    /* ============================================================ */
    /* GENUA DESIGN SYSTEM 2.0 — Apple Human Interface Guidelines   */
    /* ============================================================ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {{
        --genua-primaria: {CORES_GENUA['primaria']};
        --genua-secundaria: {CORES_GENUA['secundaria']};
        --genua-fundo: {CORES_GENUA['fundo_claro']};
        --genua-texto: {CORES_GENUA['texto_escuro']};
        --genua-suave: {CORES_GENUA['texto_suave']};
        --raio-card: 22px;
        --raio-input: 12px;
        --raio-btn: 980px; /* Formato pílula Apple */
        --sombra-card: 0 2px 8px rgba(0, 0, 0, 0.03), 0 12px 32px rgba(16, 62, 85, 0.05);
        --sombra-hover: 0 6px 16px rgba(0, 0, 0, 0.06), 0 18px 40px rgba(16, 62, 85, 0.09);
        --sombra-input: 0 1px 2px rgba(0, 0, 0, 0.03);
        --transicao: all 0.25s cubic-bezier(0.25, 0.1, 0.25, 1);
    }}

    /* ===== BASE & TIPOGRAFIA SF PRO / INTER ===== */
    html, body, [class*="css"] {{
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif !important;
        -webkit-text-size-adjust: 100%;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        letter-spacing: -0.015em;
        color: var(--genua-texto);
    }}

    .stApp {{
        background-color: var(--genua-fundo) !important;
        background-image:
            radial-gradient(900px 450px at 95% -5%, rgba(46, 139, 154, 0.06), transparent 60%),
            radial-gradient(800px 400px at 0% 5%, rgba(16, 62, 85, 0.04), transparent 55%) !important;
        color: var(--genua-texto);
    }}

    /* Hierarquia Tipográfica Apple */
    h1 {{ font-size: clamp(1.75rem, 3.5vw, 2.35rem) !important; font-weight: 800 !important; letter-spacing: -0.03em !important; color: var(--genua-texto) !important; }}
    h2 {{ font-size: clamp(1.35rem, 2.8vw, 1.8rem) !important; font-weight: 700 !important; letter-spacing: -0.025em !important; color: var(--genua-texto) !important; }}
    h3 {{ font-size: clamp(1.15rem, 2.2vw, 1.4rem) !important; font-weight: 700 !important; letter-spacing: -0.02em !important; color: var(--genua-primaria) !important; }}
    h4 {{ font-size: clamp(1.0rem, 1.8vw, 1.15rem) !important; font-weight: 600 !important; letter-spacing: -0.015em !important; color: var(--genua-primaria) !important; }}
    body, p, label, .stMarkdown {{ font-size: 0.96rem !important; line-height: 1.55 !important; }}

    /* Esconde elementos rústicos do Streamlit e aplica Glass no topo */
    #MainMenu, footer, .stDeployButton, .stStatusWidget {{ display: none !important; }}
    header[data-testid="stHeader"] {{
        background: rgba(245, 245, 247, 0.72) !important;
        backdrop-filter: saturate(180%) blur(20px) !important;
        -webkit-backdrop-filter: saturate(180%) blur(20px) !important;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05) !important;
    }}

    [data-testid="block-container"] {{
        padding-top: clamp(1.2rem, 2.5vw, 2.2rem) !important;
        padding-bottom: 3rem !important;
        padding-left: clamp(1rem, 4vw, 3.5%) !important;
        padding-right: clamp(1rem, 4vw, 3.5%) !important;
        max-width: 1200px !important;
    }}

    /* ===== CARDS FLUTUANTES APPLE (st.container(border=True)) ===== */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #FFFFFF !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
        border-radius: var(--raio-card) !important;
        padding: 24px 26px !important;
        box-shadow: var(--sombra-card) !important;
        transition: var(--transicao) !important;
        margin-bottom: 16px !important;
    }}

    /* ===== INPUTS E SELETORES (Estilo macOS Sonoma / iOS 18) ===== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div {{
        border-radius: var(--raio-input) !important;
        border: 1px solid rgba(0, 0, 0, 0.09) !important;
        background-color: #FFFFFF !important;
        box-shadow: var(--sombra-input) !important;
        padding: 10px 14px !important;
        min-height: 46px !important;
        font-size: 15px !important;
        color: var(--genua-texto) !important;
        transition: var(--transicao) !important;
    }}

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox [data-baseweb="select"] > div:focus-within,
    .stMultiSelect [data-baseweb="select"] > div:focus-within {{
        border-color: var(--genua-secundaria) !important;
        box-shadow: 0 0 0 4px rgba(46, 139, 154, 0.16) !important;
        background-color: #FFFFFF !important;
    }}

    /* Labels dos inputs mais elegantes */
    .stTextInput label, .stTextArea label, .stNumberInput label,
    .stDateInput label, .stSelectbox label, .stMultiSelect label, .stSlider label {{
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        color: #3A3A3C !important;
        margin-bottom: 4px !important;
    }}

    /* Tags do Multiselect estilo Chip iOS */
    span[data-baseweb="tag"] {{
        background: rgba(16, 62, 85, 0.08) !important;
        color: var(--genua-primaria) !important;
        border-radius: 980px !important;
        font-weight: 600 !important;
        padding: 4px 10px !important;
        border: 1px solid rgba(16, 62, 85, 0.12) !important;
    }}

    /* ===== BOTÕES (Pílula Apple + Micro-interação) ===== */
    .stButton > button {{
        background: linear-gradient(135deg, {CORES_GENUA['primaria']} 0%, #175473 100%) !important;
        color: #FFFFFF !important;
        border-radius: var(--raio-btn) !important;
        border: none !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        letter-spacing: -0.01em !important;
        min-height: 48px !important;
        box-shadow: 0 4px 14px rgba(16, 62, 85, 0.20) !important;
        transition: var(--transicao) !important;
    }}
    .stButton > button:hover {{
        transform: scale(1.012) translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(16, 62, 85, 0.28) !important;
        filter: brightness(1.06) !important;
    }}
    .stButton > button:active {{
        transform: scale(0.985) !important;
    }}

    /* Botão Secundário (Branco translúcido estilo Apple) */
    .stButton > button[kind="secondary"] {{
        background: #FFFFFF !important;
        color: var(--genua-primaria) !important;
        border: 1px solid rgba(0, 0, 0, 0.10) !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04) !important;
        min-height: 42px !important;
        padding: 8px 18px !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background: #F5F5F7 !important;
        border-color: rgba(0, 0, 0, 0.18) !important;
        transform: scale(1.01) !important;
    }}

    /* Botão de Download */
    .stDownloadButton > button {{
        background: linear-gradient(135deg, {CORES_GENUA['secundaria']} 0%, #206B78 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: var(--raio-btn) !important;
        min-height: 48px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 14px rgba(46, 139, 154, 0.25) !important;
        transition: var(--transicao) !important;
    }}

    /* ===== MÉTRICAS / KPIs (Apple Health Cards) ===== */
    [data-testid="stMetric"] {{
        background: #FFFFFF !important;
        border-radius: 20px !important;
        padding: 20px 22px !important;
        box-shadow: var(--sombra-card) !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
        transition: var(--transicao) !important;
    }}
    [data-testid="stMetric"]:hover {{
        transform: translateY(-2px) !important;
        box-shadow: var(--sombra-hover) !important;
    }}
    [data-testid="stMetricValue"] {{
        font-weight: 800 !important;
        font-size: clamp(1.5rem, 2.5vw, 2.0rem) !important;
        letter-spacing: -0.03em !important;
        color: var(--genua-primaria) !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-weight: 600 !important;
        font-size: 0.80rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        color: var(--genua-suave) !important;
    }}

    /* ===== TABS (Segmented Control Nativo iOS) ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px !important;
        background: rgba(118, 118, 128, 0.12) !important; /* Cor exata do Segmented Control iOS */
        padding: 4px !important;
        border-radius: 14px !important;
        border: none !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px !important;
        padding: 8px 18px !important;
        background: transparent !important;
        color: #3A3A3C !important;
        font-weight: 600 !important;
        font-size: 0.90rem !important;
        min-height: 38px !important;
        transition: var(--transicao) !important;
        border: none !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: #FFFFFF !important;
        color: var(--genua-primaria) !important;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12), 0 1px 1px rgba(0, 0, 0, 0.04) !important;
    }}
    /* Remove linha sublinhada padrão do Streamlit nas abas */
    .stTabs [data-baseweb="tab-highlight"] {{
        display: none !important;
    }}

    /* ===== EXPANDERS (Listas Agrupadas estilo Ajustes do iOS) ===== */
    [data-testid="stExpander"] {{
        border-radius: 18px !important;
        border: 1px solid rgba(0, 0, 0, 0.06) !important;
        background: #FFFFFF !important;
        box-shadow: var(--sombra-card) !important;
        overflow: hidden !important;
        margin-bottom: 12px !important;
    }}
    [data-testid="stExpander"] summary {{
        font-weight: 600 !important;
        padding: 14px 18px !important;
        color: var(--genua-texto) !important;
    }}

    /* ===== SIDEBAR (macOS Vibrancy / Translúcida) ===== */
    [data-testid="stSidebar"] {{
        background: rgba(255, 255, 255, 0.86) !important;
        backdrop-filter: saturate(180%) blur(25px) !important;
        -webkit-backdrop-filter: saturate(180%) blur(25px) !important;
        border-right: 1px solid rgba(0, 0, 0, 0.06) !important;
    }}

    /* Estilização do st.radio na Sidebar como Menu macOS Finder */
    [data-testid="stSidebar"] .stRadio > div {{
        gap: 6px !important;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        padding: 10px 14px !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        transition: var(--transicao) !important;
        cursor: pointer !important;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background: rgba(16, 62, 85, 0.06) !important;
    }}

    /* ===== SLIDERS E PROGRESS BAR ===== */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, {CORES_GENUA['secundaria']}, {CORES_GENUA['primaria']}) !important;
        border-radius: 980px !important;
    }}

    /* ===== ALERTAS E TOASTS ===== */
    .stAlert {{
        border-radius: 16px !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
        box-shadow: var(--sombra-card) !important;
    }}

    .genua-toast {{
        padding: 14px 20px; border-radius: 16px; font-weight: 600; margin: 12px 0;
        display: flex; align-items: center; gap: 12px; box-shadow: var(--sombra-card);
    }}
    .genua-toast.success {{ background: #E8F8EF; color: #136B36; }}
    .genua-toast.warning {{ background: #FFF7E6; color: #8A6300; }}
    .genua-toast.error   {{ background: #FDECEA; color: #8A1F1F; }}
    .genua-toast.info    {{ background: #E9F4FB; color: #0B3B66; }}

    hr {{ border-color: rgba(0, 0, 0, 0.06) !important; margin: 1.5rem 0 !important; }}

    /* ===== RESPONSIVIDADE MOBILE ===== */
    @media (max-width: 768px) {{
        [data-testid="block-container"] {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
        .stTabs [data-baseweb="tab-list"] {{ overflow-x: auto !important; flex-wrap: nowrap !important; }}
        div[data-testid="stVerticalBlockBorderWrapper"] {{ padding: 16px !important; border-radius: 18px !important; }}
    }}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 5. LOGO NA SIDEBAR (Oculta na tela de Login para não duplicar)
# ============================================================
if st.session_state.get("pagina", "login") != "login":
    try:
        st.sidebar.image(NOVO_LOGO_GENUA, width="stretch")
        st.sidebar.markdown("---")
    except Exception:
        st.sidebar.markdown(f"<h2 style='text-align:center; color:{CORES_GENUA['primaria']};'>GENUA</h2>", unsafe_allow_html=True)
        st.sidebar.markdown("---")


# ============================================================
# 6. HELPERS DE UI E GRÁFICOS APPLE HEALTH
# ============================================================
def titulo(texto: str):
    """Renderiza um título de seção padronizado com acento visual Apple."""
    st.markdown(
        f"<h4 style='color: {CORES_GENUA['primaria']}; margin-top: 8px; margin-bottom: 12px; font-weight: 700;'>{texto}</h4>",
        unsafe_allow_html=True,
    )


def toast(mensagem: str, tipo: str = "info"):
    """Toast visual (success/warning/error/info)."""
    icones = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
    icone = icones.get(tipo, "ℹ️")
    st.markdown(
        f"<div class='genua-toast {tipo}'>{icone}<span>{mensagem}</span></div>",
        unsafe_allow_html=True,
    )


def secao(titulo_texto: str, descricao: str = None):
    """Bloco de seção com título + subtítulo opcional."""
    titulo(titulo_texto)
    if descricao:
        st.markdown(
            f"<p style='color: {CORES_GENUA['texto_suave']}; "
            f"margin-top: -8px; margin-bottom: 16px; font-size: 0.9rem;'>{descricao}</p>",
            unsafe_allow_html=True,
        )


def aplicar_tema_matplotlib(plt):
    """Configura o Matplotlib para renderizar gráficos limpos estilo Apple Health."""
    plt.rcParams.update({
        "figure.facecolor": "#FFFFFF",
        "axes.facecolor": "#FFFFFF",
        "axes.edgecolor": "#E5E5EA",
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.color": "#F2F2F7",
        "grid.linestyle": "--",
        "grid.linewidth": 0.9,
        "font.sans-serif": ["Inter", "SF Pro Display", "DejaVu Sans", "Arial"],
        "text.color": CORES_GENUA["texto_escuro"],
        "axes.labelcolor": CORES_GENUA["texto_suave"],
        "xtick.color": CORES_GENUA["texto_suave"],
        "ytick.color": CORES_GENUA["texto_suave"],
    })
