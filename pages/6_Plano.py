"""Plano del pañol: dónde queda cada estantería y qué hay en cada una."""

from pathlib import Path

import streamlit as st

from auth import current_user
from sheets_backend import get_estanterias, get_items, numero_estanteria

if current_user() is None:
    st.stop()

ASSETS = Path(__file__).parent.parent / "assets"

st.title("🗺️ Plano del pañol")

estanterias = get_estanterias()
items = get_items()

tab_plano, tab_estanterias = st.tabs(["📐 Plano", "🗄️ Estanterías"])

with tab_plano:
    plano = ASSETS / "plano_panol.png"
    if plano.exists():
        st.image(str(plano), use_container_width=True,
                 caption="Plano de ubicación de stock — Htal. Sor María Ludovica")
        pdf = ASSETS / "plano_panol.pdf"
        if pdf.exists():
            st.download_button("Descargar el plano en PDF", pdf.read_bytes(),
                               file_name="plano_panol.pdf", mime="application/pdf")
    else:
        st.warning("No se encontró la imagen del plano en la carpeta assets/.")

with tab_estanterias:
    if estanterias.empty:
        st.info("No hay estanterías cargadas en la pestaña 'Plano Pañol' de la planilla.")
        st.stop()

    areas = ["Todas"] + sorted(a for a in estanterias["area"].unique() if a)
    col_a, col_b = st.columns([1, 2])
    with col_a:
        area_sel = st.selectbox("Filtrar por área", areas)
    with col_b:
        q = st.text_input("Buscar en el contenido de las estanterías", "",
                          placeholder="ej. termofusion, cables, griferia...")

    filtradas = estanterias
    if area_sel != "Todas":
        filtradas = filtradas[filtradas["area"] == area_sel]
    if q.strip():
        filtradas = filtradas[filtradas["objetos"].str.contains(q.strip(), case=False, na=False)]

    st.caption(f"{len(filtradas)} de {len(estanterias)} estanterías")
    st.dataframe(
        filtradas[["estanteria", "area", "objetos", "ancho", "profundidad", "estantes"]]
        .rename(columns={"estanteria": "Estantería", "area": "Área", "objetos": "Qué guarda",
                         "ancho": "Ancho (m)", "profundidad": "Prof. (m)", "estantes": "N° estantes"}),
        hide_index=True, use_container_width=True, height=400,
    )

    st.divider()
    st.subheader("Ver qué productos hay en una estantería")
    elegida = st.selectbox("Estantería", filtradas["estanteria"].tolist() if not filtradas.empty else [])
    if elegida:
        fila = estanterias[estanterias["estanteria"] == elegida].iloc[0]
        st.write(f"**Área:** {fila['area']} · **Medidas:** {fila['ancho']} × {fila['profundidad']} m "
                 f"· **Estantes:** {fila['estantes']}")
        st.caption(fila["objetos"])

        if not items.empty:
            dentro = items[items["ubicacion"].apply(numero_estanteria) == elegida]
            if dentro.empty:
                st.info("Todavía no hay productos del inventario asignados a esta estantería. "
                        "Se cargan desde **Asignar ubicaciones**.")
            else:
                st.dataframe(
                    dentro[["id", "descripcion", "ubicacion", "stock_actual", "unidad", "estado"]]
                    .rename(columns={"id": "N°", "descripcion": "Producto", "ubicacion": "Ubicación",
                                     "stock_actual": "Stock", "unidad": "Unidad", "estado": "Estado"}),
                    hide_index=True, use_container_width=True,
                )
