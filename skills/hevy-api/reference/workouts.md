# Workouts

Six routes. Field-level detail for `Workout`, `Exercise` and `Set` is in
[objects.md](objects.md).

## GET /v1/workouts

A page of complete workouts, each with its exercises and sets.

| Parameter  | In     | Default | Notes                    |
| ---------- | ------ | ------- | ------------------------ |
| `api-key`  | header | —       | required                 |
| `page`     | query  | 1       | 1 or greater             |
| `pageSize` | query  | 5       | maximum 10               |

```bash
curl -s "https://api.hevyapp.com/v1/workouts?page=1&pageSize=10" \
  -H "api-key: $HEVY_API_KEY"
```

```json
{ "page": 1, "page_count": 5, "workouts": [ { "id": "b459cba5-…", "title": "Morning Workout 💪", "exercises": [] } ] }
```

`400` means `pageSize` was over 10 or `page` was below 1.

## POST /v1/workouts

Creates a workout and returns `201` with the created `Workout`, including the
ids the server assigned.

The body wraps everything in a `workout` key:

| Field         | Type                | Notes                                       |
| ------------- | ------------------- | ------------------------------------------- |
| `title`       | string              |                                             |
| `description` | string, null        |                                             |
| `start_time`  | string              | ISO 8601, such as `2024-08-14T12:00:00Z`    |
| `end_time`    | string              | ISO 8601                                    |
| `is_private`  | boolean             | accepted here, absent from the response     |
| `exercises`   | request Exercise[]  | see [objects.md](objects.md)                |

```bash
curl -s -X POST "https://api.hevyapp.com/v1/workouts" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "workout": {
      "title": "Friday Leg Day 🔥",
      "description": "Medium intensity, quad focus.",
      "start_time": "2024-08-14T12:00:00Z",
      "end_time": "2024-08-14T12:30:00Z",
      "is_private": false,
      "exercises": [
        { "exercise_template_id": "D04AC939",
          "superset_id": null,
          "notes": "Felt good today.",
          "sets": [
            { "type": "warmup", "weight_kg": 60, "reps": 8, "rpe": null },
            { "type": "normal", "weight_kg": 100, "reps": 10, "rpe": 8.5 }
          ] } ] } }'
```

The spec marks no field as required, so the practical minimum is a
`start_time`, an `end_time` and one exercise with one set. Resolve every
`exercise_template_id` first, because an unknown id is a `400` with
`{"error": "…"}`.

Sets are ordered by their position in the array. Do not send `index`.

## GET /v1/workouts/count

```bash
curl -s "https://api.hevyapp.com/v1/workouts/count" -H "api-key: $HEVY_API_KEY"
# {"workout_count": 42}
```

Use it to size a backfill before paging through `/v1/workouts` at 10 per page.

## GET /v1/workouts/events

The incremental feed. Events run newest first.

| Parameter  | In     | Default                | Notes                        |
| ---------- | ------ | ---------------------- | ---------------------------- |
| `api-key`  | header | —                      | required                     |
| `page`     | query  | 1                      | 1 or greater                 |
| `pageSize` | query  | 5                      | maximum 10                   |
| `since`    | query  | `1970-01-01T00:00:00Z` | ISO 8601 timestamp           |

```bash
curl -s "https://api.hevyapp.com/v1/workouts/events?since=2024-08-01T00:00:00Z&pageSize=10" \
  -H "api-key: $HEVY_API_KEY"
```

```json
{ "page": 1, "page_count": 2, "events": [
  { "type": "updated", "workout": { "id": "b459cba5-…", "title": "Morning Workout 💪" } },
  { "type": "deleted", "id": "efe6801c-…", "deleted_at": "2021-09-13T12:00:00Z" } ] }
```

Branch on `type`: `updated` carries a full `workout` to upsert, `deleted`
carries only an `id` to remove. This is the only route that reports deletions,
so a client that polls `/v1/workouts` alone never learns a workout is gone.

The default `since` makes an unfiltered call a full history dump. Always pass
`since` after the first sync.

`500` is a documented response here, so retry with backoff rather than treating
it as fatal.

## GET /v1/workouts/{workoutId}

```bash
curl -s "https://api.hevyapp.com/v1/workouts/$WORKOUT_ID" -H "api-key: $HEVY_API_KEY"
```

Returns a bare `Workout`, not wrapped in a key. `404` if the id is unknown or
belongs to another account.

## PUT /v1/workouts/{workoutId}

Takes the same body as `POST /v1/workouts` and returns the updated `Workout`.

**It replaces the workout.** Every exercise and set you leave out is dropped,
so read the workout, edit the object, and send the whole thing back. The
response and the request use the same field names, so nothing needs renaming
along the way.

`400` returns `{"error": "…"}`.
