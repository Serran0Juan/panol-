"""Mis órdenes: las reparaciones asignadas a cada uno."""

import pandas as pd
import streamlit as st

from auth import current_user
import estilo
from orden_impresa import nombre_archivo, orden_en_html
from sheets_backend import (ESTADOS_ABIERTOS, TRANSICIONES_OT, ahora_texto,
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
    # lo vencido primero, después por prioridad
    pendientes = abiertas.sort_values(["vencida", "orden_prioridad", "ID_OT"],
                                      ascending=[False, True, True])

    for _, o in pendientes.iterrows():
        id_ot = o["ID_OT"]
        estado = o["ESTADO"]
        with st.container(border=True):
            st.markdown(estilo.cabecera_orden(id_ot, o["AREA"], estado, o["PRIORIDAD"]),
                        unsafe_allow_html=True)
            st.caption(f"Pidió {o['SOLICITANTE']} el {o['FECHA_ALTA']}"
                       + (f" · hace {o['dias_abierta']} día(s)" if o["dias_abierta"] >= 0 else ""))
            st.write(o["DESCRIPCION"])
            if o["OBSERVACIONES"]:
                st.caption(f"Contacto: {o['OBSERVACIONES']}")

            # ojo: pandas deja NaN (no None) cuando la orden no tiene fecha
            d = o["dias_para_vencer"]
            if d is not None and not pd.isna(d):
                d = int(d)
                if d < 0:
                    st.error(f"Vencida hace {abs(d)} día(s) — era para el "
                             f"{o['FECHA_COMPROMISO']}")
                elif d == 0:
                    st.warning("Vence hoy")
                else:
                    st.caption(f"Vence en {d} día(s) — {o['FECHA_COMPROMISO']}")
            if o["dia_programado"]:
                st.caption(f"Programada para el {o['dia_programado'].strftime('%d/%m/%Y')}")

            # la hoja para llevarse al trabajo y hacerla firmar al volver
            st.download_button("Imprimir orden",
                               orden_en_html(o, usuario["NOMBRE"], ahora_texto()),
                               file_name=nombre_archivo(o), mime="text/html",
                               key=f"imprimir_{id_ot}",
                               help="Para anotar a mano qué hiciste y qué materiales "
                                    "usaste, y que el responsable del sector te firme "
                                    "la conformidad.")

            # cambiar de estado sin salir de la tarjeta
            posibles = [e for e in TRANSICIONES_OT.get(estado, []) if e not in ("RESUELTA", "ANULADA")]
            if posibles:
                cols = st.columns(len(posibles) + 1)
                for i, nuevo in enumerate(posibles):
                    if cols[i].button(f"Pasar a {nuevo}", key=f"est_{id_ot}_{nuevo}",
                                      width="stretch"):
                        cambiar_estado_orden(id_ot, nuevo, usuario["NOMBRE"])
                        st.rerun()

            with st.expander("Cerrar esta orden"):
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
