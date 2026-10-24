"""Console and SVG visualisation (no third-party dependencies).

The SVG can be static (final state) or animated: cells light up in the exact
order the algorithm expanded them, then the final path is drawn. Animation
uses SVG SMIL, which plays in every modern browser and in GitHub READMEs.
"""
from __future__ import annotations

import os
import sys
from html import escape
from pathlib import Path
from typing import List, Optional, Sequence, Union

from .grid import Maze
from .search import SearchResult

# Palette
BG = "#0f172a"
PANEL = "#111827"
WALL = "#1e293b"
OPEN = "#f8fafc"
EXPLORED = "#bfdbfe"
FRONTIER_FLASH = "#60a5fa"
PATH = "#10b981"
PATH_LINE = "#047857"
START = "#f59e0b"
GOAL = "#ef4444"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"

# ANSI colours for the console view
_ANSI = {
    "wall": "\033[48;5;236m  \033[0m",
    "open": "\033[48;5;255m  \033[0m",
    "explored": "\033[48;5;153m  \033[0m",
    "path": "\033[48;5;42m  \033[0m",
    "start": "\033[48;5;214m\033[30mS \033[0m",
    "goal": "\033[48;5;196m\033[97mG \033[0m",
}
_PLAIN = {"wall": "#", "open": "-", "explored": ".", "path": "*", "start": "S", "goal": "G"}


def _supports_color(stream=sys.stdout) -> bool:
    return hasattr(stream, "isatty") and stream.isatty() and os.environ.get("NO_COLOR") is None


def render_text(maze: Maze, result: Optional[SearchResult] = None, color: Optional[bool] = None) -> str:
    """Render the maze as text. ``color=None`` auto-detects a colour terminal."""
    color = _supports_color() if color is None else color
    route = set(result.path or []) if result else set()
    visited = set(result.expanded) if result else set()
    lines = []
    for r, row in enumerate(maze.grid):
        tokens = []
        for c, value in enumerate(row):
            p = (r, c)
            if p == maze.start:
                kind = "start"
            elif p == maze.goal:
                kind = "goal"
            elif value:
                kind = "wall"
            elif p in route:
                kind = "path"
            elif p in visited:
                kind = "explored"
            else:
                kind = "open"
            tokens.append(_ANSI[kind] if color else _PLAIN[kind])
        lines.append(("" if color else " ").join(tokens))
    if not color:
        lines.append("S=start  G=goal  #=wall  *=path  .=explored  -=unexplored")
    return "\n".join(lines)


def _fmt(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:.0f}" if abs(value - round(value)) < 1e-9 else f"{value:.2f}"


def render_svg(
    maze: Maze,
    result: SearchResult,
    animate: bool = False,
    duration: float = 6.0,
    title: Optional[str] = None,
) -> str:
    """Return an SVG document visualising ``result`` on ``maze``.

    Args:
        animate: replay the search in expansion order, then draw the path.
        duration: approximate length of the exploration phase in seconds.
    """
    longest = max(maze.rows, maze.cols)
    size = max(6, min(44, 720 // longest))
    margin, header, footer = 24, 92, 44
    grid_w, grid_h = maze.cols * size, maze.rows * size
    width = max(grid_w + 2 * margin, 520)
    height = grid_h + header + footer + margin
    ox, oy = (width - grid_w) // 2, header

    route = result.path or []
    route_set = set(route)
    route_pos = {cell: i for i, cell in enumerate(route)}
    order = {cell: i for i, cell in reversed(list(enumerate(result.expanded)))}  # first expansion
    n = max(len(result.expanded), 1)
    step = min(0.05, duration / n)
    explore_end = n * step + 0.2
    path_step = min(0.06, 2.0 / max(len(route), 1))

    title = title or "Maze solver"
    status = (f"Path found · {result.steps} moves · cost {_fmt(result.cost)}" if result.found
              else "No path: goal is unreachable")
    stats = (f"{result.label} · heuristic: {result.heuristic} · "
             f"{'8-way' if result.diagonal else '4-way'} · expanded {result.nodes_expanded} · "
             f"peak frontier {result.max_frontier}")

    out: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">',
        f"<title>{escape(title)}</title>",
        f'<rect width="100%" height="100%" rx="14" fill="{BG}"/>',
        f'<text x="{margin}" y="38" font-size="20" font-weight="700" fill="{TEXT}">{escape(title)}</text>',
        f'<text x="{margin}" y="62" font-size="14" fill="{PATH if result.found else GOAL}" '
        f'font-weight="600">{escape(status)}</text>',
        f'<text x="{margin}" y="80" font-size="11.5" fill="{MUTED}">{escape(stats)}</text>',
        f'<g shape-rendering="crispEdges">',
    ]

    stroke = ' stroke="#cbd5e1" stroke-width="0.5"' if size >= 14 else ""
    for r, row in enumerate(maze.grid):
        for c, value in enumerate(row):
            p = (r, c)
            x, y = ox + c * size, oy + r * size
            if value:
                out.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{WALL}"/>')
                continue
            final = PATH if p in route_set else EXPLORED if p in order else OPEN
            if not animate:
                out.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{final}"{stroke}/>')
                continue
            anims = []
            if p in order:
                t = order[p] * step
                anims.append(f'<set attributeName="fill" to="{FRONTIER_FLASH}" begin="{t:.3f}s" fill="freeze"/>')
                anims.append(f'<set attributeName="fill" to="{EXPLORED}" begin="{t + step * 4:.3f}s" fill="freeze"/>')
            if p in route_set:
                t = explore_end + route_pos[p] * path_step
                anims.append(f'<set attributeName="fill" to="{PATH}" begin="{t:.3f}s" fill="freeze"/>')
            out.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{OPEN}"{stroke}>'
                       + "".join(anims) + "</rect>")
    out.append("</g>")

    # Path polyline through cell centres
    if len(route) > 1:
        pts = " ".join(f"{ox + c * size + size / 2:.1f},{oy + r * size + size / 2:.1f}" for r, c in route)
        length = sum(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in zip(route, route[1:])) * size
        line_w = max(1.5, size * 0.18)
        if animate:
            out.append(
                f'<polyline points="{pts}" fill="none" stroke="{PATH_LINE}" stroke-width="{line_w:.1f}" '
                f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{length:.1f}" '
                f'stroke-dashoffset="{length:.1f}">'
                f'<animate attributeName="stroke-dashoffset" from="{length:.1f}" to="0" '
                f'begin="{explore_end:.3f}s" dur="{len(route) * path_step:.3f}s" fill="freeze"/></polyline>'
            )
        else:
            out.append(f'<polyline points="{pts}" fill="none" stroke="{PATH_LINE}" stroke-width="{line_w:.1f}" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')

    # Start and goal markers
    for cell, colour, label in ((maze.start, START, "S"), (maze.goal, GOAL, "G")):
        cx, cy = ox + cell[1] * size + size / 2, oy + cell[0] * size + size / 2
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{size * 0.38:.1f}" fill="{colour}"/>')
        if size >= 16:
            out.append(f'<text x="{cx:.1f}" y="{cy + size * 0.15:.1f}" text-anchor="middle" '
                       f'font-size="{size * 0.42:.1f}" font-weight="700" fill="#ffffff">{label}</text>')

    # Legend
    ly = oy + grid_h + 28
    lx = margin
    for colour, label in ((START, "Start"), (GOAL, "Goal"), (WALL, "Wall"),
                          (EXPLORED, "Explored"), (PATH, "Shortest path")):
        out.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" rx="2" fill="{colour}" '
                   f'stroke="{MUTED}" stroke-width="0.5"/>')
        out.append(f'<text x="{lx + 18}" y="{ly}" font-size="12" fill="{MUTED}">{label}</text>')
        lx += 18 + 8 * len(label) + 22
    out.append("</svg>")
    return "\n".join(out) + "\n"


def save_svg(maze: Maze, result: SearchResult, path: Union[str, Path], **kwargs) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_svg(maze, result, **kwargs), encoding="utf-8")
    return path


def comparison_table(results: Sequence[SearchResult], markdown: bool = False) -> str:
    """Tabulate several runs on the same maze."""
    optimal = min((r.cost for r in results if r.cost is not None), default=None)
    headers = ["Algorithm", "Heuristic", "Found", "Moves", "Cost", "Optimal", "Expanded", "Peak frontier", "Time (ms)"]
    rows = []
    for r in results:
        is_opt = (r.cost is not None and optimal is not None and abs(r.cost - optimal) < 1e-9)
        rows.append([r.label, r.heuristic, "yes" if r.found else "no",
                     "—" if r.steps is None else str(r.steps), _fmt(r.cost),
                     "yes" if is_opt else ("—" if not r.found else "no"),
                     str(r.nodes_expanded), str(r.max_frontier), f"{r.elapsed_ms:.2f}"])
    if markdown:
        lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
        lines += ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join(lines)
    widths = [max(len(h), *(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    lines = [fmt.format(*headers), "  ".join("-" * w for w in widths)]
    lines += [fmt.format(*row) for row in rows]
    return "\n".join(line.rstrip() for line in lines)
