"""Sistema de Gestión Integral de Mantenimiento — entrypoint, login y navegación por rol."""

from pathlib import Path

import streamlit as st

from auth import current_user, login_widget, puede
from sheets_backend import usando_sheets_reales

st.set_page_config(page_title="Sistema de Gestión Integral de Mantenimiento",
                   page_icon="🧰", layout="wide")

ASSETS = Path(__file__).parent / "assets"
if (ASSETS / "logo_sidebar.png").exists():
    st.logo(str(ASSETS / "logo_sidebar.png"), icon_image=str(ASSETS / "logo_chico.png"),
            size="large")

usuario = current_user()

if usuario is None:
    st.navigation([st.Page(login_widget, title="Iniciar sesión", icon="🔐")]).run()
    st.stop()

if puede("ver_gestion"):
    movimientos = []
    if puede("registrar_movimiento"):
        movimientos.append(
            st.Page("pages/3_Movimientos.py", title="Registrar movimiento", icon="➕"))
    movimientos += [
        st.Page("pages/9_Historial.py", title="Historial", icon="📜"),
        st.Page("pages/4_Reclamos.py", title="Pedidos y reclamos", icon="📢"),
    ]

    paginas = {
        "Pañol": [
            st.Page("pages/0_Panel.py", title="Panel de control", icon="🏠", default=True),
            st.Page("pages/1_Buscar_Productos.py", title="Buscar material", icon="🔍"),
            st.Page("pages/6_Plano.py", title="Plano del pañol", icon="🗺️"),
        ],
        "Movimientos": movimientos,
        "Inventario": [
            st.Page("pages/5_Inventario.py", title="Materiales", icon="📦"),
            st.Page("pages/7_Ubicaciones.py", title="Ubicaciones", icon="📍"),
        ],
    }
    if puede("administrar"):
        paginas["Administración"] = [
            st.Page("pages/11_Administracion.py", title="Configuración", icon="⚙️")]
else:
    paginas = {
        "Pañol": [
            st.Page("pages/1_Buscar_Productos.py", title="Buscar material", icon="🔍", default=True),
            st.Page("pages/6_Plano.py", title="Plano del pañol", icon="🗺️"),
        ],
        "Lo mío": [
            st.Page("pages/10_Mi_Historial.py", title="Mi historial", icon="📜"),
            st.Page("pages/4_Reclamos.py", title="Pedidos y reclamos", icon="📢"),
        ],
    }

# st.navigation tiene que ir antes de escribir cualquier otra cosa: si no,
# Streamlit no llega a construir la barra lateral.
navegacion = st.navigation(paginas)

with st.sidebar:
    st.divider()
    st.markdown(f"**{usuario['NOMBRE']}**")
    st.caption(f"{usuario['ROL']} · {usuario.get('SECTOR', '')}")
    if not usando_sheets_reales():
        st.warning("Modo de prueba: copia local, no la planilla real (ver SETUP.md).")
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state.pop("usuario", None)
        st.rerun()

navegacion.run()
