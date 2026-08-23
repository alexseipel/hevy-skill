#!/usr/bin/env python3
"""Offline tests for the client. No key and no network: request() is replaced
with a fake serving canned pages, and every path the client writes is
redirected into a temporary directory.

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
import unittest.mock as mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIENT = ROOT / "skills" / "hevy-api" / "scripts" / "hevy.py"


def load_client():
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec = importlib.util.spec_from_file_location("hevy_client_under_test", CLIENT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = previous


hevy = load_client()

NOW = dt.datetime.now(dt.timezone.utc)


def offset_ts(delta_days: float) -> str:
    """A start_time-style timestamp: offset form, whole seconds."""
    stamp = NOW - dt.timedelta(days=delta_days)
    return stamp.replace(microsecond=0).isoformat()


def day(delta_days: int) -> str:
    return (NOW - dt.timedelta(days=delta_days)).date().isoformat()


class FakeApi:
    """Serves canned pages per path and records every call it gets."""

    def __init__(self):
        self.pages: dict[str, dict[int, dict]] = {}
        self.calls: list[tuple[str, str, dict]] = []

    def request(self, method, path, params=None, body=None, retries=3):
        params = params or {}
        self.calls.append((method, path, dict(params)))
        return self.pages[path][params.get("page", 1)]

    def calls_to(self, path) -> list[dict]:
        return [params for _, called, params in self.calls if called == path]


class ClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)

        self.saved = {name: getattr(hevy, name) for name in
                      ("CACHE_DIR", "CONFIG_DIR", "CONFIG_FILE", "DB_FILE",
                       "CATALOGUE_FILE", "request")}
        self.addCleanup(lambda: [setattr(hevy, k, v) for k, v in self.saved.items()])

        hevy.CACHE_DIR = base / "cache"
        hevy.CONFIG_DIR = base / "config"
        hevy.CONFIG_FILE = hevy.CONFIG_DIR / "config.json"
        hevy.DB_FILE = hevy.CACHE_DIR / "hevy.db"
        hevy.CATALOGUE_FILE = hevy.CACHE_DIR / "exercise_templates.json"

        os.environ["HEVY_QUIET"] = "1"
        self.addCleanup(os.environ.pop, "HEVY_QUIET", None)

        self.api = FakeApi()
        hevy.request = self.api.request

    def write_catalogue(self, templates):
        hevy.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        hevy.CATALOGUE_FILE.write_text(json.dumps(
            {"fetched_at": NOW.isoformat(), "exercise_templates": templates}))

    # ------------------------------------------------------------------ util

    def test_parse_timestamp_reads_both_formats(self):
        offset = hevy.parse_timestamp("2024-08-14T18:30:00+00:00")
        zulu = hevy.parse_timestamp("2024-08-14T19:31:12.765Z")
        self.assertIsNotNone(offset.tzinfo)
        self.assertIsNotNone(zulu.tzinfo)
        self.assertLess(offset, zulu)

    def test_require_confirmation_refuses_without_yes(self):
        import argparse
        with self.assertRaises(SystemExit):
            hevy.require_confirmation(argparse.Namespace(yes=False))
        hevy.require_confirmation(argparse.Namespace(yes=True))

    def test_request_passes_a_plain_text_body_through(self):
        """POST /v1/exercise_templates answers with a bare UUID, not JSON."""
        class FakeResp(io.BytesIO):
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False

        os.environ["HEVY_API_KEY"] = "test-key"
        self.addCleanup(os.environ.pop, "HEVY_API_KEY", None)
        real_request = self.saved["request"]
        with mock.patch.object(hevy.urllib.request, "urlopen",
                               return_value=FakeResp(b"11111111-2222-3333-4444-555555555555")):
            body = real_request("POST", "/v1/exercise_templates",
                                body={"exercise": {"title": "x"}})
        self.assertEqual(body, "11111111-2222-3333-4444-555555555555")

    # ------------------------------------------------------------- pagination

    def test_paginate_walks_every_page_and_caps_page_size(self):
        self.api.pages["/v1/workouts"] = {
            1: {"page": 1, "page_count": 3, "workouts": [{"id": "a"}]},
            2: {"page": 2, "page_count": 3, "workouts": [{"id": "b"}]},
            3: {"page": 3, "page_count": 3, "workouts": [{"id": "c"}]},
        }
        items = hevy.paginate("/v1/workouts", "workouts", page_size=999)
        self.assertEqual([i["id"] for i in items], ["a", "b", "c"])
        sizes = {p["pageSize"] for p in self.api.calls_to("/v1/workouts")}
        self.assertEqual(sizes, {10}, "the per-route cap bounds pageSize")

    # ---------------------------------------------------------------- summary

    def test_training_summary_math_and_early_stop(self):
        self.write_catalogue([{"id": "T1", "primary_muscle_group": "chest"}])
        in_window = {
            "id": "w1", "title": "Push", "start_time": offset_ts(1),
            "end_time": (hevy.parse_timestamp(offset_ts(1))
                         + dt.timedelta(hours=1)).isoformat(),
            "exercises": [{
                "title": "Bench Press (Barbell)", "exercise_template_id": "T1",
                "sets": [
                    {"type": "warmup", "weight_kg": 60, "reps": 8},
                    {"type": "normal", "weight_kg": 100, "reps": 10},
                ]}],
        }
        older = dict(in_window, id="w0", start_time=offset_ts(30),
                     end_time=offset_ts(30))
        # page_count says 5, but the page already reaches past the window, so
        # the walk must stop after one call.
        self.api.pages["/v1/workouts"] = {
            1: {"page": 1, "page_count": 5, "workouts": [in_window, older]}}
        self.api.pages["/v1/body_measurements"] = {
            1: {"page": 1, "page_count": 5, "body_measurements": [
                {"date": day(0), "weight_kg": 81.0},
                {"date": day(3), "weight_kg": 80.0},
                {"date": day(30), "weight_kg": 85.0},
            ]}}

        summary = hevy.training_summary(weeks=1)

        self.assertEqual(summary["workouts"], 1)
        self.assertEqual(summary["working_sets"], 1, "warmup sets are excluded")
        self.assertEqual(summary["reps"], 10)
        self.assertEqual(summary["volume_kg"], 1000)
        self.assertEqual(summary["volume_by_muscle_group"], {"chest": 1000})
        self.assertEqual(summary["hours_trained"], 1.0)
        self.assertEqual(summary["body_weight_kg"]["latest"], (day(0), 81.0))
        self.assertEqual(summary["body_weight_kg"]["change_kg"], 1.0)
        self.assertIsNone(summary["body_weight_kg"]["note"])
        self.assertEqual(len(self.api.calls_to("/v1/workouts")), 1)
        self.assertEqual(len(self.api.calls_to("/v1/body_measurements")), 1)

    def test_training_summary_groups_a_renamed_exercise_once(self):
        """A title is a display name. Two spellings of one template are one row."""
        self.write_catalogue([{"id": "T1", "primary_muscle_group": "legs",
                               "title": "Example Press (Dumbbell)"}])
        def workout(wid, title):
            return {"id": wid, "title": "Legs", "start_time": offset_ts(1),
                    "end_time": (hevy.parse_timestamp(offset_ts(1))
                                 + dt.timedelta(hours=1)).isoformat(),
                    "exercises": [{"title": title, "exercise_template_id": "T1",
                                   "sets": [{"type": "normal",
                                             "weight_kg": 30, "reps": 10}]}]}
        # The catalogue renamed T1, so the older workout kept the old title.
        self.api.pages["/v1/workouts"] = {1: {"page": 1, "page_count": 1, "workouts": [
            workout("w1", "Example Press (Dumbbell)"),
            workout("w0", "Example Press"),
        ]}}
        self.api.pages["/v1/body_measurements"] = {
            1: {"page": 1, "page_count": 1, "body_measurements": []}}

        top = hevy.training_summary(weeks=1)["top_exercises"]

        self.assertEqual(list(top), ["Example Press (Dumbbell)"],
                         "one template is one row, under its current title")
        self.assertEqual(top["Example Press (Dumbbell)"]["sets"], 2)
        self.assertEqual(top["Example Press (Dumbbell)"]["volume_kg"], 600)

    def test_rank_exercises_keeps_a_shared_title_apart(self):
        """Two templates under one display name must not overwrite each other."""
        ranked = hevy.rank_exercises({
            "T1": {"title": "Bench Press", "sets": 3,
                   "volume_kg": 900.0, "best_weight_kg": 100},
            "T2": {"title": "Bench Press", "sets": 1,
                   "volume_kg": 100.0, "best_weight_kg": 50},
        })

        self.assertEqual(list(ranked), ["Bench Press", "Bench Press [T2]"])
        self.assertEqual(ranked["Bench Press"]["volume_kg"], 900)

    def test_training_summary_names_a_stale_weight(self):
        self.write_catalogue([])
        self.api.pages["/v1/workouts"] = {
            1: {"page": 1, "page_count": 1, "workouts": []}}
        self.api.pages["/v1/body_measurements"] = {
            1: {"page": 1, "page_count": 1, "body_measurements": [
                {"date": day(30), "weight_kg": 85.0}]}}

        weight = hevy.training_summary(weeks=1)["body_weight_kg"]

        self.assertEqual(weight["latest"], (day(30), 85.0))
        self.assertIsNone(weight["change_kg"])
        self.assertEqual(weight["note"], "latest reading predates the window")

    # ----------------------------------------------------------------- mirror

    def test_store_workout_replaces_rather_than_merges(self):
        workout = {
            "id": "w1", "title": "A", "start_time": offset_ts(1),
            "end_time": offset_ts(1),
            "exercises": [
                {"index": 0, "exercise_template_id": "T1",
                 "sets": [{"index": 0, "type": "normal"},
                          {"index": 1, "type": "normal"}]},
                {"index": 1, "exercise_template_id": "T2",
                 "sets": [{"index": 0, "type": "normal"}]},
            ],
        }
        db = hevy.open_db()
        hevy.store_workout(db, workout)
        shrunk = dict(workout, exercises=workout["exercises"][:1])
        shrunk["exercises"] = [dict(shrunk["exercises"][0],
                                    sets=[{"index": 0, "type": "normal"}])]
        hevy.store_workout(db, shrunk)
        exercises = db.execute("SELECT COUNT(*) AS n FROM exercises").fetchone()["n"]
        sets = db.execute("SELECT COUNT(*) AS n FROM sets").fetchone()["n"]
        db.close()
        self.assertEqual((exercises, sets), (1, 1),
                         "an edit that removes rows must remove them here too")

    def test_sync_upserts_deletes_and_advances_the_watermark(self):
        workout = {"id": "w1", "title": "A", "start_time": offset_ts(1),
                   "end_time": offset_ts(1), "exercises": []}
        self.api.pages["/v1/workouts/events"] = {
            1: {"page": 1, "page_count": 1, "events": [
                {"type": "updated", "workout": workout}]}}
        first = hevy.sync(["workouts"])
        self.assertEqual(first["workouts"], {"updated": 1, "deleted": 0})

        self.api.pages["/v1/workouts/events"] = {
            1: {"page": 1, "page_count": 1, "events": [
                {"type": "deleted", "id": "w1"}]}}
        second = hevy.sync(["workouts"])
        self.assertEqual(second["workouts"], {"updated": 0, "deleted": 1})

        events_calls = self.api.calls_to("/v1/workouts/events")
        self.assertEqual(events_calls[0]["since"], "1970-01-01T00:00:00Z")
        self.assertNotEqual(events_calls[1]["since"], "1970-01-01T00:00:00Z",
                            "the second sync must resume from the watermark")
        db = hevy.open_db(read_only=True)
        rows = db.execute("SELECT COUNT(*) AS n FROM workouts").fetchone()["n"]
        db.close()
        self.assertEqual(rows, 0)

    def test_sync_survives_an_empty_events_feed(self):
        """A caught-up feed has no events key, only an empty workouts array."""
        self.api.pages["/v1/workouts/events"] = {
            1: {"page": 1, "page_count": 1, "workouts": []}}
        counts = hevy.sync(["workouts"])
        self.assertEqual(counts["workouts"], {"updated": 0, "deleted": 0})

    def test_run_query_accepts_reads_only(self):
        with self.assertRaises(SystemExit):
            hevy.run_query("DELETE FROM workouts")
        with self.assertRaises(SystemExit) as refused:
            hevy.run_query("SELECT 1")   # nothing synced yet
        self.assertIn("sync", str(refused.exception))
        hevy.open_db().close()           # creates the schema
        rows = hevy.run_query("SELECT 1 AS one")
        self.assertEqual(rows, [{"one": 1}])

    # -------------------------------------------------------------- catalogue

    def test_exercise_catalogue_is_fetched_once_then_cached(self):
        self.api.pages["/v1/exercise_templates"] = {
            1: {"page": 1, "page_count": 1, "exercise_templates": [
                {"id": "T1", "title": "Bench Press (Barbell)"}]}}
        first = hevy.exercise_catalogue()
        again = hevy.exercise_catalogue()
        self.assertEqual(first, again)
        self.assertEqual(len(self.api.calls_to("/v1/exercise_templates")), 1,
                         "the second read must come from the cache file")


if __name__ == "__main__":
    unittest.main()
