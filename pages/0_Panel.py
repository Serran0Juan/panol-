"""Panel de control del pañol: la pantalla de entrada de quien lo gestiona."""

import pandas as pd
import plotly.express as px
import streamlit as st

from auth import current_user, exigir
from sheets_backend import (DIAS_PARA_DEMORA, dias_desde, get_items, get_movimientos,
                            get_reclamos, get_vales)

usuario = current_user()
if usuario is None:
    st.stop()
exigir("ver_gestion")

st.markdown("###### PAÑOL · MANTENIMIENTO")
st.title("Panel de control")
st.caption("Actividad registrada, solicitudes y estado del inventario.")

items = get_items()
movimientos = get_movimientos()
vales = get_vales()
reclamos = get_reclamos()

if items.empty:
    st.info("Todavía no hay productos cargados.")
    st.stop()

COLORES = {"🟢 OK": "#2ecc71", "🟡 Mínimo": "#f1c40f", "🔴 Sin stock": "#e74c3c"}

sin_stock = int((items["estado"] == "🔴 Sin stock").sum())
en_minimo = int((items["estado"] == "🟡 Mínimo").sum())
abiertos = vales[vales["ESTADO VALE"].str.upper() == "ABIERTO"] if not vales.empty else pd.DataFrame()
pendientes = reclamos[reclamos["ESTADO"].str.upper() == "ABIERTO"] if not reclamos.empty else pd.DataFrame()

hoy = pd.Timestamp.now().strftime("%Y-%m-%d")
movs_hoy = (movimientos[movimientos["FECHA_VALE"].astype(str).str.startswith(hoy)]
            if not movimientos.empty else pd.DataFrame())

# ───────────────────────────────────────────────── indicadores
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Productos activos", f"{len(items):,}".replace(",", "."))
k2.metric("Movimientos hoy", len(movs_hoy))
k3.metric("Solicitudes pendientes", len(pendientes))
k4.metric("Sin stock 🔴", sin_stock)
k5.metric("En mínimo 🟡", en_minimo)

valor = items["valor"].sum()
sin_ubicacion = int((items["ubicacion"].str.strip() == "").sum())
v1, v2, v3 = st.columns(3)
v1.metric("Valor del inventario", f"${valor:,.0f}".replace(",", "."))
v2.metric("Préstamos abiertos", len(abiertos))
v3.metric("Sin ubicación asignada", sin_ubicacion)

st.divider()

# ───────────────────────────────────────────────── movimientos recientes
st.subheader("Movimientos recientes")
st.caption("Últimas operaciones que modificaron el stock.")
if movimientos.empty:
    st.info("Todavía no se registró ningún movimiento.")
else:
    recientes = movimientos.sort_values("ID_REGISTRO", ascending=False).head(15)
    st.dataframe(
        recientes[["FECHA_VALE", "ID_VALE_REF", "DESCRIPCIÓN_ITEM", "TIPO_MOV",
                   "CANT", "UNIDAD", "SECTOR", "Receptor / Para Quien", "REGISTRADO_POR"]]
        .rename(columns={"FECHA_VALE": "Fecha", "ID_VALE_REF": "Vale",
                         "DESCRIPCIÓN_ITEM": "Material", "TIPO_MOV": "Tipo",
                         "CANT": "Cant.", "UNIDAD": "Un.", "SECTOR": "Sector",
                         "Receptor / Para Quien": "Para quién",
                         "REGISTRADO_POR": "Registrado por"}),
        hide_index=True, use_container_width=True, height=420,
    )

# ───────────────────────────────────────────────── préstamos demorados
if not abiertos.empty:
    demora = abiertos.copy()
    demora["dias"] = demora["FECHA HORA"].apply(dias_desde)
    demorados = demora[demora["dias"] >= DIAS_PARA_DEMORA].sort_values("dias", ascending=False)
    if not demorados.empty:
        st.subheader(f"⏰ Préstamos demorados (más de {DIAS_PARA_DEMORA} días)")
        st.dataframe(
            demorados[["ID VALE", "Receptor / Para Quien", "SECTOR", "dias", "FECHA HORA"]]
            .rename(columns={"ID VALE": "Vale", "Receptor / Para Quien": "Prestado a",
                             "SECTOR": "Sector", "dias": "Días", "FECHA HORA": "Desde"}),
            hide_index=True, use_container_width=True,
        )

# ───────────────────────────────────────────────── indicadores gráficos
st.divider()
st.subheader("Indicadores")

g1, g2 = st.columns(2)
with g1:
    por_categoria = (items.groupby(["categoria", "estado"], as_index=False)
                     .size().rename(columns={"size": "cantidad"}))
    fig = px.bar(por_categoria, x="categoria", y="cantidad", color="estado",
                 color_discrete_map=COLORES, title="Productos por categoría y estado",
                 labels={"categoria": "Categoría", "cantidad": "Productos", "estado": "Estado"})
    fig.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

with g2:
    conteo = items["estado"].value_counts().reset_index()
    conteo.columns = ["estado", "cantidad"]
    fig2 = px.pie(conteo, names="estado", values="cantidad", hole=0.45,
                  color="estado", color_discrete_map=COLORES, title="Salud general del stock")
    fig2.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig2, use_container_width=True)

if not movimientos.empty:
    consumos = movimientos[movimientos["TIPO_MOV"] == "CONSUMO"]
    if not consumos.empty:
        top = (consumos.groupby("DESCRIPCIÓN_ITEM", as_index=False)["CANT"].sum()
               .sort_values("CANT", ascending=False).head(15))
        fig3 = px.bar(top, x="CANT", y="DESCRIPCIÓN_ITEM", orientation="h",
                      title="Materiales más consumidos",
                      labels={"CANT": "Unidades", "DESCRIPCIÓN_ITEM": ""})
        fig3.update_layout(height=450, margin=dict(l=20, r=20, t=50, b=20),
                           yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig3, use_container_width=True)
