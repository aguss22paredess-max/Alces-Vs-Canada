#!/usr/bin/env python3
"""
AlceKnow - "Ranking de TODAS las skins de Alce"

Reutiliza el estilo y el sistema de barra de nota de
video_ranking_soldados.py y agrega: narracion con subtitulos sincronizados,
iconos de skins dibujados, precio con moneda, etiquetas, sellos, cinta,
caja de codigo y confeti para el #1.

    python video_ranking_skins.py             -> output/alceknow_ranking_skins.mp4
    python video_ranking_skins.py --muestras  -> output/muestras_skins/ (5 PNG + 10 s de voz)
"""
from __future__ import annotations

import hashlib
import math
import os
import random
import re
import subprocess
import sys
import tarfile
import urllib.request
import wave
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import generate_video as g
import video_ranking_soldados as rs
from generate_video import (FONT_BLACK, FONT_BOLD, INK, WHITE, YELLOW, W, H,
                            FPS, drop_shadow, ease_out, ease_out_back, font,
                            paste_center)
from video_ranking_soldados import SR, pill, text

OUTPUT = os.path.join(g.ROOT, "output", "alceknow_ranking_skins.mp4")
MUESTRAS = os.path.join(g.ROOT, "output", "muestras_skins")

# --- voz -------------------------------------------------------------------
# edge-tts (es-MX-JorgeNeural / es-CL-LorenzoNeural) no es accesible desde
# este entorno; se uso Piper offline. Entre las voces es_MX probadas, la que
# mejor reconocio Whisper fue "claude-high".
VOICE = "es_MX-claude-high"
VOICE_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/"
             "tts-models/vits-piper-es_MX-claude-high.tar.bz2")
LENGTH_SCALE = 0.97           # velocidad normal (3 % mas agil)

# Solo para el TTS: como deben sonar algunas palabras
FONETICA = {
    "AlceCoins": "Alce Cóins",
    "GOLDMOOSE": "Góld Mus",
    "Aguz": "Agús",
    "studs": "stads",
    "PEEERO": "Peeeeero",
    "AlceKnow": "Alce Nou",
    "4 Fantásticos": "cuatro Fantásticos",
    "Halloween": "Jálowin",
}

# --- layout (zona segura: 120 px a los lados, 250 px abajo) ----------------
SAFE_X0, SAFE_X1, SAFE_BOTTOM = 120, W - 120, H - 250
CARD = (SAFE_X0, 290, SAFE_X1, 1005)
TEXT_W = SAFE_X1 - SAFE_X0 - 70
DOTS_Y = CARD[3] + 30
SUB_Y = 1122
MOOSE_SCALE = 1.1
MOOSE_BOTTOM = SAFE_BOTTOM - 5

GRAY = (150, 150, 165)
RED, ORANGE, AMBER = rs.RED, rs.ORANGE, rs.AMBER
GREEN, GOLD, SOFT = rs.GREEN, rs.GOLD, rs.SOFT
PLUS, MINUS = (150, 230, 110), (255, 120, 110)


def nota_color(n):
    if n is None:
        return GRAY
    if n >= 10:
        return GOLD
    if n >= 8.5:
        return GREEN
    if n >= 7.5:
        return AMBER
    if n >= 6:
        return ORANGE
    return RED


# ---------------------------------------------------------------------------
# Datos (solo lo indicado por el usuario)
# ---------------------------------------------------------------------------

@dataclass
class Skin:
    puesto: str
    nombre: str
    corto: str                 # nombre en la tabla final
    nota: float | None
    nota_txt: str
    precio: str                # "" = sin precio; "Gratis", "Solo con código"...
    tag: str                   # COSMÉTICA / CON HABILIDAD / ""
    iconos: list
    lineas: list               # (texto, tipo, palabra que lo dispara)
    voz: str                   # texto de la narracion (con *resaltado*)
    pose: str
    gesto: str = ""            # "" | pensando
    rareza: str = ""
    sello: str = ""            # palabra que dispara el sello RECOMENDADO
    cinta: str = ""
    tachado: bool = False
    codigo: str = ""


SKINS = [
    Skin("#11", "POR DEFECTO", "POR DEFECTO", None, "NULA", "Gratis", "",
         ["default"],
         [("Marrón con *ojos rojos*", "i", "marrón"),
          ("“Aburrida, pero gratis”", "verdict", "Aburrida")],
         "Por defecto: marrón, ojos rojos. *Aburrida*, pero *gratis*.",
         "normal_parado", gesto="pensando"),
    Skin("#10", "ALCE PLATINO", "PLATINO", 4, "4", "500", "COSMÉTICA",
         ["platino"],
         [("Bonita, pero *puramente cosmética*", "i", "bonita")],
         "*Platino*: bonita, pero solo *cosmética*.", "explicando"),
    Skin("#9", "ALCE DORADO", "DORADO", 5, "5", "Solo con código",
         "COSMÉTICA", ["dorado"],
         [("*Estatua* en el lobby y en los mapas", "i", "estatua")],
         "*Dorado*: sin habilidades, pero con *estatua* en el lobby. "
         "*Gratis* con el código *GOLDMOOSE*.", "senalando",
         codigo="GOLDMOOSE"),
    Skin("#8", "ALCE DIAMANTE y\nALCE ESMERALDA", "DIAMANTE y ESMERALDA",
         5.5, "5,5", "2000 cada una", "COSMÉTICAS", ["diamante", "esmeralda"],
         [("Bonitas, pero *sin habilidades*", "i", "bonitas")],
         "*Diamante* y *Esmeralda*: bonitas, sin habilidades, *dos mil* "
         "cada una.", "normal_parado", gesto="pensando"),
    Skin("#7", "ALCE SOMBRA", "SOMBRA", 6.5, "6,5", "1500", "CON HABILIDAD",
         ["sombra"],
         [("*Invisible* por *20 s*", "+", "invisible"),
          ("Contra: si una linterna te alumbra *3 s*, reapareces", "-",
           "linterna")],
         "*Sombra*: *invisible* veinte segundos… pero si una *linterna* lo "
         "alumbra tres segundos, *reaparece*.", "sorprendido"),
    Skin("#6", "ALCE AURORA", "AURORA", 7, "7", "3000", "CON HABILIDAD",
         ["aurora"],
         [("Teletransporte de *100 studs*", "+", "teletransporta"),
          ("*SOLO* en el mapa Ártico", "-", "Ártico")],
         "*Aurora* se teletransporta *cien studs*. Ojo, pillo: *solo en el "
         "Ártico*.", "explicando"),
    Skin("#5", "ALCE MAGMA", "MAGMA", 7.8, "7,8", "1800", "CON HABILIDAD",
         ["magma"],
         [("Quema *5 de daño* al contacto", "+", "quema")],
         "*Magma*: parece la Mole de los 4 Fantásticos, pero *quema* a los "
         "Soldados cercanos.", "senalando",
         sello="Recomendado"),
    Skin("#5", "ALCE PERÚ", "PERÚ", 7.8, "7,8", "2500", "CON HABILIDAD",
         ["peru"],
         [("*Escudo* anti-disparos", "+", "escudo"),
          ("*30%* menos daño de disparos", "+", "treinta"),
          ("(solo disparos, no cuchilladas)", "note", "Solo")],
         "*Alce Perú*: ¿xenofobia o *mística*? Su *escudo* le quita *treinta "
         "por ciento* del daño de disparos. Solo disparos, *no cuchilladas*.",
         "sorprendido", rareza="MÍTICO"),
    Skin("#4", "ALCE FLACO", "FLACO", 8.1, "8,1", "1200", "CON HABILIDAD",
         ["flaco"],
         [("*+35%* de velocidad", "+", "treinta"),
          ("Ideal para *remontar* partidas", "i", "remontar")],
         "El *Flaco* corre *treinta y cinco por ciento* más rápido. Ideal "
         "para *remontar*.", "explicando", sello="remontar"),
    Skin("#2", "ALCE CALABAZA", "CALABAZA", 8.9, "8,9", "6000",
         "CON HABILIDAD", ["calabaza"],
         [("*Calabomba*: 30–65 de daño, lanzamiento recto o bombeado", "+",
           "Calabomba"),
          ("*Disfraz*", "+", "Disfraz"),
          ("Contra: solo *150 de vida*", "-", "PEEERO")],
         "*Calabaza*: *Disfraz* y *Calabomba*, una granada de *treinta a "
         "sesenta y cinco* de daño. *PEEERO* solo tiene *ciento cincuenta* de "
         "vida. Lástima: era de *Halloween* y *ya no se consigue*.",
         "sorprendido", cinta="EDICIÓN HALLOWEEN · YA NO DISPONIBLE",
         tachado=True),
    Skin("#1", "ALCE AGUZ", "AGUZ", 10, "10", "15000", "CON HABILIDAD",
         ["aguz"],
         [("*50%* menos daño de disparos", "+", "Cincuenta"),
          ("*+10%* de velocidad", "+", "diez"),
          ("Tool: *Embestida*", "+", "Embestida"),
          ("Diseño de la skin del creador", "note", "creador")],
         "*Número uno*: *Alce Aguz*, diseño del *creador*. *Cincuenta "
         "por ciento* menos daño de disparos, *diez por ciento* más velocidad "
         "y *Embestida*: contra un muro te aturdes; contra un Soldado, lo "
         "*empujas*. *Quince mil* AlceCoins… y *valen la pena*.",
         "senalando", rareza="RAREZA MÁXIMA"),
]

HOOK_VOZ = ("Califiqué *TODAS* las skins de Alce. ¿Cuál vale tus "
            "*AlceCoins*?")
RANK_VOZ = "Ese fue el *ranking*."
OUTRO_VOZ = "¿Cuál es tu skin *favorita*? *¡Comenta!*"


# ---------------------------------------------------------------------------
# Iconos de skins (cabeza de alce dibujada, con el color de cada skin)
# ---------------------------------------------------------------------------

ANT = (238, 215, 160)
FUR = (140, 95, 60)
MUZ = (205, 165, 120)
OLW = 8


def _shade(col, k):
    return tuple(max(0, min(255, int(c * k))) for c in col)


def fur_pattern(kind, size=400):
    y = np.linspace(0, 1, size)[:, None]
    x = np.linspace(0, 1, size)[None, :]
    shade = (1.12 - 0.28 * y)[..., None] * np.ones((1, size, 1))

    def solid(c):
        return np.ones((size, size, 3)) * np.array(c)[None, None, :]

    if kind == "default" or kind == "aguz":
        base = solid(FUR)
    elif kind == "platino":
        base = solid((214, 220, 230))
        base += (np.abs((x + y) - 0.9) < 0.06)[..., None] * 35
    elif kind == "dorado":
        base = solid((236, 182, 40))
        base += (np.abs((x + y) - 0.9) < 0.07)[..., None] * 45
    elif kind == "sombra":
        base = solid((48, 30, 70))
    elif kind == "diamante":
        base = solid((120, 214, 245))
        base += ((np.floor(x * 7) + np.floor(y * 7)) % 2)[..., None] * 25
    elif kind == "esmeralda":
        base = solid((40, 170, 100))
        base += ((np.floor(x * 7) + np.floor(y * 7)) % 2)[..., None] * 22
    elif kind == "magma":
        base = solid((196, 46, 30)) * (1 - y[..., None] * 0.2)
        base += (np.sin(x * 30 + np.sin(y * 9) * 3) > 0.93)[..., None] * \
            np.array([60, 140, 30])
    elif kind == "flaco":
        base = solid((130, 70, 190))
    elif kind == "peru":
        red = np.array([210, 30, 45])
        white = np.array([245, 245, 245])
        band = ((x > 0.4) & (x < 0.6))[..., None]
        base = np.where(band, white, red) * np.ones((size, size, 1))
        shade = shade * 0 + 1.0
    elif kind == "aurora":
        cols = np.array([(40, 200, 140), (40, 170, 220), (130, 80, 220),
                         (220, 70, 170)])
        tt = np.clip(y + 0.15 * np.sin(x * 9), 0, 0.999) * (len(cols) - 1)
        i0 = np.floor(tt).astype(int)
        fr = (tt - i0)[..., None]
        base = cols[i0] * (1 - fr) + cols[np.minimum(i0 + 1, 3)] * fr
    elif kind == "calabaza":
        base = solid((245, 140, 30))
        base -= (np.abs(np.sin(x * math.pi * 6)) < 0.18)[..., None] * 45
    else:
        base = solid(FUR)
    img = np.clip(base * shade, 0, 255).astype(np.uint8)
    return Image.fromarray(img, "RGB").convert("RGBA")


def _fill_shape(canvas, shape, bbox, pattern):
    mask = Image.new("L", canvas.size, 0)
    md = ImageDraw.Draw(mask)
    getattr(md, shape)(bbox, fill=255)
    canvas.paste(pattern, (0, 0), mask)
    ImageDraw.Draw(canvas).__getattribute__(shape)(bbox, outline=INK,
                                                   width=OLW)


def skin_head(kind):
    S = 400
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pat = fur_pattern(kind)
    ant = ANT
    if kind == "dorado":
        ant = (255, 222, 120)
    elif kind == "sombra":
        ant = (120, 100, 150)
    elif kind == "diamante":
        ant = (220, 245, 255)
    elif kind == "magma":
        ant = (60, 40, 40)
    # astas
    left = [(156, 160), (120, 128), (72, 122), (38, 70), (72, 92), (74, 46),
            (98, 88), (112, 36), (128, 86), (150, 56), (150, 110), (176, 146)]
    for pts in (left, [(S - x, y) for x, y in left]):
        d.polygon(pts, fill=ant, outline=INK, width=OLW)
    # orejas + cabeza con el patron de la skin
    _fill_shape(im, "ellipse", (78, 172, 166, 224), pat)
    _fill_shape(im, "ellipse", (234, 172, 322, 224), pat)
    _fill_shape(im, "ellipse", (116, 112, 284, 334), pat)
    d = ImageDraw.Draw(im)
    if kind == "magma":
        for (x0, y0, x1, y1) in ((150, 150, 175, 185), (230, 140, 250, 175),
                                 (135, 230, 160, 250)):
            d.line((x0, y0, x1, y1), fill=(255, 190, 40), width=6)
    # sombrero / gorro (antes del hocico y los ojos)
    if kind == "aguz":
        d.ellipse((118, 112, 282, 140), fill=(25, 25, 30), outline=INK,
                  width=OLW)
        d.rounded_rectangle((150, 18, 250, 128), 10, fill=(25, 25, 30),
                            outline=INK, width=OLW)
        d.rectangle((154, 92, 246, 112), fill=(200, 40, 50))
    if kind == "peru":
        # chullo andino con franjas en zigzag y pompon
        d.pieslice((128, 82, 272, 230), 180, 360, fill=(210, 30, 45),
                   outline=INK, width=OLW)
        for k, col in enumerate(((245, 245, 245), (250, 200, 40))):
            yy = 128 + k * 22
            pts = [(140 + i * 15, yy + (8 if i % 2 else -8))
                   for i in range(9)]
            d.line(pts, fill=col, width=8)
        d.ellipse((180, 58, 220, 98), fill=(245, 245, 245), outline=INK,
                  width=6)
        for sx in (-1, 1):
            cx = 200 + sx * 70
            d.polygon([(cx - 18, 150), (cx + 18, 150), (cx, 230)],
                      fill=(210, 30, 45), outline=INK, width=6)
    if kind == "calabaza":
        d.rounded_rectangle((188, 70, 214, 124), 8, fill=(70, 130, 50),
                            outline=INK, width=6)
        d.ellipse((208, 78, 262, 108), fill=(90, 170, 60), outline=INK,
                  width=5)
    # hocico
    muz = MUZ
    if kind == "sombra":
        muz = (90, 70, 110)
    elif kind in ("platino", "diamante"):
        muz = (235, 230, 225)
    d.ellipse((138, 236, 262, 340), fill=muz, outline=INK, width=OLW)
    d.ellipse((170, 270, 186, 284), fill=INK)
    d.ellipse((214, 270, 230, 284), fill=INK)
    d.arc((178, 290, 222, 318), 20, 160, fill=INK, width=6)
    # ojos
    eye = {"default": (220, 30, 30), "sombra": (200, 120, 255),
           "magma": (255, 160, 30)}.get(kind, INK)
    for cx in (172, 228):
        d.ellipse((cx - 24, 180, cx + 24, 228), fill=WHITE, outline=INK,
                  width=6)
        d.ellipse((cx - 11, 194, cx + 11, 216), fill=eye)
        d.ellipse((cx - 2, 196, cx + 6, 204), fill=WHITE)
    if kind == "flaco":
        im = im.resize((int(S * 0.8), S), Image.LANCZOS)
        out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        out.alpha_composite(im, ((S - im.width) // 2, 0))
        im = out
        d = ImageDraw.Draw(im)
        for k in range(3):    # lineas de velocidad
            yy = 210 + k * 34
            d.line((20, yy, 70 - k * 8, yy), fill=WHITE, width=8)
    if kind in ("diamante", "esmeralda", "dorado", "platino"):
        for (sx, sy, r) in ((300, 120, 22), (95, 260, 16), (310, 300, 14)):
            d.polygon([(sx, sy - r), (sx + r * .3, sy - r * .3), (sx + r, sy),
                       (sx + r * .3, sy + r * .3), (sx, sy + r),
                       (sx - r * .3, sy + r * .3), (sx - r, sy),
                       (sx - r * .3, sy - r * .3)], fill=WHITE)
    return im


BADGE_BG = {"default": (70, 50, 40), "platino": (70, 76, 92),
            "dorado": (96, 70, 20), "diamante": (30, 80, 110),
            "esmeralda": (20, 80, 50), "sombra": (30, 20, 45),
            "aurora": (20, 40, 70), "magma": (90, 25, 15),
            "flaco": (60, 30, 90), "peru": (110, 25, 35),
            "calabaza": (100, 50, 15), "aguz": (60, 45, 30)}


def skin_badge(kind, ring, size):
    S = 440
    b = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.ellipse((6, 6, S - 7, S - 7), fill=BADGE_BG.get(kind, (40, 40, 60)))
    if kind == "aurora":
        for k, col in enumerate(((60, 230, 160, 90), (120, 90, 240, 80))):
            d.arc((40, 60 + k * 40, 400, 330 + k * 40), 200, 340,
                  fill=col, width=26)
    head = skin_head(kind).resize((380, 380), Image.LANCZOS)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    layer.alpha_composite(head, (30, 44))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((6, 6, S - 7, S - 7), fill=255)
    clipped = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    clipped.paste(layer, (0, 0), Image.composite(
        layer.getchannel("A"), Image.new("L", (S, S), 0), mask))
    b.alpha_composite(clipped)
    d = ImageDraw.Draw(b)
    d.ellipse((6, 6, S - 7, S - 7), outline=ring, width=24)
    d.ellipse((6, 6, S - 7, S - 7), outline=INK, width=6)
    return b.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Narracion: TTS con cache, frases y subtitulos
# ---------------------------------------------------------------------------

def ensure_voice():
    onnx = os.path.join(g.VOICES, VOICE + ".onnx")
    if os.path.exists(onnx) and os.path.exists(onnx + ".json"):
        return onnx
    os.makedirs(g.VOICES, exist_ok=True)
    tar_path = os.path.join(g.VOICES, "voice.tar.bz2")
    print("Descargando voz", VOICE_URL)
    urllib.request.urlretrieve(VOICE_URL, tar_path)
    with tarfile.open(tar_path) as tf:
        for m in tf.getmembers():
            base = os.path.basename(m.name)
            if base in (VOICE + ".onnx", VOICE + ".onnx.json"):
                m.name = base
                tf.extract(m, g.VOICES)
    os.remove(tar_path)
    return onnx


def plain(s):
    return s.replace("*", "")


def for_tts(s):
    s = plain(s)
    for a, b in FONETICA.items():
        s = s.replace(a, b)
    # palabras en MAYUSCULAS: en minuscula para que no las deletree
    return re.sub(r"\b([A-ZÁÉÍÓÚÑ]{2,})\b", lambda m: m.group(1).lower()
                  if m.group(1) not in ("VIP",) else m.group(1), s)


def tts(text_):
    os.makedirs(g.BUILD, exist_ok=True)
    key = hashlib.md5(f"{VOICE}|{LENGTH_SCALE}|{text_}".encode()).hexdigest()
    path = os.path.join(g.BUILD, f"skins_{key[:16]}.wav")
    if not os.path.exists(path):
        subprocess.run([sys.executable, "-m", "piper", "-m", ensure_voice(),
                        "-f", path, "--length-scale", str(LENGTH_SCALE)],
                       input=text_.encode("utf-8"), check=True,
                       capture_output=True)
    with wave.open(path) as wf:
        sr = wf.getframerate()
        dd = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    x = dd.astype(np.float32) / 32768.0
    n = int(len(x) * SR / sr)
    x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)),
                  x).astype(np.float32)
    # recorta silencios al inicio y al final
    idx = np.nonzero(np.abs(x) > 0.02)[0]
    if len(idx):
        a = max(0, idx[0] - int(0.03 * SR))
        b = min(len(x), idx[-1] + int(0.06 * SR))
        x = x[a:b]
    return x


def split_sentences(s):
    parts = re.split(r"(?<=[.?!…])\s+", s.strip())
    return [p for p in parts if p]


def chunk_words(sentence, max_chars=24):
    """Subtitulos de 2-6 palabras: corta primero en comas/dos puntos y
    luego reparte cada tramo largo en partes de largo parecido."""
    words = sentence.split()
    clauses, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[,:;]\**$", w):
            clauses.append(cur)
            cur = []
    if cur:
        clauses.append(cur)
    # une tramos de una sola palabra con el siguiente / anterior
    merged = []
    for c in clauses:
        if merged and (len(c) == 1 or len(merged[-1]) == 1) and \
                len(plain(" ".join(merged[-1] + c))) <= max_chars + 6:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    out = []
    for c in merged:
        n_chars = len(plain(" ".join(c)))
        parts = max(1, math.ceil(n_chars / max_chars))
        parts = min(parts, max(1, len(c) // 2))
        target = n_chars / parts
        cur, acc = [], 0
        for i, w in enumerate(c):
            cur.append(w)
            acc += len(plain(w)) + 1
            left = len(c) - i - 1
            if len(out_parts := cur) and acc >= target * 0.95 and left >= 2 \
                    and parts > 1:
                out.append(" ".join(out_parts))
                cur, acc, parts = [], 0, parts - 1
        if cur:
            out.append(" ".join(cur))
    return out


def fix_markup(chunks):
    """Si un *resaltado* cruza dos subtitulos, lo cierra/abre en cada uno."""
    out, open_ = [], False
    for c in chunks:
        prefix = "*" if open_ else ""
        if c.count("*") % 2:
            open_ = not open_
        out.append(prefix + c + ("*" if open_ else ""))
    return out


def pauses(x):
    """Centros de silencios internos (s) de al menos 70 ms."""
    hop = int(0.01 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2))
                  for i in range(0, len(x) - hop, hop)])
    quiet = e < max(0.008, e.max() * 0.06)
    res, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        if not q and start is not None:
            if i - start >= 7 and start > 3:
                res.append((start + i) / 2 * 0.01)
            start = None
    return res


@dataclass
class Narr:
    audio: np.ndarray
    subs: list                  # (inicio, fin, texto) relativos
    words: list                 # (inicio, palabra) relativos


def narrate(display):
    """Sintetiza frase por frase y calcula los tiempos de los subtitulos."""
    pieces, subs, words = [], [], []
    t = 0.0
    gap = 0.10
    for sent in split_sentences(display):
        x = tts(for_tts(sent))
        dur = len(x) / SR
        chunks = chunk_words(sent)
        weights = [len(plain(c)) + 3 * bool(re.search(r"[,:;]\**$", c))
                   for c in chunks]
        tot = sum(weights)
        bounds = [0.0]
        acc = 0
        for wgt in weights[:-1]:
            acc += wgt
            bounds.append(dur * acc / tot)
        bounds.append(dur)
        ps = pauses(x)
        for k in range(1, len(bounds) - 1):   # ajusta cortes a las pausas
            if re.search(r"[,:;]\**$", chunks[k - 1]) and ps:
                near = min(ps, key=lambda p: abs(p - bounds[k]))
                if abs(near - bounds[k]) < 0.45:
                    bounds[k] = near
        for k, c in enumerate(fix_markup(chunks)):
            subs.append((t + bounds[k], t + bounds[k + 1], c))
            ws = c.split()
            span = bounds[k + 1] - bounds[k]
            for j, w in enumerate(ws):
                words.append((t + bounds[k] + span * j / len(ws), plain(w)))
        pieces.append(x)
        pieces.append(np.zeros(int(gap * SR), np.float32))
        t += dur + gap
    audio = np.concatenate(pieces[:-1]) if pieces else np.zeros(1)
    return Narr(audio, subs, words)


# ---------------------------------------------------------------------------
# Linea de tiempo
# ---------------------------------------------------------------------------

@dataclass
class Seg:
    kind: str                   # hook | card | pre | ranking | outro
    voz: str = ""
    pose: str = "senalando"
    skin: Skin | None = None
    start: float = 0.0
    dur: float = 0.0
    lead: float = 0.08
    narr: Narr | None = None
    events: dict = field(default_factory=dict)


def build_timeline():
    segs = [Seg("hook", HOOK_VOZ, "senalando", lead=0.0)]
    for s in SKINS:
        if s.puesto == "#1":
            segs.append(Seg("pre", pose="sorprendido"))
        segs.append(Seg("card", s.voz, s.pose, skin=s))
    segs.append(Seg("ranking", RANK_VOZ, "explicando", lead=0.25))
    segs.append(Seg("outro", OUTRO_VOZ, "senalando", lead=0.1))
    for s in segs:
        if s.voz:
            s.narr = narrate(s.voz)
        vl = len(s.narr.audio) / SR if s.narr else 0.0
        if s.kind == "hook":
            s.dur = max(4.0, vl + 0.3)
        elif s.kind == "card":
            s.dur = s.lead + vl + 0.5      # narracion + 0,5 s
        elif s.kind == "pre":
            s.dur = 1.0
        elif s.kind == "ranking":
            s.dur = max(4.6, s.lead + vl + 0.5)
        else:
            s.dur = max(3.0, s.lead + vl + 0.6)
    t = 0.0
    for s in segs:
        s.start = t
        t += s.dur
        if s.kind == "card":
            sk = s.skin
            ev = {}
            for k, (_, _, trig) in enumerate(sk.lineas):
                ev[f"line{k}"] = word_time(s, trig, 1.7 + 0.5 * k)
            if sk.sello:
                ev["sello"] = word_time(s, sk.sello, s.dur * 0.6)
            if sk.codigo:
                ev["codigo"] = word_time(s, "código", 2.4)
            s.events = ev
    return segs, t


def word_time(seg, trig, default):
    for wt, w in seg.narr.words:
        if w.lower().strip("¿¡.,:;…!?()").startswith(trig.lower()):
            return max(1.5, seg.lead + wt)
    return default


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

def thud():
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * (60 + 60 * np.exp(-t * 25)) * t) * np.exp(-t * 14)
    s += np.random.default_rng(2).standard_normal(n) * np.exp(-t * 40) * 0.3
    return 0.8 * s.astype(np.float32)


def build_audio(segs, total):
    n = int(SR * (total + 2))
    voz = np.zeros(n, np.float32)
    fx = np.zeros(n, np.float32)

    def put(buf, sig, t, gain=1.0):
        i = int(t * SR)
        if i >= len(buf):
            return
        sig = sig[:len(buf) - i]
        buf[i:i + len(sig)] += gain * sig

    for k, s in enumerate(segs):
        if s.narr:
            put(voz, s.narr.audio, s.start + s.lead)
        if k > 0:
            put(fx, rs.whoosh(), max(0, s.start - 0.18), 0.35)
        if s.kind == "card":
            put(fx, rs.ding(), s.start + rs.CARD_T["bar_end"], 0.5)
            if "sello" in s.events:
                put(fx, thud(), s.start + s.events["sello"], 0.7)
            if s.skin.puesto == "#1":
                sp = g.sfx("sparkle", SR).astype(np.float32)
                put(fx, sp, s.start + 0.1, 0.8)
        if s.kind == "pre":
            put(fx, rs.drumroll(s.dur), s.start, 0.6)

    music = rs.make_music(total)[:n]
    music = np.pad(music, (0, max(0, n - len(music))))
    env = np.abs(voz)
    win = int(SR * 0.2)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    # ducking: la musica baja a ~30 % cuando habla el alce
    duck = 1.0 - 0.7 * np.clip(env / (env.max() * 0.25 + 1e-6), 0, 1)
    mix = voz + fx + music * 0.5 * duck
    mix = mix[:int(SR * total)]
    fade = int(SR * 0.25)
    mix[-fade:] *= np.linspace(1, 0, fade)
    peak = float(np.abs(mix).max())
    mix /= max(1.0, peak / 0.95)
    path = os.path.join(g.BUILD, "skins_audio.wav")
    write_wav(path, mix)
    nf = int(total * FPS) + 1
    hop = SR / FPS
    lip = np.array([np.sqrt(np.mean(voz[int(f * hop):int(f * hop + hop)] ** 2)
                            + 1e-12) for f in range(nf)])
    lip /= lip.max()
    return path, lip, voz[:int(SR * total)]


def write_wav(path, x):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------------------
# Tarjetas
# ---------------------------------------------------------------------------

def price_row(sk, color, stacked=False):
    """Moneda + precio (+ tachado) + etiqueta COSMÉTICA / CON HABILIDAD."""
    parts = []
    if sk.precio:
        f = font(FONT_BLACK, 46)
        label = sk.precio
        coin = g.coin(58)
        tw = int(f.getlength(label))
        im = Image.new("RGBA", (tw + 90, 74), (0, 0, 0, 0))
        im.alpha_composite(coin, (0, 8))
        d = ImageDraw.Draw(im)
        d.text((72, 38), label, font=f, fill=(255, 214, 64), anchor="lm",
               stroke_width=6, stroke_fill=INK)
        if sk.tachado:
            d.line((66, 40, 80 + tw, 34), fill=(255, 60, 60), width=8)
        parts.append(im)
    if sk.tag:
        col = (120, 200, 255) if sk.tag.startswith("COSM") else (150, 230,
                                                                  110)
        parts.append(pill(sk.tag, col, size=30, pad=(20, 8)))
    if not parts:
        return None
    gap = 22
    if stacked:     # precio arriba, etiqueta abajo
        w = max(p.width for p in parts)
        h = sum(p.height for p in parts) + 6 * (len(parts) - 1)
        col = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y = 0
        for p in parts:
            col.alpha_composite(p, ((w - p.width) // 2, y))
            y += p.height + 6
        return col
    w = sum(p.width for p in parts) + gap * (len(parts) - 1)
    h = max(p.height for p in parts)
    row = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 0
    for p in parts:
        row.alpha_composite(p, (x, (h - p.height) // 2))
        x += p.width + gap
    return row


def tight(s):
    """'*palabra*.' -> '*palabra.*' para que no quede un espacio antes."""
    return re.sub(r"\*([.,:;!?…]+)", r"\1*", s)


def line_img(s, kind, size):
    s = tight(s)
    if kind == "verdict":
        return text(s, size + 8, TEXT_W, color=YELLOW, stroke=7)
    if kind == "note":
        return text(s, max(26, size - 10), TEXT_W, color=SOFT, stroke=4,
                    fp=FONT_BOLD)
    color = {"+": PLUS, "-": MINUS}.get(kind, WHITE)
    if kind == "+":
        s = "+ " + s if not s.startswith("*+") else s
    return text(s, size, TEXT_W, color=color, stroke=5)


def code_box(code):
    lab = text("CÓDIGO", 34, 600, stroke=0, fp=FONT_BOLD)
    main = text(code, 84, 760, color=YELLOW, stroke=8)
    bw, bh = main.width + 80, lab.height + main.height + 6
    box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), 30, fill=(70, 50, 10, 240),
                        outline=GOLD, width=8)
    box.alpha_composite(lab, ((bw - lab.width) // 2, 8))
    box.alpha_composite(main, ((bw - main.width) // 2, lab.height - 6))
    return box


def stamp_img():
    S = 300
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (60, 200, 110, 255)
    d.ellipse((8, 8, S - 9, S - 9), outline=col, width=12)
    d.ellipse((30, 30, S - 31, S - 31), outline=col, width=4)
    f1 = font(FONT_BLACK, 40)
    f2 = font(FONT_BLACK, 26)
    d.text((S / 2, S / 2 - 6), "RECOMENDADO", font=f2, fill=col,
           anchor="mm")
    d.text((S / 2, S / 2 - 50), "★", font=font(FONT_BOLD, 48), fill=col,
           anchor="mm")
    d.text((S / 2, S / 2 + 34), "POR EL", font=f2, fill=col, anchor="mm")
    d.text((S / 2, S / 2 + 70), "PROFESOR", font=f2, fill=col, anchor="mm")
    del f1
    return im.rotate(-14, resample=Image.BICUBIC, expand=True)


def ribbon_img(label):
    f = font(FONT_BLACK, 32)
    tw = int(f.getlength(label))
    im = Image.new("RGBA", (tw + 90, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (im.width, 0), (im.width - 22, 32), (im.width, 63),
               (0, 63), (22, 32)], fill=(200, 30, 40), outline=INK)
    d.text((im.width / 2, 33), label, font=f, fill=WHITE, anchor="mm",
           stroke_width=4, stroke_fill=INK)
    return im.rotate(4, resample=Image.BICUBIC, expand=True)


class Card:
    def __init__(self, sk: Skin):
        self.sk = sk
        self.color = nota_color(sk.nota)
        self.rank = pill(sk.puesto, self.color, size=56, pad=(32, 10))
        self.rareza = None
        if sk.rareza:
            fill = (170, 90, 230) if sk.rareza == "MÍTICO" else GOLD
            self.rareza = pill(sk.rareza, fill, fg=INK if fill == GOLD
                               else WHITE, size=30, pad=(20, 7))
        self.price = price_row(sk, self.color)
        self.code = code_box(sk.codigo) if sk.codigo else None
        self.stamp = stamp_img() if sk.sello else None
        self.ribbon = ribbon_img(sk.cinta) if sk.cinta else None
        self._fit()

    def _fit(self):
        """Cabecera horizontal (icono | nombre + precio) y debajo barra,
        codigo y lineas. Achica todo hasta que entre en la tarjeta."""
        sk = self.sk
        x0, y0, x1, y1 = CARD
        top, bottom = y0 + 44, y1 - 16
        n = len(sk.iconos)
        for icon, name_sz, line_sz in ((210, 70, 46), (190, 64, 44),
                                       (172, 60, 42), (156, 56, 40),
                                       (140, 52, 38)):
            self.icon_size = icon
            self.icons = [skin_badge(k, self.color, icon) for k in sk.iconos]
            self.icons_w = icon + (n - 1) * int(icon * 0.62)
            col_max = 820 - self.icons_w - 34
            self.price = price_row(sk, self.color)
            if self.price and self.price.width > col_max:
                self.price = price_row(sk, self.color, stacked=True)
            self.name = text(sk.nombre, name_sz if n == 1 else
                             int(name_sz * 0.68), col_max, stroke=8)
            col_h = self.name.height + (self.price.height + 6
                                        if self.price else 0)
            col_w = max(self.name.width, self.price.width if self.price
                        else 0)
            self.col_w = col_w
            head_h = max(icon, col_h)
            self.lines = [line_img(s, k, line_sz) for s, k, _ in sk.lineas]
            blocks = [("head", head_h)]
            if self.ribbon:
                blocks.append(("ribbon", self.ribbon.height - 6))
            blocks.append(("bar", 80))
            if self.code:
                blocks.append(("code", self.code.height))
            for k, l in enumerate(self.lines):
                blocks.append((f"line{k}", l.height - 8))
            used = sum(h for _, h in blocks)
            gap = (bottom - top - used) / (len(blocks) + 1)
            if gap >= 16 or icon == 140:
                break
        if gap < 12:
            print(f"AVISO: tarjeta {sk.nombre} muy llena (gap {gap:.0f})")
        group = self.icons_w + 34 + col_w
        gx = W / 2 - group / 2
        self.icon_cx = [gx + icon / 2 + k * int(icon * 0.62)
                        for k in range(n)]
        self.col_cx = gx + self.icons_w + 34 + col_w / 2
        self.col_h = col_h
        self.pos = {}
        y = top + gap
        for k, h in blocks:
            self.pos[k] = y + h / 2
            y += h + gap


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

class Renderer:
    def __init__(self, segs, total, lip):
        self.segs, self.total, self.lip = segs, total, lip
        self.bg = g.make_background()
        self.poses = g.load_poses(MOOSE_SCALE)
        self.icons = g.load_icons()
        self.brand = g.Renderer._brand(None)
        self.cards = {id(s.skin): Card(s.skin) for s in segs if s.skin}
        self.mouth = self._mouth_track()
        self.hook1 = drop_shadow(text("Ranking de *TODAS* las skins de Alce",
                                      92, TEXT_W, stroke=10))
        self.hook2 = drop_shadow(text("¿Cuál vale tus *AlceCoins?*", 64,
                                      TEXT_W, stroke=8))
        self.hook_icons = [skin_badge(k, (255, 255, 255), 120) for k in
                           ("default", "platino", "dorado", "diamante",
                            "esmeralda", "sombra", "aurora", "magma", "peru",
                            "flaco", "calabaza", "aguz")]
        self.pre1 = drop_shadow(text("Y la *MEJOR* skin es…", 100, TEXT_W,
                                     stroke=11))
        self.medal = rs.Renderer._medal(None)
        self.rank_title = drop_shadow(text("RANKING *FINAL*", 66, stroke=9))
        self.rows = self._rank_rows()
        self.outro = drop_shadow(text(
            "¿Cuál es tu skin *favorita?* *¡COMENTA!*", 84, TEXT_W,
            stroke=10))
        self.sub_cache = {}
        rnd = random.Random(4)
        self.confetti = [(rnd.uniform(SAFE_X0 - 60, SAFE_X1 + 60),
                          rnd.uniform(-1, 0), rnd.uniform(0.35, 0.7),
                          rnd.choice([GOLD, (255, 90, 90), (90, 200, 255),
                                      (140, 230, 110), (255, 255, 255),
                                      (200, 120, 255)]),
                          rnd.uniform(0, 6.28), rnd.uniform(-8, 8))
                         for _ in range(130)]

    def _mouth_track(self):
        on, res = False, []
        for f, v in enumerate(self.lip):
            if not on and v > 0.12:
                on = True
            elif on and v < 0.06:
                on = False
            res.append(on and (f // 3) % 3 != 2)
        return res

    def seg_at(self, t):
        for i, s in enumerate(self.segs):
            if t < s.start + s.dur:
                return i, s
        return len(self.segs) - 1, self.segs[-1]

    # ------------------------------------------------------------------
    def frame(self, f):
        t = f / FPS
        i, s = self.seg_at(t)
        lt = t - s.start
        img = self.bg.copy()
        getattr(self, "_draw_" + s.kind)(img, s, t, lt)
        bx = (W - self.brand.width) // 2
        img.alpha_composite(self.brand, (bx, 140))
        paste_center(img, self.icons["book"], bx + 58, 186, scale=0.62)
        self._draw_dots(img, s)
        self._draw_moose(img, f, s, t, lt)
        self._draw_sub(img, s, lt)
        if 0 < lt < 0.14 and i > 0:
            a = int(90 * (1 - lt / 0.14))
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, a)))
        out = img.convert("RGB")
        if s.kind == "card" and s.skin.puesto == "#1" and lt < 0.5:
            k = (1 - lt / 0.5) * 14
            arr = np.array(out)
            arr = np.roll(arr, int(math.sin(lt * 90) * k), axis=1)
            arr = np.roll(arr, int(math.cos(lt * 70) * k * 0.6), axis=0)
            out = Image.fromarray(arr)
        return out

    def _draw_moose(self, img, f, s, t, lt):
        closed, opened = self.poses[s.pose]
        talk = self.mouth[min(f, len(self.mouth) - 1)]
        sp = opened if talk else closed
        lvl = self.lip[min(f, len(self.lip) - 1)]
        bob = math.sin(t * 2 * math.pi * 0.9) * 5 - 6 * lvl
        if s.kind == "card" and s.skin.puesto == "#1" and lt < 1.0:
            bob -= abs(math.sin(lt * math.pi * 3)) * 28
        sx = 1.0 + 0.012 * math.sin(t * 2 * math.pi * 0.45) + 0.012 * lvl
        sp = sp.resize((int(sp.width * sx), int(sp.height * sx)),
                       Image.BILINEAR)
        x = (W - sp.width) // 2
        y = int(MOOSE_BOTTOM - sp.height + bob)
        img.alpha_composite(sp, (x, y))
        if s.skin and s.skin.gesto == "pensando":
            a = ease_out((lt - 0.6) / 0.3)
            if a > 0:
                rs.Renderer._thought(None, img, W / 2 + 140, y + 70, t, a)

    def _draw_dots(self, img, s):
        if s.kind != "card":
            return
        cards = [x for x in self.segs if x.kind == "card"]
        cur = cards.index(s)
        n = len(cards)
        d = ImageDraw.Draw(img)
        for k in range(n):
            cx = W / 2 + (k - (n - 1) / 2) * 34
            done = k <= cur
            col = nota_color(cards[k].skin.nota) if done else (95, 90, 130)
            r = 11 if k == cur else 8
            d.ellipse((cx - r, DOTS_Y - r, cx + r, DOTS_Y + r), fill=col,
                      outline=INK, width=3)

    def _draw_sub(self, img, s, lt):
        if not s.narr:
            return
        rel = lt - s.lead
        cur = None
        for a, b, txt in s.narr.subs:
            if a - 0.05 <= rel < b + 0.15:
                cur = (a, txt)
        if cur is None:
            return
        a0, txt = cur
        if txt not in self.sub_cache:
            body = text(tight(txt), 58, TEXT_W - 40, stroke=7)
            box = Image.new("RGBA", (body.width + 50, body.height + 14),
                            (0, 0, 0, 0))
            ImageDraw.Draw(box).rounded_rectangle(
                (0, 0, box.width - 1, box.height - 1), 26,
                fill=(10, 8, 24, 165))
            box.alpha_composite(body, (25, 4))
            self.sub_cache[txt] = box
        pop = 0.9 + 0.1 * ease_out_back((rel - a0) / 0.18)
        paste_center(img, self.sub_cache[txt], W / 2, SUB_Y, scale=pop)

    # ------------------------------------------------------------------
    def _draw_hook(self, img, s, t, lt):
        pulse = 1 + 0.03 * math.sin(t * 2 * math.pi * 1.6)
        paste_center(img, self.hook1, W / 2, 430, scale=pulse)
        a = ease_out_back((lt - 0.4) / 0.4)
        paste_center(img, self.hook2, W / 2, 430 + self.hook1.height / 2 + 30,
                     scale=max(a, 0.01))
        for k, ic in enumerate(self.hook_icons):
            row, col = divmod(k, 6)
            cx = W / 2 + (col - 2.5) * 132 + (66 if row else 0) * 0
            cy = 840 + row * 140 + math.sin(t * 3 + k) * 8
            pop = ease_out_back((lt - 0.2 - k * 0.06) / 0.35)
            if pop > 0:
                paste_center(img, ic, cx, cy, scale=max(pop, 0.01))

    def _card_base(self, img, color, lt, gold=False, t=0.0):
        x0, y0, x1, y1 = CARD
        ap = ease_out(lt / 0.25)
        card = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        oc = color
        if gold:
            k = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 1.5)
            oc = tuple(int(c + (255 - c) * 0.5 * k) for c in GOLD)
        d.rounded_rectangle((0, 0, card.width - 1, card.height - 1), 48,
                            fill=(14, 12, 32, 185), outline=oc + (255,),
                            width=12 if gold else 9)
        if gold:
            glow = Image.new("RGBA", (card.width + 120, card.height + 120),
                             (0, 0, 0, 0))
            ImageDraw.Draw(glow).rounded_rectangle(
                (40, 40, glow.width - 41, glow.height - 41), 60,
                outline=GOLD + (int(120 + 80 * math.sin(t * 6)),), width=26)
            glow = glow.filter(ImageFilter.GaussianBlur(22))
            paste_center(img, glow, W / 2, (y0 + y1) / 2, alpha=ap)
        paste_center(img, card, W / 2, (y0 + y1) / 2 + (1 - ap) * 40,
                     alpha=ap)

    def _draw_card(self, img, s, t, lt):
        sk = s.skin
        C = self.cards[id(sk)]
        top1 = sk.puesto == "#1"
        self._card_base(img, C.color, lt, gold=top1, t=t)
        x0, y0, x1, y1 = CARD
        a = ease_out_back(lt / 0.35)
        paste_center(img, C.rank, W / 2, y0, scale=max(a, 0.01))
        if C.rareza:
            a = ease_out_back((lt - 0.3) / 0.35)
            paste_center(img, C.rareza, W / 2 + C.rank.width / 2 + 22 +
                         C.rareza.width / 2, y0, scale=max(a, 0.01))
        # cabecera: icono(s) | nombre + precio
        hy = C.pos["head"]
        for k, ic in enumerate(C.icons):
            a = ease_out_back((lt - 0.05 - k * 0.15) / 0.4)
            if a <= 0:
                continue
            wob = math.sin(t * 2.2 + k) * 3
            paste_center(img, drop_shadow(ic, blur=10), C.icon_cx[k],
                         hy + wob, scale=max(a, 0.01))
        ny = hy - C.col_h / 2 + C.name.height / 2
        a = ease_out_back((lt - 0.1) / 0.35)
        paste_center(img, C.name, C.col_cx, ny, scale=max(a, 0.01))
        if C.price:
            a = ease_out((lt - 0.3) / 0.3)
            py = hy + C.col_h / 2 - C.price.height / 2
            paste_center(img, C.price, C.col_cx, py + (1 - a) * 20, alpha=a)
        if C.ribbon:
            a = ease_out_back((lt - 0.5) / 0.35)
            paste_center(img, C.ribbon, W / 2, C.pos["ribbon"],
                         scale=max(a, 0.01))
        self._bar(img, C, t, lt)
        if C.code:
            st = s.events.get("codigo", 2.4)
            a = ease_out_back((lt - st) / 0.4)
            if a > 0:
                sh = 1 + 0.03 * math.sin((lt - st) * 7)
                paste_center(img, C.code, W / 2, C.pos["code"],
                             scale=max(a, 0.01) * sh)
        for k, li in enumerate(C.lines):
            st = s.events.get(f"line{k}", 1.7 + 0.5 * k)
            a = ease_out((lt - st) / 0.3)
            if a > 0:
                paste_center(img, li, W / 2, C.pos[f"line{k}"] + (1 - a) * 22,
                             alpha=a)
        if C.stamp:
            st = s.events.get("sello", s.dur * 0.6)
            k = (lt - st) / 0.22
            if k > 0:
                sc = 1.0 + 1.2 * max(0, 1 - k)
                # al costado del profesor (zona libre junto al alce)
                paste_center(img, C.stamp, 265, 1400,
                             scale=sc * 0.9, alpha=min(1, k * 1.5))
        if top1:
            self._confetti(img, lt)

    def _bar(self, img, C, t, lt):
        sk = C.sk
        f = font(FONT_BLACK, 76)
        f2 = font(FONT_BLACK, 40)
        suffix = "" if sk.nota is None else "/10"
        num_w = f.getlength(sk.nota_txt) + 8 + f2.getlength(suffix) + 16
        bar_w = 480
        bx0 = W / 2 - (bar_w + 18 + num_w) / 2
        bx1 = bx0 + bar_w
        by = C.pos["bar"]
        bh = 44
        k = ease_out((lt - rs.CARD_T["bar0"]) /
                     (rs.CARD_T["bar_end"] - rs.CARD_T["bar0"]))
        val = (sk.nota or 0) * k
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((bx0, by - bh / 2, bx1, by + bh / 2), bh // 2,
                            fill=(40, 36, 70), outline=INK, width=5)
        col = C.color
        if sk.nota == 10:
            sh = 0.5 + 0.5 * math.sin(t * 8)
            col = tuple(int(v + (255 - v) * 0.4 * sh) for v in GOLD)
        fx = bx0 + (bx1 - bx0) * val / 10
        if fx - bx0 > bh:
            d.rounded_rectangle((bx0 + 5, by - bh / 2 + 5, fx - 5,
                                 by + bh / 2 - 5), (bh - 10) // 2, fill=col)
            d.rounded_rectangle((bx0 + 14, by - bh / 2 + 9, fx - 14,
                                 by - bh / 2 + 16), 4,
                                fill=(255, 255, 255, 90))
        for m in range(1, 10):
            mx = bx0 + (bx1 - bx0) * m / 10
            d.line((mx, by + bh / 2 - 12, mx, by + bh / 2 - 5),
                   fill=(255, 255, 255, 70), width=2)
        if sk.nota == 10 and k > 0.05:
            rnd = random.Random(int(t * FPS))
            for _ in range(16):
                sx = rnd.uniform(bx0 + 10, fx)
                life = rnd.random()
                sy = by - bh / 2 - life * 55
                r = 7 * (1 - life) + 2
                d.ellipse((sx - r, sy - r, sx + r, sy + r),
                          fill=(255, int(240 - 60 * life), 120,
                                int(240 * (1 - life))))
        if sk.nota is None:
            num = sk.nota_txt if lt > rs.CARD_T["bar_end"] else "?"
        else:
            dec = 1 if "," in sk.nota_txt else 0
            num = (f"{val:.{dec}f}".replace(".", ",") if k < 1
                   else sk.nota_txt)
        pop = 1.0
        if lt > rs.CARD_T["bar_end"]:
            pop = 1 + 0.25 * max(0, 1 - (lt - rs.CARD_T["bar_end"]) / 0.3)
        im = Image.new("RGBA", (300, 110), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        dd.text((8, 55), num, font=f, fill=col, anchor="lm", stroke_width=8,
                stroke_fill=INK)
        if suffix:
            dd.text((16 + f.getlength(num), 66), suffix, font=f2, fill=WHITE,
                    anchor="lm", stroke_width=5, stroke_fill=INK)
        paste_center(img, im, bx1 + 18 + 150, by, scale=pop)

    def _confetti(self, img, lt):
        d = ImageDraw.Draw(img)
        for x, ph, spd, col, rot, sw in self.confetti:
            y = CARD[1] - 80 + ((lt * spd + ph + 1) % 1.0) * 1000
            yy = y if lt * spd + ph + 1 < 2.2 else None
            if yy is None:
                continue
            xx = x + math.sin(lt * 3 + rot) * 30
            ang = rot + lt * sw
            w, h = 14, 8
            pts = [(xx + math.cos(ang) * dx - math.sin(ang) * dy,
                    yy + math.sin(ang) * dx + math.cos(ang) * dy)
                   for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
            d.polygon(pts, fill=col)

    def _draw_pre(self, img, s, t, lt):
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 110)))
        k = min(1, lt / s.dur)
        sc = 1 + 0.04 * math.sin(lt * 30) * k
        paste_center(img, self.pre1, W / 2, 480,
                     scale=ease_out_back(lt / 0.3) * sc)
        glow = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((60, 60, 360, 360),
                                     fill=GOLD + (int(90 + 90 * k),))
        glow = glow.filter(ImageFilter.GaussianBlur(40))
        shake = math.sin(lt * 55) * 10 * k
        pop = max(ease_out_back((lt - 0.1) / 0.3), 0.01)
        paste_center(img, glow, W / 2, 800, scale=pop * (1 + 0.15 * k))
        paste_center(img, self.medal, W / 2 + shake, 800, scale=pop,
                     angle=shake * 0.6)

    def _rank_rows(self):
        rows = []
        f_name = font(FONT_BLACK, 32)
        w = SAFE_X1 - SAFE_X0 - 40
        order = list(reversed(SKINS))
        for sk in order:
            col = nota_color(sk.nota)
            im = Image.new("RGBA", (w, 50), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            top = sk.puesto == "#1"
            if top:
                d.rounded_rectangle((0, 0, w - 1, 49), 22, fill=GOLD + (70,),
                                    outline=GOLD, width=4)
            tc = GOLD if top else WHITE
            d.text((14, 25), sk.puesto, font=f_name,
                   fill=GOLD if top else SOFT, anchor="lm", stroke_width=4,
                   stroke_fill=INK)
            x = 92
            for kk in sk.iconos:
                im.alpha_composite(skin_badge(kk, col, 46), (int(x), 2))
                x += 36
            x += 18
            b0, b1 = w - 240, w - 110
            fs = 32     # achica el nombre si no entra antes de la barra
            while font(FONT_BLACK, fs).getlength(sk.corto) > b0 - x - 16:
                fs -= 1
            d.text((x, 25), sk.corto, font=font(FONT_BLACK, fs), fill=tc,
                   anchor="lm", stroke_width=4, stroke_fill=INK)
            d.rounded_rectangle((b0, 14, b1, 36), 11, fill=(40, 36, 70),
                                outline=INK, width=3)
            if sk.nota:
                d.rounded_rectangle((b0 + 3, 17, b0 + 3 + (b1 - b0 - 6) *
                                     sk.nota / 10, 33), 8, fill=col)
            d.text((w - 14, 25), sk.nota_txt, font=f_name, fill=col,
                   anchor="rm", stroke_width=4, stroke_fill=INK)
            rows.append(im)
        return rows

    def _draw_ranking(self, img, s, t, lt):
        self._card_base(img, GOLD, lt)
        x0, y0, x1, y1 = CARD
        paste_center(img, self.rank_title, W / 2, y0 + 58,
                     scale=max(ease_out_back(lt / 0.35), 0.01))
        for k, r in enumerate(self.rows):
            a = ease_out((lt - 0.25 - k * 0.09) / 0.25)
            if a <= 0:
                continue
            cy = y0 + 122 + k * 54
            sc = 1 + (0.03 * math.sin(t * 2 * math.pi * 1.4) if k == 0
                      else 0)
            paste_center(img, r, W / 2 + (1 - a) * 60, cy, alpha=a, scale=sc)

    def _draw_outro(self, img, s, t, lt):
        pop = ease_out_back(lt / 0.4)
        paste_center(img, drop_shadow(self.icons["interrobang"]), W / 2, 440,
                     scale=1.9 * max(pop, 0.01) *
                     (1 + 0.05 * math.sin(t * 2 * math.pi * 1.4)))
        paste_center(img, self.outro, W / 2, 740, scale=max(pop, 0.01))


# ---------------------------------------------------------------------------

def main(argv):
    segs, total = build_timeline()
    print(f"Duración total: {total:.2f} s")
    for s in segs:
        name = s.skin.nombre if s.skin else ""
        print(f"  {s.kind:8s} {s.start:6.2f}s  {s.dur:5.2f}s  {name}")
    if not 80 <= total <= 95:
        print("AVISO: la duración está fuera de 80–95 s")
    audio, lip, voz = build_audio(segs, total)
    r = Renderer(segs, total, lip)
    if "--muestras" in argv:
        os.makedirs(MUESTRAS, exist_ok=True)

        def card(p):
            return next(s for s in segs if s.skin and s.skin.puesto == p and
                        (p != "#5"))
        dor = next(s for s in segs if s.skin and s.skin.codigo)
        cal = next(s for s in segs if s.skin and s.skin.cinta)
        agu = card("#1")
        rk = next(s for s in segs if s.kind == "ranking")
        picks = {"1_gancho": 2.2,
                 "2_dorado_codigo": dor.start + dor.events["codigo"] + 0.8,
                 "3_calabaza": cal.start + cal.dur - 1.0,
                 "4_aguz": agu.start + agu.dur - 1.5,
                 "5_ranking": rk.start + rk.dur - 0.8}
        for x in argv[2:]:
            picks[f"extra_{x}"] = float(x)
        for name, tt in picks.items():
            r.frame(int(tt * FPS)).save(os.path.join(MUESTRAS, name + ".png"))
            print("muestra", name, round(tt, 2))
        # 10 s de voz (sin musica) desde el inicio
        clip = voz[:int(SR * 10)]
        wav = os.path.join(g.BUILD, "voz_10s.wav")
        write_wav(wav, clip / max(1e-6, np.abs(clip).max()) * 0.9)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                        "-c:a", "aac", "-b:a", "160k",
                        os.path.join(MUESTRAS, "voz_muestra_10s.m4a")],
                       check=True)
        return
    nframes = int(round(total * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", audio,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
           "-shortest", "-movflags", "+faststart", OUTPUT]
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(nframes):
        proc.stdin.write(r.frame(f).tobytes())
        if f % 300 == 0:
            print(f"  frame {f}/{nframes}")
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg falló")
    print("Listo:", OUTPUT)


if __name__ == "__main__":
    main(sys.argv)
