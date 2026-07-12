// Punto de entrada del motor Scala de CineLogic
// Lee un JSON por stdin con la consulta del usuario y las películas,
// calcula similitud TF-IDF y devuelve un ranking ordenado por relevancia
package cinalogic

import org.json4s._
import org.json4s.native.JsonMethods._
import org.json4s.native.Serialization.write
import cinalogic.models._
import cinalogic.tfidf.TfIdfCalculator
import cinalogic.similarity.SimilarityEngine

object Main {
  def main(args: Array[String]): Unit = {
    implicit val formats: Formats = DefaultFormats

    // 1. Leer JSON desde stdin (enviado por ScalaBridge en Python)
    val input = scala.io.Source.stdin.getLines().mkString("\n")
    if (input.trim.isEmpty) {
      System.err.println("Error: No input provided")
      System.exit(1)
    }

    // 2. Parsear el JSON a un RecommendationRequest
    val request = try {
      parse(input).extract[RecommendationRequest]
    } catch {
      case e: Exception =>
        System.err.println(s"Error parsing input: ${e.getMessage}")
        System.exit(1)
        null
    }

    if (request == null) return

    // 3. Armar el corpus: la consulta del usuario + todas las películas convertidas a texto
    val allDocs = request.query :: request.movies.map(_.toText)
    val allTokens = allDocs.map(TfIdfCalculator.tokenize)

    // 4. Calcular IDF global y vectores TF-IDF para cada documento
    val idf = TfIdfCalculator.inverseDocumentFrequency(allTokens)
    val vectors = allTokens.map(t =>
      TfIdfCalculator.computeTfIdf(TfIdfCalculator.termFrequency(t), idf)
    )

    // 5. Separar el vector de consulta de los vectores de películas
    val queryVector = vectors.head
    val movieVectors = request.movies.map(_.id).zip(vectors.tail)

    // 6. Rankear por similitud coseno y tomar los top N
    val ranked = SimilarityEngine
      .rankBySimilarity(queryVector, movieVectors)
      .take(request.topN)

    // 7. Imprimir resultados como JSON en stdout (lo lee ScalaBridge)
    val results = ranked.map { case (id, score) => RecommendationResult(id, score) }
    println(write(results))
  }
}
