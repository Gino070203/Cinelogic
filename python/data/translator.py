# ──────────────────────────────────────────────
# TitleTranslator: traduce títulos y sinopsis
# ──────────────────────────────────────────────
# El dataset TMDB está en inglés. Este módulo traduce
# títulos y sinopsis a español usando Google Translate.
#
# IMPORTANTE: tiene un caché en disco (title_cache.json)
# para no llamar a la API cada vez. La primera ejecución
# es lenta; las siguientes son instantáneas.

import json
import os
from pathlib import Path

# Archivo donde se guardan las traducciones ya hechas
CACHE_PATH = os.path.join(
    Path(__file__).resolve().parent, "title_cache.json"
)


class TitleTranslator:
    """
    Traduce títulos y sinopsis de películas de inglés a español.
    Usa un caché persistente para evitar traducir lo mismo dos veces.
    """

    def __init__(self):
        # cache: {"The Godfather": "El Padrino", "overview_12345": "traducción...", ...}
        self.cache = self._load_cache()
        self.translator = None  # se crea bajo demanda

    # ───── Manejo del caché ─────

    def _load_cache(self):
        """Carga el caché desde title_cache.json (si existe)."""
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """Guarda el caché a disco para usos futuros."""
        try:
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except:
            pass

    # ───── Traducción (con fallback) ─────

    def _translate_text(self, text):
        """Traduce un texto de inglés a español usando deep_translator.
        Si falla, intenta con googletrans como respaldo.
        Si ambos fallan, devuelve el texto original sin traducir."""
        if not text:
            return text
        try:
            from deep_translator import GoogleTranslator
            if self.translator is None:
                self.translator = GoogleTranslator(source="en", target="es")
            return self.translator.translate(text)
        except:
            try:
                from googletrans import Translator
                fallback = Translator()
                return fallback.translate(text, src="en", dest="es").text
            except:
                return text

    # ───── Traducción de listas de películas ─────

    def translate_titles(self, movies):
        """Traduce el título de cada película en la lista.
        Si el título ya está en caché, lo reusa.
        Si no, lo traduce y lo guarda en caché.
        Modifica la lista in-place."""
        if not movies:
            return movies
        try:
            for m in movies:
                title = m.get("title", "")
                if not title:
                    continue
                if title in self.cache:
                    m["title"] = self.cache[title]
                else:
                    translated = self._translate_text(title)
                    if translated and translated != title:
                        self.cache[title] = translated
                        m["title"] = translated
            self._save_cache()
        except:
            pass
        return movies

    def translate_overviews(self, movies):
        """Traduce la sinopsis de cada película en la lista.
        Usa hash(overview) como clave de caché porque las
        sinopsis son textos largos."""
        if not movies:
            return movies
        try:
            for m in movies:
                overview = m.get("overview", "")
                if not overview:
                    continue
                cache_key = f"overview_{hash(overview)}"
                if cache_key in self.cache:
                    m["overview"] = self.cache[cache_key]
                else:
                    translated = self._translate_text(overview)
                    if translated and translated != overview:
                        self.cache[cache_key] = translated
                        m["overview"] = translated
            self._save_cache()
        except:
            pass
        return movies
