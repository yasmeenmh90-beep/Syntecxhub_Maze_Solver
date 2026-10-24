"""Command-line interface.

    python -m astar_maze solve    [--maze FILE] [--algorithm A] [--diagonal] [--svg OUT] [--animate]
    python -m astar_maze compare  [--maze FILE] [--diagonal] [--svg-dir DIR] [--markdown]
    python -m astar_maze generate --rows R --cols C [--seed N] [--braid F] --out FILE
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import List, Optional

from . import __version__
from .generator import generate_maze, random_obstacles
from .grid import DEMO_MAZE, Maze, MazeError
from .heuristics import HEURISTICS
from .search import ALGORITHMS, solve
from .visualize import comparison_table, render_text, save_svg

COMMANDS = ("solve", "compare", "generate")


def _add_maze_source(p: argparse.ArgumentParser) -> None:
    src = p.add_mutually_exclusive_group()
    src.add_argument("--maze", metavar="FILE", help="maze file (.json or .txt); default: built-in 5x5 demo")
    src.add_argument("--random", nargs=2, type=int, metavar=("ROWS", "COLS"),
                     help="generate a random maze with ROWS x COLS rooms instead of loading a file")
    p.add_argument("--seed", type=int, default=None, help="random seed for --random (reproducible)")
    p.add_argument("--braid", type=float, default=0.0,
                   help="for --random: fraction of dead ends opened to create loops (0-1)")
    p.add_argument("--diagonal", action="store_true", help="allow 8-direction movement (diagonal cost sqrt 2)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="astar-maze",
        description="Shortest-path maze solver using A* search, with algorithm comparison and visualisation.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    s = sub.add_parser("solve", help="solve one maze and visualise the result")
    _add_maze_source(s)
    s.add_argument("--algorithm", "-a", choices=ALGORITHMS, default="astar")
    s.add_argument("--heuristic", choices=list(HEURISTICS), default=None,
                   help="default: manhattan (4-way) or octile (8-way)")
    s.add_argument("--weight", type=float, default=2.0, help="heuristic weight for --algorithm weighted")
    s.add_argument("--svg", metavar="OUT", help="save an SVG visualisation")
    s.add_argument("--animate", action="store_true", help="make the SVG replay the search step by step")
    s.add_argument("--json", action="store_true", help="print the result as JSON instead of text")
    s.add_argument("--no-color", action="store_true", help="plain-text console output")
    s.add_argument("--quiet", "-q", action="store_true", help="do not draw the maze in the console")

    c = sub.add_parser("compare", help="run every algorithm on the same maze and compare them")
    _add_maze_source(c)
    c.add_argument("--weight", type=float, default=2.0, help="heuristic weight for weighted A*")
    c.add_argument("--svg-dir", metavar="DIR", help="save one animated SVG per algorithm to DIR")
    c.add_argument("--markdown", action="store_true", help="print the table in Markdown")

    g = sub.add_parser("generate", help="generate a random maze file")
    g.add_argument("--rows", type=int, required=True, help="number of rooms vertically")
    g.add_argument("--cols", type=int, required=True, help="number of rooms horizontally")
    g.add_argument("--seed", type=int, default=None)
    g.add_argument("--braid", type=float, default=0.0, help="fraction of dead ends to open (0-1)")
    g.add_argument("--obstacles", type=float, default=None, metavar="DENSITY",
                   help="instead of a corridor maze, scatter walls on an open ROWSxCOLS field")
    g.add_argument("--out", required=True, help="output file (.json or .txt)")
    return parser


def _load(args: argparse.Namespace) -> Maze:
    if args.maze:
        return Maze.load(args.maze)
    if args.random:
        return generate_maze(args.random[0], args.random[1], seed=args.seed, braid=args.braid)
    return DEMO_MAZE


def _cmd_solve(args: argparse.Namespace) -> int:
    maze = _load(args)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = solve(maze, args.algorithm, heuristic=args.heuristic, diagonal=args.diagonal, weight=args.weight)
    for w in caught:
        print(f"Warning: {w.message}", file=sys.stderr)

    if args.json:
        print(json.dumps(result.summary(), indent=2))
    else:
        print(f"Maze: {maze.rows}x{maze.cols}, {maze.open_cells} open cells, "
              f"start {list(maze.start)} -> goal {list(maze.goal)}")
        print(f"Algorithm: {result.label} (heuristic: {result.heuristic}, "
              f"{'8-way' if args.diagonal else '4-way'} movement)")
        if result.found:
            cost = "" if not args.diagonal else f", cost {result.cost:.3f}"
            print(f"Shortest path: {result.steps} moves{cost}")
            coords = [tuple(p) for p in result.path]
            if len(coords) > 24:
                print(f"Coordinates: {coords[:6]} ... {coords[-6:]} ({len(coords)} cells)")
            else:
                print(f"Coordinates: {coords}")
        else:
            print("No path found: goal is unreachable.")
        print(f"Expanded cells: {result.nodes_expanded} | peak frontier: {result.max_frontier} | "
              f"time: {result.elapsed_ms:.2f} ms")
        if not args.quiet:
            print()
            print(render_text(maze, result, color=False if args.no_color else None))
    if args.svg:
        title = Path(args.maze).stem if args.maze else "Maze solver"
        save_svg(maze, result, args.svg, animate=args.animate, title=f"{title} — {result.label}")
        if not args.json:
            print(f"\nVisualisation saved: {args.svg}" + (" (animated)" if args.animate else ""))
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    maze = _load(args)
    results = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for algorithm in ALGORITHMS:
            results.append(solve(maze, algorithm, diagonal=args.diagonal, weight=args.weight))
    print(f"Maze: {maze.rows}x{maze.cols}, {maze.open_cells} open cells, "
          f"{'8-way' if args.diagonal else '4-way'} movement\n")
    print(comparison_table(results, markdown=args.markdown))
    if args.svg_dir:
        out = Path(args.svg_dir)
        for r in results:
            save_svg(maze, r, out / f"{r.algorithm}.svg", animate=True, title=r.label)
        print(f"\nAnimated SVGs saved to: {out}/")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    if args.obstacles is not None:
        maze = random_obstacles(args.rows, args.cols, density=args.obstacles, seed=args.seed)
    else:
        maze = generate_maze(args.rows, args.cols, seed=args.seed, braid=args.braid)
    maze.save(args.out)
    print(f"Saved {maze.rows}x{maze.cols} maze to {args.out}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Backwards compatible: `maze_solver.py --maze x.json --svg y.svg` means `solve ...`
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help", "--version")):
        argv.insert(0, "solve")
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {"solve": _cmd_solve, "compare": _cmd_compare, "generate": _cmd_generate}
    try:
        return handlers[args.command](args)
    except (MazeError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
