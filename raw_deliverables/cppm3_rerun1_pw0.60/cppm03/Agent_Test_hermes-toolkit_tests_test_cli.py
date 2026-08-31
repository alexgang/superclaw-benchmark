"""Unit tests for :mod:`src.cli`.

These tests exercise the two public entry points of the CLI:

1. ``--version`` returns a string of the form ``"hermes-toolkit <version>"``.
2. ``greet --name <name>`` returns ``"Hello, <name>! ..."``.
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from src import __version__
from src.cli import build_parser, cmd_greet, cmd_version, main


class TestVersionCommand(unittest.TestCase):
    """Verify the ``--version`` command."""

    def test_cmd_version_returns_program_and_version(self) -> None:
        args = build_parser().parse_args(["--version"])
        output = cmd_version(args)
        self.assertEqual(output, f"hermes-toolkit {__version__}")
        self.assertIn(__version__, output)
        self.assertTrue(output.startswith("hermes-toolkit "))


class TestGreetCommand(unittest.TestCase):
    """Verify the ``greet --name`` command."""

    def test_cmd_greet_with_custom_name(self) -> None:
        args = build_parser().parse_args(["greet", "--name", "Hermes"])
        output = cmd_greet(args)
        self.assertEqual(output, "Hello, Hermes! Welcome to hermes-toolkit.")

    def test_cmd_greet_uses_default_when_name_omitted(self) -> None:
        args = build_parser().parse_args(["greet"])
        output = cmd_greet(args)
        self.assertEqual(output, "Hello, World! Welcome to hermes-toolkit.")

    def test_main_routes_greet_to_stdout(self) -> None:
        """``main()`` should print the greeting and exit with code 0."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["greet", "--name", "Alice"])
        self.assertEqual(rc, 0)
        self.assertIn("Hello, Alice!", buf.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()