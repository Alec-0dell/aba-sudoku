from shutil import which

import pytest

from backend.app.benchmarks.runner import run_prolog_sample
from backend.app.core.solver_contract import SolverOptions
from backend.app.solvers.prolog_solver import PrologSudokuSolver
from backend.tests.test_board import VALID_PUZZLE, VALID_SOLUTION


pytestmark = pytest.mark.skipif(which("swipl") is None, reason="SWI-Prolog is not installed")


def test_prolog_solver_solves_known_puzzle() -> None:
    result = PrologSudokuSolver().solve(VALID_PUZZLE)

    assert result.solver == "prolog"
    assert result.status == "solved"
    assert result.solution == VALID_SOLUTION
    assert result.stats.placements == VALID_PUZZLE.count("0")
    assert result.errors == []


def test_prolog_solver_can_return_limited_explanation_steps() -> None:
    result = PrologSudokuSolver().solve(
        VALID_PUZZLE,
        SolverOptions(explain=True, max_steps=3),
    )

    assert result.status == "solved"
    assert len(result.steps) == 3
    assert result.steps[0].reason == "prolog constraint solution"


def test_prolog_solver_rejects_conflicting_givens() -> None:
    result = PrologSudokuSolver().solve("550" + "0" * 78)

    assert result.status == "invalid"
    assert result.solution is None
    assert result.errors


def test_prolog_sample_simulation_runs_against_bank() -> None:
    results = run_prolog_sample(difficulty="Easy", limit=1)

    assert len(results) == 1
    assert results[0].solver_result.status == "solved"

