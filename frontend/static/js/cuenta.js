function mostrarPanel(nombre) {
    document.querySelectorAll('.cuenta-tab').forEach((tab) => {
        const activo = tab.dataset.panel === nombre;
        tab.classList.toggle('is-active', activo);
        tab.setAttribute('aria-selected', activo ? 'true' : 'false');
    });

    document.querySelectorAll('.cuenta-form').forEach((form) => {
        form.hidden = form.dataset.panel !== nombre;
    });

    history.replaceState({}, '', nombre === 'registro' ? '/registrarse' : '/ingresar');
}

document.querySelectorAll('.cuenta-tab').forEach((tab) => {
    tab.addEventListener('click', () => mostrarPanel(tab.dataset.panel));
});

// Los enlaces de "¿No tenes cuenta?" apuntan a la ruta real, asi que sin JS
// igual navegan; con JS solo cambian de panel.
document.querySelectorAll('.cuenta-switch').forEach((link) => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        mostrarPanel(link.dataset.panel);
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const inicial = window.location.pathname.startsWith('/registrarse') ? 'registro' : 'login';
    mostrarPanel(inicial);

    // La transicion se habilita despues del primer pintado: si no, al abrir
    // /registrarse el subrayado se ve viajar desde la pestaña del markup.
    const tabs = document.querySelector('.cuenta-tabs');
    if (tabs) {
        void tabs.offsetWidth;
        tabs.classList.add('is-ready');
    }

    document.getElementById('panel-login').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            usuario: document.getElementById('usuario').value,
            password: document.getElementById('password').value
        };
        try {
            const result = await api.auth.login(data);
            if (result.error) {
                showAlert('Credenciales incorrectas.', 'error');
            } else {
                localStorage.setItem('user', JSON.stringify({ ...(result.usuario || {}), token: result.token }));
                showAlert('¡Inicio de sesión exitoso!', 'success');
                setTimeout(() => window.location.href = '/', 1500);
            }
        } catch (error) {
            showAlert('No se pudo conectar con el servidor.', 'error');
        }
    });

    document.getElementById('panel-registro').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            nombre: document.getElementById('nombre').value,
            usuario: document.getElementById('usuarioReg').value,
            email: document.getElementById('email').value,
            password: document.getElementById('passwordReg').value
        };
        if (data.password !== document.getElementById('password2').value) {
            showAlert('Las contraseñas no coinciden.', 'error');
            return;
        }
        try {
            const result = await api.auth.registro(data);
            if (result.error) {
                showAlert('Error: ' + result.error, 'error');
            } else {
                showAlert('¡Registro exitoso! Ahora podés iniciar sesión.', 'success');
                setTimeout(() => mostrarPanel('login'), 1500);
            }
        } catch (error) {
            showAlert('No se pudo conectar con el servidor.', 'error');
        }
    });
});