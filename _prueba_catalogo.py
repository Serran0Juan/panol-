"""Pruebas del chequeo de la planilla de inventario.

La duda que originó esto: la planilla llega al número 492 pero el panel dice
486 materiales. No es un error —la app cuenta filas con descripción, no el
número más alto— pero hasta ahora no había forma de comprobarlo sin hacer
cuentas a mano.

    py -3 _prueba_catalogo.py
"""

import os

os.environ["PANOL_MODO_LOCAL"] = "1"

import pandas as pd  # noqa: E402
from unittest import mock  # noqa: E402

import sheets_backend as sb  # noqa: E402

ok = fallos = 0


def check(etiqueta, condicion, detalle=""):
    global ok, fallos
    if condicion:
        ok += 1
        print(f"  OK    {etiqueta} {detalle}")
    else:
        fallos += 1
        print(f"  FALLA {etiqueta} {detalle}")


ID = sb.COLS_INVENTARIO["id"]
DESC = sb.COLS_INVENTARIO["descripcion"]


def diagnosticar(filas):
    """Corre el diagnóstico contra una planilla de juguete."""
    df = pd.DataFrame(filas, columns=[ID, DESC])
    with mock.patch.object(sb, "_leer", return_value=df):
        return sb.diagnostico_catalogo()


print("1. Una planilla sin huecos ni problemas")
dx = diagnosticar([(1, "Martillo"), (2, "Pinza"), (3, "Destornillador")])
check("cuenta los materiales", dx["con_descripcion"] == 3)
check("toma el número más alto", dx["mayor"] == 3)
check("no encuentra huecos", dx["faltantes"] == [], f"-> {dx['faltantes']}")
check("no encuentra repetidos", dx["repetidos"] == [])
check("no encuentra filas sin descripción", dx["sin_descripcion"] == 0)

print("\n2. El caso real: el último número es mayor que la cantidad")
# se borraron las filas 2 y 4: quedan 3 materiales y el mayor es 5
dx = diagnosticar([(1, "Martillo"), (3, "Pinza"), (5, "Destornillador")])
check("cuenta 3 materiales", dx["con_descripcion"] == 3)
check("el número más alto es 5", dx["mayor"] == 5)
check("señala los huecos", dx["faltantes"] == [2, 4], f"-> {dx['faltantes']}")
check("la diferencia queda explicada",
      dx["mayor"] - dx["con_descripcion"] == len(dx["faltantes"]))
check("no lo reporta como problema",
      dx["sin_descripcion"] == 0 and dx["repetidos"] == [])

print("\n3. Filas con número pero sin descripción: eso sí es un problema")
dx = diagnosticar([(1, "Martillo"), (2, ""), (3, "   "), (4, "Pinza")])
check("no las cuenta como materiales", dx["con_descripcion"] == 2)
check("las reporta aparte", dx["sin_descripcion"] == 2, f"-> {dx['sin_descripcion']}")
check("avisa que esos números quedaron libres", dx["faltantes"] == [2, 3])

print("\n4. Números repetidos")
dx = diagnosticar([(1, "Martillo"), (2, "Pinza"), (2, "Pinza grande"), (3, "Llave")])
check("detecta el repetido", dx["repetidos"] == [2], f"-> {dx['repetidos']}")
check("igual cuenta las cuatro filas", dx["con_descripcion"] == 4)

print("\n5. Material con descripción pero sin número")
dx = diagnosticar([(1, "Martillo"), (0, "Pinza sin numerar"), (3, "Llave")])
check("lo detecta", dx["sin_numero"] == 1, f"-> {dx['sin_numero']}")
check("lo sigue contando como material", dx["con_descripcion"] == 3)

print("\n6. Renglones vacíos al final de la hoja")
dx = diagnosticar([(1, "Martillo"), (2, "Pinza"), (0, ""), (0, ""), (0, "")])
check("no los cuenta como filas cargadas", dx["filas"] == 2, f"-> {dx['filas']}")
check("no los reporta como error", dx["sin_descripcion"] == 0)

print("\n7. Una planilla vacía no rompe nada")
dx = diagnosticar([])
check("devuelve todo en cero", dx["con_descripcion"] == 0 and dx["mayor"] == 0)
check("sin huecos ni repetidos", dx["faltantes"] == [] and dx["repetidos"] == [])

print("\n8. Contra la planilla local de prueba")
real = sb.diagnostico_catalogo()
items = sb.get_items()
check("coincide con lo que muestra la app",
      real["con_descripcion"] == len(items),
      f"-> diagnóstico {real['con_descripcion']}, app {len(items)}")
check("el mayor no es menor que la cantidad", real["mayor"] >= real["con_descripcion"])

print(f"\n{'=' * 52}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 52}")
raise SystemExit(1 if fallos else 0)
