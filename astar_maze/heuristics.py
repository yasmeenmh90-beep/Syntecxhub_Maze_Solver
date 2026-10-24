"""Distance heuristics h(n) for grid search.

All functions take two ``(row, column)`` cells and return an estimate of the
remaining cost. Admissibility depends on the movement model:

* 4-direction moves (cost 1): every heuristic below is admissible.
* 8-direction moves (orthogonal 1, diagonal sqrt(2)): Manhattan can
  overestimate and is therefore *not* admissible; the others are.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, Tuple

Cell = Tuple[int, int]
Heuristic = Callable[[Cell, Cell], float]

SQRT2 = math.sqrt(2)


def manhattan(a: Cell, b: Cell) -> float:
    """|dr| + |dc|. Exact distance on an empty 4-connected grid."""
    return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))


def euclidean(a: Cell, b: Cell) -> float:
    """Straight-line distance. Admissible, but weaker than Manhattan/octile."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def octile(a: Cell, b: Cell) -> float:
    """Exact distance on an empty 8-connected grid with sqrt(2) diagonals."""
    dr, dc = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dr + dc) + (SQRT2 - 2) * min(dr, dc)


def chebyshev(a: Cell, b: Cell) -> float:
    """max(|dr|, |dc|). Admissible for both movement models."""
    return float(max(abs(a[0] - b[0]), abs(a[1] - b[1])))


def zero(a: Cell, b: Cell) -> float:
    """h = 0: turns A* into Dijkstra's algorithm."""
    return 0.0


HEURISTICS: Dict[str, Heuristic] = {
    "manhattan": manhattan,
    "euclidean": euclidean,
    "octile": octile,
    "chebyshev": chebyshev,
    "zero": zero,
}


def default_for(diagonal: bool) -> str:
    """The tightest admissible heuristic for the movement model."""
    return "octile" if diagonal else "manhattan"


def is_admissible(name: str, diagonal: bool) -> bool:
    return not (diagonal and name == "manhattan")
