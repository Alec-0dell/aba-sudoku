from collections.abc import Iterable, Sequence
from typing import TypeAlias


Grid: TypeAlias = list[list[int]]
Cell: TypeAlias = tuple[int, int]

DIGITS = set(range(1, 10))
GRID_SIZE = 9
BOX_SIZE = 3
CELL_COUNT = GRID_SIZE * GRID_SIZE


class BoardValidationError(ValueError):
    """Raised when a puzzle or grid cannot be interpreted as a Sudoku board."""


def parse_puzzle_string(puzzle: str) -> Grid:
    """Parse an 81-character Sudoku string into a 9x9 integer grid.

    Digits 1-9 are givens, 0 is blank. Dots are accepted as blanks to make the
    API forgiving for common Sudoku notation.
    """

    normalized = "".join(puzzle.split())
    if len(normalized) != CELL_COUNT:
        raise BoardValidationError(f"Puzzle must contain exactly {CELL_COUNT} cells.")

    values: list[int] = []
    for index, char in enumerate(normalized):
        if char == ".":
            values.append(0)
        elif char.isdigit():
            values.append(int(char))
        else:
            raise BoardValidationError(
                f"Puzzle contains invalid character {char!r} at index {index}."
            )

    return [values[row : row + GRID_SIZE] for row in range(0, CELL_COUNT, GRID_SIZE)]


def grid_to_string(grid: Sequence[Sequence[int]]) -> str:
    _validate_grid_shape(grid)
    return "".join(str(cell) for row in grid for cell in row)


def validate_givens(grid: Sequence[Sequence[int]]) -> list[str]:
    errors = _shape_errors(grid)
    if errors:
        return errors

    for unit_type, index, values in _iter_units(grid):
        duplicates = _duplicates([value for value in values if value != 0])
        if duplicates:
            joined = ", ".join(str(value) for value in duplicates)
            errors.append(f"{unit_type} {index + 1} has duplicate givens: {joined}.")

    return errors


def validate_complete_solution(grid: Sequence[Sequence[int]]) -> list[str]:
    errors = _shape_errors(grid)
    if errors:
        return errors

    for row_index, row in enumerate(grid):
        if any(value == 0 for value in row):
            errors.append(f"Row {row_index + 1} contains blanks.")

    for unit_type, index, values in _iter_units(grid):
        value_set = set(values)
        if value_set != DIGITS:
            errors.append(f"{unit_type} {index + 1} must contain digits 1-9 exactly once.")

    return errors


def peers(row: int, col: int) -> set[Cell]:
    _validate_coordinate(row, col)

    row_peers = {(row, peer_col) for peer_col in range(GRID_SIZE)}
    col_peers = {(peer_row, col) for peer_row in range(GRID_SIZE)}

    box_row = (row // BOX_SIZE) * BOX_SIZE
    box_col = (col // BOX_SIZE) * BOX_SIZE
    box_peers = {
        (peer_row, peer_col)
        for peer_row in range(box_row, box_row + BOX_SIZE)
        for peer_col in range(box_col, box_col + BOX_SIZE)
    }

    return (row_peers | col_peers | box_peers) - {(row, col)}


def box_index(row: int, col: int) -> int:
    _validate_coordinate(row, col)
    return (row // BOX_SIZE) * BOX_SIZE + (col // BOX_SIZE)


def _validate_grid_shape(grid: Sequence[Sequence[int]]) -> None:
    errors = _shape_errors(grid)
    if errors:
        raise BoardValidationError(errors[0])


def _shape_errors(grid: Sequence[Sequence[int]]) -> list[str]:
    if len(grid) != GRID_SIZE:
        return [f"Grid must contain exactly {GRID_SIZE} rows."]

    errors: list[str] = []
    for row_index, row in enumerate(grid):
        if len(row) != GRID_SIZE:
            errors.append(f"Row {row_index + 1} must contain exactly {GRID_SIZE} cells.")
            continue
        for col_index, value in enumerate(row):
            if not isinstance(value, int) or value < 0 or value > 9:
                errors.append(
                    f"Cell ({row_index + 1}, {col_index + 1}) must be an integer from 0 to 9."
                )
    return errors


def _iter_units(grid: Sequence[Sequence[int]]) -> Iterable[tuple[str, int, list[int]]]:
    for row_index in range(GRID_SIZE):
        yield "Row", row_index, list(grid[row_index])

    for col_index in range(GRID_SIZE):
        yield "Column", col_index, [grid[row_index][col_index] for row_index in range(GRID_SIZE)]

    for box in range(GRID_SIZE):
        box_row = (box // BOX_SIZE) * BOX_SIZE
        box_col = (box % BOX_SIZE) * BOX_SIZE
        values = [
            grid[row][col]
            for row in range(box_row, box_row + BOX_SIZE)
            for col in range(box_col, box_col + BOX_SIZE)
        ]
        yield "Box", box, values


def _duplicates(values: list[int]) -> list[int]:
    seen: set[int] = set()
    duplicates: set[int] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _validate_coordinate(row: int, col: int) -> None:
    if row < 0 or row >= GRID_SIZE or col < 0 or col >= GRID_SIZE:
        raise BoardValidationError("Coordinates must be between 0 and 8.")


PEERS: dict[Cell, set[Cell]] = {
    (row, col): peers(row, col)
    for row in range(GRID_SIZE)
    for col in range(GRID_SIZE)
}
