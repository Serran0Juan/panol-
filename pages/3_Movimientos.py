"""Movimientos: entregas a operarios, devoluciones e ingresos.

Un vale = una visita de un operario. Cada renglón lleva su propio tipo, así una
misma entrega puede tener una herramienta prestada y unos tornillos consumidos.
"""

import streamlit as st

from auth import current_user, exigir
from sheets_backend import (DIAS_PARA_DEMORA, TIPOS_ENTREGA, cerrar_vale, convertir_a_consumo,
                            devolver_renglon, dias_desde, get_items, get_parametros,
                            get_registro, get_vales, registrar_ingreso, registrar_vale)

usuario = current_user()
if usuario is None:
    st.stop()
exigir("registrar_movimiento",
       "No tenés permiso para registrar movimientos. Podés consultar el **Historial**.")

st.markdown("###### PAÑOL · MANTENIMIENTO")
st.title("Registrar movimiento")
st.caption("Entregas a operarios, devoluciones e ingresos de mercadería.")

items = get_items()
if items.empty:
    st.info("Todavía no hay productos cargados.")
    st.stop()

parametros = get_parametros()
sectores = parametros.get("SECTOR", []) or ["MANTENIMIENTO"]

if "carrito" not in st.session_state:
    st.session_state["carrito"] = []

ICONO = {"PRESTADO": "🔄", "CONSUMO": "✔️", "INGRESO": "📥"}

tab_entrega, tab_ingreso, tab_pendientes = st.tabs(
    ["➕ Nueva entrega", "📥 Ingreso de mercadería", "⏳ Pendientes"]
)

# ═══════════════════════════════════════════════ Nueva entrega
with tab_entrega:
    st.subheader("1. ¿Para quién es?")
    c1, c2, c3 = st.columns(3)
    with c1:
        receptor = st.text_input("Receptor / para quién *", key="ent_receptor")
    with c2:
        sector = st.selectbox("Sector", sectores, key="ent_sector")
    with c3:
        area_sala = st.text_input("Área / Sala", key="ent_area",
                                  placeholder="ej. Sala 3, Cocina")

    st.subheader("2. ¿Qué se lleva?")
    p1, p2, p3, p4 = st.columns([4, 1.2, 1.6, 1.2])
    with p1:
        opciones = {f"{r.descripcion} (N° {r.id}) — hay {r.stock_actual:g} {r.unidad}": r.id
                    for r in items.itertuples()}
        elegido = st.selectbox("Producto", list(opciones.keys()), key="ent_producto")
        item = items[items["id"] == opciones[elegido]].iloc[0]
    with p2:
        cantidad = st.number_input(f"Cant. ({item['unidad']})", min_value=0.01, value=1.0,
                                   step=1.0, key="ent_cant")
    with p3:
        tipo = st.radio("Tipo", TIPOS_ENTREGA, key="ent_tipo", horizontal=False,
                        help="PRESTADO espera devolución. CONSUMO no vuelve "
                             "(pero podés registrar el sobrante después).")
    with p4:
        st.write("")
        if st.button("Agregar", use_container_width=True, key="ent_agregar"):
            st.session_state["carrito"].append({
                "item_id": int(item["id"]), "descripcion": item["descripcion"],
                "cantidad": float(cantidad), "unidad": item["unidad"], "tipo": tipo,
                "stock_actual": float(item["stock_actual"]),
            })
            st.rerun()

    detalle = [f"📍 {item['ubicacion']}" if item["ubicacion"] else "📍 sin ubicación",
               item["estado"]]
    st.caption(" · ".join(detalle))

    carrito = st.session_state["carrito"]
    if not carrito:
        st.info("Todavía no agregaste productos a este vale.")
    else:
        st.subheader("3. Productos del vale")
        for i, r in enumerate(carrito):
            col_a, col_b = st.columns([8, 1])
            col_a.write(f"{ICONO[r['tipo']]} **{r['descripcion']}** — "
                        f"{r['cantidad']:g} {r['unidad']} · {r['tipo'].title()}")
            if col_b.button("Quitar", key=f"quitar_{i}"):
                st.session_state["carrito"].pop(i)
                st.rerun()

        observaciones = st.text_area("Observaciones del vale", "", height=70, key="ent_obs")

        # el stock no puede quedar en negativo
        faltantes = []
        por_producto = {}
        for r in carrito:
            por_producto[r["item_id"]] = por_producto.get(r["item_id"], 0) + r["cantidad"]
        for item_id, total in por_producto.items():
            disponible = float(items[items["id"] == item_id].iloc[0]["stock_actual"])
            if total > disponible:
                nombre = items[items["id"] == item_id].iloc[0]["descripcion"]
                faltantes.append(f"{nombre} (pedís {total:g}, hay {disponible:g})")

        if faltantes:
            st.error("No hay stock suficiente de: " + "; ".join(faltantes))

        if st.button("✅ Registrar vale", type="primary",
                     disabled=bool(faltantes) or not receptor.strip()):
            id_vale = registrar_vale(sector, area_sala, receptor.strip(), observaciones,
                                     carrito, registrado_por=usuario["NOMBRE"])
            st.session_state["carrito"] = []
            st.success(f"Vale **{id_vale}** registrado con {len(carrito)} producto(s). "
                       "El stock se recalcula solo en la planilla.")
            st.rerun()

        if not receptor.strip():
            st.caption("Completá el receptor para poder registrar.")

# ═══════════════════════════════════════════════ Ingreso
with tab_ingreso:
    st.subheader("Reposición del pañol")
    st.caption("Para cuando llega una compra. Suma al stock inicial del producto "
               "y queda registrado en el historial.")

    with st.form("nuevo_ingreso", clear_on_submit=True):
        i1, i2 = st.columns([3, 1])
        with i1:
            op_ing = {f"{r.descripcion} (N° {r.id}) — hay {r.stock_actual:g} {r.unidad}": r.id
                      for r in items.itertuples()}
            eleg_ing = st.selectbox("Producto", list(op_ing.keys()))
        with i2:
            cant_ing = st.number_input("Cantidad", min_value=0.01, value=1.0, step=1.0)

        proveedor = st.text_input("Proveedor / remito", placeholder="ej. Ferretería Sur, remito 0012")
        obs_ing = st.text_area("Observaciones", "", height=70)

        if st.form_submit_button("Registrar ingreso", type="primary"):
            id_vale = registrar_ingreso(op_ing[eleg_ing], cant_ing,
                                        " · ".join(x for x in [proveedor, obs_ing] if x.strip()),
                                        usuario["NOMBRE"])
            st.success(f"Ingreso **{id_vale}** registrado.")

# ═══════════════════════════════════════════════ Pendientes
with tab_pendientes:
    vales = get_vales()
    registro = get_registro()

    abiertos = (vales[vales["ESTADO VALE"].str.upper() == "ABIERTO"]
                if not vales.empty else vales)

    if abiertos.empty:
        st.success("No hay nada pendiente de devolución.")
    else:
        st.caption(f"{len(abiertos)} vale(s) con préstamos sin devolver")

        for _, v in abiertos.iterrows():
            id_vale = v["ID VALE"]
            dias = dias_desde(v["FECHA HORA"])
            demorado = dias >= DIAS_PARA_DEMORA

            with st.container(border=True):
                cab1, cab2 = st.columns([4, 1])
                titulo = f"**{id_vale}** · {v['Receptor / Para Quien']}"
                if demorado:
                    titulo += f" · ⏰ **{dias} días**"
                elif dias >= 0:
                    titulo += f" · hace {dias} día(s)"
                cab1.markdown(titulo)
                cab1.caption(f"{v['SECTOR']} · {v['ÁREA / SALA'] or 'sin área'}"
                             + (f" · {v['OBSERVACIONES']}" if v["OBSERVACIONES"] else ""))
                if cab2.button("Devolver todo", key=f"todo_{id_vale}", use_container_width=True):
                    cerrar_vale(id_vale)
                    st.success(f"Vale {id_vale} cerrado.")
                    st.rerun()

                renglones = registro[registro["ID_VALE_REF"] == id_vale]
                for _, r in renglones.iterrows():
                    rid = r["ID_REGISTRO"]
                    pend = float(r["pendiente"])
                    # solo está saldado si además no le queda nada por devolver
                    saldado = r["ESTADO_RENGLON"] != "PENDIENTE" and pend == 0

                    f1, f2, f3, f4 = st.columns([4, 1.3, 1.3, 1.6])
                    etiqueta = (f"{ICONO.get(r['TIPO_MOV'], '•')} {r['DESCRIPCIÓN_ITEM']} — "
                                f"{r['CANT']:g} {r['UNIDAD']}")
                    if r["CANT_DEVUELTA"] > 0:
                        etiqueta += f"  ·  devuelto {r['CANT_DEVUELTA']:g}"
                    f1.write(etiqueta + ("  ✅" if saldado else ""))

                    if pend > 0:
                        cant_dev = f2.number_input("Devolver", min_value=0.0, max_value=pend,
                                                   value=pend, step=1.0, key=f"cd_{rid}",
                                                   label_visibility="collapsed")
                        if f3.button("Devolver", key=f"dev_{rid}", use_container_width=True):
                            devolver_renglon(rid, cant_dev)
                            st.success(f"Devolución registrada: {cant_dev:g} {r['UNIDAD']}.")
                            st.rerun()
                        if r["TIPO_MOV"] == "PRESTADO":
                            if f4.button("No vuelve → consumo", key=f"cons_{rid}",
                                         use_container_width=True):
                                convertir_a_consumo(rid)
                                st.success("Marcado como consumo. El stock queda descontado.")
                                st.rerun()
