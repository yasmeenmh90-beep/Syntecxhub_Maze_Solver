"""A* maze solver: four-direction movement with unit costs; Python 3.9+."""
import argparse
import heapq
import json
from pathlib import Path

DEMO = [[0,0,1,0,0],[1,0,1,0,1],[0,0,0,0,0],[0,1,1,1,0],[0,0,0,1,0]]


def astar(grid, start, goal):
    """Return (shortest path, expansion order); path is None if unreachable.

    Each open cell is a graph node; orthogonally adjacent open cells are edges.
    Manhattan distance is admissible and consistent for these unit-cost edges.
    """
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError('Grid must be nonempty and rectangular.')
    if any(cell not in (0, 1) for row in grid for cell in row):
        raise ValueError('Grid cells must be 0 (open) or 1 (wall).')
    rows, cols = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    for point in (start, goal):
        if len(point) != 2 or any(type(v) is not int for v in point):
            raise ValueError('Coordinates must contain two integers.')
        r, c = point
        if not (0 <= r < rows and 0 <= c < cols) or grid[r][c] == 1:
            raise ValueError('Start and goal must be open cells inside the grid.')
    def heuristic(p):
        return abs(p[0]-goal[0]) + abs(p[1]-goal[1])
    frontier = [(heuristic(start), 0, start)]
    cost, parent, expanded = {start: 0}, {}, []
    while frontier:
        _, g, current = heapq.heappop(frontier)
        if g != cost[current]:  # Ignore an outdated queue entry.
            continue
        expanded.append(current)
        if current == goal:
            path = [current]
            while current in parent:
                current = parent[current]
                path.append(current)
            return path[::-1], expanded
        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
            nxt = (current[0]+dr, current[1]+dc)
            r, c = nxt
            if 0 <= r < rows and 0 <= c < cols and grid[r][c] == 0:
                new_cost = g + 1
                if new_cost < cost.get(nxt, float('inf')):
                    cost[nxt], parent[nxt] = new_cost, current
                    heapq.heappush(frontier, (new_cost+heuristic(nxt), new_cost, nxt))
    return None, expanded


def display(grid, start, goal, path, expanded):
    route, visited = set(path or []), set(expanded)
    for r, row in enumerate(grid):
        print(' '.join('B' if (r,c)==start==goal else 'S' if (r,c)==start else
                       'G' if (r,c)==goal else '#' if v else '*' if (r,c) in route
                       else '.' if (r,c) in visited else '-' for c,v in enumerate(row)))
    print('S=start G=goal B=start/goal #=wall *=path .=explored -=open')


def save_svg(grid, start, goal, path, expanded, filename):
    """Save a standalone visualization without external dependencies."""
    size, margin = 48, 24
    width, height = len(grid[0])*size+2*margin, len(grid)*size+100
    route, visited = set(path or []), set(expanded)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#f8fafc"/>']
    for r,row in enumerate(grid):
        for c,v in enumerate(row):
            p = (r,c)
            color = '#1e293b' if v else '#a7f3d0' if p in route else '#dbeafe' if p in visited else '#ffffff'
            label = 'B' if p==start==goal else 'S' if p==start else 'G' if p==goal else ''
            x,y = margin+c*size, margin+r*size
            parts.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{color}" stroke="#94a3b8"/>')
            if label:
                parts.append(f'<text x="{x+24}" y="{y+31}" text-anchor="middle" font-family="sans-serif" font-size="22">{label}</text>')
    message = f'Shortest path: {len(path)-1} moves' if path else 'No path found'
    parts.append(f'<text x="24" y="{height-38}" font-family="sans-serif" font-size="16">{message}</text>')
    parts.append(f'<text x="24" y="{height-15}" font-family="sans-serif" font-size="11">Green: path | Blue: explored | Dark: walls</text></svg>')
    Path(filename).write_text('\n'.join(parts), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--maze', help='JSON file with grid, start and goal')
    parser.add_argument('--svg', help='Save an SVG visualization to this path')
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.maze).read_text()) if args.maze else {'grid': DEMO, 'start':[0,0], 'goal':[4,4]}
        grid, start, goal = data['grid'], tuple(data['start']), tuple(data['goal'])
        path, expanded = astar(grid, start, goal)
        print(f'Shortest path: {len(path)-1} moves\nCoordinates: {path}' if path else 'No path found: goal is unreachable.')
        print(f'Expanded cells: {len(expanded)}')
        display(grid, start, goal, path, expanded)
        if args.svg:
            save_svg(grid, start, goal, path, expanded, args.svg)
            print(f'Visualization saved: {args.svg}')
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')

if __name__ == '__main__':
    main()
