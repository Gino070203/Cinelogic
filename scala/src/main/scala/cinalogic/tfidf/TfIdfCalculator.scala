// ============================================================================
// Módulo: TfIdfCalculator
// Descripción: Implementación del algoritmo TF-IDF (Term Frequency - Inverse
//   Document Frequency) utilizado para convertir textos de películas y
//   consultas de usuarios en vectores numéricos. Esto permite medir qué tan
//   relevante es cada película respecto a lo que el usuario busca.
//
// El proceso completo es:
//   1. Tokenizar: dividir el texto en palabras individuales
//   2. Calcular TF: qué tan frecuente es cada término en el documento
//   3. Calcular IDF: qué tan raro es cada término en el corpus completo
//   4. Computar TF-IDF: multiplicar TF x IDF para obtener el peso final
//
// Este módulo es llamado desde Main.scala, donde se construye el corpus
// (consulta del usuario + todas las películas), se tokeniza cada documento,
// se calculan los vectores TF-IDF y luego SimilarityEngine calcula la
// similitud coseno entre la consulta y cada película para rankearlas.
// ============================================================================
package cinalogic.tfidf

object TfIdfCalculator {

  // ==========================================================================
  // Stop Words: conjunto de palabras vacías en inglés que se filtran durante
  // la tokenización. Estas palabras (artículos, preposiciones, pronombres,
  // etc.) aparecen en casi todos los textos y no aportan información útil
  // para diferenciar el contenido de una película de otra.
  //
  // Por ejemplo, en la frase "the dark knight rises", las palabras "the"
  // aparece en casi cualquier texto, pero "dark", "knight" y "rises" son
  // las que realmente distinguen de qué película se trata. Por eso filtramos
  // "the" y conservamos el resto.
  // ==========================================================================
  private val StopWords: Set[String] = Set(
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "ought", "used", "this", "that", "these", "those", "it", "its",
    "he", "she", "they", "them", "their", "his", "her", "my", "your",
    "our", "we", "you", "i", "me", "mine", "yours", "ours", "theirs",
    "not", "no", "nor", "none", "neither", "so", "very", "just", "too",
    "also", "only", "quite", "some", "any", "each", "every", "all",
    "both", "few", "many", "much", "more", "most", "other", "another",
    "such", "what", "which", "who", "whom", "when", "where", "why", "how"
  )

  // ==========================================================================
  // tokenize(text)
  // --------------------
  // Propósito: Convierte un texto crudo (título + resumen + generos +
  //   palabras clave de una pelicula, o la consulta del usuario) en una
  //   lista de tokens (palabras) limpias y significativas.
  //
  // Proceso paso a paso:
  //   1. text.toLowerCase
  //      Convierte todo el texto a minusculas para que palabras como
  //      "Action" y "action" se traten como el mismo termino. Esto es
  //      importante porque en los datos las palabras pueden venir con
  //      mayusculas o minusculas segun el contexto.
  //
  //   2. .replaceAll("[^a-z0-9\\s]", " ")
  //      Reemplaza cualquier caracter que NO sea letra (a-z), numero (0-9)
  //      o espacio en blanco (\s) por un espacio. Esto elimina signos de
  //      puntuacion como comas, puntos, parentesis, apostrofes, etc.
  //      Por ejemplo: "Inception!" se convierte en "Inception ",
  //      "science-fiction" se convierte en "science fiction" (dos palabras).
  //
  //   3. .split("\\s+")
  //      Divide el texto por uno o mas espacios en blanco, obteniendo
  //      asi una lista de palabras individuales. El "+" indica que pueden
  //      haber multiples espacios seguidos (caso comun tras eliminar
  //      puntuacion).
  //
  //   4. .toList
  //      Convierte el arreglo resultante de split() a una lista de Scala
  //      para poder usar las operaciones funcionales posteriores (filter).
  //
  //   5. .filter(w => w.nonEmpty && !StopWords.contains(w))
  //      Elimina dos tipos de elementos:
  //      - Palabras vacias (w.nonEmpty): tokens que quedaron vacios tras
  //        el proceso de limpieza
  //      - Stop words: palabras como "the", "and", "of" que estan en el
  //        conjunto StopWords porque no aportan significado distintivo
  //
  // Parametros:
  //   text: String - El texto a procesar (puede ser el titulo, resumen,
  //         generos y palabras clave concatenados de una pelicula, o la
  //         consulta escrita por el usuario)
  //
  // Retorna:
  //   List[String] - Lista de tokens (palabras) significativas y limpias,
  //   listas para ser procesadas por termFrequency()
  //
  // Ejemplo:
  //   tokenize("The Dark Knight Rises!")
  //   -> Paso 1: "the dark knight rises!"
  //   -> Paso 2: "the dark knight rises "
  //   -> Paso 3: ["the", "dark", "knight", "rises"]
  //   -> Paso 5: ["dark", "knight", "rises"]  (se filtro "the")
  // ==========================================================================
  def tokenize(text: String): List[String] = {
    text.toLowerCase
      .replaceAll("[^a-z0-9\\s]", " ")
      .split("\\s+")
      .toList
      .filter(w => w.nonEmpty && !StopWords.contains(w))
  }

  // ==========================================================================
  // termFrequency(tokens)
  // --------------------
  // Propósito: Calcula la frecuencia de cada termino dentro de un unico
  //   documento (TF). La frecuencia de un termino indica que tan importante
  //   es dentro de ese documento especifico.
  //
  // Formula matematica:
  //   TF(termino) = (cantidad de veces que aparece el termino en el documento)
  //                 / (total de palabras en el documento)
  //
  // Esto normaliza el valor para que documentos de distinta longitud puedan
  // compararse. Un termino que aparece 3 veces en un texto de 10 palabras
  // (TF=0.3) es mas relevante que si aparece 3 veces en un texto de 100
  // palabras (TF=0.03).
  //
  // Proceso paso a paso:
  //   1. val total = tokens.length.toDouble
  //      Obtenemos la cantidad total de palabras del documento. Se convierte
  //      a Double para que la division posterior no sea entera.
  //
  //   2. if (total == 0) Map.empty
  //      Si el documento no tiene palabras (vacio), devolvemos un mapa
  //      vacio para evitar division por cero.
  //
  //   3. tokens.groupBy(identity)
  //      Agrupa las palabras iguales. Por ejemplo, si el documento es
  //      ["dark", "knight", "dark"], groupBy crea:
  //      Map("dark" -> List("dark", "dark"), "knight" -> List("knight"))
  //
  //   4. .view.mapValues(_.length / total).toMap
  //      Para cada grupo, divide la cantidad de apariciones por el total
  //      de palabras. Siguiendo el ejemplo:
  //      Map("dark" -> 2/3=0.666, "knight" -> 1/3=0.333)
  //      .view crea una vista perezosa para no copiar la coleccion
  //      innecesariamente, y .toMap materializa el resultado.
  //
  // Parametros:
  //   tokens: List[String] - Lista de palabras (tokens) de un solo
  //           documento, obtenida tras llamar a tokenize()
  //
  // Retorna:
  //   Map[String, Double] - Mapa donde cada clave es un termino y su valor
  //   es la frecuencia normalizada (entre 0.0 y 1.0). La suma de todos
  //   los valores del mapa es 1.0.
  // ==========================================================================
  def termFrequency(tokens: List[String]): Map[String, Double] = {
    val total = tokens.length.toDouble
    if (total == 0) Map.empty
    else tokens.groupBy(identity).view.mapValues(_.length / total).toMap
  }

  // ==========================================================================
  // inverseDocumentFrequency(documents)
  // --------------------
  // Proposito: Calcula la frecuencia inversa de documento (IDF) para cada
  //   termino en el corpus completo. IDF mide que tan comun o raro es un
  //   termino a traves de todos los documentos. Los terminos que aparecen
  //   en muchos documentos reciben un IDF bajo (son palabras genericas),
  //   mientras que los que aparecen en pocos documentos reciben un IDF alto
  //   (son palabras distintivas).
  //
  // Formula matematica:
  //   IDF(termino) = ln(1 + N / (1 + df))
  //
  //   donde:
  //     N  = numero total de documentos en el corpus
  //     df = cantidad de documentos que contienen el termino (document
  //          frequency)
  //
  // Se suma 1 tanto al numerador como al denominador para evitar:
  //   - Division por cero (si un termino no aparece en ningun documento,
  //     aunque esto no ocurre en la practica porque IDF se calcula solo
  //     sobre terminos que existen en al menos un documento)
  //   - Valores infinitos (log de 0)
  //
  // Interpretacion:
  //   - Si un termino aparece en todos los documentos (df = N), entonces
  //     IDF ≈ ln(1 + N/(1+N)) ≈ ln(1 + ~1) ≈ 0.69 -> peso bajo
  //   - Si un termino aparece en solo 1 documento (df = 1), entonces
  //     IDF = ln(1 + N/2) -> peso alto (para N=10: ln(6) ≈ 1.79)
  //   - Si un termino aparece en 0 documentos teorico:
  //     IDF = ln(1 + N/1) -> el maximo posible
  //
  // Proceso paso a paso:
  //   1. val numDocs = documents.length.toDouble
  //      Contamos cuantos documentos tiene el corpus. Es la "N" de la
  //      formula. Se convierte a Double para la division.
  //
  //   2. val allTerms = documents.flatten.distinct
  //      Unimos todos los tokens de todos los documentos en una sola
  //      lista (flatten) y luego nos quedamos solo con los terminos
  //      unicos (distinct). Estos son todos los terminos que existen
  //      en el corpus.
  //
  //   3. allTerms.map { term => ... }
  //      Para cada termino unico en el corpus:
  //
  //   4. val docFrequency = documents.count(_.contains(term))
  //      Contamos en cuantos documentos aparece este termino. Importante:
  //      NO contamos cuantas veces aparece (eso es TF), sino en CUANTOS
  //      documentos distintos aparece.
  //
  //   5. term -> math.log(1.0 + numDocs / (1.0 + docFrequency))
  //      Aplicamos la formula matematica del IDF. math.log es logaritmo
  //      natural (base e). Cuanto mayor sea docFrequency, menor sera el
  //      resultado.
  //
  //   6. .toMap
  //      Convertimos la coleccion de pares (termino -> idf) en un Map
  //      para acceso rapido por termino.
  //
  // Parametros:
  //   documents: List[List[String]] - Lista de documentos, donde cada
  //              documento es una lista de tokens (el resultado de aplicar
  //              tokenize() a cada texto). El primer documento del corpus
  //              es la consulta del usuario y los siguientes son las
  //              peliculas.
  //
  // Retorna:
  //   Map[String, Double] - Mapa donde cada clave es un termino y su valor
  //   es el IDF correspondiente. Valores tipicos van de ~0.5 (terminos
  //   muy comunes) a ~4.0 (terminos muy raros).
  // ==========================================================================
  def inverseDocumentFrequency(documents: List[List[String]]): Map[String, Double] = {
    val numDocs = documents.length.toDouble
    val allTerms = documents.flatten.distinct
    allTerms.map { term =>
      val docFrequency = documents.count(_.contains(term))
      term -> math.log(1.0 + numDocs / (1.0 + docFrequency))
    }.toMap
  }

  // ==========================================================================
  // computeTfIdf(tf, idf)
  // --------------------
  // Proposito: Combina los valores de TF e IDF para obtener el peso final
  //   de cada termino en un documento. El peso TF-IDF es mayor cuando un
  //   termino aparece muchas veces en el documento (TF alto) pero aparece
  //   en pocos documentos del corpus (IDF alto).
  //
  // Formula matematica:
  //   TF-IDF(termino) = TF(termino) x IDF(termino)
  //
  // Esto significa que:
  //   - Un termino que aparece 5 veces en el documento (TF=0.5) y es raro
  //     en el corpus (IDF=2.0) tendra TF-IDF = 0.5 x 2.0 = 1.0
  //   - Un termino que aparece 5 veces (TF=0.5) pero es muy comun en el
  //     corpus (IDF=0.5) tendra TF-IDF = 0.5 x 0.5 = 0.25
  //
  // El resultado es un vector donde cada dimension es un termino y su
  // valor es el peso TF-IDF. Estos vectores son los que se comparan
  // mediante similitud coseno en SimilarityEngine.
  //
  // Proceso paso a paso:
  //   1. tf.map { case (term, tfVal) => ... }
  //      Iteramos sobre cada termino que existe en el documento actual
  //      (el mapa TF solo contiene terminos que aparecen en este documento).
  //
  //   2. idf.getOrElse(term, 0.0)
  //      Buscamos el IDF de este termino en el mapa IDF global. Si el
  //      termino no existe en el mapa IDF (caso borde), usamos 0.0 como
  //      valor por defecto, lo que hace que el peso TF-IDF sea 0.
  //
  //   3. term -> tfVal * idfVal
  //      Multiplicamos TF por IDF para obtener el peso final del termino
  //      en este documento.
  //
  // Nota: Solo se procesan terminos que existen en el documento actual.
  // Los terminos que estan en el IDF pero no en el TF de este documento
  // simplemente tienen peso 0 para este documento, lo cual es correcto
  // porque no aparecen en el.
  //
  // Parametros:
  //   tf: Map[String, Double] - Mapa de frecuencias del documento actual
  //       (resultado de termFrequency() para un solo documento)
  //   idf: Map[String, Double] - Mapa de IDF global para todo el corpus
  //        (resultado de inverseDocumentFrequency())
  //
  // Retorna:
  //   Map[String, Double] - Vector TF-IDF del documento. Cada clave es un
  //   termino y su valor es el peso combinado. Este vector se usa luego
  //   en SimilarityEngine.cosineSimilarity() para comparar la consulta
  //   del usuario con cada pelicula.
  // ==========================================================================
  def computeTfIdf(tf: Map[String, Double], idf: Map[String, Double]): Map[String, Double] = {
    tf.map { case (term, tfVal) =>
      term -> tfVal * idf.getOrElse(term, 0.0)
    }
  }
}
