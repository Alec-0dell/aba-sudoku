from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import random
import threading

from backend.app.core.board import BoardValidationError, parse_puzzle_string, validate_givens


DIFFICULTIES = ("Easy", "Medium", "Hard", "Diabolical")
_DIFFICULTY_FILES = {difficulty: f"{difficulty.lower()}.txt" for difficulty in DIFFICULTIES}
_DEFAULT_BANK_DIR = Path(__file__).resolve().parents[3] / "game-bank"


@dataclass(frozen=True)
class PuzzleRecord:
    id: str
    puzzle: str
    difficulty: str
    rating: float | None = None


class PuzzleBank:
    def __init__(self, bank_dir: Path = _DEFAULT_BANK_DIR) -> None:
        self.bank_dir = bank_dir
        # Hold currently-available records per difficulty. Start with a small
        # sample to make the first request fast, then fill the full banks in the background.
        self._records: dict[str, list[PuzzleRecord]] | None = {}
        self._preload_count = 5
        self._start_preload()

    def by_difficulty(self, difficulty: str) -> list[PuzzleRecord]:
        records = self._load()
        if difficulty not in records:
            raise KeyError(f"No puzzle bank found for difficulty {difficulty!r}.")
        return records[difficulty]

    def random(self, difficulty: str) -> PuzzleRecord:
        puzzles = self.by_difficulty(difficulty)
        if not puzzles:
            raise KeyError(f"No puzzles loaded for difficulty {difficulty!r}.")
        return random.choice(puzzles)

    def _load(self) -> dict[str, list[PuzzleRecord]]:
        # Return whatever is currently available (samples or fully-loaded banks).
        return self._records

    def _start_preload(self) -> None:
        # Load a small sample per difficulty, then background-load
        # the full files and replace the samples when ready.
        for difficulty, filename in _DIFFICULTY_FILES.items():
            path = self.bank_dir / filename
            try:
                sample = self._load_file(difficulty, path, max_records=self._preload_count, strict=False)
            except Exception:
                sample = []
            self._records[difficulty] = sample

        thread = threading.Thread(target=self._background_load_all, daemon=True)
        thread.start()

    def _load_file(self, difficulty: str, path: Path, *, max_records: int | None = None, strict: bool = True) -> list[PuzzleRecord]:
        if not path.exists():
            return []
        records: list[PuzzleRecord] = []
        with path.open(encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                parts = stripped.split()
                if len(parts) < 2:
                    if strict:
                        raise ValueError(f"{path}:{line_number} must contain at least id and puzzle.")
                    continue

                puzzle_id, puzzle = parts[0], parts[1]
                rating = float(parts[2]) if len(parts) >= 3 else None

                try:
                    grid = parse_puzzle_string(puzzle)
                except BoardValidationError as exc:
                    if strict:
                        raise ValueError(f"{path}:{line_number} has invalid puzzle: {exc}") from exc
                    continue

                given_errors = validate_givens(grid)
                if given_errors:
                    if strict:
                        raise ValueError(
                            f"{path}:{line_number} has conflicting givens: {' '.join(given_errors)}"
                        )
                    continue

                records.append(PuzzleRecord(id=puzzle_id, puzzle=puzzle, difficulty=difficulty, rating=rating))
                if max_records is not None and len(records) >= max_records:
                    break

        return records

    def _background_load_all(self) -> None:
        for difficulty, filename in _DIFFICULTY_FILES.items():
            path = self.bank_dir / filename
            try:
                full = self._load_file(difficulty, path)
            except Exception:
                full = []
            self._records[difficulty] = full


@lru_cache(maxsize=1)
def get_puzzle_bank() -> PuzzleBank:
    return PuzzleBank()

