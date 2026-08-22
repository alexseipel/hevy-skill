#!/usr/bin/env python3
"""Command-line client for the Hevy API, one command per endpoint.

Reads the key from HEVY_API_KEY. Standard library only, so it runs anywhere
python3 does. Every command prints JSON to stdout and errors to stderr.

    export HEVY_API_KEY="..."
    python3 hevy.py workouts --all | jq '.[].title'
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.hevyapp.com"

# The API has no search route, so the exercise catalogue is paged once and kept
# on disk. It is ~500 entries that change when Hevy ships new exercises.
CACHE_DIR = pathlib.Path(
    os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "hevy-skill"

# The local mirror is off unless the user turns it on. Training data is
# personal, and writing it to disk is their decision to make, not a default.
CONFIG_DIR = pathlib.Path(
    os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "hevy-skill"
CONFIG_FILE = CONFIG_DIR / "config.json"
DB_FILE = CACHE_DIR / "hevy.db"
# Cached by default, because --search cannot work without it. Announced on
# every read and write, and removed by 'cache clear' along with the mirror.
CATALOGUE_FILE = CACHE_DIR / "exercise_templates.json"

# Only workouts have a change feed, so only workouts can be synced exactly.
# The others are refreshed wholesale, which is why they say so at opt-in time.
DATASETS = {
    "workouts": "exact incremental sync via /v1/workouts/events",
    "measurements": "no change feed: refreshed in full on every sync",
    "routines": "no change feed: refreshed in full on every sync",
}

# Per-route pageSize caps. The API answers 400 above these, and they differ
# per route, so paging code cannot share one constant.
PAGE_SIZE_CAP = {
    "/v1/workouts": 10,
    "/v1/workouts/events": 10,
    "/v1/routines": 10,
    "/v1/routine_folders": 10,
    "/v1/exercise_templates": 100,
    "/v1/body_measurements": 10,
}

RETRY_STATUSES = {429, 500, 502, 503, 504}

# Anything cached, read from cache, or unusually expensive is announced on
# stderr so stdout stays a clean JSON stream for piping. Set HEVY_QUIET=1 to
# silence them.
CALLS_BEFORE_HINT = 10
_api_calls = 0


def notify(message: str) -> None:
    if not os.environ.get("HEVY_QUIET"):
        print(f"[hevy] {message}", file=sys.stderr)


class HevyError(RuntimeError):
    """An API response that was not a success."""

    def __init__(self, status: int, body: str, url: str) -> None:
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status} from {url}: {body[:400]}")


def api_key() -> str:
    key = os.environ.get("HEVY_API_KEY", "").strip()
    if not key:
        sys.exit("HEVY_API_KEY is not set. Get a key at https://hevy.com/settings?developer")
    return key


def request(method: str, path: str, params: dict | None = None,
            body: dict | None = None, retries: int = 3) -> object:
    """Call one endpoint and return the decoded JSON, or None for an empty body."""
    url = BASE_URL + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)

    data = json.dumps(body).encode() if body is not None else None
    headers = {"api-key": api_key(), "Accept": "application/json"}
    if data:
        headers["Content-Type"] = "application/json"

    global _api_calls
    for attempt in range(retries + 1):
        _api_calls += 1
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            # A 401 arrives as the plain string "InvalidApiKey" with a text/html
            # content type, so decoding the body as JSON is never safe here.
            if exc.code in RETRY_STATUSES and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise HevyError(exc.code, raw, url) from None
        except urllib.error.URLError as exc:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise HevyError(0, str(exc.reason), url) from None
    raise AssertionError("unreachable")


def paginate(path: str, key: str, page_size: int | None = None,
             extra: dict | None = None) -> list:
    """Walk every page of a list route and return the concatenated items."""
    cap = PAGE_SIZE_CAP.get(path, 10)
    size = min(page_size or cap, cap)
    items: list = []
    page = 1
    while True:
        params = {"page": page, "pageSize": size}
        if extra:
            params.update(extra)
        payload = request("GET", path, params=params)
        items.extend(payload.get(key, []))
        page_count = payload.get("page_count", page)
        if page >= page_count:
            return items
        page += 1


def read_json_arg(source: str) -> dict:
    """Load a JSON body from a file path, or from stdin when given '-'."""
    text = sys.stdin.read() if source == "-" else open(source, encoding="utf-8").read()
    return json.loads(text)


def emit(value: object) -> None:
    json.dump(value, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def require_confirmation(args: argparse.Namespace) -> None:
    """Refuse a write unless it was asked for explicitly.

    The Hevy API has no delete route, so every create is permanent and every
    update overwrites. A confirmation flag is the only undo available.
    """
    if not getattr(args, "yes", False):
        sys.exit("This command writes to your Hevy account and cannot be undone.\n"
                 "The API has no delete route. Re-run with --yes to proceed.")


def exercise_catalogue(refresh: bool = False) -> list[dict]:
    """Every exercise template, cached on disk after the first walk."""
    cache = CATALOGUE_FILE
    if not refresh and cache.is_file():
        stored = json.loads(cache.read_text())
        notify(f"read {len(stored['exercise_templates'])} exercise templates from cache "
               f"(fetched {stored['fetched_at'][:19]}, {cache}). "
               f"Refresh with --refresh, remove with 'cache clear'.")
        return stored["exercise_templates"]
    templates = paginate("/v1/exercise_templates", "exercise_templates")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(
        {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
         "exercise_templates": templates}))
    notify(f"cached {len(templates)} exercise templates to {cache}. "
           f"The catalogue is a lookup table, not training history. "
           f"Remove it with 'cache clear'.")
    return templates


def parse_timestamp(value: str) -> dt.datetime:
    """Read either timestamp format the API uses.

    start_time arrives as 2024-08-14T18:30:00+00:00 and updated_at as
    2024-08-14T19:31:12.765Z, so a parser fixed to one of them fails on the
    other (reference/observed.md).
    """
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def training_summary(weeks: int) -> dict:
    """Aggregate recent training the way a person asks about it.

    The API answers per workout, so volume, set counts and muscle-group split
    have to be computed here.
    """
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(weeks=weeks)
    by_id = {t["id"]: t for t in exercise_catalogue()}

    workouts, page = [], 1
    while True:
        payload = request("GET", "/v1/workouts", params={"page": page, "pageSize": 10})
        batch = payload.get("workouts", [])
        workouts.extend(w for w in batch if parse_timestamp(w["start_time"]) >= since)
        # Workouts come newest first, so the walk stops at the first older page.
        if not batch or parse_timestamp(batch[-1]["start_time"]) < since:
            break
        if page >= payload.get("page_count", page):
            break
        page += 1

    volume_kg = sets = reps = 0
    per_muscle: dict[str, float] = {}
    per_exercise: dict[str, dict] = {}
    minutes = 0.0
    for workout in workouts:
        minutes += (parse_timestamp(workout["end_time"])
                    - parse_timestamp(workout["start_time"])).total_seconds() / 60
        for exercise in workout.get("exercises", []):
            template = by_id.get(exercise.get("exercise_template_id"), {})
            muscle = template.get("primary_muscle_group", "unknown")
            entry = per_exercise.setdefault(
                exercise.get("title", "unknown"),
                {"sets": 0, "volume_kg": 0.0, "best_weight_kg": None})
            for one in exercise.get("sets", []):
                if one.get("type") == "warmup":
                    continue
                weight, count = one.get("weight_kg") or 0, one.get("reps") or 0
                load = weight * count
                sets += 1
                reps += count
                volume_kg += load
                per_muscle[muscle] = per_muscle.get(muscle, 0.0) + load
                entry["sets"] += 1
                entry["volume_kg"] += load
                if weight and (entry["best_weight_kg"] or 0) < weight:
                    entry["best_weight_kg"] = weight

    # Measurements come newest first too, so index 0 is the latest entry. The
    # walk needs every entry inside the window plus one weighted entry for the
    # stale fallback, and stops at the first page that satisfies both.
    all_weights: list[tuple[str, float]] = []
    page = 1
    while True:
        payload = request("GET", "/v1/body_measurements",
                          params={"page": page, "pageSize": 10})
        batch = payload.get("body_measurements", [])
        all_weights.extend((m["date"], m["weight_kg"])
                           for m in batch if m.get("weight_kg"))
        if not batch or (all_weights
                         and dt.date.fromisoformat(batch[-1]["date"]) < since.date()):
            break
        if page >= payload.get("page_count", page):
            break
        page += 1
    weights = [w for w in all_weights if dt.date.fromisoformat(w[0]) >= since.date()]
    stale = not weights and all_weights

    return {
        "weeks": weeks,
        "since": since.date().isoformat(),
        "workouts": len(workouts),
        "hours_trained": round(minutes / 60, 1),
        "working_sets": sets,
        "reps": reps,
        "volume_kg": round(volume_kg),
        "volume_by_muscle_group": dict(
            sorted(((k, round(v)) for k, v in per_muscle.items()),
                   key=lambda kv: -kv[1])),
        "top_exercises": dict(sorted(
            ((k, {**v, "volume_kg": round(v["volume_kg"])})
             for k, v in per_exercise.items()),
            key=lambda kv: -kv[1]["volume_kg"])[:10]),
        "body_weight_kg": {
            "first": weights[-1] if weights else None,
            "latest": weights[0] if weights else (all_weights[0] if stale else None),
            "change_kg": round(weights[0][1] - weights[-1][1], 2)
            if len(weights) > 1 else None,
            # A null change with a latest reading means the window holds no
            # measurement, not that the weight held steady.
            "note": "latest reading predates the window" if stale else None,
        },
    }


# --------------------------------------------------------------------------
# Local mirror. Off by default; every function here refuses to act until the
# user has opted in by naming the datasets they want stored.
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS workouts (
  id TEXT PRIMARY KEY, title TEXT, description TEXT, routine_id TEXT,
  start_time TEXT, end_time TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS exercises (
  workout_id TEXT, exercise_index INTEGER, title TEXT, notes TEXT,
  exercise_template_id TEXT, superset_id INTEGER,
  PRIMARY KEY (workout_id, exercise_index));
CREATE TABLE IF NOT EXISTS sets (
  workout_id TEXT, exercise_index INTEGER, set_index INTEGER, set_type TEXT,
  weight_kg REAL, reps INTEGER, distance_meters REAL, duration_seconds REAL,
  rpe REAL, custom_metric REAL,
  PRIMARY KEY (workout_id, exercise_index, set_index));
CREATE TABLE IF NOT EXISTS measurements (
  date TEXT PRIMARY KEY, weight_kg REAL, fat_percent REAL, payload TEXT);
CREATE TABLE IF NOT EXISTS routines (
  id TEXT PRIMARY KEY, title TEXT, folder_id INTEGER,
  created_at TEXT, updated_at TEXT, payload TEXT);
CREATE INDEX IF NOT EXISTS sets_template
  ON sets(workout_id, exercise_index);
CREATE INDEX IF NOT EXISTS workouts_start ON workouts(start_time);
"""

# One row per performed set, with its workout and exercise alongside. Most
# questions people ask are one WHERE clause away from this.
SCHEMA_VIEW = """
CREATE VIEW IF NOT EXISTS performed_sets AS
SELECT w.id AS workout_id, w.title AS workout_title, w.start_time, w.end_time,
       e.exercise_index, e.title AS exercise_title, e.exercise_template_id,
       e.superset_id, s.set_index, s.set_type, s.weight_kg, s.reps,
       s.distance_meters, s.duration_seconds, s.rpe, s.custom_metric,
       (COALESCE(s.weight_kg, 0) * COALESCE(s.reps, 0)) AS volume_kg
FROM workouts w
JOIN exercises e ON e.workout_id = w.id
JOIN sets s ON s.workout_id = w.id AND s.exercise_index = e.exercise_index;
"""


def read_config() -> dict:
    if CONFIG_FILE.is_file():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def write_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def enabled_datasets() -> list[str]:
    return read_config().get("cache", {}).get("datasets", [])


def require_cache(action: str) -> list[str]:
    datasets = enabled_datasets()
    if not datasets:
        sys.exit(f"The local mirror is off, so there is nothing to {action}.\n"
                 f"It is off by default: your training data stays on Hevy unless "
                 f"you choose otherwise.\n"
                 f"To turn it on, name the datasets you want stored:\n"
                 f"  hevy.py cache enable --workouts")
    return datasets


def open_db(read_only: bool = False) -> sqlite3.Connection:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if read_only:
        connection = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
    else:
        connection = sqlite3.connect(DB_FILE)
        connection.executescript(SCHEMA)
        connection.executescript(SCHEMA_VIEW)
    connection.row_factory = sqlite3.Row
    return connection


def store_workout(db: sqlite3.Connection, workout: dict) -> None:
    db.execute("INSERT OR REPLACE INTO workouts VALUES (?,?,?,?,?,?,?,?)",
               (workout["id"], workout.get("title"), workout.get("description"),
                workout.get("routine_id"), workout.get("start_time"),
                workout.get("end_time"), workout.get("created_at"),
                workout.get("updated_at")))
    # Replaced wholesale: an edit can remove an exercise, and a partial upsert
    # would leave the removed rows behind.
    db.execute("DELETE FROM exercises WHERE workout_id = ?", (workout["id"],))
    db.execute("DELETE FROM sets WHERE workout_id = ?", (workout["id"],))
    for position, exercise in enumerate(workout.get("exercises") or []):
        index = exercise.get("index", position)
        db.execute("INSERT OR REPLACE INTO exercises VALUES (?,?,?,?,?,?)",
                   (workout["id"], index, exercise.get("title"),
                    exercise.get("notes"), exercise.get("exercise_template_id"),
                    exercise.get("superset_id")))
        for set_position, one in enumerate(exercise.get("sets") or []):
            db.execute("INSERT OR REPLACE INTO sets VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (workout["id"], index, one.get("index", set_position),
                        one.get("type"), one.get("weight_kg"), one.get("reps"),
                        one.get("distance_meters"), one.get("duration_seconds"),
                        one.get("rpe"), one.get("custom_metric")))


def sync(datasets: list[str], full: bool = False) -> dict:
    """Bring the mirror up to date. Cheap when nothing changed."""
    db = open_db()
    counts = {}

    if "workouts" in datasets:
        row = db.execute("SELECT value FROM meta WHERE key='workouts_watermark'").fetchone()
        # Taken before the walk, so a workout written mid-run is caught next time.
        started_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        since = "1970-01-01T00:00:00Z" if (full or not row) else row["value"]
        updated = deleted = 0
        page = 1
        while True:
            payload = request("GET", "/v1/workouts/events",
                              params={"page": page, "pageSize": 10, "since": since})
            for event in payload.get("events", []):
                if event.get("type") == "updated":
                    store_workout(db, event["workout"])
                    updated += 1
                elif event.get("type") == "deleted":
                    for table in ("sets", "exercises"):
                        db.execute(f"DELETE FROM {table} WHERE workout_id = ?", (event["id"],))
                    db.execute("DELETE FROM workouts WHERE id = ?", (event["id"],))
                    deleted += 1
            if page >= payload.get("page_count", page):
                break
            page += 1
        db.execute("INSERT OR REPLACE INTO meta VALUES ('workouts_watermark', ?)",
                   (started_at,))
        counts["workouts"] = {"updated": updated, "deleted": deleted}

    if "measurements" in datasets:
        # No change feed, so the table is rebuilt rather than patched.
        rows = paginate("/v1/body_measurements", "body_measurements")
        db.execute("DELETE FROM measurements")
        db.executemany("INSERT OR REPLACE INTO measurements VALUES (?,?,?,?)",
                       [(m["date"], m.get("weight_kg"), m.get("fat_percent"),
                         json.dumps(m)) for m in rows])
        counts["measurements"] = {"replaced": len(rows)}

    if "routines" in datasets:
        rows = paginate("/v1/routines", "routines")
        db.execute("DELETE FROM routines")
        db.executemany("INSERT OR REPLACE INTO routines VALUES (?,?,?,?,?,?)",
                       [(r["id"], r.get("title"), r.get("folder_id"),
                         r.get("created_at"), r.get("updated_at"), json.dumps(r))
                        for r in rows])
        counts["routines"] = {"replaced": len(rows)}

    db.execute("INSERT OR REPLACE INTO meta VALUES ('last_synced_at', ?)",
               (dt.datetime.now(dt.timezone.utc).isoformat(),))
    db.commit()
    db.close()
    written = ", ".join(f"{name}: {v}" for name, v in counts.items())
    notify(f"wrote to the local mirror at {DB_FILE} ({written})")
    return counts


def run_query(statement: str) -> list[dict]:
    """Read-only. The mirror is derived data, and a write here would desync it."""
    if not re.match(r"^\s*(SELECT|WITH)\b", statement, re.IGNORECASE):
        sys.exit("Only SELECT and WITH statements are allowed. The mirror is a "
                 "copy of Hevy, so writes go to the API instead.")
    if not DB_FILE.is_file():
        sys.exit("The mirror is enabled but nothing is synced yet. "
                 "Run 'hevy.py sync' first, or drop --no-sync.")
    db = open_db(read_only=True)
    try:
        rows = [dict(row) for row in db.execute(statement).fetchall()]
    finally:
        db.close()
    stamp = ""
    if DB_FILE.is_file():
        peek = open_db(read_only=True)
        try:
            row = peek.execute("SELECT value FROM meta WHERE key='last_synced_at'").fetchone()
            stamp = f", synced {row['value'][:19]}" if row else ""
        finally:
            peek.close()
    notify(f"answered from the local mirror at {DB_FILE}{stamp}, not from the API")
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hevy.py", description="Hevy API client. One command per endpoint.")
    sub = parser.add_subparsers(dest="command", required=True)

    def listing(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--page", type=int, default=1)
        p.add_argument("--page-size", type=int)
        p.add_argument("--all", action="store_true", help="walk every page")
        return p

    sub.add_parser("user", help="GET /v1/user/info")

    listing("workouts", "GET /v1/workouts")
    sub.add_parser("workout-count", help="GET /v1/workouts/count")
    p = sub.add_parser("workout", help="GET /v1/workouts/{workoutId}")
    p.add_argument("workout_id")
    p = sub.add_parser("create-workout", help="POST /v1/workouts")
    p.add_argument("body", help="JSON file, or - for stdin")
    p = sub.add_parser("update-workout", help="PUT /v1/workouts/{workoutId}")
    p.add_argument("workout_id")
    p.add_argument("body", help="JSON file, or - for stdin")
    p = listing("events", "GET /v1/workouts/events")
    p.add_argument("--since", help="ISO 8601, defaults to the epoch")

    listing("routines", "GET /v1/routines")
    p = sub.add_parser("routine", help="GET /v1/routines/{routineId}")
    p.add_argument("routine_id")
    p = sub.add_parser("create-routine", help="POST /v1/routines")
    p.add_argument("body", help="JSON file, or - for stdin")
    p = sub.add_parser("update-routine", help="PUT /v1/routines/{routineId}")
    p.add_argument("routine_id")
    p.add_argument("body", help="JSON file, or - for stdin")

    listing("folders", "GET /v1/routine_folders")
    p = sub.add_parser("folder", help="GET /v1/routine_folders/{folderId}")
    p.add_argument("folder_id")
    p = sub.add_parser("create-folder", help="POST /v1/routine_folders")
    p.add_argument("title")

    p = listing("templates", "GET /v1/exercise_templates")
    p.add_argument("--search", metavar="TEXT",
                   help="filter the cached catalogue by title substring")
    p.add_argument("--muscle", help="filter by primary muscle group")
    p.add_argument("--refresh", action="store_true", help="re-fetch the catalogue")
    p = sub.add_parser("template", help="GET /v1/exercise_templates/{exerciseTemplateId}")
    p.add_argument("template_id")
    p = sub.add_parser("create-template", help="POST /v1/exercise_templates")
    p.add_argument("body", help="JSON file, or - for stdin")
    p = sub.add_parser("history", help="GET /v1/exercise_history/{exerciseTemplateId}")
    p.add_argument("template_id")
    p.add_argument("--start", help="ISO 8601 start_date")
    p.add_argument("--end", help="ISO 8601 end_date")

    listing("measurements", "GET /v1/body_measurements")
    p = sub.add_parser("measurement", help="GET /v1/body_measurements/{date}")
    p.add_argument("date", help="YYYY-MM-DD")
    p = sub.add_parser("create-measurement", help="POST /v1/body_measurements")
    p.add_argument("body", help="JSON file, or - for stdin")
    p = sub.add_parser("update-measurement", help="PUT /v1/body_measurements/{date}")
    p.add_argument("date", help="YYYY-MM-DD")
    p.add_argument("body", help="JSON file, or - for stdin")

    p = sub.add_parser("summary", help="Aggregate recent training. Reads workouts "
                                      "and body measurements, computes locally.")
    p.add_argument("--weeks", type=int, default=4, help="1 to 52, default 4")

    # Opt-in local mirror. Off unless the user turns it on.
    cache = sub.add_parser("cache", help="Manage the optional local mirror (off by default)")
    cache_sub = cache.add_subparsers(dest="cache_command", required=True)
    enable = cache_sub.add_parser("enable", help="store the named datasets locally")
    for name, note in DATASETS.items():
        enable.add_argument(f"--{name}", action="store_true", help=note)
    cache_sub.add_parser("status", help="what is stored, how fresh, how large")
    cache_sub.add_parser("disable", help="stop using the mirror, keep the file")
    cache_sub.add_parser("clear", help="delete the mirror from disk")

    p = sub.add_parser("sync", help="Update the local mirror. Requires opt-in.")
    p.add_argument("--full", action="store_true", help="rebuild from the beginning")

    p = sub.add_parser("sql", help="Query the local mirror. Syncs first. Requires opt-in.")
    p.add_argument("statement", help="a SELECT or WITH statement")
    p.add_argument("--no-sync", action="store_true",
                   help="skip the freshness sync and query what is on disk")

    # Writes are permanent: the API has no delete route.
    for name in ("create-workout", "update-workout", "create-routine", "update-routine",
                 "create-folder", "create-template", "create-measurement",
                 "update-measurement"):
        sub.choices[name].add_argument(
            "--yes", action="store_true",
            help="confirm this permanent write")

    return parser


def run_cache_command(args: argparse.Namespace) -> object:
    config = read_config()
    action = args.cache_command

    if action == "enable":
        chosen = [name for name in DATASETS if getattr(args, name, False)]
        if not chosen:
            sys.exit("Name at least one dataset. Nothing is stored implicitly.\n"
                     + "\n".join(f"  --{n:<14} {note}" for n, note in DATASETS.items()))
        config["cache"] = {
            "datasets": chosen,
            "enabled_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        write_config(config)
        return {
            "enabled": chosen,
            "database": str(DB_FILE),
            "note": "This writes your Hevy data to that file in plain text. "
                    "Remove it with: hevy.py cache clear",
            "next": "hevy.py sync",
        }

    if action == "status":
        datasets = enabled_datasets()
        state = {"enabled": bool(datasets), "datasets": datasets,
                 "database": str(DB_FILE), "exists": DB_FILE.is_file()}
        if DB_FILE.is_file():
            state["size_bytes"] = DB_FILE.stat().st_size
            db = open_db(read_only=True)
            try:
                rows = db.execute("SELECT key, value FROM meta").fetchall()
                state["meta"] = {r["key"]: r["value"] for r in rows}
                for table in ("workouts", "exercises", "sets", "measurements", "routines"):
                    state[f"{table}_rows"] = db.execute(
                        f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            finally:
                db.close()
        return state

    if action == "disable":
        config.pop("cache", None)
        write_config(config)
        return {"enabled": False,
                "note": f"{DB_FILE} is still on disk. Delete it with: hevy.py cache clear"}

    if action == "clear":
        config.pop("cache", None)
        write_config(config)
        removed = [str(f) for f in (DB_FILE, CATALOGUE_FILE) if f.is_file()]
        for f in (DB_FILE, CATALOGUE_FILE):
            f.unlink(missing_ok=True)
        notify(f"removed {len(removed)} cache file(s) from {CACHE_DIR}")
        return {"removed": removed,
                "note": "The exercise catalogue will be re-fetched and re-cached "
                        "the next time --search runs."}

    raise AssertionError(f"unhandled cache command {action}")


def run(args: argparse.Namespace) -> object:
    cmd = args.command

    def page_params() -> dict:
        return {"page": args.page, "pageSize": args.page_size}

    if cmd == "user":
        return request("GET", "/v1/user/info")

    if cmd == "workouts":
        if args.all:
            return paginate("/v1/workouts", "workouts", args.page_size)
        return request("GET", "/v1/workouts", params=page_params())
    if cmd == "workout-count":
        return request("GET", "/v1/workouts/count")
    if cmd == "workout":
        return request("GET", f"/v1/workouts/{args.workout_id}")
    if cmd == "create-workout":
        require_confirmation(args)
        return request("POST", "/v1/workouts", body=read_json_arg(args.body))
    if cmd == "update-workout":
        require_confirmation(args)
        return request("PUT", f"/v1/workouts/{args.workout_id}",
                       body=read_json_arg(args.body))
    if cmd == "events":
        # Sent explicitly because the spec's epoch default is wrong: omitting
        # since returns no events at all (reference/observed.md).
        extra = {"since": args.since or "1970-01-01T00:00:00Z"}
        if args.all:
            return paginate("/v1/workouts/events", "events", args.page_size, extra)
        params = page_params()
        params.update(extra)
        return request("GET", "/v1/workouts/events", params=params)

    if cmd == "routines":
        if args.all:
            return paginate("/v1/routines", "routines", args.page_size)
        return request("GET", "/v1/routines", params=page_params())
    if cmd == "routine":
        return request("GET", f"/v1/routines/{args.routine_id}")
    if cmd == "create-routine":
        require_confirmation(args)
        return request("POST", "/v1/routines", body=read_json_arg(args.body))
    if cmd == "update-routine":
        require_confirmation(args)
        return request("PUT", f"/v1/routines/{args.routine_id}",
                       body=read_json_arg(args.body))

    if cmd == "folders":
        if args.all:
            return paginate("/v1/routine_folders", "routine_folders", args.page_size)
        return request("GET", "/v1/routine_folders", params=page_params())
    if cmd == "folder":
        return request("GET", f"/v1/routine_folders/{args.folder_id}")
    if cmd == "create-folder":
        require_confirmation(args)
        return request("POST", "/v1/routine_folders",
                       body={"routine_folder": {"title": args.title}})

    if cmd == "templates":
        if args.search or args.muscle or args.refresh:
            catalogue = exercise_catalogue(refresh=args.refresh)
            needle = (args.search or "").lower()
            return [t for t in catalogue
                    if needle in t.get("title", "").lower()
                    and (not args.muscle
                         or t.get("primary_muscle_group") == args.muscle)]
        if args.all:
            return paginate("/v1/exercise_templates", "exercise_templates", args.page_size)
        return request("GET", "/v1/exercise_templates", params=page_params())
    if cmd == "template":
        return request("GET", f"/v1/exercise_templates/{args.template_id}")
    if cmd == "create-template":
        require_confirmation(args)
        return request("POST", "/v1/exercise_templates", body=read_json_arg(args.body))
    if cmd == "history":
        return request("GET", f"/v1/exercise_history/{args.template_id}",
                       params={"start_date": args.start, "end_date": args.end})

    if cmd == "measurements":
        if args.all:
            return paginate("/v1/body_measurements", "body_measurements", args.page_size)
        return request("GET", "/v1/body_measurements", params=page_params())
    if cmd == "measurement":
        return request("GET", f"/v1/body_measurements/{args.date}")
    if cmd == "create-measurement":
        require_confirmation(args)
        return request("POST", "/v1/body_measurements", body=read_json_arg(args.body))
    if cmd == "update-measurement":
        require_confirmation(args)
        return request("PUT", f"/v1/body_measurements/{args.date}",
                       body=read_json_arg(args.body))

    if cmd == "cache":
        return run_cache_command(args)

    if cmd == "sync":
        datasets = require_cache("sync")
        return {"synced": sync(datasets, full=args.full), "datasets": datasets}

    if cmd == "sql":
        datasets = require_cache("query")
        # Syncing here rather than as a separate step is what makes the answer
        # trustworthy: there is no path that queries a stale mirror by accident.
        if not args.no_sync:
            sync(datasets)
        return run_query(args.statement)

    if cmd == "summary":
        if not 1 <= args.weeks <= 52:
            sys.exit("--weeks must be between 1 and 52")
        return training_summary(args.weeks)

    raise AssertionError(f"unhandled command {cmd}")


def suggest_mirror_if_expensive(command: str) -> None:
    """Mention the mirror only when this run actually paid for its absence.

    Cost is the honest trigger. Detecting a repeated query across runs would
    need a persistent log of what was asked for, and writing that by default
    is the thing the mirror being opt-in exists to avoid.
    """
    if command in ("cache", "sync", "sql") or enabled_datasets():
        return
    if _api_calls < CALLS_BEFORE_HINT:
        return
    notify(f"this took {_api_calls} API calls. A local SQLite mirror can answer "
           f"repeat questions from disk instead. It is off by default and stores "
           f"your training data locally: 'hevy.py cache enable --workouts' turns "
           f"it on, and 'cache clear' removes it.")


def main() -> int:
    args = build_parser().parse_args()
    try:
        emit(run(args))
        suggest_mirror_if_expensive(args.command)
    except HevyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
