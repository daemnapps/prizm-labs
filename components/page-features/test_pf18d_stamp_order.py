#!/usr/bin/env python3
"""PF-18d (stamp order): a dev_issues move is stamped at least one second after the newest record of the task it
moves, so a move made right after a batch filing never sorts before its task's create and is never dropped by
dev_queue.fold_dev.

    python3 components/page-features/test_pf18d_stamp_order.py

    (a) a batch of 5 filed at T; `discussing`, `wont` and `card` on its LAST item at T+1 s: each move's records sort
        after the create in dev_queue's own order and `show` reports the new state; two moves in a row stay in order
    (b) a move on a task whose newest record is in the past is stamped at now, unchanged
    (c) the kill: a start more than 60 s past now is refused (exit 2, "this task has records from the future"),
        nothing written; exactly 60 s is still stamped; a move that makes no sense names its own reason first
    (d) `file` keeps its one-second spacing, and an item naming an earlier item of the same batch lands after it

Fixtures are built in temp folders from test_pf18_dev_queue's fixture repo; no .md fixtures under components/.
Stdlib only, Python 3.9. No network; no real task record is written.
"""
import io
import json
import os
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dev_issues  # noqa: E402
import dev_queue  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the PF-18 fixture repo, reused

TASKS = "platform/data/records/tasks/"
T = "2026-10-29T07:25:07Z"
T1 = "2026-10-29T07:25:08Z"
BATCH = [{"kind": "issue", "ref": str(i), "title": "Batch issue number %d" % i, "quote": "item %d" % i,
          "session": "b3c1aa"} for i in range(1, 6)]


def run(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    code = dev_issues.main(list(argv) + ["--root", root], out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def listing(root):
    d = os.path.join(root, TASKS)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def file_batch(test, root, items=None, now=T):
    path = os.path.join(root, "items.json")
    pf18.write(root, "items.json", json.dumps(items or BATCH))
    code, out, err = run(root, "file", path, "--by", "developer", "--now", now)
    test.assertEqual(code, 0, err)


def task_id(root, title):
    items, _n = dev_queue.dev_items(root)
    return next(e["id"] for e in items if e["title"] == title)


def rows_of(root, tid):
    return dev_queue.read_task_records(root)[0][tid]


def shown(test, root, tid):
    code, out, err = run(root, "show", "--json")
    test.assertEqual(code, 0, err)
    return next(e for e in json.loads(out) if e["id"] == tid)


class AfterTheBatch(unittest.TestCase):
    """(a)"""

    def setUp(self):
        self.root = pf18.fixture()
        self.addCleanup(shutil.rmtree, self.root, True)
        file_batch(self, self.root)
        self.last = task_id(self.root, "Batch issue number 5")
        self.create_at = rows_of(self.root, self.last)[0][1]["created"]

    def test_the_last_create_is_after_t_plus_1(self):
        self.assertEqual(self.create_at, "2026-10-29T07:25:11Z", "five creates one second apart from T")
        self.assertGreater(self.create_at, T1, "the defect's shape: the batch runs past the move's --now")

    def check_move(self, argv, state, events):
        code, out, err = run(self.root, *argv)
        self.assertEqual(code, 0, err)
        rows = rows_of(self.root, self.last)
        self.assertEqual(rows[0][1]["verdict"]["event"], "create", "dev_queue's order: the create first")
        moved = [r for _n, r in rows[1:]]
        self.assertEqual([r["verdict"]["event"] for r in moved], events)
        for r in moved:
            self.assertGreater(r["created"], self.create_at, "a move sorts after its task's create")
        self.assertEqual(moved[0]["created"], "2026-10-29T07:25:12Z", "one second after the newest record")
        self.assertEqual(shown(self, self.root, self.last)["state"], state)
        return moved

    def test_discussing(self):
        self.check_move(["discussing", self.last, "--by", "developer", "--now", T1], "discussing", ["status"])

    def test_discussing_with_people(self):
        moved = self.check_move(["discussing", self.last, "--by", "developer", "--with", "email_lead", "--now", T1],
                                "discussing", ["assign", "status"])
        self.assertEqual(moved[1]["created"], "2026-10-29T07:25:13Z")
        self.assertEqual(shown(self, self.root, self.last)["assignees"], ["email_lead"])

    def test_wont(self):
        self.check_move(["wont", self.last, "--by", "developer", "--reason", "not now", "--now", T1], "wont-do",
                        ["status"])
        self.assertEqual(shown(self, self.root, self.last)["reason"], "not now")

    def test_card(self):
        self.check_move(["card", self.last, "PF-5", "--by", "developer", "--now", T1], "carded", ["link", "status"])
        self.assertEqual(shown(self, self.root, self.last)["carded_as"], "PF-5")

    def test_two_moves_in_a_row_stay_in_order(self):
        self.check_move(["discussing", self.last, "--by", "developer", "--now", T1], "discussing", ["status"])
        code, out, err = run(self.root, "wont", self.last, "--by", "developer", "--reason", "after all", "--now", T1)
        self.assertEqual(code, 0, err)
        rows = rows_of(self.root, self.last)
        self.assertEqual([r["created"] for _n, r in rows][1:], ["2026-10-29T07:25:12Z", "2026-10-29T07:25:13Z"])
        self.assertEqual(shown(self, self.root, self.last)["state"], "wont-do")

    def test_a_dry_run_stamps_the_same_and_writes_nothing(self):
        before = listing(self.root)
        code, out, err = run(self.root, "wont", self.last, "--by", "developer", "--reason", "x", "--now", T1,
                             "--dry-run", "--json")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["records"][0]["created"], "2026-10-29T07:25:12Z")
        self.assertEqual(listing(self.root), before)


class InThePast(unittest.TestCase):
    """(b)"""

    def setUp(self):
        self.root = pf18.fixture()
        self.addCleanup(shutil.rmtree, self.root, True)
        file_batch(self, self.root)

    def test_stamped_at_now_unchanged(self):
        last = task_id(self.root, "Batch issue number 5")
        for argv, now in ((["discussing", last, "--by", "developer", "--with", "email_lead"], "2026-10-29T08:00:00Z"),
                          (["card", last, "PF-5", "--by", "developer"], "2026-10-29T09:00:00Z")):
            code, out, err = run(self.root, *(argv + ["--now", now]))
            self.assertEqual(code, 0, err)
        stamps = [r["created"] for _n, r in rows_of(self.root, last)[1:]]
        self.assertEqual(stamps, ["2026-10-29T08:00:00Z", "2026-10-29T08:00:01Z",
                                  "2026-10-29T09:00:00Z", "2026-10-29T09:00:01Z"])
        self.assertEqual(shown(self, self.root, last)["state"], "carded")

    def test_newest_record_counts_not_only_the_create(self):
        first = task_id(self.root, "Batch issue number 1")
        code, out, err = run(self.root, "fix", first, "an idea", "--by", "developer", "--now", "2026-10-29T08:00:30Z")
        self.assertEqual(code, 0, err)
        code, out, err = run(self.root, "wont", first, "--by", "developer", "--reason", "x", "--now",
                             "2026-10-29T08:00:10Z")
        self.assertEqual(code, 0, err)
        rows = rows_of(self.root, first)
        self.assertEqual([r["verdict"]["event"] for _n, r in rows], ["create", "comment", "status"])
        self.assertEqual(rows[-1][1]["created"], "2026-10-29T08:00:31Z", "one second after the comment")


class FromTheFuture(unittest.TestCase):
    """(c)"""

    def setUp(self):
        self.root = pf18.fixture()
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_more_than_60_s_ahead_is_refused(self):
        file_batch(self, self.root, items=BATCH[:1], now="2026-10-29T07:27:00Z")
        tid = task_id(self.root, "Batch issue number 1")
        before = listing(self.root)
        for argv in (["discussing", tid, "--by", "developer"], ["wont", tid, "--by", "developer", "--reason", "x"],
                     ["card", tid, "PF-5", "--by", "developer"]):
            code, out, err = run(self.root, *(argv + ["--now", "2026-10-29T07:25:59Z"]))
            self.assertEqual(code, 2, out)
            self.assertIn("this task has records from the future (2026-10-29T07:27:00Z)", err)
            self.assertEqual(listing(self.root), before, "nothing written")
        self.assertEqual(shown(self, self.root, tid)["state"], "raised")

    def test_a_move_that_makes_no_sense_names_its_own_reason_first(self):
        file_batch(self, self.root, items=BATCH[:1], now="2026-10-29T07:27:00Z")
        tid = task_id(self.root, "Batch issue number 1")
        code, out, err = run(self.root, "done", tid, "--by", "developer", "--now", "2026-10-29T07:25:59Z")
        self.assertEqual(code, 2, out)
        self.assertIn("never ticked done", err)

    def test_exactly_60_s_ahead_is_stamped(self):
        file_batch(self, self.root, items=BATCH[:1], now="2026-10-29T07:25:59Z")
        tid = task_id(self.root, "Batch issue number 1")
        code, out, err = run(self.root, "discussing", tid, "--by", "developer", "--now", "2026-10-29T07:25:00Z")
        self.assertEqual(code, 0, err)
        self.assertEqual(rows_of(self.root, tid)[-1][1]["created"], "2026-10-29T07:26:00Z")


class Filing(unittest.TestCase):
    """(d)"""

    def setUp(self):
        self.root = pf18.fixture()
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_one_second_spacing_and_parent_first(self):
        items = [{"kind": "follow-up", "title": "Tell email_lead", "quote": "tell her", "session": "b3c1aa",
                  "parent": "1", "person": "email_lead"}] + BATCH[:2]
        file_batch(self, self.root, items=items)
        recs = [json.loads(pf18.read(os.path.join(self.root, TASKS, f))) for f in listing(self.root)]
        self.assertEqual(sorted(r["created"] for r in recs),
                         ["2026-10-29T07:25:07Z", "2026-10-29T07:25:08Z", "2026-10-29T07:25:09Z"])
        parent = task_id(self.root, "Batch issue number 1")
        follow = task_id(self.root, "Tell email_lead")
        self.assertLess(rows_of(self.root, parent)[0][1]["created"], rows_of(self.root, follow)[0][1]["created"])
        self.assertEqual(shown(self, self.root, parent)["follow_ups"], [follow])


if __name__ == "__main__":
    unittest.main()
