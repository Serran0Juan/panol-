"""Prueba de la lógica de vales contra la copia local (no toca la planilla real).

Fuerza el modo local ANTES de importar el backend, para que no exista la
posibilidad de escribir en la planilla de producción aunque haya credenciales.
"""

import logging
import os
import warnings

os.environ["PANOL_MODO_LOCAL"] = "1"
warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import sheets_backend as sb  # noqa: E402

if sb.usando_sheets_reales():
    raise SystemExit("ABORTADO: la prueba iba a escribir en la planilla real.")

ok = fallos = 0


def check(etiqueta, condicion, detalle=""):
    global ok, fallos
    if condicion:
        ok += 1
        print(f"  OK   {etiqueta} {detalle}")
    else:
        fallos += 1
        print(f"  FALLA {etiqueta} {detalle}")


items = sb.get_items()
a = items.iloc[0]
b = items.iloc[5]
print(f"inventario: {len(items)} productos\n")

# ---------------------------------------------------------------- vale mixto
print("1. Vale con un préstamo y un consumo en la misma entrega")
vale = sb.registrar_vale("PLOMERÍA", "Sala 3", "Bazan Ramiro", "prueba mixta", [
    {"item_id": int(a["id"]), "descripcion": a["descripcion"], "cantidad": 3,
     "unidad": a["unidad"], "tipo": "PRESTADO"},
    {"item_id": int(b["id"]), "descripcion": b["descripcion"], "cantidad": 10,
     "unidad": b["unidad"], "tipo": "CONSUMO"},
])
reg = sb.get_registro()
r_vale = reg[reg["ID_VALE_REF"] == vale]
cab = sb.get_vales().set_index("ID VALE").loc[vale]
check("2 renglones", len(r_vale) == 2)
check("tipos distintos por renglón", set(r_vale["TIPO_MOV"]) == {"PRESTADO", "CONSUMO"})
check("cabecera MIXTO", cab["TIPO MOVIMIENTO"] == "MIXTO", f"-> {cab['TIPO MOVIMIENTO']}")
check("vale ABIERTO", cab["ESTADO VALE"] == "ABIERTO")
prest = r_vale[r_vale["TIPO_MOV"] == "PRESTADO"].iloc[0]
cons = r_vale[r_vale["TIPO_MOV"] == "CONSUMO"].iloc[0]
check("préstamo PENDIENTE", prest["ESTADO_RENGLON"] == "PENDIENTE")
check("consumo CERRADO", cons["ESTADO_RENGLON"] == "CERRADO")

# ---------------------------------------------------------------- devolución parcial
print("\n2. Devolución parcial del préstamo (3 prestados, devuelve 1)")
sb.devolver_renglon(prest["ID_REGISTRO"], 1)
reg = sb.get_registro()
p = reg[reg["ID_REGISTRO"] == prest["ID_REGISTRO"]].iloc[0]
check("devuelto = 1", float(p["CANT_DEVUELTA"]) == 1, f"-> {p['CANT_DEVUELTA']}")
check("pendiente = 2", float(p["pendiente"]) == 2, f"-> {p['pendiente']}")
check("sigue PENDIENTE", p["ESTADO_RENGLON"] == "PENDIENTE")
check("vale sigue ABIERTO",
      sb.get_vales().set_index("ID VALE").loc[vale, "ESTADO VALE"] == "ABIERTO")

print("\n3. Devuelve los 2 que faltaban")
sb.devolver_renglon(prest["ID_REGISTRO"], 2)
reg = sb.get_registro()
p = reg[reg["ID_REGISTRO"] == prest["ID_REGISTRO"]].iloc[0]
check("pendiente = 0", float(p["pendiente"]) == 0)
check("renglón CERRADO", p["ESTADO_RENGLON"] == "CERRADO")
check("vale se cerró solo",
      sb.get_vales().set_index("ID VALE").loc[vale, "ESTADO VALE"] == "CERRADO")

# ---------------------------------------------------------------- sobrante de consumo
print("\n4. Sobrante de consumo (entregó 10, traen 4 de vuelta)")
sb.devolver_renglon(cons["ID_REGISTRO"], 4)
c = sb.get_registro().set_index("ID_REGISTRO").loc[cons["ID_REGISTRO"]]
check("devuelto = 4", float(c["CANT_DEVUELTA"]) == 4)
check("consumo real = 6", float(c["CANT"]) - float(c["CANT_DEVUELTA"]) == 6)

# ---------------------------------------------------------------- no vuelve -> consumo
print("\n5. Préstamo que no vuelve, se convierte en consumo")
vale2 = sb.registrar_vale("ELECTRICIDAD", "Sala 1", "Dias Diego", "se rompió", [
    {"item_id": int(a["id"]), "descripcion": a["descripcion"], "cantidad": 2,
     "unidad": a["unidad"], "tipo": "PRESTADO"},
])
reg = sb.get_registro()
r2 = reg[reg["ID_VALE_REF"] == vale2].iloc[0]
sb.convertir_a_consumo(r2["ID_REGISTRO"])
r2b = sb.get_registro().set_index("ID_REGISTRO").loc[r2["ID_REGISTRO"]]
check("pasó a CONSUMO", r2b["TIPO_MOV"] == "CONSUMO", f"-> {r2b['TIPO_MOV']}")
check("renglón CERRADO", r2b["ESTADO_RENGLON"] == "CERRADO")
check("vale cerrado",
      sb.get_vales().set_index("ID VALE").loc[vale2, "ESTADO VALE"] == "CERRADO")

# ---------------------------------------------------------------- devolver todo
print("\n6. Botón 'devolver todo' sobre un vale con dos préstamos")
vale3 = sb.registrar_vale("PINTURA", "Depósito", "Rondan Pablo", "", [
    {"item_id": int(a["id"]), "descripcion": a["descripcion"], "cantidad": 1,
     "unidad": a["unidad"], "tipo": "PRESTADO"},
    {"item_id": int(b["id"]), "descripcion": b["descripcion"], "cantidad": 2,
     "unidad": b["unidad"], "tipo": "PRESTADO"},
])
sb.cerrar_vale(vale3)
reg3 = sb.get_registro()
reg3 = reg3[reg3["ID_VALE_REF"] == vale3]
check("todos los renglones cerrados", (reg3["ESTADO_RENGLON"] == "CERRADO").all())
check("nada pendiente", (reg3["pendiente"] == 0).all())
check("vale cerrado",
      sb.get_vales().set_index("ID VALE").loc[vale3, "ESTADO VALE"] == "CERRADO")

# ---------------------------------------------------------------- validaciones
print("\n7. Validaciones")
try:
    sb.devolver_renglon(cons["ID_REGISTRO"], 999)
    check("rechaza devolver de más", False)
except ValueError as e:
    check("rechaza devolver de más", True, f"-> {e}")
try:
    sb.devolver_renglon(cons["ID_REGISTRO"], 0)
    check("rechaza cantidad cero", False)
except ValueError:
    check("rechaza cantidad cero", True)

# ---------------------------------------------------------------- ingreso
print("\n8. Ingreso de mercadería suma al stock inicial")
ini = float(sb.get_items().set_index("id").loc[int(a["id"]), "stock_inicial"])
sb.registrar_ingreso(int(a["id"]), 25, "remito 0012", "Serrano Juan")
fin = float(sb.get_items().set_index("id").loc[int(a["id"]), "stock_inicial"])
check("stock inicial +25", fin == ini + 25, f"-> {ini} a {fin}")

print(f"\n{'=' * 46}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 46}")
raise SystemExit(1 if fallos else 0)
