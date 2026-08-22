# Body measurements

Four routes. One entry per date, and the date is the key: there is no separate
measurement id anywhere in this resource.

Every field except `date` is a nullable number. The full list is in
[objects.md](objects.md#bodymeasurement).

## GET /v1/body_measurements

| Parameter  | In     | Default | Notes                                    |
| ---------- | ------ | ------- | ---------------------------------------- |
| `api-key`  | header | —       | required                                 |
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

A page past the end returns `404` here, and on every other list route too,
whatever their spec entries document.

## POST /v1/body_measurements

Creates the entry for one date and returns `200` with an empty body. Read it
back with `GET /v1/body_measurements/{date}` if you need the stored values.

```bash
curl -s -X POST "https://api.hevyapp.com/v1/body_measurements" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: application/json" \
  -d '{ "date": "2024-08-14", "weight_kg": 80.5, "fat_percent": 18.5 }'
```

The body is a `BodyMeasurement` directly, with no wrapper key. Only `date` is
required, in `YYYY-MM-DD`.

**`409` means an entry for that date already exists.** Treat it as the signal
to switch to `PUT`, not as an error to retry. An importer that walks a range of
dates should expect it on every date it has already written.

## GET /v1/body_measurements/{date}

```bash
curl -s "https://api.hevyapp.com/v1/body_measurements/2024-08-14" \
  -H "api-key: $HEVY_API_KEY"
```

Returns a bare `BodyMeasurement`. `404` returns `{"error": "…"}` when no entry
exists for that date.

## PUT /v1/body_measurements/{date}

Returns `200` with an empty body. The request body is a `BodyMeasurement`
without `date`, because the path carries it.

**Every omitted field is set to `null`.** This is a full overwrite, not a
patch. Sending `{"weight_kg": 81}` erases the body-fat percentage and every
circumference recorded for that date. It is the sharpest edge in the API.

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
