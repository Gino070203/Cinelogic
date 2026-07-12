# ──────────────────────────────────────────────
# MovieLoader: carga las películas del dataset
# ──────────────────────────────────────────────
# Lee los archivos CSV de TMDB y mantiene toda la
# información en memoria (DataFrame de pandas).
# Es la "base de datos" del programa: todos los
# demás módulos consultan aquí los datos de películas.

import pandas as pd
import json
import os
from pathlib import Path

# Carpeta raíz del proyecto (tres niveles arriba: python/ → Proyecto_Lenguajes_Programacion/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Rutas a los archivos CSV del dataset TMDB
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "tmdb_5000_movies.csv")
CREDITS_PATH = os.path.join(BASE_DIR, "dataset", "tmdb_5000_credits.csv")


class MovieLoader:
    """
    Carga y mantiene en memoria las ~4800 películas del dataset TMDB.
    Proporciona métodos para consultar películas por ID, título,
    obtener actores/directores, y una versión simplificada para filtrar.
    """

    def __init__(self):
        # self.df: DataFrame de pandas con todas las películas
        # Columnas principales: id, title, genres, overview, runtime,
        #                      vote_average, release_date, popularity, keywords
        self.df = None
        self.credits_df = None

        # Diccionarios que asocian cada película con su reparto y dirección
        # Formato: {id_pelicula: ["Actor1", "Actor2", ...]}
        self._actors_by_movie = {}
        self._directors_by_movie = {}

        # Cache para get_simplified_movies (se construye una sola vez)
        self._simplified_cache = None

        # ¡Arranca la carga!
        self.load()

    # ───── Carga inicial ─────

    def load(self):
        """Lee el CSV de películas y el de créditos, los procesa y los deja listos en memoria."""
        if not os.path.exists(DATASET_PATH):
            print(f"Dataset not found at {DATASET_PATH}. Run in offline mode.")
            self.df = pd.DataFrame()
            return
        self.df = pd.read_csv(DATASET_PATH)
        self._preprocess()
        self._load_credits()

    def _preprocess(self):
        """Limpia y prepara el DataFrame:
        - Elimina filas sin título o sinopsis (no sirven)
        - Rellena campos nulos con valores vacíos
        - Convierte release_date a formato fecha y calcula la década
        """
        self.df = self.df.dropna(subset=["title", "overview"])
        self.df["genres"] = self.df["genres"].fillna("[]")
        self.df["keywords"] = self.df["keywords"].fillna("[]")
        if "release_date" in self.df.columns:
            self.df["release_date"] = pd.to_datetime(self.df["release_date"], errors="coerce")
            # Década: 1999 → 1990, 2005 → 2000, 2015 → 2010
            self.df["decade"] = self.df["release_date"].dt.year // 10 * 10

    # ───── Carga de actores y directores ─────

    def _load_credits(self):
        """Lee el CSV de créditos y construye los diccionarios
        _actors_by_movie y _directors_by_movie.

        El cast y crew vienen como texto JSON en el CSV, así que
        hay que parsearlos. Solo guardamos los 5 actores principales
        y los miembros del crew con cargo 'Director'.
        """
        if not os.path.exists(CREDITS_PATH):
            print(f"Credits not found at {CREDITS_PATH}. Actor/director filter disabled.")
            return
        try:
            self.credits_df = pd.read_csv(CREDITS_PATH)
            for _, row in self.credits_df.iterrows():
                mid = int(row["movie_id"])
                cast = self._parse_credits_json(row.get("cast", "[]"))
                crew = self._parse_credits_json(row.get("crew", "[]"))
                actors = [c["name"] for c in cast[:5]]  # top 5 actores
                directors = [c["name"] for c in crew if c.get("job") == "Director"]
                self._actors_by_movie[mid] = actors
                self._directors_by_movie[mid] = directors
            print(f"[MovieLoader] Loaded credits for {len(self._actors_by_movie)} movies")
        except Exception as e:
            print(f"[MovieLoader] Error loading credits: {e}")

    def _parse_credits_json(self, val):
        """Convierte un string JSON a lista de Python.
        El CSV guarda el cast/crew como texto JSON en una celda."""
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return []
        if isinstance(val, list):
            return val
        return []

    # ───── Consultas públicas ─────

    def get_actors(self, movie_id):
        """Devuelve la lista de actores de una película (vacio si no hay)."""
        return self._actors_by_movie.get(int(movie_id), [])

    def get_directors(self, movie_id):
        """Devuelve la lista de directores de una película (vacio si no hay)."""
        return self._directors_by_movie.get(int(movie_id), [])

    def get_movies_by_ids(self, ids):
        """Dada una lista de IDs, devuelve los datos COMPLETOS
        de esas películas con todas sus columnas.
        Útil cuando ya sabemos qué IDs queremos mostrar."""
        if self.df is None or self.df.empty:
            return self._fallback_movies(ids)
        subset = self.df[self.df["id"].isin(ids)]
        records = subset.to_dict("records")
        # Convertir tipos numpy/pandas a tipos nativos de Python
        # para que json.dumps pueda serializarlos sin error
        for rec in records:
            for k, v in rec.items():
                if pd.isna(v):
                    rec[k] = None
                elif hasattr(v, 'item'):  # numpy.int64, numpy.float64, etc.
                    rec[k] = v.item()
                elif isinstance(v, pd.Timestamp):
                    rec[k] = v.isoformat()
        return records

    def get_all_movies(self):
        """Devuelve el DataFrame completo de pandas."""
        if self.df is None:
            return pd.DataFrame()
        return self.df

    def get_simplified_movies(self):
        """Devuelve una versión LIGERA de todas las películas,
        solo con los campos necesarios para filtrar (sin sinopsis pesadas).
        Se construye una vez y se cachea en _simplified_cache."""
        if self._simplified_cache is not None:
            return self._simplified_cache
        if self.df is None or self.df.empty:
            self._simplified_cache = self._fallback_movies([550, 680, 238, 500, 155])
            return self._simplified_cache
        simplified = []
        for _, row in self.df.iterrows():
            mid = int(row["id"])
            simplified.append({
                "id": mid,
                "genres": row.get("genres", "[]"),
                "decade": row.get("decade", None),
                "title": row.get("title", ""),
                "actors": self._actors_by_movie.get(mid, []),
                "directors": self._directors_by_movie.get(mid, []),
                "runtime": row.get("runtime"),
                "vote_average": row.get("vote_average"),
                "release_date": row.get("release_date"),
                "original_language": row.get("original_language"),
            })
        self._simplified_cache = simplified
        return simplified

    def get_movie_by_id(self, movie_id):
        """Busca una película por su ID numérico exacto."""
        if self.df is None or self.df.empty:
            return None
        row = self.df[self.df["id"] == movie_id]
        if row.empty:
            return None
        record = row.iloc[0].to_dict()
        for k, v in record.items():
            if pd.isna(v):
                record[k] = None
            elif hasattr(v, 'item'):
                record[k] = v.item()
            elif isinstance(v, pd.Timestamp):
                record[k] = v.isoformat()
        return record

    def get_movie_by_title(self, title, exact=True):
        """Busca una película por su título.
        Si exact=True: compara exacto (sin distinguir mayúsculas).
        Si exact=False: busca que el título CONTENGA el texto."""
        if self.df is None or self.df.empty:
            return None
        if exact:
            mask = self.df["title"].str.lower() == title.lower()
        else:
            mask = self.df["title"].str.lower().str.contains(title.lower(), na=False)
        matches = self.df[mask]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    # ───── Fallback (cuando no hay CSV) ─────

    def _fallback_movies(self, ids):
        """Películas de respaldo hardcodeadas para cuando no se encuentra el dataset.
        Útil para pruebas o cuando se ejecuta sin los archivos CSV."""
        fallback = [
            {"id": 550, "title": "Fight Club", "overview": "A ticking time bomb of insanity.",
             "genres": "[{\"name\":\"Drama\"}]", "keywords": "[{\"name\":\"psychological\"}]",
             "actors": ["Brad Pitt", "Edward Norton"], "directors": ["David Fincher"]},
            {"id": 680, "title": "Pulp Fiction", "overview": "Intertwining stories of crime.",
             "genres": "[{\"name\":\"Crime\"}]", "keywords": "[{\"name\":\"crime\"}]",
             "actors": ["John Travolta", "Samuel L. Jackson"], "directors": ["Quentin Tarantino"]},
            {"id": 238, "title": "The Godfather", "overview": "The aging patriarch of an organized crime dynasty.",
             "genres": "[{\"name\":\"Crime\"}]", "keywords": "[{\"name\":\"mafia\"}]",
             "actors": ["Marlon Brando", "Al Pacino"], "directors": ["Francis Ford Coppola"]},
            {"id": 500, "title": "Reservoir Dogs", "overview": "A botched robbery.",
             "genres": "[{\"name\":\"Crime\"}]", "keywords": "[{\"name\":\"heist\"}]",
             "actors": ["Harvey Keitel", "Tim Roth"], "directors": ["Quentin Tarantino"]},
            {"id": 155, "title": "The Dark Knight", "overview": "When the menace known as the Joker wreaks havoc.",
             "genres": "[{\"name\":\"Action\"}]", "keywords": "[{\"name\":\"superhero\"}]",
             "actors": ["Christian Bale", "Heath Ledger"], "directors": ["Christopher Nolan"]},
        ]
        return [m for m in fallback if m["id"] in ids]
