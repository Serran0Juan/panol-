"""Pruebas de la sección de pilas recargables.

Las pilas son cientos y se mueven todos los días, así que tienen pantalla
propia. Pero los movimientos se guardan en las mismas tablas que el resto: el
stock de la planilla se calcula con fórmulas que suman sobre `Registro APP`, y
si las pilas fueran a otra tabla su stock dejaría de calcularse solo.

Lo que se verifica acá es justamente eso: que la separación sea de pantalla y
no de datos, y que el circuito de préstamo funcione con cantidades.

    py -3 pruebas/prueba_pilas.py
"""

import os

import ruta_app  # noqa: F401  agrega la raíz del proyecto al camino de importación

os.environ["PANOL_MODO_LOCAL"] = "1"

import pandas as pd  # noqa: E402

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


print("1. Qué cuenta como recargable")
check("reconoce la subcategoría", sb.es_recargable(sb.SUBCATEGORIA_RECARGABLE))
check("no distingue mayúsculas", sb.es_recargable(sb.SUBCATEGORIA_RECARGABLE.upper()))
check("tolera espacios", sb.es_recargable(f"  {sb.SUBCATEGORIA_RECARGABLE}  "))
check("otra subcategoría no lo es", not sb.es_recargable("Fijaciones"))
check("vacío no lo es", not sb.es_recargable(""))

print("\n2. Marcar un material en la planilla alcanza")
items = sb.get_items()
antes = len(sb.items_recargables())

marcado = items.copy()
objetivo = int(marcado.iloc[0]["id"])
marcado.loc[marcado["id"] == objetivo, "subcategoria"] = sb.SUBCATEGORIA_RECARGABLE

from unittest import mock  # noqa: E402

with mock.patch.object(sb, "get_items", return_value=marcado):
    check("lo toma de la subcategoría", len(sb.items_recargables()) == antes + 1,
          f"-> antes {antes}, ahora {len(sb.items_recargables())}")

print("\n3. La separación es de pantalla, no de datos")
movs = sb.get_movimientos()
with mock.patch.object(sb, "get_items", return_value=marcado):
    de_pilas = sb.separar_recargables(movs, incluir=True)
    del_resto = sb.separar_recargables(movs, incluir=False)

check("ningún movimiento se pierde",
      len(de_pilas) + len(del_resto) == len(movs),
      f"-> {len(de_pilas)} + {len(del_resto)} = {len(movs)}")
check("ninguno queda en los dos lados",
      set(de_pilas["ID_REGISTRO"]).isdisjoint(set(del_resto["ID_REGISTRO"])))
check("los de pilas son solo del material marcado",
      all(int(n) == objetivo for n in de_pilas["ID_ITEM"].dropna()))

# sin ningún material marcado, las pantallas generales no pierden nada
sin_marcar = items.copy()
sin_marcar["subcategoria"] = "Otra cosa"
with mock.patch.object(sb, "get_items", return_value=sin_marcar):
    check("sin pilas marcadas el resto ve todo",
          len(sb.separar_recargables(movs, incluir=False)) == len(movs))
    check("y la pantalla de pilas no muestra nada",
          sb.separar_recargables(movs, incluir=True).empty)

print("\n4. Una entrega con dos tipos y cantidades distintas")
# nombre distinto en cada corrida: la copia local no se limpia entre pruebas, y
# el agrupado suma todos los vales de una misma persona, que es lo correcto
QUIEN = f"Prueba Pilas {sb.ahora():%H%M%S}"
dos = items.head(2).copy()
ids = [int(x) for x in dos["id"]]
vale = sb.registrar_vale(
    "ELECTRICIDAD", "Sala 4", QUIEN, "prueba de pilas",
    [{"item_id": ids[0], "descripcion": dos.iloc[0]["descripcion"],
      "cantidad": 12, "unidad": "un", "tipo": "PRESTADO"},
     {"item_id": ids[1], "descripcion": dos.iloc[1]["descripcion"],
      "cantidad": 4, "unidad": "un", "tipo": "PRESTADO"}],
    registrado_por="Serrano Juan")

reg = sb.get_registro()
mios = reg[reg["ID_VALE_REF"] == vale]
check("queda un solo vale", len(mios["ID_VALE_REF"].unique()) == 1, f"-> {vale}")
check("con un renglón por tipo", len(mios) == 2)
check("cada uno con su cantidad", sorted(mios["CANT"]) == [4, 12],
      f"-> {sorted(mios['CANT'])}")
check("los dos nacen pendientes",
      all(mios["ESTADO_RENGLON"] == "PENDIENTE"))

print("\n5. Quién tiene qué, agrupado")
con_pilas = items.copy()
con_pilas.loc[con_pilas["id"].isin(ids), "subcategoria"] = sb.SUBCATEGORIA_RECARGABLE
with mock.patch.object(sb, "get_items", return_value=con_pilas):
    afuera = sb.prestamos_por_persona(solo_recargables=True)

mio = afuera[afuera["persona"] == QUIEN]
check("aparece la persona", not mio.empty)
check("con una fila por tipo de pila", len(mio) == 2, f"-> {len(mio)}")
check("con las cantidades sin devolver", sorted(mio["pendiente"]) == [4.0, 12.0],
      f"-> {sorted(mio['pendiente'])}")
check("dice el sector", set(mio["sector"]) == {"ELECTRICIDAD"})
check("y qué vale es", all(vale in v for v in mio["vales"]))

print("\n6. Devolución parcial: se llevó 12, trae 8")
renglon = mios[mios["CANT"] == 12].iloc[0]
sb.devolver_renglon(int(renglon["ID_REGISTRO"]), 8)

reg = sb.get_registro()
actualizado = reg[reg["ID_REGISTRO"].astype(str) == str(renglon["ID_REGISTRO"])].iloc[0]
check("registra las devueltas", float(actualizado["CANT_DEVUELTA"]) == 8)
check("el renglón sigue abierto", actualizado["ESTADO_RENGLON"] == "PENDIENTE")

with mock.patch.object(sb, "get_items", return_value=con_pilas):
    afuera = sb.prestamos_por_persona(solo_recargables=True)
quedan = afuera[(afuera["persona"] == QUIEN)
                & (afuera["material"] == dos.iloc[0]["descripcion"])]
check("quedan 4 sin devolver", float(quedan.iloc[0]["pendiente"]) == 4,
      f"-> {float(quedan.iloc[0]['pendiente'])}")

print("\n7. El plazo de reclamo de las pilas es propio")
check("es distinto al de las herramientas",
      sb.DIAS_PARA_DEMORA_RECARGABLE != sb.DIAS_PARA_DEMORA,
      f"-> pilas {sb.DIAS_PARA_DEMORA_RECARGABLE} d, resto {sb.DIAS_PARA_DEMORA} d")

print(f"\n{'=' * 52}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 52}")
raise SystemExit(1 if fallos else 0)
