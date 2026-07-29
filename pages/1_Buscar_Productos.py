"""Buscador de productos: dónde está, cuánto hay y en qué estantería."""

import streamlit as st

from auth import current_user
from sheets_backend import get_estanterias, get_items, numero_estanteria

if current_user() is None:
    st.stop()

st.title("🔍 Buscar productos")

items = get_items()
if items.empty:
    st.info("Todavía no hay productos cargados.")
    st.stop()

estanterias = get_estanterias().set_index("estanteria")

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    q = st.text_input("Buscar por nombre", "", placeholder="ej. cable, canilla, tornillo...")
with c2:
    categorias = ["Todas"] + sorted(c for c in items["categoria"].unique() if c)
    cat = st.selectbox("Categoría", categorias)
with c3:
    estado_sel = st.selectbox("Estado", ["Todos", "🟢 OK", "🟡 Mínimo", "🔴 Sin stock"])

filtrado = items
if q.strip():
    filtrado = filtrado[filtrado["descripcion"].str.contains(q.strip(), case=False, na=False)]
if cat != "Todas":
    filtrado = filtrado[filtrado["categoria"] == cat]
if estado_sel != "Todos":
    filtrado = filtrado[filtrado["estado"] == estado_sel]

st.caption(f"{len(filtrado)} de {len(items)} productos")

sin_ubicacion = int((filtrado["ubicacion"].str.strip() == "").sum())
if sin_ubicacion:
    st.info(f"{sin_ubicacion} de estos productos todavía no tienen ubicación cargada.")

st.dataframe(
    filtrado[["id", "descripcion", "ubicacion", "stock_actual", "unidad",
              "stock_minimo", "estado", "categoria", "subcategoria"]]
    .rename(columns={
        "id": "N°", "descripcion": "Producto", "ubicacion": "Ubicación",
        "stock_actual": "Stock", "unidad": "Unidad", "stock_minimo": "Mínimo",
        "estado": "Estado", "categoria": "Categoría", "subcategoria": "Subcategoría",
    }),
    hide_index=True, width="stretch", height=420,
)

st.divider()
st.subheader("Ver detalle de un producto")

if filtrado.empty:
    st.stop()

opciones = {f"{r.descripcion} (N° {r.id})": r.id for r in filtrado.itertuples()}
elegido = st.selectbox("Producto", list(opciones.keys()), label_visibility="collapsed")
item = items[items["id"] == opciones[elegido]].iloc[0]

d1, d2, d3 = st.columns(3)
d1.metric("Stock actual", f"{item['stock_actual']:.0f} {item['unidad']}")
d2.metric("Stock mínimo", f"{item['stock_minimo']:.0f}")
d3.metric("Estado", item["estado"])

est = numero_estanteria(item["ubicacion"])
if not item["ubicacion"].strip():
    st.warning("Este producto todavía no tiene ubicación asignada.")
elif est in estanterias.index:
    fila = estanterias.loc[est]
    st.success(f"📍 **Ubicación: {item['ubicacion']}** — Estantería {est}, área {fila['area']}")
    st.caption(f"Qué guarda esa estantería: {fila['objetos']}")

    vecinos = items[(items["ubicacion"].apply(numero_estanteria) == est) & (items["id"] != item["id"])]
    if not vecinos.empty:
        with st.expander(f"Otros {len(vecinos)} productos en la estantería {est}"):
            st.dataframe(
                vecinos[["descripcion", "ubicacion", "stock_actual", "unidad", "estado"]]
                .rename(columns={"descripcion": "Producto", "ubicacion": "Ubicación",
                                 "stock_actual": "Stock", "unidad": "Unidad", "estado": "Estado"}),
                hide_index=True, width="stretch",
            )
else:
    st.info(f"📍 Ubicación: {item['ubicacion']}")
