---
name: writing
description: House style for every English word this repo ships — README, SKILL.md and its references, code comments, commit messages, PR text. Ties every factual claim to the document that supports it, keeps the prose out of the AI register, and carries the English tells worth hunting. Use before writing or editing any prose here, down to a single comment.
license: MIT
---

# Writing

One register, every surface. A code comment gets the same treatment as the
README, because the same developer reads both in the same minute and judges the
skill by whichever one they hit first.

**English only.** No other language ships from this repo, including in
examples, sample payloads and fixture data.

Per-surface length and shape: [references/surfaces.md](references/surfaces.md).

## Order of work

**Source, then sentence, then style.** A sentence written first and sourced
afterwards gets matched to whatever agrees with it, which is how a plausible
wrong claim about an endpoint enters a document and never leaves.

1. Find the document. Read the passage, not a summary of it, and not your
   memory of the last API that looked like this one.
2. Write the sentence that passage supports. No more.
3. Cut the AI out of it.
4. Link it while the tab is still open.

A fact you cannot source is a gap, and a gap is written down as one:
`<!-- UNVERIFIED: ... -->` in prose, `TODO(unverified):` in code. Never a
guess. A gap gets fixed by the next person who touches the file; a guess gets
trusted, copied into a caller's code, and found in production.

## What a claim may rest on

Take the highest tier that covers the claim.

| Tier | What                                                                            | Use for                                                                    |
| ---- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 1    | The Hevy API reference at `api.hevyapp.com/docs` and the OpenAPI document it serves | every statement about a route, parameter, field, status code or default |
| 2    | A response you captured yourself, kept together with the request that produced it | behaviour the reference leaves out: pagination edges, error bodies, limits |
| 3    | Hevy's own product and support pages                                            | product facts, such as what a plan includes or what the app calls a thing  |

**Never a source:** a blog post, a Stack Overflow answer, another wrapper
library's README, a changelog someone else summarised, or a language model's
recollection of an API it has seen.

**Tier 2 says so in the text.** "Observed against the live API on 2026-08-22,
not documented" is a fact with a shelf life, and the reader needs to know it
carries one. An observation dressed as documentation is the most expensive
sentence in a reference file.

## Numbers

| Rule                                    | Instead of                | Write                                                       |
| --------------------------------------- | ------------------------- | ----------------------------------------------------------- |
| Every number carries its unit and scope | "the limit is 10"         | "`pageSize` accepts 1 to 10 on `/v1/workouts`"              |
| A range is written as a range           | "up to 10"                | "1 to 10, default 5"                                        |
| No number without a source              | "rate limited to ~60/min" | the documented figure, or no sentence at all                |
| Round the way the source rounds         | "roughly 300"             | the source's own figure                                     |

A number nobody can trace is not concreteness, it is invention wearing its
clothes. Cut the sentence.

## Plain language

The reader is a developer who has never used Hevy, is three tabs deep into
something else, and wants one answer. Plain does not mean thin: it means the
claim survives intact at a lower reading cost.

- **One concept, one word.** A `workout` is a `workout` in every file. Never a
  "session", a "training", a "log" or an "entry" because the paragraph already
  said "workout" twice.
- **A term is explained once, in the sentence that first uses it**, and the
  plain word carries the rest.
- **Verbs, not nouns.** "when you upload a workout", not "in the case of a
  workout upload".
- **One question per heading, answered in the first line under it.** Whoever
  stops reading there still has the answer.
- **Uncertainty is named, not hedged.** "The reference does not state what
  happens past page 100" is a fact. "may potentially behave differently" is
  nothing.
- **Sentence ceiling: about 25 words.** Code comments run shorter.
- **Second person for instructions, never "we".** The reader acts. The repo
  does not accompany them.

## Prose

Twelve rules. They are the whole difference between text a developer trusts
and text they skim past.

1. **The first line answers the heading.** No "In this section we will
   explore", no "Authentication is an important topic".
2. **Every claim ends on something checkable.** WRONG: "This significantly
   improves reliability." RIGHT: "Retries cover 429 and 5xx, up to three
   attempts."
3. **No intensifiers.** "significantly", "greatly", "extremely important" are
   placeholders standing where the number belongs.
4. **Active voice, named subject.** No "it is recommended". Name who
   recommends, or state the rule.
5. **No "not only X, but also Y".** State Y.
6. **No rule of three.** Use the number of items the facts have. Two is
   normal, and four is fine.
7. **Vary sentence length.** Uniform length is the most measurable AI signal
   there is. A wall of 22-word sentences fails as badly as a wall of 6-word
   ones.
8. **No parataxis chain.** Three blunt statements in a row read as machine
   output. Where the logic is causal or conditional, say so in a subordinate
   clause.
9. **No mirrored sections.** Vary how each `##` block opens and how long it
   runs.
10. **No summary paragraph.** Stop at the last fact. "In summary" introduces a
    paragraph that adds none.
11. **The verb is "is" when the fact is "is".** "serves as", "acts as",
    "functions as" and "is designed to" pad a copula into a clause.
12. **No participle padding.** "..., ensuring reliable delivery" adds a clause
    and no fact. Name the fact it stood in for, or cut it.

**Em dash and semicolon share one budget: two marks per document, counted
together.** Both stage the same pause, and both read as machine-written, so
spending the budget on one leaves nothing for the other. A full stop or a colon
does the same work, and where the logic is causal a subordinate clause does it
better. The budget counts marks that stage a beat in running prose. A separator
inside a table cell and anything inside a code block are not beats, and the
frontmatter `description` spends from the same budget as the body.

Read the English tells before the last pass:
[references/english.md](references/english.md).

## Where the two rule sets collide

Anti-slop and technical accuracy pull against each other in six places. Each
resolves the same way: accuracy wins on substance, anti-slop wins on form.

| Anti-slop says             | Technical writing says            | Resolution                                                                             |
| -------------------------- | --------------------------------- | -------------------------------------------------------------------------------------- |
| Pick a side, cut hedges    | Represent uncertainty honestly    | Delete authorial hedges. Keep named uncertainty: which endpoint, which case, undocumented |
| Vary the wording           | One concept, one word             | Terminology is fixed. Vary sentence shape instead                                      |
| Cut qualifiers and adverbs | The API's scope has to survive    | Keep a qualifier the API sets, such as "for the authenticated user only". Cut yours    |
| Be concrete, use numbers   | No number without a source        | An unsourced number is not concreteness. Cut it                                        |
| Short, punchy sentences    | Precision                         | Split for length, never by dropping the condition a claim hangs on                     |
| Show, don't tell           | An example is one case, not a spec | State the rule, then show one example that does not stand in for it                    |

## Before you call it done

- [ ] every factual sentence traced to a tier 1, 2 or 3 source, and tier 2
      marked as observed
- [ ] no sentence claims more than its source does
- [ ] no unmarked gap left where a fact was unavailable
- [ ] the judgement rules walked one by one
      ([references/review.md](references/review.md))
- [ ] the em dash and semicolon budget counted, not estimated
- [ ] read once from the top as a reader gets it, not as a diff
