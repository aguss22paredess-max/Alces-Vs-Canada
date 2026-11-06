"""AlceKnow – bot de Discord de Alces vs Canadá.

Comandos:
  /ask pregunta:<texto>  Responde cualquier duda sobre Alces vs Canadá.
  /moose                 Muestra una foto real de un alce sacada de Wikimedia Commons.
  /moose-origins         Explica dónde viven los alces en el mundo.

Variables de entorno (o archivo .env junto a este script):
  DISCORD_TOKEN       Token del bot (Discord Developer Portal -> Bot -> Reset Token).
  ANTHROPIC_API_KEY   Clave de la API de Claude, necesaria para /ask.
  GUILD_ID            (Opcional) ID de tu servidor: los comandos aparecen al instante
                      en ese servidor en lugar de tardar hasta 1 h en propagarse.
"""

from __future__ import annotations

import logging
import os
import random
from pathlib import Path

import aiohttp
import anthropic
import discord
from discord import app_commands

BASE_DIR = Path(__file__).resolve().parent
CONOCIMIENTO = BASE_DIR / "conocimiento.md"

MODELO = "claude-opus-5-5"
COLOR_ALCE = discord.Color.from_rgb(139, 90, 43)
LIMITE_DISCORD = 2000
USER_AGENT = "AlceKnowDiscordBot/1.0 (bot de Discord de Alces vs Canada)"

log = logging.getLogger("alceknow")


def cargar_env(ruta: Path) -> None:
    """Lee un .env sencillo (CLAVE=valor) sin pisar variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def prompt_sistema() -> str:
    """La personalidad y todo lo que sabe el Profesor Alce vienen de conocimiento.md."""
    personaje = CONOCIMIENTO.read_text(encoding="utf-8") if CONOCIMIENTO.exists() else ""
    return (
        f"{personaje.strip()}\n\n"
        "═══ FORMATO EN DISCORD ═══\n"
        "- Escribe directamente la respuesta del Profesor Alce, sin el prefijo \"Profesor Alce:\".\n"
        "- Puedes usar negritas y listas de Discord cuando ayuden. Nunca pases de 1900 caracteres."
    )


def partir_mensaje(texto: str, limite: int = LIMITE_DISCORD) -> list[str]:
    """Divide un texto largo en trozos que quepan en un mensaje de Discord."""
    partes: list[str] = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte <= 0:
            corte = texto.rfind(" ", 0, limite)
        if corte <= 0:
            corte = limite
        partes.append(texto[:corte])
        texto = texto[corte:].lstrip()
    if texto:
        partes.append(texto)
    return partes


# ---------------------------------------------------------------------------
# /ask
# ---------------------------------------------------------------------------

async def preguntar_a_claude(cliente: anthropic.AsyncAnthropic, pregunta: str) -> str:
    respuesta = await cliente.beta.messages.create(
        model=MODELO,
        max_tokens=16000,
        output_config={"effort": "low"},
        system=[{"type": "text", "text": prompt_sistema(), "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": pregunta}],
        # Si el modelo rechaza la pregunta, la API la reintenta sola con otro modelo.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if respuesta.stop_reason == "refusal":
        return "🫎 Esa pregunta no la puedo responder. ¡Prueba con otra sobre Alces vs Canadá!"
    texto = "".join(b.text for b in respuesta.content if b.type == "text").strip()
    return texto or "🫎 Me quedé sin palabras… intenta preguntar de otra forma."


# ---------------------------------------------------------------------------
# /moose
# ---------------------------------------------------------------------------

COMMONS_API = "https://commons.wikimedia.org/w/api.php"


async def foto_de_alce(sesion: aiohttp.ClientSession) -> dict | None:
    """Busca una foto al azar de un alce (Alces alces) en Wikimedia Commons."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": '"Alces alces" filetype:bitmap',
        "gsrnamespace": "6",
        "gsrlimit": "50",
        "gsroffset": str(random.randint(0, 400)),
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "1280",
    }
    async with sesion.get(COMMONS_API, params=params, headers={"User-Agent": USER_AGENT}) as r:
        r.raise_for_status()
        datos = await r.json()
    paginas = list(datos.get("query", {}).get("pages", {}).values())
    fotos = []
    for p in paginas:
        info = (p.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if url and url.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp")):
            fotos.append({
                "titulo": p.get("title", "").removeprefix("File:").rsplit(".", 1)[0],
                "imagen": url,
                "pagina": info.get("descriptionurl"),
            })
    return random.choice(fotos) if fotos else None


# ---------------------------------------------------------------------------
# /moose-origins
# ---------------------------------------------------------------------------

def embed_origenes() -> discord.Embed:
    e = discord.Embed(
        title="🌲 ¿Dónde viven los alces?",
        description=(
            "El alce (*Alces alces*) es el ciervo más grande del mundo: un macho puede medir "
            "más de 2 m hasta la cruz y pesar más de 600 kg. Vive en el **hemisferio norte**, "
            "en zonas frías llenas de bosques, lagos y pantanos."
        ),
        color=COLOR_ALCE,
    )
    e.add_field(
        name="🇨🇦 Norteamérica",
        value=(
            "Casi todo **Canadá** (es su animal más emblemático, con cientos de miles de alces), "
            "**Alaska** y el norte de **EE. UU.**: Maine, Minnesota, Montana, Wyoming e Idaho, "
            "entre otros. En **Terranova** fueron introducidos a principios del siglo XX."
        ),
        inline=False,
    )
    e.add_field(
        name="🌍 Europa",
        value=(
            "**Noruega, Suecia y Finlandia**, los **países bálticos**, **Polonia** y el norte de "
            "**Bielorrusia**. Allí se le llama *elk* en inglés británico."
        ),
        inline=False,
    )
    e.add_field(
        name="🌏 Asia",
        value=(
            "Toda la **taiga de Rusia y Siberia**, el norte de **Mongolia** y el noreste de **China**."
        ),
        inline=False,
    )
    e.add_field(
        name="🏞️ Su hábitat ideal",
        value=(
            "El **bosque boreal (taiga)**: abetos, pinos y abedules cerca del agua. En verano se "
            "meten a lagos y ríos para comer plantas acuáticas y escapar de los mosquitos; en "
            "invierno comen ramas, cortezas y brotes. No soportan bien el calor."
        ),
        inline=False,
    )
    e.set_footer(text="AlceKnow 🫎 – Alces vs Canadá")
    return e


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

class AlceKnow(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.sesion: aiohttp.ClientSession | None = None
        self.claude: anthropic.AsyncAnthropic | None = None

    async def setup_hook(self) -> None:
        self.sesion = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        if os.environ.get("ANTHROPIC_API_KEY"):
            self.claude = anthropic.AsyncAnthropic()
        else:
            log.warning("Falta ANTHROPIC_API_KEY: /ask no podrá responder.")

        registrar_comandos(self)
        guild_id = os.environ.get("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Comandos sincronizados en el servidor %s", guild_id)
        else:
            await self.tree.sync()
            log.info("Comandos sincronizados globalmente (pueden tardar hasta 1 h en aparecer)")

    async def close(self) -> None:
        if self.sesion:
            await self.sesion.close()
        await super().close()

    async def on_ready(self) -> None:
        log.info("Conectado como %s", self.user)
        await self.change_presence(activity=discord.Game("Alces vs Canadá | /ask"))


def registrar_comandos(bot: AlceKnow) -> None:
    @bot.tree.command(name="ask", description="Pregúntale a AlceKnow lo que quieras de Alces vs Canadá")
    @app_commands.describe(pregunta="Tu pregunta sobre el juego")
    async def ask(interaction: discord.Interaction, pregunta: app_commands.Range[str, 1, 1000]) -> None:
        if bot.claude is None:
            await interaction.response.send_message(
                "⚠️ El bot no tiene configurada la clave de Claude (ANTHROPIC_API_KEY).", ephemeral=True
            )
            return
        await interaction.response.defer(thinking=True)
        try:
            texto = await preguntar_a_claude(bot.claude, pregunta)
        except anthropic.RateLimitError:
            texto = "🫎 Estoy recibiendo demasiadas preguntas. Intenta de nuevo en un momento."
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            log.exception("Error en la API de Claude: %s", exc)
            texto = "🫎 Algo falló al pensar la respuesta. Intenta de nuevo en un rato."
        encabezado = f"❓ **{interaction.user.display_name}:** {pregunta}\n\n"
        partes = partir_mensaje(encabezado + texto)
        await interaction.followup.send(partes[0])
        for parte in partes[1:]:
            await interaction.followup.send(parte)

    @bot.tree.command(name="moose", description="Muestra una foto de un alce sacada de internet")
    async def moose(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        foto = None
        try:
            for _ in range(3):  # algunos rangos de búsqueda vienen vacíos
                foto = await foto_de_alce(bot.sesion)
                if foto:
                    break
        except (aiohttp.ClientError, TimeoutError) as exc:
            log.warning("No se pudo obtener la foto: %s", exc)
        if not foto:
            await interaction.followup.send("🫎 No encontré ningún alce esta vez. ¡Prueba otra vez!")
            return
        e = discord.Embed(title="🫎 ¡Un alce salvaje apareció!", url=foto["pagina"], color=COLOR_ALCE)
        e.set_image(url=foto["imagen"])
        e.set_footer(text=f"{foto['titulo'][:200]} · Wikimedia Commons")
        await interaction.followup.send(embed=e)

    @bot.tree.command(name="moose-origins", description="Explica dónde habitan los alces en el mundo")
    async def moose_origins(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=embed_origenes())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cargar_env(BASE_DIR / ".env")
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Falta DISCORD_TOKEN. Copia .env.example a .env y pon el token de tu bot.")
    AlceKnow().run(token, log_handler=None)


if __name__ == "__main__":
    main()
