function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.style.cssText = `
        position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
        padding: 12px 24px; border-radius: 8px; z-index: 1000;
        font-size: 0.95rem; max-width: 90%; text-align: center;
        background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#ff9800'};
        color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: fadeIn 0.3s ease;
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        alertDiv.style.transition = 'opacity 0.5s';
        setTimeout(() => alertDiv.remove(), 500);
    }, 4000);
}

async function handleFormSubmit(formId, apiCall, successMessage, redirectUrl) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const data = {};
        formData.forEach((value, key) => { data[key] = value; });

        try {
            const result = await apiCall(data);

            if (result.error) {
                showAlert(`Error: ${result.error}`, 'error');
            } else if (result.mensaje) {
                showAlert(result.mensaje, 'success');
                if (redirectUrl) {
                    setTimeout(() => window.location.href = redirectUrl, 1500);
                }
            } else {
                showAlert(successMessage, 'success');
                if (redirectUrl) {
                    setTimeout(() => window.location.href = redirectUrl, 1500);
                }
            }
        } catch (error) {
            showAlert('No se pudo conectar con el servidor. Verificá que el backend esté funcionando.', 'error');
            console.error('Error de conexión:', error);
        }
    });
}

function checkAuth() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
}

function updateNav() {
    const user = checkAuth();
    const loginLink = document.getElementById('h_ingresar');
    const registerLink = document.getElementById('h_registrarse');

    if (user && loginLink && registerLink) {
        loginLink.textContent = user.usuario || 'Cuenta';
        loginLink.href = '/perfil';
        registerLink.textContent = 'Salir';
        registerLink.href = '#';
        registerLink.onclick = async (e) => {
            e.preventDefault();
            try { await api.auth.logout(); } catch (_) {}
            localStorage.removeItem('user');
            window.location.href = '/';
        };
    }
}

// Limita el texto de las cards a unas pocas lineas y agrega "Ver mas" solo si
// el contenido se corta, para que todas las cards mantengan el mismo alto.
function setupCardClamp(root) {
    const scope = root || document;
    scope.querySelectorAll('.card-text').forEach((el) => {
        if (el.dataset.clampReady) return;
        el.dataset.clampReady = '1';
        if (el.scrollHeight - el.clientHeight <= 2) return;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'card-more';
        btn.textContent = 'Ver mas';
        btn.addEventListener('click', () => {
            const abierto = el.classList.toggle('is-expanded');
            btn.textContent = abierto ? 'Ver menos' : 'Ver mas';
        });
        el.insertAdjacentElement('afterend', btn);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    updateNav();
    setupCardClamp();
});
