# Live observations and upstream changes

The [upstream spec](../openapi.json) was refreshed from
[Hevy's OpenAPI document](https://developers.hevy.com/openapi.json) on
**2026-11-18**. It holds 24 operations, the earlier 22 and two image uploads,
and six more patches are redundant. The numbered observations below retain
their original numbering for links.

**The spec moved.** The Swagger bundle at `api.hevyapp.com/docs` that served it
now answers `404`, and that address redirects to `developers.hevy.com/docs`.
This repository's weekly drift job fetched the bundle on 2026-11-02 and has
failed since 2026-11-09.

Read checks last ran on **2026-11-18** with `scripts/verify_live.py`.
Successful writes were last tested on 2026-08-23
([write behaviour](#write-behaviour)), so a new specification is not evidence
that a write response was tested again.

Re-run the check before trusting a row:

```bash
HEVY_API_KEY=... python3 scripts/verify_live.py
```

**[openapi.corrected.json](../openapi.corrected.json) applies the remaining corrections.**
Upstream now declares its server and both security schemes, an `api-key`
header and an OAuth bearer token, so the four patches that added them are gone.

| # | Where | Original spec | Observation and current status |
| - | ----- | ------------- | ------------ |
| 1 | `Exercise` in every response | `supersets_id` | **`superset_id`**, matching the request field. Fixed upstream |
| 2 | `Routine.exercises[].rest_seconds` | `string` | **integer or null**. Fixed upstream |
| 3 | `ExerciseTemplate` | `equipment_category` | **`equipment`**. Fixed upstream |
| 4 | `pageSize` default | `5` on most list routes | **the route's own cap**, formerly except folders. Defaults updated upstream |
| 5 | `page` below 1 | `400` | **`0` returns page 1**, `-1` returns `400` |
| 6 | `page` past the end | `400` on most routes | **`200` with an empty array** on 2026-11-18, `404` before |
| 7 | `BodyMeasurement` | `date` plus measurement fields | adds **`id`** and **`created_at`**, and omits null fields |
| 8 | `Workout.routine_id` | `string` | **nullable**, `null` for an unplanned workout. Fixed upstream |
| 9 | Timestamp format | `2021-09-14T12:00:00Z` everywhere | **two formats**, see below |
| 10 | `GET /v1/workouts/events` | `since` defaults to the epoch | **omitting `since` returns no events at all** |
| 11 | every write that returns a body | returns the bare object | **wrapped in a key**. Workout create fixed upstream, routine writes now document an object |
| 12 | `POST /v1/exercise_templates` | `{"id": <integer>}` | **a bare UUID string as `text/html`** |
| 13 | `POST /v1/body_measurements` | `200` | **`201`**. Fixed upstream |
| 14 | `GET /v1/workouts/events` with nothing to report | `events: []` | formerly a `workouts` key instead. **Fixed on the server** by 2026-11-18 |
| 15 | `GET /v1/routines/{routineId}`, unknown id | `200` and `400` only | **`404`**, like every other single-item GET |
| 16 | a wrong or missing credential | no `401` documented | **the plain string `InvalidApiKey` as `text/html`** for a key, **JSON** for a bearer token |
| 17 | a `404` body | JSON, where it is declared at all | **plain text as `text/html` on three routes**, JSON on two |
| 18 | `POST /v1/exercise_templates`, invalid body | `error` is a string | **an object holding an `issues` array** |
| 19 | four pinned-note operations | absent | **named in Hevy's guides, `404` on the server** |
| 20 | `/v1/webhook-subscription` | absent | **served**, allowing `GET`, `POST` and `DELETE` |
| 21 | a rate-limited request | no `429` declared | **documented outside the spec**: empty body, no `Retry-After` |

## 1. The superset field is not renamed

The current response schemas use `superset_id`, matching requests and the
live API. The old `supersets_id` spelling was fixed upstream by 2026-10-27,
so the three rename patches were removed.

**A superset id can be `0`.** It is an index, not a database id, so a falsy
check drops the first superset of every workout. Test against `null`.

## 2. `rest_seconds` is a number

The current spec types `rest_seconds` as a nullable integer. Its old `string`
type was fixed upstream by 2026-10-27, so the type patch was removed.

## 3. Exercise templates carry `equipment`

```json
{ "id": "3BC06AD3", "title": "21s Bicep Curl", "type": "weight_reps",
  "primary_muscle_group": "biceps", "secondary_muscle_groups": [],
  "equipment": "barbell", "is_custom": false }
```

The values match the spec's `EquipmentCategory` enum. The response schema now
uses `equipment`, so its rename patch was removed on 2026-10-27. Creating a
custom exercise still sends `equipment_category`.

## 4. Page size defaults

The current spec defaults every list route to its cap. The four old default
patches were removed on 2026-10-27.

| Route | Current default | Cap |
| ----- | --------------- | --- |
| `/v1/workouts` | 10 | 10 |
| `/v1/routines` | 10 | 10 |
| `/v1/exercise_templates` | 100 | 100 |
| `/v1/routine_folders` | 10 | 10 |
| `/v1/body_measurements` | 10 | 10 |
| `/v1/workouts/events` | 10 | 10 |

Folders previously defaulted to 5. A request without `pageSize` returned
seven folders on 2026-10-27, confirming that 5 no longer holds. The default
of 10 comes from the current spec: this account has too few folders to prove it.

Send `pageSize` explicitly. The verifier reports a skipped default check when
there are too few records to fill multiple pages.

## 5 and 6. Page bounds

`page=0` returns `200` with page 1, echoing `"page": 1`. `page=-1` returns
`400`.

**A page past the last returns `200` and an empty array**, echoing the
requested page beside the real `page_count`:

```json
{"page": 99999, "page_count": 5, "workouts": []}
```

All six list routes answered this way on 2026-11-18. On 2026-10-27 they
answered `404` with `{"error":"Page not found"}`, and the spec still documents
`400`. A loop that waits for a `404` now never ends, so stop on `page_count`.

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
current spec includes `nullable: true`, so the old patch was removed on
2026-10-27.

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

Re-checked 2026-11-18.

## 11. Writes answer with the object wrapped, and in an array

The live writes on 2026-08-23 returned `{"workout": [ {...} ]}` for workout
creates and updates, and `{"routine": [ {...} ]}` for routine writes.
The array held one element.

The spec has documented the workout create wrapper since 2026-10-27. It
describes routine writes as `{"routine": {...}}`, with an object instead of
the previously observed array. No successful write has been repeated since
2026-08-23, so that change remains unverified against the live API.

| Route | Shape to handle |
| ----- | --------------- |
| `POST`/`PUT` workouts | `{"workout": [ {...} ]}`, a one-element array |
| `POST`/`PUT` routines | `{"routine": {...}}` in the current spec, or the earlier observed array |
| `POST /v1/routine_folders` | `{"routine_folder": {...}}`, observed 2026-08-23 |
| `GET /v1/routines/{routineId}` | `{"routine": {...}}`, checked 2026-11-18 |
| every other `GET` for one item | the bare object |

The corrected spec uses `oneOf` for the two routine write shapes. Accept
either until an authorised write confirms which the server currently returns.
The client passes the decoded response through unchanged.

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

The spec now documents `201` with an empty body, matching the write observed
on 2026-08-23. The status patch was removed on 2026-10-27. Read the entry back
with `GET /v1/body_measurements/{date}` when you need the stored values.

## 14. An empty events feed answered with the wrong key

Fixed on the server. Up to 2026-10-27 a feed with nothing to report dropped
`events`, a required property, and sent an empty `workouts` array in its place.
On 2026-11-18 it sent the documented shape, and both patches for it were
removed:

```json
{ "page": 1, "page_count": 1, "events": [] }
```

`payload.get("events", [])` reads either shape.

## 15. An unknown routine id is 404

Every sibling single-item GET documents a `404`, and `PUT` on this same route
does too. The spec gives the GET `200` and `400` only, while the API answers
`404` for an unknown id like the rest. Observed 2026-08-23.

## 16. A 401 is plain text for a key, and JSON for a token

A missing or wrong key returns the string `InvalidApiKey` with
`Content-Type: text/html`. A wrong bearer token returns
`{"message":"Invalid or expired token"}` as `application/json`, a third error
shape beside `{"error": …}`. The spec declares both schemes and no `401`, so
check the status before parsing the body.

The key `401` was observed 2026-08-22 and re-checked across all 24 routes on
2026-11-18. The token `401` was observed 2026-11-18 on `/v1/user/info` with an
invalid token. No valid token has been exercised
([auth.md](auth.md)).

**Two routes answer `400` before they check the key.** A malformed body sent to
`POST /v1/exercise_templates` or `POST /v1/body_measurements` returns the
validation error even when the key is invalid, so a `400` there does not mean
the key was accepted. Send a well-formed body and the same request returns
`401`. The other 22 routes check the key first. Observed 2026-08-24,
re-checked 2026-11-18.

## 17. A 404 body is plain text on three routes

| Route | `404` body | Content type |
| ----- | ---------- | ------------ |
| `GET /v1/workouts/{workoutId}` | `Workout not found` | `text/html` |
| `GET /v1/routine_folders/{folderId}` | `Routine folder not found` | `text/html` |
| `GET /v1/exercise_templates/{exerciseTemplateId}` | `Exercise template not found` | `text/html` |
| `GET /v1/routines/{routineId}` | `{"error":"Routine not found"}` | `application/json` |
| `GET /v1/body_measurements/{date}` | `{"error":"Body measurement not found"}` | `application/json` |
| a path the server does not register | an HTML error page | `text/html` |

The spec declares a JSON body on the measurement route and nothing about
content anywhere else. Nothing upstream warns a caller that three of these
throw on `json.loads`, so read the status first and the body as text. Observed
2026-08-24 and re-checked 2026-11-18, and the corrected spec declares both
shapes.

The list routes left this table on 2026-11-18, when a page past the end stopped
being a `404` ([5 and 6](#5-and-6-page-bounds)).

## 18. An invalid template body answers with an error object

`POST /v1/exercise_templates` sends `{"error": {"issues": [...]}}`, an object,
where the spec declares `error` as a string. `POST /v1/body_measurements` does
send a string, but the string is itself a JSON document, so neither route gives
a message you can show a user. Observed 2026-08-24.

## 19. The guides name routes the API does not serve

Hevy's [authentication](https://developers.hevy.com/authentication) and
[rate-limit](https://developers.hevy.com/rate-limits) guides list four
pinned-note operations that the spec omits:

| Operation | Where the guides name it |
| --------- | ------------------------ |
| `GET /v1/pinned_notes` | scope `read-exercise` |
| `POST /v1/pinned_notes` | scope `modify-exercise`, and a limit of 100 per 5 minutes |
| `PUT /v1/pinned_notes/{noteId}` | scope `modify-exercise` |
| `DELETE /v1/pinned_notes/{noteId}` | scope `modify-exercise` |

With a personal key, `GET /v1/pinned_notes` answers `404`. Both paths answer
`404` to `OPTIONS`, where a registered route lists its methods. Observed
2026-11-18.

Whether a bearer token reaches them is unverified, since no token was
exercised. `verify_live.py` fails when one starts answering, which is the cue
to document it.

**That cue fired once already.** The guides named two image routes the same
way, and both answered `404` to `OPTIONS` when the 2026-11-18 checks began.
Before those checks ended they were registered and in the spec, so they are
documented with [workouts](workouts.md#post-v1workoutsworkoutidimages) and
[measurements](measurements.md#put-v1body_measurementsdateimage).

## 20. A webhook subscription route the spec omits

`OPTIONS /v1/webhook-subscription` answers `Allow: POST,DELETE,GET,HEAD`, so
the route is registered. Neither spec pinned here, from 2026-08 or 2026-10,
carried it.

| Probe | Answer |
| ----- | ------ |
| `GET`, valid key, no subscription | `404`, the plain text `Webhook subscription not found` |
| `GET` or `DELETE`, invalid key | `401`, `InvalidApiKey` |
| `POST`, invalid key, empty body | `400`, the plain text `Invalid request body` |

Observed 2026-11-18. It is the only `DELETE` found under `/v1`, and it removes
a subscription rather than training data.

The body `POST` takes and the payload Hevy delivers are unverified. If Hevy
documents them, it is behind the login at `https://developers.hevy.com/api-key`
([auth.md](auth.md#personal-webhook)).

## 21. Rate limits are documented outside the spec

[Hevy's rate-limit page](https://developers.hevy.com/rate-limits) gives the
limits ([SKILL.md](../SKILL.md#rate-limits)) and the `429` they produce: an
empty body and no `Retry-After`. The spec declares a `429` on no operation.

Rapid reads drew a `429` in August 2026. None was provoked on 2026-11-18, so
the documented shape is unobserved.

## Fields added in the current spec

`UserInfo` now documents `username`, `weight_unit`, `distance_unit` and
`is_pro`. `ExerciseTemplate` adds nullable `thumbnail_url`. Their presence
and types were checked on 2026-10-27 through user info and both template GETs.

Routine sets no longer document `rpe`, and routine exercises allow null
`rest_seconds` and `notes`. Workout descriptions and exercise notes are also
nullable. The live verifier checks routine set fields when the account has sets.

Since 2026-11-18 both `403` bodies document a `message` beside the `error`
code ([the `403` limits](#the-403-limits-are-free-account-limits)).

The same refresh added `Workout.media`, an array of `WorkoutMedia`, and
`BodyMeasurement.picture_url`. Every workout read on 2026-11-18 carried
`media`, and no measurement carried `picture_url`
([objects.md](objects.md#workoutmedia)).

`PostWorkoutsRequestBody` now requires `workout`, and its object requires
`title`, `start_time`, `end_time` and `exercises`. `is_private` is optional
and defaults to `false`, according to the current spec.

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
**2026-08-23**. The test objects had to be removed by hand, the API being
unable to delete them.

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

## No delete route for training data

`OPTIONS` makes the server enumerate its registered methods in the `Allow`
header, settling the question more firmly than probing. Checked 2026-08-23 and
again on 2026-11-18:

| Route | Allow |
| ----- | ----- |
| `/v1/workouts`, `/v1/routines`, `/v1/routine_folders` | `GET,HEAD,POST` |
| `/v1/workouts/{workoutId}`, `/v1/routines/{routineId}`, `/v1/body_measurements/{date}` | `GET,HEAD,PUT` |
| `/v1/routine_folders/{folderId}`, `/v1/exercise_templates/{exerciseTemplateId}` | `GET,HEAD` |

No `DELETE` and no `PATCH` is registered on any resource, and folders and
exercise templates cannot even be updated. Method overrides
(`X-HTTP-Method-Override`, `?_method=DELETE`) and guessed paths (`/delete` and
`/archive` suffixes, `/v2/`, `/v1/me`, `/v1/account`, `/v1/routines/count`) all
returned `404` on 2026-08-23. `verify_live.py` re-checks the `Allow` headers.

The one `DELETE` under `/v1` removes a webhook subscription
([20](#20-a-webhook-subscription-route-the-spec-omits)). The guides also name a
`DELETE` for pinned notes, which the server does not register
([19](#19-the-guides-name-routes-the-api-does-not-serve)).

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

## The `403` limits are free-account limits

The current spec describes both `403`s as limits on free accounts. One caps
`POST /v1/routines` at 4 routines, not counting routines inside programs, and
the other caps `POST /v1/exercise_templates` at 7 custom exercises. Each body
pairs an `error` code with a `message`:

```json
{"error": "routine-limit-exceeded",
 "message": "Free accounts are limited to 4 routines. Upgrade to Hevy Pro (https://hevy.com/plans) to create more."}
```

A personal key needs Hevy Pro, per
[Hevy's developer overview](https://developers.hevy.com/). An active Pro
account therefore cannot reach either branch, and one well past the free cap
returned no `403`.

Hevy's pages do not say which free accounts reach the API. The users of an
OAuth app are the candidates, since the OAuth guide names no plan. Neither
`403` body has been observed.

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
- **Anything behind a bearer token.** No OAuth app was created, so the flow,
  the scopes and the app webhook in [auth.md](auth.md) rest on Hevy's guide
  alone.
- **The routine write shape.** An object in the spec, an array when last
  written on 2026-08-23
  ([11](#11-writes-answer-with-the-object-wrapped-and-in-an-array)).
- **The personal webhook.** The body `POST /v1/webhook-subscription` takes and
  the payload it delivers.
- **The `429` body.** Documented as empty with no `Retry-After`, and unobserved.
- **A successful image upload.** Both routes are documented from the spec.
  Whether a later `PUT` of the workout or the measurement keeps the image is
  unknown.
