"""Verifica que cada rol tenga exactamente los permisos definidos."""

import os

import ruta_app  # noqa: F401  agrega la raíz del proyecto al camino de importación

os.environ["PANOL_MODO_LOCAL"] = "1"

import warnings  # noqa: E402

warnings.filterwarnings("ignore")

from auth import PERMISOS, ROLES, puede  # noqa: E402

ESPERADO = {
    "ADMIN": {"ver_gestion", "registrar_movimiento", "editar_inventario",
              "resolver_reclamos", "gestionar_ot", "administrar"},
    "JEFE": {"ver_gestion", "registrar_movimiento", "gestionar_ot"},
    "COORDINADOR": {"ver_gestion", "registrar_movimiento", "gestionar_ot"},
    "LECTOR": {"ver_gestion"},
    "OPERARIO": set(),
}

ok = fallos = 0
TODAS = sorted({a for p in ESPERADO.values() for a in p})

print(f"{'ROL':<13}" + "".join(f"{a[:11]:<13}" for a in TODAS))
for rol in ROLES:
    usuario = {"ROL": rol, "NOMBRE": "prueba"}
    marcas = ""
    for accion in TODAS:
        real = puede(accion, usuario)
        esperado = accion in ESPERADO[rol]
        if real == esperado:
            ok += 1
        else:
            fallos += 1
        marcas += f"{'  SI' if real else '  no':<13}"
    print(f"{rol:<13}{marcas}")

# nadie debe tener permisos de más
for rol in ROLES:
    if PERMISOS[rol] != ESPERADO[rol]:
        fallos += 1
        print(f"FALLA: {rol} tiene {PERMISOS[rol]}, se esperaba {ESPERADO[rol]}")

# un rol desconocido no debe poder nada
for accion in TODAS:
    if puede(accion, {"ROL": "INVENTADO"}):
        fallos += 1
        print(f"FALLA: un rol desconocido puede {accion}")
    else:
        ok += 1

print("\nTexto de los usuarios metido en HTML")
import estilo  # noqa: E402

# El área de una orden la escribe a mano cualquiera. Si no se escapara, esa
# etiqueta se ejecutaría en la pantalla de todos los que abren la orden.
ATAQUE = '<img src=x onerror="alert(1)">'
for nombre, salida in [
    ("cabecera de la orden", estilo.cabecera_orden("OT-1", ATAQUE, "ASIGNADA", "ALTA")),
    ("etiqueta de color", estilo.badge(ATAQUE)),
    ("tarjeta de indicador", estilo.indicador("Abiertas", ATAQUE, ATAQUE)),
]:
    # lo que importa es que no quede una etiqueta abierta: con el < escapado,
    # el resto ("onerror=...") es texto suelto que el navegador solo muestra
    if "<img" in salida:
        fallos += 1
        print(f"  FALLA {nombre} deja pasar una etiqueta HTML sin escapar")
    elif "&lt;img" not in salida:
        fallos += 1
        print(f"  FALLA {nombre} perdió el texto en lugar de escaparlo")
    else:
        ok += 1
        print(f"  OK    {nombre} escapa el HTML")

print("\nFreno a los intentos de contraseña a repetición")
import datetime as dt  # noqa: E402

import auth  # noqa: E402


def check(etiqueta, condicion, detalle=""):
    global ok, fallos
    if condicion:
        ok += 1
        print(f"  OK    {etiqueta} {detalle}")
    else:
        fallos += 1
        print(f"  FALLA {etiqueta} {detalle}")


CORREO = "alguien@hospital.gob.ar"
auth.limpiar_intentos(CORREO)

check("un email limpio no espera", auth.minutos_de_espera(CORREO) == 0)

for i in range(auth.INTENTOS_MAXIMOS - 1):
    auth.registrar_intento_fallido(CORREO)
check(f"aguanta {auth.INTENTOS_MAXIMOS - 1} intentos sin frenar",
      auth.minutos_de_espera(CORREO) == 0)

auth.registrar_intento_fallido(CORREO)
espera = auth.minutos_de_espera(CORREO)
check(f"al intento {auth.INTENTOS_MAXIMOS} frena", espera > 0, f"-> {espera} min")
check("la espera no pasa del tope", espera <= auth.MINUTOS_BLOQUEO)
check("aparece en la lista para destrabar", CORREO in auth.emails_frenados())

# el freno es por email, no por sesión: otro email no queda afectado
check("no arrastra a otros usuarios", auth.minutos_de_espera("otro@hospital.gob.ar") == 0)

# no distingue mayúsculas: no se saltea escribiendo el email distinto
check("no se saltea cambiando mayúsculas", auth.minutos_de_espera(CORREO.upper()) > 0)

auth.limpiar_intentos(CORREO)
check("un ADMIN puede destrabarlo", auth.minutos_de_espera(CORREO) == 0)
check("y sale de la lista", CORREO not in auth.emails_frenados())

# cumplida la espera se suelta solo
auth._intentos()[CORREO] = (auth.INTENTOS_MAXIMOS,
                            auth.ahora() - dt.timedelta(minutes=auth.MINUTOS_BLOQUEO + 1))
check("pasado el tiempo se suelta solo", auth.minutos_de_espera(CORREO) == 0)
check("y se olvida la cuenta vieja", CORREO not in auth._intentos())

# entrar bien tiene que limpiar la cuenta
auth.registrar_intento_fallido(CORREO)
auth.limpiar_intentos(CORREO)
check("entrar bien borra los fallos previos", CORREO not in auth._intentos())

# contarlo también para emails que no existen evita averiguar cuáles sí existen
auth.limpiar_intentos("noexiste@x.com")
for i in range(auth.INTENTOS_MAXIMOS):
    auth.registrar_intento_fallido("noexiste@x.com")
check("también frena emails que no existen",
      auth.minutos_de_espera("noexiste@x.com") > 0,
      "(si no, quedar frenado delataría que el email existe)")
auth.limpiar_intentos("noexiste@x.com")

import inspect  # noqa: E402
fuente = inspect.getsource(auth.login_widget)
check("el freno se revisa antes de mirar la contraseña",
      fuente.index("minutos_de_espera") < fuente.index("verificar_password"))
check("el contador vive en el servidor, no en la sesión",
      "cache_resource" in inspect.getsource(auth).split("def _intentos")[0][-120:])

print(f"\n{'=' * 46}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 46}")
raise SystemExit(1 if fallos else 0)
