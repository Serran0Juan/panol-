"""Controla que el script de Google Form no se desfase de la app.

El riesgo de ese camino es que la numeración y los nombres de las columnas
quedan escritos en dos lados: en Python y en `apps_script/formulario_a_ordenes.gs`.
Si alguien renombra una columna en la app, el script sigue escribiendo en la
vieja y las órdenes entran mal, sin que nadie se entere.

Esta prueba lee el .gs como texto y lo compara contra las constantes reales.

    py -3 _prueba_apps_script.py
"""

import os
import pathlib
import re

os.environ["PANOL_MODO_LOCAL"] = "1"

import sheets_backend as sb  # noqa: E402

SCRIPT = pathlib.Path(__file__).parent / "apps_script" / "formulario_a_ordenes.gs"

ok = fallos = 0


def check(etiqueta, condicion, detalle=""):
    global ok, fallos
    if condicion:
        ok += 1
        print(f"  OK    {etiqueta} {detalle}")
    else:
        fallos += 1
        print(f"  FALLA {etiqueta} {detalle}")


print("1. El script existe y se puede leer")
check("está en apps_script/", SCRIPT.exists())
if not SCRIPT.exists():
    raise SystemExit(1)
fuente = SCRIPT.read_text(encoding="utf-8")

print("\n2. Escribe en las pestañas que existen")
check("apunta a la hoja de órdenes", f"'{sb.HOJA_ORDENES}'" in fuente)
check("apunta a la bitácora", f"'{sb.HOJA_OT_ESTADOS}'" in fuente)

print("\n3. Las columnas que usa son las de la app")
# los nombres que el script pone como clave al escribir: 'ID_OT': ...
usadas = set(re.findall(r"^\s*'([A-ZÁÉÍÓÚÑ_ ()/]+)':", fuente, re.MULTILINE))
conocidas = set(sb.COLS_ORDENES) | set(sb.COLS_OT_ESTADOS)
desconocidas = usadas - conocidas
check("ninguna columna inventada", not desconocidas,
      f"-> sobran {sorted(desconocidas)}" if desconocidas else f"({len(usadas)} columnas)")

for obligatoria in ("ID_OT", "FECHA_ALTA", "SOLICITANTE", "SOLICITANTE_EMAIL",
                    "AREA", "DESCRIPCION", "PRIORIDAD", "ESTADO"):
    check(f"completa {obligatoria}", f"'{obligatoria}'" in fuente)

print("\n4. La orden nace igual que en la app")
check("en estado SOLICITADA", "'SOLICITADA'" in fuente)
check("con el mismo formato de fecha", "yyyy-MM-dd HH:mm:ss" in fuente)
check("en hora de Argentina, no la de la planilla",
      "America/Argentina/Buenos_Aires" in fuente)

print("\n5. Las prioridades son las mismas")
en_script = set(re.search(r"var PRIORIDADES = \[(.*?)\]", fuente, re.S).group(1)
                .replace("'", "").replace("\n", "").replace(" ", "").split(","))
check("coinciden con PRIORIDADES", en_script == set(sb.PRIORIDADES),
      f"-> script {sorted(en_script)} vs app {sorted(sb.PRIORIDADES)}")

print("\n6. La numeración")
check("usa cuatro dígitos como la app", "slice(-4)" in fuente)
check("toma el mayor existente y suma uno", "maximo + 1" in fuente)
check("se protege de dos envíos simultáneos", "LockService" in fuente)

print("\n7. No duplica lo que ya resuelve la app")
check("no calcula la fecha de compromiso", "FECHA_COMPROMISO" not in fuente,
      "(la app la calcula al asignar)")
check("no asigna responsable", "'ASIGNADO_A'" not in fuente)

print(f"\n{'=' * 52}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 52}")
raise SystemExit(1 if fallos else 0)
