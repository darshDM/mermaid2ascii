from __future__ import annotations

from typing import Dict, Type

from ..detector import DiagramType
from ..exceptions import UnsupportedDiagramError
from .base import BaseRenderer
from .flowchart_ascii import FlowchartASCIIRenderer


class RendererFactory:
    _registry: Dict[DiagramType, Type[BaseRenderer]] = {}

    @classmethod
    def register(cls, diagram_type: DiagramType, renderer_cls: Type[BaseRenderer]) -> None:
        cls._registry[diagram_type] = renderer_cls

    @classmethod
    def get_renderer(cls, diagram_type: DiagramType) -> BaseRenderer:
        renderer_cls = cls._registry.get(diagram_type)
        if renderer_cls is None:
            supported = ", ".join(t.value for t in cls._registry) or "none"
            raise UnsupportedDiagramError(
                f"No renderer registered yet for diagram type '{diagram_type.value}'. "
                f"Currently supported: {supported}."
            )
        return renderer_cls()

    @classmethod
    def supported_types(cls):
        return list(cls._registry.keys())


RendererFactory.register(DiagramType.FLOWCHART, FlowchartASCIIRenderer)
