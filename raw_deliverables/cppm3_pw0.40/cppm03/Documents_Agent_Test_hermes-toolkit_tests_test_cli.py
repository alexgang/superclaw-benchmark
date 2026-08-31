"""Unit tests for the hermes-toolkit CLI."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from src.cli import build_parser, greet, main


class TestVersionFlag(unittest.TestCase):
    def test_version_flag_prints_version(self):
        parser = build_parser()
        with self.assertRaises(SystemExit) as cm:
            with mock.patch("sys.stdout", new_callable=io.StringIO) as fake_out:
                with redirect_stdout(fake_out):
                    parser.parse_args(["--version"])
        self.assertEqual(cm.exception.code, 0)


class TestGreetCommand(unittest.TestCase):
    def test_greet_returns_expected_message(self):
        self.assertEqual(greet("Alice"), "Hello, Alice! Welcome to hermes-toolkit.")

    def test_main_greet_prints_greeting(self):
        with mock.patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            with redirect_stdout(fake_out):
                rc = main(["greet", "--name", "Bob"])
        self.assertEqual(rc, 0)
        self.assertIn("Hello, Bob!", fake_out.getvalue())


if __name__ == "__main__":
    unittest.main()