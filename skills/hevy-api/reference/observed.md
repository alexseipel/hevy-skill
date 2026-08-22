# Where the spec is wrong

The published [openapi.json](../openapi.json) disagrees with the live API in
ten places. Every row below was checked against a real account on
**2026-08-23** with `scripts/verify_live.py`, and the rest of this skill
documents the observed column rather than the spec column.

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

Note the float: `80.50000000000045` is stored as a binary float, so round for
display rather than assuming the value you sent comes back unchanged.

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

## Ordering, which the spec never states

Every list route returns **newest first**. `/v1/workouts` and
`/v1/body_measurements` both start at the most recent entry, and
`/v1/workouts/events` documents the same order.

This is what makes an early stop safe: walking `/v1/workouts` until the last
item on a page falls outside your window covers the window without paging the
whole account.

## Not verified

These come from the spec alone, because the account used for verification could
not produce them:

- **`deleted` workout events.** Three pages of events from the epoch returned
  `updated` only. The `deleted` shape is documented but unobserved.
- **Every write route.** The API has no delete route, so testing `POST` and
  `PUT` leaves permanent data in a real account.
- **The `403` limits** on routines and custom exercises.
