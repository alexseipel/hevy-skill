#!/usr/bin/env python3
"""Re-check the claims in reference/observed.md against the live API.

    HEVY_API_KEY=... python3 verify_live.py

Read-only. It calls no write route, because the Hevy API has no delete route
and test data in a real account is permanent.

Every check names the claim it is testing, so a failure says which line of the
documentation went stale rather than only that something changed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.hevyapp.com"
results: list[tuple[bool, str, str]] = []


def call(path: str, **params) -> tuple[int, object]:
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"api-key": os.environ["HEVY_API_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode()
            return response.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:200]


def check(claim: str, expected, actual) -> None:
    results.append((expected == actual, claim, f"expected {expected!r}, got {actual!r}"))


def main() -> int:
    if not os.environ.get("HEVY_API_KEY"):
        sys.exit("HEVY_API_KEY is not set.")

    caps = {"/v1/workouts": 10, "/v1/workouts/events": 10, "/v1/routines": 10,
            "/v1/routine_folders": 10, "/v1/exercise_templates": 100,
            "/v1/body_measurements": 10}
    for path, cap in caps.items():
        check(f"{path} accepts pageSize={cap}", 200, call(path, pageSize=cap)[0])
        check(f"{path} rejects pageSize={cap + 1}", 400, call(path, pageSize=cap + 1)[0])

    defaults = {"/v1/workouts": ("workouts", 10), "/v1/routines": ("routines", 10),
                "/v1/exercise_templates": ("exercise_templates", 100),
                "/v1/routine_folders": ("routine_folders", 5),
                "/v1/body_measurements": ("body_measurements", 10)}
    for path, (key, expected) in defaults.items():
        _, body = call(path)
        got = len(body.get(key, [])) if isinstance(body, dict) else None
        # An account with fewer entries than the default returns fewer, which is
        # not a failed claim about the default.
        page_count = body.get("page_count") if isinstance(body, dict) else 0
        if page_count and page_count > 1:
            check(f"{path} default pageSize is {expected}", expected, got)

    check("page=0 returns page 1", (200, 1),
          (lambda s, b: (s, b.get("page")))(*call("/v1/workouts", page=0, pageSize=1)))
    check("page=-1 is rejected", 400, call("/v1/workouts", page=-1, pageSize=1)[0])
    check("page past the end is 404", 404, call("/v1/workouts", page=99999)[0])
    check("pageSize=0 is accepted", 200, call("/v1/workouts", pageSize=0)[0])

    _, listing = call("/v1/workouts", pageSize=1)
    workout_id = listing["workouts"][0]["id"]
    _, workout = call(f"/v1/workouts/{workout_id}")
    check("GET /v1/workouts/{id} is not wrapped", False, list(workout.keys()) == ["workout"])
    check("the workout response has no is_private", False, "is_private" in workout)
    check("Workout.routine_id may be null", True,
          "routine_id" in listing["workouts"][0])

    exercise = workout["exercises"][0]
    check("workout exercises use superset_id", True, "superset_id" in exercise)
    check("workout exercises do not use supersets_id", False, "supersets_id" in exercise)

    _, routines = call("/v1/routines", pageSize=1)
    if routines.get("routines"):
        _, one = call(f"/v1/routines/{routines['routines'][0]['id']}")
        check("GET /v1/routines/{id} is wrapped in routine", ["routine"], list(one.keys()))
        rex = one["routine"]["exercises"][0]
        check("routine exercises use superset_id", True, "superset_id" in rex)
        check("rest_seconds is an integer", "int", type(rex.get("rest_seconds")).__name__)
        check("routine sets carry rep_range", True, "rep_range" in rex["sets"][0])

    _, templates = call("/v1/exercise_templates", pageSize=1)
    template = templates["exercise_templates"][0]
    check("templates use equipment", True, "equipment" in template)
    check("templates do not use equipment_category", False, "equipment_category" in template)

    template_id = exercise["exercise_template_id"]
    _, history = call(f"/v1/exercise_history/{template_id}")
    _, paged = call(f"/v1/exercise_history/{template_id}", page=1, pageSize=1)
    check("exercise history ignores paging",
          len(history["exercise_history"]), len(paged["exercise_history"]))

    _, measurements = call("/v1/body_measurements", pageSize=1)
    if measurements.get("body_measurements"):
        entry = measurements["body_measurements"][0]
        check("measurements carry an undocumented id", True, "id" in entry)
        check("measurements carry created_at", True, "created_at" in entry)
        check("unrecorded measurement fields are omitted", False, "neck_cm" in entry)
    check("a missing measurement date is 404", 404, call("/v1/body_measurements/1990-01-01")[0])

    _, folders = call("/v1/routine_folders", pageSize=1)
    if folders.get("routine_folders"):
        check("folder ids are integers", "int",
              type(folders["routine_folders"][0]["id"]).__name__)

    check("an unknown workout id is 404", 404,
          call("/v1/workouts/00000000-0000-0000-0000-000000000000")[0])

    failed = [r for r in results if not r[0]]
    for ok, claim, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {claim}" + ("" if ok else f"\n         {detail}"))
    print(f"\n{len(results) - len(failed)}/{len(results)} claims hold.")
    if failed:
        print(f"{len(failed)} claim(s) no longer hold. Update "
              f"reference/observed.md.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
