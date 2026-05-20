from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import puzzles, solvers


app = FastAPI(
    title="ABA Sudoku Backend",
    description="Backend API for Sudoku puzzle validation, solving, and benchmarking.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(puzzles.router)
app.include_router(solvers.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
