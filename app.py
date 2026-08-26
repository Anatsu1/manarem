"""API de Manarem.

Backend Flask + SQLite. Pensado para correr detras de un proxy inverso
(nginx / Caddy / Cloudflare Tunnel) en un VPS chico.

Es una API de un sitio de prueba, asi que viene con cupos y limites de uso
deliberados: nadie deberia poder llenar el disco del VPS desde el formulario
del foro. Todo se configura por variables de entorno (ver .env.example).
"""
import ipaddress
import os
import re
import threading
import time
import uuid
from collections import deque
from datetime import date, datetime, timedelta, timezone
from functools import wraps

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

import db

RAIZ = os.path.dirname(os.path.abspath(__file__))


def env_texto(nombre, defecto=''):
    valor = os.environ.get(nombre)
    return valor.strip() if valor and valor.strip() else defecto


def env_entero(nombre, defecto):
    try:
        return int(env_texto(nombre, str(defecto)))
    except ValueError:
        return defecto


def env_bool(nombre, defecto=False):
    return env_texto(nombre, '1' if defecto else '0').lower() in ('1', 'true', 'yes', 'on', 'si')


def env_lista(nombre, defecto):
    crudo = env_texto(nombre, '')
    if not crudo:
        return list(defecto)
    return [p.strip() for p in crudo.split(',') if p.strip()]


# Sin MANAREM_DATABASE_URL corre sobre SQLite (MANAREM_DB); con una URL de
# Postgres usa ese motor y un pool de conexiones. Ver db.py.
DB_PATH = env_texto('MANAREM_DB', os.path.join(RAIZ, 'manarem.db'))
MAX_CONEXIONES = env_entero('MANAREM_MAX_CONEXIONES', 5)

ORIGENES = env_lista('MANAREM_CORS_ORIGINS', [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
])

CONFIA_PROXY = env_bool('MANAREM_TRUST_PROXY', False)
# Cuantos proxies hay adelante. Importa: ProxyFix toma el valor N-esimo desde la
# derecha de X-Forwarded-For, asi que si el numero es menor que la cadena real
# la API termina viendo la IP del proxy y el limite por IP se vuelve global.
# Detras de Cloudflare + Traefik son 2.
PROXY_SALTOS = max(1, env_entero('MANAREM_PROXY_SALTOS', 1))
# Cabecera de la que sacar la IP real cuando X-Forwarded-For no sirve. Traefik
# reescribe XFF si el que le habla no esta en sus trustedIPs, y entonces la
# cadena se pierde entera; detras de Cloudflare, CF-Connecting-IP si llega.
# Vacio = usar solo X-Forwarded-For via ProxyFix.
IP_HEADER = env_texto('MANAREM_IP_HEADER', '')

# Redes desde las que se acepta IP_HEADER. Sin esto, cualquiera que llegue a la
# API manda la cabecera que quiere y se elige su propia clave de rate limit:
# un bucket nuevo por pedido deja todos los limites en nada. Vacio = no confiar
# en la cabecera nunca.
def _parsear_redes(crudo):
    redes = []
    for parte in crudo:
        try:
            redes.append(ipaddress.ip_network(parte, strict=False))
        except ValueError:
            pass
    return redes


PROXIES_CONFIABLES = _parsear_redes(env_lista('MANAREM_PROXIES_CONFIABLES', []))

# Redes en las que tiene que caer el que le habla al proxy para creerle a
# IP_HEADER. Detras de Cloudflare van los rangos publicados en
# cloudflare.com/ips-v4 y /ips-v6: sin este chequeo alcanza con pegarle directo
# al VPS, salteando Cloudflare, para mandar la cabecera que uno quiera.
# Vacio = no exigir nada (util cuando no hay CDN adelante).
REDES_EDGE = _parsear_redes(env_lista('MANAREM_REDES_EDGE', []))

# Token opcional para ver el detalle de /salud/ip. Sin el, ese endpoint solo
# devuelve la IP que la API le atribuye a quien pregunta.
DIAG_TOKEN = env_texto('MANAREM_DIAG_TOKEN', '')
MAX_BODY = env_entero('MANAREM_MAX_BODY', 16 * 1024)
SESION_DIAS = env_entero('MANAREM_SESION_DIAS', 7)
SESIONES_POR_USUARIO = env_entero('MANAREM_SESIONES_POR_USUARIO', 5)

CATEGORIAS_VALIDAS = ['anime', 'manga', 'musica', 'general']
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s.]+\.[^@\s]+$')
CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# Largos maximos por campo. Cortan el texto antes de que llegue a la base.
LARGO = {
    'usuario': env_entero('MANAREM_LARGO_USUARIO', 32),
    'nombre': env_entero('MANAREM_LARGO_NOMBRE', 60),
    'email': env_entero('MANAREM_LARGO_EMAIL', 120),
    'password': env_entero('MANAREM_LARGO_PASSWORD', 128),
    'titulo': env_entero('MANAREM_LARGO_TITULO', 120),
    'contenido': env_entero('MANAREM_LARGO_CONTENIDO', 4000),
    'respuesta': env_entero('MANAREM_LARGO_RESPUESTA', 2000),
    'opinion': env_entero('MANAREM_LARGO_OPINION', 600),
    'mensaje': env_entero('MANAREM_LARGO_MENSAJE', 2000),
}

PASSWORD_MINIMO = env_entero('MANAREM_PASSWORD_MINIMO', 8)

# El default de Werkzeug es scrypt:32768:8:1, que reserva 32 MB de RAM por cada
# hash. Con varios logins en paralelo eso tumba un VPS chico, asi que se usa
# pbkdf2: mismo orden de seguridad, memoria constante. Los hashes viejos siguen
# validando solos porque check_password_hash lee el metodo del hash guardado.
METODO_HASH = env_texto('MANAREM_METODO_HASH', 'pbkdf2:sha256:200000')
USUARIO_RE = re.compile(r'^[A-Za-z0-9._-]{3,%d}$' % LARGO['usuario'])

# Cupos globales: el sitio es una demo, no un servicio. Cuando se llenan, la
# API responde 429 en vez de seguir escribiendo en el disco del VPS.
CUPO = {
    'usuarios': env_entero('MANAREM_CUPO_USUARIOS', 200),
    'temas': env_entero('MANAREM_CUPO_TEMAS', 500),
    'respuestas_por_tema': env_entero('MANAREM_CUPO_RESPUESTAS_TEMA', 200),
    'opiniones': env_entero('MANAREM_CUPO_OPINIONES', 300),
    'opiniones_por_usuario': env_entero('MANAREM_CUPO_OPINIONES_USUARIO', 3),
    'mensajes': env_entero('MANAREM_CUPO_MENSAJES', 300),
}

TEMAS_POR_PAGINA = env_entero('MANAREM_TEMAS_POR_PAGINA', 50)
TEMAS_MAXIMO = env_entero('MANAREM_TEMAS_MAXIMO', 100)
OPINIONES_MAXIMO = env_entero('MANAREM_OPINIONES_MAXIMO', 100)

# Techo grueso para cualquier pedido, aparte de los limites por endpoint.
GLOBAL_MAXIMO = env_entero('MANAREM_GLOBAL_MAXIMO', 300)
GLOBAL_VENTANA = env_entero('MANAREM_GLOBAL_VENTANA', 60)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_BODY

if CONFIA_PROXY:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=PROXY_SALTOS, x_proto=1, x_host=1)

CORS(
    app,
    origins='*' if ORIGENES == ['*'] else ORIGENES,
    methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
    max_age=86400,
)


class ErrorApi(Exception):
    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class Limitador:
    """Ventana deslizante en memoria, sin dependencias.

    Vive en el proceso: con varios workers de gunicorn cada uno lleva su propia
    cuenta, asi que el limite real es el configurado por la cantidad de workers.
    Para un sitio de prueba alcanza; correr con 1 o 2 workers lo mantiene fiel.
    """

    def __init__(self):
        self._eventos = {}
        self._lock = threading.Lock()

    def permitido(self, clave, maximo, ventana):
        ahora = time.monotonic()
        with self._lock:
            if len(self._eventos) > 5000:
                self._purgar(ahora)
            cola = self._eventos.setdefault(clave, deque())
            while cola and ahora - cola[0] > ventana:
                cola.popleft()
            if len(cola) >= maximo:
                return False
            cola.append(ahora)
            return True

    def _purgar(self, ahora):
        for clave in [c for c, cola in self._eventos.items() if not cola or ahora - cola[-1] > 3600]:
            self._eventos.pop(clave, None)


limitador = Limitador()


def _en_redes(texto, redes):
    try:
        direccion = ipaddress.ip_address((texto or '').strip())
    except ValueError:
        return False
    return any(direccion in red for red in redes)


def viene_de_proxy_confiable():
    if not PROXIES_CONFIABLES:
        return False
    return _en_redes(request.remote_addr, PROXIES_CONFIABLES)


def peer_del_proxy():
    """La IP de quien le hablo al proxy, segun lo que el proxy escribio.

    Traefik reescribe X-Forwarded-For con la direccion real de su interlocutor
    cuando no confia en el, asi que este valor no lo elige el cliente.
    """
    adelante = (request.headers.get('X-Forwarded-For') or '').strip()
    if adelante:
        return adelante.split(',')[-1].strip()
    return (request.headers.get('X-Real-Ip') or '').strip()


def viene_del_edge():
    if not REDES_EDGE:
        return True
    return _en_redes(peer_del_proxy(), REDES_EDGE)


def ip_cliente():
    if IP_HEADER and viene_de_proxy_confiable() and viene_del_edge():
        valor = (request.headers.get(IP_HEADER) or '').split(',')[0].strip()
        if valor:
            return valor
    return request.remote_addr or 'desconocida'


def limite(maximo, ventana, ambito):
    """Tope de pedidos por IP y por ambito, en segundos."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not limitador.permitido(f'{ambito}:{ip_cliente()}', maximo, ventana):
                raise ErrorApi('Demasiados pedidos. Esperá un rato y probá de nuevo.', 429)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def gastar_escritura(maximo, ambito, ventana=3600):
    """Consume una unidad del cupo de escritura de esta IP.

    Se llama recien cuando el pedido ya paso autenticacion y validacion: un
    error de tipeo, una categoria mal escrita o un pedido sin token no tienen
    por que gastarle el cupo a nadie, y menos a quien comparta la salida a
    internet. El techo global sigue cubriendo el caso del que solo inunda.
    """
    if not limitador.permitido(f'escritura-{ambito}:{ip_cliente()}', maximo, ventana):
        raise ErrorApi('Estas publicando demasiado seguido. Esperá un rato.', 429)


def get_db():
    if 'conexion' not in g:
        g.conexion = db.conectar(DB_PATH, MAX_CONEXIONES)
    return g.conexion


@app.teardown_appcontext
def close_db(exception):
    conexion = g.pop('conexion', None)
    if conexion is not None:
        conexion.close()


def hoy():
    return date.today().isoformat()


def ahora_iso():
    return datetime.now(timezone.utc).isoformat()


def cuerpo():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApi('El cuerpo del pedido tiene que ser un objeto JSON')
    return datos


def campo(datos, nombre, maximo, minimo=1, etiqueta=None):
    etiqueta = etiqueta or nombre.capitalize()
    valor = datos.get(nombre)
    if valor is None:
        valor = ''
    if not isinstance(valor, str):
        raise ErrorApi(f'{etiqueta} tiene que ser texto')
    valor = CONTROL_RE.sub('', valor).strip()
    if len(valor) < minimo:
        raise ErrorApi(f'{etiqueta} es obligatorio' if minimo == 1
                       else f'{etiqueta} necesita al menos {minimo} caracteres')
    if len(valor) > maximo:
        raise ErrorApi(f'{etiqueta} no puede superar los {maximo} caracteres')
    return valor


def contar(conexion, tabla, where='', params=()):
    sql = f'SELECT COUNT(*) AS c FROM {tabla}'
    if where:
        sql += f' WHERE {where}'
    return conexion.execute(sql, params).fetchone()['c']


def revisar_cupo(conexion, tabla, tope, mensaje, where='', params=()):
    if tope >= 0 and contar(conexion, tabla, where, params) >= tope:
        raise ErrorApi(mensaje, 429)


def purgar_sesiones(conexion):
    corte = (datetime.now(timezone.utc) - timedelta(days=SESION_DIAS)).isoformat()
    conexion.execute('DELETE FROM sesiones WHERE creado < ?', (corte,))


def usuario_actual():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    conexion = get_db()
    fila = conexion.execute(
        '''SELECT s.creado AS sesion_creada, u.id, u.usuario, u.nombre, u.email
           FROM sesiones s JOIN usuarios u ON s.usuario_id = u.id
           WHERE s.token = ?''',
        (token,)
    ).fetchone()
    if not fila:
        return None
    try:
        creada = datetime.fromisoformat(fila['sesion_creada'])
    except ValueError:
        creada = None
    if creada is None:
        return fila
    if creada.tzinfo is None:
        creada = creada.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - creada > timedelta(days=SESION_DIAS):
        conexion.execute('DELETE FROM sesiones WHERE token = ?', (token,))
        conexion.commit()
        return None
    return fila


def exigir_usuario():
    user = usuario_actual()
    if not user:
        raise ErrorApi('No autenticado', 401)
    return user


db.init_esquema(DB_PATH, MAX_CONEXIONES)


@app.before_request
def techo_global():
    # OPTIONS queda afuera: es el preflight de CORS y no toca la base.
    if request.method == 'OPTIONS':
        return None
    if not limitador.permitido(f'global:{ip_cliente()}', GLOBAL_MAXIMO, GLOBAL_VENTANA):
        return jsonify({'error': 'Demasiados pedidos. Esperá un rato y probá de nuevo.'}), 429
    return None


@app.after_request
def cabeceras_seguras(respuesta):
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    respuesta.headers['Referrer-Policy'] = 'no-referrer'
    respuesta.headers['Cache-Control'] = 'no-store'
    respuesta.headers.pop('Server', None)
    return respuesta


@app.errorhandler(ErrorApi)
def _error_api(e):
    return jsonify({'error': e.mensaje}), e.codigo


@app.errorhandler(400)
def _error_400(e):
    return jsonify({'error': 'Pedido invalido'}), 400


@app.errorhandler(404)
def _error_404(e):
    return jsonify({'error': 'Recurso no encontrado'}), 404


@app.errorhandler(405)
def _error_405(e):
    return jsonify({'error': 'Metodo no permitido'}), 405


@app.errorhandler(413)
def _error_413(e):
    return jsonify({'error': 'El contenido enviado es demasiado grande'}), 413


@app.errorhandler(500)
def _error_500(e):
    app.logger.exception('Error no controlado')
    return jsonify({'error': 'Error interno del servidor'}), 500


def _error_base(e):
    app.logger.exception('Error de base de datos')
    return jsonify({'error': 'Error interno del servidor'}), 500


for _clase_error in db.ERRORES_BASE:
    app.register_error_handler(_clase_error, _error_base)


@app.route('/salud', methods=['GET'])
def salud():
    conexion = get_db()
    return jsonify({
        'estado': 'ok',
        'usuarios': contar(conexion, 'usuarios'),
        'temas': contar(conexion, 'temas'),
        'opiniones': contar(conexion, 'opiniones'),
    }), 200


@app.route('/salud/ip', methods=['GET'])
def salud_ip():
    """Para verificar de que IP cree la API que viene cada pedido.

    Si `ip` no es la IP real del visitante, el rate limit por IP no esta
    funcionando: todos comparten el mismo cupo. Con X-Diag-Token se ve el
    detalle de la cadena de proxies.
    """
    respuesta = {'ip': ip_cliente()}

    # El detalle describe la topologia interna (IP del proxy, que cabeceras
    # llegan), asi que va solo con token.
    if DIAG_TOKEN and request.headers.get('X-Diag-Token') == DIAG_TOKEN:
        respuesta.update({
            # De donde salio realmente el valor de `ip`, no que cabecera esta
            # configurada: desde que Traefik confia en los rangos de Cloudflare,
            # ProxyFix ya resuelve la IP real y la rama de la cabecera casi nunca
            # se usa. Decir siempre 'CF-Connecting-IP' confundia el diagnostico.
            'origen': (
                IP_HEADER
                if (IP_HEADER and viene_de_proxy_confiable() and viene_del_edge())
                else 'remote_addr'
            ),
            'proxy_confiable': viene_de_proxy_confiable(),
            'peer_del_proxy': peer_del_proxy(),
            'viene_del_edge': viene_del_edge(),
            'saltos_declarados': PROXY_SALTOS if CONFIA_PROXY else 0,
            'remote_addr': request.remote_addr,
            'x_forwarded_for': request.headers.get('X-Forwarded-For'),
            'cf_connecting_ip': request.headers.get('CF-Connecting-IP'),
            'x_real_ip': request.headers.get('X-Real-Ip'),
        })

    return jsonify(respuesta), 200


@app.route('/registro', methods=['POST'])
@limite(20, 3600, 'registro-intentos')
def registro():
    datos = cuerpo()
    usuario = campo(datos, 'usuario', LARGO['usuario'], 3, 'El usuario')
    nombre = campo(datos, 'nombre', LARGO['nombre'], 2, 'El nombre')
    email = campo(datos, 'email', LARGO['email'], 5, 'El email')
    password = campo(datos, 'password', LARGO['password'], PASSWORD_MINIMO, 'La contraseña')

    if not USUARIO_RE.match(usuario):
        raise ErrorApi('El usuario solo puede tener letras, numeros, punto, guion y guion bajo')
    if not EMAIL_RE.match(email):
        raise ErrorApi('El email no parece valido')

    conexion = get_db()
    revisar_cupo(conexion, 'usuarios', CUPO['usuarios'],
                 'El sitio de prueba llego al maximo de cuentas registradas')

    if conexion.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,)).fetchone():
        return jsonify({'error': 'El usuario ya existe'}), 409

    # El tope de altas se cuenta recien aca: un error de tipeo o un usuario
    # repetido no gastan cupo, solo las cuentas que realmente se crean.
    if not limitador.permitido(f'registro-altas:{ip_cliente()}', 5, 3600):
        raise ErrorApi('Se crearon demasiadas cuentas desde esta conexion. Probá mas tarde.', 429)

    try:
        conexion.execute(
            'INSERT INTO usuarios (usuario, nombre, email, password_hash, creado) VALUES (?, ?, ?, ?, ?)',
            (usuario, nombre, email, generate_password_hash(password, method=METODO_HASH), hoy())
        )
        conexion.commit()
    except db.ERRORES_INTEGRIDAD:
        return jsonify({'error': 'El usuario ya existe'}), 409

    return jsonify({'mensaje': 'Usuario registrado correctamente'}), 201


@app.route('/login', methods=['POST'])
@limite(10, 300, 'login')
def login():
    datos = cuerpo()
    usuario = campo(datos, 'usuario', LARGO['usuario'], 1, 'El usuario')
    password = campo(datos, 'password', LARGO['password'], 1, 'La contraseña')

    conexion = get_db()
    user = conexion.execute('SELECT * FROM usuarios WHERE usuario = ?', (usuario,)).fetchone()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    purgar_sesiones(conexion)
    sobrantes = conexion.execute(
        '''SELECT token FROM sesiones WHERE usuario_id = ?
           ORDER BY creado DESC LIMIT 1000000 OFFSET ?''',
        (user['id'], max(SESIONES_POR_USUARIO - 1, 0))
    ).fetchall()
    for fila in sobrantes:
        conexion.execute('DELETE FROM sesiones WHERE token = ?', (fila['token'],))

    token = uuid.uuid4().hex
    conexion.execute(
        'INSERT INTO sesiones (token, usuario_id, creado) VALUES (?, ?, ?)',
        (token, user['id'], ahora_iso())
    )
    conexion.commit()

    return jsonify({
        'mensaje': 'Inicio de sesión exitoso',
        'token': token,
        'usuario': {
            'id': user['id'],
            'usuario': user['usuario'],
            'nombre': user['nombre'],
            'email': user['email']
        }
    }), 200


@app.route('/logout', methods=['POST'])
def logout():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        conexion = get_db()
        conexion.execute('DELETE FROM sesiones WHERE token = ?', (auth[7:].strip(),))
        conexion.commit()
    return jsonify({'mensaje': 'Sesion cerrada'}), 200


@app.route('/perfil', methods=['GET'])
def perfil():
    user = exigir_usuario()
    conexion = get_db()

    creado = conexion.execute(
        'SELECT creado FROM usuarios WHERE id = ?', (user['id'],)
    ).fetchone()['creado']

    temas = conexion.execute(
        'SELECT id, titulo, categoria, fecha FROM temas WHERE autor_id = ? ORDER BY id DESC',
        (user['id'],)
    ).fetchall()

    return jsonify({
        'usuario': user['usuario'],
        'nombre': user['nombre'],
        'email': user['email'],
        'creado': creado,
        'total_temas': contar(conexion, 'temas', 'autor_id = ?', (user['id'],)),
        'total_respuestas': contar(conexion, 'respuestas', 'autor_id = ?', (user['id'],)),
        'temas': [dict(t) for t in temas]
    }), 200


@app.route('/foro/temas', methods=['GET'])
@limite(120, 60, 'lectura')
def listar_temas():
    try:
        limitar = int(request.args.get('limite', TEMAS_POR_PAGINA))
        desde = int(request.args.get('desde', 0))
    except ValueError:
        raise ErrorApi('Los parametros limite y desde tienen que ser numeros')

    limitar = max(1, min(limitar, TEMAS_MAXIMO))
    desde = max(0, desde)

    conexion = get_db()
    filas = conexion.execute(
        '''SELECT t.id, t.titulo, t.categoria, u.usuario AS autor, t.fecha,
           (SELECT COUNT(*) FROM respuestas r WHERE r.tema_id = t.id) AS respuestas
           FROM temas t JOIN usuarios u ON t.autor_id = u.id
           ORDER BY t.id DESC LIMIT ? OFFSET ?''',
        (limitar, desde)
    ).fetchall()
    return jsonify([dict(f) for f in filas])


@app.route('/foro/temas', methods=['POST'])
def crear_tema():
    user = exigir_usuario()
    datos = cuerpo()
    titulo = campo(datos, 'titulo', LARGO['titulo'], 3, 'El titulo')
    categoria = campo(datos, 'categoria', 20, 1, 'La categoria')
    contenido = campo(datos, 'contenido', LARGO['contenido'], 3, 'El contenido')

    if categoria not in CATEGORIAS_VALIDAS:
        raise ErrorApi('Categoría inválida')

    conexion = get_db()
    revisar_cupo(conexion, 'temas', CUPO['temas'],
                 'El foro de prueba llego al maximo de temas')
    gastar_escritura(10, 'temas')

    resultado = conexion.insertar(
        'INSERT INTO temas (titulo, categoria, contenido, autor_id, fecha) VALUES (?, ?, ?, ?, ?)',
        (titulo, categoria, contenido, user['id'], hoy())
    )
    conexion.commit()

    return jsonify({'mensaje': 'Tema creado correctamente', 'id': resultado.id_insertado}), 201


@app.route('/foro/temas/<int:id>', methods=['GET'])
@limite(120, 60, 'lectura')
def obtener_tema(id):
    conexion = get_db()
    tema = conexion.execute(
        '''SELECT t.id, t.titulo, t.categoria, t.contenido, u.usuario AS autor, t.fecha
           FROM temas t JOIN usuarios u ON t.autor_id = u.id
           WHERE t.id = ?''',
        (id,)
    ).fetchone()

    if not tema:
        return jsonify({'error': 'Tema no encontrado'}), 404

    respuestas = conexion.execute(
        '''SELECT r.id, u.usuario AS autor, r.fecha, r.contenido
           FROM respuestas r JOIN usuarios u ON r.autor_id = u.id
           WHERE r.tema_id = ?
           ORDER BY r.id ASC''',
        (id,)
    ).fetchall()

    resultado = dict(tema)
    resultado['respuestas'] = [dict(r) for r in respuestas]

    return jsonify(resultado)


@app.route('/foro/temas/<int:id>/respuestas', methods=['POST'])
def crear_respuesta(id):
    user = exigir_usuario()

    conexion = get_db()
    if not conexion.execute('SELECT id FROM temas WHERE id = ?', (id,)).fetchone():
        return jsonify({'error': 'Tema no encontrado'}), 404

    contenido = campo(cuerpo(), 'contenido', LARGO['respuesta'], 1, 'El contenido')

    revisar_cupo(conexion, 'respuestas', CUPO['respuestas_por_tema'],
                 'Este tema llego al maximo de respuestas', 'tema_id = ?', (id,))
    gastar_escritura(30, 'respuestas')

    resultado = conexion.insertar(
        'INSERT INTO respuestas (tema_id, contenido, autor_id, fecha) VALUES (?, ?, ?, ?)',
        (id, contenido, user['id'], hoy())
    )
    conexion.commit()

    return jsonify({'mensaje': 'Respuesta creada correctamente', 'id': resultado.id_insertado}), 201


@app.route('/opiniones', methods=['GET'])
@limite(120, 60, 'lectura')
def listar_opiniones():
    conexion = get_db()
    filas = conexion.execute(
        'SELECT id, nombre, avatar, texto, fecha FROM opiniones ORDER BY id DESC LIMIT ?',
        (OPINIONES_MAXIMO,)
    ).fetchall()
    return jsonify([dict(f) for f in filas])


@app.route('/opiniones', methods=['POST'])
def crear_opinion():
    user = exigir_usuario()
    texto = campo(cuerpo(), 'texto', LARGO['opinion'], 1, 'El texto')

    conexion = get_db()
    revisar_cupo(conexion, 'opiniones', CUPO['opiniones'],
                 'El muro de opiniones de prueba esta lleno')
    revisar_cupo(conexion, 'opiniones', CUPO['opiniones_por_usuario'],
                 'Ya dejaste todas las opiniones que permite el sitio de prueba',
                 'autor_id = ?', (user['id'],))
    gastar_escritura(10, 'opiniones')

    resultado = conexion.insertar(
        'INSERT INTO opiniones (autor_id, nombre, avatar, texto, fecha) VALUES (?, ?, ?, ?, ?)',
        (user['id'], user['usuario'], 'persona1-f.jpg', texto, hoy())
    )
    conexion.commit()

    return jsonify({'mensaje': 'Opinion enviada', 'id': resultado.id_insertado}), 201


@app.route('/contacto', methods=['POST'])
def contacto():
    datos = cuerpo()
    nombre = campo(datos, 'nombre', LARGO['nombre'], 2, 'El nombre')
    email = campo(datos, 'email', LARGO['email'], 5, 'El email')
    mensaje = campo(datos, 'mensaje', LARGO['mensaje'], 5, 'El mensaje')

    if not EMAIL_RE.match(email):
        raise ErrorApi('El email no parece valido')

    conexion = get_db()
    revisar_cupo(conexion, 'contacto_mensajes', CUPO['mensajes'],
                 'La casilla de contacto de prueba esta llena')
    gastar_escritura(5, 'contacto')

    conexion.execute(
        'INSERT INTO contacto_mensajes (nombre, email, mensaje, fecha) VALUES (?, ?, ?, ?)',
        (nombre, email, mensaje, hoy())
    )
    conexion.commit()

    return jsonify({'mensaje': 'Mensaje enviado correctamente'}), 201


if __name__ == '__main__':
    app.run(host=env_texto('MANAREM_HOST', '127.0.0.1'),
            port=env_entero('MANAREM_PORT', 5000),
            debug=env_bool('MANAREM_DEBUG', False))
