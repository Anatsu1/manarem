import os
import sqlite3
import uuid
from datetime import date

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manarem.db')

CATEGORIAS_VALIDAS = ['anime', 'manga', 'musica', 'general']


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            nombre TEXT,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            creado TEXT NOT NULL
        )''')
        cols = [r[1] for r in conn.execute('PRAGMA table_info(usuarios)')]
        if 'nombre' not in cols:
            conn.execute('ALTER TABLE usuarios ADD COLUMN nombre TEXT')
        conn.execute('''CREATE TABLE IF NOT EXISTS sesiones(
            token TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            creado TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS temas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            contenido TEXT NOT NULL,
            autor_id INTEGER NOT NULL REFERENCES usuarios(id),
            fecha TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS respuestas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema_id INTEGER NOT NULL REFERENCES temas(id),
            contenido TEXT NOT NULL,
            autor_id INTEGER NOT NULL REFERENCES usuarios(id),
            fecha TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS opiniones(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor_id INTEGER NOT NULL REFERENCES usuarios(id),
            nombre TEXT NOT NULL,
            avatar TEXT NOT NULL,
            texto TEXT NOT NULL,
            fecha TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS contacto_mensajes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            fecha TEXT NOT NULL
        )''')
        conn.commit()


def usuario_actual(request):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[7:]
    db = get_db()
    return db.execute(
        'SELECT u.id, u.usuario, u.email FROM sesiones s JOIN usuarios u ON s.usuario_id = u.id WHERE s.token = ?',
        (token,)
    ).fetchone()


init_db()


@app.route('/registro', methods=['POST'])
def registro():
    data = request.get_json(silent=True) or {}
    usuario = (data.get('usuario') or '').strip()
    nombre = (data.get('nombre') or '').strip()
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()

    if not usuario or not nombre or not email or not password:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    db = get_db()
    try:
        db.execute(
            'INSERT INTO usuarios (usuario, nombre, email, password_hash, creado) VALUES (?, ?, ?, ?, ?)',
            (usuario, nombre, email, generate_password_hash(password), date.today().isoformat())
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El usuario ya existe'}), 409

    return jsonify({'mensaje': 'Usuario registrado correctamente'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    usuario = (data.get('usuario') or '').strip()
    password = (data.get('password') or '').strip()

    if not usuario or not password:
        return jsonify({'error': 'Usuario y contraseña son obligatorios'}), 400

    db = get_db()
    user = db.execute(
        'SELECT * FROM usuarios WHERE usuario = ?', (usuario,)
    ).fetchone()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    token = uuid.uuid4().hex
    db.execute(
        'INSERT INTO sesiones (token, usuario_id, creado) VALUES (?, ?, ?)',
        (token, user['id'], date.today().isoformat())
    )
    db.commit()

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


@app.route('/foro/temas', methods=['GET'])
def listar_temas():
    db = get_db()
    filas = db.execute(
        '''SELECT t.id, t.titulo, t.categoria, u.usuario AS autor, t.fecha,
           (SELECT COUNT(*) FROM respuestas r WHERE r.tema_id = t.id) AS respuestas
           FROM temas t JOIN usuarios u ON t.autor_id = u.id
           ORDER BY t.id DESC'''
    ).fetchall()
    return jsonify([dict(f) for f in filas])


@app.route('/foro/temas', methods=['POST'])
def crear_tema():
    user = usuario_actual(request)
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or {}
    titulo = (data.get('titulo') or '').strip()
    categoria = (data.get('categoria') or '').strip()
    contenido = (data.get('contenido') or '').strip()

    if not titulo or not categoria or not contenido:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if categoria not in CATEGORIAS_VALIDAS:
        return jsonify({'error': 'Categoría inválida'}), 400

    db = get_db()
    cursor = db.execute(
        'INSERT INTO temas (titulo, categoria, contenido, autor_id, fecha) VALUES (?, ?, ?, ?, ?)',
        (titulo, categoria, contenido, user['id'], date.today().isoformat())
    )
    db.commit()

    return jsonify({'mensaje': 'Tema creado correctamente', 'id': cursor.lastrowid}), 201


@app.route('/foro/temas/<int:id>', methods=['GET'])
def obtener_tema(id):
    db = get_db()
    tema = db.execute(
        '''SELECT t.id, t.titulo, t.categoria, t.contenido, u.usuario AS autor, t.fecha
           FROM temas t JOIN usuarios u ON t.autor_id = u.id
           WHERE t.id = ?''',
        (id,)
    ).fetchone()

    if not tema:
        return jsonify({'error': 'Tema no encontrado'}), 404

    respuestas = db.execute(
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
    user = usuario_actual(request)
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    db = get_db()
    tema = db.execute('SELECT id FROM temas WHERE id = ?', (id,)).fetchone()
    if not tema:
        return jsonify({'error': 'Tema no encontrado'}), 404

    data = request.get_json(silent=True) or {}
    contenido = (data.get('contenido') or '').strip()

    if not contenido:
        return jsonify({'error': 'El contenido no puede estar vacío'}), 400

    cursor = db.execute(
        'INSERT INTO respuestas (tema_id, contenido, autor_id, fecha) VALUES (?, ?, ?, ?)',
        (id, contenido, user['id'], date.today().isoformat())
    )
    db.commit()

    return jsonify({'mensaje': 'Respuesta creada correctamente', 'id': cursor.lastrowid}), 201


@app.route('/contacto', methods=['POST'])
def contacto():
    data = request.get_json(silent=True) or {}
    nombre = (data.get('nombre') or '').strip()
    email = (data.get('email') or '').strip()
    mensaje = (data.get('mensaje') or '').strip()

    if not nombre or not email or not mensaje:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO contacto_mensajes (nombre, email, mensaje, fecha) VALUES (?, ?, ?, ?)',
        (nombre, email, mensaje, date.today().isoformat())
    )
    db.commit()

    return jsonify({'mensaje': 'Mensaje enviado correctamente'}), 201


@app.route('/opiniones', methods=['GET'])
def listar_opiniones():
    db = get_db()
    filas = db.execute(
        'SELECT id, nombre, avatar, texto, fecha FROM opiniones ORDER BY id DESC'
    ).fetchall()
    return jsonify([dict(f) for f in filas])


@app.route('/opiniones', methods=['POST'])
def crear_opinion():
    user = usuario_actual(request)
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or {}
    texto = (data.get('texto') or '').strip()

    if not texto:
        return jsonify({'error': 'El texto no puede estar vacío'}), 400

    db = get_db()
    cursor = db.execute(
        'INSERT INTO opiniones (autor_id, nombre, avatar, texto, fecha) VALUES (?, ?, ?, ?, ?)',
        (user['id'], user['usuario'], 'persona1-f.jpg', texto, date.today().isoformat())
    )
    db.commit()

    return jsonify({'mensaje': 'Opinion enviada', 'id': cursor.lastrowid}), 201


@app.route('/logout', methods=['POST'])
def logout():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth[7:]
        db = get_db()
        db.execute('DELETE FROM sesiones WHERE token = ?', (token,))
        db.commit()
    return jsonify({'mensaje': 'Sesion cerrada'}), 200


@app.route('/perfil', methods=['GET'])
def perfil():
    user = usuario_actual(request)
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    db = get_db()
    fila = db.execute(
        'SELECT creado, nombre FROM usuarios WHERE id = ?', (user['id'],)
    ).fetchone()
    creado = fila['creado']
    nombre = fila['nombre']

    total_temas = db.execute(
        'SELECT COUNT(*) AS c FROM temas WHERE autor_id = ?', (user['id'],)
    ).fetchone()['c']

    total_respuestas = db.execute(
        'SELECT COUNT(*) AS c FROM respuestas WHERE autor_id = ?', (user['id'],)
    ).fetchone()['c']

    temas = db.execute(
        'SELECT id, titulo, categoria, fecha FROM temas WHERE autor_id = ? ORDER BY id DESC',
        (user['id'],)
    ).fetchall()

    return jsonify({
        'usuario': user['usuario'],
        'nombre': nombre,
        'email': user['email'],
        'creado': creado,
        'total_temas': total_temas,
        'total_respuestas': total_respuestas,
        'temas': [dict(t) for t in temas]
    }), 200


if __name__ == '__main__':
    app.run(debug=True)
