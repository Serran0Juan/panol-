"""Login por email + contraseña.

Las contraseñas nunca se guardan en texto plano: se guarda un "hash" (una huella
irreversible) en la columna PASSWORD_HASH de la hoja Usuarios. Ni mirando la
planilla se puede recuperar la contraseña original.

La pantalla de inicio no muestra ninguna lista de usuarios: hay que saber el
email. Y cuando algo no cierra el mensaje es siempre el mismo, así que desde
afuera tampoco se puede averiguar qué emails existen.

La primera vez que entra un usuario nuevo (sin hash cargado) la app le pide que
elija su propia contraseña.
"""

import datetime as dt
import hashlib
import hmac
import math
import os
from pathlib import Path

import streamlit as st

from sheets_backend import ahora, get_usuarios_activos, set_password_hash

ITERACIONES = 200_000

ASSETS = Path(__file__).parent / "assets"

# Un solo mensaje para "ese email no existe" y para "la contraseña está mal":
# si fueran distintos, cualquiera podría ir probando emails hasta dar con uno.
ERROR_LOGIN = "Email o contraseña incorrectos."

# ── Freno a los intentos a repetición ───────────────────────────────────────
# La app está abierta en internet, así que cualquiera puede tirarle contraseñas
# al login. Después de unos cuantos intentos fallidos ese email queda esperando
# unos minutos.
INTENTOS_MAXIMOS = 5
MINUTOS_BLOQUEO = 10


@st.cache_resource(show_spinner=False)
def _intentos() -> dict:
    """Los intentos fallidos por email, compartidos por todas las sesiones.

    Va en la memoria del servidor y no en la sesión del navegador: si estuviera
    en la sesión, bastaría con abrir una pestaña nueva para tener otros cinco
    intentos y el freno no serviría de nada.

    Se pierde cuando la app se reinicia. Es un costo aceptable: lo que esto
    frena es a alguien probando contraseñas a mano o con un script simple, no a
    un atacante con tiempo y herramientas.
    """
    return {}


def _clave(email) -> str:
    return str(email).strip().lower()


def minutos_de_espera(email) -> int:
    """Minutos que faltan para poder volver a intentar. 0 si no está frenado."""
    registro = _intentos().get(_clave(email))
    if not registro:
        return 0

    fallos, ultimo = registro
    if fallos < INTENTOS_MAXIMOS:
        return 0

    faltan = (ultimo + dt.timedelta(minutes=MINUTOS_BLOQUEO) - ahora()).total_seconds()
    if faltan <= 0:
        _intentos().pop(_clave(email), None)  # cumplió la espera, arranca de cero
        return 0
    return max(1, math.ceil(faltan / 60))


def registrar_intento_fallido(email):
    """Suma uno a la cuenta de ese email.

    Se cuenta también cuando el email no existe: si solo se contaran los
    existentes, quedar frenado sería una forma de averiguar que un email está
    dado de alta.
    """
    fallos, _ = _intentos().get(_clave(email), (0, None))
    _intentos()[_clave(email)] = (fallos + 1, ahora())


def limpiar_intentos(email):
    """Borra la cuenta: se llama al entrar bien y cuando un ADMIN destraba."""
    _intentos().pop(_clave(email), None)


def emails_frenados() -> list:
    """Los emails que están esperando, para que un ADMIN pueda destrabarlos."""
    return sorted(email for email in list(_intentos()) if minutos_de_espera(email))

# Qué puede hacer cada rol. Todo lo que no esté acá, no se puede.
#   ver_gestion         : entrar a panel, historial, inventario y ubicaciones (solo mirar)
#   registrar_movimiento: cargar entregas, devoluciones e ingresos
#   editar_inventario   : dar de alta y modificar materiales y sus ubicaciones
#   resolver_reclamos   : responder y cerrar los pedidos de los operarios
#   gestionar_ot        : asignar órdenes de trabajo y moverlas de estado
#   administrar         : usuarios, permisos y configuración
#
# Cargar una solicitud de reparación y cerrar las órdenes propias lo puede
# hacer cualquier usuario, así que no llevan permiso.
PERMISOS = {
    "ADMIN": {"ver_gestion", "registrar_movimiento", "editar_inventario",
              "resolver_reclamos", "gestionar_ot", "administrar"},
    "JEFE": {"ver_gestion", "registrar_movimiento", "gestionar_ot"},
    "COORDINADOR": {"ver_gestion", "registrar_movimiento", "gestionar_ot"},
    "LECTOR": {"ver_gestion"},
    "OPERARIO": set(),
}

ROLES = list(PERMISOS)

DESCRIPCION_ROLES = {
    "ADMIN": "Control total: configura el sistema y los usuarios.",
    "JEFE": "Ve todo el sistema y registra movimientos.",
    "COORDINADOR": "Ve todo el sistema y registra movimientos.",
    "LECTOR": "Ve todo el sistema, sin modificar nada.",
    "OPERARIO": "Consulta el stock, ve lo suyo y pide materiales.",
}


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERACIONES)
    return f"pbkdf2${ITERACIONES}${salt.hex()}${dk.hex()}"


def verificar_password(password: str, guardado: str) -> bool:
    try:
        _, iteraciones, salt_hex, hash_hex = guardado.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iteraciones))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def current_user():
    return st.session_state.get("usuario")


def puede(accion: str, usuario=None) -> bool:
    """True si el usuario tiene ese permiso. Es la única fuente de verdad."""
    usuario = usuario or current_user()
    if usuario is None:
        return False
    return accion in PERMISOS.get(str(usuario.get("ROL", "")).upper(), set())


def exigir(accion: str, mensaje: str = "No tenés permiso para ver esta sección."):
    """Corta la página si el usuario no tiene el permiso pedido."""
    import streamlit as st  # noqa: PLC0415  (evita el import circular al cargar el módulo)

    if not puede(accion):
        st.error(mensaje)
        st.stop()


def puede_gestionar(usuario=None) -> bool:
    """Puede entrar a las secciones de gestión, aunque sea solo para mirar."""
    return puede("ver_gestion", usuario)


def es_admin(usuario=None) -> bool:
    return puede("administrar", usuario)


def _encabezado():
    """La marca del sistema arriba del formulario."""
    marca = ASSETS / "logo_login.png"
    if marca.exists():
        st.image(str(marca), width=68)
    st.markdown("###### SISTEMA DE GESTIÓN INTEGRAL DE MANTENIMIENTO")
    st.title("Iniciar sesión")


def _elegir_password(usuario):
    """Segundo paso, solo para quien todavía no tiene contraseña."""
    st.info(f"Primer ingreso de **{usuario['NOMBRE']}**. "
            "Elegí la contraseña que vas a usar de ahora en más.")
    with st.form("crear_password"):
        p1 = st.text_input("Nueva contraseña", type="password")
        p2 = st.text_input("Repetir contraseña", type="password")
        crear = st.form_submit_button("Crear contraseña e ingresar", type="primary",
                                      width="stretch")

    if crear:
        if len(p1) < 6:
            st.error("La contraseña tiene que tener al menos 6 caracteres.")
        elif p1 != p2:
            st.error("Las dos contraseñas no coinciden.")
        else:
            set_password_hash(usuario["EMAIL"], hash_password(p1))
            st.session_state.pop("login_sin_password", None)
            st.session_state["usuario"] = usuario
            st.rerun()

    if st.button("← Volver", width="stretch"):
        st.session_state.pop("login_sin_password", None)
        st.rerun()


def login_widget():
    # con layout="wide" un formulario a todo el ancho queda enorme; va centrado
    _, centro, _ = st.columns([1, 1.3, 1])
    with centro:
        _encabezado()

        usuarios = get_usuarios_activos()
        if not usuarios:
            st.error("No hay usuarios activos cargados. "
                     "Revisá la pestaña **Usuarios** de la planilla.")
            return

        por_email = {str(u["EMAIL"]).strip().lower(): u for u in usuarios}

        pendiente = st.session_state.get("login_sin_password")
        if pendiente in por_email:
            _elegir_password(por_email[pendiente])
            return

        st.caption("Entrá con tu email y tu contraseña.")
        with st.form("login"):
            email = st.text_input("Email", placeholder="nombre@ejemplo.com",
                                  autocomplete="username")
            password = st.text_input("Contraseña", type="password",
                                     autocomplete="current-password")
            entrar = st.form_submit_button("Ingresar", type="primary", width="stretch")

        if entrar:
            espera = minutos_de_espera(email)
            if espera:
                # se corta antes de mirar la contraseña, así los intentos que
                # llegan durante la espera no la alargan indefinidamente
                st.error(f"Demasiados intentos fallidos con ese email. "
                         f"Probá de nuevo en {espera} minuto(s), o pedile a un "
                         f"ADMIN que lo destrabe.")
                return

            usuario = por_email.get(str(email).strip().lower())
            if usuario is None:
                registrar_intento_fallido(email)
                st.error(ERROR_LOGIN)
            elif not str(usuario.get("PASSWORD_HASH", "")).strip():
                # nunca eligió contraseña: pasa al segundo paso
                st.session_state["login_sin_password"] = str(email).strip().lower()
                st.rerun()
            elif verificar_password(password, str(usuario["PASSWORD_HASH"])):
                limpiar_intentos(email)
                st.session_state["usuario"] = usuario
                st.rerun()
            else:
                registrar_intento_fallido(email)
                st.error(ERROR_LOGIN)

        st.caption("¿Olvidaste tu contraseña? Pedile a un ADMIN que la reinicie "
                   "desde la sección Usuarios.")
