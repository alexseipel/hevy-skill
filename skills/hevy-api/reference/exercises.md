# Exercise templates and history

Four routes. An exercise template is the definition of a movement, and its `id`
is the value every workout and routine references as `exercise_template_id`.

## GET /v1/exercise_templates

The catalogue: Hevy's built-in exercises plus the account's custom ones.

| Parameter  | In     | Default | Notes                            |
| ---------- | ------ | ------- | -------------------------------- |
| `api-key`  | header | —       | required                         |
| `page`     | query  | 1       | 1 or greater                     |
| `pageSize` | query  | 5       | maximum 100, the highest cap here |

```bash
curl -s "https://api.hevyapp.com/v1/exercise_templates?pageSize=100" \
  -H "api-key: $HEVY_API_KEY"
```

```json
{ "page": 1, "page_count": 5, "exercise_templates": [
  { "id": "3BC06AD3", "title": "21s Bicep Curl", "type": "weight_reps",
    "primary_muscle_group": "biceps", "secondary_muscle_groups": [],
    "equipment": "barbell", "is_custom": false } ] }
```

**The field is `equipment` when reading**, not the `equipment_category` the
spec names ([observed.md](observed.md)). Ids are short hex strings such as
`3BC06AD3`, not the UUIDs the spec's examples show.

**There is no search parameter.** Page the whole catalogue once at
`pageSize=100`, build a title-to-id map, and cache it. Every workout and
routine you create depends on that map, and rebuilding it per call wastes the
largest page budget the API offers.

`is_custom` separates the account's own exercises from the built-in set.

## POST /v1/exercise_templates

Creates a custom exercise. It answers `200` rather than `201`, and the body is
`{"id": 123}` with an integer, while `ExerciseTemplate.id` is a string
everywhere else. Fetch the template afterwards if you need its canonical form.

The body wraps everything in an `exercise` key.

| Field                | Type          | Notes                                        |
| -------------------- | ------------- | -------------------------------------------- |
| `title`              | string        |                                              |
| `exercise_type`      | enum          | one of the `CustomExerciseType` values       |
| `equipment_category` | enum          | on the way in only, read back as `equipment` |
| `muscle_group`       | enum          | the primary muscle group                     |
| `other_muscles`      | enum[]        | secondary muscle groups                      |

```bash
curl -s -X POST "https://api.hevyapp.com/v1/exercise_templates" \
  -H "api-key: $HEVY_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "exercise": {
      "title": "Bench Press",
      "exercise_type": "weight_reps",
      "equipment_category": "barbell",
      "muscle_group": "chest",
      "other_muscles": ["biceps", "triceps"]
    } }'
```

Every enum value is listed in [objects.md](objects.md#enums). A value outside
those lists is a `400`.

`403` returns `{"error": "exceeds-custom-exercise-limit"}`, which is a plan
limit rather than a rate limit.

**`exercise_type` decides which set fields carry meaning.** A `duration`
exercise ignores `weight_kg` and `reps`, and a `distance_duration` exercise
uses `distance_meters` with `duration_seconds`. Pick the type from how the
movement is actually logged.

## GET /v1/exercise_templates/{exerciseTemplateId}

```bash
curl -s "https://api.hevyapp.com/v1/exercise_templates/D04AC939" \
  -H "api-key: $HEVY_API_KEY"
```

Returns a bare `ExerciseTemplate`. `404` if the id is unknown.

## GET /v1/exercise_history/{exerciseTemplateId}

Every set ever logged for one exercise, flattened into rows, with the workout
repeated on each row.

| Parameter    | In     | Notes                                       |
| ------------ | ------ | ------------------------------------------- |
| `api-key`    | header | required                                    |
| `start_date` | query  | optional, ISO 8601, filters from this date  |
| `end_date`   | query  | optional, ISO 8601, filters up to this date |

```bash
curl -s "https://api.hevyapp.com/v1/exercise_history/D04AC939?start_date=2024-01-01T00:00:00Z" \
  -H "api-key: $HEVY_API_KEY"
```

```json
{ "exercise_history": [
  { "workout_id": "b459cba5-…", "workout_title": "Morning Workout 💪",
    "workout_start_time": "2024-01-01T12:00:00Z", "workout_end_time": "2024-01-01T13:00:00Z",
    "exercise_template_id": "D04AC939", "weight_kg": 100, "reps": 10,
    "distance_meters": null, "duration_seconds": null, "rpe": 8.5,
    "custom_metric": null, "set_type": "normal" } ] }
```

**This route is not paginated**, so an exercise with years of history returns
one large response. Bound it with `start_date` and `end_date` rather than
fetching everything and filtering locally.

There is no set index in a row. Rows keep the order the API returns them in, so
preserve that order if set sequence matters to your analysis.

`400` covers both an invalid parameter and a malformed date.
