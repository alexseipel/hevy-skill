#!/usr/bin/env python3
"""Offline tests for the repository checks, which gate every merge.

A check that reports the wrong thing is worse than no check, so the rules with
no judgement in them are exercised in both directions.

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VALIDATE = ROOT / "scripts" / "validate_skill.py"


def load(path: pathlib.Path, name: str):
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = previous


validate = load(VALIDATE, "validate_skill_under_test")


def frontmatter(*lines: str) -> str:
    return "---\n" + "\n".join(lines) + "\n---\n\n# Body\n"


class FrontmatterYamlTest(unittest.TestCase):
    """Claude Code parses frontmatter leniently, so this rule is the only
    thing standing between an unquoted scalar and a strict parser refusing
    the file (skill-authoring/references/frontmatter.md)."""

    def setUp(self):
        validate.failures.clear()
        self.path = ROOT / "skills" / "hevy-api" / "SKILL.md"

    def run_rule(self, text: str) -> list[str]:
        validate.check_frontmatter_yaml(self.path, text)
        return list(validate.failures)

    def test_an_unquoted_colon_space_is_rejected(self):
        text = frontmatter("name: x", "description: Call the API: workouts and sets.")
        # Bound once: the rule appends, so calling it twice would count twice.
        found = self.run_rule(text)
        self.assertEqual(len(found), 1)
        self.assertIn("description", found[0])

    def test_an_unquoted_trailing_comment_is_rejected(self):
        self.assertEqual(len(self.run_rule(frontmatter("name: x #1"))), 1)

    def test_quoting_it_is_accepted(self):
        text = frontmatter("name: x", 'description: "Call the API: workouts and sets."')
        self.assertEqual(self.run_rule(text), [])

    def test_a_flow_collection_is_accepted(self):
        """metadata is a map and allowed-tools a list in the open standard, and
        both are valid YAML unquoted."""
        text = frontmatter("name: x", "metadata: {tier: 1}",
                           "allowed-tools: [Read, Bash]")
        self.assertEqual(self.run_rule(text), [])

    def test_a_url_is_accepted(self):
        """The separator is a colon and a space, so :// carries no ambiguity."""
        self.assertEqual(self.run_rule(frontmatter("homepage: https://a.example")), [])


class SecretScanTest(unittest.TestCase):
    def setUp(self):
        validate.failures.clear()

    def scan(self, text: str) -> list[str]:
        # A real file, because check_secrets reports paths relative to ROOT.
        with tempfile.NamedTemporaryFile("w", suffix=".py", dir=ROOT) as handle:
            handle.write(text)
            handle.flush()
            validate.check_secrets(pathlib.Path(handle.name))
        return list(validate.failures)

    def test_a_quoted_header_leaks(self):
        """The shape the client itself writes: a quoted header name, then a key.

        Assembled here rather than written out, because a literal one would
        make this file fail the very scan it is testing."""
        uuid = "-".join(["a" * 8, "b" * 4, "c" * 4, "d" * 4, "e" * 12])
        found = self.scan('headers = {"api-key": "%s"}' % uuid)
        self.assertEqual(len(found), 1)

    def test_the_environment_variable_does_not(self):
        self.assertEqual(self.scan('{"api-key": "$HEVY_API_KEY"}'), [])


if __name__ == "__main__":
    unittest.main()
