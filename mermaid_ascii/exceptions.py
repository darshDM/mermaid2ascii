class MermaidAsciiError(Exception):
    """Base class for every error this library raises."""


class MermaidParseError(MermaidAsciiError):
    """Raised when input text cannot be parsed as valid mermaid syntax."""


class UnsupportedDiagramError(MermaidAsciiError):
    """Raised when the diagram type is recognised but has no parser/renderer yet."""
