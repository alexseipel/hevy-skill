# Body measurements

Five routes. One entry per date, and the date is the key: there is no separate
measurement id anywhere in this resource.

Every field except `date` is a nullable number. The full list is in
[objects.md](objects.md#bodymeasurement).

## GET /v1/body_measurements

| Parameter  | In     | Default | Notes                                    |
| ---------- | ------ | ------- | ---------------------------------------- |
| `page`     | query  | 1       | 1 or greater                             |
| `pageSize` | query  | 10      | maximum 10, so the default is the maximum |

```bash
curl -s "https://api.hevyapp.com/v1/body_measurements?page=1&pageSize=10" \
  -H "api-key: $HEVY_API_KEY"
```

```json
{ "page": 1, "page_count": 3, "body_measurements": [
  { "id": 10000001, "date": "2024-08-14", "weight_kg": 80.50000000000045,
    "fat_percent": 18.5, "created_at": "2024-08-14T11:59:31.028Z" } ] }
```

**`id` and `created_at` are absent from the spec**, and a field that was never
recorded is left out rather than sent as `null`
([observed.md](observed.md)).

A page past the end returns `200` and an empty array here, as on every other
list route, where the spec documents `400`
([observed.md](observed.md#5-and-6-page-bounds)).

## POST /v1/body_measurements

Creates the entry for one date and returns **`201`**, as the current spec
documents. The body is empty, so read the entry back with
`GET /v1/body_measurements/{date}` when you need the stored values.

```bash
curl -s -X POST "https://api.hevyapp.com/v1/body_measurements" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: application/json" \
  -d '{ "date": "2024-08-14", "weight_kg": 80.5, "fat_percent": 18.5 }'
```

The body is a `BodyMeasurement` directly, with no wrapper key. Only `date` is
required, in `YYYY-MM-DD`. This route validates the body before it checks the
key, so a malformed request answers `400` whether or not the key is valid
([observed.md](observed.md#16-a-401-is-plain-text-for-a-key-and-json-for-a-token)).

**`409` means an entry for that date already exists.** Treat it as the signal
to switch to `PUT`, not as an error to retry. An importer that walks a range of
dates should expect it on every date it has already written.

## GET /v1/body_measurements/{date}

```bash
curl -s "https://api.hevyapp.com/v1/body_measurements/2024-08-14" \
  -H "api-key: $HEVY_API_KEY"
```

Returns a bare `BodyMeasurement`. `404` returns `{"error": "…"}` when no entry
exists for that date, one of the two `404`s that are JSON
([observed.md](observed.md#17-a-404-body-is-plain-text-on-three-routes)).

## PUT /v1/body_measurements/{date}

Returns `200` with an empty body. The request body is a `BodyMeasurement`
without `date`, because the path carries it.

**Every omitted field is set to `null`.** This is a full overwrite, not a
patch, and it is the sharpest edge in the API. Verified on 2026-08-23: an entry
holding `weight_kg`, `fat_percent` and `chest_cm`, updated with
`{"weight_kg": 72}` alone, came back holding the weight and nothing else.

Read, merge, then write. `PutBodyMeasurement` has no `date`, no `id` and no
`created_at`, so all three come out before the write:

```bash
DATE=2024-08-14
curl -s "https://api.hevyapp.com/v1/body_measurements/$DATE" -H "api-key: $HEVY_API_KEY" \
  | jq 'del(.date, .id, .created_at) | .weight_kg = 81' \
  | curl -s -X PUT "https://api.hevyapp.com/v1/body_measurements/$DATE" \
      -H "api-key: $HEVY_API_KEY" -H "Content-Type: application/json" --data-binary @-
```

`404` means there is nothing at that date to update, so create it with `POST`
instead.

## PUT /v1/body_measurements/{date}/image

Sets the progress picture of an existing entry, replacing any current one, and
returns `200` with the updated `BodyMeasurement`. The body is the raw image
under `image/jpeg`, `image/png` or `image/webp`, as on
[the workout image route](workouts.md#post-v1workoutsworkoutidimages).

```bash
curl -s -X PUT "https://api.hevyapp.com/v1/body_measurements/2024-08-14/image" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: image/jpeg" \
  --data-binary @progress.jpg
```

The file may be up to 10 MB and 50 megapixels, and is stored as a JPEG fitting
900 by 1,200 pixels. `404` means no entry exists for the date, so create it
first. `400`, `413` and `415` mean what they mean on the workout route, and the
two routes share one limit of 100 uploads per 24 hours.

The entry then carries `picture_url`, which the spec marks nullable and
read-only. None of the entries read on 2026-11-18 carried the field.

**This section is the spec's word.** The route entered the spec on 2026-11-18
and no upload was made. Observed that day: it allows `PUT` only and checks the
key before the body.

<!-- UNVERIFIED: whether PUT /v1/body_measurements/{date}, which nulls omitted fields, keeps the picture. -->
