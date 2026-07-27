"""Capa de acceso a datos, mapeada contra el Google Sheet real del pañol.

Pestañas que usa (nombres tal cual están en la planilla):
  - "Inventario"    : catálogo de productos (fuente de verdad del stock)
  - "Vales APP"     : cabecera de cada movimiento (un vale = una entrega/préstamo)
  - "Registro APP"  : renglones de cada vale (un renglón por producto)
  - "Parametros"    : listas desplegables (tipos de movimiento, sectores, unidades...)
  - "Plano Pañol"   : catálogo de las 35 estanterías y qué guarda cada una
  - "Usuarios"      : quién puede entrar a la app (la crea la app si no existe)
  - "Reclamos"      : pedidos/quejas de los operarios (la crea la app si no existe)

Si no hay credenciales configuradas todavía, trabaja contra una copia local de la
planilla (_devdata/) para poder probar sin tocar los datos reales.
"""

import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

DEVDATA_DIR = Path(__file__).parent / "_devdata"
SEED_XLSX = DEVDATA_DIR / "seed_sheet.xlsx"

HOJA_INVENTARIO = "Inventario"
HOJA_VALES = "Vales APP"
HOJA_REGISTRO = "Registro APP"
HOJA_PARAMETROS = "Parametros"
HOJA_PLANO = "Plano Pañol"
HOJA_USUARIOS = "Usuarios"
HOJA_RECLAMOS = "Reclamos"

# nombre interno -> encabezado exacto en la planilla
COLS_INVENTARIO = {
    "id": "Nro/SKU",
    "descripcion": "Descripción del Producto",
    "stock_inicial": "Stock Inicial",
    "stock_actual": "Stock Actual",
    "unidad": "Unidad",
    "ubicacion": "Ubicación",
    "estado_hoja": "Estado/Alerta",
    "stock_minimo": "Stock Minimo",
    "consumo": "Consumo",
    "prestamos_pendiente": "Prestamos Pendiente",
    "precio_unitario": "Precio Unitario",
    "total": "Total",
    "categoria": "Categoria/Area",
    "subcategoria": "Subcategoria",
}
# Columnas de "Inventario" que la app puede escribir (el resto son fórmulas de la planilla).
INVENTARIO_ESCRIBIBLES = {"descripcion", "stock_actual", "unidad", "ubicacion", "stock_minimo",
                          "precio_unitario", "categoria", "subcategoria"}

COLS_VALES = ["ID VALE", "FECHA HORA", "TIPO MOVIMIENTO", "SECTOR", "ÁREA / SALA",
              "Receptor / Para Quien", "OBSERVACIONES", "ESTADO VALE", "DIAS RETRASO"]
COLS_REGISTRO = ["ID_REGISTRO", "ID_VALE_REF", "ID_ITEM", "CANT", "UNIDAD", "TIPO_MOV",
                 "DESCRIPCIÓN_ITEM", "FECHA_VALE", "OBSERVACIONES", "ESTADO_VALE (auto)"]
COLS_USUARIOS = ["EMAIL", "NOMBRE", "ROL", "SECTOR", "ACTIVO", "PASSWORD_HASH"]
COLS_RECLAMOS = ["ID", "FECHA_HORA", "TIPO", "PRODUCTO", "DETALLE", "EMAIL", "NOMBRE", "ESTADO", "RESPUESTA"]

TIPOS_MOVIMIENTO = ["CONSUMO", "PRESTADO", "DEVOLUCION", "INGRESO"]
# efecto de cada tipo sobre el stock
DELTA_STOCK = {"INGRESO": 1, "DEVOLUCION": 1, "CONSUMO": -1, "PRESTADO": -1}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

ADMIN_INICIAL = ("juaniserrano410@gmail.com", "Serrano Juan", "ADMIN", "MANTENIMIENTO")


def usando_sheets_reales() -> bool:
    try:
        return "gcp_service_account" in st.secrets and "gcp" in st.secrets
    except Exception:
        return False


# ------------------------------------------------------------------ Google Sheets

@st.cache_resource(show_spinner=False)
def _spreadsheet():
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(st.secrets["gcp"]["sheet_id"])


def _ws(nombre: str, crear_con=None):
    """Devuelve la hoja. Si no existe y se pasan encabezados, la crea (solo hojas propias de la app)."""
    ss = _spreadsheet()
    try:
        return ss.worksheet(nombre)
    except Exception:
        if crear_con is None:
            raise
        ws = ss.add_worksheet(title=nombre, rows=1000, cols=max(10, len(crear_con)))
        ws.append_row(crear_con)
        if nombre == HOJA_USUARIOS:
            ws.append_row([ADMIN_INICIAL[0], ADMIN_INICIAL[1], ADMIN_INICIAL[2],
                           ADMIN_INICIAL[3], "TRUE", ""])
        return ws


def _leer_hoja(nombre: str, crear_con=None) -> pd.DataFrame:
    valores = _ws(nombre, crear_con).get_all_values()
    if len(valores) < 2:
        return pd.DataFrame(columns=valores[0] if valores else (crear_con or []))
    encabezados = valores[0]
    ancho = len(encabezados)
    filas = [(f + [""] * ancho)[:ancho] for f in valores[1:]]
    return pd.DataFrame(filas, columns=encabezados)


def _col_letra(idx: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    letra = ""
    idx += 1
    while idx:
        idx, resto = divmod(idx - 1, 26)
        letra = chr(65 + resto) + letra
    return letra


# ------------------------------------------------------------- Fallback local (dev)

def _leer_local(nombre: str, crear_con=None) -> pd.DataFrame:
    import openpyxl

    csv = DEVDATA_DIR / f"{nombre}.csv"
    if csv.exists():
        return pd.read_csv(csv, dtype=str).fillna("")

    if SEED_XLSX.exists():
        wb = openpyxl.load_workbook(SEED_XLSX, data_only=True)
        if nombre in wb.sheetnames:
            ws = wb[nombre]
            valores = [["" if v is None else str(v) for v in r] for r in ws.iter_rows(values_only=True)]
            if nombre == HOJA_PLANO:
                df = pd.DataFrame(valores)
            else:
                encabezados = valores[0]
                ancho = len(encabezados)
                filas = [(f + [""] * ancho)[:ancho] for f in valores[1:]]
                df = pd.DataFrame(filas, columns=encabezados)
                df = df[df.apply(lambda r: any(str(v).strip() for v in r), axis=1)]
            df.to_csv(csv, index=False)
            return df

    df = pd.DataFrame(columns=crear_con or [])
    if nombre == HOJA_USUARIOS:
        df = pd.DataFrame([{"EMAIL": ADMIN_INICIAL[0], "NOMBRE": ADMIN_INICIAL[1], "ROL": ADMIN_INICIAL[2],
                            "SECTOR": ADMIN_INICIAL[3], "ACTIVO": "TRUE", "PASSWORD_HASH": ""}],
                          columns=COLS_USUARIOS)
    DEVDATA_DIR.mkdir(exist_ok=True)
    df.to_csv(csv, index=False)
    return df


def _guardar_local(nombre: str, df: pd.DataFrame):
    DEVDATA_DIR.mkdir(exist_ok=True)
    df.to_csv(DEVDATA_DIR / f"{nombre}.csv", index=False)


def _leer(nombre: str, crear_con=None) -> pd.DataFrame:
    if usando_sheets_reales():
        return _leer_hoja(nombre, crear_con)
    return _leer_local(nombre, crear_con)


def _agregar_fila(nombre: str, fila: dict, columnas: list):
    if usando_sheets_reales():
        _ws(nombre, columnas).append_row([str(fila.get(c, "")) for c in columnas],
                                         value_input_option="USER_ENTERED")
    else:
        df = _leer_local(nombre, columnas)
        nueva = {c: str(fila.get(c, "")) for c in (df.columns if len(df.columns) else columnas)}
        df = pd.concat([df.astype(str), pd.DataFrame([nueva])], ignore_index=True).fillna("")
        _guardar_local(nombre, df)


def limpiar_cache():
    st.cache_data.clear()


# ------------------------------------------------------------------ Inventario

def _estado(stock_actual: float, stock_minimo: float) -> str:
    if stock_actual <= 0:
        return "🔴 Sin stock"
    if stock_actual <= stock_minimo:
        return "🟡 Mínimo"
    return "🟢 OK"


@st.cache_data(ttl=30, show_spinner=False)
def get_items() -> pd.DataFrame:
    crudo = _leer(HOJA_INVENTARIO)
    if crudo.empty:
        return pd.DataFrame(columns=list(COLS_INVENTARIO))

    df = pd.DataFrame()
    for interno, encabezado in COLS_INVENTARIO.items():
        df[interno] = crudo[encabezado] if encabezado in crudo.columns else ""

    df["_fila"] = range(2, len(df) + 2)  # fila real en la planilla (encabezado = 1)
    df = df[df["descripcion"].astype(str).str.strip() != ""]

    for c in ["id", "stock_actual", "stock_minimo", "precio_unitario", "stock_inicial"]:
        df[c] = pd.to_numeric(
            df[c].astype(str).str.replace(r"[^\d,.\-]", "", regex=True).str.replace(",", ".", regex=False),
            errors="coerce",
        ).fillna(0)
    df["id"] = df["id"].astype(int)

    for c in ["descripcion", "categoria", "subcategoria", "unidad", "ubicacion"]:
        df[c] = df[c].astype(str).str.strip()

    df["estado"] = [_estado(a, m) for a, m in zip(df["stock_actual"], df["stock_minimo"])]
    df["valor"] = df["stock_actual"] * df["precio_unitario"]
    return df.reset_index(drop=True)


def update_item(item_id: int, **cambios):
    """Actualiza celdas puntuales de un producto, sin pisar las columnas con fórmulas."""
    items = get_items()
    fila = items[items["id"] == item_id]
    if fila.empty:
        raise ValueError(f"No existe el producto {item_id}")
    cambios = {k: v for k, v in cambios.items() if k in INVENTARIO_ESCRIBIBLES}
    if not cambios:
        return

    if usando_sheets_reales():
        ws = _ws(HOJA_INVENTARIO)
        encabezados = ws.row_values(1)
        nro_fila = int(fila.iloc[0]["_fila"])
        actualizaciones = []
        for interno, valor in cambios.items():
            encabezado = COLS_INVENTARIO[interno]
            if encabezado not in encabezados:
                continue
            letra = _col_letra(encabezados.index(encabezado))
            actualizaciones.append({"range": f"{letra}{nro_fila}", "values": [[valor]]})
        if actualizaciones:
            ws.batch_update(actualizaciones, value_input_option="USER_ENTERED")
    else:
        crudo = _leer_local(HOJA_INVENTARIO)
        idx = int(fila.iloc[0]["_fila"]) - 2
        for interno, valor in cambios.items():
            columna = COLS_INVENTARIO[interno]
            crudo[columna] = crudo[columna].astype(str)
            crudo.at[idx, columna] = str(valor)
        _guardar_local(HOJA_INVENTARIO, crudo)

    limpiar_cache()


def add_item(descripcion, categoria, subcategoria, unidad, ubicacion,
             stock_minimo, stock_actual, precio_unitario):
    items = get_items()
    nuevo_id = int(items["id"].max()) + 1 if not items.empty else 1
    fila = {
        COLS_INVENTARIO["id"]: nuevo_id,
        COLS_INVENTARIO["descripcion"]: descripcion,
        COLS_INVENTARIO["stock_inicial"]: stock_actual,
        COLS_INVENTARIO["stock_actual"]: stock_actual,
        COLS_INVENTARIO["unidad"]: unidad,
        COLS_INVENTARIO["ubicacion"]: ubicacion,
        COLS_INVENTARIO["stock_minimo"]: stock_minimo,
        COLS_INVENTARIO["precio_unitario"]: precio_unitario,
        COLS_INVENTARIO["categoria"]: categoria,
        COLS_INVENTARIO["subcategoria"]: subcategoria,
    }
    columnas = list(COLS_INVENTARIO.values())
    _agregar_fila(HOJA_INVENTARIO, fila, columnas)
    limpiar_cache()
    return nuevo_id


# ------------------------------------------------------------------ Vales / movimientos

@st.cache_data(ttl=15, show_spinner=False)
def get_vales() -> pd.DataFrame:
    df = _leer(HOJA_VALES, COLS_VALES)
    if df.empty:
        return pd.DataFrame(columns=COLS_VALES)
    return df[df["ID VALE"].astype(str).str.strip() != ""].reset_index(drop=True)


@st.cache_data(ttl=15, show_spinner=False)
def get_registro() -> pd.DataFrame:
    df = _leer(HOJA_REGISTRO, COLS_REGISTRO)
    if df.empty:
        return pd.DataFrame(columns=COLS_REGISTRO)
    df = df[df["ID_REGISTRO"].astype(str).str.strip() != ""].copy()
    for c in ["ID_ITEM", "CANT"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df.reset_index(drop=True)


def _siguiente_id_vale() -> str:
    vales = get_vales()
    nums = pd.to_numeric(
        vales["ID VALE"].astype(str).str.extract(r"(\d+)", expand=False), errors="coerce"
    ).dropna() if not vales.empty else pd.Series(dtype=float)
    return f"V-{int(nums.max()) + 1 if len(nums) else 1:04d}"


def _siguiente_id_registro() -> int:
    reg = get_registro()
    if reg.empty:
        return 1
    nums = pd.to_numeric(reg["ID_REGISTRO"], errors="coerce").dropna()
    return int(nums.max()) + 1 if len(nums) else 1


def registrar_vale(tipo, sector, area_sala, receptor, observaciones, renglones,
                   fecha_dev_esperada=""):
    """Crea un vale con uno o más renglones y ajusta el stock de cada producto.

    renglones: lista de dicts con item_id, descripcion, cantidad, unidad.
    Devuelve el ID del vale creado.
    """
    if not renglones:
        raise ValueError("El vale no tiene renglones")

    id_vale = _siguiente_id_vale()
    ahora = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_vale = "ABIERTO" if tipo == "PRESTADO" else "CERRADO"

    _agregar_fila(HOJA_VALES, {
        "ID VALE": id_vale, "FECHA HORA": ahora, "TIPO MOVIMIENTO": tipo,
        "SECTOR": sector, "ÁREA / SALA": area_sala, "Receptor / Para Quien": receptor,
        "OBSERVACIONES": observaciones, "ESTADO VALE": estado_vale, "DIAS RETRASO": "",
    }, COLS_VALES)

    id_reg = _siguiente_id_registro()
    items = get_items()
    for r in renglones:
        _agregar_fila(HOJA_REGISTRO, {
            "ID_REGISTRO": id_reg, "ID_VALE_REF": id_vale, "ID_ITEM": r["item_id"],
            "CANT": r["cantidad"], "UNIDAD": r.get("unidad", ""), "TIPO_MOV": tipo,
            "DESCRIPCIÓN_ITEM": r["descripcion"], "FECHA_VALE": ahora,
            "OBSERVACIONES": observaciones, "ESTADO_VALE (auto)": estado_vale,
        }, COLS_REGISTRO)
        id_reg += 1

        fila = items[items["id"] == r["item_id"]]
        if not fila.empty:
            actual = float(fila.iloc[0]["stock_actual"])
            nuevo = max(0.0, actual + DELTA_STOCK.get(tipo, 0) * float(r["cantidad"]))
            update_item(int(r["item_id"]), stock_actual=nuevo)

    limpiar_cache()
    return id_vale


def cerrar_vale(id_vale: str):
    """Marca un préstamo como devuelto y repone el stock de sus renglones."""
    reg = get_registro()
    renglones = reg[reg["ID_VALE_REF"] == id_vale]
    items = get_items()

    for r in renglones.itertuples():
        fila = items[items["id"] == int(r.ID_ITEM)]
        if not fila.empty:
            nuevo = float(fila.iloc[0]["stock_actual"]) + float(r.CANT)
            update_item(int(r.ID_ITEM), stock_actual=nuevo)

    if usando_sheets_reales():
        ws = _ws(HOJA_VALES)
        celda = ws.find(id_vale, in_column=1)
        if celda:
            col = _col_letra(COLS_VALES.index("ESTADO VALE"))
            ws.update(f"{col}{celda.row}", [["CERRADO"]])
        ws_reg = _ws(HOJA_REGISTRO)
        col_ref = COLS_REGISTRO.index("ID_VALE_REF") + 1
        col_est = _col_letra(COLS_REGISTRO.index("ESTADO_VALE (auto)"))
        for celda_reg in ws_reg.findall(id_vale, in_column=col_ref):
            ws_reg.update(f"{col_est}{celda_reg.row}", [["CERRADO"]])
    else:
        vales = _leer_local(HOJA_VALES, COLS_VALES)
        vales.loc[vales["ID VALE"] == id_vale, "ESTADO VALE"] = "CERRADO"
        _guardar_local(HOJA_VALES, vales)
        regl = _leer_local(HOJA_REGISTRO, COLS_REGISTRO)
        regl.loc[regl["ID_VALE_REF"] == id_vale, "ESTADO_VALE (auto)"] = "CERRADO"
        _guardar_local(HOJA_REGISTRO, regl)

    limpiar_cache()


# ------------------------------------------------------------------ Usuarios

@st.cache_data(ttl=30, show_spinner=False)
def get_usuarios() -> pd.DataFrame:
    df = _leer(HOJA_USUARIOS, COLS_USUARIOS)
    if df.empty:
        return pd.DataFrame(columns=COLS_USUARIOS)
    for c in COLS_USUARIOS:
        if c not in df.columns:
            df[c] = ""
    df = df[df["EMAIL"].astype(str).str.strip() != ""]
    return df[COLS_USUARIOS].reset_index(drop=True)


def get_usuarios_activos() -> list:
    df = get_usuarios()
    if df.empty:
        return []
    activos = df[df["ACTIVO"].astype(str).str.upper().isin(["TRUE", "1", "SI", "SÍ", "VERDADERO"])]
    return activos.to_dict("records")


def add_usuario(email, nombre, rol, sector, password_hash=""):
    _agregar_fila(HOJA_USUARIOS, {
        "EMAIL": email.strip().lower(), "NOMBRE": nombre, "ROL": rol,
        "SECTOR": sector, "ACTIVO": "TRUE", "PASSWORD_HASH": password_hash,
    }, COLS_USUARIOS)
    limpiar_cache()


def set_password_hash(email: str, password_hash: str):
    email = email.strip().lower()
    if usando_sheets_reales():
        ws = _ws(HOJA_USUARIOS, COLS_USUARIOS)
        encabezados = ws.row_values(1)
        celda = ws.find(email, in_column=1)
        if celda is None:
            raise ValueError(f"No se encontró el usuario {email}")
        letra = _col_letra(encabezados.index("PASSWORD_HASH"))
        ws.update(f"{letra}{celda.row}", [[password_hash]])
    else:
        df = _leer_local(HOJA_USUARIOS, COLS_USUARIOS)
        df.loc[df["EMAIL"].astype(str).str.lower() == email, "PASSWORD_HASH"] = password_hash
        _guardar_local(HOJA_USUARIOS, df)
    limpiar_cache()


def set_usuario_activo(email: str, activo: bool):
    email = email.strip().lower()
    valor = "TRUE" if activo else "FALSE"
    if usando_sheets_reales():
        ws = _ws(HOJA_USUARIOS, COLS_USUARIOS)
        encabezados = ws.row_values(1)
        celda = ws.find(email, in_column=1)
        if celda:
            ws.update(f"{_col_letra(encabezados.index('ACTIVO'))}{celda.row}", [[valor]])
    else:
        df = _leer_local(HOJA_USUARIOS, COLS_USUARIOS)
        df.loc[df["EMAIL"].astype(str).str.lower() == email, "ACTIVO"] = valor
        _guardar_local(HOJA_USUARIOS, df)
    limpiar_cache()


# ------------------------------------------------------------------ Reclamos

@st.cache_data(ttl=15, show_spinner=False)
def get_reclamos() -> pd.DataFrame:
    df = _leer(HOJA_RECLAMOS, COLS_RECLAMOS)
    if df.empty:
        return pd.DataFrame(columns=COLS_RECLAMOS)
    return df[df["ID"].astype(str).str.strip() != ""].reset_index(drop=True)


def add_reclamo(tipo, producto, detalle, email, nombre):
    reclamos = get_reclamos()
    nums = pd.to_numeric(reclamos["ID"], errors="coerce").dropna() if not reclamos.empty else pd.Series(dtype=float)
    nuevo_id = int(nums.max()) + 1 if len(nums) else 1
    _agregar_fila(HOJA_RECLAMOS, {
        "ID": nuevo_id, "FECHA_HORA": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "TIPO": tipo, "PRODUCTO": producto, "DETALLE": detalle,
        "EMAIL": email, "NOMBRE": nombre, "ESTADO": "ABIERTO", "RESPUESTA": "",
    }, COLS_RECLAMOS)
    limpiar_cache()


def responder_reclamo(reclamo_id, estado, respuesta):
    if usando_sheets_reales():
        ws = _ws(HOJA_RECLAMOS, COLS_RECLAMOS)
        encabezados = ws.row_values(1)
        celda = ws.find(str(reclamo_id), in_column=1)
        if celda:
            ws.batch_update([
                {"range": f"{_col_letra(encabezados.index('ESTADO'))}{celda.row}", "values": [[estado]]},
                {"range": f"{_col_letra(encabezados.index('RESPUESTA'))}{celda.row}", "values": [[respuesta]]},
            ], value_input_option="USER_ENTERED")
    else:
        df = _leer_local(HOJA_RECLAMOS, COLS_RECLAMOS)
        mask = df["ID"].astype(str) == str(reclamo_id)
        df.loc[mask, "ESTADO"] = estado
        df.loc[mask, "RESPUESTA"] = respuesta
        _guardar_local(HOJA_RECLAMOS, df)
    limpiar_cache()


# ------------------------------------------------------------------ Parámetros y plano

@st.cache_data(ttl=300, show_spinner=False)
def get_parametros() -> dict:
    """Devuelve {columna: [valores no vacíos]} de la hoja Parametros."""
    df = _leer(HOJA_PARAMETROS)
    if df.empty:
        return {}
    return {c: [v for v in df[c].astype(str).str.strip().tolist() if v] for c in df.columns}


@st.cache_data(ttl=300, show_spinner=False)
def get_estanterias() -> pd.DataFrame:
    """Catálogo de estanterías del pañol (número, medidas, área y qué guarda)."""
    crudo = _leer(HOJA_PLANO)
    if crudo.empty:
        return pd.DataFrame(columns=["estanteria", "ancho", "profundidad", "estantes", "area", "objetos"])

    filas = []
    for fila in crudo.itertuples(index=False):
        vals = ["" if pd.isna(v) else str(v).strip() for v in fila]
        vals += [""] * (10 - len(vals))
        estanteria = vals[1]
        if not estanteria or estanteria.lower().startswith("estanteria"):
            continue
        filas.append({
            "estanteria": estanteria.zfill(2) if estanteria.isdigit() else estanteria,
            "ancho": vals[2], "profundidad": vals[3], "estantes": vals[4],
            "area": vals[5], "objetos": vals[9],
        })
    return pd.DataFrame(filas)


def numero_estanteria(ubicacion: str) -> str:
    """Extrae el número de estantería de una ubicación libre ('18', '18-2', 'Est. 18')."""
    import re

    m = re.search(r"\d+", str(ubicacion or ""))
    return m.group(0).zfill(2) if m else ""
