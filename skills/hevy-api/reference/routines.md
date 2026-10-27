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
| `pageSize` | query  | 10      | maximum 10 |

```bash
curl -s "https://api.hevyapp.com/v1/routines?pageSize=10" -H "api-key: $HEVY_API_KEY"
# {"page":1,"page_count":3,"routines":[{"id":"b459cba5-…","title":"Upper Body 💪","folder_id":42,"exercises":[]}]}
```

**This list is grouped by folder, not sorted by date**
([observed.md](observed.md#ordering-which-the-spec-never-states)). Folders come
in the order they were created and unfoldered routines come last, so a newly
created routine can sit on the last page. Fetch it by id instead of looking for
it at the top.

## POST /v1/routines

Returns `201`. The current [spec](../openapi.json) declares
`{"routine": {...}}`, with the routine as an object. Live writes on
2026-08-23 returned `{"routine": [{...}]}` instead, and successful writes
were not repeated during the 2026-10-27 refresh.

Handle both shapes until re-verified
([observed.md](observed.md#11-writes-answer-with-the-object-wrapped-and-in-an-array)):

```python
routine = body["routine"]
if isinstance(routine, list):
    routine = routine[0]
```

The request body wraps everything in a `routine` key too.

| Field       | Type               | Notes                                            |
| ----------- | ------------------ | ------------------------------------------------ |
| `title`     | string             |                                                  |
| `folder_id` | number, null       | `null` puts it in the default `My Routines`      |
| `notes`     | string             | write-only: accepted here, absent from every response |
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

`403` means the account is at its routine limit, which is a free-plan limit of
4 routines: an active Pro key cannot reach it
([observed.md](observed.md#the-403-limits-are-free-plan-limits)). Retrying
does not help.

## GET /v1/routines/{routineId}

```bash
curl -s "https://api.hevyapp.com/v1/routines/$ROUTINE_ID" -H "api-key: $HEVY_API_KEY"
# {"routine": { … }}
```

**This one wraps its result in `{"routine": …}`.** The workout, folder and
template equivalents return the object bare, so a shared unwrapping helper has
to special-case it.

Here the wrapper holds an object. For writes, handle both the documented
object and the previously observed array.

The spec documents `400` here rather than `404`. The body is
`{"error": "Routine not found"}` as JSON, unlike the plain-text `404`s on
workouts, folders and templates
([observed.md](observed.md#17-a-404-body-is-plain-text-on-half-the-routes)).

## PUT /v1/routines/{routineId}

Returns `200`, wrapped like the create response. The request body is the same
shape as the create body, with `notes` nullable.

**It replaces the routine.** Verified on 2026-08-23 the same way as the workout
route: two exercises in, one sent on the update, one left afterwards. Send the
full exercise list every time, stripped of the keys only reads carry: `index`
on sets, `index` and `title` on exercises
([observed.md](observed.md#write-behaviour)). A routine cannot be emptied,
because `exercises: []` is a `400`. `404` means the routine does not exist or
belongs to another account.

## Routine folders

A folder holds routines and carries an `index` that sets its position in the
list. Ids are numbers here, unlike the UUID strings every other resource uses.

### GET /v1/routine_folders

| Parameter  | In     | Default | Notes        |
| ---------- | ------ | ------- | ------------ |
| `api-key`  | header | —       | required     |
| `page`     | query  | 1       | 1 or greater |
| `pageSize` | query  | 10      | maximum 10   |

```bash
curl -s "https://api.hevyapp.com/v1/routine_folders" -H "api-key: $HEVY_API_KEY"
# {"page":1,"page_count":1,"routine_folders":[{"id":42,"index":1,"title":"Push Pull 🏋️‍♂️"}]}
```

### POST /v1/routine_folders

Returns `201` as `{"routine_folder": { … }}`, wrapped in a key and holding an
object, as observed on 2026-08-23
([observed.md](observed.md#11-writes-answer-with-the-object-wrapped-and-in-an-array)).
`title` is the only field you send.

```bash
curl -s -X POST "https://api.hevyapp.com/v1/routine_folders" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: application/json" \
  -d '{"routine_folder": {"title": "Push Pull 🏋️‍♂️"}}'
```

**A new folder always lands at index 0**, and every existing folder shifts down
by one. Verified on 2026-08-23: five folders at indexes 0 to 4 became 1 to 5,
relative order intact. Cached `index` values are stale the moment this call
succeeds, so refetch the list rather than adjusting them locally.

There is no folder update or delete route, so the API cannot undo the
renumbering. Creating a folder is the one write here that changes data you did
not name.

### GET /v1/routine_folders/{folderId}

```bash
curl -s "https://api.hevyapp.com/v1/routine_folders/42" -H "api-key: $HEVY_API_KEY"
```

Returns a bare `RoutineFolder`. `404` if the folder does not exist, sent as the
bare text `Routine folder not found` rather than JSON
([observed.md](observed.md#17-a-404-body-is-plain-text-on-half-the-routes)).

To move a routine between folders, change `folder_id` with
`PUT /v1/routines/{routineId}`.
