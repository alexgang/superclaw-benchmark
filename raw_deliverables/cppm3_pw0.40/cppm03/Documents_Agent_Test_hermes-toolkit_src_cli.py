"""Command-line interface for hermes-toolkit.

Supports:
  hermes-toolkit --version
  hermes-toolkit greet --name <name>
"""
from __future__ import annotations

import argparse
import sys

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser with --version and the
        ``greet`` sub-command.
    """
    parser = argparse.ArgumentParser(
        prog="hermes-toolkit",
        description="hermes-toolkit: a lightweight open-source toolkit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"hermes-toolkit {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    greet = subparsers.add_parser("greet", help="Greet a person by name.")
    greet.add_argument(
        "--name",
        required=True,
        help="Name of the person to greet.",
    )
    return parser


def greet(name: str) -> str:
    """Return a greeting message for ``name``.

    Args:
        name: The person's name to greet.

    Returns:
        A friendly greeting string.
    """
    return f"Hello, {name}! Welcome to hermes-toolkit."


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI.

    Args:
        argv: Optional argument vector. When ``None``, ``sys.argv[1:]`` is used.

    Returns:
        Process exit code (0 on success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "greet":
        print(greet(args.name))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())