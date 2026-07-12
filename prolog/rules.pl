% rules.pl - Reglas de razonamiento lógico para el sistema de recomendación CineLogic
%
% Define reglas que infieren relaciones entre películas basadas en los hechos
% (genero, decada, director, actor, popularidad) que Python genera dinámicamente.

% Una película es "clásica" si su década es anterior a 1980
clasica(ID) :-
    decada(ID, Decada),
    Decada < 1980.

% Una película es "moderna" si su década es 2000 o posterior
moderna(ID) :-
    decada(ID, Decada),
    Decada >= 2000.

% Recomienda películas que compartan género Y década (similares temática y cronológicamente)
recomendar_similar(ID, OtraID) :-
    ID \= OtraID,
    genero(ID, Genero),
    genero(OtraID, Genero),
    decada(ID, Decada),
    decada(OtraID, Decada).

% Recomienda películas dirigidas por la misma persona
recomendar_mismo_director(ID, OtraID) :-
    ID \= OtraID,
    director(ID, Director),
    director(OtraID, Director).

% Recomienda películas con el mismo actor
recomendar_mismo_actor(ID, OtraID) :-
    ID \= OtraID,
    actor(ID, Actor),
    actor(OtraID, Actor).

% Clasifica una película como "muy popular" si su popularidad > 50
muy_popular(ID) :-
    popularidad(ID, Pop),
    Pop > 50.

% Clasifica una película como "poco conocida" si su popularidad < 10
poco_conocida(ID) :-
    popularidad(ID, Pop),
    Pop < 10.
