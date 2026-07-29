"""Repone el encabezado REGISTRADO_POR en la hoja "Vales APP".

La columna guarda quién cargó cada vale. Se perdió al reemplazar la pestaña,
así que este script la vuelve a agregar al final, sin tocar las demás.

Uso:
    py -3 migracion_registrado_por.py
"""

import json
import pathlib
import tomllib

import gspread
from google.oauth2.service_account import Credentials

SECRETS = pathlib.Path(__file__).parent / ".streamlit" / "secrets.toml"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
COLUMNA = "REGISTRADO_POR"


def main():
    if not SECRETS.exists():
        raise SystemExit(f"Falta {SECRETS}. Ver SETUP.md, paso 3.")
    cfg = tomllib.loads(SECRETS.read_text(encoding="utf-8"))
    creds = Credentials.from_service_account_info(dict(cfg["gcp_service_account"]), scopes=SCOPES)
    ss = gspread.authorize(creds).open_by_key(cfg["gcp"]["sheet_id"])

    ws = ss.worksheet("Vales APP")
    encabezados = ws.row_values(1)
    print("encabezados actuales:", encabezados)

    if COLUMNA in encabezados:
        print(f"{COLUMNA} ya existe, no se toca nada.")
        return

    destino = len(encabezados) + 1
    letra = chr(64 + destino)
    ws.update(values=[[COLUMNA]], range_name=f"{letra}1")
    print(f"{COLUMNA} agregada en la columna {letra}")
    print("encabezados ahora:", ws.row_values(1))


if __name__ == "__main__":
    main()
