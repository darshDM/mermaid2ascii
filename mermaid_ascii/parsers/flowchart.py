"""Parser for mermaid ``flowchart`` / ``graph`` diagrams.

Supported syntax (deliberately a practical subset, not the full mermaid
grammar):

    flowchart TD
        A[Start] --> B{Valid?}
        B -->|Yes| C(Process)
        B -- No --> D[[Reject]]
        C --> E((Done))

* Directions: TD, TB, BT, LR, RL
* Node shapes: [rect], (rounded), ([stadium]), ((circle)),
  {rhombus/decision}, {{hexagon}}, [[subroutine]], [(cylinder)]
* Edge styles: -->, ---, -.->. -.- , ==>, ===
* Edge labels: ``A -->|label| B`` and ``A -- label --> B``
* Chained edges on one line: ``A --> B --> C``
* ``subgraph`` / ``end`` blocks are flattened (their nodes/edges are kept,
  the grouping itself is not rendered - see README limitations)
* ``style`` / ``classDef`` / ``class`` / ``click`` / ``linkStyle`` lines and
  ``%%`` comments are ignored
"""
from __future__ import annotations

import re
from typing import List, Optional

from ..exceptions import MermaidParseError
from ..models import Direction, Edge, EdgeStyle, Graph, Node, NodeShape
from .base import BaseParser

# Order matters: more specific (longer) bracket pairs must be tried before
# the shorter ones they contain, e.g. `((` before `(`.
_SHAPE_PATTERNS = [
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)\(\((?P<label>.*)\)\)$"), NodeShape.CIRCLE),
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)\(\[(?P<label>.*)\]\)$"), NodeShape.STADIUM),
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)\[\((?P<label>.*)\)\]$"), NodeShape.CYLINDER),
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)\{\{(?P<label>.*)\}\}$"), NodeShape.HEXAGON),
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)\[\[(?P<label>.*)\]\]$"), NodeShape.SUBROUTINE),
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)\{(?P<label>.*)\}$"), NodeShape.RHOMBUS),
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)\((?P<label>.*)\)$"), NodeShape.ROUNDED),
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)\[(?P<label>.*)\]$"), NodeShape.RECTANGLE),
    (re.compile(r"^(?P<id>[A-Za-z0-9_\-]+)$"), NodeShape.DEFAULT),
]

_ARROW_TO_STYLE = {
    "-->": EdgeStyle.SOLID,
    "---": EdgeStyle.OPEN,
    "-.->": EdgeStyle.DOTTED,
    "-.-": EdgeStyle.OPEN,
    "==>": EdgeStyle.THICK,
    "===": EdgeStyle.OPEN,
}

_SKIP_PREFIXES = (
    "subgraph", "end", "style ", "style\t", "classdef", "class ",
    "click", "linkstyle", "%%",
)


class FlowchartParser(BaseParser):
    # longest tokens first so e.g. "-.->" isn't mistakenly matched as "-.-" + ">"
    _ARROW_RE = re.compile(r"(-\.->|-\.-|==>|===|-->|---)(?:\s*\|([^|]*)\|)?")
    _INLINE_LABEL_RE = re.compile(r"--\s*([^>\-][^\n]*?)\s*-->")
    _HEADER_RE = re.compile(r"^(flowchart|graph)\s+([A-Za-z]{2})\b", re.IGNORECASE)

    def parse(self, text: str) -> Graph:
        if not text or not text.strip():
            raise MermaidParseError("Empty flowchart definition.")

        graph = Graph(direction=Direction.TOP_DOWN)
        header_seen = False

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if not header_seen:
                match = self._HEADER_RE.match(line)
                if match:
                    graph.direction = Direction.from_token(match.group(2))
                    header_seen = True
                    continue
                # tolerate missing header line, default to TD
                header_seen = True

            lower = line.lower()
            if line.startswith("%%") or lower.startswith(_SKIP_PREFIXES):
                continue

            # normalise `A -- some label --> B` into `A -->|some label| B`
            line = self._INLINE_LABEL_RE.sub(lambda m: f"-->|{m.group(1)}|", line)
            self._parse_line(line, graph)

        if not graph.nodes:
            raise MermaidParseError(
                "No nodes found - is this valid flowchart/graph syntax?"
            )
        return graph

    def _parse_line(self, line: str, graph: Graph) -> None:
        matches = list(self._ARROW_RE.finditer(line))

        if not matches:
            node = self._parse_node_expr(line)
            if node:
                graph.add_node(node)
            return

        segments: List[str] = []
        pos = 0
        for m in matches:
            segments.append(line[pos:m.start()].strip())
            pos = m.end()
        segments.append(line[pos:].strip())

        nodes = [self._parse_node_expr(seg) for seg in segments]
        for i, m in enumerate(matches):
            src, dst = nodes[i], nodes[i + 1]
            if src is None or dst is None:
                continue
            arrow_token, label = m.group(1), m.group(2)
            style = _ARROW_TO_STYLE.get(arrow_token, EdgeStyle.SOLID)
            graph.add_node(src)
            graph.add_node(dst)
            graph.add_edge(Edge(
                source=src.id,
                target=dst.id,
                label=label.strip() if label else None,
                style=style,
                directed=style != EdgeStyle.OPEN,
            ))

    def _parse_node_expr(self, expr: str) -> Optional[Node]:
        expr = expr.strip()
        if not expr:
            return None
        for pattern, shape in _SHAPE_PATTERNS:
            m = pattern.match(expr)
            if m:
                node_id = m.group("id")
                label = m.groupdict().get("label")
                return Node(id=node_id, label=(label if label else node_id), shape=shape)
        # Fallback: strip stray punctuation and treat the remainder as an id.
        cleaned = re.sub(r"[^A-Za-z0-9_\-]", "", expr)
        if not cleaned:
            return None
        return Node(id=cleaned, label=cleaned)
