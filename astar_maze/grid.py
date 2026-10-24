"""Maze model: validation, neighbour generation and file I/O (JSON and text)."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Sequence, Tuple, Union

Cell = Tuple[int, int]

OPEN, WALL = 0, 1
SQRT2 = math.sqrt(2)

_ORTHOGONAL = ((-1, 0), (1, 0), (0, -1), (0, 1))
_DIAGONAL = ((-1, -1), (-1, 1), (1, -1), (1, 1))

# Text format symbols
TEXT_WALL, TEXT_OPEN, TEXT_START, TEXT_GOAL = "#", ".", "S", "G"


class MazeError(ValueError):
    """Raised when a maze definition is malformed."""


@dataclass(frozen=True)
class Maze:
    """An immutable rectangular grid maze.

    ``grid[r][c]`` is ``0`` for an open cell and ``1`` for a wall.
    Coordinates are ``(row, column)`` with ``(0, 0)`` at the top-left.
    """

    grid: Tuple[Tuple[int, ...], ...]
    start: Cell
    goal: Cell

    def __post_init__(self) -> None:
        grid = self.grid
        if not grid or not grid[0]:
            raise MazeError("Grid must be non-empty.")
        width = len(grid[0])
        if any(len(row) != width for row in grid):
            raise MazeError("Grid must be rectangular (all rows the same length).")
        if any(cell not in (OPEN, WALL) for row in grid for cell in row):
            raise MazeError("Grid cells must be 0 (open) or 1 (wall).")
        for name, point in (("start", self.start), ("goal", self.goal)):
            if len(point) != 2 or any(type(v) is not int for v in point):
                raise MazeError(f"{name} must be two integers [row, column].")
            if not self.in_bounds(point):
                raise MazeError(f"{name} {list(point)} is outside the {self.rows}x{self.cols} grid.")
            if not self.is_open(point):
                raise MazeError(f"{name} {list(point)} is a wall.")

    # ------------------------------------------------------------------ build
    @classmethod
    def from_lists(cls, grid: Sequence[Sequence[int]], start: Sequence[int], goal: Sequence[int]) -> "Maze":
        try:
            frozen = tuple(tuple(row) for row in grid)
        except TypeError as exc:
            raise MazeError("Grid must be a list of lists.") from exc
        return cls(frozen, tuple(start), tuple(goal))  # type: ignore[arg-type]

    @classmethod
    def from_text(cls, text: str) -> "Maze":
        """Parse ``#`` walls, ``.`` open cells, ``S`` start and ``G`` goal."""
        lines = [line.rstrip("\r\n") for line in text.strip("\n").splitlines()]
        lines = [line for line in lines if line.strip()]
        start = goal = None
        grid: List[List[int]] = []
        for r, line in enumerate(lines):
            row = []
            for c, ch in enumerate(line):
                if ch == TEXT_WALL:
                    row.append(WALL)
                elif ch in (TEXT_OPEN, " "):
                    row.append(OPEN)
                elif ch == TEXT_START:
                    if start is not None:
                        raise MazeError("Text maze has more than one 'S'.")
                    start = (r, c)
                    row.append(OPEN)
                elif ch == TEXT_GOAL:
                    if goal is not None:
                        raise MazeError("Text maze has more than one 'G'.")
                    goal = (r, c)
                    row.append(OPEN)
                else:
                    raise MazeError(f"Unexpected character {ch!r} at row {r}, column {c}.")
            grid.append(row)
        if start is None or goal is None:
            raise MazeError("Text maze needs exactly one 'S' and one 'G'.")
        return cls.from_lists(grid, start, goal)

    @classmethod
    def from_dict(cls, data: dict) -> "Maze":
        missing = {"grid", "start", "goal"} - set(data)
        if missing:
            raise MazeError(f"Maze JSON is missing: {', '.join(sorted(missing))}.")
        return cls.from_lists(data["grid"], data["start"], data["goal"])

    @classmethod
    def load(cls, path: Union[str, Path]) -> "Maze":
        """Load a ``.json`` or ``.txt`` maze file."""
        path = Path(path)
        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            try:
                return cls.from_dict(json.loads(content))
            except json.JSONDecodeError as exc:
                raise MazeError(f"Invalid JSON in {path}: {exc}") from exc
        return cls.from_text(content)

    # ----------------------------------------------------------------- export
    def to_dict(self) -> dict:
        return {"grid": [list(row) for row in self.grid], "start": list(self.start), "goal": list(self.goal)}

    def to_text(self) -> str:
        lines = []
        for r, row in enumerate(self.grid):
            chars = []
            for c, value in enumerate(row):
                if (r, c) == self.start:
                    chars.append(TEXT_START)
                elif (r, c) == self.goal:
                    chars.append(TEXT_GOAL)
                else:
                    chars.append(TEXT_WALL if value else TEXT_OPEN)
            lines.append("".join(chars))
        return "\n".join(lines) + "\n"

    def save(self, path: Union[str, Path]) -> None:
        path = Path(path)
        if path.suffix.lower() == ".json":
            path.write_text(json.dumps(self.to_dict()) + "\n", encoding="utf-8")
        else:
            path.write_text(self.to_text(), encoding="utf-8")

    # ---------------------------------------------------------------- queries
    @property
    def rows(self) -> int:
        return len(self.grid)

    @property
    def cols(self) -> int:
        return len(self.grid[0])

    @property
    def open_cells(self) -> int:
        return sum(1 for row in self.grid for v in row if v == OPEN)

    def in_bounds(self, cell: Cell) -> bool:
        r, c = cell
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_open(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and self.grid[cell[0]][cell[1]] == OPEN

    def neighbors(self, cell: Cell, diagonal: bool = False) -> Iterator[Tuple[Cell, float]]:
        """Yield ``(neighbour, move_cost)`` pairs.

        Orthogonal moves cost 1. Diagonal moves (if enabled) cost sqrt(2) and
        may not cut corners: both adjacent orthogonal cells must be open.
        """
        r, c = cell
        for dr, dc in _ORTHOGONAL:
            nxt = (r + dr, c + dc)
            if self.is_open(nxt):
                yield nxt, 1.0
        if diagonal:
            for dr, dc in _DIAGONAL:
                nxt = (r + dr, c + dc)
                if self.is_open(nxt) and self.is_open((r + dr, c)) and self.is_open((r, c + dc)):
                    yield nxt, SQRT2


DEMO_MAZE = Maze.from_lists(
    [
        [0, 0, 1, 0, 0],
        [1, 0, 1, 0, 1],
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 1, 0],
    ],
    (0, 0),
    (4, 4),
)
