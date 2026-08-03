"""Pruebas del aguante frente a los cortes de la API de Google.

Google limita las consultas por minuto. Al registrar varias devoluciones
seguidas se llegaba a ese tope y la app se caía con un error crudo en la cara
del usuario. Acá se verifica que ahora reintente, que espere cada vez un poco
más, y que si no hay caso avise en castellano.

    py -3 _prueba_reintentos.py
"""

import os

os.environ["PANOL_MODO_LOCAL"] = "1"

from unittest import mock  # noqa: E402

import sheets_backend as sb  # noqa: E402

ok = fallos = 0


def check(etiqueta, condicion, detalle=""):
    global ok, fallos
    if condicion:
        ok += 1
        print(f"  OK    {etiqueta} {detalle}")
    else:
        fallos += 1
        print(f"  FALLA {etiqueta} {detalle}")


def error_api(codigo):
    """Un APIError como el que devuelve gspread, sin llamar a Google."""
    from gspread.exceptions import APIError

    respuesta = mock.Mock()
    respuesta.json.return_value = {"error": {"code": codigo, "message": "de prueba",
                                             "status": "X"}}
    return APIError(respuesta)


print("1. Lo que anda a la primera no se reintenta")
llamadas = []
with mock.patch("time.sleep") as dormir:
    resultado = sb._con_reintentos(lambda: llamadas.append(1) or "listo")
check("devuelve el resultado", resultado == "listo")
check("llama una sola vez", len(llamadas) == 1, f"-> {len(llamadas)}")
check("no espera de gusto", dormir.call_count == 0)

print("\n2. Un corte pasajero se reintenta y se sale adelante")
for codigo in sb.CODIGOS_PASAJEROS:
    intentos = {"n": 0}

    def falla_una_vez():
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise error_api(codigo)
        return "recuperado"

    with mock.patch("time.sleep"):
        salida = sb._con_reintentos(falla_una_vez)
    check(f"se recupera de un {codigo}", salida == "recuperado" and intentos["n"] == 2)

print("\n3. Cada espera es más larga que la anterior")
esperas = []
with mock.patch("time.sleep", side_effect=esperas.append):
    try:
        sb._con_reintentos(lambda: (_ for _ in ()).throw(error_api(503)))
    except Exception:
        pass
check("espera entre intento e intento", len(esperas) == sb.REINTENTOS - 1,
      f"-> {esperas}")
check("va duplicando la espera", esperas == sorted(esperas) and len(set(esperas)) == len(esperas))
check("no se pasa de un minuto en total", sum(esperas) < 60, f"-> {sum(esperas):g}s")

print("\n4. Si el tope no cede, el mensaje es entendible")
with mock.patch("time.sleep"):
    try:
        sb._con_reintentos(lambda: (_ for _ in ()).throw(error_api(429)))
        check("avisa del límite", False, "-> no levantó nada")
    except sb.LimiteDeGoogle as e:
        texto = str(e)
        check("avisa con LimiteDeGoogle", True)
        check("está en castellano", "Esperá un minuto" in texto)
        check("aclara que no se perdió nada", "no se perdió nada" in texto)
        check("no muestra tripas técnicas",
              "APIError" not in texto and "quota" not in texto.lower())

print("\n5. Un error real no se reintenta ni se disfraza")
intentos = {"n": 0}


def sin_permiso():
    intentos["n"] += 1
    raise error_api(403)


with mock.patch("time.sleep") as dormir:
    try:
        sb._con_reintentos(sin_permiso)
        check("un 403 se propaga", False, "-> no levantó nada")
    except sb.LimiteDeGoogle:
        check("un 403 se propaga", False, "-> lo confundió con el tope")
    except Exception as e:
        check("un 403 se propaga tal cual", type(e).__name__ == "APIError")
check("y no lo reintenta", intentos["n"] == 1, f"-> {intentos['n']} intento(s)")

print("\n6. Una hoja que no existe no se confunde con un corte")
import inspect  # noqa: E402

fuente = inspect.getsource(sb._ws)
check("solo crea la hoja ante WorksheetNotFound", "except WorksheetNotFound" in fuente)
check("y no ante cualquier error", "except Exception" not in fuente)

print("\n7. La hoja se busca una sola vez")
fuente_hoja = inspect.getsource(sb._hoja)
check("la búsqueda está cacheada", "cache_resource" in inspect.getsource(sb).split("def _hoja")[0][-200:]
      or hasattr(sb._hoja, "clear"))
check("se puede limpiar si se crea una hoja nueva", hasattr(sb._hoja, "clear"))
check("pasa por los reintentos", "_con_reintentos" in fuente_hoja)

print(f"\n{'=' * 52}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 52}")
raise SystemExit(1 if fallos else 0)
