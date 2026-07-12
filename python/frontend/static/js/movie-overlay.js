function showMovieDetail(movieId) {
  const overlay = document.getElementById('movieOverlay');
  const content = document.getElementById('overlayContent');
  overlay.style.display = 'block';
  content.innerHTML = '<p class="detail-loading">Cargando...</p>';

  fetch('/api/movie/' + movieId)
    .then(r => { if (!r.ok) throw Error(); return r.json(); })
    .then(m => {
      const year = m.release_date ? String(m.release_date).slice(0, 4) : '';
      const rating = m.vote_average ? `⭐ ${m.vote_average}` : '';
      const poster = m.poster_url
        ? `<img src="${m.poster_url}" alt="${m.title}" class="detail-poster">`
        : '<div class="detail-poster" style="height:450px;background:var(--bg-card);border-radius:14px;display:flex;align-items:center;justify-content:center;color:var(--text-muted)">Sin imagen</div>';
      const trailer = m.trailer_key
        ? `<div class="trailer-wrapper"><h3>▶ Tráiler</h3><iframe src="https://www.youtube.com/embed/${m.trailer_key}" allowfullscreen></iframe></div>`
        : '<div class="trailer-wrapper"><p>No hay tráiler disponible.</p></div>';
      const directors = m.directors && m.directors.length
        ? `<p><strong>Dirección:</strong> ${m.directors.join(', ')}</p>` : '';
      const actors = m.actors && m.actors.length
        ? `<p><strong>Reparto:</strong> ${m.actors.slice(0, 5).join(', ')}</p>` : '';
      const genres = m.genres_es && m.genres_es.length
        ? `<p><strong>Géneros:</strong> ${m.genres_es.map(g => `<a href="/genre/${g.slug}" class="genre-link">${g.name_es}</a>`).join(', ')}</p>`
        : '';

      content.innerHTML = `
        <div class="detail-layout">
          ${poster}
          <div class="detail-info">
            <h1>${m.title}${year ? ` <span class="year">(${year})</span>` : ''}</h1>
            ${rating ? `<div class="rating">${rating}</div>` : ''}
            <p class="overview">${m.overview || 'Sin descripción disponible.'}</p>
            ${genres}
            ${directors}
            ${actors}
          </div>
        </div>
        ${trailer}
      `;
    })
    .catch(() => {
      content.innerHTML = '<p class="detail-loading">Error al cargar la información de esta película.</p>';
    });
}

function closeMovieOverlay() {
  const overlay = document.getElementById('movieOverlay');
  overlay.querySelectorAll('iframe').forEach(iframe => iframe.src = '');
  overlay.style.display = 'none';
}
