// ==========================================================================
// ALCES VS CANADÁ · TODO LO QUE SE EDITA DEL SITIO ESTÁ ACÁ
// Cambia este archivo y súbelo de nuevo. No hace falta tocar index.html.
// ==========================================================================

const SITIO = {
  juego: "https://www.roblox.com/games/75124408421132",

  // ---- REDES: pega cada enlace entre las comillas.
  // Si queda vacío, la tarjeta muestra "En camino".
  redes: [
    { nombre: "Discord", url: "https://discord.gg/CcngQs3Zr", texto: "El servidor oficial: partidas, avisos y reportes de errores.", principal: true },
    { nombre: "TikTok", url: "https://www.tiktok.com/@alces.vs.canada", texto: "Clips, tips y videos del Alce Profesor." },
    { nombre: "Roblox", url: "https://www.roblox.com/games/75124408421132", texto: "La página del juego: dale me gusta y agrégalo a favoritos." },
    { nombre: "YouTube", url: "", texto: "Tráilers y explicaciones en 3D." },
    { nombre: "Reddit", url: "", texto: "Ideas, debates y memes de la comunidad." },
    { nombre: "Grupo de Roblox", url: "", texto: "Únete al grupo oficial del juego." },
  ],

  // ---- ACTUALIZACIONES: la más nueva va primero.
  actualizaciones: [
    {
      fecha: "Noviembre 2026",
      titulo: "Ahora también defiendes contra los bots",
      cambios: [
        "Modo práctica como Soldado: tú defiendes las banderas y los alces son bots.",
        "Nuevo nivel Imposible: 6 bots que no perdonan un error.",
        "Los niveles Difícil, Medio y Fácil contra alces bot ahora son más justos.",
        "Los alces ven todo el mapa claro y el tono rojo casi no se nota.",
        "Sonidos nuevos para golpes, habilidades, portón y captura de banderas.",
        "Alces remodelados y menús más limpios.",
        "La Tienda estrena la sección Extras: el Alce Calabaza deja de venderse y quien lo compró lo sigue usando.",
        "Corregido: la pantalla de reaparición ya no se queda pegada al terminar la ronda.",
      ],
    },
    {
      fecha: "22 de octubre de 2026",
      titulo: "Bots con linterna",
      cambios: [
        "Los soldados bot ahora caminan y corren con animación propia.",
        "Sacan la linterna cuando te pierden de vista y pueden descubrir al Alce Sombra.",
      ],
    },
    {
      fecha: "20 de octubre de 2026",
      titulo: "Práctica por niveles y escenas de victoria",
      cambios: [
        "Modo práctica con niveles: Fácil, Medio, Difícil y Pacífico.",
        "Bots más listos: se coordinan, flanquean y defienden la bandera.",
        "Escena final con el MVP cuando termina la ronda.",
        "Nuevo Alce Calabaza, con Calabomba y disfraz.",
      ],
    },
    {
      fecha: "18 de octubre de 2026",
      titulo: "Alce Aguz y premios diarios",
      cambios: [
        "Nuevo Alce Aguz: aguanta la mitad de los disparos y embiste como un búfalo.",
        "Premio diario por racha, de 50 a 500 monedas.",
        "Invita amigos: tú ganas 150 monedas y tu amigo recibe 100 de bienvenida.",
      ],
    },
  ],

  // ---- LEAKS. estado: "listo" (terminado, sin publicar) o "estudio" (idea sin fecha).
  // imagen es opcional. Cuando algo se publique, muévelo a actualizaciones.
  leaks: [
    {
      codigo: "AVC-01",
      estado: "listo",
      titulo: "Partida Rápida",
      texto: "Un toque y a jugar: mapa y bando al azar, en nivel Medio. Sin pasar por tres menús.",
      imagen: "recursos/leak_rapida.jpg",
      alt: "Botones Partida Rápida y Esperar jugadores en el menú de práctica",
    },
    {
      codigo: "AVC-02",
      estado: "listo",
      titulo: "Reto del día",
      texto: "Cada día, una misma combinación de mapa, bando y nivel para todos. En la captura: Ontario como Soldado en Imposible.",
      imagen: "recursos/leak_reto.jpg",
      alt: "Tarjeta Reto del día en el menú de práctica",
    },
    {
      codigo: "AVC-03",
      estado: "estudio",
      titulo: "Premio por unirte al grupo",
      texto: "Se está evaluando una recompensa para quienes se unan al grupo del juego. Todavía no hay fecha ni monto.",
    },
  ],
};
