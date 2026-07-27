"""Pedidos y reclamos: los operarios avisan qué falta o qué problema hay."""

import streamlit as st

from auth import current_user, puede_gestionar
from sheets_backend import add_reclamo, get_items, get_reclamos, responder_reclamo

usuario = current_user()
if usuario is None:
    st.stop()

st.title("📢 Pedidos y reclamos")

TIPOS = ["FALTA STOCK", "PRODUCTO NUEVO", "PRODUCTO ROTO/VENCIDO", "UBICACIÓN INCORRECTA", "OTRO"]

tab_nuevo, tab_mios, tab_todos = st.tabs(["➕ Nuevo pedido", "📋 Los míos", "🗂️ Todos"])

with tab_nuevo:
    items = get_items()
    with st.form("nuevo_reclamo", clear_on_submit=True):
        tipo = st.selectbox("Tipo", TIPOS)

        productos = [""] + (items["descripcion"].tolist() if not items.empty else [])
        producto = st.selectbox("Producto relacionado (opcional)", productos,
                                help="Dejalo vacío si el producto todavía no está en el sistema.")
        producto_libre = st.text_input("...o escribí el nombre si no está en la lista", "")

        detalle = st.text_area("Contanos el detalle *", height=120,
                               placeholder="ej. Se acabaron los tarugos del 8, hacen falta para la sala 3.")

        if st.form_submit_button("Enviar", type="primary"):
            if not detalle.strip():
                st.error("Escribí el detalle del pedido.")
            else:
                add_reclamo(tipo, (producto or producto_libre).strip(), detalle.strip(),
                            usuario["EMAIL"], usuario["NOMBRE"])
                st.success("Pedido enviado. Queda registrado para que lo vea el responsable del pañol.")

with tab_mios:
    reclamos = get_reclamos()
    mios = (reclamos[reclamos["EMAIL"].str.lower() == usuario["EMAIL"].lower()]
            if not reclamos.empty else reclamos)
    if mios.empty:
        st.info("Todavía no enviaste ningún pedido.")
    else:
        for _, r in mios.sort_values("ID", ascending=False).iterrows():
            with st.container(border=True):
                icono = "🟢" if str(r["ESTADO"]).upper() == "RESUELTO" else "🟠"
                st.write(f"{icono} **{r['TIPO']}** · {r['PRODUCTO'] or 'sin producto'}")
                st.caption(f"{r['FECHA_HORA']} · Estado: {r['ESTADO']}")
                st.write(r["DETALLE"])
                if r["RESPUESTA"]:
                    st.success(f"Respuesta: {r['RESPUESTA']}")

with tab_todos:
    reclamos = get_reclamos()
    if reclamos.empty:
        st.info("No hay pedidos cargados.")
    elif not puede_gestionar(usuario):
        st.dataframe(
            reclamos[["FECHA_HORA", "TIPO", "PRODUCTO", "DETALLE", "NOMBRE", "ESTADO"]]
            .rename(columns={"FECHA_HORA": "Fecha", "TIPO": "Tipo", "PRODUCTO": "Producto",
                             "DETALLE": "Detalle", "NOMBRE": "Pidió", "ESTADO": "Estado"}),
            hide_index=True, use_container_width=True,
        )
    else:
        solo_abiertos = st.checkbox("Ver solo los abiertos", value=True)
        vista = reclamos[reclamos["ESTADO"].str.upper() == "ABIERTO"] if solo_abiertos else reclamos
        if vista.empty:
            st.success("No hay pedidos abiertos.")
        for _, r in vista.sort_values("ID", ascending=False).iterrows():
            with st.container(border=True):
                st.write(f"**{r['TIPO']}** · {r['PRODUCTO'] or 'sin producto'}")
                st.caption(f"{r['FECHA_HORA']} · {r['NOMBRE']} · Estado: {r['ESTADO']}")
                st.write(r["DETALLE"])
                with st.form(f"responder_{r['ID']}"):
                    respuesta = st.text_input("Respuesta", value=r["RESPUESTA"])
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("Guardar respuesta"):
                        responder_reclamo(r["ID"], r["ESTADO"], respuesta)
                        st.rerun()
                    if c2.form_submit_button("Marcar resuelto", type="primary"):
                        responder_reclamo(r["ID"], "RESUELTO", respuesta)
                        st.rerun()
