"""
DIRTBIKE SIMULATOR — "WE ARE ON STEAM" motion (Instagram 4:5, 1080x1350, 30fps, 120 BPM)

Uso:
    python3 prep.py <pasta-com-os-screenshots>   # (uma vez) gera assets/
    python3 render.py                            # gera out/dirtbike-on-steam.mp4 (+ versao com beat guia)
    python3 render.py --stills 0,30,95           # salva frames soltos em out/stills/ para conferir

1 batida = 0.5s = 15 frames. Toda a timeline e definida em batidas.
  0- 8  WE / ARE / ON  (uma palavra a cada 2 batidas) + pilha WE ARE ON
  8-16  repeticao das palavras de 16 formas diferentes (troca a cada 1/2 batida)
 16-20  build-up (troca a cada 1/4 de batida) + respiro
 20-28  DROP: WE ARE ON STEAM
 28-36  WISHLIST NOW
 36-44  logo do jogo + "WISHLIST NOW ON STEAM"
"""
import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(HERE, "assets", *p)
OUT = os.path.join(HERE, "out")

W, H = 1080, 1350
FPS = 30
BPM = 120
TOTAL_BEATS = 44
NFRAMES = int(TOTAL_BEATS * 60 / BPM * FPS)

ORANGE = (255, 86, 20)
CYAN = (102, 192, 244)
NAVY = (27, 40, 56)
BLUE = (42, 71, 94)
DARK = (11, 14, 19)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FONTS = {"tall": A("fonts", "Anton-Regular.ttf"), "wide": A("fonts", "ArchivoBlack-Regular.ttf")}

# ---------------------------------------------------------------- helpers

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo_expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def eo_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eo_back(x, s=2.2):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def env(x, k=6.0):
    """envelope que decai depois de um hit (x em batidas desde o hit)."""
    return math.exp(-k * x) if x >= 0 else 0.0


def ph(x):
    return x - math.floor(x)


@lru_cache(None)
def font(fk, size):
    return ImageFont.truetype(FONTS[fk], size)


@lru_cache(maxsize=512)
def tmask(text, fk, size, stroke=0, outline=False, tracking=0):
    f = font(fk, size)
    l, t, r, b = f.getbbox(text)
    pad = stroke + 6
    w = (r - l) + tracking * max(len(text) - 1, 0) + 2 * pad
    h = (b - t) + 2 * pad

    def draw(sw):
        im = Image.new("L", (int(w), int(h)), 0)
        d = ImageDraw.Draw(im)
        if tracking:
            x = pad - l
            for c in text:
                d.text((x, pad - t), c, font=f, fill=255, stroke_width=sw, stroke_fill=255)
                x += f.getlength(c) + tracking
        else:
            d.text((pad - l, pad - t), text, font=f, fill=255, stroke_width=sw, stroke_fill=255)
        return im

    im = draw(stroke)
    if outline:
        im = ImageChops.subtract(im, draw(0))
    bb = im.getbbox()
    return im.crop(bb) if bb else im


@lru_cache(maxsize=512)
def fit_size(text, fk, w, h, tr):
    f = font(fk, 400)
    l, t, r, b = f.getbbox(text)
    bw = (r - l) + tr * 400 * max(len(text) - 1, 0)
    s = min(w / bw if w else 1e9, h / (b - t) if h else 1e9)
    return max(8, int(400 * s))


def text(t, fk="tall", w=None, h=None, stroke=0, outline=False, tr=0.0):
    size = fit_size(t, fk, w, h, tr)
    return tmask(t, fk, size, stroke, outline, int(tr * size))


def xform(m, scale=1.0, rot=0.0, alpha=1.0):
    if abs(scale - 1) > 1e-3:
        m = m.resize((max(1, int(m.width * scale)), max(1, int(m.height * scale))), Image.BILINEAR)
    if abs(rot) > 1e-3:
        m = m.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        m = Image.fromarray((np.asarray(m, np.float32) * clamp(alpha)).astype(np.uint8))
    return m


def put(cv, m, color, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if alpha <= 0.004 or scale <= 0.01:
        return
    m = xform(m, scale, rot, alpha)
    cv.paste(color, (int(round(cx - m.width / 2)), int(round(cy - m.height / 2))), m)


def full(m, cx, cy, scale=1.0, rot=0.0):
    """mascara posicionada no tamanho do canvas."""
    out = Image.new("L", (W, H), 0)
    m = xform(m, scale, rot)
    out.paste(m, (int(round(cx - m.width / 2)), int(round(cy - m.height / 2))))
    return out


def put_img(cv, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if alpha <= 0.004 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 1e-3:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    a = im.getchannel("A")
    if alpha < 0.999:
        a = Image.fromarray((np.asarray(a, np.float32) * alpha).astype(np.uint8))
    cv.paste(im.convert("RGB"), (int(round(cx - im.width / 2)), int(round(cy - im.height / 2))), a)


def solid(c):
    return Image.new("RGB", (W, H), c)


# ---------------------------------------------------------------- assets (carregados por processo)

_BG = {}


def bgsrc(i):
    i %= 14
    if i not in _BG:
        _BG[i] = Image.open(A("bg", f"bg{i:02d}.jpg")).convert("RGB")
    return _BG[i]


def bg(i, z=1.0, dx=0.0, dy=0.0, rot=0.0, mirror=False):
    src = bgsrc(i)
    cx, cy = src.width / 2 + dx, src.height / 2 + dy
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    a, b_, d, e = c / z, s / z, -s / z, c / z
    data = (a, b_, cx - (W / 2 * a + H / 2 * b_), d, e, cy - (W / 2 * d + H / 2 * e))
    im = src.transform((W, H), Image.AFFINE, data, Image.BILINEAR)
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im


@lru_cache(None)
def steam_logo_mask():
    return Image.open(A("steam-logo.png")).getchannel("A")


def steam_logo(size):
    return steam_logo_mask().resize((size, size), Image.LANCZOS)


@lru_cache(None)
def game_logo():
    return Image.open(A("game-logo.png")).convert("RGBA")


# grids pre-calculados
_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)
_R = np.sqrt(((_XX - W / 2) / W) ** 2 + ((_YY - H / 2) / H) ** 2)
VIGNETTE = np.clip(1.15 - _R * 1.1, 0.35, 1.0)[..., None]


def arr(im):
    return np.asarray(im, np.float32)


def img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def lum(a):
    return (a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114) / 255.0


def darken(im, k=0.45, vig=True):
    a = arr(im) * k
    if vig:
        a = a * VIGNETTE
    return img(a)


def duotone(im, c0, c1, contrast=1.35):
    L = np.clip((lum(arr(im)) - 0.5) * contrast + 0.5, 0, 1)[..., None]
    c0, c1 = np.array(c0, np.float32), np.array(c1, np.float32)
    return img(c0 + (c1 - c0) * L)


def blend(a, b, t):
    return Image.blend(a, b, clamp(t))


def flash(im, a, color=WHITE):
    return blend(im, solid(color), a) if a > 0.004 else im


def rgb_split(im, px):
    px = int(round(px))
    if px < 1:
        return im
    a = np.asarray(im).copy()
    a[..., 0] = np.roll(a[..., 0], px, axis=1)
    a[..., 2] = np.roll(a[..., 2], -px, axis=1)
    return Image.fromarray(a)


def glitch(im, seed, n=6, amp=80):
    if n <= 0:
        return im
    rng = np.random.default_rng(seed)
    a = np.asarray(im).copy()
    for _ in range(n):
        y = rng.integers(0, H - 20)
        h = rng.integers(8, 90)
        a[y:y + h] = np.roll(a[y:y + h], int(rng.integers(-amp, amp)), axis=1)
    return Image.fromarray(a)


def shake(im, amt, seed):
    if amt < 0.5:
        return im
    rng = np.random.default_rng(seed)
    dx, dy = rng.uniform(-amt, amt, 2)
    rot = rng.uniform(-amt, amt) * 0.04
    z = 1 + (2.5 * amt) / W
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    a, b_, d, e = c / z, s / z, -s / z, c / z
    data = (a, b_, W / 2 + dx - (W / 2 * a + H / 2 * b_), d, e, H / 2 + dy - (W / 2 * d + H / 2 * e))
    return im.transform((W, H), Image.AFFINE, data, Image.BILINEAR)


def grain(im, seed, amt=7.0):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, amt, (H, W, 1)).astype(np.float32)
    return img(arr(im) + n)


def ring(cv, cx, cy, r, width, color, alpha):
    if alpha <= 0.01 or r <= 1:
        return
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=int(255 * clamp(alpha)), width=max(1, int(width)))
    cv.paste(color, (0, 0), m)


def label(cv, color=WHITE, alpha=0.9):
    """assinatura pequena no canto (consistencia visual)."""
    put(cv, text("DIRTBIKE SIMULATOR", "wide", h=22, tr=0.18), color, 60 + text("DIRTBIKE SIMULATOR", "wide", h=22, tr=0.18).width / 2, 62, alpha=alpha)


def rays(cv, cx, cy, n, rot, color, alpha):
    th = np.arctan2(_YY - cy, _XX - cx)
    m = (np.sin(th * n + rot) > 0.55).astype(np.float32)
    rr = np.sqrt((_XX - cx) ** 2 + (_YY - cy) ** 2)
    m *= np.clip(rr / 300, 0, 1) * np.clip(1.4 - rr / 1100, 0, 1)
    cv.paste(color, (0, 0), Image.fromarray((m * 255 * alpha).astype(np.uint8)))


def radial_bg(c_in, c_out, cx=W / 2, cy=H / 2, rad=900):
    rr = np.sqrt((_XX - cx) ** 2 + (_YY - cy) ** 2)[..., None] / rad
    t = np.clip(rr, 0, 1)
    return img(np.array(c_in, np.float32) * (1 - t) + np.array(c_out, np.float32) * t)


def stripes(c0, c1, width=70, offset=0.0, angle=1.0):
    v = ((_XX + _YY * angle + offset) // width).astype(np.int32) % 2
    out = np.where(v[..., None] == 0, np.array(c0, np.float32), np.array(c1, np.float32))
    return img(out)


def marquee(cv, msg, y, band_h, band_col, txt_col, offset):
    ImageDraw.Draw(cv).rectangle((0, y, W, y + band_h), fill=band_col)
    m = text(msg.strip(), "wide", h=int(band_h * 0.42), tr=0.06)
    gap = int(band_h * 0.5)
    period = m.width + gap
    x = -(offset % period)
    while x < W:
        cv.paste(txt_col, (int(x), int(y + (band_h - m.height) / 2)), m)
        x += period


# ---------------------------------------------------------------- secoes

WORDS = ["WE", "ARE", "ON"]


def big_word(cv, w, color, cx=W / 2, cy=H / 2 + 20, scale=1.0, rot=0.0, shadow=None, shoff=16, maxw=960, maxh=820, fk="tall"):
    m = text(w, fk, w=maxw, h=maxh)
    if shadow is not None:
        put(cv, m, shadow, cx + shoff * scale, cy + shoff * scale, scale, rot)
    put(cv, m, color, cx, cy, scale, rot)


def sec_intro(b, f):
    """0-8: WE / ARE / ON, cada uma 2 batidas; depois pilha."""
    if b < 6:
        wi = int(b // 2)
        lb = b - wi * 2
        word = WORDS[wi]
        order = [0, 4, 3, 1, 2, 5, 10, 6, 7, 8, 11, 9]
        hb = int(b * 2)
        z = 1.16 - 0.08 * ph(b * 2) + 0.05 * env(ph(b), 6)
        base = bg(order[hb], z, dx=(hb % 2 * 2 - 1) * 30 * ph(b * 2))
        if wi == 0:
            cv, col, sh = darken(base, 0.42), WHITE, ORANGE
        elif wi == 1:
            cv, col, sh = duotone(base, DARK, CYAN), WHITE, NAVY
        else:
            cv, col, sh = duotone(base, (20, 6, 0), ORANGE), BLACK, WHITE
        label(cv, WHITE if wi < 2 else BLACK)
        s = 1 + 0.9 * (1 - eo_expo(lb / 0.35)) + 0.08 * env(lb - 1, 8) + 0.03 * env(ph(b * 2), 10)
        m = text(word, "tall", w=960, h=820)
        # rastro de zoom na entrada
        for k in (3, 2, 1):
            put(cv, m, sh, W / 2, H / 2 + 20, s * (1 + 0.14 * k), alpha=0.35 * env(lb, 7) / k)
        big_word(cv, word, col, scale=s, shadow=sh)
        cv = flash(cv, 0.65 * env(lb, 10))
        cv = rgb_split(cv, 18 * env(lb, 5) + 10 * env(lb - 1, 6))
        if lb > 1:
            cv = glitch(cv, f, n=int(4 * env(lb - 1, 5) * 3), amp=60)
        return shake(cv, 24 * env(lb, 6) + 14 * env(lb - 1, 7), f)

    # 6-8: pilha WE / ARE / ON entrando a cada colcheia
    lb = b - 6
    step = int(lb * 2)  # 0..3
    knock = step >= 3
    cv = solid(ORANGE if knock else DARK)
    ys = [250, 680, 1110]
    hh = 400
    pic = bg(2, 1.1 + 0.1 * ph(lb * 2)) if knock else None
    for i, w in enumerate(WORDS):
        if step < i:
            continue
        t = ph(lb * 2) if step == i else 1.0
        d = -1 if i % 2 == 0 else 1
        x = W / 2 + d * W * (1 - eo_expo(t / 0.6))
        m = text(w, "tall", w=1000, h=hh)
        if knock:
            cv.paste(pic, (0, 0), full(m, x, ys[i]))
        else:
            put(cv, m, WHITE if i != step else ORANGE, x, ys[i])
    label(cv, BLACK if knock else WHITE)
    cv = flash(cv, 0.5 * env(ph(lb * 2), 12))
    cv = rgb_split(cv, 12 * env(ph(lb * 2), 6))
    return shake(cv, 16 * env(ph(lb * 2), 7), f)


def st_repeat(slot, sl, f):
    """8-16: 16 variacoes, cada uma meia batida. sl = progresso 0..1 dentro do slot."""
    w = WORDS[slot % 3]
    pin = 1 + 0.28 * (1 - eo_expo(sl / 0.5))
    bi = (slot * 5 + 3) % 14
    kind = slot

    if kind == 0:  # preto sobre laranja, inclinado
        cv = solid(ORANGE)
        big_word(cv, w, BLACK, scale=pin, rot=-6, maxw=1000, maxh=900)
        label(cv, BLACK)
    elif kind == 1:  # contorno + eco vertical
        cv = darken(bg(bi, 1.1 + 0.08 * sl), 0.35)
        mo = text(w, "tall", w=880, h=360, stroke=7, outline=True)
        ms = text(w, "tall", w=880, h=360)
        for y, m, dx in ((290, mo, -1), (675, ms, 0), (1060, mo, 1)):
            put(cv, m, WHITE, W / 2 + dx * 140 * (1 - eo_expo(sl / 0.6)), y, pin if dx == 0 else 1)
        label(cv)
    elif kind == 2:  # ciano sobre navy
        cv = blend(solid(NAVY), duotone(bg(bi, 1.15 - 0.1 * sl), NAVY, CYAN), 0.35)
        big_word(cv, w, CYAN, scale=pin, shadow=DARK)
        label(cv)
    elif kind == 3:  # linhas em marquee alternado
        cv = solid(BLACK)
        row = "WE ARE ON WE ARE ON WE ARE ON "
        m = text(row, "tall", h=150)
        for r in range(8):
            y = 60 + r * 175
            d = 1 if r % 2 else -1
            x = -400 + d * 900 * sl - (r * 137) % 500
            col = ORANGE if r == 3 else (WHITE if r % 2 == 0 else (90, 90, 90))
            cv.paste(col, (int(x), int(y)), m)
    elif kind == 4:  # knockout: imagem dentro da palavra gigante
        cv = solid(DARK)
        m = text(w, "tall", w=1500, h=1500)
        cv.paste(bg(bi, 1.25 - 0.1 * sl), (0, 0), full(m, W / 2, H / 2, 1.18 - 0.18 * eo_expo(sl / 0.7)))
        label(cv)
    elif kind == 5:  # glitch pesado
        cv = darken(bg(bi, 1.12), 0.5)
        big_word(cv, w, WHITE, scale=pin, shadow=ORANGE)
        cv = glitch(rgb_split(cv, 30 * (1 - sl) + 6), f, n=10, amp=140)
        label(cv)
    elif kind == 6:  # 3 faixas WE / ARE / ON
        cv = solid(BLACK)
        bands = [(ORANGE, BLACK), (WHITE, BLACK), (NAVY, CYAN)]
        d = ImageDraw.Draw(cv)
        for i, (bc, tc) in enumerate(bands):
            off = (1 if i % 2 else -1) * W * (1 - eo_expo((sl - i * 0.12) / 0.45))
            d.rectangle((off, i * 450, off + W, (i + 1) * 450), fill=bc)
            put(cv, text(WORDS[i], "tall", w=900, h=380), tc, W / 2 + off, i * 450 + 225)
    elif kind == 7:  # ON + anel
        cv = darken(bg(bi, 1.1 + 0.1 * sl), 0.3)
        r = 120 + 700 * eo_cubic(sl)
        ring(cv, W / 2, H / 2, r, 26 * (1 - sl) + 4, ORANGE, 1 - sl * 0.7)
        ring(cv, W / 2, H / 2, r * 0.7, 10, CYAN, 1 - sl)
        big_word(cv, w, WHITE, scale=pin, maxh=700)
        label(cv)
    elif kind == 8:  # invertido: branco/preto + barra laranja
        cv = solid(WHITE)
        big_word(cv, w, BLACK, scale=pin, cy=H / 2 - 40, maxh=760)
        bw = 900 * eo_expo(sl / 0.5)
        ImageDraw.Draw(cv).rectangle((W / 2 - bw / 2, 1100, W / 2 + bw / 2, 1140), fill=ORANGE)
        label(cv, BLACK)
    elif kind == 9:  # vertical, rotacionado
        cv = duotone(bg(bi, 1.12 - 0.08 * sl), DARK, CYAN)
        m = text(w, "tall", w=1250, h=1000)
        put(cv, m, WHITE, W / 2, H / 2, pin, rot=90)
        label(cv)
    elif kind == 10:  # knockout em laranja
        cv = solid(ORANGE)
        m = text(w, "tall", w=1000, h=1150)
        cv.paste(bg(bi, 1.2 - 0.1 * sl), (0, 0), full(m, W / 2, H / 2, pin))
        label(cv, BLACK)
    elif kind == 11:  # espelhado + 3 linhas largas
        a = bg(bi, 1.15 + 0.1 * sl)
        cv = darken(a, 0.4, vig=False)
        half = cv.crop((0, 0, W // 2, H))
        cv.paste(half.transpose(Image.FLIP_LEFT_RIGHT), (W // 2, 0))
        for i, ww in enumerate(WORDS):
            m = text(ww, "wide", w=760, h=300)
            put(cv, m, ORANGE if i == slot % 3 else WHITE, W / 2, 330 + i * 345, pin if i == slot % 3 else 1)
        label(cv)
    elif kind == 12:  # grade de contornos
        cv = solid(DARK)
        mo = text(w, "tall", h=230, stroke=4, outline=True)
        ms = text(w, "tall", h=230)
        cols = 3 if len(w) <= 2 else 2
        sx = W / cols
        z = 1.0 + 0.25 * sl
        for r in range(6):
            for c in range(cols + 1):
                x = W / 2 + (c - cols / 2) * sx * z + (r % 2) * sx / 2 * z
                y = H / 2 + (r - 2.5) * 245 * z
                solid_one = (r == 2 and c == 1)
                put(cv, ms if solid_one else mo, ORANGE if solid_one else (210, 210, 210), x, y, z)
    elif kind == 13:  # listras de perigo
        cv = stripes(ORANGE, BLACK, 80, offset=-sl * 320)
        m = text(w, "tall", w=960, h=760)
        put(cv, m, BLACK, W / 2 + 18, H / 2 + 18, pin)
        put(cv, m, WHITE, W / 2, H / 2, pin)
    elif kind == 14:  # zoom blur
        cv = solid(NAVY)
        m = text(w, "tall", w=940, h=800)
        for k in range(7, 0, -1):
            put(cv, m, CYAN, W / 2, H / 2, pin * (1 + 0.09 * k * (1 - sl * 0.5)), alpha=0.18)
        put(cv, m, WHITE, W / 2, H / 2, pin)
        label(cv)
    else:  # 15: WE ARE ON em uma linha piscando em semicolcheias
        q = int(sl * 2)
        bgc, tc = [(WHITE, BLACK), (BLACK, ORANGE)][q % 2]
        cv = solid(bgc)
        m = text("WE ARE ON", "tall", w=1000, h=420)
        put(cv, m, tc, W / 2, H / 2, 1 + 0.15 * (1 - eo_expo(ph(sl * 2) / 0.6)))
    return cv


def sec_repeat(lb, f):
    slot = int(lb * 2)
    sl = ph(lb * 2)
    cv = st_repeat(slot, sl, f)
    cv = flash(cv, 0.45 * env(sl, 14))
    cv = rgb_split(cv, 10 * env(sl, 8))
    return shake(cv, 14 * env(sl, 9) + 6 * env(ph(lb), 6), f)


def sec_build(lb, f):
    """16-20: semicolcheias acelerando + subida + respiro."""
    if lb < 3:
        sub = int(lb * 4)
        sp = ph(lb * 4)
        p = lb / 3
        word = WORDS[sub % 3]
        mode = sub % 4
        if mode == 0:
            cv, col = darken(bg((sub * 5) % 14, 1.1 + 0.4 * p), 0.45), WHITE
        elif mode == 1:
            cv, col = solid(BLACK), ORANGE
        elif mode == 2:
            cv, col = duotone(bg((sub * 3 + 7) % 14, 1.1 + 0.4 * p), DARK, CYAN), BLACK
        else:
            cv, col = solid(WHITE), BLACK
        s = (0.55 + 0.75 * p ** 1.5) * (1 + 0.2 * (1 - eo_expo(sp / 0.6)))
        big_word(cv, word, col, scale=s, maxh=700)
        label(cv, WHITE if mode < 3 else BLACK, 0.7)
        cv = flash(cv, 0.45 * p ** 2.2)
        cv = rgb_split(cv, 4 + 22 * p)
        cv = glitch(cv, f, n=int(10 * p), amp=int(40 + 100 * p))
        return shake(cv, 5 + 26 * p, f)
    if lb < 3.5:  # whiteout
        t = (lb - 3) / 0.5
        cv = darken(bg(11, 1.1 + 0.8 * t ** 2), 0.7)
        cv = flash(cv, 0.35 + 0.65 * t)
        put(cv, text("WE ARE ON", "tall", h=150, tr=0.05 + 0.25 * t), BLACK, W / 2, H / 2)
        return shake(cv, 18 * t, f)
    # respiro antes do drop
    t = (lb - 3.5) / 0.5
    cv = solid(BLACK)
    put(cv, text("WE ARE ON", "tall", h=120, tr=0.3 + 0.15 * t), WHITE, W / 2, H / 2)
    lw = 600 * eo_expo(t / 0.8)
    ImageDraw.Draw(cv).rectangle((W / 2 - lw / 2, H / 2 + 110, W / 2 + lw / 2, H / 2 + 116), fill=CYAN)
    return cv


def sec_drop(lb, f):
    """20-28: WE ARE ON STEAM."""
    beat = int(lb)
    bp = ph(lb)
    alt = False
    if lb >= 4:
        alt = beat % 2 == 1
    if lb >= 6:
        alt = int(lb * 2) % 2 == 1
    if alt:
        cv = radial_bg((140, 215, 255), CYAN, rad=800)
        rays(cv, W / 2, 680, 12, lb * 0.9, WHITE, 0.25)
        fg, logo_c, steam_c, sh = NAVY, NAVY, WHITE, NAVY
    else:
        cv = radial_bg(BLUE, DARK, rad=850)
        pic = duotone(bg((beat * 3 + 1) % 14, 1.2 - 0.1 * bp), DARK, CYAN)
        cv = blend(cv, pic, 0.22)
        rays(cv, W / 2, 680, 12, lb * 0.9, CYAN, 0.12)
        fg, logo_c, steam_c, sh = WHITE, WHITE, CYAN, DARK

    # anel de choque a cada batida
    r = 190 + 950 * eo_cubic(bp)
    ring(cv, W / 2, 680, r, 22 * (1 - bp) + 3, WHITE if not alt else NAVY, (1 - bp) ** 1.5)
    ring(cv, W / 2, 680, r * 0.75, 8, CYAN if not alt else WHITE, (1 - bp) ** 2)

    punch = 1 + 0.06 * env(bp, 7)

    # glow + logo steam
    ls = eo_back(lb / 0.55) * punch
    lrot = -220 * (1 - eo_expo(lb / 0.9))
    if not alt:
        g = Image.new("L", (W, H), 0)
        rr = int(240 * ls)
        ImageDraw.Draw(g).ellipse((W / 2 - rr, 680 - rr, W / 2 + rr, 680 + rr), fill=int(140 + 80 * env(bp, 5)))
        cv.paste(CYAN, (0, 0), g.filter(ImageFilter.GaussianBlur(70)))
    put(cv, steam_logo(400), logo_c, W / 2, 680, ls, lrot)

    # WE ARE ON desce do topo
    if lb >= 0.5:
        t = eo_expo((lb - 0.5) / 0.4)
        m = text("WE ARE ON", "tall", w=900, h=260)
        y = 260 - 500 * (1 - t)
        put(cv, m, sh, W / 2 + 10, y + 10, punch)
        put(cv, m, fg, W / 2, y, punch)
    # STEAM bate no 2o tempo
    if lb >= 1:
        t = eo_expo((lb - 1) / 0.35)
        m = text("STEAM", "wide", w=960, h=260)
        s = (1 + 1.4 * (1 - t)) * punch
        put(cv, m, sh, W / 2 + 12, 1080 + 12, s, alpha=t)
        put(cv, m, steam_c, W / 2, 1080, s, alpha=0.3 + 0.7 * t)

    # linhas de velocidade
    rng = np.random.default_rng(beat + 99)
    lm = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lm)
    for _ in range(36):
        a = rng.uniform(0, 2 * math.pi)
        r0 = 260 + 900 * eo_cubic(bp) * rng.uniform(0.4, 1.0)
        r1 = r0 + rng.uniform(60, 220)
        d.line((W / 2 + math.cos(a) * r0, 680 + math.sin(a) * r0, W / 2 + math.cos(a) * r1, 680 + math.sin(a) * r1),
               fill=int(200 * (1 - bp)), width=int(rng.integers(2, 6)))
    cv.paste(WHITE if not alt else NAVY, (0, 0), lm)

    label(cv, fg, 0.8)
    fl = 1.0 * env(lb, 4) + 0.6 * env(lb - 1, 7) + 0.25 * env(bp, 12) * (lb >= 2)
    cv = flash(cv, fl)
    cv = rgb_split(cv, 14 * env(bp, 6))
    return shake(cv, 26 * env(lb, 5) + 16 * env(lb - 1, 6) + 9 * env(bp, 8), f)


@lru_cache(None)
def button_layer():
    bw, bh, rad = 800, 150, 24
    grad = np.linspace(0, 1, bw, dtype=np.float32)[None, :, None]
    c0, c1 = np.array((117, 212, 255), np.float32), np.array((58, 143, 196), np.float32)
    g = np.repeat(c0 * (1 - grad) + c1 * grad, bh, axis=0)
    im = Image.fromarray(g.astype(np.uint8)).convert("RGBA")
    m = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, bw - 1, bh - 1), rad, fill=255)
    im.putalpha(m)
    lg = steam_logo(92)
    im.paste(NAVY, (40, (bh - 92) // 2), lg)
    tm = text("WISHLIST ON STEAM", "wide", w=590, h=58)
    im.paste(NAVY, (40 + 92 + 30, (bh - tm.height) // 2), tm)
    return im


def cursor_mask(size=90):
    m = Image.new("L", (size, size), 0)
    s = size / 24
    pts = [(2, 1), (2, 19), (7, 15), (10, 22), (13, 21), (10, 14), (17, 14)]
    ImageDraw.Draw(m).polygon([(x * s, y * s) for x, y in pts], fill=255)
    return m


def wish_scene(lb, f):
    beat = int(lb)
    bp = ph(lb)
    hb = int(lb * 2) if lb >= 6 else beat
    order = [10, 1, 4, 0, 2, 3, 12, 6, 8, 11, 5, 7, 9, 13]
    cv = darken(bg(order[hb % len(order)], 1.12 - 0.06 * bp + 0.03 * env(bp, 8)), 0.42)
    # gradiente laranja vindo de baixo
    gr = np.clip((_YY / H - 0.55) * 1.6, 0, 1)[..., None] * 0.45
    a = arr(cv)
    cv = img(a * (1 - gr) + np.array(ORANGE, np.float32) * gr)

    punch = 1 + 0.05 * env(bp, 8)
    # WISHLIST
    t = eo_expo(lb / 0.35)
    m = text("WISHLIST", "tall", w=960, h=420)
    s = (1 + 0.8 * (1 - t)) * punch
    put(cv, m, ORANGE, W / 2 + 14, 450 + 14, s)
    put(cv, m, WHITE, W / 2, 450, s)
    # NOW
    if lb >= 1:
        t = eo_expo((lb - 1) / 0.3)
        m = text("NOW", "wide", w=620, h=250)
        s = (1 + 1.2 * (1 - t)) * punch
        put(cv, m, BLACK, W / 2 + 12, 790 + 12, s)
        put(cv, m, ORANGE, W / 2, 790, s)
    # botao
    if lb >= 2:
        t = eo_back((lb - 2) / 0.5)
        press = 1 - 0.07 * env(lb - 5, 6) if lb >= 5 else 1
        s = t * (1 + 0.04 * env(bp, 7)) * press
        # halo
        hm = Image.new("L", (W, H), 0)
        ImageDraw.Draw(hm).rounded_rectangle((W / 2 - 420, 1080 - 95, W / 2 + 420, 1080 + 95), 40,
                                             fill=int(150 * clamp(t) * (0.6 + 0.4 * env(bp, 4))))
        cv.paste(CYAN, (0, 0), hm.filter(ImageFilter.GaussianBlur(28)))
        put_img(cv, button_layer(), W / 2, 1080, s)
        # cursor clica no botao
        if 4.2 <= lb:
            ct = eo_cubic((lb - 4.2) / 0.8)
            cx = W / 2 + 425 + (1 - ct) * 200
            cy = 1118 + (1 - ct) * 220
            if lb >= 5:
                rp = clamp((lb - 5) / 0.8)
                ring(cv, cx - 30, cy - 34, 20 + 140 * eo_cubic(rp), 8 * (1 - rp) + 2, WHITE, 1 - rp)
            cm = cursor_mask()
            put(cv, cm, BLACK, cx + 4, cy + 4, press)
            put(cv, cm.filter(ImageFilter.MaxFilter(5)), BLACK, cx, cy)
            put(cv, cm, WHITE, cx, cy, 0.86)
    # faixas marquee
    marquee(cv, "WISHLIST NOW  •  ON STEAM  •  ", 0, 96, ORANGE, BLACK, lb * 220)
    marquee(cv, "DIRTBIKE SIMULATOR  •  WISHLIST NOW  •  ", H - 96, 96, CYAN, NAVY, -lb * 220 + 3000)
    return cv


def sec_wish(lb, f):
    cv = wish_scene(lb, f)
    if lb < 0.5:  # wipe diagonal laranja revelando a cena
        t = eo_cubic(lb / 0.5)
        prev = sec_drop(8 + lb, f)
        x0 = -700 + (W + 1600) * t
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([(x0 + 900, 0), (W + 900, 0), (W + 900, H), (x0 + 400, H)], fill=255)
        cv.paste(prev, (0, 0), m)
        sl = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sl).polygon([(x0 + 600, 0), (x0 + 900, 0), (x0 + 400, H), (x0 + 100, H)], fill=255)
        cv.paste(ORANGE, (0, 0), sl)
    bp = ph(lb)
    fl = 0.5 * env(lb - 1, 9) + (0.15 * env(bp, 12) if lb >= 4 else 0)
    cv = flash(cv, fl)
    cv = rgb_split(cv, 10 * env(bp, 7) + 14 * env(lb - 1, 5))
    return shake(cv, 18 * env(lb - 1, 6) + 8 * env(bp, 9) + 10 * env(lb - 5, 8) * (lb >= 5), f)


def sec_end(lb, f):
    """36-44: logo final."""
    bp = ph(lb)
    z = 1.14 - 0.12 * eo_cubic(lb / 8)
    cv = darken(bg(11, z, dy=60), 0.72)
    gr = np.clip((_YY / H - 0.40) * 1.7, 0, 1)[..., None]
    cv = img(arr(cv) * (1 - gr * 0.88))

    # logo do jogo
    lg = game_logo()
    t = eo_expo(lb / 0.5)
    s = (960 / lg.width) * (1 + 0.5 * (1 - t)) * (1 + 0.012 * env(bp, 8) * (lb >= 1))
    put_img(cv, lg, W / 2, 800, s, alpha=clamp(lb / 0.15))
    # brilho atravessando o logo
    if 2 <= lb < 3.2:
        sp = (lb - 2) / 1.2
        L = lg.resize((int(lg.width * s), int(lg.height * s)), Image.BICUBIC)
        a = np.asarray(L.getchannel("A"), np.float32) / 255
        yy, xx = np.mgrid[0:L.height, 0:L.width]
        pos = -300 + (L.width + 600) * sp
        band = np.clip(1 - np.abs(xx + yy * 0.5 - pos) / 90, 0, 1)
        sm = Image.fromarray((a * band * 230).astype(np.uint8))
        cv.paste(WHITE, (int(W / 2 - L.width / 2), int(800 - L.height / 2)), sm)

    # linha laranja
    if lb >= 1:
        lw = 560 * eo_expo((lb - 1) / 0.5)
        ImageDraw.Draw(cv).rectangle((W / 2 - lw / 2, 1010, W / 2 + lw / 2, 1018), fill=ORANGE)
    # Steam + WISHLIST NOW ON STEAM
    if lb >= 1.5:
        t = eo_expo((lb - 1.5) / 0.5)
        dy = 50 * (1 - t)
        tm = text("WISHLIST NOW ON STEAM", "wide", w=680, h=60)
        lsz = 76
        total = lsz + 26 + tm.width
        x0 = W / 2 - total / 2
        put(cv, steam_logo(lsz), WHITE, x0 + lsz / 2, 1100 + dy, alpha=t)
        put(cv, tm, WHITE, x0 + lsz + 26 + tm.width / 2, 1100 + dy, alpha=t)
    if lb >= 2:
        t = eo_expo((lb - 2) / 0.5)
        m = text("STORE PAGE NOW LIVE", "wide", w=420, h=24, tr=0.12)
        put(cv, m, CYAN, W / 2, 1180, alpha=t * 0.95)

    cv = flash(cv, 0.9 * env(lb, 4))
    cv = rgb_split(cv, 22 * env(lb, 4) + 2 * env(bp, 10) * (lb >= 1))
    return shake(cv, 20 * env(lb, 5), f)


# ---------------------------------------------------------------- frame

def render(fi):
    b = fi / FPS * BPM / 60
    if b < 8:
        cv = sec_intro(b, fi)
    elif b < 16:
        cv = sec_repeat(b - 8, fi)
    elif b < 20:
        cv = sec_build(b - 16, fi)
    elif b < 28:
        cv = sec_drop(b - 20, fi)
    elif b < 36:
        cv = sec_wish(b - 28, fi)
    else:
        cv = sec_end(b - 36, fi)
    cv = grain(cv, fi + 7, 3.5)
    return cv.convert("RGB")


def render_bytes(fi):
    return render(fi).tobytes()


# ---------------------------------------------------------------- beat guia (opcional, so pra conferir sync)

def guide_beat(path):
    sr = 48000
    n = int(NFRAMES / FPS * sr)
    out = np.zeros(n, np.float32)
    spb = 60 / BPM
    rng = np.random.default_rng(1)

    def add(t, sig):
        i = int(t * sr)
        j = min(n, i + len(sig))
        if i < n:
            out[i:j] += sig[: j - i]

    tt = np.arange(int(0.45 * sr)) / sr
    kick = np.sin(2 * np.pi * (45 + 110 * np.exp(-tt * 28)) * tt) * np.exp(-tt * 7) * 0.9
    th = np.arange(int(0.05 * sr)) / sr
    hat = rng.normal(0, 1, len(th)) * np.exp(-th * 90) * 0.18
    tc = np.arange(int(0.2 * sr)) / sr
    clap = rng.normal(0, 1, len(tc)) * np.exp(-tc * 22) * 0.4
    timp = np.arange(int(2.0 * sr)) / sr
    impact = (np.sin(2 * np.pi * (35 + 60 * np.exp(-timp * 5)) * timp) * np.exp(-timp * 2.2) +
              rng.normal(0, 1, len(timp)) * np.exp(-timp * 4) * 0.35) * 0.9

    for k in range(TOTAL_BEATS):
        t = k * spb
        if 19 <= k < 20:
            continue  # respiro
        add(t, kick)
        if k % 2 == 1 and not (16 <= k < 20):
            add(t, clap)
        for s in (0, 0.5):
            if k < 16 or k >= 20:
                add(t + s * spb, hat)
        if 16 <= k < 19:
            for s in (0, .25, .5, .75):
                add(t + s * spb, clap * 0.6)
    # riser no build
    t0, t1 = 16 * spb, 19.5 * spb
    tr = np.arange(int((t1 - t0) * sr)) / sr
    riser = rng.normal(0, 1, len(tr)) * (tr / tr[-1]) ** 2 * 0.25
    riser += np.sin(2 * np.pi * (200 + 1400 * (tr / tr[-1]) ** 2) * tr) * (tr / tr[-1]) ** 2 * 0.12
    add(t0, riser)
    for k in (20, 28, 36):
        add(k * spb, impact)
    out = np.tanh(out * 1.4) * 0.8
    pcm = (np.stack([out, out], 1) * 32767).astype(np.int16)
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--stills":
        os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)
        for s in sys.argv[2].split(","):
            render(int(s)).save(os.path.join(OUT, "stills", f"f{int(s):04d}.jpg"), quality=88)
        return

    mp4 = os.path.join(OUT, "dirtbike-on-steam.mp4")
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-shortest", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", mp4,
    ], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, buf in enumerate(pool.imap(render_bytes, range(NFRAMES), chunksize=2)):
            ff.stdin.write(buf)
            if i % 60 == 0:
                print(f"frame {i}/{NFRAMES}", flush=True)
    ff.stdin.close()
    ff.wait()

    wav = os.path.join(OUT, "guide-beat-120bpm.wav")
    guide_beat(wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    os.path.join(OUT, "dirtbike-on-steam_with-guide-beat.mp4")], check=True)
    os.remove(wav)
    print("ok ->", mp4)


if __name__ == "__main__":
    main()
