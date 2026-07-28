"""Migración única de la planilla: soporte para devoluciones parciales.

Qué hace:
  1. Agrega (si faltan) las columnas CANT_DEVUELTA y ESTADO_RENGLON al final
     de la hoja "Registro APP".
  2. Reescribe las fórmulas de "Inventario" en las columnas D, I, J y L para
     que descuenten lo que se devolvió:

       I (Consumo)            = entregado − devuelto        de renglones CONSUMO
       J (Préstamos pend.)    = entregado − devuelto        de renglones PRESTADO
                                aún marcados como PENDIENTE
       D (Stock Actual)       = C − I − J   (sin cambios de lógica)
       L (Total)              = D × K       (sin cambios de lógica)

El respaldo completo de fórmulas está en _backup/respaldo_formulas_*.json.
Para restaurar, correr este archivo con el argumento "restaurar".

Uso:
    py -3 migracion_formulas.py            # aplica la migración
    py -3 migracion_formulas.py restaurar  # vuelve al respaldo más reciente
"""

import json
import pathlib
import sys
import tomllib

import gspread
from google.oauth2.service_account import Credentials

SECRETS = pathlib.Path(__file__).parent / ".streamlit" / "secrets.toml"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]


def credenciales():
    """Lee el ID de la planilla y la cuenta de servicio de .streamlit/secrets.toml."""
    if not SECRETS.exists():
        raise SystemExit(f"Falta {SECRETS}. Ver SETUP.md, paso 3.")
    cfg = tomllib.loads(SECRETS.read_text(encoding="utf-8"))
    return cfg["gcp"]["sheet_id"], cfg["gcp_service_account"]

R = "'Registro APP'!"
CANT = f"{R}$D$2:$D$1999"
ITEM = f"{R}$C$2:$C$1999"
TIPO = f"{R}$F$2:$F$1999"
DEVUELTA = f"{R}$K$2:$K$1999"
ESTADO_RENGLON = f"{R}$L$2:$L$1999"


def abrir():
    sheet_id, cuenta = credenciales()
    creds = Credentials.from_service_account_info(dict(cuenta), scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(sheet_id)


def formula_consumo(n: int) -> str:
    """Consumo real: lo entregado menos el sobrante devuelto."""
    return (f'=SUMIFS({CANT};{ITEM};A{n};{TIPO};"CONSUMO")'
            f'-SUMIFS({DEVUELTA};{ITEM};A{n};{TIPO};"CONSUMO")')


def formula_prestamo(n: int) -> str:
    """Préstamos sin devolver: entregado menos devuelto, solo renglones pendientes."""
    return (f'=SUMIFS({CANT};{ITEM};A{n};{TIPO};"PRESTADO";{ESTADO_RENGLON};"PENDIENTE")'
            f'-SUMIFS({DEVUELTA};{ITEM};A{n};{TIPO};"PRESTADO";{ESTADO_RENGLON};"PENDIENTE")')


def migrar():
    ss = abrir()

    registro = ss.worksheet("Registro APP")
    encabezados = registro.row_values(1)
    faltantes = [c for c in ("CANT_DEVUELTA", "ESTADO_RENGLON") if c not in encabezados]
    if faltantes:
        desde = len(encabezados) + 1
        rango = f"{chr(64 + desde)}1:{chr(64 + desde + len(faltantes) - 1)}1"
        registro.update(values=[faltantes], range_name=rango)
        print(f"Registro APP: columnas agregadas {faltantes}")
    else:
        print("Registro APP: las columnas ya existían")

    inventario = ss.worksheet("Inventario")
    filas = inventario.get_all_values()
    ultima = max(i for i, f in enumerate(filas, start=1) if len(f) > 1 and str(f[1]).strip())
    print(f"Inventario: {ultima - 1} productos")

    inventario.batch_update([
        {"range": f"D2:D{ultima}", "values": [[f"=C{n}-I{n}-J{n}"] for n in range(2, ultima + 1)]},
        {"range": f"I2:I{ultima}", "values": [[formula_consumo(n)] for n in range(2, ultima + 1)]},
        {"range": f"J2:J{ultima}", "values": [[formula_prestamo(n)] for n in range(2, ultima + 1)]},
        {"range": f"L2:L{ultima}", "values": [[f"=D{n}*K{n}"] for n in range(2, ultima + 1)]},
    ], value_input_option="USER_ENTERED")
    print("Inventario: fórmulas D, I, J y L reescritas")


def restaurar():
    respaldos = sorted(pathlib.Path("_backup").glob("respaldo_formulas_*.json"))
    if not respaldos:
        raise SystemExit("No hay respaldos en _backup/")
    datos = json.loads(respaldos[-1].read_text(encoding="utf-8"))
    print(f"Restaurando desde {respaldos[-1].name}")

    ss = abrir()
    for nombre, filas in datos.items():
        if not filas:
            continue
        try:
            ws = ss.worksheet(nombre)
        except gspread.WorksheetNotFound:
            print(f"  {nombre}: no existe, se omite")
            continue
        ws.clear()
        ws.update(values=filas, range_name=f"A1", value_input_option="USER_ENTERED")
        print(f"  {nombre}: {len(filas)} filas restauradas")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restaurar":
        restaurar()
    else:
        migrar()
