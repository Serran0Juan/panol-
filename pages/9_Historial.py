"""Historial de movimientos: registro completo de lo que modificó el stock."""

import datetime as dt

import streamlit as st

import estilo
from auth import current_user, exigir, puede
from sheets_backend import (SUBCATEGORIA_RECARGABLE, devolver_renglon,
                            get_movimientos, hoy, items_recargables,
                            separar_recargables)

usuario = current_user()
if usuario is None:
    st.stop()
exigir("ver_gestion", "No tenés permiso para ver esta sección. "
                      "Consultá lo tuyo en **Mi historial**.")

st.markdown("###### PAÑOL · MANTENIMIENTO")
st.title("Historial de movimientos")
st.caption("Registro de todas las operaciones que modificaron el stock.")

movs = get_movimientos()
if movs.empty:
    st.info("Todavía no hay movimientos registrados.")
    st.stop()

# Las pilas recargables se mueven todos los días y son cientos: si no se
# pueden esconder, tapan los préstamos de herramientas. Tienen su propia
# pantalla, así que acá vienen ocultas de entrada.
if not items_recargables().empty:
    ver_pilas = st.checkbox(
        f"Incluir los movimientos de {SUBCATEGORIA_RECARGABLE.lower()}", value=False,
        help="Tienen su propia sección. Se esconden acá para que no tapen el resto.")
    if not ver_pilas:
        movs = separar_recargables(movs, incluir=False)

# Cuántos días para atrás mira cada opción. None = sin límite.
PERIODOS = {"Todo": None, "Hoy": 0, "Últimos 7 días": 6, "Últimos 30 días": 29,
            "Elegir fechas": "libre"}

f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
with f1:
    periodo = st.selectbox("Período", list(PERIODOS))
with f2:
    tipo = st.selectbox("Tipo", ["Todos"] + sorted(movs["TIPO_MOV"].unique()))
with f3:
    estado = st.selectbox("Estado", ["Todos", "PENDIENTE", "CERRADO"])
with f4:
    q = st.text_input("Buscar material, vale o persona", "")

desde = hasta = None
if periodo == "Elegir fechas":
    rango = st.date_input("Desde / hasta", value=(hoy() - dt.timedelta(days=6), hoy()),
                          max_value=hoy(), format="DD/MM/YYYY")
    # mientras se elige la segunda fecha, el control devuelve una sola
    if len(rango) == 2:
        desde, hasta = rango
elif PERIODOS[periodo] is not None:
    desde, hasta = hoy() - dt.timedelta(days=PERIODOS[periodo]), hoy()

vista = movs
if desde is not None:
    dia = vista["_fecha"].dt.date
    vista = vista[dia.notna() & (dia >= desde) & (dia <= hasta)]
if tipo != "Todos":
    vista = vista[vista["TIPO_MOV"] == tipo]
if estado != "Todos":
    vista = vista[vista["ESTADO_RENGLON"] == estado]
if q.strip():
    t = q.strip()
    vista = vista[
        vista["DESCRIPCIÓN_ITEM"].str.contains(t, case=False, na=False, regex=False)
        | vista["ID_VALE_REF"].str.contains(t, case=False, na=False, regex=False)
        | vista["Receptor / Para Quien"].astype(str).str.contains(t, case=False, na=False, regex=False)
    ]

st.caption(f"{len(vista)} de {len(movs)} registros")

tabla = vista.sort_values("ID_REGISTRO", ascending=False)[
    ["ID_VALE_REF", "_fecha", "DESCRIPCIÓN_ITEM", "TIPO_MOV", "CANT", "CANT_DEVUELTA",
     "pendiente", "UNIDAD", "SECTOR", "Receptor / Para Quien", "REGISTRADO_POR",
     "ESTADO_RENGLON", "OBSERVACIONES"]
].rename(columns={
    "ID_VALE_REF": "Vale", "_fecha": "Fecha y hora", "DESCRIPCIÓN_ITEM": "Material",
    "TIPO_MOV": "Tipo", "CANT": "Entregado", "CANT_DEVUELTA": "Devuelto",
    "pendiente": "Pendiente", "UNIDAD": "Unidad", "SECTOR": "Sector",
    "Receptor / Para Quien": "Para quién", "REGISTRADO_POR": "Registrado por",
    "ESTADO_RENGLON": "Estado", "OBSERVACIONES": "Observaciones",
})

st.dataframe(
    estilo.tabla(tabla, {"Estado": estilo.COLORES_RENGLON,
                         "Sector": estilo.COLORES_SECTOR}),
    hide_index=True, width="stretch", height=480)

st.download_button("Descargar CSV", tabla.to_csv(index=False).encode("utf-8-sig"),
                   file_name="historial_panol.csv", mime="text/csv")

if not puede("registrar_movimiento"):
    st.stop()

with st.expander("Registrar la devolución de un sobrante"):
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
