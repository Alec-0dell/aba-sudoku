from __future__ import annotations

import platform
import shutil
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

# written by claude, ran into very confusing issues while running on my machine at home (worked fine on eduroam)
def _resolve_swipl() -> list[str]:
    """
    Resolve the swipl executable for the current platform/environment.

    Resolution order:
      1. Native swipl on PATH (works on macOS, Linux, and Windows without restrictions)
      2. WSL swipl — for Windows machines where the native binary is blocked by
         Application Control (Smart App Control / WDAC). Tries both the snap path
         and the plain 'swipl' name inside WSL.
      3. Falls back to ['swipl'] and lets the OS surface a clear FileNotFoundError.
    """
    # Non-Windows: native swipl is always the right answer
    if platform.system() != "Windows":
        return ["swipl"]

    # Windows: try native first (works fine on machines without AppLocker/SAC)
    if shutil.which("swipl") is not None:
        try:
            result = subprocess.run(
                ["swipl", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return ["swipl"]
        except (OSError, subprocess.TimeoutExpired):
            pass

    # Windows fallback: route through WSL
    if shutil.which("wsl") is not None:
        # Try snap-installed path first (installed via `sudo snap install swi-prolog`)
        snap_path = "/snap/swi-prolog/current/usr/bin/swipl"
        for candidate in [snap_path, "swipl"]:
            try:
                result = subprocess.run(
                    ["wsl", candidate, "--version"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return ["wsl", candidate]
            except (OSError, subprocess.TimeoutExpired):
                continue

    # Last resort, let it fail at solve time
    return ["swipl"]


def _windows_path_to_wsl(path: Path) -> str:
    """Convert a Windows path (C:\\foo\\bar) to a WSL mount path (/mnt/c/foo/bar)."""
    parts = path.parts
    drive = parts[0].rstrip(":\\").lower()
    rest = "/".join(p.replace("\\", "/") for p in parts[1:])
    return f"/mnt/{drive}/{rest}"


class PrologSudokuSolver:
    name = "prolog"

    def __init__(
        self,
        prolog_file: Path | None = None,
        executable: list[str] | str | None = None,
        timeout_seconds: float = 15,
    ) -> None:
        self.prolog_file = prolog_file or Path(__file__).resolve().parents[3] / "backend" / "solvers" / "soduko.pl"
        # Allow callers to pin a specific executable; otherwise auto-resolve.
        if executable is None:
            self._cmd = _resolve_swipl()
        elif isinstance(executable, str):
            self._cmd = [executable]
        else:
            self._cmd = list(executable)
        self.timeout_seconds = timeout_seconds

    @property
    def executable(self) -> str:
        """Return the primary executable name (for error messages)."""
        return self._cmd[0]

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

        # When routing through WSL, the prolog file path must be in WSL format.
        using_wsl = len(self._cmd) >= 2 and self._cmd[0] == "wsl"
        pl_path = (
            _windows_path_to_wsl(self.prolog_file)
            if using_wsl
            else str(self.prolog_file)
        )

        cmd = self._cmd + ["-q", "-s", pl_path, "-g", goal]

        completed = subprocess.run(
            cmd,
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

