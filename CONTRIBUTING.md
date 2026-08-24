# Contributing

Changes arrive as pull requests against `main`. The conventions the repository
is built under, including how a new endpoint gets documented, are in
[AGENTS.md](AGENTS.md).

## Run the checks first

```bash
python3 scripts/validate_skill.py && python3 scripts/check_coverage.py
python3 scripts/build_corrected_spec.py --check
python3 -m unittest discover -s tests
```

All four run in CI and gate the merge.

## What a change carries

- Source every claim. The tier table in `.agents/skills/writing` says what
  counts as one.
- Behaviour the spec does not document is marked as observed, with a date, and
  gains a check in `skills/hevy-api/scripts/verify_live.py` in the same commit.
- The key comes from `HEVY_API_KEY` and never appears in a file.
- Measure any prose you touched. The script takes the files as arguments and
  reports nothing when given none:

```bash
python3 .agents/skills/writing/scripts/prose_check.py README.md skills/hevy-api/SKILL.md
```

Contributions are accepted under the MIT licence in [LICENSE](LICENSE).
