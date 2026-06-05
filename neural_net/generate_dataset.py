import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
GAME_BANK_DIR = ROOT_DIR / "game-bank"
OUTPUT_DIR = SCRIPT_DIR / "processed_data"

sys.path.append(str(ROOT_DIR))

from tqdm import tqdm

from backend.app.solvers.python_solver import PythonSudokuSolver


def parse_game_bank_line(line: str) -> str | None:
    tokens = line.strip().split()
    if not tokens or len(tokens) < 2:
        return None

    puzzle_str = tokens[1]
    if len(puzzle_str) != 81:
        return None

    return puzzle_str


def process_files():
    if not GAME_BANK_DIR.exists():
        raise FileNotFoundError(f"Could not locate 'game-bank/' folder at: {GAME_BANK_DIR}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    solver = PythonSudokuSolver()

    target_files = ["easy.txt", "medium.txt", "hard.txt", "diabolical.txt"]
    max_puzzles = 10_000

    for filename in target_files:
        input_path = GAME_BANK_DIR / filename
        output_path = OUTPUT_DIR / f"solved_{filename}"

        if not input_path.exists():
            print(f"Skipping {filename}: file not found.")
            continue

        success_count = 0
        total_count = 0

        with open(input_path, "r") as infile, open(output_path, "w") as outfile, \
                tqdm(total=max_puzzles, desc=filename, unit="puzzle") as pbar:
            for line in infile:
                puzzle_str = parse_game_bank_line(line)
                if not puzzle_str:
                    continue

                total_count += 1
                result = solver.solve(puzzle_str)

                if result.status == "solved" and result.solution:
                    outfile.write(f"{puzzle_str},{result.solution}\n")
                    success_count += 1
                else:
                    print(f"Warning: Failed to solve line {total_count} in {filename}. Status: {result.status}")

                pbar.update(1)
                if total_count >= max_puzzles:
                    break

        print(f"Finished {filename}: Successfully solved {success_count}/{total_count} boards.\n")


if __name__ == "__main__":
    process_files()