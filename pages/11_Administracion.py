"""Administración: catálogos, ubicaciones, usuarios y permisos del sistema."""

import pandas as pd
import streamlit as st

from auth import (DESCRIPCION_ROLES, MINUTOS_BLOQUEO, PERMISOS, ROLES, current_user,
                  emails_frenados, exigir, limpiar_intentos, minutos_de_espera)
from sheets_backend import (add_usuario, get_estanterias, get_items, get_ordenes,
                            get_parametros, get_usuarios, set_password_hash,
                            set_usuario_activo)
from solicitud_publica import codigo_configurado, enlace_publico, qr_svg

usuario = current_user()
if usuario is None:
    st.stop()
exigir("administrar", "Solo un ADMIN puede entrar a esta sección.")

st.markdown("###### PAÑOL · MANTENIMIENTO")
st.title("Administración")
st.caption("Configuración de catálogos, ubicaciones y permisos del sistema.")

items = get_items()
estanterias = get_estanterias()
parametros = get_parametros()
usuarios = get_usuarios()

sectores = parametros.get("SECTOR", []) or ["MANTENIMIENTO"]

# ───────────────────────────────────────────── resumen
c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.markdown("### Materiales y categorías")
        st.caption("Catálogo, unidades de medida y mínimos.")
        st.markdown(f"**{len(items)} materiales · "
                    f"{items['categoria'].nunique()} categorías**")
with c2:
    with st.container(border=True):
        st.markdown("### Ubicaciones")
        st.caption("Estanterías usadas para localizar cada material.")
        ubicados = int((items["ubicacion"].str.strip() != "").sum())
        st.markdown(f"**{len(estanterias)} estanterías · {ubicados} materiales ubicados**")
with c3:
    with st.container(border=True):
        st.markdown("### Usuarios y permisos")
        st.caption("Quién entra a la app y qué puede hacer.")
        activos = usuarios["ACTIVO"].astype(str).str.upper().isin(["TRUE", "1", "SI", "SÍ"]).sum()
        st.markdown(f"**{len(ROLES)} perfiles · {activos} usuarios activos**")

st.divider()

tab_usuarios, tab_permisos, tab_catalogo, tab_ubic, tab_formulario = st.tabs(
    ["Usuarios", "Permisos", "Catálogo", "Ubicaciones", "Formulario del hospital"])

# ───────────────────────────────────────────── usuarios
with tab_usuarios:
    sub_lista, sub_nuevo = st.tabs(["Cargados", "Nuevo usuario"])

    with sub_lista:
        if usuarios.empty:
            st.info("No hay usuarios cargados.")
        else:
            vista = usuarios.copy()
            vista["CONTRASEÑA"] = vista["PASSWORD_HASH"].apply(
                lambda h: "definida" if str(h).strip() else "sin definir (la elige al entrar)")
            st.dataframe(
                vista[["EMAIL", "NOMBRE", "ROL", "SECTOR", "ACTIVO", "CONTRASEÑA"]],
                hide_index=True, width="stretch",
            )

            st.divider()
            elegido = st.selectbox("Usuario", usuarios["EMAIL"].tolist())
            fila = usuarios[usuarios["EMAIL"] == elegido].iloc[0]
            activo = str(fila["ACTIVO"]).upper() in ("TRUE", "1", "SI", "SÍ", "VERDADERO")

            a1, a2 = st.columns(2)
            with a1:
                if st.button("Reiniciar contraseña", width="stretch"):
                    set_password_hash(elegido, "")
                    st.success(f"{elegido} va a elegir una nueva la próxima vez que entre.")
                    st.rerun()
            with a2:
                if activo:
                    if st.button("Desactivar acceso", width="stretch",
                                 disabled=elegido == usuario["EMAIL"]):
                        set_usuario_activo(elegido, False)
                        st.rerun()
                else:
                    if st.button("Reactivar acceso", width="stretch"):
                        set_usuario_activo(elegido, True)
                        st.rerun()

            if elegido == usuario["EMAIL"]:
                st.caption("No podés desactivar tu propio usuario.")

            # Después de varios intentos fallidos el email queda esperando unos
            # minutos. Acá se destraba sin tener que aguantar la espera.
            frenados = emails_frenados()
            if frenados:
                st.divider()
                st.warning(f"{len(frenados)} email(s) frenados por intentos "
                           f"fallidos de contraseña.")
                for correo in frenados:
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{correo}** — puede reintentar en "
                                f"{minutos_de_espera(correo)} minuto(s)")
                    if c2.button("Destrabar", key=f"destrabar_{correo}",
                                 width="stretch"):
                        limpiar_intentos(correo)
                        st.rerun()
                st.caption(f"El freno se suelta solo a los {MINUTOS_BLOQUEO} "
                           "minutos. Si ves muchos emails acá y nadie se olvidó "
                           "la contraseña, puede ser que alguien esté probando "
                           "de afuera.")

    with sub_nuevo:
        with st.form("nuevo_usuario", clear_on_submit=True):
            email = st.text_input("Email *", placeholder="nombre@ejemplo.com")
            nombre = st.text_input("Nombre y apellido *",
                                   help="Tiene que coincidir con el nombre que se usa "
                                        "al cargar los vales, para que le aparezca en Mi historial.")
            rol = st.selectbox("Rol", ROLES, index=ROLES.index("OPERARIO"),
                               format_func=lambda r: f"{r} — {DESCRIPCION_ROLES[r]}")
            sector = st.selectbox("Sector", sectores)
            st.caption("No hace falta asignarle contraseña: la elige la primera vez que entra.")

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

# ───────────────────────────────────────────── permisos
with tab_permisos:
    st.subheader("Qué puede hacer cada perfil")
    st.caption("La app se maneja con estos permisos: lo que no está marcado, no se puede.")

    ACCIONES = [
        ("Consultar stock y plano", None),
        ("Pedir material", None),
        ("Ver el sistema completo", "ver_gestion"),
        ("Registrar movimientos", "registrar_movimiento"),
        ("Editar inventario y ubicaciones", "editar_inventario"),
        ("Resolver pedidos", "resolver_reclamos"),
        ("Administrar usuarios", "administrar"),
    ]

    filas = []
    for rol in ROLES:
        fila = {"Perfil": rol}
        for etiqueta, permiso in ACCIONES:
            fila[etiqueta] = "Sí" if permiso is None or permiso in PERMISOS[rol] else "—"
        filas.append(fila)
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")

    st.subheader("Para qué sirve cada perfil")
    for rol, texto in DESCRIPCION_ROLES.items():
        st.markdown(f"- **{rol}** — {texto}")

    st.info("**JEFE y COORDINADOR** ven todo el sistema y registran movimientos, "
            "pero no modifican el inventario ni la configuración. "
            "**LECTOR** ve todo sin poder tocar nada.")

# ───────────────────────────────────────────── catálogo
with tab_catalogo:
    st.subheader("Categorías")
    resumen = (items.groupby("categoria", as_index=False)
               .agg(materiales=("id", "count"), unidades=("stock_actual", "sum"))
               .sort_values("materiales", ascending=False))
    st.dataframe(
        resumen.rename(columns={"categoria": "Categoría", "materiales": "Materiales",
                                "unidades": "Unidades en stock"}),
        hide_index=True, width="stretch",
    )

    st.subheader("Listas desplegables de la planilla")
    st.caption("Salen de la pestaña **Parametros** de tu Google Sheet. "
               "Para cambiarlas, editalas ahí.")
    for nombre, valores in parametros.items():
        if valores:
            st.markdown(f"**{nombre}** ({len(valores)}): {', '.join(valores)}")

# ───────────────────────────────────────────── ubicaciones
with tab_ubic:
    if estanterias.empty:
        st.info("No hay estanterías cargadas en la pestaña 'Plano Pañol'.")
    else:
        st.caption("Las estanterías salen de la pestaña **Plano Pañol** de tu planilla.")
        conteo = (items[items["ubicacion"].str.strip() != ""]
                  .assign(est=lambda d: d["ubicacion"].str.extract(r"(\d+)")[0].str.zfill(2))
                  .groupby("est", as_index=False).size().rename(columns={"size": "materiales"}))
        tabla = estanterias.merge(conteo, left_on="estanteria", right_on="est", how="left")
        tabla["materiales"] = tabla["materiales"].fillna(0).astype(int)
        st.dataframe(
            tabla[["estanteria", "area", "materiales", "objetos", "ancho", "profundidad", "estantes"]]
            .rename(columns={"estanteria": "Estantería", "area": "Área",
                             "materiales": "Materiales asignados", "objetos": "Qué guarda",
                             "ancho": "Ancho (m)", "profundidad": "Prof. (m)",
                             "estantes": "N° estantes"}),
            hide_index=True, width="stretch", height=420,
        )
        vacias = tabla[tabla["materiales"] == 0]
        if not vacias.empty:
            st.warning(f"{len(vacias)} estantería(s) todavía sin materiales asignados: "
                       + ", ".join(vacias["estanteria"].tolist()))

# ───────────────────────────────────────────── formulario del hospital
with tab_formulario:
    st.markdown("### Pedidos desde los sectores")
    st.caption("El cartel que se pega en cada sector para que médicos y enfermeros "
               "carguen sus pedidos de reparación sin pasar por administración. "
               "Lo que cargan entra directo como orden de trabajo.")

    if codigo_configurado():
        st.success("El formulario está **activo**: quien tenga el link y el código "
                   "del hospital puede cargar un pedido.")
    else:
        st.error("El formulario está **apagado**: falta cargar el código del hospital "
                 "en los secretos. Hasta que se configure, quien entre al link ve un "
                 "cartel de \"no habilitado\" y no puede cargar nada. Ver SETUP.md.")

    st.divider()
    st.markdown("##### 1. La dirección de la app")
    base = st.text_input(
        "Dirección", value=st.session_state.get("url_publica", ""),
        placeholder="https://tu-app.streamlit.app",
        help="Copiala de la barra del navegador, sin nada después del dominio.")
    st.session_state["url_publica"] = base

    if not base.strip():
        st.info("Pegá la dirección de arriba y aparecen el link y el código QR.")
    else:
        st.markdown("##### 2. El sector")
        st.caption("Si elegís uno, el QR de ese cartel ya viene con el lugar "
                   "completado y la persona no lo tiene que escribir.")
        ordenes_cargadas = get_ordenes()
        areas = (sorted(a for a in ordenes_cargadas["AREA"].unique() if a)
                 if not ordenes_cargadas.empty else [])
        area = st.selectbox("Lugar", ["(sin completar)"] + areas,
                            accept_new_options=True,
                            help="Podés escribir uno nuevo si todavía no se usó.")
        con_area = None if area in ("(sin completar)", None) else area

        enlace = enlace_publico(base, con_area)
        st.markdown("##### 3. El cartel")
        st.code(enlace, language=None)

        svg = qr_svg(enlace)
        if svg is None:
            st.warning("Para generar el código QR falta la librería `qrcode`. "
                       "Mientras tanto, copiá el link de arriba en cualquier "
                       "generador de QR gratuito.")
        else:
            izq, der = st.columns([1, 2])
            with izq:
                st.image(svg, width=190)
            with der:
                st.download_button(
                    "Descargar el QR para imprimir", svg,
                    file_name=f"qr-{(con_area or 'general').replace(' ', '-').lower()}.svg",
                    mime="image/svg+xml")
                st.caption("Es un SVG: se agranda todo lo que quieras sin que se "
                           "pixele. Al lado del QR acordate de escribir el código "
                           "del hospital, que es lo que pide el formulario.")
