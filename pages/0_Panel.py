"""Panel de control del pañol: la pantalla de entrada de quien lo gestiona."""

import pandas as pd
import plotly.express as px
import streamlit as st

import estilo
from auth import current_user, exigir
from sheets_backend import (DIAS_PARA_DEMORA, dias_desde, estado_movimiento, get_items,
                            get_movimientos, get_reclamos, get_vales, hoy)

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

sin_stock = int((items["estado"] == "Sin stock").sum())
en_minimo = int((items["estado"] == "Mínimo").sum())
abiertos = vales[vales["ESTADO VALE"].str.upper() == "ABIERTO"] if not vales.empty else pd.DataFrame()
pendientes = reclamos[reclamos["ESTADO"].str.upper() == "ABIERTO"] if not reclamos.empty else pd.DataFrame()

dia = hoy().strftime("%Y-%m-%d")
movs_hoy = (movimientos[movimientos["FECHA_VALE"].astype(str).str.startswith(dia)]
            if not movimientos.empty else pd.DataFrame())


# ───────────────────────────────────────────────── indicadores
def money(n: float) -> str:
    """Monto corto, para que entre en la tarjeta: 208.342.653 -> $208,3 M.

    El monto completo va en la línea de abajo, con `estilo.pesos()`.
    """
    if n >= 1_000_000:
        return f"${n / 1_000_000:,.1f} M".replace(",", "X").replace(".", ",").replace("X", ".")
    if n >= 1_000:
        return f"${n / 1_000:,.0f} mil".replace(",", ".")
    return estilo.pesos(n)


def miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def porcentaje(parte: int, total: int) -> str:
    return f"{parte / total * 100:.0f}%" if total else "0%"


valor = items["valor"].sum()
sin_ubicacion = int((items["ubicacion"].str.strip() == "").sum())
demorados = 0
if not abiertos.empty:
    demorados = int((abiertos["FECHA HORA"].apply(dias_desde) >= DIAS_PARA_DEMORA).sum())

# Cada número lleva abajo una línea que dice si está bien o mal. El número solo
# no alcanza: "154" no significa nada hasta saber que es un tercio del catálogo.
st.markdown("##### Estado del inventario")
estilo.fila_indicadores([
    estilo.indicador("Materiales", miles(len(items)), "en el catálogo"),
    estilo.indicador("Sin stock", miles(sin_stock),
                     f"{porcentaje(sin_stock, len(items))} del catálogo",
                     estilo.COLORES_STOCK["Sin stock"]),
    estilo.indicador("En mínimo", miles(en_minimo), "hay que reponer",
                     estilo.COLORES_STOCK["Mínimo"]),
    estilo.indicador("Sin ubicación", miles(sin_ubicacion),
                     f"{porcentaje(sin_ubicacion, len(items))} sin estantería asignada",
                     estilo.COLORES_STOCK["Mínimo"]),
])

st.markdown("##### Movimiento y pendientes")
estilo.fila_indicadores([
    estilo.indicador("Movimientos de hoy", miles(len(movs_hoy)), "renglones registrados"),
    estilo.indicador("Préstamos abiertos", miles(len(abiertos)),
                     f"{demorados} con más de {DIAS_PARA_DEMORA} días" if demorados
                     else "ninguno demorado",
                     estilo.COLORES_STOCK["Sin stock"] if demorados else None),
    estilo.indicador("Solicitudes", miles(len(pendientes)), "pedidos sin responder",
                     estilo.COLORES_STOCK["Mínimo"]),
    estilo.indicador("Valor del stock", money(valor), estilo.pesos(valor)),
])

st.divider()

# ───────────────────────────────────────────────── movimientos recientes
st.subheader("Movimientos recientes")
st.caption("Últimas operaciones que modificaron el stock.")
if movimientos.empty:
    st.info("Todavía no se registró ningún movimiento.")
else:
    recientes = movimientos.sort_values("ID_REGISTRO", ascending=False).head(15).copy()
    recientes["estado"] = estado_movimiento(recientes)
    tabla = (recientes[["FECHA_VALE", "ID_VALE_REF", "DESCRIPCIÓN_ITEM", "TIPO_MOV", "estado",
                        "CANT", "UNIDAD", "SECTOR", "Receptor / Para Quien", "REGISTRADO_POR"]]
             .rename(columns={"FECHA_VALE": "Fecha", "ID_VALE_REF": "Vale",
                              "DESCRIPCIÓN_ITEM": "Material", "TIPO_MOV": "Tipo",
                              "estado": "Estado", "CANT": "Cant.", "UNIDAD": "Un.",
                              "SECTOR": "Sector", "Receptor / Para Quien": "Para quién",
                              "REGISTRADO_POR": "Registrado por"}))
    # las celdas de Estado y Sector van pintadas: ahora que no hay emojis, el
    # color es lo que hace que se lean de un vistazo
    st.dataframe(
        estilo.tabla(tabla, {"Estado": estilo.COLORES_RENGLON,
                             "Sector": estilo.COLORES_SECTOR}),
        hide_index=True, width="stretch", height=420,
    )

# ───────────────────────────────────────────────── préstamos demorados
if not abiertos.empty:
    demora = abiertos.copy()
    demora["dias"] = demora["FECHA HORA"].apply(dias_desde)
    atrasados = demora[demora["dias"] >= DIAS_PARA_DEMORA].sort_values("dias", ascending=False)
    if not atrasados.empty:
        st.subheader(f"Préstamos demorados (más de {DIAS_PARA_DEMORA} días)")
        tabla_demora = (atrasados[["ID VALE", "Receptor / Para Quien", "SECTOR",
                                   "dias", "FECHA HORA"]]
                        .rename(columns={"ID VALE": "Vale",
                                         "Receptor / Para Quien": "Prestado a",
                                         "SECTOR": "Sector", "dias": "Días",
                                         "FECHA HORA": "Desde"}))
        st.dataframe(
            estilo.tabla(tabla_demora, {"Sector": estilo.COLORES_SECTOR}),
            hide_index=True, width="stretch",
        )

# ───────────────────────────────────────────────── indicadores gráficos
st.divider()
st.subheader("Indicadores")

LAYOUT = dict(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
              font=dict(size=13), separators=",.")

g1, g2 = st.columns([1, 1.4])
with g1:
    st.markdown("##### Salud del stock")
    st.caption(f"{porcentaje(sin_stock + en_minimo, len(items))} del catálogo "
               "necesita atención.")
    conteo = items["estado"].value_counts().reset_index()
    conteo.columns = ["estado", "cantidad"]
    # En las porciones muy finas plotly achica el porcentaje hasta dejarlo
    # ilegible; ahí conviene no escribir nada y que lo diga la referencia.
    conteo["etiqueta"] = [f"{c / len(items) * 100:.0f}%" if c / len(items) >= 0.05 else ""
                          for c in conteo["cantidad"]]
    fig = px.pie(conteo, names="estado", values="cantidad", hole=0.62, color="estado",
                 color_discrete_map=estilo.mapa_grafico(conteo["estado"],
                                                        estilo.COLORES_STOCK))
    # y las que sí se escriben van derechas: por defecto las dibuja curvadas
    fig.update_traces(text=conteo["etiqueta"], textinfo="text", textfont_size=15,
                      textposition="inside", insidetextorientation="horizontal",
                      hovertemplate="%{label}: %{value} materiales<extra></extra>")
    fig.update_layout(height=300, legend=dict(orientation="h", y=-0.1),
                      annotations=[dict(text=f"<b>{len(items)}</b><br>materiales",
                                        showarrow=False, font=dict(size=15))],
                      **LAYOUT)
    st.plotly_chart(fig, width="stretch")

with g2:
    st.markdown("##### Cómo está cada sector")
    st.caption("Cuántos materiales de cada sector están sin stock o en el mínimo.")
    por_sector = (items.groupby(["categoria", "estado"], as_index=False)
                  .size().rename(columns={"size": "cantidad"}))
    fig2 = px.bar(por_sector, y="categoria", x="cantidad", color="estado",
                  orientation="h", color_discrete_map=estilo.mapa_grafico(
                      por_sector["estado"], estilo.COLORES_STOCK),
                  category_orders={"estado": ["OK", "Mínimo", "Sin stock"]},
                  labels={"categoria": "", "cantidad": "", "estado": "Estado"})
    # sin título en el eje: lo que se cuenta ya lo dice la línea de arriba, y
    # además se le montaba encima a la referencia
    fig2.update_layout(height=300, legend=dict(orientation="h", y=-0.18, title=""),
                       xaxis=dict(gridcolor="#EDF1F6"), **LAYOUT)
    st.plotly_chart(fig2, width="stretch")

if not movimientos.empty:
    consumos = movimientos[movimientos["TIPO_MOV"] == "CONSUMO"]
    if not consumos.empty:
        st.markdown("##### Materiales más consumidos")
        st.caption("Lo que más sale del pañol, con el color del sector que lo pidió.")
        top = (consumos.groupby(["DESCRIPCIÓN_ITEM", "SECTOR"], as_index=False)["CANT"]
               .sum().sort_values("CANT", ascending=False).head(15))
        fig3 = px.bar(top, x="CANT", y="DESCRIPCIÓN_ITEM", color="SECTOR",
                      orientation="h", color_discrete_map=estilo.mapa_grafico(
                          top["SECTOR"], estilo.COLORES_SECTOR),
                      labels={"CANT": "Unidades", "DESCRIPCIÓN_ITEM": "", "SECTOR": "Sector"})
        # la altura acompaña a la cantidad de barras: con tres materiales, una
        # altura fija deja unos ladrillos enormes
        fig3.update_layout(height=max(220, 34 * len(top) + 110),
                           yaxis=dict(autorange="reversed"),
                           xaxis=dict(gridcolor="#EDF1F6"),
                           legend=dict(orientation="h", y=-0.12, title=""), **LAYOUT)
        st.plotly_chart(fig3, width="stretch")
