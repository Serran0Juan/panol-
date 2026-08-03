"""Pruebas del formulario público de pedidos de reparación.

El formulario está abierto: no pide ninguna clave. Lo que se verifica acá es
que efectivamente no quedó ningún resto del código que pedía antes, que el link
y el QR del cartel se armen bien, y que el seguimiento de un pedido solo
funcione con el email de quien lo cargó.

    py -3 _prueba_solicitud_publica.py
"""

import os

os.environ["PANOL_MODO_LOCAL"] = "1"

from unittest import mock  # noqa: E402

import solicitud_publica as sp  # noqa: E402

ok = fallos = 0


def check(etiqueta, condicion, detalle=""):
    global ok, fallos
    if condicion:
        ok += 1
        print(f"  OK    {etiqueta} {detalle}")
    else:
        fallos += 1
        print(f"  FALLA {etiqueta} {detalle}")


print("1. El formulario no pide ninguna clave")
import inspect  # noqa: E402

fuente_carga = inspect.getsource(sp._pestana_carga)
check("no hay campo de código", "Código del hospital" not in fuente_carga)
check("no se compara ninguna clave", "compare_digest" not in inspect.getsource(sp))
check("no lee secretos", "st.secrets" not in inspect.getsource(sp))
check("la pantalla se dibuja sin condiciones previas",
      "no está habilitado" not in inspect.getsource(sp.formulario_publico))
check("queda el tope por sesión como único freno",
      sp.MAXIMO_POR_SESION > 0 and "MAXIMO_POR_SESION" in fuente_carga,
      f"-> {sp.MAXIMO_POR_SESION} pedidos por sesión")

print("\n2. El link del cartel")
base = "https://panol.streamlit.app"
check("lleva el parámetro que abre el formulario",
      sp.enlace_publico(base) == f"{base}/?solicitar=1")
check("tolera la barra final",
      sp.enlace_publico(base + "/") == f"{base}/?solicitar=1")
check("completa el sector",
      sp.enlace_publico(base, "Sala 3") == f"{base}/?solicitar=1&area=Sala%203")
check("escapa los caracteres raros del sector",
      "%C3%B3" in sp.enlace_publico(base, "Quirófano 2"),
      f"-> {sp.enlace_publico(base, 'Quirófano 2')}")
check("un sector vacío no agrega nada",
      sp.enlace_publico(base, "   ") == f"{base}/?solicitar=1")

print("\n3. El código QR")
svg = sp.qr_svg(sp.enlace_publico(base, "Sala 3"))
if svg is None:
    check("falta la librería qrcode, el cartel se arma con el link", True,
          "(instalá qrcode para generarlo desde la app)")
else:
    check("genera un SVG", svg.lstrip().startswith("<svg"))
    check("es escalable, no una imagen pixelada", "viewBox" in svg)

print("\n4. El email que da trazabilidad")
for texto, esperado in [("laura@hospital.gob.ar", True), ("laura@hospital", False),
                        ("laura", False), ("", False), ("  a@b.co  ", True)]:
    check(f"{texto!r} -> {'válido' if esperado else 'inválido'}",
          sp.email_valido(texto) is esperado)

print("\n6. Seguir un pedido con el número y el email")
import sheets_backend as sb  # noqa: E402

EMAIL = "laura.gimenez@hospital.gob.ar"
ot = sb.crear_solicitud("Quirófano 2", "La luz parpadea desde ayer", "MEDIA",
                        "Laura Gimenez", EMAIL, "Cirugía")

check("lo encuentra con su número y su email", sp.buscar_pedido(ot, EMAIL) is not None)
check("tolera el número escrito de otra forma",
      sp.buscar_pedido(ot.replace("OT-", "").lstrip("0"), EMAIL) is not None,
      f"-> probando con {ot.replace('OT-', '').lstrip('0')!r}")
check("no distingue mayúsculas en el email",
      sp.buscar_pedido(ot, EMAIL.upper()) is not None)
check("con otro email no lo muestra",
      sp.buscar_pedido(ot, "otro@hospital.gob.ar") is None)
check("sin email no muestra nada", sp.buscar_pedido(ot, "") is None)
check("un número que no existe no rompe", sp.buscar_pedido("OT-9999", EMAIL) is None)
check("el pedido nace en SOLICITADA",
      sp.buscar_pedido(ot, EMAIL)["ESTADO"] == "SOLICITADA")
check("hay un texto en criollo para cada estado",
      all(e in sp.QUE_SIGNIFICA for e in sb.ESTADOS_OT),
      f"-> {len(sp.QUE_SIGNIFICA)} de {len(sb.ESTADOS_OT)}")

sb.asignar_orden(ot, "ELECTRICIDAD", "Dias Diego", "MEDIA", "Serrano Juan")
check("al asignarla, quien pidió ve el cambio",
      sp.buscar_pedido(ot, EMAIL)["ESTADO"] == "ASIGNADA")
check("y ve quién la tiene a cargo",
      sp.buscar_pedido(ot, EMAIL)["ASIGNADO_A"] == "Dias Diego")

print(f"\n{'=' * 52}\nRESULTADO: {ok} OK, {fallos} fallas\n{'=' * 52}")
raise SystemExit(1 if fallos else 0)
