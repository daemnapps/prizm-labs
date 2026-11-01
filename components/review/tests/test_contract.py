#!/usr/bin/env python3
"""components/review — the CONTRACT test.

Components rule 2: the contract is the only dependable surface, and nothing
outside the folder may depend on internals. So this file asserts the SURFACE —
what RV-3 (on_accept adapter), RV-6 (reference panels) and RV-10 (PM review
integration) are allowed to import and what each promises — and the REFUSALS,
which are the other half of a contract: what the module will not do, proven
rather than promised.

The card's own claims — byte-equality between the two doors, the fold's three
cases, `is_accepted` — are proven in the declared test,
`new-workflow-design/builds/review-component/test_rv2_request.py`. This file
does not restate them; it holds the component to its own wall.

Run: python3 components/review/tests/test_contract.py
"""
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))

import review_request as rr        # noqa: E402 — after the path insert

ASSET = {"warehouse": "repo", "ref": "components/review/review_request.py",
         "title": "The request module"}
CALL = dict(asset=ASSET, type="md", reviewers=["steph"], lane="dev-qc",
            requested_by="dayu")


class Plane(unittest.TestCase):
    """A records plane in a temp dir. No git repo: the contract cases never
    commit, so `commit=False` is passed everywhere here."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / rr.RECORDS_REL).mkdir(parents=True)

    def file(self, **over):
        kw = dict(CALL, root=str(self.root), env={}, commit=False)
        kw.update(over)
        return rr.file_request(**kw)

    def records(self):
        return sorted((self.root / rr.RECORDS_REL).glob("*.json"))


class TheSurface(unittest.TestCase):
    def test_the_four_the_card_declares_are_exposed(self):
        for name in ("file_request", "list_open", "latest_verdicts",
                     "is_accepted"):
            self.assertTrue(callable(getattr(rr, name, None)),
                            "%s is not on the contract" % name)

    def test_the_shared_parts_a_later_reader_imports_are_exposed(self):
        """The fold and the writer are the SHARED PARTS on the card. A consumer
        that cannot reach them from here would write a second copy, which is
        the failure the card names."""
        for name in ("fold", "file_record", "read_records", "record", "render",
                     "filename", "Refused"):
            self.assertTrue(hasattr(rr, name), "%s is not reachable" % name)

    def test_file_request_takes_the_grammars_own_words(self):
        """The parameter names ARE the record's field names — a caller reading
        the manifest can call this without a translation table."""
        params = list(inspect.signature(rr.file_request).parameters)
        self.assertEqual(params[:5], ["asset", "type", "reviewers", "lane",
                                      "requested_by"])
        for optional in ("item", "due", "on_accept", "notes"):
            self.assertIn(optional, params)

    def test_the_module_needs_no_credential_to_be_imported_or_read(self):
        """Components rule 7: reading finished results needs nothing. Import,
        fold and list are all credential-free; only the API door is
        credential-bearing, and it is chosen by the environment."""
        self.assertEqual(rr.list_open(records=[]), [])
        self.assertEqual(rr.latest_verdicts([]), {})
        self.assertFalse(rr.is_accepted([]))


class TheRefusals(Plane):
    """Every refusal writes NOTHING. A half-filed request is worse than a
    refused one: the reviewer sees an item nobody meant to ask about."""

    def refuses(self, **over):
        with self.assertRaises(rr.Refused):
            self.file(**over)
        self.assertEqual(self.records(), [],
                         "a refused request left a record behind")

    def test_a_type_outside_the_grammar(self):
        self.refuses(type="pdf")

    def test_a_warehouse_outside_the_grammar(self):
        self.refuses(asset=dict(ASSET, warehouse="s3"))

    def test_an_asset_with_no_ref_or_no_title(self):
        self.refuses(asset={"warehouse": "repo", "ref": "", "title": "x"})
        self.refuses(asset={"warehouse": "repo", "ref": "x", "title": ""})

    def test_a_request_that_asks_nobody(self):
        self.refuses(reviewers=[])

    def test_a_reviewer_that_is_not_a_person_id(self):
        self.refuses(reviewers=["the team Smith <steph@…>"])

    def test_a_lane_that_is_not_a_label(self):
        self.refuses(lane="Email Sends")

    def test_a_due_date_that_is_not_a_date(self):
        self.refuses(due="next tuesday")

    def test_an_on_accept_that_names_no_action(self):
        """RV-3 (on_accept adapter) files exactly what the request declared;
        an `on_accept` with no action is a promise it could never keep."""
        self.refuses(on_accept={"chain": "copy-general"})

    def test_an_item_id_outside_the_RQ_grammar(self):
        self.refuses(item="review-1")
        self.refuses(item="RQ-a--b")          # `--` is the filename separator

    def test_an_event_outside_the_grammar(self):
        with self.assertRaises(rr.Refused):
            rr.file_record("RQ-20260908010000-x", {"event": "comment"}, "dayu",
                           root=str(self.root), env={}, commit=False)
        self.assertEqual(self.records(), [])


class TheWriterServesEveryEvent(Plane):
    """`file_record` is the ONE writer. RV-3 (on_accept adapter) and the panels
    file `verdict` and `close` records through it rather than minting a second
    one, and what it writes folds."""

    def test_a_request_a_verdict_and_a_close_round_trip_through_the_fold(self):
        out = self.file(now="2026-09-08T01:00:00Z")
        item = out["item"]
        rr.file_record(item, {"event": "verdict", "verdict": "approve",
                              "reasons": ["accuracy"], "note": "ship it"},
                       "steph", root=str(self.root), env={}, commit=False,
                       now="2026-09-08T02:00:00Z")
        state = rr.fold(rr.read_records(root=str(self.root), item=item))
        self.assertEqual(state["status"], "open")
        self.assertEqual(list(state["verdicts"]), ["steph"])
        self.assertFalse(state["accepted"])

        rr.file_record(item, {"event": "close", "decision": "accepted"},
                       "dayu", root=str(self.root), env={}, commit=False,
                       now="2026-09-08T03:00:00Z")
        recs = rr.read_records(root=str(self.root), item=item)
        self.assertEqual(len(recs), 3)
        self.assertTrue(rr.is_accepted(recs))
        self.assertEqual(rr.fold(recs)["status"], "closed")
        self.assertEqual(rr.list_open(root=str(self.root)), [])

    def test_every_record_it_writes_is_on_the_kind_and_named_by_the_plane(self):
        out = self.file(now="2026-09-08T01:00:00Z")
        path = Path(out["path"])
        rec = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(rec["kind"], rr.KIND)
        self.assertEqual(rec["reviewer"], "dayu")
        self.assertEqual(rec["created"], "2026-09-08T01:00:00Z")
        self.assertEqual(path.name,
                         "20260908T010000Z--dayu--%s.json" % out["item"])
        self.assertEqual(path.parent, self.root / rr.RECORDS_REL,
                         "the plane it emits is the one its CLAUDE.md declares")

    def test_the_module_writes_nowhere_but_the_review_plane(self):
        before = {p for p in self.root.rglob("*") if p.is_file()}
        self.file()
        after = {p for p in self.root.rglob("*") if p.is_file()}
        for p in after - before:
            self.assertEqual(p.parent, self.root / rr.RECORDS_REL,
                             "%s is outside the review plane" % p)


class TheCommandLine(unittest.TestCase):
    """`--dry-run` prints the record and touches nothing — the thing a person
    runs before filing for real, and the thing a reviewer of this card can run
    without writing to the plane."""

    def test_dry_run_prints_a_parseable_record_and_writes_nothing(self):
        r = subprocess.run(
            [sys.executable, str(HERE.parents[1] / "review_request.py"),
             "--dry-run", "--title", "The request module", "--type", "md",
             "--warehouse", "repo", "--ref", "components/review/review_request.py",
             "--lane", "dev-qc", "--reviewer", "steph", "--by", "dayu"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        name, body = r.stdout.split("\n", 1)
        self.assertTrue(name.endswith(".json"))
        rec = json.loads(body)
        self.assertEqual(rec["verdict"]["event"], "request")
        self.assertEqual(rec["verdict"]["asset"]["warehouse"], "repo")
        self.assertEqual(rec["reviewer"], "dayu")

    def test_a_refusal_exits_two_and_says_which_field(self):
        r = subprocess.run(
            [sys.executable, str(HERE.parents[1] / "review_request.py"),
             "--dry-run", "--title", "x", "--type", "md", "--warehouse", "repo",
             "--ref", "x", "--lane", "Email Sends", "--reviewer", "steph",
             "--by", "dayu"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn("lane", r.stderr)
        self.assertIn("Nothing was filed", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
