# Contributing

## Testing

```bash
python -m unittest discover -s tests -v
```

Add tests for bug fixes and features (see `tests/test_flowchart.py`). Regression tests for layout bugs are especially valuable.

## Examples

Test changes against bundled examples:

```bash
for f in examples/*.mmd; do echo "=== $f ==="; python -m mermaid_ascii.cli --full "$f"; echo; done
```

## New diagram types

The architecture is additive. To add a diagram type (sequence, class, state, etc.):

1. Add `BaseParser` subclass in `mermaid_ascii/parsers/your_type.py`
2. Add `BaseRenderer` subclass in `mermaid_ascii/renderers/your_type_ascii.py`
3. Register both in their factory registries
4. Add header keyword to `_HEADER_MAP` in `detector.py` if needed

Nothing in `cli.py`, `__init__.py`, or existing renderers needs to change.

## Bug reports

Include:
- Exact mermaid source that failed
- Actual output (in code block to preserve spacing)
- What was expected (e.g. "boxes shouldn't overlap")

## Pull requests

- One fix or feature per PR
- Run test suite before opening
- Update README if user-facing behavior changed
