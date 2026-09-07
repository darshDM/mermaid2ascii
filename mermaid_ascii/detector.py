"""Figures out which kind of mermaid diagram a block of text declares.

This is deliberately separate from any single parser so that adding a new
diagram type is a two-step, additive change: register a header keyword here,
register a Parser/Renderer pair in their factories. Nothing here needs to
change to support flowchart, sequence, class, etc.
"""
from __future__ import annotations

from enum import Enum

import re

from .exceptions import MermaidParseError


class DiagramType(Enum):
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    CLASS = "class"
    STATE = "state"
    ER = "er"
    GANTT = "gantt"
    PIE = "pie"
    JOURNEY = "journey"
    UNKNOWN = "unknown"


# mermaid header keyword (lowercased, first token of the first real line) -> type
_HEADER_MAP = {
    "flowchart": DiagramType.FLOWCHART,
    "graph": DiagramType.FLOWCHART,
    "sequencediagram": DiagramType.SEQUENCE,
    "classdiagram": DiagramType.CLASS,
    "statediagram": DiagramType.STATE,
    "statediagram-v2": DiagramType.STATE,
    "erdiagram": DiagramType.ER,
    "gantt": DiagramType.GANTT,
    "pie": DiagramType.PIE,
    "journey": DiagramType.JOURNEY,
}


_ARROW_HINT_RE = re.compile(r"-->|---|-\.->|-\.-|==>|===")


def detect_diagram_type(text: str) -> DiagramType:
    """Return the DiagramType declared by the first non-empty, non-comment line.

    Falls back to FLOWCHART (without requiring the header line) if the text
    doesn't declare a recognised diagram type but clearly contains flowchart
    style arrows - handy for callers that pass a bare edge list.
    """
    first_token = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%%"):
            continue
        first_token = line.split()[0].lower()
        break

    if first_token is None:
        raise MermaidParseError("Input is empty - nothing to detect.")

    detected = _HEADER_MAP.get(first_token)
    if detected is not None:
        return detected
    if _ARROW_HINT_RE.search(text):
        return DiagramType.FLOWCHART
    return DiagramType.UNKNOWN
