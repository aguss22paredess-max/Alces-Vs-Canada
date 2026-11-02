#!/usr/bin/env python3
"""
AlceKnow - "Como ganar monedas facil en Alces vs Canada"

Genera un video vertical 1080x1920 (9:16), MP4 H.264 + AAC, con el
Alce Profesor hablando (lip-sync por volumen de la voz) y los iconos de
jugadas (error grave, error, buena jugada, brillante).

Uso:
    pip install -r requirements.txt
    python generate_video.py            # -> output/alceknow_monedas.mp4

La voz se genera offline con Piper (voz masculina es_MX "ald"). Si el
modelo no existe en ./voices se descarga automaticamente.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import tarfile
import urllib.request
import wave
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
VOICES = os.path.join(ROOT, "voices")
BUILD = os.path.join(ROOT, "build")
OUTPUT = os.path.join(ROOT, "output", "alceknow_monedas.mp4")

W, H, FPS = 1080, 1920, 30

# Voz: "un poco mas rapida" -> length_scale < 1 (0.85 = ~18% mas rapido)
VOICE_NAME = "es_MX-ald-medium"
VOICE_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/"
             "tts-models/vits-piper-es_MX-ald-medium.tar.bz2")
LENGTH_SCALE = 0.85

FONT_BLACK = [
    "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_BOLD = [
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

YELLOW = (255, 214, 64)
WHITE = (255, 255, 255)
INK = (24, 22, 38)


# ---------------------------------------------------------------------------
# Guion
# ---------------------------------------------------------------------------
# Cada linea: (texto que dice la voz, texto que aparece en pantalla).
# En el texto de pantalla, *palabra* se resalta en amarillo.
# La voz usa ortografia fonetica para nombres en ingles.

@dataclass
class Segment:
    kind: str                  # intro | play | outro
    pose: str
    lines: list
    icon: str | None = None
    label: str = ""
    color: tuple = YELLOW
    sfx: str = "ding"
    start: float = 0.0
    end: float = 0.0
    line_starts: list = field(default_factory=list)


SCRIPT = [
    Segment(
        kind="intro", pose="senalando", sfx="none",
        lines=[("¡Hola alumnos! Hoy en Alce Nou vamos a aprender cómo ganar "
                "monedas fácil en Alces vs Canadá.", None)],
    ),
    Segment(
        kind="play", pose="enojado_explicando", icon="blunder",
        label="ERROR GRAVE", color=(220, 52, 52), sfx="buzz",
        lines=[
            ("Error grave: no jugar con alces con habilidades.",
             "NO jugar con alces *CON habilidades*"),
            ("Jugar con alces sin habilidades puede ser una desventaja.",
             "Sin habilidades = *DESVENTAJA*"),
        ],
    ),
    Segment(
        kind="play", pose="enojado_parado", icon="mistake",
        label="ERROR", color=(240, 150, 40), sfx="buzz",
        lines=[
            ("Error: no capturar las banderas siendo alce.",
             "NO capturar las *banderas* siendo alce"),
            ("Esto es un error, puesto que es la única manera de ganar "
             "siendo alce.",
             "¡Es la *ÚNICA* forma de ganar siendo alce!"),
        ],
    ),
    Segment(
        kind="play", pose="explicando", icon="good",
        label="BUENA JUGADA", color=(140, 196, 72), sfx="ding",
        lines=[
            ("Buena jugada: unirse todos los días para recibir "
             "recompensas diarias.",
             "Unirse *todos los días* = recompensas diarias"),
        ],
    ),
    Segment(
        kind="play", pose="senalando", icon="brilliant",
        label="¡BRILLANTE!", color=(32, 190, 178), sfx="sparkle",
        lines=[
            ("Y la jugada brillante: que te unas todos los días,",
             "Únete *todos los días*"),
            ("invites a tus amigos para ganar dinero los dos,",
             "Invita amigos: *ganan los dos*"),
            ("y uses los códigos. Por ejemplo: zi ferst mus, que te da "
             "setecientas cincuenta monedas.",
             "CODE:*THEFIRSTMOOSE*|+750 MONEDAS"),
            ("Quédate a abrir los cofres,", "Abre los *cofres*"),
            ("y haz las misiones diarias.", "Haz las *misiones diarias*"),
        ],
    ),
    Segment(
        kind="play", pose="sorprendido", icon="crown",
        label="VIP", color=(232, 178, 30), sfx="sparkle",
        lines=[
            ("Por cierto: con el VIP, que cuesta cincuenta róbux,",
             "VIP = *50 Robux*"),
            ("te duplican el dinero ganado por ronda.",
             "*x2* monedas por ronda"),
        ],
    ),
    Segment(
        kind="outro", pose="normal_parado", sfx="ding",
        lines=[("¡Nos vemos en la próxima clase!", None)],
    ),
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def ease_out_back(x):
    x = min(max(x, 0.0), 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def remove_bg(img: Image.Image, thresh=38) -> Image.Image:
    """Quita el fondo liso haciendo flood-fill desde los bordes."""
    rgb = img.convert("RGB")
    probe = rgb.copy()
    key = (255, 0, 255)
    w, h = probe.size
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
             (w // 2, 0), (0, h // 2), (w - 1, h // 2)]
    for s in seeds:
        if probe.getpixel(s) != key:
            ImageDraw.floodfill(probe, s, key, thresh=thresh)
    # huecos interiores (p.ej. entre el brazo y el puntero)
    bgc = np.array(rgb.getpixel((2, 2)), dtype=int)
    # (solo zonas grandes: los pixeles sueltos de antialias se conservan)
    keep = (1, 2, 3)
    for _ in range(400):
        a = np.array(probe).astype(int)
        near = (np.abs(a - bgc).sum(2) <= 6)
        ys, xs = np.nonzero(near)
        if len(ys) == 0:
            break
        seed = (int(xs[0]), int(ys[0]))
        before = np.array(probe)
        ImageDraw.floodfill(probe, seed, key, thresh=6)
        changed = (np.array(probe) != before).any(2)
        if changed.sum() < 150:
            arr = np.array(probe)
            arr[changed] = keep
            probe = Image.fromarray(arr)
    a = np.array(probe)
    mask = ~((a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255))
    alpha = Image.fromarray((mask * 255).astype(np.uint8))
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(
        ImageFilter.GaussianBlur(0.7))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


# ---------------------------------------------------------------------------
# Sprites del alce (recortados de la hoja de modelo)
# ---------------------------------------------------------------------------

SHEET = os.path.join(ASSETS, "alce_profesor_sheet.png")
ICONS = os.path.join(ASSETS, "iconos_jugadas.png")
CELL_W, ROW_TOP, ROW_H, ROW_STEP = 360, 180, 410, 540
MOUTH = (164, 179, 196, 199)   # caja de la boca, relativa a la celda


def cell(sheet, row, col):
    x0, y0 = col * CELL_W, ROW_TOP + row * ROW_STEP
    return sheet.crop((x0, y0, x0 + CELL_W, y0 + ROW_H))


def with_mouth(base, donor):
    out = base.copy()
    out.paste(donor.crop(MOUTH), MOUTH[:2])
    return out


def load_poses(scale):
    sheet = Image.open(SHEET).convert("RGB")
    c = lambda r, k: cell(sheet, r, k)
    raw = {
        # pose: (boca cerrada, boca abierta)
        "normal_parado": (c(0, 0), c(0, 1)),
        "senalando": (c(1, 0), c(1, 1)),
        "enojado_parado": (c(0, 2), with_mouth(c(0, 2), c(0, 1))),
        "enojado_explicando": (c(1, 3), with_mouth(c(1, 3), c(1, 2))),
        "explicando": (with_mouth(c(1, 2), c(0, 0)), c(1, 2)),
        "sorprendido": (c(0, 3), with_mouth(c(0, 3), c(0, 1))),
    }
    poses = {}
    for name, pair in raw.items():
        imgs = []
        for im in pair:
            im = remove_bg(im)
            im = im.resize((int(im.width * scale), int(im.height * scale)),
                           Image.LANCZOS)
            imgs.append(im)
        poses[name] = tuple(imgs)
    return poses


ICON_BOXES = {
    "blunder": (300, 139, 428, 265),   # ?? rojo
    "mistake": (760, 0, 888, 125),     # ?  naranja/amarillo
    "good": (450, 700, 578, 825),      # pulgar arriba
    "brilliant": (0, 139, 128, 265),   # !! celeste
    "crown": (0, 280, 128, 406),       # corona (VIP)
    "book": (150, 139, 278, 265),      # libro (AlceKnow)
}


def load_icons():
    sheet = Image.open(ICONS).convert("RGB")
    out = {}
    for k, box in ICON_BOXES.items():
        x0, y0, x1, y1 = box
        crop = sheet.crop((x0 - 4, y0 - 4, x1 + 4, y1 + 4))
        out[k] = remove_bg(crop, thresh=20)
    return out


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def parse_runs(text):
    """'hola *mundo*' -> [('hola', False), ('mundo', True)] por palabra."""
    words, hl = [], False
    for part in text.split("*"):
        for w in part.split():
            words.append((w, hl))
        hl = not hl
    return words


def wrap_words(words, fnt, max_w):
    lines, cur, cur_w = [], [], 0
    space = fnt.getlength(" ")
    for w, hl in words:
        ww = fnt.getlength(w)
        add = ww if not cur else cur_w + space + ww
        if cur and add > max_w:
            lines.append(cur)
            cur, cur_w = [(w, hl)], ww
        else:
            cur.append((w, hl))
            cur_w = add
    if cur:
        lines.append(cur)
    return lines


def render_text_block(text, size, max_w, color=WHITE, hl_color=YELLOW,
                      stroke=8, line_gap=1.12, fpaths=FONT_BLACK):
    fnt = font(fpaths, size)
    lines = wrap_words(parse_runs(text), fnt, max_w)
    space = fnt.getlength(" ")
    lh = int(size * line_gap)
    widths = [sum(fnt.getlength(w) for w, _ in ln) + space * (len(ln) - 1)
              for ln in lines]
    bw = int(max(widths) + stroke * 2 + 8)
    bh = int(lh * len(lines) + stroke * 2 + size * 0.25)
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        x = (bw - widths[i]) / 2
        y = stroke + i * lh
        for w, hl in ln:
            d.text((x, y), w, font=fnt, fill=hl_color if hl else color,
                   stroke_width=stroke, stroke_fill=INK)
            x += fnt.getlength(w) + space
    return img


def drop_shadow(img, offset=(0, 10), blur=14, alpha=120):
    pad = blur * 3
    sh = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2),
                   (0, 0, 0, 0))
    a = img.getchannel("A").point(lambda v: v * alpha // 255)
    blk = Image.new("RGBA", img.size, (0, 0, 0, 255))
    blk.putalpha(a)
    sh.paste(blk, (pad + offset[0], pad + offset[1]), blk)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh.alpha_composite(img, (pad, pad))
    return sh


def render_code_item(text, max_w):
    code, sub = text[len("CODE:"):].split("|")
    code_img = render_text_block("CÓDIGO", 40, max_w, color=WHITE, stroke=0,
                                 fpaths=FONT_BOLD)
    main = render_text_block(code, 74, max_w, stroke=6)
    sub_img = render_text_block(sub, 54, max_w, color=YELLOW, stroke=6)
    bw = max(main.width, sub_img.width) + 70
    bh = code_img.height + main.height + sub_img.height + 30
    box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), 34, fill=(20, 18, 40, 235),
                        outline=YELLOW, width=6)
    y = 14
    for im in (code_img, main, sub_img):
        box.alpha_composite(im, ((bw - im.width) // 2, y))
        y += im.height - 4
    # moneda dibujada al lado del +750
    return box


# ---------------------------------------------------------------------------
# Audio: voz (Piper) + efectos
# ---------------------------------------------------------------------------

def ensure_voice():
    onnx = os.path.join(VOICES, VOICE_NAME + ".onnx")
    if os.path.exists(onnx) and os.path.exists(onnx + ".json"):
        return onnx
    os.makedirs(VOICES, exist_ok=True)
    tar_path = os.path.join(VOICES, "voice.tar.bz2")
    print("Descargando voz", VOICE_URL)
    urllib.request.urlretrieve(VOICE_URL, tar_path)
    with tarfile.open(tar_path) as tf:
        for m in tf.getmembers():
            base = os.path.basename(m.name)
            if base in (VOICE_NAME + ".onnx", VOICE_NAME + ".onnx.json"):
                m.name = base
                tf.extract(m, VOICES)
    os.remove(tar_path)
    return onnx


def tts(text, model, path):
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", model, "-f", path,
         "--length-scale", str(LENGTH_SCALE)],
        input=text.encode("utf-8"), check=True, capture_output=True)
    with wave.open(path) as wf:
        sr = wf.getframerate()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    return data.astype(np.float32) / 32768.0, sr


def sfx(kind, sr):
    def tone(freqs, dur, decay):
        t = np.arange(int(sr * dur)) / sr
        s = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
        return s * np.exp(-t * decay)

    if kind == "ding":
        return 0.35 * np.concatenate([tone([880, 1760], 0.12, 18),
                                      tone([1318, 2636], 0.45, 7)])
    if kind == "buzz":
        t = np.arange(int(sr * 0.35)) / sr
        s = np.sign(np.sin(2 * np.pi * 140 * t)) * 0.5 + \
            np.sin(2 * np.pi * 70 * t) * 0.5
        return 0.22 * s * np.exp(-t * 6)
    if kind == "sparkle":
        notes = [1046, 1318, 1568, 2093]
        parts = [tone([f, f * 2], 0.09, 10) for f in notes[:-1]]
        parts.append(tone([notes[-1], notes[-1] * 1.5], 0.5, 6))
        return 0.3 * np.concatenate(parts)
    return np.zeros(1)


def build_audio(model):
    os.makedirs(BUILD, exist_ok=True)
    sr = None
    voice = []          # (inicio, samples)
    effects = []
    t = 0.10
    for si, seg in enumerate(SCRIPT):
        seg.start = t
        if seg.sfx != "none":
            effects.append((t, seg.sfx))
            t += 0.20
        seg.line_starts = []
        for li, (say, _show) in enumerate(seg.lines):
            seg.line_starts.append(t)
            if not say:
                continue
            samples, sr = tts(say, model,
                              os.path.join(BUILD, f"voz_{si}_{li}.wav"))
            voice.append((t, samples))
            t += len(samples) / sr + 0.12
        t += 0.35
        seg.end = t
    total = t + 0.6
    mix = np.zeros(int(total * sr) + 1, np.float32)
    voz = np.zeros_like(mix)
    for start, s in voice:
        i = int(start * sr)
        voz[i:i + len(s)] += s
    mix += voz
    for start, kind in effects:
        s = sfx(kind, sr).astype(np.float32)
        i = int(start * sr)
        mix[i:i + len(s)] += s[:len(mix) - i]
    mix /= max(1.0, float(np.abs(mix).max()) / 0.95)
    out = os.path.join(BUILD, "audio.wav")
    with wave.open(out, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())
    # envolvente de la voz para el lip-sync (un valor por frame)
    n = int(total * FPS) + 1
    env = np.zeros(n)
    hop = sr / FPS
    for f in range(n):
        a = int(f * hop)
        seg = voz[a:a + int(hop)]
        env[f] = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
    env /= env.max() or 1
    return out, total, env


# ---------------------------------------------------------------------------
# Escena
# ---------------------------------------------------------------------------

def make_background():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    top, bot = np.array([30, 40, 92]), np.array([78, 34, 104])
    base = top[None, None, :] * (1 - y[..., None]) + bot[None, None, :] * y[..., None]
    stripes = ((np.floor((x * W + y * H) / 70) % 2) * 6)[..., None]
    glow = np.exp(-(((x - 0.5) * 1.6) ** 2 + ((y - 0.66) * 2.4) ** 2))[..., None]
    img = base + stripes + glow * np.array([60, 50, 40])
    img = np.clip(img, 0, 255).astype(np.uint8)
    bg = Image.fromarray(img, "RGB").convert("RGBA")
    return bg


def coin(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, size - 1, size - 1), fill=(196, 132, 20), outline=INK,
              width=max(3, size // 18))
    d.ellipse((size * .12, size * .12, size * .88, size * .82),
              fill=(255, 205, 50))
    f = font(FONT_BLACK, int(size * 0.5))
    d.text((size / 2, size / 2), "$", font=f, fill=(196, 132, 20),
           anchor="mm")
    return im


def paste_center(canvas, img, cx, cy, scale=1.0, alpha=1.0, angle=0.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)),
                          max(1, int(img.height * scale))), Image.BICUBIC)
    if angle:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 1.0:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(cx - img.width / 2), int(cy - img.height / 2)
    canvas.alpha_composite(img, (x, y)) if x >= 0 and y >= 0 else \
        canvas.paste(img, (x, y), img)


class Renderer:
    TEXT_W = 840          # ancho maximo del texto (zona segura TikTok)
    CARD = (70, 250, 1010, 1085)

    def __init__(self, env, total):
        self.env = env
        self.total = total
        self.bg = make_background()
        self.poses = load_poses(1.45)
        self.icons = load_icons()
        self.coin = coin(120)
        self.brand = self._brand()
        self.hook_title = render_text_block(
            "¿CÓMO GANAR *MONEDAS FÁCIL?*", 104, 900, stroke=10)
        self.hook_sub = render_text_block(
            "en *ALCES VS CANADÁ*", 66, 900, stroke=8)
        self.outro = render_text_block(
            "¡Sígueme para más clases de *AlceKnow!*", 84, 860, stroke=9)
        self.items = {}
        self.labels = {}
        for si, seg in enumerate(SCRIPT):
            if seg.kind != "play":
                continue
            self.labels[si] = drop_shadow(render_text_block(
                seg.label, 104, 900, color=seg.color, stroke=10))
            self.items[si] = self._layout_items(seg)
        self.mouth_open = self._mouth_track()

    def _brand(self):
        f = font(FONT_BLACK, 50)
        text = "AlceKnow"
        tw = int(f.getlength(text))
        icon = self_icon = None
        pill = Image.new("RGBA", (tw + 150, 92), (0, 0, 0, 0))
        d = ImageDraw.Draw(pill)
        d.rounded_rectangle((0, 0, pill.width - 1, 91), 46,
                            fill=(255, 255, 255, 235))
        d.text((112, 46), text, font=f, fill=INK, anchor="lm")
        return pill

    ITEMS_AVAIL = 440     # alto disponible para el texto en la tarjeta

    def _fit(self, shows):
        """Busca el tamano de letra mas grande con el que todo entra."""
        for size in range(92, 38, -4):
            imgs = []
            for s in shows:
                if s.startswith("CODE:"):
                    im = render_code_item(s, self.TEXT_W)
                    k = min(1.0, self.ITEMS_AVAIL / im.height)
                    im = im.resize((int(im.width * k), int(im.height * k)),
                                   Image.LANCZOS)
                else:
                    im = render_text_block(s, size, self.TEXT_W, stroke=8)
                imgs.append(im)
            total_h = sum(i.height for i in imgs) + 14 * (len(imgs) - 1)
            if total_h <= self.ITEMS_AVAIL:
                return imgs
        return imgs

    def _layout_items(self, seg):
        """<=2 lineas: se apilan. Mas lineas: una a la vez, bien grande."""
        if len(seg.lines) <= 2:
            imgs = iter(self._fit([s for _, s in seg.lines if s]))
            return [next(imgs) if s else None for _, s in seg.lines]
        return [self._fit([s])[0] if s else None for _, s in seg.lines]

    def _mouth_track(self):
        on, opened = False, []
        for v in self.env:
            if not on and v > 0.12:
                on = True
            elif on and v < 0.06:
                on = False
            opened.append(on)
        # alterna abierta/cerrada cada 3 frames mientras habla (mas natural)
        res = []
        for f, o in enumerate(opened):
            res.append(o and (f // 3) % 3 != 2)
        return res

    def segment_at(self, t):
        for si, seg in enumerate(SCRIPT):
            if t < seg.end:
                return si, seg
        return len(SCRIPT) - 1, SCRIPT[-1]

    def frame(self, f):
        t = f / FPS
        si, seg = self.segment_at(t)
        lt = t - seg.start
        img = self.bg.copy()

        # marca AlceKnow arriba (debajo de la barra de TikTok)
        img.alpha_composite(self.brand, ((W - self.brand.width) // 2, 140))
        paste_center(img, self.icons["book"], (W - self.brand.width) // 2 + 58,
                     186, scale=0.62)

        if seg.kind == "intro":
            self._draw_intro(img, t)
        elif seg.kind == "outro":
            pop = ease_out_back(lt / 0.4)
            paste_center(img, drop_shadow(self.icons["book"]), W / 2, 420,
                         scale=1.8 * max(pop, 0.01))
            paste_center(img, self.outro, W / 2, 700, scale=max(pop, 0.01))
        else:
            self._draw_play(img, si, seg, t, lt)

        # alce
        closed, opened = self.poses[seg.pose]
        talking = self.mouth_open[min(f, len(self.mouth_open) - 1)]
        sprite = opened if talking else closed
        bob = math.sin(t * 2 * math.pi * 0.9) * 6
        lvl = self.env[min(f, len(self.env) - 1)]
        sx = 1.0 + 0.012 * math.sin(t * 2 * math.pi * 0.45) + 0.01 * lvl
        sp = sprite.resize((int(sprite.width * sx), int(sprite.height * sx)),
                           Image.BILINEAR) if sx != 1 else sprite
        x = (W - sp.width) // 2
        y = int(1715 - sp.height + bob)
        img.alpha_composite(sp, (x, y))

        # destello rapido al cambiar de segmento
        if 0 < lt < 0.14 and si > 0:
            a = int(110 * (1 - lt / 0.14))
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, a)))
        return img.convert("RGB")

    def _draw_intro(self, img, t):
        # gancho: visible desde el frame 0
        pulse = 1.0 + 0.035 * math.sin(t * 2 * math.pi * 1.6)
        paste_center(img, drop_shadow(self.hook_title), W / 2, 480,
                     scale=pulse)
        paste_center(img, self.hook_sub, W / 2, 760)
        for i, (cx, cy, ph) in enumerate([(110, 900, 0), (970, 880, 1.3),
                                          (230, 1060, 2.1), (850, 1080, 0.7),
                                          (95, 1240, 2.8), (985, 1250, 1.9)]):
            dy = math.sin(t * 3 + ph) * 18
            ang = math.sin(t * 2 + ph) * 15
            paste_center(img, self.coin, cx, cy + dy,
                         scale=0.7 + 0.15 * (i % 2), angle=ang)

    def _draw_play(self, img, si, seg, t, lt):
        x0, y0, x1, y1 = self.CARD
        card = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle((0, 0, card.width - 1, card.height - 1), 48,
                            fill=(14, 12, 32, 170), outline=seg.color + (255,),
                            width=8)
        appear = ease_out(lt / 0.25)
        paste_center(img, card, W / 2, (y0 + y1) / 2 + (1 - appear) * 40,
                     alpha=appear)

        many = len(seg.lines) > 2
        icon_y = 375
        icon_scale = 1.5 * ease_out_back(lt / 0.4)
        shake = 0.0
        if seg.sfx == "buzz" and lt < 0.6:
            shake = math.sin(lt * 50) * 9 * (1 - lt / 0.6)
        glow = 1 + 0.05 * math.sin(t * 2 * math.pi * 1.2)
        paste_center(img, drop_shadow(self.icons[seg.icon]), W / 2, icon_y,
                     scale=icon_scale * glow, angle=shake)
        label = self.labels[si]
        lbl_pop = ease_out_back((lt - 0.12) / 0.35)
        label_y = icon_y + 160
        paste_center(img, label, W / 2, label_y, scale=max(lbl_pop, 0.01))

        top = label_y + label.height / 2 - 10
        bottom = y1 - (60 if many else 30)
        items = list(zip(self.items[si], seg.line_starts))
        if many:
            shown = [(im, st) for im, st in items if im and t >= st][-1:]
            # puntos de progreso
            n = len(items)
            cur = sum(1 for _, st in items if t >= st)
            d = ImageDraw.Draw(img)
            for i in range(n):
                cx = W / 2 + (i - (n - 1) / 2) * 44
                r = 12 if i < cur else 9
                d.ellipse((cx - r, y1 - 52 - r, cx + r, y1 - 52 + r),
                          fill=seg.color if i < cur else (90, 86, 120))
        else:
            shown = [(im, st) for im, st in items if im]
        total_h = sum(im.height for im, _ in shown) + 14 * (len(shown) - 1)
        y = top + max(0, (bottom - top - total_h) / 2)
        for im, st in shown:
            k = (t - st) / 0.28
            if k > 0:
                a = ease_out(k)
                paste_center(img, im, W / 2, y + im.height / 2 + (1 - a) * 40,
                             alpha=a, scale=0.9 + 0.1 * ease_out_back(k))
            y += im.height + 14


def main():
    model = ensure_voice()
    print("Generando voz...")
    audio, total, env = build_audio(model)
    print(f"Duracion: {total:.2f}s")
    if not 15 <= total <= 60:
        print("ADVERTENCIA: la duracion esta fuera de 15-60 s")
    r = Renderer(env, total)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    nframes = int(math.ceil(total * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", audio,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
           "-shortest", "-movflags", "+faststart", OUTPUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(nframes):
        proc.stdin.write(r.frame(f).tobytes())
        if f % 150 == 0:
            print(f"  frame {f}/{nframes}")
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg fallo")
    print("Listo:", OUTPUT)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        # python generate_video.py --preview 1.0 5.0 12.0  -> PNGs en build/
        model = ensure_voice()
        audio, total, env = build_audio(model)
        r = Renderer(env, total)
        for s in sys.argv[2:]:
            fr = int(float(s) * FPS)
            r.frame(fr).save(os.path.join(BUILD, f"preview_{s}.png"))
        for seg in SCRIPT:
            print(seg.kind, seg.label, round(seg.start, 2), round(seg.end, 2))
        print("total", round(total, 2))
    else:
        main()
