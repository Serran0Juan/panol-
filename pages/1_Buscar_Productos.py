"""Buscador de productos: dónde está, cuánto hay y en qué estantería."""

import streamlit as st

import estilo
from auth import current_user
from sheets_backend import ESTADOS_STOCK, get_estanterias, get_items, numero_estanteria

if current_user() is None:
    st.stop()

st.markdown("###### PAÑOL")
st.title("Buscar productos")

items = get_items()
if items.empty:
    st.info("Todavía no hay productos cargados.")
    st.stop()

estanterias = get_estanterias().set_index("estanteria")

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    # Un selectbox y no un text_input: Streamlit filtra la lista en el navegador
    # a medida que se escribe, sin ir y volver al servidor en cada letra.
    # accept_new_options deja además escribir cualquier texto y buscar por parte
    # del nombre, aunque no coincida con ningún producto entero.
    q = st.selectbox(
        "Buscar por nombre",
        sorted(items["descripcion"].unique()),
        index=None,
        placeholder="Escribí y van apareciendo: cable, canilla, tornillo...",
        accept_new_options=True,
    )
with c2:
    categorias = ["Todas"] + sorted(c for c in items["categoria"].unique() if c)
    cat = st.selectbox("Sector", categorias)
with c3:
    estado_sel = st.selectbox("Estado", ["Todos"] + ESTADOS_STOCK)

texto = str(q or "").strip()

filtrado = items
if texto:
    # regex=False: hay productos con paréntesis y comillas en el nombre, y como
    # expresión regular romperían la búsqueda.
    filtrado = filtrado[filtrado["descripcion"].str.contains(
        texto, case=False, na=False, regex=False)]
if cat != "Todas":
    filtrado = filtrado[filtrado["categoria"] == cat]
if estado_sel != "Todos":
    filtrado = filtrado[filtrado["estado"] == estado_sel]

st.caption(f"{len(filtrado)} de {len(items)} productos")

sin_ubicacion = int((filtrado["ubicacion"].str.strip() == "").sum())
if sin_ubicacion:
    st.info(f"{sin_ubicacion} de estos productos todavía no tienen ubicación cargada.")

# El stock mínimo no se muestra acá: al operario le alcanza con el semáforo de
# la columna Estado. El número está en Inventario, para quien gestiona.
tabla = (filtrado[["id", "descripcion", "ubicacion", "stock_actual", "unidad",
                   "estado", "categoria", "subcategoria"]]
         .rename(columns={
             "id": "N°", "descripcion": "Producto", "ubicacion": "Ubicación",
             "stock_actual": "Stock", "unidad": "Unidad", "estado": "Estado",
             "categoria": "Sector", "subcategoria": "Subcategoría",
         }))
st.dataframe(
    estilo.tabla(tabla, {"Estado": estilo.COLORES_STOCK,
                         "Sector": estilo.COLORES_SECTOR}),
    hide_index=True, width="stretch", height=420,
)

st.divider()
st.subheader("Ver detalle de un producto")

if filtrado.empty:
    st.stop()

opciones = {f"{r.descripcion} (N° {r.id})": r.id for r in filtrado.itertuples()}
elegido = st.selectbox("Producto", list(opciones.keys()), label_visibility="collapsed")
item = items[items["id"] == opciones[elegido]].iloc[0]

d1, d2 = st.columns([1, 2])
d1.metric("Stock actual", f"{item['stock_actual']:.0f} {item['unidad']}")
with d2:
    st.caption("Estado")
    st.markdown(estilo.etiqueta(item["estado"], estilo.COLORES_STOCK) + " " +
                estilo.etiqueta(item["categoria"], estilo.COLORES_SECTOR),
                unsafe_allow_html=True)

est = numero_estanteria(item["ubicacion"])
if not item["ubicacion"].strip():
    st.warning("Este producto todavía no tiene ubicación asignada.")
elif est in estanterias.index:
    fila = estanterias.loc[est]
    st.success(f"**Ubicación: {item['ubicacion']}** — Estantería {est}, área {fila['area']}")
    st.caption(f"Qué guarda esa estantería: {fila['objetos']}")

    vecinos = items[(items["ubicacion"].apply(numero_estanteria) == est) & (items["id"] != item["id"])]
    if not vecinos.empty:
        with st.expander(f"Otros {len(vecinos)} productos en la estantería {est}"):
            cercanos = (vecinos[["descripcion", "ubicacion", "stock_actual", "unidad", "estado"]]
                        .rename(columns={"descripcion": "Producto", "ubicacion": "Ubicación",
                                         "stock_actual": "Stock", "unidad": "Unidad",
                                         "estado": "Estado"}))
            st.dataframe(
                estilo.tabla(cercanos, {"Estado": estilo.COLORES_STOCK}),
                hide_index=True, width="stretch",
            )
else:
    st.info(f"Ubicación: {item['ubicacion']}")
