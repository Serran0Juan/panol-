"""Pilas recargables: entrega, devolución y quién tiene qué.

Las pilas se prestan y vuelven, igual que una herramienta, pero son cientos y
se mueven todos los días. Mezcladas con el resto de los vales tapan todo, así
que tienen su propia pantalla.

Los movimientos se guardan en las mismas tablas que el resto (`Vales APP` y
`Registro APP`): el stock de la planilla se calcula con fórmulas que suman ahí,
y si las pilas fueran a otra tabla su stock dejaría de calcularse solo. Lo que
cambia es la pantalla, no dónde viven los datos.

Qué material es "pila recargable" se define en la planilla, escribiendo
`Pilas recargables` en la columna Subcategoria. Ver SUBCATEGORIA_RECARGABLE.
"""

import pandas as pd
import streamlit as st

import estilo
from auth import current_user, exigir, puede
from sheets_backend import (DIAS_PARA_DEMORA_RECARGABLE, SUBCATEGORIA_RECARGABLE,
                            devolver_renglon, estado_movimiento, get_movimientos,
                            get_parametros, items_recargables, prestamos_por_persona,
                            registrar_vale, separar_recargables)

usuario = current_user()
if usuario is None:
    st.stop()
exigir("ver_gestion", "No tenés permiso para ver esta sección.")

st.markdown("###### PAÑOL · RECARGABLES")
st.title("Pilas recargables")
st.caption("Se entregan y vuelven. Acá está solo lo de pilas, separado del "
           "movimiento del resto del pañol.")

pilas = items_recargables()
if pilas.empty:
    st.warning(
        "Todavía no hay ningún material marcado como recargable.\n\n"
        f"Para que aparezca acá, escribí **{SUBCATEGORIA_RECARGABLE}** en la "
        "columna **Subcategoria** de la hoja Inventario, en las filas de las "
        "pilas. La app las toma de ahí, así que no hace falta tocar nada más.")
    st.stop()

movs = separar_recargables(get_movimientos(), incluir=True)
afuera = prestamos_por_persona(solo_recargables=True)

# ───────────────────────────────────────────────── indicadores
en_pañol = pilas["stock_actual"].sum()
prestadas = afuera["pendiente"].sum() if not afuera.empty else 0
demoradas = afuera[afuera["dias"] >= DIAS_PARA_DEMORA_RECARGABLE] if not afuera.empty \
    else pd.DataFrame()

estilo.fila_indicadores([
    estilo.indicador("Tipos de pila", len(pilas), "materiales marcados"),
    estilo.indicador("En el pañol", f"{en_pañol:g}", "disponibles para entregar"),
    estilo.indicador("Prestadas", f"{prestadas:g}", "sin devolver todavía",
                     estilo.COLORES_STOCK["Mínimo"] if prestadas else None),
    estilo.indicador("Demoradas", len(demoradas),
                     f"más de {DIAS_PARA_DEMORA_RECARGABLE} días",
                     estilo.COLORES_STOCK["Sin stock"]),
])

st.divider()

tab_quien, tab_entregar, tab_devolver, tab_historial = st.tabs(
    ["Quién tiene", "Entregar", "Registrar devolución", "Historial"])

# ═══════════════════════════════════════════════ quién tiene qué
with tab_quien:
    if afuera.empty:
        st.success("No hay pilas prestadas. Están todas en el pañol.")
    else:
        st.caption("Agrupado por persona y por tipo de pila. Lo más viejo, arriba.")
        tabla = afuera.rename(columns={
            "persona": "Quién", "sector": "Sector", "material": "Pila",
            "pendiente": "Sin devolver", "unidad": "Un.", "dias": "Días",
            "vales": "Vales"})
        st.dataframe(
            estilo.tabla(tabla, {"Sector": estilo.COLORES_SECTOR}),
            hide_index=True, width="stretch", height=380,
        )
        st.download_button("Descargar CSV",
                           tabla.to_csv(index=False).encode("utf-8-sig"),
                           file_name="pilas_prestadas.csv", mime="text/csv")

        if not demoradas.empty:
            st.warning(f"{len(demoradas)} entrega(s) llevan más de "
                       f"{DIAS_PARA_DEMORA_RECARGABLE} días sin volver.")

# ═══════════════════════════════════════════════ entregar
with tab_entregar:
    if not puede("registrar_movimiento"):
        st.info("Tenés acceso de solo lectura: podés ver quién tiene pilas, "
                "pero no registrar entregas.")
    else:
        if "carrito_pilas" not in st.session_state:
            st.session_state["carrito_pilas"] = []

        sectores = get_parametros().get("SECTOR", []) or ["MANTENIMIENTO"]

        st.subheader("1. ¿Para quién es?")
        c1, c2, c3 = st.columns(3)
        with c1:
            receptor = st.text_input("Nombre y apellido *", key="pil_receptor")
        with c2:
            sector = st.selectbox("Sector", sectores, key="pil_sector")
        with c3:
            area = st.text_input("Área / Sala", key="pil_area",
                                 placeholder="ej. Sala 3, Quirófano 2")

        st.subheader("2. ¿Qué pilas se lleva?")
        st.caption("Se pueden agregar de más de un tipo en la misma entrega.")
        p1, p2, p3 = st.columns([4, 1.4, 1.2])
        with p1:
            opciones = {f"{r.descripcion} — hay {r.stock_actual:g} {r.unidad}": r.id
                        for r in pilas.itertuples()}
            elegida = st.selectbox("Tipo de pila", list(opciones.keys()),
                                   key="pil_producto")
            item = pilas[pilas["id"] == opciones[elegida]].iloc[0]
        with p2:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1,
                                       key="pil_cant")
        with p3:
            st.write("")
            if st.button("Agregar", width="stretch", key="pil_agregar"):
                st.session_state["carrito_pilas"].append({
                    "item_id": int(item["id"]), "descripcion": item["descripcion"],
                    "cantidad": float(cantidad), "unidad": item["unidad"],
                    # siempre PRESTADO: son recargables, vuelven. No se ofrece
                    # CONSUMO para que nadie las descuente para siempre por error
                    "tipo": "PRESTADO",
                })
                st.rerun()

        carrito = st.session_state["carrito_pilas"]
        if not carrito:
            st.info("Todavía no agregaste pilas a esta entrega.")
        else:
            st.subheader("3. Se lleva")
            for i, r in enumerate(carrito):
                col_a, col_b = st.columns([8, 1])
                col_a.write(f"**{r['descripcion']}** — {r['cantidad']:g} {r['unidad']}")
                if col_b.button("Quitar", key=f"pil_quitar_{i}"):
                    st.session_state["carrito_pilas"].pop(i)
                    st.rerun()

            observaciones = st.text_area("Observaciones", "", height=68, key="pil_obs",
                                         placeholder="ej. para el equipo de la sala 4")

            # el stock no puede quedar en negativo
            faltantes = []
            por_pila = {}
            for r in carrito:
                por_pila[r["item_id"]] = por_pila.get(r["item_id"], 0) + r["cantidad"]
            for item_id, total in por_pila.items():
                fila = pilas[pilas["id"] == item_id].iloc[0]
                if total > float(fila["stock_actual"]):
                    faltantes.append(f"{fila['descripcion']} (pedís {total:g}, "
                                     f"hay {fila['stock_actual']:g})")
            if faltantes:
                st.error("No hay stock suficiente de: " + "; ".join(faltantes))

            if st.button("Registrar entrega", type="primary",
                         disabled=bool(faltantes) or not receptor.strip()):
                id_vale = registrar_vale(sector, area, receptor.strip(), observaciones,
                                         carrito, registrado_por=usuario["NOMBRE"])
                st.session_state["carrito_pilas"] = []
                st.success(f"Entrega **{id_vale}** registrada a nombre de "
                           f"{receptor.strip()}. Queda pendiente de devolución.")
                st.rerun()

            if not receptor.strip():
                st.caption("Completá el nombre para poder registrar.")

# ═══════════════════════════════════════════════ devolución
with tab_devolver:
    if not puede("registrar_movimiento"):
        st.info("Tenés acceso de solo lectura.")
    else:
        pendientes = movs[(movs["ESTADO_RENGLON"] == "PENDIENTE") & (movs["pendiente"] > 0)]
        if pendientes.empty:
            st.success("No hay pilas pendientes de devolución.")
        else:
            st.caption("Se puede devolver todo o solo una parte: si se llevó 12 y "
                       "trae 8, quedan 4 pendientes.")
            opciones = {
                f"{r.Receptor_Para_Quien} · {r.DESCRIPCIÓN_ITEM} — "
                f"faltan {r.pendiente:g} {r.UNIDAD} ({r.ID_VALE_REF})": r.ID_REGISTRO
                for r in pendientes.rename(
                    columns={"Receptor / Para Quien": "Receptor_Para_Quien"}).itertuples()
            }
            elegido = st.selectbox("Entrega", list(opciones.keys()))
            reng = pendientes[pendientes["ID_REGISTRO"] == opciones[elegido]].iloc[0]
            maximo = float(reng["pendiente"])

            d1, d2 = st.columns([1, 3])
            with d1:
                cuantas = st.number_input("Cuántas vuelven", min_value=1,
                                          max_value=int(maximo), value=int(maximo),
                                          step=1)
            with d2:
                st.write("")
                if st.button("Registrar devolución", type="primary", width="stretch"):
                    devolver_renglon(opciones[elegido], float(cuantas))
                    st.success(f"{cuantas:g} pila(s) devueltas. El stock se repone solo.")
                    st.rerun()

# ═══════════════════════════════════════════════ historial
with tab_historial:
    if movs.empty:
        st.info("Todavía no hay movimientos de pilas registrados.")
    else:
        st.caption(f"{len(movs)} movimiento(s) de pilas. El resto del pañol no "
                   "aparece acá.")
        vista = movs.sort_values("ID_REGISTRO", ascending=False).copy()
        vista["estado"] = estado_movimiento(vista)
        tabla = (vista[["FECHA_VALE", "ID_VALE_REF", "DESCRIPCIÓN_ITEM", "estado",
                        "CANT", "CANT_DEVUELTA", "pendiente", "UNIDAD", "SECTOR",
                        "Receptor / Para Quien", "REGISTRADO_POR"]]
                 .rename(columns={
                     "FECHA_VALE": "Fecha", "ID_VALE_REF": "Vale",
                     "DESCRIPCIÓN_ITEM": "Pila", "estado": "Estado",
                     "CANT": "Entregadas", "CANT_DEVUELTA": "Devueltas",
                     "pendiente": "Faltan", "UNIDAD": "Un.", "SECTOR": "Sector",
                     "Receptor / Para Quien": "Quién",
                     "REGISTRADO_POR": "Registrado por"}))
        st.dataframe(
            estilo.tabla(tabla, {"Estado": estilo.COLORES_RENGLON,
                                 "Sector": estilo.COLORES_SECTOR}),
            hide_index=True, width="stretch", height=420,
        )
        st.download_button("Descargar CSV",
                           tabla.to_csv(index=False).encode("utf-8-sig"),
                           file_name="historial_pilas.csv", mime="text/csv")
