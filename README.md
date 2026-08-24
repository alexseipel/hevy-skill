# hevy-skill

[![checks](https://github.com/alexseipel/hevy-skill/actions/workflows/checks.yml/badge.svg)](https://github.com/alexseipel/hevy-skill/actions/workflows/checks.yml)

An agent skill for the [Hevy](https://hevy.com) training API: every endpoint of
`api.hevyapp.com/v1`, the object shapes behind them, and a dependency-free
client to call them with.

All 22 operations are covered, and a CI check proves it. Every documented
behaviour was verified against a live account, which turned up **eighteen
places where Hevy's published OpenAPI spec is wrong**
([observed.md](skills/hevy-api/reference/observed.md)). This skill documents
what the API does, not what the spec says.

## Install

```bash
git clone https://github.com/alexseipel/hevy-skill.git
mkdir -p ~/.agents/skills
cp -R hevy-skill/skills/hevy-api ~/.agents/skills/hevy-api
```

No single skills path is read by every tool:

| Tool | Personal directory |
| ---- | ------------------ |
| Codex | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Cursor | project-level `.cursor/skills/` only |

Claude Code can add the repository as a plugin marketplace instead, installing
the same directory as `hevy:hevy-api`:

```bash
claude plugin marketplace add alexseipel/hevy-skill
```

The `owner/repo` shorthand clones over SSH. Without a key loaded, set
`CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` or pass the full HTTPS URL.

The skill declares `name`, `description` and `license`, three of the six fields
the [Agent Skills](https://agentskills.io) standard defines. No host extension
appears anywhere, so nothing here is tied to one vendor.

## Use it

Get a key at `https://hevy.com/settings?developer`, which needs Hevy Pro:

```bash
export HEVY_API_KEY="..."
```

Then ask the agent in your own words: "sync my last month of Hevy workouts
into a CSV", "chart my bench press over the past year".

The client also runs on its own, with 26 commands: one per endpoint, plus
`summary`, `sync`, `sql` and `cache`. Standard library only, on Python 3.9 or
newer.

```bash
python3 skills/hevy-api/scripts/hevy.py templates --search "bench press"
python3 skills/hevy-api/scripts/hevy.py summary --weeks 4 --unit lb
python3 skills/hevy-api/scripts/hevy.py workouts --all | jq '.[].title'
```

**Write commands refuse to run without `--yes`**, because the API has no delete
route: a create is permanent and an update overwrites. A failed write is never re-sent
either, except on `429`: a `5xx` or a dropped connection can follow a commit,
so the error says the write may have landed. `--help` lists every command.

## What this has that a Hevy client usually doesn't

| | |
| --- | --- |
| **A corrected OpenAPI document** | Feed [openapi.corrected.json](skills/hevy-api/openapi.corrected.json) to any code generator, in any language |
| **Search** | The API has no search route. The catalogue is paged once, cached, then matched locally |
| **A training summary** | Volume, working sets and a muscle-group split, joined against the exercise catalogue. Warmup sets excluded, which otherwise inflates volume by roughly a fifth. `--unit lb` converts and renames every key, because the API answers in kilograms whatever the account displays |
| **Claims that re-run** | `verify_live.py` re-checks every read-only claim against a real account, and a weekly CI job re-applies every spec correction to whatever Hevy is serving |

The upstream spec declares no server and no security scheme, so a generated
client knows neither where to send a request nor how to authenticate. One
command re-pins Hevy's document from the Swagger UI bundle and re-applies all 31
corrections from [spec-patches.json](skills/hevy-api/spec-patches.json):

```bash
python3 scripts/build_corrected_spec.py --fetch
```

**A patch that no longer matches stops the build.** Either Hevy fixed the bug
or Hevy changed something else, and both need a person.

### Optional: a local SQLite mirror

**Off by default, and the agent will not suggest it unprompted.** Nothing
reaches disk until you name the datasets you want stored:

```bash
python3 skills/hevy-api/scripts/hevy.py cache enable --workouts
python3 skills/hevy-api/scripts/hevy.py sql "
  SELECT substr(start_time,1,7) AS month,
         ROUND(MAX(weight_kg * (1 + reps/30.0)), 1) AS best_e1rm_kg
  FROM performed_sets
  WHERE exercise_template_id = '79D0BB3A'
    AND set_type != 'warmup' AND reps > 0
  GROUP BY month ORDER BY month DESC"
```

`79D0BB3A` is Bench Press (Barbell), from `templates --search`. Filtering on
the title would span six templates, including the close-grip variant Hevy files
under triceps.

- `cache status` reports what is stored and how fresh. `cache clear` deletes
  the mirror and the catalogue together.
- **Only workouts sync exactly.** The events feed reports edits to a workout of
  any age. Measurements and routines have no feed and refresh in full,
  so they are separate opt-ins.
- `sql` syncs before it queries, so no path reads a stale mirror.
  It takes `SELECT` and `WITH` only.
- A few hundred workouts backfill in about twelve seconds, and a later sync
  with nothing to do takes about one.
- **The exercise catalogue is cached without being asked**, as JSON, because
  `--search` cannot work without it. It is a lookup table rather than training
  history, and `cache clear` removes it.

Every cache read, write and deletion is announced:

```
[hevy] cached 453 exercise templates to ~/.cache/hevy-skill/exercise_templates.json.
       The catalogue is a lookup table, not training history. Remove it with 'cache clear'.
[hevy] answered from the local mirror at ~/.cache/hevy-skill/hevy.db,
       synced 2026-08-22T17:04:11, not from the API
```

Notices go to stderr, so `| jq` still works. `HEVY_QUIET=1` silences them.

The mirror is suggested in one case only: a single command costing ten or more
API calls. The suggestion stops once the mirror is on.

## What is in the repository

| Path | What it holds |
| ---- | ------------- |
| `skills/hevy-api/SKILL.md` | auth, the endpoint index, pagination, errors, the gotchas |
| `skills/hevy-api/reference/` | one file per resource, plus `observed.md` and `recipes.md` |
| `skills/hevy-api/scripts/hevy.py` | the client, standard library only |
| `skills/hevy-api/scripts/verify_live.py` | re-checks every observed claim against a real account |
| `skills/hevy-api/openapi.json` | the pinned upstream spec, kept unedited for comparison |
| `skills/hevy-api/openapi.corrected.json` | the same spec with the corrections applied |
| `skills/hevy-api/spec-patches.json` | each correction, with what it asserts and why |
| `tests/` | offline tests for the client, run in CI without a key |
| `.agents/skills/writing` | the English house style every word here follows |
| `.agents/skills/skill-authoring` | how to write a skill other tools load |

Symlinks in `.claude/skills/`, `.cursor/skills/` and `.gemini/skills/` let a
clone pick the last two up whichever tool you open it with. The plugin manifest
omits them, so installing the API skill does not drag them along.

## What it does not cover

- **Deleting anything.** No delete route for any resource, confirmed by the
  server's own `Allow` headers.
- **Other people's data.** A key reaches one account. No OAuth, no user
  scoping.
- **Anything outside `/v1`.** No webhooks, no streaming, no bulk import.
- **Plan and unit settings.** The API exposes an account id, a name and a
  profile URL, and nothing else.

Hevy's documentation says the API may change shape or be withdrawn, so pin the
behaviour you depend on with tests.

## Checks

```bash
python3 scripts/validate_skill.py
python3 scripts/check_coverage.py
python3 scripts/build_corrected_spec.py --check
python3 -m unittest discover -s tests
```

| Check | What it fails on |
| ----- | ---------------- |
| `validate_skill.py` | frontmatter, portable fields, the name, relative links, a key committed by accident, a missing discovery symlink |
| `check_coverage.py` | any operation in `openapi.json` missing from the docs, the client or the command line |
| `build_corrected_spec.py --check` | the committed corrected spec no longer matching its patch set |
| `unittest` | the summary arithmetic, the sync upsert and delete paths, the guard rails, and the checks' own rules |

A fifth needs a key, so it runs on demand:

```bash
HEVY_API_KEY=... python3 skills/hevy-api/scripts/verify_live.py
```

The count varies by account: checks needing routines, folders or
measurements are skipped when there are none. Its write probes carry an
invalid key, so write behaviour was verified once by hand
([observed.md](skills/hevy-api/reference/observed.md)). A failure names the
claim it broke.

Conventions for editing the skills: [AGENTS.md](AGENTS.md). Getting a change
merged: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT, in [LICENSE](LICENSE), covering the skills, documentation, client and
checks alike, so a copied skill carries one licence rather than two.

**Two files are not mine to license.** `openapi.json` is Hevy's own OpenAPI
document, extracted from the Swagger UI bundle and re-serialised, content
unchanged, so the corrections have a fixed reference.
`openapi.corrected.json` is generated from it. Copyright belongs to Hevy, who
attach no licence to it. The MIT grant reaches neither them nor the Hevy name.

The documentation restates Hevy's descriptions in different words and cites the
source, and sample payloads reuse the spec's own example values.
[NOTICE](NOTICE) covers both.
