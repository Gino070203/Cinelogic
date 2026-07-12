# Descarga una sola vez los pósters de las 10 películas de la cartelera
# Se ejecuta con: python scripts/download_posters.py
# Los pósters se guardan en python/frontend/static/posters/{id}.jpg

import os
import requests
import urllib3
from pathlib import Path

urllib3.disable_warnings()

API_KEY = os.environ.get("TMDB_API_KEY", "87300fc227033b3519f4ff979753637c")
POSTERS_DIR = Path(__file__).resolve().parent.parent / "python" / "frontend" / "static" / "posters"
POSTERS_DIR.mkdir(parents=True, exist_ok=True)

# Tendencias | Mejor calificadas
MOVIES = [
    (19995, "Avatar"),
    (49026, "The Dark Knight Rises"),
    (157336, "Interstellar"),
    (27205, "Inception"),
    (550, "Fight Club"),
    (155, "The Dark Knight"),
    (8587, "The Lion King"),
    (150540, "Inside Out"),
    (122, "The Lord of the Rings: The Return of the King"),
    (38757, "Tangled"),
]

for mid, title in MOVIES:
    dest = POSTERS_DIR / f"{mid}.jpg"
    if dest.exists():
        print(f"  [SKIP] {title} — ya existe")
        continue

    url = f"https://api.themoviedb.org/3/movie/{mid}?api_key={API_KEY}"
    try:
        resp = requests.get(url, timeout=10, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            poster_path = data.get("poster_path")
            if poster_path:
                img_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
                img = requests.get(img_url, timeout=10, verify=False)
                if img.status_code == 200:
                    with open(dest, "wb") as f:
                        f.write(img.content)
                    print(f"  [OK] {title} -> {dest.name}")
                else:
                    print(f"  [ERR] {title} — imagen HTTP {img.status_code}")
            else:
                print(f"  [ERR] {title} — sin poster_path")
        else:
            print(f"  [ERR] {title} — API HTTP {resp.status_code}")
    except Exception as e:
        print(f"  [ERR] {title} — {e}")

print(f"\nListo. Posters en: {POSTERS_DIR}")
