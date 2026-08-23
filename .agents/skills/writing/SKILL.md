---
name: writing
description: "House style for every English word this repo ships: README, SKILL.md and its references, code comments, commit messages, PR text. Sources every factual claim, keeps prose out of the AI register, and holds the line on concision. Use before writing or editing any prose here, down to a single comment."
license: MIT
---

# Writing

One register, every surface, English only. That includes examples, sample
payloads and fixture data.

Per-surface length and shape: [references/surfaces.md](references/surfaces.md).

## Concision comes first

**A skill file is loaded into context on every invocation.** Its length is a
cost every user pays again, unlike a README read once. Long prose is not a
style flaw here, it is a bill.

1. **Cut any sentence carrying no fact.** Delete it and check: if nothing
   checkable is lost, it stays deleted.
2. **State a rule once.** The restatement is the padding.
3. **Give the reason only when it changes what the reader does.**
4. **One example, never two of the same shape.**
5. **Three sentences per paragraph.** One sentence of prose between two tables.
6. **No opener that delays the fact**: "Note that", "It is worth noting", "In
   practice", "Keep in mind", "Essentially", "Of course", "Importantly",
   "That said", "Simply put".
7. **A code comment is one line.** Two only when the second carries a source.

**Cut words, never claims.** A shorter sentence that drops a qualifier the API
sets is not concision, it is a wrong sentence. Facts, dates, tier-2 markers and
the conditions a claim hangs on survive every edit.

## Order of work

**Source, then sentence, then style.** A sentence written first and sourced
afterwards gets matched to whatever agrees with it.

1. Find the document. Read the passage, not a summary of it.
2. Write the sentence that passage supports. No more.
3. Cut the AI out of it.
4. Link it while the tab is still open.

A fact you cannot source is a gap, written down as one: `<!-- UNVERIFIED: -->`
in prose, `TODO(unverified):` in code. Never a guess. A gap gets fixed by the
next person; a guess gets trusted and copied into a caller's code.

## What a claim may rest on

Take the highest tier that covers the claim.

| Tier | What | Use for |
| ---- | ---- | ------- |
| 1 | The Hevy API reference at `api.hevyapp.com/docs` and the OpenAPI document it serves | every statement about a route, parameter, field, status code or default |
| 2 | A response you captured yourself, kept with the request that produced it | behaviour the reference omits: pagination edges, error bodies, limits |
| 3 | Hevy's own product and support pages | product facts: what a plan includes, what the app calls a thing |

**Never a source:** a blog post, a Stack Overflow answer, another wrapper
library's README, a changelog someone else summarised, or a language model's
recollection of an API.

**Tier 2 says so in the text.** "Observed against the live API on 2026-08-22,
not documented" carries a shelf life the reader needs to see. An observation
dressed as documentation is the most expensive sentence in a reference file.

## Numbers

| Rule | Instead of | Write |
| ---- | ---------- | ----- |
| Every number carries its unit and scope | "the limit is 10" | "`pageSize` accepts 1 to 10 on `/v1/workouts`" |
| A range is written as a range | "up to 10" | "1 to 10, default 5" |
| No number without a source | "rate limited to ~60/min" | the documented figure, or no sentence |
| Round the way the source rounds | "roughly 300" | the source's own figure |

Cut any number nobody can trace.

## Plain language

The reader is a developer who has never used Hevy and wants one answer.

- **One concept, one word.** A `workout` is a `workout` in every file, never a
  "session", "training", "log" or "entry" for variety.
- **A term is explained once, in the sentence that first uses it.**
- **Verbs, not nouns.** "when you upload a workout", not "in the case of a
  workout upload".
- **One question per heading, answered in the first line under it.**
- **Uncertainty is named, not hedged.** "The reference does not state what
  happens past page 100" is a fact. "may potentially behave differently" is
  nothing.
- **Sentence ceiling: about 25 words.** Code comments run shorter.
- **Second person for instructions, never "we".**

## Prose

Twelve rules.

1. **The first line answers the heading.** No "In this section we will
   explore".
2. **Every claim ends on something checkable.** WRONG: "This significantly
   improves reliability." RIGHT: "Retries cover 429 and 5xx, up to three
   attempts."
3. **No intensifiers.** "significantly", "greatly", "extremely important"
   stand where the number belongs.
4. **Active voice, named subject.** No "it is recommended". Name who
   recommends, or state the rule.
5. **No "not only X, but also Y".** State Y.
6. **No rule of three.** Use the number of items the facts have. Two is
   normal, four is fine.
7. **Vary sentence length.** Uniform length is the most measurable AI signal
   there is.
8. **No parataxis chain.** Where the logic is causal or conditional, say so in
   a subordinate clause.
9. **No mirrored sections.** Vary how each `##` block opens and how long it
   runs.
10. **No summary paragraph.** Stop at the last fact.
11. **The verb is "is" when the fact is "is".** "serves as", "acts as" and "is
    designed to" pad a copula into a clause.
12. **No participle padding.** "..., ensuring reliable delivery" adds a clause
    and no fact.

**Em dash and semicolon share one budget: two marks per document, counted
together.** Both stage the same pause and both read as machine-written. A full
stop or a colon does the same work. A separator inside a table cell and
anything inside a code block are not beats, and the frontmatter `description`
spends from the same budget as the body.

Read the English tells before the last pass:
[references/english.md](references/english.md).

## Where the two rule sets collide

Accuracy wins on substance, anti-slop wins on form.

| Anti-slop says | Technical writing says | Resolution |
| -------------- | ---------------------- | ---------- |
| Pick a side, cut hedges | Represent uncertainty honestly | Delete authorial hedges. Keep named uncertainty: which endpoint, which case |
| Vary the wording | One concept, one word | Terminology is fixed. Vary sentence shape instead |
| Cut qualifiers and adverbs | The API's scope has to survive | Keep a qualifier the API sets. Cut yours |
| Be concrete, use numbers | No number without a source | An unsourced number is not concreteness. Cut it |
| Short, punchy sentences | Precision | Split for length, never by dropping a condition |
| Show, don't tell | An example is one case, not a spec | State the rule, then show one example |

## Before you call it done

```bash
python3 .agents/skills/writing/scripts/prose_check.py <files>
```

- [ ] every factual sentence traced to a tier 1, 2 or 3 source, tier 2 marked
- [ ] no sentence claims more than its source does
- [ ] no unmarked gap where a fact was unavailable
- [ ] the judgement rules walked one by one
      ([references/review.md](references/review.md))
- [ ] `prose_check.py` clean: budget, filler, paragraph length
- [ ] read once from the top as a reader gets it, not as a diff
