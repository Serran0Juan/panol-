"""La orden de trabajo en papel, para entregarle al operario.

Se genera un archivo HTML suelto, sin nada externo: se descarga, se abre con
doble clic y se imprime. Va en HTML y no en PDF a propósito, para no sumarle
una dependencia al proyecto y para que se pueda abrir también desde un celular.

El papel es la contracara del sistema: el operario se lleva la orden impresa,
anota qué hizo y qué materiales usó, y el responsable del sector le firma la
conformidad de que el trabajo se hizo. Después eso se carga en la app.
"""

import base64
import html
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"

# Renglones en blanco que se dejan para completar a mano.
LINEAS_TRABAJO = 5
FILAS_MATERIALES = 6


def _marca() -> str:
    """El logo embebido en el propio archivo, así no depende de internet."""
    archivo = ASSETS / "logo_chico.png"
    if not archivo.exists():
        return ""
    datos = base64.b64encode(archivo.read_bytes()).decode()
    return f'<img class="marca" src="data:image/png;base64,{datos}" alt="">'


def _texto(valor) -> str:
    """Escapa lo que viene de la planilla: puede tener < > &."""
    return html.escape(str(valor or "").strip())


def _fila(etiqueta: str, valor) -> str:
    valor = _texto(valor) or "—"
    return f"<tr><th>{html.escape(etiqueta)}</th><td>{valor}</td></tr>"


def _renglones(cantidad: int) -> str:
    return '<div class="renglon"></div>' * cantidad


def _bloque_trabajo(orden) -> str:
    """Qué se hizo: ya completado si la orden está cerrada, o en blanco."""
    realizado = _texto(orden.get("TRABAJO_REALIZADO"))
    if not realizado:
        return f'<div class="caja">{_renglones(LINEAS_TRABAJO)}</div>'

    extra = []
    if _texto(orden.get("CAUSA")):
        extra.append(f"<p><strong>Causa:</strong> {_texto(orden['CAUSA'])}</p>")
    if orden.get("HORAS"):
        extra.append(f"<p><strong>Horas:</strong> {orden['HORAS']:g}</p>")
    return f'<div class="caja"><p>{realizado}</p>{"".join(extra)}</div>'


def _tabla_materiales() -> str:
    filas = ("<tr><td></td><td></td><td></td></tr>" * FILAS_MATERIALES)
    return f"""
    <table class="materiales">
      <thead><tr><th style="width:16%">Cantidad</th><th>Material</th>
                 <th style="width:16%">Unidad</th></tr></thead>
      <tbody>{filas}</tbody>
    </table>"""


CSS = """
@page { size: A4; margin: 14mm; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", Arial, sans-serif; color: #0F172A;
  font-size: 11.5pt; line-height: 1.45; margin: 0; padding: 18px;
  max-width: 800px; margin-inline: auto;
}
.marca { width: 34px; height: 34px; vertical-align: middle; }
header { border-bottom: 2px solid #14507E; padding-bottom: 10px; margin-bottom: 16px;
         display: flex; align-items: center; gap: 12px; }
header .titulo { flex: 1; }
header .sistema { font-size: 8.5pt; letter-spacing: .1em; text-transform: uppercase;
                  color: #14507E; font-weight: 700; }
header h1 { font-size: 16pt; margin: 2px 0 0 0; }
header .numero { font-size: 20pt; font-weight: 700; color: #14507E; white-space: nowrap; }
.pastillas { margin-bottom: 14px; }
.pastilla { display: inline-block; border: 1px solid #94A3B8; border-radius: 999px;
            padding: 2px 12px; font-size: 9.5pt; font-weight: 700; margin-right: 6px; }
.urgente { border-color: #B91C1C; color: #B91C1C; }
table.datos { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
table.datos th { text-align: left; width: 30%; font-weight: 600; color: #475569;
                 padding: 4px 8px 4px 0; vertical-align: top; }
table.datos td { padding: 4px 0; }
h2 { font-size: 9.5pt; letter-spacing: .08em; text-transform: uppercase;
     color: #475569; margin: 16px 0 6px 0; }
h2 .aclaracion { text-transform: none; letter-spacing: 0; font-weight: 400; }
.caja { border: 1px solid #94A3B8; border-radius: 4px; padding: 10px 12px; min-height: 30px; }
.caja p { margin: 0 0 6px 0; }
.renglon { border-bottom: 1px dotted #94A3B8; height: 26px; }
.renglon:last-child { border-bottom: none; }
table.materiales { width: 100%; border-collapse: collapse; }
table.materiales th, table.materiales td { border: 1px solid #94A3B8; padding: 6px 8px; }
table.materiales th { background: #F1F5F9; font-size: 9.5pt; text-align: left; }
table.materiales td { height: 26px; }
.cierre { display: flex; gap: 26px; margin-top: 14px; }
.cierre div { flex: 1; }
.firmas { display: flex; gap: 26px; margin-top: 30px; page-break-inside: avoid; }
.firma { flex: 1; }
.firma .linea { border-top: 1px solid #0F172A; margin-bottom: 4px; }
.firma .rol { font-weight: 700; font-size: 10pt; }
.firma .dato { color: #475569; font-size: 9pt; margin-top: 10px; }
footer { margin-top: 22px; border-top: 1px solid #CBD5E1; padding-top: 8px;
         font-size: 8.5pt; color: #64748B; }
.imprimir { position: fixed; top: 14px; right: 14px; background: #14507E; color: #fff;
            border: none; border-radius: 8px; padding: 10px 18px; font-size: 11pt;
            font-weight: 600; cursor: pointer; }
@media print { .imprimir { display: none; } body { padding: 0; } }
"""


def orden_en_html(orden, generada_por: str = "", generada_el: str = "") -> str:
    """El HTML completo de una orden, listo para descargar e imprimir."""
    id_ot = _texto(orden["ID_OT"])
    prioridad = _texto(orden.get("PRIORIDAD")).upper()
    clase_prioridad = "pastilla urgente" if prioridad == "URGENTE" else "pastilla"

    datos = "".join([
        _fila("Lugar / área", orden.get("AREA")),
        _fila("Sector asignado", orden.get("SECTOR_ASIGNADO")),
        _fila("Responsable", orden.get("ASIGNADO_A")),
        _fila("Solicitó", orden.get("SOLICITANTE")),
        _fila("Fecha de alta", orden.get("FECHA_ALTA")),
        _fila("Fecha comprometida", orden.get("FECHA_COMPROMISO")),
        _fila("Programada para", orden.get("FECHA_PROGRAMADA")),
        _fila("Horas estimadas",
              f"{orden['HORAS_ESTIMADAS']:g}" if orden.get("HORAS_ESTIMADAS") else ""),
    ])

    pie = [f"Orden {id_ot} — Sistema de Gestión Integral de Mantenimiento"]
    if generada_por:
        pie.append(f"impresa por {_texto(generada_por)}")
    if generada_el:
        pie.append(_texto(generada_el))

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Orden de trabajo {id_ot}</title>
<style>{CSS}</style>
</head>
<body>
<button class="imprimir" onclick="window.print()">Imprimir</button>

<header>
  {_marca()}
  <div class="titulo">
    <div class="sistema">Sistema de Gestión Integral de Mantenimiento</div>
    <h1>Orden de trabajo</h1>
  </div>
  <div class="numero">{id_ot}</div>
</header>

<div class="pastillas">
  <span class="pastilla">{_texto(orden.get("ESTADO")) or "—"}</span>
  <span class="{clase_prioridad}">Prioridad {prioridad or "—"}</span>
</div>

<table class="datos">{datos}</table>

<h2>Problema informado</h2>
<div class="caja"><p>{_texto(orden.get("DESCRIPCION")) or "—"}</p>
{f'<p>Contacto: {_texto(orden["OBSERVACIONES"])}</p>' if _texto(orden.get("OBSERVACIONES")) else ""}
</div>

<h2>Trabajo realizado <span class="aclaracion">— a completar por el operario</span></h2>
{_bloque_trabajo(orden)}

<h2>Materiales utilizados</h2>
{_tabla_materiales()}

<div class="cierre">
  <div><h2>Fecha de finalización</h2><div class="renglon"></div></div>
  <div><h2>Horas trabajadas</h2><div class="renglon"></div></div>
</div>

<div class="firmas">
  <div class="firma">
    <div class="linea"></div>
    <div class="rol">Firma del operario</div>
    <div class="dato">Aclaración:</div>
    <div class="dato">Fecha:</div>
  </div>
  <div class="firma">
    <div class="linea"></div>
    <div class="rol">Conformidad del responsable del sector</div>
    <div class="dato">Aclaración:</div>
    <div class="dato">Fecha:</div>
  </div>
</div>

<footer>{" · ".join(pie)}</footer>
</body>
</html>"""


def nombre_archivo(orden) -> str:
    return f"orden-{_texto(orden['ID_OT']).lower().replace(' ', '-')}.html"
