"""Verifica la conversión de números que vienen formateados desde la planilla."""

import os

import ruta_app  # noqa: F401  agrega la raíz del proyecto al camino de importación

os.environ["PANOL_MODO_LOCAL"] = "1"

import warnings  # noqa: E402

warnings.filterwarnings("ignore")

from sheets_backend import a_numero  # noqa: E402

CASOS = [
    # lo que devuelve Google Sheets    esperado    por qué
    ("$ 10.000",        10000.0, "precio con separador de miles"),
    ("$ 45",               45.0, "precio chico"),
    ("1.000",           1000.0, "stock de mil"),
    ("177.367.393", 177367393.0, "valor total del inventario"),
    ("$ 177.367.393", 177367393.0, "el mismo, con signo peso"),
    ("7791.88",        7791.88, "decimal con punto (formato viejo)"),
    ("9.5",                9.5, "un decimal con punto"),
    ("0.125",            0.125, "decimal chico que empieza en cero"),
    ("1.234,56",       1234.56, "miles con punto y decimal con coma"),
    ("1,5",                1.5, "decimal con coma"),
    ("$ 1.234,56",     1234.56, "lo mismo con signo peso"),
    ("20",                20.0, "entero simple"),
    ("-15",              -15.0, "negativo"),
    ("-1.500",         -1500.0, "negativo con miles"),
    ("",                   0.0, "vacío"),
    ("   ",                0.0, "espacios"),
    ("sin dato",           0.0, "texto"),
    (None,                 0.0, "nulo"),
    (10000,            10000.0, "ya venía como entero"),
    (45.5,                45.5, "ya venía como decimal"),
    ("1.000 un",        1000.0, "con unidad pegada"),
    ("100 %",            100.0, "con símbolo de porcentaje"),
]

ok = fallos = 0
for entrada, esperado, motivo in CASOS:
    real = a_numero(entrada)
    if abs(real - esperado) < 1e-9:
        ok += 1
        print(f"  OK    {str(entrada)!r:>16} -> {real:<14g} ({motivo})")
    else:
        fallos += 1
        print(f"  FALLA {str(entrada)!r:>16} -> {real} , se esperaba {esperado} ({motivo})")

print(f"\n{'=' * 60}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 60}")
raise SystemExit(1 if fallos else 0)
