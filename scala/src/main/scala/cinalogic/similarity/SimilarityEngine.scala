// Motor de similitud: compara vectores TF-IDF usando similitud coseno
// y rankea las películas de más a menos relevante respecto a la consulta
package cinalogic.similarity

object SimilarityEngine {

  // Calcula la magnitud (norma) de un vector
  def magnitude(vector: Map[String, Double]): Double = {
    math.sqrt(vector.values.map(v => v * v).sum)
  }

  // Producto punto entre dos vectores (solo términos que existen en ambos)
  def dotProduct(v1: Map[String, Double], v2: Map[String, Double]): Double = {
    v1.keySet.intersect(v2.keySet)
      .map(k => v1(k) * v2(k))
      .sum
  }

  // Similitud coseno: mide el ángulo entre dos vectores (0 = ortogonal, 1 = idénticos)
  def cosineSimilarity(v1: Map[String, Double], v2: Map[String, Double]): Double = {
    val dot = dotProduct(v1, v2)
    val mag1 = magnitude(v1)
    val mag2 = magnitude(v2)
    if (mag1 == 0.0 || mag2 == 0.0) 0.0
    else dot / (mag1 * mag2)
  }

  // Rankea una lista de vectores de películas por su similitud coseno con el vector de consulta
  def rankBySimilarity(
    queryVector: Map[String, Double],
    documentVectors: List[(Int, Map[String, Double])]
  ): List[(Int, Double)] = {
    documentVectors
      .map { case (id, vec) => (id, cosineSimilarity(queryVector, vec)) }
      .sortBy(-_._2)  // Orden descendente por score
  }
}
