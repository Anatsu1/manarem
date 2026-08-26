// ---------------------------------------------------------------------------
// Configuracion. Es el unico lugar del frontend donde se decide a que API se
// le pega. No hay build step: se edita aca, se commitea y Vercel redeploya.
// ---------------------------------------------------------------------------
const CONFIG = {
    // URL de la API en produccion.
    //
    //   ''  -> todavia no hay backend publicado. El sitio se muestra igual, con
    //          los datos simulados de mock-data.js. Es el estado seguro: nada
    //          se rompe mientras el VPS no este arriba.
    //
    //   '/api' -> usa el proxy declarado en vercel.json, que reenvia al VPS. El
    //          pedido sale al mismo origen: sin CORS y sin contenido mixto.
    //          Hay que completar el destino real en vercel.json.
    //
    //   'https://api.tu-dominio.com' -> le pega directo al backend. Requiere
    //          que el dominio de Vercel este en MANAREM_CORS_ORIGINS del VPS.
    //
    // Ver deploy/README.md.
    apiBase: '/api',

    // API cuando el sitio se sirve desde localhost (dev_server.py + app.py).
    apiBaseDev: 'http://localhost:5000',

    // true fuerza los datos simulados en todas las paginas, tambien en local.
    mockMode: false,
};

const ES_LOCAL = ['localhost', '127.0.0.1', ''].includes(window.location.hostname);

// Interruptor de emergencia sin tocar codigo: ?mock=1 prende los datos
// simulados y queda guardado; ?mock=0 los apaga. Sirve para mostrar el sitio
// aunque el VPS este caido.
(function leerInterruptorMock() {
    const pedido = new URLSearchParams(window.location.search).get('mock');
    if (pedido === null) return;
    try {
        if (pedido === '0') localStorage.removeItem('manarem_mock');
        else localStorage.setItem('manarem_mock', '1');
    } catch (e) {}
})();

function mockActivo() {
    if (CONFIG.mockMode) return true;
    // Sin API configurada no hay a donde pegarle: se cae a los mocks en vez de
    // dejar la mitad del sitio tirando errores.
    if (!(ES_LOCAL ? CONFIG.apiBaseDev : CONFIG.apiBase)) return true;
    try {
        return localStorage.getItem('manarem_mock') === '1';
    } catch (e) {
        return false;
    }
}

const API_BASE = ES_LOCAL ? CONFIG.apiBaseDev : CONFIG.apiBase;
const MOCK_MODE = mockActivo();

function mockRequest(method, path, data) {
    return new Promise(resolve => {
        setTimeout(() => {
            const parts = path.split('/').filter(Boolean);

            if (method === 'POST' && path === '/login') {
                const usuario = data.usuario || data.email || 'Otaku';
                const email = data.email || '';
                const nombre = data.nombre || usuario;
                const token = 'mock-token-' + Date.now();
                resolve({ mensaje: 'Inicio de sesion exitoso', token, usuario: { id: 1, usuario, nombre, email } });
                return;
            }

            if (method === 'POST' && path === '/registro') {
                resolve({ mensaje: 'Registro exitoso' });
                return;
            }

            if (method === 'POST' && path === '/contacto') {
                resolve({ mensaje: 'Mensaje enviado' });
                return;
            }

            if (method === 'GET' && path === '/opiniones') {
                resolve(MOCK_DB.opiniones);
                return;
            }

            if (method === 'POST' && path === '/opiniones') {
                const userRaw = localStorage.getItem('user');
                if (!userRaw) {
                    resolve({ error: 'No autenticado' });
                    return;
                }
                const user = JSON.parse(userRaw);
                const maxId = MOCK_DB.opiniones.reduce((m, o) => Math.max(m, o.id), 0);
                const val = data instanceof FormData ? v => data.get(v) : v => data[v];
                const hoy = new Date();
                const fecha = hoy.getFullYear() + '-' + String(hoy.getMonth() + 1).padStart(2, '0') + '-' + String(hoy.getDate()).padStart(2, '0');
                MOCK_DB.opiniones.push({
                    id: maxId + 1,
                    nombre: user.usuario || 'Usuario',
                    avatar: 'persona1-f.jpg',
                    texto: val('texto') || val('opinion') || '',
                    fecha,
                });
                resolve({ mensaje: 'Opinion enviada', id: maxId + 1 });
                return;
            }

            if (method === 'POST' && path === '/logout') {
                resolve({ mensaje: 'Sesion cerrada' });
                return;
            }

            if (method === 'GET' && path === '/perfil') {
                const userRaw = localStorage.getItem('user');
                if (!userRaw) {
                    resolve({ error: 'No autenticado' });
                    return;
                }
                const user = JSON.parse(userRaw);
                const mios = MOCK_DB.temas.filter(t => t.autor === user.usuario);
                let totalRespuestas = 0;
                MOCK_DB.temas.forEach(t => t.respuestas.forEach(r => {
                    if (r.autor === user.usuario) totalRespuestas++;
                }));
                resolve({
                    usuario: user.usuario,
                    nombre: user.nombre || user.usuario,
                    email: user.email || '',
                    creado: user.creado || '—',
                    total_temas: mios.length,
                    total_respuestas: totalRespuestas,
                    temas: mios
                        .slice()
                        .sort((a, b) => b.id - a.id)
                        .map(t => ({ id: t.id, titulo: t.titulo, categoria: t.categoria, fecha: t.fecha })),
                });
                return;
            }

            if (method === 'GET' && parts[0] === 'foro' && parts[1] === 'temas' && !parts[2]) {
                const res = MOCK_DB.temas.map(t => ({
                    id: t.id, titulo: t.titulo, categoria: t.categoria,
                    autor: t.autor, fecha: t.fecha, respuestas: t.respuestas.length,
                }));
                resolve(res);
                return;
            }

            if (method === 'GET' && parts[0] === 'foro' && parts[1] === 'temas' && parts[2]) {
                const tema = MOCK_DB.temas.find(t => t.id === parseInt(parts[2]));
                resolve(tema || { error: 'Tema no encontrado' });
                return;
            }

            if (method === 'POST' && path === '/foro/temas') {
                const userRaw = localStorage.getItem('user');
                if (!userRaw) {
                    resolve({ error: 'No autenticado' });
                    return;
                }
                const user = JSON.parse(userRaw);
                const maxId = MOCK_DB.temas.reduce((m, t) => Math.max(m, t.id), 0);
                const hoy = new Date();
                const fecha = hoy.getFullYear() + '-' + String(hoy.getMonth() + 1).padStart(2, '0') + '-' + String(hoy.getDate()).padStart(2, '0');
                MOCK_DB.temas.push({
                    id: maxId + 1,
                    titulo: data.titulo,
                    categoria: data.categoria,
                    autor: user.usuario,
                    fecha,
                    contenido: data.contenido,
                    respuestas: [],
                });
                resolve({ mensaje: 'Tema creado', id: maxId + 1 });
                return;
            }

            if (method === 'POST' && parts[0] === 'foro' && parts[1] === 'temas' && parts[2] && parts[3] === 'respuestas') {
                const tema = MOCK_DB.temas.find(t => t.id === parseInt(parts[2]));
                if (!tema) {
                    resolve({ error: 'Tema no encontrado' });
                    return;
                }
                const userRaw = localStorage.getItem('user');
                if (!userRaw) {
                    resolve({ error: 'No autenticado' });
                    return;
                }
                const user = JSON.parse(userRaw);
                const hoy = new Date();
                const fecha = hoy.getFullYear() + '-' + String(hoy.getMonth() + 1).padStart(2, '0') + '-' + String(hoy.getDate()).padStart(2, '0');
                let maxRespId = 100;
                MOCK_DB.temas.forEach(t => t.respuestas.forEach(r => { if (r.id > maxRespId) maxRespId = r.id; }));
                tema.respuestas.push({
                    id: maxRespId + 1,
                    autor: user.usuario,
                    fecha,
                    contenido: data.contenido,
                });
                resolve({ mensaje: 'Respuesta publicada', id: maxRespId + 1 });
                return;
            }

            if (method === 'GET' && path === '/salud') {
                resolve({ estado: 'mock' });
                return;
            }

            resolve({ error: 'Ruta no implementada en mock' });
        }, 300);
    });
}

function tokenGuardado() {
    try {
        const userRaw = localStorage.getItem('user');
        if (!userRaw) return null;
        return JSON.parse(userRaw).token || null;
    } catch (e) {
        return null;
    }
}

// Siempre resuelve: nunca tira. Los errores de red, los HTML de error de un
// proxy y los estados 4xx/5xx salen todos como { error: '...' }, que es lo que
// esperan las paginas.
async function apiRequest(method, path, data) {
    if (MOCK_MODE) return mockRequest(method, path, data);

    const options = { method, headers: {} };

    const token = tokenGuardado();
    if (token) options.headers['Authorization'] = 'Bearer ' + token;

    if (data instanceof FormData) {
        options.body = data;
    } else if (data) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(data);
    }

    let respuesta;
    try {
        respuesta = await fetch(`${API_BASE}${path}`, options);
    } catch (e) {
        return { error: 'No se pudo conectar con el servidor.' };
    }

    // Token vencido o revocado: la sesion local ya no sirve.
    if (respuesta.status === 401 && token) {
        try { localStorage.removeItem('user'); } catch (e) {}
    }

    let cuerpo = null;
    try {
        cuerpo = await respuesta.json();
    } catch (e) {}

    if (cuerpo === null || cuerpo === undefined) {
        return respuesta.ok ? {} : { error: `El servidor respondio ${respuesta.status}.` };
    }

    if (!respuesta.ok) {
        const detalle = (cuerpo && cuerpo.error) || `El servidor respondio ${respuesta.status}.`;
        return { error: detalle };
    }

    return cuerpo;
}

const api = {
    auth: {
        registro: (data) => apiRequest('POST', '/registro', data),
        login: (data) => apiRequest('POST', '/login', data),
        logout: () => apiRequest('POST', '/logout'),
    },
    contacto: {
        enviar: (data) => apiRequest('POST', '/contacto', data),
    },
    perfil: {
        obtener: () => apiRequest('GET', '/perfil'),
    },
    opiniones: {
        listar: () => apiRequest('GET', '/opiniones'),
        crear: (data) => apiRequest('POST', '/opiniones', data),
    },
    foro: {
        listarTemas: () => apiRequest('GET', '/foro/temas'),
        obtenerTema: (id) => apiRequest('GET', '/foro/temas/' + encodeURIComponent(id)),
        crearTema: (data) => apiRequest('POST', '/foro/temas', data),
        responder: (id, data) => apiRequest('POST', '/foro/temas/' + encodeURIComponent(id) + '/respuestas', data),
    },
    salud: () => apiRequest('GET', '/salud'),
};
