"""Renders a flowchart Graph as a plain ASCII/Unicode box-and-arrow diagram.

Algorithm (a simplified Sugiyama-style layered layout):

1.  Layer assignment - each node is placed in the layer one below the
    deepest of its predecessors (longest-path layering), computed with
    Kahn's algorithm. Nodes with no predecessors start at layer 0.
2.  Positioning - within a layer, nodes are laid out left-to-right (or
    top-to-bottom for LR/RL) in first-seen order, each sized to fit its
    label.
3.  Drawing - every node becomes a box on a Canvas; every edge becomes an
    orthogonal (right-angle) connector between box edges, with its label
    placed on the connector's middle segment.

This is a best-effort planar layout, not a full crossing-minimising graph
drawer: dense graphs with many long skip-layer edges may overlap. It is
tuned to look good on the common case - small/medium flowcharts.
"""
from __future__ import annotations

import textwrap
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..models import Direction, Edge, Graph, Node, NodeShape
from .base import BaseRenderer
from .canvas import Canvas



# shape -> (corners "TL TR BL BR", horizontal char, vertical char)
_BOX_STYLE: Dict[NodeShape, Tuple[str, str, str]] = {
    NodeShape.DEFAULT: ("\u250c\u2510\u2514\u2518", "\u2500", "\u2502"),
    NodeShape.RECTANGLE: ("\u250c\u2510\u2514\u2518", "\u2500", "\u2502"),
    NodeShape.SUBROUTINE: ("\u250c\u2510\u2514\u2518", "\u2500", "\u2502"),
    NodeShape.CYLINDER: ("\u250c\u2510\u2514\u2518", "\u2500", "\u2502"),
    NodeShape.ROUNDED: ("\u256d\u256e\u2570\u256f", "\u2500", "\u2502"),
    NodeShape.STADIUM: ("\u256d\u256e\u2570\u256f", "\u2500", "\u2502"),
    NodeShape.CIRCLE: ("\u2554\u2557\u255a\u255d", "\u2550", "\u2551"),
    NodeShape.HEXAGON: ("\u2554\u2557\u255a\u255d", "\u2550", "\u2551"),
    NodeShape.RHOMBUS: ("/\\\\/", "-", "|"),  # parallelogram look for decisions
}


@dataclass
class _Box:
    node: Node
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    lines: List[str] = None

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2


class FlowchartASCIIRenderer(BaseRenderer):
    # Small margin kept before the very first layer, so a detour edge that
    # targets a layer-0 node always has a safe row/column to enter from
    # "outside" the diagram, even when that node has no predecessor layer.
    _MARGIN = 2

    # Spacing gets ratcheted down through these profiles, in order, until
    # the rendered diagram fits within max_width (or the profiles run out).
    # Each tuple is (layer_gap, node_spacing, label_wrap_width).
    _SPACING_PROFILES: Tuple[Tuple[int, int, int], ...] = (
        (5, 3, 18),
        (4, 2, 16),
        (3, 2, 13),
        (2, 1, 11),
        (1, 1, 9),
    )

    def __init__(self, layer_gap: int = 5, node_spacing: int = 3, label_wrap: int = 18) -> None:
        self.layer_gap = layer_gap
        self.node_spacing = node_spacing
        self.label_wrap = label_wrap

    def render(self, graph: Graph, max_width: "int | None" = None, direction: "str | None" = None) -> str:
        """Render ``graph`` to an ASCII string.

        Args:
            max_width: if given, spacing is progressively tightened (see
                ``_SPACING_PROFILES``) until every line fits within this
                many columns, or the tightest profile is reached. ``None``
                (the default) always renders at this instance's own spacing.
            direction: optional override (``"TD"``, ``"LR"``, ...) applied
                on top of whatever direction the mermaid source declared -
                useful for forcing a wide left-right chain into a
                terminal-friendly top-down layout, or vice versa.
        """
        if direction:
            graph.direction = Direction.from_token(direction)

        if max_width is None:
            return self._render_once(graph)

        profiles = ((self.layer_gap, self.node_spacing, self.label_wrap),) + self._SPACING_PROFILES
        result = None
        for layer_gap, node_spacing, label_wrap in profiles:
            self.layer_gap, self.node_spacing, self.label_wrap = layer_gap, node_spacing, label_wrap
            result = self._render_once(graph)
            widest = max((len(line) for line in result.splitlines()), default=0)
            if widest <= max_width:
                return result
        return result  # exhausted every profile - return the tightest anyway

    def _render_once(self, graph: Graph) -> str:
        layers = self._compute_layers(graph)
        layer_index = {nid: i for i, layer_ids in enumerate(layers) for nid in layer_ids}
        if graph.direction.is_reversed:
            layers = list(reversed(layers))

        boxes = self._build_boxes(graph, layers)
        if graph.direction.is_horizontal:
            # Inline edge labels sit *in* the gap between layers for LR/RL
            # layouts (see _connect_horizontal), so the gap needs to be wide
            # enough for the longest one, or it'll crowd into the next box.
            longest_label = max((len(e.label) for e in graph.edges if e.label), default=0)
            effective_gap = max(self.layer_gap, longest_label + 3) if longest_label else self.layer_gap
            self._position_horizontal(layers, boxes, layer_gap=effective_gap)
        else:
            self._position_vertical(layers, boxes)

        width = max((b.x + b.w for b in boxes.values()), default=1) + 1
        height = max((b.y + b.h for b in boxes.values()), default=1) + 1
        canvas = Canvas(width, height)

        for box in boxes.values():
            corners, horiz, vert = _BOX_STYLE.get(box.node.shape, _BOX_STYLE[NodeShape.DEFAULT])
            canvas.draw_box(box.x, box.y, box.w, box.h, box.lines, corners, horiz, vert)

        # Only an edge between two *adjacent* layers can be routed straight
        # through the interior as a simple orthogonal connector. A "back
        # edge" (cycle / retry) or a "skip edge" (more than one layer at
        # once) would otherwise cut straight across unrelated boxes sitting
        # in between, so both get routed around the outside instead.
        forward_edges, detour_edges = [], []
        for edge in graph.edges:
            src, dst = boxes.get(edge.source), boxes.get(edge.target)
            if src is None or dst is None or src is dst:
                continue
            if layer_index.get(edge.target, 0) == layer_index.get(edge.source, 0) + 1:
                forward_edges.append((edge, src, dst))
            else:
                detour_edges.append((edge, src, dst))

        # Phase 1: mark every edge's path so overlapping/branching lines at
        # shared cells merge into the correct box-drawing character.
        connect = self._connect_horizontal if graph.direction.is_horizontal else self._connect_vertical
        decorations = [connect(canvas, src, dst, edge) for edge, src, dst in forward_edges]

        if graph.direction.is_horizontal:
            # Layers run left-to-right. Every node's own layer has a "right
            # edge" column (the widest box in that layer) which is
            # guaranteed free of *any* box at *any* row - so it's always
            # safe to exit sideways into it, then travel down a shared
            # lane below every box (also guaranteed free, at *any* column),
            # then back up into the gap column just before the target's
            # own layer.
            layer_right: Dict[str, int] = {}
            for layer_ids in layers:
                if not layer_ids:
                    continue
                right = max(boxes[n].x + boxes[n].w for n in layer_ids)
                for n in layer_ids:
                    layer_right[n] = right
            base_lane = max((b.y + b.h for b in boxes.values()), default=0) + 2
            for i, (edge, src, dst) in enumerate(detour_edges):
                exit_col = layer_right.get(edge.source, src.x + src.w)
                lane_y = base_lane + i * 2
                decorations.append(self._connect_detour_horizontal(canvas, src, dst, edge, exit_col, lane_y))
        else:
            # Layers run top-to-bottom. Symmetric idea: every node's own
            # layer has a "bottom edge" row (the tallest box in that layer)
            # free of any box at any column, so it's safe to exit downward
            # into it, travel sideways to a shared lane to the right of
            # every box (free at any row), then back to the gap row just
            # above the target's own layer.
            layer_bottom: Dict[str, int] = {}
            for layer_ids in layers:
                if not layer_ids:
                    continue
                bottom = max(boxes[n].y + boxes[n].h for n in layer_ids)
                for n in layer_ids:
                    layer_bottom[n] = bottom
            base_lane = max((b.x + b.w for b in boxes.values()), default=0) + 2
            for i, (edge, src, dst) in enumerate(detour_edges):
                exit_row = layer_bottom.get(edge.source, src.y + src.h)
                lane_x = base_lane + i * 2
                decorations.append(self._connect_detour_vertical(canvas, src, dst, edge, exit_row, lane_x))

        canvas.commit_lines()

        # Phase 2: arrowheads and labels are drawn on top, after merging.
        for deco in decorations:
            if deco is None:
                continue
            arrow, label = deco
            if arrow:
                canvas.set(*arrow)
            if label:
                canvas.draw_text(*label)

        return canvas.render()

    # ------------------------------------------------------------------
    # Layer assignment
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_layers(graph: Graph) -> List[List[str]]:
        """Longest-path layering via a cycle-tolerant Kahn's algorithm.

        Plain topological sort gives up as soon as a cycle leaves no node
        with in-degree 0. Flowcharts commonly have cycles (retry loops,
        "go back" edges), so instead: whenever the ready-queue runs dry but
        nodes remain, the earliest-declared remaining node is forced through
        - which is equivalent to treating its not-yet-satisfied incoming
        edges as "back edges" to be routed separately later (see
        ``_connect_detour``).
        """
        order = list(graph.nodes.keys())  # first-seen / declaration order
        adjacency: Dict[str, List[str]] = {nid: [] for nid in order}
        for edge in graph.edges:
            if edge.source in adjacency and edge.target in adjacency and edge.source != edge.target:
                adjacency[edge.source].append(edge.target)

        indegree: Dict[str, int] = {nid: 0 for nid in order}
        for targets in adjacency.values():
            for t in targets:
                indegree[t] += 1

        layer: Dict[str, int] = {nid: 0 for nid in order}
        remaining_indeg = dict(indegree)
        processed = set()
        in_queue = set(n for n in order if remaining_indeg[n] == 0)
        queue = deque(n for n in order if remaining_indeg[n] == 0)

        while len(processed) < len(order):
            if not queue:
                forced = next(n for n in order if n not in processed)
                queue.append(forced)
                in_queue.add(forced)
            node_id = queue.popleft()
            in_queue.discard(node_id)
            if node_id in processed:
                continue
            processed.add(node_id)
            for neighbour in adjacency[node_id]:
                if neighbour in processed:
                    continue  # back edge into an already-placed node: ignore for layering
                layer[neighbour] = max(layer[neighbour], layer[node_id] + 1)
                remaining_indeg[neighbour] = max(0, remaining_indeg[neighbour] - 1)
                if remaining_indeg[neighbour] == 0 and neighbour not in in_queue:
                    queue.append(neighbour)
                    in_queue.add(neighbour)

        layers_by_index: Dict[int, List[str]] = {}
        for node_id in order:  # preserves first-seen / insertion order within a layer
            layers_by_index.setdefault(layer[node_id], []).append(node_id)

        max_index = max(layers_by_index.keys(), default=0)
        return [layers_by_index.get(i, []) for i in range(max_index + 1)]

    # ------------------------------------------------------------------
    # Box sizing
    # ------------------------------------------------------------------
    def _build_boxes(self, graph: Graph, layers: List[List[str]]) -> Dict[str, _Box]:
        boxes: Dict[str, _Box] = {}
        for layer_ids in layers:
            for node_id in layer_ids:
                node = graph.get_node(node_id)
                lines = textwrap.wrap(node.label, self.label_wrap) or [node.label]
                inner_w = max(len(l) for l in lines)
                w = inner_w + 4   # 1 border + 1 pad each side
                h = len(lines) + 2
                # decision parallelogram needs a little breathing room
                if node.shape == NodeShape.RHOMBUS:
                    w += 2
                boxes[node_id] = _Box(node=node, w=w, h=h, lines=lines)
        return boxes

    # ------------------------------------------------------------------
    # Positioning
    # ------------------------------------------------------------------
    def _position_vertical(self, layers: List[List[str]], boxes: Dict[str, _Box]) -> None:
        y = self._MARGIN  # leaves a sliver above layer 0 for detours entering it from "above"
        max_width = 0
        for layer_ids in layers:
            layer_boxes = [boxes[nid] for nid in layer_ids]
            total_w = sum(b.w for b in layer_boxes) + self.node_spacing * max(0, len(layer_boxes) - 1)
            max_width = max(max_width, total_w)

        prev_single_cx = None
        for layer_ids in layers:
            layer_boxes = [boxes[nid] for nid in layer_ids]
            total_w = sum(b.w for b in layer_boxes) + self.node_spacing * max(0, len(layer_boxes) - 1)
            x = max(0, (max_width - total_w) // 2)
            layer_h = max((b.h for b in layer_boxes), default=1)
            for box in layer_boxes:
                box.x = x
                box.y = y
                x += box.w + self.node_spacing
            if len(layer_boxes) == 1:
                if prev_single_cx is not None:
                    # Straight 1-to-1 chain: snap to the predecessor's exact
                    # center instead of this layer's own independent centering,
                    # so long linear chains draw as one clean vertical line
                    # instead of a little left/right jog at every box.
                    layer_boxes[0].x = max(0, prev_single_cx - layer_boxes[0].w // 2)
                prev_single_cx = layer_boxes[0].cx
            else:
                prev_single_cx = None
            y += layer_h + self.layer_gap

    def _position_horizontal(self, layers: List[List[str]], boxes: Dict[str, _Box], layer_gap: int = None) -> None:
        gap = self.layer_gap if layer_gap is None else layer_gap
        x = self._MARGIN  # leaves a sliver before layer 0 for detours entering it from "before"
        max_height = 0
        for layer_ids in layers:
            layer_boxes = [boxes[nid] for nid in layer_ids]
            total_h = sum(b.h for b in layer_boxes) + self.node_spacing * max(0, len(layer_boxes) - 1)
            max_height = max(max_height, total_h)

        prev_single_cy = None
        for layer_ids in layers:
            layer_boxes = [boxes[nid] for nid in layer_ids]
            total_h = sum(b.h for b in layer_boxes) + self.node_spacing * max(0, len(layer_boxes) - 1)
            y = max(0, (max_height - total_h) // 2)
            layer_w = max((b.w for b in layer_boxes), default=1)
            for box in layer_boxes:
                box.x = x
                box.y = y
                y += box.h + self.node_spacing
            if len(layer_boxes) == 1:
                if prev_single_cy is not None:
                    layer_boxes[0].y = max(0, prev_single_cy - layer_boxes[0].h // 2)
                prev_single_cy = layer_boxes[0].cy
            else:
                prev_single_cy = None
            x += layer_w + gap

    # ------------------------------------------------------------------
    # Edge drawing
    # ------------------------------------------------------------------
    @staticmethod
    def _connect_vertical(canvas: Canvas, src: "_Box", dst: "_Box", edge: Edge):
        """Mark a vertical (top-down style) orthogonal connector.

        Returns ``(arrow_set_args, label_draw_args)`` to be applied by the
        caller *after* every edge's lines have been merged, or ``None``
        pieces where there is nothing to draw.
        """
        x1, x2 = src.cx, dst.cx
        going_down = dst.y >= src.y
        y1 = src.y + src.h if going_down else src.y - 1
        y2 = dst.y - 1 if going_down else dst.y + dst.h
        step = 1 if y2 >= y1 else -1
        arrow_char = "v" if step > 0 else "^"

        if x1 == x2:
            canvas.line_v(x1, min(y1, y2), abs(y2 - y1) + 1)
            arrow = (x2, y2, arrow_char) if edge.directed else None
            label = (x1 + 2, (y1 + y2) // 2, edge.label) if edge.label else None
            return arrow, label

        mid = y1 + step * (abs(y2 - y1) // 2) if abs(y2 - y1) > 1 else y1
        canvas.line_v(x1, min(y1, mid), abs(mid - y1) + 1)
        lo, hi = min(x1, x2), max(x1, x2)
        canvas.line_h(lo, mid, hi - lo + 1)
        canvas.line_v(x2, min(mid, y2), abs(y2 - mid) + 1)

        arrow = (x2, y2, arrow_char) if edge.directed else None
        label = None
        if edge.label:
            text_x = lo + max(0, (hi - lo - len(edge.label)) // 2)
            label_y = mid - 1 if mid - 1 > min(y1, y2) else mid + 1
            label = (text_x, label_y, edge.label)
        return arrow, label

    @staticmethod
    def _connect_detour_horizontal(canvas: Canvas, src: "_Box", dst: "_Box", edge: Edge,
                                    exit_col: int, lane_y: int):
        """Route a back/skip edge (LR/RL layouts) via: sideways out of src's
        own layer (safe at any row), down/up a shared lane below every box
        (safe at any column), then sideways into the gap just before dst's
        own layer (safe at any row) and straight into dst's left edge.

        Both of ``exit_col``/``lane_y`` are chosen so every segment below
        only ever touches rows/columns that no box occupies - see the
        module-level routing note in ``_render_once`` for why that holds.
        """
        y1 = src.cy
        entry_col = dst.x - 1  # always just before dst's own layer - see _render_once
        src_right = src.x + src.w

        canvas.line_h(src_right, y1, max(1, exit_col - src_right + 1))
        lo, hi = min(y1, lane_y), max(y1, lane_y)
        canvas.line_v(exit_col, lo, hi - lo + 1)
        lo2, hi2 = min(exit_col, entry_col), max(exit_col, entry_col)
        canvas.line_h(lo2, lane_y, hi2 - lo2 + 1)
        lo3, hi3 = min(lane_y, dst.cy), max(lane_y, dst.cy)
        canvas.line_v(entry_col, lo3, hi3 - lo3 + 1)

        arrow = (entry_col, dst.cy, ">") if edge.directed else None
        label = (min(exit_col, entry_col), lane_y - 1, edge.label) if edge.label else None
        return arrow, label

    @staticmethod
    def _connect_detour_vertical(canvas: Canvas, src: "_Box", dst: "_Box", edge: Edge,
                                  exit_row: int, lane_x: int):
        """Route a back/skip edge (TD/BT layouts) via: down out of src's own
        layer (safe at any column), sideways to a shared lane to the right
        of every box (safe at any row), then down/up into the gap just
        above dst's own layer (safe at any column) and straight into dst's
        top edge. Mirrors ``_connect_detour_horizontal`` with axes swapped.
        """
        x1 = src.cx
        entry_row = dst.y - 1  # always just above dst's own layer - see _render_once
        src_bottom = src.y + src.h

        canvas.line_v(x1, src_bottom, max(1, exit_row - src_bottom + 1))
        lo, hi = min(x1, lane_x), max(x1, lane_x)
        canvas.line_h(lo, exit_row, hi - lo + 1)
        lo2, hi2 = min(exit_row, entry_row), max(exit_row, entry_row)
        canvas.line_v(lane_x, lo2, hi2 - lo2 + 1)
        lo3, hi3 = min(lane_x, dst.cx), max(lane_x, dst.cx)
        canvas.line_h(lo3, entry_row, hi3 - lo3 + 1)

        arrow = (dst.cx, entry_row, "v") if edge.directed else None
        label = (lane_x + 1, min(exit_row, entry_row), edge.label) if edge.label else None
        return arrow, label

    @staticmethod
    def _connect_horizontal(canvas: Canvas, src: "_Box", dst: "_Box", edge: Edge):
        """Mark a horizontal (left-right style) orthogonal connector. See
        ``_connect_vertical`` for the return-value contract."""
        y1, y2 = src.cy, dst.cy
        going_right = dst.x >= src.x
        x1 = src.x + src.w if going_right else src.x - 1
        x2 = dst.x - 1 if going_right else dst.x + dst.w
        step = 1 if x2 >= x1 else -1
        arrow_char = ">" if step > 0 else "<"

        if y1 == y2:
            canvas.line_h(min(x1, x2), y1, abs(x2 - x1) + 1)
            arrow = (x2, y2, arrow_char) if edge.directed else None
            label = None
            if edge.label:
                lo, hi = min(x1, x2), max(x1, x2)
                gap = hi - lo
                if len(edge.label) + 2 <= gap:
                    # Fits inline with at least one clear column on each side.
                    text_x = lo + max(1, (gap - len(edge.label)) // 2)
                    text_x = min(text_x, hi - len(edge.label) - 1)
                    label = (max(text_x, lo + 1), y1, edge.label)
                else:
                    # Too long for the gap - put it on the row above instead
                    # of letting it run into whichever box is closer.
                    label = (lo, y1 - 1, edge.label)
            return arrow, label

        mid = x1 + step * (abs(x2 - x1) // 2) if abs(x2 - x1) > 1 else x1
        canvas.line_h(min(x1, mid), y1, abs(mid - x1) + 1)
        lo, hi = min(y1, y2), max(y1, y2)
        canvas.line_v(mid, lo, hi - lo + 1)
        canvas.line_h(min(mid, x2), y2, abs(x2 - mid) + 1)

        arrow = (x2, y2, arrow_char) if edge.directed else None
        label = None
        if edge.label:
            # Clamp into [x1, x2] - the gap between the two boxes, which is
            # guaranteed clear of *both* box rectangles at any row - rather
            # than anchoring off "mid" and potentially overrunning into dst.
            lo, hi = min(x1, x2), max(x1, x2)
            text_x = lo + max(1, (hi - lo - len(edge.label)) // 2)
            text_x = min(text_x, hi - len(edge.label) - 1)
            text_x = max(text_x, lo + 1)
            label = (text_x, (y1 + y2) // 2, edge.label)
        return arrow, label
