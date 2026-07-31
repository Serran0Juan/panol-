"""Prueba los vencimientos automáticos, la agenda y la carga de trabajo."""

import datetime as dt
import logging
import os
import warnings

os.environ["PANOL_MODO_LOCAL"] = "1"
warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import sheets_backend as sb  # noqa: E402

if sb.usando_sheets_reales():
    raise SystemExit("ABORTADO: la prueba iba a escribir en la planilla real.")

# arranca siempre de cero: si no, las órdenes de una corrida anterior
# desvirtúan los conteos de los indicadores
for hoja in (sb.HOJA_ORDENES, sb.HOJA_OT_ESTADOS):
    (sb.DEVDATA_DIR / f"{hoja}.csv").unlink(missing_ok=True)
sb.limpiar_cache()

ok = fallos = 0


def check(etiqueta, condicion, detalle=""):
    global ok, fallos
    if condicion:
        ok += 1
        print(f"  OK    {etiqueta} {detalle}")
    else:
        fallos += 1
        print(f"  FALLA {etiqueta} {detalle}")


hoy = sb.hoy()

print("1. Plazo automático según la prioridad")
base = sb.ahora()
for prioridad, dias in sb.SLA_DIAS.items():
    esperado = (base + dt.timedelta(days=dias)).strftime("%Y-%m-%d")
    check(f"{prioridad} -> {dias} día(s)",
          sb.calcular_compromiso(prioridad, base) == esperado)

print("\n2. Al asignar se calcula el vencimiento solo")
ot = sb.crear_solicitud("Sala 5", "Pierde la cañería del baño", "ALTA",
                        "Franco", "f@e.com")
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("nace sin vencimiento", not str(o["FECHA_COMPROMISO"]).strip())

sb.asignar_orden(ot, "PLOMERÍA", "Bazan Ramiro", "ALTA", "Serrano Juan")
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("queda con vencimiento", bool(str(o["FECHA_COMPROMISO"]).strip()),
      f"-> {o['FECHA_COMPROMISO']}")
check("son 3 días (prioridad ALTA)", o["dias_para_vencer"] == 3,
      f"-> faltan {o['dias_para_vencer']}")
check("toma horas estimadas por defecto",
      float(o["HORAS_ESTIMADAS"]) == sb.HORAS_ESTIMADAS_DEFECTO)
check("todavía no está vencida", not o["vencida"])

print("\n3. Al subir la prioridad se acorta el plazo")
sb.asignar_orden(ot, "PLOMERÍA", "Bazan Ramiro", "URGENTE", "Serrano Juan")
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("URGENTE vence hoy", o["dias_para_vencer"] == 0, f"-> {o['dias_para_vencer']}")
check("marca que vence hoy", bool(o["vence_hoy"]))

print("\n4. Se puede pisar la fecha a mano")
otra = (hoy + dt.timedelta(days=20)).strftime("%Y-%m-%d")
sb.asignar_orden(ot, "PLOMERÍA", "Bazan Ramiro", "URGENTE", "Serrano Juan",
                 fecha_compromiso=otra, horas_estimadas=4)
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("respeta la fecha elegida", o["FECHA_COMPROMISO"] == otra, f"-> {otra}")
check("respeta las horas cargadas", float(o["HORAS_ESTIMADAS"]) == 4)

print("\n5. Detección de vencidas")
vieja = sb.crear_solicitud("Cocina", "No anda el extractor", "MEDIA", "Franco", "f@e.com")
sb.asignar_orden(vieja, "ELECTRICIDAD", "Valentin Rondan", "MEDIA", "Serrano Juan",
                 fecha_compromiso=(hoy - dt.timedelta(days=4)).strftime("%Y-%m-%d"))
o = sb.get_ordenes().set_index("ID_OT").loc[vieja]
check("la marca vencida", bool(o["vencida"]))
check("cuenta 4 días de atraso", o["dias_para_vencer"] == -4, f"-> {o['dias_para_vencer']}")

print("\n6. Agenda")
sb.programar_orden(ot, hoy.strftime("%Y-%m-%d"), "Serrano Juan", 3)
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("queda programada para hoy", o["dia_programado"] == hoy)
check("actualiza las horas", float(o["HORAS_ESTIMADAS"]) == 3)

sb.programar_orden(ot, "", "Serrano Juan")
o = sb.get_ordenes().set_index("ID_OT").loc[ot]
check("se puede sacar de la agenda", o["dia_programado"] is None)

print("\n7. Carga de trabajo por persona")
sb.programar_orden(ot, hoy.strftime("%Y-%m-%d"), "Serrano Juan", 3)
carga = sb.carga_por_persona(sb.get_ordenes())
bazan = carga[carga["persona"] == "Bazan Ramiro"]
check("aparece cada responsable", not bazan.empty)
if not bazan.empty:
    check("suma sus horas", float(bazan.iloc[0]["horas"]) == 3,
          f"-> {bazan.iloc[0]['horas']}")
    esperada = round(3 / (sb.HORAS_JORNADA * 5), 2)
    check("calcula la ocupación", float(bazan.iloc[0]["capacidad"]) == esperada,
          f"-> {bazan.iloc[0]['capacidad']}")
valentin = carga[carga["persona"] == "Valentin Rondan"]
check("cuenta las vencidas de cada uno",
      not valentin.empty and int(valentin.iloc[0]["vencidas"]) == 1)

print("\n8. Indicadores de jefatura")
sb.cambiar_estado_orden(vieja, "EN CURSO", "Valentin Rondan")
sb.cerrar_orden(vieja, "Se cambió el capacitor del extractor", "Desgaste", 2,
                "Valentin Rondan")
ind = sb.indicadores_mantenimiento(sb.get_ordenes())
check("cuenta las resueltas", ind["resueltas"] == 1, f"-> {ind['resueltas']}")
check("cuenta las abiertas", ind["abiertas"] == 1, f"-> {ind['abiertas']}")
check("suma las horas trabajadas", ind["horas_cerradas"] == 2)
check("calcula el cumplimiento", ind["cumplimiento"] == 0,
      f"-> {ind['cumplimiento']}% (se cerró fuera de plazo)")
check("calcula días promedio", ind["dias_promedio"] is not None,
      f"-> {ind['dias_promedio']}")
check("una orden cerrada ya no figura vencida", ind["vencidas"] == 0)

print(f"\n{'=' * 48}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 48}")
raise SystemExit(1 if fallos else 0)
