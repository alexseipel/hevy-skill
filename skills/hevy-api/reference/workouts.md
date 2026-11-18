# Workouts

Seven routes. Field-level detail for `Workout`, `Exercise` and `Set` is in
[objects.md](objects.md).

## GET /v1/workouts

A page of complete workouts, each with its exercises and sets.

| Parameter  | In     | Default | Notes                    |
| ---------- | ------ | ------- | ------------------------ |
| `page`     | query  | 1       | 1 or greater             |
| `pageSize` | query  | 10      | maximum 10 |

```bash
curl -s "https://api.hevyapp.com/v1/workouts?page=1&pageSize=10" \
  -H "api-key: $HEVY_API_KEY"
```

```json
{ "page": 1, "page_count": 5, "workouts": [ { "id": "b459cba5-…", "title": "Morning Workout 💪", "exercises": [] } ] }
```

`400` means `pageSize` was over 10 or `page` was negative. `page=0` returns
page 1, and a page past the last returns `200` with an empty array
([observed.md](observed.md#5-and-6-page-bounds)).

## POST /v1/workouts

Creates a workout and returns `201` as `{"workout": [ {...} ]}`, matching
the current [response schema](../openapi.json).
Reach the created object with `body.workout[0]`, and read its `id` from there.

The body wraps everything in a `workout` key:

| Field         | Type                | Notes                                       |
| ------------- | ------------------- | ------------------------------------------- |
| `title`       | string              |                                             |
| `description` | string, null        |                                             |
| `start_time`  | string              | ISO 8601, such as `2024-08-14T12:00:00Z`    |
| `end_time`    | string              | ISO 8601                                    |
| `is_private`  | boolean             | optional, defaults to `false`, absent from the response |
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

The spec requires the `workout` wrapper and its `title`, `start_time`,
`end_time` and `exercises` fields. Resolve every `exercise_template_id` first,
because an unknown id is a `400` with `{"error": "…"}`.

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
| `page`     | query  | 1                      | 1 or greater                 |
| `pageSize` | query  | 10                     | maximum 10 |
| `since`    | query  | —                      | ISO 8601. The spec's epoch default is wrong: omitting `since` returns no events ([observed.md](observed.md)) |

```bash
curl -s "https://api.hevyapp.com/v1/workouts/events?since=2024-08-01T00:00:00Z&pageSize=10" \
  -H "api-key: $HEVY_API_KEY"
```

```json
{ "page": 1, "page_count": 2, "events": [
  { "type": "updated", "workout": { "id": "b459cba5-…", "title": "Morning Workout 💪" } },
  { "type": "deleted", "id": "efe6801c-…", "deleted_at": "2021-09-13T12:00:00Z" } ] }
```

With nothing to report, `events` is an empty array. Up to 2026-10-27 the key
was missing instead, so `payload.get("events", [])` is the read that survived
both
([observed.md](observed.md#14-an-empty-events-feed-answered-with-the-wrong-key)).

Branch on `type`: `updated` carries a full `workout` to upsert, `deleted`
carries only an `id` to remove. This is the only route that reports deletions,
so a client that polls `/v1/workouts` alone never learns a workout is gone.

Pass `since` on every call: the epoch for a first backfill, the stored
watermark after. Omitting it does not dump the full history, whatever the
spec's default suggests
([observed.md](observed.md#10-omitting-since-is-not-an-epoch-backfill)).

`500` is a documented response here, so retry with backoff rather than treating
it as fatal.

## GET /v1/workouts/{workoutId}

```bash
curl -s "https://api.hevyapp.com/v1/workouts/$WORKOUT_ID" -H "api-key: $HEVY_API_KEY"
```

Returns a bare `Workout`, not wrapped in a key. `404` if the id is unknown or
belongs to another account, and **that `404` is the bare text `Workout not
found` under `text/html`**, not JSON
([observed.md](observed.md#17-a-404-body-is-plain-text-on-three-routes)).

## PUT /v1/workouts/{workoutId}

Takes the same body as `POST /v1/workouts` and returns `200`.

**It replaces the workout.** Verified on 2026-11-18: a workout with two
exercises, updated with a body carrying one, came back with one. Every exercise
you leave out is dropped, so read the workout, edit the object, and send the
whole thing back. Its images are kept.

**Strip the read-only keys first.** The write schema rejects unrecognized
keys, and a read carries four: `index` on every set, `index` and `title` on
every exercise, `media` on the workout. Sending them back is a `400` with
"Unrecognized key(s)" ([observed.md](observed.md#write-behaviour)).

The response is wrapped the same way as the create response, so read the result
from `body.workout[0]`.

`400` returns `{"error": "…"}`.

## POST /v1/workouts/{workoutId}/images

Adds one image after the workout's existing media and returns `201` with the
updated `Workout`, bare, unlike the create and the update. **The body is the
raw image, not JSON and not multipart**, under a `Content-Type` of
`image/jpeg`, `image/png` or `image/webp`.

```bash
curl -s -X POST "https://api.hevyapp.com/v1/workouts/$WORKOUT_ID/images" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: image/jpeg" \
  --data-binary @photo.jpg
```

| Limit             | Value                                                    |
| ----------------- | -------------------------------------------------------- |
| media per workout | 3 images and videos in total                             |
| file              | 10 MB and 50 megapixels                                  |
| stored as         | JPEG, resized to fit 800 by 800 pixels                   |
| uploads           | 100 per 24 hours for each account, across both image routes |

| Status | Meaning                                              | Body        |
| ------ | ---------------------------------------------------- | ----------- |
| 400    | not a valid image, or the workout already holds 3    | `{"error"}` |
| 404    | no such workout                                      | `{"error"}`, where the `GET` sends plain text |
| 413    | larger than 10 MB                                    | an HTML page |
| 415    | a `Content-Type` outside the three, or an empty body | `{"error"}` |

The image comes back in the workout's `media` array as
`{"type": "image", "url": "…"}` ([objects.md](objects.md#workoutmedia)).

Verified with three uploads on 2026-11-18
([observed.md](observed.md#image-uploads)). A 1,200 by 1,600 PNG was stored as
a 600 by 800 JPEG, and a 64 by 64 WebP was not enlarged.

**Nothing removes an image.** The route allows `POST` only, and a later
`PUT /v1/workouts/{workoutId}` keeps the media. The stored URL answers without
a key, on a private workout too.
