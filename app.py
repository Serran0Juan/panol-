"""Pañol — app web: entrypoint, login y navegación por rol."""

import streamlit as st

from auth import current_user, es_admin, login_widget, puede_gestionar
from sheets_backend import usando_sheets_reales

st.set_page_config(page_title="Pañol", page_icon="🧰", layout="wide")

usuario = current_user()

if usuario is None:
    st.navigation([st.Page(login_widget, title="Iniciar sesión", icon="🔐")]).run()
    st.stop()

paginas = [
    st.Page("pages/1_Buscar_Productos.py", title="Buscar productos", icon="🔍"),
    st.Page("pages/6_Plano.py", title="Plano del pañol", icon="🗺️"),
    st.Page("pages/4_Reclamos.py", title="Pedidos y reclamos", icon="📢"),
]
if puede_gestionar(usuario):
    paginas += [
        st.Page("pages/3_Movimientos.py", title="Movimientos", icon="🔄"),
        st.Page("pages/2_Dashboard.py", title="Dashboard", icon="📊"),
        st.Page("pages/5_Inventario.py", title="Inventario", icon="📦"),
        st.Page("pages/7_Ubicaciones.py", title="Asignar ubicaciones", icon="📍"),
    ]
if es_admin(usuario):
    paginas.append(st.Page("pages/8_Usuarios.py", title="Usuarios", icon="👥"))

with st.sidebar:
    st.markdown(f"**{usuario['NOMBRE']}**")
    st.caption(f"{usuario['ROL']} · {usuario.get('SECTOR', '')}")
    if not usando_sheets_reales():
        st.warning("Modo de prueba: trabajando sobre una copia local, no sobre la planilla real (ver SETUP.md).")
    if st.button("Cerrar sesión"):
        st.session_state.pop("usuario", None)
        st.rerun()

st.navigation(paginas).run()
