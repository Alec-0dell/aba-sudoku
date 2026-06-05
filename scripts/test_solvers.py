import csv
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import importlib
from pathlib import Path
import statistics
from shutil import which

from backend.app.core.board import (
    BoardValidationError,
    parse_puzzle_string,
    validate_complete_solution,
)
from backend.app.core.puzzle_bank import DIFFICULTIES, PuzzleBank
from backend.app.core.solver_contract import SolverOptions, SolverResult
from backend.app.solvers.clingo_solver import ClingoSudokuSolver
from backend.app.solvers.nn_solver import NNSudokuSolver
from backend.app.solvers.prolog_solver import PrologSudokuSolver
from backend.app.solvers.python_solver import PythonSudokuSolver


BOARDS_PER_DIFFICULTY = 100
_LOGS_DIR = Path(__file__).parent / "logs"


@dataclass(frozen=True)
class SolverSpec:
    name: str
    solve: Callable[[str], SolverResult]
    # Optional per-puzzle cell accuracy fn (returns fraction 0-1). Only used for NN.
    cell_accuracy: Callable[[str], float] | None = None


@dataclass(frozen=True)
class BenchmarkRow:
    solver: str
    difficulty: str
    attempted: int
    correct: int
    average_time_ms: float
    std_dev_ms: float
    avg_cell_accuracy_pct: float | None = None
    std_cell_accuracy_pct: float | None = None

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
            solve=lambda puzzle: python_solver.solve(puzzle, SolverOptions(explain=False)),
        ),
    ]

    if which(prolog_solver.executable) is not None:
        solvers.append(
            SolverSpec(
                name="prolog",
                solve=lambda puzzle: prolog_solver.solve(puzzle, SolverOptions(explain=False)),
            )
        )

    clingo_solver = ClingoSudokuSolver()
    if which(clingo_solver.executable) is not None or importlib.util.find_spec("clingo") is not None:
        solvers.append(
            SolverSpec(
                name="clingo",
                solve=lambda puzzle: clingo_solver.solve(puzzle, SolverOptions(explain=False)),
            )
        )

    nn_solver = NNSudokuSolver()
    if nn_solver.model_path.exists():
        def _nn_cell_accuracy(puzzle: str) -> float:
            """Fraction of blank cells the NN predicted correctly vs Python ground truth."""
            python_result = python_solver.solve(puzzle, SolverOptions(explain=False))
            if python_result.status != "solved" or not python_result.solution:
                return 0.0
            nn_preds, _ = nn_solver.infer_raw(puzzle)
            total_blank = puzzle.count('0')
            if total_blank == 0:
                return 1.0
            correct = sum(
                1 for orig, pred, truth in zip(puzzle, nn_preds, python_result.solution)
                if orig == '0' and str(pred) == truth
            )
            return correct / total_blank

        solvers.append(
            SolverSpec(
                name="nn",
                solve=lambda puzzle: nn_solver.solve(puzzle, SolverOptions(explain=False)),
                cell_accuracy=_nn_cell_accuracy,
            )
        )
    else:
        print("NN model weights not found — skipping nn benchmarks.")

    rows = run_benchmarks(bank, solvers, BOARDS_PER_DIFFICULTY)
    print()
    print_table(rows)
    csv_path = save_csv(rows)
    print(f"\nResults saved to {csv_path}")


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
            times = [result.time_ms for result in results]
            average_time = sum(times) / len(times) if times else 0.0
            std_dev = statistics.stdev(times) if len(times) > 1 else 0.0

            avg_cell_acc: float | None = None
            std_cell_acc: float | None = None
            if solver.cell_accuracy is not None:
                cell_accs = [solver.cell_accuracy(record.puzzle) for record in records]
                avg_cell_acc = (sum(cell_accs) / len(cell_accs)) * 100 if cell_accs else 0.0
                std_cell_acc = statistics.stdev(cell_accs) * 100 if len(cell_accs) > 1 else 0.0

            row = BenchmarkRow(
                solver=solver.name,
                difficulty=difficulty,
                attempted=len(records),
                correct=correct,
                average_time_ms=average_time,
                std_dev_ms=std_dev,
                avg_cell_accuracy_pct=avg_cell_acc,
                std_cell_accuracy_pct=std_cell_acc,
            )
            rows.append(row)

            cell_str = (
                f" | cell {avg_cell_acc:.1f}% ± {std_cell_acc:.1f}%"
                if avg_cell_acc is not None else ""
            )
            print(
                f"  [{solver.name} / {difficulty}] "
                f"{correct}/{len(records)} correct ({row.correct_percent:.1f}%) — "
                f"avg {average_time:.3f}ms ± {std_dev:.3f}ms"
                f"{cell_str}"
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
    has_cell_acc = any(row.avg_cell_accuracy_pct is not None for row in rows)
    headers = ["Solver", "Difficulty", "Boards", "Avg Time (ms)", "Std Dev (ms)", "Correct", "Correct %"]
    if has_cell_acc:
        headers += ["Cell Acc (%)", "Cell Acc Std"]

    def fmt_row(row: BenchmarkRow) -> list[str]:
        cols = [
            row.solver,
            row.difficulty,
            str(row.attempted),
            f"{row.average_time_ms:.3f}",
            f"{row.std_dev_ms:.3f}",
            f"{row.correct}/{row.attempted}",
            f"{row.correct_percent:.1f}%",
        ]
        if has_cell_acc:
            cols.append(f"{row.avg_cell_accuracy_pct:.1f}%" if row.avg_cell_accuracy_pct is not None else "N/A")
            cols.append(f"±{row.std_cell_accuracy_pct:.1f}%" if row.std_cell_accuracy_pct is not None else "N/A")
        return cols

    table_rows = [fmt_row(row) for row in rows]
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in table_rows))
        for i in range(len(headers))
    ]

    separator = "-+-".join("-" * w for w in widths)
    print(" | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print(separator)
    for r in table_rows:
        print(" | ".join(v.ljust(widths[i]) for i, v in enumerate(r)))


def save_csv(rows: list[BenchmarkRow]) -> Path:
    _LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _LOGS_DIR / f"results_{timestamp}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "solver", "difficulty", "attempted", "correct", "correct_pct",
            "avg_time_ms", "std_dev_ms", "avg_cell_accuracy_pct", "std_cell_accuracy_pct",
        ])
        for row in rows:
            writer.writerow([
                row.solver,
                row.difficulty,
                row.attempted,
                row.correct,
                f"{row.correct_percent:.1f}",
                f"{row.average_time_ms:.3f}",
                f"{row.std_dev_ms:.3f}",
                f"{row.avg_cell_accuracy_pct:.1f}" if row.avg_cell_accuracy_pct is not None else "",
                f"{row.std_cell_accuracy_pct:.1f}" if row.std_cell_accuracy_pct is not None else "",
            ])
    return path


if __name__ == "__main__":
    main()
