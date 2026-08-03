const HEADER_HTML = `
<header class="site-header">
    <nav class="nav container" aria-label="Navegación principal">
        <a class="nav-logo" href="/"><img class="nav-logo-img" src="/static/img/logo.svg" alt=""><span>Manarem</span></a>
        <button class="nav-toggle" aria-expanded="false" aria-controls="nav-menu" aria-label="Abrir menú">
            <span></span><span></span><span></span>
        </button>
        <div class="nav-menu" id="nav-menu">
            <a class="nav-link" href="/">Home</a>
            <a class="nav-link" href="/recomend">Recomendados</a>
            <a class="nav-link" href="/musica">Música</a>
            <a class="nav-link" href="/foro">Foro</a>
            <div class="nav-drop">
                <button class="nav-link nav-drop-btn" aria-expanded="false">Otros ▾</button>
                <div class="nav-drop-panel">
                    <a class="nav-link" href="/acerca-de">Acerca de</a>
                    <a class="nav-link" href="/contacto">Contacto</a>
                    <a class="nav-link" href="/preguntas-frecuentes">Preguntas frecuentes</a>
                    <a class="nav-link" href="/opiniones">Opiniones</a>
                </div>
            </div>
            <div class="nav-auth">
                <a class="nav-link nav-cta" id="h_ingresar" href="/ingresar">Iniciar sesión</a>
                <a class="nav-link" id="h_salir" href="#" hidden>Salir</a>
            </div>
        </div>
    </nav>
</header>`;

const FOOTER_HTML = `
<footer class="site-footer">
    <div class="container footer-grid">
        <div class="footer-brand">
            <p class="footer-logo"><img class="footer-logo-img" src="/static/img/logo.svg" alt=""><span>Manarem</span></p>
            <p class="footer-tag">Descubrí animes, mangas y su música, todo en un solo lugar.</p>
        </div>
        <nav class="footer-nav" aria-label="Enlaces del sitio">
            <a href="/recomend">Recomendados</a>
            <a href="/musica">Música</a>
            <a href="/opiniones">Opiniones</a>
            <a href="/contacto">Contacto</a>
        </nav>
        <div class="footer-authors">
            <p>Creado por</p>
            <a href="https://github.com/Anatsu1" target="_blank" rel="noopener">Cesar Augusto Fernandez Carbonell</a>
            <a href="https://github.com/Jodenly9" target="_blank" rel="noopener">John CV</a>
            <a href="https://github.com/Quiroz-Monica-R" target="_blank" rel="noopener">Monica Quiroz</a>
        </div>
    </div>
    <div class="footer-bottom">
        <p>&copy; 2024 Manarem &bull; Hecho con HTML5, CSS3, JavaScript y Python</p>
    </div>
</footer>`;

const OCEAN_BG_HTML = `
<div class="ocean-bg" aria-hidden="true">
    <video autoplay muted loop playsinline preload="auto" poster="/static/img/fondo.jpg">
        <source src="/static/video/ocean.mp4" type="video/mp4">
    </video>
</div>`;

function renderLayout() {
    if (document.body.dataset.bg === 'ocean') {
        document.body.insertAdjacentHTML('afterbegin', OCEAN_BG_HTML);
    }
    document.body.insertAdjacentHTML('afterbegin', HEADER_HTML);
    document.body.insertAdjacentHTML('beforeend', FOOTER_HTML);

    const path = window.location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('.nav-menu > .nav-link, .nav-drop-panel .nav-link').forEach((link) => {
        const href = link.getAttribute('href').replace(/\/$/, '') || '/';
        if (href === path) link.classList.add('is-active');
    });

    const toggle = document.querySelector('.nav-toggle');
    const menu = document.getElementById('nav-menu');
    toggle.addEventListener('click', () => {
        const open = menu.classList.toggle('is-open');
        toggle.setAttribute('aria-expanded', String(open));
    });

    const dropBtn = document.querySelector('.nav-drop-btn');
    const drop = dropBtn.parentElement;
    dropBtn.addEventListener('click', () => {
        const open = drop.classList.toggle('is-open');
        dropBtn.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', (e) => {
        if (!drop.contains(e.target) && drop.classList.contains('is-open')) {
            drop.classList.remove('is-open');
            dropBtn.setAttribute('aria-expanded', 'false');
        }
    });
}

renderLayout();
