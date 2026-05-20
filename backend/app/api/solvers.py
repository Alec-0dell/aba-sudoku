from fastapi import APIRouter

from backend.app.core.solver_contract import SolverRequest, SolverResult
from backend.app.solvers.prolog_solver import PrologSudokuSolver


router = APIRouter(tags=["solvers"])

_prolog_solver = PrologSudokuSolver()


@router.get("/solvers")
def list_solvers() -> list[dict[str, str]]:
    return [{"id": "prolog", "name": "SWI-Prolog CLP(FD)", "status": "available"}]


@router.post("/solve", response_model=SolverResult)
def solve(request: SolverRequest) -> SolverResult:
    return _prolog_solver.solve(request.puzzle, request.options)

