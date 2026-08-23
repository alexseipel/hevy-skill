# What the published repositories do

Drawn from the official API-skill repositories on GitHub, checked on
2026-08-22: [alpacahq/alpaca-skills](https://github.com/alpacahq/alpaca-skills),
[veniceai/skills](https://github.com/veniceai/skills) and
[anthropics/skills](https://github.com/anthropics/skills).

## The section shape they converge on

The two vendor sets, Alpaca and Venice, land in nearly the same place:

```
frontmatter (name, description)
# Title
one paragraph: what this covers, and when to prefer it over a sibling
## Use when          explicit trigger conditions, as a list
## Endpoints         table: Method | Path | Notes
## Quick start       a runnable call, above the fold
## Parameters        required and optional, split
## Response          real JSON, not a schema
## Errors            table: Status | Cause | Fix
## Gotchas           edge cases, limits, the thing that breaks first
cross-links to sibling skills
```

Deviate where the API demands it. Do not deviate to be original.

## Splitting

Venice runs one flat directory per API surface with a vendor prefix
(`skills/venice-chat/`). Alpaca groups by product first
(`skills/broker-api/trading-orders/`). Both pair every `SKILL.md` with a
`reference.md`, without exception.

The rule underneath: **a skill covers what a person would ask for in one
request.** "Place an order" is a skill. "The trading API" is a repository.

For a small API, one skill with per-resource reference files is the same idea
at a smaller scale, and it keeps the install to a single directory.

## The hub

Once a set passes about three skills, one of them holds auth, the base URL and
the shared error table, and every other skill names it in the first paragraph.
Alpaca does this with `alpaca-broker-integration` and opens the sibling skills
with a line telling the reader to load it first.

## Generation and drift

Venice ships `scripts/sync_from_swagger.py` with JSON snapshots, so its skills
regenerate from the vendor's OpenAPI document instead of drifting.

**Treat a generated artifact as a starting point, not as truth.** A vendor spec
can disagree with the vendor's own running API, and a generated client encodes
that error in authoritative-looking types. Verifying live catches it, and almost
nobody does.

## Checks in CI

Alpaca runs `scripts/validate_skills.py` on every pull request, covering
directory layout, frontmatter fields, a regex over the skill name, and
secret-scanning heuristics with a placeholder allowlist.

The heuristics matter less than the habit. A repository that scans for keys
catches the one commit where somebody pasted a real one, and review does not.

## Repository furniture

README, LICENSE, CONTRIBUTING, and an `AGENTS.md` holding the conventions for
whoever edits the skills next. A contributor template directory, so a new skill
starts from the house shape. A `.claude-plugin/` manifest where the repository
is meant to be installable as a plugin.

## Secrets

Environment variables in every published repository, with the key named in the
README and never in a file. Alpaca enforces it in CI rather than in review,
which is the part worth copying: review catches a pasted key only when somebody
happens to look.

State the rule in full where a reader will meet it. A key belongs out of
command arguments, payloads, URLs, shell history, logs and responses, and a
`--help` that works without one is how somebody checks an install safely.
