"""QB-5 (production contract): the email adapter, adapter.py, on fixture runs only.

report maps each fixture state to the PROPOSED stage table (live unreachable, said), writes under the shadow root only
and refuses runs/queue while the live switch is off; detail reads layout.json with subprocess and Chrome made to fail
if called; apply round-trips every shared word (and fill) with sync.py's calls stubbed at the seam, `go` refused exit 2.
Stdlib only: no network, no Chrome, no Klaviyo. Run from the repo root (only this folder goes on sys.path — the folder
above has an email.py that would shadow the standard library):
    python3 tools/email-production/adapter/test_qb5_email_adapter.py
"""
import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter  # noqa: E402

FIX = HERE / "test_qb5_fixtures"
BRAND = "fxbrand"
NOW = "2026-10-22T05:00:00Z"
CASES = json.loads((FIX / "cards.json").read_text())["runs"]


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def files(top):
    return {p.relative_to(top).as_posix() for p in Path(top).rglob("*") if p.is_file()}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qb5-email-"))
        self.runs = self.tmp / "runs" / "email-production"
        for label, c in CASES.items():
            run = self.runs / BRAND / label
            (run / "klaviyo").mkdir(parents=True)
            (run / "klaviyo" / "card.json").write_text(json.dumps(c["card"], indent=1) + "\n")
            if not c.get("no_design"):
                (run / "design").mkdir()
                shutil.copy(str(FIX / "email.json"), str(run / "design" / "email.json"))
                (run / "klaviyo" / "email.html").write_text("<html><body>%s</body></html>\n" % label)
        self.saved = (adapter.REPO, adapter.RUNS, adapter.LEARNINGS, adapter.prepare.STAMPS, adapter.run_sync)
        adapter.REPO, adapter.RUNS = self.tmp, self.runs
        adapter.LEARNINGS = self.tmp / "runs" / "learnings"
        adapter.prepare.STAMPS = self.tmp / "stamps.json"

    def tearDown(self):
        adapter.REPO, adapter.RUNS, adapter.LEARNINGS, adapter.prepare.STAMPS, adapter.run_sync = self.saved
        shutil.rmtree(str(self.tmp))

    def run_dir(self, label):
        return self.runs / BRAND / label

    def eid(self, label):
        return "%s_email_%s" % (BRAND, label)

    def main(self, *argv):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = adapter.main(list(argv))
        return code, out.getvalue(), err.getvalue()


class Report(Base):
    def test_each_state_maps_to_the_table(self):
        before = files(self.tmp)
        out = adapter.report(None, source="fixture-mac", now=NOW)
        obs = json.loads((self.tmp / "runs" / "queue-shadow" / "observations" / "fixture-mac.json").read_text())
        self.assertEqual(obs["source"], "fixture-mac")
        self.assertEqual(obs["as_of"], NOW)
        ents = obs["entries"]
        want = {self.eid(k): v["expect"] for k, v in CASES.items() if not v.get("no_design")}
        self.assertEqual(sorted(ents), sorted(want))             # the card with no design/email.json is not reported
        for eid, (stage, state) in want.items():
            e = ents[eid]
            self.assertEqual((e["observed_stage"], e["state"]), (stage, state), eid)
            self.assertEqual(e["kind"], "email")
            self.assertEqual(e["brand"], BRAND)
            self.assertEqual(e["links"], {"run": "runs/email-production/%s/%s" % (BRAND, e["label"])})
            self.assertEqual(e["title"], CASES[e["label"]]["card"]["subjects"][0]["subject"])
        self.assertEqual(ents[self.eid("fx-held")]["held"], ["a price the offer bank does not sell"])
        self.assertEqual([k for k, e in ents.items() if e["held"]], [self.eid("fx-held")])
        self.assertEqual({k: e.get("approved_by") for k, e in ents.items() if e.get("approved_by")},
                         {self.eid("fx-eve"): "eve"})
        # live is unreachable, and the report says so
        self.assertNotIn("live", {e["observed_stage"] for e in ents.values()})
        self.assertIn("unreachable", out["live"])
        self.assertEqual(out["stages"], {"making": 2, "final-needs-you": 2, "launch": 2})
        # written under the shadow root only
        new = files(self.tmp) - before
        self.assertEqual(new, {"runs/queue-shadow/observations/fixture-mac.json"})
        # the queue core reads it
        idx = adapter.qcore.reduce(*adapter.qcore.load(self.tmp / "runs" / "queue-shadow"), NOW)
        self.assertEqual(len(idx["entries"]), 6)

    def test_command_output_states_live_unreachable(self):
        code, out, _ = self.main("report", "--source", "fixture-mac")
        self.assertEqual(code, 0)
        got = json.loads(out)
        self.assertIn("unreachable", got["live"])
        self.assertEqual(got["root"], "runs/queue-shadow")
        code, out, _ = self.main("report", "--source", "fixture-mac")
        self.assertTrue(json.loads(out)["unchanged"])           # same entries: the file is not rewritten

    def test_live_queue_refused_while_switch_off(self):
        live = self.tmp / "runs" / "queue"
        code, _, err = self.main("report", "--root", str(live), "--source", "fixture-mac")
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", err)
        self.assertFalse(live.exists())
        sw = self.tmp / "components" / "creative-queue" / "live-switch.json"
        sw.parent.mkdir(parents=True)
        sw.write_text('{"live": "off"}\n')
        with self.assertRaises(adapter.qcore.Refused):
            adapter.report(live / "sub", source="fixture-mac")
        self.assertFalse(live.exists())


class Detail(Base):
    def setUp(self):
        super(Detail, self).setUp()
        run = self.run_dir("fx-ready")
        (run / "klaviyo" / "layout.json").write_text(json.dumps({
            "schema": 1, "height": 1000.0,
            "sections": [{"i": 0, "top": 0.0, "bottom": 100.0}, {"i": 1, "top": 100.0, "bottom": 600.0},
                         {"i": 2, "top": 600.0, "bottom": 700.0}],
            "from": sha(run / "design" / "email.json"), "html": sha(run / "klaviyo" / "email.html")}))
        eve = self.run_dir("fx-eve")
        (eve / "klaviyo" / "layout.json").write_text(json.dumps({
            "schema": 1, "height": 1000.0, "sections": [{"i": 0, "top": 0.0, "bottom": 100.0}],
            "from": "an-older-layout", "html": sha(eve / "klaviyo" / "email.html")}))

        def boom(*a, **k):
            raise AssertionError("detail called a process or Chrome: %r" % (a[:1],))
        self.patches = [(subprocess, "run"), (subprocess, "Popen"), (subprocess, "check_output"), (subprocess, "call"),
                        (adapter.LF, "measure"), (adapter.LF, "shot"), (adapter.sync, "_shot")]
        self.kept = [getattr(m, n) for m, n in self.patches]
        for m, n in self.patches:
            setattr(m, n, boom)

    def tearDown(self):
        for (m, n), v in zip(self.patches, self.kept):
            setattr(m, n, v)
        super(Detail, self).tearDown()

    def test_positions_from_layout_json(self):
        d = adapter.detail(self.eid("fx-ready"))
        self.assertIs(d["layout_stale"], False)
        self.assertEqual(d["title"], "Ready one")
        p = d["parts"]
        self.assertEqual([x["n"] for x in p], [0, 1, 2, 3])
        self.assertEqual([x["kind"] for x in p], ["band", "hero_photo", "cta", "photo_card"])
        self.assertEqual(p[1]["label"], "Hero picture")
        self.assertEqual(p[1]["position"], {"top": 0.1, "bottom": 0.6})
        self.assertIsNone(p[3]["position"])                        # a section the layout does not place
        self.assertEqual(p[1]["words"], [{"path": "headline", "value": "Hello there"}, {"path": "sub", "value": "A line under it"}])
        self.assertEqual(p[1]["media"], [{"path_label": "run:media/hero.png", "alt": "A hero picture",
                                          "drive_id": "fixture-drive-id"}])
        self.assertEqual(p[3]["media"], [{"path_label": None, "alt": "still to make", "state": "not made"}])
        self.assertEqual([x["ok"] for x in p], [False, True, False, False])
        # sync's row id names the same email
        self.assertEqual(adapter.detail("%s__fx-ready" % BRAND)["id"], self.eid("fx-ready"))

    def test_missing_or_stale_layout_gives_null_positions(self):
        for label in ("fx-checks", "fx-eve"):                      # none, and one from an older layout
            d = adapter.detail(self.eid(label))
            self.assertIs(d["layout_stale"], True, label)
            self.assertEqual({x["position"] for x in d["parts"]}, {None}, label)

    def test_unknown_id(self):
        self.assertIsNone(adapter.detail(self.eid("fx-old")))      # no design/email.json: not a designed email
        code, _, err = self.main("detail", "nobody_email_nothing")
        self.assertEqual(code, 1)
        self.assertIn("no designed email", err)


# word, part, payload -> the sync.py call it must make
TABLE = [
    ("words", "1", json.dumps([{"path": "headline", "before": "Hello there", "value": "Hi"}]),
     {"action": "words", "section": 1, "edits": [{"path": "headline", "before": "Hello there", "value": "Hi"}]}),
    ("picture", "1", "0: warmer light", {"action": "picture", "section": 1, "picture": 0, "note": "warmer light"}),
    ("redo", "2", "a calmer button", {"action": "look", "section": 2, "note": "a calmer button"}),
    ("redo", "-", "calmer all through", {"action": "send_back", "note": "calmer all through"}),
    ("move", "2", "up", {"action": "move", "section": 2, "dir": "up"}),
    ("remove", "3", "", {"action": "remove", "section": 3}),
    ("ok", "1", "", {"action": "ok", "section": 1}),
    ("note", "-", "too long overall", {"action": "send_back", "note": "too long overall"}),
    ("fill", "-", "", {"action": "fill"}),
]


class Apply(Base):
    def setUp(self):
        super(Apply, self).setUp()
        self.calls = []

        def fake(calls):
            self.calls.extend(calls)
            k = calls[0]
            run = self.runs / k["brand"] / k["label"]
            if k["action"] == "ok":
                f = run / "klaviyo" / "card.json"
                c = json.loads(f.read_text())
                c["sections_ok"] = sorted(set(c.get("sections_ok") or []) | {k["section"]})
                f.write_text(json.dumps(c) + "\n")
            else:
                f = run / "design" / "email.json"
                d = json.loads(f.read_text())
                d["applied"] = (d.get("applied") or []) + [k["action"]]
                f.write_text(json.dumps(d) + "\n")
                (run / "media").mkdir(exist_ok=True)
                (run / "media" / "new.png").write_bytes(b"\x89PNG media, never committed")
                learn = self.tmp / "runs" / "learnings" / ("%s.jsonl" % k["brand"])
                learn.parent.mkdir(parents=True, exist_ok=True)
                with learn.open("a") as fh:
                    fh.write(json.dumps({"rule": k["action"]}) + "\n")
            return [{"id": k["id"], "state": "applied", "result": "done"}]
        adapter.run_sync = fake

    def test_every_word_round_trips(self):
        self.assertEqual(sorted({w for w, _, _, _ in TABLE}), sorted(adapter.WORDS))
        run = self.run_dir("fx-ready")
        rel = "runs/email-production/%s/fx-ready" % BRAND
        for word, part, payload, want in TABLE:
            rev = adapter.revision(run)
            n = len(self.calls)
            code, out = adapter.apply(self.eid("fx-ready"), part, word, payload or None, by="the team")
            self.assertEqual(code, 0, (word, out))
            self.assertIs(out["ok"], True)
            self.assertEqual(len(self.calls), n + 1, word)
            k = self.calls[-1]
            for key, v in want.items():
                self.assertEqual(k.get(key), v, (word, part, key))
            if "section" not in want:
                self.assertNotIn("section", k, word)
            self.assertEqual((k["brand"], k["label"], k["email"], k["by"]), (BRAND, "fx-ready", "%s__fx-ready" % BRAND, "the team"))
            self.assertNotEqual(out["revision"], rev, word)
            self.assertEqual(out["revision"], adapter.revision(run))
            self.assertEqual(out["ref"], rel + "/design/email.json")
            changed = rel + ("/klaviyo/card.json" if word == "ok" else "/design/email.json")
            self.assertIn(changed, out["paths"], word)
            self.assertFalse([p for p in out["paths"] if p.endswith(".png")], out["paths"])   # media never reported
            if word != "ok":
                self.assertIn("runs/learnings/%s.jsonl" % BRAND, out["paths"])
        # the rebuilding words keep the card's marks and stamp the build, as ask.py does
        self.assertIn("%s/fx-ready" % BRAND, json.loads((self.tmp / "stamps.json").read_text()))
        self.assertEqual(json.loads((run / "klaviyo" / "card.json").read_text())["sections_ok"], [1])

    def test_go_and_scheduled_refused_exit_2(self):
        for word, names in (("go", "approval page"), ("scheduled", "Klaviyo"), ("send", "approval"),
                            ("approve", "approval"), ("schedule", "approval")):
            code, out = adapter.apply(self.eid("fx-ready"), "-", word, None, by="the team")
            self.assertEqual(code, 2, word)
            self.assertIs(out["ok"], False)
            self.assertIn(names, out["message"])
        code, out, _ = self.main("apply", self.eid("fx-ready"), "-", "go", "--by", "the team")
        self.assertEqual(code, 2)
        self.assertIn("refused", json.loads(out)["message"])
        self.assertEqual(self.calls, [])                            # nothing reached sync.py

    def test_unknown_word_refused_bad_payload_failed(self):
        code, _ = adapter.apply(self.eid("fx-ready"), "1", "sparkle", None, by="the team")
        self.assertEqual(code, 2)
        for part, word, payload in (("1", "move", "sideways"), ("-", "words", "[]"), ("-", "picture", "0: x"),
                                    ("1", "fill", None), ("1", "redo", None), ("x", "ok", None)):
            code, out = adapter.apply(self.eid("fx-ready"), part, word, payload, by="the team")
            self.assertEqual(code, 1, (part, word, out))
        code, out = adapter.apply(self.eid("fx-ready"), "1", "ok", None, by=None)
        self.assertEqual(code, 1)
        self.assertIn("--by", out["message"])
        code, out = adapter.apply("nobody_email_nothing", "1", "ok", None, by="the team")
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, [])

    def test_a_klaviyo_draft_is_warned_about(self):
        code, out = adapter.apply(self.eid("fx-draft"), "2", "redo", "warmer", by="the team")
        self.assertEqual(code, 0)
        self.assertIn("already a Klaviyo draft (fixture-campaign)", out["message"])

    def test_a_failed_sync_call_is_failed(self):
        adapter.run_sync = lambda calls: [{"id": calls[0]["id"], "state": "failed", "result": "it can't move further that way"}]
        code, out = adapter.apply(self.eid("fx-ready"), "0", "move", "up", by="the team")
        self.assertEqual(code, 1)
        self.assertIs(out["ok"], False)
        self.assertIn("further", out["message"])
        self.assertEqual(out["paths"], [])


if __name__ == "__main__":
    unittest.main()
