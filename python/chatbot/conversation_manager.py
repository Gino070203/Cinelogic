# ──────────────────────────────────────────────
# ConversationManager: memoria de la conversación
# ──────────────────────────────────────────────
# Cada usuario tiene una sesión en su cookie HTTP.
# La sesión guarda:
#   - Lo que ya ha elegido (género, década, etc.)
#   - En qué paso de la conversación va
#   - Los últimos resultados para poder pedir "más opciones"
#
# Esto permite que el bot pregunte paso a paso:
#   ¿género? → ¿década? → ¿duración? → ¿calificación? → mostrar

class ConversationManager:
    def ensure(self, session):
        if "preferences" not in session:
            session["preferences"] = {}
        if "step" not in session:
            session["step"] = "greeting"
        if "last_results" not in session:
            session["last_results"] = []
        if "offset" not in session:
            session["offset"] = 0
        return session

    def update_preferences(self, session, new_prefs, skip_current=False):
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

        for k, v in new_prefs.items():
            if v:
                if k == "genres":
                    existing = session["preferences"].get("genres", [])
                    session["preferences"]["genres"] = list(set(existing + v))
                else:
                    session["preferences"][k] = v
        return session

    def determine_next_step(self, session):
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

    def advance_step(self, session):
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

    def reset(self, session):
        for key in ["preferences", "step", "last_results", "offset", "pending_keep_filters"]:
            session.pop(key, None)
        self.ensure(session)

    def soft_reset_genre(self, session):
        session["preferences"].pop("genres", None)
        session["last_results"] = []
        session["offset"] = 0
        prefs = session["preferences"]
        has_decade = prefs.get("decade") not in (None, "any")
        has_runtime = prefs.get("runtime") not in (None, "any")
        has_rating = prefs.get("min_rating") not in (None, 0)
        session["pending_keep_filters"] = has_decade or has_runtime or has_rating

    def clear_secondary_filters(self, session):
        for k in ["decade", "runtime", "min_rating"]:
            session["preferences"].pop(k, None)
        session["last_results"] = []
        session["offset"] = 0
        session["pending_keep_filters"] = False
