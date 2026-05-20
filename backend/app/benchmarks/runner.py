from dataclasses import dataclass

from backend.app.core.puzzle_bank import PuzzleBank
from backend.app.core.solver_contract import SolverOptions, SolverResult
from backend.app.solvers.prolog_solver import PrologSudokuSolver


@dataclass(frozen=True)
class SimulationResult:
    puzzle_id: str
    difficulty: str
    solver_result: SolverResult


def run_prolog_sample(
    difficulty: str = "Easy",
    limit: int = 10,
    bank: PuzzleBank | None = None,
    solver: PrologSudokuSolver | None = None,
) -> list[SimulationResult]:
    puzzle_bank = bank or PuzzleBank()
    prolog_solver = solver or PrologSudokuSolver()

    results: list[SimulationResult] = []
    for record in puzzle_bank.by_difficulty(difficulty)[:limit]:
        result = prolog_solver.solve(record.puzzle, SolverOptions(explain=False))
        results.append(
            SimulationResult(
                puzzle_id=record.id,
                difficulty=record.difficulty,
                solver_result=result,
            )
        )

    return results

