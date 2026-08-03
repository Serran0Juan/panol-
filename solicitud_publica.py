"""Pedido de reparación para gente de afuera de mantenimiento.

Es la única pantalla del sistema a la que se entra sin usuario: la idea es que
un médico o una enfermera escanee el QR pegado en su sector, cargue el problema
desde el celular y listo. Antes eso lo tenía que transcribir un administrativo.

Lo que se carga acá nace como una orden más, con el mismo `crear_solicitud()`
que usa el resto del sistema. No hay una segunda bandeja de entrada que después
haya que reconciliar.

Tiene dos pestañas: cargar un pedido y seguirlo. Para lo segundo hace falta el
número de orden y el email con el que se cargó, así cada uno ve lo suyo y nadie
puede ir probando números para leer los pedidos del resto.

La pantalla queda abierta: alcanza con tener el link para cargar un pedido. Se
decidió así para que no haya nada que escribir ni recordar. El único freno que
queda es el límite de pedidos por sesión, que frena a un robot torpe pero no a
alguien decidido. Si aparecen pedidos basura en el tablero, la vuelta atrás es
volver a pedir un código (está en el historial de git).
"""

import re
from pathlib import Path
from urllib.parse import quote

import streamlit as st

import estilo
from sheets_backend import PRIORIDADES, crear_solicitud, get_ordenes, get_ot_estados

ASSETS = Path(__file__).parent / "assets"

# Cuántos pedidos se aceptan por sesión. Una persona real carga uno, tal vez
# dos. Es el único freno que queda: frena a un robot torpe, no a alguien
# decidido, que puede recargar la página y volver a empezar.
MAXIMO_POR_SESION = 5

AYUDA_PRIORIDAD = {
    "URGENTE": "Hay riesgo para alguien o el servicio está parado. Se atiende hoy.",
    "ALTA": "Molesta para trabajar pero se puede seguir. Dentro de 3 días.",
    "MEDIA": "Hay que arreglarlo, no corre apuro. Dentro de la semana.",
    "BAJA": "Puede esperar. Dentro de los 15 días.",
}

# Los estados internos contados en criollo, para quien pidió el arreglo y no
# tiene por qué conocer el circuito de una orden de trabajo.
QUE_SIGNIFICA = {
    "SOLICITADA": "Lo recibimos. Está esperando que se le asigne un responsable.",
    "ASIGNADA": "Ya tiene un responsable asignado y entró en la planificación.",
    "EN CURSO": "Lo están trabajando en este momento.",
    "PAUSADA": "Está pausado. Suele ser porque falta un material o no se pudo "
               "acceder al lugar.",
    "RESUELTA": "El trabajo se hizo.",
    "ANULADA": "El pedido se dio de baja.",
}


def email_valido(texto: str) -> bool:
    """Un control mínimo, para atajar el error de tipeo y nada más."""
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(texto).strip()))


def normalizar_id(texto: str) -> str:
    """Acepta el número de orden como venga: OT-0003, ot 3, o solo 3."""
    limpio = (str(texto).strip().upper().replace(" ", "")
              .replace("OT-", "").replace("OT", ""))
    return f"OT-{int(limpio):04d}" if limpio.isdigit() else str(texto).strip().upper()


def buscar_pedido(id_ot: str, email: str):
    """La orden, si el número y el email coinciden. None si no.

    Se pide el email además del número a propósito: sin eso, cualquiera podría
    ir probando OT-0001, OT-0002... y leer los pedidos de todo el hospital.
    """
    email = str(email).strip().lower()
    if not email:
        return None

    ordenes = get_ordenes()
    if ordenes.empty:
        return None

    coincide = ordenes[
        (ordenes["ID_OT"].astype(str).str.strip().str.upper() == normalizar_id(id_ot))
        & (ordenes["SOLICITANTE_EMAIL"].astype(str).str.strip().str.lower() == email)]
    return None if coincide.empty else coincide.iloc[0]


def enlace_publico(base: str, area: str | None = None) -> str:
    """El link que va en el cartel de cada sector.

    Si se le pasa un área, el formulario ya viene con el lugar completado y la
    persona no lo tiene que escribir.
    """
    enlace = base.strip().rstrip("/") + "/?solicitar=1"
    if area and area.strip():
        enlace += "&area=" + quote(area.strip())
    return enlace


def qr_svg(enlace: str) -> str | None:
    """El QR del cartel, en SVG para poder agrandarlo sin que se pixele.

    Devuelve None si no está instalada la librería: el cartel se puede armar
    igual copiando el link en cualquier generador de QR.
    """
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return None

    codigo = qrcode.QRCode(box_size=10, border=2)
    codigo.add_data(enlace)
    codigo.make(fit=True)
    imagen = codigo.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    return imagen.to_string(encoding="unicode")


def _encabezado():
    marca = ASSETS / "logo_login.png"
    if marca.exists():
        st.image(str(marca), width=64)
    st.markdown("###### SISTEMA DE GESTIÓN INTEGRAL DE MANTENIMIENTO")
    st.title("Pedido de reparación")


def _confirmacion(id_ot: str, email: str):
    """Lo que ve la persona después de mandar el pedido."""
    st.success("Listo, tu pedido llegó a mantenimiento.")
    st.markdown(f"## {id_ot}")
    st.write(f"**Anotá ese número.** Con él y tu email ({email}) podés ver cómo "
             "viene desde la pestaña **Seguir un pedido**, sin llamar a nadie.")
    st.caption("Mantenimiento lo ve en su tablero y le asigna un responsable. "
               "Si dejaste un interno, te van a contactar por ahí.")
    if st.button("Cargar otro pedido", type="primary"):
        st.session_state.pop("solicitud_enviada", None)
        st.session_state.pop("email_enviado", None)
        st.rerun()


def _linea_tiempo(id_ot: str):
    """Los pasos por los que fue pasando el pedido."""
    historia = get_ot_estados()
    if historia.empty:
        return
    mia = historia[historia["ID_OT"].astype(str).str.strip().str.upper() == id_ot]
    if mia.empty:
        return

    st.markdown("##### Cómo fue avanzando")
    for _, paso in mia.sort_values("ID", ascending=False).iterrows():
        st.markdown(estilo.etiqueta(paso["ESTADO"], estilo.COLORES_ESTADO_OT)
                    + f" &nbsp; {estilo.escapar(paso['FECHA_HORA'])}",
                    unsafe_allow_html=True)
        if str(paso["NOTA"]).strip():
            st.caption(paso["NOTA"])


def _ficha_pedido(orden):
    """El estado de un pedido, contado para quien lo pidió."""
    estado = str(orden["ESTADO"]).strip().upper()
    st.markdown(f"## {orden['ID_OT']}")
    st.markdown(estilo.etiqueta(estado, estilo.COLORES_ESTADO_OT),
                unsafe_allow_html=True)
    st.info(QUE_SIGNIFICA.get(estado, "Consultá con el pañol."))

    st.markdown(f"**Dónde:** {orden['AREA']}")
    st.markdown(f"**Qué pediste:** {orden['DESCRIPCION']}")
    st.caption(f"Lo recibimos el {orden['FECHA_ALTA']}")

    if str(orden["ASIGNADO_A"]).strip():
        sector = str(orden["SECTOR_ASIGNADO"]).strip()
        st.markdown(f"**Lo tiene a cargo:** {orden['ASIGNADO_A']}"
                    + (f" ({sector})" if sector else ""))
    if str(orden["FECHA_PROGRAMADA"]).strip():
        st.markdown(f"**Programado para el** {orden['FECHA_PROGRAMADA']}")

    if str(orden["TRABAJO_REALIZADO"]).strip():
        st.success(f"**Qué se hizo:** {orden['TRABAJO_REALIZADO']}")
        if str(orden["FECHA_CIERRE"]).strip():
            st.caption(f"Cerrado el {orden['FECHA_CIERRE']}")

    _linea_tiempo(str(orden["ID_OT"]).strip().upper())

    st.divider()
    st.caption("¿Algo no cierra o el problema volvió? Cargá un pedido nuevo "
               "mencionando este número.")


def _pestana_seguimiento():
    """Consulta del estado con el número de orden y el email."""
    st.caption("Poné el número que te dimos al cargar el pedido y el email con "
               "el que lo mandaste.")

    with st.form("seguir_pedido"):
        c1, c2 = st.columns([1, 2])
        with c1:
            numero = st.text_input("Número de pedido", placeholder="OT-0003")
        with c2:
            email = st.text_input("Tu email", placeholder="nombre@ejemplo.com")
        buscar = st.form_submit_button("Ver cómo viene", type="primary",
                                       width="stretch")

    if not buscar:
        return
    if not numero.strip() or not email.strip():
        st.error("Necesitamos el número y el email para encontrarlo.")
        return

    orden = buscar_pedido(numero, email)
    if orden is None:
        # el mismo mensaje para "no existe" y para "no es tuyo": si fueran
        # distintos, se podría averiguar qué números existen probando
        st.error("No encontramos ningún pedido con ese número y ese email. "
                 "Fijate que el número esté completo (por ejemplo OT-0003) y "
                 "que sea el mismo email con el que lo cargaste.")
        return

    _ficha_pedido(orden)


def _pestana_carga():
    """El formulario para cargar un pedido nuevo."""
    enviada = st.session_state.get("solicitud_enviada")
    if enviada:
        _confirmacion(enviada, st.session_state.get("email_enviado", ""))
        return

    if st.session_state.get("solicitudes_enviadas", 0) >= MAXIMO_POR_SESION:
        st.warning("Ya cargaste varios pedidos desde este teléfono. "
                   "Si te falta alguno, llamá al pañol.")
        return

    st.caption("Contanos qué hay que arreglar. Lo recibe mantenimiento "
               "directamente, no hace falta pasar por administración.")

    # el área puede venir del QR de cada sector: .../?solicitar=1&area=Sala+3
    area_sugerida = str(st.query_params.get("area", "")).strip()

    with st.form("pedido_publico", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Tu nombre y apellido *")
        with c2:
            servicio = st.text_input("Tu servicio *",
                                     placeholder="ej. Enfermería, Pediatría")

        c3, c4 = st.columns(2)
        with c3:
            email = st.text_input("Tu email *", placeholder="nombre@ejemplo.com",
                                  help="Con el email y el número de pedido vas a "
                                       "poder consultar después cómo viene.")
        with c4:
            contacto = st.text_input("Interno o teléfono",
                                     placeholder="ej. interno 234")

        area = st.text_input("¿Dónde es? *", value=area_sugerida,
                             placeholder="ej. Sala 3, Quirófano 2, Cocina")
        descripcion = st.text_area(
            "¿Qué pasa? *", height=140,
            placeholder="Contá el problema con el mayor detalle posible: qué "
                        "falla, desde cuándo, si hay riesgo para alguien.")

        prioridad = st.radio(
            "¿Qué tan urgente es?", PRIORIDADES, index=PRIORIDADES.index("MEDIA"),
            format_func=lambda p: f"{p.capitalize()} — {AYUDA_PRIORIDAD[p]}")

        enviar = st.form_submit_button("Enviar pedido", type="primary",
                                       width="stretch")

    if not enviar:
        st.caption("Si lo que necesitás es material del pañol, no uses este "
                   "formulario: pedilo por el canal de siempre.")
        return

    if not nombre.strip() or not servicio.strip():
        st.error("Necesitamos tu nombre y tu servicio para poder ubicarte.")
        return
    if not email_valido(email):
        st.error("Poné un email válido: es con lo que después vas a poder "
                 "consultar cómo viene tu pedido.")
        return
    if not area.strip():
        st.error("Indicá en qué lugar del hospital es.")
        return
    if len(descripcion.strip()) < 10:
        st.error("Contá un poco más sobre el problema.")
        return

    observaciones = " · ".join(x for x in [servicio.strip(), contacto.strip()] if x)
    id_ot = crear_solicitud(area.strip(), descripcion.strip(), prioridad,
                            nombre.strip(), email.strip(), observaciones)

    st.session_state["solicitud_enviada"] = id_ot
    st.session_state["email_enviado"] = email.strip()
    st.session_state["solicitudes_enviadas"] = (
        st.session_state.get("solicitudes_enviadas", 0) + 1)
    st.rerun()


def formulario_publico():
    """La pantalla completa. Se dibuja antes del login, sin usuario."""
    _, centro, _ = st.columns([1, 1.6, 1])
    with centro:
        _encabezado()

        tab_nuevo, tab_seguir = st.tabs(["Cargar un pedido", "Seguir un pedido"])
        with tab_nuevo:
            _pestana_carga()
        with tab_seguir:
            _pestana_seguimiento()
