# The surfaces

Every surface in this repo takes the same register. They differ in length,
in what counts as a fact, and in who is reading.

## README.md

The reader is deciding whether to install this. They give it thirty seconds.

- **The first sentence says what the skill does and for which API.** Not what
  skills are, not why the Hevy API is interesting.
- **Working example above the fold**, and the example runs as written.
- **Say what it does not cover.** A README that lists only capabilities is an
  advertisement, and the reader finds the gap later at a worse moment.
- No badge wall, no "Features" section of adjectives, no roadmap of things
  that do not exist.

## SKILL.md

The reader is a model with a budget, and every token spent on preamble is a
token not spent on the task.

- **The description field is a trigger, not a summary.** It says what the
  skill covers and when to reach for it, in the third person, and it names the
  words a user would actually type.
- **Instructions, not prose about instructions.** "Call `GET /v1/workouts`
  with `page` starting at 1" beats a paragraph describing pagination.
- **Front-load the operational facts**: auth, base URL, the one gotcha that
  breaks the first call.
- **Anything longer than a screen moves to a reference file**, linked from the
  line that needs it.

## Reference files

The reader is a model that followed a link because it needs one specific
answer.

- **Tables over paragraphs** wherever the content is a mapping.
- **Every table has the same columns as the other tables** describing the same
  kind of thing.
- **No cross-file narrative.** A reference file is entered in the middle and
  has to work from there.

## Code comments

- **Comment the why.** The what is in the code, and a comment restating it
  goes stale on the first refactor.
- **A comment that explains a non-obvious API fact carries its source**, as a
  link or a doc reference. That is the comment worth writing, because the next
  reader cannot derive it from anywhere.
- **No section-banner comments**, no `# --- helpers ---`, no comment above a
  function that repeats its signature in a sentence.
- **No commented-out code.** Delete it.

## Commit messages

- **Subject: imperative, under 72 characters, no full stop.** "Add cursor
  paging to routine fetch".
- **Body says why, and what would break without it.** Skip the body when the
  subject is the whole fact.
- **No conventional-commit prefix unless the repo already uses one.** Check
  before assuming.

## PR descriptions

- **What changed, why, and how it was verified.** The third one is the part
  people leave out and the reviewer needs most.
- **Name what you did not do**, and why, where the scope looks like it should
  have covered it.
