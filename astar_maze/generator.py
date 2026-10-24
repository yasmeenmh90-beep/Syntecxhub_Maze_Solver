"""Reproducible maze generation."""
from __future__ import annotations

import random
from typing import List, Optional

from .grid import OPEN, WALL, Maze


def generate_maze(rows: int, cols: int, seed: Optional[int] = None, braid: float = 0.0) -> Maze:
    """Generate a maze with the iterative recursive-backtracker algorithm.

    ``rows`` and ``cols`` are the number of *rooms*; the returned grid is
    ``(2*rows+1) x (2*cols+1)`` cells including walls. With ``braid=0`` the
    maze is "perfect" (exactly one route between any two cells). ``braid``
    in ``(0, 1]`` removes that fraction of dead-end walls, adding loops so
    several routes exist and algorithms behave differently.

    Start is the top-left room, goal the bottom-right room.
    """
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be at least 1.")
    if not 0.0 <= braid <= 1.0:
        raise ValueError("braid must be between 0 and 1.")
    rng = random.Random(seed)
    height, width = 2 * rows + 1, 2 * cols + 1
    grid: List[List[int]] = [[WALL] * width for _ in range(height)]

    def cell(r: int, c: int):
        return 2 * r + 1, 2 * c + 1

    visited = [[False] * cols for _ in range(rows)]
    stack = [(0, 0)]
    visited[0][0] = True
    gr, gc = cell(0, 0)
    grid[gr][gc] = OPEN
    while stack:
        r, c = stack[-1]
        options = [(r + dr, c + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                   if 0 <= r + dr < rows and 0 <= c + dc < cols and not visited[r + dr][c + dc]]
        if not options:
            stack.pop()
            continue
        nr, nc = rng.choice(options)
        visited[nr][nc] = True
        (ar, ac), (br, bc) = cell(r, c), cell(nr, nc)
        grid[(ar + br) // 2][(ac + bc) // 2] = OPEN  # knock down the wall between rooms
        grid[br][bc] = OPEN
        stack.append((nr, nc))

    if braid > 0:
        _braid(grid, rows, cols, braid, rng)

    return Maze.from_lists(grid, cell(0, 0), cell(rows - 1, cols - 1))


def _braid(grid: List[List[int]], rows: int, cols: int, fraction: float, rng: random.Random) -> None:
    """Open one wall of a random subset of dead ends to create loops."""
    dead_ends = []
    for r in range(rows):
        for c in range(cols):
            gr, gc = 2 * r + 1, 2 * c + 1
            if sum(grid[gr + dr][gc + dc] == OPEN for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))) == 1:
                dead_ends.append((gr, gc))
    rng.shuffle(dead_ends)
    for gr, gc in dead_ends[: round(len(dead_ends) * fraction)]:
        walls = [(gr + dr, gc + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                 if grid[gr + dr][gc + dc] == WALL
                 and 0 < gr + 2 * dr < len(grid) - 1 and 0 < gc + 2 * dc < len(grid[0]) - 1]
        if walls:
            wr, wc = rng.choice(walls)
            grid[wr][wc] = OPEN


def random_obstacles(rows: int, cols: int, density: float = 0.3, seed: Optional[int] = None) -> Maze:
    """Open field with randomly placed walls; start top-left, goal bottom-right.

    The goal may be unreachable, which is useful for testing.
    """
    if not 0.0 <= density < 1.0:
        raise ValueError("density must be in [0, 1).")
    rng = random.Random(seed)
    grid = [[WALL if rng.random() < density else OPEN for _ in range(cols)] for _ in range(rows)]
    grid[0][0] = grid[rows - 1][cols - 1] = OPEN
    return Maze.from_lists(grid, (0, 0), (rows - 1, cols - 1))
