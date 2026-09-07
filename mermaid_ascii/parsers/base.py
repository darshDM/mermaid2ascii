from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Graph


class BaseParser(ABC):
    """Strategy interface every diagram-specific parser must implement.

    A parser's only job is: raw mermaid text in, a diagram-agnostic
    Graph out. It should not know or care how that Graph gets rendered.
    """

    @abstractmethod
    def parse(self, text: str) -> Graph:
        """Parse mermaid source text into a Graph. Raises MermaidParseError."""
        raise NotImplementedError
