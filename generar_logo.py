"""Genera el logo de la barra lateral.

Un engranaje sobre un cuadrado redondeado, con el nombre del sistema al lado.
Se dibuja al cuádruple de tamaño y después se reduce, para que los bordes
queden suaves.

Se corre una sola vez; el resultado va a assets/. Volver a correrlo solo si
cambia el nombre del sistema o los colores.

Uso:
    py -3 generar_logo.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).parent / "assets"
TITULO = ["Sistema de Gestión", "Integral de Mantenimiento"]

# La barra lateral es azul noche, así que la marca va en claro.
CELESTE = (111, 168, 220, 255)
AZUL_NOCHE = (14, 32, 56, 255)
BLANCO = (245, 249, 255, 255)
GRIS_CLARO = (150, 174, 202, 255)

ESCALA = 4  # se dibuja 4 veces más grande y se reduce al final


def fuente(tam):
    for nombre in ("segoeuib.ttf", "arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def puntos_engranaje(cx, cy, r_diente, r_base, dientes, ancho=0.42):
    """Contorno de un engranaje: alterna entre el radio del diente y el del cuerpo."""
    pts = []
    paso = 2 * math.pi / dientes
    medio = paso * ancho / 2
    for i in range(dientes):
        a = i * paso
        b = a + paso / 2
        for angulo, radio in ((a - medio, r_diente), (a + medio, r_diente),
                              (b - medio, r_base), (b + medio, r_base)):
            pts.append((cx + radio * math.cos(angulo), cy + radio * math.sin(angulo)))
    return pts


def dibujar_marca(lado):
    """Cuadrado redondeado celeste con un engranaje calado en el medio."""
    L = lado * ESCALA
    marca = Image.new("RGBA", (L, L), (0, 0, 0, 0))

    # el cuadrado de fondo
    fondo = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    ImageDraw.Draw(fondo).rounded_rectangle([0, 0, L - 1, L - 1],
                                            radius=int(L * 0.22), fill=CELESTE)

    # el engranaje se cala: máscara blanca = se ve el celeste
    mascara = Image.new("L", (L, L), 255)
    d = ImageDraw.Draw(mascara)
    cx = cy = L / 2
    d.polygon(puntos_engranaje(cx, cy, L * 0.40, L * 0.30, 8), fill=0)
    d.ellipse([cx - L * 0.13, cy - L * 0.13, cx + L * 0.13, cy + L * 0.13], fill=255)

    fondo.putalpha(Image.composite(fondo.getchannel("A"), Image.new("L", (L, L), 0), mascara))
    marca.alpha_composite(fondo)
    return marca.resize((lado, lado), Image.LANCZOS)


def generar(ancho, alto, salida, con_texto=True, tam_fuente=13):
    img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    lado = alto - 8
    img.alpha_composite(dibujar_marca(lado), (0, 4))

    if con_texto:
        d = ImageDraw.Draw(img)
        x = lado + 13
        d.text((x, alto * 0.17), TITULO[0], font=fuente(tam_fuente), fill=GRIS_CLARO)
        d.text((x, alto * 0.45), TITULO[1], font=fuente(tam_fuente + 3), fill=BLANCO)

    ASSETS.mkdir(exist_ok=True)
    img.save(ASSETS / salida)
    print("generado:", ASSETS / salida, img.size)


if __name__ == "__main__":
    generar(340, 58, "logo_sidebar.png")
    generar(58, 58, "logo_chico.png", con_texto=False)
