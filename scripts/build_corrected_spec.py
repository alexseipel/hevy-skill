#!/usr/bin/env python3
"""Apply the verified corrections to Hevy's OpenAPI document.

    python3 scripts/build_corrected_spec.py            # rebuild from the pinned copy
    python3 scripts/build_corrected_spec.py --fetch    # re-pin upstream first, then rebuild
    python3 scripts/build_corrected_spec.py --check    # fail if the committed output is stale

Every patch asserts what it expects to find. A patch that no longer matches is
not skipped: it stops the build and names itself, because the two things that
cause it are Hevy fixing the bug and Hevy changing something else, and both
need a person to look ([reference/observed.md](../skills/hevy-api/reference/observed.md)).

Corrections are never derived from live responses. A response shows which
fields are present, never which fields exist, so an account that has recorded
no neck measurement would teach a deriving script to delete `neck_cm` from the
schema. Every patch here is a human assertion checked by `verify_live.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "hevy-api"
UPSTREAM = SKILL / "openapi.json"
PATCHES = SKILL / "spec-patches.json"
CORRECTED = SKILL / "openapi.corrected.json"
SWAGGER_BUNDLE = "https://api.hevyapp.com/docs/swagger-ui-init.js"


class PatchError(RuntimeError):
    pass


def unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def resolve(document: object, pointer: str) -> tuple[object, str]:
    """Return the container holding the pointer's last token, and that token."""
    tokens = [unescape(t) for t in pointer.split("/")[1:]]
    node = document
    for token in tokens[:-1]:
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node, tokens[-1]


def apply_patch(document: dict, patch: dict) -> None:
    op, pid = patch["op"], patch["id"]

    if op == "drop-parameter":
        removed = 0
        for item in document["paths"].values():
            for operation in item.values():
                params = operation.get("parameters")
                if not isinstance(params, list):
                    continue
                keep = [p for p in params if p.get("name") != patch["parameter"]]
                removed += len(params) - len(keep)
                if keep:
                    operation["parameters"] = keep
                else:
                    del operation["parameters"]
        if removed != patch["expect_count"]:
            raise PatchError(f"{pid}: expected {patch['expect_count']} occurrences of "
                             f"'{patch['parameter']}', found {removed}")
        return

    if op in ("set-parameter-default", "drop-parameter-default"):
        # Addressed by name, never by array index: dropping the api-key
        # parameter shifts every index, and so would any upstream reorder.
        operation = document["paths"][patch["route"]][patch["method"]]
        matches = [p for p in operation.get("parameters", [])
                   if p.get("name") == patch["parameter"]]
        if len(matches) != 1:
            raise PatchError(f"{pid}: found {len(matches)} '{patch['parameter']}' "
                             f"parameters on {patch['method'].upper()} {patch['route']}")
        current = matches[0].get("schema", {}).get("default")
        if current != patch["from"]:
            raise PatchError(f"{pid}: expected default {patch['from']!r}, found {current!r}")
        if op == "set-parameter-default":
            matches[0]["schema"]["default"] = patch["to"]
        else:
            del matches[0]["schema"]["default"]
        return

    container, key = resolve(document, patch["pointer"])

    if op == "add":
        if key in container:
            raise PatchError(f"{pid}: '{patch['pointer']}' already exists upstream. "
                             f"Hevy may have fixed this; re-check the patch.")
        container[key] = patch["value"]

    elif op == "replace":
        if key not in container:
            raise PatchError(f"{pid}: '{patch['pointer']}' is gone from upstream")
        if container[key] != patch["from"]:
            raise PatchError(f"{pid}: expected {patch['from']!r} at '{patch['pointer']}', "
                             f"found {container[key]!r}")
        container[key] = patch["to"]

    elif op == "rename-key":
        target = container.get(key)
        if not isinstance(target, dict):
            raise PatchError(f"{pid}: '{patch['pointer']}' is not an object")
        if patch["from"] not in target:
            raise PatchError(f"{pid}: '{patch['from']}' is gone from upstream. "
                             f"Hevy may have fixed this; re-check the patch.")
        if patch["to"] in target:
            raise PatchError(f"{pid}: '{patch['to']}' already exists upstream")
        # Rebuilt rather than popped, so the renamed key keeps its position.
        container[key] = {(patch["to"] if k == patch["from"] else k): v
                          for k, v in target.items()}

    elif op == "merge":
        target = container.get(key)
        if not isinstance(target, dict):
            raise PatchError(f"{pid}: '{patch['pointer']}' is not an object")
        # Merged keys must be absent upstream, or the patch would silently
        # overwrite whatever Hevy started saying there.
        clashes = [k for k in patch["value"] if k in target]
        if clashes:
            raise PatchError(f"{pid}: {', '.join(clashes)} already set upstream. "
                             f"Hevy may have fixed this; re-check the patch.")
        target.update(patch["value"])

    else:
        raise PatchError(f"{pid}: unknown op '{op}'")


def add_page_not_found(document: dict, routes: list[str]) -> int:
    """A page past the end returns 404 on every list route, undocumented."""
    added = 0
    for route in routes:
        responses = document["paths"][route]["get"]["responses"]
        if "404" in responses:
            continue
        responses["404"] = {
            "description": "Page number past the last page",
            # JSON here, unlike the plain-text 404s on three single-item routes
            # (reference/observed.md row 17).
            "content": {"application/json": {"schema": {
                "type": "object",
                "properties": {"error": {"type": "string"}},
                "example": {"error": "Page not found"},
            }}},
        }
        added += 1
    return added


def fetch_upstream() -> dict:
    """Pull the spec out of the Swagger UI bundle, which is where Hevy serves it."""
    with urllib.request.urlopen(SWAGGER_BUNDLE, timeout=30) as response:
        text = response.read().decode()
    start = text.index("{", text.index('"swaggerDoc":') + len('"swaggerDoc":'))
    depth, in_string, escaped = 0, False, False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            in_string = not in_string
        elif not in_string:
            depth += 1 if char == "{" else -1 if char == "}" else 0
            if depth == 0:
                return json.loads(text[start:index + 1])
    raise PatchError("could not find swaggerDoc in the Swagger UI bundle")


def build(fetch: bool) -> str:
    if fetch:
        upstream = fetch_upstream()
        UPSTREAM.write_text(json.dumps(upstream, indent=2) + "\n")
        print(f"  re-pinned {UPSTREAM.relative_to(ROOT)} from upstream")
    else:
        upstream = json.loads(UPSTREAM.read_text())

    config = json.loads(PATCHES.read_text())
    document = json.loads(json.dumps(upstream))

    for patch in config["patches"]:
        apply_patch(document, patch)
        print(f"  [ok] {patch['id']}")

    added = add_page_not_found(document, config["page_not_found_routes"])
    print(f"  [ok] page-not-found ({added} routes)")

    document["info"]["description"] = (
        document["info"].get("description", "").rstrip()
        + f"\n\n      CORRECTED COPY. {len(config['patches'])} corrections based on live "
          f"observations dated {config['verified_at']}, plus 404 responses on "
          f"{added} list routes. The upstream document is openapi.json, and the "
          f"corrections are listed in spec-patches.json and reference/observed.md. "
          f"Upstream reviewed on {config['upstream_checked_at']}; later write "
          f"response changes remain unverified.\n      ")
    document["info"]["x-corrections-verified-at"] = config["verified_at"]
    document["info"]["x-upstream-checked-at"] = config["upstream_checked_at"]
    document["info"]["x-corrections-source"] = "spec-patches.json"
    document["info"]["x-upstream"] = {
        "source": "https://api.hevyapp.com/docs",
        "notice": "Derived from Hevy's own OpenAPI document. Copyright in the "
                  "original, including its descriptions and examples, belongs to "
                  "Hevy. The corrections are MIT licensed; the underlying document "
                  "is redistributed for interoperability. See NOTICE.",
    }

    return json.dumps(document, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fetch", action="store_true",
                        help="re-pin openapi.json from upstream before building")
    parser.add_argument("--check", action="store_true",
                        help="fail if the committed corrected spec is out of date")
    args = parser.parse_args()

    try:
        rendered = build(args.fetch)
    except (PatchError, KeyError) as exc:
        print(f"\nPatch failed: {exc}", file=sys.stderr)
        print("Upstream changed. Re-verify with skills/hevy-api/scripts/verify_live.py, "
              "then update spec-patches.json and reference/observed.md.", file=sys.stderr)
        return 1

    if args.check:
        current = CORRECTED.read_text() if CORRECTED.is_file() else ""
        if current != rendered:
            print("\nopenapi.corrected.json is stale. Run "
                  "scripts/build_corrected_spec.py", file=sys.stderr)
            return 1
        print("\nopenapi.corrected.json is up to date.")
        return 0

    CORRECTED.write_text(rendered)
    print(f"\nwrote {CORRECTED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
