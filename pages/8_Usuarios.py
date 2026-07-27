"""Usuarios: alta, baja y reinicio de contraseñas (solo ADMIN)."""

import streamlit as st

from auth import current_user, es_admin
from sheets_backend import add_usuario, get_parametros, get_usuarios, set_password_hash, set_usuario_activo

usuario = current_user()
if usuario is None:
    st.stop()
if not es_admin(usuario):
    st.error("Solo un ADMIN puede administrar usuarios.")
    st.stop()

st.title("👥 Usuarios")

ROLES = ["ADMIN", "JEFE", "COORDINADOR", "OPERARIO"]
sectores = get_parametros().get("SECTOR", []) or ["MANTENIMIENTO"]

usuarios = get_usuarios()

tab_lista, tab_nuevo = st.tabs(["📋 Usuarios cargados", "➕ Nuevo usuario"])

with tab_lista:
    if usuarios.empty:
        st.info("No hay usuarios cargados.")
    else:
        vista = usuarios.copy()
        vista["CONTRASEÑA"] = vista["PASSWORD_HASH"].apply(
            lambda h: "definida" if str(h).strip() else "sin definir (la elige al entrar)"
        )
        st.dataframe(
            vista[["EMAIL", "NOMBRE", "ROL", "SECTOR", "ACTIVO", "CONTRASEÑA"]],
            hide_index=True, use_container_width=True,
        )

        st.divider()
        elegido = st.selectbox("Usuario", usuarios["EMAIL"].tolist())
        fila = usuarios[usuarios["EMAIL"] == elegido].iloc[0]
        activo = str(fila["ACTIVO"]).upper() in ("TRUE", "1", "SI", "SÍ", "VERDADERO")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Reiniciar contraseña"):
                set_password_hash(elegido, "")
                st.success(f"Contraseña de {elegido} borrada. "
                           "La próxima vez que entre va a elegir una nueva.")
                st.rerun()
        with c2:
            if activo:
                if st.button("Desactivar acceso", disabled=elegido == usuario["EMAIL"]):
                    set_usuario_activo(elegido, False)
                    st.success(f"{elegido} ya no puede entrar.")
                    st.rerun()
            else:
                if st.button("Reactivar acceso"):
                    set_usuario_activo(elegido, True)
                    st.success(f"{elegido} puede volver a entrar.")
                    st.rerun()

        if elegido == usuario["EMAIL"]:
            st.caption("No podés desactivar tu propio usuario.")

with tab_nuevo:
    with st.form("nuevo_usuario", clear_on_submit=True):
        email = st.text_input("Email *", placeholder="nombre@ejemplo.com")
        nombre = st.text_input("Nombre y apellido *")
        rol = st.selectbox("Rol", ROLES, index=ROLES.index("OPERARIO"))
        sector = st.selectbox("Sector", sectores)

        st.caption("No hace falta que le pongas contraseña: la primera vez que entre "
                   "la app le va a pedir que elija la suya.")

        if st.form_submit_button("Agregar usuario", type="primary"):
            if not email.strip() or "@" not in email:
                st.error("Poné un email válido.")
            elif not nombre.strip():
                st.error("El nombre es obligatorio.")
            elif not usuarios.empty and email.strip().lower() in usuarios["EMAIL"].str.lower().values:
                st.error("Ese email ya está cargado.")
            else:
                add_usuario(email, nombre.strip(), rol, sector)
                st.success(f"{nombre} ya puede entrar a la app.")
                st.rerun()
