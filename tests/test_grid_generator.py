import tempfile
import unittest
from collections import deque
from pathlib import Path

from astar_maze import Maze, MazeError, generate_maze, random_obstacles


def reachable(maze):
    seen, queue = {maze.start}, deque([maze.start])
    while queue:
        for n, _ in maze.neighbors(queue.popleft()):
            if n not in seen:
                seen.add(n)
                queue.append(n)
    return seen


class MazeValidationTests(unittest.TestCase):
    def test_rejects_malformed_mazes(self):
        bad = [
            ([], (0, 0), (0, 0)),                 # empty
            ([[0], [0, 0]], (0, 0), (0, 0)),      # ragged
            ([[2]], (0, 0), (0, 0)),              # bad cell value
            ([[1]], (0, 0), (0, 0)),              # start on wall
            ([[0]], (-1, 0), (0, 0)),             # out of bounds
            ([[0, 0]], (0, 0), (0, 5)),           # goal out of bounds
            ([[0]], (0.0, 0), (0, 0)),            # non-integer coordinate
            ([[0]], (0,), (0, 0)),                # wrong arity
        ]
        for grid, start, goal in bad:
            with self.assertRaises(MazeError, msg=(grid, start, goal)):
                Maze.from_lists(grid, start, goal)

    def test_text_round_trip(self):
        text = "S..#\n.#.#\n...G\n"
        maze = Maze.from_text(text)
        self.assertEqual(maze.start, (0, 0))
        self.assertEqual(maze.goal, (2, 3))
        self.assertEqual(maze.grid[1], (0, 1, 0, 1))
        self.assertEqual(maze.to_text(), text)

    def test_text_errors(self):
        for text in ("S..\n...", "S.G\nS..", "S.G\n.x."):
            with self.assertRaises(MazeError):
                Maze.from_text(text)

    def test_file_round_trip(self):
        maze = generate_maze(5, 6, seed=3)
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("m.json", "m.txt"):
                path = Path(tmp) / name
                maze.save(path)
                self.assertEqual(Maze.load(path), maze)

    def test_json_missing_keys(self):
        with self.assertRaises(MazeError):
            Maze.from_dict({"grid": [[0]], "start": [0, 0]})


class GeneratorTests(unittest.TestCase):
    def test_perfect_maze_is_fully_connected_tree(self):
        for seed in range(20):
            maze = generate_maze(7, 9, seed=seed)
            self.assertEqual((maze.rows, maze.cols), (15, 19))
            self.assertEqual(len(reachable(maze)), maze.open_cells)
            # A spanning tree over R*C rooms has R*C-1 passages: open = rooms + passages.
            self.assertEqual(maze.open_cells, 7 * 9 + (7 * 9 - 1))

    def test_seed_is_reproducible(self):
        self.assertEqual(generate_maze(6, 6, seed=99), generate_maze(6, 6, seed=99))
        self.assertNotEqual(generate_maze(6, 6, seed=1), generate_maze(6, 6, seed=2))

    def test_braiding_adds_loops_and_keeps_border(self):
        perfect, braided = generate_maze(10, 10, seed=4), generate_maze(10, 10, seed=4, braid=1.0)
        self.assertGreater(braided.open_cells, perfect.open_cells)
        g = braided.grid
        self.assertTrue(all(g[0][c] == g[-1][c] == 1 for c in range(braided.cols)))
        self.assertTrue(all(g[r][0] == g[r][-1] == 1 for r in range(braided.rows)))

    def test_invalid_generator_arguments(self):
        with self.assertRaises(ValueError):
            generate_maze(0, 3)
        with self.assertRaises(ValueError):
            generate_maze(3, 3, braid=2)
        with self.assertRaises(ValueError):
            random_obstacles(3, 3, density=1.0)


if __name__ == "__main__":
    unittest.main()
