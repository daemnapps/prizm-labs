"""QB-1 (queue core): the pure reducer. Fixtures only, in memory; nothing here reads or writes the repo's queue.

    python3 components/creative-queue/test_qb1_reduce.py
"""
import builtins
import io
import os
import pathlib
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import qcore  # noqa: E402

NOW = "2026-10-22T03:00:00Z"


def obs(source, as_of, entries):
    return {"schema": 1, "source": source, "as_of": as_of, "entries": entries}


def dec(eid, op, by, made, field=None, value=None, legacy=False):
    d = {"schema": 1, "id": eid, "op": op, "field": field, "value": value, "by": by, "made": made}
    if legacy:
        d["legacy"] = True
    return d


def one(index, eid):
    hits = [e for e in index["entries"] if e["id"] == eid]
    return hits[0] if hits else None


BASE = {"mac": obs("mac", "2026-10-22T02:59:00Z", {"a": {"title": "A", "observed_stage": "making"}})}


class Reduce(unittest.TestCase):
    def test_shape(self):
        idx = qcore.reduce(BASE, [], NOW)
        self.assertEqual(idx["schema"], 1)
        self.assertEqual(idx["built"], NOW)
        self.assertEqual([e["id"] for e in idx["entries"]], ["a"])
        a = one(idx, "a")
        self.assertEqual(a["title"], "A")
        self.assertEqual(a["observed_stage"], "making")
        self.assertIs(a["removed"], False)
        self.assertEqual(a["decided_by"], {})

    def test_entries_sorted_and_add_creates(self):
        o = {"mac": obs("mac", NOW, {"c": {}, "a": {}})}
        d = [dec("b", "add", "pm", "2026-10-22T01:00:00Z", value={"title": "B", "brand": "x", "type": "video-ad"}),
             dec("z", "set", "pm", "2026-10-22T01:00:00Z", "note", "orphan")]   # a set alone makes no entry
        idx = qcore.reduce(o, d, NOW)
        self.assertEqual([e["id"] for e in idx["entries"]], ["a", "b", "c"])
        b = one(idx, "b")
        self.assertEqual((b["title"], b["brand"], b["type"]), ("B", "x", "video-ad"))
        self.assertEqual(b["decided_by"]["title"], {"by": "pm", "made": "2026-10-22T01:00:00Z"})

    def test_latest_made_wins_per_field_across_two_people(self):
        d = [dec("a", "set", "owner", "2026-10-22T01:00:00Z", "priority", "top"),
             dec("a", "set", "pm", "2026-10-22T02:00:00Z", "priority", "low"),
             dec("a", "set", "pm", "2026-10-22T01:30:00Z", "note", "pm's"),
             dec("a", "set", "owner", "2026-10-22T01:10:00Z", "note", "owner's")]
        a = one(qcore.reduce(BASE, d, NOW), "a")
        self.assertEqual(a["priority"], "low")
        self.assertEqual(a["note"], "pm's")
        self.assertEqual(a["decided_by"]["priority"], {"by": "pm", "made": "2026-10-22T02:00:00Z"})
        self.assertEqual(a["decided_by"]["note"], {"by": "pm", "made": "2026-10-22T01:30:00Z"})
        # load order does not matter when `made` differs
        self.assertEqual(one(qcore.reduce(BASE, list(reversed(d)), NOW), "a")["priority"], "low")

    def test_made_compares_as_time_not_text(self):
        d = [dec("a", "set", "owner", "2026-10-22T01:00:05Z", "who", "late"),
             dec("a", "set", "pm", "2026-10-22T01:00:05.500Z", "who", "later")]
        self.assertEqual(one(qcore.reduce(BASE, d, NOW), "a")["who"], "later")

    def test_tie_is_deterministic(self):
        t = "2026-10-22T01:00:00Z"
        d = [dec("a", "set", "pm", t, "who", "from-pm"), dec("a", "set", "owner", t, "who", "from-owner")]
        r1 = one(qcore.reduce(BASE, d, NOW), "a")
        r2 = one(qcore.reduce(BASE, list(reversed(d)), NOW), "a")
        self.assertEqual(r1["who"], "from-pm")        # ties break by `by`: the later name wins
        self.assertEqual(r2["who"], "from-pm")
        same = [dec("a", "set", "pm", t, "who", "first line"), dec("a", "set", "pm", t, "who", "second line")]
        self.assertEqual(one(qcore.reduce(BASE, same, NOW), "a")["who"], "second line")   # then load order
        self.assertEqual(qcore.reduce(BASE, d, NOW), qcore.reduce(BASE, d, NOW))

    def test_remove_then_newer_observation_still_removed(self):
        d = [dec("a", "remove", "pm", "2026-10-22T01:00:00Z")]
        later = {"mac": obs("mac", "2026-10-22T02:59:00Z", {"a": {"title": "A again", "observed_stage": "live"}})}
        a = one(qcore.reduce(later, d, NOW), "a")
        self.assertIs(a["removed"], True)
        self.assertEqual(a["observed_stage"], "live")
        self.assertEqual(a["decided_by"]["removed"], {"by": "pm", "made": "2026-10-22T01:00:00Z"})
        # an observation that itself claims removed: false never clears the tombstone
        claim = {"mac": obs("mac", NOW, {"a": {"removed": False}})}
        self.assertIs(one(qcore.reduce(claim, d, NOW), "a")["removed"], True)

    def test_restore_after_remove_shows(self):
        d = [dec("a", "remove", "pm", "2026-10-22T01:00:00Z"), dec("a", "restore", "owner", "2026-10-22T02:00:00Z")]
        self.assertIs(one(qcore.reduce(BASE, d, NOW), "a")["removed"], False)
        # an older restore loses to a newer remove, whatever the load order
        d2 = [dec("a", "remove", "pm", "2026-10-22T02:00:00Z"), dec("a", "restore", "owner", "2026-10-22T01:00:00Z")]
        self.assertIs(one(qcore.reduce(BASE, list(reversed(d2)), NOW), "a")["removed"], True)

    def test_observed_stage_furthest_of_two_sources(self):
        o = {"mac": obs("mac", "2026-10-22T02:00:00Z", {"a": {"observed_stage": "editing"}}),
             "mini": obs("mini", "2026-10-22T02:30:00Z", {"a": {"observed_stage": "brief"}})}
        a = one(qcore.reduce(o, [], NOW), "a")
        self.assertEqual(a["observed_stage"], "editing")
        self.assertEqual(sorted(a["observed_in"]), ["mac", "mini"])

    def test_requested_stage_kept_apart_with_stage_differs(self):
        d = [dec("a", "set", "pm", "2026-10-22T01:00:00Z", "requested_stage", "launch")]
        a = one(qcore.reduce(BASE, d, NOW), "a")
        self.assertEqual(a["observed_stage"], "making")
        self.assertEqual(a["requested_stage"], "launch")
        self.assertIs(a["stage_differs"], True)
        same = [dec("a", "set", "pm", "2026-10-22T01:00:00Z", "requested_stage", "making")]
        self.assertIs(one(qcore.reduce(BASE, same, NOW), "a")["stage_differs"], False)
        self.assertIs(one(qcore.reduce(BASE, [], NOW), "a")["stage_differs"], False)

    def test_approve_pending_then_receipt_wins(self):
        d = [dec("a", "approve", "owner", "2026-10-22T01:00:00Z")]
        a = one(qcore.reduce(BASE, d, NOW), "a")
        self.assertEqual(a["approved"], {"by": "owner", "made": "2026-10-22T01:00:00Z"})
        self.assertEqual(a["execution"], "pending")
        ran = {"mac": obs("mac", NOW, {"a": {"observed_stage": "making", "execution": "running"}})}
        self.assertEqual(one(qcore.reduce(ran, d, NOW), "a")["execution"], "running")
        self.assertNotIn("execution", one(qcore.reduce(BASE, [], NOW), "a"))

    def test_per_source_age(self):
        o = {"mac": obs("mac", "2026-10-22T02:00:00Z", {"a": {}}),
             "mini": obs("mini", "2026-10-19T03:00:00Z", {"b": {}})}
        idx = qcore.reduce(o, [], NOW)
        self.assertEqual(idx["sources"], {"mac": {"as_of": "2026-10-22T02:00:00Z", "age_s": 3600},
                                          "mini": {"as_of": "2026-10-19T03:00:00Z", "age_s": 3 * 86400}})

    def test_legacy_loses_to_a_later_real_one(self):
        d = [dec("a", "set", "owner", "2026-10-22T09:00:00", "priority", "top", legacy=True),
             dec("a", "set", "pm", "2026-10-21T01:00:00Z", "priority", "low")]
        a = one(qcore.reduce(BASE, d, NOW), "a")
        self.assertEqual(a["priority"], "low")       # naive legacy text never outranks a real decision
        self.assertEqual(a["decided_by"]["priority"]["by"], "pm")
        only = [dec("a", "set", "owner", "2026-10-17T17:11:11", "note", "kept", legacy=True)]
        self.assertEqual(one(qcore.reduce(BASE, only, NOW), "a")["note"], "kept")
        rm = [dec("a", "remove", "owner", "2026-10-19T17:20:31", legacy=True),
              dec("a", "restore", "pm", "2026-10-20T00:00:00Z")]
        self.assertIs(one(qcore.reduce(BASE, rm, NOW), "a")["removed"], False)

    def test_observed_fields_carried_and_freshest_source_wins(self):
        o = {"mac": obs("mac", "2026-10-22T01:00:00Z", {"a": {"title": "old", "thumb": "t.jpg"}}),
             "mini": obs("mini", "2026-10-22T02:00:00Z", {"a": {"title": "new"}})}
        a = one(qcore.reduce(o, [], NOW), "a")
        self.assertEqual((a["title"], a["thumb"]), ("new", "t.jpg"))

    def test_reduce_touches_no_file_clock_or_env(self):
        d = [dec("a", "approve", "owner", "2026-10-22T01:00:00Z"),
             dec("a", "set", "pm", "2026-10-22T01:00:00.25Z", "requested_stage", "launch")]
        expect = qcore.reduce(BASE, d, NOW)

        def boom(*a, **k):
            raise AssertionError("reduce touched the outside world")

        class NoClock(qcore.datetime):
            now = utcnow = today = classmethod(boom)

        class NoEnv(dict):
            __getitem__ = get = __contains__ = __iter__ = boom

        with mock.patch.object(builtins, "open", boom), mock.patch.object(io, "open", boom), \
                mock.patch.object(os, "open", boom), mock.patch.object(os, "stat", boom), \
                mock.patch.object(os, "listdir", boom), mock.patch.object(os, "scandir", boom), \
                mock.patch.object(pathlib.Path, "open", boom), mock.patch.object(pathlib.Path, "read_text", boom), \
                mock.patch.object(pathlib.Path, "write_text", boom), mock.patch.object(pathlib.Path, "glob", boom), \
                mock.patch.object(qcore, "datetime", NoClock), mock.patch.object(qcore.os, "environ", NoEnv()), \
                mock.patch.object(qcore.subprocess, "run", boom):
            got = qcore.reduce(BASE, d, NOW)
        self.assertEqual(got, expect)
        self.assertEqual(one(got, "a")["execution"], "pending")


if __name__ == "__main__":
    unittest.main()
