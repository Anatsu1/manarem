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

Los tres pasos corren solos. El deploy usa `VPS_HOST`, `VPS_USER` y
`VPS_SSH_KEY`, cargados en *Settings → Secrets and variables → Actions*; el paso
está guardado con `if: env.VPS_HOST != ''`, así que si esos secrets faltaran se
saltearía en vez de dejar el build en rojo.

Para desplegar a mano, si alguna vez hace falta:

```bash
ssh servidor 'cd /srv/infrastructure/manarem && docker compose pull && docker compose up -d'
```

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

`/salud/ip` es el chequeo que importa: el campo `ip` tiene que ser **la IP del
visitante**, no la de Cloudflare ni la de Traefik. Si no lo es, el límite por IP
se vuelve uno solo compartido y el primer visitante que publique diez temas deja
afuera a todos los demás.

### Cómo se determina esa IP (y por qué no es obvio)

Desde el 2026-08-26 los rangos de Cloudflare están en los `trustedIPs` de
Traefik, así que la cadena de `X-Forwarded-For` llega entera: por Cloudflare
queda `<visitante>, <edge>`, y `MANAREM_PROXY_SALTOS=2` hace que ProxyFix tome
el anteúltimo valor, que es el visitante. Ése es hoy el camino normal.

Antes de eso Traefik **pisaba** el `X-Forwarded-For` con la dirección de su
interlocutor, la cadena original se perdía y sólo quedaba la IP del edge. La
que llegaba intacta era `CF-Connecting-IP`, y la app la leía con un doble
chequeo. Ese camino sigue en el código y sigue haciendo falta, porque es el que
tapa el bypass:

| Variable | Qué exige | Valor en este VPS |
|---|---|---|
| `MANAREM_PROXIES_CONFIABLES` | que el pedido venga de la red interna de docker, o sea de Traefik | `172.18.0.0/16` |
| `MANAREM_REDES_EDGE` | que quien le habló a Traefik sea un edge de Cloudflare | los rangos de `cloudflare.com/ips-v4` y `/ips-v6` |

El puerto 443 del VPS está abierto a internet, así que se puede llegar a Traefik
salteando Cloudflare. En ese caso Traefik no confía en el interlocutor y vuelve
a pisar el `X-Forwarded-For`, que queda con un solo valor: ProxyFix no lo usa,
`remote_addr` sigue siendo la IP interna de Traefik, y el chequeo de edge
descarta cualquier `CF-Connecting-IP` forjado. El pedido cae al cupo compartido
en vez de estrenar uno propio. **Verificado explotable antes de tener el chequeo
de edge, y verificado cerrado después.**

Si la lista de rangos queda vieja, el efecto es que esos pedidos caen al cupo
compartido, no que se rompa nada. Conviene refrescarla de vez en cuando — en
Traefik y en el `.env`, que llevan la misma lista.

El detalle completo de la cadena se ve con el token:

```bash
curl -s -H "X-Diag-Token: $(ssh servidor 'grep MANAREM_DIAG_TOKEN /srv/infrastructure/manarem/.env | cut -d= -f2-')" \
  https://manarem-api.augustofc.com/salud/ip
```

### Aplicado: `trustedIPs` de Cloudflare en Traefik

Hecho el 2026-08-26 en `/srv/infrastructure/traefik/config/traefik.yml`, en
**los dos** entrypoints (commit `b1af874` de `server_infraestructure`):

```yaml
entryPoints:
  web:
    address: ":80"
    forwardedHeaders:
      trustedIPs: &cloudflare
        - "173.245.48.0/20"
        # ... los 22 rangos de cloudflare.com/ips-v4 y /ips-v6
    http:
      redirections: { ... }        # lo que ya estaba
  websecure:
    address: ":443"
    forwardedHeaders:
      trustedIPs: *cloudflare
    http: { ... }                  # lo que ya estaba
```

Antes de tocar la que estaba en uso, la config nueva se levantó en un
contenedor `traefik:v3.7` descartable, con una copia de `acme.json` para que no
pidiera certificados. Arrancó y se quedó corriendo, que es la prueba que
importa: un error en la config estática lo hace salir al instante.

Después del `docker restart traefik` responden los 7 servicios más el
dashboard, con los mismos códigos que antes del cambio, y `traefik.log` no tiene
un solo error. La copia del archivo viejo quedó en `~/traefik.yml.bak-20260826`
del VPS.

Lo que cambió, medido con `/salud/ip` y el token de diagnóstico:

| | Antes | Ahora |
|---|---|---|
| `x_forwarded_for` | `172.69.11.130` (sólo el edge) | `45.173.193.206, 172.69.11.130` |
| `remote_addr` | `172.18.0.2` (Traefik) | `45.173.193.206` (el visitante) |
| Bypass del 443 con `CF-Connecting-IP` forjado | descartado | descartado igual |

O sea: **todos** los servicios del VPS pasan a ver la IP real sin tener que
leer `CF-Connecting-IP` ni mantener listas propias — incluido `utn-api`, que
tenía el mismo punto ciego y no lo esquivaba. Para aprovecharlo, Express
necesita `app.set('trust proxy', ...)`; sin eso ve la IP de Traefik como antes,
pero ahora el dato le llega.

Manarem no necesitó ningún cambio: sigue atribuyendo bien, sólo que ahora por
ProxyFix en vez de por la cabecera de Cloudflare.

### Lo que sigue abierto

El 443 del VPS acepta conexiones de cualquiera, no sólo de Cloudflare. La API
degrada bien (ignora la cabecera y manda esos pedidos al cupo compartido), pero
si alguna vez se quiere cerrar del todo, la forma es limitar 80/443 a los rangos
de Cloudflare en el firewall. Análisis hecho: los 7 hostnames están en naranja y
el certificado usa `dnsChallenge`, así que hoy no rompería nada — el costo es
que perdés la nube gris para depurar, y que la lista de rangos hay que
refrescarla o algunos visitantes empiezan a recibir connection refused.
**Afecta a todos los servicios del VPS**, así que es una decisión aparte.

La alternativa sin lista de IPs es **Authenticated Origin Pulls**: Traefik exige
un certificado de cliente que sólo tiene Cloudflare, y el CA es estable.

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
| IP del visitante | Traefik confía en los rangos de Cloudflare y ProxyFix toma el anteúltimo salto; el doble chequeo tapa el bypass del 443 (ver arriba) |
| `/salud/ip` | sólo devuelve la IP atribuida; el detalle va con `MANAREM_DIAG_TOKEN` |
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
- **El 443 del VPS es público**, así que se puede hablar con Traefik sin pasar
  por Cloudflare. La API lo detecta y degrada al cupo compartido; cerrarlo del
  todo es una decisión de infraestructura que afecta a todos los servicios.
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
