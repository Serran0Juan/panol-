"""Repara los renglones ya cargados en "Registro APP".

Arregla dos cosas que hacen que el stock no se descuente:

  1. CANT y CANT_DEVUELTA quedaron guardadas como TEXTO ("1.0" en vez de 1).
     La planilla está en es_ES, donde el separador decimal es la coma, así que
     "1.0" no le parece un número. Los SUMIFS de "Inventario" lo suman como 0 y
     por eso Consumo da 0 y el Stock Actual nunca baja.
     (El origen estaba en sheets_backend._agregar_fila, ya corregido: ahora los
     números se mandan como números.)

  2. Varios ID_ITEM apuntan al producto equivocado. En algún momento se borraron
     6 filas de "Inventario" y se renumeró la columna Nro/SKU, así que los
     renglones viejos quedaron corridos (el corrimiento crece hacia abajo: -2,
     -3, -6 según el tramo). El renglón guarda también la descripción, y esa no
     se movió: se usa para volver a encontrar el SKU correcto.

Importante: los dos arreglos van juntos. Si solo se corrigieran los números, los
renglones mal apuntados empezarían a descontar del producto equivocado.

Uso:
    py -3 arreglar_registro.py            # simula y muestra qué cambiaría
    py -3 arreglar_registro.py --aplicar  # escribe en la planilla
"""

import datetime as dt
import json
import pathlib
import sys
import tomllib

import gspread
from google.oauth2.service_account import Credentials

BASE = pathlib.Path(__file__).parent
SECRETS = BASE / ".streamlit" / "secrets.toml"
BACKUP = BASE / "_backup"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

HOJA_REGISTRO = "Registro APP"
HOJA_INVENTARIO = "Inventario"
COL_ITEM, COL_CANT, COL_TIPO, COL_DESC, COL_DEVUELTA = 2, 3, 5, 6, 10  # base 0


def abrir():
    if not SECRETS.exists():
        raise SystemExit(f"Falta {SECRETS}. Ver SETUP.md, paso 3.")
    cfg = tomllib.loads(SECRETS.read_text(encoding="utf-8"))
    creds = Credentials.from_service_account_info(dict(cfg["gcp_service_account"]), scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(cfg["gcp"]["sheet_id"])


def a_numero(valor):
    """Lo mismo que hace la app al leer: acepta coma o punto decimal."""
    if isinstance(valor, bool) or valor is None:
        return 0
    if isinstance(valor, (int, float)):
        f = float(valor)
    else:
        t = str(valor).strip().replace(" ", "")
        if not t:
            return 0
        if "," in t and "." in t:
            t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
        elif "," in t:
            t = t.replace(",", ".")
        try:
            f = float(t)
        except ValueError:
            raise SystemExit(f"No se entiende la cantidad {valor!r}; revisar a mano.")
    return int(f) if f.is_integer() else f


def catalogo(ss):
    """SKU -> descripción y descripción (en minúsculas) -> SKU."""
    filas = ss.worksheet(HOJA_INVENTARIO).get("A1:B1000", value_render_option="UNFORMATTED_VALUE")
    por_sku, por_desc = {}, {}
    for f in filas[1:]:
        if not f or not str(f[0]).strip():
            continue
        sku = str(f[0]).strip()
        desc = str(f[1]).strip() if len(f) > 1 else ""
        if not desc:
            continue
        por_sku[sku] = desc
        por_desc.setdefault(desc.lower(), []).append(sku)
    return por_sku, por_desc


def planear(ss):
    """Devuelve (cambios, dudosos, filas). Un cambio por celda a reescribir."""
    por_sku, por_desc = catalogo(ss)
    filas = ss.worksheet(HOJA_REGISTRO).get("A1:L2000", value_render_option="UNFORMATTED_VALUE")

    cambios, dudosos = [], []
    for i, f in enumerate(filas[1:], start=2):  # i = fila real en la planilla
        if not f or not str(f[0]).strip():
            continue
        item = str(f[COL_ITEM]).strip() if len(f) > COL_ITEM else ""
        desc = str(f[COL_DESC]).strip() if len(f) > COL_DESC else ""
        cant = f[COL_CANT] if len(f) > COL_CANT else ""
        dev = f[COL_DEVUELTA] if len(f) > COL_DEVUELTA else ""

        # ── ID_ITEM: si la descripción del renglón no es la del SKU, se recupera
        if por_sku.get(item, "").lower() != desc.lower():
            candidatos = por_desc.get(desc.lower(), [])
            if len(candidatos) == 1:
                cambios.append((i, "C", int(candidatos[0]), f"ID_ITEM {item} -> {candidatos[0]}"))
            else:
                motivo = "ninguna descripción igual" if not candidatos else f"{len(candidatos)} productos con esa descripción"
                dudosos.append((i, item, desc, motivo))

        # ── CANT y CANT_DEVUELTA: de texto a número
        if isinstance(cant, str) and cant.strip() != "":
            cambios.append((i, "D", a_numero(cant), f"CANT {cant!r} -> número"))
        if isinstance(dev, str) and dev.strip() != "":
            cambios.append((i, "K", a_numero(dev), f"CANT_DEVUELTA {dev!r} -> número"))

    return cambios, dudosos, filas


def resumen_impacto(cambios, filas, ss):
    """Cuánto va a descontar cada producto una vez arreglado."""
    por_sku, _ = catalogo(ss)
    nuevo_item = {i: str(v) for i, col, v, _ in cambios if col == "C"}
    consumo, prestado = {}, {}
    for i, f in enumerate(filas[1:], start=2):
        if not f or not str(f[0]).strip():
            continue
        sku = nuevo_item.get(i, str(f[COL_ITEM]).strip())
        cant = a_numero(f[COL_CANT] if len(f) > COL_CANT else 0)
        dev = a_numero(f[COL_DEVUELTA] if len(f) > COL_DEVUELTA else 0)
        tipo = str(f[COL_TIPO]).strip().upper() if len(f) > COL_TIPO else ""
        estado = str(f[11]).strip().upper() if len(f) > 11 else ""
        if tipo == "CONSUMO":
            consumo[sku] = consumo.get(sku, 0) + cant - dev
        elif tipo == "PRESTADO" and estado == "PENDIENTE":
            prestado[sku] = prestado.get(sku, 0) + cant - dev
    return por_sku, consumo, prestado


def main(aplicar: bool):
    ss = abrir()
    cambios, dudosos, filas = planear(ss)

    print(f"Renglones leídos: {sum(1 for f in filas[1:] if f and str(f[0]).strip())}")
    print(f"Celdas a corregir: {len(cambios)}")
    ids = [c for c in cambios if c[1] == "C"]
    print(f"  · ID_ITEM mal apuntados: {len(ids)}")
    print(f"  · cantidades guardadas como texto: {len(cambios) - len(ids)}")

    if dudosos:
        print("\nSIN RESOLVER (hay que mirarlos a mano):")
        for fila, item, desc, motivo in dudosos:
            print(f"  fila {fila}: ID_ITEM={item} desc={desc!r} -> {motivo}")

    por_sku, consumo, prestado = resumen_impacto(cambios, filas, ss)
    print("\nDespués del arreglo, cada producto va a descontar:")
    for sku in sorted(set(consumo) | set(prestado), key=lambda s: int(s) if s.isdigit() else 0):
        c, p = consumo.get(sku, 0), prestado.get(sku, 0)
        if c or p:
            print(f"  SKU {sku:>4} {por_sku.get(sku, '??')[:45]:<47} consumo={c:g} prestado={p:g}")

    if not aplicar:
        print("\n(simulación: no se escribió nada. Correr con --aplicar para hacerlo)")
        return

    if dudosos:
        raise SystemExit("\nHay renglones sin resolver. Arreglarlos antes de aplicar.")

    BACKUP.mkdir(exist_ok=True)
    sello = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    destino = BACKUP / f"respaldo_registro_{sello}.json"
    crudo = ss.worksheet(HOJA_REGISTRO).get("A1:L2000", value_render_option="FORMULA")
    destino.write_text(json.dumps(crudo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nRespaldo de Registro APP en {destino.name}")

    ws = ss.worksheet(HOJA_REGISTRO)
    ws.batch_update([{"range": f"{col}{fila}", "values": [[valor]]}
                     for fila, col, valor, _ in cambios],
                    value_input_option="USER_ENTERED")
    print(f"Listo: {len(cambios)} celdas corregidas.")
    print("Las fórmulas de Inventario recalculan solas; puede tardar unos segundos.")


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
