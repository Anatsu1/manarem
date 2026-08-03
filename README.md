# Manarem

Plataforma web para descubrir y recomendar animes, mangas y música relacionada.

## Stack

### Frontend
- **HTML5** + **CSS3** (Grid, Flexbox, custom properties)
- **JavaScript vanilla** (sin frameworks ni build step)

### Backend
- **Python 3** + **Flask** (API REST)
- **SQLite** (etapa actual; PostgreSQL previsto)
- **Werkzeug** (hash de contraseñas)

## Inicio rápido

### Frontend (etapa actual — funciona sin backend, con datos mock)

```bash
git clone <repo>
cd manarem_anime
python3 dev_server.py
```

Abre `http://localhost:8000`. El server replica las URLs limpias de Vercel (`/recomend`, `/foro`, etc.). Los datos salen de `frontend/static/js/mock-data.js`; para volver al backend real, poner `MOCK_MODE = false` en `frontend/static/js/api.js`.

### Backend (opcional en esta etapa)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Servidor en `http://localhost:5000`.

## Estructura

```
manarem_anime/
├── agents/                    # Planificación de tareas (local, gitignored)
├── frontend/
│   ├── index.html             # Home
│   ├── recomend.html          # Recomendaciones
│   ├── musica.html            # Música anime
│   ├── cuenta.html            # Login + registro (dos paneles, una página)
│   ├── perfil.html            # Perfil del usuario
│   ├── contacto.html          # Contacto
│   ├── opiniones.html         # Opiniones
│   ├── preg_frec.html         # FAQ
│   ├── acerca_de.html         # Acerca de
│   ├── foro.html              # Foro: listado de temas
│   ├── foro_tema.html         # Foro: tema con respuestas
│   ├── vercel.json            # Rutas Vercel
│   ├── static/css/            # Hojas de estilo (design system + por página)
│   ├── static/js/             # api.js, mock-data.js, components.js, app.js,
│   │                          # home.js, cuenta.js
│   ├── static/img/            # Imágenes
│   ├── static/video/          # ocean.mp4 (fondo del home)
│   └── assets/fonts/          # Alkatra + Fonstars
├── app.py                     # Backend Flask (foro + usuarios, SQLite)
├── dev_server.py              # Server local con URLs limpias
├── requirements.txt
├── README.md
└── .gitignore
```

## Páginas

| Ruta | Archivo |
|---|---|
| `/` | index.html |
| `/recomend` | recomend.html |
| `/musica` | musica.html |
| `/ingresar` | cuenta.html (abre en el panel de ingreso) |
| `/registrarse` | cuenta.html (abre en el panel de registro) |
| `/perfil` | perfil.html |
| `/contacto` | contacto.html |
| `/opiniones` | opiniones.html |
| `/preguntas-frecuentes` | preg_frec.html |
| `/acerca-de` | acerca_de.html |
| `/foro` | foro.html |
| `/foro/tema?id=N` | foro_tema.html |

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/registro` | Crear usuario (`nombre`, `usuario`, `email`, `password`) |
| POST | `/login` | Iniciar sesión (devuelve token y `usuario: {id, usuario, nombre, email}`) |
| GET | `/foro/temas` | Listar temas del foro |
| POST | `/foro/temas` | Crear tema (requiere token) |
| GET | `/foro/temas/<id>` | Tema con respuestas |
| POST | `/foro/temas/<id>/respuestas` | Responder (requiere token) |

El frontend funciona sin backend gracias a la capa mock (`MOCK_MODE` en `api.js`). El hero del home carga banners desde la API de AniList (fallback: Jikan, luego imágenes locales).

## Identidad visual

Paleta oscura con acentos púrpura y rosa neón.

| Variable | Valor | Uso |
|---|---|---|
| `--accent-color` | `#9e4c9e` | Botones, bordes, hover |
| `--letter-color` | `#ffbeff` | Texto principal |
| `--letter-hover` | `#60fdbc` | Hover links |
| `--header-bg` | `#15003d` | Header, footer |
| `--body-color` | `#0a1641` | Fondo de página |
| `--main-bg` | `#0d062c` | Cards, contenido |
| `--form-bg` | `#2c1a80` | Formularios, tablas |
| `--border-light` | `rgba(255,190,255,0.15)` | Bordes |
| `--shadow-color` | `rgba(0,0,0,0.3)` | Sombras |

**Fuentes:** Alkatra (cuerpo), Fonstars (títulos).
**Breakpoints:** 520px (mobile), 900px (tablet), 1200px (desktop).
**Patrones:** CSS Grid, sticky header, cards con hover lift, glassmorphism.

### Reglas de identidad visual

Salieron de iteraciones concretas y **conviene respetarlas al rediseñar cada página**:

1. **El mar es la identidad; el arte de los animes es contenido.** No compiten. El video de fondo (`ocean.mp4`, estampa de la gran ola) va **solo en el home**, donde el hero lo muestra entero. Ninguna otra página lo carga: antes estaba en las doce, tapado por un panel oscuro, y era la razón de que todas se parecieran. Las portadas de animes no se usan de decoración.
2. **Un solo oscurecido por página, nunca uno por sección.** Cada capa tiene bordes, y sobre un fondo continuo los bordes se ven como líneas y recuadros. El home usa una única capa sobre `main` que va de transparente a opaca de arriba abajo.
3. **El contraste vive en las letras, no en manchas de fondo.** Los títulos llevan degradado animado con `background-clip: text` y resplandor; el cuerpo, una sombra ceñida al texto. Nada de rectángulos oscuros sobre la imagen.
4. **Ojo con `background-clip: text`**: con `color: transparent`, un `text-shadow` se dibuja detrás y aparece como silueta sólida. Para el resplandor va `filter: drop-shadow()`.
5. **Fonstars no soporta tildes.** Todo lo que se muestre con `--font-display` va sin acentos; el cuerpo (Alkatra) sí las lleva. El contenido dinámico pasa por `sinAcentos()`.
6. **El video de fondo arranca debajo del header**, que es opaco. Con un header traslúcido se veía el mar por detrás y quedaba una costura en su borde.

## Estado del proyecto y roadmap

### Hecho (julio 2026)

- ✅ **Rediseño visual v2** completo: design system con tokens CSS, header/footer inyectados por `components.js`, glassmorphism, cards con glow, responsive 520/900/1200.
- ✅ **Frontend standalone**: capa de mocks (`MOCK_MODE` en `api.js`) — todo funciona sin backend, listo para Vercel.
- ✅ **Home dinámico**: hero carrousel (mín. 75vh) y destacados alimentados por la **API de AniList** (fallback Jikan → imágenes locales), más los 3 temas con más respuestas del foro.
- ✅ **Foro con usuarios** (reemplazó al CRUD de productos): backend Flask + SQLite con registro, login (hash + token de sesión), temas por categoría y respuestas. Mocks con contrato idéntico.
- ✅ **Cuentas y comunidad fase 2**: backend real de **contacto** y **opiniones** (persistidos en SQLite), **logout** (invalida el token) y **perfil** (`/perfil` con datos y temas del usuario). Login obligatorio para opinar. Mocks con el mismo contrato.
- ✅ **Fondo animado** (video del mar) en todas las páginas, con panel central oscuro que lo deja ver solo por los costados; hero con carrousel de destacados, efecto sobre el texto y separación con sombra.
- ✅ Logo SVG propio con la tipografía del sitio (Fonstars), fuentes display sin acentos, `dev_server.py` con URLs limpias.

### Hecho (agosto 2026) — rediseño v3

- ✅ **Home rediseñado**. El hero pasó a ser tipográfico sobre el mar abierto: se ven la ola, el Fuji y los botes, sin recuadros de arte encima. Antes el carrousel se veía quemado por tres causas sumadas — dos imágenes superpuestas en cada cruce, un overlay que arrancaba en 0.92 de opacidad, y banners panorámicos estirados a 80vh.
- ✅ **Ritmo de secciones**: destacado principal ancho + grilla, foro en columna angosta, glosario en tres columnas y cierre nuevo. Ninguna repite el patrón de otra.
- ✅ **Fondo con una sola capa continua**, que eliminó las líneas y recuadros entre secciones.
- ✅ **`ocean.mp4` en bucle real**: rehecho en ping-pong con ffmpeg, cierra sin salto. Pasó de 8s a 16s casi al mismo peso (2,24 MB).
- ✅ **Cuenta unificada**: `/ingresar` y `/registrarse` son la misma página con dos paneles conmutables. El campo Nombre ahora se guarda de verdad (migración idempotente de `usuarios`) y viaja en registro, login y perfil. Se cayeron la foto de perfil, que no se enviaba a ningún lado, y el checkbox de términos.
- ✅ **Header con una sola entrada** ("Iniciar sesión"); "Salir" aparece solo con sesión iniciada.
- ✅ **Seguridad**: los datos de AniList dejaron de interpolarse sin escapar en `home.js`. Se agregaron `escaparHtml()` y `urlSegura()` (solo `http`/`https`, así una `javascript:` URI no llega a un `href`).
- ✅ **Accesibilidad**: volvió el anillo de foco en los formularios (había un `outline: none`).

### Próximos pasos

**Rediseño de páginas interiores**, en este orden:

- [ ] **Foro** (`/foro` y `/foro/tema`). Es la de más contenido real y la única con dos vistas; fija el patrón de "página con listado" que después reusan las demás.
- [ ] **Perfil**. Ahí aterriza el `nombre` que ya se guarda: hoy `GET /perfil` lo devuelve pero la página sigue mostrando solo el usuario.
- [ ] **Contenido en tanda**: recomendados, música y opiniones, que comparten la grilla de cards.
- [ ] **Estáticas**: acerca de, contacto y preguntas frecuentes.

**Backend** (pendiente, se hace después del frontend):

- [ ] **Foro fase 2 (resto)**: editar/borrar temas y respuestas propios, paginación, expiración de sesiones.
- [ ] **Perfiles**: avatar propio (hoy hay uno por defecto), edición de datos.
- [ ] **Deploy**: frontend a Vercel (modo mock) y backend a PythonAnywhere; apuntar `API_BASE` a la URL de producción y `MOCK_MODE = false`.
- [ ] **A evaluar**: migración a PostgreSQL, búsqueda de animes vía AniList en `/recomend`, moderación del foro, rate limiting en la API, tests automatizados del backend.

**Deuda conocida**:

- [ ] Los términos y condiciones ya no se aceptan en ningún lado (se sacó la casilla). Si alguna vez importa, la salida sin casilla es una frase bajo el botón.
- [ ] `perfil.html` no muestra el `nombre` que ya devuelve la API.

## Autores

- [Cesar Augusto Fernandez Carbonell](https://github.com/Anatsu1)
- [John CV](https://github.com/Jodenly9)
- [Monica Quiroz](https://github.com/Quiroz-Monica-R)

## Licencia

© 2024 Manarem. Todos los derechos reservados.
