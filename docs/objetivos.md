# Objetivos del Proyecto CineLogic

## Objetivo General

Diseñar e implementar un sistema de software multilenguaje que integre Scala, Prolog y Python, aplicando principios de modularidad y separación de responsabilidades.

## Objetivos Específicos

| # | Objetivo | Implementación | Lenguaje |
|---|----------|----------------|----------|
| 1 | Implementar la lógica principal del sistema utilizando Scala | `TfIdfCalculator.scala`, `SimilarityEngine.scala` | Scala |
| 2 | Desarrollar un módulo de razonamiento lógico mediante Prolog | `knowledge_base.pl`, `rules.pl`, consultas dinámicas | Prolog |
| 3 | Utilizar Python como lenguaje de integración y procesamiento auxiliar | FastAPI, NLP, bridges, chatbot | Python |
| 4 | Definir una estructura de carpetas clara y extensible para el proyecto | Organización por módulos independientes | — |
| 5 | Establecer mecanismos de comunicación entre los distintos lenguajes | ScalaBridge (subprocess), PrologBridge (pyswip) | Python |

## Alcance del Proyecto

- Diseño de la arquitectura del sistema
- Definición de módulos independientes por lenguaje
- Integración funcional entre Scala, Prolog y Python
- Documentación técnica del sistema
- Interfaz de chat conversacional con personalidad cinéfila
- Recomendación basada en contenido (TF-IDF + similitud de coseno)
- Razonamiento lógico con reglas dinámicas en Prolog

## Funcionalidades Clave

1. **Chatbot cinéfilo**: Interfaz conversacional con tono apasionado por el cine
2. **NLP básico**: Extracción de preferencias (género, década, director, actor) de texto libre
3. **Ranking TF-IDF**: Motor funcional en Scala que computa similitud entre películas
4. **Reglas lógicas**: Prolog con reglas dinámicas generadas desde Python según la consulta
5. **Fallback automático**: Cada bridge tiene modo fallback si el módulo respectivo no está disponible
