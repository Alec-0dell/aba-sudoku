from collections.abc import Callable
from dataclasses import dataclass
import importlib
from shutil import which

from backend.app.core.board import (
    BoardValidationError,
    parse_puzzle_string,
    validate_complete_solution,
)
from backend.app.core.puzzle_bank import DIFFICULTIES, PuzzleBank
from backend.app.core.solver_contract import SolverOptions, SolverResult
from backend.app.solvers.clingo_solver import ClingoSudokuSolver
from backend.app.solvers.prolog_solver import PrologSudokuSolver
from backend.app.solvers.python_solver import PythonSudokuSolver


# Try to include Clingo solver when available
try:
    from backend.app.solvers.clingo_solver import ClingoSudokuSolver  # type: ignore
    _clingo_available = True
except Exception:
    ClingoSudokuSolver = None  # type: ignore
    _clingo_available = False


BOARDS_PER_DIFFICULTY = 10


@dataclass(frozen=True)
class SolverSpec:
    name: str
    solve: Callable[[str], SolverResult]


@dataclass(frozen=True)
class BenchmarkRow:
    solver: str
    difficulty: str
    attempted: int
    correct: int
    average_time_ms: float

    @property
    def correct_percent(self) -> float:
        if self.attempted == 0:
            return 0.0
        return (self.correct / self.attempted) * 100


def main() -> None:
    bank = PuzzleBank()
    python_solver = PythonSudokuSolver()
    # Ensure the full banks are loaded before running benchmarks so the
    # sample/preload (5 records) doesn't affect the attempted counts.
    bank._background_load_all()
    prolog_solver = PrologSudokuSolver()
    solvers = [
        SolverSpec(
            name="python",
            solve=lambda puzzle: python_solver.solve(
                puzzle,
                SolverOptions(explain=False),
            ),
        ),
    ]

    if which(prolog_solver.executable) is not None:
        solvers.append(
            SolverSpec(
                name="prolog",
                solve=lambda puzzle: prolog_solver.solve(
                    puzzle,
                    SolverOptions(explain=False),
                ),
            )
        )

    clingo_solver = ClingoSudokuSolver()
    if which(clingo_solver.executable) is not None or importlib.util.find_spec("clingo") is not None:
        solvers.append(
            SolverSpec(
                name="clingo",
                solve=lambda puzzle: clingo_solver.solve(
                    puzzle,
                    SolverOptions(explain=False),
                ),
            )
        )

    if _clingo_available and ClingoSudokuSolver is not None:
        clingo_solver = ClingoSudokuSolver()
        solvers.append(
            SolverSpec(
                name="clingo",
                solve=lambda puzzle: clingo_solver.solve(
                    puzzle,
                    SolverOptions(explain=False),
                ),
            )
        )
    else:
        print("Clingo solver not available — skipping clingo benchmarks.")

    rows = run_benchmarks(bank, solvers, BOARDS_PER_DIFFICULTY)
    print_table(rows)


def run_benchmarks(
    bank: PuzzleBank,
    solvers: list[SolverSpec],
    limit: int,
) -> list[BenchmarkRow]:
    rows: list[BenchmarkRow] = []

    for solver in solvers:
        for difficulty in DIFFICULTIES:
            records = bank.by_difficulty(difficulty)[:limit]
            results = [solver.solve(record.puzzle) for record in records]
            correct = sum(
                1
                for record, result in zip(records, results, strict=True)
                if is_correct_solution(record.puzzle, result)
            )
            average_time = (
                sum(result.time_ms for result in results) / len(results)
                if results
                else 0.0
            )

            rows.append(
                BenchmarkRow(
                    solver=solver.name,
                    difficulty=difficulty,
                    attempted=len(records),
                    correct=correct,
                    average_time_ms=average_time,
                )
            )

    return rows


def is_correct_solution(puzzle: str, result: SolverResult) -> bool:
    if result.status != "solved" or result.solution is None:
        return False

    try:
        puzzle_grid = parse_puzzle_string(puzzle)
        solution_grid = parse_puzzle_string(result.solution)
    except BoardValidationError:
        return False

    if validate_complete_solution(solution_grid):
        return False

    puzzle_values = [value for row in puzzle_grid for value in row]
    solution_values = [value for row in solution_grid for value in row]
    return all(
        given == 0 or given == solved
        for given, solved in zip(puzzle_values, solution_values, strict=True)
    )


def print_table(rows: list[BenchmarkRow]) -> None:
    headers = ["Solver", "Difficulty", "Boards", "Avg Time (ms)", "Correct", "Correct %"]
    table_rows = [
        [
            row.solver,
            row.difficulty,
            str(row.attempted),
            f"{row.average_time_ms:.3f}",
            f"{row.correct}/{row.attempted}",
            f"{row.correct_percent:.1f}%",
        ]
        for row in rows
    ]

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in table_rows))
        for index in range(len(headers))
    ]

    separator = "-+-".join("-" * width for width in widths)
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print(separator)
    for row in table_rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


if __name__ == "__main__":
    main()
