"""Genera la marca del sistema: el engranaje sobre el cuadrado redondeado.

Se dibuja al cuádruple de tamaño y después se reduce, para que los bordes
queden suaves. Todo sale al doble de la medida en que se muestra, así en las
pantallas de alta resolución no se ve borroso.

Genera tres archivos, cada uno para un fondo distinto:
  - logo_sidebar.png : marca celeste + nombre, para la barra lateral azul noche
  - logo_chico.png   : marca azul, para cuando la barra está plegada y el ícono
                       queda sobre el fondo blanco. También es el ícono de la
                       pestaña del navegador.
  - logo_login.png   : la misma marca azul, más grande, para la pantalla de
                       inicio de sesión

Se corre a mano; el resultado va a assets/. Volver a correrlo solo si cambia el
nombre del sistema o los colores.

Uso:
    py -3 generar_logo.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).parent / "assets"
TITULO = ["Sistema de Gestión", "Integral de Mantenimiento"]

# La barra lateral es azul noche, así que ahí la marca va en claro. Sobre el
# fondo blanco (barra plegada, pantalla de login) va en el azul del sistema.
CELESTE = (111, 168, 220, 255)
AZUL = (20, 80, 126, 255)  # #14507E, el primaryColor de config.toml
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


def dibujar_marca(lado, color=CELESTE):
    """Cuadrado redondeado con un engranaje calado en el medio."""
    L = lado * ESCALA
    marca = Image.new("RGBA", (L, L), (0, 0, 0, 0))

    # el cuadrado de fondo
    fondo = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    ImageDraw.Draw(fondo).rounded_rectangle([0, 0, L - 1, L - 1],
                                            radius=int(L * 0.22), fill=color)

    # el engranaje se cala: máscara blanca = se ve el celeste
    mascara = Image.new("L", (L, L), 255)
    d = ImageDraw.Draw(mascara)
    cx = cy = L / 2
    d.polygon(puntos_engranaje(cx, cy, L * 0.40, L * 0.30, 8), fill=0)
    d.ellipse([cx - L * 0.13, cy - L * 0.13, cx + L * 0.13, cy + L * 0.13], fill=255)

    fondo.putalpha(Image.composite(fondo.getchannel("A"), Image.new("L", (L, L), 0), mascara))
    marca.alpha_composite(fondo)
    return marca.resize((lado, lado), Image.LANCZOS)


def generar(ancho, alto, salida, con_texto=True, tam_fuente=13, color=CELESTE,
            margen=8):
    img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    lado = alto - margen
    img.alpha_composite(dibujar_marca(lado, color), (margen // 2, margen // 2))

    if con_texto:
        d = ImageDraw.Draw(img)
        x = lado + alto * 0.22
        d.text((x, alto * 0.17), TITULO[0], font=fuente(tam_fuente), fill=GRIS_CLARO)
        d.text((x, alto * 0.45), TITULO[1], font=fuente(tam_fuente + 3), fill=BLANCO)

    ASSETS.mkdir(exist_ok=True)
    img.save(ASSETS / salida)
    print("generado:", ASSETS / salida, img.size)


if __name__ == "__main__":
    # al doble de la medida en que se muestran, para que no se vean borrosos
    generar(680, 116, "logo_sidebar.png", tam_fuente=26, margen=16)
    generar(128, 128, "logo_chico.png", con_texto=False, color=AZUL, margen=0)
    generar(256, 256, "logo_login.png", con_texto=False, color=AZUL, margen=0)
