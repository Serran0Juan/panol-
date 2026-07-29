"""Historial de movimientos: registro completo de lo que modificó el stock."""

import streamlit as st

from auth import current_user, puede_gestionar
from sheets_backend import devolver_renglon, get_movimientos

usuario = current_user()
if usuario is None:
    st.stop()
if not puede_gestionar(usuario):
    st.error("No tenés permiso para ver esta sección. Consultá lo tuyo en **Mi historial**.")
    st.stop()

st.markdown("###### PAÑOL · MANTENIMIENTO")
st.title("Historial de movimientos")
st.caption("Registro de todas las operaciones que modificaron el stock.")

movs = get_movimientos()
if movs.empty:
    st.info("Todavía no hay movimientos registrados.")
    st.stop()

f1, f2, f3 = st.columns([1, 1, 2])
with f1:
    tipo = st.selectbox("Tipo", ["Todos"] + sorted(movs["TIPO_MOV"].unique()))
with f2:
    estado = st.selectbox("Estado", ["Todos", "PENDIENTE", "CERRADO"])
with f3:
    q = st.text_input("Buscar material, vale o persona", "")

vista = movs
if tipo != "Todos":
    vista = vista[vista["TIPO_MOV"] == tipo]
if estado != "Todos":
    vista = vista[vista["ESTADO_RENGLON"] == estado]
if q.strip():
    t = q.strip()
    vista = vista[
        vista["DESCRIPCIÓN_ITEM"].str.contains(t, case=False, na=False)
        | vista["ID_VALE_REF"].str.contains(t, case=False, na=False)
        | vista["Receptor / Para Quien"].astype(str).str.contains(t, case=False, na=False)
    ]

st.caption(f"{len(vista)} de {len(movs)} registros")

tabla = vista.sort_values("ID_REGISTRO", ascending=False)[
    ["ID_VALE_REF", "FECHA_VALE", "DESCRIPCIÓN_ITEM", "TIPO_MOV", "CANT", "CANT_DEVUELTA",
     "pendiente", "UNIDAD", "SECTOR", "Receptor / Para Quien", "REGISTRADO_POR",
     "ESTADO_RENGLON", "OBSERVACIONES"]
].rename(columns={
    "ID_VALE_REF": "Vale", "FECHA_VALE": "Fecha y hora", "DESCRIPCIÓN_ITEM": "Material",
    "TIPO_MOV": "Tipo", "CANT": "Entregado", "CANT_DEVUELTA": "Devuelto",
    "pendiente": "Pendiente", "UNIDAD": "Unidad", "SECTOR": "Sector",
    "Receptor / Para Quien": "Para quién", "REGISTRADO_POR": "Registrado por",
    "ESTADO_RENGLON": "Estado", "OBSERVACIONES": "Observaciones",
})

st.dataframe(tabla, hide_index=True, use_container_width=True, height=480)

st.download_button("⬇️ Descargar CSV", tabla.to_csv(index=False).encode("utf-8-sig"),
                   file_name="historial_panol.csv", mime="text/csv")

with st.expander("↩️ Registrar la devolución de un sobrante"):
    st.caption("Para cuando traen de vuelta parte de algo ya entregado.")
    devolvibles = movs[(movs["CANT"] - movs["CANT_DEVUELTA"]) > 0]
    if devolvibles.empty:
        st.info("No hay renglones con cantidad pendiente de devolver.")
    else:
        op = {f"{r.ID_VALE_REF} · {r.DESCRIPCIÓN_ITEM} — quedan "
              f"{r.CANT - r.CANT_DEVUELTA:g} {r.UNIDAD}": r.ID_REGISTRO
              for r in devolvibles.itertuples()}
        sel = st.selectbox("Renglón", list(op.keys()))
        reng = movs[movs["ID_REGISTRO"] == op[sel]].iloc[0]
        maximo = float(reng["CANT"] - reng["CANT_DEVUELTA"])
        cant = st.number_input("Cantidad devuelta", min_value=0.01, max_value=maximo,
                               value=maximo, step=1.0)
        if st.button("Registrar devolución", type="primary"):
            devolver_renglon(op[sel], cant)
            st.success("Devolución registrada. El stock se repone solo.")
            st.rerun()
