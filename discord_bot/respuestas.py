"""Respuestas del Profesor Alce para /ask, sin usar ninguna API.

Datos actualizados con la ficha pública del proyecto del 6 de noviembre de 2026.

Cada tema tiene una lista de palabras clave y una respuesta ya escrita.
/ask busca qué palabras clave aparecen en la pregunta y responde con el tema
que más coincide. Para agregar un tema nuevo, copia uno de la lista TEMAS,
cambia las claves y la respuesta, y reinicia el bot.

Las claves no distinguen mayúsculas ni tildes (ñ cuenta como n), y una clave
también coincide con el comienzo de una palabra: "bandera" encuentra "banderas".
Las claves de varias palabras valen más puntos, así ganan los temas más específicos.
"""

from __future__ import annotations

import re
import unicodedata

NO_SE = (
    "Eso no lo tengo en mis apuntes, pregúntale a Aguz, el creador. 🫎\n"
    "Puedes preguntarme por clases, skins, monedas, mapas, el modo práctica, "
    "habilidades, enlaces o cómo ganar."
)

# solo_si_nada=True: el tema solo se usa si ningún otro coincide (saludos, insultos).
TEMAS: list[dict] = [
    # ── Conversación ──────────────────────────────────────────────────────
    {
        "claves": ["hola", "buenas", "holi", "que tal", "saludos", "wena"],
        "solo_si_nada": True,
        "respuesta": "¡Hola, pillo! 🫎 Soy el Profesor Alce. Pregúntame lo que quieras de "
                     "Alces VS Canadá: clases, skins, monedas, mapas o cómo ganar.",
    },
    {
        "claves": ["gracias", "grax", "thanks", "vale", "buena profe"],
        "solo_si_nada": True,
        "respuesta": "De nada. 🫎 Para eso estoy, pillo.",
    },
    {
        "claves": ["tonto", "idiota", "estupido", "basura", "weon", "callate", "aweonao"],
        "solo_si_nada": True,
        "respuesta": "Uy, qué agresivo 😅. Te pongo un 2/10 en modales, PEEERO te subo la "
                     "nota si me haces una pregunta del juego. 🫎",
    },
    {
        "claves": ["quien eres", "que eres", "profesor alce", "presentate"],
        "respuesta": "Soy el Profesor Alce, la mascota y sabio oficial de Alces VS Canadá 🫎. "
                     "Traje azul, corbata roja, lentes y mi libro bajo el brazo. "
                     "Salgo en los videos de AlceKnow.",
    },
    {
        "claves": ["creador", "crearon", "hicieron", "aguz", "agus", "camilo", "jacob", "quien hizo",
                   "quien creo", "dueno"],
        "respuesta": "Los creadores del juego son **Agus**, **Camilo** y **Jacob**. 👑 "
                     "Ojo: si juegas una partida con Aguz te ganas el badge secreto "
                     "**\"itzNotAguz\"**. Y su skin, el Alce Aguz, es un 10/10. 🫎",
    },

    # ── Enlaces ───────────────────────────────────────────────────────────
    {
        "claves": ["link", "enlace", "jugar", "roblox", "donde juego", "como entro"],
        "respuesta": "🎮 Juega Alces VS Canadá en Roblox:\n"
                     "https://www.roblox.com/games/75124408421132\n"
                     "Y únete al Discord: https://discord.gg/CcngQs3Zr 🫎",
    },
    {
        "claves": ["discord", "invitacion", "server"],
        "respuesta": "💬 Discord oficial: https://discord.gg/CcngQs3Zr\n"
                     "Ojo: esa invitación vence el **28 de noviembre de 2026** a las 22:27 "
                     "(hora de Chile y Argentina).",
    },
    {
        "claves": ["tiktok", "video", "alceknow", "redes", "youtube", "reddit", "grupo de roblox",
                   "pagina web", "sitio web", "alcesvscanada"],
        "respuesta": "📱 TikTok oficial: **@alces.vs.canada** → https://www.tiktok.com/@alces.vs.canada "
                     "(ahí salen mis videos de AlceKnow).\n"
                     "YouTube, Reddit y el Grupo de Roblox vienen en camino, y el sitio "
                     "**alcesvscanada.cl** todavía no está publicado. 🫎",
    },

    # ── El juego ──────────────────────────────────────────────────────────
    {
        "claves": ["de que trata", "que es el juego", "como se juega", "como funciona",
                   "reglas", "equipos", "alces vs canada"],
        "respuesta": "Dos equipos: los **Alces** atacan y los **Soldados de Canadá** defienden ⚔️.\n"
                     "Los Alces tienen que capturar **3 banderas en orden** (1, 2 y 3), quedándose "
                     "50 s cerca del poste. Si pasan los **6 minutos** sin las 3 banderas, "
                     "ganan los Soldados.",
    },
    {
        "claves": ["bandera", "capturar", "ganar como alce", "gano como alce", "gano rapido como alce",
                   "objetivo", "zona", "poste"],
        "respuesta": "Ojo, pillo: como Alce ganas capturando las **3 banderas en orden** (1, 2 y 3). "
                     "Tienes que quedarte **50 s cerca del poste**; si te alejas, la captura se "
                     "cancela. Usa el Empuje Fuerte para sacar a los Soldados de ahí. 🫎",
    },
    {
        "claves": ["ronda", "cuanto dura", "minutos", "ganar como soldado", "gano como soldado",
                   "ganan los soldados", "defender"],
        "respuesta": "Cada ronda dura **6 minutos** ⏱️. Si pasa ese tiempo sin que los Alces "
                     "capturen las 3 banderas, ganan los Soldados. Ojo, Soldados: su pega es aguantar.",
    },
    {
        "claves": ["morir", "muero", "me matan", "reaparec", "respawn", "revivir"],
        "respuesta": "Al morir esperas **10 s** y vuelves a la partida. ¡Al tiro de vuelta, pillo! 🫎",
    },
    {
        "claves": ["vision", "oscuro", "noche", "rojo", "se ve", "como ven"],
        "respuesta": "👀 Los **Alces** ven todo el mapa claro, con un tono rojo casi imperceptible. "
                     "Los **Soldados** usan **linterna**… y ojo: la linterna descubre al Alce Sombra.",
    },
    {
        "claves": ["mapa", "mapas"],
        "respuesta": "🗺️ Mapas: **Ottawa, Toronto, Ártico, Vancouver, Montreal, Quebec, Ontario, "
                     "Tundra** (grande) y **Calgary** (mediano).\n"
                     "Ojo: en el Ártico el Alce Aurora tiene +140 de vida y puede teletransportarse.",
    },

    # ── Modo práctica ─────────────────────────────────────────────────────
    {
        "claves": ["practica", "modo practica", "bots", "solo en el servidor", "jugar solo",
                   "facil", "medio", "dificil", "imposible", "pacifico"],
        "respuesta": "🎯 **Modo práctica**: se ofrece cuando estás solo en el servidor. Juegas de "
                     "Alce o de Soldado, PEEERO no da monedas.\n"
                     "· **Fácil**: 2 bots · **Medio**: 3 · **Difícil**: 5 soldados bot (o 4 alces bot) · "
                     "**Imposible**: 6\n"
                     "· **Pacífico**: sin bots ni banderas, para pasear tranquilo.",
    },

    # ── Monedas y premios ─────────────────────────────────────────────────
    {
        "claves": ["moneda", "alcecoin", "coins", "dinero", "plata", "ganar rapido", "farmear"],
        "respuesta": "💰 Cómo ganar monedas:\n"
                     "· Ganar la ronda: **79**, más **5 por asesinato** al final (morir mucho baja el bonus).\n"
                     "· Premio diario: de **50 a 500** según tu racha.\n"
                     "· Invitar amigos: **150** por cada amigo distinto.\n"
                     "· Misiones diarias: **200** extra por completar las 3.\n"
                     "Ojo: un Alce que no usa sus habilidades pierde. De nada. 🫎",
    },
    {
        "claves": ["premio diario", "diario", "racha", "recompensa diaria"],
        "respuesta": "📅 **Premio diario** según tu racha: 50, 75, 100, 150, 200, 300 y **500** "
                     "monedas. ¡No cortes la racha, pillo!",
    },
    {
        "claves": ["invitar", "referido", "amigo"],
        "respuesta": "🤝 **Invitar**: ganas **150 monedas** por cada amigo distinto que invites, "
                     "y tu amigo recibe **100 de bienvenida**. De nada.",
    },
    {
        "claves": ["mision", "misiones"],
        "respuesta": "📋 **Misiones diarias**: completa las 3 del día y te llevas **200 monedas** extra.",
    },
    {
        "claves": ["mvp", "mejor jugador"],
        "respuesta": "🏆 El **MVP** es quien tenga el mejor saldo entre asesinatos y muertes. "
                     "O sea: mata harto y muere poco.",
    },
    {
        "claves": ["vip", "pase", "pass", "gamepass"],
        "respuesta": "⭐ **Pase VIP**: duplica las monedas por victoria y te da cartel y etiqueta "
                     "de chat. El precio no lo tengo en mis apuntes, revísalo en la tienda.",
    },
    {
        "claves": ["xp", "experiencia", "subir de nivel", "cofre", "logro", "estadistica", "consejo"],
        "respuesta": "📈 También hay **nivel y XP**, un **cofre por tiempo**, **logros**, "
                     "**estadísticas** y **consejos**. Mientras más juegas, más cosas desbloqueas. 🫎",
    },
    {
        "claves": ["tienda", "shop", "donde compro", "como compro", "extras"],
        "respuesta": "🛒 En la **tienda** gastas tus monedas en clases y skins. En la sección "
                     "**Tienda › Extras** se equipa el Alce Calabaza si lo compraste.",
    },
    {
        "claves": ["codigo", "code", "goldmoose", "canjear"],
        "respuesta": "🏅 El **Alce Dorado** solo se obtiene con un código. En mis apuntes tengo "
                     "**GOLDMOOSE**. Si no te funciona, pregúntale a Aguz. De nada. 🫎",
    },

    # ── Novedades y leaks ─────────────────────────────────────────────────
    {
        "claves": ["leak", "proximamente", "partida rapida", "reto del dia", "que viene",
                   "nuevo modo"],
        "respuesta": "🤫 **Leaks** (todavía sin publicar, sin fecha):\n"
                     "· **Partida Rápida**: mapa y bando al azar, nivel Medio.\n"
                     "· **Reto del día**: el mismo mapa, bando y nivel para todos; cambia a las 21:00 "
                     "de Chile y Argentina.\n"
                     "· Premio por unirse al grupo: por ahora es solo una idea.\n"
                     "Yo no prometo nada, pillo. 🫎",
    },
    {
        "claves": ["actualizacion", "update", "historial", "novedades", "que hay de nuevo",
                   "cambios", "parche", "evento", "halloween"],
        "respuesta": "🆕 **Noviembre 2026**: práctica como Soldado, nivel Imposible, bots rebalanceados, "
                     "visión de alce más clara, sonidos nuevos, alces remodelados, menús minimalistas, "
                     "sección Extras, Halloween retirado y arreglo de la pantalla de reaparición.\n"
                     "**22 oct**: bots con linterna y animaciones. **20 oct**: práctica por niveles, "
                     "bots más listos, escenas de victoria, Alce Calabaza y evento de Halloween. "
                     "**18 oct**: Alce Aguz, premio diario e invitaciones.",
    },

    # ── Alces: vida y habilidades ─────────────────────────────────────────
    {
        "claves": ["habilidad", "poderes", "cooldown", "recarga", "ataques del alce", "vida del alce",
                   "cuanta vida", "vida base"],
        "respuesta": "🫎 **Alce**: vida base **300**.\n"
                     "· **Golpe**: 35 de daño, se recarga en 24 s.\n"
                     "· **Empuje Fuerte**: manda a volar a un soldado, se recarga en 70 s.\n"
                     "Ojo: un Alce sin habilidades está en DESVENTAJA.",
    },
    {
        "claves": ["golpe"],
        "respuesta": "👊 **Golpe**: 35 de daño y se recarga en **24 s**. Con el Alce Aguz pega **70** "
                     "y se recarga en 19 s.",
    },
    {
        "claves": ["empuje fuerte", "empuje", "mandar a volar", "volar"],
        "respuesta": "🚀 El **Empuje Fuerte** manda a volar a un soldado y se recarga en **70 s**. "
                     "Úsalo para limpiar la zona de la bandera. De nada.",
    },
    {
        "claves": ["embestida", "embestir"],
        "respuesta": "💥 La **Embestida** es del **Alce Aguz**: 45 de daño, PEEERO si choca contra "
                     "algo se aturde y pierde vida. ¡Apunta bien!",
    },

    # ── Soldados ──────────────────────────────────────────────────────────
    {
        "claves": ["que clase", "mejor clase", "clase compro", "clase me compro", "clases",
                   "ranking de clases", "soldado", "clase de pago"],
        "respuesta": "Las clases de pago son el **Leñador** (1.550 monedas, 8,5/10) y el "
                     "**Disciplinado** (750 monedas, 7/10). Si vas corto, el **Fusilero** con "
                     "mosquete cumple. También existe el **Pesado**. De nada. 🫎",
    },
    {
        "claves": ["arma", "armas"],
        "respuesta": "🔫 Armas de los Soldados:\n"
                     "· **Mosquete**: 55 de daño, 20 s de recarga.\n"
                     "· **Navaja**: 35 de daño.\n"
                     "· **Linterna**: alumbra y descubre al Alce Sombra.",
    },
    {
        "claves": ["mosquete", "fusilero", "disparo"],
        "respuesta": "🎯 **Mosquete**: 55 de daño y 20 s de recarga. Ojo: el Alce Aguz recibe la "
                     "mitad de daño por disparo y el escudo del Alce Perú bloquea disparos.",
    },
    {
        "claves": ["navaja", "cuchillo"],
        "respuesta": "🔪 **Navaja**: 35 de daño. Corta distancia, así que ojo con el Golpe del Alce.",
    },
    {
        "claves": ["linterna"],
        "respuesta": "🔦 La **linterna** alumbra y descubre al **Alce Sombra**: lo encuentra en 3 s.",
    },
    {
        "claves": ["lenador", "jarabe"],
        "respuesta": "🪓 **Leñador — 8,5/10 · 1.550 monedas.** Clase de pago con muchos beneficios.",
    },
    {
        "claves": ["disciplinado"],
        "respuesta": "🎖️ **Disciplinado — 7/10 · 750 monedas.** La clase de pago más barata. Sí sirve.",
    },
    {
        "claves": ["pesado"],
        "respuesta": "🛡️ **Pesado**: existe, PEEERO sus datos nuevos no los tengo en mis apuntes. "
                     "Pregúntale a Aguz.",
    },
    {
        "claves": ["pyro", "lanzallamas"],
        "respuesta": "🔥 El **Pyro** no aparece en mis apuntes nuevos, así que no te puedo confirmar "
                     "si sigue en el juego. Pregúntale a Aguz, el creador.",
    },
    {
        "claves": ["medico", "botiquin", "curar", "curacion"],
        "respuesta": "🩹 **Médico**: cura **50 de vida** a quienes estén cerca, con **3 usos**. "
                     "Ideal cuando hay harta gente.",
    },
    {
        "claves": ["albanil", "trampa", "senuelo", "martillo", "paleta", "tecla f"],
        "respuesta": "🧱 **Albañil** (1 por equipo):\n"
                     "· **Trampas de oso**: clic con el martillo, máximo 4 por partida. Aturden 6 s, "
                     "los alces no las ven y cada una sirve una vez.\n"
                     "· **Señuelo**: tecla F, un soldado falso para engañar a los alces (máximo 4).\n"
                     "· **Paleta**: 35 de daño.",
    },

    # ── Skins de Alce ─────────────────────────────────────────────────────
    {
        "claves": ["que skin", "mejor skin", "skin compro", "skin me compro", "skins",
                   "ranking de skins"],
        "respuesta": "La mejor es el **Alce Aguz**: 10/10, cuesta 15.000 monedas. Caro, PEEERO vale "
                     "la pena 🔥.\nTambién están buenos el **Perú** (escudo contra disparos), el "
                     "**Magma** (quema) y el **Aurora** si juegas en el Ártico. El **Dorado** se "
                     "consigue con código. De nada. 🫎",
    },
    {
        "claves": ["alce aguz", "skin aguz", "skin del creador"],
        "respuesta": "👑 **Alce Aguz — 10/10 · 15.000 monedas.** Mitad de daño por disparo, Golpe de "
                     "**70 cada 19 s**, 10 % más rápido y **Embestida** de 45 de daño (si choca, se "
                     "aturde y pierde vida). Caro, PEEERO vale la pena.",
    },
    {
        "claves": ["calabaza", "calabomba", "disfraz"],
        "respuesta": "🎃 **Alce Calabaza**: ya no se vende. 150 de vida, Calabomba y Disfraz. "
                     "Si lo compraste, lo equipas en **Tienda › Extras**.",
    },
    {
        "claves": ["magma"],
        "respuesta": "🌋 **Alce Magma**: quema a los soldados que se le pegan. Quizás se parece a la "
                     "Mole de los 4 Fantásticos, pero es útil.",
    },
    {
        "claves": ["peru", "chullo", "escudo"],
        "respuesta": "🇵🇪 **Alce Perú**: recibe **30 % menos de daño** y su escudo **bloquea disparos**.",
    },
    {
        "claves": ["aurora", "teletransport", "artico"],
        "respuesta": "🌌 **Alce Aurora**: en el **Ártico** tiene **+140 de vida** y puede "
                     "teletransportarse. En los demás mapas no tiene esos poderes.",
    },
    {
        "claves": ["sombra", "invisible", "humo"],
        "respuesta": "🌑 **Alce Sombra**: se desvanece en humo, PEEERO una linterna lo descubre en **3 s**.",
    },
    {
        "claves": ["dorado", "estatua"],
        "respuesta": "🏅 **Alce Dorado**: solo se obtiene con un código. En mis apuntes tengo "
                     "**GOLDMOOSE**. De nada.",
    },

    # ── Extras ────────────────────────────────────────────────────────────
    {
        "claves": ["badge", "insignia", "itznotaguz", "secreto"],
        "respuesta": "🤫 El badge secreto **\"itzNotAguz\"** se consigue jugando una partida con el "
                     "creador. ¡A buscarlo, pillo!",
    },
]


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes (ñ -> n) y sin signos de puntuación."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _patron(clave: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(normalizar(clave)))


_INDICE = [
    (tema, [(_patron(c), len(normalizar(c).split())) for c in tema["claves"]])
    for tema in TEMAS
]


def responder(pregunta: str) -> str:
    """Devuelve la respuesta del Profesor Alce a una pregunta."""
    texto = normalizar(pregunta)
    puntajes: list[tuple[int, int, dict]] = []
    for orden, (tema, patrones) in enumerate(_INDICE):
        puntos = sum(peso for patron, peso in patrones if patron.search(texto))
        if puntos:
            puntajes.append((puntos, orden, tema))
    if not puntajes:
        return NO_SE

    principales = [p for p in puntajes if not p[2].get("solo_si_nada")] or puntajes
    principales.sort(key=lambda p: (-p[0], p[1]))
    mejor = principales[0][0]
    # Si preguntan por dos cosas a la vez ("¿Pyro o Leñador?"), responde ambas.
    elegidos = [tema for puntos, _, tema in principales if puntos == mejor][:2]
    return "\n\n".join(tema["respuesta"] for tema in elegidos)
