#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/mermaid-ascii}"
rm -rf "$SKILL_DIR"
rm -f "$HOME/.local/bin/mermaid-ascii"

echo "✓ Mermaid ASCII removed"
