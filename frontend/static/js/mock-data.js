// Datos simulados. Solo se usan cuando CONFIG.mockMode (api.js) esta en true
// o el visitante entro con ?mock=1. Con la API real conectada no se tocan.
const MOCK_DB = {
    opiniones: [
        { id: 1, nombre: 'Maria Lopez', avatar: 'persona1-f.jpg', texto: 'Encontre mi proxima serie para maratonear en dos minutos. Las recomendaciones estan muy bien curadas.', fecha: '2025-03-15' },
        { id: 2, nombre: 'Ana Garcia', avatar: 'persona2-f.jpg', texto: 'Me copa que junten el anime con su musica. Cai por un opening y termine escuchando todo el disco.', fecha: '2025-04-02' },
        { id: 3, nombre: 'Carlos Perez', avatar: 'persona3-m.jpg', texto: 'El foro esta buenisimo para debatir teorias. La comunidad responde rapido y con onda.', fecha: '2025-05-20' },
        { id: 4, nombre: 'Lucia Martinez', avatar: 'persona4-f.jpg', texto: 'La pagina es facil de navegar y los enlaces a donde ver cada anime van directo. Muy completa.', fecha: '2025-06-10' },
    ],
    temas: [
        {
            id: 1, titulo: 'Recomendaciones de temporada', categoria: 'anime', autor: 'Maria Lopez', fecha: '2026-07-01',
            contenido: 'Esta temporada de primavera trajo animes increibles. Mi favorito hasta ahora es Oshi no Ko segunda temporada. Que estan viendo ustedes?',
            respuestas: [
                { id: 101, autor: 'Ana Garcia', fecha: '2026-07-02', contenido: 'Totalmente de acuerdo, Oshi no Ko es una locura. Tambien recomiendo Kaiju No. 8.' },
                { id: 102, autor: 'Carlos Perez', fecha: '2026-07-03', contenido: 'Yo estoy viendo Wind Breaker y me esta gustando mucho mas de lo que esperaba.' },
            ],
        },
        {
            id: 2, titulo: 'Debate manga vs anime', categoria: 'manga', autor: 'Ana Garcia', fecha: '2026-07-05',
            contenido: 'Creen que el anime realmente captura la esencia del manga original? A veces siento que los estudios se toman demasiadas libertades.',
            respuestas: [
                { id: 103, autor: 'Lucia Martinez', fecha: '2026-07-06', contenido: 'Depende del estudio. Ufotable y Kyoto Animation hacen un trabajo increible respetando el material original.' },
            ],
        },
        {
            id: 3, titulo: 'Mejores openings del momento', categoria: 'musica', autor: 'Carlos Perez', fecha: '2026-07-08',
            contenido: 'Quiero armar una playlist con los mejores openings de esta temporada. Cuales son sus favoritos?',
            respuestas: [
                { id: 104, autor: 'Maria Lopez', fecha: '2026-07-09', contenido: 'El opening de Jujutsu Kaisen es GOD. La cancion de King Gnu es perfecta.' },
                { id: 105, autor: 'Lucia Martinez', fecha: '2026-07-10', contenido: 'Mi favorito es el opening de Frieren. La instrumental me hace llorar cada vez.' },
                { id: 106, autor: 'Ana Garcia', fecha: '2026-07-11', contenido: 'No puedo creer que nadie mencione el opening de Spy x Family. Es demasiado pegadizo.' },
            ],
        },
        {
            id: 4, titulo: 'Presentaciones de la comunidad', categoria: 'general', autor: 'Lucia Martinez', fecha: '2026-07-12',
            contenido: 'Bienvenidos al foro! Cuentennos desde cuando son fans del anime y cual fue su primer anime.',
            respuestas: [
                { id: 107, autor: 'Carlos Perez', fecha: '2026-07-13', contenido: 'Mi primer anime fue Dragon Ball Z alla por los 90s. Desde ahi no pare.' },
            ],
        },
    ],
};
