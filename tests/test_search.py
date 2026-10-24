import math
import random
import unittest
import warnings

from astar_maze import Maze, generate_maze, random_obstacles, solve
from astar_maze.heuristics import HEURISTICS, is_admissible
from astar_maze.search import ALGORITHMS


def assert_valid_path(test, maze, result):
    """Path starts/ends correctly, uses legal moves, avoids walls and corner cutting."""
    path = result.path
    test.assertEqual(path[0], maze.start)
    test.assertEqual(path[-1], maze.goal)
    cost = 0.0
    for a, b in zip(path, path[1:]):
        legal = {n: c for n, c in maze.neighbors(a, result.diagonal)}
        test.assertIn(b, legal, f"illegal move {a} -> {b}")
        cost += legal[b]
    test.assertAlmostEqual(cost, result.cost, places=9)


class OptimalityTests(unittest.TestCase):
    def test_astar_matches_bfs_on_4way_grids(self):
        rng = random.Random(42)
        for _ in range(300):
            maze = random_obstacles(rng.randint(2, 14), rng.randint(2, 14), density=0.3, seed=rng.random())
            a, b = solve(maze, "astar"), solve(maze, "bfs")
            self.assertEqual(a.found, b.found)
            if a.found:
                self.assertEqual(a.steps, b.steps)
                assert_valid_path(self, maze, a)

    def test_astar_matches_dijkstra_on_8way_grids(self):
        rng = random.Random(7)
        for _ in range(300):
            maze = random_obstacles(rng.randint(2, 14), rng.randint(2, 14), density=0.3, seed=rng.random())
            a, d = solve(maze, "astar", diagonal=True), solve(maze, "dijkstra", diagonal=True)
            self.assertEqual(a.found, d.found)
            if a.found:
                self.assertTrue(math.isclose(a.cost, d.cost, abs_tol=1e-9))
                assert_valid_path(self, maze, a)

    def test_every_admissible_heuristic_is_optimal(self):
        rng = random.Random(3)
        for diagonal in (False, True):
            for _ in range(60):
                maze = random_obstacles(10, 10, density=0.25, seed=rng.random())
                ref = solve(maze, "dijkstra", diagonal=diagonal)
                for name in HEURISTICS:
                    if not is_admissible(name, diagonal):
                        continue
                    r = solve(maze, "astar", heuristic=name, diagonal=diagonal)
                    self.assertEqual(r.found, ref.found)
                    if r.found:
                        self.assertTrue(math.isclose(r.cost, ref.cost, abs_tol=1e-9), (name, diagonal))

    def test_weighted_astar_is_bounded_suboptimal(self):
        rng = random.Random(5)
        for w in (1.5, 2.0, 5.0):
            for _ in range(60):
                maze = generate_maze(8, 8, seed=rng.random(), braid=0.6)
                opt = solve(maze, "astar").cost
                got = solve(maze, "weighted", weight=w).cost
                self.assertLessEqual(got, w * opt + 1e-9)

    def test_greedy_returns_a_valid_but_possibly_longer_path(self):
        rng = random.Random(9)
        for _ in range(60):
            maze = generate_maze(8, 8, seed=rng.random(), braid=0.6)
            g, a = solve(maze, "greedy"), solve(maze, "astar")
            assert_valid_path(self, maze, g)
            self.assertGreaterEqual(g.cost, a.cost)

    def test_astar_expands_no_more_than_dijkstra(self):
        rng = random.Random(1)
        for _ in range(60):
            maze = generate_maze(10, 10, seed=rng.random(), braid=0.5)
            self.assertLessEqual(solve(maze, "astar").nodes_expanded, solve(maze, "dijkstra").nodes_expanded)


class EdgeCaseTests(unittest.TestCase):
    def test_unreachable_goal(self):
        maze = Maze.from_lists([[0, 1, 0]], (0, 0), (0, 2))
        for algorithm in ALGORITHMS:
            r = solve(maze, algorithm)
            self.assertFalse(r.found)
            self.assertIsNone(r.path)
            self.assertIsNone(r.steps)

    def test_start_equals_goal(self):
        maze = Maze.from_lists([[0]], (0, 0), (0, 0))
        r = solve(maze)
        self.assertEqual(r.path, [(0, 0)])
        self.assertEqual(r.steps, 0)
        self.assertEqual(r.cost, 0)

    def test_no_diagonal_corner_cutting(self):
        # The only diagonal step from S to G squeezes between two walls.
        maze = Maze.from_lists([[0, 1], [1, 0]], (0, 0), (1, 1))
        self.assertFalse(solve(maze, diagonal=True).found)

    def test_diagonal_shortcut_used_when_legal(self):
        maze = Maze.from_lists([[0, 0], [0, 0]], (0, 0), (1, 1))
        r = solve(maze, diagonal=True)
        self.assertEqual(r.steps, 1)
        self.assertAlmostEqual(r.cost, math.sqrt(2))

    def test_manhattan_with_diagonals_warns(self):
        maze = Maze.from_lists([[0, 0], [0, 0]], (0, 0), (1, 1))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            solve(maze, heuristic="manhattan", diagonal=True)
        self.assertTrue(any(issubclass(w.category, RuntimeWarning) for w in caught))

    def test_bad_arguments(self):
        maze = Maze.from_lists([[0, 0]], (0, 0), (0, 1))
        with self.assertRaises(ValueError):
            solve(maze, "dfs")
        with self.assertRaises(ValueError):
            solve(maze, heuristic="nope")
        with self.assertRaises(ValueError):
            solve(maze, "weighted", weight=0.5)

    def test_summary_is_json_serialisable(self):
        import json
        json.dumps(solve(generate_maze(4, 4, seed=1)).summary())


if __name__ == "__main__":
    unittest.main()
