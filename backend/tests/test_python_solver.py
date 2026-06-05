from backend.app.benchmarks.runner import run_python_sample
from backend.app.core.solver_contract import SolverOptions
from backend.app.solvers.python_solver import PythonSudokuSolver
from backend.tests.test_board import VALID_PUZZLE, VALID_SOLUTION


def test_python_solver_solves_known_puzzle() -> None:
    result = PythonSudokuSolver().solve(VALID_PUZZLE)

    assert result.solver == "python"
    assert result.status == "solved"
    assert result.solution == VALID_SOLUTION
    assert result.stats.placements == VALID_PUZZLE.count("0")
    assert result.stats.guesses == 0
    assert result.errors == []


def test_python_solver_can_return_limited_explanation_steps() -> None:
    result = PythonSudokuSolver().solve(
        VALID_PUZZLE,
        SolverOptions(explain=True, max_steps=3),
    )

    assert result.status == "solved"
    assert len(result.steps) == 3
    assert result.steps[0].reason in {"hidden single", "naked single", "python search guess"}


def test_python_solver_rejects_conflicting_givens() -> None:
    result = PythonSudokuSolver().solve("550" + "0" * 78)

    assert result.status == "invalid"
    assert result.solution is None
    assert result.errors


def test_python_sample_simulation_runs_against_bank() -> None:
    results = run_python_sample(difficulty="Easy", limit=1)

    assert len(results) == 1
    assert results[0].solver_result.status == "solved"
