from __future__ import annotations

from pathlib import Path
from time import perf_counter

import torch
import torch.nn as nn

from backend.app.core.board import (
    BoardValidationError,
    Grid,
    grid_to_string,
    parse_puzzle_string,
    validate_complete_solution,
    validate_givens,
)
from backend.app.core.solver_contract import SolverOptions, SolverResult, SolverStats, SolverStep

# Same architecture constants from train_nn.py exactly.
_EMBED_DIM, _NUM_HEADS, _NUM_LAYERS, _DIM_FF, _STEPS = 256, 8, 2, 512, 4


def _generate_sudoku_mask() -> torch.Tensor:
    mask = torch.full((81, 81), float("-inf"))
    for i in range(81):
        r1, c1 = i // 9, i % 9
        b1 = (r1 // 3) * 3 + (c1 // 3)
        for j in range(81):
            r2, c2 = j // 9, j % 9
            b2 = (r2 // 3) * 3 + (c2 // 3)
            if r1 == r2 or c1 == c2 or b1 == b2:
                mask[i, j] = 0.0
    return mask


class _RecurrentSudokuTransformer(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.embedding = nn.Embedding(10, _EMBED_DIM)
        self.row_embed = nn.Embedding(9, _EMBED_DIM)
        self.col_embed = nn.Embedding(9, _EMBED_DIM)
        self.box_embed = nn.Embedding(9, _EMBED_DIM)

        self.register_buffer("row_idx", torch.arange(81) // 9)
        self.register_buffer("col_idx", torch.arange(81) % 9)
        self.register_buffer(
            "box_idx",
            (torch.arange(81) // 27) * 3 + ((torch.arange(81) % 9) // 3),
        )
        self.register_buffer("attn_mask", _generate_sudoku_mask())

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=_EMBED_DIM, nhead=_NUM_HEADS, dim_feedforward=_DIM_FF,
            activation="relu", batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=_NUM_LAYERS)
        self.classifier = nn.Linear(_EMBED_DIM, 9)
        self.prediction_projection = nn.Linear(9, _EMBED_DIM)

    def forward(self, x: torch.Tensor, steps: int = _STEPS) -> list[torch.Tensor]:
        pos = self.row_embed(self.row_idx) + self.col_embed(self.col_idx) + self.box_embed(self.box_idx)
        h = self.embedding(x) + pos.unsqueeze(0)
        all_logits: list[torch.Tensor] = []
        for _ in range(steps):
            h = self.transformer(h, mask=self.attn_mask)
            logits = self.classifier(h)
            all_logits.append(logits)
            h = h + self.prediction_projection(torch.softmax(logits, dim=-1))
        return all_logits


class NNSudokuSolver:
    name = "nn"

    def __init__(
        self,
        model_path: Path | None = None,
        device: str | None = None,
    ) -> None:
        self.model_path = model_path or (Path(__file__).resolve().parent / "sudoku_benchmark.pt")
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self._model: _RecurrentSudokuTransformer | None = None

    # Lazy-load so startup cost is paid only on first solve.
    def _get_model(self) -> _RecurrentSudokuTransformer:
        if self._model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(self.model_path)
            model = _RecurrentSudokuTransformer().to(self.device)
            model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            model.eval()
            self._model = model
        return self._model

    def infer_raw(self, puzzle: str) -> tuple[list[int], float]:
        """Return (flat list of 81 predicted digits 1-9, time_ms) without validation."""
        started = perf_counter()
        grid = parse_puzzle_string(puzzle)
        model = self._get_model()
        solved_grid = self._run_inference(model, grid)
        flat = [v for row in solved_grid for v in row]
        return flat, round((perf_counter() - started) * 1000, 3)

    def solve(self, puzzle: str, options: SolverOptions | None = None) -> SolverResult:
        options = options or SolverOptions()
        started = perf_counter()

        try:
            grid = parse_puzzle_string(puzzle)
        except BoardValidationError as exc:
            return self._result("invalid", started, errors=[str(exc)])

        given_errors = validate_givens(grid)
        if given_errors:
            return self._result("invalid", started, errors=given_errors)

        try:
            model = self._get_model()
        except FileNotFoundError:
            return self._result("error", started, errors=[f"Model weights not found: {self.model_path}"])

        solved_grid = self._run_inference(model, grid)

        solution_errors = validate_complete_solution(solved_grid)
        if solution_errors:
            return self._result("unsolved", started, stats=SolverStats(placements=0))

        solution = grid_to_string(solved_grid)
        blank_count = sum(v == 0 for row in grid for v in row)
        steps = self._build_steps(grid, solution, options)
        return self._result(
            "solved", started, solution=solution, steps=steps,
            stats=SolverStats(placements=blank_count),
        )

    def _run_inference(self, model: _RecurrentSudokuTransformer, grid: Grid) -> Grid:
        flat = [v for row in grid for v in row]
        x = torch.tensor(flat, dtype=torch.long, device=self.device).unsqueeze(0)  # (1, 81)

        with torch.no_grad():
            all_logits = model(x)

        preds = torch.argmax(all_logits[-1], dim=-1).squeeze(0).tolist()  # (81,)

        # Clamp: given cells stay constant regardless of what the model predicted.
        solved: Grid = [[0] * 9 for _ in range(9)]
        for idx, (given, pred) in enumerate(zip(flat, preds)):
            solved[idx // 9][idx % 9] = given if given != 0 else pred + 1

        return solved

    def _build_steps(self, grid: Grid, solution: str, options: SolverOptions) -> list[SolverStep]:
        if not options.explain:
            return []

        steps: list[SolverStep] = []
        for index, original in enumerate(v for row in grid for v in row):
            if original != 0:
                continue
            steps.append(SolverStep(
                index=index,
                row=index // 9,
                col=index % 9,
                value=solution[index],
                reason="nn inference",
                details=(
                    f"RecurrentSudokuTransformer ({_STEPS} recurrent steps) predicted "
                    "this digit from row, column, and box attention constraints."
                ),
            ))
            if options.max_steps is not None and len(steps) >= options.max_steps:
                break

        return steps

    def _result(
        self,
        status: str,
        started: float,
        solution: str | None = None,
        steps: list[SolverStep] | None = None,
        stats: SolverStats | None = None,
        errors: list[str] | None = None,
    ) -> SolverResult:
        return SolverResult(
            solver=self.name,
            status=status,
            solution=solution,
            time_ms=round((perf_counter() - started) * 1000, 3),
            steps=steps or [],
            stats=stats or SolverStats(),
            errors=errors or [],
        )