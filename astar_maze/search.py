"""Search algorithms: A*, weighted A*, Dijkstra, greedy best-first and BFS.

A*, weighted A*, Dijkstra and greedy best-first share one priority-queue
engine and differ only in how a node's priority is computed:

=================  ==========================  =========================
algorithm          priority f(n)               shortest path guaranteed?
=================  ==========================  =========================
A*                 g(n) + h(n)                 yes (admissible h)
weighted A*        g(n) + w * h(n), w >= 1     within factor w of optimal
Dijkstra           g(n)                        yes
greedy best-first  h(n)                        no
=================  ==========================  =========================

BFS uses a FIFO queue and minimises the number of moves, which equals the
shortest path only when every move has the same cost.
"""
from __future__ import annotations

import heapq
import itertools
import time
import warnings
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .grid import Cell, Maze
from .heuristics import HEURISTICS, default_for, is_admissible

ALGORITHMS = ("astar", "weighted", "dijkstra", "greedy", "bfs")
ALGORITHM_LABELS = {
    "astar": "A*",
    "weighted": "Weighted A*",
    "dijkstra": "Dijkstra",
    "greedy": "Greedy best-first",
    "bfs": "Breadth-first",
}


@dataclass(frozen=True)
class SearchResult:
    """Everything a solver run produces, including search statistics."""

    algorithm: str
    heuristic: str
    diagonal: bool
    path: Optional[List[Cell]]
    cost: Optional[float]
    expanded: List[Cell] = field(repr=False)  # cells in the order they were expanded
    max_frontier: int
    elapsed_ms: float

    @property
    def found(self) -> bool:
        return self.path is not None

    @property
    def steps(self) -> Optional[int]:
        return None if self.path is None else len(self.path) - 1

    @property
    def nodes_expanded(self) -> int:
        return len(self.expanded)

    @property
    def label(self) -> str:
        return ALGORITHM_LABELS.get(self.algorithm, self.algorithm)

    def summary(self) -> dict:
        """JSON-serialisable summary."""
        return {
            "algorithm": self.algorithm,
            "heuristic": self.heuristic,
            "diagonal": self.diagonal,
            "found": self.found,
            "steps": self.steps,
            "cost": None if self.cost is None else round(self.cost, 4),
            "nodes_expanded": self.nodes_expanded,
            "max_frontier": self.max_frontier,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "path": None if self.path is None else [list(p) for p in self.path],
        }


def _reconstruct(parent: Dict[Cell, Cell], goal: Cell) -> List[Cell]:
    path = [goal]
    while path[-1] in parent:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def _best_first(
    maze: Maze,
    *,
    algorithm: str,
    heuristic: str,
    diagonal: bool,
    g_weight: float,
    h_weight: float,
) -> SearchResult:
    """Generic best-first search with priority ``g_weight*g + h_weight*h``.

    Uses lazy deletion: when a cheaper route to a cell is found, a new heap
    entry is pushed and stale entries are skipped when popped. Ties on f are
    broken toward the smaller h (the cell closer to the goal), then FIFO.
    """
    h_fn = HEURISTICS[heuristic]
    start, goal = maze.start, maze.goal
    t0 = time.perf_counter()

    counter = itertools.count()
    h0 = h_fn(start, goal)
    frontier = [(g_weight * 0 + h_weight * h0, h0, next(counter), 0.0, start)]
    best_g: Dict[Cell, float] = {start: 0.0}
    parent: Dict[Cell, Cell] = {}
    expanded: List[Cell] = []
    max_frontier = 1

    while frontier:
        _, _, _, g, current = heapq.heappop(frontier)
        if g > best_g[current]:
            continue  # stale entry: a cheaper route was found after this push
        expanded.append(current)
        if current == goal:
            return SearchResult(algorithm, heuristic, diagonal, _reconstruct(parent, goal), g,
                                expanded, max_frontier, (time.perf_counter() - t0) * 1000)
        for nxt, step in maze.neighbors(current, diagonal):
            new_g = g + step
            if new_g < best_g.get(nxt, float("inf")) - 1e-12:
                best_g[nxt] = new_g
                parent[nxt] = current
                h = h_fn(nxt, goal)
                heapq.heappush(frontier, (g_weight * new_g + h_weight * h, h, next(counter), new_g, nxt))
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult(algorithm, heuristic, diagonal, None, None, expanded, max_frontier,
                        (time.perf_counter() - t0) * 1000)


def bfs(maze: Maze, diagonal: bool = False) -> SearchResult:
    """Breadth-first search: fewest moves, ignores move costs and heuristics."""
    start, goal = maze.start, maze.goal
    t0 = time.perf_counter()
    queue = deque([start])
    parent: Dict[Cell, Cell] = {}
    seen = {start}
    expanded: List[Cell] = []
    max_frontier = 1
    while queue:
        current = queue.popleft()
        expanded.append(current)
        if current == goal:
            path = _reconstruct(parent, goal)
            cost = sum(1.0 if a[0] == b[0] or a[1] == b[1] else 2 ** 0.5 for a, b in zip(path, path[1:]))
            return SearchResult("bfs", "none", diagonal, path, cost, expanded, max_frontier,
                                (time.perf_counter() - t0) * 1000)
        for nxt, _ in maze.neighbors(current, diagonal):
            if nxt not in seen:
                seen.add(nxt)
                parent[nxt] = current
                queue.append(nxt)
        max_frontier = max(max_frontier, len(queue))
    return SearchResult("bfs", "none", diagonal, None, None, expanded, max_frontier,
                        (time.perf_counter() - t0) * 1000)


def solve(
    maze: Maze,
    algorithm: str = "astar",
    heuristic: Optional[str] = None,
    diagonal: bool = False,
    weight: float = 2.0,
) -> SearchResult:
    """Solve ``maze`` with the chosen algorithm.

    Args:
        algorithm: one of ``astar``, ``weighted``, ``dijkstra``, ``greedy``, ``bfs``.
        heuristic: ``manhattan``, ``euclidean``, ``octile``, ``chebyshev`` or
            ``zero``. Defaults to the tightest admissible choice for the
            movement model (Manhattan for 4-way, octile for 8-way).
        diagonal: allow 8-direction movement (diagonals cost sqrt(2), no corner cutting).
        weight: heuristic weight for ``weighted`` A* (must be >= 1).
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm {algorithm!r}; choose from {', '.join(ALGORITHMS)}.")
    if algorithm == "bfs":
        return bfs(maze, diagonal)

    heuristic = heuristic or default_for(diagonal)
    if heuristic not in HEURISTICS:
        raise ValueError(f"Unknown heuristic {heuristic!r}; choose from {', '.join(HEURISTICS)}.")
    if algorithm in ("astar", "weighted") and not is_admissible(heuristic, diagonal):
        warnings.warn(
            f"'{heuristic}' can overestimate with diagonal moves; the path may not be optimal.",
            RuntimeWarning,
            stacklevel=2,
        )

    if algorithm == "astar":
        return _best_first(maze, algorithm="astar", heuristic=heuristic, diagonal=diagonal,
                           g_weight=1.0, h_weight=1.0)
    if algorithm == "weighted":
        if weight < 1:
            raise ValueError("Weighted A* requires weight >= 1.")
        return _best_first(maze, algorithm="weighted", heuristic=heuristic, diagonal=diagonal,
                           g_weight=1.0, h_weight=float(weight))
    if algorithm == "dijkstra":
        return _best_first(maze, algorithm="dijkstra", heuristic="zero", diagonal=diagonal,
                           g_weight=1.0, h_weight=0.0)
    return _best_first(maze, algorithm="greedy", heuristic=heuristic, diagonal=diagonal,
                       g_weight=0.0, h_weight=1.0)


def astar(maze: Maze, heuristic: Optional[str] = None, diagonal: bool = False) -> SearchResult:
    """Convenience wrapper for ``solve(maze, 'astar', ...)``."""
    return solve(maze, "astar", heuristic=heuristic, diagonal=diagonal)
