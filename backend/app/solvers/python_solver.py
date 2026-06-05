from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from backend.app.core.board import (
    BOX_SIZE,
    BoardValidationError,
    Cell,
    DIGITS,
    GRID_SIZE,
    Grid,
    PEERS,
    grid_to_string,
    parse_puzzle_string,
    validate_complete_solution,
    validate_givens,
)
from backend.app.core.solver_contract import (
    SolverOptions,
    SolverResult,
    SolverStats,
    SolverStep,
)


@dataclass(frozen=True)
class PlacementTrace:
    row: int
    col: int
    value: int
    reason: str
    details: str

    @property
    def index(self) -> int:
        return self.row * GRID_SIZE + self.col


@dataclass
class SearchStats:
    guesses: int = 0
    backtracks: int = 0
    constraints_checked: int = 0


@dataclass(frozen=True)
class HiddenSingle:
    row: int
    col: int
    value: int
    unit_label: str


class PythonSudokuSolver:
    name = "python"

    def solve(self, puzzle: str, options: SolverOptions | None = None) -> SolverResult:
        options = options or SolverOptions()
        started = perf_counter()

        try:
            grid = parse_puzzle_string(puzzle)
        except BoardValidationError as exc:
            return self._result("invalid", started, errors=[str(exc)])

        given_errors = validate_givens(grid)
        if given_errors:
            return self._result("invalid", started, errors=given_errors)

        stats = SearchStats()
        blank_count = sum(value == 0 for row in grid for value in row)
        solved = self._search(self._copy_grid(grid), stats)
        solver_stats = SolverStats(
            placements=blank_count,
            guesses=stats.guesses,
            backtracks=stats.backtracks,
            constraints_checked=stats.constraints_checked,
        )

        if solved is None:
            return self._result("unsolved", started, stats=solver_stats)

        solved_grid, trace = solved
        solution_errors = validate_complete_solution(solved_grid)
        if solution_errors:
            return self._result("error", started, stats=solver_stats, errors=solution_errors)

        steps = self._build_steps(trace, options)
        return self._result(
            "solved",
            started,
            solution=grid_to_string(solved_grid),
            steps=steps,
            stats=solver_stats,
        )

    def _search(
        self,
        grid: Grid,
        stats: SearchStats,
    ) -> tuple[Grid, list[PlacementTrace]] | None:
        propagation_trace = self._propagate(grid, stats)
        if propagation_trace is None:
            return None

        if self._is_complete(grid):
            return self._copy_grid(grid), propagation_trace

        candidates = self._candidate_map(grid, stats)
        unresolved = [
            (cell, values)
            for cell, values in candidates.items()
            if grid[cell[0]][cell[1]] == 0
        ]
        if not unresolved or any(not values for _, values in unresolved):
            return None

        (row, col), values = min(unresolved, key=lambda item: len(item[1]))
        for value in sorted(values):
            stats.guesses += 1
            branch = self._copy_grid(grid)
            branch[row][col] = value
            guess_trace = PlacementTrace(
                row=row,
                col=col,
                value=value,
                reason="python search guess",
                details=(
                    f"Selected the cell with the fewest candidates "
                    f"({self._format_candidates(values)}) and tried {value}."
                ),
            )

            solved = self._search(branch, stats)
            if solved is not None:
                solved_grid, branch_trace = solved
                return solved_grid, propagation_trace + [guess_trace] + branch_trace

            stats.backtracks += 1

        return None

    def _propagate(self, grid: Grid, stats: SearchStats) -> list[PlacementTrace] | None:
        trace: list[PlacementTrace] = []

        while True:
            candidates = self._candidate_map(grid, stats)
            if any(not values for values in candidates.values()):
                return None

            naked_single = next(
                (
                    (row, col, next(iter(values)))
                    for (row, col), values in candidates.items()
                    if len(values) == 1
                ),
                None,
            )
            if naked_single is not None:
                row, col, value = naked_single
                grid[row][col] = value
                trace.append(
                    PlacementTrace(
                        row=row,
                        col=col,
                        value=value,
                        reason="naked single",
                        details=(
                            f"Only {value} remains possible after checking "
                            "row, column, and box peers."
                        ),
                    )
                )
                continue

            try:
                hidden_single = self._find_hidden_single(grid, candidates, stats)
            except Contradiction:
                return None

            if hidden_single is None:
                return trace

            grid[hidden_single.row][hidden_single.col] = hidden_single.value
            trace.append(
                PlacementTrace(
                    row=hidden_single.row,
                    col=hidden_single.col,
                    value=hidden_single.value,
                    reason="hidden single",
                    details=(
                        f"{hidden_single.value} can only go in this cell "
                        f"within {hidden_single.unit_label}."
                    ),
                )
            )

    def _find_hidden_single(
        self,
        grid: Grid,
        candidates: dict[Cell, set[int]],
        stats: SearchStats,
    ) -> HiddenSingle | None:
        for unit_label, cells in self._iter_units():
            present = {grid[row][col] for row, col in cells if grid[row][col] != 0}
            for value in sorted(DIGITS - present):
                stats.constraints_checked += 1
                possible_cells = [
                    (row, col)
                    for row, col in cells
                    if grid[row][col] == 0 and value in candidates[(row, col)]
                ]

                if not possible_cells:
                    raise Contradiction

                if len(possible_cells) == 1:
                    row, col = possible_cells[0]
                    return HiddenSingle(row=row, col=col, value=value, unit_label=unit_label)

        return None

    def _candidate_map(self, grid: Grid, stats: SearchStats) -> dict[Cell, set[int]]:
        return {
            (row, col): self._candidates_for(grid, row, col, stats)
            for row in range(GRID_SIZE)
            for col in range(GRID_SIZE)
            if grid[row][col] == 0
        }

    def _candidates_for(
        self,
        grid: Grid,
        row: int,
        col: int,
        stats: SearchStats,
    ) -> set[int]:
        stats.constraints_checked += 1
        used = {
            grid[peer_row][peer_col]
            for peer_row, peer_col in PEERS[(row, col)]
            if grid[peer_row][peer_col] != 0
        }
        return set(DIGITS - used)

    def _build_steps(
        self,
        trace: list[PlacementTrace],
        options: SolverOptions,
    ) -> list[SolverStep]:
        if not options.explain:
            return []

        limited_trace = trace[: options.max_steps]
        return [
            SolverStep(
                index=placement.index,
                row=placement.row,
                col=placement.col,
                value=str(placement.value),
                reason=placement.reason,
                details=placement.details,
            )
            for placement in limited_trace
        ]

    def _result(
        self,
        status: str,
        started: float,
        solution: str | None = None,
        steps: list[SolverStep] | None = None,
        stats: SolverStats | None = None,
        errors: list[str] | None = None,
    ) -> SolverResult:
        return SolverResult(
            solver=self.name,
            status=status,
            solution=solution,
            time_ms=round((perf_counter() - started) * 1000, 3),
            steps=steps or [],
            stats=stats or SolverStats(),
            errors=errors or [],
        )

    def _iter_units(self) -> list[tuple[str, list[Cell]]]:
        rows = [
            (f"row {row + 1}", [(row, col) for col in range(GRID_SIZE)])
            for row in range(GRID_SIZE)
        ]
        columns = [
            (f"column {col + 1}", [(row, col) for row in range(GRID_SIZE)])
            for col in range(GRID_SIZE)
        ]
        boxes: list[tuple[str, list[Cell]]] = []
        for box in range(GRID_SIZE):
            box_row = (box // BOX_SIZE) * BOX_SIZE
            box_col = (box % BOX_SIZE) * BOX_SIZE
            boxes.append(
                (
                    f"box {box + 1}",
                    [
                        (row, col)
                        for row in range(box_row, box_row + BOX_SIZE)
                        for col in range(box_col, box_col + BOX_SIZE)
                    ],
                )
            )

        return rows + columns + boxes

    def _is_complete(self, grid: Grid) -> bool:
        return all(value != 0 for row in grid for value in row)

    def _copy_grid(self, grid: Grid) -> Grid:
        return [row.copy() for row in grid]

    def _format_candidates(self, candidates: set[int]) -> str:
        return ", ".join(str(value) for value in sorted(candidates))


class Contradiction(RuntimeError):
    pass
