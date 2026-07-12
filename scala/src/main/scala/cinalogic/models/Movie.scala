// Modelos de datos usados para la comunicación entre Python y Scala via JSON
package cinalogic.models

// Representa una película con sus campos de texto para el análisis TF-IDF
case class MovieData(
  id: Int,
  title: String,
  overview: String,   // Resumen/sinopsis
  genres: String,     // Nombres de géneros separados por espacio
  keywords: String    // Palabras clave enriquecidas (incluye actores/directores)
) {
  // Concatena todos los campos de texto para formar el "documento" a vectorizar
  def toText: String = s"$title $overview $genres $keywords"
}

// Solicitud completa: la consulta del usuario, la lista de películas y cuántas devolver
case class RecommendationRequest(
  query: String,
  movies: List[MovieData],
  topN: Int
)
