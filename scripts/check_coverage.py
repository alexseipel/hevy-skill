#!/usr/bin/env python3
"""Check that every operation in openapi.json is documented and reachable.

Three questions, one per column of the report:

  docs    does a markdown file in the skill name this method and this path?
  client  does scripts/hevy.py issue a request against this path?
  cli     does a subcommand of hevy.py declare this operation in its help?

The cli column reads the real argparse tree rather than grepping the source,
so a command renamed without its help text still fails the check.

Exits non-zero when any operation misses any column, so CI fails on a gap
instead of shipping a coverage claim nobody checked.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "hevy-api"
SPEC = SKILL_DIR / "openapi.json"
CLIENT = SKILL_DIR / "scripts" / "hevy.py"
METHODS = ("get", "post", "put", "patch", "delete")

# A path reference ends where the path ends. Without this, /v1/workouts would
# match inside /v1/workouts/count and report coverage it does not have.
BOUNDARY = r"(?![\w/{-])"


def operations(spec: dict) -> list[tuple[str, str]]:
    found = [(method.upper(), path)
             for path, item in spec.get("paths", {}).items()
             for method in item if method.lower() in METHODS]
    return sorted(found, key=lambda op: (op[1], op[0]))


def path_regex(path: str, placeholder: str = r"\{[^}/]+\}") -> str:
    """Regex for one path, accepting any name for a placeholder segment.

    `/v1/workouts/{workoutId}` has to match the same path written with a
    different placeholder, such as the client's f-string `{args.workout_id}`.
    """
    segments = [placeholder if seg.startswith("{") else re.escape(seg)
                for seg in path.strip("/").split("/")]
    return "/" + "/".join(segments) + BOUNDARY


def load_client() -> object:
    # dont_write_bytecode keeps a __pycache__ out of the skill directory, which
    # ships to users' machines exactly as it sits here.
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec = importlib.util.spec_from_file_location("hevy_client", CLIENT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = previous


def subcommand_help(parser: argparse.ArgumentParser) -> list[str]:
    """Every subcommand's help string, read from the parser itself."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return [choice.help for choice in action._choices_actions]
    return []


def main() -> int:
    if not SPEC.is_file():
        sys.exit(f"missing spec: {SPEC}")

    ops = operations(json.loads(SPEC.read_text()))
    docs = "\n".join(p.read_text() for p in sorted(SKILL_DIR.rglob("*.md")))
    source = CLIENT.read_text()
    helps = "\n".join(h or "" for h in subcommand_help(load_client().build_parser()))

    rows, failures = [], 0
    for method, path in ops:
        documented = re.search(rf"{method}\s+{path_regex(path)}", docs)
        # The client writes paths as f-strings, so {args.workout_id} counts.
        called = re.search(path_regex(path, r"\{[^}]+\}"), source)
        exposed = re.search(rf"{method} {path_regex(path)}", helps)
        ok = bool(documented and called and exposed)
        failures += not ok
        rows.append((method, path, bool(documented), bool(called), bool(exposed), ok))

    mark = {True: "yes", False: "NO"}
    width = max(len(path) for _, path, *_ in rows)
    print(f"{'METHOD':<7} {'PATH':<{width}}  docs  client  cli")
    for method, path, documented, called, exposed, ok in rows:
        print(f"{method:<7} {path:<{width}}  {mark[documented]:<4}  "
              f"{mark[called]:<6}  {mark[exposed]}")

    print(f"\n{len(rows) - failures}/{len(rows)} operations fully covered.")
    if failures:
        print(f"{failures} operation(s) incomplete.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
