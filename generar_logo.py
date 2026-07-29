"""Genera el logo de la barra lateral (texto sobre fondo transparente).

Se corre una sola vez; el resultado queda en assets/logo_sidebar.png y
assets/logo_chico.png. Volver a correrlo solo si cambia el nombre del sistema.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).parent / "assets"
TITULO = ["Sistema de Gestión", "Integral de Mantenimiento"]
AZUL = (15, 42, 74)


def fuente(tam):
    for nombre in ("segoeuib.ttf", "arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def generar(ancho, alto, tam_fuente, salida, con_texto=True):
    img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # marquita cuadrada a la izquierda
    lado = alto - 8
    d.rounded_rectangle([0, 4, lado, 4 + lado], radius=8, fill=AZUL)
    d.rectangle([lado * 0.28, alto * 0.42, lado * 0.72, alto * 0.68], fill=(255, 255, 255))

    if con_texto:
        f1 = fuente(tam_fuente)
        f2 = fuente(tam_fuente + 2)
        x = lado + 12
        d.text((x, alto * 0.18), TITULO[0], font=f1, fill=(90, 105, 125))
        d.text((x, alto * 0.46), TITULO[1], font=f2, fill=AZUL)

    ASSETS.mkdir(exist_ok=True)
    img.save(ASSETS / salida)
    print("generado:", ASSETS / salida, img.size)


if __name__ == "__main__":
    generar(320, 56, 13, "logo_sidebar.png")
    generar(56, 56, 13, "logo_chico.png", con_texto=False)
