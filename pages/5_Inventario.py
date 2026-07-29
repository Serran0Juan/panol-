"""Inventario: alta y edición de productos (solo roles de gestión)."""

import streamlit as st

from auth import current_user, exigir, puede
from sheets_backend import add_item, get_estanterias, get_items, get_parametros, update_item

usuario = current_user()
if usuario is None:
    st.stop()
exigir("ver_gestion")

puede_editar = puede("editar_inventario")

st.markdown("###### PAÑOL · MANTENIMIENTO")
st.title("Inventario")
st.caption("Existencias, ubicación y estado de cada material.")

items = get_items()
parametros = get_parametros()
unidades = parametros.get("UNIDAD", []) or ["un"]
categorias_param = parametros.get("CATEGORIA", [])
estanterias = get_estanterias()

if puede_editar:
    tab_editar, tab_nuevo, tab_valor = st.tabs(
        ["📋 Materiales", "➕ Nuevo material", "💲 Valorización"])
else:
    tab_editar, tab_valor = st.tabs(["📋 Materiales", "💲 Valorización"])
    tab_nuevo = st.empty()  # marcador de posición: sin permiso no se dibuja el alta

with tab_editar:
    if items.empty:
        st.info("No hay productos cargados.")
    else:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            q = st.text_input("Buscar", "", placeholder="nombre o ubicación...")
        with c2:
            cat = st.selectbox("Categoría", ["Todas"] + sorted(c for c in items["categoria"].unique() if c))
        with c3:
            est = st.selectbox("Estado", ["Todos", "🟢 OK", "🟡 Mínimo", "🔴 Sin stock"])

        filtrado = items
        if q.strip():
            t = q.strip()
            filtrado = filtrado[filtrado["descripcion"].str.contains(t, case=False, na=False)
                                | filtrado["ubicacion"].str.contains(t, case=False, na=False)]
        if cat != "Todas":
            filtrado = filtrado[filtrado["categoria"] == cat]
        if est != "Todos":
            filtrado = filtrado[filtrado["estado"] == est]

        st.caption(f"{len(filtrado)} materiales encontrados")
        st.dataframe(
            filtrado[["id", "descripcion", "categoria", "ubicacion", "stock_actual",
                      "unidad", "stock_minimo", "estado"]]
            .rename(columns={"id": "N°", "descripcion": "Descripción", "categoria": "Categoría",
                             "ubicacion": "Ubicación", "stock_actual": "Stock",
                             "unidad": "Unidad", "stock_minimo": "Mínimo", "estado": "Estado"}),
            hide_index=True, use_container_width=True, height=380,
        )

        if not puede_editar:
            st.caption("Tenés acceso de solo lectura: podés consultar el inventario "
                       "pero no modificarlo.")

        if puede_editar and not filtrado.empty:
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
                    stock_inicial = st.number_input(
                        "Stock inicial", min_value=0.0, value=float(item["stock_inicial"]), step=1.0,
                        help="El stock actual NO se edita: la planilla lo calcula como "
                             "stock inicial menos consumos menos préstamos pendientes.")
                    stock_minimo = st.number_input("Stock mínimo", min_value=0.0,
                                                   value=float(item["stock_minimo"]), step=1.0)
                    precio = st.number_input("Precio unitario ($)", min_value=0.0,
                                             value=float(item["precio_unitario"]), step=1.0)

                st.info(f"**Stock actual: {item['stock_actual']:g} {item['unidad']}** "
                        f"= inicial {item['stock_inicial']:g} − consumos − préstamos pendientes. "
                        "Se recalcula solo con cada movimiento.")

                if st.form_submit_button("Guardar cambios", type="primary"):
                    update_item(int(item["id"]), descripcion=descripcion, categoria=categoria,
                                subcategoria=subcategoria, ubicacion=ubicacion, unidad=unidad,
                                stock_inicial=stock_inicial, stock_minimo=stock_minimo,
                                precio_unitario=precio)
                    st.success("Producto actualizado en la planilla.")
                    st.rerun()

            st.caption("Los productos no se eliminan desde la app para no romper el historial de vales. "
                       "Si hace falta dar de baja uno, hacelo directamente en la planilla.")

def formulario_nuevo_material():
    """Alta de un material. Solo se dibuja si el usuario puede editar el inventario."""
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


if puede_editar:
    with tab_nuevo:
        formulario_nuevo_material()

# ═══════════════════════════════════════════════ Valorización
with tab_valor:
    if items.empty:
        st.info("No hay productos cargados.")
    else:
        st.caption("Precios unitarios y cuánto vale el stock que hay hoy en el pañol.")

        con_precio = items[items["precio_unitario"] > 0]
        v1, v2, v3 = st.columns(3)
        v1.metric("Valor total del inventario",
                  f"${items['valor'].sum():,.0f}".replace(",", "."))
        v2.metric("Materiales con precio cargado", f"{len(con_precio)} de {len(items)}")
        faltante = items[items["stock_actual"] <= 0]
        costo_reposicion = (faltante["stock_minimo"] * faltante["precio_unitario"]).sum()
        v3.metric("Costo de reponer lo agotado",
                  f"${costo_reposicion:,.0f}".replace(",", "."),
                  help="Lo que costaría llevar al mínimo todo lo que está sin stock.")

        por_cat = (items.groupby("categoria", as_index=False)["valor"].sum()
                   .sort_values("valor", ascending=False))
        st.dataframe(
            por_cat.rename(columns={"categoria": "Categoría", "valor": "Valor del stock ($)"}),
            hide_index=True, use_container_width=True,
        )

        st.subheader("Detalle por material")
        orden = st.selectbox("Ordenar por", ["Mayor valor en stock", "Mayor precio unitario",
                                             "Sin precio cargado"])
        detalle = items.copy()
        if orden == "Mayor valor en stock":
            detalle = detalle.sort_values("valor", ascending=False)
        elif orden == "Mayor precio unitario":
            detalle = detalle.sort_values("precio_unitario", ascending=False)
        else:
            detalle = detalle[detalle["precio_unitario"] <= 0].sort_values("descripcion")

        st.dataframe(
            detalle[["id", "descripcion", "categoria", "stock_actual", "unidad",
                     "precio_unitario", "valor"]]
            .rename(columns={"id": "N°", "descripcion": "Descripción", "categoria": "Categoría",
                             "stock_actual": "Stock", "unidad": "Unidad",
                             "precio_unitario": "Precio unit. ($)", "valor": "Valor ($)"}),
            hide_index=True, use_container_width=True, height=380,
        )
