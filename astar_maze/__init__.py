"""A* maze solver with algorithm comparison, maze generation and visualisation."""
from .generator import generate_maze, random_obstacles
from .grid import DEMO_MAZE, Maze, MazeError
from .heuristics import HEURISTICS
from .search import ALGORITHMS, SearchResult, astar, bfs, solve

__version__ = "2.0.0"

__all__ = [
    "ALGORITHMS", "DEMO_MAZE", "HEURISTICS", "Maze", "MazeError", "SearchResult",
    "astar", "bfs", "generate_maze", "random_obstacles", "solve", "__version__",
]
