#!/usr/bin/env python3
"""Check that every operation in openapi.json is documented and reachable.

Three questions, one per column of the report:

  docs    does a markdown file in the skill name this method and this path?
  client  does scripts/hevy.py request this method against this path?
  cli     does a subcommand of hevy.py declare this operation in its help?

The cli column reads the parser's own --help rendering rather than the source,
so a command renamed without its help text still fails.

Exits non-zero when any operation misses any column, so CI fails on a gap
instead of shipping an unchecked coverage claim.
"""

from __future__ import annotations

import importlib.util
import json
import os
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

# What a placeholder segment looks like at a client call site: an f-string
# field such as {seg(args.workout_id)}.
CLIENT_PLACEHOLDER = r"\{[^}]+\}"


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


def cli_help_text() -> str:
    """The parser's own --help rendering, with every subcommand's help line.

    format_help() wraps at the terminal width, and a wrapped path would slip
    past the coverage regex, so COLUMNS is pinned wide for the call.
    """
    os.environ["COLUMNS"] = "400"
    return load_client().build_parser().format_help()


def main() -> int:
    if not SPEC.is_file():
        sys.exit(f"missing spec: {SPEC}")

    ops = operations(json.loads(SPEC.read_text()))
    docs = "\n".join(p.read_text() for p in sorted(SKILL_DIR.rglob("*.md")))
    source = CLIENT.read_text()
    helps = cli_help_text()

    rows, failures = [], 0
    for method, path in ops:
        documented = re.search(rf"{method}\s+{path_regex(path)}", docs)
        # The call site must carry the method too: most paths serve a GET and
        # a write, and a path-only match kept a deleted write green through
        # its sibling. Paths appear as f-strings, so {seg(...)} counts.
        called = re.search(
            rf'request\(\s*"{method}",\s*f?"{path_regex(path, CLIENT_PLACEHOLDER)}"',
            source)
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
