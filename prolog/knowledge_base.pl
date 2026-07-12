% knowledge_base.pl - Base de conocimiento dinámica de CineLogic
%
% Define los predicados dinámicos (hechos) que Python genera automáticamente
% para cada película, y reglas de consulta que el sistema usa para recomendar.
%
% Los hechos (genero/2, decada/2, etc.) son insertados dinámicamente en memoria
% por PrologBridge, no están escritos en este archivo.

% Declaración de predicados dinámicos (se poblan en tiempo de ejecución)
:- dynamic genero/2.       % genero(ID, NombreGenero)
:- dynamic decada/2.       % decada(ID, AnioDecada)
:- dynamic director/2.     % director(ID, NombreDirector)
:- dynamic actor/2.        % actor(ID, NombreActor)
:- dynamic popularidad/2.  % popularidad(ID, ValorPopularidad)
:- dynamic calificacion/2. % calificacion(ID, PuntajePromedio)

% Regla base: una película es recomendable si tiene al menos un género
recomendar(ID) :-
    genero(ID, _).

% Recomienda todas las películas de un género específico
recomendar_por_genero(ID, Genero) :-
    genero(ID, Genero).

% Recomienda todas las películas de una década específica
recomendar_por_decada(ID, Decada) :-
    decada(ID, Decada).

% Recomienda todas las películas de un director específico
recomendar_por_director(ID, Director) :-
    director(ID, Director).

% Recomienda todas las películas de un actor específico
recomendar_por_actor(ID, Actor) :-
    actor(ID, Actor).

% Regla compuesta: recomienda una película si cumple TODAS las condiciones de una lista
% Ejemplo: recomendar_si_cumple(ID, [genero('Action'), decada(2000)])
recomendar_si_cumple(ID, Preferencias) :-
    maplist(cumple_condicion(ID), Preferencias).

% Verifica si una película cumple una condición individual
cumple_condicion(ID, genero(Genero)) :-
    genero(ID, Genero).

cumple_condicion(ID, decada(Decada)) :-
    decada(ID, Decada).

cumple_condicion(ID, director(Director)) :-
    director(ID, Director).

cumple_condicion(ID, actor(Actor)) :-
    actor(ID, Actor).

% Regla combinada: recomienda por género + década + calificación mínima
recomendar_top(ID, Genero, Decada, CalificacionMin) :-
    genero(ID, Genero),
    decada(ID, Decada),
    calificacion(ID, Cal),
    Cal >= CalificacionMin.
