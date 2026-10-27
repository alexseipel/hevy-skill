# User

One route, and the only one that says anything about the account itself.

## GET /v1/user/info

| Parameter | In     | Notes    |
| --------- | ------ | -------- |
| `api-key` | header | required |

```bash
curl -s "https://api.hevyapp.com/v1/user/info" -H "api-key: $HEVY_API_KEY"
```

```json
{ "data": { "id": "9c465af3-de7d-42bc-9c7c-f0170396358b",
            "username": "jhon",
            "name": "John doe",
            "url": "https://hevy.com/user/jhon",
            "weight_unit": "kg", "distance_unit": "kilometers",
            "is_pro": true } }
```

The result is wrapped in `data`, which no other route does.

| Field  | Type   | Notes                        |
| ------ | ------ | ---------------------------- |
| `id`   | string | UUID for the account         |
| `username` | string | the account's username |
| `name` | string | the display name             |
| `url`  | string | the public profile URL       |
| `weight_unit` | string | `kg` or `lbs`, defaults to `kg` if unset |
| `distance_unit` | string | `kilometers` or `miles`, defaults to `kilometers` if unset |
| `is_pro` | boolean | whether the account has an active Hevy Pro subscription |

These fields are documented in the current [UserInfo schema](../openapi.json)
and were checked live on 2026-10-27 with `scripts/verify_live.py`.

`404` is the documented failure, and a wrong key gives `401` before that.

**Use it as the key check.** It takes no parameters and touches no training
data, which makes it the cheapest way to prove a key works before an import.

Use the unit preferences when displaying results. Weights remain kilograms
and distances remain metres in training payloads, so convert before display.
Per-exercise unit overrides are not exposed by this schema.

The client returns these fields unchanged through `python3 scripts/hevy.py user`.
Its `summary` command defaults to kilograms: use `--unit lb` when `weight_unit`
is `lbs`.
