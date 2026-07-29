"""Órdenes de trabajo: asignar, seguir el estado y hacer el cierre técnico."""

import pandas as pd
import streamlit as st

from auth import current_user, exigir
from sheets_backend import (ESTADOS_ABIERTOS, HORAS_ESTIMADAS_DEFECTO, ICONO_ESTADO_OT,
                            PRIORIDADES, SLA_DIAS, TRANSICIONES_OT, asignar_orden,
                            calcular_compromiso, cambiar_estado_orden, cerrar_orden,
                            get_ordenes, get_ot_estados, get_parametros,
                            get_usuarios_activos, parse_fecha)

usuario = current_user()
if usuario is None:
    st.stop()
exigir("gestionar_ot", "No tenés permiso para gestionar órdenes. "
                       "Las tuyas están en **Mis órdenes**.")

st.markdown("###### MANTENIMIENTO · CORRECTIVO")
st.title("Órdenes de trabajo")
st.caption("Solicitudes recibidas, asignación por sector y seguimiento hasta el cierre.")

ordenes = get_ordenes()
if ordenes.empty:
    st.info("Todavía no hay órdenes. Se generan desde **Solicitudes de reparación**.")
    st.stop()

sectores = get_parametros().get("SECTOR", []) or ["MANTENIMIENTO"]
personas = [u["NOMBRE"] for u in get_usuarios_activos()]

abiertas = ordenes[ordenes["ESTADO"].isin(ESTADOS_ABIERTOS)]
sin_asignar = ordenes[ordenes["ESTADO"] == "SOLICITADA"]
urgentes = abiertas[abiertas["PRIORIDAD"].str.upper() == "URGENTE"]
resueltas = ordenes[ordenes["ESTADO"] == "RESUELTA"]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Abiertas", len(abiertas))
k2.metric("Sin asignar", len(sin_asignar))
k3.metric("Urgentes 🔴", len(urgentes))
k4.metric("Vencidas ⏰", int(ordenes["vencida"].sum()))
k5.metric("Resueltas", len(resueltas))

st.divider()

tab_tablero, tab_detalle = st.tabs(["📋 Tablero", "🔎 Detalle y acciones"])

# ═════════════════════════════════════════════════ tablero
with tab_tablero:
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        f_estado = st.selectbox("Estado", ["Abiertas", "Todas"] + list(ICONO_ESTADO_OT))
    with f2:
        f_sector = st.selectbox("Sector", ["Todos"] + sectores)
    with f3:
        f_prioridad = st.selectbox("Prioridad", ["Todas"] + PRIORIDADES)
    with f4:
        q = st.text_input("Buscar", "", placeholder="área, problema, persona...")

    vista = ordenes
    if f_estado == "Abiertas":
        vista = vista[vista["ESTADO"].isin(ESTADOS_ABIERTOS)]
    elif f_estado != "Todas":
        vista = vista[vista["ESTADO"] == f_estado]
    if f_sector != "Todos":
        vista = vista[vista["SECTOR_ASIGNADO"] == f_sector]
    if f_prioridad != "Todas":
        vista = vista[vista["PRIORIDAD"].str.upper() == f_prioridad]
    if q.strip():
        t = q.strip()
        vista = vista[
            vista["AREA"].str.contains(t, case=False, na=False)
            | vista["DESCRIPCION"].str.contains(t, case=False, na=False)
            | vista["ASIGNADO_A"].str.contains(t, case=False, na=False)
            | vista["SOLICITANTE"].str.contains(t, case=False, na=False)
            | vista["ID_OT"].str.contains(t, case=False, na=False)
        ]

    st.caption(f"{len(vista)} de {len(ordenes)} órdenes")
    tabla = vista.sort_values(["vencida", "orden_prioridad", "ID_OT"],
                              ascending=[False, True, False])[
        ["ID_OT", "FECHA_ALTA", "AREA", "DESCRIPCION", "PRIORIDAD", "SECTOR_ASIGNADO",
         "ASIGNADO_A", "ESTADO", "FECHA_COMPROMISO", "dias_para_vencer",
         "FECHA_PROGRAMADA", "dias_abierta", "SOLICITANTE"]
    ].rename(columns={
        "ID_OT": "OT", "FECHA_ALTA": "Alta", "AREA": "Lugar", "DESCRIPCION": "Problema",
        "PRIORIDAD": "Prioridad", "SECTOR_ASIGNADO": "Sector", "ASIGNADO_A": "Responsable",
        "ESTADO": "Estado", "FECHA_COMPROMISO": "Vence",
        "dias_para_vencer": "Días restantes", "FECHA_PROGRAMADA": "Programada",
        "dias_abierta": "Días abierta", "SOLICITANTE": "Pidió",
    })
    st.dataframe(tabla, hide_index=True, width="stretch", height=420)
    st.download_button("⬇️ Descargar CSV", tabla.to_csv(index=False).encode("utf-8-sig"),
                       file_name="ordenes_trabajo.csv", mime="text/csv")

    if not sin_asignar.empty:
        st.subheader(f"🆕 Esperando asignación ({len(sin_asignar)})")
        for _, o in sin_asignar.sort_values("ID_OT", ascending=False).iterrows():
            with st.container(border=True):
                marca = " 🔴" if str(o["PRIORIDAD"]).upper() == "URGENTE" else ""
                st.markdown(f"**{o['ID_OT']}** · {o['AREA']} · {o['PRIORIDAD']}{marca}")
                st.caption(f"{o['FECHA_ALTA']} · pidió {o['SOLICITANTE']}"
                           + (f" · hace {o['dias_abierta']} día(s)" if o["dias_abierta"] >= 0 else ""))
                st.write(o["DESCRIPCION"])

# ═════════════════════════════════════════════════ detalle
with tab_detalle:
    etiquetas = {
        f"{ICONO_ESTADO_OT.get(o.ESTADO, '•')} {o.ID_OT} · {o.AREA} · {o.ESTADO}": o.ID_OT
        for o in ordenes.sort_values("ID_OT", ascending=False).itertuples()
    }
    elegida = st.selectbox("Orden", list(etiquetas.keys()))
    id_ot = etiquetas[elegida]
    o = ordenes[ordenes["ID_OT"] == id_ot].iloc[0]
    estado = o["ESTADO"]

    izq, der = st.columns([2, 1])
    with izq:
        st.subheader(f"{ICONO_ESTADO_OT.get(estado, '•')} {id_ot}")
        st.write(f"**Lugar:** {o['AREA']}  ·  **Prioridad:** {o['PRIORIDAD']}")
        st.write(f"**Problema:** {o['DESCRIPCION']}")
        if o["OBSERVACIONES"]:
            st.caption(f"Contacto: {o['OBSERVACIONES']}")
        st.caption(f"Pidió {o['SOLICITANTE']} el {o['FECHA_ALTA']}")
        if o["TRABAJO_REALIZADO"]:
            st.success(f"**Trabajo realizado:** {o['TRABAJO_REALIZADO']}")
            detalle_cierre = [f"Causa: {o['CAUSA']}" if o["CAUSA"] else "",
                              f"Horas: {o['HORAS']:g}" if o["HORAS"] else "",
                              f"Cierre: {o['FECHA_CIERRE']}"]
            st.caption(" · ".join(x for x in detalle_cierre if x))
    with der:
        st.metric("Estado", estado)
        if o["ASIGNADO_A"]:
            st.write(f"**Responsable:** {o['ASIGNADO_A']}")
            st.caption(f"Sector {o['SECTOR_ASIGNADO']}")
        if estado in ESTADOS_ABIERTOS and o["dias_abierta"] >= 0:
            st.caption(f"Abierta hace {o['dias_abierta']} día(s)")

    st.divider()

    if estado in ("RESUELTA", "ANULADA"):
        st.info(f"Esta orden está **{estado}**. No admite más cambios.")
    else:
        acc1, acc2 = st.columns(2)

        # ── asignar ──
        with acc1:
            st.markdown("##### Asignar")
            with st.form(f"asignar_{id_ot}"):
                idx_sector = sectores.index(o["SECTOR_ASIGNADO"]) if o["SECTOR_ASIGNADO"] in sectores else 0
                sector = st.selectbox("Sector", sectores, index=idx_sector)
                opciones_p = personas or [""]
                idx_p = opciones_p.index(o["ASIGNADO_A"]) if o["ASIGNADO_A"] in opciones_p else 0
                asignado = st.selectbox("Responsable", opciones_p, index=idx_p)
                idx_pri = PRIORIDADES.index(o["PRIORIDAD"]) if o["PRIORIDAD"] in PRIORIDADES else 1
                prioridad = st.selectbox("Prioridad", PRIORIDADES, index=idx_pri)
                horas_est = st.number_input(
                    "Horas estimadas", min_value=0.0, step=0.5,
                    value=float(o["HORAS_ESTIMADAS"] or HORAS_ESTIMADAS_DEFECTO),
                    help="Sirve para calcular la carga de trabajo de cada persona.")

                compromiso_auto = calcular_compromiso(prioridad, parse_fecha(o["FECHA_ALTA"]))
                pisar = st.checkbox("Elegir otra fecha de vencimiento",
                                    help=f"Por prioridad {prioridad} vence el {compromiso_auto}.")
                fecha_compromiso = None
                if pisar:
                    actual = parse_fecha(o["FECHA_COMPROMISO"]) or parse_fecha(compromiso_auto)
                    elegida_f = st.date_input("Vence el", value=actual.date(),
                                              format="DD/MM/YYYY")
                    fecha_compromiso = elegida_f.strftime("%Y-%m-%d")
                else:
                    st.caption(f"Vencimiento automático: **{compromiso_auto}** "
                               f"({SLA_DIAS.get(prioridad, 7)} días desde el alta)")

                if st.form_submit_button("Guardar asignación", type="primary"):
                    asignar_orden(id_ot, sector, asignado, prioridad, usuario["NOMBRE"],
                                  fecha_compromiso=fecha_compromiso,
                                  horas_estimadas=horas_est)
                    st.success(f"{id_ot} asignada a {asignado}.")
                    st.rerun()

        # ── cambiar estado ──
        with acc2:
            st.markdown("##### Cambiar estado")
            posibles = TRANSICIONES_OT.get(estado, [])
            if not posibles:
                st.caption("No hay transiciones posibles desde este estado.")
            else:
                with st.form(f"estado_{id_ot}"):
                    nuevo = st.selectbox("Nuevo estado", posibles)
                    nota = st.text_input("Nota (opcional)")
                    if st.form_submit_button("Aplicar"):
                        if nuevo == "RESUELTA":
                            st.warning("Para resolver, usá el cierre técnico de abajo.")
                        else:
                            cambiar_estado_orden(id_ot, nuevo, usuario["NOMBRE"], nota)
                            st.success(f"{id_ot} pasó a {nuevo}.")
                            st.rerun()

        # ── cierre técnico ──
        if estado in ("ASIGNADA", "EN CURSO", "PAUSADA"):
            st.markdown("##### Cierre técnico")
            with st.form(f"cerrar_{id_ot}"):
                trabajo = st.text_area("¿Qué se hizo? *", height=110,
                                       placeholder="Detalle de la reparación realizada.")
                cc1, cc2 = st.columns(2)
                with cc1:
                    causa = st.text_input("Causa de la falla",
                                          placeholder="ej. desgaste, mal uso, falta de mantenimiento")
                with cc2:
                    horas = st.number_input("Horas de trabajo", min_value=0.0, value=1.0, step=0.5)
                if st.form_submit_button("Cerrar orden", type="primary"):
                    try:
                        cerrar_orden(id_ot, trabajo.strip(), causa.strip(), horas,
                                     usuario["NOMBRE"])
                        st.success(f"{id_ot} cerrada como RESUELTA.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            st.caption("Los materiales usados todavía se descargan aparte, desde "
                       "**Registrar movimiento**. La integración automática viene después.")

    # ── bitácora ──
    estados = get_ot_estados()
    historia = estados[estados["ID_OT"] == id_ot] if not estados.empty else pd.DataFrame()
    if not historia.empty:
        st.divider()
        st.markdown("##### Seguimiento")
        for _, h in historia.sort_values("ID", ascending=False).iterrows():
            icono = ICONO_ESTADO_OT.get(str(h["ESTADO"]).upper(), "•")
            st.write(f"{icono} **{h['ESTADO']}** · {h['FECHA_HORA']} · {h['USUARIO']}"
                     + (f" — {h['NOTA']}" if h["NOTA"] else ""))
