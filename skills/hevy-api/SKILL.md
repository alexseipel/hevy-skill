---
name: hevy-api
description: "Call the Hevy REST API at api.hevyapp.com from any language: workouts, routines, routine folders, exercise templates, exercise history, body measurements, user info. Covers all 24 endpoints under /v1, the api-key header, OAuth bearer tokens, scopes and webhooks, rate limits, pageSize caps, the workout-events sync feed, and the set and exercise shapes routines and workouts share. Use when reading or writing Hevy training data, syncing a workout cache, creating routines or custom exercises, importing gym logs, building a Hevy OAuth app, or debugging a Hevy API response."
license: MIT
---

# Hevy API

A read-and-write REST API over one Hevy account. Every route is under
`https://api.hevyapp.com/v1`, returns JSON except where noted, and acts on the
account behind the credential. No route deletes training data.

**Two credentials work.** A personal key goes in an `api-key` header, needs
Hevy Pro and is issued at `https://developers.hevy.com/api-key`. An OAuth
access token goes in `Authorization: Bearer`, for an app other Hevy users
connect ([reference/auth.md](reference/auth.md)).

## Before the first call

```bash
export HEVY_API_KEY="…"   # from https://developers.hevy.com/api-key

curl -s "https://api.hevyapp.com/v1/user/info" -H "api-key: $HEVY_API_KEY"
# {"data":{"id":"9c465af3-…","username":"jhon","name":"John doe","url":"https://hevy.com/user/jhon","weight_unit":"kg","distance_unit":"kilometers","is_pro":true}}
```

Never put the key in a URL, a source file or a committed fixture.

## The endpoints

All 24, grouped by resource. Every one accepts either credential.

### [Workouts](reference/workouts.md)

| Method | Path                    | Returns                                     |
| ------ | ----------------------- | ------------------------------------------- |
| GET    | `/v1/workouts`          | `{page, page_count, workouts[]}`            |
| POST   | `/v1/workouts`          | `201`, as `{workout: [ … ]}`                |
| GET    | `/v1/workouts/count`    | `{workout_count}`                           |
| GET    | `/v1/workouts/events`   | `{page, page_count, events[]}` for syncing  |
| GET    | `/v1/workouts/{workoutId}` | a `Workout`                              |
| PUT    | `/v1/workouts/{workoutId}` | `200`, as `{workout: [ … ]}`             |
| POST   | `/v1/workouts/{workoutId}/images` | `201`, the updated `Workout`      |

### [Routines](reference/routines.md)

| Method | Path                       | Returns                          |
| ------ | -------------------------- | -------------------------------- |
| GET    | `/v1/routines`             | `{page, page_count, routines[]}` |
| POST   | `/v1/routines`             | `201`, `{routine}`, wrapped      |
| GET    | `/v1/routines/{routineId}` | `{routine}`, wrapped             |
| PUT    | `/v1/routines/{routineId}` | `200`, `{routine}`, wrapped      |

### [Routine folders](reference/routines.md#routine-folders)

| Method | Path                          | Returns                                 |
| ------ | ----------------------------- | --------------------------------------- |
| GET    | `/v1/routine_folders`         | `{page, page_count, routine_folders[]}` |
| POST   | `/v1/routine_folders`         | `201`, `{routine_folder: …}`  |
| GET    | `/v1/routine_folders/{folderId}` | a `RoutineFolder`                    |

### [Exercise templates and history](reference/exercises.md)

| Method | Path                                       | Returns                                    |
| ------ | ------------------------------------------ | ------------------------------------------ |
| GET    | `/v1/exercise_templates`                   | `{page, page_count, exercise_templates[]}` |
| POST   | `/v1/exercise_templates`                   | `200`, a bare UUID as plain text           |
| GET    | `/v1/exercise_templates/{exerciseTemplateId}` | an `ExerciseTemplate`                   |
| GET    | `/v1/exercise_history/{exerciseTemplateId}` | `{exercise_history[]}`                    |

### [Body measurements](reference/measurements.md)

| Method | Path                          | Returns                                   |
| ------ | ----------------------------- | ----------------------------------------- |
| GET    | `/v1/body_measurements`       | `{page, page_count, body_measurements[]}` |
| POST   | `/v1/body_measurements`       | `201`, empty body                         |
| GET    | `/v1/body_measurements/{date}` | a `BodyMeasurement`                      |
| PUT    | `/v1/body_measurements/{date}` | `200`, empty body                        |
| PUT    | `/v1/body_measurements/{date}/image` | `200`, the updated `BodyMeasurement` |

### [User](reference/user.md)

| Method | Path            | Returns                        |
| ------ | --------------- | ------------------------------ |
| GET    | `/v1/user/info` | `{data: {id, username, name, url, weight_unit, distance_unit, is_pro}}`      |

## Pagination

Every list route takes `page` and `pageSize` as query parameters and answers
with `page` and `page_count`. Pages are 1-based, and `pageSize` caps differ per
route:

| Route                    | Documented default | Maximum |
| ------------------------ | ---------------- | ------- |
| `/v1/workouts`           | 10               | 10      |
| `/v1/workouts/events`    | 10               | 10      |
| `/v1/routines`           | 10               | 10      |
| `/v1/routine_folders`    | 10               | 10      |
| `/v1/exercise_templates` | 100              | 100     |
| `/v1/body_measurements`  | 10               | 10      |

Send `pageSize` explicitly. These defaults come from the spec fetched on
2026-11-18 ([reference/observed.md](reference/observed.md#4-page-size-defaults)).

Exceeding the cap returns `400`, and `page=0` returns page 1. Loop while
`page <= page_count`, reading `page_count` from the first response.

**A page past the last answers `200` with an empty array.** It was a `404`
when checked on 2026-10-27, so a loop that stops on `404` no longer stops.
Observed 2026-11-18, not documented
([reference/observed.md](reference/observed.md#5-and-6-page-bounds)).

## Rate limits

| Applies to                     | Limit               | Counted per |
| ------------------------------ | ------------------- | ----------- |
| every request                  | 1,000 per 5 minutes | IP address  |
| `POST /v1/workouts`            | 1,000 per 24 hours  | account     |
| `POST /v1/routines`            | 40 per 5 minutes    | account     |
| `PUT /v1/routines/{routineId}` | 20 per 5 minutes    | account     |
| `POST /v1/routine_folders`     | 20 per 5 minutes    | account     |
| the two image routes together  | 100 per 24 hours    | account     |

These are [Hevy's published limits](https://developers.hevy.com/rate-limits),
each a fixed window opened by the first request. Past one the API answers `429`
with an empty body and no `Retry-After`, so wait for the window to pass. The
personal key and every connected app share an account's limits.

Hevy also asks for scheduled fetches on a random minute, not `xx:00`.

## Errors

| Status | Where                                        | Meaning                                             |
| ------ | -------------------------------------------- | --------------------------------------------------- |
| 400    | list routes                                  | `pageSize` over the cap, or a negative `page`       |
| 400    | POST and PUT routes                          | an invalid body. `error` is a string, except on `POST /v1/exercise_templates` |
| 401    | everywhere                                   | missing or wrong credential, after body validation on two POSTs |
| 403    | `POST /v1/routines`                          | `{"error": "routine-limit-exceeded", "message": …}`, free accounts only |
| 403    | `POST /v1/exercise_templates`                | `{"error": "exceeds-custom-exercise-limit", "message": …}`, free accounts only |
| 404    | single-item GETs, `PUT /v1/routines/{id}`    | no such item, or it belongs to another account      |
| 409    | `POST /v1/body_measurements`                 | a measurement already exists for that date          |
| 413    | the two image routes                         | an image over 10 MB                                 |
| 415    | the two image routes                         | a `Content-Type` other than JPEG, PNG or WebP       |
| 429    | everywhere                                   | over a rate limit: empty body, no `Retry-After`     |
| 500    | `GET /v1/workouts/events`                    | documented, so retry with backoff                   |

**An error body is not reliably JSON.** A wrong key's `401` is the plain string
`InvalidApiKey` as `text/html`, a wrong token's is JSON, three `404`s are
plain text and the `413` is an HTML page. Read the status first, the body as
text. Observed
2026-11-18, not documented
([reference/observed.md](reference/observed.md#17-a-404-body-is-plain-text-on-three-routes)).

**`GET /v1/exercise_history/{id}` answers `200` and an empty array for an
unknown id**, not the `404` every other path-id route gives, so a wrong id
reads as an exercise never trained
([reference/observed.md](reference/observed.md#an-unknown-id-is-not-always-a-404)).

## Syncing a local cache

`GET /v1/workouts/events` returns `updated` and `deleted` events newest first,
filtered by `since`, so a client need not refetch everything. The loop is in
[reference/recipes.md](reference/recipes.md#keeping-a-local-copy-in-step).

**The spec's epoch default for `since` is wrong**: omitting it returns no
events ([reference/observed.md](reference/observed.md)). Send it on every call,
from the epoch for the first backfill, sized with `GET /v1/workouts/count`.

An OAuth app can take a `workout.created` webhook instead of polling, though
edits and deletions arrive through the feed alone
([reference/auth.md](reference/auth.md#app-webhooks)).

## Writing data

**Creating a workout** needs `exercise_template_id` per exercise, so resolve
titles against `/v1/exercise_templates` and cache the mapping. Sets order by
array position, not by an index you send. There is no search route
([reference/recipes.md](reference/recipes.md)).

**Updating a workout** takes the create body and replaces the workout. Verified
live: two exercises in, an update carrying one, one left. Send the complete
exercise list every time.

**Updating a measurement** is sharper: `PUT /v1/body_measurements/{date}` sets
every omitted field to `null`. Read, merge, send the whole object back.

## Gotchas

- **A superset id can be `0`.** It indexes supersets within one workout, so
  `if (superset_id)` drops the first superset of every workout. Test against
  `null`.
- **Workout writes answer with an array, routine writes with an object.** Read
  `body.workout[0]` and `body.routine`
  ([reference/observed.md](reference/observed.md#11-writes-answer-with-the-object-wrapped-and-in-an-array)).
- **A read cannot be written back untouched.** Strip `index` from every set,
  `index` and `title` from every exercise, `media` from a workout and a null
  `rep_range` from a routine set, or the `PUT` is a `400`.
- **`rpe` accepts only `6, 7, 7.5, 8, 8.5, 9, 9.5, 10`** or `null`.
- **Reading a template gives `equipment`**, while creating one takes
  `equipment_category`.
- **Training values use metric units.** Read `weight_unit` and `distance_unit`
  from `/v1/user/info`, then convert for display. Per-exercise unit overrides
  are absent from the schema ([reference/objects.md](reference/objects.md#units)).
- **A dumbbell weight is the total lifted per rep**, as Hevy's app instructs: a
  pair of 10 kg dumbbells goes in as 20 kg. People log one hand instead and
  nothing distinguishes them, so such an account understates its volume
  ([reference/recipes.md](reference/recipes.md#dumbbell-weight-is-the-total-and-nothing-enforces-it)).
- **No hidden route deletes training data either**: every resource's `Allow`
  header lists `GET`, `HEAD`, `POST` and `PUT` only. Deleting stays a job for
  the Hevy app
  ([reference/observed.md](reference/observed.md#no-delete-route-for-training-data)).
- **Hevy's guides name four pinned-note routes the API answers `404` on**
  ([reference/observed.md](reference/observed.md#19-the-guides-name-routes-the-api-does-not-serve)).
- **An image upload sends the raw file as the body**, not JSON or multipart
  ([reference/workouts.md](reference/workouts.md#post-v1workoutsworkoutidimages)).
- **A write can reach the mobile app late**, showing in the web interface while
  the phone still shows nothing. Check the web before concluding a write failed
  ([reference/observed.md](reference/observed.md#a-write-can-reach-the-mobile-app-late)).
- **An exercise title is a display name, not an identity.** A `Bench Press%`
  filter spans six templates, and a title stored in an old workout can differ
  from the catalogue's. Group, filter and join on `exercise_template_id`
  ([reference/observed.md](reference/observed.md#an-exercise-title-is-a-display-name-not-an-identity)).
- **The two `403` limits bind free accounts only**, at 4 routines and 7 custom
  exercises
  ([reference/observed.md](reference/observed.md#the-403-limits-are-free-account-limits)).
- **The API does not enforce the 150-set cap** in Hevy's help centre: 151 sets
  were accepted. Stay under it anyway
  ([reference/observed.md](reference/observed.md#the-150-set-cap-is-not-enforced)).
- **The API changes without notice.** Between 2026-10-27 and 2026-11-18 the
  spec moved and a `404` became a `200`, under an unchanged `info.version`. Pin
  behaviour with tests.

## The local mirror is off, and stays off unless asked

`scripts/hevy.py` can keep a SQLite copy of the account for querying with SQL.
**It writes nothing to disk until the user names the datasets they want
stored.**

**Do not propose it on your own judgement**, however much data a request paged
or how slow a summary was. Putting training data on disk is the user's decision
to make unprompted.

Raise it in two cases only. The user asks about local storage, caching,
offline use or slow repeated queries, or the client printed its own hint after
ten API calls: relay that hint and stop.

**Pass every cache notice on to the user.** `hevy.py` writes one to stderr on
every cache read, write and deletion. Swallowing them turns a disclosed cache
into a hidden one.

```
[hevy] read 453 exercise templates from cache (fetched 2026-08-22T17:01:15, …)
[hevy] wrote to the local mirror at … (workouts: {'updated': 3, 'deleted': 0})
[hevy] answered from the local mirror at …, synced 2026-08-22T17:04:11, not from the API
```

Stdout stays a clean JSON stream, so a pipe still works. `HEVY_QUIET=1`
silences the notices, and is for scripts rather than conversations.

If they do ask:

```bash
python3 scripts/hevy.py cache enable --workouts   # names the datasets explicitly
python3 scripts/hevy.py sql "SELECT ... FROM performed_sets"
python3 scripts/hevy.py cache status              # what is stored, how fresh
python3 scripts/hevy.py cache clear               # deletes the file
```

Only `workouts` syncs exactly, through the events feed, which reports edits to
workouts of any age. `measurements` and `routines` have no change feed and
refresh in full. `sql` syncs before querying, so a stale answer is unreachable
by accident, and it accepts `SELECT` and `WITH` only.

**The exercise catalogue is cached without being asked**, because `--search`
cannot work without it. It is a lookup table rather than training history,
every read and write of it is announced, and `cache clear` deletes it with the
mirror.

## Reference files

| File                                                     | What is in it                                     |
| -------------------------------------------------------- | ------------------------------------------------- |
| [reference/objects.md](reference/objects.md)             | every shared object and enum, field by field      |
| [reference/workouts.md](reference/workouts.md)           | the seven workout routes, with bodies and responses |
| [reference/routines.md](reference/routines.md)           | routines and routine folders, seven routes        |
| [reference/exercises.md](reference/exercises.md)         | templates and exercise history, four routes       |
| [reference/measurements.md](reference/measurements.md)   | body measurements, five routes                    |
| [reference/user.md](reference/user.md)                   | the account route, and what it does not expose    |
| [reference/auth.md](reference/auth.md)                   | the personal key, the OAuth flow, scopes and webhooks |
| [reference/observed.md](reference/observed.md)           | live observations, upstream fixes and open differences |
| [reference/recipes.md](reference/recipes.md)             | the multi-call workflows: search, summary, sync   |
| [openapi.json](openapi.json)                             | the pinned upstream spec, kept unedited            |
| [openapi.corrected.json](openapi.corrected.json)         | the same spec with the corrections applied         |
| [spec-patches.json](spec-patches.json)                   | each correction, with what it asserts and why      |

`scripts/hevy.py` is a dependency-free client handling the header, the paging
loop and the five responses that are not JSON. Beyond one command per endpoint:

```bash
python3 scripts/hevy.py templates --search "bench press"   # no search route exists
python3 scripts/hevy.py summary --weeks 4 --unit lb       # volume and muscle split
python3 scripts/hevy.py workouts --all | jq '.[].title'
```

**Every write command refuses to run without `--yes`**, because a create is
permanent and an update overwrites.
