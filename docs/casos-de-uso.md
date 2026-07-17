# Diagramas de Casos de Uso - CineLogic

## Actores

- **Visitante**: Usuario no autenticado que navega por el catalogo.
- **Usuario**: Usuario autenticado que puede chatear, recibir recomendaciones y gestionar favoritos.
- **Sistema**: El sistema mismo, que ejecuta logica de negocio (Prolog, Scala, TMDB).

---

## Diagrama PlantUML

```plantuml
@startuml
left to right direction
actor Visitante as V
actor Usuario as U
actor Sistema as S

rectangle "CineLogic" {
  usecase (Registrarse) as UC1
  usecase (Iniciar Sesion) as UC2
  usecase (Cerrar Sesion) as UC3
  usecase (Ver Cartelera) as UC4
  usecase (Filtrar por Genero) as UC5
  usecase (Ver Detalle de Pelicula) as UC6
  usecase (Reproducir Trailer) as UC7
  usecase (Chatear con Asistente) as UC8
  usecase (Especificar Preferencias) as UC9
  usecase (Recibir Recomendaciones) as UC10
  usecase (Solicitar Mas Opciones) as UC11
  usecase (Cambiar Preferencias) as UC12
  usecase (Agregar o Quitar Favoritos) as UC13
  usecase (Ver Favoritos) as UC14
  usecase (Recomendar desde Favoritos) as UC15
  usecase (Filtrar con Logica) as UC16
  usecase (Rankear por Similitud) as UC17
}

V --> UC1
V --> UC4
V --> UC5
V --> UC6

U --> UC2
U --> UC3
U --> UC4
U --> UC5
U --> UC6
U --> UC7
U --> UC8
U --> UC11
U --> UC13
U --> UC14
U --> UC15

UC8 --> UC9 : incluye
UC8 --> UC10 : incluye
UC8 --> UC12 : incluye
UC13 --> UC14 : incluye
UC15 --> UC10 : incluye

S --> UC16
S --> UC17
@enduml
```

---

## Diagrama Mermaid

```mermaid
graph TB
  subgraph "Sistema CineLogic"
    UC1[Registrarse]
    UC2[Iniciar Sesion]
    UC3[Cerrar Sesion]
    UC4[Ver Cartelera]
    UC5[Filtrar por Genero]
    UC6[Ver Detalle de Pelicula]
    UC7[Reproducir Trailer]
    UC8[Chatear con Asistente]
    UC9[Especificar Preferencias]
    UC10[Recibir Recomendaciones]
    UC11[Solicitar Mas Opciones]
    UC12[Cambiar Preferencias]
    UC13[Agregar o Quitar Favoritos]
    UC14[Ver Favoritos]
    UC15[Recomendar desde Favoritos]
    UC16[Filtrar con Logica]
    UC17[Rankear por Similitud]
  end

  Visitante --> UC1
  Visitante --> UC4
  Visitante --> UC5
  Visitante --> UC6

  Usuario --> UC2
  Usuario --> UC3
  Usuario --> UC4
  Usuario --> UC5
  Usuario --> UC6
  Usuario --> UC7
  Usuario --> UC8
  Usuario --> UC11
  Usuario --> UC13
  Usuario --> UC14
  Usuario --> UC15

  UC8 -.-> UC9
  UC8 -.-> UC10
  UC8 -.-> UC12
  UC13 -.-> UC14
  UC15 -.-> UC10

  Sistema --> UC16
  Sistema --> UC17
```

---

## Leyenda

- `-->` : el actor participa en el caso de uso
- `..>` (Mermaid) / `--> : incluye` (PlantUML) : relacion de inclusion entre casos de uso
- **Visitante**: Solo puede registrarse, ver cartelera, filtrar por genero y ver detalle.
- **Usuario**: Hereda todo lo del visitante (excepto registrarse) y agrega autenticacion, chat, favoritos y recomendaciones.
- **Sistema**: Ejecuta logica interna (Prolog para filtrado deductivo, Scala para ranking TF-IDF).
