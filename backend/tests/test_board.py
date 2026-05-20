import pytest

from backend.app.core.board import (
    BoardValidationError,
    PEERS,
    box_index,
    grid_to_string,
    parse_puzzle_string,
    peers,
    validate_complete_solution,
    validate_givens,
)


VALID_PUZZLE = (
    "530070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)

VALID_SOLUTION = (
    "534678912"
    "672195348"
    "198342567"
    "859761423"
    "426853791"
    "713924856"
    "961537284"
    "287419635"
    "345286179"
)


def test_parse_and_format_puzzle_string() -> None:
    grid = parse_puzzle_string(VALID_PUZZLE)

    assert grid[0] == [5, 3, 0, 0, 7, 0, 0, 0, 0]
    assert grid_to_string(grid) == VALID_PUZZLE


def test_parse_accepts_dots_as_blanks() -> None:
    dotted = VALID_PUZZLE.replace("0", ".")

    assert grid_to_string(parse_puzzle_string(dotted)) == VALID_PUZZLE


def test_parse_rejects_wrong_length() -> None:
    with pytest.raises(BoardValidationError):
        parse_puzzle_string("123")


def test_validate_givens_detects_duplicates() -> None:
    invalid = parse_puzzle_string("550" + "0" * 78)

    errors = validate_givens(invalid)

    assert any("Row 1" in error for error in errors)
    assert any("Box 1" in error for error in errors)


def test_validate_complete_solution() -> None:
    assert validate_complete_solution(parse_puzzle_string(VALID_SOLUTION)) == []


def test_peer_sets_have_expected_cells() -> None:
    center_peers = peers(4, 4)

    assert len(center_peers) == 20
    assert (4, 0) in center_peers
    assert (0, 4) in center_peers
    assert (3, 3) in center_peers
    assert (4, 4) not in center_peers
    assert PEERS[(4, 4)] == center_peers


def test_box_index() -> None:
    assert box_index(0, 0) == 0
    assert box_index(4, 4) == 4
    assert box_index(8, 8) == 8

