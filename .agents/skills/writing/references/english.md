# English

One language ships from this repo. That removes the translation problem and
leaves the harder one: English is the language language models were trained
hardest on, so it produces the densest, most recognisable tells.

|             |                                                                                                          |
| ----------- | -------------------------------------------------------------------------------------------------------- |
| Address     | you, for anything the reader does. Never "we", never "one"                                               |
| Spelling    | one variety per document, and en-GB across the repo. `-ise`, not `-ize`                                  |
| Typography  | curly quotes in prose, straight quotes inside code; en dash for numeric ranges; no space around the en dash |
| Dates       | ISO 8601 in anything a machine might read, `22 August 2026` in running prose. Never `08/22/2026`         |
| Terminology | Hevy's own names for Hevy's own things: `routine`, `workout`, `exercise template`, `set`                 |

## The tells

**Words**, each a literal string worth grepping for: `delve`, `tapestry`,
`landscape`, `realm`, `robust`, `seamless`, `leverage` (as a verb), `utilise`,
`foster`, `unlock`, `harness`, `elevate`, `streamline`, `empower`,
`comprehensive`, `holistic`, `cutting-edge`, `game-changer`, and `ensure` where
"make sure" or nothing would do.

**Phrases.** "it's worth noting", "it's important to note", "in today's
world", "plays a crucial role", "navigate the complexities", "at its core",
"under the hood" (as decoration rather than as a real contrast with the
surface), "not just X but Y", "whether you're a beginner or a seasoned
developer", "the possibilities are endless".

**Shapes**, which survive after the words are gone and matter more:

- The tricolon: three items, three clauses, three bullets, when the facts had
  two or five.
- The mirrored bullet list, where every entry opens with a bold noun phrase
  and runs the same length.
- The pivot sentence: "But here's the thing", "That said", "The catch?"
- The rhetorical question as a heading, answered immediately underneath.
- The closing gesture: a final paragraph that repeats the opening in warmer
  words.
- Uniform paragraph length down the whole document.

## Technical English

- **The subject of a sentence about code is the code.** "`getWorkouts` returns
  an empty `events` array", not "You will find that the response will contain
  an empty array".
- **Present tense for behaviour.** "The endpoint returns 404", not "will
  return".
- **Imperative for instructions.** "Set `HEVY_API_KEY`", not "You should set"
  and not "You'll want to set".
- **Say what fails.** An error section that lists status codes without saying
  which call produces them is decoration.
- **Backticks are for things you can type**: identifiers, paths, values,
  headers. Not for emphasis.
- **No apology and no reassurance.** "Don't worry", "simply", "just", and
  "easily" all tell the reader how to feel about a step instead of telling
  them the step.

## The check that catches what a list cannot

Read the document aloud, or at least sub-vocally, from the top. The tells that
survive a word-level pass are rhythmic, and rhythm is audible where it is
invisible. A document that sounds like a narrator rather than a colleague has
one of the shapes above in it, and reading it out is how you find which.
