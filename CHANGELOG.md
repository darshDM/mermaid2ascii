# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - Unreleased

Initial working prototype.

### Added
- Flowchart/graph parsing: all standard node shapes, edge styles, inline
  and pipe-form labels, chained edges, `subgraph`/`style`/comment tolerance.
- Layered ASCII layout engine with a bitmask-based line-merging canvas, so
  branch/merge points render as proper `┬`/`┴`/`┼` junctions.
- Cycle- and skip-layer-edge routing that travels only through the gap
  rows/columns between layers and a shared outer lane, both provably clear
  of box content - detours never overwrite another box's text, even in
  dense diagrams with many stacked siblings and back-edges.
- CLI (`mermaid-ascii`) with file/stdin/`-c` input, automatic terminal-width
  fitting (progressive spacing tightening), `--max-width`, `--full`, and
  `--direction` override.
- Python API: `mermaid_ascii.convert(text, *, max_width=None, direction=None)`.
- MCP server (`mermaid-ascii-mcp`, optional `mcp` extra) exposing
  `render_mermaid_ascii` as a tool for any MCP-compatible agent.
- Test suite covering the parser, renderer, and known regression cases.
