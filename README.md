# hevy-skill

An agent skill for the [Hevy](https://hevy.com) training API: every endpoint of
`api.hevyapp.com/v1`, the object shapes behind them, and a dependency-free
client to call them with.

All 22 operations are covered, and a check in CI proves it rather than claiming
it. Every documented behaviour was verified against a live account, which turned
up **nine places where Hevy's published OpenAPI spec is wrong**. Those are listed
in [reference/observed.md](skills/hevy-api/reference/observed.md), and this skill
documents what the API does rather than what the spec says.

## Install

```bash
git clone https://github.com/alexseipel/hevy-skill.git
```

Copy the skill into your own tool's personal skills directory. There is no
single path that every tool reads:

| Tool | Personal directory |
| ---- | ------------------ |
| Codex | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Cursor | project-level `.cursor/skills/` only |

```bash
cp -R skills/hevy-api ~/.agents/skills/hevy-api
```

Claude Code users can add the repository as a plugin marketplace instead, which
installs the same directory:

```bash
claude plugin marketplace add alexseipel/hevy-skill
```

The `owner/repo` shorthand clones over SSH. Without a key loaded, set
`CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` or pass the full HTTPS URL instead.

The skill declares only `name`, `description` and `license`, which are three of
the six fields the [Agent Skills](https://agentskills.io) standard defines. No
host extension appears anywhere, so nothing here is tied to one vendor.

## Use it

Get a key at `https://hevy.com/settings?developer`, which needs a Hevy Pro
account, and put it in the environment:

```bash
export HEVY_API_KEY="..."
```

Then ask the agent for what you want, in its own words: "sync my last month of
Hevy workouts into a CSV", "build a push-pull routine from my best lifts",
"chart my bench press over the past year".

The bundled client also runs on its own. It has 26 commands: one per endpoint,
plus `summary`, `sync`, `sql` and `cache`.

```bash
python3 skills/hevy-api/scripts/hevy.py templates --search "bench press"
```

```bash
python3 skills/hevy-api/scripts/hevy.py summary --weeks 4
```

```bash
python3 skills/hevy-api/scripts/hevy.py workouts --all | jq '.[].title'
```

Search exists because the API has no search route, and the catalogue is cached
on disk after the first walk. `summary` computes volume, working sets and a
muscle-group split, none of which the API returns.

**Write commands refuse to run without `--yes`**, because the API has no delete
route. `--help` lists every command.

## What this has that a Hevy client usually doesn't

**A corrected OpenAPI document.** Hevy's published spec disagrees with Hevy's
running API in nine places, and it declares no server and no security scheme at
all, so a client generated from it knows neither where to send a request nor how
to authenticate. [openapi.corrected.json](skills/hevy-api/openapi.corrected.json)
fixes all of it. Feed it to any code generator, in any language.

```bash
python3 scripts/build_corrected_spec.py --fetch
```

That one command re-pins Hevy's document straight from the Swagger UI bundle it
is served in, then re-applies all 15 corrections from
[spec-patches.json](skills/hevy-api/spec-patches.json), each carrying what it
asserts and why. **A patch that no longer matches stops the build** rather than
reapplying quietly, because the two things that cause it are Hevy fixing the bug
and Hevy changing something else, and both need a person.

**Search, which the API has no route for.** The catalogue is paged once and
cached on disk, then matched locally.

**A training summary the API cannot return.** Volume, working sets and a
muscle-group split, computed here by joining workouts to the exercise catalogue.
Warmup sets are excluded, which otherwise inflates volume by roughly a fifth.

**Writes that refuse to run without `--yes`.** The API has no delete route, so a
create is permanent and an update overwrites.

**Claims that re-run.** `verify_live.py` re-checks 38 statements about live
behaviour against a real account, and a weekly CI job re-applies every spec
correction to whatever Hevy is serving that day.

### Optional: a local SQLite mirror

**Off by default. Nothing is written to disk until you ask for it**, and the
agent will not suggest it unprompted. Your training data stays on Hevy unless
you decide otherwise.

When you do want SQL over your whole history, name the datasets you want stored:

```bash
python3 skills/hevy-api/scripts/hevy.py cache enable --workouts
```

```bash
python3 skills/hevy-api/scripts/hevy.py sql "
  SELECT substr(start_time,1,7) AS month,
         ROUND(MAX(weight_kg * (1 + reps/30.0)), 1) AS best_e1rm_kg
  FROM performed_sets
  WHERE exercise_title LIKE 'Bench Press%' AND set_type != 'warmup'
  GROUP BY month ORDER BY month DESC"
```

`cache status` reports what is stored and how fresh it is. `cache clear` deletes
the mirror and the cached exercise catalogue together.

Only workouts sync exactly. The events feed reports edits to a workout of any
age, so a session from last year corrected this morning arrives on the next
sync. Measurements and routines have no such feed and are refreshed in full,
which is why they are separate opt-ins rather than one switch.

`sql` syncs before it queries, so there is no path that reads a stale mirror by
accident. It takes `SELECT` and `WITH` only, because writes belong to the API.

A several-hundred-workout account backfills in about twelve seconds and produces roughly
thousands of set rows. Later syncs take about one second when nothing has changed.

**One thing is cached without being asked**: the exercise catalogue, as a JSON
file, because `--search` cannot work without it. It is a lookup table rather
than training history, and `cache clear` removes it.

### Nothing is cached quietly

Every read from a cache, write to one, and deletion of one is announced:

```
[hevy] cached 453 exercise templates to ~/.cache/hevy-skill/exercise_templates.json.
       The catalogue is a lookup table, not training history. Remove it with 'cache clear'.
[hevy] answered from the local mirror at ~/.cache/hevy-skill/hevy.db,
       synced 2026-08-22T17:04:11, not from the API
```

Notices go to stderr, so `| jq` still works on stdout. `HEVY_QUIET=1` turns them
off for scripts.

The mirror is suggested in one situation only: when a single command has cost
ten or more API calls, the client says so and names the option. That threshold
is a measurement rather than a guess, and the suggestion disappears once the
mirror is on.

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

Two more skills ship with a clone and are **not** installed alongside the API
skill. They are the rules this repository is built under, and they load
automatically for anyone working on it:

| Path | What it is for |
| ---- | -------------- |
| `.agents/skills/writing` | the English house style every word here follows |
| `.agents/skills/skill-authoring` | how to write a skill other tools load and a model reaches for |

Both are symlinked into `.claude/skills/`, `.cursor/skills/` and
`.gemini/skills/`, so a clone picks them up whichever tool you open it with.
They are absent from the plugin manifest, so installing the API skill does not
drag them along.

## What it does not cover

- **Deleting anything.** The API has no delete route for any resource.
- **Other people's data.** A key reaches exactly one account, and there is no
  OAuth flow and no user scoping.
- **Anything outside `/v1`.** No webhooks, no streaming, no bulk import route.
- **Plan and unit settings.** The API exposes an account id, a name and a
  profile URL, and nothing else about the account.

Hevy's own documentation says the API may change shape or be withdrawn, so pin
the behaviour you depend on with tests.

## Checks

Three run on every pull request:

```bash
python3 scripts/validate_skill.py
```

Frontmatter, the portable-field set, the name, relative links, a scan for keys
committed by accident, and the discovery symlinks, so a skill added without
cross-tool wiring fails before it reaches a Codex user.

```bash
python3 scripts/check_coverage.py
```

Every operation in `openapi.json` against the documentation, the client and the
command line, printed as a table. It fails on a gap, which is how the coverage
claim above stays true.

```bash
python3 scripts/build_corrected_spec.py --check
```

Fails when the committed corrected spec no longer matches its patch set.

The fourth needs a key, so it runs on demand rather than in CI:

```bash
HEVY_API_KEY=... python3 skills/hevy-api/scripts/verify_live.py
```

38 claims about live behaviour, re-checked against a real account. Read-only: it
calls no write route, because the API has no delete route and test data in a
real account is permanent. A failure names the claim, so it points at the line
of documentation that went stale.

Conventions for editing the skills are in [AGENTS.md](AGENTS.md), which
[CLAUDE.md](CLAUDE.md) points at as well.

## Licence

MIT, in [LICENSE](LICENSE), covering the skills, the documentation, the client
and the checks alike, so a skill copied out of this repository carries one
licence rather than two.

**Two files are not mine to license.** `openapi.json` is Hevy's own OpenAPI
document, redistributed unmodified so the corrections have a fixed reference to
be checked against, and `openapi.corrected.json` is generated from it. Copyright
in that document belongs to Hevy, who attach no licence to it. [NOTICE](NOTICE)
says so, and the MIT grant does not reach them or the Hevy name.

No description or example from Hevy's document is reproduced verbatim in any
Markdown file here. The documentation restates the facts and cites the source.
