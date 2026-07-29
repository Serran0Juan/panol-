"""Agenda: qué hay para hacer hoy, esta semana, y cómo está repartido el trabajo."""

import datetime as dt

import pandas as pd
import streamlit as st

from auth import current_user, exigir
from sheets_backend import (ESTADOS_ABIERTOS, HORAS_JORNADA, ICONO_ESTADO_OT,
                            carga_por_persona, get_ordenes, get_usuarios_activos,
                            programar_orden)

usuario = current_user()
if usuario is None:
    st.stop()
exigir("gestionar_ot", "No tenés permiso para planificar. Lo tuyo está en **Mis órdenes**.")

st.markdown("###### MANTENIMIENTO · PLANIFICACIÓN")
st.title("Agenda")
st.caption("Qué hay para hacer, cuándo vence y cómo está repartida la carga.")

ordenes = get_ordenes()
if ordenes.empty:
    st.info("Todavía no hay órdenes de trabajo cargadas.")
    st.stop()

abiertas = ordenes[ordenes["ESTADO"].isin(ESTADOS_ABIERTOS)].copy()
if abiertas.empty:
    st.success("No hay órdenes abiertas. Todo al día.")
    st.stop()

hoy = dt.date.today()
fin_semana = hoy + dt.timedelta(days=(6 - hoy.weekday()))

vencidas = abiertas[abiertas["vencida"]]
de_hoy = abiertas[abiertas["dia_programado"] == hoy]
de_semana = abiertas[abiertas["dia_programado"].apply(
    lambda d: d is not None and hoy < d <= fin_semana)]
sin_programar = abiertas[abiertas["dia_programado"].isna()]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Vencidas ⏰", len(vencidas))
k2.metric("Para hoy", len(de_hoy))
k3.metric("Resto de la semana", len(de_semana))
k4.metric("Sin programar", len(sin_programar))

st.divider()


def tarjeta(o, contexto, con_programar=True):
    """Dibuja una orden con sus datos y el control para agendarla.

    Una misma orden puede salir en más de una lista (por ejemplo vencida y sin
    programar), así que la clave de cada control lleva el contexto además del
    número de orden: si no, Streamlit se queja de claves repetidas.
    """
    clave = f"{contexto}_{o['ID_OT']}"
    with st.container(border=True):
        c1, c2 = st.columns([3, 1.4])
        with c1:
            marca = " 🔴" if o["PRIORIDAD"] == "URGENTE" else ""
            st.markdown(f"{ICONO_ESTADO_OT.get(o['ESTADO'], '•')} **{o['ID_OT']}** · "
                        f"{o['AREA']} · {o['PRIORIDAD']}{marca}")
            detalle = [o["ESTADO"]]
            if o["ASIGNADO_A"]:
                detalle.append(o["ASIGNADO_A"])
            if o["SECTOR_ASIGNADO"]:
                detalle.append(o["SECTOR_ASIGNADO"])
            if o["HORAS_ESTIMADAS"]:
                detalle.append(f"{o['HORAS_ESTIMADAS']:g} h estimadas")
            st.caption(" · ".join(detalle))
            st.write(o["DESCRIPCION"])

            # ojo: pandas deja NaN (no None) cuando la orden no tiene fecha
            d = o["dias_para_vencer"]
            if d is not None and not pd.isna(d):
                d = int(d)
                if d < 0:
                    st.error(f"⏰ Vencida hace {abs(d)} día(s) "
                             f"(era para el {o['FECHA_COMPROMISO']})")
                elif d == 0:
                    st.warning("Vence hoy")
                else:
                    st.caption(f"Vence en {d} día(s) — {o['FECHA_COMPROMISO']}")

        if con_programar:
            with c2:
                actual = o["dia_programado"] or hoy
                nueva = st.date_input("Programar para", value=actual,
                                      key=f"fecha_{clave}", format="DD/MM/YYYY")
                horas = st.number_input("Horas estimadas", min_value=0.0, step=0.5,
                                        value=float(o["HORAS_ESTIMADAS"] or 1.0),
                                        key=f"horas_{clave}")
                b1, b2 = st.columns(2)
                if b1.button("Agendar", key=f"ag_{clave}", width="stretch"):
                    programar_orden(o["ID_OT"], nueva.strftime("%Y-%m-%d"),
                                    usuario["NOMBRE"], horas)
                    st.rerun()
                if o["dia_programado"] and b2.button("Quitar", key=f"qu_{clave}",
                                                     width="stretch"):
                    programar_orden(o["ID_OT"], "", usuario["NOMBRE"])
                    st.rerun()


tab_hoy, tab_semana, tab_pendientes, tab_carga = st.tabs(
    ["📅 Hoy", "🗓️ Esta semana", "📥 Sin programar", "⚖️ Carga del equipo"])

with tab_hoy:
    if not vencidas.empty:
        st.subheader(f"⏰ Vencidas ({len(vencidas)})")
        st.caption("Van primero: ya pasaron su fecha comprometida.")
        for _, o in vencidas.sort_values("dias_para_vencer").iterrows():
            tarjeta(o, "venc")
        st.divider()

    st.subheader(f"Programadas para hoy ({len(de_hoy)})")
    if de_hoy.empty:
        st.info("No hay nada agendado para hoy.")
    else:
        for _, o in de_hoy.sort_values("orden_prioridad").iterrows():
            tarjeta(o, "hoy")

with tab_semana:
    if de_semana.empty:
        st.info("No hay nada agendado para el resto de la semana.")
    else:
        for dia in sorted({d for d in de_semana["dia_programado"] if d is not None}):
            del_dia = de_semana[de_semana["dia_programado"] == dia]
            horas = del_dia["HORAS_ESTIMADAS"].sum()
            nombre_dia = ["lunes", "martes", "miércoles", "jueves", "viernes",
                          "sábado", "domingo"][dia.weekday()]
            st.subheader(f"{nombre_dia.capitalize()} {dia.strftime('%d/%m')} — "
                         f"{len(del_dia)} orden(es), {horas:g} h")
            for _, o in del_dia.sort_values("orden_prioridad").iterrows():
                tarjeta(o, f"sem{dia}")

with tab_pendientes:
    if sin_programar.empty:
        st.success("Todas las órdenes abiertas están agendadas.")
    else:
        st.caption(f"{len(sin_programar)} orden(es) sin fecha. Ordenadas por prioridad "
                   "y por vencimiento más cercano.")
        for _, o in sin_programar.sort_values(
                ["orden_prioridad", "dias_para_vencer"], na_position="last").iterrows():
            tarjeta(o, "pend")

with tab_carga:
    carga = carga_por_persona(ordenes)
    if carga.empty:
        st.info("No hay órdenes abiertas asignadas a nadie.")
    else:
        st.caption(f"Horas pendientes por persona. La barra toma como referencia una "
                   f"semana de {HORAS_JORNADA * 5:g} horas ({HORAS_JORNADA} h por día).")
        for _, p in carga.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{p['persona']}**")
                    st.caption(f"{int(p['ordenes'])} orden(es) · {p['horas']:g} h estimadas"
                               + (f" · ⏰ {int(p['vencidas'])} vencida(s)" if p["vencidas"] else ""))
                    st.progress(min(float(p["capacidad"]), 1.0))
                with c2:
                    pct = int(p["capacidad"] * 100)
                    st.metric("Ocupación", f"{pct}%")
                if p["capacidad"] > 1:
                    st.warning("Tiene más trabajo del que entra en la semana.")

        sin_nadie = ordenes[ordenes["ESTADO"].isin(ESTADOS_ABIERTOS)
                            & (ordenes["ASIGNADO_A"].astype(str).str.strip() == "")]
        if not sin_nadie.empty:
            st.info(f"Además hay {len(sin_nadie)} orden(es) abiertas sin responsable. "
                    "Se asignan desde **Órdenes de trabajo**.")

        libres = [u["NOMBRE"] for u in get_usuarios_activos()
                  if u["NOMBRE"] not in set(carga["persona"])]
        if libres:
            st.caption("Sin órdenes abiertas: " + ", ".join(libres))
