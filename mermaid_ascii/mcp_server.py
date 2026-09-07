"""MCP server exposing mermaid-ascii as a tool for any MCP-compatible agent
(Claude Code, Claude Desktop, Kiro, Cursor, Windsurf, etc.).

Install the optional dependency group first:

    pip install "mermaid-ascii[mcp]"

Run directly to sanity-check it starts (it will sit waiting for an MCP
client to talk to it over stdio - Ctrl+C to stop):

    mermaid-ascii-mcp

Point any MCP-compatible agent at this command instead of running it
yourself - see the README's "Using with AI coding agents" section for
copy-paste config snippets per agent.
"""
from __future__ import annotations

from typing import Optional

from . import convert
from .exceptions import MermaidAsciiError

try:
    from mcp.server.fastmcp import FastMCP as _MCPServerCls  # mcp SDK 1.x
except ImportError:
    try:
        from mcp.server.mcpserver import MCPServer as _MCPServerCls  # mcp SDK 2.x+
    except ImportError as exc:  # pragma: no cover - exercised only when the
        # optional dependency group hasn't been installed
        raise ImportError(
            "The MCP server requires the optional 'mcp' dependency. "
            "Install it with: pip install \"mermaid-ascii[mcp]\""
        ) from exc

mcp = _MCPServerCls("mermaid-ascii")


@mcp.tool()
def render_mermaid_ascii(
    mermaid_source: str,
    direction: Optional[str] = None,
    max_width: Optional[int] = None,
) -> str:
    """Render mermaid diagram source as a plain ASCII/Unicode text diagram.

    Currently supports flowchart/graph diagrams. The result is ready to
    print or display verbatim in a terminal - no further processing needed.

    Args:
        mermaid_source: The mermaid diagram source, e.g.
            "flowchart TD\\nA[Start] --> B{Ok?}\\nB -->|Yes| C[Done]".
        direction: Optional layout override - one of "TD", "TB", "BT",
            "LR", "RL" - applied regardless of what the source declares.
            Useful for forcing a wide diagram into a narrower orientation.
        max_width: Optional column width to fit the diagram to. Spacing is
            tightened automatically as needed. Leave unset for the default,
            evenly-spaced layout.
    """
    try:
        return convert(mermaid_source, direction=direction, max_width=max_width)
    except MermaidAsciiError as exc:
        return f"Error: {exc}"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
