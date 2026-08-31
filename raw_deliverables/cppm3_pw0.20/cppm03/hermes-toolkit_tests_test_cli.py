"""Unit tests for ``hermes-toolkit`` CLI."""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Make ``src`` importable regardless of how the tests are invoked.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.cli import build_parser, greet, main  # noqa: E402


class TestGreetHelper(unittest.TestCase):
    """Direct tests for the ``greet`` helper function."""

    def test_greet_helper_returns_greeting(self) -> None:
        self.assertEqual(greet("World"), "Hello, World!")

    def test_greet_helper_chinese_name(self) -> None:
        self.assertEqual(greet("张三"), "Hello, 张三!")


class TestBuildParser(unittest.TestCase):
    """Tests for the argument parser construction."""

    def test_version_action_registered(self) -> None:
        parser = build_parser()
        # The --version action should be present.
        self.assertTrue(any("--version" in a.option_strings for a in parser._actions))

    def test_greet_subcommand_registered(self) -> None:
        parser = build_parser()
        # Sanity-check that subparsers are wired up.
        self.assertIsNotNone(parser._subparsers)


class TestVersionFlag(unittest.TestCase):
    """Verify ``--version`` triggers ``SystemExit`` with the version on stdout."""

    def test_version(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                main(["--version"])
        # argparse exits with code 0 on --version.
        self.assertEqual(cm.exception.code, 0)
        # The version string must be on stdout (argparse default for --version).
        self.assertIn("hermes-toolkit 0.1.0", buf.getvalue())


class TestGreetCommand(unittest.TestCase):
    """Verify ``greet --name <NAME>`` writes the expected greeting."""

    def test_greet(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main(["greet", "--name", "World"])
        self.assertEqual(exit_code, 0)
        self.assertIn("Hello, World!", buf.getvalue())

    def test_greet_missing_name_errors(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            with self.assertRaises(SystemExit):
                main(["greet"])
        self.assertIn("--name", err.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
