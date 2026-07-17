const chatContainer = document.getElementById('chatContainer');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;

  addMessage(text, 'user');
  messageInput.value = '';

  const typingId = showTyping();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    removeTyping(typingId);
    addMessage(data.response, 'bot');
  } catch (err) {
    removeTyping(typingId);
    addMessage('Lo siento, ocurrió un error al procesar tu mensaje.', 'bot');
  }
});

messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event('submit'));
  }
});

function addMessage(text, sender) {
  const div = document.createElement('div');
  div.className = `message ${sender}-message`;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');

  div.appendChild(bubble);
  chatContainer.appendChild(div);

  if (sender === 'user') {
    scrollToBottom();
  } else {
    setTimeout(() => div.scrollIntoView({ block: 'start', behavior: 'smooth' }), 50);
  }
}

function showTyping() {
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'message bot-message';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

  div.appendChild(bubble);
  chatContainer.appendChild(div);
  scrollToBottom();
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

messageInput.focus();

let favoriteIds = [];

async function loadFavorites() {
  try {
    const res = await fetch('/api/favorites');
    if (res.ok) {
      const data = await res.json();
      favoriteIds = data.favorite_ids;
      markHearts();
      const btn = document.getElementById('btnLogout');
      if (btn) btn.style.display = '';
    }
  } catch(e) {}
}

function markHearts() {
  document.querySelectorAll('.fav-heart').forEach(el => {
    const id = parseInt(el.dataset.id);
    if (favoriteIds.includes(id)) {
      el.textContent = '❤️';
      el.style.color = '#e94560';
    } else {
      el.textContent = '♡';
      el.style.color = '#888';
    }
  });
}

chatContainer.addEventListener('click', async (e) => {
  const heart = e.target.closest('.fav-heart');
  if (!heart) return;
  const movieId = parseInt(heart.dataset.id);
  const isFav = favoriteIds.includes(movieId);
  try {
    if (isFav) {
      const res = await fetch('/api/favorites/' + movieId, { method: 'DELETE' });
      if (res.ok) {
        favoriteIds = favoriteIds.filter(id => id !== movieId);
        markHearts();
      }
    } else {
      const res = await fetch('/api/favorites/' + movieId, { method: 'POST' });
      if (res.ok) {
        favoriteIds.push(movieId);
        markHearts();
      }
    }
  } catch(e) {}
});

loadFavorites();

// Capturar clicks en "▶ Ver detalle" dentro del chat
chatContainer.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn-detail');
  if (btn) {
    e.preventDefault();
    showMovieDetail(btn.getAttribute('href').split('/').pop());
  }
});


