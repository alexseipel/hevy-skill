# Authentication, OAuth and webhooks

Two credentials reach the API, and the spec accepts either on all 24
operations. This file restates
[Hevy's authentication guide](https://developers.hevy.com/authentication) as
read on 2026-11-18. **The OAuth flow was not exercised**: of everything below,
only the two `401` bodies and the webhook subscription route were observed.

| Credential         | Header                          | Reaches                         | `401` body                                |
| ------------------ | ------------------------------- | ------------------------------- | ----------------------------------------- |
| personal key       | `api-key: <key>`                | your own account, with Hevy Pro | `InvalidApiKey`, plain text               |
| OAuth access token | `Authorization: Bearer <token>` | accounts connected to your app  | `{"message": "Invalid or expired token"}` |

Neither `401` is in the spec
([observed.md](observed.md#16-a-401-is-plain-text-for-a-key-and-json-for-a-token)).

## Personal key

Issued at `https://developers.hevy.com/api-key`, where the older
`https://hevy.com/settings?developer` now redirects. It reaches the whole
account and carries no scopes.

## OAuth

An OAuth app is created at `https://developers.hevy.com/apps` and yields a
client id and a client secret. It serves up to 10 accounts until Hevy reviews
it.

1. **Send the user to Hevy.** `redirect_uri` must match one registered on the
   app, and `state` is a random string to check when the user returns.

   ```
   https://hevy.com/oauth/authorize?client_id=CLIENT_ID&redirect_uri=https://yourapp.example/callback&state=RANDOM
   ```

2. **Read `code` from the callback.** It works once and expires after 10
   minutes. A user who declines arrives with `error=access_denied` instead.

3. **Exchange the code from a server**, so the secret never reaches a browser
   or an app.

   ```bash
   curl -s -X POST https://hevy.com/api/token \
     -d grant_type=authorization_code -d code="$CODE" \
     -d client_id="$CLIENT_ID" -d client_secret="$CLIENT_SECRET"
   ```

   ```json
   { "access_token": "…", "token_type": "Bearer", "expires_in": 3600,
     "refresh_token": "…", "user_id": "11111111-2222-3333-4444-555555555555",
     "username": "jane_lifts", "profile_pic": null }
   ```

4. **Call the API** with `Authorization: Bearer <access_token>`. The token is
   valid for one hour.

5. **Refresh** by posting `grant_type=refresh_token` and `refresh_token` to the
   same URL, with the client id and secret.

**A refresh token works once.** Each refresh returns a new one and retires the
old, so store the new token before using the new access token. Never refresh
one token from two places at once.

Store `user_id` beside the tokens, because webhooks identify the user by it.
`username` and `profile_pic`, a thumbnail URL or `null`, arrive with the first
exchange whatever the scopes, and a refresh returns neither.

### Scopes

Scopes are fixed when the app is created, not requested per authorisation, and
the user sees them before connecting. A `modify` scope includes its `read`
counterpart.

| Scope                     | Routes                                                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `read-workout`            | `GET` on `/v1/workouts`, `/v1/workouts/count`, `/v1/workouts/events`, `/v1/workouts/{workoutId}`, `/v1/exercise_history/{exerciseTemplateId}` |
| `modify-workout`          | `POST /v1/workouts`, `PUT /v1/workouts/{workoutId}`, `POST /v1/workouts/{workoutId}/images`                                    |
| `read-routine`            | `GET` on `/v1/routines`, `/v1/routines/{routineId}`, `/v1/routine_folders`, `/v1/routine_folders/{folderId}`                   |
| `modify-routine`          | `POST /v1/routines`, `PUT /v1/routines/{routineId}`, `POST /v1/routine_folders`                                                |
| `read-exercise`           | `GET` on `/v1/exercise_templates`, `/v1/exercise_templates/{exerciseTemplateId}`                                               |
| `modify-exercise`         | `POST /v1/exercise_templates`                                                                                                  |
| `read-body-measurement`   | `GET` on `/v1/body_measurements`, `/v1/body_measurements/{date}`                                                               |
| `modify-body-measurement` | `POST /v1/body_measurements`, `PUT /v1/body_measurements/{date}`, `PUT /v1/body_measurements/{date}/image`                     |
| `read-profile`            | `GET /v1/user/info`                                                                                                            |

The guide also lists four pinned-note routes under the two exercise scopes.
The API does not serve them
([observed.md](observed.md#19-the-guides-name-routes-the-api-does-not-serve)).

## App webhooks

An OAuth app with a webhook URL receives a `POST` whenever a connected user
saves a new workout, provided that user granted `read-workout` or
`modify-workout`.

```json
{ "type": "workout.created", "workoutId": "f1085cdb-…", "userId": "11111111-…" }
```

`userId` is the `user_id` from the token response. Fetch the workout with
`GET /v1/workouts/{workoutId}` and that user's access token.

**Verify `Hevy-Signature` before parsing the body.** The header is `sha256=`
followed by the hex HMAC-SHA256 of the raw body, keyed with the client secret:

```python
import hashlib, hmac

def is_from_hevy(raw_body: bytes, signature: str, client_secret: str) -> bool:
    digest = hmac.new(client_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest("sha256=" + digest, signature)
```

| Delivery rule   | Detail                                                                      |
| --------------- | --------------------------------------------------------------------------- |
| deadline        | answer `200` within 5 seconds                                               |
| retries         | any other outcome is retried up to 5 times, so a `workoutId` can repeat     |
| redirects       | not followed                                                                |
| address         | public only: local and private network addresses are refused                |
| secret rotation | later requests are signed with the new secret                               |

`workout.created` is the only event type the guide lists, so edits and
deletions still need
[the events feed](workouts.md#get-v1workoutsevents).

## Personal webhook

Hevy's key page is titled "API key & webhooks" and sits behind a login, so its
webhook documentation was not read. A subscription route is live and absent
from the spec
([observed.md](observed.md#20-a-webhook-subscription-route-the-spec-omits)).
Whether that page manages it is unverified.

<!-- UNVERIFIED: the body POST /v1/webhook-subscription takes, and the payload a personal webhook delivers. -->
