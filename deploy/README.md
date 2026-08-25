# Poner Manarem en produccion

Frontend en Vercel (estatico) + API Flask en el VPS de Oracle.

---

## Lo primero: en Vercel NO hay que configurar ninguna variable de entorno

El frontend es HTML, CSS y JS servidos tal cual, **sin build step**. Vercel solo
inyecta variables de entorno durante un build, y aca no hay build: nada de lo
que se ponga en *Settings → Environment Variables* llega al navegador.

La configuracion del frontend vive en **dos archivos del repo**, y se aplica
haciendo push (Vercel redeploya solo):

| Archivo | Que se toca |
|---|---|
| `frontend/static/js/api.js` | `CONFIG.apiBase` — a que API le pega el sitio |
| `frontend/vercel.json` | el destino real del proxy `/api/:ruta*` |

Mientras `apiBase` este vacio, el sitio funciona con los datos simulados de
`mock-data.js`. Es el estado seguro: se puede pushear sin romper la demo.

---

## Paso 1 — Elegir como se expone la API

El sitio en Vercel se sirve por **https**. Un navegador en una pagina https no
puede pedirle nada a un `http://`: lo bloquea como contenido mixto. Asi que la
API necesita https si o si.

### Opcion A — Cloudflare Tunnel (la recomendada)

Sin abrir un solo puerto en el VPS, con certificado incluido y sin publicar la
IP del servidor. Es lo que mejor encaja con "que no sea una carga innecesaria":
lo que no esta expuesto no se puede inundar.

```bash
cloudflared tunnel login
cloudflared tunnel create manarem-api
cloudflared tunnel route dns manarem-api api.tu-dominio.com
```

`/etc/cloudflared/config.yml`:

```yaml
tunnel: manarem-api
credentials-file: /root/.cloudflared/<id-del-tunnel>.json
ingress:
  - hostname: api.tu-dominio.com
    service: http://127.0.0.1:5000
  - service: http_status:404
```

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

### Opcion B — nginx o Caddy con dominio propio

Ya hay dos plantillas listas: `deploy/nginx-manarem.conf` y `deploy/Caddyfile`.
Caddy saca el certificado solo; con nginx hace falta `certbot --nginx`.

Con esta opcion **si** hay que abrir puertos, y en Oracle Cloud son **dos
lugares distintos** — el que casi siempre se olvida es el segundo:

1. Consola de OCI → la VNIC de la instancia → *Security List* / NSG: ingress
   0.0.0.0/0 en 80 y 443.
2. Dentro de la maquina, las imagenes de Oracle traen un iptables cerrado:

```bash
sudo firewall-cmd --permanent --add-service=http --add-service=https && sudo firewall-cmd --reload
# o, en las imagenes de Ubuntu:
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

**El puerto 5000 no se abre nunca.** gunicorn escucha en `127.0.0.1` y solo el
proxy le habla.

### Opcion C — pegarle directo a la IP del VPS

No sirve: sin dominio no hay certificado, sin certificado es http, y el
navegador lo bloquea. Ademas publica la IP del servidor.

---

## Paso 2 — La base de datos

### SQLite (lo que corre por defecto)

No hay nada que instalar. Para un sitio de prueba con los cupos puestos es la
opcion mas liviana: un archivo, cero procesos, cero memoria residente.

```bash
sudo mkdir -p /var/lib/manarem && sudo chown manarem:manarem /var/lib/manarem
```

y en el archivo de entorno: `MANAREM_DB=/var/lib/manarem/manarem.db`

### PostgreSQL (si se quiere usar el que ya corre en el VPS)

```bash
sudo -u postgres psql <<'SQL'
CREATE USER manarem WITH PASSWORD 'una-clave-larga-y-random';
CREATE DATABASE manarem OWNER manarem;
SQL
```

En el archivo de entorno:

```
MANAREM_DATABASE_URL=postgresql://manarem:una-clave-larga-y-random@127.0.0.1:5432/manarem
MANAREM_MAX_CONEXIONES=5
```

y se instalan las dependencias con `pip install -r requirements-postgres.txt`.

`MANAREM_MAX_CONEXIONES` es el tamaño del pool **por worker de gunicorn**: con
2 workers y 5 conexiones son 10 conexiones al motor. Conviene tenerlo en cuenta
si el Postgres del VPS lo comparten otros servicios — el default de PostgreSQL
es 100 en total.

Las tablas se crean solas al arrancar, en los dos motores.

---

## Paso 3 — El servicio en el VPS

```bash
sudo useradd --system --home /opt/manarem --shell /usr/sbin/nologin manarem
sudo git clone https://github.com/Anatsu1/manarem.git /opt/manarem
cd /opt/manarem
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt          # o requirements-postgres.txt
sudo chown -R manarem:manarem /opt/manarem

sudo mkdir -p /etc/manarem
sudo cp .env.example /etc/manarem/api.env
sudo nano /etc/manarem/api.env                            # ajustar
sudo chmod 640 /etc/manarem/api.env
sudo chown root:manarem /etc/manarem/api.env

sudo cp deploy/manarem-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now manarem-api
sudo systemctl status manarem-api
curl -s localhost:5000/salud
```

En `/etc/manarem/api.env`, lo que no puede faltar:

```
MANAREM_CORS_ORIGINS=https://manarem.vercel.app
MANAREM_TRUST_PROXY=1
MANAREM_DEBUG=0
```

`MANAREM_TRUST_PROXY=1` es **obligatorio** cuando hay un proxy adelante: sin
eso, la API ve la IP del proxy en todos los pedidos y el rate limit por IP se
convierte en un limite compartido que echa a todo el mundo junto.

---

## Paso 4 — Conectar el frontend

Con la API respondiendo en `https://api.tu-dominio.com/salud`:

**Con el proxy de Vercel (recomendado).** El pedido sale al mismo origen, asi
que no hay CORS ni preflight, y la URL del VPS no aparece en el navegador.

1. En `frontend/vercel.json`, cambiar el destino:
   ```json
   { "source": "/api/:ruta*", "destination": "https://api.tu-dominio.com/:ruta*" }
   ```
2. En `frontend/static/js/api.js`: `apiBase: '/api'`
3. Commit y push. Vercel redeploya solo.

**Sin proxy, directo al backend.** `apiBase: 'https://api.tu-dominio.com'` y el
dominio de Vercel en `MANAREM_CORS_ORIGINS`.

---

## Paso 5 — Verificar

```bash
curl -s https://api.tu-dominio.com/salud
curl -s https://manarem.vercel.app/api/salud        # si se uso el proxy
```

Y en el sitio: crear una cuenta, iniciar sesion, publicar un tema, responderlo,
dejar una opinion. El `/perfil` tiene que mostrar el nombre y los temas propios.

Si algo no responde, `?mock=1` en cualquier pagina vuelve a los datos simulados
sin tocar codigo, y `?mock=0` lo desactiva.

---

## Que trae puesto para no cargar el servidor

| Que | Como |
|---|---|
| Cuerpo del pedido | 16 KB, mas arriba responde 413 |
| Largo de cada campo | titulo 120, tema 4000, respuesta 2000, opinion 600 |
| Techo global por IP | 300 pedidos por minuto |
| Altas de cuenta | 5 por hora por IP, contando solo las que se concretan |
| Login | 10 intentos cada 5 minutos por IP |
| Temas | 10 por hora por IP; respuestas 30 por hora |
| Contacto | 5 por hora por IP |
| Cupos del sitio | 200 cuentas, 500 temas, 200 respuestas por tema, 300 opiniones |
| Listados | 50 temas por pagina, tope 100; opiniones tope 100 |
| Sesiones | vencen a los 7 dias, 5 activas por usuario como maximo |
| Hash de contraseña | pbkdf2 en vez del scrypt por defecto de Werkzeug, que reserva **32 MB de RAM por hash** |
| Consultas | siempre parametrizadas; indices en las claves foraneas |
| Cabeceras | `nosniff`, `Referrer-Policy`, `no-store`; el frontend suma `X-Frame-Options` y `Permissions-Policy` |

Todo se ajusta por variables de entorno: ver `.env.example`.

### Lo que queda afuera a proposito

- **El rate limit vive en la memoria del proceso.** Con varios workers cada uno
  lleva su cuenta, asi que el limite real es el configurado por la cantidad de
  workers. Por eso el service arranca con 2. Un limite compartido de verdad
  necesitaria Redis, que es justo el proceso extra que no queremos.
- **`X-Forwarded-For` se puede falsear** si alguien le pega directo al backend
  saltando el proxy. Es la razon de fondo para no exponer el 5000 y de que la
  opcion A (tunnel, sin puertos abiertos) sea la recomendada.
- **No hay verificacion de email ni recuperacion de contraseña**: haria falta un
  servidor de correo.
- **No hay CSP en el frontend**: las paginas usan `<script>` y estilos inline, y
  una CSP util pediria sacarlos primero.
