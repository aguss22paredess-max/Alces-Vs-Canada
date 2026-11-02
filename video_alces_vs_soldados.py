#!/usr/bin/env python3
"""
AlceKnow - "¿Es más fácil ganar como Alce o como Soldado?"

Usa el mismo motor que generate_video.py, solo cambia el guion.
    python video_alces_vs_soldados.py   -> output/alceknow_alces_vs_soldados.mp4
"""
import os
import sys

import generate_video as g
from generate_video import Segment

ALCE = (232, 150, 60)       # naranja/marron
SOLDADO = (226, 62, 62)     # rojo Canada

g.OUTPUT = os.path.join(g.ROOT, "output", "alceknow_alces_vs_soldados.mp4")
g.HOOK_TITLE = "¿Es más fácil ganar como *ALCE* o como *SOLDADO?*"
g.HOOK_SUB = "*ALCES* VS *SOLDADOS*"
g.HOOK_DECOR = "versus"
g.HOOK_SIZE = 96
g.OUTRO_TEXT = "¿De qué equipo eres? *¡COMENTA!*"
g.OUTRO_ICON = "interrobang"

g.SCRIPT = [
    Segment(
        kind="intro", pose="senalando", sfx="none",
        lines=[("¿Es más fácil ganar como alce, o como soldado? "
                "Hoy en Alce Nou lo analizamos.", None)],
    ),
    Segment(
        kind="play", pose="senalando", icon="flag",
        label="ALCES", color=ALCE, sfx="ding",
        lines=[
            ("Los alces tienen cuatro habilidades.", "*4* habilidades"),
            ("Pero tienen que capturar tres banderas, en orden,",
             "Capturar *3 banderas* en orden"),
            ("cincuenta segundos cada una,", "*50 segundos* cada una"),
            ("y todo en solo seis minutos.", "Todo en solo *6 minutos*"),
        ],
    ),
    Segment(
        kind="play", pose="explicando", icon="timer",
        label="SOLDADOS", color=SOLDADO, sfx="ding",
        lines=[
            ("Los soldados tienen cuatro clases,", "*4* clases"),
            ("y sesenta segundos para prepararse.",
             "*60 segundos* para prepararse"),
            ("Y ganan si se acaba el tiempo.",
             "Ganan si *se acaba el tiempo*"),
        ],
    ),
    Segment(
        kind="versus", pose="sorprendido", sfx="sparkle",
        label="¿Quién tiene *más ventaja?*",
        versus=(
            ("ALCES", ALCE, "flag",
             ["4 habilidades", "3 banderas en orden", "Solo 6 minutos"]),
            ("SOLDADOS", SOLDADO, "timer",
             ["4 clases", "60 s para prepararse", "Ganan con el tiempo"]),
        ),
        lines=[("Los alces tienen habilidades, pero el reloj corre en su "
                "contra. Los soldados solo tienen que aguantar. "
                "Entonces... ¿quién tiene más ventaja?", None)],
    ),
    Segment(
        kind="outro", pose="normal_parado", sfx="ding",
        lines=[("¿Y tú, de qué equipo eres? ¡Comenta!", None)],
    ),
]

if __name__ == "__main__":
    g.run(sys.argv)
