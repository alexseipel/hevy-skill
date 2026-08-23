---
name: hevy-api
description: Call the Hevy REST API at api.hevyapp.com from any language — workouts, routines, routine folders, exercise templates, exercise history, body measurements and user info. Covers all 22 endpoints under /v1, the api-key header, the pageSize caps, the workout-events sync feed, and the set and exercise shapes shared between routines and workouts. Use when reading or writing Hevy training data, syncing a local workout cache, creating routines or custom exercises, importing gym logs, or debugging a Hevy API response.
license: MIT
---

# Hevy API

A read-and-write REST API over one Hevy account. Every route is under
`https://api.hevyapp.com/v1`, takes the key in an `api-key` header, returns
JSON, and acts on the account that owns the key. There is no OAuth, no user
scoping and no delete route.

**The API is available to Hevy Pro accounts only.** The key is issued at
`https://hevy.com/settings?developer`.

## Before the first call

```bash
export HEVY_API_KEY="…"   # from https://hevy.com/settings?developer

curl -s "https://api.hevyapp.com/v1/user/info" -H "api-key: $HEVY_API_KEY"
# {"data":{"id":"9c465af3-…","name":"John doe","url":"https://hevy.com/user/jhon"}}
```

Never put the key in a URL, a source file or a committed fixture. Read it from
the environment.

## The endpoints

All 22, grouped by resource. Every one requires the `api-key` header.

### [Workouts](reference/workouts.md)

| Method | Path                    | Returns                                     |
| ------ | ----------------------- | ------------------------------------------- |
| GET    | `/v1/workouts`          | `{page, page_count, workouts[]}`            |
| POST   | `/v1/workouts`          | `201`, as `{workout: [ … ]}`                |
| GET    | `/v1/workouts/count`    | `{workout_count}`                           |
| GET    | `/v1/workouts/events`   | `{page, page_count, events[]}` for syncing  |
| GET    | `/v1/workouts/{workoutId}` | a `Workout`                              |
| PUT    | `/v1/workouts/{workoutId}` | `200`, as `{workout: [ … ]}`             |

### [Routines](reference/routines.md)

| Method | Path                       | Returns                          |
| ------ | -------------------------- | -------------------------------- |
| GET    | `/v1/routines`             | `{page, page_count, routines[]}` |
| POST   | `/v1/routines`             | `201`, as `{routine: [ … ]}`     |
| GET    | `/v1/routines/{routineId}` | `{routine}`, wrapped             |
| PUT    | `/v1/routines/{routineId}` | `200`, as `{routine: [ … ]}`     |

### [Routine folders](reference/routines.md#routine-folders)

| Method | Path                          | Returns                                 |
| ------ | ----------------------------- | --------------------------------------- |
| GET    | `/v1/routine_folders`         | `{page, page_count, routine_folders[]}` |
| POST   | `/v1/routine_folders`         | `201` with the created `RoutineFolder`  |
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

### [User](reference/user.md)

| Method | Path            | Returns                        |
| ------ | --------------- | ------------------------------ |
| GET    | `/v1/user/info` | `{data: {id, name, url}}`      |

## Pagination

Every list route takes `page` and `pageSize` as query parameters and answers
with `page` and `page_count`. Pages are 1-based, and `pageSize` caps differ per
route:

| Route                    | Observed default | Maximum |
| ------------------------ | ---------------- | ------- |
| `/v1/workouts`           | 10               | 10      |
| `/v1/workouts/events`    | 10               | 10      |
| `/v1/routines`           | 10               | 10      |
| `/v1/routine_folders`    | 5                | 10      |
| `/v1/exercise_templates` | 100              | 100     |
| `/v1/body_measurements`  | 10               | 10      |

**The spec's default of 5 is wrong on four routes**: workouts, workout events,
routines and exercise templates default to their caps
([reference/observed.md](reference/observed.md)). Send `pageSize` explicitly and
the disagreement stops mattering.

Exceeding the cap returns `400`. Loop while `page <= page_count`, and read
`page_count` from the first response rather than assuming it. A page past the
last one returns `404`, and `page=0` quietly returns page 1.

## Errors

| Status | Where                                        | Meaning                                             |
| ------ | -------------------------------------------- | --------------------------------------------------- |
| 400    | list routes                                  | `pageSize` over the cap, or a negative `page`       |
| 400    | POST and PUT routes                          | `{"error": "…"}`, an invalid body                   |
| 401    | everywhere                                   | missing or wrong `api-key`                          |
| 403    | `POST /v1/routines`                          | routine limit: free plan only, unreachable on active Pro |
| 403    | `POST /v1/exercise_templates`                | `{"error": "exceeds-custom-exercise-limit"}`, free plan only |
| 404    | single-item GETs, `PUT /v1/routines/{id}`    | no such item, or it belongs to another account      |
| 404    | list routes                                  | `page` past `page_count`                            |
| 409    | `POST /v1/body_measurements`                 | a measurement already exists for that date          |
| 500    | `GET /v1/workouts/events`                    | documented, so retry with backoff                   |

**A `401` is not JSON.** It comes back as the plain string `InvalidApiKey`
with `Content-Type: text/html`. A client that calls `.json()` on every response
throws on the most common failure there is, so check the status first. (Observed against the live API on 2026-08-22, not documented.)

## Syncing a local cache

`GET /v1/workouts/events` exists so a client does not refetch everything. It
returns `updated` and `deleted` events newest first, filtered by `since`.

1. Store the timestamp before you start the run.
2. Page through `/v1/workouts/events?since=<last run>` until `page` reaches
   `page_count`.
3. For `type: "updated"`, upsert `event.workout`. For `type: "deleted"`,
   delete `event.id`.
4. Save the stored timestamp as the new watermark, so a workout written during
   the run is picked up next time.

The spec says `since` defaults to the epoch, and it is wrong: omitting it
returns no events at all ([reference/observed.md](reference/observed.md)).
Send `since` explicitly on every call, from the epoch for the first backfill,
and size that backfill with `GET /v1/workouts/count` first.

## Writing data

**Creating a workout** needs `exercise_template_id` for each exercise, so
resolve titles against `/v1/exercise_templates` first and cache the mapping.
Sets are ordered by array position, not by an index field you send. There is no
search route, and [reference/recipes.md](reference/recipes.md) has the workaround.

**Updating a workout** takes the same body as creating one and replaces it.
Verified against a live account: two exercises in, an update carrying one, one
left afterwards. Send the complete exercise list every time, stripped of
`index` on sets and of `index` and `title` on exercises, which only reads
carry.

**Updating a measurement** is the sharper version of the same rule: `PUT
/v1/body_measurements/{date}` sets every omitted field to `null`. Read the
current entry, merge your change into it, and send the whole object back.

## Gotchas

- **A superset id can be `0`.** It indexes the supersets within one workout, so
  `if (superset_id)` drops the first superset of every workout. Test against
  `null`.
- **The published spec is wrong in fourteen places**, including the superset
  field name and four `pageSize` defaults. The corrections are in
  [reference/observed.md](reference/observed.md), and this skill documents the
  API's actual behaviour.
- **`GET /v1/routines/{routineId}` wraps its result in `{routine: …}`**, while
  the workout, folder and template equivalents return the object bare.
- **Write responses are wrapped, and inside an array.** Creating or updating a
  workout returns `{"workout": [ {...} ]}`, not the bare object the spec
  promises, and routines behave the same way. Read the result from
  `body.workout[0]`.
- **`POST /v1/exercise_templates` does not return JSON at all.** The body is
  the new template's UUID as plain text, served as `text/html`.
- **A read cannot be written back untouched.** The write schemas reject
  unrecognized keys, so strip `index` from every set and `index` and `title`
  from every exercise before a `PUT`, or it is a `400`.
- **`rpe` on a set accepts only `6, 7, 7.5, 8, 8.5, 9, 9.5, 10`** or `null`.
- **Reading an exercise template gives you `equipment`**, while creating one
  takes `equipment_category`.
- **Every value is metric, and the API never says what the user sees.** Weights
  are kilograms, distances metres, body measurements centimetres. Hevy displays
  pounds and miles when the account asks it to, per exercise as well as
  globally, and no route reports that preference, so **convert before quoting a
  number back to somebody** ([reference/objects.md](reference/objects.md#units)).
- **A dumbbell weight is the total lifted per rep**, which is what Hevy's app
  tells a user to log: a pair of 10 kg dumbbells goes in as 20 kg. People log
  one hand instead, and nothing in the API distinguishes them, so volume from
  such an account is understated
  ([reference/recipes.md](reference/recipes.md#dumbbell-weight-is-the-total-and-nothing-enforces-it)).
- **There is no delete route** for any resource, and no hidden one under
  `/v1`: the server's `Allow` headers list `GET`, `HEAD`, `POST` and `PUT`
  only. Deleting stays a job for the Hevy app
  ([reference/observed.md](reference/observed.md#no-hidden-delete-route)).
- **A write can reach the mobile app late.** It shows in the web interface at
  once while the phone still shows nothing, which looks like a cache on the
  app's side. Check the web interface before concluding a write failed
  ([reference/observed.md](reference/observed.md#a-write-can-reach-the-mobile-app-late)).
- **An exercise title is a display name, not an identity.** Titles share
  prefixes, so a `Bench Press%` filter spans six different templates, and a
  title stored in an old workout can differ from the catalogue's current one.
  Group, filter and join on `exercise_template_id`
  ([reference/observed.md](reference/observed.md#an-exercise-title-is-a-display-name-not-an-identity)).
- **The two documented `403` limits are free-plan limits**, at 4 routines and
  7 custom exercises. The API is Pro-only, so an active Pro key cannot reach
  either branch, and a lapsed key is unverified
  ([reference/observed.md](reference/observed.md#the-403-limits-are-free-plan-limits)).
- **150 sets per workout and per routine**, on Pro as well, per Hevy's help
  centre. Which status the API returns for a longer one is unmeasured.
- **The API is explicitly unstable.** Its own documentation says the structure
  may change or the project may be abandoned, so pin behaviour with tests.

## The local mirror is off, and stays off unless asked

`scripts/hevy.py` can keep a SQLite copy of the account for querying with SQL.
**It is disabled by default and writes nothing to disk until the user names the
datasets they want stored.**

**Do not propose it on your own judgement.** Not because a request paged a lot
of data, not because a summary took a few seconds, and not as a suggestion
tacked onto an answer. Training data is personal, and putting it on disk is the
user's decision to make unprompted.

There are exactly two moments to raise it. The user asks about local storage,
caching, offline use or repeated slow queries. Or the client itself measured
the cost and printed a hint, which it does after ten API calls in one command.
Relay that hint and stop there. The trigger is a measurement, never a guess.

## Say what was cached

`hevy.py` writes notices to stderr whenever it reads from a cache, writes to
one, or deletes one. **Pass them on to the user.** They are how somebody knows
their data is on disk and where, and swallowing them turns a disclosed cache
into a hidden one.

```
[hevy] read 453 exercise templates from cache (fetched 2026-08-22T17:01:15, …)
[hevy] wrote to the local mirror at … (workouts: {'updated': 3, 'deleted': 0})
[hevy] answered from the local mirror at …, synced 2026-08-22T17:04:11, not from the API
```

Notices go to stderr, so stdout stays a clean JSON stream and a pipe still
works. `HEVY_QUIET=1` silences them, and is for scripts rather than for
conversations.

If they do ask:

```bash
python3 scripts/hevy.py cache enable --workouts   # names the datasets explicitly
python3 scripts/hevy.py sql "SELECT ... FROM performed_sets"
python3 scripts/hevy.py cache status              # what is stored, how fresh
python3 scripts/hevy.py cache clear               # deletes the file
```

Only `workouts` syncs exactly, through the events feed, which reports edits to
workouts of any age. `measurements` and `routines` have no change feed and are
refreshed in full each time. `sql` syncs before it queries, so a stale answer is
not reachable by accident, and it accepts `SELECT` and `WITH` only.

**One thing is cached without being asked**: the exercise catalogue, because
`--search` cannot work without it. It is a lookup table rather than training
history, every read and write of it is announced, and `cache clear` deletes it
along with the mirror.

## Reference files

| File                                                     | What is in it                                     |
| -------------------------------------------------------- | ------------------------------------------------- |
| [reference/objects.md](reference/objects.md)             | every shared object and enum, field by field      |
| [reference/workouts.md](reference/workouts.md)           | the six workout routes, with bodies and responses |
| [reference/routines.md](reference/routines.md)           | routines and routine folders, seven routes        |
| [reference/exercises.md](reference/exercises.md)         | templates and exercise history, four routes       |
| [reference/measurements.md](reference/measurements.md)   | body measurements, four routes                    |
| [reference/user.md](reference/user.md)                   | the account route, and what it does not expose    |
| [reference/observed.md](reference/observed.md)           | where the published spec is wrong, row by row     |
| [reference/recipes.md](reference/recipes.md)             | the multi-call workflows: search, summary, sync   |
| [openapi.json](openapi.json)                             | the pinned upstream spec, kept unedited            |
| [openapi.corrected.json](openapi.corrected.json)         | the same spec with the corrections applied         |
| [spec-patches.json](spec-patches.json)                   | each correction, with what it asserts and why      |

`scripts/hevy.py` is a dependency-free client that handles the header, the
paging loop and the API's two non-JSON bodies, the `401` and the
create-template response. Beyond one command per endpoint it adds the
three things the API cannot do itself:

```bash
python3 scripts/hevy.py templates --search "bench press"   # no search route exists
python3 scripts/hevy.py summary --weeks 4 --unit lb       # volume and muscle split
python3 scripts/hevy.py workouts --all | jq '.[].title'
```

**Every write command refuses to run without `--yes`.** The API has no delete
route, so a create is permanent and an update overwrites.
