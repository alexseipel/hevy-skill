#!/usr/bin/env python3
"""Measure prose only: punctuation budget, filler, paragraph length, sentence spread."""
import re, sys, statistics
from pathlib import Path

TELLS = ["delve","tapestry","landscape","realm","robust","seamless","leverage",
         "utilise","utilize","foster","unlock","harness","elevate","streamline",
         "empower","holistic","cutting-edge","game-changer","it's worth noting",
         "it's important to note","in today's world","plays a crucial role",
         "navigate the complexities","at its core","not just","but also",
         "in summary","in conclusion","seasoned developer","possibilities are endless",
         "serves as","acts as","is designed to","simply","just","easily",
         "significantly","greatly","extremely","comprehensive","that said"]

# Openers that delay the fact, and padding that carries none (SKILL.md §Concision).
FILLER = ["note that","it is worth noting","worth noting","in practice",
          "keep in mind","essentially","of course","importantly","simply put",
          "in other words","needless to say","as mentioned","as we saw",
          "it should be noted","basically","actually,","the fact that",
          "in order to","due to the fact","there is no need to","please note"]

MAX_SENTENCES_PER_PARAGRAPH = 3
MAX_MARKS = 2   # em dashes and semicolons share one budget


ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s")
CODE_SPAN = re.compile(r"`[^`]*`")
QUOTED = re.compile("[\"\u201c][^\"\u201d]*[\"\u201d]")


FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def split_frontmatter(text):
    """Frontmatter is not body prose, but its description spends the same budget."""
    match = FRONTMATTER.match(text)
    return (match.group(0), text[match.end():]) if match else ("", text)


def prose_blocks(text):
    """Prose paragraphs, with code, tables and headings dropped.

    Each list item is its own block: joining them invents sentences spanning
    two bullets. Backticked and quoted spans become placeholders, because a
    file listing the words it bans would otherwise flag every one of them.
    """
    blocks, current, in_code = [], [], False

    def flush():
        if not current:
            return
        # Cleaned after joining, because a quoted phrase can wrap across lines.
        clean = QUOTED.sub("QUOTE", CODE_SPAN.sub("CODE", " ".join(current)))
        blocks.append(clean.strip())
        current.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.lstrip().startswith(("|", "#")):
            continue
        if not line.strip():
            flush()
            continue
        if ITEM.match(line):
            flush()
        current.append(line.strip())
    flush()
    return blocks


def hit(term, text):
    """Whole-word match, so "just" is not found inside "adjust a summary"."""
    return re.search(rf"(?<!\w){re.escape(term.strip())}(?!\w)", text) is not None


def sentences(block):
    # A bold lead-in ends its sentence inside the markers: "**Do this.** Then that."
    return [s.strip() for s in re.split(r"(?<=[.!?])\**\s+", block)
            if len(s.split()) > 2]


breaches = 0

for path in sys.argv[1:]:
    front, body = split_frontmatter(Path(path).read_text())
    blocks = prose_blocks(body)
    prose = "\n".join(blocks)
    lower = prose.lower()
    every = [s for b in blocks for s in sentences(b)]
    lens = [len(s.split()) for s in every]
    if not lens:
        print(f"{path}\n   no prose"); continue

    budget = len(re.findall(r"—|;", prose + front))
    cov = statistics.pstdev(lens) / statistics.mean(lens) if len(lens) > 1 else 0
    words = len(prose.split())
    tells = sorted({t for t in TELLS if hit(t, lower)})
    fillers = sorted({f for f in FILLER if hit(f, lower)})
    # A bullet list is one block by construction, so only real paragraphs count.
    long_paragraphs = [b for b in blocks
                       if not b.lstrip().startswith(("-", "*", "1.", "2."))
                       and len(sentences(b)) > MAX_SENTENCES_PER_PARAGRAPH]

    over = budget > MAX_MARKS
    breaches += over
    print(f"{path}")
    print(f"   prose {words}w  sentences {len(lens)}  mean {statistics.mean(lens):.1f}  "
          f"CoV {cov:.2f}  budget {budget} ({'OVER' if over else 'ok'})")
    if tells:
        print(f"   TELLS: {', '.join(tells)}")
    if fillers:
        print(f"   FILLER: {', '.join(fillers)}")
    for b in long_paragraphs[:3]:
        print(f"   PARA ({len(sentences(b))} sentences): {b[:90]}")
    for s in [s for s in every if len(s.split()) > 30][:2]:
        print(f"   LONG ({len(s.split())}w): {s[:90]}")

# The budget is the one rule with no judgement in it, so it is the one that
# gates. Everything else prints for a person to weigh.
sys.exit(1 if breaches else 0)
