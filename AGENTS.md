# Working on mermaid-ascii

## Testing

```bash
python -m unittest discover -s tests -v
```

All 23 tests should pass. Run before and after changes.

## Code layout

- `mermaid_ascii/__init__.py` - public API: `convert(text, *, max_width=None, direction=None)`
- `mermaid_ascii/models.py` - `Node`, `Edge`, `Graph`, `Direction`, `NodeShape` domain objects
- `mermaid_ascii/detector.py` - diagram type detection
- `mermaid_ascii/parsers/` - parser strategy, registry, flowchart parser
- `mermaid_ascii/renderers/` - renderer strategy, registry, flowchart ASCII renderer
  - `canvas.py` - ASCII grid with bitmask line tracking → box-drawing chars
- `mermaid_ascii/cli.py` - CLI wrapper
- `mermaid_ascii/exceptions.py` - `MermaidParseError`, `UnsupportedDiagramError`

## Layout changes (critical)

Changes to `renderers/flowchart_ascii.py` can silently corrupt box text if routing is wrong. Always:

1. Run full test suite (especially `test_dense_pipeline_with_rollback_loops_does_not_corrupt_boxes`)
2. Render a dense example with cycles/back-edges (e.g. `examples/architecture.mmd`)
3. Visually confirm all node labels are intact and unbroken
4. Read the routing logic comment at the top of `_render_once()` — understand why current routing is collision-free, and verify your change preserves it

## Constraints

- Zero runtime dependencies (core lib uses stdlib only)
- `mcp` extra is optional (try/except import in `mcp_server.py`)
- Add regression tests for bugs, don't just fix inline
- Keep docstrings short (summary line + Args/Returns where clarity helps)
