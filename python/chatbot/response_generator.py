# ──────────────────────────────────────────────
# ResponseGenerator: genera las respuestas del bot
# ──────────────────────────────────────────────
# Este módulo produce el texto y HTML que el usuario
# ve en pantalla. Tiene métodos para cada tipo de
# respuesta: preguntas, tarjetas de películas, etc.

import random
import json
import html


class ResponseGenerator:
    """
    Genera las respuestas textuales y HTML del chatbot.
    Cada método produce un tipo distinto de mensaje.
    """

    def __init__(self):
        # Mensajes para cuando el bot no entiende bien lo que quiere el usuario
        self.clarifications = [
            "¡Cuéntame más! ¿Prefieres algún género en particular? ¿Tal vez una década específica? Dime cualquier detalle.",
            "Dame más pistas, amigo cinéfilo... ¿acción, comedia, terror o ciencia ficción? ¿De qué año?",
            "¿Buscas algo ligero para reír o algo intenso que te mantenga al borde del asiento? ¿Algún actor o director que admires?",
            "Explícame mejor: ¿qué estado de ánimo tienes? ¿Una película de culto, un clásico, o algo más moderno?",
        ]

        # Mensajes cuando no se encuentra ninguna película
        self.no_result_messages = [
            "Vaya, ni en la filmoteca más grande encontré algo que coincida 😅. ¿Intentamos con otros criterios?",
            "No encontré películas con esas características exactas. ¡Pero el cine es tan vasto! Prueba con otros detalles.",
            "Upps, mi base de datos no tiene eso que buscas. Dame otras pistas y seguro encontramos algo increíble.",
        ]

        # Medallas para las posiciones del ranking
        self.medals = ["🥇", "🥈", "🥉", " 4.", " 5."]

        # Traducción de nombres de géneros inglés → español
        self.genre_translation = {
            "Action": "Acción",
            "Adventure": "Aventura",
            "Comedy": "Comedia",
            "Crime": "Crimen",
            "Drama": "Drama",
            "Horror": "Terror",
            "Science Fiction": "Ciencia Ficción",
            "Thriller": "Thriller",
            "Romance": "Romance",
            "Fantasy": "Fantasía",
            "Animation": "Animación",
            "Mystery": "Misterio",
            "War": "Bélico",
            "Music": "Musical",
            "History": "Histórico",
            "Western": "Western",
            "Documentary": "Documental",
        }

    # ───── Formateo de nombres ─────

    def _format_actor_director(self, prefs):
        """Convierte actor/director a texto: "de Nolan con Al Pacino" (o "" si no hay)."""
        parts = []
        if prefs.get("director"):
            parts.append(f"de {prefs['director']}")
        if prefs.get("actor"):
            parts.append(f"con {prefs['actor']}")
        return " ".join(parts) if parts else ""

    # ───── Preguntas del flujo guiado ─────

    def ask_genre(self):
        """Pregunta: ¿qué género? (primer paso, cuando no hay nada elegido aún)."""
        return (
            "¡Bienvenido a CineLogic! 🎬 Soy tu crítico de cine personal.\n\n"
            "Cuéntame, **¿qué género te apetece ver?**\n\n"
            "Puedes decirme: acción, comedia, terror, ciencia ficción, "
            "drama, romance, thriller... el que tú quieras."
        )

    def ask_genre_only(self):
        """Pregunta solo el género (cuando ya hay otros datos, como década o actor)."""
        return (
            "**¿Qué género te gustaría ver?**\n\n"
            "Dime: acción, comedia, terror, ciencia ficción, drama, romance... "
            "o cualquier otro que prefieras."
        )

    def ask_genre_with_context(self, existing_prefs):
        """Pregunta el género cuando el usuario ya ha dado otros datos (década, actor, etc.)."""
        parts = []
        if existing_prefs.get("decade") and existing_prefs["decade"] not in ("any", None):
            parts.append(f"década de los {existing_prefs['decade']}s")
        if existing_prefs.get("director"):
            parts.append(f"director {existing_prefs['director']}")
        if existing_prefs.get("actor"):
            parts.append(f"actor {existing_prefs['actor']}")
        ctx = " y ".join(parts) if parts else ""

        if ctx:
            return (
                f"He anotado lo de {ctx}. Genial.\n\n"
                "**Ahora dime, ¿qué género buscas?**\n\n"
                "Acción, comedia, drama, terror... el que prefieras."
            )
        return self.ask_genre_only()

    def ask_decade(self, genre_str, prefs=None):
        """Pregunta: ¿qué década? con el género/actor ya elegido."""
        genre_es = self._translate_genre(genre_str)
        extra = self._format_actor_director(prefs or {})
        if genre_es and extra:
            desc = f"{genre_es} {extra}"
        elif extra:
            desc = extra
        else:
            desc = genre_es
        return (
            f"¡{desc}! Excelente elección. 🔥🔥\n\n"
            "**¿De qué década prefieres las películas?**\n\n"
            "Ejemplos: 80s, 90s, 2000s, 2010s...\n"
            "O dime **'cualquiera'** si no te importa el año."
        )

    def ask_runtime(self, genre_str, decade_str, prefs=None):
        """Pregunta: ¿qué duración? con género/década/actor ya elegidos."""
        genre_es = self._translate_genre(genre_str)
        extra = self._format_actor_director(prefs or {})
        parts = [p for p in [genre_es, extra, decade_str] if p]
        desc = " ".join(parts)
        return (
            f"¡Perfecto! {desc} suena genial. 🎬\n\n"
            "**¿Qué duración prefieres?**\n\n"
            "• **Cortas** — menos de 90 minutos\n"
            "• **Medias** — entre 90 y 120 minutos\n"
            "• **Largas** — más de 2 horas\n\n"
            "O dime **'cualquiera'** si te da igual."
        )

    def ask_rating(self):
        """Pregunta: ¿alta calificación? (último paso antes de mostrar)"""
        return (
            "Última pregunta 🙌\n\n"
            "**¿Prefieres solo películas con alta calificación?**\n\n"
            "• **Alta** — solo las mejor valoradas (7+)\n"
            "• **Cualquiera** — sin filtro de calificación"
        )

    # ───── Generación de tarjetas de películas ─────

    def generate_recommendation(self, ranked, movies, preferences, include_header_footer=True):
        """Genera el HTML completo de las tarjetas de películas.

        Args:
            ranked: lista de {id, score} ordenada por relevancia
            movies: datos completos de las películas
            preferences: lo que pidió el usuario (para el encabezado)
            include_header_footer: si incluye el encabezado y footer

        Returns:
            String con HTML de las tarjetas
        """
        if not ranked:
            return self._no_results()

        movie_map = {int(m["id"]): m for m in movies}
        pref_desc = self._describe_preferences(preferences)

        cards = []
        for i, item in enumerate(ranked[:5]):
            movie = movie_map.get(item["id"], {})
            raw_title = movie.get("title", f"Película #{item['id']}")
            title = html.escape(raw_title)
            score = item.get("score", 0)

            # Año (de la fecha de lanzamiento)
            year = ""
            if "release_date" in movie:
                try:
                    year = str(movie["release_date"])[:4]
                except:
                    pass

            poster = movie.get("poster_url") or ""
            rating = movie.get("vote_average")

            # Medalla: 🥇🥈🥉 para top 3, "4." "5." para el resto
            medal = self.medals[i] if i < 3 else f"{i+1}."

            # Barra de score: ████████░░ 85%
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            pct = f"{score:.0%}"

            # Poster (se oculta si no carga con onerror)
            img = f'<img src="{poster}" alt="{title}" class="movie-poster" onerror="this.style.display=\'none\'" loading="lazy">' if poster else ""

            # Badge de calificación
            badge = f' <span class="rating-badge">⭐ {rating}</span>' if rating else ""

            # Géneros (vienen como JSON en el dataset)
            genres_str = ""
            try:
                genres_data = json.loads(movie.get("genres", "[]"))
                genre_names = [g["name"] for g in genres_data if g.get("name")]
                genres_str = html.escape(", ".join(genre_names))
            except:
                pass
            genres_html = f'<div class="movie-genres">Géneros: {genres_str}</div>' if genres_str else ""

            # Sinopsis
            overview = movie.get("overview", "")
            overview_html = f'<div class="movie-overview">{html.escape(overview)}</div>' if overview else ""

            snippet = genres_html + overview_html

            # Tarjeta completa
            cards.append(
                f'<div class="movie-card" style="animation-delay:{i*0.1}s">'
                f'{img}'
                f'<div class="movie-card-body">'
                f'<div class="movie-card-header">'
                f'<span class="medal">{medal}</span>'
                f'<strong>{title}</strong>'
                f'{f" <span class=\"year\">({year})</span>" if year else ""}'
                f'{badge}'
                f'</div>'
                f'<span class="fav-heart" data-id="{item["id"]}" title="Añadir a favoritos">♡</span>'
                f'<div class="movie-score">'
                f'<span class="score-bar">{bar}</span>'
                f'<span class="score-pct">{pct}</span>'
                f'</div>'
                f'{snippet}'
                f'<a href="/movie/{item["id"]}" class="btn-detail">▶ Ver detalle</a>'
                f'</div>'
                f'</div>'
            )

        header = f"🔥 ¡Aquí tienes {pref_desc}!<br><br>"
        footer = '<br><br>¿Quieres <strong>más opciones</strong> o probar con otro género?'

        if include_header_footer:
            return header + "".join(cards) + footer
        return "".join(cards)

    # ───── Traducción de géneros ─────

    def _translate_genre(self, name):
        """Traduce un nombre de género de inglés a español."""
        return self.genre_translation.get(name, name)

    def _describe_preferences(self, prefs):
        """Genera una descripción legible de las preferencias del usuario.
        Ejemplo: "Drama de los 90s con Al Pacino cortas bien calificadas (7+)" """
        parts = []
        if "genres" in prefs:
            g = [self._translate_genre(x) for x in prefs["genres"]]
            parts.append(" y ".join(g) if len(g) > 1 else g[0])
        dec = prefs.get("decade")
        if dec and dec != "any":
            parts.append(f"de los {dec}s")
        if prefs.get("director"):
            parts.append(f"dirigidas por {prefs['director']}")
        if prefs.get("actor"):
            parts.append(f"con {prefs['actor']}")
        runtime = prefs.get("runtime")
        if runtime and runtime != "any":
            labels = {"short": "cortas", "medium": "medianas", "long": "largas"}
            parts.append(labels.get(runtime, runtime))
        rating = prefs.get("min_rating")
        if rating:
            parts.append(f"bien calificadas ({rating}+)")
        return " ".join(parts) if parts else "mis recomendaciones"

    # ───── Mensajes generales ─────

    def ask_keep_filters(self, prefs):
        """Pregunta si quiere conservar los filtros secundarios (década, duración, rating).
        Se usa después de un soft reset cuando ya había otros filtros definidos."""
        parts = []
        dec = prefs.get("decade")
        if dec and dec != "any":
            parts.append(f"década de los {dec}s")
        runtime = prefs.get("runtime")
        if runtime and runtime != "any":
            labels = {"short": "cortas", "medium": "medianas", "long": "largas"}
            parts.append(labels.get(runtime, runtime))
        rating = prefs.get("min_rating")
        if rating:
            parts.append(f"alta calificación ({rating}+)")
        filters_desc = ", ".join(parts) if parts else ""

        genre_es = ""
        if prefs.get("genres"):
            genre_names = [self._translate_genre(g) for g in prefs["genres"]]
            genre_es = " y ".join(genre_names)

        msg = f"¡{genre_es}! Entendido. 🎬\n\n"
        if filters_desc:
            msg += (
                f"Tienes estos filtros guardados: **{filters_desc}**.\n\n"
                "**¿Quieres conservarlos o prefieres cambiarlos?**\n\n"
                "• **Sí** — mantener todo y mostrar resultados\n"
                "• **No** — limpiar filtros y empezar de nuevo\n"
                "• Dime qué cambiar (ej: **'década 90s'**, **'largas'**, **'cualquier calificación'**)\n"
            )
        else:
            msg += "**Dime más detalles para encontrar la película perfecta.**"
        return msg

    def ask_clarification(self):
        """Pide más detalles cuando el bot no entendió bien."""
        return random.choice(self.clarifications)

    def no_results(self):
        return self._no_results()

    def no_more_results(self):
        return (
            "No tengo más opciones con esos criterios. 😅\n\n"
            "Puedes **probar otro género** o decir **'reiniciar'** para empezar de nuevo."
        )

    def movie_not_found(self, title):
        return (
            f"No encontré '{title}' en mis registros. 🎬\n\n"
            "¿Sabes el título en inglés? O dime **qué género te gustaría ver** "
            "y te recomiendo algo similar."
        )

    def _no_results(self):
        """Mensaje cuando no hay películas que coincidan."""
        return random.choice(self.no_result_messages)
