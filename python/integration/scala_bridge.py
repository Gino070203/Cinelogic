import subprocess
import json
import os
from pathlib import Path

# Puente con el motor Scala: ranking de películas usando TF-IDF implementado en Scala
# Envía las películas y la consulta a un JAR, recibe scores de relevancia
class ScalaBridge:
    def __init__(self, movie_loader=None):
        self.jar_path = self._find_jar()
        self.movie_loader = movie_loader

    # Busca el archivo JAR compilado en scala/target/
    def _find_jar(self):
        base = Path(__file__).resolve().parent.parent.parent
        candidates = list(
            (base / "scala" / "target").rglob("cinalogic-assembly-*.jar")
        )
        if candidates:
            jar = str(candidates[0])
            print(f"[ScalaBridge] Found JAR: {jar}")
            return jar
        print("[ScalaBridge] JAR not found. Build with: cd scala && sbt assembly")
        return None

    # Método principal: rankea las películas según la consulta del usuario
    # Usa TF-IDF en Scala si está disponible, sino cae en fallback por voto
    def rank_movies(self, query_text, movies, top_n=5):
        if self.jar_path is None:
            return self._fallback_ranking_vote(movies, top_n)

        # Preparar los datos de cada película para enviarlos al JAR
        movie_data = [
            {
                "id": int(m["id"]),
                "title": m.get("title", ""),
                "overview": m.get("overview", ""),
                "genres": self._extract_names(m.get("genres", "[]")),
                "keywords": self._build_enriched_keywords(m),
            }
            for m in movies
        ]

        # Enviar consulta y películas al JAR de Scala como JSON por stdin
        request = {"query": query_text, "movies": movie_data, "topN": top_n}

        try:
            result = subprocess.run(
                ["java", "-jar", self.jar_path],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                output = json.loads(result.stdout)
                # Verificar que los scores no sean todos cercanos a cero
                if self._has_meaningful_scores(output):
                    print(f"[ScalaBridge] Got {len(output)} recommendations")
                    return output
                print("[ScalaBridge] Scores near zero, using vote-based fallback")
            else:
                print(f"[ScalaBridge] Error: {result.stderr}")
        except FileNotFoundError:
            print("[ScalaBridge] Java not found. Is Java installed?")
        except json.JSONDecodeError as e:
            print(f"[ScalaBridge] JSON parse error: {e}")
        except Exception as e:
            print(f"[ScalaBridge] Unexpected error: {e}")

        return self._fallback_ranking_vote(movies, top_n)

    # Enriquece las palabras clave de una película agregando actores y directores
    def _build_enriched_keywords(self, movie):
        base_keywords = self._extract_names(movie.get("keywords", "[]"))
        if self.movie_loader:
            mid = int(movie["id"])
            actors = self.movie_loader.get_actors(mid)
            directors = self.movie_loader.get_directors(mid)
            extra = actors + directors
            if extra:
                return f"{base_keywords} {' '.join(extra)}".strip()
        return base_keywords

    # Extrae nombres de un JSON como "keywords" o "genres"
    def _extract_names(self, json_str):
        try:
            items = json.loads(json_str)
            return " ".join(item.get("name", "") for item in items)
        except (json.JSONDecodeError, TypeError):
            return ""

    # Verifica que al menos un resultado tenga un score significativo (> 0.10)
    def _has_meaningful_scores(self, results, threshold=0.10):
        return any(r.get("score", 0) >= threshold for r in results)

    # Fallback: ordena las películas por su calificación (vote_average) descendente
    def _fallback_ranking_vote(self, movies, top_n):
        with_scores = []
        for m in movies:
            vote = float(m.get("vote_average", 0))
            score = vote / 10.0
            with_scores.append({"id": int(m["id"]), "score": round(score, 2)})
        with_scores.sort(key=lambda x: x["score"], reverse=True)
        return with_scores[:top_n]

    # Fallback simple: asigna scores decrecientes según la posición en la lista
    def _fallback_ranking(self, movies, top_n):
        ranked = []
        for i, m in enumerate(movies[:top_n]):
            score = max(0.1, 1.0 - (i * 0.15))
            ranked.append({"id": int(m["id"]), "score": round(score, 2)})
        return ranked
