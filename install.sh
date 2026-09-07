#!/usr/bin/env bash
set -euo pipefail

# Mermaid2ASCII installer for Claude Code.
# Usage (after replacing YOUR_GITHUB_USERNAME in this file):
#   curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/mermaid2ascii/main/install.sh | bash

REPO="${MERMAID2ASCII_REPO:-https://github.com/YOUR_GITHUB_USERNAME/mermaid2ascii}"
REF="${MERMAID2ASCII_REF:-main}"
SKILL_NAME="mermaid-ascii"
SKILL_DIR="${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/$SKILL_NAME}"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: Python 3 is required but was not found." >&2
  exit 1
fi

PYTHON="$(command -v python3)"
PY_VERSION="$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

case "$PY_VERSION" in
  3.[89]|3.10|3.11|3.12|3.13|3.14) ;;
  *)
    echo "Error: Python 3.8+ is required (found $PY_VERSION)." >&2
    exit 1
    ;;
esac

echo "Installing $SKILL_NAME..."

echo "  Repository: $REPO"
echo "  Skill dir:  $SKILL_DIR"

echo "  Python:     $PY_VERSION"

mkdir -p "$(dirname "$SKILL_DIR")"
rm -rf "$SKILL_DIR"
mkdir -p "$SKILL_DIR"

ARCHIVE_URL="${REPO%/}/archive/refs/heads/${REF}.tar.gz"

if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$ARCHIVE_URL" -o "$TMP_DIR/repo.tar.gz"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP_DIR/repo.tar.gz" "$ARCHIVE_URL"
else
  echo "Error: curl or wget is required." >&2
  exit 1
fi

tar -xzf "$TMP_DIR/repo.tar.gz" -C "$TMP_DIR"
SOURCE_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

cp "$SOURCE_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
cp -R "$SOURCE_DIR/mermaid_ascii" "$SKILL_DIR/mermaid_ascii"
cp "$SOURCE_DIR/pyproject.toml" "$SKILL_DIR/pyproject.toml"
cp "$SOURCE_DIR/README.md" "$SKILL_DIR/README.md"

# Keep the runtime self-contained. The current renderer has zero third-party
# runtime dependencies, so we don't need pip or a package index during install.
# A tiny venv still gives the skill its own Python interpreter and leaves room
# for future dependencies without changing the agent-facing command.
"$PYTHON" -m venv --without-pip "$SKILL_DIR/.venv"

mkdir -p "$SKILL_DIR/bin"
cat > "$SKILL_DIR/bin/mermaid-ascii" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export PYTHONPATH="$SKILL_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec "$SKILL_DIR/.venv/bin/python" -m mermaid_ascii.cli "$@"
WRAPPER
chmod +x "$SKILL_DIR/bin/mermaid-ascii"

# Claude Code also benefits from having the command on PATH for manual use.
mkdir -p "$HOME/.local/bin"
ln -sfn "$SKILL_DIR/bin/mermaid-ascii" "$HOME/.local/bin/mermaid-ascii"

# Remove packaging metadata that is no longer needed at runtime.
rm -f "$SKILL_DIR/pyproject.toml" "$SKILL_DIR/README.md"

echo
echo "✓ Mermaid ASCII installed for Claude Code"
echo "✓ Skill:  $SKILL_DIR"
echo "✓ CLI:    $HOME/.local/bin/mermaid-ascii"
echo
echo "Restart Claude Code, then ask it to render a Mermaid flowchart."
echo
echo "Manual test:"
echo "  echo 'flowchart TD; A[Start] --> B[End]' | $HOME/.local/bin/mermaid-ascii"
