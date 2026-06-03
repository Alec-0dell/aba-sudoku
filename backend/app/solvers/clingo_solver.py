from __future__ import annotations

import json
import subprocess
from time import perf_counter
import shutil
import importlib

from backend.app.core.board import (
    BoardValidationError,
    Grid,
    grid_to_string,
    parse_puzzle_string,
    validate_complete_solution,
    validate_givens,
)
from backend.app.core.solver_contract import SolverOptions, SolverResult, SolverStats, SolverStep

# Inline ASP program: given/3 facts are injected at solve-time.
# Choice rule assigns exactly one digit per blank cell; integrity constraints
# enforce row, column, and box uniqueness.
_ASP_TEMPLATE = """\
row(1..9). col(1..9). digit(1..9).
{givens}
1 {{ cell(R,C,D) : digit(D) }} 1 :- row(R), col(C), not given(R,C,_).
cell(R,C,D) :- given(R,C,D).
:- row(R), digit(D), #count{{ C : cell(R,C,D) }} != 1.
:- col(C), digit(D), #count{{ R : cell(R,C,D) }} != 1.
:- digit(D), BR=1..3, BC=1..3,
   R1=((BR-1)*3+1), C1=((BC-1)*3+1),
   #count{{ R,C : cell(R,C,D), R=R1..R1+2, C=C1..C1+2 }} != 1.
"""


class ClingoSudokuSolver:
    name = "clingo"

    def __init__(self, executable: str = "clingo", timeout_seconds: float = 15) -> None:
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
            solved_grid = self._run_clingo(grid)
        except FileNotFoundError:
            return self._result("error", started, errors=[f"{self.executable!r} was not found."])
        except subprocess.TimeoutExpired:
            return self._result(
                "error", started,
                errors=[f"Clingo timed out after {self.timeout_seconds:g} seconds."],
            )
        except ClingoSolverError as exc:
            return self._result("error", started, errors=[str(exc)])

        if solved_grid is None:
            return self._result("unsolved", started)

        solution_errors = validate_complete_solution(solved_grid)
        if solution_errors:
            return self._result("error", started, errors=solution_errors)

        solution = grid_to_string(solved_grid)
        steps = self._build_steps(grid, solution, options)
        return self._result(
            "solved", started, solution=solution, steps=steps,
            stats=SolverStats(placements=sum(v == 0 for row in grid for v in row)),
        )

    def _run_clingo(self, grid: Grid) -> Grid | None:
        facts = "\n".join(
            f"given({r},{c},{v})."
            for r, row in enumerate(grid, 1)
            for c, v in enumerate(row, 1)
            if v != 0
        )
        # Prefer the CLI if available; otherwise try the Python clingo module
        if shutil.which(self.executable):
            completed = subprocess.run(
                [self.executable, "-n", "1", "--outf=2"],
                input=_ASP_TEMPLATE.format(givens=facts),
                capture_output=True, text=True,
                timeout=self.timeout_seconds, check=False,
            )

            if completed.returncode == 20:
                return None  # UNSATISFIABLE

            if completed.returncode not in (10, 30):
                stderr = completed.stderr.strip()
                raise ClingoSolverError(stderr or f"Clingo exited with code {completed.returncode}.")

            try:
                atoms: list[str] = json.loads(completed.stdout)["Call"][0]["Witnesses"][0]["Value"]
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                raise ClingoSolverError("Clingo returned an unreadable solution.") from exc
        else:
            # Try Python API
            spec = importlib.util.find_spec("clingo")
            if spec is None:
                raise FileNotFoundError(self.executable)

            try:
                clingo = importlib.import_module("clingo")
            except Exception as exc:  # pragma: no cover - defensive
                raise ClingoSolverError("Failed to import clingo Python module.") from exc

            ctl = clingo.Control()
            ctl.add("base", [], _ASP_TEMPLATE.format(givens=facts))
            ctl.ground([("base", [])])
            atoms = []
            with ctl.solve(yield_=True) as handle:
                it = iter(handle)
                try:
                    model = next(it)
                except StopIteration:
                    return None

                atoms = [str(s) for s in model.symbols(shown=True)]

        solved: Grid = [[0] * 9 for _ in range(9)]
        for atom in atoms:
            if atom.startswith("cell("):
                r, c, d = atom[5:-1].split(",")
                solved[int(r) - 1][int(c) - 1] = int(d)
        return solved

    def _build_steps(self, grid: Grid, solution: str, options: SolverOptions) -> list[SolverStep]:
        if not options.explain:
            return []

        steps: list[SolverStep] = []
        for index, original in enumerate(v for row in grid for v in row):
            if original != 0:
                continue
            steps.append(SolverStep(
                index=index,
                row=index // 9,
                col=index % 9,
                value=solution[index],
                reason="clingo constraint solution",
                details="Clingo ASP satisfied row, column, box, and digit-domain constraints.",
            ))
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


class ClingoSolverError(RuntimeError):
    pass