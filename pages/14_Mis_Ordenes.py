"""Mis órdenes: las reparaciones asignadas a cada uno."""

import streamlit as st

from auth import current_user
from sheets_backend import (ESTADOS_ABIERTOS, ICONO_ESTADO_OT, TRANSICIONES_OT,
                            cambiar_estado_orden, cerrar_orden, get_ordenes)

usuario = current_user()
if usuario is None:
    st.stop()

st.markdown("###### MANTENIMIENTO · CORRECTIVO")
st.title("Mis órdenes")
st.caption("Las reparaciones que tenés asignadas.")

ordenes = get_ordenes()
if ordenes.empty:
    st.info("Todavía no hay órdenes de trabajo cargadas.")
    st.stop()

nombre = str(usuario["NOMBRE"]).strip().lower()
mias = ordenes[ordenes["ASIGNADO_A"].astype(str).str.strip().str.lower() == nombre]

if mias.empty:
    st.info("No tenés órdenes asignadas por ahora.")
    st.stop()

abiertas = mias[mias["ESTADO"].isin(ESTADOS_ABIERTOS)]
cerradas = mias[~mias["ESTADO"].isin(ESTADOS_ABIERTOS)]

k1, k2, k3 = st.columns(3)
k1.metric("Asignadas a mí", len(mias))
k2.metric("Pendientes", len(abiertas))
k3.metric("Terminadas", len(cerradas))

if abiertas.empty:
    st.success("No te queda ninguna orden pendiente.")
else:
    st.subheader("Pendientes")
    orden_prioridad = {"URGENTE": 0, "ALTA": 1, "MEDIA": 2, "BAJA": 3}
    pendientes = abiertas.assign(
        _orden=abiertas["PRIORIDAD"].str.upper().map(orden_prioridad).fillna(9)
    ).sort_values(["_orden", "ID_OT"])

    for _, o in pendientes.iterrows():
        id_ot = o["ID_OT"]
        estado = o["ESTADO"]
        with st.container(border=True):
            marca = " 🔴" if str(o["PRIORIDAD"]).upper() == "URGENTE" else ""
            st.markdown(f"{ICONO_ESTADO_OT.get(estado, '•')} **{id_ot}** · {o['AREA']} "
                        f"· {o['PRIORIDAD']}{marca}")
            st.caption(f"{estado} · pidió {o['SOLICITANTE']} el {o['FECHA_ALTA']}"
                       + (f" · hace {o['dias_abierta']} día(s)" if o["dias_abierta"] >= 0 else ""))
            st.write(o["DESCRIPCION"])
            if o["OBSERVACIONES"]:
                st.caption(f"Contacto: {o['OBSERVACIONES']}")

            # cambiar de estado sin salir de la tarjeta
            posibles = [e for e in TRANSICIONES_OT.get(estado, []) if e not in ("RESUELTA", "ANULADA")]
            if posibles:
                cols = st.columns(len(posibles) + 1)
                for i, nuevo in enumerate(posibles):
                    if cols[i].button(f"Pasar a {nuevo}", key=f"est_{id_ot}_{nuevo}",
                                      width="stretch"):
                        cambiar_estado_orden(id_ot, nuevo, usuario["NOMBRE"])
                        st.rerun()

            with st.expander("✅ Cerrar esta orden"):
                with st.form(f"cerrar_mia_{id_ot}"):
                    trabajo = st.text_area("¿Qué hiciste? *", height=100,
                                           placeholder="Detalle de la reparación.")
                    c1, c2 = st.columns(2)
                    with c1:
                        causa = st.text_input("Causa de la falla")
                    with c2:
                        horas = st.number_input("Horas", min_value=0.0, value=1.0, step=0.5)
                    if st.form_submit_button("Cerrar orden", type="primary"):
                        try:
                            cerrar_orden(id_ot, trabajo.strip(), causa.strip(), horas,
                                         usuario["NOMBRE"])
                            st.success(f"{id_ot} cerrada.")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                st.caption("Si usaste materiales del pañol, avisá para que se "
                           "descarguen del stock.")

if not cerradas.empty:
    st.subheader("Terminadas")
    st.dataframe(
        cerradas.sort_values("ID_OT", ascending=False)[
            ["ID_OT", "AREA", "DESCRIPCION", "ESTADO", "FECHA_CIERRE", "HORAS"]
        ].rename(columns={"ID_OT": "OT", "AREA": "Lugar", "DESCRIPCION": "Problema",
                          "ESTADO": "Estado", "FECHA_CIERRE": "Cierre", "HORAS": "Horas"}),
        hide_index=True, width="stretch",
    )
