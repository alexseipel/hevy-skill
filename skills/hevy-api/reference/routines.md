# Routines and routine folders

Seven routes. A routine is a saved plan; a workout is a performed session.
They share the exercise and set shapes in [objects.md](objects.md), with two
differences: a routine set adds `rep_range`, and a routine exercise adds
`rest_seconds`.

## GET /v1/routines

| Parameter  | In     | Default | Notes        |
| ---------- | ------ | ------- | ------------ |
| `api-key`  | header | —       | required     |
| `page`     | query  | 1       | 1 or greater |
| `pageSize` | query  | 10      | maximum 10. The spec's default of 5 is wrong ([observed.md](observed.md)) |

```bash
curl -s "https://api.hevyapp.com/v1/routines?pageSize=10" -H "api-key: $HEVY_API_KEY"
# {"page":1,"page_count":3,"routines":[{"id":"b459cba5-…","title":"Upper Body 💪","folder_id":42,"exercises":[]}]}
```

## POST /v1/routines

Returns `201` with the created `Routine`. The body wraps everything in a
`routine` key.

| Field       | Type               | Notes                                            |
| ----------- | ------------------ | ------------------------------------------------ |
| `title`     | string             |                                                  |
| `folder_id` | number, null       | `null` puts it in the default `My Routines`      |
| `notes`     | string             |                                                  |
| `exercises` | request Exercise[] | with `rest_seconds`, and `rep_range` on sets     |

```bash
curl -s -X POST "https://api.hevyapp.com/v1/routines" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "routine": {
      "title": "April Leg Day 🔥",
      "folder_id": null,
      "notes": "Form over weight.",
      "exercises": [
        { "exercise_template_id": "D04AC939",
          "superset_id": null,
          "rest_seconds": 90,
          "notes": "Slow and controlled.",
          "sets": [
            { "type": "normal", "weight_kg": 100, "reps": 10,
              "rep_range": { "start": 8, "end": 12 } }
          ] } ] } }'
```

`403` means the account is at its routine limit. It is a plan limit, so
retrying does not help. Delete a routine in the app, or reuse an existing one.

## GET /v1/routines/{routineId}

```bash
curl -s "https://api.hevyapp.com/v1/routines/$ROUTINE_ID" -H "api-key: $HEVY_API_KEY"
# {"routine": { … }}
```

**This one wraps its result in `{"routine": …}`.** The workout, folder and
template equivalents return the object bare, so a shared unwrapping helper has
to special-case it.

The spec documents `400` here rather than `404`.

## PUT /v1/routines/{routineId}

Returns the updated `Routine`. The body is the same shape as the create body,
with `notes` nullable.

Like a workout update, it replaces the routine, so send the full exercise list.
`404` means the routine does not exist or belongs to another account.

## Routine folders

A folder holds routines and carries an `index` that sets its position in the
list. Ids are numbers here, unlike the UUID strings every other resource uses.

### GET /v1/routine_folders

| Parameter  | In     | Default | Notes        |
| ---------- | ------ | ------- | ------------ |
| `api-key`  | header | —       | required     |
| `page`     | query  | 1       | 1 or greater |
| `pageSize` | query  | 5       | maximum 10   |

```bash
curl -s "https://api.hevyapp.com/v1/routine_folders" -H "api-key: $HEVY_API_KEY"
# {"page":1,"page_count":1,"routine_folders":[{"id":42,"index":1,"title":"Push Pull 🏋️‍♂️"}]}
```

### POST /v1/routine_folders

Returns `201` with the created `RoutineFolder`. `title` is the only field.

```bash
curl -s -X POST "https://api.hevyapp.com/v1/routine_folders" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: application/json" \
  -d '{"routine_folder": {"title": "Push Pull 🏋️‍♂️"}}'
```

**A new folder always lands at index 0**, and every existing folder shifts down
by one. Cached `index` values from an earlier page are stale the moment this
call succeeds, so refetch the list rather than adjusting them locally.

### GET /v1/routine_folders/{folderId}

```bash
curl -s "https://api.hevyapp.com/v1/routine_folders/42" -H "api-key: $HEVY_API_KEY"
```

Returns a bare `RoutineFolder`. `404` if the folder does not exist.

There is no update or delete route for a folder. To move a routine between
folders, change `folder_id` with `PUT /v1/routines/{routineId}`.
