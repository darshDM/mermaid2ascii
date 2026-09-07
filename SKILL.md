---
name: mermaid-ascii
description: Render Mermaid diagrams as ASCII/Unicode directly in the response. Use this whenever the user asks to create, show, render, or convert a Mermaid diagram for a terminal, CLI, text-only environment, or ASCII output.
---

# Mermaid ASCII

Render Mermaid source into an ASCII/Unicode diagram using the bundled renderer.

## REQUIRED BEHAVIOR

When the user asks you to create or show a Mermaid diagram:

1. Generate the Mermaid source.
2. Render it using the bundled CLI below.
3. Capture the complete stdout produced by the renderer.
4. Put the actual rendered stdout directly into your final response.
5. Do NOT merely say that the diagram was generated.
6. Do NOT summarize the diagram instead of showing it.
7. Do NOT tell the user to scroll through terminal/tool output.
8. The final response MUST contain the complete rendered ASCII/Unicode diagram in a fenced `text` code block.

The shell/tool output is not the user-facing answer. You must copy the renderer's stdout into the final answer.

## Rendering command

The renderer is bundled with this skill. Always use `${CLAUDE_SKILL_DIR}` so the command works regardless of the current working directory.

For inline Mermaid:

```bash
"${CLAUDE_SKILL_DIR}/bin/mermaid-ascii" -c 'flowchart TD
    A[Start] --> B{Valid?}
    B -->|Yes| C[Process]
    B -->|No| D[Reject]'
```

For multiline Mermaid, stdin is preferred:

```bash
printf '%s\n' 'flowchart TD
    A[Start] --> B[Process]
    B --> C[End]' | "${CLAUDE_SKILL_DIR}/bin/mermaid-ascii"
```

If a Mermaid file already exists:

```bash
"${CLAUDE_SKILL_DIR}/bin/mermaid-ascii" diagram.mmd
```

## After rendering

Inspect the command's stdout. The stdout is the diagram that must be shown to the user.

Return it exactly, preferably as:

```text
<complete renderer stdout here>
```

Do not replace it with phrases such as:

- "Diagram generated."
- "The diagram was rendered successfully."
- "You can scroll up to see the diagram."
- "I created the diagram using the skill."

If the renderer returns a diagram, the diagram itself MUST appear in the final response.

## Errors

If rendering fails:

1. Read the error from stderr.
2. Fix the Mermaid source.
3. Run the renderer again.
4. Do not claim success until actual diagram stdout has been produced.

## CLI notes

The bundled CLI accepts Mermaid from:

- a positional `.mmd` file
- stdin
- `-c` / `--code`

It also supports renderer options such as `--max-width` and `--full`.

Do not use unsupported options such as `--input` or `--output`.

## Python API

If Python integration is required, use the package's actual public API:

```python
from mermaid_ascii import convert

ascii_output = convert(mermaid_code)
print(ascii_output)
```

Do not use `render_diagram`; the package exposes `convert`.
