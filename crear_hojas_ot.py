"""Crea (si faltan) y deja prolijas las pestañas del módulo de mantenimiento.

La app las crea sola cuando se usan por primera vez; este script además les
pone encabezado fijo, negrita, anchos razonables y listas desplegables.

Es seguro correrlo varias veces: si la pestaña ya existe, no borra nada.

Uso:
    py -3 crear_hojas_ot.py
"""

import pathlib
import tomllib

import gspread
from google.oauth2.service_account import Credentials

from sheets_backend import (COLS_ORDENES, COLS_OT_ESTADOS, ESTADOS_OT, HOJA_ORDENES,
                            HOJA_OT_ESTADOS, PRIORIDADES)

SECRETS = pathlib.Path(__file__).parent / ".streamlit" / "secrets.toml"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

AZUL = {"red": 0.055, "green": 0.125, "blue": 0.22}
BLANCO = {"red": 1, "green": 1, "blue": 1}

# columna interna -> ancho en píxeles
ANCHOS_ORDENES = {
    "ID_OT": 90, "FECHA_ALTA": 145, "SOLICITANTE": 150, "SOLICITANTE_EMAIL": 220,
    "AREA": 130, "DESCRIPCION": 380, "PRIORIDAD": 95, "SECTOR_ASIGNADO": 130,
    "ASIGNADO_A": 150, "ESTADO": 110, "FECHA_ASIGNACION": 145, "FECHA_CIERRE": 145,
    "TRABAJO_REALIZADO": 380, "CAUSA": 220, "HORAS": 70, "VALE_REF": 90,
    "OBSERVACIONES": 220, "FECHA_COMPROMISO": 130, "FECHA_PROGRAMADA": 130,
    "HORAS_ESTIMADAS": 105,
}
ANCHOS_ESTADOS = {"ID": 60, "ID_OT": 90, "FECHA_HORA": 145, "ESTADO": 110,
                  "USUARIO": 160, "NOTA": 420}


def abrir():
    if not SECRETS.exists():
        raise SystemExit(f"Falta {SECRETS}. Ver SETUP.md, paso 3.")
    cfg = tomllib.loads(SECRETS.read_text(encoding="utf-8"))
    creds = Credentials.from_service_account_info(dict(cfg["gcp_service_account"]), scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(cfg["gcp"]["sheet_id"])


def col_letra(idx: int) -> str:
    letra = ""
    idx += 1
    while idx:
        idx, resto = divmod(idx - 1, 26)
        letra = chr(65 + resto) + letra
    return letra


def preparar(ss, nombre, columnas, anchos, validaciones):
    try:
        ws = ss.worksheet(nombre)
        print(f"{nombre}: ya existía")
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=nombre, rows=2000, cols=len(columnas))
        print(f"{nombre}: creada")

    actuales = ws.row_values(1)
    if actuales != columnas:
        ws.update(values=[columnas], range_name=f"A1:{col_letra(len(columnas) - 1)}1")
        print(f"  encabezados escritos ({len(columnas)} columnas)")

    ws.freeze(rows=1)
    ws.format(f"A1:{col_letra(len(columnas) - 1)}1", {
        "backgroundColor": AZUL,
        "textFormat": {"bold": True, "foregroundColor": BLANCO, "fontSize": 10},
        "horizontalAlignment": "LEFT",
        "verticalAlignment": "MIDDLE",
    })

    peticiones = []
    hoja_id = ws.id
    for columna, ancho in anchos.items():
        if columna not in columnas:
            continue
        i = columnas.index(columna)
        peticiones.append({"updateDimensionProperties": {
            "range": {"sheetId": hoja_id, "dimension": "COLUMNS",
                      "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": ancho}, "fields": "pixelSize"}})

    for columna, opciones in validaciones.items():
        if columna not in columnas:
            continue
        i = columnas.index(columna)
        peticiones.append({"setDataValidation": {
            "range": {"sheetId": hoja_id, "startRowIndex": 1, "endRowIndex": 2000,
                      "startColumnIndex": i, "endColumnIndex": i + 1},
            "rule": {
                "condition": {"type": "ONE_OF_LIST",
                              "values": [{"userEnteredValue": v} for v in opciones]},
                "showCustomUi": True, "strict": False,
            }}})

    if peticiones:
        ss.batch_update({"requests": peticiones})
        print(f"  formato aplicado ({len(peticiones)} ajustes)")
    return ws


def main():
    ss = abrir()
    print(f"planilla: {ss.title}\n")

    preparar(ss, HOJA_ORDENES, COLS_ORDENES, ANCHOS_ORDENES,
             {"ESTADO": ESTADOS_OT, "PRIORIDAD": PRIORIDADES})
    preparar(ss, HOJA_OT_ESTADOS, COLS_OT_ESTADOS, ANCHOS_ESTADOS,
             {"ESTADO": ESTADOS_OT})

    print("\npestañas de la planilla:", [w.title for w in ss.worksheets()])


if __name__ == "__main__":
    main()
