from fastapi import APIRouter
import shutil
import importlib

from backend.app.core.solver_contract import SolverRequest, SolverResult
from backend.app.solvers.prolog_solver import PrologSudokuSolver
from backend.app.solvers.clingo_solver import ClingoSudokuSolver


router = APIRouter(tags=["solvers"])

# Instantiate solver wrappers (they won't call executables until used)
_prolog_solver = PrologSudokuSolver()
_clingo_solver = ClingoSudokuSolver()


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

    return [
        {"id": "prolog", "name": "Prolog", "status": prolog_status},
        {"id": "clingo", "name": "Clingo", "status": clingo_status},
    ]


@router.post("/solve", response_model=SolverResult)
def solve(request: SolverRequest) -> SolverResult:
    # Dispatch to the requested solver if provided
    if request.solver == "clingo":
        return _clingo_solver.solve(request.puzzle, request.options)

    # Default to Prolog solver
    return _prolog_solver.solve(request.puzzle, request.options)

