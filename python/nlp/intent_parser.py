import re
import unicodedata

# Analizador de lenguaje natural para entender lo que el usuario pide
# Convierte frases en español en preferencias estructuradas (género, década, actor, etc.)
class IntentParser:
    def __init__(self):
        # Mapa que traduce palabras sueltas en español a nombres de géneros en inglés (como los usa TMDB)
        self.genre_map = {
            "accion": "Action", "acción": "Action",
            "aventura": "Adventure",
            "comedia": "Comedy",
            "drama": "Drama",
            "terror": "Horror", "horror": "Horror",
            "ciencia ficcion": "Science Fiction",
            "ciencia ficción": "Science Fiction",
            "sci fi": "Science Fiction", "scifi": "Science Fiction",
            "thriller": "Thriller", "suspenso": "Thriller", "suspense": "Thriller",
            "romance": "Romance",
            "animacion": "Animation", "animación": "Animation",
            "documental": "Documentary",
            "fantasia": "Fantasy", "fantasía": "Fantasy",
            "misterio": "Mystery",
            "belico": "War", "bélico": "War", "guerra": "War",
            "musical": "Music",
            "ficcion": "Science Fiction", "ficción": "Science Fiction",
            "crimen": "Crime",
            "historia": "History", "historico": "History", "histórico": "History",
            "western": "Western", "vaqueros": "Western",
            "pelicula tv": "TV Movie", "telefilme": "TV Movie",
        }

        # Franquicias conocidas: asocia un nombre (p.ej. "marvel") con un texto de búsqueda enriquecido
        # y los géneros típicos de esa franquicia, para mejorar las recomendaciones
        self.franchise_map = {
            "marvel": ("marvel superhero avengers comic", ["Action", "Adventure", "Science Fiction"]),
            "dc": ("dc superhero batman superman comic", ["Action", "Adventure", "Fantasy"]),
            "star wars": ("star wars space jedi empire", ["Science Fiction", "Adventure", "Action"]),
            "star trek": ("star trek space federation", ["Science Fiction", "Adventure"]),
            "harry potter": ("harry potter wizard magic hogwarts", ["Fantasy", "Adventure"]),
            "señor de los anillos": ("lord rings middle earth fantasy", ["Fantasy", "Adventure", "Action"]),
            "lotr": ("lord rings middle earth fantasy", ["Fantasy", "Adventure", "Action"]),
            "james bond": ("james bond spy secret agent 007", ["Action", "Thriller", "Adventure"]),
            "007": ("james bond spy secret agent", ["Action", "Thriller"]),
            "indiana jones": ("indiana jones adventure artifact", ["Adventure", "Action"]),
            "jurassic": ("jurassic dinosaur park", ["Adventure", "Action", "Science Fiction"]),
            "terminator": ("terminator robot future skynet", ["Science Fiction", "Action", "Thriller"]),
            "misión imposible": ("mission impossible spy ethan hunt", ["Action", "Thriller", "Adventure"]),
            "rapidos y furiosos": ("fast furious street racing car", ["Action", "Thriller", "Crime"]),
            "rápidos y furiosos": ("fast furious street racing car", ["Action", "Thriller", "Crime"]),
            "transformers": ("transformers robot alien combat", ["Science Fiction", "Action", "Adventure"]),
            "alien": ("alien xenomorph space horror", ["Science Fiction", "Horror", "Thriller"]),
            "predator": ("predator hunter jungle alien", ["Science Fiction", "Action", "Horror"]),
            "matrix": ("matrix virtual reality simulation", ["Science Fiction", "Action"]),
        }

        # Mapa de estados de ánimo: asocia palabras como "reír" o "triste" con géneros sugeridos
        self.mood_map = {
            "reír": ["Comedy"], "reirme": ["Comedy"], "risa": ["Comedy"],
            "divertir": ["Comedy", "Adventure"],
            "feliz": ["Comedy", "Animation", "Adventure"],
            "alegre": ["Comedy", "Animation"],
            "profundo": ["Drama", "Mystery"],
            "pensar": ["Drama", "Mystery", "Science Fiction"],
            "reflexionar": ["Drama"],
            "reflexivo": ["Drama"],
            "asustar": ["Horror", "Thriller"],
            "miedo": ["Horror", "Thriller"],
            "terrorífico": ["Horror"],
            "triste": ["Drama", "Romance"],
            "llorar": ["Drama", "Romance"],
            "melancólico": ["Drama", "Romance"],
            "emocionante": ["Action", "Thriller", "Adventure"],
            "adrenalina": ["Action", "Thriller"],
            "intensa": ["Action", "Thriller", "Drama"],
            "intenso": ["Action", "Thriller", "Drama"],
            "entretenido": ["Comedy", "Adventure", "Action"],
            "pasatiempo": ["Comedy", "Adventure"],
            "inspirar": ["Drama", "Documentary", "History"],
            "motivación": ["Drama", "Documentary"],
            "motivacion": ["Drama", "Documentary"],
            "relajar": ["Comedy", "Animation", "Music"],
            "aburrido": ["Action", "Adventure", "Comedy"],
            "interesante": ["Drama", "Mystery", "Documentary"],
            "culto": ["Drama", "Thriller", "Science Fiction"],
            "clásico": ["Drama", "History", "Romance"],
        }

        # Patrones de negación: frases como "sin terror" o "que no tenga comedia"
        self.negation_triggers = [
            r'sin\s+',
            r'que\s+no\s+(?:tenga|sea|quiero)\s+(?:de\s+)?',
            r'excepto\s+',
            r'menos\s+',
            r'evit[ae]\s+',
            r'quit[ae]\s+',
        ]

    # Busca si el texto menciona alguna franquicia conocida (Marvel, Star Wars, etc.)
    def _extract_franchise(self, text_lower):
        for keyword, (boost, genre_hints) in self.franchise_map.items():
            if keyword in text_lower:
                return boost, genre_hints
        return None, []

    # Detecta palabras de estado de ánimo y devuelve los géneros asociados
    def _extract_mood(self, text_lower):
        def strip_accents(s):
            return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII')
        norm_text = strip_accents(text_lower)
        found = []
        for keyword, genres in self.mood_map.items():
            norm_key = strip_accents(keyword)
            if norm_key in norm_text:
                found.extend(genres)
            # Stem matching para verbos conjugados: "asusten" → "asust" (raíz de "asustar")
            elif (
                len(norm_key) > 4
                and norm_key.endswith(("ar", "er", "ir"))
                and len(stem := norm_key[:-2]) >= 3
                and re.search(re.escape(stem) + r"\w*", norm_text)
            ):
                found.extend(genres)
        return found

    # Encuentra géneros que el usuario quiere excluir (p.ej. "sin terror", "que no tenga comedia")
    def _extract_negated_genres(self, text_lower):
        excluded = []
        for trigger in self.negation_triggers:
            parts = re.split(trigger, text_lower)
            for i in range(1, len(parts)):
                fragment = parts[i].strip()
                for spanish, english in self.genre_map.items():
                    if fragment.startswith(spanish) and (
                        len(fragment) == len(spanish) or not fragment[len(spanish)].isalpha()
                    ):
                        excluded.append(english)
        return excluded

    # Busca nombres propios excluidos (p.ej. "sin Christopher Nolan")
    def _extract_negated_name(self, text):
        name_pat = r'[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+)*'
        for trigger in self.negation_triggers:
            pattern = trigger + rf'({name_pat})'
            m = re.search(pattern, text)
            if m:
                gname = m.group(1).strip()
                if gname.lower() not in self.franchise_map:
                    return gname
        return None

    # Método principal: analiza el texto del usuario y devuelve un diccionario con todas las preferencias detectadas
    def extract_preferences(self, text):
        text_lower = text.lower()
        preferences = {}

        # 1. Detectar exclusiones (géneros y nombres que el usuario NO quiere)
        excluded_genres = self._extract_negated_genres(text_lower)
        excluded_name = self._extract_negated_name(text)

        # 2. Detectar géneros mencionados explícitamente
        genres_found = []
        for spanish, english in self.genre_map.items():
            if spanish in text_lower:
                if english in excluded_genres:
                    continue
                genres_found.append(english)

        # 3. Detectar estado de ánimo y franquicias, y agregar sus géneros sugeridos
        mood_genres = self._extract_mood(text_lower)
        if mood_genres:
            genres_found.extend(mood_genres)

        franchise_boost, franchise_genres = self._extract_franchise(text_lower)
        if franchise_boost:
            preferences["query_boosts"] = franchise_boost
            genres_found.extend(franchise_genres)

        # 4. Limpiar duplicados y guardar géneros encontrados (excluyendo los negados)
        if genres_found:
            deduped = []
            for g in genres_found:
                if g not in excluded_genres and g not in deduped:
                    deduped.append(g)
            if deduped:
                preferences["genres"] = deduped

        if excluded_genres:
            preferences["excluded_genres"] = excluded_genres

        if excluded_name:
            preferences["excluded_name"] = excluded_name

        # 5. Detectar década (p.ej. "80s", "años 80", "1990s")
        decade_match = re.search(r'(?:los\s+)?(\d+)s\b', text_lower)
        if not decade_match:
            decade_match = re.search(r'años\s+(\d+)', text_lower)
        if decade_match:
            val = int(decade_match.group(1))
            if val < 100:
                preferences["decade"] = 1900 + val if val >= 20 else 2000 + val
            else:
                preferences["decade"] = (val // 10) * 10

        # 6. Detectar año específico (p.ej. "1999", "2023")
        year_match = re.search(r'\b(19[0-9]{2}|20[0-9]{2})\b', text_lower)
        if year_match:
            year_val = int(year_match.group(1))
            preferences["year"] = year_val
            if "decade" not in preferences:
                preferences["decade"] = (year_val // 10) * 10

        name_pat = r'[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+)*'

        # 7. Detectar director (p.ej. "dirigida por Steven Spielberg")
        director_match = re.search(
            r'(?:director|dirigid[ao]s?)\s+(?:por\s+)?(?:de\s+)?'
            rf'({name_pat})',
            text
        )
        if director_match:
            preferences["director"] = director_match.group(1).strip()

        # 8. Detectar actor (p.ej. "protagonizada por Tom Hanks")
        actor_match = re.search(
            r'(?:actor|protagonizad[ao]s?|con|interpretad[ao]s?)\s+(?:por\s+)?'
            rf'({name_pat})',
            text
        )
        if actor_match:
            preferences["actor"] = actor_match.group(1).strip()

        # 9. Si no se encontró actor ni director explícito, buscar frases como "películas de [nombre]"
        if not actor_match and not director_match:
            general_name_match = re.search(
                rf'(?:pel[íi]culas?|pelis?)\s+de\s+({name_pat})',
                text
            )
            if not general_name_match:
                general_name_match = re.search(
                    rf'(?:quiero|quisiera)\s+ver\s+({name_pat})',
                    text
                )
            if not general_name_match:
                general_name_match = re.search(
                    rf'(?:busco|recomiend[ae]me|dame)\s+({name_pat})',
                    text
                )
            if general_name_match:
                gname = general_name_match.group(1).strip()
                if gname.lower() not in self.franchise_map:
                    preferences["actor"] = gname

        # 10. Detectar preferencia de duración (corta, media, larga)
        runtime_patterns = [
            (r'\b(cort[ao]s?|menos\s+de\s+\d+)\b', "short"),
            (r'\b(medi[ao]s?|median[ao]s?)\b', "medium"),
            (r'\b(larg[ao]s?|m[áa]s\s+de\s+\d+)\b', "long"),
        ]
        for pattern, value in runtime_patterns:
            if re.search(pattern, text_lower):
                preferences["runtime"] = value
                break

        # 11. Detectar si pide películas con alta calificación
        high_rating_keywords = ["alta", "alto", "alta calificacion", "alta calificación",
                                "alta puntuacion", "alta puntuación", "mejores",
                                "mejor calificadas", "mejor puntuadas",
                                "solo buenas", "las mejores"]
        if any(kw in text_lower for kw in high_rating_keywords):
            preferences["min_rating"] = 7.0

        # 12. Detectar calificación numérica específica (p.ej. "calificación de 8")
        rating_match = re.search(r'(?:calificacion|calificación|rating|puntaje)\s*(?:de|:)?\s*(\d+(?:\.\d+)?)', text_lower)
        if rating_match:
            preferences["min_rating"] = float(rating_match.group(1))

        # 13. Detectar si pide películas populares o taquilleras
        popular_keywords = ["popular", "populares", "taquillera", "taquilleras",
                            "más vista", "mas vista", "más vistos", "mas vistos",
                            "más popular", "mas popular", "más famosa", "mas famosa",
                            "famosa", "famosas", "conocida", "conocidas"]
        if any(kw in text_lower for kw in popular_keywords):
            preferences["sort_by"] = "popularity"

        # 14. Detectar peticiones de películas similares
        # Pattern A: "recomiéndame películas parecidas a Inception"
        similar_match = re.search(
            r'(?:recomiend[ae]me|busco|dame|quisiera)\s+'
            r'(?:pel[íi]culas?|pelis?)\s+'
            r'(?:parecid[ao]s?|similares)\s+'
            r'(?:a\s+)?'
            rf'({name_pat})',
            text
        )
        # Pattern B: "parecida a Inception" / "parecidas a Inception" / "similares a Inception"
        if not similar_match:
            similar_match = re.search(
                r'(?:parecid[ao]s?|similar(?:es)?)\s+(?:a\s+)?'
                rf'({name_pat})',
                text
            )
        # Pattern C: "películas como Inception"
        if not similar_match:
            similar_match = re.search(
                r'(?:pel[íi]culas?|pelis?)\s+como\s+'
                rf'({name_pat})',
                text
            )
        # Pattern D: "algo como Inception"
        if not similar_match:
            similar_match = re.search(
                r'(?:algo\s+)?como\s+'
                rf'({name_pat})',
                text
            )
        if similar_match:
            title = similar_match.group(1).strip()
            title_lower = title.lower()
            if title_lower not in ("tal", "eso", "esto", "aquello", "siempre"):
                preferences["similar_to"] = title

        # 15. Detectar idioma (audio o subtítulos)
        language_map = {
            "español": "es", "española": "es", "españolas": "es",
            "subtitulada": None, "subtituladas": None, "subtitulado": None,
            "doblada": None, "dobladas": None, "doblado": None,
            "latino": None, "latina": None,
            "inglés": "en", "ingles": "en", "inglesa": "en", "ingl": "en",
            "frances": "fr", "francés": "fr", "francesa": "fr",
            "coreano": "ko", "coreana": "ko",
            "japones": "ja", "japonés": "ja", "japonesa": "ja",
            "italiano": "it", "italiana": "it",
            "aleman": "de", "alemán": "de", "alemana": "de",
        }
        found_lang = None
        for kw, code in language_map.items():
            if kw in text_lower:
                found_lang = code
                break
        if found_lang is not None:
            preferences["language"] = found_lang

        # 16. Devolver todas las preferencias detectadas en el mensaje del usuario
        return preferences

    # Convierte las preferencias en un texto simple para búsqueda por palabras clave
    def build_query_text(self, preferences):
        parts = []
        if "genres" in preferences:
            parts.extend(preferences["genres"])
        if "decade" in preferences:
            parts.append(str(preferences["decade"]))
        if "year" in preferences and "decade" not in preferences:
            parts.append(str(preferences["year"]))
        if "director" in preferences:
            parts.append(preferences["director"])
        if "actor" in preferences:
            parts.append(preferences["actor"])
        return " ".join(parts)

    # Indica si la consulta necesita búsqueda semántica (franquicia o similar_to)
    def has_semantic_query(self, preferences):
        return bool(
            preferences.get("query_boosts")
            or preferences.get("similar_to")
        )

    # Construye un texto de búsqueda enriquecido con palabras clave relacionadas a cada género
    # para mejorar los resultados cuando se usa búsqueda semántica (TF-IDF)
    def build_rich_query(self, preferences):
        genre_keywords = {
            "Action": "action fight chase combat mission rescue battle explosive gun war crime",
            "Adventure": "adventure journey discovery exploration quest travel expedition",
            "Comedy": "comedy funny humorous hilarious laugh jokes parody witty fun",
            "Crime": "crime murder detective investigation mafia gangster robbery thief",
            "Drama": "drama emotional relationship family life struggle love story",
            "Horror": "horror scary fear terror haunted nightmare dark evil monster ghost",
            "Science Fiction": "science fiction future technology alien space robot AI time",
            "Thriller": "thriller suspense mystery tension psychological conspiracy spy",
            "Romance": "romance love romantic relationship couple dating marriage passion",
            "Fantasy": "fantasy magic wizard mythical dragon medieval sword epic adventure",
            "Animation": "animation animated cartoon family adventure fantasy musical",
            "Mystery": "mystery detective investigation secret clue puzzle hidden crime",
            "War": "war battle military soldier army combat history violence",
            "Music": "music musical singer concert band performance dance rock",
            "History": "history historical period epic ancient medieval war biography",
            "Western": "western cowboy outlaw sheriff gunfight desert frontier",
            "Documentary": "documentary real story history nature science biography true",
        }
        parts = []
        genres = preferences.get("genres", [])
        for g in genres:
            parts.append(g)
            parts.append(genre_keywords.get(g, ""))
        if "decade" in preferences:
            parts.append(str(preferences["decade"]))
        if "director" in preferences:
            parts.append(preferences["director"])
        if "actor" in preferences:
            parts.append(preferences["actor"])
        if "query_boosts" in preferences:
            parts.append(preferences["query_boosts"])
        return " ".join(parts)


    # Detecta si el usuario dice que no tiene preferencia ("lo que sea", "da igual", etc.)
    def is_no_preference(self, text):
        text_lower = text.lower()
        patterns = [
            "no se", "no sé", "cualquiera", "da igual", "no importa",
            "lo que sea", "como sea", "no me importa",
            "no tengo preferencia", "cualquier", "todas",
            "cualquier genero", "cualquier género",
            "cualquier epoca", "cualquier época",
        ]
        return any(p in text_lower for p in patterns)

    # Detecta si el usuario solo pide "más opciones" sin agregar nuevas preferencias
    def is_only_more(self, text, new_prefs):
        has_any_pref = bool(new_prefs and any(new_prefs.values()))
        if has_any_pref:
            return False
        text_lower = text.lower()
        patterns = ["más opciones", "mas opciones", "más", "mas",
                     "siguientes", "more"]
        return any(p in text_lower for p in patterns)

    # Genera condiciones en formato Prolog para consultar la base de hechos
    # (usado por PrologBridge para hacer inferencias lógicas)
    def build_prolog_conditions(self, preferences):
        conditions = []
        if "genres" in preferences:
            for g in preferences["genres"]:
                conditions.append(f"genero(ID, '{g}')")
        if "excluded_genres" in preferences:
            for g in preferences["excluded_genres"]:
                conditions.append(f"not(genero(ID, '{g}'))")
        if "decade" in preferences:
            conditions.append(f"decada(ID, {preferences['decade']})")
        if "director" in preferences:
            conditions.append(f"director(ID, '{preferences['director']}')")
        if "actor" in preferences:
            conditions.append(f"actor(ID, '{preferences['actor']}')")
        if "excluded_name" in preferences:
            excluded = preferences["excluded_name"]
            conditions.append(f"not(actor(ID, '{excluded}'))")
            conditions.append(f"not(director(ID, '{excluded}'))")
        return conditions
