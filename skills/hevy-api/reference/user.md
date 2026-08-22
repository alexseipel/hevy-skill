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
            "name": "John doe",
            "url": "https://hevy.com/user/jhon" } }
```

The result is wrapped in `data`, which no other route does.

| Field  | Type   | Notes                        |
| ------ | ------ | ---------------------------- |
| `id`   | string | UUID for the account         |
| `name` | string | the display name             |
| `url`  | string | the public profile URL       |

`404` is the documented failure, and a wrong key gives `401` before that.

**Use it as the key check.** It takes no parameters and touches no training
data, which makes it the cheapest way to prove a key works before an import.

**Nothing else about the account is exposed.** There is no route for display
units and none for subscription state. A `403` elsewhere in the API therefore
cannot be traced back to which limit produced it. Weights are kilograms and
distances are metres in the payload whatever the app displays.
