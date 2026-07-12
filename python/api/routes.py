import json
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from pathlib import Path
from nlp.intent_parser import IntentParser
from integration.prolog_bridge import PrologBridge
from integration.scala_bridge import ScalaBridge
from integration.tmdb_client import TMDBClient
from data.loader import MovieLoader
from data.translator import TitleTranslator
from chatbot.response_generator import ResponseGenerator
from chatbot.conversation_manager import ConversationManager

BASE = Path(__file__).resolve().parent.parent

router = APIRouter()

# Genre mapping: Spanish URL slug → English genre name
GENRE_SLUG_MAP = {
    "accion": "Action", "acción": "Action",
    "aventura": "Adventure",
    "comedia": "Comedy",
    "crimen": "Crime",
    "drama": "Drama",
    "terror": "Horror",
    "ciencia-ficcion": "Science Fiction",
    "suspenso": "Thriller", "suspense": "Thriller",
    "romance": "Romance",
    "fantasia": "Fantasy", "fantasía": "Fantasy",
    "animacion": "Animation", "animación": "Animation",
    "misterio": "Mystery",
    "belico": "War", "bélico": "War",
    "musical": "Music",
    "historico": "History", "histórico": "History",
    "western": "Western",
    "documental": "Documentary",
}

# English genre name → Spanish display name
EN_TO_ES = {
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


def _movie_genres_es(movie):
    """Extract genre names from movie and return list of {name_es, slug}."""
    result = []
    try:
        raw = movie.get("genres", "[]")
        if isinstance(raw, str):
            genres_data = json.loads(raw)
        elif isinstance(raw, list):
            genres_data = raw
        else:
            return result
        for g in genres_data:
            name_en = g.get("name", "")
            name_es = EN_TO_ES.get(name_en, name_en)
            slug = next((s for s, en in GENRE_SLUG_MAP.items() if en == name_en), "")
            if slug:
                result.append({"name_es": name_es, "slug": slug})
    except (json.JSONDecodeError, TypeError):
        pass
    return result

# Esquema de entrada para el endpoint /chat
class ChatMessage(BaseModel):
    message: str

# Extrae preferencias de una película existente (útil para "parecida a X")
def _prefs_from_movie(movie, movie_loader):
    prefs = {}
    try:
        genres_data = json.loads(movie.get("genres", "[]"))
        if genres_data:
            prefs["genres"] = [g["name"] for g in genres_data if g.get("name")]
    except (json.JSONDecodeError, TypeError):
        pass
    mid = int(movie["id"])
    boosts = []
    actors = movie_loader.get_actors(mid)
    if actors:
        boosts.append(actors[0])
    directors = movie_loader.get_directors(mid)
    if directors:
        boosts.append(directors[0])
    if boosts:
        prefs["query_boosts"] = " ".join(boosts)
    return prefs

# Ranking simple: ordena películas por vote_average descendente
def _rank_by_vote(movies, top_n=10):
    with_scores = []
    for m in movies:
        vote = float(m.get("vote_average", 0))
        score = vote / 10.0
        with_scores.append({"id": int(m["id"]), "score": round(score, 2)})
    with_scores.sort(key=lambda x: x["score"], reverse=True)
    return with_scores[:top_n]

# Ranking por popularidad descendente (usado cuando el usuario pide "populares")
def _rank_by_popularity(movies, top_n=10):
    sorted_movies = sorted(
        movies, key=lambda m: float(m.get("popularity", 0)), reverse=True
    )
    ranked = []
    for i, m in enumerate(sorted_movies[:top_n]):
        score = max(0.1, 1.0 - (i * 0.10))
        ranked.append({"id": int(m["id"]), "score": round(score, 2)})
    return ranked

# Instancia global de todos los módulos del sistema (singletons)
movie_loader = MovieLoader()
intent_parser = IntentParser()
prolog_bridge = PrologBridge()
scala_bridge = ScalaBridge(movie_loader=movie_loader)
tmdb_client = TMDBClient()
response_gen = ResponseGenerator()
title_translator = TitleTranslator()
conv_manager = ConversationManager()

# Adjunta URLs de pósters a las películas usando TMDB
def _attach_posters(movies):
    for m in movies:
        m["poster_url"] = tmdb_client.get_poster_url(m["id"])
    return movies

# Endpoint principal del chat: orquesta todos los módulos del sistema
@router.post("/chat")
async def chat(msg: ChatMessage, request: Request):
    client_id = request.client.host
    user_text = msg.message

    # 1. Obtener o crear sesión para este cliente
    session = conv_manager.get_or_create(client_id)

    # ★ Si estábamos preguntando si conservar filtros, procesar la respuesta
    if session.get("step") == "ask_keep_filters":
        text_lower = user_text.lower().strip()
        session.pop("pending_keep_filters", None)

        if text_lower in ("si", "sí", "yes", "mantener", "conservar", "dale", "ok", "okay"):
            # Mantener filtros → pasar al flujo normal para mostrar resultados
            session["step"] = "show_results"
        elif text_lower in ("no", "nope", "limpiar", "borrar", "clean", "empezar de nuevo"):
            conv_manager.clear_secondary_filters(client_id)
            session = conv_manager.get_or_create(client_id)
            step = conv_manager.determine_next_step(session)
            session["step"] = step
            prefs = session["preferences"]
            if step == "ask_decade":
                genre_str = " y ".join(prefs.get("genres", []))
                return {"response": response_gen.ask_decade(genre_str, prefs)}
            if step == "ask_runtime":
                genre_str = " y ".join(prefs.get("genres", []))
                return {"response": response_gen.ask_runtime(genre_str, "", prefs)}
            if step == "ask_rating":
                return {"response": response_gen.ask_rating()}
            return {"response": response_gen.ask_genre_only()}
        else:
            # Usuario especificó un cambio específico (ej: "década 90s")
            conv_manager.clear_secondary_filters(client_id)
            session = conv_manager.get_or_create(client_id)
            new_prefs = intent_parser.extract_preferences(user_text)
            no_pref = intent_parser.is_no_preference(user_text)
            session = conv_manager.update_preferences(client_id, new_prefs, no_pref)
            step = conv_manager.determine_next_step(session)
            session["step"] = step
            if step == "ask_genre":
                prefs = session["preferences"]
                if any(k in prefs for k in ["decade", "actor", "director"]):
                    return {"response": response_gen.ask_genre_with_context(prefs)}
                return {"response": response_gen.ask_genre_only()}
            if step == "ask_decade":
                genre_str = " y ".join(session["preferences"].get("genres", []))
                return {"response": response_gen.ask_decade(genre_str, session["preferences"])}
            if step == "ask_runtime":
                genre_str = " y ".join(session["preferences"].get("genres", []))
                decade = session["preferences"].get("decade", "")
                decade_str = f"de los {decade}s" if decade and decade != "any" else ""
                return {"response": response_gen.ask_runtime(genre_str, decade_str, session["preferences"])}
            if step == "ask_rating":
                return {"response": response_gen.ask_rating()}
            # show_results → generar recomendaciones
            prefs = session["preferences"]
            all_movies = movie_loader.get_simplified_movies()
            candidate_ids = prolog_bridge.query(prefs, all_movies)
            movies = movie_loader.get_movies_by_ids(candidate_ids)
            if not movies:
                return {"response": response_gen.no_results()}
            if prefs.get("sort_by") == "popularity":
                ranked = _rank_by_popularity(movies, top_n=10)
            elif intent_parser.has_semantic_query(prefs):
                if len(movies) > 200:
                    movies.sort(key=lambda m: float(m.get("popularity", 0)), reverse=True)
                    movies = movies[:200]
                query_text = intent_parser.build_rich_query(prefs)
                ranked = scala_bridge.rank_movies(query_text, movies, top_n=10)
            else:
                ranked = _rank_by_vote(movies, top_n=10)
            session["last_results"] = ranked
            session["offset"] = 0
            display = ranked[:5]
            display_ids = {r["id"] for r in display}
            display_movies = [m for m in movies if m["id"] in display_ids]
            title_translator.translate_titles(display_movies)
            title_translator.translate_overviews(display_movies)
            _attach_posters(display_movies)
            return {"response": response_gen.generate_recommendation(display, movies, prefs)}

    new_prefs = intent_parser.extract_preferences(user_text)
    no_pref = intent_parser.is_no_preference(user_text)

    # 2. Si el usuario pide algo "similar a" una película, extraer preferencias de esa película
    if new_prefs.get("similar_to"):
        similar_title = new_prefs["similar_to"]
        similar_movie = movie_loader.get_movie_by_title(similar_title)
        if not similar_movie:
            similar_movie = movie_loader.get_movie_by_title(similar_title, exact=False)
        if not similar_movie:
            for eng_title, spa_title in title_translator.cache.items():
                if isinstance(spa_title, str) and spa_title.lower() == similar_title.lower():
                    similar_movie = movie_loader.get_movie_by_title(eng_title)
                    break
        if similar_movie:
            similar_prefs = _prefs_from_movie(similar_movie, movie_loader)
            for k, v in similar_prefs.items():
                if k == "genres":
                    existing = new_prefs.get("genres", [])
                    new_prefs["genres"] = list(set(existing + v))
                elif k not in new_prefs or not new_prefs[k]:
                    new_prefs[k] = v
        else:
            del new_prefs["similar_to"]
            return {"response": response_gen.movie_not_found(similar_title)}
        del new_prefs["similar_to"]

    # 3. Detectar si el usuario quiere cambiar de género (soft reset) o reiniciar todo (hard reset)
    hard_reset_keywords = ["reiniciar", "empezar de nuevo", "desde cero", "olvida", "en realidad"]
    soft_reset_keywords = ["otro género", "otra género", "probar otro", "probar otra",
                           "nuevo género", "nueva búsqueda", "cambiar", "cambie", "cambio",
                           "cambiar de opinión", "cambiar de opinion", "cambie de opinión",
                           "cambie de opinion", "mejor busco", "mejor quiero"]

    if any(kw in user_text.lower() for kw in hard_reset_keywords):
        conv_manager.reset_session(client_id)
        session = conv_manager.get_or_create(client_id)
        new_prefs = intent_parser.extract_preferences(user_text)
        no_pref = intent_parser.is_no_preference(user_text)

    elif any(kw in user_text.lower() for kw in soft_reset_keywords):
        conv_manager.soft_reset_genre(client_id)
        session = conv_manager.get_or_create(client_id)
        new_prefs = intent_parser.extract_preferences(user_text)
        no_pref = intent_parser.is_no_preference(user_text)
        if new_prefs.get("genres"):
            session["preferences"].pop("actor", None)
            session["preferences"].pop("director", None)
            session["preferences"].pop("decade", None)
            session["preferences"].pop("runtime", None)
            session["preferences"].pop("min_rating", None)

    # 4. Si hay nuevos géneros y ya había otros, reiniciar (cambio de preferencia)
    if new_prefs.get("genres") and session["preferences"].get("genres"):
        conv_manager.reset_session(client_id)
        session = conv_manager.get_or_create(client_id)

    # 5. Si hay resultados previos y se menciona actor/director, reiniciar
    if session.get("last_results") and (new_prefs.get("actor") or new_prefs.get("director")):
        conv_manager.reset_session(client_id)
        session = conv_manager.get_or_create(client_id)

    # 6. Actualizar sesión con nuevas preferencias y determinar el siguiente paso del flujo
    session = conv_manager.update_preferences(client_id, new_prefs, no_pref)
    step = conv_manager.determine_next_step(session)

    # ★ Si el usuario dijo "probar otro género" pero no especificó cuál, forzar ask_genre
    if (step == "show_results"
            and not session["preferences"].get("genres")
            and any(kw in user_text.lower() for kw in soft_reset_keywords)):
        step = "ask_genre"

    # ★ Si hay filtros guardados y usuario acaba de elegir género, preguntar si conservarlos
    if (session.get("pending_keep_filters")
            and new_prefs.get("genres")
            and step == "show_results"):
        session["pending_keep_filters"] = False
        session["step"] = "ask_keep_filters"
        return {"response": response_gen.ask_keep_filters(session["preferences"])}

    # Pasos del flujo conversacional: preguntar género, década, duración, calificación
    if step == "ask_genre":
        prefs = session["preferences"]
        # Si viene de "probar otro género", mostrar sin contexto
        if not prefs.get("genres") and any(kw in user_text.lower() for kw in soft_reset_keywords):
            return {"response": response_gen.ask_genre_only()}
        # Si ya hay década, actor o director, usar mensaje contextual
        if any(k in prefs for k in ["decade", "actor", "director"]):
            return {"response": response_gen.ask_genre_with_context(prefs)}
        # Si hay runtime o min_rating sin género, es un reset sin otros datos
        if not prefs:
            return {"response": response_gen.ask_genre()}
        return {"response": response_gen.ask_genre_only()}

    if step == "ask_decade":
        prefs = session["preferences"]
        genre_str = " y ".join(prefs["genres"]) if prefs.get("genres") else ""
        return {"response": response_gen.ask_decade(genre_str, prefs)}

    if step == "ask_runtime":
        prefs = session["preferences"]
        genre_str = " y ".join(prefs["genres"]) if prefs.get("genres") else ""
        decade = prefs.get("decade", "")
        decade_str = f"de los {decade}s" if decade and decade != "any" else ""
        return {"response": response_gen.ask_runtime(genre_str, decade_str, prefs)}

    if step == "ask_rating":
        return {"response": response_gen.ask_rating()}

    # 7. Si el usuario solo pide "más opciones", devolver el siguiente lote de resultados
    only_more = intent_parser.is_only_more(user_text, new_prefs)
    if only_more and session.get("last_results"):
        ranked = session["last_results"]
        prefs = session["preferences"]
        offset = session.get("offset", 0) + 5
        batch = ranked[offset:offset+5]
        if batch:
            session["offset"] = offset
            movie_ids = [r["id"] for r in batch]
            movies = movie_loader.get_movies_by_ids(movie_ids)
            title_translator.translate_titles(movies)
            title_translator.translate_overviews(movies)
            _attach_posters(movies)
            return {"response": response_gen.generate_recommendation(batch, movies, prefs)}
        else:
            session["offset"] = 0
            return {"response": response_gen.no_more_results()}

    # 8. Flujo principal de recomendación
    prefs = session["preferences"]
    all_movies = movie_loader.get_simplified_movies()
    # Filtrar películas según preferencias (usa Prolog si está disponible)
    candidate_ids = prolog_bridge.query(prefs, all_movies)
    movies = movie_loader.get_movies_by_ids(candidate_ids)

    if not movies:
        conv_manager.reset_session(client_id)
        return {"response": response_gen.no_results()}

    # 9. Ranking: por popularidad, por TF-IDF (Scala) o por calificación
    if prefs.get("sort_by") == "popularity":
        ranked = _rank_by_popularity(movies, top_n=10)
    elif intent_parser.has_semantic_query(prefs):
        # Limitar a 200 películas para TF-IDF por rendimiento
        if len(movies) > 200:
            movies.sort(key=lambda m: float(m.get("popularity", 0)), reverse=True)
            movies = movies[:200]
        query_text = intent_parser.build_rich_query(prefs)
        ranked = scala_bridge.rank_movies(query_text, movies, top_n=10)
    else:
        ranked = _rank_by_vote(movies, top_n=10)
    session["last_results"] = ranked
    session["offset"] = 0

    # 10. Mostrar las primeras 5, traducir títulos y adjuntar pósters
    display = ranked[:5]
    display_ids = {r["id"] for r in display}
    display_movies = [m for m in movies if m["id"] in display_ids]
    title_translator.translate_titles(display_movies)
    title_translator.translate_overviews(display_movies)
    _attach_posters(display_movies)
    resp = response_gen.generate_recommendation(display, movies, prefs)

    return {"response": resp}


# Endpoint de la cartelera: devuelve JSON con películas agrupadas (tendencias, mejores, por género)
# Página principal: cartelera de cine
@router.get("/")
async def home():
    html = (BASE / "frontend" / "templates" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


# Página del chat (separada de la cartelera)
@router.get("/chat")
async def chat_page():
    html = (BASE / "frontend" / "templates" / "chat.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


# Página de favoritos
@router.get("/favorites")
async def favorites_page():
    html = (BASE / "frontend" / "templates" / "favorites.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


# API: datos completos de una película para la página de detalle
@router.get("/api/movie/{movie_id}")
async def movie_detail(movie_id: int):
    try:
        movie = movie_loader.get_movie_by_id(movie_id)
        if not movie:
            return JSONResponse({"error": "La película no existe en el catálogo."}, status_code=404)
        data = jsonable_encoder(movie)
        data["poster_url"] = tmdb_client.get_poster_url(movie_id) or ""
        data["trailer_key"] = tmdb_client.get_trailer_key(movie_id) or ""
        data["actors"] = movie_loader.get_actors(movie_id) or []
        data["directors"] = movie_loader.get_directors(movie_id) or []
        data["genres_es"] = _movie_genres_es(data)
        title_translator.translate_titles([data])
        title_translator.translate_overviews([data])
        return data
    except Exception as e:
        print(f"[ERROR] movie_detail({movie_id}): {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Página de detalle de película (con tráiler)
@router.get("/movie/{movie_id}")
async def movie_page(movie_id: int):
    html = (BASE / "frontend" / "templates" / "movie.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


# Página de género: muestra películas filtradas por género
@router.get("/genre/{slug}")
async def genre_page(slug: str):
    slug = slug.lower().replace(" ", "-")
    if slug not in GENRE_SLUG_MAP:
        return HTMLResponse("<h1>Género no encontrado</h1><a href='/'>Volver</a>", status_code=404)
    html = (BASE / "frontend" / "templates" / "genre.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


# API: películas de un género (con ranking)
@router.get("/api/genre/{slug}/movies")
async def genre_movies_api(slug: str):
    slug = slug.lower().replace(" ", "-")
    english_genre = GENRE_SLUG_MAP.get(slug)
    if not english_genre:
        return JSONResponse({"error": "Género no encontrado"}, status_code=404)

    prefs = {"genres": [english_genre]}
    all_movies = movie_loader.get_simplified_movies()
    candidate_ids = prolog_bridge.query(prefs, all_movies)
    movies = movie_loader.get_movies_by_ids(candidate_ids)

    if not movies:
        return {"movies": [], "genre_es": EN_TO_ES.get(english_genre, english_genre)}

    ranked = _rank_by_vote(movies, top_n=10)

    ranked_movies = []
    movie_map = {}
    for m in movies:
        movie_map[int(m["id"])] = m
    for r in ranked:
        m = movie_map.get(r["id"])
        if m:
            ranked_movies.append(m)

    _attach_posters(ranked_movies)

    for m in ranked_movies:
        m["genres_es"] = _movie_genres_es(m)

    return {"movies": ranked_movies, "genre_es": EN_TO_ES.get(english_genre, english_genre)}


# API: lista de todos los géneros disponibles
@router.get("/api/genres")
async def genres_list():
    seen = set()
    genres = []
    for english, spanish in EN_TO_ES.items():
        slug = next((s for s, en in GENRE_SLUG_MAP.items() if en == english), "")
        if slug and english not in seen:
            seen.add(english)
            genres.append({"slug": slug, "name_es": spanish})
    genres.sort(key=lambda g: g["name_es"])
    return {"genres": genres}
