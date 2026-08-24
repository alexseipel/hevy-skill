# Where the spec is wrong

The published [openapi.json](../openapi.json) disagrees with the live API in
eighteen places. Every read-only row re-runs with `scripts/verify_live.py`,
last on **2026-08-24**. Rows 11 to 13 need writes and were verified once on
2026-08-23 ([write behaviour](#write-behaviour)).

Re-run the check before trusting a row:

```bash
HEVY_API_KEY=... python3 scripts/verify_live.py
```

**[openapi.corrected.json](../openapi.corrected.json) has all of this applied.**
It also adds the two things upstream omits entirely: a `servers` entry and an
`api-key` security scheme. Without those, a generated client knows neither
where to send a request nor how to authenticate.

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
| 15 | `GET /v1/routines/{routineId}`, unknown id | `200` and `400` only | **`404`**, like every other single-item GET |
| 16 | a wrong or missing key | no `401` documented | **the plain string `InvalidApiKey` as `text/html`**, never JSON |
| 17 | a `404` body | JSON, where it is declared at all | **plain text as `text/html` on three routes**, JSON on three |
| 18 | `POST /v1/exercise_templates`, invalid body | `error` is a string | **an object holding an `issues` array** |

## 1. The superset field is not renamed

The spec's response schema calls it `supersets_id`, a field the API never
sends. Workout and routine exercises both return `superset_id`, the same name
the request body uses, so a read-edit-write round trip needs no rename.

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

`page=0` returns `200` with page 1, echoing `"page": 1`. `page=-1` returns
`400`. A page past the last returns `404` on every list route, including those
whose spec entry documents only `400`, and `verify_live.py` re-checks all six.

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

Neither `id` nor `created_at` appears in the spec. An unrecorded field is
**absent**, not `null`, so `entry["chest_cm"]` raises where the spec implies a
`null`.

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
nothing is undetermined, and telling them apart needs a write. The epoch
default does not hold either way, so send `since` explicitly on every call. The
corrected spec drops the false value rather than replacing it.

## 11. Writes answer with the object wrapped, and in an array

`POST /v1/workouts` and `PUT /v1/workouts/{workoutId}` both return

```json
{ "workout": [ { "id": "…", "title": "…", "exercises": [] } ] }
```

and the routine routes return the same shape under `"routine"`. The spec
declares a bare `Workout` and `Routine`, so `response.id` is undefined and a
generated client reads nothing.

**The array holds one element.** Three shapes are in play, and nothing in the
spec distinguishes them:

| Route | Shape |
| ----- | ----- |
| `POST`/`PUT` workouts and routines | `{"workout": [ {...} ]}`, a one-element array |
| `POST /v1/routine_folders` | `{"routine_folder": {...}}`, an object |
| `GET /v1/routines/{routineId}` | `{"routine": {...}}`, an object |
| every other `GET` for one item | the bare object |

The read and write shapes of one resource differ, so a shared unwrapping helper
must know which it is looking at.

## 12. Creating an exercise template answers with plain text

```
HTTP 200
Content-Type: text/html; charset=utf-8

11111111-2222-3333-4444-555555555555
```

36 bytes, no JSON, no quotes. The spec promises `{"id": <integer>}`, so a
client parsing the body throws and one reading `.id` gets nothing. The value is
the new template's id, a UUID string like every other, not an integer.

## 13. Creating a measurement answers `201`

The spec documents `200`. The body is empty either way, so read the entry back
with `GET /v1/body_measurements/{date}` when you need the stored values.

## 14. An empty events feed answers with the wrong key

`events` is a required property of `PaginatedWorkoutEvents`. When the feed has
nothing to report it is absent, replaced by a differently named empty array:

```json
{ "page": 1, "page_count": 1, "workouts": [] }
```

So `payload["events"]` raises exactly when a sync has caught up, the common
case for a scheduled poll. Read `payload.get("events", [])`.

## 15. An unknown routine id is 404

Every sibling single-item GET documents a `404`, and `PUT` on this same route
does too. The spec gives the GET `200` and `400` only, while the API answers
`404` for an unknown id like the rest. Observed 2026-08-23.

## 16. A 401 is plain text

A missing or wrong key returns the string `InvalidApiKey` with
`Content-Type: text/html`. The spec documents no `401` at all, so check the
status before parsing the body.

Observed 2026-08-22, re-checked on 2026-08-24 across all 22 routes, and
carried on the corrected spec's security scheme.

**Two routes answer `400` before they check the key.** A malformed body sent to
`POST /v1/exercise_templates` or `POST /v1/body_measurements` returns the
validation error even when the key is invalid, so a `400` there does not mean
the key was accepted. Send a well-formed body and the same request returns
`401`. The other twenty routes check the key first. Observed 2026-08-24.

## 17. A 404 body is plain text on half the routes

| Route | `404` body | Content type |
| ----- | ---------- | ------------ |
| `GET /v1/workouts/{workoutId}` | `Workout not found` | `text/html` |
| `GET /v1/routine_folders/{folderId}` | `Routine folder not found` | `text/html` |
| `GET /v1/exercise_templates/{exerciseTemplateId}` | `Exercise template not found` | `text/html` |
| `GET /v1/routines/{routineId}` | `{"error":"Routine not found"}` | `application/json` |
| `GET /v1/body_measurements/{date}` | `{"error":"Body measurement not found"}` | `application/json` |
| any list route, `page` past the end | `{"error":"Page not found"}` | `application/json` |

The spec declares a JSON body on the measurement route and nothing about
content anywhere else. Nothing upstream warns a caller that half of these throw
on `json.loads`, so read the status first and the body as text. Observed
2026-08-24, and the corrected spec now declares both shapes.

## 18. An invalid template body answers with an error object

`POST /v1/exercise_templates` sends `{"error": {"issues": [...]}}`, an object,
where the spec declares `error` as a string. `POST /v1/body_measurements` does
send a string, but the string is itself a JSON document, so neither route gives
a message you can show a user. Observed 2026-08-24.

## An unknown id is not always a 404

`GET /v1/exercise_history/{exerciseTemplateId}` answers `200` and
`{"exercise_history": []}` for an id that does not exist, while every other
route taking a path id answers `404`. A typo reads as an exercise you have
never trained rather than as a wrong id. Check the id against the catalogue
before reporting an empty history. Observed 2026-08-24.

## Ordering, which the spec never states

**`/v1/workouts` and `/v1/body_measurements` return newest first**, and
`/v1/workouts/events` documents the same order. That is what makes an early
stop safe: walking `/v1/workouts` until the last item on a page falls outside
your window covers the window without paging the whole account.

**`/v1/routines` does not.** It groups by `folder_id`, one contiguous run per
folder, in ascending folder id, which is creation order. Unfoldered routines
come last. Measured 2026-08-23 over several folders of differing sizes.

A routine created today lands wherever its folder sits, not at the top, so
there is no early stop here. Page it all, or fetch by id.

## An exercise title is a display name, not an identity

`exercise_template_id` identifies an exercise. The `title` beside it is what
the app shows, and the two drift apart.

Hevy renames templates, and a workout logged before a rename keeps the title it
was written with. Reading it returns the old title next to an id whose
catalogue entry now reads differently, so one exercise arrives under two names.
`/v1/exercise_history/{exerciseTemplateId}` shows which the API treats as the
identity: it returns no title at all, only the id.

Titles also share prefixes. `Bench Press` is six templates once equipment is
counted, and `Bench Press - Close Grip (Barbell)` is a triceps exercise rather
than a chest one. Group and filter on `exercise_template_id`, and match titles
only to find that id ([recipes.md](recipes.md#finding-an-exercise-by-name)).

## Write behaviour

All eight write routes were exercised once against a real account on
**2026-08-23**. The test objects had to be removed by hand, the API having no
delete route.

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

The folder case was measured: five folders at indexes 0 to 4 became 1 to 5,
relative order intact, with the new folder at 0. No folder update or delete
route exists, so the API cannot put the order back.

Deleting a workout in the app surfaces in `/v1/workouts/events` as
`{"type": "deleted", "id": "…", "deleted_at": "…"}`: all three fields present,
with `deleted_at` in the `Z`-millisecond format. The feed retains deletions, so
`verify_live.py` pins that shape on any account that holds one.

**A read response cannot be written back as it is.** The write schemas reject
undeclared keys, and a read carries three:

```json
{"error":"Unrecognized key(s) in object: 'index'. Unrecognized key(s) in object: 'index', 'title'"}
```

Strip `index` from every set and `index` and `title` from every exercise, and
the same `PUT` returns `200`. Identical on workouts and routines. Measurements
were already documented this way: `date`, `id` and `created_at` come out first.

## No hidden delete route

`OPTIONS` makes the server enumerate its registered methods in the `Allow`
header, settling the question more firmly than probing. Checked 2026-08-23:

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

Emptying is no back door either: a routine must keep at least one exercise.

Hevy's own apps do delete, through a separate API outside `/v1` that a
developer key cannot authenticate against. Deleting stays a job for the app.

## A write can reach the mobile app late

Something created through `/v1` shows in the web interface at once and can
reach the mobile app later. Observed twice on 2026-08-22, with custom exercises
and with a routine, each visible on the web while the phone showed neither.

Whether the app holds a cached copy or the write never signalled it is
undetermined. The data was on the server both times, so **check the web
interface before concluding a write failed.**

## The `403` limits are free-plan limits

`POST /v1/routines` documents a `403` for exceeding a routine limit, and
`POST /v1/exercise_templates` a `403` for exceeding a custom-exercise limit.
Hevy's [Pro subscription page](https://help.hevyapp.com/hc/en-us/articles/35119778922263-Hevy-Pro-Subscription-How-to-get-Pro-and-What-Does-It-Include)
puts both on the free plan, at **4 routines and 7 custom exercises**, and the
API's own description says it "is only available to Hevy Pro users". An active
Pro account therefore cannot reach either branch, and one well past the free cap
returned no `403`.

What a lapsed subscription does is unverified. Treat the status as a plan
problem rather than something to retry, not as impossible.

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
