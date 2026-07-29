"""Estilo visual del sistema.

La paleta base está en .streamlit/config.toml; acá va el detalle fino:
tarjetas, tablas, botones y la barra lateral.

Se apunta a los atributos data-testid de Streamlit, que son estables entre
versiones, y no a las clases generadas (que cambian en cada release).
"""

import streamlit as st

AZUL_NOCHE = "#0E2038"
AZUL = "#14507E"
AZUL_CLARO = "#2C7BC0"
FONDO = "#F5F7FA"
PANEL = "#FFFFFF"
BORDE = "#E3E9F0"
TEXTO = "#0F172A"
GRIS = "#64748B"

VERDE = "#15803D"
AMBAR = "#B45309"
ROJO = "#B91C1C"

CSS = f"""
<style>
/* ───────────────────────────── base ───────────────────────────── */
[data-testid="stAppViewContainer"] {{ background: {FONDO}; }}
[data-testid="stHeader"] {{ background: transparent; }}
/* Streamlit deja 80px de aire a cada lado; con 40px entran mejor las tablas */
[data-testid="stMainBlockContainer"] {{
    padding: 2.2rem 2.5rem 5rem 2.5rem; max-width: 1600px;
}}

/* ─────────────────────────── tipografía ────────────────────────── */
[data-testid="stMain"] h1 {{
    font-size: 2.1rem; font-weight: 700; color: {TEXTO};
    letter-spacing: -.02em; margin: 0 0 .2rem 0; padding: 0;
}}
[data-testid="stMain"] h2 {{
    font-size: 1.25rem; font-weight: 650; color: {TEXTO};
    margin: 1.6rem 0 .6rem 0; padding: 0;
}}
[data-testid="stMain"] h3 {{ font-size: 1.05rem; font-weight: 650; color: {TEXTO}; }}
/* el "PAÑOL · MANTENIMIENTO" de arriba de cada título */
[data-testid="stMain"] h6 {{
    font-size: .72rem; font-weight: 700; color: {AZUL_CLARO};
    letter-spacing: .12em; text-transform: uppercase;
    margin: 0 0 .1rem 0; padding: 0;
}}

/* ──────────────────────── indicadores (KPI) ────────────────────── */
[data-testid="stMetric"] {{
    background: {PANEL};
    border: 1px solid {BORDE};
    border-radius: 12px;
    padding: 1rem 1.15rem;
    box-shadow: 0 1px 2px rgba(15,23,42,.04);
}}
[data-testid="stMetricLabel"] {{
    font-size: .78rem !important; font-weight: 600; color: {GRIS};
}}
/* que la etiqueta larga baje de renglón en vez de cortarse con "..." */
[data-testid="stMetricLabel"] * {{
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.6rem !important; font-weight: 700; color: {TEXTO};
    line-height: 1.2; white-space: normal; overflow-wrap: anywhere;
}}

/* ───────────────────────────── tablas ──────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDE};
    border-radius: 12px;
    overflow: hidden;
    background: {PANEL};
    box-shadow: 0 1px 2px rgba(15,23,42,.04);
}}

/* ──────────────────────────── botones ──────────────────────────── */
[data-testid="stButton"] button {{
    border-radius: 8px; font-weight: 600; border: 1px solid {BORDE};
    transition: filter .15s ease;
}}
[data-testid="stButton"] button:hover {{ filter: brightness(.97); }}
[data-testid="stButton"] button[kind="primary"],
[data-testid="stButton"] button[kind="primaryFormSubmit"] {{
    background: {AZUL}; border-color: {AZUL}; color: #fff;
}}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stButton"] button[kind="primaryFormSubmit"]:hover {{
    background: #0F3F66; border-color: #0F3F66;
}}

/* ─────────────────────────── contenedores ──────────────────────── */
/* las "tarjetas" de st.container(border=True) */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
    background: {PANEL};
    border-radius: 12px;
}}

/* ───────────────────────────── pestañas ────────────────────────── */
[data-baseweb="tab-list"] {{ gap: .35rem; border-bottom: 1px solid {BORDE}; }}
[data-baseweb="tab"] {{
    font-weight: 600; color: {GRIS}; padding: .55rem .9rem;
}}
[data-baseweb="tab"][aria-selected="true"] {{ color: {AZUL}; }}

/* ───────────────────────────── avisos ──────────────────────────── */
[data-testid="stAlertContainer"] {{ border-radius: 10px; border: 1px solid {BORDE}; }}

/* ─────────────────────────── barra lateral ─────────────────────── */
[data-testid="stSidebarNavLink"] {{
    border-radius: 8px; margin: 1px .4rem; padding: .45rem .6rem;
    font-weight: 500;
}}
[data-testid="stSidebarNavLink"]:hover {{ background: rgba(255,255,255,.07); }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: rgba(111,168,220,.18);
    box-shadow: inset 3px 0 0 {AZUL_CLARO};
    font-weight: 650;
}}
[data-testid="stNavSectionHeader"] {{
    font-size: .68rem; font-weight: 700; letter-spacing: .13em;
    text-transform: uppercase; color: #8FA9C6;
    margin: 1rem .95rem .25rem .95rem;
}}
[data-testid="stSidebarHeader"], [data-testid="stSidebarLogo"] {{ padding-left: .3rem; }}
[data-testid="stSidebarUserContent"] [data-testid="stMetric"] {{ background: transparent; border: none; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.12); }}

/* filas de la barra lateral que no son navegación */
[data-testid="stSidebarUserContent"] p {{ color: #E6EDF7; }}
[data-testid="stSidebarUserContent"] [data-testid="stCaptionContainer"] p {{ color: #9DB4CE; }}
</style>
"""


def aplicar():
    """Inyecta el estilo. Se llama una vez, desde app.py."""
    st.markdown(CSS, unsafe_allow_html=True)


def badge(texto: str, tono: str = "gris") -> str:
    """Devuelve el HTML de una etiqueta de color, para usar con st.markdown."""
    colores = {
        "verde": (VERDE, "#DCFCE7"),
        "ambar": (AMBAR, "#FEF3C7"),
        "rojo": (ROJO, "#FEE2E2"),
        "azul": (AZUL, "#DBEAFE"),
        "gris": (GRIS, "#F1F5F9"),
    }
    color, fondo = colores.get(tono, colores["gris"])
    return (f'<span style="background:{fondo};color:{color};padding:2px 10px;'
            f'border-radius:999px;font-size:.75rem;font-weight:650;">{texto}</span>')
