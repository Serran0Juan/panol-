"""Solicitudes de reparación: se avisa que algo se rompió y nace una orden de trabajo."""

import streamlit as st

from auth import current_user, puede
import estilo
from sheets_backend import PRIORIDADES, crear_solicitud, get_ordenes

usuario = current_user()
if usuario is None:
    st.stop()

st.markdown("###### MANTENIMIENTO · CORRECTIVO")
st.title("Solicitudes de reparación")
st.caption("Para avisar que algo se rompió o no funciona. Cada solicitud abre una "
           "orden de trabajo.")

ordenes = get_ordenes()
areas_previas = sorted(a for a in ordenes["AREA"].unique() if a) if not ordenes.empty else []

tab_nueva, tab_mias = st.tabs(["Nueva solicitud", "Las mías"])

# ═════════════════════════════════════════════════ nueva
with tab_nueva:
    with st.form("nueva_solicitud", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            area = st.text_input("¿Dónde es? *", placeholder="ej. Sala 3, Cocina, Quirófano 2")
            if areas_previas:
                st.caption("Ya se usaron: " + " · ".join(areas_previas[:8]))
        with c2:
            prioridad = st.selectbox("Prioridad", PRIORIDADES, index=1)

        descripcion = st.text_area(
            "¿Qué pasa? *", height=130,
            placeholder="Contá el problema con el mayor detalle posible: qué falla, "
                        "desde cuándo, si hay riesgo para alguien.")
        observaciones = st.text_input(
            "Cómo ubicarte (opcional)", placeholder="ej. interno 234, turno mañana")

        if st.form_submit_button("Enviar solicitud", type="primary"):
            if not area.strip():
                st.error("Indicá en qué lugar del hospital es.")
            elif len(descripcion.strip()) < 10:
                st.error("Contá un poco más sobre el problema.")
            else:
                id_ot = crear_solicitud(area.strip(), descripcion.strip(), prioridad,
                                        usuario["NOMBRE"], usuario["EMAIL"],
                                        observaciones.strip())
                st.success(f"Solicitud enviada. Quedó como orden **{id_ot}**. "
                           "Podés seguirla desde la pestaña «Las mías».")

    st.info("Si lo que falta es **material del pañol** (se acabaron los tornillos, "
            "hace falta comprar algo), usá **Pedidos y reclamos** en vez de esta sección.")

# ═════════════════════════════════════════════════ las mías
with tab_mias:
    if ordenes.empty:
        st.info("Todavía no hay solicitudes cargadas.")
        st.stop()

    mias = ordenes[ordenes["SOLICITANTE_EMAIL"].astype(str).str.lower()
                   == str(usuario["EMAIL"]).lower()]
    if mias.empty:
        st.info("Todavía no enviaste ninguna solicitud.")
        st.stop()

    st.caption(f"{len(mias)} solicitud(es) tuyas")
    for _, o in mias.sort_values("ID_OT", ascending=False).iterrows():
        with st.container(border=True):
            st.markdown(estilo.cabecera_orden(o["ID_OT"], o["AREA"], o["ESTADO"]),
                        unsafe_allow_html=True)
            st.caption(f"{o['FECHA_ALTA']} · prioridad {o['PRIORIDAD']}"
                       + (f" · asignada a {o['ASIGNADO_A']}" if o["ASIGNADO_A"] else ""))
            st.write(o["DESCRIPCION"])
            if o["ESTADO"] == "RESUELTA" and o["TRABAJO_REALIZADO"]:
                st.success(f"**Resuelta:** {o['TRABAJO_REALIZADO']}")

    if puede("gestionar_ot"):
        st.caption("Para ver todas las solicitudes del hospital, andá a "
                   "**Órdenes de trabajo**.")
