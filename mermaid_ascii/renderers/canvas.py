"""A tiny mutable 2D character grid used to compose ASCII art.

Renderers should not manipulate strings by hand - they draw onto a Canvas
(boxes, lines, text) and call ``render()`` once at the end. This keeps all
the "how do characters actually get placed" logic in one, testable place.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# Bitmask directions used to auto-merge overlapping line segments into the
# correct box-drawing character (so a branch and a merge both "just work"
# even when several edges pass through the same cell).
NORTH, SOUTH, EAST, WEST = 1, 2, 4, 8

_MASK_TO_CHAR = {
    NORTH: "\u2502", SOUTH: "\u2502", NORTH | SOUTH: "\u2502",
    EAST: "\u2500", WEST: "\u2500", EAST | WEST: "\u2500",
    NORTH | EAST: "\u2514", NORTH | WEST: "\u2518",
    SOUTH | EAST: "\u250c", SOUTH | WEST: "\u2510",
    NORTH | SOUTH | EAST: "\u251c", NORTH | SOUTH | WEST: "\u2524",
    SOUTH | EAST | WEST: "\u252c", NORTH | EAST | WEST: "\u2534",
    NORTH | SOUTH | EAST | WEST: "\u253c",
}


class Canvas:
    def __init__(self, width: int = 1, height: int = 1, fill: str = " ") -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self._fill = fill
        self._grid: List[List[str]] = [[fill] * self.width for _ in range(self.height)]
        self._line_mask: Dict[Tuple[int, int], int] = {}

    def _ensure_size(self, x: int, y: int) -> None:
        if y >= self.height:
            for _ in range(y - self.height + 1):
                self._grid.append([self._fill] * self.width)
            self.height = len(self._grid)
        if x >= self.width:
            grow = x - self.width + 1
            for row in self._grid:
                row.extend([self._fill] * grow)
            self.width += grow

    def set(self, x: int, y: int, ch: str) -> None:
        if x < 0 or y < 0 or not ch:
            return
        self._ensure_size(x, y)
        self._grid[y][x] = ch

    def draw_text(self, x: int, y: int, text: str) -> None:
        for i, ch in enumerate(text):
            self.set(x + i, y, ch)

    def draw_hline(self, x: int, y: int, length: int, ch: str = "\u2500") -> None:
        for i in range(max(0, length)):
            self.set(x + i, y, ch)

    def draw_vline(self, x: int, y: int, length: int, ch: str = "\u2502") -> None:
        for i in range(max(0, length)):
            self.set(x, y + i, ch)

    # -- merge-aware line drawing, for connectors --------------------------
    def _mark(self, x: int, y: int, bits: int) -> None:
        self._ensure_size(x, y)
        self._line_mask[(x, y)] = self._line_mask.get((x, y), 0) | bits

    def line_h(self, x: int, y: int, length: int) -> None:
        """Mark a horizontal line segment; merges cleanly with crossing lines."""
        length = max(1, length)
        for i in range(length - 1):
            self._mark(x + i, y, EAST)
            self._mark(x + i + 1, y, WEST)
        if length == 1:
            self._mark(x, y, EAST | WEST)

    def line_v(self, x: int, y: int, length: int) -> None:
        """Mark a vertical line segment; merges cleanly with crossing lines."""
        length = max(1, length)
        for i in range(length - 1):
            self._mark(x, y + i, SOUTH)
            self._mark(x, y + i + 1, NORTH)
        if length == 1:
            self._mark(x, y, NORTH | SOUTH)

    def commit_lines(self) -> None:
        """Bake all marked line segments into the character grid.

        Call this once after every edge has been marked (so junctions merge
        correctly) and before drawing arrowheads/labels on top.
        """
        for (x, y), bits in self._line_mask.items():
            self.set(x, y, _MASK_TO_CHAR.get(bits, "\u2502" if bits & (NORTH | SOUTH) else "\u2500"))
        self._line_mask.clear()

    def draw_box(self, x: int, y: int, w: int, h: int, lines: List[str],
                 corners: str, horiz: str, vert: str) -> None:
        """Draw a w x h box with the given corner/edge characters and
        vertically-centered, horizontally-centered text lines inside it."""
        tl, tr, bl, br = corners[0], corners[1], corners[2], corners[3]
        self.draw_hline(x + 1, y, w - 2, horiz)
        self.draw_hline(x + 1, y + h - 1, w - 2, horiz)
        self.draw_vline(x, y + 1, h - 2, vert)
        self.draw_vline(x + w - 1, y + 1, h - 2, vert)
        self.set(x, y, tl)
        self.set(x + w - 1, y, tr)
        self.set(x, y + h - 1, bl)
        self.set(x + w - 1, y + h - 1, br)

        text_top = y + 1 + max(0, ((h - 2) - len(lines)) // 2)
        for i, line in enumerate(lines):
            text_x = x + max(1, (w - len(line)) // 2)
            self.draw_text(text_x, text_top + i, line)

    def render(self) -> str:
        return "\n".join("".join(row).rstrip() for row in self._grid).strip("\n")
