---
name: skill-authoring
description: How to write an agent skill that other tools can load and that a model actually reaches for — the SKILL.md frontmatter the open standard allows, the three tiers of progressive disclosure, how to word a description so it triggers, and the layout conventions the largest published API-skill repositories share. Use when creating a skill, editing one, splitting a large one, debugging why a skill never fires, or reviewing a skill before release.
license: MIT
---

# Authoring an agent skill

A skill is a directory holding a `SKILL.md`: YAML frontmatter, then markdown.
The [Agent Skills](https://agentskills.io) standard covers it, and Claude Code,
Codex, Cursor, Gemini CLI and others read the same file.

Two decisions carry most of the outcome. The description decides whether the
skill is ever loaded, and the split between body and reference files decides
what it costs once it is.

## The three tiers

| Tier | What loads | When | Cost |
| ---- | ---------- | ---- | ---- |
| 1 | `name` and `description` | always, for every installed skill | about 100 tokens each |
| 2 | the `SKILL.md` body | when the skill activates | stays in context for the rest of the session |
| 3 | reference files | only when the body sends the model to one | nothing until then |

Tier 2 is the one people get wrong. Its content does not leave context after
the turn that loaded it, so a paragraph explaining why the API is interesting
is paid for again on every later turn. Put the operational facts in the body
and everything else behind a link.

Keep the body under 500 lines. Past that, the split you have not made yet is
the thing to fix.

## The description decides everything

It is the retrieval key, not a summary, and it is the only text competing
against every other installed skill.

- **Third person, and it says when to load the skill**, not only what it
  covers. "Use when …" earns its place.
- **Name the concrete surface.** Routes, parameter names, object names, file
  extensions. A model matching a request against ten descriptions needs
  something to match on.
- **Use the words a user would type.** A description written for another skill
  author describes the skill accurately and never fires.
- **Front-load it.** The description and `when_to_use` are truncated together
  at 1,536 characters in the listing.

WRONG: `description: A helpful skill for working with fitness data.`
RIGHT: `description: Call the Hevy REST API at api.hevyapp.com — workouts,
routines, exercise templates, body measurements. Covers the api-key header,
the pageSize caps and the workout-events sync feed. Use when reading or
writing Hevy training data, or debugging a Hevy API response.`

## Frontmatter

**Six fields travel**: `name`, `description`, `license`, `compatibility`,
`metadata`, `allowed-tools`. Everything else is a host extension.

A skill that uses `context: fork`, `argument-hint` or any other extension does
not degrade gracefully outside its host. Packaging for claude.ai or the Skills
API **fails outright** with an unexpected-key error. Full field reference and
the portability rules: [references/frontmatter.md](references/frontmatter.md).

## Layout

```
skills/
  <skill-name>/
    SKILL.md          # workflow, the facts needed on every call
    reference/        # one file per surface, entered in the middle
    scripts/          # anything the model runs rather than reads
```

- **`name` matches the directory name.** Lowercase kebab-case.
- **One skill per surface.** Splitting is how tier 3 stays cheap.
- **Relative links between files**, never an absolute install path.
- **A hub skill** carrying auth and shared errors, which every sibling names in
  its first paragraph, once a set grows past about three skills.

What the largest published API-skill repositories do, and the section shape
they converge on: [references/patterns.md](references/patterns.md).

## Write the body as instructions

State what to do. A skill is read by a model that is mid-task, not by someone
evaluating whether the library is any good.

- **Tables wherever the content is a mapping.** Endpoints, fields, error codes,
  enum values.
- **A runnable example above the fold**, and it runs as written.
- **The gotcha that breaks the first call goes near the top**, not in a
  troubleshooting section at the bottom.
- **Say what the skill does not cover.** The model needs to know when to stop
  using it as much as when to start.

## Verify rather than assert

A skill is a set of claims about a system that changes without telling you.

- **Pin the upstream artifact** in the skill, such as the OpenAPI document, so
  the content has a source to be checked against.
- **Ship a check that fails.** A coverage or validation script that has never
  gone red is decoration. Break it on purpose once.
- **Separate documented from observed.** A behaviour you tested but the vendor
  never wrote down is worth more than anything else in the skill, and it needs
  a date attached, because it is the part most likely to rot.

## Before release

- [ ] the description names the surface and says when to load the skill
- [ ] frontmatter uses only the six portable fields
- [ ] `name` matches the directory, in kebab-case
- [ ] the body is under 500 lines, with the rest behind links
- [ ] every relative link resolves
- [ ] no key, token or credential in any file, checked by a script
- [ ] the first example runs as written
- [ ] a check exists that would fail if the skill drifted
