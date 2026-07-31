"""Tablero de jefatura: cómo viene el mantenimiento, en números."""

import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

import estilo
from auth import current_user, exigir
from estilo import AMBAR, AZUL, ROJO, VERDE  # noqa: F401  (los usan los gráficos)
from sheets_backend import (ESTADOS_ABIERTOS, ahora, carga_por_persona, get_ordenes,
                            hoy, indicadores_mantenimiento, parse_fecha)

usuario = current_user()
if usuario is None:
    st.stop()
exigir("ver_gestion")

st.markdown("###### MANTENIMIENTO · JEFATURA")
st.title("Tablero de jefatura")
st.caption("Estado del mantenimiento correctivo, cumplimiento y reparto del trabajo.")

ordenes = get_ordenes()
if ordenes.empty:
    st.info("Todavía no hay órdenes de trabajo cargadas.")
    st.stop()

# ───────────────────────────────────── período
c_periodo, _ = st.columns([1, 3])
with c_periodo:
    periodo = st.selectbox("Período", ["Últimos 30 días", "Últimos 90 días",
                                       "Este año", "Todo"], index=0)

dias = {"Últimos 30 días": 30, "Últimos 90 días": 90}.get(periodo)
vista = ordenes
if dias:
    corte = ahora() - dt.timedelta(days=dias)
    vista = ordenes[ordenes["FECHA_ALTA"].apply(
        lambda f: (parse_fecha(f) or dt.datetime.min) >= corte)]
elif periodo == "Este año":
    vista = ordenes[ordenes["FECHA_ALTA"].apply(
        lambda f: (parse_fecha(f) or dt.datetime.min).year == hoy().year)]

ind = indicadores_mantenimiento(vista)


# ───────────────────────────────────── indicadores
cumplimiento = ind["cumplimiento"]
estilo.fila_indicadores([
    estilo.indicador("Órdenes del período", ind["total"], "dadas de alta"),
    estilo.indicador("Abiertas", ind["abiertas"], "sin resolver todavía"),
    estilo.indicador("Vencidas", ind["vencidas"], "pasaron su plazo",
                     estilo.COLORES_PRIORIDAD["URGENTE"]),
    estilo.indicador("Sin asignar", ind["sin_asignar"], "sin responsable",
                     estilo.COLORES_PRIORIDAD["ALTA"]),
])
estilo.fila_indicadores([
    estilo.indicador("Resueltas", ind["resueltas"], "en el período"),
    estilo.indicador("Demora promedio",
                     f"{ind['dias_promedio']:g} d" if ind["dias_promedio"] is not None else "—",
                     "del alta al cierre"),
    estilo.indicador("Cumplimiento del plazo",
                     f"{cumplimiento}%" if cumplimiento is not None else "—",
                     "resueltas antes de vencer",
                     None if cumplimiento is None or cumplimiento >= 80
                     else estilo.COLORES_PRIORIDAD["ALTA"]),
    estilo.indicador("Horas trabajadas", f"{ind['horas_cerradas']:g}",
                     "según los cierres"),
])

if ind["cumplimiento"] is not None and ind["cumplimiento"] < 70:
    st.warning(f"Solo el {ind['cumplimiento']}% de las órdenes se resolvió dentro del "
               "plazo comprometido. Puede ser falta de gente, plazos poco realistas "
               "o prioridades mal cargadas.")

st.divider()

COLOR_ESTADO = {"SOLICITADA": "#94A3B8", "ASIGNADA": AZUL, "EN CURSO": "#2C7BC0",
                "PAUSADA": AMBAR, "RESUELTA": VERDE, "ANULADA": "#CBD5E1"}

g1, g2 = st.columns(2)

with g1:
    por_estado = vista["ESTADO"].value_counts().reset_index()
    por_estado.columns = ["estado", "cantidad"]
    fig = px.pie(por_estado, names="estado", values="cantidad", hole=.45,
                 color="estado", color_discrete_map=COLOR_ESTADO,
                 title="Órdenes por estado")
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")

with g2:
    abiertas = vista[vista["ESTADO"].isin(ESTADOS_ABIERTOS)]
    if abiertas.empty:
        st.info("No hay órdenes abiertas en el período.")
    else:
        por_sector = (abiertas.assign(
            sector=abiertas["SECTOR_ASIGNADO"].replace("", "Sin asignar"))
            .groupby("sector", as_index=False).size()
            .rename(columns={"size": "abiertas"}).sort_values("abiertas", ascending=False))
        fig2 = px.bar(por_sector, x="sector", y="abiertas",
                      title="Órdenes abiertas por sector",
                      labels={"sector": "Sector", "abiertas": "Órdenes"})
        fig2.update_traces(marker_color=AZUL)
        fig2.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig2, width="stretch")

# ───────────────────────────────────── evolución
altas = vista["FECHA_ALTA"].apply(parse_fecha)
cierres = vista["FECHA_CIERRE"].apply(parse_fecha)
serie = []
for f in altas.dropna():
    serie.append({"mes": f.strftime("%Y-%m"), "tipo": "Ingresadas"})
for f in cierres.dropna():
    serie.append({"mes": f.strftime("%Y-%m"), "tipo": "Resueltas"})

if serie:
    evolucion = (pd.DataFrame(serie).groupby(["mes", "tipo"], as_index=False)
                 .size().rename(columns={"size": "cantidad"}).sort_values("mes"))
    fig3 = px.bar(evolucion, x="mes", y="cantidad", color="tipo", barmode="group",
                  title="Ingresadas vs. resueltas por mes",
                  color_discrete_map={"Ingresadas": AMBAR, "Resueltas": VERDE},
                  labels={"mes": "Mes", "cantidad": "Órdenes", "tipo": ""})
    fig3.update_layout(height=340, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig3, width="stretch")

# ───────────────────────────────────── vencidas
vencidas = vista[vista["vencida"]]
if not vencidas.empty:
    st.subheader(f"Órdenes vencidas ({len(vencidas)})")
    st.dataframe(
        vencidas.sort_values("dias_para_vencer")[
            ["ID_OT", "AREA", "DESCRIPCION", "PRIORIDAD", "SECTOR_ASIGNADO",
             "ASIGNADO_A", "ESTADO", "FECHA_COMPROMISO", "dias_para_vencer"]
        ].rename(columns={"ID_OT": "OT", "AREA": "Lugar", "DESCRIPCION": "Problema",
                          "PRIORIDAD": "Prioridad", "SECTOR_ASIGNADO": "Sector",
                          "ASIGNADO_A": "Responsable", "ESTADO": "Estado",
                          "FECHA_COMPROMISO": "Vencía", "dias_para_vencer": "Días de atraso"}),
        hide_index=True, width="stretch",
    )

# ───────────────────────────────────── carga
carga = carga_por_persona(vista)
if not carga.empty:
    st.subheader("Carga de trabajo pendiente")
    fig4 = px.bar(carga, x="horas", y="persona", orientation="h",
                  labels={"horas": "Horas estimadas pendientes", "persona": ""},
                  title="Horas pendientes por responsable")
    fig4.update_traces(marker_color=AZUL)
    fig4.update_layout(height=max(260, 46 * len(carga)),
                       margin=dict(l=20, r=20, t=50, b=20),
                       yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig4, width="stretch")

# ───────────────────────────────────── reporte
st.divider()
st.subheader("Reporte")
st.caption("Descargá el detalle para presentarlo o seguir trabajándolo en Excel.")

reporte = vista[
    ["ID_OT", "FECHA_ALTA", "AREA", "DESCRIPCION", "PRIORIDAD", "SECTOR_ASIGNADO",
     "ASIGNADO_A", "ESTADO", "FECHA_COMPROMISO", "FECHA_PROGRAMADA", "FECHA_CIERRE",
     "HORAS_ESTIMADAS", "HORAS", "TRABAJO_REALIZADO", "CAUSA", "SOLICITANTE"]
].rename(columns={
    "ID_OT": "OT", "FECHA_ALTA": "Alta", "AREA": "Lugar", "DESCRIPCION": "Problema",
    "PRIORIDAD": "Prioridad", "SECTOR_ASIGNADO": "Sector", "ASIGNADO_A": "Responsable",
    "ESTADO": "Estado", "FECHA_COMPROMISO": "Vence", "FECHA_PROGRAMADA": "Programada",
    "FECHA_CIERRE": "Cierre", "HORAS_ESTIMADAS": "Horas est.", "HORAS": "Horas reales",
    "TRABAJO_REALIZADO": "Trabajo realizado", "CAUSA": "Causa", "SOLICITANTE": "Pidió",
})

st.download_button(f"Descargar el reporte ({periodo})",
                   reporte.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"mantenimiento_{hoy():%Y-%m-%d}.csv",
                   mime="text/csv", type="primary")

with st.expander("Ver el detalle completo"):
    st.dataframe(reporte, hide_index=True, width="stretch", height=420)
