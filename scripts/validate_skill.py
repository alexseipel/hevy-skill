#!/usr/bin/env python3
"""Validate the skill's layout, frontmatter, links and secret hygiene.

Run it before opening a pull request, and in CI:

    python3 scripts/validate_skill.py

Every failure names the file and the rule, so the fix does not need a reading
of this script.
"""

from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Two roots, and the split is the point. skills/ is what a user installs.
# .agents/skills holds the skills for working ON this repository, which ship
# with a clone and are never installed alongside the product.
PUBLISHED_ROOT = ROOT / "skills"
DEV_ROOT = ROOT / ".agents" / "skills"

# No single directory covers every tool: Codex reads .agents/skills, Claude Code
# .claude/skills, Cursor .cursor/skills and Gemini CLI .gemini/skills. A skill
# wired into only some of them is invisible to the rest.
MIRROR_DIRS = tuple(ROOT / f".{tool}" / "skills"
                    for tool in ("claude", "cursor", "gemini"))

# The Agent Skills spec accepts these six fields. Anything else is a Claude
# Code extension, and it makes packaging for claude.ai or the Skills API fail
# with a hard error rather than being ignored.
PORTABLE_FIELDS = {"name", "description", "license", "compatibility",
                   "metadata", "allowed-tools"}

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DESCRIPTION_CAP = 1536      # the skill listing truncates here
BODY_LINE_CAP = 500         # documented guidance for SKILL.md

SECRET_PATTERNS = [
    ("bearer-token", re.compile(r"\b[A-Za-z0-9_-]{32,}\.[A-Za-z0-9_-]{16,}\b")),
    # The optional quote covers the shape the client itself uses, a quoted
    # header name in a dict: {"api-key": "..."}.
    ("assigned-key", re.compile(r"(?i)\b(api[-_]?key|hevy[-_]?api[-_]?key)\b"
                                r"['\"]?\s*[:=]\s*"
                                r"['\"]?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}"
                                r"-[0-9a-f]{4}-[0-9a-f]{12}")),
]
# UUIDs that appear in the upstream spec's own examples are not secrets.
SECRET_ALLOWLIST = ("00000000-0000-0000-0000-000000000000",
                    "$HEVY_API_KEY", "HEVY_API_KEY}", "example", "…")

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]*)(#[^)\s]*)?\)")
HEADING = re.compile(r"^#{1,6}\s+(.*)$")

failures: list[str] = []


def fail(path: Path, rule: str, message: str) -> None:
    failures.append(f"{path.relative_to(ROOT)}: [{rule}] {message}")


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fields, key = {}, None
    for line in text[4:end].splitlines():
        if line[:1] in (" ", "\t") and key:
            fields[key] += " " + line.strip()
        elif ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            fields[key] = unquote(value.strip())
    return fields


def check_frontmatter_yaml(skill_md: Path, text: str) -> None:
    """Reject scalars a strict YAML parser rejects.

    Claude Code parses frontmatter leniently, so an unquoted value holding
    ": " loads here and fails in PyYAML, js-yaml and Psych with "mapping
    values are not allowed in this context".
    """
    end = text.find("\n---", 4)
    for line in text[4:end].splitlines():
        match = re.match(r"^([\w-]+):\s*(\S.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        # A flow collection is already unambiguous: metadata is documented as a
        # map, and allowed-tools as a list.
        if value[0] in ("'", '"', ">", "|", "[", "{"):
            continue
        if ": " in value or " #" in value:
            fail(skill_md, "yaml",
                 f"unquoted '{key}' value breaks strict YAML parsers. Quote it.")


def check_skill(skill_md: Path) -> None:
    text = skill_md.read_text()
    directory = skill_md.parent

    front = parse_frontmatter(text)
    if front is None:
        fail(skill_md, "frontmatter", "no YAML frontmatter between --- markers")
        return
    check_frontmatter_yaml(skill_md, text)

    for field in ("name", "description"):
        if not front.get(field):
            fail(skill_md, "frontmatter", f"missing required field: {field}")

    extra = set(front) - PORTABLE_FIELDS
    if extra:
        fail(skill_md, "portability",
             f"non-spec frontmatter breaks packaging: {', '.join(sorted(extra))}")

    name = front.get("name", "")
    if name and not NAME_PATTERN.match(name):
        fail(skill_md, "name", f"'{name}' is not lowercase kebab-case")
    if name and name != directory.name:
        fail(skill_md, "name", f"'{name}' does not match its directory '{directory.name}'")

    description = front.get("description", "")
    if len(description) > DESCRIPTION_CAP:
        fail(skill_md, "description",
             f"{len(description)} characters, truncated at {DESCRIPTION_CAP}")

    body_lines = len(text.splitlines())
    if body_lines > BODY_LINE_CAP:
        fail(skill_md, "length", f"{body_lines} lines, over the {BODY_LINE_CAP} guideline")


def skill_dirs(root: Path) -> list[Path]:
    """Real skill directories under a root, ignoring symlinks into other trees."""
    return sorted(p for p in root.iterdir()
                  if not p.is_symlink() and (p / "SKILL.md").is_file())


def check_discovery_wiring() -> None:
    """Every skill resolves from every tool's directory.

    A published skill is symlinked into all four, including .agents. A dev
    skill already lives in .agents, so it needs the other three.
    """
    wiring = [(d, (DEV_ROOT,) + MIRROR_DIRS, "../../skills")
              for d in skill_dirs(PUBLISHED_ROOT)]
    wiring += [(d, MIRROR_DIRS, "../../.agents/skills")
               for d in skill_dirs(DEV_ROOT)]

    for skill_dir, mirrors, target in wiring:
        for mirror in mirrors:
            link = mirror / skill_dir.name
            where = mirror.relative_to(ROOT)
            if not link.is_symlink():
                fail(skill_dir / "SKILL.md", "discovery",
                     f"no symlink at {where}/{skill_dir.name}. Run: "
                     f"ln -sfn {target}/{skill_dir.name} {where}/{skill_dir.name}")
            elif link.resolve() != skill_dir.resolve():
                fail(skill_dir / "SKILL.md", "discovery",
                     f"{where}/{skill_dir.name} points at {link.resolve()}")


@functools.lru_cache(maxsize=None)
def heading_anchors(path: Path) -> frozenset[str]:
    """GitHub's anchor per heading: lowercase, punctuation dropped, spaces to hyphens."""
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    in_code = False
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        match = None if in_code else HEADING.match(line)
        if not match:
            continue
        text = match.group(1).strip().replace("`", "")
        slug = re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return frozenset(anchors)


def check_links(path: Path) -> None:
    for target, anchor in MARKDOWN_LINK.findall(path.read_text()):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if not target and not anchor:
            continue
        resolved = (path.parent / target).resolve() if target else path
        if not resolved.exists():
            fail(path, "link", f"relative link does not resolve: {target}")
            continue
        if anchor and resolved.suffix == ".md":
            if anchor[1:] not in heading_anchors(resolved):
                fail(path, "anchor", f"no heading matches {target}{anchor}")


def check_secrets(path: Path) -> None:
    text = path.read_text()
    for rule, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            hit = match.group(0)
            if any(allowed in hit for allowed in SECRET_ALLOWLIST):
                continue
            fail(path, rule, f"possible secret in source: {hit[:60]}")


def main() -> int:
    skill_files = [d / "SKILL.md"
                   for root in (PUBLISHED_ROOT, DEV_ROOT) for d in skill_dirs(root)]
    if not skill_files:
        sys.exit(f"no SKILL.md found under {PUBLISHED_ROOT} or {DEV_ROOT}")

    for skill_md in skill_files:
        check_skill(skill_md)

    check_discovery_wiring()

    # .json is scanned too: a captured response pasted into a fixture is the
    # likeliest place a real key would land.
    scanned = [p for root in (PUBLISHED_ROOT, DEV_ROOT)
               for d in skill_dirs(root) for p in sorted(d.rglob("*"))]
    scanned += sorted((ROOT / "scripts").glob("*.py"))
    scanned += sorted((ROOT / "tests").glob("*.py"))
    # The repo's front door and its workflows leak keys as readily as a fixture.
    scanned += [ROOT / name for name in
                ("README.md", "AGENTS.md", "CONTRIBUTING.md", "CLAUDE.md",
                 "NOTICE", "LICENSE")]
    scanned += sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    for path in scanned:
        if path.is_file() and path.suffix in (".md", ".py", ".json", ".yml", ""):
            check_secrets(path)
            if path.suffix == ".md":
                check_links(path)

    if failures:
        print(f"{len(failures)} problem(s):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    published = len(skill_dirs(PUBLISHED_ROOT))
    print(f"{published} published + {len(skill_files) - published} dev skill(s) valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
