"""Disapprove -> learnings: the card carries its reasons to sent-back; one line in
learnings.jsonl on the cards root (never the repo); per-step digests the upstream
tools read; the Learnings tab's summary; the approver list; prompt hooks stay
silent until their switch is on. Fake Meta, temp tree."""
import json, os, sys, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import cards as C, learnings as L
from fake_meta import FakeMeta
from test_cards import Base, NAME


class Learnings(Base):
    def setUp(self):
        super().setUp()
        os.environ.pop("META_LEARNINGS_HOOKS", None)

    def test_disapprove_writes_one_learning(self):
        import approve as A
        f = self.card()
        code, out = A.disapprove(C.card_id(f), ["hook", "looks"], "faces melt in frame 2", "the owner")
        self.assertEqual(code, 200, out)
        recs = [json.loads(x) for x in (self.root / "learnings.jsonl").read_text().splitlines()]
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual((r["by"], r["brand"], r["lane"], r["unit"]), ("the owner", "brand-a", "image", NAME))
        self.assertEqual(r["brief_key"], "brand-a_glow-body-scrub_brief-0154")
        self.assertEqual([(x["id"], x["step"], x["tool"]) for x in r["reasons"]],
                         [("hook", 2, "image-teardown"), ("hook", 4, "copywriter"), ("looks", 5, "image-teardown")])
        self.assertEqual(r["card"]["words"]["headlines"], ["H1"])
        self.assertEqual(len(r["card"]["media"]), 2)
        self.assertEqual(out["to"][0], "2 Teardown · image-teardown")
        # the card carries the reasons into sent-back
        a = C.load(C.folder_of(out["id"]))["approval"]
        self.assertEqual([x["id"] for x in a["reasons"]], ["hook", "hook", "looks"])

    def test_lane_picks_the_tool(self):
        rs = L.resolve(["frame", "looks"], "video")
        self.assertEqual([(r["step"], r["tool"]) for r in rs], [(7, "video-edit"), (5, "video-production")])

    def test_digest_and_recent(self):
        import approve as A
        A.disapprove(C.card_id(self.card()), ["words"], "claims a cure", "the owner")
        d = self.root / "learnings" / "4-brief" / "brand-a.md"
        self.assertTrue(d.is_file())
        lines = L.recent(4, "brand-a", "copywriter")
        self.assertEqual(len(lines), 1)
        self.assertIn('[copywriter] Words wrong', lines[0])
        self.assertIn('"claims a cure"', lines[0])
        self.assertIn(NAME, lines[0])
        self.assertEqual(L.recent(4, "brand-a", "catalog"), [])
        self.assertEqual(L.recent(4, "brand-b"), [])

    def test_prompt_hook_off_by_default(self):
        import approve as A
        A.disapprove(C.card_id(self.card()), ["words"], "claims a cure", "the owner")
        self.assertEqual(L.prompt_block("copywriter", 4, "brand-a"), "")
        hooks = json.loads(L.HOOKS.read_text())
        self.assertTrue(hooks and not any(v.get("on") for k, v in hooks.items() if not k.startswith("_")))
        with mock.patch.dict(os.environ, {"META_LEARNINGS_HOOKS": "copywriter"}):
            b = L.prompt_block("copywriter", 4, "brand-a")
            self.assertTrue(b.strip().startswith(L.HEAD))
            self.assertIn("claims a cure", b)
            self.assertEqual(L.prompt_block("copywriter", 4, "brand-b"), "")   # nothing to say -> nothing added

    def test_summary_groups_by_step_and_tool(self):
        import approve as A
        A.disapprove(C.card_id(self.card()), ["words", "page"], "wrong page and claim", "the owner")
        A.disapprove(C.card_id(self.card(name=NAME[:-1] + "b")), ["words"], "off-brand", "the owner")
        s = L.summary()
        self.assertEqual(s["total"], 2)
        st = s["steps"][0]
        self.assertEqual((st["step"], st["name"], st["count"]), (4, "Brief", 3))
        cw = next(t for t in st["tools"] if t["tool"] == "copywriter")
        self.assertEqual((cw["count"], cw["reasons"][0]["count"], cw["notes"][0]["note"]), (2, 2, "off-brand"))
        self.assertEqual(L.summary(lane="video")["total"], 0)
        self.assertEqual(L.summary(brand="brand-a")["total"], 2)

    def test_approver_written_and_checked(self):
        import approve as A
        f = self.card()
        with mock.patch("upload.approvers", return_value=["the owner", "the developer"]):
            with self.assertRaises(SystemExit):
                A.disapprove(C.card_id(f), ["words"], "x", "Nobody")
            with self.assertRaises(SystemExit):
                A.disapprove(C.card_id(f), ["words"], "x", None)       # two approvers: must pick
            with mock.patch.object(A, "FAKE", FakeMeta):
                code, out = A.approve(C.card_id(f), "PAUSED", "the developer")
        self.assertTrue(out["ok"], out)
        self.assertEqual(C.load(C.folder_of(out["id"]))["approval"]["by"], "the developer")
        self.assertFalse((self.root / "learnings.jsonl").exists())     # an approve teaches nothing

    def test_uploader_refuses_a_name_not_on_the_list(self):
        import upload as U
        f = self.card()
        c = C.load(f)
        c["approval"] = {"by": "Somebody", "decision": "approve", "start": "PAUSED"}
        C.save(f, c)
        f = C.move(f, "2-approved")
        with self.assertRaises(SystemExit):
            U.upload_card(f, m=FakeMeta("brand-a"), log=lambda *_: None)


if __name__ == "__main__":
    unittest.main()
