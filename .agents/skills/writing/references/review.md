# Reviewing a document

Two halves. The countable half is measured, never estimated, and
[prose_check.py](../scripts/prose_check.py) does the measuring. This file is
the other half: the seven rules no regex decides.

One document at a time, read the way a reader gets it, not as a diff.

## The output

One row per rule. A `breaks` verdict quotes the sentence, because a verdict
with no sentence under it is a guess.

| Rule                                  | Verdict | Sentence                                    |
| ------------------------------------- | ------- | ------------------------------------------- |
| 1 The first line answers the heading  | holds   |                                             |
| 6 No rule of three                    | breaks  | "fast, reliable and easy to use"            |

**No score and no aggregate.** The rules are not commensurable. A padded copula
and an unsourced claim about a status code do not trade against each other, and
averaging them hides which one fired.

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

**It exits 1 when any file is over the punctuation budget**, and 0 otherwise.
Everything else it prints is for a person to weigh.

It counts prose, not markup. Fenced code, table rows and headings are dropped
outright, and the frontmatter block is held back and counted for the budget
alone.

Inline code and quoted spans become placeholders, because a file listing the
words it bans would otherwise flag every one. Each list item is measured alone,
since joining them invents sentences spanning two bullets.

| Reading | Means |
| ------- | ----- |
| `budget` over 2 | the punctuation rule, and the only hard stop |
| `prose Nw` over the surface's budget | the file is doing two jobs ([surfaces.md](surfaces.md)) |
| `CoV` below about 0.35 | rule 7: every sentence the same length, the most measurable AI signal there is. Healthy technical prose here runs 0.45 to 0.65 |
| `TELLS` | a word to look at, not an automatic cut. Check the sentence |
| `FILLER` | an opener that delays the fact. Usually deletable outright |
| `PARA` | a paragraph past three sentences |
| `LONG` | a sentence past 30 words, against a ceiling of about 25 |

A `LONG` line made only of `CODE` placeholders is a list of identifiers rather
than a sentence, so read it before cutting.

Word repetition is deliberately not measured. "One concept, one word" is a rule
here, so a diversity score would flag the correct behaviour as a defect.

## The last pass

Close the source document and read yours. Anything you cannot now justify from
memory is either sourced somewhere you did not link, or it is not a fact.
