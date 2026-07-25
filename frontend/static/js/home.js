function sinAcentos(texto) {
    return (texto || '').normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function limpiarDescripcion(html, max) {
    const texto = (html || '').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
    if (!texto) return 'Sin descripcion disponible.';
    return texto.length > max ? texto.slice(0, max).trimEnd() + '…' : texto;
}

async function catalogoAniList() {
    const query = `{
        Page(perPage: 20) {
            media(type: ANIME, sort: TRENDING_DESC) {
                bannerImage
                title { romaji english }
                coverImage { extraLarge }
                genres
                averageScore
                siteUrl
                description
            }
        }
    }`;
    const res = await fetch('https://graphql.anilist.co', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error('AniList ' + res.status);
    const json = await res.json();
    const media = json.data.Page.media;
    const destacados = media
        .filter((m) => m.coverImage && m.coverImage.extraLarge)
        .slice(0, 8)
        .map((m) => ({
            titulo: m.title.english || m.title.romaji,
            imagen: m.coverImage.extraLarge,
            banner: m.bannerImage,
            descripcion: limpiarDescripcion(m.description, 110),
            generos: (m.genres || []).slice(0, 2),
            puntaje: m.averageScore,
            url: m.siteUrl,
        }));
    // El carrousel del hero usa solo las imagenes de los destacados
    return {
        banners: destacados.map((d) => d.banner || d.imagen).filter(Boolean),
        destacados,
    };
}

async function catalogoJikan() {
    const res = await fetch('https://api.jikan.moe/v4/top/anime?limit=8');
    if (!res.ok) throw new Error('Jikan ' + res.status);
    const json = await res.json();
    const items = json.data || [];
    const destacados = items.map((a) => ({
        titulo: a.title_english || a.title,
        imagen: a.images.jpg.large_image_url,
        descripcion: limpiarDescripcion(a.synopsis, 110),
        generos: (a.genres || []).slice(0, 2).map((g) => g.name),
        puntaje: a.score ? Math.round(a.score * 10) : null,
        url: a.url,
    }));
    return {
        banners: destacados.map((d) => d.imagen).filter(Boolean),
        destacados,
    };
}

function precargar(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(url);
        img.onerror = reject;
        img.src = url;
    });
}

function pintarSlides(banners) {
    const slides = document.querySelectorAll('.hero-slide');
    const elegidas = banners.slice(0, slides.length);
    if (elegidas.length < slides.length) return Promise.resolve();
    return Promise.all(elegidas.map(precargar)).then(() => {
        slides.forEach((slide, i) => {
            slide.style.backgroundImage = `url("${elegidas[i]}")`;
        });
    }).catch(() => {});
}

function pintarDestacados(destacados) {
    const grid = document.getElementById('destacados-grid');
    if (!grid || !destacados.length) return;
    grid.innerHTML = destacados.map((d) => `
        <article class="card">
            <div class="card-media">
                <img src="${d.imagen}" alt="Portada de ${sinAcentos(d.titulo)}" loading="lazy">
                <span class="card-badge">${d.puntaje ? '★ ' + d.puntaje + '%' : 'Anime'}</span>
            </div>
            <div class="card-body">
                <h3 class="card-title">${sinAcentos(d.titulo)}</h3>
                <p class="card-text">${d.descripcion}</p>
                <div class="card-tags">
                    ${d.generos.map((g) => `<span class="card-tag">${g}</span>`).join('')}
                </div>
                <div class="card-links">
                    <a href="${d.url}" target="_blank" rel="noopener">Ver ficha completa</a>
                </div>
            </div>
        </article>
    `).join('');
    if (typeof setupCardClamp === 'function') setupCardClamp(grid);
}

async function cargarCatalogo() {
    let catalogo;
    try {
        catalogo = await catalogoAniList();
    } catch (e) {
        try {
            catalogo = await catalogoJikan();
        } catch (e2) {
            return;
        }
    }
    pintarSlides(catalogo.banners);
    pintarDestacados(catalogo.destacados);
}

async function cargarForoHome() {
    const cont = document.getElementById('foro-home');
    if (!cont) return;
    try {
        const temas = await api.foro.listarTemas();
        const top = temas.slice().sort((a, b) => b.respuestas - a.respuestas).slice(0, 3);
        if (!top.length) {
            cont.innerHTML = '<div class="foro-aviso">Todavia no hay temas. <a href="/foro">Crea el primero</a>.</div>';
            return;
        }
        cont.innerHTML = top.map((t) => `
            <article class="tema-card">
                <a class="tema-titulo" href="/foro/tema?id=${t.id}"><h3>${sinAcentos(t.titulo)}</h3></a>
                <div class="tema-meta">
                    <span class="tema-badge tema-badge--${t.categoria}">${t.categoria}</span>
                    <span>por ${t.autor}</span>
                    <time datetime="${t.fecha}">${t.fecha}</time>
                    <span class="tema-respuestas">${t.respuestas} respuestas</span>
                </div>
            </article>
        `).join('');
    } catch (e) {
        cont.innerHTML = '<div class="foro-aviso">No se pudo cargar el foro. <a href="/foro">Ir al foro</a>.</div>';
    }
}

cargarCatalogo();
cargarForoHome();
