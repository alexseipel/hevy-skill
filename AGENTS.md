# Conventions

For whoever edits this repository next, human or agent.

## Layout

Two roots, and the split is the point.

| Path                              | Purpose                                          |
| --------------------------------- | ------------------------------------------------ |
| `skills/hevy-api/`                | the API skill. The only thing a user installs    |
| `skills/hevy-api/reference/`      | one file per API resource, plus `observed.md`    |
| `.agents/skills/writing/`         | the English house style for every word here      |
| `.agents/skills/skill-authoring/` | the conventions the skills themselves follow     |
| `.claude/skills/`, `.cursor/skills/`, `.gemini/skills/` | symlinks, so every tool sees both sets |
| `scripts/`                        | repository checks, not shipped with the skill    |
| `tests/`                          | offline tests for the client, no key needed      |
| `.claude-plugin/`                 | plugin marketplace manifest                      |

**`skills/` is what ships. `.agents/skills/` is what builds it.** The two dev
skills travel with a clone so anyone working on the repository picks them up,
and they are absent from the marketplace manifest so nobody installs them
alongside the API skill.

The mirrors under `.claude/`, `.cursor/` and `.gemini/` are committed
symlinks. On Windows, enable Developer Mode or set `core.symlinks` to `true`
before cloning, or they arrive as plain text files and discovery breaks.

**Load `writing` before editing any prose, and `skill-authoring` before
changing a `SKILL.md`.** They are the rules the rest of this file assumes.

Repository furniture stays out of `skills/`. Anything under `skills/hevy-api/`
is copied to a user's machine, so it earns its place there or it moves.

## Frontmatter

**Only the six fields the Agent Skills standard defines**: `name`,
`description`, `license`, `compatibility`, `metadata`, `allowed-tools`. These
skills use three of them.

The point is portability, and it is not theoretical. No two of these tools
read the same directory: Codex scans `.agents/skills`, Claude Code
`.claude/skills`, Cursor `.cursor/skills` and Gemini CLI `.gemini/skills`. A
repository wired to one vendor is invisible to the rest. Host extensions such
as `context: fork` or `argument-hint` are worse than invisible, because
packaging for claude.ai or the Skills API fails outright on them.
`validate_skill.py` enforces both rules, and prints the `ln -sfn` that fixes a
missing symlink.

`allowed-tools` is deliberately unset. The skill's work is HTTP calls, and the
only rule broad enough to pre-approve them is `Bash(curl:*)`, which would let
the skill reach any host without a prompt. That is not a grant to make on a
user's behalf.

## Writing a new endpoint up

1. **Read the spec entry in `skills/hevy-api/openapi.json` first**, then check
   it against the live API. The spec is the starting point, not the source of
   truth: it is already wrong in ten places
   (`skills/hevy-api/reference/observed.md`).
2. Add the row to the endpoint index in `SKILL.md`.
3. Add the section to the resource's file under `reference/`, with a runnable
   `curl` and the real response shape.
4. Add the subcommand to `scripts/hevy.py`, with `help` set to the method and
   path verbatim, because `check_coverage.py` reads it.
5. Run both checks.

**Behaviour the spec does not document is marked as observed**, with the date
and how it was found. `reference/observed.md` is where a correction goes, and
`scripts/verify_live.py` gains a check for it in the same commit. A claim
nobody can re-run is the one that rots silently.

`openapi.json` stays as `--fetch` wrote it, unedited. Correcting it there would
hide the disagreement, and the disagreement is the useful part.

## Secrets

The key comes from `HEVY_API_KEY`, always. No key in a source file, a fixture,
a URL or a test. `validate_skill.py` scans for the shapes that leak most often,
and passing that scan is the floor rather than the goal.

## Checks

```bash
python3 scripts/validate_skill.py && python3 scripts/check_coverage.py
python3 scripts/build_corrected_spec.py --check
python3 -m unittest discover -s tests
```

All four run in CI. `check_coverage.py` fails on any operation missing from
the documentation, the client or the command line. An endpoint added to one of
them and forgotten in the others does not merge. The tests cover the client's
own logic offline: the summary arithmetic, the sync paths and the guard rails.
