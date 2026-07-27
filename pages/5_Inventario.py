"""Inventario: alta y edición de productos (solo roles de gestión)."""

import streamlit as st

from auth import current_user, puede_gestionar
from sheets_backend import add_item, get_estanterias, get_items, get_parametros, update_item

usuario = current_user()
if usuario is None:
    st.stop()
if not puede_gestionar(usuario):
    st.error("No tenés permiso para ver esta sección.")
    st.stop()

st.title("📦 Inventario")

items = get_items()
parametros = get_parametros()
unidades = parametros.get("UNIDAD", []) or ["un"]
categorias_param = parametros.get("CATEGORIA", [])
estanterias = get_estanterias()

tab_editar, tab_nuevo = st.tabs(["✏️ Editar productos", "➕ Nuevo producto"])

with tab_editar:
    if items.empty:
        st.info("No hay productos cargados.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            q = st.text_input("Buscar", "")
        with c2:
            cat = st.selectbox("Categoría", ["Todas"] + sorted(c for c in items["categoria"].unique() if c))

        filtrado = items
        if q.strip():
            filtrado = filtrado[filtrado["descripcion"].str.contains(q.strip(), case=False, na=False)]
        if cat != "Todas":
            filtrado = filtrado[filtrado["categoria"] == cat]

        st.caption(f"{len(filtrado)} productos")
        st.dataframe(
            filtrado[["id", "descripcion", "categoria", "ubicacion", "stock_actual",
                      "stock_minimo", "unidad", "precio_unitario", "estado"]]
            .rename(columns={"id": "N°", "descripcion": "Producto", "categoria": "Categoría",
                             "ubicacion": "Ubicación", "stock_actual": "Stock",
                             "stock_minimo": "Mínimo", "unidad": "Unidad",
                             "precio_unitario": "Precio", "estado": "Estado"}),
            hide_index=True, use_container_width=True, height=320,
        )

        if not filtrado.empty:
            opciones = {f"{r.descripcion} (N° {r.id})": r.id for r in filtrado.itertuples()}
            elegido = st.selectbox("Producto a editar", list(opciones.keys()))
            item = items[items["id"] == opciones[elegido]].iloc[0]

            with st.form("editar_item"):
                e1, e2 = st.columns(2)
                with e1:
                    descripcion = st.text_input("Descripción", item["descripcion"])
                    categoria = st.text_input("Categoría", item["categoria"])
                    subcategoria = st.text_input("Subcategoría", item["subcategoria"])
                    ubicacion = st.text_input("Ubicación", item["ubicacion"],
                                              help="Número de estantería, ej. 18 o 18-2 (estantería-nivel)")
                with e2:
                    unidad = st.text_input("Unidad", item["unidad"])
                    stock_actual = st.number_input("Stock actual", min_value=0.0,
                                                   value=float(item["stock_actual"]), step=1.0)
                    stock_minimo = st.number_input("Stock mínimo", min_value=0.0,
                                                   value=float(item["stock_minimo"]), step=1.0)
                    precio = st.number_input("Precio unitario ($)", min_value=0.0,
                                             value=float(item["precio_unitario"]), step=1.0)

                if st.form_submit_button("Guardar cambios", type="primary"):
                    update_item(int(item["id"]), descripcion=descripcion, categoria=categoria,
                                subcategoria=subcategoria, ubicacion=ubicacion, unidad=unidad,
                                stock_actual=stock_actual, stock_minimo=stock_minimo,
                                precio_unitario=precio)
                    st.success("Producto actualizado en la planilla.")
                    st.rerun()

            st.caption("Los productos no se eliminan desde la app para no romper el historial de vales. "
                       "Si hace falta dar de baja uno, hacelo directamente en la planilla.")

with tab_nuevo:
    with st.form("nuevo_item", clear_on_submit=True):
        n1, n2 = st.columns(2)
        with n1:
            descripcion = st.text_input("Descripción *")
            categoria = st.selectbox("Categoría *", categorias_param) if categorias_param \
                else st.text_input("Categoría *")
            subcategoria = st.text_input("Subcategoría")
            opciones_ubi = [""] + estanterias["estanteria"].tolist() if not estanterias.empty else [""]
            ubicacion = st.selectbox("Estantería", opciones_ubi)
        with n2:
            unidad = st.selectbox("Unidad", unidades)
            stock_actual = st.number_input("Stock actual", min_value=0.0, value=0.0, step=1.0)
            stock_minimo = st.number_input("Stock mínimo", min_value=0.0, value=0.0, step=1.0)
            precio = st.number_input("Precio unitario ($)", min_value=0.0, value=0.0, step=1.0)

        if st.form_submit_button("Agregar producto", type="primary"):
            if not descripcion.strip() or not categoria:
                st.error("Descripción y categoría son obligatorias.")
            else:
                nuevo_id = add_item(descripcion.strip(), categoria, subcategoria.strip(),
                                    unidad, ubicacion, stock_minimo, stock_actual, precio)
                st.success(f"Producto agregado con el N° {nuevo_id}.")
