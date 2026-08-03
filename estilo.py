"""Estilo visual del sistema.

La paleta base está en .streamlit/config.toml; acá va el detalle fino:
tarjetas, tablas, botones y la barra lateral.

Se apunta a los atributos data-testid de Streamlit, que son estables entre
versiones, y no a las clases generadas (que cambian en cada release).

El sistema no usa emojis: el color y la tipografía hacen ese trabajo. Cada
familia de valores (sector, estado del stock, estado y prioridad de una orden)
tiene su color definido acá y en ningún otro lado, así una misma cosa se ve
igual en toda la app.
"""

import html

import streamlit as st
import streamlit.components.v1 as components

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

# ── Colores por familia ──────────────────────────────────────────────────────
# Cada entrada es (texto, fondo, gráfico):
#   texto   = el color de la letra sobre el fondo claro
#   fondo   = el relleno de la etiqueta o de la celda
#   gráfico = el tono lleno, para las barras y las tortas
NEUTRO = ("#475569", "#F1F5F9", "#9AA7B8")

# Sectores y áreas. El criterio es el que ya venía usando el pañol.
COLORES_SECTOR = {
    "TAREAS VARIAS": ("#166534", "#DCFCE7", "#6EC177"),  # verde claro
    "ELECTRICIDAD": ("#5B21B6", "#EDE9FE", "#9B7EDE"),   # violeta claro
    "PLOMERÍA": ("#1D4ED8", "#DBEAFE", "#6BA6E8"),       # azul claro
    "PINTURA": ("#9A3412", "#FFEDD5", "#E8A860"),        # naranja claro
    "OTROS": NEUTRO,
}

# Semáforo del stock. Reemplaza a los círculos de colores que había antes.
COLORES_STOCK = {
    "OK": (VERDE, "#DCFCE7", "#6EC177"),
    "Mínimo": (AMBAR, "#FEF3C7", "#E9B949"),
    "Sin stock": (ROJO, "#FEE2E2", "#E06B6B"),
}

# Circuito de una orden de trabajo.
COLORES_ESTADO_OT = {
    "SOLICITADA": ("#475569", "#F1F5F9", "#9AA7B8"),
    "ASIGNADA": ("#1D4ED8", "#DBEAFE", "#6BA6E8"),
    "EN CURSO": ("#5B21B6", "#EDE9FE", "#9B7EDE"),
    "PAUSADA": (AMBAR, "#FEF3C7", "#E9B949"),
    "RESUELTA": (VERDE, "#DCFCE7", "#6EC177"),
    "ANULADA": ("#64748B", "#F1F5F9", "#C3CBD6"),
}

COLORES_PRIORIDAD = {
    "URGENTE": (ROJO, "#FEE2E2", "#E06B6B"),
    "ALTA": (AMBAR, "#FEF3C7", "#E9B949"),
    "MEDIA": ("#1D4ED8", "#DBEAFE", "#6BA6E8"),
    "BAJA": NEUTRO,
}

# Estado de un renglón de movimiento.
COLORES_RENGLON = {
    "Cerrado": (VERDE, "#DCFCE7", "#6EC177"),
    "Pendiente": (AMBAR, "#FEF3C7", "#E9B949"),
}


def escapar(valor) -> str:
    """Deja un texto listo para meter dentro de HTML.

    Todo lo que se dibuja con unsafe_allow_html tiene que pasar por acá. El
    área de una orden, por ejemplo, la escribe a mano cualquier usuario al
    cargar una solicitud: sin escapar, alguien podría dejar etiquetas HTML que
    después se ejecutan en la pantalla del resto.
    """
    return html.escape(str(valor if valor is not None else ""))


def colores(valor, mapa) -> tuple[str, str, str]:
    """Los tres colores de un valor. Lo que no está en el mapa sale neutro.

    No distingue mayúsculas de minúsculas (en la planilla los estados están en
    mayúsculas y en pantalla se muestran capitalizados) y descarta el detalle
    entre paréntesis que llevan algunos, como "Pendiente (3 de 10)".
    """
    clave = str(valor).strip().split(" (")[0].casefold()
    for nombre, terna in mapa.items():
        if nombre.casefold() == clave:
            return terna
    return NEUTRO


def color_grafico(valor, mapa) -> str:
    return colores(valor, mapa)[2]


def mapa_grafico(valores, mapa) -> dict:
    """color_discrete_map listo para plotly."""
    return {v: color_grafico(v, mapa) for v in valores}


def pintar_celda(mapa):
    """Función para df.style.map(): pinta la celda con el color de su valor."""
    def estilo_de(valor):
        texto, fondo, _ = colores(valor, mapa)
        return f"background-color: {fondo}; color: {texto}; font-weight: 600;"

    return estilo_de


def pesos(monto) -> str:
    """Un monto como se escribe acá: $1.234.567, redondeado al peso.

    Los centavos se van a propósito: un precio de $84.932,65 se lee peor y no
    cambia ninguna decisión.
    """
    try:
        return "$" + f"{float(monto):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return ""


def tabla(df, pintar: dict | None = None, moneda=()):
    """Prepara un DataFrame para st.dataframe con las celdas de color puestas.

    `pintar` dice qué columna se pinta con qué mapa, por ejemplo
    {"Estado": COLORES_STOCK, "Sector": COLORES_SECTOR}. Es lo que reemplaza a
    los emojis: el color hace que el estado y el sector se lean de un vistazo.
    `moneda` es la lista de columnas que llevan importes.

    Además vuelve a formatear los números. Streamlit los muestra prolijos por su
    cuenta, pero deja de hacerlo en cuanto se le pasa un Styler: sin esto un 2
    se vería como 2.000000 y un importe como 73824205.6.
    """
    estilizado = df.style
    for columna, mapa in (pintar or {}).items():
        if columna in df.columns:
            estilizado = estilizado.map(pintar_celda(mapa), subset=[columna])

    importes = [c for c in moneda if c in df.columns]
    if importes:
        estilizado = estilizado.format(pesos, subset=importes, na_rep="")
    numericas = [c for c in df.select_dtypes("number").columns if c not in importes]
    if numericas:
        estilizado = estilizado.format("{:g}", subset=numericas, na_rep="")
    return estilizado

CSS = f"""
<style>
/* ───────────────────────────── base ───────────────────────────── */
/* el componente que declara el idioma no dibuja nada: que no deje hueco */
[data-testid="stIFrame"][height="0"],
[data-testid="stElementContainer"]:has(> [data-testid="stIFrame"][height="0"]) {{
    display: none !important;
}}
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
/* Tarjeta propia, en vez de st.metric: permite agregar una línea de contexto
   ("34% del catálogo") y una franja de color al costado cuando el número es
   una alerta. Un número suelto no dice si está bien o mal; el contexto sí. */
.kpi {{
    background: {PANEL}; border: 1px solid {BORDE}; border-radius: 12px;
    padding: .95rem 1.1rem; box-shadow: 0 1px 2px rgba(15,23,42,.04);
    height: 100%; min-height: 122px; border-left: 4px solid {BORDE};
}}
/* con cinco tarjetas en fila la columna queda angosta; sin esto Streamlit
   parte las palabras a la mitad ("responsabl / e") */
.kpi-etiqueta, .kpi-detalle {{ overflow-wrap: break-word; word-break: normal; }}
/* y que todas las tarjetas de una fila midan lo mismo aunque el texto de una
   ocupe dos renglones. La columna ya se estira sola; hay que ir pasándole el
   alto a cada envoltorio que Streamlit mete entre la columna y la tarjeta */
[data-testid="stColumn"]:has(.kpi) [data-testid="stVerticalBlock"],
[data-testid="stColumn"]:has(.kpi) [data-testid="stElementContainer"],
[data-testid="stColumn"]:has(.kpi) [data-testid="stMarkdown"],
[data-testid="stColumn"]:has(.kpi) [data-testid="stMarkdown"] > div,
[data-testid="stColumn"]:has(.kpi) [data-testid="stMarkdownContainer"] {{
    height: 100%;
}}
.kpi-etiqueta {{
    font-size: .68rem; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: {GRIS};
}}
/* el número nunca parte en dos renglones: si no entra, se achica */
.kpi-valor {{
    font-size: clamp(1.35rem, 2.1vw, 1.85rem); font-weight: 700; color: {TEXTO};
    line-height: 1.15; margin-top: .3rem; white-space: nowrap;
}}
.kpi-detalle {{ font-size: .78rem; color: {GRIS}; margin-top: .2rem; }}
.kpi-cero .kpi-valor {{ color: {GRIS}; }}

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

/* ──────────────────────── buscador de productos ────────────────── */
/* El buscador deja escribir texto libre además de elegir un producto de la
   lista (accept_new_options). Streamlit rotula esa opción "Add: lo que
   escribiste", en inglés, que al operario no le dice nada: se tapa el rótulo y
   se pone uno en castellano. Si Streamlit cambiara ese atributo, lo único que
   pasa es que se vuelve a ver el rótulo original. */
[role="option"][data-key="__creatable__"] > div {{
    color: transparent; position: relative;
}}
[role="option"][data-key="__creatable__"] > div::after {{
    content: "Buscar ese texto en toda la lista";
    color: {GRIS}; position: absolute; left: 0; top: 0; white-space: nowrap;
}}

/* ───────────────────────────── avisos ──────────────────────────── */
[data-testid="stAlertContainer"] {{ border-radius: 10px; border: 1px solid {BORDE}; }}

/* ─────────────────────────── barra lateral ─────────────────────── */
/* Los nombres van en versalita: en mayúsculas, algo más chicos y con las
   letras separadas, que es lo que las hace legibles a ese tamaño. Se hace
   desde acá y no en app.py para que en el código los títulos se sigan
   leyendo normales. */
[data-testid="stSidebarNavLink"] {{
    border-radius: 8px; margin: 1px .4rem; padding: .5rem .65rem;
    font-size: .78rem; font-weight: 600; letter-spacing: .07em;
    text-transform: uppercase;
}}
[data-testid="stSidebarNavLink"]:hover {{ background: rgba(255,255,255,.07); }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: rgba(111,168,220,.18);
    box-shadow: inset 3px 0 0 {AZUL_CLARO};
    font-weight: 700;
}}
/* el encabezado del grupo tiene que distinguirse de sus páginas: va más
   chico, más espaciado y sin peso */
[data-testid="stNavSectionHeader"] {{
    font-size: .64rem; font-weight: 700; letter-spacing: .16em;
    text-transform: uppercase; color: #7C93AF;
    margin: 1.25rem .95rem .3rem .95rem;
}}
[data-testid="stSidebarHeader"], [data-testid="stSidebarLogo"] {{ padding-left: .3rem; }}
[data-testid="stSidebarUserContent"] [data-testid="stMetric"] {{ background: transparent; border: none; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.12); }}

/* filas de la barra lateral que no son navegación */
[data-testid="stSidebarUserContent"] p {{ color: #E6EDF7; }}
[data-testid="stSidebarUserContent"] [data-testid="stCaptionContainer"] p {{ color: #9DB4CE; }}
</style>
"""


def declarar_idioma():
    """Le avisa al navegador que la página está en castellano.

    Streamlit marca la página como inglés (`<html lang="en">`) y no da forma de
    cambiarlo. Con eso, Chrome ofrece traducirla y a veces lo hace solo, con
    resultados absurdos: "Registrar movimiento" le sale "Movimiento del
    registrador" —leyó "registrar" como sustantivo inglés— y "Agenda" le sale
    "Orden del día".

    El script va dentro de un componente, que es la única forma de que Streamlit
    ejecute JavaScript. El componente es un iframe del mismo origen, así que
    puede tocar la página que lo contiene. Queda de alto cero y escondido.
    """
    components.html(
        """<script>
        const doc = window.parent.document;
        doc.documentElement.lang = "es";
        if (!doc.querySelector('meta[name="google"]')) {
            const meta = doc.createElement("meta");
            meta.name = "google";
            meta.content = "notranslate";
            doc.head.appendChild(meta);
        }
        </script>""",
        height=0,
    )


def aplicar():
    """Inyecta el estilo. Se llama una vez, desde app.py."""
    st.markdown(CSS, unsafe_allow_html=True)
    declarar_idioma()


TONOS = {
    "verde": (VERDE, "#DCFCE7", "#6EC177"),
    "ambar": (AMBAR, "#FEF3C7", "#E9B949"),
    "rojo": (ROJO, "#FEE2E2", "#E06B6B"),
    "azul": (AZUL, "#DBEAFE", "#6BA6E8"),
    "gris": NEUTRO,
}


def badge(texto: str, tono="gris") -> str:
    """HTML de una etiqueta de color, para usar con st.markdown.

    `tono` puede ser un nombre ("verde", "rojo"...) o directamente una terna de
    colores sacada de alguno de los mapas de arriba.
    """
    color, fondo = (tono if isinstance(tono, tuple) else TONOS.get(tono, NEUTRO))[:2]
    return (f'<span style="background:{fondo};color:{color};padding:2px 10px;'
            f'border-radius:999px;font-size:.75rem;font-weight:650;'
            f'white-space:nowrap;">{escapar(texto)}</span>')


def etiqueta(valor, mapa) -> str:
    """La etiqueta de color que le corresponde a un valor de un mapa."""
    return badge(valor, colores(valor, mapa))


def cabecera_orden(id_ot, area, estado, prioridad="") -> str:
    """Título de una orden: el número, el lugar y sus etiquetas de color.

    Reemplaza a los iconos que había antes por estado. Se usa igual en Órdenes,
    Mis órdenes, Agenda y Solicitudes, así una orden se ve siempre igual.
    Va con st.markdown(..., unsafe_allow_html=True).
    """
    pastillas = [etiqueta(estado, COLORES_ESTADO_OT)]
    if prioridad:
        pastillas.append(etiqueta(prioridad, COLORES_PRIORIDAD))
    # el área la escribe a mano quien carga la solicitud: va escapada
    return f"**{escapar(id_ot)}** · {escapar(area)} &nbsp; " + " ".join(pastillas)


def indicador(etiqueta_kpi: str, valor, detalle: str = "", tono=None) -> str:
    """HTML de una tarjeta de indicador.

    `detalle` es la línea de contexto de abajo, la que explica si el número está
    bien o mal. `tono` pinta la franja del costado; se pasa solo cuando el
    número es una alerta, y no se dibuja si el número es cero: un cero no tiene
    nada de qué alertar.
    """
    apagado = "" if valor not in (0, "0") else " kpi-cero"
    franja = f"border-left-color: {tono[0]};" if tono and not apagado else ""
    linea = f'<div class="kpi-detalle">{escapar(detalle)}</div>' if detalle else ""
    return (f'<div class="kpi{apagado}" style="{franja}">'
            f'<div class="kpi-etiqueta">{escapar(etiqueta_kpi)}</div>'
            f'<div class="kpi-valor">{escapar(valor)}</div>{linea}</div>')


def fila_indicadores(tarjetas):
    """Dibuja una fila de indicadores, uno por columna."""
    for columna, html in zip(st.columns(len(tarjetas)), tarjetas):
        columna.markdown(html, unsafe_allow_html=True)
