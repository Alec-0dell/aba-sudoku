from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.core.board import (
    BoardValidationError,
    grid_to_string,
    parse_puzzle_string,
    validate_complete_solution,
    validate_givens,
)
from backend.app.core.puzzle_bank import DIFFICULTIES, PuzzleBank, PuzzleRecord, get_puzzle_bank


router = APIRouter(prefix="/puzzles", tags=["puzzles"])


class PuzzleResponse(BaseModel):
    id: str
    puzzle: str
    difficulty: str
    rating: float | None = None

    @classmethod
    def from_record(cls, record: PuzzleRecord) -> "PuzzleResponse":
        return cls(
            id=record.id,
            puzzle=record.puzzle,
            difficulty=record.difficulty,
            rating=record.rating,
        )


class PuzzleValidationRequest(BaseModel):
    puzzle: str = Field(..., min_length=1)


class PuzzleValidationResponse(BaseModel):
    valid: bool
    valid_givens: bool
    complete: bool
    valid_solution: bool
    normalized: str | None
    errors: list[str]


def _difficulty_query(
    difficulty: Annotated[str, Query(description="Puzzle difficulty")] = "Easy",
) -> str:
    normalized = difficulty.strip().title()
    if normalized not in DIFFICULTIES:
        allowed = ", ".join(DIFFICULTIES)
        raise HTTPException(status_code=422, detail=f"difficulty must be one of: {allowed}")
    return normalized


@router.get("/random", response_model=PuzzleResponse)
def random_puzzle(
    difficulty: Annotated[str, Depends(_difficulty_query)],
    bank: Annotated[PuzzleBank, Depends(get_puzzle_bank)],
) -> PuzzleResponse:
    try:
        return PuzzleResponse.from_record(bank.random(difficulty))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/validate", response_model=PuzzleValidationResponse)
def validate_puzzle(request: PuzzleValidationRequest) -> PuzzleValidationResponse:
    errors: list[str] = []

    try:
        grid = parse_puzzle_string(request.puzzle)
    except BoardValidationError as exc:
        return PuzzleValidationResponse(
            valid=False,
            valid_givens=False,
            complete=False,
            valid_solution=False,
            normalized=None,
            errors=[str(exc)],
        )

    normalized = grid_to_string(grid)
    given_errors = validate_givens(grid)
    errors.extend(given_errors)

    complete = "0" not in normalized
    solution_errors = validate_complete_solution(grid) if complete else ["Puzzle is not complete."]
    if complete:
        errors.extend(solution_errors)

    valid_givens = not given_errors
    valid_solution = complete and not solution_errors

    return PuzzleValidationResponse(
        valid=valid_givens and (not complete or valid_solution),
        valid_givens=valid_givens,
        complete=complete,
        valid_solution=valid_solution,
        normalized=normalized,
        errors=errors,
    )

