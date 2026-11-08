"""Prepara os assets: crops verticais dos screenshots, logo, logo da Steam e fontes."""
import os, sys
from PIL import Image
from fontTools.ttLib import TTFont
import cairosvg

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1]  # pasta com os uploads originais
W, H, MARGIN = 1080, 1350, 1.3

# (arquivo, foco horizontal 0..1, foco vertical 0..1)
BGS = [
    ("7ec24403-image.png", 0.50, 0.50),  # wheelie floresta
    ("c4798089-image.png", 0.52, 0.50),  # lama + banners
    ("f5d2f6b0-image.png", 0.62, 0.50),  # traseira na lama
    ("958870f0-image.png", 0.40, 0.45),  # salto sobre a arvore
    ("703ade9f-image.png", 0.40, 0.50),  # salto com bandeira
    ("068e7715-image.png", 0.43, 0.55),  # trilha cerca
    ("140655eb-image.png", 0.50, 0.55),  # POV
    ("b45815b8-image.png", 0.60, 0.55),  # trilha cerca 2
    ("f8557be1-image.png", 0.63, 0.55),  # vindo na floresta
    ("6bafa7f3-image.png", 0.66, 0.55),  # casa
    ("957c7a98-image.jpg", 0.25, 0.45),  # whip por do sol
    ("b0731974-image.jpg", 0.46, 0.45),  # salto por do sol
    ("9ead6afb-image.jpg", 0.33, 0.55),  # parado por do sol
    ("3130eaaa-image.jpg", 0.52, 0.55),  # por do sol centro
]

ow, oh = int(W * MARGIN), int(H * MARGIN)
for i, (name, fx, fy) in enumerate(BGS):
    im = Image.open(os.path.join(SRC, name)).convert("RGB")
    s = max(ow / im.width, oh / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = min(max(int(fx * im.width - ow / 2), 0), im.width - ow)
    y = min(max(int(fy * im.height - oh / 2), 0), im.height - oh)
    im.crop((x, y, x + ow, y + oh)).save(os.path.join(HERE, "assets/bg", f"bg{i:02d}.jpg"), quality=90)

Image.open(os.path.join(SRC, "10be4528-image.png")).convert("RGBA").save(os.path.join(HERE, "assets/game-logo.png"))

cairosvg.svg2png(url=os.path.join(HERE, "assets/raw/steam.svg"), write_to=os.path.join(HERE, "assets/steam-logo.png"),
                 output_width=1024, output_height=1024)

for woff, ttf in [("anton-latin-400-normal.woff", "Anton-Regular.ttf"),
                  ("archivo-black-latin-400-normal.woff", "ArchivoBlack-Regular.ttf")]:
    f = TTFont(os.path.join(HERE, "assets/raw", woff)); f.flavor = None
    f.save(os.path.join(HERE, "assets/fonts", ttf))
print("ok")
