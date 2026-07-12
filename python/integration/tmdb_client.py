import os
import json
import requests
import urllib3
from pathlib import Path

# Silenciar advertencias SSL (útil en entornos sin certificados actualizados)
urllib3.disable_warnings()

# Archivos JSON donde se guarda la caché local (pósters y tráilers)
CACHE_FILE = Path(__file__).resolve().parent / "poster_cache.json"
CACHE_TRAILER = Path(__file__).resolve().parent / "trailer_cache.json"

# Cliente para obtener URLs de pósters desde TMDB (The Movie Database)
class TMDBClient:
    def __init__(self):
        # La API key se lee de la variable de entorno; si no está configurada, no se hacen consultas
        self.api_key = os.environ.get("TMDB_API_KEY", "")
        self.cache = self._load_cache()
        if self.api_key:
            print("[TMDBClient] API key configured")
        else:
            print("[TMDBClient] No API key set. Set TMDB_API_KEY env var for posters.")

    # Carga la caché de pósters desde el archivo JSON al iniciar
    def _load_cache(self):
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    # Guarda la caché actualizada en el archivo JSON para persistencia entre ejecuciones
    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f)
        except OSError:
            pass

    def _load_json(self, path):
        try:
            if path.exists():
                with open(path, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    def _save_json(self, path, data):
        try:
            with open(path, "w") as f:
                json.dump(data, f)
        except OSError:
            pass

    # Obtiene el key de YouTube del tráiler de una película
    # Cachea el resultado para no consultar la API repetidamente
    def get_trailer_key(self, movie_id):
        mid = str(movie_id)
        cache = self._load_json(CACHE_TRAILER)
        if mid in cache:
            return cache[mid]
        if not self.api_key:
            cache[mid] = None
            self._save_json(CACHE_TRAILER, cache)
            return None
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={self.api_key}"
        try:
            resp = requests.get(url, timeout=5, verify=False)
            if resp.status_code == 200:
                videos = resp.json().get("results", [])
                for v in videos:
                    if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                        cache[mid] = v["key"]
                        self._save_json(CACHE_TRAILER, cache)
                        return v["key"]
        except requests.RequestException:
            pass
        cache[mid] = None
        self._save_json(CACHE_TRAILER, cache)
        return None

    # Obtiene la URL del póster de una película por su ID de TMDB
    # Usa caché local para evitar consultas repetidas a la API
    def get_poster_url(self, movie_id):
        mid = str(movie_id)
        # Si ya está cacheado, devolver inmediatamente
        if mid in self.cache:
            return self.cache[mid]

        # Si no hay API key, no se puede consultar
        if not self.api_key:
            self.cache[mid] = None
            return None

        # Consultar la API de TMDB y extraer la ruta del póster
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={self.api_key}"
        try:
            resp = requests.get(url, timeout=5, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                poster = data.get("poster_path")
                if poster:
                    poster_url = f"https://image.tmdb.org/t/p/w342{poster}"
                    self.cache[mid] = poster_url
                else:
                    self.cache[mid] = None
            else:
                self.cache[mid] = None
            self._save_cache()
            return self.cache[mid]
        except requests.RequestException:
            self.cache[mid] = None
            return None
