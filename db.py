"""Capa de datos de Manarem: SQLite o PostgreSQL, misma interfaz.

Sin MANAREM_DATABASE_URL corre sobre SQLite y el proyecto se clona y arranca
sin instalar nada mas. Con MANAREM_DATABASE_URL apuntando a Postgres usa un
pool de conexiones, que es lo que corresponde en un servidor donde el motor ya
esta levantado: abrir y cerrar una conexion TCP por pedido es carga al pedo.

Las consultas se escriben SIEMPRE con `?` como marcador; para Postgres se
traducen a `%s` en `_traducir()`. Ninguna consulta del proyecto lleva `?` ni `%`
dentro de un literal, que es lo unico que romperia esa traduccion.
"""
import os
import sqlite3
import threading

DATABASE_URL = (os.environ.get('MANAREM_DATABASE_URL') or '').strip()
ES_POSTGRES = DATABASE_URL.startswith(('postgres://', 'postgresql://'))

if ES_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    ERRORES_INTEGRIDAD = (psycopg.errors.IntegrityError,)
    ERRORES_BASE = (psycopg.Error,)
else:
    ERRORES_INTEGRIDAD = (sqlite3.IntegrityError,)
    ERRORES_BASE = (sqlite3.Error,)


def _traducir(sql):
    return sql.replace('?', '%s') if ES_POSTGRES else sql


class Resultado:
    """Envoltura fina sobre el cursor, para que las vistas no sepan el motor."""

    def __init__(self, cursor, id_insertado=None):
        self._cursor = cursor
        self.id_insertado = id_insertado

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class Conexion:
    def __init__(self, cruda, devolver=None):
        self._cruda = cruda
        self._devolver = devolver

    def execute(self, sql, params=()):
        cursor = self._cruda.cursor()
        cursor.execute(_traducir(sql), params)
        return Resultado(cursor)

    def insertar(self, sql, params=()):
        """INSERT que devuelve el id generado, en los dos motores."""
        cursor = self._cruda.cursor()
        if ES_POSTGRES:
            cursor.execute(_traducir(sql) + ' RETURNING id', params)
            fila = cursor.fetchone()
            nuevo = fila['id'] if fila else None
        else:
            cursor.execute(sql, params)
            nuevo = cursor.lastrowid
        return Resultado(cursor, nuevo)

    def commit(self):
        self._cruda.commit()

    def close(self):
        if self._devolver is None:
            self._cruda.close()
            return
        # Postgres abre una transaccion con la primera consulta. Las lecturas no
        # commitean, asi que sin esto la conexion vuelve al pool con una
        # transaccion abierta: el pool la revierte igual, pero mientras tanto
        # bloquea el vacuum del servidor. Lo que no se commiteo no se queria.
        try:
            self._cruda.rollback()
        except Exception:
            pass
        self._devolver(self._cruda)


_pool = None
_lock = threading.Lock()


def _obtener_pool(max_size):
    global _pool
    with _lock:
        if _pool is None:
            _pool = ConnectionPool(
                DATABASE_URL,
                min_size=1,
                max_size=max_size,
                kwargs={'row_factory': dict_row},
                open=True,
            )
    return _pool


def conectar(ruta_sqlite, max_conexiones=5):
    if ES_POSTGRES:
        pool = _obtener_pool(max_conexiones)
        cruda = pool.getconn()
        return Conexion(cruda, devolver=pool.putconn)

    cruda = sqlite3.connect(ruta_sqlite, timeout=10)
    cruda.row_factory = sqlite3.Row
    cruda.execute('PRAGMA foreign_keys = ON')
    return Conexion(cruda)


ESQUEMA_SQLITE = [
    '''CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        nombre TEXT,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        creado TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS sesiones(
        token TEXT PRIMARY KEY,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
        creado TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS temas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        categoria TEXT NOT NULL,
        contenido TEXT NOT NULL,
        autor_id INTEGER NOT NULL REFERENCES usuarios(id),
        fecha TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS respuestas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema_id INTEGER NOT NULL REFERENCES temas(id),
        contenido TEXT NOT NULL,
        autor_id INTEGER NOT NULL REFERENCES usuarios(id),
        fecha TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS opiniones(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        autor_id INTEGER NOT NULL REFERENCES usuarios(id),
        nombre TEXT NOT NULL,
        avatar TEXT NOT NULL,
        texto TEXT NOT NULL,
        fecha TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS contacto_mensajes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        fecha TEXT NOT NULL
    )''',
]

ESQUEMA_POSTGRES = [
    '''CREATE TABLE IF NOT EXISTS usuarios(
        id SERIAL PRIMARY KEY,
        usuario TEXT UNIQUE NOT NULL,
        nombre TEXT,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        creado TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS sesiones(
        token TEXT PRIMARY KEY,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
        creado TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS temas(
        id SERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        categoria TEXT NOT NULL,
        contenido TEXT NOT NULL,
        autor_id INTEGER NOT NULL REFERENCES usuarios(id),
        fecha TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS respuestas(
        id SERIAL PRIMARY KEY,
        tema_id INTEGER NOT NULL REFERENCES temas(id),
        contenido TEXT NOT NULL,
        autor_id INTEGER NOT NULL REFERENCES usuarios(id),
        fecha TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS opiniones(
        id SERIAL PRIMARY KEY,
        autor_id INTEGER NOT NULL REFERENCES usuarios(id),
        nombre TEXT NOT NULL,
        avatar TEXT NOT NULL,
        texto TEXT NOT NULL,
        fecha TEXT NOT NULL
    )''',
    '''CREATE TABLE IF NOT EXISTS contacto_mensajes(
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        fecha TEXT NOT NULL
    )''',
]

INDICES = [
    'CREATE INDEX IF NOT EXISTS idx_temas_autor ON temas(autor_id)',
    'CREATE INDEX IF NOT EXISTS idx_respuestas_tema ON respuestas(tema_id)',
    'CREATE INDEX IF NOT EXISTS idx_respuestas_autor ON respuestas(autor_id)',
    'CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON sesiones(usuario_id)',
    'CREATE INDEX IF NOT EXISTS idx_sesiones_creado ON sesiones(creado)',
]


def columnas_usuarios(conexion):
    if ES_POSTGRES:
        filas = conexion.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'usuarios'"
        ).fetchall()
        return [f['column_name'] for f in filas]
    filas = conexion.execute('PRAGMA table_info(usuarios)').fetchall()
    return [f[1] for f in filas]


def init_esquema(ruta_sqlite, max_conexiones=5):
    conexion = conectar(ruta_sqlite, max_conexiones)
    try:
        if not ES_POSTGRES:
            conexion.execute('PRAGMA journal_mode = WAL')
        for sentencia in (ESQUEMA_POSTGRES if ES_POSTGRES else ESQUEMA_SQLITE):
            conexion.execute(sentencia)
        # La tabla usuarios puede venir de una base vieja sin la columna nombre:
        # CREATE TABLE IF NOT EXISTS no la agrega. Mismo patron para cualquier
        # columna que se sume mas adelante.
        if 'nombre' not in columnas_usuarios(conexion):
            conexion.execute('ALTER TABLE usuarios ADD COLUMN nombre TEXT')
        for indice in INDICES:
            conexion.execute(indice)
        conexion.commit()
    finally:
        conexion.close()


def cerrar_pool():
    global _pool
    with _lock:
        if _pool is not None:
            _pool.close()
            _pool = None
