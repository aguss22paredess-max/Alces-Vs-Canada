# Alces vs Canadá – Video AlceKnow

Video vertical para TikTok del **Alce Profesor** explicando cómo ganar monedas fácil en *Alces vs Canadá*.

- Resultado: [`output/alceknow_monedas.mp4`](output/alceknow_monedas.mp4)
- 1080×1920 (9:16), 30 fps, H.264 + AAC, ~53 s
- Gancho en el primer frame: "¿CÓMO GANAR MONEDAS FÁCIL? en ALCES VS CANADÁ"
- Texto grande y centrado dentro de la zona segura de TikTok

## Generarlo de nuevo

```bash
pip install -r requirements.txt   # también necesita ffmpeg instalado
python generate_video.py
```

La voz se genera offline con [Piper](https://github.com/rhasspy/piper) (voz masculina es_MX "ald",
un poco más rápida: `LENGTH_SCALE = 0.85`). El modelo se descarga solo la primera vez en `voices/`.
El guion está en la lista `SCRIPT` de `generate_video.py`.

`python generate_video.py --preview 1 10 30` guarda capturas en `build/` sin renderizar el video.

## Assets
- `assets/alce_profesor_sheet.png` – hoja de modelo del alce (poses y bocas para el lip-sync)
- `assets/iconos_jugadas.png` – íconos de jugadas (??, ?, 👍, !!, corona, libro)
