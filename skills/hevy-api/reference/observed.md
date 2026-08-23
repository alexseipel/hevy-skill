# Where the spec is wrong

The published [openapi.json](../openapi.json) disagrees with the live API in
fourteen places. Every read-only row re-runs with `scripts/verify_live.py`,
last on **2026-08-23**. Rows 11 to 13 need writes, so they were verified once,
on the same date, as [write behaviour](#write-behaviour) describes. The rest
of this skill documents the observed column rather than the spec column.

Re-run the check before trusting a row:

```bash
HEVY_API_KEY=... python3 scripts/verify_live.py
```

**[openapi.corrected.json](../openapi.corrected.json) has all of this applied**,
so a client generated from it gets the field names the API actually uses. It
also gains the two things the upstream document omits entirely: a `servers`
entry and an `api-key` security scheme, without which a generated client knows
neither where to send a request nor how to authenticate it.

| # | Where | The spec says | The API does |
| - | ----- | ------------- | ------------ |
| 1 | `Exercise` in every response | `supersets_id` | **`superset_id`**, matching the request field |
| 2 | `Routine.exercises[].rest_seconds` | `string` | **integer**, such as `120` |
| 3 | `ExerciseTemplate` | `equipment_category` | **`equipment`** |
| 4 | `pageSize` default | `5` on most list routes | **the route's own cap**, except folders |
| 5 | `page` below 1 | `400` | **`0` returns page 1**, `-1` returns `400` |
| 6 | `page` past the end | `400` on most routes | **`404`** everywhere |
| 7 | `BodyMeasurement` | `date` plus measurement fields | adds **`id`** and **`created_at`**, and omits null fields |
| 8 | `Workout.routine_id` | `string` | **nullable**, `null` for an unplanned workout |
| 9 | Timestamp format | `2021-09-14T12:00:00Z` everywhere | **two formats**, see below |
| 10 | `GET /v1/workouts/events` | `since` defaults to the epoch | **omitting `since` returns no events at all** |
| 11 | every write that returns a body | returns the bare object | **wrapped in a key**, and for workouts and routines inside an array |
| 12 | `POST /v1/exercise_templates` | `{"id": <integer>}` | **a bare UUID string as `text/html`** |
| 13 | `POST /v1/body_measurements` | `200` | **`201`** |
| 14 | `GET /v1/workouts/events` with nothing to report | `events: []` | **a `workouts` key instead**, and no `events` at all |

## 1. The superset field is not renamed

The spec's response schema calls it `supersets_id`, so a client generated from
that spec reads a field the API never sends. The live API returns
`superset_id` in workout and routine exercises alike, which is the same name
the request body uses. A read-edit-write round trip needs no rename.

**A superset id can be `0`.** It is an index, not a database id, so a falsy
check drops the first superset of every workout. Test against `null`.

## 2. `rest_seconds` is a number

The spec types it `string` while giving `60` as the example. The API sends an
integer.

## 3. Exercise templates carry `equipment`

```json
{ "id": "3BC06AD3", "title": "21s Bicep Curl", "type": "weight_reps",
  "primary_muscle_group": "biceps", "secondary_muscle_groups": [],
  "equipment": "barbell", "is_custom": false }
```

The values match the spec's `EquipmentCategory` enum. Only the field name is
different, and only when reading: creating a custom exercise still sends
`equipment_category`.

## 4. The default page size is the cap, not 5

| Route | Spec default | Observed default | Cap |
| ----- | ------------ | ---------------- | --- |
| `/v1/workouts` | 5 | **10** | 10 |
| `/v1/routines` | 5 | **10** | 10 |
| `/v1/exercise_templates` | 5 | **100** | 100 |
| `/v1/routine_folders` | 5 | 5 | 10 |
| `/v1/body_measurements` | 10 | 10 | 10 |
| `/v1/workouts/events` | 5 | **10** | 10 |

Send `pageSize` explicitly rather than relying on either number.

## 5 and 6. Page bounds

`page=0` returns `200` with page 1, and the response echoes `"page": 1`.
`page=-1` returns `400`. A page past the last one returns `404` on every list
route, including the ones whose spec entry documents only `400`.
`verify_live.py` re-checks the `404` on all six.

`pageSize=0` returns `200`. `pageSize` above the cap returns `400` with a
usable message:

```json
{"error":"pageSize must be less than or equal to 10"}
```

## 7. Body measurements carry an id, and omit their nulls

```json
{ "id": 10000001, "date": "2024-08-14", "weight_kg": 80.50000000000045,
  "fat_percent": 18.5, "created_at": "2024-08-14T11:59:31.028Z" }
```

Neither `id` nor `created_at` appears in the spec. A field that was never
recorded is **absent**, not `null`, so code that reads
`entry["chest_cm"]` raises where the spec implies a `null`.

**Strip `id` and `created_at` before sending the entry back to
`PUT /v1/body_measurements/{date}`.** They are not part of `PutBodyMeasurement`.

Note the float: `80.5` went in and `80.50000000000045` came back, because the
value is stored as a binary float. Round for display rather than assuming what
you sent comes back unchanged.

## 8. `routine_id` is nullable

A workout logged without a routine comes back with `routine_id: null`. The
spec types the field as a plain `string`, and the corrected spec adds
`nullable: true`.

## 9. Two timestamp formats in one object

| Field | Format | Example |
| ----- | ------ | ------- |
| `start_time`, `end_time` | offset, no fractional seconds | `2024-08-14T18:30:00+00:00` |
| `created_at`, `updated_at` | `Z`, with milliseconds | `2024-08-14T19:31:12.765Z` |

Both are valid ISO 8601, and a strict parser written against one rejects the
other. Use a parser that accepts both.

## 10. Omitting `since` is not an epoch backfill

The spec gives `since` a default of `1970-01-01T00:00:00Z`, which reads as
"omitting it returns everything". It does not. On an account whose epoch
backfill spans many pages, a call without `since` returned `page_count: 1` and
zero events.

Whether the server substitutes a recent timestamp or the filter matches
nothing was not determined, and telling the two apart needs a write. What is
certain is that the epoch default in the spec does not hold, so send `since`
explicitly on every call. The corrected spec drops the false value rather than
replacing it.

## 11. Writes answer with the object wrapped, and in an array

`POST /v1/workouts` and `PUT /v1/workouts/{workoutId}` both return

```json
{ "workout": [ { "id": "…", "title": "…", "exercises": [] } ] }
```

and the routine routes return the same shape under `"routine"`. The spec
declares a bare `Workout` and `Routine`, so `response.id` is undefined against
the real API and a generated client reads nothing.

**The array holds one element.** Three shapes are in play across the API, and
nothing in the spec distinguishes them:

| Route | Shape |
| ----- | ----- |
| `POST`/`PUT` workouts and routines | `{"workout": [ {...} ]}`, a one-element array |
| `POST /v1/routine_folders` | `{"routine_folder": {...}}`, an object |
| `GET /v1/routines/{routineId}` | `{"routine": {...}}`, an object |
| every other `GET` for one item | the bare object |

So the read and write shapes of one resource differ, and a shared unwrapping
helper has to know which shape it is looking at.

## 12. Creating an exercise template answers with plain text

```
HTTP 200
Content-Type: text/html; charset=utf-8

11111111-2222-3333-4444-555555555555
```

36 bytes, no JSON, no quotes. The spec promises `{"id": <integer>}`, so a
client that parses the body throws, and one that reads `.id` gets nothing. The
value is the new template's id, and it is a UUID string like every other
template id rather than the integer the spec names.

## 13. Creating a measurement answers `201`

The spec documents `200`. The body is empty either way, so read the entry back
with `GET /v1/body_measurements/{date}` when you need the stored values.

## 14. An empty events feed answers with the wrong key

`events` is a required property of `PaginatedWorkoutEvents`. When the feed has
nothing to report it is absent, and a differently named empty array takes its
place:

```json
{ "page": 1, "page_count": 1, "workouts": [] }
```

So `payload["events"]` raises exactly when a sync has caught up, which is the
common case for a client polling on a schedule. Read it as
`payload.get("events", [])`.

## Ordering, which the spec never states

**`/v1/workouts` and `/v1/body_measurements` return newest first**, and
`/v1/workouts/events` documents the same order. That is what makes an early
stop safe: walking `/v1/workouts` until the last item on a page falls outside
your window covers the window without paging the whole account.

**`/v1/routines` does not.** It groups by `folder_id`, one contiguous run per
folder, in ascending folder id, which is the order the folders were created in.
Routines with no folder come last. Measured on 2026-08-23, over several
folders of very different sizes, and the runs matched the folder ids in order
every time.

A routine created today therefore lands wherever its folder sits, not at the
top, so there is no early stop for this route. Page it all, or fetch by id.

## An exercise title is a display name, not an identity

`exercise_template_id` identifies an exercise. The `title` returned beside it
is what the app shows, and the two drift apart.

Hevy renames a template from time to time, and a workout logged before the
rename keeps the title it was written with. Reading such a workout returns the
old title next to an id whose catalogue entry now reads differently, so the
same exercise arrives under two names.

`/v1/exercise_history/{exerciseTemplateId}` shows which of the two the API
treats as the identity: it returns no title at all, only the id.

Titles also share prefixes. `Bench Press` is six separate templates once
equipment is counted, and one of them, `Bench Press - Close Grip (Barbell)`,
is a triceps exercise rather than a chest one. Group and filter on
`exercise_template_id`, and match on the title only to find that id in the
first place ([recipes.md](recipes.md#finding-an-exercise-by-name)).

## Write behaviour

All eight write routes were exercised once against a real account on
**2026-08-23**, creating test objects that had to be removed by hand
afterwards, because the API has no delete route.

| Behaviour | Result |
| --------- | ------ |
| `PUT /v1/workouts/{workoutId}` with fewer exercises | **full replace**: two exercises became one |
| `PUT /v1/routines/{routineId}` with fewer exercises | **full replace**, same as workouts |
| `PUT /v1/body_measurements/{date}` with one field | **full overwrite**: `fat_percent` and `chest_cm` were erased |
| `POST /v1/body_measurements` on an existing date | `409` with `{"error":"A measurement for this date already exists"}` |
| `superset_id` sent as `0`, then as `null` | round-trips unchanged, under the same field name |
| `rpe`, `rest_seconds`, `rep_range` | all round-trip unchanged |
| `POST /v1/routine_folders` | lands at **index 0** and pushes every existing folder down by one |
| `PUT` with the object just read | **`400`**: the write schemas reject unrecognized keys |
| `PUT /v1/routines/{routineId}` with `exercises: []` | `400`, "Array must contain at least 1 element(s)" |
| a set of `-100` kg times `-5` reps, an empty title, `sets: []` | all accepted: no range validation |

The folder case was measured: five folders at indexes 0 to 4 became indexes 1
to 5, keeping their relative order, and the new folder took index 0. There is
no folder update or delete route, so the API cannot put the order back.

Deleting a workout in the app surfaces in `/v1/workouts/events` as
`{"type": "deleted", "id": "…", "deleted_at": "…"}`: all three fields present,
with `deleted_at` in the `Z`-millisecond format. The feed retains deletions, so
`verify_live.py` pins that shape on any account that holds one.

**A read response cannot be written back as it is.** The write schemas reject
keys they do not declare, and a read carries three of them:

```json
{"error":"Unrecognized key(s) in object: 'index'. Unrecognized key(s) in object: 'index', 'title'"}
```

Strip `index` from every set and `index` and `title` from every exercise, and
the same `PUT` returns `200`. Confirmed identically on workouts and routines.
Measurements were already documented this way, with `date`, `id` and
`created_at` coming out before the write.

## No hidden delete route

`OPTIONS` makes the server enumerate its own registered methods in the `Allow`
header, which settles the question more strongly than probing. Checked on
2026-08-23:

| Route | Allow |
| ----- | ----- |
| `/v1/workouts`, `/v1/routines`, `/v1/routine_folders` | `GET,HEAD,POST` |
| `/v1/workouts/{workoutId}`, `/v1/routines/{routineId}`, `/v1/body_measurements/{date}` | `GET,HEAD,PUT` |
| `/v1/routine_folders/{folderId}`, `/v1/exercise_templates/{exerciseTemplateId}` | `GET,HEAD` |

No `DELETE` and no `PATCH` is registered under `/v1`, and folders and exercise
templates cannot even be updated. Method overrides (`X-HTTP-Method-Override`,
`?_method=DELETE`) and guessed paths (`/delete` and `/archive` suffixes,
`/v2/`, `/v1/me`, `/v1/account`, `/v1/routines/count`) all return `404`.
`verify_live.py` re-checks the `Allow` headers.

Emptying is not a back door either: a routine must keep at least one exercise,
so nothing can be hollowed out as a pseudo-delete.

Hevy's own apps do delete, through a separate API outside `/v1` that a
developer key cannot authenticate against. Nothing there is reachable with a
key, so deleting stays a job for the app.

## A write can reach the mobile app late

Something created through `/v1` shows in the web interface at once and can take
longer to appear in the mobile app. Observed twice on 2026-08-22, with custom
exercises and with a routine, each visible on the web while the phone showed
neither.

Whether the app is holding a cached copy or the write never signalled it is
undetermined. The data was on the server both times, so **check the web
interface before concluding a write failed.**

## The `403` limits are free-plan limits

`POST /v1/routines` documents a `403` for exceeding a routine limit, and
`POST /v1/exercise_templates` a `403` for exceeding a custom-exercise limit.
Hevy's [Pro subscription page](https://help.hevyapp.com/hc/en-us/articles/35119778922263-Hevy-Pro-Subscription-How-to-get-Pro-and-What-Does-It-Include)
puts both limits on the free plan, at **4 routines and 7 custom exercises**,
with Pro lifting each, and the API's own description says it "is only
available to Hevy Pro users". An account with active Pro therefore cannot
reach either branch. A Pro account well past the free cap returned no `403`.

What a key does when its Pro subscription lapses is not verified. Treat the
status as a plan problem rather than something to retry, not as impossible.

**A limit that does apply to Pro**: [150 sets per workout and per routine](https://help.hevyapp.com/hc/en-us/articles/34896183826455-Hevy-Set-Limit-Explained-Why-Workouts-and-Routines-Have-a-150-Set-Cap),
which an import that flattens a long session can meet. The status code it
returns has not been measured.

## Still not verified

- **The status code of the 150-set cap.** Meeting it takes a write carrying
  151 sets.
- **A key whose Pro subscription has lapsed.** The `403` reasoning above
  stands on Pro entitlement tracking the key, and nobody has watched a key
  outlive its plan.
- **The shape of the rate limit.** Reads in quick succession can return a
  `429`, which no Hevy documentation mentions. The threshold, the window and
  whether either varies by route are unmeasured, so retry with backoff rather
  than to a schedule.
