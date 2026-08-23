# Frontmatter

Two parts: what the open standard defines, and what a single host adds. Mixing
them is the most expensive mistake available here. It fails at packaging time,
long after the skill looked fine locally.

## The portable six

These six travel. The [Agent Skills](https://agentskills.io) standard allows
nothing else, and a skill built from them alone loads everywhere a skill can be
loaded, from a local directory to the Skills API.

| Field | Required | What it does |
| ----- | -------- | ------------ |
| `name` | no | display name in listings. Defaults to the directory name |
| `description` | recommended | what the skill does and when to load it. Falls back to the first paragraph |
| `license` | no | the licence covering the skill |
| `compatibility` | no | environment requirements, up to 500 characters |
| `metadata` | no | a free-form map for your own tooling to read |
| `allowed-tools` | no | tools granted without a permission prompt for the turn |

**Quote every value that holds free text.** An unquoted description containing
a colon followed by a space fails strict YAML parsers with "mapping values are
not allowed in this context". Claude Code parses leniently and masks the error,
so the file looks fine exactly where portability is not being tested.

## What happens when you exceed them

Claude Code accepts a longer list, including `when_to_use`, `argument-hint`,
`arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`,
`model`, `effort`, `context`, `agent`, `paths` and `shell`.

None of them degrades gracefully elsewhere. Upload to claude.ai, package with
`package_skill.py` or call the Skills API, and the file is rejected outright:

```
Unexpected key(s) in SKILL.md frontmatter: argument-hint.
Allowed properties are: allowed-tools, compatibility, description, license,
metadata, name
```

A skill restricted to the six still loads in Claude Code unchanged. So the
portable set costs nothing, while the extended set costs every other host. Reach
for an extension only when the skill is deliberately Claude Code only, and say
so in the `README`.

## `allowed-tools` is a permission grant

It pre-approves tools for the turn that invokes the skill, and the grant then
clears on the next user message.

**Grant the narrowest rule that does the job, or none.** A skill whose work is
HTTP calls needs at least `Bash(curl:*)`, reaching every host on the internet
without a prompt. That is the installer's decision, not the author's. Leave the
field unset and explain why in the repository.

## Naming

| Where the skill lives | What sets the command you type |
| --------------------- | ------------------------------ |
| personal or project `skills/` | the directory name. `name` is only a label |
| a plugin's `skills/` | frontmatter `name` or the directory, namespaced by plugin |
| a plugin root `SKILL.md` | frontmatter `name`, falling back to the plugin directory |

Keep `name` identical to the directory name. Divergence is legal in some of the
layouts above and confusing in all of them.

Lowercase kebab-case. It has to stay unique across everything a user might
install at once, which is why the published repositories all reach for a vendor
prefix: `hevy-api`, `venice-chat`, `alpaca-broker-trading-orders`.

## The description cap

Claude Code concatenates `description` with `when_to_use`, the extension, and
truncates the pair at **1,536 characters**. Anything past the cut is invisible
to the decision the description exists to inform. Put the key use case first.
