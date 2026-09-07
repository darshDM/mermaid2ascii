from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Graph


class BaseRenderer(ABC):
    """Strategy interface every diagram-specific renderer must implement."""

    @abstractmethod
    def render(self, graph: Graph, **options) -> str:
        """Render a Graph into a plain-text ASCII string ready to print.

        ``**options`` lets a specific renderer accept extra knobs (e.g. the
        flowchart renderer's ``max_width``/``direction``) without forcing
        every other renderer to have the same parameters.
        """
        raise NotImplementedError
