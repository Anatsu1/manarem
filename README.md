# Manarem

Plataforma web para descubrir y recomendar animes, mangas y música relacionada.

## Stack

### Frontend
- **HTML5** + **CSS3** (Grid, Flexbox, custom properties)
- **JavaScript vanilla** (sin frameworks ni build step)

### Backend
- **Python 3** + **Flask** (API REST)
- **PostgreSQL** — en producción; SQLite queda como modo local sin instalar nada
- **Werkzeug** (hash de contraseñas)
- **gunicorn** en un contenedor, detrás de Traefik

## Inicio rápido

```bash
git clone <repo>
cd manarem_anime

python -m venv venv
source venv/bin/activate
pip install -r requirements-postgres.txt

createdb manarem
MANAREM_DATABASE_URL=postgresql:///manarem python app.py   # API en :5000
python3 dev_server.py                                      # sitio en :8000
```

`dev_server.py` replica las URLs limpias de Vercel (`/recomend`, `/foro`, etc.).
Servido desde `localhost`, el frontend le pega a la API local.

### Sin instalar PostgreSQL

Sin `MANAREM_DATABASE_URL` la API corre sobre **SQLite**, que viene con Python:

```bash
pip install -r requirements.txt
python app.py
```

Es el mismo esquema y el mismo contrato — las respuestas se verifican idénticas
motor contra motor. Sirve para clonar y arrancar sin preparar nada; producción
corre sobre Postgres.

### Sin backend

Cualquier página acepta `?mock=1`: el sitio pasa a los datos simulados de
`frontend/static/js/mock-data.js` y sigue navegable entero. `?mock=0` lo apaga.
Sirve para mostrar el sitio aunque la API esté caída.

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
├── deploy/                    # systemd, nginx, Caddy y la guia de despliegue
│   ├── README.md              # Como sale a produccion (y por que Vercel no
│   │                          # necesita variables de entorno)
│   ├── manarem-api.service
│   ├── nginx-manarem.conf
│   └── Caddyfile
├── app.py                     # API Flask: auth, foro, opiniones, contacto
├── db.py                      # Capa de datos: SQLite o PostgreSQL
├── wsgi.py                    # Entrada para gunicorn
├── dev_server.py              # Server local con URLs limpias
├── .env.example               # Todas las variables de entorno, comentadas
├── requirements.txt
├── requirements-postgres.txt
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

Base local: `http://localhost:5000`. Todas las respuestas son JSON, también los
errores.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/salud` | Estado y contadores del sitio |
| POST | `/registro` | Crear usuario (`nombre`, `usuario`, `email`, `password`) |
| POST | `/login` | Iniciar sesión → `token` y `usuario: {id, usuario, nombre, email}` |
| POST | `/logout` | Cerrar sesión (invalida el token) |
| GET | `/perfil` | Datos, contadores y temas propios (requiere token) |
| GET | `/foro/temas` | Listar temas (`?limite=&desde=`) |
| POST | `/foro/temas` | Crear tema (requiere token) |
| GET | `/foro/temas/<id>` | Tema con sus respuestas |
| POST | `/foro/temas/<id>/respuestas` | Responder (requiere token) |
| GET | `/opiniones` | Listar opiniones |
| POST | `/opiniones` | Dejar una opinión (requiere token) |
| POST | `/contacto` | Enviar un mensaje de contacto |

El token va en `Authorization: Bearer <token>` y sale de `localStorage.user`.
Categorías del foro: `anime`, `manga`, `musica`, `general`.

**A qué API le pega el frontend** se decide en un solo lugar, `CONFIG` arriba de
`frontend/static/js/api.js`. Con `apiBase` vacío el sitio usa los datos
simulados, así que la demo nunca queda rota mientras el backend no esté online.
La capa mock devuelve exactamente las mismas formas que el backend real.

El hero del home carga banners desde la API de AniList (fallback: Jikan, y
después imágenes locales).

### Límites y cupos

La API está pensada para un sitio de prueba en un VPS chico, así que trae topes
puestos: 16 KB por pedido, largos máximos por campo, rate limiting por IP
(altas, login, escrituras y un techo global), cupos globales de cuentas, temas,
respuestas y opiniones, sesiones que vencen a los 7 días, y hash de contraseñas
con pbkdf2 en vez del scrypt por defecto de Werkzeug, que reserva 32 MB de RAM
por hash. Todo se ajusta con variables de entorno: ver `.env.example`.

## Despliegue

**En producción**: el sitio está en `manarem.vercel.app` y la API en
`manarem-api.augustofc.com`, como contenedor detrás de Traefik en un VPS, sobre
el PostgreSQL que ya corría ahí.

```
navegador ──► manarem.vercel.app          (estático, Vercel)
                  │  /api/*  (rewrite de vercel.json)
                  ▼
              Cloudflare ──► Traefik ──► manarem-api ──► postgres
```

Cada push a `master` que toque la API dispara un build ARM64 en Actions que
publica la imagen en `ghcr.io/anatsu1/manarem-api`.

**Vercel no necesita ninguna variable de entorno**: el sitio es estático y sin
build step, así que nada de lo que se configure ahí llega al navegador. A qué
API le pega se decide en `frontend/static/js/api.js` y `frontend/vercel.json`.

Todo lo demás —el pipeline, la base, cómo se determina la IP del visitante y qué
queda abierto— está en [`deploy/README.md`](deploy/README.md).

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

### Hecho (agosto 2026) — API en producción

- ✅ **La API está online** en `manarem-api.augustofc.com`, como contenedor
  detrás de Traefik, con su propio rol y base en el PostgreSQL del VPS. El
  frontend de Vercel le pega por el proxy `/api`, así que los pedidos salen al
  mismo origen: sin CORS y sin contenido mixto.
- ✅ **Pipeline igual al del portafolio**: push a `master` → build ARM64 con
  QEMU → `ghcr.io/anatsu1/manarem-api` → `docker compose pull` en el VPS.
- ✅ **Se cerró un agujero de rate limiting** que sólo apareció al desplegar.
  Traefik reescribe `X-Forwarded-For` porque Cloudflare no está en sus
  `trustedIPs`, así que la API veía su propia IP interna en todos los pedidos y
  el límite por IP era uno solo compartido. Se pasó a `CF-Connecting-IP`, pero
  creerle sin condiciones era peor: pegándole directo al VPS, salteando
  Cloudflare, se podía declarar cualquier IP y estrenar un cupo por pedido.
  Ahora se exige que el pedido venga de Traefik **y** que quien le habló a
  Traefik sea un edge de Cloudflare. Verificado en los dos sentidos.

### Hecho (agosto 2026) — API conectada

- ✅ **La API pasó de prototipo a servicio**. Ahora responde JSON también en los
  errores, valida y acota cada campo, tiene rate limiting por IP, cupos
  globales, sesiones que vencen, cabeceras de seguridad y un `/salud`.
- ✅ **Dos motores, una API**: SQLite por defecto (se clona y arranca sin
  instalar nada) o PostgreSQL con `MANAREM_DATABASE_URL`, con pool de
  conexiones. El esquema y la migración de `nombre` funcionan en los dos, y las
  respuestas se verificaron idénticas motor contra motor.
- ✅ **Frontend conectado de verdad**: `CONFIG` en `api.js` decide a qué API se
  le pega, con caída a datos simulados cuando no hay backend publicado y un
  `?mock=1` de emergencia. `apiRequest` ya no explota con un 500 ni con un HTML
  de error: todo sale como `{ error }`.
- ✅ **Se cerró un XSS almacenado.** El foro, el detalle de tema y las opiniones
  interpolaban texto de usuario sin escapar. Con datos mock no se notaba; con
  registro abierto, cualquiera publicaba un `<img onerror>` y se ejecutaba en el
  navegador de todos. `escaparHtml()` y `sinAcentos()` subieron a `app.js` para
  que las tenga todo el sitio.
- ✅ **El perfil muestra el nombre** que la API ya devolvía (deuda saldada).
- ✅ **Despliegue documentado**: `deploy/` con systemd, nginx, Caddy y la guía.

### Próximos pasos

**Rediseño de páginas interiores**, en este orden:

- [ ] **Foro** (`/foro` y `/foro/tema`). Es la de más contenido real y la única
  con dos vistas; fija el patrón de "página con listado" que después reusan las
  demás.
- [ ] **Perfil**.
- [ ] **Contenido en tanda**: recomendados, música y opiniones, que comparten la
  grilla de cards.
- [ ] **Estáticas**: acerca de, contacto y preguntas frecuentes.

**Backend**:

- [ ] **Cargar los secrets del VPS** (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`) en
  el repo, para que el último paso del deploy deje de ser manual.
- [ ] **Foro fase 2 (resto)**: editar y borrar temas y respuestas propios,
  moderación.
- [ ] **Perfiles**: avatar propio (hoy hay uno por defecto), edición de datos.
- [ ] **A evaluar**: búsqueda de animes vía AniList en `/recomend`, tests
  automatizados del backend, CSP en el frontend (pide sacar los `<script>` y
  estilos inline primero).

**Deuda conocida**:

- [ ] Los términos y condiciones ya no se aceptan en ningún lado (se sacó la
  casilla). Si alguna vez importa, la salida sin casilla es una frase bajo el
  botón.
- [ ] El rate limiting vive en la memoria del proceso: con varios workers cada
  uno lleva su cuenta. Un límite compartido de verdad necesitaría Redis.

## Autores

- [Cesar Augusto Fernandez Carbonell](https://github.com/Anatsu1)
- [John CV](https://github.com/Jodenly9)
- [Monica Quiroz](https://github.com/Quiroz-Monica-R)

## Licencia

© 2024 Manarem. Todos los derechos reservados.
