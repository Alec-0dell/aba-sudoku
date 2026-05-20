from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import random

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
        self._records: dict[str, list[PuzzleRecord]] | None = None

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
        if self._records is None:
            self._records = {
                difficulty: self._load_file(difficulty, self.bank_dir / filename)
                for difficulty, filename in _DIFFICULTY_FILES.items()
            }
        return self._records

    def _load_file(self, difficulty: str, path: Path) -> list[PuzzleRecord]:
        if not path.exists():
            return []

        records: list[PuzzleRecord] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) < 2:
                raise ValueError(f"{path}:{line_number} must contain at least id and puzzle.")

            puzzle_id, puzzle = parts[0], parts[1]
            rating = float(parts[2]) if len(parts) >= 3 else None

            try:
                grid = parse_puzzle_string(puzzle)
            except BoardValidationError as exc:
                raise ValueError(f"{path}:{line_number} has invalid puzzle: {exc}") from exc

            given_errors = validate_givens(grid)
            if given_errors:
                raise ValueError(
                    f"{path}:{line_number} has conflicting givens: {' '.join(given_errors)}"
                )

            records.append(
                PuzzleRecord(
                    id=puzzle_id,
                    puzzle=puzzle,
                    difficulty=difficulty,
                    rating=rating,
                )
            )

        return records


@lru_cache(maxsize=1)
def get_puzzle_bank() -> PuzzleBank:
    return PuzzleBank()

