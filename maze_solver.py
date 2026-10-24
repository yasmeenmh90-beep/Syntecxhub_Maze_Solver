#!/usr/bin/env python3
"""Entry point kept for convenience: `python3 maze_solver.py [command] [options]`.

Equivalent to `python3 -m astar_maze`. Run with --help for all options.
"""
import sys

from astar_maze.cli import main

if __name__ == "__main__":
    sys.exit(main())
