:- use_module(library(clpfd)).
:- set_prolog_flag(answer_write_options, [max_depth(0)]).

% Main solver predicate
sudoku(Rows) :-
    length(Rows, 9),
    maplist(same_length(Rows), Rows),

    % Flatten the 9x9 grid into one list of 81 cells
    append(Rows, Cells),

    % Every cell must be an integer from 1 to 9
    Cells ins 1..9,

    % Every row must contain distinct numbers
    maplist(all_distinct, Rows),

    % Every column must contain distinct numbers
    transpose(Rows, Columns),
    maplist(all_distinct, Columns),

    % Every 3x3 box must contain distinct numbers
    Rows = [A,B,C,D,E,F,G,H,I],
    boxes(A, B, C),
    boxes(D, E, F),
    boxes(G, H, I),

    % Search for actual values
    maplist(label, Rows).

% Checks 3 rows at a time and enforces 3x3 box constraints
boxes([], [], []).
boxes(
    [A,B,C|Bs1],
    [D,E,F|Bs2],
    [G,H,I|Bs3]
) :-
    all_distinct([A,B,C,D,E,F,G,H,I]),
    boxes(Bs1, Bs2, Bs3).