"""Factory/registry that maps a DiagramType to its Parser implementation.

Adding support for a new diagram type later means: write a new BaseParser
subclass, then add one ``ParserFactory.register(...)`` call. Nothing else
in the codebase (cli.py, renderers, __init__.py) needs to change.
"""
from __future__ import annotations

from typing import Dict, Type

from ..detector import DiagramType
from ..exceptions import UnsupportedDiagramError
from .base import BaseParser
from .flowchart import FlowchartParser


class ParserFactory:
    _registry: Dict[DiagramType, Type[BaseParser]] = {}

    @classmethod
    def register(cls, diagram_type: DiagramType, parser_cls: Type[BaseParser]) -> None:
        cls._registry[diagram_type] = parser_cls

    @classmethod
    def get_parser(cls, diagram_type: DiagramType) -> BaseParser:
        parser_cls = cls._registry.get(diagram_type)
        if parser_cls is None:
            supported = ", ".join(t.value for t in cls._registry) or "none"
            raise UnsupportedDiagramError(
                f"No parser registered yet for diagram type '{diagram_type.value}'. "
                f"Currently supported: {supported}."
            )
        return parser_cls()

    @classmethod
    def supported_types(cls):
        return list(cls._registry.keys())


ParserFactory.register(DiagramType.FLOWCHART, FlowchartParser)
