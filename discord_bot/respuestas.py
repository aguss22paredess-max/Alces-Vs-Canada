"""Respuestas del Profesor Alce para /ask, sin usar ninguna API.

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
    "Puedes preguntarme por clases, skins, AlceCoins, el código, mapas, "
    "habilidades o cómo ganar."
)

# solo_si_nada=True: el tema solo se usa si ningún otro coincide (saludos, insultos).
TEMAS: list[dict] = [
    # ── Conversación ──────────────────────────────────────────────────────
    {
        "claves": ["hola", "buenas", "holi", "que tal", "saludos", "wena"],
        "solo_si_nada": True,
        "respuesta": "¡Hola, pillo! 🫎 Soy el Profesor Alce. Pregúntame lo que quieras de "
                     "Alces vs Canadá: clases, skins, AlceCoins, mapas o cómo ganar.",
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
        "respuesta": "Soy el Profesor Alce, la mascota y sabio oficial de Alces vs Canadá 🫎. "
                     "Traje azul, corbata roja, lentes y mi libro bajo el brazo. "
                     "Salgo en los videos de AlceKnow.",
    },
    {
        "claves": ["creador", "aguz", "quien hizo", "quien creo", "dueno"],
        "respuesta": "El creador del juego es **Aguz**. Ojo: si juegas una partida con él "
                     "te ganas el badge secreto **\"itzNotAguz\"**. Y su skin, el Alce Aguz, "
                     "es un 10/10. 🫎",
    },
    {
        "claves": ["actualizacion", "update", "cuando sale", "evento", "proxima"],
        "respuesta": "Eso no lo tengo en mis apuntes, pregúntale a Aguz, el creador. 🫎 "
                     "Yo no prometo nada, pillo.",
    },

    # ── El juego ──────────────────────────────────────────────────────────
    {
        "claves": ["de que trata", "que es el juego", "como se juega", "como funciona",
                   "reglas", "equipos", "alces vs canada"],
        "respuesta": "Dos equipos: los **Alces** atacan y los **Soldados de Canadá** defienden ⚔️.\n"
                     "Los Alces tienen que capturar **3 banderas en orden** (50 s en cada zona). "
                     "La ronda dura **6 minutos**: si los Alces capturan las 3 ganan al tiro; "
                     "si se acaba el tiempo, ganan los Soldados.",
    },
    {
        "claves": ["bandera", "capturar", "ganar como alce", "gano como alce", "gano rapido como alce",
                   "objetivo", "zona"],
        "respuesta": "Ojo, pillo: la única forma de ganar como Alce es capturar las **3 banderas "
                     "en orden**, 50 s cada una. Y usa tus habilidades: el Empuje Fuerte saca a "
                     "los Soldados de la zona. Un Alce sin habilidades es un Alce perdedor. 🫎",
    },
    {
        "claves": ["ronda", "cuanto dura", "minutos", "ganar como soldado", "gano como soldado",
                   "ganan los soldados", "defender"],
        "respuesta": "Cada ronda dura **6 minutos** ⏱️. Si los Alces capturan las 3 banderas, "
                     "ganan al instante. Si se acaba el tiempo, ganan los Soldados. "
                     "Ojo, Soldados: su pega es aguantar hasta el final.",
    },
    {
        "claves": ["lobby", "preparacion", "cuenta regresiva", "cuando empieza", "puerta"],
        "respuesta": "En el **lobby**, cuando hay suficientes jugadores, parte una cuenta regresiva "
                     "de **10 s** y se elige un mapa al azar. Después vienen **60 s de preparación**: "
                     "los Soldados eligen clase y se preparan. Luego se abre la puerta y "
                     "¡los Alces atacan! 🫎",
    },
    {
        "claves": ["morir", "muero", "me matan", "reaparec", "respawn", "revivir"],
        "respuesta": "Al morir esperas **25 s** y reapareces en un punto de tu equipo con tu clase. "
                     "Aprovecha esos segundos para pensar tu siguiente jugada. 🫎",
    },
    {
        "claves": ["mapa", "mapas"],
        "respuesta": "Hay **7 mapas** 🗺️: Vancouver, Alaska, Ártico Canadiense, Toronto, "
                     "Terranova y Labrador, San Pedro y Miquelón y Tundra Canadiense. "
                     "Se elige uno al azar en cada partida.\n"
                     "Ojo: en el Ártico el Alce Aurora puede teletransportarse.",
    },

    # ── AlceCoins, tienda y código ────────────────────────────────────────
    {
        "claves": ["moneda", "alcecoin", "coins", "dinero", "plata", "ganar rapido", "farmear"],
        "respuesta": "💰 El equipo que gana la ronda recibe **+50 AlceCoins**. Mis tips:\n"
                     "· Error grave: no usar las habilidades. Un Alce sin habilidades está en DESVENTAJA.\n"
                     "· Error: no capturar banderas siendo Alce. ¡Es la ÚNICA forma de ganar como Alce!\n"
                     "Y usa el código **GOLDMOOSE**. De nada. 🫎",
    },
    {
        "claves": ["tienda", "shop", "donde compro", "como compro"],
        "respuesta": "La tienda está en el **botón de arriba a la derecha** 🛒. Tiene tres pestañas: "
                     "**Clases**, **Skins** y **Pases**. Ahí gastas tus AlceCoins.",
    },
    {
        "claves": ["pase", "pass", "gamepass"],
        "respuesta": "Los Pases están en la tienda, PEEERO todavía no tengo esos datos en mis "
                     "apuntes. Pregúntale a Aguz, el creador. 🫎",
    },
    {
        "claves": ["codigo", "code", "goldmoose", "canjear"],
        "respuesta": "El código activo es **GOLDMOOSE** 🏅: te da la skin **Alce Dorado**. De nada. 🫎",
    },

    # ── Habilidades del Alce ──────────────────────────────────────────────
    {
        "claves": ["habilidad", "poderes", "cooldown", "golpe", "empuje", "ataques del alce"],
        "respuesta": "Habilidades del Alce ⚔️:\n"
                     "· **Embestida** (tecla Q o botón en celular): carga, daña y empuja.\n"
                     "· **Golpe**: cooldown de 10 s.\n"
                     "· **Empuje**: cooldown de 8 s.\n"
                     "· **Empuje Fuerte**: cooldown de 40 s, manda a volar a los Soldados hasta 200 studs.\n"
                     "Ojo: un Alce sin habilidades está en desventaja.",
    },
    {
        "claves": ["embestida", "tecla q", "embestir"],
        "respuesta": "La **Embestida** se usa con la **tecla Q** (o el botón en celular): cargas hacia "
                     "adelante y dañas y empujas a los Soldados. 🫎💨",
    },
    {
        "claves": ["empuje fuerte", "mandar a volar", "volar"],
        "respuesta": "El **Empuje Fuerte** tiene cooldown de **40 s** y manda a volar a los Soldados "
                     "hasta **200 studs** 🚀. Ideal para limpiar la zona de la bandera. De nada.",
    },

    # ── Clases de Soldado ─────────────────────────────────────────────────
    {
        "claves": ["que clase", "mejor clase", "clase compro", "clase me compro", "clases",
                   "ranking de clases", "soldado"],
        "respuesta": "Si tienes con qué, **Pyro** sin pensarlo: 9,6/10 🔥. Si no, el **Leñador** "
                     "está buenísimo (8,5). PEEERO si vas corto de monedas, el **Fusilero** por "
                     "defecto cumple. De nada. 🫎",
    },
    {
        "claves": ["pyro", "lanzallamas"],
        "respuesta": "🔥 **Pyro — 9,6/10.** Lanzallamas (40 de daño instantáneo + 5 por segundo "
                     "durante 9 s), hacha y linterna. La mejor clase hasta ahora.",
    },
    {
        "claves": ["lenador", "jarabe"],
        "respuesta": "🪓 **Leñador — 8,5/10.** Hacha de mucho daño (algo de cooldown), jarabe de alce "
                     "de 3 usos (más velocidad y curación progresiva) y linterna. Muchos beneficios.",
    },
    {
        "claves": ["fusilero", "mosquete"],
        "respuesta": "🎯 **Fusilero — 7/10.** Por defecto, solo 4 cupos por partida. Mosquete, navaja "
                     "y linterna. Buena opción si no tienes dinero.",
    },
    {
        "claves": ["disciplinado"],
        "respuesta": "🎖️ **Disciplinado — 7/10.** De paga. Revólver y navaja, con más vida y más daño. "
                     "La peor clase de paga… aunque sí sirve.",
    },
    {
        "claves": ["pesado"],
        "respuesta": "🛡️ **Pesado — 6/10.** Revólver y navaja. Más lento, pero resiste más golpes y "
                     "empujes. Útil con un Fusilero de apoyo.",
    },
    {
        "claves": ["medico", "botiquin", "curar"],
        "respuesta": "🩹 **Médico — 5/10.** Gratis. Sable, botiquín de 3 usos (lo cura a él y a los "
                     "Soldados cercanos) y linterna. Tiene menos vida. Mejor cuando hay mucha gente.",
    },
    {
        "claves": ["albanil", "trampa", "senuelo", "martillo"],
        "respuesta": "🧱 **Albañil — 4/10.** Cuchara de albañil para apuñalar, martillo para crear un "
                     "señuelo (que, honestamente, no confunde a nadie), trampa de oso invisible que "
                     "aturde a los Alces, y linterna. Casi inútil si juegas solo.",
    },
    {
        "claves": ["linterna"],
        "respuesta": "Ojo: la **linterna** de los Soldados delata al **Alce Sombra**. Si lo alumbra "
                     "3 s, reaparece a la fuerza. 🔦",
    },

    # ── Skins de Alce ─────────────────────────────────────────────────────
    {
        "claves": ["que skin", "mejor skin", "skin compro", "skin me compro", "skins",
                   "ranking de skins"],
        "respuesta": "La mejor es el **Alce Aguz**: 10/10, cuesta 15.000. Caro, PEEERO vale la pena 🔥.\n"
                     "Si vas más corto, te recomiendo el **Alce Flaco** (8,1 · 1.200) o el "
                     "**Alce Magma** (7,8 · 1.800). Y gratis tienes el **Alce Dorado** con el código "
                     "GOLDMOOSE. De nada. 🫎",
    },
    {
        "claves": ["alce aguz", "skin aguz", "skin del creador"],
        "respuesta": "👑 **Alce Aguz — 10/10 · 15.000.** El diseño de la skin del creador. 50% menos "
                     "daño de disparos, 10% más de velocidad y su propia Embestida (si chocas con un "
                     "muro te aturdes; si chocas con un Soldado, golpe fuerte y empujón). "
                     "Caro, PEEERO vale la pena.",
    },
    {
        "claves": ["calabaza", "halloween", "calabomba"],
        "respuesta": "🎃 **Alce Calabaza — 8,9/10.** Edición Halloween, YA NO SE PUEDE CONSEGUIR. "
                     "Tenía Calabomba (30–65 de daño, recta o bombeada) y Disfraz, pero solo 150 de vida.",
    },
    {
        "claves": ["flaco"],
        "respuesta": "💨 **Alce Flaco — 8,1/10 · 1.200.** 35% más de velocidad, ideal para remontar "
                     "partidas. Recomendado por el Profesor. 🫎",
    },
    {
        "claves": ["magma"],
        "respuesta": "🌋 **Alce Magma — 7,8/10 · 1.800.** Quema con 5 de daño a los Soldados que se le "
                     "acercan. Quizás se parece a la Mole de los 4 Fantásticos, pero es útil. "
                     "Recomendado por el Profesor.",
    },
    {
        "claves": ["peru", "chullo"],
        "respuesta": "🇵🇪 **Alce Perú — 7,8/10 · 2.500.** Colores de Perú y chullo, con un escudo bajo "
                     "la barbilla. Recibe 30% menos daño de DISPAROS (ojo: no de cuchilladas ni otros golpes).",
    },
    {
        "claves": ["aurora", "teletransport"],
        "respuesta": "🌌 **Alce Aurora — 7/10 · 3.000.** Se teletransporta hasta 100 studs a su "
                     "alrededor, PEEERO solo en el mapa Ártico. En los demás es cosmética.",
    },
    {
        "claves": ["sombra", "invisible"],
        "respuesta": "🌑 **Alce Sombra — 6,5/10 · 1.500.** Invisible por 20 s, pero si una linterna lo "
                     "alumbra 3 s, reaparece a la fuerza.",
    },
    {
        "claves": ["diamante", "esmeralda"],
        "respuesta": "💎 **Alce Diamante y Alce Esmeralda — 5,5/10 · 2.000 c/u.** Solo cosméticas.",
    },
    {
        "claves": ["dorado", "estatua"],
        "respuesta": "🏅 **Alce Dorado — 5/10 · gratis** con el código **GOLDMOOSE**. Cosmética, pero "
                     "tiene estatua en el lobby y en los mapas. De nada.",
    },
    {
        "claves": ["platino"],
        "respuesta": "🪙 **Alce Platino — 4/10 · 500.** Cosmética. Ser bonita no la hace mejor.",
    },
    {
        "claves": ["por defecto", "default", "skin gratis", "marron", "ojos rojos"],
        "respuesta": "🟤 **Skin por defecto — sin nota · gratis.** Marrón con ojos rojos. Aburrida, "
                     "pero se salva por ser gratis.",
    },

    # ── Extras ────────────────────────────────────────────────────────────
    {
        "claves": ["badge", "insignia", "itznotaguz", "logro", "secreto"],
        "respuesta": "🤫 El badge secreto **\"itzNotAguz\"** se consigue jugando una partida con el "
                     "creador. ¡A buscarlo, pillo!",
    },
    {
        "claves": ["tiktok", "video", "alceknow", "redes"],
        "respuesta": "📱 El TikTok oficial es **@alces.vs.canada**. Ahí salen mis videos de AlceKnow. "
                     "¡Sígueme, pillo! 🫎",
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
