# Recipes

The API answers one resource at a time, so anything people ask for spans
several calls and joins client-side. Each recipe is implemented in
[../scripts/hevy.py](../scripts/hevy.py): read the algorithm here, call the
command when a shell is available.

## Finding an exercise by name

There is no search route. The catalogue is about 500 entries over 5 pages at
`pageSize=100`, changing only when Hevy ships new exercises.

1. Page `/v1/exercise_templates` once at `pageSize=100`.
2. Cache the result on disk.
3. Match titles locally, case-insensitively, on a substring.

```bash
python3 scripts/hevy.py templates --search "bench press"
python3 scripts/hevy.py templates --search curl --muscle biceps
python3 scripts/hevy.py templates --refresh --search squat
```

Titles carry the equipment in brackets, so `Bench Press` matches fourteen
entries. Show them and let the user pick rather than guessing.

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
python3 scripts/hevy.py summary --weeks 4 --unit lb
```

**Skip warmup sets from volume.** Including them inflates it by roughly a fifth.

**Say what unit the figures are in.** The API answers in kilograms and reports
nothing about what the account displays ([objects.md](objects.md#units)).
`--unit lb` renames every key as it converts, so a `volume_lb` cannot be read as
a `volume_kg`.

**A null weight change with a latest reading is not a flat weight.** The window
holds no measurement at all.

## Dumbbell weight is the total, and nothing enforces it

Hevy's app tells a user to log the total lifted per rep, so a pair of 10 kg
dumbbells is entered as 20 kg. Plenty of people enter one hand instead. The API
stores both identically and flags neither, so an account logging per hand
reports half the dumbbell volume it did.

**You cannot tell which from the data.** A weight that could only be per hand
needs a rack carrying half-increments. Its absence says nothing, and most
accounts never produce one, so treat the convention as unknown.

One weak hint: a movement logged both with a barbell and with dumbbells shows
the dumbbell figure near half its barbell counterpart, which is arithmetically
what logging one hand does. The two lifts differ anyway, so it settles nothing.

**Say which convention a number assumes, and ask when it matters.** Reporting
"31,000 kg of volume, counting dumbbell weights as logged" lets the user catch a
mismatch at once. It matters for a volume figure, a muscle-group split, or a
dumbbell lift compared against anything else. Trends survive either convention,
since halving every entry leaves the curve's shape alone.

**Never correct it yourself.** Do not double a weight, adjust a summary, or
rewrite the sets. The convention is theirs to name, and changing history means a
`PUT` over every affected workout with no undo.

## Turning a routine into a logged workout

The routine holds the plan, the workout what happened. The API will not invent
the difference.

1. `GET /v1/routines/{routineId}`, remembering the result is wrapped in
   `{"routine": …}`.
2. Ask the user for the actual sets: weight, reps, and the start and end time.
3. Build the workout body from the routine's `exercise_template_id` and
   `superset_id`, and the user's numbers.
4. `POST /v1/workouts`.

Drop `rest_seconds` and `rep_range`, which exist on a routine set and not a
workout set. Never carry a planned weight into a workout as though performed.

## Progress on one exercise

`GET /v1/exercise_history/{exerciseTemplateId}` returns every logged set, one
row per set, unpaginated. Bound it with `start_date` and `end_date`.

```bash
python3 scripts/hevy.py history 79D0BB3A --start 2026-01-01T00:00:00Z
```

Rows carry no set index, so group by `workout_id` and keep the returned order.

## Keeping a local copy in step

1. Store the timestamp before the run starts.
2. Page `/v1/workouts/events?since=<last watermark>` to the end.
3. Upsert on `type: "updated"`, delete on `type: "deleted"`.
4. Save the stored timestamp as the new watermark.

Taking the timestamp first stops a workout written mid-run from being missed.
`/v1/workouts` alone never reports a deletion.

## Editing without losing data

`PUT /v1/body_measurements/{date}` overwrites: the spec says omitted fields
become `null`, and a live update confirmed it. `PUT /v1/workouts/{workoutId}`
and `PUT /v1/routines/{routineId}` drop omitted exercises the same way,
verified live ([observed.md](observed.md#write-behaviour)).

Read the object, change the one field, strip the keys only reads carry, send it
back. For a workout or routine that is `index` on every set plus `index` and
`title` on every exercise, and for a measurement `date`, `id` and `created_at`.
Unrecognized keys are a `400` ([observed.md](observed.md#write-behaviour)).

The client refuses a write without `--yes`, because a mistake is permanent.

## Querying with SQL, when the user has asked for it

The mirror is off by default, so this recipe does not apply until the user
turns it on. Never suggest it unprompted ([SKILL.md](../SKILL.md#the-local-mirror-is-off-and-stays-off-unless-asked)).

Once enabled, `performed_sets` is one row per performed set, joined to its
workout and exercise, with `volume_kg` precomputed:

```sql
SELECT substr(start_time, 1, 7) AS month,
       ROUND(MAX(weight_kg * (1 + reps / 30.0)), 1) AS best_e1rm_kg
FROM performed_sets
WHERE exercise_template_id = '79D0BB3A'   -- Bench Press (Barbell)
  AND set_type != 'warmup' AND reps > 0
GROUP BY month ORDER BY month DESC;
```

**Filter on `exercise_template_id`, never on `exercise_title`.** A title looks
like the obvious key and is not one. `LIKE 'Bench Press%'` matches six
templates, mixing barbell with dumbbell and with the close-grip variant Hevy
files under triceps, so `MAX()` returns a number belonging to no exercise.
Widening to `%Bench Press%` reaches fourteen, adding every incline and decline.
Titles drift too ([observed.md](observed.md#an-exercise-title-is-a-display-name-not-an-identity)).

Look the id up first:

```bash
python3 scripts/hevy.py templates --search "bench press"
```

To compare variants rather than pick one, group by the id and label with the
title:

```sql
SELECT exercise_title, exercise_template_id,
       ROUND(MAX(weight_kg * (1 + reps / 30.0)), 1) AS best_e1rm_kg
FROM performed_sets
WHERE exercise_title LIKE 'Bench Press%' AND set_type != 'warmup' AND reps > 0
GROUP BY exercise_template_id
ORDER BY best_e1rm_kg DESC;
```

`weight_kg * (1 + reps / 30.0)` is the Epley estimate, drifting high above about
ten reps. Filter warmup sets out of anything measuring volume or effort. Every
weight column is kilograms, as the API returns them
([objects.md](objects.md#units)).

**The mirror is never authoritative for writes.** It is derived, disposable and
rebuildable with `hevy.py sync --full`, which is what makes querying it safe.
