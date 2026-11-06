"""AlceKnow – bot de Discord de Alces vs Canadá.

Comandos:
  /ask pregunta:<texto>  El Profesor Alce responde dudas del juego (respuestas en respuestas.py,
                         sin usar ninguna API de pago).
  /moose                 Muestra una foto real de un alce sacada de Wikimedia Commons.
  /moose-origins         Explica dónde viven los alces en el mundo.
  /game                  Muestra el enlace para jugar Alces VS Canadá en Roblox.
  /creators              Muestra a los creadores del juego.

Variables de entorno (o archivo .env junto a este script):
  DISCORD_TOKEN       Token del bot (Discord Developer Portal -> Bot -> Reset Token).
  GUILD_ID            (Opcional) ID de tu servidor: los comandos aparecen al instante
                      en ese servidor en lugar de tardar hasta 1 h en propagarse.
"""

from __future__ import annotations

import logging
import os
import random
from pathlib import Path

import aiohttp
import discord
from discord import app_commands

from extras import registrar_extras
from respuestas import responder

BASE_DIR = Path(__file__).resolve().parent
COLOR_ALCE = discord.Color.from_rgb(139, 90, 43)
LIMITE_DISCORD = 2000
# Wikimedia rechaza (403) a los bots que no dejan un enlace de contacto en el User-Agent.
USER_AGENT = "ProfesorAlceBot/1.1 (https://github.com/aguss22paredess-max/Alces-Vs-Canada) discord.py"

ENLACE_JUEGO = "https://www.roblox.com/games/75124408421132"
CREADORES = ["Agus", "Camilo", "Jacob"]

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
# /moose
# ---------------------------------------------------------------------------

COMMONS_API = "https://commons.wikimedia.org/w/api.php"


async def foto_commons(sesion: aiohttp.ClientSession) -> dict | None:
    """Busca una foto al azar de un alce (Alces alces) en Wikimedia Commons."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": 'incategory:"Alces alces" filetype:bitmap',
        "gsrnamespace": "6",
        "gsrlimit": "50",
        "gsroffset": str(random.randint(0, 100)),
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
                "fuente": "Wikimedia Commons",
            })
    return random.choice(fotos) if fotos else None


INATURALIST_API = "https://api.inaturalist.org/v1"
_taxon_alce: int | None = None


async def id_taxon_alce(sesion: aiohttp.ClientSession) -> int | None:
    """Busca (una sola vez) el número de especie del moose (Alces alces) en iNaturalist."""
    global _taxon_alce
    if _taxon_alce is None:
        params = {"q": "moose", "rank": "species", "per_page": "10", "locale": "en"}
        async with sesion.get(f"{INATURALIST_API}/taxa", params=params,
                              headers={"User-Agent": USER_AGENT}) as r:
            r.raise_for_status()
            datos = await r.json()
        for taxon in datos.get("results", []):
            if taxon.get("name") == "Alces alces":
                _taxon_alce = taxon["id"]
                break
    return _taxon_alce


async def foto_inaturalist(sesion: aiohttp.ClientSession) -> dict | None:
    """Una foto de alce verificada, con licencia libre, de iNaturalist."""
    taxon_id = await id_taxon_alce(sesion)
    if not taxon_id:
        return None
    params = {
        "taxon_id": str(taxon_id),
        "photos": "true",
        "quality_grade": "research",
        # Solo el animal: sin caca, huellas ni restos ("Evidence of Presence" = "Organism").
        "term_id": "22",
        "term_value_id": "24",
        "photo_license": "cc0,cc-by,cc-by-sa",
        "per_page": "50",
        "page": str(random.randint(1, 10)),
        "order_by": "votes",
    }
    async with sesion.get(f"{INATURALIST_API}/observations", params=params,
                          headers={"User-Agent": USER_AGENT}) as r:
        r.raise_for_status()
        datos = await r.json()
    fotos = []
    for obs in datos.get("results", []):
        # Doble control: solo aceptamos observaciones identificadas como alce.
        nombre = (obs.get("taxon") or {}).get("name", "")
        if not nombre.startswith("Alces alces"):
            continue
        evidencias = {
            (a.get("controlled_attribute_id"), a.get("controlled_value_id"))
            for a in obs.get("annotations", [])
        }
        if (22, 24) not in evidencias:  # no es una foto del animal
            continue
        for foto in obs.get("photos", [])[:1]:
            url = foto.get("url") or ""
            if "square" not in url:
                continue
            fotos.append({
                "titulo": (foto.get("attribution") or "Foto de iNaturalist"),
                "imagen": url.replace("square", "large"),
                "pagina": obs.get("uri") or f"https://www.inaturalist.org/observations/{obs.get('id')}",
                "fuente": "iNaturalist",
            })
    return random.choice(fotos) if fotos else None


async def foto_de_alce(sesion: aiohttp.ClientSession) -> dict | None:
    """Prueba primero iNaturalist (fotos verificadas por expertos) y, si falla, Wikimedia Commons."""
    for buscar in (foto_inaturalist, foto_commons):
        for _ in range(2):  # algunos rangos de búsqueda vienen vacíos
            try:
                foto = await buscar(sesion)
            except (aiohttp.ClientError, TimeoutError) as exc:
                log.warning("No se pudo obtener la foto de %s: %s", buscar.__name__, exc)
                break
            if foto:
                return foto
    return None


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

    async def setup_hook(self) -> None:
        self.sesion = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        registrar_comandos(self)
        registrar_extras(self)
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
    @bot.tree.command(name="ask", description="Pregúntale al Profesor Alce lo que quieras de Alces vs Canadá")
    @app_commands.describe(pregunta="Tu pregunta sobre el juego")
    async def ask(interaction: discord.Interaction, pregunta: app_commands.Range[str, 1, 1000]) -> None:
        texto = responder(pregunta)
        encabezado = f"❓ **{interaction.user.display_name}:** {pregunta}\n\n"
        partes = partir_mensaje(encabezado + texto)
        await interaction.response.send_message(partes[0])
        for parte in partes[1:]:
            await interaction.followup.send(parte)

    @bot.tree.command(name="moose", description="Muestra una foto de un alce sacada de internet")
    async def moose(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        foto = await foto_de_alce(bot.sesion)
        if not foto:
            await interaction.followup.send("🫎 No encontré ningún alce esta vez. ¡Prueba otra vez!")
            return
        e = discord.Embed(title="🫎 ¡Un alce salvaje apareció!", url=foto["pagina"], color=COLOR_ALCE)
        e.set_image(url=foto["imagen"])
        e.set_footer(text=f"{foto['titulo'][:200]} · {foto['fuente']}")
        await interaction.followup.send(embed=e)

    @bot.tree.command(name="moose-origins", description="Explica dónde habitan los alces en el mundo")
    async def moose_origins(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=embed_origenes())


    @bot.tree.command(name="game", description="Enlace para jugar Alces VS Canadá en Roblox")
    async def game(interaction: discord.Interaction) -> None:
        e = discord.Embed(
            title="🎮 Alces VS Canadá",
            url=ENLACE_JUEGO,
            description=f"¡Ojo, pillo! Entra al tiro y elige tu bando: **Alce** o **Soldado**. 🫎⚔️\n{ENLACE_JUEGO}",
            color=COLOR_ALCE,
        )
        boton = discord.ui.View()
        boton.add_item(discord.ui.Button(label="Jugar en Roblox", url=ENLACE_JUEGO, emoji="🎮"))
        await interaction.response.send_message(embed=e, view=boton)

    @bot.tree.command(name="creators", description="Los creadores de Alces VS Canadá")
    async def creators(interaction: discord.Interaction) -> None:
        nombres = "\n".join(f"🫎 **{nombre}**" for nombre in CREADORES)
        e = discord.Embed(
            title="👑 Creadores de Alces VS Canadá",
            description=f"{nombres}\n\nGracias a ellos existe este juego. De nada. 🫎",
            color=COLOR_ALCE,
        )
        await interaction.response.send_message(embed=e)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cargar_env(BASE_DIR / ".env")
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Falta DISCORD_TOKEN. Copia .env.example a .env y pon el token de tu bot.")
    AlceKnow().run(token, log_handler=None)


if __name__ == "__main__":
    main()
