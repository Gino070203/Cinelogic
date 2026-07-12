# CineLogic 🎬

**Asistente Inteligente de Recomendación Cinematográfica**

Sistema multilenguaje que integra **Scala** (funcional), **Prolog** (lógico) y **Python** (multiparadigma) para recomendar películas mediante un chat conversacional con personalidad cinéfila.

## Arquitectura

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│  Python  │◄──►│  Scala   │   │  Prolog  │
│ FastAPI  │   │ TF-IDF   │   │ Reglas   │
│ Orquesta │   │ Similitud │   │ Lógicas  │
└────┬─────┘   └──────────┘   └──────────┘
     │
┌────▼─────┐
│ Frontend │
│ Chat UI  │
└──────────┘
```

## Requisitos

- **Python** 3.13+
- **Scala** 2.13.12 + **SBT** 1.12.11
- **SWI-Prolog** 10.0.2
- **Java** 11+ (para ejecutar JAR de Scala)

## Instalación

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd CineLogic

# 2. Instalar dependencias Python
pip install -r python/requirements.txt

# 3. Compilar Scala
cd scala && sbt assembly && cd ..

# 4. Colocar dataset
# Descargar tmdb_5000_movies.csv de Kaggle en dataset/

# 5. Ejecutar
make run
# o: cd python && uvicorn api.main:app --reload
```

## Estructura del Proyecto

```
CineLogic/
├── dataset/          # Datasets CSV
├── scala/            # Módulo funcional (TF-IDF, similitud)
├── prolog/           # Módulo lógico (hechos, reglas)
├── python/           # Módulo multiparadigma (API, NLP, bridges, chatbot)
│   ├── api/          # FastAPI + rutas
│   ├── data/         # Carga y procesamiento de datos
│   ├── nlp/          # Parseo de intención del usuario
│   ├── integration/  # Puentes con Scala y Prolog
│   ├── chatbot/      # Generador de respuestas
│   └── frontend/     # Templates y estáticos (chat UI)
└── docs/             # Documentación técnica
```

## Uso

1. Abrir `http://localhost:8000` en el navegador
2. Escribir en el chat qué tipo de película buscas
3. Ejemplos: _"Quiero una película de ciencia ficción de los 2000s"_
4. El sistema responde con recomendaciones personalizadas

## Lenguajes y Paradigmas

| Lenguaje | Paradigma | Rol |
|----------|-----------|-----|
| Scala | Funcional | TF-IDF, similitud de coseno, inmutabilidad, high-order functions |
| Prolog | Lógico | Base de conocimiento, reglas de inferencia, backtracking |
| Python | Multiparadigma | Orquestación, NLP, API REST, frontend |

## Dataset

El proyecto utiliza el dataset **TMDB 5000 Movie Dataset** de Kaggle.
Debe descargarse y colocarse en `dataset/tmdb_5000_movies.csv`.
