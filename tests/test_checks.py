#!/usr/bin/env python3
"""Offline tests for the repository checks, which gate every merge.

A check that reports the wrong thing is worse than no check, so the rules with
no judgement in them are exercised in both directions.

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

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
builder = load(ROOT / "scripts" / "build_corrected_spec.py", "spec_builder_under_test")


def frontmatter(*lines: str) -> str:
    return "---\n" + "\n".join(lines) + "\n---\n\n# Body\n"


class CorrectedSpecTest(unittest.TestCase):
    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return json.loads(builder.build(False))

    def test_current_upstream_builds_and_preserves_new_fields(self):
        document = self.build()
        schemas = document["components"]["schemas"]
        self.assertIn("superset_id", schemas["Exercise"]["properties"])
        self.assertNotIn("supersets_id", schemas["Exercise"]["properties"])
        self.assertIn("thumbnail_url", schemas["ExerciseTemplate"]["properties"])
        self.assertTrue({"username", "weight_unit", "distance_unit", "is_pro"}
                        <= schemas["UserInfo"]["properties"].keys())
        for item in document["paths"].values():
            params = item.get("get", {}).get("parameters", [])
            for param in params:
                if param["name"] == "pageSize":
                    self.assertEqual(param["schema"]["default"], param["schema"]["maximum"])

    def test_routine_writes_keep_the_object_upstream_documents(self):
        """Both answered with an object on 2026-11-18, so no patch touches them."""
        document = self.build()
        for route, method, status in (("/v1/routines", "post", "201"),
                                      ("/v1/routines/{routineId}", "put", "200")):
            schema = document["paths"][route][method]["responses"][status]["content"]["application/json"]["schema"]
            self.assertEqual(schema["properties"]["routine"],
                             {"$ref": "#/components/schemas/Routine"})

    def test_a_routine_update_no_longer_claims_a_null_rep_range(self):
        document = self.build()
        schemas = document["components"]["schemas"]
        self.assertFalse(schemas["PutRoutinesRequestSet"]["properties"]["rep_range"]["nullable"])
        self.assertTrue(schemas["PostRoutinesRequestSet"]["properties"]["rep_range"]["nullable"])

    def test_a_new_upstream_fix_still_fails_instead_of_silently_skipping(self):
        upstream = json.loads(builder.UPSTREAM.read_text())
        upstream["components"]["schemas"]["BodyMeasurement"]["properties"]["id"] = {
            "type": "integer"}
        patches = {p["id"]: p for p in json.loads(builder.PATCHES.read_text())["patches"]}
        with self.assertRaisesRegex(builder.PatchError, "measurement-id.*already exists"):
            builder.apply_patch(upstream, patches["measurement-id"])

    def test_upstream_already_declares_its_server_and_both_security_schemes(self):
        """The four patches that added these went when Hevy did it, and a
        regression upstream should fail here rather than in a generated client."""
        upstream = json.loads(builder.UPSTREAM.read_text())
        self.assertEqual(upstream["servers"], [{"url": "https://api.hevyapp.com"}])
        self.assertEqual(upstream["security"], [{"apiKey": []}, {"oauth": []}])
        for item in upstream["paths"].values():
            for operation in item.values():
                names = [p["name"] for p in operation.get("parameters", [])]
                self.assertNotIn("api-key", names)

    def test_a_moved_spec_fails_with_a_message_instead_of_a_traceback(self):
        gone = urllib.error.HTTPError(builder.SPEC_URL, 404, "Not Found", None,
                                      io.BytesIO(b""))
        self.addCleanup(gone.close)
        with mock.patch.object(builder.urllib.request, "urlopen", side_effect=gone):
            with self.assertRaisesRegex(builder.PatchError, "may have moved"):
                builder.fetch_upstream()
        not_a_spec = io.BytesIO(b'{"error": "nothing here"}')
        with mock.patch.object(builder.urllib.request, "urlopen", return_value=not_a_spec):
            with self.assertRaisesRegex(builder.PatchError, "OpenAPI document"):
                builder.fetch_upstream()

    def test_fetch_rebuilds_from_the_downloaded_spec(self):
        upstream = json.loads(builder.UPSTREAM.read_text())
        upstream["info"]["title"] = "Updated upstream title"
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "openapi.json"
            with mock.patch.object(builder, "ROOT", pathlib.Path(directory)), \
                 mock.patch.object(builder, "UPSTREAM", path), \
                 mock.patch.object(builder, "fetch_upstream", return_value=upstream), \
                 contextlib.redirect_stdout(io.StringIO()):
                document = json.loads(builder.build(True))
            self.assertEqual(json.loads(path.read_text()), upstream)
            self.assertEqual(document["info"]["title"], "Updated upstream title")
            self.assertIn("InvalidApiKey",
                          document["components"]["securitySchemes"]["apiKey"]["description"])


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
