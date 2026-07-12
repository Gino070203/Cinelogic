# ──────────────────────────────────────────────
# ConversationManager: memoria de la conversación
# ──────────────────────────────────────────────
# Cada usuario (identificado por IP) tiene una sesión.
# La sesión guarda:
#   - Lo que ya ha elegido (género, década, etc.)
#   - En qué paso de la conversación va
#   - Los últimos resultados para poder pedir "más opciones"
#
# Esto permite que el bot pregunte paso a paso:
#   ¿género? → ¿década? → ¿duración? → ¿calificación? → mostrar

import time


class ConversationManager:
    """
    Administra las sesiones de los usuarios.
    self.sessions = {
        "127.0.0.1": {
            "preferences": {"genres": ["Drama"], "decade": 1990, ...},
            "last_active": 1234567890,
            "step": "ask_runtime",
            "last_results": [{"id": 238, "score": 0.85}, ...],
            "offset": 0
        }
    }
    """

    def __init__(self):
        self.sessions = {}

    def _cleanup(self):
        """Elimina sesiones inactivas (>10 minutos sin actividad)."""
        now = time.time()
        expired = [
            k for k, v in self.sessions.items()
            if now - v.get("last_active", 0) > 600
        ]
        for k in expired:
            del self.sessions[k]

    def get_or_create(self, client_id):
        """Obtiene la sesión de un usuario. Si no existe, la crea."""
        self._cleanup()
        if client_id not in self.sessions:
            self.sessions[client_id] = {
                "preferences": {},        # nada elegido aún
                "last_active": time.time(),
                "step": "greeting",       # recién llegó
                "last_results": [],       # últimos resultados (para "más opciones")
                "offset": 0,              # para paginar resultados
            }
        return self.sessions[client_id]

    def update_preferences(self, client_id, new_prefs, skip_current=False):
        """Actualiza las preferencias del usuario en su sesión.

        Si skip_current=True: el usuario dijo "cualquiera"/"da igual".
            → Completa los campos faltantes con valores por defecto.
        Si no: acumula las nuevas preferencias con las existentes.
        """
        session = self.get_or_create(client_id)
        session["last_active"] = time.time()

        # ─── El usuario dijo "cualquiera" ───
        if skip_current:
            prefs = session["preferences"]
            tiene_id = prefs.get("genres") or prefs.get("actor") or prefs.get("director")
            if tiene_id and prefs.get("decade") is None:
                session["preferences"]["decade"] = "any"
            if tiene_id and prefs.get("runtime") is None:
                session["preferences"]["runtime"] = "any"
            if tiene_id and prefs.get("min_rating") is None:
                session["preferences"]["min_rating"] = 0
            return session

        # ─── El usuario dio preferencias nuevas ───
        for k, v in new_prefs.items():
            if v:
                if k == "genres":
                    # Acumula géneros (no reemplaza)
                    existing = session["preferences"].get("genres", [])
                    session["preferences"]["genres"] = list(set(existing + v))
                else:
                    # Reemplaza (década, actor, runtime, etc.)
                    session["preferences"][k] = v

        return session

    def determine_next_step(self, session):
        """Determina qué sigue en la conversación según lo que ya tenga el usuario.

        Orden de preguntas:
        1. ¿Género o actor/director?
        2. ¿Década?
        3. ¿Duración?
        4. ¿Calificación?
        5. ¡Todo listo, mostrar resultados!
        """
        prefs = session["preferences"]
        tiene_persona = prefs.get("actor") or prefs.get("director")
        if not prefs.get("genres") and not tiene_persona:
            return "ask_genre"
        if prefs.get("decade") is None:
            return "ask_decade"
        if prefs.get("runtime") is None:
            return "ask_runtime"
        if prefs.get("min_rating") is None:
            return "ask_rating"
        return "show_results"

    def advance_step(self, client_id):
        """Avanza al siguiente paso de la conversación (obsoleto, se usa determine_next_step)."""
        session = self.get_or_create(client_id)
        session["last_active"] = time.time()
        mapping = {
            "greeting": "ask_genre",
            "ask_genre": "ask_decade",
            "ask_decade": "ask_runtime",
            "ask_runtime": "ask_rating",
            "ask_rating": "show_results",
            "show_results": "show_results",
        }
        current = session.get("step", "greeting")
        session["step"] = mapping.get(current, "show_results")
        return session

    def reset_session(self, client_id):
        """Borra toda la sesión del usuario (empieza de nuevo)."""
        if client_id in self.sessions:
            del self.sessions[client_id]

    def soft_reset_genre(self, client_id):
        """Limpia solo los géneros de la sesión, conservando década/actor/director.
        Útil cuando el usuario dice 'probar otro género' pero ya había dado otros datos."""
        session = self.get_or_create(client_id)
        session["preferences"].pop("genres", None)
        session["last_results"] = []
        session["offset"] = 0
        session["last_active"] = time.time()
        # Si hay otros filtros reales (década, duración, rating), marcarlo para preguntar
        prefs = session["preferences"]
        has_decade = prefs.get("decade") not in (None, "any")
        has_runtime = prefs.get("runtime") not in (None, "any")
        has_rating = prefs.get("min_rating") not in (None, 0)
        session["pending_keep_filters"] = has_decade or has_runtime or has_rating

    def clear_secondary_filters(self, client_id):
        """Limpia década, duración y calificación, conservando género.
        Se usa cuando el usuario dice 'no' a conservar filtros viejos."""
        session = self.get_or_create(client_id)
        for k in ["decade", "runtime", "min_rating"]:
            session["preferences"].pop(k, None)
        session["last_results"] = []
        session["offset"] = 0
        session["pending_keep_filters"] = False
        session["last_active"] = time.time()
