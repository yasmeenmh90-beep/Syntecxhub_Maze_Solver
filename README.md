# Week 1 — Project 1: Maze Solver using A* Search

A Python implementation of A* that returns a shortest path through a rectangular maze, handles unreachable goals, and visualizes explored cells and the final path. No third-party packages are required. Use Python 3.9 or newer.

## Run on Mac

1. Extract this ZIP.
2. Open Terminal, type `cd ` (with a space), drag the extracted `maze_solver` folder into Terminal, and press Enter.
3. Run:

```bash
python3 maze_solver.py --svg solution.svg
```

Open `solution.svg` in your browser to see the result. The default maze has a shortest path of **8 moves**. The output also prints path coordinates and a console visualization.

## Use your own maze

Edit `maze.json`: `0` is open, `1` is a wall. Coordinates are `[row, column]`, starting at zero in the top-left corner. Start and goal must be open cells.

```bash
python3 maze_solver.py --maze maze.json --svg solution.svg
python3 maze_solver.py --maze unreachable.json --svg unreachable.svg
```

The second command prints “No path found”. An unreachable maze is a valid result; malformed inputs produce an error.

## How A* works

Each open cell represents a node. Edges connect open cells immediately above, below, left or right. Each move costs 1; diagonal movement is disabled.

A* prioritizes the smallest `f(n) = g(n) + h(n)`:

- `g(n)`: best known number of moves from the start.
- `h(n)`: Manhattan distance, `abs(row-goal_row) + abs(column-goal_column)`.
- `f(n)`: estimated total distance through that cell.

A heap stores candidate cells. When a cheaper route to a neighbor is found, its cost and parent are updated. When the goal is removed from the heap, parent links reconstruct the path. If the heap becomes empty first, the goal is unreachable. Outdated heap entries are skipped.

Manhattan distance never overestimates the remaining distance under these movement rules and is consistent, so A* returns an optimal path. Multiple equally short paths may exist. The number of moves is `len(path) - 1`, because the path includes both endpoints.

## Visualization

Console: S=start, G=goal, B=both, #=wall, *=path, .=explored, -=open.
SVG: green=path, blue=explored, dark=walls. Visualization is a final static snapshot, not an animation.

## Verify

```bash
python3 -m unittest -v
```

Tests cover unreachable goals, identical endpoints, invalid grids/endpoints, and 100 seeded random mazes compared against an independent breadth-first search for shortest-path length. Returned paths are checked for legal steps and wall avoidance.

## Files

- `maze_solver.py`: algorithm, command-line runner, console and SVG visualization.
- `maze.json`: editable reachable example.
- `unreachable.json`: unreachable example.
- `test_maze_solver.py`: correctness checks.
- `solution.svg`: generated example output.

## Explain it in your own words

“My program models a maze as a graph. A* selects cells using the distance already travelled plus Manhattan distance to the goal. It tracks parent cells to reconstruct a shortest route and reports when no route exists.”

Prepared implementation: run and review it before submitting. Submission is not implied by these files.
