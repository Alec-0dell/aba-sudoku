from __future__ import annotations

from ast import literal_eval
from pathlib import Path
import subprocess
from time import perf_counter

from backend.app.core.board import (
    BoardValidationError,
    Grid,
    grid_to_string,
    parse_puzzle_string,
    validate_complete_solution,
    validate_givens,
)
from backend.app.core.solver_contract import SolverOptions, SolverResult, SolverStats, SolverStep


class PrologSudokuSolver:
    name = "prolog"

    def __init__(
        self,
        prolog_file: Path | None = None,
        executable: str = "swipl",
        timeout_seconds: float = 15,
    ) -> None:
        self.prolog_file = prolog_file or Path(__file__).resolve().parents[3] / "backend" / "solvers" / "soduko.pl"
        self.executable = executable
        self.timeout_seconds = timeout_seconds

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

        try:
            solved_grid = self._run_prolog(grid)
        except FileNotFoundError:
            return self._result("error", started, errors=[f"{self.executable!r} was not found."])
        except subprocess.TimeoutExpired:
            return self._result(
                "error",
                started,
                errors=[f"Prolog solver timed out after {self.timeout_seconds:g} seconds."],
            )
        except PrologSolverError as exc:
            return self._result("error", started, errors=[str(exc)])

        if solved_grid is None:
            return self._result("unsolved", started)

        solution_errors = validate_complete_solution(solved_grid)
        if solution_errors:
            return self._result("error", started, errors=solution_errors)

        solution = grid_to_string(solved_grid)
        steps = self._build_steps(grid, solution, options)

        return self._result(
            "solved",
            started,
            solution=solution,
            steps=steps,
            stats=SolverStats(placements=len([value for row in grid for value in row if value == 0])),
        )

    def _run_prolog(self, grid: Grid) -> Grid | None:
        goal = f"(Rows = {self._grid_to_prolog_term(grid)}, sudoku(Rows) -> write(Rows), halt(0); halt(2))"
        completed = subprocess.run(
            [self.executable, "-q", "-s", str(self.prolog_file), "-g", goal],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )

        if completed.returncode == 2:
            return None

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise PrologSolverError(stderr or f"Prolog exited with code {completed.returncode}.")

        try:
            parsed = literal_eval(completed.stdout.strip())
        except (SyntaxError, ValueError) as exc:
            raise PrologSolverError("Prolog returned an unreadable solution.") from exc

        if not isinstance(parsed, list):
            raise PrologSolverError("Prolog returned an unexpected solution shape.")

        return parsed

    def _grid_to_prolog_term(self, grid: Grid) -> str:
        rows: list[str] = []
        for row in grid:
            cells = ["_" if value == 0 else str(value) for value in row]
            rows.append(f"[{','.join(cells)}]")
        return f"[{','.join(rows)}]"

    def _build_steps(self, grid: Grid, solution: str, options: SolverOptions) -> list[SolverStep]:
        if not options.explain:
            return []

        steps: list[SolverStep] = []
        for index, original in enumerate(value for row in grid for value in row):
            if original != 0:
                continue

            steps.append(
                SolverStep(
                    index=index,
                    row=index // 9,
                    col=index % 9,
                    value=solution[index],
                    reason="prolog constraint solution",
                    details="SWI-Prolog CLP(FD) satisfied row, column, box, and digit-domain constraints.",
                )
            )

            if options.max_steps is not None and len(steps) >= options.max_steps:
                break

        return steps

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


class PrologSolverError(RuntimeError):
    pass

