export type Difficulty = 'Easy' | 'Medium' | 'Hard' | 'Diabolical';

export type PuzzleResponse = {
  id: string;
  puzzle: string;
  difficulty: Difficulty;
  rating: number | null;
};

export type PuzzleValidationResponse = {
  valid: boolean;
  valid_givens: boolean;
  complete: boolean;
  valid_solution: boolean;
  normalized: string | null;
  errors: string[];
};

export type SolverResult = {
  solver: string;
  status: 'solved' | 'unsolved' | 'invalid' | 'error';
  solution: string | null;
  time_ms: number;
  steps: Array<{
    index: number;
    row: number;
    col: number;
    value: string;
    reason: string;
    details: string;
  }>;
  stats: {
    placements: number;
    guesses: number | null;
    backtracks: number | null;
    constraints_checked: number | null;
  };
  errors: string[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8080';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (options?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function fetchRandomPuzzle(difficulty: Difficulty): Promise<PuzzleResponse> {
  const params = new URLSearchParams({ difficulty });
  return request<PuzzleResponse>(`/puzzles/random?${params.toString()}`);
}

export function validatePuzzle(puzzle: string): Promise<PuzzleValidationResponse> {
  return request<PuzzleValidationResponse>('/puzzles/validate', {
    method: 'POST',
    body: JSON.stringify({ puzzle }),
  });
}

export function solvePuzzle(puzzle: string): Promise<SolverResult> {
  return request<SolverResult>('/solve', {
    method: 'POST',
    body: JSON.stringify({
      puzzle,
      options: {
        explain: true,
        max_steps: 10,
      },
    }),
  });
}
