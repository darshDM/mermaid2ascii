# mermaid-ascii

Render [mermaid](https://mermaid.js.org/) diagrams as plain ASCII/Unicode text for terminals and agents.

```
flowchart TD
    A[Start] --> B{Valid?}
    B -->|Yes| C[Process]
    B -->|No| D[Reject]
    C --> E[Done]
    D --> E
```

Renders as:

```
             ┌───────┐
             │ Start │
             └───────┘
                 │
                 v
        /────────────────\
        |    Valid?      |
        \────────────────/
                 │
           Yes   │   No
        ┌────────┴─────────┐
        │                  │
        v                  v
┌──────────────┐   ┌──────────────┐
│   Process    │   │   Reject     │
└──────────────┘   └──────────────┘
        │                  │
        └────────┬─────────┘
                 │
                 v
             ┌──────┐
             │ Done │
             └──────┘
```

## Quick start

Clone into your skill directory:

```bash
# Claude Code / Claude.ai - project level
git clone https://github.com/anthropics/mermaid2ascii.git .claude/skills/mermaid-ascii

# Claude Code - personal
git clone https://github.com/anthropics/mermaid2ascii.git ~/.claude/skills/mermaid-ascii
```

That's it. No install needed.

## Usage

### As a skill

Use in any agent prompt: "create a flowchart showing..." The agent renders it directly in the response.

### CLI (if installed)

```bash
python3 -m mermaid_ascii.cli diagram.mmd
python3 -m mermaid_ascii.cli -c "flowchart TD; A[Start] --> B[End]"
cat diagram.mmd | python3 -m mermaid_ascii.cli
```

### Python API

```python
from mermaid_ascii import convert

diagram = convert("flowchart TD; A[Start] --> B[End]")
print(diagram)
```

## Supported (flowcharts only)

| Feature | Status |
|---------|--------|
| Rectangle, rounded, stadium, circle, decision, hexagon shapes | ✅ |
| Solid, dotted, thick arrows | ✅ |
| Edge labels | ✅ |
| Cycles & skip edges (auto-routed) | ✅ |
| TD, TB, BT, LR, RL directions | ✅ |
| Width fitting (`--max-width`, `--direction`) | ✅ |
| Subgraph syntax | ✅ (flattened — boxes not drawn) |

## Architecture

Parser → Graph → Renderer

Each diagram type (flowchart, sequence, class, etc.) is self-contained:

- Add parser in `parsers/`
- Add renderer in `renderers/`
- Register in factories
- Done

See `AGENTS.md` for development.

## License

MIT

## One-command Claude Code install

The project includes a self-contained installer for Claude Code. Replace `YOUR_GITHUB_USERNAME` in `install.sh` once after publishing the repository, then users can install the skill with:

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/mermaid2ascii/main/install.sh | bash
```

The installer:

- installs the skill to `~/.claude/skills/mermaid-ascii`
- keeps the Python runtime inside the skill at `~/.claude/skills/mermaid-ascii/.venv`
- exposes `mermaid-ascii` at `~/.local/bin/mermaid-ascii`
- does not require pip or third-party packages for the current zero-dependency renderer

To install from a fork without editing `install.sh`, set `MERMAID2ASCII_REPO`:

```bash
MERMAID2ASCII_REPO=https://github.com/YOUR_GITHUB_USERNAME/mermaid2ascii \
curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/mermaid2ascii/main/install.sh | bash
```

After installation, restart Claude Code. The skill can invoke the bundled renderer regardless of the current working directory.

### Uninstall

```bash
rm -rf ~/.claude/skills/mermaid-ascii
rm -f ~/.local/bin/mermaid-ascii
```
