from fastapi import APIRouter
import shutil
import importlib

from backend.app.core.solver_contract import SolverOptions, SolverRequest, SolverResult, SolverStats
from backend.app.solvers.clingo_solver import ClingoSudokuSolver
from backend.app.solvers.nn_solver import NNSudokuSolver
from backend.app.solvers.prolog_solver import PrologSudokuSolver
from backend.app.solvers.python_solver import PythonSudokuSolver


router = APIRouter(tags=["solvers"])

# Instantiate solver wrappers (they won't call executables until used)
_python_solver = PythonSudokuSolver()
_prolog_solver = PrologSudokuSolver()
_clingo_solver = ClingoSudokuSolver()
_nn_solver = NNSudokuSolver()


def _exe_available(name: str) -> bool:
    return shutil.which(name) is not None


@router.get("/solvers")
def list_solvers() -> list[dict[str, str]]:
    # Mark status based on whether underlying CLI is present
    prolog_status = "available" if _exe_available(_prolog_solver.executable) else "unavailable"
    # clingo can be available either as a CLI executable or as a Python module
    clingo_status = (
        "available"
        if _exe_available(_clingo_solver.executable) or importlib.util.find_spec("clingo") is not None
        else "unavailable"
    )

    nn_status = "available" if _nn_solver.model_path.exists() else "unavailable"

    return [
        {"id": "python", "name": "Python", "status": "available"},
        {"id": "prolog", "name": "Prolog", "status": prolog_status},
        {"id": "clingo", "name": "Clingo", "status": clingo_status},
        {"id": "nn", "name": "Neural Network", "status": nn_status},
    ]


@router.post("/solve", response_model=SolverResult)
def solve(request: SolverRequest) -> SolverResult:
    if request.solver in (None, "python"):
        return _python_solver.solve(request.puzzle, request.options)

    if request.solver == "prolog":
        return _prolog_solver.solve(request.puzzle, request.options)

    if request.solver == "clingo":
        return _clingo_solver.solve(request.puzzle, request.options)

    if request.solver == "nn":
        # Run Python first to get ground truth, then validate NN predictions against it.
        python_result = _python_solver.solve(request.puzzle, SolverOptions())
        if python_result.status != "solved" or not python_result.solution:
            return SolverResult(
                solver="nn", status="invalid", solution=None, time_ms=0,
                errors=["Python solver could not establish ground truth for validation."],
            )

        try:
            nn_preds, nn_time = _nn_solver.infer_raw(request.puzzle)
        except Exception as exc:
            return SolverResult(
                solver="nn", status="error", solution=None, time_ms=0, errors=[str(exc)],
            )

        python_sol = python_result.solution
        partial: list[str] = []
        correct = 0
        for orig, pred, truth in zip(request.puzzle, nn_preds, python_sol):
            if orig != '0':
                partial.append(orig)
            elif str(pred) == truth:
                partial.append(truth)
                correct += 1
            else:
                partial.append('0')

        partial_str = ''.join(partial)
        remaining = partial_str.count('0')
        return SolverResult(
            solver="nn",
            status="solved" if remaining == 0 else "unsolved",
            solution=partial_str,
            time_ms=nn_time,
            stats=SolverStats(placements=correct),
            errors=[],
        )

    return SolverResult(
        solver=request.solver,
        status="error",
        solution=None,
        time_ms=0,
        errors=[f"Unknown solver {request.solver!r}."],
    )
