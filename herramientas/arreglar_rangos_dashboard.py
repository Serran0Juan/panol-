"""Extiende los rangos del Dasboard para que no se queden cortos.

Las fórmulas del tablero de la planilla apuntaban hasta Inventario!$X$449,
pero el inventario ya pasa esa fila: los últimos materiales quedaban fuera
de los conteos y del valor total.

Se reemplaza ese tope por uno holgado, así el tablero acompaña el
crecimiento del inventario sin que haya que tocarlo de nuevo.

Uso:
    py -3 herramientas/arreglar_rangos_dashboard.py            # muestra qué cambiaría
    py -3 herramientas/arreglar_rangos_dashboard.py aplicar    # lo aplica
"""

import pathlib
import re
import sys
import tomllib

import gspread
from google.oauth2.service_account import Credentials

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SECRETS = RAIZ / ".streamlit" / "secrets.toml"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

HOJA = "Dasboard"
TOPE_NUEVO = 2000  # holgado: el inventario puede crecer sin tocar nada


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


def extender(formula: str) -> str:
    """Lleva a TOPE_NUEVO cualquier referencia Inventario!$X$n:$X$m corta."""
    def cambiar(m):
        col, desde, hasta = m.group(1), m.group(2), int(m.group(3))
        if hasta >= TOPE_NUEVO:
            return m.group(0)
        return f"Inventario!${col}${desde}:${col}${TOPE_NUEVO}"

    return re.sub(r"Inventario!\$([A-Z]+)\$(\d+):\$[A-Z]+\$(\d+)", cambiar, formula)


def main():
    aplicar = len(sys.argv) > 1 and sys.argv[1] == "aplicar"
    ws = abrir().worksheet(HOJA)
    filas = ws.get_all_values(value_render_option="FORMULA")

    cambios = []
    for i, fila in enumerate(filas, start=1):
        for j, celda in enumerate(fila):
            if not (isinstance(celda, str) and celda.startswith("=") and "Inventario!" in celda):
                continue
            nueva = extender(celda)
            if nueva != celda:
                cambios.append((f"{col_letra(j)}{i}", nueva))

    if not cambios:
        print("Los rangos ya estaban bien, no hay nada que cambiar.")
        return

    print(f"{len(cambios)} fórmula(s) con el rango corto:")
    for celda, _ in cambios[:8]:
        print(f"  {celda}")
    if len(cambios) > 8:
        print(f"  ... y {len(cambios) - 8} más")

    if not aplicar:
        print("\nEsto fue una vista previa. Para aplicarlo:")
        print("    py -3 herramientas/arreglar_rangos_dashboard.py aplicar")
        return

    ws.batch_update([{"range": celda, "values": [[formula]]} for celda, formula in cambios],
                    value_input_option="USER_ENTERED")
    print(f"\nListo: {len(cambios)} fórmula(s) extendidas hasta la fila {TOPE_NUEVO}.")


if __name__ == "__main__":
    main()
