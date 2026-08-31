"""Command-line interface for hermes-toolkit.

This module provides a minimal CLI built on top of the standard
``argparse`` library. It exposes two commands:

* ``--version`` — print the package version and exit.
* ``greet`` — print a greeting for a given name.

The module is structured so that ``build_parser`` and ``main`` can be
imported and exercised independently from the unit tests.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

try:
    # When imported as part of the ``hermes_toolkit`` package.
    from hermes_toolkit.src import __version__
except ImportError:  # pragma: no cover - fallback for direct module use
    try:
        # Fallback when run as ``python -m src.cli`` from project root.
        from src import __version__
    except ImportError:
        # Last-resort fallback (e.g. executing the file directly).
        __version__ = "0.1.0"

__all__ = ["build_parser", "greet", "main"]


def greet(name: str) -> str:
    """Return a greeting message for ``name``.

    Parameters
    ----------
    name:
        The name of the person to greet. Should be a non-empty string.

    Returns
    -------
    str
        A greeting of the form ``"Hello, <name>!"``.
    """
    if not isinstance(name, str):  # pragma: no cover - defensive guard
        raise TypeError("name must be a string")
    return f"Hello, {name}!"


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level :class:`ArgumentParser`.

    The parser supports:

    * ``--version`` — print the package version and exit.
    * ``greet --name <NAME>`` — print a greeting for ``<NAME>``.

    Returns
    -------
    argparse.ArgumentParser
        A fully configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="hermes-toolkit",
        description="hermes-toolkit: a minimal Python CLI toolkit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"hermes-toolkit {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    greet_parser = subparsers.add_parser(
        "greet",
        help="Print a greeting for the given name.",
    )
    greet_parser.add_argument(
        "--name",
        required=True,
        help="Name of the person to greet.",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for the CLI.

    Parameters
    ----------
    argv:
        Optional sequence of argument strings. If ``None``, ``sys.argv[1:]``
        is used. This indirection makes the function easy to test.

    Returns
    -------
    int
        Exit code (``0`` on success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "greet":
        print(greet(args.name))
    else:
        # No subcommand given and no --version flag: print help.
        parser.print_help()

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
