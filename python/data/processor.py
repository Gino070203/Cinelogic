import json
import pandas as pd

class MovieProcessor:
    @staticmethod
    def extract_genre_names(genres_json):
        try:
            items = json.loads(genres_json)
            return [g["name"] for g in items]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    @staticmethod
    def extract_keyword_names(keywords_json):
        try:
            items = json.loads(keywords_json)
            return [k["name"] for k in items]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    @staticmethod
    def get_decade(release_date):
        if pd.isna(release_date):
            return None
        return (release_date.year // 10) * 10

    @staticmethod
    def movie_to_dict(movie_row):
        return {
            "id": int(movie_row["id"]),
            "title": movie_row["title"],
            "overview": movie_row.get("overview", ""),
            "genres": movie_row.get("genres", "[]"),
            "keywords": movie_row.get("keywords", "[]"),
            "popularity": movie_row.get("popularity", 0),
            "vote_average": movie_row.get("vote_average", 0),
            "decade": MovieProcessor.get_decade(
                movie_row.get("release_date", None)
            ),
        }
