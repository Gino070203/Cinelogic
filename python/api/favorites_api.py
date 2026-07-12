import json
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pathlib import Path

from database import get_db
from models.favorite import Favorite
from api.routes import (
    movie_loader, intent_parser, prolog_bridge,
    scala_bridge, response_gen, title_translator, tmdb_client
)

router = APIRouter()
BASE = Path(__file__).resolve().parent.parent


def _attach_posters(movies):
    for m in movies:
        m["poster_url"] = tmdb_client.get_poster_url(m["id"])
    return movies


@router.get("/api/favorites")
async def list_favorites(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    favs = db.query(Favorite).filter(Favorite.user_id == user_id).all()
    return {"favorite_ids": [f.movie_id for f in favs]}


class DetailsRequest(BaseModel):
    ids: list[int]


@router.get("/api/favorites/recommend")
async def recommend_from_favorites(
    request: Request,
    db: Session = Depends(get_db),
    offset: int = 0,
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    favs = db.query(Favorite).filter(Favorite.user_id == user_id).all()
    if not favs:
        return {"html": "<p class='text-muted'>Añade películas a favoritos primero.</p>", "count": 0}

    ids = [f.movie_id for f in favs]
    fav_movies = movie_loader.get_movies_by_ids(ids)
    if not fav_movies:
        return {"html": "<p class='text-muted'>No se encontraron datos de esas películas.</p>", "count": 0}

    genre_counter = {}
    actor_counter = {}
    director_counter = {}
    for m in fav_movies:
        try:
            genres_data = json.loads(m.get("genres", "[]"))
            for g in genres_data:
                name = g.get("name")
                if name:
                    genre_counter[name] = genre_counter.get(name, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
        mid = int(m["id"])
        for a in movie_loader.get_actors(mid):
            actor_counter[a] = actor_counter.get(a, 0) + 1
        for d in movie_loader.get_directors(mid):
            director_counter[d] = director_counter.get(d, 0) + 1

    prefs = {}
    if genre_counter:
        top_genres = sorted(genre_counter, key=genre_counter.get, reverse=True)[:1]
        prefs["genres"] = top_genres
    if actor_counter:
        top_actor = sorted(actor_counter, key=actor_counter.get, reverse=True)[0]
        prefs["actor"] = top_actor
    if director_counter:
        top_director = sorted(director_counter, key=director_counter.get, reverse=True)[0]
        prefs["director"] = top_director

    all_movies = movie_loader.get_simplified_movies()
    candidate_ids = prolog_bridge.query(prefs, all_movies)
    # Excluir películas que el usuario ya tiene en favoritos
    candidate_ids = [cid for cid in candidate_ids if cid not in ids]
    # Si no quedan candidatos, relajar criterios (quitar actor/director)
    if not candidate_ids and prefs.get("genres"):
        prefs.pop("actor", None)
        prefs.pop("director", None)
        candidate_ids = prolog_bridge.query(prefs, all_movies)
        candidate_ids = [cid for cid in candidate_ids if cid not in ids]
    movies = movie_loader.get_movies_by_ids(candidate_ids)

    if not movies:
        return {"html": "<p class='text-muted'>No encontré películas con esos criterios.</p>", "count": 0}

    if intent_parser.has_semantic_query(prefs):
        if len(movies) > 200:
            movies.sort(key=lambda m: float(m.get("popularity", 0)), reverse=True)
            movies = movies[:200]
        query_text = intent_parser.build_rich_query(prefs)
        ranked = scala_bridge.rank_movies(query_text, movies, top_n=10)
    else:
        ranked = []
        for m in movies:
            vote = float(m.get("vote_average", 0))
            ranked.append({"id": int(m["id"]), "score": round(vote / 10.0, 2)})
        ranked.sort(key=lambda x: x["score"], reverse=True)
        ranked = ranked[:10]

    display = ranked[offset:offset + 5]
    display_ids = {r["id"] for r in display}
    display_movies = [m for m in movies if m["id"] in display_ids]
    title_translator.translate_titles(display_movies)
    title_translator.translate_overviews(display_movies)
    _attach_posters(display_movies)

    html = response_gen.generate_recommendation(display, movies, prefs, include_header_footer=(offset == 0))
    return {"html": html, "count": len(ranked), "total": len(ranked), "has_more": len(ranked) > offset + 5, "offset": offset}


@router.post("/api/favorites/details")
async def favorites_details(req: DetailsRequest):
    movies = movie_loader.get_movies_by_ids(req.ids)
    title_translator.translate_titles(movies)
    title_translator.translate_overviews(movies)
    _attach_posters(movies)
    return {"movies": jsonable_encoder(movies)}


@router.post("/api/favorites/{movie_id}")
async def add_favorite(
    movie_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    existing = db.query(Favorite).filter(
        Favorite.user_id == user_id, Favorite.movie_id == movie_id
    ).first()
    if not existing:
        fav = Favorite(user_id=user_id, movie_id=movie_id)
        db.add(fav)
        db.commit()
    return {"ok": True}


@router.delete("/api/favorites/{movie_id}")
async def remove_favorite(
    movie_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    fav = db.query(Favorite).filter(
        Favorite.user_id == user_id, Favorite.movie_id == movie_id
    ).first()
    if fav:
        db.delete(fav)
        db.commit()
    return {"ok": True}
