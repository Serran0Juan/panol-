"""Verifica que cada rol tenga exactamente los permisos definidos."""

import os

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

print(f"\n{'=' * 46}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 46}")
raise SystemExit(1 if fallos else 0)
