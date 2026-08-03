function sinAcentos(texto) {
    return (texto || '').normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function escaparHtml(texto) {
    return String(texto ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }[c]));
}

function urlSegura(url) {
    if (typeof url !== 'string' || !url.trim()) return null;
    try {
        const u = new URL(url, window.location.origin);
        return u.protocol === 'https:' || u.protocol === 'http:' ? u.href : null;
    } catch (e) {
        return null;
    }
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
    return { destacados };
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
    return { destacados };
}

function pintarSpot(destacado) {
    if (!destacado) return;
    const spot = document.getElementById('destacado-spot');
    if (!spot) return;

    const img = spot.querySelector('.spot-media img');
    const portada = urlSegura(destacado.imagen);
    if (img && portada) {
        img.src = portada;
        img.alt = 'Portada de ' + sinAcentos(destacado.titulo);
    }

    const titulo = spot.querySelector('.spot-title');
    if (titulo) titulo.textContent = sinAcentos(destacado.titulo);

    const meta = spot.querySelector('.spot-meta');
    if (meta) {
        meta.textContent = '';
        const etiquetas = (destacado.generos || []).map((g) => sinAcentos(g));
        if (destacado.puntaje) etiquetas.push('★ ' + destacado.puntaje + '%');
        etiquetas.forEach((texto) => {
            const tag = document.createElement('span');
            tag.className = 'card-tag';
            tag.textContent = texto;
            meta.appendChild(tag);
        });
    }

    const texto = spot.querySelector('.spot-text');
    if (texto) texto.textContent = destacado.descripcion;

    const link = spot.querySelector('.card-links a');
    const ficha = urlSegura(destacado.url);
    if (link && ficha) link.href = ficha;
}

function pintarDestacados(destacados) {
    const grid = document.getElementById('destacados-grid');
    if (!grid || !destacados.length) return;
    grid.innerHTML = destacados.slice(1).map((d) => {
        const portada = urlSegura(d.imagen);
        const ficha = urlSegura(d.url);
        const titulo = escaparHtml(sinAcentos(d.titulo));
        return `
        <article class="card">
            <div class="card-media">
                ${portada ? `<img src="${escaparHtml(portada)}" alt="Portada de ${titulo}" loading="lazy">` : ''}
                <span class="card-badge">${d.puntaje ? '★ ' + escaparHtml(d.puntaje) + '%' : 'Anime'}</span>
            </div>
            <div class="card-body">
                <h3 class="card-title">${titulo}</h3>
                <p class="card-text">${escaparHtml(d.descripcion)}</p>
                <div class="card-tags">
                    ${(d.generos || []).map((g) => `<span class="card-tag">${escaparHtml(g)}</span>`).join('')}
                </div>
                <div class="card-links">
                    ${ficha ? `<a href="${escaparHtml(ficha)}" target="_blank" rel="noopener">Ver ficha completa</a>` : ''}
                </div>
            </div>
        </article>
    `;
    }).join('');
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
    pintarSpot(catalogo.destacados[0]);
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
                <a class="tema-titulo" href="/foro/tema?id=${encodeURIComponent(t.id)}"><h3>${escaparHtml(sinAcentos(t.titulo))}</h3></a>
                <div class="tema-meta">
                    <span class="tema-badge tema-badge--${escaparHtml(t.categoria)}">${escaparHtml(t.categoria)}</span>
                    <span>por ${escaparHtml(t.autor)}</span>
                    <time datetime="${escaparHtml(t.fecha)}">${escaparHtml(t.fecha)}</time>
                    <span class="tema-respuestas">${escaparHtml(t.respuestas)} respuestas</span>
                </div>
            </article>
        `).join('');
    } catch (e) {
        cont.innerHTML = '<div class="foro-aviso">No se pudo cargar el foro. <a href="/foro">Ir al foro</a>.</div>';
    }
}

cargarCatalogo();
cargarForoHome();
