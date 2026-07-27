"""Login por email + contraseña.

Las contraseñas nunca se guardan en texto plano: se guarda un "hash" (una huella
irreversible) en la columna PASSWORD_HASH de la hoja Usuarios. Ni mirando la
planilla se puede recuperar la contraseña original.

La primera vez que entra un usuario nuevo (sin hash cargado) la app le pide que
elija su propia contraseña.
"""

import hashlib
import hmac
import os

import streamlit as st

from sheets_backend import get_usuarios_activos, set_password_hash

ROLES_GESTION = ("ADMIN", "JEFE", "COORDINADOR")
ITERACIONES = 200_000


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


def puede_gestionar(usuario=None) -> bool:
    usuario = usuario or current_user()
    return usuario is not None and usuario.get("ROL") in ROLES_GESTION


def es_admin(usuario=None) -> bool:
    usuario = usuario or current_user()
    return usuario is not None and usuario.get("ROL") == "ADMIN"


def login_widget():
    st.title("🧰 Pañol · Iniciar sesión")

    usuarios = get_usuarios_activos()
    if not usuarios:
        st.error("No hay usuarios activos cargados. Revisá la pestaña **Usuarios** de la planilla.")
        return

    por_email = {u["EMAIL"].strip().lower(): u for u in usuarios}
    etiquetas = {f"{u['NOMBRE']} — {u['ROL']}": u["EMAIL"].strip().lower() for u in usuarios}

    elegido = st.selectbox("Usuario", list(etiquetas.keys()))
    usuario = por_email[etiquetas[elegido]]
    tiene_password = bool(str(usuario.get("PASSWORD_HASH", "")).strip())

    if not tiene_password:
        st.info("Primer ingreso: elegí la contraseña que vas a usar de ahora en más.")
        with st.form("crear_password"):
            p1 = st.text_input("Nueva contraseña", type="password")
            p2 = st.text_input("Repetir contraseña", type="password")
            if st.form_submit_button("Crear contraseña e ingresar", type="primary"):
                if len(p1) < 6:
                    st.error("La contraseña tiene que tener al menos 6 caracteres.")
                elif p1 != p2:
                    st.error("Las dos contraseñas no coinciden.")
                else:
                    set_password_hash(usuario["EMAIL"], hash_password(p1))
                    st.session_state["usuario"] = usuario
                    st.rerun()
        return

    with st.form("login"):
        password = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar", type="primary"):
            if verificar_password(password, str(usuario["PASSWORD_HASH"])):
                st.session_state["usuario"] = usuario
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")

    st.caption("¿Olvidaste tu contraseña? Pedile a un ADMIN que la reinicie desde la sección Usuarios.")
