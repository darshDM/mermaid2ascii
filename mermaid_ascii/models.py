"""Core domain models shared by every parser and renderer.

Keeping these classes diagram-type-agnostic is what lets the rest of the
library follow the Open/Closed Principle: new diagram types add new
Parser/Renderer subclasses without touching Node/Edge/Graph at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Direction(Enum):
    TOP_DOWN = "TD"
    TOP_BOTTOM = "TB"
    BOTTOM_TOP = "BT"
    LEFT_RIGHT = "LR"
    RIGHT_LEFT = "RL"

    @classmethod
    def from_token(cls, token: str) -> "Direction":
        token = (token or "").strip().upper()
        for member in cls:
            if member.value == token:
                return member
        return cls.TOP_DOWN

    @property
    def is_horizontal(self) -> bool:
        return self in (Direction.LEFT_RIGHT, Direction.RIGHT_LEFT)

    @property
    def is_reversed(self) -> bool:
        """True when the root/source nodes should render at the bottom/right."""
        return self in (Direction.BOTTOM_TOP, Direction.RIGHT_LEFT)


class NodeShape(Enum):
    RECTANGLE = "rectangle"     # [text]
    ROUNDED = "rounded"         # (text)
    STADIUM = "stadium"         # ([text])
    CIRCLE = "circle"           # ((text))
    RHOMBUS = "rhombus"         # {text}          -> decision
    HEXAGON = "hexagon"         # {{text}}
    SUBROUTINE = "subroutine"   # [[text]]
    CYLINDER = "cylinder"       # [(text)]        -> database
    DEFAULT = "default"         # bare id, no declared shape


class EdgeStyle(Enum):
    SOLID = "solid"       # -->
    DOTTED = "dotted"     # -.->
    THICK = "thick"       # ==>
    OPEN = "open"         # ---  (no arrowhead)


@dataclass
class Node:
    id: str
    label: str
    shape: NodeShape = NodeShape.DEFAULT

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.id


@dataclass
class Edge:
    source: str
    target: str
    label: Optional[str] = None
    style: EdgeStyle = EdgeStyle.SOLID
    directed: bool = True


@dataclass
class Graph:
    """Diagram-agnostic container of nodes + edges produced by a parser."""

    direction: Direction = Direction.TOP_DOWN
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> Node:
        existing = self.nodes.get(node.id)
        if existing is not None:
            # A node may be referenced bare first (e.g. in an edge) and
            # given its real shape/label later (or vice versa) - keep
            # whichever declaration actually carries information.
            if existing.label == existing.id and node.label != node.id:
                existing.label = node.label
            if existing.shape == NodeShape.DEFAULT and node.shape != NodeShape.DEFAULT:
                existing.shape = node.shape
            return existing
        self.nodes[node.id] = node
        return node

    def add_edge(self, edge: Edge) -> None:
        self.add_node(Node(edge.source, edge.source))
        self.add_node(Node(edge.target, edge.target))
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def __len__(self) -> int:
        return len(self.nodes)
