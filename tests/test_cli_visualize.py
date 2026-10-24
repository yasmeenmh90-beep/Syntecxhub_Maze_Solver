import contextlib
import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from astar_maze import DEMO_MAZE, Maze, solve
from astar_maze.cli import main
from astar_maze.visualize import comparison_table, render_svg, render_text

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class VisualizeTests(unittest.TestCase):
    def test_text_render(self):
        text = render_text(DEMO_MAZE, solve(DEMO_MAZE), color=False)
        self.assertTrue(text.startswith("S * #"))
        self.assertIn("G", text)

    def test_svg_is_well_formed_static_and_animated(self):
        result = solve(DEMO_MAZE)
        static = ET.fromstring(render_svg(DEMO_MAZE, result))
        animated_src = render_svg(DEMO_MAZE, result, animate=True)
        ET.fromstring(animated_src)
        self.assertTrue(static.tag.endswith("svg"))
        self.assertIn("<set ", animated_src)
        self.assertIn("stroke-dashoffset", animated_src)

    def test_svg_for_unreachable(self):
        maze = Maze.from_lists([[0, 1, 0]], (0, 0), (0, 2))
        svg = render_svg(maze, solve(maze), animate=True)
        ET.fromstring(svg)
        self.assertIn("unreachable", svg)

    def test_comparison_table(self):
        results = [solve(DEMO_MAZE, a) for a in ("astar", "greedy")]
        self.assertIn("A*", comparison_table(results))
        self.assertTrue(comparison_table(results, markdown=True).startswith("| Algorithm"))


class CliTests(unittest.TestCase):
    def test_default_demo_backwards_compatible(self):
        code, out, _ = run("--no-color")
        self.assertEqual(code, 0)
        self.assertIn("Shortest path: 8 moves", out)

    def test_solve_example_files(self):
        code, out, _ = run("solve", "--maze", str(EXAMPLES / "unreachable.json"), "-q")
        self.assertEqual(code, 0)
        self.assertIn("No path found", out)
        code, out, _ = run("solve", "--maze", str(EXAMPLES / "open_room.txt"), "-q", "--diagonal")
        self.assertEqual(code, 0)
        self.assertIn("Shortest path", out)

    def test_json_output(self):
        code, out, _ = run("solve", "--json")
        self.assertEqual(json.loads(out)["steps"], 8)

    def test_svg_and_generate_and_compare(self):
        with tempfile.TemporaryDirectory() as tmp:
            maze_file = Path(tmp) / "m.json"
            self.assertEqual(run("generate", "--rows", "6", "--cols", "6", "--seed", "1", "--out", str(maze_file))[0], 0)
            svg = Path(tmp) / "out.svg"
            self.assertEqual(run("solve", "--maze", str(maze_file), "--svg", str(svg), "--animate", "-q")[0], 0)
            ET.parse(svg)
            code, out, _ = run("compare", "--maze", str(maze_file), "--svg-dir", str(Path(tmp) / "cmp"))
            self.assertEqual(code, 0)
            self.assertIn("Dijkstra", out)
            self.assertEqual(len(list((Path(tmp) / "cmp").glob("*.svg"))), 5)

    def test_errors_exit_with_code_2(self):
        code, _, err = run("solve", "--maze", "does_not_exist.json")
        self.assertEqual(code, 2)
        self.assertIn("Error", err)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text('{"grid": [[0, 1]], "start": [0, 1], "goal": [0, 0]}')
            code, _, err = run("solve", "--maze", str(bad))
            self.assertEqual(code, 2)
            self.assertIn("wall", err)


if __name__ == "__main__":
    unittest.main()
