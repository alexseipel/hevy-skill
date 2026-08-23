# The surfaces

One register everywhere. What changes between surfaces is length, what counts as
a fact, and who is reading.

Length is a rule, not a preference ([SKILL.md](../SKILL.md#concision-comes-first)).
Measure it:

```bash
python3 .agents/skills/writing/scripts/prose_check.py <files>
```

`prose Nw` counts prose only. Tables, code blocks and headings are content and
do not spend the budget.

| Surface | Prose budget | Where the words go instead |
| ------- | ------------ | -------------------------- |
| README.md | 800w | a working example, and the table of what it does not cover |
| SKILL.md | 1100w | the endpoint table, then a link to a reference file |
| A reference file | 900w | field tables and one payload per route |
| A code comment | 1 line | the source it cites, on a second line |

Over budget means the file is doing two jobs. Split it or cut it, and never
delete a fact to hit a number.

One file stands outside this. `reference/observed.md` runs to roughly 1,400
words because it catalogues sixteen spec disagreements, and splitting it would
scatter corrections a reader needs together.

## README.md

Thirty seconds, and someone decides whether to install this.

- **The first sentence says what the skill does and for which API.**
- **A working example above the fold**, running as written.
- **Say what it does not cover.** A README listing only capabilities is an
  advertisement, and the reader finds the gap later at a worse moment.
- No badge wall, no adjective-only "Features" section, no roadmap of things
  that do not exist.

## SKILL.md

A model with a budget reads it. Every token of preamble is one not spent on the
task.

- **The description field is a trigger, not a summary.** Third person, naming
  the words a user would type.
- **Instructions, not prose about instructions.** "Call `GET /v1/workouts`
  with `page` starting at 1" beats a paragraph on pagination.
- **Front-load auth, base URL, and the gotcha that breaks the first call.**
- **Anything longer than a screen moves to a reference file**, linked from the
  line that needs it.

## Reference files

Entered mid-document, by a model that followed a link for one answer.

- **Tables over paragraphs** wherever the content is a mapping.
- **Matching columns** across tables describing the same kind of thing.
- **No cross-file narrative.** A reference file is entered in the middle.

## Code comments

- **Comment the why.** The what is in the code and goes stale on the first
  refactor.
- **One line.** A second line only to carry a source, as a link or a file
  reference. That is the comment worth writing, because the next reader cannot
  derive it.
- **No section banners**, no `# --- helpers ---`, no sentence above a function
  repeating its signature.
- **No commented-out code.**

## Commit messages

- **Subject: imperative, under 72 characters, no full stop.** "Add cursor
  paging to routine fetch".
- **Body says why, and what would break without it.** Skip it when the subject
  is the whole fact.
- **No conventional-commit prefix unless the repo already uses one.**

## PR descriptions

- **What changed, why, and how it was verified.** The third is the part people
  leave out and the reviewer needs most.
- **Name what you did not do**, where the scope looks like it should have
  covered it.
