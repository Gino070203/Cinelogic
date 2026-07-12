// Resultado de la recomendación: ID de la película y su puntaje de similitud
package cinalogic.models

case class RecommendationResult(
  id: Int,
  score: Double   // Puntaje de similitud coseno (0.0 a 1.0)
)
