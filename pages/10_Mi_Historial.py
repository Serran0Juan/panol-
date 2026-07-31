"""Mi historial: lo que retiró cada persona y lo que todavía tiene sin devolver."""

import streamlit as st

import estilo
from auth import current_user
from sheets_backend import DIAS_PARA_DEMORA, dias_desde, get_items, get_movimientos

usuario = current_user()
if usuario is None:
    st.stop()

st.markdown("###### PAÑOL · MANTENIMIENTO")
st.title("Mi historial")

movs = get_movimientos()
if movs.empty:
    st.info("Todavía no hay movimientos registrados.")
    st.stop()

nombre = str(usuario["NOMBRE"]).strip().lower()
mios = movs[movs["Receptor / Para Quien"].astype(str).str.strip().str.lower() == nombre]

if mios.empty:
    st.info("Todavía no retiraste nada del pañol. "
            "Si creés que falta algo, avisale al responsable del pañol: los vales se "
            "cargan con el nombre tal como figura en tu usuario.")
    st.stop()

items = get_items().set_index("id")
pendientes = mios[(mios["ESTADO_RENGLON"] == "PENDIENTE") & (mios["pendiente"] > 0)]

# ───────────────────────────────────────────── lo que debo devolver
if pendientes.empty:
    st.success("No tenés nada pendiente de devolver.")
else:
    st.subheader(f"Tenés {len(pendientes)} cosa(s) sin devolver")
    for _, r in pendientes.iterrows():
        dias = dias_desde(r["FECHA_VALE"])
        with st.container(border=True):
            titulo = f"**{r['DESCRIPCIÓN_ITEM']}** — {r['pendiente']:g} {r['UNIDAD']}"
            if dias >= DIAS_PARA_DEMORA:
                titulo += f"  ·  **{dias} días**"
            st.markdown(titulo)

            detalle = [f"Vale {r['ID_VALE_REF']}"]
            if dias >= 0:
                detalle.append(f"retirado hace {dias} día(s)")
            try:
                ubic = items.loc[int(r["ID_ITEM"]), "ubicacion"]
                if str(ubic).strip():
                    detalle.append(f"Ubicación {ubic}")
            except (KeyError, ValueError):
                pass
            st.caption(" · ".join(detalle))

    st.caption("La devolución la registra el pañol cuando entregás el material.")

# ───────────────────────────────────────────── todo lo que me llevé
st.divider()
st.subheader("Lo que me llevé")

c1, c2 = st.columns([1, 3])
with c1:
    tipo = st.selectbox("Tipo", ["Todos"] + sorted(mios["TIPO_MOV"].unique()))
with c2:
    q = st.text_input("Buscar material", "")

vista = mios
if tipo != "Todos":
    vista = vista[vista["TIPO_MOV"] == tipo]
if q.strip():
    vista = vista[vista["DESCRIPCIÓN_ITEM"].str.contains(q.strip(), case=False, na=False, regex=False)]

st.caption(f"{len(vista)} de {len(mios)} movimientos")
tabla = (vista.sort_values("ID_REGISTRO", ascending=False)[
    ["FECHA_VALE", "ID_VALE_REF", "DESCRIPCIÓN_ITEM", "TIPO_MOV", "CANT",
     "CANT_DEVUELTA", "pendiente", "UNIDAD", "ESTADO_RENGLON"]
].rename(columns={
    "FECHA_VALE": "Fecha", "ID_VALE_REF": "Vale", "DESCRIPCIÓN_ITEM": "Material",
    "TIPO_MOV": "Tipo", "CANT": "Retirado", "CANT_DEVUELTA": "Devuelto",
    "pendiente": "Pendiente", "UNIDAD": "Unidad", "ESTADO_RENGLON": "Estado",
}))
st.dataframe(
    estilo.tabla(tabla, {"Estado": estilo.COLORES_RENGLON}),
    hide_index=True, width="stretch", height=380,
)
