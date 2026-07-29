"""Asignar ubicaciones: cargar rápido en qué estantería está cada producto."""

import streamlit as st

from auth import current_user, exigir, puede
from sheets_backend import get_estanterias, get_items, numero_estanteria, update_item

usuario = current_user()
if usuario is None:
    st.stop()
exigir("ver_gestion")

st.title("📍 Asignar ubicaciones")

items = get_items()
estanterias = get_estanterias()

if items.empty:
    st.info("No hay productos cargados.")
    st.stop()

sin_ubicacion = items[items["ubicacion"].str.strip() == ""]
con_ubicacion = items[items["ubicacion"].str.strip() != ""]

c1, c2, c3 = st.columns(3)
c1.metric("Productos totales", len(items))
c2.metric("Con ubicación ✅", len(con_ubicacion))
c3.metric("Sin ubicación ⏳", len(sin_ubicacion))
st.progress(len(con_ubicacion) / len(items) if len(items) else 0)

if not puede("editar_inventario"):
    st.info("Tenés acceso de solo lectura: podés ver el avance de la carga de "
            "ubicaciones, pero no modificarlas.")
    st.stop()

st.caption("Consejo: filtrá por categoría o buscá un grupo de productos parecidos "
           "(ej. 'termofusion') y asignalos todos juntos a la misma estantería.")

tab_lote, tab_uno = st.tabs(["⚡ Asignar en lote", "✏️ Uno por uno"])

opciones_est = estanterias["estanteria"].tolist() if not estanterias.empty else []


def descripcion_estanteria(num: str) -> str:
    if estanterias.empty:
        return ""
    fila = estanterias[estanterias["estanteria"] == num]
    if fila.empty:
        return ""
    f = fila.iloc[0]
    return f"Área {f['area']} · {f['objetos']}"


# ------------------------------------------------------------------ Asignar en lote
with tab_lote:
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        q = st.text_input("Buscar productos", "", placeholder="ej. termofusion, cable, canilla...")
    with f2:
        cat = st.selectbox("Categoría", ["Todas"] + sorted(c for c in items["categoria"].unique() if c))
    with f3:
        solo_sin = st.checkbox("Solo sin ubicación", value=True)

    candidatos = items
    if q.strip():
        candidatos = candidatos[candidatos["descripcion"].str.contains(q.strip(), case=False, na=False)]
    if cat != "Todas":
        candidatos = candidatos[candidatos["categoria"] == cat]
    if solo_sin:
        candidatos = candidatos[candidatos["ubicacion"].str.strip() == ""]

    st.caption(f"{len(candidatos)} producto(s) coinciden")

    if candidatos.empty:
        st.success("No quedan productos para asignar con esos filtros.")
    else:
        etiquetas = {f"{r.descripcion} (N° {r.id})": int(r.id) for r in candidatos.itertuples()}
        seleccionados = st.multiselect(
            "Elegí los productos a ubicar", list(etiquetas.keys()),
            default=list(etiquetas.keys())[:20] if len(etiquetas) <= 20 else [],
        )

        u1, u2 = st.columns([1, 1])
        with u1:
            estanteria = st.selectbox("Estantería", opciones_est) if opciones_est \
                else st.text_input("Estantería")
        with u2:
            nivel = st.text_input("Nivel / estante (opcional)", "",
                                  placeholder="ej. 2 — dejalo vacío si no aplica")

        if estanteria:
            info = descripcion_estanteria(estanteria)
            if info:
                st.info(f"Estantería {estanteria} — {info}")

        ubicacion_final = f"{estanteria}-{nivel.strip()}" if nivel.strip() else str(estanteria)

        if st.button(f"Asignar «{ubicacion_final}» a {len(seleccionados)} producto(s)",
                     type="primary", disabled=not seleccionados or not estanteria):
            barra = st.progress(0.0, text="Guardando en la planilla...")
            for i, etiqueta in enumerate(seleccionados, start=1):
                update_item(etiquetas[etiqueta], ubicacion=ubicacion_final)
                barra.progress(i / len(seleccionados), text=f"Guardando {i} de {len(seleccionados)}...")
            barra.empty()
            st.success(f"Listo: {len(seleccionados)} producto(s) quedaron en la ubicación {ubicacion_final}.")
            st.rerun()

# ------------------------------------------------------------------ Uno por uno
with tab_uno:
    lista = sin_ubicacion if not sin_ubicacion.empty else items
    etiquetas_uno = {f"{r.descripcion} (N° {r.id})": int(r.id) for r in lista.itertuples()}
    elegido = st.selectbox("Producto", list(etiquetas_uno.keys()))
    item = items[items["id"] == etiquetas_uno[elegido]].iloc[0]

    st.write(f"**{item['descripcion']}** · {item['categoria']} · "
             f"stock {item['stock_actual']:.0f} {item['unidad']}")
    if item["ubicacion"].strip():
        st.caption(f"Ubicación actual: {item['ubicacion']}")

    with st.form("asignar_uno"):
        a1, a2 = st.columns(2)
        with a1:
            actual = numero_estanteria(item["ubicacion"])
            idx = opciones_est.index(actual) if actual in opciones_est else 0
            est = st.selectbox("Estantería", opciones_est, index=idx) if opciones_est \
                else st.text_input("Estantería", item["ubicacion"])
        with a2:
            niv = st.text_input("Nivel / estante (opcional)", "")

        if st.form_submit_button("Guardar ubicación", type="primary"):
            nueva = f"{est}-{niv.strip()}" if niv.strip() else str(est)
            update_item(int(item["id"]), ubicacion=nueva)
            st.success(f"«{item['descripcion']}» quedó en la ubicación {nueva}.")
            st.rerun()
