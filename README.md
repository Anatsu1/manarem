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
├── agents/                    # Planificación de tareas (local)
├── frontend/
│   ├── index.html             # Home
│   ├── recomend.html          # Recomendaciones
│   ├── musica.html            # Música anime
│   ├── registrarse.html       # Registro
│   ├── ingresar.html          # Login
│   ├── contacto.html          # Contacto
│   ├── opiniones.html         # Opiniones
│   ├── preg_frec.html         # FAQ
│   ├── acerca_de.html         # Acerca de
│   ├── foro.html              # Foro: listado de temas
│   ├── foro_tema.html         # Foro: tema con respuestas
│   ├── vercel.json            # Rutas Vercel
│   ├── static/css/            # Hojas de estilo (design system + por página)
│   ├── static/js/             # api.js, mock-data.js, components.js, app.js, hero.js
│   ├── static/img/            # Imágenes
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
| `/ingresar` | ingresar.html |
| `/registrarse` | registrarse.html |
| `/contacto` | contacto.html |
| `/opiniones` | opiniones.html |
| `/preguntas-frecuentes` | preg_frec.html |
| `/acerca-de` | acerca_de.html |
| `/foro` | foro.html |
| `/foro/tema?id=N` | foro_tema.html |

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/registro` | Crear usuario |
| POST | `/login` | Iniciar sesión (devuelve token) |
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
**Patrones:** CSS Grid, sticky header, cards con hover lift, glassmorphism, hero animado con keyframes.

## Estado del proyecto y roadmap

### Hecho (julio 2026)

- ✅ **Rediseño visual v2** completo: design system con tokens CSS, header/footer inyectados por `components.js`, glassmorphism, cards con glow, responsive 520/900/1200.
- ✅ **Frontend standalone**: capa de mocks (`MOCK_MODE` en `api.js`) — todo funciona sin backend, listo para Vercel.
- ✅ **Home dinámico**: hero carrousel (mín. 75vh) y destacados alimentados por la **API de AniList** (fallback Jikan → imágenes locales), más los 3 temas con más respuestas del foro.
- ✅ **Foro con usuarios** (reemplazó al CRUD de productos): backend Flask + SQLite con registro, login (hash + token de sesión), temas por categoría y respuestas. Mocks con contrato idéntico.
- ✅ **Cuentas y comunidad fase 2**: backend real de **contacto** y **opiniones** (persistidos en SQLite), **logout** (invalida el token) y **perfil** (`/perfil` con datos y temas del usuario). Login obligatorio para opinar. Mocks con el mismo contrato.
- ✅ **Fondo animado** (video del mar) en todas las páginas, con panel central oscuro que lo deja ver solo por los costados; hero con carrousel de destacados, efecto sobre el texto y separación con sombra.
- ✅ Logo SVG propio con la tipografía del sitio (Fonstars), fuentes display sin acentos, `dev_server.py` con URLs limpias.

### Próximos pasos

- [ ] **Deploy**: frontend a Vercel (modo mock) y backend a PythonAnywhere; apuntar `API_BASE` a la URL de producción y `MOCK_MODE = false`.
- [ ] **Foro fase 2 (resto)**: editar/borrar temas y respuestas propios, paginación, expiración de sesiones.
- [ ] **Perfiles**: avatar propio (hoy hay uno por defecto), edición de datos.
- [ ] **A evaluar**: migración a PostgreSQL, búsqueda de animes vía AniList en `/recomend`, moderación del foro, rate limiting en la API, tests automatizados del backend.

## Autores

- [Cesar Augusto Fernandez Carbonell](https://github.com/Anatsu1)
- [John CV](https://github.com/Jodenly9)
- [Monica Quiroz](https://github.com/Quiroz-Monica-R)

## Licencia

© 2024 Manarem. Todos los derechos reservados.
