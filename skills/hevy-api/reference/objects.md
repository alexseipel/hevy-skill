# Objects and enums

Every shared shape, field by field, from the pinned
[openapi.json](../openapi.json). `null` in the type column means the field is
nullable. A field marked required is required by the spec.

## Set (in a response)

Returned inside `Workout.exercises[].sets[]` and `Routine.exercises[].sets[]`.

| Field              | Type          | Notes                                            |
| ------------------ | ------------- | ------------------------------------------------ |
| `index`            | number        | position of the set within the exercise, from 0  |
| `type`             | string        | `normal`, `warmup`, `dropset` or `failure`       |
| `weight_kg`        | number, null  | kilograms, and for dumbbells the total of both   |
| `reps`             | number, null  |                                                  |
| `distance_meters`  | number, null  | metres                                           |
| `duration_seconds` | number, null  |                                                  |
| `rpe`              | number, null  | rating of perceived exertion                     |
| `custom_metric`    | number, null  | floors or steps, for stair-machine exercises     |

A routine set carries one more field: `rep_range`, an object of `{start, end}`
or `null`.

## Set (in a request)

`PostWorkoutsRequestSet`, `PostRoutinesRequestSet` and `PutRoutinesRequestSet`
share these fields. None is marked required, and there is no `index`, because
order comes from the array. A set that still carries one is rejected.

| Field              | Type          | Notes                                                  |
| ------------------ | ------------- | ------------------------------------------------------ |
| `type`             | string        | `warmup`, `normal`, `failure` or `dropset`             |
| `weight_kg`        | number, null  |                                                        |
| `reps`             | integer, null |                                                        |
| `distance_meters`  | integer, null |                                                        |
| `duration_seconds` | integer, null |                                                        |
| `custom_metric`    | number, null  |                                                        |
| `rpe`              | number, null  | workout sets only. `6, 7, 7.5, 8, 8.5, 9, 9.5, 10`     |
| `rep_range`        | object, null  | routine sets only. `{start, end}`                      |

**`rpe` is an enum, not a free number.** A value outside that list is a `400`.
A routine set has no `rpe`, and a workout set has no `rep_range`.

## Exercise (in a response)

| Field                  | Type         | Notes                                          |
| ---------------------- | ------------ | ---------------------------------------------- |
| `index`                | number       | position within the workout or routine, from 0 |
| `title`                | string       | resolved from the template, such as `Bench Press (Barbell)` |
| `notes`                | string       |                                                |
| `exercise_template_id` | string       | use it against `/v1/exercise_templates/{id}`   |
| `superset_id`          | number, null | `null` means the exercise is not in a superset |
| `sets`                 | Set[]        |                                                |

A routine exercise adds `rest_seconds`, an integer such as `120`.

The spec calls the response field `supersets_id` and types `rest_seconds` as a
string. Both are wrong ([observed.md](observed.md)). A superset id can be `0`,
so test it against `null` rather than for truthiness.

## Exercise (in a request)

| Field                  | Type          | Notes                                    |
| ---------------------- | ------------- | ---------------------------------------- |
| `exercise_template_id` | string        | such as `D04AC939`                       |
| `superset_id`          | integer, null | the same name the response uses          |
| `rest_seconds`         | integer, null | routines only                            |
| `notes`                | string, null  |                                          |
| `sets`                 | Set[]         |                                          |

The request and response use the same name for `superset_id`, so nothing needs
renaming. A round trip still strips the response-only keys, `index` and
`title` here and `index` on each set, because the write schemas reject
unrecognized keys ([observed.md](observed.md#write-behaviour)).

## Workout

| Field         | Type       | Notes                                       |
| ------------- | ---------- | ------------------------------------------- |
| `id`          | string     | UUID                                        |
| `title`       | string     |                                             |
| `routine_id`  | string, null | the routine it came from, `null` if none  |
| `description` | string     |                                             |
| `start_time`  | string     | ISO 8601                                    |
| `end_time`    | string     | ISO 8601                                    |
| `updated_at`  | string     | ISO 8601                                    |
| `created_at`  | string     | ISO 8601                                    |
| `exercises`   | Exercise[] |                                             |

`is_private` can be sent when creating a workout, and the response schema does
not list it, so do not expect to read it back.

## Routine

| Field        | Type         | Notes                                  |
| ------------ | ------------ | -------------------------------------- |
| `id`         | string       | UUID                                   |
| `title`      | string       |                                        |
| `folder_id`  | number, null | `null` means the default `My Routines` |
| `updated_at` | string       | ISO 8601                               |
| `created_at` | string       | ISO 8601                               |
| `exercises`  | Exercise[]   | routine exercises, with `rest_seconds` |

`notes` can be sent when creating or updating a routine and never comes back,
the same way `is_private` behaves on a workout.

## RoutineFolder

| Field        | Type   | Notes                                     |
| ------------ | ------ | ----------------------------------------- |
| `id`         | number | numeric, unlike every other resource id   |
| `index`      | number | position in the folder list               |
| `title`      | string |                                           |
| `updated_at` | string | ISO 8601                                  |
| `created_at` | string | ISO 8601                                  |

## ExerciseTemplate

| Field                     | Type              | Notes                                        |
| ------------------------- | ----------------- | -------------------------------------------- |
| `id`                      | string            | the value to send as `exercise_template_id`  |
| `title`                   | string            |                                              |
| `type`                    | string            | one of the exercise types below              |
| `primary_muscle_group`    | string            | one muscle group                             |
| `secondary_muscle_groups` | string[]          |                                              |
| `equipment`               | EquipmentCategory | the spec calls this `equipment_category`     |
| `is_custom`               | boolean           | `true` for exercises the account created     |

## ExerciseHistoryEntry

One row per logged set, flattened, with the workout it came from repeated on
every row.

| Field                  | Type          | Notes                        |
| ---------------------- | ------------- | ---------------------------- |
| `workout_id`           | string        |                              |
| `workout_title`        | string        |                              |
| `workout_start_time`   | string        | ISO 8601                     |
| `workout_end_time`     | string        | ISO 8601                     |
| `exercise_template_id` | string        |                              |
| `weight_kg`            | number, null  |                              |
| `reps`                 | integer, null |                              |
| `distance_meters`      | integer, null |                              |
| `duration_seconds`     | integer, null |                              |
| `rpe`                  | number, null  |                              |
| `custom_metric`        | number, null  |                              |
| `set_type`             | string        | `warmup`, `normal`, `failure` or `dropset` |

There is no set index, so rows within one workout keep the order the API sends
them in.

## BodyMeasurement

`date` is the only required field, and it is the key: one entry per date. Every
other field is a nullable number.

A response also carries **`id`** and **`created_at`**, which the spec omits, and
it **leaves out any field that was never recorded** rather than sending `null`.
Strip `id` and `created_at` before writing the entry back.

`weight_kg`, `lean_mass_kg`, `fat_percent`, `neck_cm`, `shoulder_cm`,
`chest_cm`, `left_bicep_cm`, `right_bicep_cm`, `left_forearm_cm`,
`right_forearm_cm`, `abdomen`, `waist`, `hips`, `left_thigh`, `right_thigh`,
`left_calf`, `right_calf`.

**The last seven carry no unit suffix**, unlike the ones above them. They are
centimetres all the same.

`PutBodyMeasurement` is the same object without `date`, which comes from the
path instead. It has no `id` and no `created_at` either.

## Timestamps

| Field | Format | Example |
| ----- | ------ | ------- |
| `start_time`, `end_time` | offset, whole seconds | `2024-08-14T18:30:00+00:00` |
| `created_at`, `updated_at` | `Z`, with milliseconds | `2024-08-14T19:31:12.765Z` |

One object carries both, so a parser written against either alone fails.

## Workout events

`GET /v1/workouts/events` returns `{page, page_count, events[]}`, where each
event is one of two shapes, told apart by `type`:

| `type`      | Fields                                       |
| ----------- | -------------------------------------------- |
| `updated`   | `type`, `workout` (a full `Workout`)         |
| `deleted`   | `type`, `id`, `deleted_at`                   |

`type` and `workout` are required on an update. `type` and `id` are required on
a delete, and `deleted_at` is not, though the one deletion observed on
2026-08-23 carried all three. When the feed has nothing to report, `events` is
absent and an empty `workouts` array takes its place
([observed.md](observed.md#14-an-empty-events-feed-answers-with-the-wrong-key)).

## Enums

**`EquipmentCategory`**: `none`, `barbell`, `dumbbell`, `kettlebell`,
`machine`, `plate`, `resistance_band`, `suspension`, `other`.

**`MuscleGroup`**: `abdominals`, `shoulders`, `biceps`, `triceps`, `forearms`,
`quadriceps`, `hamstrings`, `calves`, `glutes`, `abductors`, `adductors`,
`lats`, `upper_back`, `traps`, `lower_back`, `chest`, `cardio`, `neck`,
`full_body`, `other`.

**`CustomExerciseType`**: `weight_reps`, `reps_only`, `bodyweight_reps`,
`bodyweight_assisted_reps`, `duration`, `weight_duration`, `distance_duration`,
`short_distance_weight`. The type fixes which set fields mean anything: a
`duration` exercise ignores `weight_kg` and `reps`.

**On a dumbbell exercise, `weight_kg` is the total lifted per rep.** Hevy's app
says so on the exercise screen, giving a pair of 10 kg dumbbells as 20 kg.
Nothing in the API enforces it and nothing marks an account that does otherwise
([recipes.md](recipes.md#dumbbell-weight-is-the-total-and-nothing-enforces-it)).

## Units

**The API is metric everywhere, and silent about what the account displays.**

| Field | Unit |
| ----- | ---- |
| `weight_kg`, `lean_mass_kg` | kilograms |
| `distance_meters` | metres |
| every `_cm` measurement | centimetres |
| `duration_seconds` | seconds |

Hevy shows pounds and miles to an account that asks for it, and the app also
sets units per exercise rather than only globally. **No route reports either
setting.** `GET /v1/user/info` returns an id, a name and a profile URL, and
nothing else, so a client cannot discover what its user sees.

The consequence is practical: a number read off the phone will not match the
API for anyone on imperial units, and neither side is wrong. Convert when you
quote a figure back, and label it. One pound is 0.45359237 kilograms by
definition, so a kilogram is about 2.2046 pounds.

`custom_metric` is unrelated to any of this. It is the free-form set field, not
a measurement system.

**Set type**: `warmup`, `normal`, `failure`, `dropset`.
