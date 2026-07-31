"""Prueba el circuito de las órdenes de trabajo contra la copia local."""

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
        print(f"  OK    {etiqueta} {detalle}")
    else:
        fallos += 1
        print(f"  FALLA {etiqueta} {detalle}")


print("1. Alta de una solicitud")
ot = sb.crear_solicitud("Sala 3", "No corta el agua la canilla del lavatorio", "ALTA",
                        "Franco", "franco@ejemplo.com", "interno 234")
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("se creó con numeración", ot.startswith("OT-"), f"-> {ot}")
check("nace SOLICITADA", o["ESTADO"] == "SOLICITADA")
check("guarda el área", o["AREA"] == "Sala 3")
check("guarda la prioridad", o["PRIORIDAD"] == "ALTA")
h = sb.get_ot_estados()
check("anota en la bitácora", len(h[h["ID_OT"] == ot]) == 1)

print("\n2. Asignación")
sb.asignar_orden(ot, "PLOMERÍA", "Bazan Ramiro", "URGENTE", "Serrano Juan")
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("pasa a ASIGNADA", o["ESTADO"] == "ASIGNADA")
check("guarda responsable", o["ASIGNADO_A"] == "Bazan Ramiro")
check("guarda sector", o["SECTOR_ASIGNADO"] == "PLOMERÍA")
check("actualiza prioridad", o["PRIORIDAD"] == "URGENTE")
check("registra fecha de asignación", bool(str(o["FECHA_ASIGNACION"]).strip()))

print("\n3. Seguimiento de estados")
sb.cambiar_estado_orden(ot, "EN CURSO", "Bazan Ramiro", "arranco ahora")
check("ASIGNADA -> EN CURSO", sb.get_ordenes().set_index("ID_OT").loc[ot, "ESTADO"] == "EN CURSO")
sb.cambiar_estado_orden(ot, "PAUSADA", "Bazan Ramiro", "falta un repuesto")
check("EN CURSO -> PAUSADA", sb.get_ordenes().set_index("ID_OT").loc[ot, "ESTADO"] == "PAUSADA")
sb.cambiar_estado_orden(ot, "EN CURSO", "Bazan Ramiro")
check("PAUSADA -> EN CURSO", sb.get_ordenes().set_index("ID_OT").loc[ot, "ESTADO"] == "EN CURSO")

try:
    sb.cambiar_estado_orden(ot, "SOLICITADA", "Bazan Ramiro")
    check("rechaza volver a SOLICITADA", False)
except ValueError as e:
    check("rechaza volver a SOLICITADA", True, f"-> {e}")

print("\n4. Cierre técnico")
try:
    sb.cerrar_orden(ot, "", "desgaste", 2, "Bazan Ramiro")
    check("exige contar el trabajo", False)
except ValueError:
    check("exige contar el trabajo", True)

sb.cerrar_orden(ot, "Se cambió el vástago y la arandela", "Desgaste del vástago", 1.5,
                "Bazan Ramiro")
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("queda RESUELTA", o["ESTADO"] == "RESUELTA")
check("guarda el trabajo", "vástago" in o["TRABAJO_REALIZADO"])
check("guarda la causa", o["CAUSA"] == "Desgaste del vástago")
check("guarda las horas", float(o["HORAS"]) == 1.5)
check("registra fecha de cierre", bool(str(o["FECHA_CIERRE"]).strip()))

try:
    sb.cambiar_estado_orden(ot, "EN CURSO", "Bazan Ramiro")
    check("una orden resuelta no se reabre", False)
except ValueError:
    check("una orden resuelta no se reabre", True)

print("\n5. Bitácora completa")
h = sb.get_ot_estados()
mia = h[h["ID_OT"] == ot]
secuencia = mia["ESTADO"].tolist()
check("guarda todos los pasos", len(mia) == 6, f"-> {secuencia}")

print("\n6. Anulación de otra orden")
ot2 = sb.crear_solicitud("Cocina", "Pierde agua la bacha", "BAJA", "Franco", "f@e.com")
sb.cambiar_estado_orden(ot2, "ANULADA", "Serrano Juan", "duplicada")
o2 = sb.get_ordenes().set_index("ID_OT").loc[ot2]
check("se puede anular", o2["ESTADO"] == "ANULADA")
check("numeración correlativa", ot2 != ot, f"-> {ot} y {ot2}")

print("\n7. La orden impresa")
import orden_impresa  # noqa: E402  (se importa acá para no cargarlo si no se prueba)

o3 = sb.get_ordenes().set_index("ID_OT", drop=False).loc[ot]
papel = orden_impresa.orden_en_html(o3, "Serrano Juan", "2026-07-31 10:00:00")
check("lleva el número de orden", ot in papel)
check("lleva el problema", "No corta el agua la canilla del lavatorio" in papel)
check("deja lugar para el trabajo hecho", "Trabajo realizado" in papel)
check("deja lugar para los materiales", "Materiales utilizados" in papel)
check("tiene la firma del operario", "Firma del operario" in papel)
check("tiene la conformidad del responsable", "Conformidad del responsable" in papel)
check("se abarca sola: no pide nada de afuera",
      "http://" not in papel and "https://" not in papel)
check("el nombre del archivo sale del número",
      orden_impresa.nombre_archivo(o3) == f"orden-{ot.lower()}.html")

# una descripción con < > no puede romper el HTML ni inyectar etiquetas
peligrosa = dict(o3)
peligrosa["DESCRIPCION"] = "<script>alert(1)</script> se rompió"
sucia = orden_impresa.orden_en_html(peligrosa)
check("escapa el HTML que venga de la planilla",
      "<script>" not in sucia and "&lt;script&gt;" in sucia)

print(f"\n{'=' * 48}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 48}")
raise SystemExit(1 if fallos else 0)
