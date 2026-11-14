"""Tema visual e componentes compartilhados do GENUA."""
from html import escape
from pathlib import Path
import streamlit as st

CORES_GENUA = {
    'primaria': '#103E55',       # Azul-Petróleo Profundo (Identidade GENUA)
    'secundaria': '#2E8B9A',     # Teal Clínico Vibrante (Destaques e Foco)
    'accent_ios': '#0071E3',     # Azul Interativo Apple (Links e Micro-interações)
    'fundo_claro': '#F5F5F7',    # Apple System Gray 6 (Fundo acetinado)
    'card_bg': '#FFFFFF',        # Superfície elevada pura
    'texto_escuro': '#1D1D1F',   # Apple SF Charcoal (Leitura de alto contraste)
    'texto_suave': '#516872',    # Apple SF Secondary Label (Legendas e subtítulos)
    'alerta_sucesso': '#34C759', # Apple System Green
    'alerta_aviso': '#FF9F0A',   # Apple System Orange/Amber
    'alerta_erro': '#FF3B30',    # Apple System Red
}


NOVO_LOGO_GENUA = "logo_genua_novo_v2.png"
ASSETS = Path(__file__).resolve().parent / "assets"


def aplicar_tema():
    st.set_page_config(page_title="GENUA | Fisioterapia esportiva", page_icon=NOVO_LOGO_GENUA,
                       layout="wide", initial_sidebar_state="collapsed")
    st.html(ASSETS / "genua.css")


def cabecalho(nome, descricao):
    st.html(f'<header class="genua-cabecalho"><h1>{escape(nome)}</h1><p>{escape(descricao)}</p></header>')


def titulo(texto):
    st.html(f'<h3 class="genua-titulo">{escape(texto)}</h3>')


def secao(titulo_texto, descricao=None):
    titulo(titulo_texto)
    if descricao:
        st.html(f'<p class="genua-descricao">{escape(descricao)}</p>')


def toast(mensagem, tipo="info"):
    tipo = tipo if tipo in ("success", "warning", "error", "info") else "info"
    getattr(st, tipo)(mensagem)


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
