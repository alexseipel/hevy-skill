# Frontmatter

Two parts: what the open standard defines, and what a single host adds. Mixing
them is the most expensive mistake available here, because it fails at
packaging time rather than at load time.

## The portable six

These are the only fields the [Agent Skills](https://agentskills.io) standard
allows, and the only ones that survive every distribution path.

| Field | Required | What it does |
| ----- | -------- | ------------ |
| `name` | no | display name in listings. Defaults to the directory name |
| `description` | recommended | what the skill does and when to load it. Falls back to the first paragraph |
| `license` | no | the licence covering the skill |
| `compatibility` | no | environment requirements, up to 500 characters |
| `metadata` | no | a free-form map for your own tooling to read |
| `allowed-tools` | no | tools granted without a permission prompt for the turn |

## What happens when you exceed them

Claude Code accepts a longer list, including `when_to_use`, `argument-hint`,
`arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`,
`model`, `effort`, `context`, `agent`, `paths` and `shell`.

Those fields do not degrade outside Claude Code. Uploading to claude.ai,
packaging with `package_skill.py`, or using the Skills API rejects the file:

```
Unexpected key(s) in SKILL.md frontmatter: argument-hint.
Allowed properties are: allowed-tools, compatibility, description, license,
metadata, name
```

A skill restricted to the six loads in Claude Code unchanged, so the portable
set costs nothing and the extended set costs every other host. Use an extension
only when the skill is deliberately Claude Code only, and say so in the
`README`.

## `allowed-tools` is a permission grant

It pre-approves tools for the turn that invokes the skill, and the grant clears
on the next user message.

**Grant the narrowest rule that does the job, or none.** A skill whose work is
HTTP calls cannot be covered by anything narrower than `Bash(curl:*)`, which
reaches every host on the internet without a prompt. That is a decision for the
person installing the skill, not for its author. Leaving the field unset and
explaining why in the repository is the better default.

## Naming

| Where the skill lives | What sets the command you type |
| --------------------- | ------------------------------ |
| personal or project `skills/` | the directory name. `name` is only a label |
| a plugin's `skills/` | frontmatter `name` or the directory, namespaced by plugin |
| a plugin root `SKILL.md` | frontmatter `name`, falling back to the plugin directory |

Keep `name` identical to the directory name. The two diverging is legal in some
layouts and confusing in all of them.

Lowercase kebab-case, and unique across everything a user might install at
once. A vendor prefix is how the published repositories avoid collisions:
`hevy-api`, `venice-chat`, `alpaca-broker-trading-orders`.

## The description cap

`description` and `when_to_use` are concatenated in the skill listing and
truncated together at **1,536 characters**. Everything past that is invisible
to the decision the description exists to inform, so the key use case goes
first.
