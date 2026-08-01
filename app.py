"""Sistema de Gestión Integral de Mantenimiento — entrypoint, login y navegación por rol."""

from pathlib import Path

import streamlit as st

import estilo
from auth import current_user, login_widget, puede
from sheets_backend import usando_sheets_reales

ASSETS = Path(__file__).parent / "assets"
MARCA = ASSETS / "logo_chico.png"

st.set_page_config(page_title="Sistema de Gestión Integral de Mantenimiento",
                   page_icon=str(MARCA) if MARCA.exists() else "⚙️", layout="wide")
estilo.aplicar()

# La única pantalla sin login: el pedido de reparación que carga la gente del
# hospital desde el QR de su sector. Va antes que todo lo demás, porque no tiene
# que pasar por el login ni dibujar la navegación.
if "solicitar" in st.query_params:
    from solicitud_publica import formulario_publico

    # tiene que pasar por st.navigation igual que el login: si no, Streamlit
    # arma solo la navegación con todo el contenido de pages/ y le muestra el
    # menú completo del sistema a alguien que no inició sesión
    st.navigation([st.Page(formulario_publico, title="Pedido de reparación")]).run()
    st.stop()

usuario = current_user()

if usuario is None:
    # sin barra lateral el logo de st.logo queda flotando solo arriba a la
    # izquierda: en el login la marca la pone la propia pantalla, centrada
    st.navigation([st.Page(login_widget, title="Iniciar sesión")]).run()
    st.stop()

if (ASSETS / "logo_sidebar.png").exists():
    st.logo(str(ASSETS / "logo_sidebar.png"), icon_image=str(MARCA), size="large")

if puede("ver_gestion"):
    movimientos = []
    if puede("registrar_movimiento"):
        movimientos.append(
            st.Page("pages/3_Movimientos.py", title="Registrar movimiento"))
    movimientos += [
        st.Page("pages/9_Historial.py", title="Historial"),
        st.Page("pages/4_Reclamos.py", title="Pedidos y reclamos"),
    ]

    mantenimiento = [st.Page("pages/12_Solicitudes.py", title="Solicitudes")]
    if puede("gestionar_ot"):
        mantenimiento += [
            st.Page("pages/13_Ordenes.py", title="Órdenes de trabajo"),
            st.Page("pages/15_Agenda.py", title="Agenda"),
        ]
    mantenimiento += [
        st.Page("pages/16_Tablero.py", title="Tablero de jefatura"),
        st.Page("pages/14_Mis_Ordenes.py", title="Mis órdenes"),
    ]

    paginas = {
        "Pañol": [
            st.Page("pages/0_Panel.py", title="Panel de control", default=True),
            st.Page("pages/1_Buscar_Productos.py", title="Buscar material"),
            st.Page("pages/6_Plano.py", title="Plano del pañol"),
        ],
        "Movimientos": movimientos,
        "Trabajos correctivos": mantenimiento,
        "Inventario": [
            st.Page("pages/5_Inventario.py", title="Materiales"),
            st.Page("pages/7_Ubicaciones.py", title="Ubicaciones"),
        ],
    }
    if puede("administrar"):
        paginas["Administración"] = [
            st.Page("pages/11_Administracion.py", title="Configuración")]
else:
    paginas = {
        "Pañol": [
            st.Page("pages/1_Buscar_Productos.py", title="Buscar material", default=True),
            st.Page("pages/6_Plano.py", title="Plano del pañol"),
        ],
        "Trabajos correctivos": [
            st.Page("pages/12_Solicitudes.py", title="Solicitudes"),
            st.Page("pages/14_Mis_Ordenes.py", title="Mis órdenes"),
        ],
        "Lo mío": [
            st.Page("pages/10_Mi_Historial.py", title="Mi historial"),
            st.Page("pages/4_Reclamos.py", title="Pedidos y reclamos"),
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
    if st.button("Cerrar sesión", width="stretch"):
        st.session_state.pop("usuario", None)
        st.rerun()

navegacion.run()
