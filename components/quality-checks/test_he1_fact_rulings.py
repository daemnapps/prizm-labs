#!/usr/bin/env python3
"""python3 test_he1_fact_rulings.py — HE-1 (fact rulings): ids, items, the
ruling command, and what a standing ruling clears. Stdlib unittest; no
network, no model, no git. Every record lands in a temp workspace."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="he1-fact-rulings-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP)          # before anything reads the workspace

HERE = Path(__file__).resolve().parent
REPO = next(d for d in HERE.parents if (d / "components" / "brand-finder").is_dir())
sys.path.insert(0, str(HERE))
import marketing_chain_checks as Q                      # noqa: E402
from marketing_chain_checks import rulings as R         # noqa: E402

BRAND = "testbrand"
CHECK = ('```CHECK\n{"facts":[{"quote":"scrub","problem":"WRONG","files_say":"serum"}],'
         '"drafts":[{"quote":"ghost tin","product":"ghost-tin"}],"chops":[{"quote":"and so","joined":"and so on"}],'
         '"typos":[{"quote":"uy","fix":"Buy"}]}\n```')
ITEMS = [
    Q.item("delivery", "fact", "product fact UNSUPPORTED: “it lasts all day” — the files say: nothing",
           "it lasts all day", "nothing"),
    Q.item("delivery", "fact", "product fact WRONG: “wash with it” — the files say: never alone",
           "wash with it", "never alone"),
    Q.item("delivery", "price", "$99.99 is not a price the offer bank sells today (live: $49.99)"),
    Q.item("delivery", "unfilled", "the finished piece still carries an UNFILLED note", "[UNFILLED: a part]"),
    Q.item("delivery", "subject", "the preview is empty — it is the first thing a reader sees"),
    Q.item("delivery", "chop", "chopped thought: “and so” → “and so on”", "and so"),
]
IDS = {i["kind"] + str(n): i["id"] for n, i in enumerate(ITEMS)}


def make_run(label, brand=BRAND, items=ITEMS, root=TMP):
    rd = root / "runs" / "email-production" / brand / label
    (rd / "deliverable").mkdir(parents=True, exist_ok=True)
    (rd / "run.json").write_text(json.dumps({"brand": brand}))
    deliv = {"result": "HELD", "problems": [i["text"] for i in items or ITEMS]}
    if items is not None:
        deliv["items"] = items
    (rd / "deliverable" / "check.json").write_text(json.dumps({"delivery": deliv}))
    return rd


def rule(*args, root=TMP):
    env = dict(os.environ, AI_WORKSPACE=str(root))
    return subprocess.run([sys.executable, str(HERE / "rule.py"), *map(str, args)],
                          capture_output=True, text=True, env=env, timeout=60)


N = [0]


def plant(root, pid, ruling, email="e1", brand=BRAND, kind="fact", fact="", created=None):
    """A ruling record written by hand — the gate must judge it the same way."""
    N[0] += 1
    d = root / R.RECORDS_REL
    d.mkdir(parents=True, exist_ok=True)
    at = created or "2026-10-01T10:%02d:00Z" % N[0]
    rec = {"schema": 1, "kind": "fact-rulings", "reviewer": "opslead", "item": pid,
           "verdict": {"brand": brand, "problem_id": pid, "email": email, "kind": kind,
                       "quote": "q", "files_say": None, "ruling": ruling, "fact": fact,
                       "reason": "", "by": "opslead", "at": at},
           "notes": "", "created": at, "via": "test"}
    (d / ("%04d--opslead--%s.json" % (N[0], pid))).write_text(json.dumps(rec))


def fresh_root():
    return Path(tempfile.mkdtemp(dir=TMP, prefix="ws-"))


class Ids(unittest.TestCase):
    def test_ids_are_stable_and_follow_the_quote(self):
        a = Q.problem_id("delivery", "fact", "it lasts all day")
        self.assertEqual(a, Q.problem_id("delivery", "fact", "it lasts all day"))
        self.assertEqual(len(a), 12)
        self.assertNotEqual(a, Q.problem_id("delivery", "fact", "it lasts all night"))
        self.assertNotEqual(a, Q.problem_id("copy", "fact", "it lasts all day"))
        self.assertNotEqual(a, Q.problem_id("delivery", "typo", "it lasts all day"))

    def test_check_items_texts_are_read_check_blocks_strings(self):
        for text in (CHECK, "no block", "```CHECK\nnot json\n```"):
            items = Q.check_items(text, "delivery")
            self.assertEqual([i["text"] for i in items], Q.read_check_block(text))
        kinds = [i["kind"] for i in Q.check_items(CHECK, "delivery")]
        self.assertEqual(kinds, ["fact", "draft", "chop", "typo"])
        self.assertEqual(Q.check_items("no block", "delivery")[0]["kind"], "check-unreadable")
        fact = Q.check_items(CHECK, "delivery")[0]
        self.assertEqual((fact["quote"], fact["files_say"]), ("scrub", "serum"))
        self.assertEqual(fact["id"], Q.problem_id("delivery", "fact", "scrub"))

    def test_hold_without_items_is_todays_shape(self):
        d = Path(tempfile.mkdtemp(dir=TMP))
        with self.assertRaises(Q.Held):
            Q.hold("delivery", ["a problem"], d)
        self.assertEqual(json.loads((d / "check.json").read_text()),
                         {"delivery": {"result": "HELD", "problems": ["a problem"]}})
        Q.hold("delivery", [], d)
        self.assertEqual(json.loads((d / "check.json").read_text()),
                         {"delivery": {"result": "pass", "problems": []}})

    def test_hold_with_items_writes_items_and_cleared(self):
        d = Path(tempfile.mkdtemp(dir=TMP))
        it, row = ITEMS[0], {"id": "x", "kind": "fact", "ruling": "true", "by": "opslead", "at": "t"}
        with self.assertRaises(Q.Held):
            Q.hold("delivery", [it["text"]], d, items=[it], cleared=[row])
        got = json.loads((d / "check.json").read_text())["delivery"]
        self.assertEqual(got, {"result": "HELD", "problems": [it["text"]], "items": [it], "cleared": [row]})
        Q.hold("delivery", [], d, items=[])
        self.assertEqual(json.loads((d / "check.json").read_text()),
                         {"delivery": {"result": "pass", "problems": [], "items": [], "cleared": []}})
        with self.assertRaises(AssertionError):
            Q.hold("delivery", ["something else"], d, items=[it])


class TheCommand(unittest.TestCase):
    def setUp(self):
        self.root = fresh_root()
        self.rd = make_run("e1", root=self.root)

    def records(self):
        d = self.root / R.RECORDS_REL
        return sorted(d.glob("*.json")) if d.is_dir() else []

    def test_one_record_through_the_one_writer_and_nothing_in_the_repo(self):
        repo_dir = REPO / R.RECORDS_REL
        before = sorted(repo_dir.glob("*")) if repo_dir.is_dir() else []
        r = rule(self.rd, ITEMS[0]["id"], "true", "It lasts all day — tested 2026-09.", "--by", "opslead",
                 root=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        recs = self.records()
        self.assertEqual(len(recs), 1)
        self.assertIn(str(recs[0]), r.stdout)
        rec = json.loads(recs[0].read_text())
        self.assertEqual(set(rec), {"schema", "kind", "reviewer", "item", "verdict", "notes", "created", "via"})
        self.assertEqual((rec["kind"], rec["reviewer"], rec["item"], rec["via"]),
                         ("fact-rulings", "opslead", ITEMS[0]["id"], "marketing-chain-checks/rule.py"))
        v = rec["verdict"]
        self.assertEqual(list(v), ["brand", "problem_id", "email", "kind", "quote", "files_say",
                                   "ruling", "fact", "reason", "by", "at"])
        self.assertEqual((v["brand"], v["email"], v["kind"], v["ruling"], v["quote"]),
                         (BRAND, "e1", "fact", "true", "it lasts all day"))
        self.assertTrue(rec["created"].endswith("Z"))
        self.assertTrue(recs[0].name.endswith("--opslead--%s.json" % ITEMS[0]["id"]))
        after = sorted(repo_dir.glob("*")) if repo_dir.is_dir() else []
        self.assertEqual(before, after, "nothing filed under the repo")

    def refused(self, *args, says):
        r = rule(self.rd, *args, root=self.root)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("REFUSED", r.stderr)
        self.assertIn(says, r.stderr)
        self.assertEqual(self.records(), [], "a refusal files nothing")

    def test_a_price_is_never_ruled(self):
        pid = ITEMS[2]["id"]
        for ruling, extra in (("true", ["the fact"]), ("true-once", ["--reason", "x"]),
                              ("fill", ["the fact"]), ("not-ours", [])):
            self.refused(pid, ruling, *extra, "--by", "opslead",
                         says=f"brands/{BRAND}/products/offer-bank.md (the ops lead's fold) — a ruling never clears a price")
        self.refused(pid, "wrong", "--by", "opslead", says="not rulable")

    def test_fact_text_with_a_price_is_refused(self):
        for ruling in ("true", "fill"):
            self.refused(ITEMS[0]["id"], ruling, "now just $39.99", "--by", "opslead",
                         says="a ruling never clears a price")

    def test_an_unknown_id_lists_the_ids(self):
        self.refused("000000000000", "true", "x", "--by", "opslead", says=ITEMS[0]["id"])

    def test_a_pre_he1_check_json_is_refused(self):
        make_run("old", items=None, root=self.root)
        r = rule(self.root / "runs/email-production" / BRAND / "old", ITEMS[0]["id"], "true", "x",
                 "--by", "opslead", root=self.root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("re-check it first: simple_email.py", r.stderr)
        self.assertIn(f"--brand {BRAND} --no-images", r.stderr)

    def test_no_brand_in_run_json_is_refused(self):
        (self.rd / "run.json").write_text("{}")
        self.refused(ITEMS[0]["id"], "true", "x", "--by", "opslead", says="names no brand")

    def test_true_needs_text_and_true_once_needs_a_reason(self):
        self.refused(ITEMS[0]["id"], "true", "--by", "opslead", says="needs the fact text")
        self.refused(ITEMS[0]["id"], "fill", "--by", "opslead", says="needs the fact text")
        self.refused(ITEMS[0]["id"], "true-once", "--by", "opslead", says="needs --reason")

    def test_an_unknown_ruling_is_refused(self):
        self.refused(ITEMS[0]["id"], "maybe", "--by", "opslead", says="is not a ruling")

    def test_unrulable_kinds_and_unfilled_limits(self):
        self.refused(ITEMS[4]["id"], "true", "x", "--by", "opslead", says="fix the email, not rulable")
        self.refused(ITEMS[3]["id"], "true", "x", "--by", "opslead", says="takes fill | not-ours | wrong")
        r = rule(self.rd, ITEMS[3]["id"], "fill", "The handoff is the tin.", "--by", "opslead", root=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)


class WhatClears(unittest.TestCase):
    def setUp(self):
        self.root = fresh_root()

    def cleared(self, email="e1", brand=BRAND):
        kept, rows = R.split(ITEMS, brand, email, self.root)
        self.assertEqual(len(kept) + len(rows), len(ITEMS))
        return {r["id"]: r["ruling"] for r in rows}

    def test_true_clears_every_email_of_the_brand(self):
        plant(self.root, ITEMS[0]["id"], "true", email="e1", fact="it does")
        self.assertEqual(self.cleared("e1"), {ITEMS[0]["id"]: "true"})
        self.assertEqual(self.cleared("e2"), {ITEMS[0]["id"]: "true"})

    def test_not_ours_clears_every_email(self):
        plant(self.root, ITEMS[5]["id"], "not-ours", kind="chop")
        self.assertEqual(self.cleared("e9"), {ITEMS[5]["id"]: "not-ours"})

    def test_true_once_clears_its_own_email_only(self):
        plant(self.root, ITEMS[1]["id"], "true-once", email="e1")
        self.assertEqual(self.cleared("e1"), {ITEMS[1]["id"]: "true-once"})
        self.assertEqual(self.cleared("e2"), {})

    def test_wrong_and_fill_clear_nothing(self):
        plant(self.root, ITEMS[0]["id"], "wrong")
        plant(self.root, ITEMS[1]["id"], "fill", fact="a fact")
        self.assertEqual(self.cleared(), {})

    def test_a_later_wrong_revokes_a_true(self):
        plant(self.root, ITEMS[0]["id"], "true", fact="it does", created="2026-10-01T10:00:00Z")
        plant(self.root, ITEMS[0]["id"], "wrong", created="2026-10-01T11:00:00Z")
        self.assertEqual(self.cleared(), {})
        self.assertEqual(R.verified_facts(self.root, BRAND), [])

    def test_another_brands_ruling_clears_nothing(self):
        plant(self.root, ITEMS[0]["id"], "true", brand="otherbrand", fact="it does")
        self.assertEqual(self.cleared(), {})
        self.assertEqual(R.verified_facts(self.root, BRAND), [])

    def test_a_hand_planted_price_ruling_clears_nothing(self):
        for ruling in ("true", "not-ours"):
            plant(self.root, ITEMS[2]["id"], ruling, kind="fact", fact="it is $99.99")
        plant(self.root, ITEMS[4]["id"], "true", kind="fact", fact="fine")      # a subject, ruled by hand
        self.assertEqual(self.cleared(), {})
        self.assertNotIn("it is $99.99", [f["fact"] for f in R.verified_facts(self.root, BRAND)])

    def test_unfilled_is_never_dropped(self):
        for ruling in ("fill", "not-ours"):
            plant(self.root, ITEMS[3]["id"], ruling, kind="unfilled", fact="filled")
            self.assertEqual(self.cleared(), {})

    def test_an_unreadable_record_is_skipped_never_a_crash(self):
        d = self.root / R.RECORDS_REL
        d.mkdir(parents=True)
        (d / "broken.json").write_text("{not json")
        plant(self.root, ITEMS[0]["id"], "true", fact="it does")
        self.assertEqual(self.cleared(), {ITEMS[0]["id"]: "true"})


class TheList(unittest.TestCase):
    def test_list_prints_standing_true_and_fill_then_not_ours(self):
        root = fresh_root()
        plant(root, ITEMS[0]["id"], "true", fact="It lasts all day.")
        plant(root, ITEMS[3]["id"], "fill", kind="unfilled", fact="The handoff is the tin.")
        plant(root, ITEMS[5]["id"], "not-ours", kind="chop")
        plant(root, ITEMS[1]["id"], "true", fact="Revoked fact.", created="2026-10-01T09:00:00Z")
        plant(root, ITEMS[1]["id"], "wrong", created="2026-10-01T12:00:00Z")
        plant(root, "aaaaaaaaaaaa", "true", brand="otherbrand", fact="Other brand's fact.")
        r = rule("--list", BRAND, root=root)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn("It lasts all day.", out)
        self.assertIn("The handoff is the tin.", out)
        self.assertNotIn("Revoked fact.", out)
        self.assertNotIn("Other brand's fact.", out)
        self.assertLess(out.index("verified facts"), out.index("not ours"))
        self.assertIn(ITEMS[5]["id"], out[out.index("not ours"):])
        self.assertEqual(len(R.verified_facts(root, BRAND)), 2)
        self.assertEqual([g["id"] for g in R.not_ours(root, BRAND)], [ITEMS[5]["id"]])


class TheKind(unittest.TestCase):
    def test_the_kind_manifest(self):
        f = REPO / "platform" / "data" / "kinds" / "fact-rulings.json"
        m = json.loads(f.read_text())
        self.assertEqual(m["kind"], f.stem)
        self.assertEqual(m["kind"], R.KIND)
        self.assertEqual(m["written_by"], "marketing-chain-checks")
        self.assertNotIn("index", m)
        keys = [v["key"] for v in m["verdict_fields"]]
        self.assertEqual(keys, ["brand", "problem_id", "email", "kind", "quote", "files_say",
                                "ruling", "fact", "reason", "by", "at"])
        ruling = next(v for v in m["verdict_fields"] if v["key"] == "ruling")
        self.assertEqual(tuple(ruling["values"]), R.RULINGS)


if __name__ == "__main__":
    unittest.main()
