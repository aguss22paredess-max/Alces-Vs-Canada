# Alces vs Canadá – Video AlceKnow

Video vertical para TikTok del **Alce Profesor** explicando cómo ganar monedas fácil en *Alces vs Canadá*.

- Resultado: [`output/alceknow_monedas.mp4`](output/alceknow_monedas.mp4)
- 1080×1920 (9:16), 30 fps, H.264 + AAC, ~53 s
- Gancho en el primer frame: "¿CÓMO GANAR MONEDAS FÁCIL? en ALCES VS CANADÁ"
- Texto grande y centrado dentro de la zona segura de TikTok

## Videos

| Video | Script | Duración |
|---|---|---|
| ¿Cómo ganar monedas fácil? | `generate_video.py` | ~53 s |
| ¿Es más fácil ganar como Alce o como Soldado? | `video_alces_vs_soldados.py` | ~35 s |
| Ranking de TODAS las clases de Soldado | `video_ranking_soldados.py` | ~57,5 s |
| Ranking de TODAS las skins de Alce | `video_ranking_skins.py` | ~94 s |

El ranking agrega barra de nota animada, íconos de equipo dibujados, tabla final,
música de fondo sintetizada, whoosh en transiciones, ding en cada nota y redoble antes de Pyro.
`python video_ranking_soldados.py --muestras` guarda fotogramas de revisión en `output/muestras_ranking/`.

Para un video nuevo, copia `video_alces_vs_soldados.py` y cambia `SCRIPT`, el gancho y el cierre.
Tipos de tarjeta: `intro` (gancho), `play` (ícono + título + textos), `versus` (dos columnas con VS) y `outro`.

## Generarlo de nuevo

```bash
pip install -r requirements.txt   # también necesita ffmpeg instalado
python generate_video.py              # video de monedas
python video_alces_vs_soldados.py     # video alces vs soldados
```

La voz se genera offline con [Piper](https://github.com/rhasspy/piper) (voz masculina es_MX "ald",
un poco más rápida: `LENGTH_SCALE = 0.85`). El modelo se descarga solo la primera vez en `voices/`.
El guion está en la lista `SCRIPT` de `generate_video.py`.

`python generate_video.py --preview 1 10 30` guarda capturas en `build/` sin renderizar el video.

## Assets
- `assets/alce_profesor_sheet.png` – hoja de modelo del alce (poses y bocas para el lip-sync)
- `assets/iconos_jugadas.png` – íconos de jugadas (??, ?, 👍, !!, corona, libro)

### Ranking de skins
- Voz offline Piper `es_MX-claude-high` (la que mejor reconoció Whisper entre las es_MX disponibles;
  edge-tts no es accesible desde este entorno). El diccionario `FONETICA` corrige solo para el TTS
  cómo suenan AlceCoins, GOLDMOOSE, Aguz, studs, Halloween, etc.
- Subtítulos sincronizados frase por frase, con palabras clave en amarillo (`*así*` en el guion).
- Cada tarjeta dura su narración + 0,5 s.
- `python video_ranking_skins.py --muestras` genera 5 fotogramas y 10 s de voz en `output/muestras_skins/`.

## Bot de Discord – AlceKnow

Bot en español que lo sabe todo sobre *Alces vs Canadá* (carpeta [`discord_bot/`](discord_bot/)).

| Comando | Qué hace |
|---|---|
| `/ask pregunta:` | Responde dudas del juego con Claude, usando lo escrito en `discord_bot/conocimiento.md` |
| `/moose` | Muestra una foto real y al azar de un alce (Wikimedia Commons) |
| `/moose-origins` | Explica dónde habitan los alces en el mundo |

1. En el [Discord Developer Portal](https://discord.com/developers/applications) crea una aplicación → **Bot** → *Reset Token*.
2. Invítalo con OAuth2 → URL Generator, scopes `bot` y `applications.commands`, permisos *Send Messages*, *Embed Links*.
3. Configura y arranca:

```bash
cd discord_bot
pip install -r requirements.txt
cp .env.example .env      # pon DISCORD_TOKEN, ANTHROPIC_API_KEY y opcionalmente GUILD_ID
python bot.py
```

La personalidad del **Profesor Alce** y todo lo que sabe del juego están en `discord_bot/conocimiento.md`. Para cambiar datos (notas, precios, códigos), edita ese archivo: no hace falta tocar el código y se relee en cada pregunta.
