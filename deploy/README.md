# Despliegue de Manarem

Frontend estático en Vercel + API Flask en el VPS, como un contenedor detrás de
Traefik, siguiendo el mismo flujo que el portafolio y el backend de la UTN.

```
navegador ──► manarem.vercel.app          (estático, Vercel)
                  │  /api/*  (rewrite de vercel.json)
                  ▼
              Cloudflare ──► Traefik ──► manarem-api ──► postgres
                                         (contenedor)    (contenedor)
```

---

## En Vercel no hay ninguna variable de entorno que configurar

El frontend es HTML, CSS y JS servidos tal cual, **sin build step**. Vercel solo
inyecta variables durante un build, y acá no hay build: nada de lo que se ponga
en *Settings → Environment Variables* llega al navegador.

La configuración vive en dos archivos del repo y se aplica con un push:

| Archivo | Qué se toca |
|---|---|
| `frontend/static/js/api.js` | `CONFIG.apiBase` — a qué API le pega el sitio |
| `frontend/vercel.json` | el destino del proxy `/api/:ruta*` |

Con `apiBase` vacío el sitio cae a los datos simulados de `mock-data.js`. Es el
estado seguro: se puede pushear sin romper la demo.

---

## El pipeline

`.github/workflows/deploy.yml`, en cada push a `master` que toque la API:

1. **Build ARM64 con QEMU.** El VPS es aarch64 y los runners de GitHub son
   amd64; sin QEMU la imagen sale para la arquitectura equivocada y el `pull`
   falla en el servidor.
2. **Push a `ghcr.io/anatsu1/manarem-api`**, con tag `latest` y con el SHA.
3. **SSH al VPS**: `docker compose pull && docker compose up -d` en
   `/srv/infrastructure/manarem`.

El paso 3 se saltea solo si faltan los secrets, así el build no queda en rojo
por eso. Para que el deploy sea automático hacen falta tres secrets en el repo
(*Settings → Secrets and variables → Actions*), los mismos que ya usa el
portafolio: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

---

## Lo que hay en el servidor

`/srv/infrastructure/manarem/` con tres archivos:

- `docker-compose.yml` — el servicio y las labels de Traefik.
- `.env` — configuración y credenciales (modo 600, fuera de git).
- `.pgpass-manarem` — la contraseña de Postgres, generada en el propio servidor.

La ruta la publica Traefik, que ya tiene un certificado wildcard para
`*.augustofc.com` por DNS challenge de Cloudflare: el subdominio nuevo toma
HTTPS solo, sin emitir nada aparte.

```yaml
- "traefik.http.routers.manarem-api.rule=Host(`manarem-api.augustofc.com`)"
- "traefik.http.routers.manarem-api.entrypoints=websecure"
- "traefik.http.services.manarem-api.loadbalancer.server.port=5000"
```

**No se publica ningún puerto al host.** El contenedor solo es alcanzable por la
red interna `server-ubuntu-network`, y el único que le habla es Traefik.

### La base

Un rol y una base propios en el Postgres que ya corre en el VPS, igual que
`utn_project` y `n8n`. La conexión va por la red de docker
(`postgres:5432`), nunca por internet.

El pool es de 3 conexiones por worker y hay 2 workers: 6 conexiones sobre las
100 que tiene el motor. Vale tenerlo en cuenta al sumar servicios.

Si alguna vez hay que recrear la base:

```bash
docker exec postgres psql -U admin -d postgres -c "CREATE USER manarem WITH PASSWORD '<clave>'"
docker exec postgres psql -U admin -d postgres -c "CREATE DATABASE manarem OWNER manarem"
```

Las tablas se crean solas al arrancar el contenedor.

---

## Verificar

```bash
curl -s https://manarem-api.augustofc.com/salud
curl -s https://manarem-api.augustofc.com/salud/ip
curl -s https://manarem.vercel.app/api/salud     # a traves del proxy de Vercel
```

`/salud/ip` importa: el campo `ip` tiene que ser **la IP del visitante**, no la
de Cloudflare ni la de Traefik. Si no lo es, `MANAREM_PROXY_SALTOS` está mal y
el límite por IP se convierte en un límite compartido que echa a todos juntos.
ProxyFix toma el valor N-ésimo desde la derecha de `X-Forwarded-For`, y acá la
cadena es cliente → Cloudflare → Traefik, o sea **2**.

Diagnóstico rápido:

```bash
ssh servidor 'cd /srv/infrastructure/manarem && docker compose logs --tail 50'
ssh servidor 'docker ps --filter name=manarem-api'
```

Si algo se cae, `?mock=1` en cualquier página del sitio vuelve a los datos
simulados sin tocar código, y `?mock=0` lo desactiva.

---

## Qué trae puesto para no cargar el servidor

| Qué | Cómo |
|---|---|
| Cuerpo del pedido | 16 KB; más arriba responde 413 |
| Largo de cada campo | título 120, tema 4000, respuesta 2000, opinión 600 |
| Techo global por IP | 300 pedidos por minuto |
| Altas de cuenta | 5 por hora por IP, contando solo las que se concretan |
| Login | 10 intentos cada 5 minutos por IP |
| Temas | 10 por hora por IP; respuestas 30 por hora |
| Contacto | 5 por hora por IP |
| Cupos del sitio | 200 cuentas, 500 temas, 200 respuestas por tema, 300 opiniones |
| Listados | 50 temas por página, tope 100; opiniones tope 100 |
| Sesiones | vencen a los 7 días, 5 activas por usuario |
| Hash de contraseña | pbkdf2 en vez del scrypt por defecto de Werkzeug, que reserva **32 MB de RAM por hash** |
| Contenedor | `no-new-privileges`, corre como `nobody`, sin puertos al host |
| Consultas | siempre parametrizadas; índices en las claves foráneas |
| Cabeceras | `nosniff`, `Referrer-Policy`, `no-store`; el frontend suma `X-Frame-Options` y `Permissions-Policy` |

Los rechazos **no gastan cupo**: un error de tipeo, una categoría mal escrita o
un pedido sin token no le queman la cuota a quien comparta la salida a
internet. El techo global sigue cubriendo al que solo inunda.

Todo se ajusta por variables de entorno: ver `.env.example`.

### Lo que queda afuera a propósito

- **El rate limit vive en la memoria del proceso.** Con varios workers cada uno
  lleva su cuenta, así que el límite real es el configurado por la cantidad de
  workers. Por eso son 2. Un límite compartido de verdad necesitaría Redis —
  que está corriendo en el VPS, así que es una mejora barata si alguna vez hace
  falta.
- **`X-Forwarded-For` se puede falsear** si alguien llega al backend salteando
  el proxy. Acá no aplica porque el contenedor no publica puertos, pero es la
  razón de fondo para que siga siendo así.
- **No hay verificación de email ni recuperación de contraseña**: haría falta un
  servidor de correo.
- **No hay CSP en el frontend**: las páginas usan `<script>` y estilos inline, y
  una CSP útil pediría sacarlos primero.

---

## Apéndice: correrlo sin Docker

Para otro servidor sin esta infraestructura, en `deploy/` están
`manarem-api.service` (systemd), `nginx-manarem.conf` y `Caddyfile`. El resumen:
crear un usuario de sistema, un venv, `pip install -r requirements-postgres.txt`
(o `requirements.txt` para quedarse en SQLite), copiar `.env.example` a
`/etc/manarem/api.env`, y `systemctl enable --now manarem-api`. gunicorn escucha
en `127.0.0.1:5000` y el puerto **no** se abre nunca: solo le habla el proxy.

En Oracle Cloud, además de la *Security List* de la consola hay que abrir el
iptables de la propia imagen — es el paso que casi siempre se olvida:

```bash
sudo firewall-cmd --permanent --add-service=http --add-service=https && sudo firewall-cmd --reload
# en imagenes de Ubuntu:
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```
