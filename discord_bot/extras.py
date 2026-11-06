"""Comandos extra del Profesor Alce: útiles, de diversión y de información.

main.py los activa con:
    from extras import registrar_extras
    registrar_extras(self)        # dentro de setup_hook, antes de sincronizar

Todos los datos del juego salen de la ficha pública del 6 de noviembre de 2026
(ficha_publica.md). No agregues aquí nada de la parte interna del proyecto.
"""

from __future__ import annotations

import hashlib
import random

import discord
from discord import app_commands

from respuestas import normalizar

COLOR = discord.Color.from_rgb(139, 90, 43)
PIE = "Profesor Alce 🫎 – Alces VS Canadá"

ENLACES = {
    "🎮 Jugar en Roblox": "https://www.roblox.com/games/75124408421132",
    "💬 Discord": "https://discord.gg/CcngQs3Zr",
    "📱 TikTok": "https://www.tiktok.com/@alces.vs.canada",
}

MAPAS = ["Ottawa", "Toronto", "Ártico", "Vancouver", "Montreal", "Quebec", "Ontario",
         "Tundra", "Calgary"]

SKINS = {
    "Aguz": "👑 **15.000 monedas.** Mitad de daño por disparo, Golpe de 70 cada 19 s, 10 % más "
            "rápido y Embestida de 45 de daño (si choca, se aturde y pierde vida). Nota: **10/10**.",
    "Perú": "🇵🇪 Recibe **30 % menos de daño** y su escudo **bloquea disparos**.",
    "Magma": "🌋 **Quema** a los soldados que se le pegan.",
    "Aurora": "🌌 En el **Ártico** tiene **+140 de vida** y puede **teletransportarse**.",
    "Sombra": "🌑 Se **desvanece en humo**; una linterna lo descubre en **3 s**.",
    "Calabaza": "🎃 **Ya no se vende.** 150 de vida, Calabomba y Disfraz. Quien lo compró lo "
                "equipa en **Tienda › Extras**.",
    "Dorado": "🏅 Solo se obtiene con un **código**.",
}

CLASES = {
    "Fusilero": "🎯 **Mosquete** (55 de daño, 20 s de recarga), **navaja** (35) y **linterna**.",
    "Leñador": "🪓 Clase de pago: **1.550 monedas**. Nota del Profesor: **8,5/10**.",
    "Disciplinado": "🎖️ Clase de pago: **750 monedas**. Nota del Profesor: **7/10**.",
    "Médico": "🩹 Cura **50 de vida** a quienes estén cerca, con **3 usos**.",
    "Albañil": "🧱 1 por equipo. **Trampas de oso** (clic con el martillo, máx. 4, aturden 6 s, "
               "invisibles para los alces, un uso), **señuelo** con la tecla F (máx. 4) y "
               "**paleta** de 35 de daño.",
    "Pesado": "🛡️ La clase existe, PEEERO sus datos nuevos no están en mis apuntes.",
}

CONSEJOS = [
    "Ojo: las banderas van **en orden** (1, 2 y 3). No pierdas tiempo en la 3 si no tienen la 1.",
    "Si te alejas del poste, la captura **se cancela**. Quédate los 50 s completos, pillo.",
    "Usa el **Empuje Fuerte** para sacar a los soldados de la zona de la bandera. Se recarga en 70 s.",
    "Soldados: la **linterna** descubre al Alce Sombra en 3 s. ¡Alumbren todo!",
    "Alces: el **Golpe** hace 35 de daño y se recarga en 24 s. No lo gastes en el aire.",
    "Albañil: los alces **no ven las trampas de oso**. Ponlas justo al lado de los postes.",
    "Morir mucho **baja tu bonus** de monedas. Juega con cabeza, no con los cuernos.",
    "Entra todos los días: el **premio diario** sube con la racha hasta 500 monedas.",
    "Completa las **3 misiones diarias** y te llevas 200 monedas extra. De nada.",
    "Invita amigos: **150 monedas** por cada amigo distinto, y tu amigo recibe 100.",
    "¿Estás solo en el servidor? Prueba el **modo práctica** para entrenar contra bots.",
    "Médico: cura **50 de vida** a todos los cercanos. Quédate cerca de tu equipo.",
    "El escudo del **Alce Perú** bloquea disparos. Soldados, ¡usen la navaja contra él!",
    "En el **Ártico**, el Alce Aurora tiene +140 de vida. Soldados, cuidado en ese mapa.",
]

DATOS_ALCE = [
    "El alce es el **ciervo más grande del mundo**: un macho puede pesar más de 600 kg.",
    "Los alces son **excelentes nadadores** y cruzan lagos y ríos sin problema.",
    "Pueden **sumergirse** para comer plantas acuáticas del fondo de los lagos.",
    "Solo los **machos** tienen astas, y las **cambian cada año**.",
    "Las astas de un macho adulto pueden medir **más de 1,5 m** de punta a punta.",
    "En Norteamérica se le dice **moose**; en el inglés británico, **elk**.",
    "Viven en el **hemisferio norte**: Canadá, Alaska, Escandinavia, Rusia y más.",
    "No soportan bien el calor: prefieren los **bosques fríos** cerca del agua.",
    "En invierno comen **ramas, cortezas y brotes**; en verano, plantas acuáticas.",
]

RESPUESTAS_ORACULO = [
    "Sí, sin duda. 🫎", "Ojo: todo indica que sí.", "Mis apuntes dicen que sí.",
    "PEEERO… mejor no.", "No, pillo.", "Ni lo sueñes. 😅",
    "Pregúntame de nuevo después de capturar 3 banderas.",
    "Eso no lo tengo en mis apuntes, pregúntale a Aguz.",
    "Mmm… 50 y 50, como estar en la zona de la bandera.",
    "Al tiro que sí. De nada.",
]

# (pregunta, respuesta correcta, opciones incorrectas)
TRIVIA = [
    ("¿Cuántas banderas tienen que capturar los Alces?", "3", ["2", "4", "5"]),
    ("¿Cuánto dura una ronda?", "6 minutos", ["4 minutos", "5 minutos", "8 minutos"]),
    ("¿Cuánto cuesta el Alce Aguz?", "15.000", ["5.000", "10.000", "20.000"]),
    ("¿Cuántos segundos hay que quedarse cerca del poste?", "50 s", ["30 s", "40 s", "60 s"]),
    ("¿Qué descubre al Alce Sombra?", "La linterna", ["El mosquete", "La trampa", "El señuelo"]),
    ("¿Cuántas monedas da ganar la ronda?", "79", ["50", "100", "150"]),
    ("¿Con qué tecla pone el señuelo el Albañil?", "F", ["Q", "E", "R"]),
    ("¿Cuánto daño hace el mosquete?", "55", ["35", "45", "70"]),
    ("¿Cuánta vida base tiene un Alce?", "300", ["150", "200", "500"]),
    ("¿En qué mapa el Alce Aurora se teletransporta?", "Ártico", ["Toronto", "Calgary", "Ottawa"]),
    ("¿Cuánto cuesta el Leñador?", "1.550", ["750", "1.200", "2.000"]),
    ("¿Cuánta vida cura el Médico?", "50", ["25", "75", "100"]),
    ("¿Cuántos segundos esperas al morir?", "10", ["5", "25", "30"]),
    ("¿Cuál es el premio diario más alto?", "500", ["200", "300", "1.000"]),
    ("¿Cuántas trampas de oso puede poner el Albañil por partida?", "4", ["2", "3", "6"]),
    ("¿Cuánto cuesta el Disciplinado?", "750", ["500", "1.000", "1.550"]),
    ("¿Cuánto daño hace la navaja?", "35", ["20", "45", "55"]),
    ("¿Cada cuánto se recarga el Empuje Fuerte?", "70 s", ["24 s", "40 s", "90 s"]),
]


def embed(titulo: str, texto: str) -> discord.Embed:
    e = discord.Embed(title=titulo, description=texto, color=COLOR)
    e.set_footer(text=PIE)
    return e


def nota_de(cosa: str) -> int:
    """Una nota del 1 al 10 que siempre es la misma para la misma cosa."""
    clave = normalizar(cosa)
    if "aguz" in clave:
        return 10
    return int(hashlib.md5(clave.encode()).hexdigest(), 16) % 10 + 1


def comentario_nota(nota: int) -> str:
    if nota >= 9:
        return "Una joya. Recomendado por el Profesor. 🔥"
    if nota >= 7:
        return "Bastante bueno, PEEERO tiene sus detalles."
    if nota >= 5:
        return "Cumple, sin más. Como el Fusilero."
    if nota >= 3:
        return "Mmm… ser bonito no lo hace mejor."
    return "Casi inútil si juegas solo. Lo siento, pillo. 😅"


class VistaTrivia(discord.ui.View):
    def __init__(self, correcta: str, opciones: list[str]) -> None:
        super().__init__(timeout=60)
        self.correcta = correcta
        self.intentaron: set[int] = set()
        self.ganador: discord.abc.User | None = None
        self.mensaje: discord.Message | None = None
        for opcion in opciones:
            boton = discord.ui.Button(label=opcion, style=discord.ButtonStyle.secondary)
            boton.callback = self._crear_callback(opcion)
            self.add_item(boton)

    def _marcar_botones(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                if item.label == self.correcta:
                    item.style = discord.ButtonStyle.success

    def _crear_callback(self, opcion: str):
        async def callback(interaction: discord.Interaction) -> None:
            if self.ganador is not None:
                await interaction.response.send_message("Esta trivia ya terminó. 🫎", ephemeral=True)
                return
            if interaction.user.id in self.intentaron:
                await interaction.response.send_message("Ya respondiste, pillo. ¡Una sola vez!",
                                                        ephemeral=True)
                return
            self.intentaron.add(interaction.user.id)
            if opcion != self.correcta:
                await interaction.response.send_message("❌ Incorrecto. PEEERO sigue estudiando.",
                                                        ephemeral=True)
                return
            self.ganador = interaction.user
            self._marcar_botones()
            self.stop()
            await interaction.response.edit_message(
                content=f"✅ ¡**{interaction.user.display_name}** acertó! La respuesta era "
                        f"**{self.correcta}**. De nada. 🫎",
                view=self,
            )
        return callback

    async def on_timeout(self) -> None:
        if self.ganador is None and self.mensaje is not None:
            self._marcar_botones()
            try:
                await self.mensaje.edit(
                    content=f"⏰ Se acabó el tiempo. La respuesta era **{self.correcta}**.", view=self)
            except discord.HTTPException:
                pass


def registrar_extras(bot: discord.Client) -> None:
    tree: app_commands.CommandTree = bot.tree

    # ── Útiles ────────────────────────────────────────────────────────────
    @tree.command(name="ayuda", description="Todos los comandos del Profesor Alce")
    async def ayuda(interaction: discord.Interaction) -> None:
        e = embed("📚 Comandos del Profesor Alce", "Escribe `/` y elige uno. ¡De nada! 🫎")
        e.add_field(name="🎮 Juego", inline=False, value=(
            "`/ask` pregúntame lo que sea · `/game` enlace del juego · `/links` redes oficiales\n"
            "`/skin` ficha de una skin · `/clase` ficha de una clase · `/mapas` lista de mapas\n"
            "`/monedas` cómo ganar monedas · `/practica` modo práctica · `/novedades` cambios\n"
            "`/consejo` un tip del Profesor · `/creators` los creadores"))
        e.add_field(name="🎉 Diversión", inline=False, value=(
            "`/trivia` pon a prueba lo que sabes · `/bando` el Profesor elige tu bando\n"
            "`/duelo` Alce vs Soldado contra alguien · `/nota` califico lo que quieras\n"
            "`/oraculo` te respondo sí o no · `/mapa-random` un mapa al azar\n"
            "`/moose` foto de un alce · `/dato-alce` un dato real de alces"))
        e.add_field(name="ℹ️ Info", inline=False, value=(
            "`/moose-origins` dónde viven los alces · `/server` info del servidor\n"
            "`/usuario` info de alguien · `/avatar` foto de perfil · `/ping` velocidad del bot"))
        await interaction.response.send_message(embed=e)

    @tree.command(name="links", description="Enlaces oficiales de Alces VS Canadá")
    async def links(interaction: discord.Interaction) -> None:
        texto = "\n".join(f"{nombre}: {url}" for nombre, url in ENLACES.items())
        texto += ("\n\n📺 YouTube, Reddit y el Grupo de Roblox vienen en camino."
                  "\n🌐 El sitio **alcesvscanada.cl** todavía no está publicado.")
        vista = discord.ui.View()
        for nombre, url in ENLACES.items():
            emoji, etiqueta = nombre.split(" ", 1)
            vista.add_item(discord.ui.Button(label=etiqueta, url=url, emoji=emoji))
        await interaction.response.send_message(embed=embed("🔗 Enlaces oficiales", texto), view=vista)

    @tree.command(name="mapas", description="Todos los mapas del juego")
    async def mapas(interaction: discord.Interaction) -> None:
        texto = "\n".join(
            f"🗺️ **{m}**" + (" (grande)" if m == "Tundra" else " (mediano)" if m == "Calgary" else "")
            for m in MAPAS)
        await interaction.response.send_message(embed=embed(f"🗺️ Mapas ({len(MAPAS)})", texto))

    @tree.command(name="skin", description="Ficha de una skin de Alce")
    @app_commands.describe(nombre="La skin que quieres ver")
    @app_commands.choices(nombre=[app_commands.Choice(name=f"Alce {s}", value=s) for s in SKINS])
    async def skin(interaction: discord.Interaction, nombre: app_commands.Choice[str]) -> None:
        await interaction.response.send_message(
            embed=embed(f"🫎 Alce {nombre.value}", SKINS[nombre.value]))

    @tree.command(name="clase", description="Ficha de una clase de Soldado")
    @app_commands.describe(nombre="La clase que quieres ver")
    @app_commands.choices(nombre=[app_commands.Choice(name=c, value=c) for c in CLASES])
    async def clase(interaction: discord.Interaction, nombre: app_commands.Choice[str]) -> None:
        await interaction.response.send_message(
            embed=embed(f"⚔️ {nombre.value}", CLASES[nombre.value]))

    @tree.command(name="monedas", description="Todas las formas de ganar monedas")
    async def monedas(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=embed("💰 Cómo ganar monedas", (
            "🏆 **Ganar la ronda:** 79, más 5 por asesinato al final (morir mucho baja el bonus).\n"
            "📅 **Premio diario:** 50, 75, 100, 150, 200, 300 y 500 según la racha.\n"
            "🤝 **Invitar:** 150 por cada amigo distinto (y 100 de bienvenida para tu amigo).\n"
            "📋 **Misiones diarias:** 200 extra por completar las 3 del día.\n"
            "⭐ **Pase VIP:** duplica las monedas por victoria.\n\n"
            "Ojo: el modo práctica **no da monedas**. De nada. 🫎")))

    @tree.command(name="practica", description="Niveles del modo práctica")
    async def practica(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=embed("🎯 Modo práctica", (
            "Se ofrece cuando estás **solo en el servidor**. Juegas de Alce o de Soldado, "
            "PEEERO **no da monedas**.\n\n"
            "```\nNivel      Soldados bot   Alces bot\n"
            "Fácil           2             2\n"
            "Medio           3             3\n"
            "Difícil         5             4\n"
            "Imposible       6             6\n"
            "Pacífico    sin bots ni banderas\n```")))

    @tree.command(name="novedades", description="Últimos cambios del juego")
    async def novedades(interaction: discord.Interaction) -> None:
        e = embed("🆕 Novedades", "Lo último de Alces VS Canadá:")
        e.add_field(name="Noviembre 2026", inline=False, value=(
            "Práctica como Soldado, nivel Imposible, bots rebalanceados, visión de alce más clara, "
            "sonidos nuevos, alces remodelados, menús minimalistas, sección Extras, Halloween "
            "retirado y arreglo de la pantalla de reaparición."))
        e.add_field(name="22 de octubre", inline=False, value="Bots con linterna y animaciones.")
        e.add_field(name="20 de octubre", inline=False, value=(
            "Práctica por niveles, bots más listos, escenas de victoria, Alce Calabaza y evento "
            "de Halloween."))
        e.add_field(name="18 de octubre", inline=False, value="Alce Aguz, premio diario e invitaciones.")
        e.add_field(name="🤫 En camino (sin fecha)", inline=False, value=(
            "Partida Rápida y Reto del día. Yo no prometo nada, pillo."))
        await interaction.response.send_message(embed=e)

    @tree.command(name="consejo", description="Un consejo del Profesor Alce")
    async def consejo(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            embed=embed("💡 Consejo del Profesor", random.choice(CONSEJOS) + "\n\nDe nada. 🫎"))

    # ── Diversión ─────────────────────────────────────────────────────────
    @tree.command(name="trivia", description="Pregunta de trivia de Alces VS Canadá")
    async def trivia(interaction: discord.Interaction) -> None:
        pregunta, correcta, malas = random.choice(TRIVIA)
        opciones = [correcta, *malas]
        random.shuffle(opciones)
        vista = VistaTrivia(correcta, opciones)
        await interaction.response.send_message(
            content=f"🧠 **Trivia del Profesor**\n{pregunta}\n*Tienen 60 s. Cada uno responde una vez.*",
            view=vista)
        vista.mensaje = await interaction.original_response()

    @tree.command(name="bando", description="El Profesor elige tu bando, tu equipo y tu mapa")
    async def bando(interaction: discord.Interaction) -> None:
        mapa = random.choice(MAPAS)
        if random.random() < 0.5:
            skin_elegida = random.choice([s for s in SKINS if s != "Calabaza"])
            texto = (f"Te toca ser **ALCE** 🫎 con la skin **Alce {skin_elegida}**, en **{mapa}**.\n"
                     "Ojo: captura las 3 banderas en orden y usa tus habilidades.")
        else:
            clase_elegida = random.choice(list(CLASES))
            texto = (f"Te toca ser **SOLDADO** ⚔️ de **{clase_elegida}**, en **{mapa}**.\n"
                     "Ojo: aguanta los 6 minutos y no sueltes la linterna.")
        await interaction.response.send_message(
            embed=embed(f"🎲 Bando de {interaction.user.display_name}", texto))

    @tree.command(name="duelo", description="Duelo Alce vs Soldado contra otra persona")
    @app_commands.describe(rival="Con quién te quieres batir")
    async def duelo(interaction: discord.Interaction, rival: discord.Member) -> None:
        if rival.id == interaction.user.id:
            await interaction.response.send_message("¿Contra ti mismo? PEEERO… no, pillo. 😅",
                                                    ephemeral=True)
            return
        alce, soldado = random.sample([interaction.user, rival], 2)
        skin_alce = random.choice([s for s in SKINS if s != "Calabaza"])
        clase_soldado = random.choice(list(CLASES))
        ganador = random.choice([alce, soldado])
        jugadas_alce = ["lo mandó a volar con el Empuje Fuerte", "le dio un Golpe de 35 justo a tiempo",
                        "capturó las 3 banderas mientras el otro recargaba"]
        jugadas_soldado = ["le acertó un mosquetazo de 55", "lo dejó atrapado en una trampa de oso",
                           "aguantó los 6 minutos sin soltar la bandera"]
        jugada = random.choice(jugadas_alce if ganador is alce else jugadas_soldado)
        texto = (f"🫎 **{alce.display_name}** (Alce {skin_alce})\n⚔️ vs\n"
                 f"🪖 **{soldado.display_name}** ({clase_soldado})\n\n"
                 f"🏆 Ganó **{ganador.display_name}**: {jugada}. De nada.")
        await interaction.response.send_message(embed=embed("⚔️ ¡Duelo!", texto))

    @tree.command(name="nota", description="El Profesor Alce califica lo que quieras del 1 al 10")
    @app_commands.describe(cosa="Lo que quieres que califique")
    async def nota(interaction: discord.Interaction, cosa: app_commands.Range[str, 1, 100]) -> None:
        n = nota_de(cosa)
        await interaction.response.send_message(embed=embed(
            "📝 Nota del Profesor", f"**{cosa}**: **{n}/10** {'⭐' * n}\n{comentario_nota(n)}"))

    @tree.command(name="oraculo", description="Hazle una pregunta de sí o no al Profesor")
    @app_commands.describe(pregunta="Tu pregunta de sí o no")
    async def oraculo(interaction: discord.Interaction,
                      pregunta: app_commands.Range[str, 1, 200]) -> None:
        await interaction.response.send_message(embed=embed(
            "🔮 El oráculo del Profesor", f"❓ {pregunta}\n\n🫎 {random.choice(RESPUESTAS_ORACULO)}"))

    @tree.command(name="mapa-random", description="Elige un mapa al azar")
    async def mapa_random(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=embed(
            "🗺️ Mapa al azar", f"Hoy toca **{random.choice(MAPAS)}**. ¡A jugar, pillo! 🫎"))

    @tree.command(name="dato-alce", description="Un dato real sobre los alces")
    async def dato_alce(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            embed=embed("🫎 ¿Sabías que…?", random.choice(DATOS_ALCE)))

    # ── Info ──────────────────────────────────────────────────────────────
    @tree.command(name="ping", description="Mide qué tan rápido responde el bot")
    async def ping(interaction: discord.Interaction) -> None:
        ms = round(bot.latency * 1000)
        await interaction.response.send_message(f"🏓 ¡Pong! Respondo en **{ms} ms**. Al tiro. 🫎")

    @tree.command(name="server", description="Información de este servidor")
    async def server(interaction: discord.Interaction) -> None:
        g = interaction.guild
        if g is None:
            await interaction.response.send_message("Este comando funciona dentro de un servidor.",
                                                    ephemeral=True)
            return
        e = embed(f"🏠 {g.name}", g.description or "")
        e.add_field(name="👥 Miembros", value=str(g.member_count or "?"))
        e.add_field(name="💬 Canales", value=str(len(g.channels)))
        e.add_field(name="🎭 Roles", value=str(len(g.roles)))
        e.add_field(name="📅 Creado", value=discord.utils.format_dt(g.created_at, "D"))
        if g.premium_subscription_count:
            e.add_field(name="🚀 Boosts", value=str(g.premium_subscription_count))
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        await interaction.response.send_message(embed=e)

    @tree.command(name="usuario", description="Información de un usuario")
    @app_commands.describe(persona="De quién quieres ver la info (vacío = tú)")
    async def usuario(interaction: discord.Interaction, persona: discord.Member | None = None) -> None:
        p = persona or interaction.user
        e = embed(f"👤 {p.display_name}", f"Usuario: **{p.name}**")
        e.add_field(name="📅 Cuenta creada", value=discord.utils.format_dt(p.created_at, "D"))
        if isinstance(p, discord.Member) and p.joined_at:
            e.add_field(name="🚪 Entró al servidor", value=discord.utils.format_dt(p.joined_at, "D"))
        e.set_thumbnail(url=p.display_avatar.url)
        await interaction.response.send_message(embed=e)

    @tree.command(name="avatar", description="Muestra la foto de perfil de alguien")
    @app_commands.describe(persona="De quién (vacío = tú)")
    async def avatar(interaction: discord.Interaction, persona: discord.Member | None = None) -> None:
        p = persona or interaction.user
        e = embed(f"🖼️ Avatar de {p.display_name}", "")
        e.set_image(url=p.display_avatar.with_size(1024).url)
        await interaction.response.send_message(embed=e)
