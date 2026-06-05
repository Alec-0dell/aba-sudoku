import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import puzzles, solvers
from backend.app.api.solvers import warm_up_nn


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load NN weights in a thread so startup is non-blocking but model is warm by first request.
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, warm_up_nn)
    yield


app = FastAPI(
    title="ABA Sudoku Backend",
    description="Backend API for Sudoku puzzle validation, solving, and benchmarking.",
    version="0.1.0",
    lifespan=lifespan,
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
