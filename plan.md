# ABA Sudoku Solver Comparison Plan

## Project Goal

Build a Sudoku application that can play puzzles manually, solve puzzles with multiple solver approaches, explain solver decisions, and benchmark the solvers against each other by difficulty.

The main priority is a knowledge-based solver comparison:

1. Prolog-based solving with SWI-Prolog and CLP(FD)
2. Answer Set Programming with Clingo
3. Python baseline solver for validation and comparison
4. Optional ML / neural-network experiment
5. Optional additional rule-based or exact-cover solvers if useful

## Current State

- `game-bank/` contains large example puzzle banks by difficulty.
- `web-interface/` contains a React/Vite UI for manual Sudoku play.
- `backend/solvers/` and `backend/tests/` exist but are not yet implemented.
- `scripts/` exists but is currently empty.
- The UI already has manual play concepts: board state, difficulty selection, timer, number entry, undo, erase, and win overlay.

## Target Architecture

Use a Python FastAPI backend as the orchestration layer between the web UI, puzzle data, solver implementations, and benchmark scripts.

Suggested structure:

```text
backend/
  main.py
  api/
    puzzles.py
    solvers.py
    benchmarks.py
  core/
    board.py
    validation.py
    puzzle_bank.py
    solver_contract.py
  solvers/
    python_baseline.py
    prolog_solver.py
    clingo_solver.py
    ml_solver.py
  benchmarks/
    runner.py
    metrics.py

scripts/
  setup_backend.py
  prepare_data.py
  test_solvers.py
  benchmark_solvers.py
  train_ml.py

web-interface/
  src/
    api/
      client.ts
    components/
      SolverSelector.tsx
      SolverStats.tsx
      ReasoningPanel.tsx
      BenchmarkPage.tsx
```

## Shared Solver Contract

All solvers should use the same input and output shape so they can be tested, benchmarked, and displayed in the UI consistently.

Input:

```json
{
  "puzzle": "81-character puzzle string using 0 for blanks",
  "difficulty": "Easy | Medium | Hard | Diabolical",
  "options": {
    "explain": true,
    "max_steps": null
  }
}
```

Output:

```json
{
  "solver": "prolog",
  "status": "solved | unsolved | invalid | error",
  "solution": "81-character solved puzzle string or null",
  "time_ms": 12.4,
  "steps": [
    {
      "index": 40,
      "row": 4,
      "col": 4,
      "value": "5",
      "reason": "single candidate",
      "details": "Only value allowed by row, column, and box constraints."
    }
  ],
  "stats": {
    "placements": 51,
    "guesses": 0,
    "backtracks": 0,
    "constraints_checked": null
  },
  "errors": []
}
```

The `steps` explanation format can start simple and become more detailed over time. The first goal is useful, consistent explanations rather than perfect human-style Sudoku teaching.

## Phase 1: Backend Foundation

1. Create a Python backend package.
2. Add project dependency management, likely `pyproject.toml`.
3. Add FastAPI app with health check endpoint.
4. Add board representation utilities:
   - Parse string to 9x9 grid.
   - Convert grid to string.
   - Validate givens.
   - Validate complete solution.
   - Compute row, column, and box peers.
5. Add puzzle bank parser for `game-bank/*.txt`.
6. Add endpoint to fetch a random puzzle by difficulty.

FastAPI endpoints:

```text
GET  /health
GET  /puzzles/random?difficulty=Easy
POST /puzzles/validate
```

## Phase 2: Python Baseline Solver

Add a deterministic Python solver before integrating external systems.

Purpose:

- Validate puzzle banks.
- Generate known-good solutions for testing.
- Provide a fallback solver.
- Provide a fair baseline for speed and accuracy comparisons.

Implementation approach:

- Constraint propagation with candidate sets.
- Naked singles / hidden singles where straightforward.
- Backtracking when deterministic rules stall.
- Capture stats: time, placements, guesses, backtracks.

Endpoints:

```text
GET  /solvers
POST /solve
POST /solve/step
```

## Phase 3: Prolog Solver

This is the first priority knowledge-based solver.

Implementation approach:

- Use SWI-Prolog and CLP(FD).
- Keep Sudoku constraints in a `.pl` file.
- Invoke Prolog from Python using a subprocess first for portability.
- Later consider a Python-Prolog bridge only if subprocess overhead becomes a problem.

Files:

```text
backend/app/solvers/prolog_solver.py
backend/app/solvers/prolog/sudoku.pl
```

Initial Prolog responsibilities:

- Accept puzzle givens.
- Apply row, column, box, and domain constraints.
- Return solved board.
- Return timing and status.

Explanation strategy:

- Start with a generated explanation trace from Python by comparing candidate reductions or replaying solved placements.
- Later add Prolog-side trace metadata if needed.

## Phase 4: Clingo / ASP Solver

This is the second priority knowledge-based solver.

Implementation approach:

- Add Sudoku encoding in ASP.
- Use the Python `clingo` package if practical.
- Fall back to invoking the `clingo` CLI if that is simpler to install locally.

Files:

```text
backend/app/solvers/clingo_solver.py
backend/app/solvers/clingo/sudoku.lp
```

Initial Clingo responsibilities:

- Encode fixed givens.
- Enforce exactly one value per cell.
- Enforce row, column, and box uniqueness.
- Return stable model as solved board.
- Return satisfiability status, timing, and assignment stats.

## Phase 5: Web Interface Integration

Extend the current manual-play UI.

Add controls:

- Solver mode dropdown:
  - Manual
  - Python Baseline
  - Prolog
  - Clingo
  - ML Experimental
- Solve puzzle button.
- Solve step button.
- Reset / new puzzle behavior that keeps difficulty selection clear.

Add display panels:

- Solver status.
- Solve time.
- Number of placements.
- Guesses and backtracks where applicable.
- Reasoning / explanation feed.
- Error messages for unavailable solvers or invalid puzzles.

Recommended UI behavior:

- Manual mode keeps current number-entry behavior.
- Solver modes can disable manual number entry or allow edits before solving.
- Step mode applies one solver placement at a time and highlights the affected cell.
- Full solve mode fills the board and shows the explanation list.

## Phase 6: Benchmark / Simulation Page

Add a separate web page or view for solver comparison.

User inputs:

- Difficulty.
- Number of puzzles.
- Solver selection.
- Optional random seed.

Benchmark behavior:

1. Fetch selected number of puzzles from the puzzle bank.
2. Run each selected solver on each puzzle.
3. Track progress puzzle by puzzle.
4. Display aggregate results after completion.

Metrics:

- Solved count.
- Failed count.
- Invalid result count.
- Accuracy percentage.
- Average solve time.
- Median solve time.
- Min and max solve time.
- Average placements.
- Average guesses.
- Average backtracks.
- Timeout count.

FastAPI endpoints:

```text
POST /benchmarks/run
GET  /benchmarks/{benchmark_id}
```

For the first version, benchmarks can run synchronously for small puzzle counts. If larger runs become slow, add background jobs and polling.

## Phase 7: Local Scripts

Scripts should support development, testing, benchmarking, and ML experiments without needing the web UI.

Suggested scripts:

```text
scripts/setup_backend.py
```

Install/check Python dependencies and verify optional external solver tools.

```text
scripts/prepare_data.py
```

Parse puzzle banks, validate records, create train/test/eval splits, and optionally generate solutions with the baseline solver.

```text
scripts/test_solvers.py
```

Run shared correctness tests against every available solver.

```text
scripts/benchmark_solvers.py
```

Run local benchmark batches by difficulty and solver.

```text
scripts/train_ml.py
```

Train the experimental ML model once data preparation is available.

## Phase 8: Optional ML Solver

Treat the ML solver as experimental because Sudoku requires exact constraint satisfaction.

Possible approaches:

- Train a neural network to predict missing cell values.
- Measure cell-level accuracy and full-board validity.
- Optionally add a verifier/repair step using the baseline solver.

Metrics:

- Cell accuracy.
- Full puzzle accuracy.
- Valid Sudoku percentage.
- Average correction count from verifier/repair.
- Solve time compared to symbolic approaches.

ML should not block the Prolog or Clingo work.

## Recommended Milestones

### Milestone 1: Backend and Puzzle API

- FastAPI app runs locally.
- Puzzle bank parser works.
- Random puzzle endpoint returns a valid puzzle.
- Board validation tests pass.

### Milestone 2: Baseline Solver

- Python baseline solver solves sample puzzles.
- Solver contract is stable.
- Tests can validate solutions.

### Milestone 3: Prolog Solver

- SWI-Prolog solver solves puzzles through the FastAPI backend.
- Prolog results match baseline results.
- Basic reasoning/stats appear in API response.

### Milestone 4: Web Solver Demo

- UI can select Manual or Prolog mode.
- UI can solve a puzzle.
- UI can show solver stats and reasoning steps.

### Milestone 5: Clingo Solver

- Clingo solver works through the same solver contract.
- Clingo is included in tests and local benchmarks.

### Milestone 6: Benchmark Page

- User can choose difficulty and puzzle count.
- Solvers run over the selected batch.
- Results table compares speed and accuracy.

### Milestone 7: ML Experiment

- Data preparation exists.
- Simple model can train and run.
- ML results appear in benchmark comparison as experimental.

## Risks and Decisions

- External solver installation may vary by machine. Keep optional solvers detectable and report clear unavailable-solver errors.
- Puzzle bank files may not include solutions. Use the baseline solver to generate reference solutions when needed.
- Human-style reasoning is different from solver internals. Start with practical explanations, then improve detail.
- Long benchmarks should eventually move to background jobs.
- ML may perform poorly without a verifier. Treat it as research-oriented rather than a primary reliable solver.

## First Implementation Step

Start with Milestone 1:

1. Add Python project metadata and FastAPI dependency setup.
2. Implement board utilities.
3. Implement puzzle-bank parsing.
4. Add `/health` and `/puzzles/random`.

After that, implement the Python baseline solver so every later solver has a correctness oracle and shared benchmark target.
