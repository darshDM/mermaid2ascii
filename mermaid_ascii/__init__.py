"""mermaid-ascii - render mermaid diagrams as plain ASCII/Unicode text.

Typical usage from Python (e.g. inside an agent tool call):

    from mermaid_ascii import convert
    print(convert(mermaid_source))

The library is organised around two small strategy hierarchies so new
diagram types can be added later without touching existing code:

    DiagramType (detector.py)
        -> ParserFactory   -> BaseParser subclass   -> Graph
        -> RendererFactory -> BaseRenderer subclass -> ASCII string
"""
from .detector import DiagramType, detect_diagram_type
from .exceptions import MermaidAsciiError, MermaidParseError, UnsupportedDiagramError
from .models import Direction, Edge, EdgeStyle, Graph, Node, NodeShape
from .parsers.factory import ParserFactory
from .renderers.factory import RendererFactory

__version__ = "0.1.0"

__all__ = [
    "convert",
    "DiagramType",
    "detect_diagram_type",
    "MermaidAsciiError",
    "MermaidParseError",
    "UnsupportedDiagramError",
    "Direction",
    "Edge",
    "EdgeStyle",
    "Graph",
    "Node",
    "NodeShape",
    "ParserFactory",
    "RendererFactory",
]


def convert(mermaid_text: str, *, max_width: int = None, direction: str = None) -> str:
    """Convert raw mermaid source text into a printable ASCII diagram.

    Args:
        mermaid_text: the mermaid source.
        max_width: if given, spacing is automatically tightened so every
            line of the result fits within this many columns (falls back to
            the tightest supported spacing if even that isn't enough).
            Pass e.g. ``shutil.get_terminal_size().columns`` to fit the
            caller's terminal.
        direction: optional override (``"TD"``, ``"LR"``, ``"BT"``, ``"RL"``)
            applied on top of whatever direction the source declares -
            useful for forcing a wide diagram into a narrower orientation.

    Raises:
        MermaidParseError: the text isn't valid/recognisable mermaid syntax.
        UnsupportedDiagramError: the diagram type is recognised but not
            implemented yet (only 'flowchart'/'graph' today).
    """
    diagram_type = detect_diagram_type(mermaid_text)
    parser = ParserFactory.get_parser(diagram_type)
    graph = parser.parse(mermaid_text)
    renderer = RendererFactory.get_renderer(diagram_type)
    return renderer.render(graph, max_width=max_width, direction=direction)
