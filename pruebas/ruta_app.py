"""Deja importar el código de la app desde esta carpeta.

Las pruebas viven en `pruebas/` pero prueban los módulos de la raíz
(`sheets_backend`, `auth`, `estilo`...). Importar este archivo primero agrega la
raíz del proyecto al camino de búsqueda de Python.

No fuerza el modo local a propósito: cada prueba lo declara ella misma, en su
primera línea, para que se vea de un vistazo que no puede tocar la planilla real.
"""

import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
