"""Command-line interface for hermes-toolkit.

This module implements the minimal CLI entry point. It exposes two commands:

* ``--version`` — prints the package version and exits.
* ``greet --name <name>`` — prints a greeting for the given name.

The CLI is built on top of :mod:`argparse` so the module is also usable as a
library: callers can ``build_parser()`` and invoke individual ``cmd_*``
handlers programmatically (which is exactly what the unit tests do).
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from src import __version__

PROG_NAME = "hermes-toolkit"
DEFAULT_GREET_NAME = "World"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_version(_args: argparse.Namespace) -> str:
    """Return the version string for ``--version``.

    Parameters
    ----------
    _args : argparse.Namespace
        The parsed arguments. Unused; present for signature uniformity with
        other ``cmd_*`` handlers so that ``main()`` can dispatch generically.

    Returns
    -------
    str
        A string of the form ``"hermes-toolkit <version>"``.
    """
    return f"{PROG_NAME} {__version__}"


def cmd_greet(args: argparse.Namespace) -> str:
    """Build a greeting string for the user-supplied name.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments. Must expose ``name`` (a ``str``). If empty, the
        :data:`DEFAULT_GREET_NAME` placeholder is used.

    Returns
    -------
    str
        A greeting of the form ``"Hello, <name>! Welcome to hermes-toolkit."``.
    """
    name = (args.name or DEFAULT_GREET_NAME).strip() or DEFAULT_GREET_NAME
    return f"Hello, {name}! Welcome to {PROG_NAME}."


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level :class:`argparse.ArgumentParser`.

    The returned parser has two top-level features:

    * ``--version`` — prints the package version and exits.
    * ``greet`` subcommand — accepts an optional ``--name`` argument.

    Returns
    -------
    argparse.ArgumentParser
        A fully configured parser ready for ``parse_args``.
    """
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description="hermes-toolkit: a lightweight, extensible Python CLI toolkit.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the package version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command")

    greet_parser = subparsers.add_parser(
        "greet",
        help="Greet the named user.",
        description="Print a friendly greeting.",
    )
    greet_parser.add_argument(
        "--name",
        type=str,
        default=DEFAULT_GREET_NAME,
        help=f"Name to greet (default: {DEFAULT_GREET_NAME!r}).",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI.

    Parameters
    ----------
    argv : Sequence[str] | None
        Argument vector to parse. When ``None`` (the default) the arguments
        are taken from :obj:`sys.argv`. Provided mainly so tests can drive
        the CLI without mutating global state.

    Returns
    -------
    int
        Process exit code. ``0`` on success, non-zero on failure.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(cmd_version(args))
        return 0

    if args.command == "greet":
        print(cmd_greet(args))
        return 0

    # No command and no --version -> show help.
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())