"""Movimientos: arma un vale con uno o más productos (consumo, préstamo, devolución, ingreso)."""

import streamlit as st

from auth import current_user
from sheets_backend import (DELTA_STOCK, TIPOS_MOVIMIENTO, cerrar_vale, get_items, get_parametros,
                            get_registro, get_vales, registrar_vale)

usuario = current_user()
if usuario is None:
    st.stop()

st.title("🔄 Movimientos de stock")

items = get_items()
if items.empty:
    st.info("Todavía no hay productos cargados.")
    st.stop()

parametros = get_parametros()
sectores = parametros.get("SECTOR", []) or ["MANTENIMIENTO"]

if "carrito" not in st.session_state:
    st.session_state["carrito"] = []

tab_nuevo, tab_pendientes, tab_historial = st.tabs(
    ["➕ Nuevo vale", "⏳ Préstamos abiertos", "📜 Historial"]
)

# ------------------------------------------------------------------ Nuevo vale
with tab_nuevo:
    tipo = st.radio("Tipo de movimiento", TIPOS_MOVIMIENTO, horizontal=True,
                    help="CONSUMO y PRESTADO descuentan stock; DEVOLUCION e INGRESO lo suman.")

    st.subheader("1. Agregá los productos al vale")
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        opciones = {f"{r.descripcion} (N° {r.id}) — stock {r.stock_actual:.0f} {r.unidad}": r.id
                    for r in items.itertuples()}
        producto_sel = st.selectbox("Producto", list(opciones.keys()))
        item = items[items["id"] == opciones[producto_sel]].iloc[0]
    with c2:
        cantidad = st.number_input(f"Cantidad ({item['unidad']})", min_value=0.01, value=1.0, step=1.0)
    with c3:
        st.write("")
        st.write("")
        if st.button("Agregar al vale", use_container_width=True):
            st.session_state["carrito"].append({
                "item_id": int(item["id"]), "descripcion": item["descripcion"],
                "cantidad": float(cantidad), "unidad": item["unidad"],
                "stock_actual": float(item["stock_actual"]),
            })
            st.rerun()

    if item["ubicacion"].strip():
        st.caption(f"📍 Ubicación: {item['ubicacion']} · Estado: {item['estado']}")

    carrito = st.session_state["carrito"]
    if not carrito:
        st.info("Todavía no agregaste productos a este vale.")
    else:
        st.subheader("2. Productos del vale")
        for i, r in enumerate(carrito):
            col_a, col_b = st.columns([6, 1])
            col_a.write(f"**{r['descripcion']}** — {r['cantidad']:.0f} {r['unidad']} "
                        f"(stock actual: {r['stock_actual']:.0f})")
            if col_b.button("Quitar", key=f"quitar_{i}"):
                st.session_state["carrito"].pop(i)
                st.rerun()

        st.subheader("3. Datos del vale")
        with st.form("confirmar_vale"):
            f1, f2 = st.columns(2)
            with f1:
                sector = st.selectbox("Sector", sectores,
                                      index=sectores.index(usuario.get("SECTOR"))
                                      if usuario.get("SECTOR") in sectores else 0)
                area_sala = st.text_input("Área / Sala", placeholder="ej. Sala 3, Quirófano, Cocina")
            with f2:
                receptor = st.text_input("Receptor / para quién", value=usuario["NOMBRE"])
                observaciones = st.text_area("Observaciones", "", height=80)

            confirmar = st.form_submit_button("Registrar vale", type="primary")
            if confirmar:
                faltantes = [
                    r for r in carrito
                    if DELTA_STOCK.get(tipo, 0) < 0 and r["cantidad"] > r["stock_actual"]
                ]
                if faltantes:
                    nombres = ", ".join(f"{r['descripcion']} (hay {r['stock_actual']:.0f})" for r in faltantes)
                    st.error(f"No hay stock suficiente de: {nombres}")
                elif not receptor.strip():
                    st.error("Indicá para quién es el vale.")
                else:
                    id_vale = registrar_vale(tipo, sector, area_sala, receptor.strip(),
                                             observaciones, carrito)
                    st.session_state["carrito"] = []
                    st.success(f"Vale **{id_vale}** registrado con {len(carrito)} producto(s). "
                               f"El stock ya quedó actualizado.")
                    st.rerun()

# ------------------------------------------------------------------ Préstamos abiertos
with tab_pendientes:
    vales = get_vales()
    registro = get_registro()
    abiertos = vales[(vales["TIPO MOVIMIENTO"] == "PRESTADO") &
                     (vales["ESTADO VALE"].str.upper() == "ABIERTO")] if not vales.empty else vales

    if abiertos.empty:
        st.success("No hay préstamos abiertos.")
    else:
        st.caption(f"{len(abiertos)} préstamo(s) sin devolver")
        for _, v in abiertos.iterrows():
            id_vale = v["ID VALE"]
            with st.container(border=True):
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.write(f"**{id_vale}** · prestado a {v['Receptor / Para Quien']}")
                    st.caption(f"{v['FECHA HORA']} · Sector {v['SECTOR']} · "
                               f"{v['ÁREA / SALA'] or 'sin área'}")
                    for _, r in registro[registro["ID_VALE_REF"] == id_vale].iterrows():
                        st.write(f"— {r['DESCRIPCIÓN_ITEM']} × {r['CANT']:.0f} {r['UNIDAD']}")
                    if v["OBSERVACIONES"]:
                        st.caption(f"Obs.: {v['OBSERVACIONES']}")
                with col_b:
                    if st.button("Devolver", key=f"cerrar_{id_vale}", use_container_width=True):
                        cerrar_vale(id_vale)
                        st.success(f"Vale {id_vale} cerrado y stock repuesto.")
                        st.rerun()

# ------------------------------------------------------------------ Historial
with tab_historial:
    registro = get_registro()
    if registro.empty:
        st.info("Todavía no hay movimientos registrados.")
    else:
        vista = registro.sort_values("ID_REGISTRO", ascending=False)[
            ["FECHA_VALE", "ID_VALE_REF", "TIPO_MOV", "DESCRIPCIÓN_ITEM", "CANT", "UNIDAD",
             "OBSERVACIONES", "ESTADO_VALE (auto)"]
        ].rename(columns={
            "FECHA_VALE": "Fecha", "ID_VALE_REF": "Vale", "TIPO_MOV": "Tipo",
            "DESCRIPCIÓN_ITEM": "Producto", "CANT": "Cantidad", "UNIDAD": "Unidad",
            "OBSERVACIONES": "Observaciones", "ESTADO_VALE (auto)": "Estado",
        })
        st.dataframe(vista, hide_index=True, use_container_width=True, height=460)
