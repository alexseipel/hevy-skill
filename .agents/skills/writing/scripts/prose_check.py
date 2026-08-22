#!/usr/bin/env python3
"""Count the em-dash/semicolon budget and sentence-length spread in prose only."""
import re, sys, statistics
from pathlib import Path

TELLS = ["delve","tapestry","landscape","realm","robust","seamless","leverage",
         "utilise","utilize","foster","unlock","harness","elevate","streamline",
         "empower","holistic","cutting-edge","game-changer","it's worth noting",
         "it's important to note","in today's world","plays a crucial role",
         "navigate the complexities","at its core","not just","but also",
         "in summary","in conclusion","seasoned developer","possibilities are endless",
         "serves as","acts as","is designed to","simply ","just ","easily ",
         "significantly","greatly","extremely","comprehensive","that said"]

def prose_lines(text):
    out, in_code = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code; continue
        if in_code: continue
        if line.lstrip().startswith("|"): continue      # table row
        if re.match(r"^\s*[-*]\s*$", line): continue
        # An inline-code span is a mention, not a beat: `—` in backticks is the
        # character being discussed, not a pause being staged.
        out.append(re.sub(r"`[^`]*`", "CODE", line))
    return out

for path in sys.argv[1:]:
    text = Path(path).read_text()
    lines = prose_lines(text)
    prose = "\n".join(lines)
    budget = len(re.findall(r"—|;", prose))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\n+"," ",prose)) if len(s.split()) > 2]
    lens = [len(s.split()) for s in sentences]
    cov = (statistics.pstdev(lens)/statistics.mean(lens)) if len(lens) > 1 and statistics.mean(lens) else 0
    hits = sorted({t.strip() for t in TELLS if t.lower() in prose.lower()})
    over = [s for s in sentences if len(s.split()) > 30]
    flag = "OVER" if budget > 2 else "ok"
    print(f"{path}")
    print(f"   budget {budget} ({flag})  sentences {len(lens)}  mean {statistics.mean(lens):.1f}  CoV {cov:.2f}")
    if hits: print(f"   TELLS: {', '.join(hits)}")
    for s in over[:3]: print(f"   LONG ({len(s.split())}w): {s[:110]}")
