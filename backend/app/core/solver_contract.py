from pydantic import BaseModel, Field


class SolverOptions(BaseModel):
    explain: bool = False
    max_steps: int | None = Field(default=None, ge=1)


class SolverRequest(BaseModel):
    puzzle: str
    difficulty: str | None = None
    options: SolverOptions = Field(default_factory=SolverOptions)


class SolverStep(BaseModel):
    index: int
    row: int
    col: int
    value: str
    reason: str
    details: str


class SolverStats(BaseModel):
    placements: int = 0
    guesses: int | None = None
    backtracks: int | None = None
    constraints_checked: int | None = None


class SolverResult(BaseModel):
    solver: str
    status: str
    solution: str | None
    time_ms: float
    steps: list[SolverStep] = Field(default_factory=list)
    stats: SolverStats = Field(default_factory=SolverStats)
    errors: list[str] = Field(default_factory=list)

