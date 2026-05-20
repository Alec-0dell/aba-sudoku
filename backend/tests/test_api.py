from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.test_board import VALID_PUZZLE, VALID_SOLUTION


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_random_puzzle_endpoint() -> None:
    response = client.get("/puzzles/random", params={"difficulty": "Easy"})

    assert response.status_code == 200
    data = response.json()
    assert data["difficulty"] == "Easy"
    assert len(data["puzzle"]) == 81
    assert data["id"]
    assert isinstance(data["rating"], float)


def test_validate_endpoint_for_partial_puzzle() -> None:
    response = client.post("/puzzles/validate", json={"puzzle": VALID_PUZZLE})

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["valid_givens"] is True
    assert data["complete"] is False
    assert data["valid_solution"] is False
    assert data["normalized"] == VALID_PUZZLE


def test_validate_endpoint_for_complete_solution() -> None:
    response = client.post("/puzzles/validate", json={"puzzle": VALID_SOLUTION})

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["complete"] is True
    assert data["valid_solution"] is True


def test_validate_endpoint_for_invalid_puzzle() -> None:
    response = client.post("/puzzles/validate", json={"puzzle": "550" + "0" * 78})

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["valid_givens"] is False
    assert data["errors"]

