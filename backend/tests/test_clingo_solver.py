from shutil import which
from unittest.mock import patch
import json
import subprocess

import pytest

from backend.app.core.solver_contract import SolverOptions
from backend.app.solvers.clingo_solver import ClingoSudokuSolver
from backend.tests.test_board import VALID_PUZZLE, VALID_SOLUTION


def _clingo_json(solution: str) -> str:
    atoms = [f"cell({i // 9 + 1},{i % 9 + 1},{ch})" for i, ch in enumerate(solution)]
    return json.dumps({"Call": [{"Witnesses": [{"Value": atoms}]}]})


def _run(returncode: int, stdout: str = "", stderr: str = ""):
    cp = subprocess.CompletedProcess([], returncode)
    cp.stdout, cp.stderr = stdout, stderr
    return cp


@patch("backend.app.solvers.clingo_solver.subprocess.run")
def test_clingo_solver_solves_known_puzzle(mock_run) -> None:
    mock_run.return_value = _run(10, stdout=_clingo_json(VALID_SOLUTION))
    result = ClingoSudokuSolver().solve(VALID_PUZZLE)

    assert result.solver == "clingo"
    assert result.status == "solved"
    assert result.solution == VALID_SOLUTION
    assert result.stats.placements == VALID_PUZZLE.count("0")
    assert result.errors == []


@patch("backend.app.solvers.clingo_solver.subprocess.run")
def test_clingo_solver_can_return_limited_explanation_steps(mock_run) -> None:
    mock_run.return_value = _run(10, stdout=_clingo_json(VALID_SOLUTION))
    result = ClingoSudokuSolver().solve(VALID_PUZZLE, SolverOptions(explain=True, max_steps=3))

    assert result.status == "solved"
    assert len(result.steps) == 3
    assert result.steps[0].reason == "clingo constraint solution"


@patch("backend.app.solvers.clingo_solver.subprocess.run")
def test_clingo_solver_rejects_conflicting_givens(mock_run) -> None:
    result = ClingoSudokuSolver().solve("550" + "0" * 78)

    mock_run.assert_not_called()
    assert result.status == "invalid"
    assert result.solution is None
    assert result.errors


@patch("backend.app.solvers.clingo_solver.subprocess.run")
def test_clingo_solver_returns_unsolved_on_unsat(mock_run) -> None:
    mock_run.return_value = _run(20)
    result = ClingoSudokuSolver().solve(VALID_PUZZLE)

    assert result.status == "unsolved"
    assert result.solution is None


@pytest.mark.skipif(which("clingo") is None, reason="Clingo is not installed")
def test_clingo_solver_integration() -> None:
    result = ClingoSudokuSolver().solve(VALID_PUZZLE)

    assert result.status == "solved"
    assert result.solution == VALID_SOLUTION