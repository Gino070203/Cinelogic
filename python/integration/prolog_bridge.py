import json
import os
import subprocess
import tempfile
from pathlib import Path

# Directorio raíz del proyecto (subimos 3 niveles desde integration/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Puente con SWI-Prolog: convierte preferencias del usuario en consultas lógicas
# sobre una base de hechos (facts) generada a partir de las películas cargadas
class PrologBridge:
    def __init__(self):
        self._initialized = False
        self._facts_cached = False
        self._cached_facts = None
        self._init_prolog()

    # Verifica si SWI-Prolog está instalado y accesible
    def _init_prolog(self):
        try:
            result = subprocess.run(
                ["swipl", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print(f"[PrologBridge] SWI-Prolog detected: {result.stdout.strip()}")
                self._initialized = True
            else:
                print("[PrologBridge] SWI-Prolog not available. Using fallback.")
        except FileNotFoundError:
            print("[PrologBridge] swipl not found in PATH. Using fallback.")
        except Exception as e:
            print(f"[PrologBridge] Error: {e}. Using fallback.")

    # Convierte el JSON de géneros de TMDB a una lista de nombres
    def _parse_genres(self, genres_json):
        try:
            items = json.loads(genres_json)
            return [g["name"] for g in items]
        except (json.JSONDecodeError, TypeError, KeyError):
            return []

    # Construye una base de hechos en Prolog con todas las películas y sus atributos
    # Se ejecuta una sola vez y se reutiliza para todas las consultas posteriores
    def _ensure_facts_cached(self, movies):
        if self._facts_cached:
            return

        lines = []

        # Incluir el archivo de reglas Prolog (rules.pl) que define las consultas
        rules_path = os.path.join(BASE_DIR, "prolog", "rules.pl")
        lines.append(f":- consult('{rules_path.replace(chr(92), '/')}').")

        # Generar hechos: genero(ID, nombre), decada(ID, año), actor(ID, nombre), director(ID, nombre)
        for m in movies:
            mid = int(m["id"])
            genres = self._parse_genres(m.get("genres", "[]"))
            for g in genres:
                gs = g.replace("'", "\\'")
                lines.append(f"genero({mid}, '{gs}').")
            decade = m.get("decade")
            if decade is not None and str(decade) != "nan" and str(decade) != "NaT":
                lines.append(f"decada({mid}, {int(decade)}).")
            for actor in m.get("actors", []):
                a = str(actor).replace("'", "\\'")
                lines.append(f"actor({mid}, '{a}').")
            for director in m.get("directors", []):
                d = str(director).replace("'", "\\'")
                lines.append(f"director({mid}, '{d}').")

        self._cached_facts = "\n".join(lines)
        self._facts_cached = True
        total = len(lines) - 1
        print(f"[PrologBridge] Cached {total} facts for {len(movies)} movies")

    # Construye un programa Prolog completo: hechos + consulta con condiciones
    def _build_program(self, preferences, movies):
        self._ensure_facts_cached(movies)

        conditions = []

        # Convertir cada preferencia del usuario en una condición lógica
        conditions = []
        # Condiciones de género (incluyendo exclusiones)
        if "genres" in preferences:
            for g in preferences["genres"]:
                gs = g.replace("'", "\\'")
                conditions.append(f"genero(ID, '{gs}')")
        if "excluded_genres" in preferences:
            for g in preferences["excluded_genres"]:
                gs = g.replace("'", "\\'")
                conditions.append(f"not(genero(ID, '{gs}'))")

        # Condición de década
        if "decade" in preferences and preferences["decade"] not in (None, "any"):
            conditions.append(f"decada(ID, {preferences['decade']})")

        # Búsqueda de actor: usa sub_atom para emparejar palabras sueltas del nombre
        if "actor" in preferences:
            words = preferences["actor"].replace("'", "\\'").split()
            person_var = "A"
            conditions.append(f"actor(ID, {person_var})")
            for w in words:
                conditions.append(f"sub_atom({person_var}, _, _, _, '{w}')")

        # Búsqueda de director (mismo enfoque que con actor)
        if "director" in preferences:
            words = preferences["director"].replace("'", "\\'").split()
            person_var = "D"
            conditions.append(f"director(ID, {person_var})")
            for w in words:
                conditions.append(f"sub_atom({person_var}, _, _, _, '{w}')")

        # Exclusión de nombre (actor o director que no se quiere ver)
        if "excluded_name" in preferences:
            name = preferences["excluded_name"].replace("'", "\\'")
            conditions.append(f"not(actor(ID, '{name}'))")
            conditions.append(f"not(director(ID, '{name}'))")

        # Si no hay condiciones, no se puede armar una consulta significativa
        if not conditions:
            return None

        # Unir todo: hechos + consulta findall que recolecta los IDs que cumplen todas las condiciones
        join = ", ".join(conditions)
        return self._cached_facts + "\n:- findall(ID, (" + join + "), IDs), write(IDs), nl, halt."

    # Ejecuta una consulta en Prolog; si no está disponible, usa el fallback en Python
    # Ejecuta una consulta en Prolog; si no está disponible, usa el fallback en Python
    def query(self, preferences, all_movies=None):
        # Si Prolog no está disponible o no hay películas, ir al fallback
        if not self._initialized or all_movies is None:
            return self._fallback_query(preferences, all_movies)

        # Solo usar Prolog si hay actor/director (donde realmente aporta valor)
        has_person = bool(preferences.get("actor") or preferences.get("director"))
        if not has_person:
            return self._fallback_query(preferences, all_movies)

        program = self._build_program(preferences, all_movies)
        if program is None:
            return self._fallback_query(preferences, all_movies)

        # Escribir el programa a un archivo temporal y ejecutar swipl
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".pl", delete=False, encoding="utf-8"
            ) as f:
                f.write(program)
                tmp_path = f.name

            result = subprocess.run(
                ["swipl", "-q", "-f", tmp_path],
                capture_output=True, text=True, timeout=30
            )

            # Interpretar la salida: Prolog escribe una lista [id1, id2, ...]
            output = result.stdout.strip()
            if output and output.startswith("["):
                ids = json.loads(output)
                if isinstance(ids, list) and ids:
                    print(f"[PrologBridge] Prolog returned {len(ids)} movies")
                    return ids
        except subprocess.TimeoutExpired:
            print("[PrologBridge] Prolog query timed out")
        except json.JSONDecodeError:
            print(f"[PrologBridge] Could not parse: {output}")
        except Exception as e:
            print(f"[PrologBridge] Query error: {e}")
        finally:
            # Limpiar el archivo temporal
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Si algo falló, usar el fallback
        return self._fallback_query(preferences, all_movies)

    # Fallback: filtra películas directamente en Python (sin Prolog)
    # Se usa cuando SWI-Prolog no está instalado o la consulta es simple
    def _fallback_query(self, preferences, all_movies=None):
        # Si no hay datos cargados, devolver IDs de películas de ejemplo
        if all_movies is None or not all_movies:
            ids_pool = [550, 680, 238, 500, 155, 13, 11, 1891, 278, 122]
            return ids_pool[:5]

        filtered = []
        runtime = preferences.get("runtime")
        year = preferences.get("year")
        min_rating = preferences.get("min_rating")
        lang = preferences.get("language")

        # Recorrer todas las películas y aplicar cada filtro
        for m in all_movies:
            genres = self._parse_genres(m.get("genres", "[]"))
            match = True

            # Filtrar por género (debe coincidir al menos uno)
            if "genres" in preferences:
                if not any(g in genres for g in preferences["genres"]):
                    match = False
            # Excluir géneros no deseados
            if "excluded_genres" in preferences:
                if any(g in genres for g in preferences["excluded_genres"]):
                    match = False
            # Filtrar por década
            if "decade" in preferences and preferences["decade"] not in (None, "any"):
                decade = m.get("decade")
                if decade is not None and str(decade) not in ("nan", "NaT"):
                    if int(decade) != preferences["decade"]:
                        match = False
            # Filtrar por actor (coincidencia parcial de palabras)
            if "actor" in preferences:
                actor_words = preferences["actor"].lower().split()
                movie_actors = [a.lower() for a in m.get("actors", [])]
                if not all(
                    any(word in a for a in movie_actors) for word in actor_words
                ):
                    match = False
            # Filtrar por director
            if "director" in preferences:
                dir_words = preferences["director"].lower().split()
                movie_dirs = [d.lower() for d in m.get("directors", [])]
                if not all(
                    any(word in d for d in movie_dirs) for word in dir_words
                ):
                    match = False
            # Excluir nombre específico
            if "excluded_name" in preferences:
                ex_name = preferences["excluded_name"].lower()
                movie_actors = [a.lower() for a in m.get("actors", [])]
                movie_dirs = [d.lower() for d in m.get("directors", [])]
                if ex_name in movie_actors or ex_name in movie_dirs:
                    match = False
            # Filtrar por duración
            if runtime:
                m_runtime = m.get("runtime")
                if m_runtime:
                    m_runtime = int(m_runtime)
                    if runtime == "short" and m_runtime >= 90:
                        match = False
                    elif runtime == "medium" and not (90 <= m_runtime <= 120):
                        match = False
                    elif runtime == "long" and m_runtime <= 120:
                        match = False
            # Filtrar por año de estreno
            if year:
                rd = m.get("release_date")
                if rd is not None:
                    try:
                        if str(rd)[:4] != str(year):
                            match = False
                    except (ValueError, TypeError):
                        pass
            # Filtrar por calificación mínima
            if min_rating:
                va = m.get("vote_average")
                if va is not None:
                    try:
                        if float(va) < min_rating:
                            match = False
                    except (ValueError, TypeError):
                        pass
            # Filtrar por idioma original
            if lang:
                ol = m.get("original_language")
                if ol and ol != lang:
                    match = False

            if match:
                filtered.append(int(m["id"]))

        print(f"[PrologBridge] Fallback filtered {len(filtered)} movies by prefs")
        return filtered
