"""Command-line interface for mermaid-ascii.

    mermaid-ascii diagram.mmd
    mermaid-ascii < diagram.mmd
    echo "flowchart TD; A-->B" | mermaid-ascii
    mermaid-ascii -c "flowchart TD\\n A-->B"

Prints only the rendered ASCII diagram to stdout (nothing else), so it is
safe to pipe directly into another tool or have an agent print verbatim.
All diagnostics go to stderr.

By default, output is automatically fitted to the terminal's width (spacing
is tightened as needed) when stdout is an interactive terminal. Use
--max-width to fit a specific width regardless, or --full to disable
fitting entirely (e.g. when piping to a file where full-size, evenly
spaced output is preferred).
"""
from __future__ import annotations

import argparse
import shutil
import sys

from . import __version__, convert
from .exceptions import MermaidAsciiError


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mermaid-ascii",
        description="Render mermaid diagrams as plain ASCII/Unicode text for terminals.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to a .mmd/.mermaid file. Omit to read from stdin.",
    )
    parser.add_argument(
        "-c", "--code",
        help="Mermaid source given directly on the command line instead of a file.",
    )
    parser.add_argument(
        "-d", "--direction",
        choices=["TD", "TB", "BT", "LR", "RL"],
        help="Override the diagram's direction regardless of what the source declares "
             "- e.g. force a wide LR chain into a narrower TD layout.",
    )
    parser.add_argument(
        "--max-width", type=int, metavar="N",
        help="Tighten spacing as needed so every line fits within N columns. "
             "Defaults to the current terminal width when stdout is a terminal.",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Disable width fitting entirely and render at full, evenly-spaced size "
             "(useful when redirecting output to a file).",
    )
    parser.add_argument(
        "--version", action="version", version=f"mermaid-ascii {__version__}",
    )
    return parser


def _read_input(args: argparse.Namespace) -> str:
    if args.code:
        return args.code.replace("\\n", "\n")
    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            return handle.read()
    if sys.stdin.isatty():
        raise SystemExit(
            "No input given. Pass a file, use -c '<mermaid code>', or pipe text via stdin."
        )
    return sys.stdin.read()


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    max_width = None
    if not args.full:
        if args.max_width:
            max_width = args.max_width
        elif sys.stdout.isatty():
            max_width = shutil.get_terminal_size(fallback=(80, 24)).columns

    try:
        source = _read_input(args)
        ascii_diagram = convert(source, max_width=max_width, direction=args.direction)
    except MermaidAsciiError as exc:
        print(f"mermaid-ascii: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"mermaid-ascii: could not read input: {exc}", file=sys.stderr)
        return 1

    print(ascii_diagram)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
