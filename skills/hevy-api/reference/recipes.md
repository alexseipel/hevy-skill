# Recipes

The API answers one resource at a time. Everything people actually ask for
spans several calls, and the joins have to happen client-side. Each recipe
below is implemented in [../scripts/hevy.py](../scripts/hevy.py), so read the
algorithm here and call the command when a shell is available.

## Finding an exercise by name

There is no search route. The catalogue is about 500 entries over 5 pages at
`pageSize=100`, and it changes only when Hevy ships new exercises.

1. Page `/v1/exercise_templates` once at `pageSize=100`.
2. Cache the result on disk.
3. Match titles locally, case-insensitively, on a substring.

```bash
python3 scripts/hevy.py templates --search "bench press"
python3 scripts/hevy.py templates --search curl --muscle biceps
python3 scripts/hevy.py templates --refresh --search squat
```

Titles carry the equipment in brackets, so `Bench Press` alone matches
fourteen entries across barbell, dumbbell, cable, Smith machine and more. Show
the matches and let the user pick rather than guessing.

## Training summary over a period

Volume, set counts and a muscle-group split are computed here, not returned.

1. Walk `/v1/workouts` newest first, stopping at the first page whose last
   workout starts before the window ([observed.md](observed.md#ordering-which-the-spec-never-states)).
2. Join each exercise to the cached catalogue on `exercise_template_id` to get
   `primary_muscle_group`.
3. Sum `weight_kg * reps` per set, skipping `type: "warmup"`.
4. Page `/v1/body_measurements` and take the newest and oldest inside the
   window.

```bash
python3 scripts/hevy.py summary --weeks 4
```

**Skip warmup sets from volume.** Including them inflates the number by roughly
a fifth and makes week-to-week comparison meaningless.

**A null weight change with a latest reading is not a flat weight.** It means
the window holds no measurement at all.

## Turning a routine into a logged workout

The routine holds the plan. The workout holds what happened, and the API will
not invent the difference.

1. `GET /v1/routines/{routineId}`, remembering the result is wrapped in
   `{"routine": …}`.
2. Ask the user for the actual sets: weight, reps, and the start and end time.
3. Build the workout body from the routine's `exercise_template_id` and
   `superset_id`, and the user's numbers.
4. `POST /v1/workouts`.

Drop `rest_seconds` and `rep_range`, which exist on a routine set and not on a
workout set. Never carry a routine's planned weight into a workout as though it
were performed.

## Progress on one exercise

`GET /v1/exercise_history/{exerciseTemplateId}` returns every logged set, one
row per set, unpaginated. Bound it with `start_date` and `end_date`.

```bash
python3 scripts/hevy.py history 79D0BB3A --start 2026-01-01T00:00:00Z
```

Rows carry no set index, so group by `workout_id` and keep the order the API
returns.

## Keeping a local copy in step

1. Store the timestamp before the run starts.
2. Page `/v1/workouts/events?since=<last watermark>` to the end.
3. Upsert on `type: "updated"`, delete on `type: "deleted"`.
4. Save the stored timestamp as the new watermark.

Taking the timestamp first is what stops a workout written during the run from
being missed. `/v1/workouts` alone never reports a deletion.

## Editing without losing data

`PUT /v1/body_measurements/{date}` overwrites: the spec says omitted fields
become `null`. Treat `PUT /v1/workouts/{workoutId}` the same way, because it
takes the full create body and the spec does not say whether omitted exercises
survive.

Read the current object, change the one field, and send the whole thing back.
For a measurement, drop `date`, `id` and `created_at` first, because
`PutBodyMeasurement` has none of them.

The client refuses a write without `--yes`, because the API has no delete
route and a mistake is permanent.

## Querying with SQL, when the user has asked for it

The local mirror is off by default and this recipe does not apply until the
user turns it on. Never suggest it unprompted ([SKILL.md](../SKILL.md#the-local-mirror-is-off-and-stays-off-unless-asked)).

Once enabled, `performed_sets` is one row per performed set, joined to its
workout and exercise, with `volume_kg` precomputed:

```sql
SELECT substr(start_time, 1, 7) AS month,
       ROUND(MAX(weight_kg * (1 + reps / 30.0)), 1) AS best_e1rm_kg
FROM performed_sets
WHERE exercise_title LIKE 'Bench Press%' AND set_type != 'warmup' AND reps > 0
GROUP BY month ORDER BY month DESC;
```

`weight_kg * (1 + reps / 30.0)` is the Epley estimate, and it drifts high above
about ten reps. Filter warmup sets out of anything measuring volume or effort.

**The mirror is never authoritative for writes.** It is derived, disposable and
rebuildable with `hevy.py sync --full`, which is what makes querying it safe.
