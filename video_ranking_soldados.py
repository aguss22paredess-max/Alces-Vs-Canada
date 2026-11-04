#!/usr/bin/env python3
"""
AlceKnow - "Ranking de TODAS las clases de Soldado"

Reutiliza el motor/estilo de generate_video.py (fondo, alce, tipografia,
pildora AlceKnow) y agrega: barra de nota animada, iconos de equipo,
tabla de ranking final, musica de fondo, whoosh, ding y redoble.

    python video_ranking_soldados.py            -> output/alceknow_ranking_soldados.mp4
    python video_ranking_soldados.py --muestras -> 5 fotogramas en output/muestras_ranking/
"""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys
import wave
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import generate_video as g
from generate_video import (FONT_BLACK, FONT_BOLD, INK, WHITE, YELLOW, W, H,
                            FPS, drop_shadow, ease_out, ease_out_back, font,
                            paste_center, render_text_block)

OUTPUT = os.path.join(g.ROOT, "output", "alceknow_ranking_soldados.mp4")
MUESTRAS = os.path.join(g.ROOT, "output", "muestras_ranking")
SR = 44100

# Zona segura TikTok: 120 px a los lados, 250 px abajo
SAFE_X0, SAFE_X1, SAFE_BOTTOM = 120, W - 120, H - 250
CARD = (SAFE_X0, 300, SAFE_X1, 1105)
TEXT_W = SAFE_X1 - SAFE_X0 - 80
MOOSE_BOTTOM = SAFE_BOTTOM - 5
MOOSE_SCALE = 1.25

RED = (232, 64, 60)
ORANGE = (246, 146, 40)
AMBER = (250, 206, 52)
GREEN = (118, 200, 78)
GOLD = (255, 196, 36)
SOFT = (222, 222, 238)


def nota_color(n):
    if n >= 9:
        return GOLD
    if n >= 8:
        return GREEN
    if n >= 7:
        return AMBER
    if n >= 6:
        return ORANGE
    return RED


# ---------------------------------------------------------------------------
# Datos (solo lo indicado por el usuario; sin precios inventados)
# ---------------------------------------------------------------------------

@dataclass
class Clase:
    puesto: int
    nombre: str
    nota: float
    nota_txt: str
    equipo: list                 # (icono, nombre, nota_corta, chiste)
    lineas: list                 # texto con *resaltado* y prefijo +/-/i
    veredicto: str
    voz: str
    pose: str
    tag: str = ""
    gesto: str = ""              # "" | pensando | hombros


CLASES = [
    Clase(7, "ALBAÑIL", 4, "4", [
        ("trowel", "Cuchara de albañil", "Apuñala a los alces", ""),
        ("hammer", "Martillo", "Crea un señuelo", "(no confunde a nadie)"),
        ("trap", "Trampa de oso", "Invisible para alces; aturde al pisarla",
         ""),
        ("flashlight", "Linterna", "", ""),
    ], [], "“Prácticamente inútil si juegas solo”",
        "Número siete: Albañil. Cuatro de diez. Prácticamente inútil si "
        "juegas solo.", "normal_parado", gesto="pensando"),
    Clase(6, "MÉDICO", 5, "5", [
        ("saber", "Sable", "", ""),
        ("medkit", "Botiquín", "3 usos; lo cura a él y a los soldados a su "
         "alcance", ""),
        ("flashlight", "Linterna", "", ""),
    ], ["-Contra: *menos vida* que el resto"],
        "“Mejor cuando hay mucha gente”",
        "Número seis: Médico. Cinco de diez. Mejor cuando hay mucha gente.",
        "explicando", tag="GRATIS"),
    Clase(5, "PESADO", 6, "6", [
        ("revolver", "Revólver", "", ""),
        ("knife", "Navaja", "", ""),
    ], ["+Pro: más *resistencia* a golpes y empujes",
        "-Contra: *menos velocidad*"],
        "“Útil con un Fusilero flanqueándote de apoyo”",
        "Número cinco: Pesado. Seis de diez. Útil con un fusilero "
        "de apoyo.", "normal_parado", gesto="pensando"),
    Clase(4, "FUSILERO", 7, "7", [
        ("musket", "Mosquete", "", ""),
        ("knife", "Navaja", "", ""),
        ("flashlight", "Linterna", "", ""),
    ], ["iDato: solo *4 cupos* de Fusilero por partida"],
        "“Buena opción si no tienes dinero”",
        "Número cuatro: Fusilero. Siete de diez. Buena opción si no tienes "
        "dinero.", "explicando", tag="POR DEFECTO"),
    Clase(3, "DISCIPLINADO", 7, "7", [
        ("revolver", "Revólver", "", ""),
        ("knife", "Navaja", "", ""),
    ], ["+Pro: *más vida* y *más daño* que el resto"],
        "“La peor clase de paga…\naunque sí sirve”",
        "Número tres: Disciplinado. Siete de diez. La peor clase de paga... "
        "aunque sí sirve.", "sorprendido", tag="DE PAGA", gesto="hombros"),
    Clase(2, "LEÑADOR", 8.5, "8.5", [
        ("axe", "Hacha", "Mucho daño; algo de cooldown", ""),
        ("syrup", "Jarabe de alce", "3 usos: más velocidad y curación "
         "progresiva", ""),
        ("flashlight", "Linterna", "", ""),
    ], [], "“Muchos beneficios”",
        "Número dos: Leñador. Ocho punto cinco de diez. Muchos beneficios.",
        "senalando"),
    Clase(1, "PYRO", 9.6, "9.6", [
        ("flamethrower", "Lanzallamas", "", ""),
        ("axe", "Hacha", "", ""),
        ("flashlight", "Linterna", "", ""),
    ], ["i*40 de daño instantáneo*\n+ *5 por segundo* durante *9 segundos*"],
        "“La mejor clase hasta ahora”",
        "¡Pyro! Nueve punto seis de diez. La mejor clase hasta ahora.",
        "senalando"),
]


# ---------------------------------------------------------------------------
# Linea de tiempo
# ---------------------------------------------------------------------------

@dataclass
class Seg:
    kind: str           # hook | card | pre | ranking | outro
    dur: float
    voz: str
    pose: str
    clase: Clase | None = None
    start: float = 0.0
    voice_start: float = 0.0
    extra: dict = field(default_factory=dict)


def build_timeline():
    segs = [Seg("hook", 3.2, "¡Califiqué todas las clases de soldado!", "senalando")]
    for c in CLASES:
        if c.puesto == 1:
            segs.append(Seg("pre", 1.3, "Y la mejor clase es...",
                            "sorprendido"))
            segs.append(Seg("card", 6.7, c.voz, c.pose, clase=c))
        else:
            segs.append(Seg("card", 6.3, c.voz, c.pose, clase=c))
    segs.append(Seg("ranking", 5.0, "Así queda el ranking final.",
                    "explicando"))
    segs.append(Seg("outro", 3.0, "¿Estás de acuerdo con el número uno? "
                    "¡Comenta!", "senalando"))
    t = 0.0
    for s in segs:
        s.start = t
        t += s.dur
    return segs, t


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

def tts(text, path, length_scale):
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", g.ensure_voice(), "-f", path,
         "--length-scale", str(length_scale)],
        input=text.encode("utf-8"), check=True, capture_output=True)
    with wave.open(path) as wf:
        sr = wf.getframerate()
        d = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    x = d.astype(np.float32) / 32768.0
    # remuestreo a 44.1 kHz
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)),
                     x).astype(np.float32)


def env_adsr(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))
    return e


def note(f, dur, harm=(1, .5, .25), a=.01, r=.4):
    n = int(SR * dur)
    t = np.arange(n) / SR
    s = sum(w * np.sin(2 * np.pi * f * k * t) for k, w in
            zip(range(1, len(harm) + 1), harm))
    return s * env_adsr(n, a, r)


def make_music(total):
    """Loop alegre de 100 BPM: bombo, palmas, hi-hat, bajo y acordes."""
    rng = np.random.default_rng(7)
    bpm = 100
    beat = 60 / bpm
    out = np.zeros(int(SR * (total + 1)), np.float32)

    def add(sig, t, gain):
        i = int(t * SR)
        if i >= len(out):
            return
        sig = sig[:len(out) - i]
        out[i:i + len(sig)] += gain * sig

    kick_n = int(SR * 0.25)
    tk = np.arange(kick_n) / SR
    kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-tk * 30)) * tk) * \
        np.exp(-tk * 12)
    clap = rng.standard_normal(int(SR * 0.15)) * env_adsr(int(SR * 0.15),
                                                          .001, .05)
    hat_raw = rng.standard_normal(int(SR * 0.05))
    hat = np.diff(hat_raw, prepend=0) * env_adsr(len(hat_raw), .001, .012)
    # Am - F - C - G
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63),
              (130.81, 164.81, 196.0), (196.0, 246.94, 293.66)]
    roots = [110.0, 87.31, 65.41, 98.0]
    t, b = 0.0, 0
    while t < total + 0.5:
        bar = (b // 4) % 4
        if b % 4 == 0:
            for f in chords[bar]:
                add(note(f, beat * 4, (1, .3, .1), .08, 1.6), t, 0.05)
        if b % 2 == 0:
            add(kick, t, 0.55)
        else:
            add(clap, t, 0.12)
        add(note(roots[bar], beat * 0.9, (1, .4), .005, .25), t, 0.22)
        add(hat, t + beat / 2, 0.10)
        add(hat, t, 0.06)
        # arpegio suave
        add(note(chords[bar][b % 3] * 2, beat / 2, (1, .2), .005, .12),
            t + beat / 2, 0.035)
        t += beat
        b += 1
    return out


def whoosh():
    n = int(SR * 0.45)
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(n).astype(np.float32)
    t = np.linspace(0, 1, n)
    alpha = 0.02 + 0.25 * np.sin(np.pi * t) ** 2
    y = np.empty(n, np.float32)
    acc = 0.0
    for i in range(n):
        acc += alpha[i] * (noise[i] - acc)
        y[i] = acc
    y *= np.sin(np.pi * t) ** 1.5
    return 0.9 * y / (np.abs(y).max() + 1e-6)


def ding():
    return 0.5 * np.concatenate([note(1318.5, 0.08, (1, .4), .002, .05),
                                 note(1760, 0.6, (1, .5, .2), .002, .25)])


def drumroll(dur):
    rng = np.random.default_rng(5)
    out = np.zeros(int(SR * (dur + 1.3)) + 1, np.float32)
    t = 0.0
    while t < dur:
        k = t / dur
        n = int(SR * 0.06)
        hit = rng.standard_normal(n) * env_adsr(n, .001, .03)
        hit += note(190, 0.06, (1,), .001, .03) * 0.6
        i = int(t * SR)
        out[i:i + n] += (0.25 + 0.45 * k) * hit[:len(out) - i]
        t += 0.09 - 0.055 * k
    # platillo final
    n = int(SR * 1.2)
    crash = np.diff(rng.standard_normal(n), prepend=0) * env_adsr(n, .001, .45)
    i = int(dur * SR)
    out[i:i + n] += 0.35 * crash
    return out


LEAD = {"hook": 0.0, "pre": 0.05, "card": 0.25, "ranking": 0.2,
        "outro": 0.1}
TARGET_TOTAL = 57.5


def fit_timeline(segs):
    """Genera las voces y ajusta las duraciones para que nada se pise y el
    total quede en ~57,5 s (las tarjetas reparten el tiempo restante)."""
    voices = []
    for k, s in enumerate(segs):
        speed = 0.8 if s.kind in ("hook", "outro") else 0.85
        x = tts(s.voz, os.path.join(g.BUILD, f"rank_{k}.wav"), speed)
        voices.append(x)
        s.extra["voice_len"] = len(x) / SR
    fixed = 0.0
    for s in segs:
        need = LEAD[s.kind] + s.extra["voice_len"] + 0.2
        if s.kind == "hook":
            s.dur = max(3.0, need)
        elif s.kind == "pre":
            s.dur = max(1.2, need)
        elif s.kind == "ranking":
            s.dur = max(5.0, need)
        elif s.kind == "outro":
            s.dur = max(3.0, need + 0.2)
        if s.kind != "card":
            fixed += s.dur
    cards = [s for s in segs if s.kind == "card"]
    per = (TARGET_TOTAL - fixed - 0.4) / len(cards)
    for s in cards:
        s.dur = per + (0.4 if s.clase.puesto == 1 else 0.0)
        need = LEAD["card"] + s.extra["voice_len"] + 0.3
        if need > s.dur:
            print(f"AVISO: tarjeta {s.clase.nombre}: voz {need:.2f}s > "
                  f"{s.dur:.2f}s")
            s.dur = need
    t = 0.0
    for s in segs:
        s.start = t
        t += s.dur
    return voices, t


def build_audio(segs):
    os.makedirs(g.BUILD, exist_ok=True)
    voices, total = fit_timeline(segs)
    voz = np.zeros(int(SR * (total + 1)), np.float32)
    sfx = np.zeros_like(voz)

    def put(buf, sig, t, gain=1.0):
        i = int(t * SR)
        sig = sig[:len(buf) - i]
        buf[i:i + len(sig)] += gain * sig

    for k, (s, x) in enumerate(zip(segs, voices)):
        s.voice_start = s.start + LEAD[s.kind]
        print(f"  {s.kind:8s} {s.start:6.2f}s  dura {s.dur:.2f}s  "
              f"voz {len(x)/SR:.2f}s")
        put(voz, x, s.voice_start)
        if k > 0:
            put(sfx, whoosh(), max(0, s.start - 0.18), 0.35)
        if s.kind == "card":
            put(sfx, ding(), s.start + CARD_T["bar_end"], 0.55)
        if s.kind == "pre":
            put(sfx, drumroll(s.dur), s.start, 0.6)

    music = make_music(total)[:len(voz)]
    # el volumen de la musica baja cuando habla el alce (ducking)
    env = np.abs(voz)
    win = int(SR * 0.15)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    duck = 1.0 - 0.55 * np.clip(env / (env.max() * 0.3 + 1e-6), 0, 1)
    mix = voz * 1.0 + sfx + music * 0.55 * duck
    n_total = int(SR * total)
    mix = mix[:n_total]
    fade = int(SR * 0.2)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= max(1.0, float(np.abs(mix).max()) / 0.95)
    path = os.path.join(g.BUILD, "rank_audio.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())
    # envolvente de la voz por frame (lip-sync)
    nf = int(total * FPS) + 1
    hop = SR / FPS
    lip = np.array([np.sqrt(np.mean(voz[int(f * hop):int(f * hop + hop)] ** 2)
                            + 1e-12) for f in range(nf)])
    lip /= lip.max()
    return path, lip, total


# ---------------------------------------------------------------------------
# Iconos de equipo (dibujados a mano con PIL)
# ---------------------------------------------------------------------------

STEEL = (186, 192, 204)
DARK = (66, 68, 80)
WOOD = (150, 98, 52)
OL = dict(outline=INK, width=6)


def _rot(img, ang):
    return img.rotate(ang, resample=Image.BICUBIC, expand=False)


def draw_equipment(kind):
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "flashlight":
        d.polygon([(132, 76), (196, 44), (196, 156), (132, 124)],
                  fill=(255, 236, 120, 140))
        d.rounded_rectangle((22, 84, 112, 116), 10, fill=DARK, **OL)
        d.polygon([(108, 82), (136, 68), (136, 132), (108, 118)],
                  fill=STEEL, **OL)
        d.rectangle((50, 92, 66, 108), fill=(230, 70, 60))
        im = _rot(im, 25)
    elif kind == "trowel":
        d.polygon([(56, 120), (100, 18), (144, 120)], fill=STEEL, **OL)
        d.line((100, 120, 100, 146), fill=INK, width=10)
        d.rounded_rectangle((86, 142, 114, 194), 10, fill=WOOD, **OL)
        im = _rot(im, -30)
    elif kind == "hammer":
        d.rounded_rectangle((90, 70, 112, 192), 8, fill=WOOD, **OL)
        d.rounded_rectangle((40, 36, 162, 82), 8, fill=DARK, **OL)
        d.rectangle((40, 44, 60, 74), fill=STEEL)
        im = _rot(im, 25)
    elif kind == "trap":
        d.ellipse((22, 60, 178, 176), outline=INK, width=22)
        d.ellipse((22, 60, 178, 176), outline=STEEL, width=12)
        for i in range(9):
            a = math.pi + (i + 0.5) * math.pi / 9
            cx, cy = 100 + 70 * math.cos(a), 118 + 52 * math.sin(a)
            d.polygon([(cx - 9, cy), (cx + 9, cy),
                       (100 + 42 * math.cos(a), 118 + 28 * math.sin(a))],
                      fill=STEEL, outline=INK)
            a2 = (i + 0.5) * math.pi / 9
            cx, cy = 100 + 70 * math.cos(a2), 118 + 52 * math.sin(a2)
            d.polygon([(cx - 9, cy), (cx + 9, cy),
                       (100 + 42 * math.cos(a2), 118 + 28 * math.sin(a2))],
                      fill=STEEL, outline=INK)
        d.ellipse((84, 106, 116, 130), fill=(180, 60, 50), **OL)
    elif kind == "saber":
        pts_a, pts_b = [], []
        for i in range(21):
            t = i / 20
            x = 58 + 120 * t
            y = 150 - 130 * t + 26 * math.sin(math.pi * t)
            w = 11 * (1 - t) + 2
            pts_a.append((x - w * 0.6, y - w))
            pts_b.append((x + w * 0.6, y + w))
        d.polygon(pts_a + pts_b[::-1], fill=STEEL, outline=INK, width=5)
        d.arc((30, 128, 92, 190), 200, 30, fill=(225, 170, 40), width=12)
        d.line((54, 160, 30, 186), fill=INK, width=20)
        d.line((54, 160, 30, 186), fill=WOOD, width=12)
    elif kind == "medkit":
        d.rounded_rectangle((74, 36, 126, 66), 10, outline=INK, width=10)
        d.rounded_rectangle((26, 58, 174, 170), 18, fill=WHITE, **OL)
        d.rectangle((88, 78, 112, 150), fill=(228, 52, 52))
        d.rectangle((64, 102, 136, 126), fill=(228, 52, 52))
    elif kind == "revolver":
        d.rounded_rectangle((70, 62, 190, 86), 6, fill=DARK, **OL)
        d.polygon([(40, 58), (118, 58), (118, 106), (92, 112), (84, 120),
                   (40, 120)], fill=DARK, **OL)
        d.ellipse((84, 66, 124, 106), fill=STEEL, **OL)
        d.polygon([(40, 104), (82, 104), (74, 182), (26, 182)], fill=WOOD,
                  **OL)
        d.arc((76, 98, 116, 140), 0, 180, fill=INK, width=7)
        d.rectangle((176, 50, 184, 62), fill=INK)
    elif kind == "knife":
        d.polygon([(92, 86), (170, 86), (196, 98), (170, 116), (92, 116)],
                  fill=STEEL, **OL)
        d.rounded_rectangle((16, 82, 96, 120), 14, fill=WOOD, **OL)
        d.ellipse((34, 95, 46, 107), fill=STEEL)
        d.ellipse((64, 95, 76, 107), fill=STEEL)
        im = _rot(im, 30)
    elif kind == "musket":
        d.rounded_rectangle((40, 94, 196, 106), 4, fill=DARK, **OL)
        d.polygon([(4, 116), (70, 100), (150, 100), (150, 116), (78, 120),
                   (14, 150)], fill=WOOD, **OL)
        d.line((150, 112, 150, 124), fill=INK, width=6)
        im = _rot(im, 25)
    elif kind == "axe":
        d.rounded_rectangle((90, 40, 110, 196), 8, fill=WOOD, **OL)
        d.polygon([(100, 30), (150, 18), (172, 64), (150, 106), (100, 92)],
                  fill=STEEL, **OL)
        d.line((152, 22, 170, 64), fill=WHITE, width=5)
        im = _rot(im, 20)
    elif kind == "syrup":
        d.ellipse((120, 86, 176, 150), outline=INK, width=16)
        d.ellipse((120, 86, 176, 150), outline=(210, 120, 30), width=8)
        d.rounded_rectangle((44, 76, 150, 192), 24, fill=(214, 120, 34), **OL)
        d.rectangle((80, 40, 114, 80), fill=(214, 120, 34), **OL)
        d.rounded_rectangle((74, 22, 120, 46), 6, fill=(220, 50, 50), **OL)
        d.rounded_rectangle((58, 112, 136, 160), 8, fill=(250, 240, 220),
                            outline=INK, width=4)
        d.polygon([(97, 120), (110, 136), (97, 152), (84, 136)],
                  fill=(220, 50, 50))
    elif kind == "flamethrower":
        d.rounded_rectangle((14, 64, 64, 176), 18, fill=(214, 60, 52), **OL)
        d.arc((40, 96, 110, 196), 180, 360, fill=INK, width=8)
        d.rounded_rectangle((66, 98, 156, 124), 6, fill=DARK, **OL)
        d.rectangle((150, 94, 168, 128), fill=STEEL, **OL)
        d.polygon([(168, 94), (198, 111), (168, 128)],
                  fill=(255, 150, 30))
        d.polygon([(168, 102), (190, 111), (168, 120)],
                  fill=(255, 230, 90))
        d.polygon([(90, 124), (106, 124), (100, 150), (86, 150)], fill=DARK,
                  outline=INK, width=4)
    return im


def badge(kind, ring, size=106):
    s = size * 2
    b = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.ellipse((4, 4, s - 5, s - 5), fill=(246, 246, 252), outline=ring,
              width=12)
    ic = draw_equipment(kind).resize((int(s * 0.72), int(s * 0.72)),
                                     Image.LANCZOS)
    b.alpha_composite(ic, ((s - ic.width) // 2, (s - ic.height) // 2))
    return b.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Elementos de las tarjetas
# ---------------------------------------------------------------------------

CARD_T = {"name": 0.0, "bar0": 0.35, "bar_end": 1.35, "equip": 1.5,
          "lines": 2.6, "verdict": 3.2}


def balanced_width(s, size, max_w, fp):
    """Ancho minimo que mantiene la misma cantidad de lineas: reparte las
    palabras parejo y evita lineas con una sola palabra colgando."""
    f = font(fp, size)
    words = g.parse_runs(s)
    n = len(g.wrap_words(words, f, max_w))
    if n <= 1:
        return max_w
    lo, hi = max_w * 0.3, max_w
    for _ in range(18):
        mid = (lo + hi) / 2
        if len(g.wrap_words(words, f, mid)) > n:
            lo = mid
        else:
            hi = mid
    return hi + 2


def text(s, size, max_w=TEXT_W, color=WHITE, stroke=None, fp=FONT_BLACK,
         gap=1.12):
    if "\n" in s:   # salto de linea manual: cada parte centrada
        parts = [text(p, size, max_w, color, stroke, fp, gap)
                 for p in s.split("\n")]
        w = max(p.width for p in parts)
        trim = int(size * 0.2)
        im = Image.new("RGBA", (w, sum(p.height - trim for p in parts) + trim),
                       (0, 0, 0, 0))
        y = 0
        for p in parts:
            im.alpha_composite(p, ((w - p.width) // 2, y))
            y += p.height - trim
        return im
    max_w = balanced_width(s, size, max_w, fp)
    return render_text_block(s, size, max_w, color=color,
                             stroke=stroke if stroke is not None
                             else max(3, size // 11),
                             line_gap=gap, fpaths=fp)


def pill(label, fill, fg=INK, size=40, pad=(28, 12)):
    f = font(FONT_BLACK, size)
    tw = int(f.getlength(label))
    im = Image.new("RGBA", (tw + pad[0] * 2, size + pad[1] * 2 + 6),
                   (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), im.height // 2,
                        fill=fill, outline=INK, width=5)
    d.text((im.width / 2, im.height / 2 + 1), label, font=f, fill=fg,
           anchor="mm")
    return im


def equip_item(kind, name, nota, chiste, ring, col_w):
    parts = [badge(kind, ring)]
    parts.append(text(name, 32, col_w, stroke=4, fp=FONT_BLACK, gap=1.05))
    if nota:
        parts.append(text(nota, 27, col_w, color=SOFT, stroke=3,
                          fp=FONT_BOLD, gap=1.05))
    if chiste:
        parts.append(text("*" + chiste + "*", 27, col_w, stroke=3,
                          fp=FONT_BOLD, gap=1.05))
    w = max(p.width for p in parts)
    h = sum(p.height for p in parts) + 4
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for i, p in enumerate(parts):
        im.alpha_composite(p, ((w - p.width) // 2, y))
        y += p.height - (2 if i else -6)
    return im


def line_img(s):
    kind, body = s[0], s[1:]
    color = {"+": (150, 230, 110), "-": (255, 120, 110)}.get(kind, WHITE)
    return text(body, 36, TEXT_W, color=color, stroke=5, fp=FONT_BLACK)


class CardLayout:
    def __init__(self, c: Clase):
        self.c = c
        self.color = nota_color(c.nota)
        self.rank = pill(f"#{c.puesto}", self.color, size=58, pad=(34, 10))
        self.name = drop_shadow(text(c.nombre, 86, stroke=10))
        self.tag = pill(c.tag, WHITE, size=30, pad=(20, 6)) if c.tag else None
        n = len(c.equipo)
        self.col_w = (TEXT_W + 20) // n - 12
        self.items = [equip_item(*e, ring=self.color, col_w=self.col_w)
                      for e in c.equipo]
        self.lines = [line_img(s) for s in c.lineas]
        self.verdict = text(c.veredicto, 50, TEXT_W, color=YELLOW, stroke=7)
        # apilado vertical
        x0, y0, x1, y1 = CARD
        # alto visual (drop_shadow agrega 42 px de margen arriba y abajo)
        blocks = [("name", self.name.height - 84)]
        blocks.append(("bar", 84))
        blocks.append(("equip", max(i.height for i in self.items)))
        for k, l in enumerate(self.lines):
            blocks.append((f"line{k}", l.height - 6))
        blocks.append(("verdict", self.verdict.height))
        used = sum(h for _, h in blocks)
        top, bottom = y0 + 46, y1 - 18
        gap = max(10, (bottom - top - used) / (len(blocks) + 1))
        self.pos = {}
        y = top + gap
        for k, h in blocks:
            self.pos[k] = y + h / 2
            y += h + gap
        if y - gap > bottom + 4:
            print(f"AVISO: tarjeta {c.nombre} no entra ({y - gap:.0f} > "
                  f"{bottom})")


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
        self.cards = {id(c): CardLayout(c) for c in CLASES}
        self.mouth = self._mouth_track()
        self.hook1 = drop_shadow(text(
            "El Profesor Alce calificó *TODAS* las clases de Soldado", 84,
            TEXT_W, stroke=10))
        self.hook2 = drop_shadow(text("de la *PEOR* a la *MEJOR*", 64,
                                      TEXT_W, stroke=8))
        self.pre1 = drop_shadow(text("Y la *MEJOR* clase es…", 100, TEXT_W,
                                     stroke=11))
        self.medal = self._medal()
        self.rank_title = drop_shadow(text("RANKING *FINAL*", 70, stroke=9))
        self.outro = drop_shadow(text(
            "¿Estás de acuerdo con el *#1?* *¡COMENTA!*", 84, TEXT_W,
            stroke=10))
        self.rows = self._rank_rows()
        self.sparks = self._make_sparks()

    # -- utilidades ---------------------------------------------------------
    def _medal(self):
        m = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
        d = ImageDraw.Draw(m)
        d.ellipse((10, 10, 250, 250), fill=GOLD, outline=INK, width=10)
        d.ellipse((38, 38, 222, 222), outline=(255, 236, 150), width=6)
        d.text((130, 134), "?", font=font(FONT_BLACK, 150), fill=WHITE,
               anchor="mm", stroke_width=10, stroke_fill=INK)
        return drop_shadow(m)

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

    def _make_sparks(self):
        rnd = random.Random(11)
        x0, y0, x1, y1 = CARD
        per = 2 * (x1 - x0) + 2 * (y1 - y0)
        out = []
        for _ in range(260):
            p = rnd.uniform(0, per)
            out.append((p, rnd.uniform(0, 1), rnd.uniform(0.7, 1.4),
                        rnd.uniform(14, 34)))
        return out

    def _perimeter(self, p):
        x0, y0, x1, y1 = CARD
        w, h = x1 - x0, y1 - y0
        if p < w:
            return x0 + p, y1
        p -= w
        if p < h:
            return x1, y1 - p
        p -= h
        if p < w:
            return x1 - p, y0
        return x0, y0 + (p - w)

    # -- frame --------------------------------------------------------------
    def frame(self, f):
        t = f / FPS
        i, s = self.seg_at(t)
        lt = t - s.start
        img = self.bg.copy()
        getattr(self, "_draw_" + s.kind)(img, s, t, lt)
        bx = (W - self.brand.width) // 2
        img.alpha_composite(self.brand, (bx, 140))
        paste_center(img, self.icons["book"], bx + 58, 186, scale=0.62)
        self._draw_moose(img, f, s, t, lt)
        self._draw_dots(img, s)

        if 0 < lt < 0.14 and i > 0:
            a = int(90 * (1 - lt / 0.14))
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, a)))
        out = img.convert("RGB")
        # sacudida de pantalla al revelar Pyro
        if s.kind == "card" and s.clase.puesto == 1 and lt < 0.5:
            k = (1 - lt / 0.5) * 16
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
        bob = math.sin(t * 2 * math.pi * 0.9) * 5
        gesto = s.clase.gesto if s.clase else ""
        if gesto == "hombros" and 3.0 < lt < 4.6:
            bob -= abs(math.sin((lt - 3.0) * math.pi * 2.5)) * 26
        if s.kind == "card" and s.clase.puesto == 1 and lt < 1.0:
            bob -= abs(math.sin(lt * math.pi * 3)) * 30
        sx = 1.0 + 0.012 * math.sin(t * 2 * math.pi * 0.45) + 0.01 * lvl
        sp = sp.resize((int(sp.width * sx), int(sp.height * sx)),
                       Image.BILINEAR)
        x = (W - sp.width) // 2
        y = int(MOOSE_BOTTOM - sp.height + bob)
        img.alpha_composite(sp, (x, y))
        head_y = y + 175 * MOOSE_SCALE / 1.45
        if gesto == "pensando":
            a = ease_out((lt - 0.6) / 0.3)
            if a > 0:
                self._thought(img, W / 2 + 150, head_y - 30, t, a)
        if gesto == "hombros" and lt > 2.9:
            a = ease_out((lt - 2.9) / 0.3)
            d = ImageDraw.Draw(img)
            col = (255, 255, 255, int(230 * a))
            for side in (-1, 1):
                cx = W / 2 + side * 125
                cy = y + 330 * MOOSE_SCALE / 1.45 + bob * 0.2
                for k in range(3):
                    off = k * 16
                    d.arc((cx - 30 - off, cy - 60 - off, cx + 30 + off,
                           cy + off), 200 if side < 0 else 270,
                          270 if side < 0 else 340, fill=col, width=6)

    def _thought(self, img, cx, cy, t, a):
        d = ImageDraw.Draw(img)
        fill = (255, 255, 255, int(235 * a))
        for r, ox, oy in ((10, -70, 60), (16, -40, 30)):
            d.ellipse((cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r),
                      fill=fill, outline=INK, width=3)
        d.ellipse((cx - 30, cy - 70, cx + 110, cy + 10), fill=fill,
                  outline=INK, width=4)
        for k in range(3):
            on = (int(t * 3) % 4) > k
            r = 9
            px = cx + 12 + k * 28
            d.ellipse((px - r, cy - 30 - r, px + r, cy - 30 + r),
                      fill=INK if on else (170, 170, 185))

    def _draw_dots(self, img, s):
        if s.kind != "card":
            return
        n = len(CLASES)
        cur = 8 - s.clase.puesto
        d = ImageDraw.Draw(img)
        y = CARD[3] + 34
        for k in range(n):
            cx = W / 2 + (k - (n - 1) / 2) * 40
            done = k < cur
            col = nota_color(CLASES[k].nota) if done else (95, 90, 130)
            r = 12 if k == cur - 1 else 9
            d.ellipse((cx - r, y - r, cx + r, y + r), fill=col,
                      outline=INK, width=3)

    # -- segmentos ----------------------------------------------------------
    def _draw_hook(self, img, s, t, lt):
        pulse = 1.0 + 0.03 * math.sin(t * 2 * math.pi * 1.6)
        paste_center(img, self.hook1, W / 2, 480, scale=pulse)
        a = ease_out_back((lt - 0.5) / 0.4)
        paste_center(img, self.hook2, W / 2, 480 + self.hook1.height / 2 + 70,
                     scale=max(a, 0.01))
        # mini preview de colores (rojo -> dorado)
        cols = [nota_color(c.nota) for c in CLASES]
        for k, col in enumerate(cols):
            cx = 180 + k * 120
            cy = 930 + math.sin(t * 3 + k) * 10
            h = 30 + k * 14
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((cx - 34, cy - h, cx + 34, cy + h), 14,
                                fill=col, outline=INK, width=5)

    def _card_base(self, img, color, lt, gold=False, t=0.0):
        x0, y0, x1, y1 = CARD
        ap = ease_out(lt / 0.25)
        card = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        oc = color
        if gold:
            k = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 1.5)
            oc = tuple(int(c + (255 - c) * 0.45 * k) for c in GOLD)
        d.rounded_rectangle((0, 0, card.width - 1, card.height - 1), 48,
                            fill=(14, 12, 32, 185), outline=oc + (255,),
                            width=12 if gold else 9)
        paste_center(img, card, W / 2, (y0 + y1) / 2 + (1 - ap) * 40,
                     alpha=ap)

    def _flames(self, img, t, strength):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for p, ph, spd, size in self.sparks:
            x, y = self._perimeter(p)
            k = (t * spd + ph) % 1.0
            yy = y - k * (40 if y <= CARD[1] else 150)
            xx = x + math.sin(t * 6 + ph * 10) * 10
            r = size * (1 - k) ** 0.8 * strength
            if r < 1.5:
                continue
            # lengua de fuego: gota alargada (amarillo -> naranja -> rojo)
            col = (255, int(max(40, 235 - 260 * k)), int(70 * (1 - k) ** 3),
                   int(235 * (1 - k ** 1.5)))
            d.polygon([(xx - r, yy), (xx, yy - r * 2.4), (xx + r, yy)],
                      fill=col)
            d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=col)
            if k < 0.35:
                rc = r * 0.45
                d.ellipse((xx - rc, yy - rc * 0.5, xx + rc, yy + rc * 1.2),
                          fill=(255, 250, 200, 200))
        glow = layer.filter(ImageFilter.GaussianBlur(14))
        img.alpha_composite(glow)
        img.alpha_composite(glow)
        img.alpha_composite(layer)

    def _draw_card(self, img, s, t, lt):
        c = s.clase
        L = self.cards[id(c)]
        pyro = c.puesto == 1
        if pyro:
            self._flames(img, t, min(1.0, lt / 0.4))
        self._card_base(img, L.color, lt, gold=pyro, t=t)
        x0, y0, x1, y1 = CARD
        # puesto arriba de la tarjeta
        a = ease_out_back(lt / 0.35)
        paste_center(img, L.rank, W / 2, y0, scale=max(a, 0.01))
        a = ease_out_back((lt - 0.1) / 0.35)
        paste_center(img, L.name, W / 2, L.pos["name"], scale=max(a, 0.01))
        if L.tag:
            # etiqueta (GRATIS / POR DEFECTO / DE PAGA) junto al puesto
            a = ease_out_back((lt - 0.3) / 0.35)
            paste_center(img, L.tag, W / 2 + L.rank.width / 2 + 24 +
                         L.tag.width / 2, y0, scale=max(a, 0.01))
        self._bar(img, L, t, lt)
        # equipo
        n = len(L.items)
        for k, it in enumerate(L.items):
            st = CARD_T["equip"] + k * 0.18
            a = ease_out_back((lt - st) / 0.35)
            if a <= 0:
                continue
            cx = W / 2 + (k - (n - 1) / 2) * (L.col_w + 12)
            ey = L.pos["equip"]
            # alineados por arriba (el icono siempre a la misma altura)
            paste_center(img, it, cx, ey + (L.items[k].height -
                         max(i.height for i in L.items)) / 2,
                         scale=max(a, 0.01))
        for k, li in enumerate(L.lines):
            a = ease_out((lt - CARD_T["lines"] - k * 0.25) / 0.3)
            if a > 0:
                paste_center(img, li, W / 2, L.pos[f"line{k}"] + (1 - a) * 25,
                             alpha=a)
        a = ease_out_back((lt - CARD_T["verdict"]) / 0.4)
        if a > 0:
            # entra como "sello" y despues late suave para que no quede quieto
            beat = 0.025 * math.sin((lt - CARD_T["verdict"]) * 2 * math.pi
                                    * 1.2) * min(1, lt - CARD_T["verdict"])
            paste_center(img, L.verdict, W / 2, L.pos["verdict"],
                         scale=max(a, 0.01) * (1 + max(beat, -0.01)))

    def _bar(self, img, L, t, lt):
        c = L.c
        f = font(FONT_BLACK, 76)
        f2 = font(FONT_BLACK, 40)
        num_w = f.getlength(c.nota_txt) + 8 + f2.getlength("/10") + 16
        bar_w = 500
        group = bar_w + 18 + num_w
        bx0 = W / 2 - group / 2      # barra + numero centrados
        bx1 = bx0 + bar_w
        by = L.pos["bar"]
        bh = 46
        k = ease_out((lt - CARD_T["bar0"]) /
                     (CARD_T["bar_end"] - CARD_T["bar0"]))
        val = c.nota * k
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((bx0, by - bh / 2, bx1, by + bh / 2), bh // 2,
                            fill=(40, 36, 70), outline=INK, width=5)
        fx = bx0 + (bx1 - bx0) * val / 10
        col = L.color
        if c.puesto == 1:
            sh = 0.5 + 0.5 * math.sin(t * 8)
            col = tuple(int(v + (255 - v) * 0.35 * sh) for v in GOLD)
        if fx - bx0 > bh:
            d.rounded_rectangle((bx0 + 5, by - bh / 2 + 5, fx - 5,
                                 by + bh / 2 - 5), (bh - 10) // 2, fill=col)
            d.rounded_rectangle((bx0 + 14, by - bh / 2 + 9, fx - 14,
                                 by - bh / 2 + 17), 4,
                                fill=(255, 255, 255, 90))
        for m in range(1, 10):
            mx = bx0 + (bx1 - bx0) * m / 10
            d.line((mx, by + bh / 2 - 12, mx, by + bh / 2 - 5),
                   fill=(255, 255, 255, 70), width=2)
        if c.puesto == 1 and k > 0.05:
            rnd = random.Random(int(t * FPS))
            for _ in range(14):
                sx = rnd.uniform(bx0 + 10, fx)
                life = rnd.random()
                sy = by - bh / 2 - life * 55
                r = 7 * (1 - life) + 2
                d.ellipse((sx - r, sy - r, sx + r, sy + r),
                          fill=(255, int(220 - 150 * life), 40,
                                int(240 * (1 - life))))
        # numero
        dec = 1 if "." in c.nota_txt else 0
        num = f"{val:.{dec}f}" if k < 1 else c.nota_txt
        pop = 1.0
        if lt > CARD_T["bar_end"]:
            pop = 1 + 0.25 * max(0, 1 - (lt - CARD_T["bar_end"]) / 0.3)
        im = Image.new("RGBA", (260, 110), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        dd.text((8, 55), num, font=f, fill=col, anchor="lm", stroke_width=8,
                stroke_fill=INK)
        nw = f.getlength(num)
        dd.text((16 + nw, 66), "/10", font=f2, fill=WHITE, anchor="lm",
                stroke_width=5, stroke_fill=INK)
        paste_center(img, im, bx1 + 18 + 130, by, scale=pop)

    def _draw_pre(self, img, s, t, lt):
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 110))
        img.alpha_composite(dark)
        k = min(1, lt / s.dur)
        sc = 1 + 0.04 * math.sin(lt * 30) * k
        paste_center(img, self.pre1, W / 2, 500,
                     scale=ease_out_back(lt / 0.3) * sc)
        # medalla #1 misteriosa que tiembla mas fuerte con el redoble
        glow = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((60, 60, 360, 360),
                                     fill=GOLD + (int(90 + 90 * k),))
        glow = glow.filter(ImageFilter.GaussianBlur(40))
        shake = math.sin(lt * 55) * 10 * k
        pop = max(ease_out_back((lt - 0.15) / 0.35), 0.01)
        paste_center(img, glow, W / 2, 860, scale=pop * (1 + 0.15 * k))
        paste_center(img, self.medal, W / 2 + shake, 860, scale=pop,
                     angle=shake * 0.6)

    def _rank_rows(self):
        rows = []
        f_name = font(FONT_BLACK, 42)
        for c in sorted(CLASES, key=lambda c: c.puesto):
            col = nota_color(c.nota)
            w = SAFE_X1 - SAFE_X0 - 40
            im = Image.new("RGBA", (w, 80), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            if c.puesto == 1:
                d.rounded_rectangle((0, 0, w - 1, 79), 26,
                                    fill=GOLD + (70,), outline=GOLD, width=5)
            d.text((22, 40), f"#{c.puesto}", font=f_name,
                   fill=GOLD if c.puesto == 1 else SOFT, anchor="lm",
                   stroke_width=5, stroke_fill=INK)
            d.text((110, 40), c.nombre, font=f_name,
                   fill=GOLD if c.puesto == 1 else WHITE, anchor="lm",
                   stroke_width=5, stroke_fill=INK)
            b0, b1 = 450, 640
            d.rounded_rectangle((b0, 26, b1, 54), 14, fill=(40, 36, 70),
                                outline=INK, width=4)
            d.rounded_rectangle((b0 + 4, 30, b0 + 4 + (b1 - b0 - 8) *
                                 c.nota / 10, 50), 10, fill=col)
            d.text((w - 22, 40), c.nota_txt, font=f_name, fill=col,
                   anchor="rm", stroke_width=5, stroke_fill=INK)
            rows.append(im)
        return rows

    def _draw_ranking(self, img, s, t, lt):
        self._card_base(img, GOLD, lt)
        x0, y0, x1, y1 = CARD
        paste_center(img, self.rank_title, W / 2, y0 + 70,
                     scale=max(ease_out_back(lt / 0.35), 0.01))
        for k, r in enumerate(self.rows):
            a = ease_out((lt - 0.3 - k * 0.15) / 0.3)
            if a <= 0:
                continue
            cy = y0 + 170 + k * 88
            sc = 1.0
            if k == 0:
                sc = 1 + 0.03 * math.sin(t * 2 * math.pi * 1.4)
            paste_center(img, r, W / 2 + (1 - a) * 60, cy, alpha=a, scale=sc)

    def _draw_outro(self, img, s, t, lt):
        pop = ease_out_back(lt / 0.4)
        paste_center(img, drop_shadow(self.icons["interrobang"]), W / 2, 450,
                     scale=1.9 * max(pop, 0.01) *
                     (1 + 0.05 * math.sin(t * 2 * math.pi * 1.4)))
        paste_center(img, self.outro, W / 2, 760, scale=max(pop, 0.01))


# ---------------------------------------------------------------------------

def main(argv):
    segs, _ = build_timeline()
    audio, lip, total = build_audio(segs)
    print(f"Duración total: {total:.2f} s")
    assert 55 <= total <= 58.5, total
    r = Renderer(segs, total, lip)
    if "--muestras" in argv:
        os.makedirs(MUESTRAS, exist_ok=True)
        card5 = next(s for s in segs if s.clase and s.clase.puesto == 5)
        pyro = next(s for s in segs if s.clase and s.clase.puesto == 1)
        rank = next(s for s in segs if s.kind == "ranking")
        outro = next(s for s in segs if s.kind == "outro")
        picks = {
            "1_gancho": 1.6,
            "2_tarjeta_pesado": card5.start + 4.5,
            "3_pyro": pyro.start + 4.5,
            "4_ranking": rank.start + 3.0,
            "5_cierre": outro.start + 1.5,
        }
        for k in sys.argv[2:]:
            picks[f"extra_{k}"] = float(k)
        for name, tt in picks.items():
            r.frame(int(tt * FPS)).save(os.path.join(MUESTRAS, name + ".png"))
            print("muestra", name, round(tt, 2))
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
