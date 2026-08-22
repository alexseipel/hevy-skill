# Reviewing a document

Two halves. The countable one is the punctuation budget and the sentence
lengths, and you count those rather than estimating them. This file is the
other half: the seven rules no regex decides.

One document at a time, read the way a reader gets it, not as a diff.

## The output

One row per rule. A `breaks` verdict quotes the sentence, because a verdict
with no sentence under it is a guess.

| Rule                                  | Verdict | Sentence                                    |
| ------------------------------------- | ------- | ------------------------------------------- |
| 1 The first line answers the heading  | holds   |                                             |
| 6 No rule of three                    | breaks  | "fast, reliable and easy to use"            |

**No score and no aggregate.** The rules are not commensurable. A padded
copula and an unsourced claim about a status code do not trade against each
other, and averaging them hides which one fired.

## What to look for

| Rule                                      | Where it hides                                                     |
| ----------------------------------------- | ------------------------------------------------------------------ |
| 1 First line answers the heading          | the first sentence under every `##`, not only the opening one      |
| 2 Every claim ends on something checkable | any sentence with no identifier, number, status code or path in it |
| 6 No rule of three                        | lists of exactly three where the API has two or five               |
| 9 No mirrored sections                    | `##` blocks of the same length that open the same way              |
| 10 No summary paragraph                   | the last paragraph. Read it alone: does it carry a fact?           |
| 11 The verb is "is" when the fact is "is" | "serves as", "acts as", "is designed to", "allows you to"          |
| 12 No participle padding                  | a trailing clause after a comma that names no fact                 |

Rules 3, 4, 5, 7 and 8 are matters of degree. Handle them in the same pass by
measure rather than verdict.

## The countable half

```bash
python3 .agents/skills/writing/scripts/prose_check.py FILE...
```

It strips code blocks, inline code and table rows first. A `—` in a table cell
is a separator, and a `;` inside a shell snippet is syntax. A bare
`grep -o '—\|;'` counts both and reports a breach that is not there.

It prints three things per file: the budget, the sentence-length coefficient of
variation, and any tell from [english.md](english.md) that appears in the text.

- **Budget over 2** is the punctuation rule, and it is a hard stop.
- **CoV below about 0.35** is rule 7: the sentences are all the same length,
  which is the most measurable AI signal there is. Healthy technical prose here
  runs 0.45 to 0.65.
- **A tell** is a word to look at, not an automatic cut. Check the sentence.

Headings that carry no prose under them get joined to the next sentence, so a
long-sentence flag that starts with `##` is an artifact rather than a finding.

Word repetition is deliberately not measured. "One concept, one word" is a
rule here, so a diversity score would flag the correct behaviour as a defect.

## The last pass

Close the source document and read yours. Anything you cannot now justify from
memory is either sourced somewhere you did not link, or it is not a fact.
