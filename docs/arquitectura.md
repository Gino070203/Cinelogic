# Arquitectura de CineLogic

## Visión General

CineLogic es un sistema multilenguaje que integra tres paradigmas de programación:

- **Programación Funcional** (Scala): Motor TF-IDF y similitud de coseno
- **Programación Lógica** (Prolog): Base de conocimiento y reglas de inferencia
- **Multiparadigma** (Python): Orquestación, NLP, API y frontend

## Diagrama de Arquitectura

```
                    ┌─────────────────────────────────────┐
                    │         Frontend (Bootstrap)         │
                    │    Jinja2 Templates + CSS + JS       │
                    └──────────────┬──────────────────────┘
                                   │ HTTP POST /chat
                    ┌──────────────▼──────────────────────┐
                    │         Python (FastAPI)             │
                    │         Orquestador Central          │
                    ├──────────┬──────────┬────────────────┤
                    │  NLP/    │  data/   │  integration/  │
                    │  Intent  │  Pandas  │  Scala+Prolog  │
                    │  Parser  │  Loader  │  Bridges       │
                    └─────┬────┴──────────┴────┬───────────┘
                          │                    │
                    ┌─────▼─────┐       ┌──────▼────────┐
                    │   Scala    │       │    Prolog      │
                    │  (JAR vía  │       │  (pyswip vía   │
                    │  subproc)  │       │  embebido)     │
                    └───────────┘       └───────────────┘
```

## Flujo de Datos

1. **Usuario** escribe mensaje en el chat
2. **JavaScript** envía POST a `/chat`
3. **IntentParser** extrae preferencias (género, década, director, actor)
4. **PrologBridge** construye reglas dinámicas y consulta la base de conocimiento
5. **MovieLoader** obtiene datos de películas candidatas desde el dataset
6. **ScalaBridge** envía datos a Scala JAR para ranking TF-IDF
7. **ResponseGenerator** combina resultados y genera respuesta cinéfila
8. **Frontend** muestra la respuesta en formato chat

## Comunicación entre Lenguajes

| Desde | Hacia | Método | Formato |
|-------|-------|--------|---------|
| Python | Scala | Subprocess JAR (stdin/stdout) | JSON |
| Python | Prolog | pyswip (embebido en proceso) | Consultas Prolog |

## Stack Tecnológico

- **Backend**: FastAPI (Python 3.13)
- **Frontend**: Jinja2 + Bootstrap 5 + JavaScript vanilla
- **Dataset**: TMDB 5000 Movies (Kaggle)
- **Motor Funcional**: Scala 2.13.12 + SBT 1.12.11
- **Motor Lógico**: SWI-Prolog 10.0.2 + pyswip
- **Procesamiento**: Pandas para datos tabulares
