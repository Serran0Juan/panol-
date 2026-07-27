"""Dashboard: estado del stock, faltantes, préstamos abiertos y reclamos."""

import pandas as pd
import plotly.express as px
import streamlit as st

from auth import current_user
from sheets_backend import get_items, get_reclamos, get_registro, get_vales

if current_user() is None:
    st.stop()

st.title("📊 Dashboard")

items = get_items()
vales = get_vales()
reclamos = get_reclamos()

if items.empty:
    st.info("Todavía no hay productos cargados.")
    st.stop()

sin_stock = int((items["estado"] == "🔴 Sin stock").sum())
minimo = int((items["estado"] == "🟡 Mínimo").sum())
prestamos_abiertos = (
    vales[(vales["TIPO MOVIMIENTO"] == "PRESTADO") & (vales["ESTADO VALE"].str.upper() == "ABIERTO")]
    if not vales.empty else pd.DataFrame()
)
reclamos_abiertos = (
    reclamos[reclamos["ESTADO"].str.upper() == "ABIERTO"] if not reclamos.empty else pd.DataFrame()
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Productos", len(items))
k2.metric("Sin stock 🔴", sin_stock)
k3.metric("En mínimo 🟡", minimo)
k4.metric("Préstamos abiertos", len(prestamos_abiertos))
k5.metric("Reclamos abiertos", len(reclamos_abiertos))

valor = items["valor"].sum()
sin_ubicacion = int((items["ubicacion"].str.strip() == "").sum())
v1, v2 = st.columns(2)
v1.metric("Valor total del inventario", f"${valor:,.0f}".replace(",", "."))
v2.metric("Productos sin ubicación asignada", sin_ubicacion)

col1, col2 = st.columns(2)
with col1:
    por_categoria = (
        items.groupby(["categoria", "estado"], as_index=False)
        .size().rename(columns={"size": "cantidad"})
    )
    colores = {"🟢 OK": "#2ecc71", "🟡 Mínimo": "#f1c40f", "🔴 Sin stock": "#e74c3c"}
    fig = px.bar(por_categoria, x="categoria", y="cantidad", color="estado",
                 color_discrete_map=colores, title="Productos por categoría y estado",
                 labels={"categoria": "Categoría", "cantidad": "Productos", "estado": "Estado"})
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    conteo = items["estado"].value_counts().reset_index()
    conteo.columns = ["estado", "cantidad"]
    fig2 = px.pie(conteo, names="estado", values="cantidad", hole=0.45,
                  color="estado", color_discrete_map=colores, title="Salud general del stock")
    fig2.update_layout(height=400, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("🔴 Sin stock — reponer con prioridad")
criticos = items[items["estado"] == "🔴 Sin stock"].sort_values("descripcion")
if criticos.empty:
    st.success("No hay productos sin stock.")
else:
    st.dataframe(
        criticos[["id", "descripcion", "categoria", "ubicacion", "stock_minimo", "unidad"]]
        .rename(columns={"id": "N°", "descripcion": "Producto", "categoria": "Categoría",
                         "ubicacion": "Ubicación", "stock_minimo": "Mínimo", "unidad": "Unidad"}),
        hide_index=True, use_container_width=True, height=260,
    )

st.subheader("🟡 En el mínimo — conviene reponer")
bajos = items[items["estado"] == "🟡 Mínimo"].sort_values("descripcion")
if bajos.empty:
    st.success("No hay productos en el mínimo.")
else:
    st.dataframe(
        bajos[["id", "descripcion", "categoria", "ubicacion", "stock_actual", "stock_minimo", "unidad"]]
        .rename(columns={"id": "N°", "descripcion": "Producto", "categoria": "Categoría",
                         "ubicacion": "Ubicación", "stock_actual": "Stock", "stock_minimo": "Mínimo",
                         "unidad": "Unidad"}),
        hide_index=True, use_container_width=True, height=260,
    )

if not prestamos_abiertos.empty:
    st.subheader("⏳ Préstamos sin devolver")
    st.dataframe(
        prestamos_abiertos[["ID VALE", "FECHA HORA", "Receptor / Para Quien", "SECTOR", "ÁREA / SALA"]]
        .rename(columns={"ID VALE": "Vale", "FECHA HORA": "Fecha",
                         "Receptor / Para Quien": "Prestado a", "SECTOR": "Sector",
                         "ÁREA / SALA": "Área"}),
        hide_index=True, use_container_width=True,
    )

registro = get_registro()
if not registro.empty:
    st.subheader("📈 Productos más movidos")
    top = (registro.groupby("DESCRIPCIÓN_ITEM", as_index=False)["CANT"].sum()
           .sort_values("CANT", ascending=False).head(15))
    fig3 = px.bar(top, x="CANT", y="DESCRIPCIÓN_ITEM", orientation="h",
                  labels={"CANT": "Unidades movidas", "DESCRIPCIÓN_ITEM": ""})
    fig3.update_layout(height=450, margin=dict(l=20, r=20, t=20, b=20),
                       yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig3, use_container_width=True)
