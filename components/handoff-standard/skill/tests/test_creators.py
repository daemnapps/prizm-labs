#!/usr/bin/env python3
"""creators.py — offline tests. Run: python3 components/handoff-standard/skill/tests/test_creators.py

No network, no Drive, no key, no message sent. Scoring is tested on fixture
cards and a fixture ask; the hand-off and track tests take the first creator
brief in the register whose brief file is on disk (never a literal brand or
brief here) and write only into a temporary folder."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import creators as C  # noqa: E402
import handoff as H  # noqa: E402
from test_handoff import fixture_catalog  # noqa: E402


def card(cid, **kw):
    base = {"id": cid, "name": cid.title(), "handle": None, "kind": "real-creator", "role": "ugc",
            "gender": "female", "ethnic-appearance": None, "ethnic-appearance-source": None,
            "age-band": "55-64", "age-band-source": "stated", "avatars-fit": ["av-one"], "sub-avatars-fit": [],
            "reads": "", "source": "fixture", "notes": [], "missing": []}
    base.update(kw)
    return base


def write_cards(root, cards, retired=()):
    f = Path(root) / "cards-v6.json"
    f.write_text(json.dumps({"cards": cards, "_retired": {"people": [{"id": r} for r in retired]}}))
    return f


ASK = {"brief": "brief-0001", "title": "t", "avatar": "av-one", "sub_avatar": None, "gender": "female",
       "age": [55, 70], "ethnic": None, "look": ["grey hair", "curly hair"], "language": "english",
       "lane": "creator", "role": "protagonist", "own_creator": "some-handle", "written_for": None, "sources": {}}


class ScoreTests(unittest.TestCase):
    def test_stated_age_beats_band_and_look_counts(self):
        a = card("ann", notes=["age: self-stated age 62"], reads="curly grey hair")
        b = card("bea", reads="blonde")
        sa, mx, _ = C.score(a, ASK)
        sb, _, _ = C.score(b, ASK)
        self.assertGreater(sa, sb)
        self.assertEqual(mx, 100)

    def test_own_post_is_a_reason(self):
        a = card("cat", handle="@some.handle")
        _, _, why = C.score(a, ASK)
        self.assertTrue(any("her own post" in w for w in why), why)

    def test_gates(self):
        retired = {"gone"}
        self.assertIn("retired", C.excluded_why(card("gone"), ASK, retired))
        self.assertIn("AI character", C.excluded_why(card("bot", kind="ai-character", **{"casting-sheet": "yes", "status": "current"}), ASK, retired))
        self.assertIn("not the person", C.excluded_why(card("doc", role="authority", credential="x"), ASK, retired))
        self.assertIn("asks for a woman", C.excluded_why(card("bob", gender="male"), ASK, retired))
        ai = dict(ASK, lane="ai")
        self.assertIsNone(C.excluded_why(card("sheet", kind="ai-character", **{"casting-sheet": "yes", "status": "current"}), ai, retired))
        self.assertIn("no casting sheet", C.excluded_why(card("nosheet", kind="ai-character", **{"casting-sheet": "no", "status": "not current — no casting sheet"}), ai, retired))
        self.assertIn("real creator", C.excluded_why(card("real"), ai, retired))

    def test_card_age_reads(self):
        self.assertEqual(C.card_age(card("x", notes=["age: self-stated age 68"])), (68, 68, True))
        self.assertEqual(C.card_age(card("x", notes=["age: profile read [55-60] + own copy"])), (55, 60, False))
        self.assertEqual(C.card_age(card("x", **{"age-band": "65-plus"})), (65, 85, False))
        self.assertEqual(C.card_age(card("x", **{"age-band": None, "age-band-source": None})), (None, None, False))

    def test_handle_match(self):
        c = card("kay", handle="@kay.zed", **{"old-ids": ["kay-zed"]})
        self.assertTrue(C.card_matches_handle(c, "kay-zed"))
        self.assertTrue(C.card_matches_handle(c, "@kay.zed"))
        self.assertFalse(C.card_matches_handle(c, "someone-else"))

    def test_bad_cards_file_refuses(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            f = write_cards(tmp, [card("x", gender="other")])
            with self.assertRaises(H.Refused):
                C.load_cards("any", f)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def creator_brief():
    reg = H.BR.load()
    for key, rec in reg["briefs"].items():
        if not isinstance(rec, dict) or "creator" not in str(rec.get("type") or "") or not rec.get("brand"):
            continue
        if H.brief_file(dict(rec, id=key), rec["brand"]) and rec.get("product"):
            return H.N.brief_id(key), rec["brand"], rec["product"]
    return None, None, None


BID, BRAND, PRODUCT = creator_brief()


@unittest.skipIf(BID is None, "no creator brief with a brief file on disk")
class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="creators-test-"))
        self.cat = fixture_catalog(self.tmp, BRAND, PRODUCT)
        self.staging = self.tmp / "staging"
        self.ids = self.tmp / "ids.json"
        self.ids.write_text("{}")
        ask = C.brief_ask(BRAND, BID)
        self.cards = write_cards(self.tmp, [
            card("good", gender=None, **{"avatars-fit": [ask["avatar"]] if ask["avatar"] else []}),
            card("robot", kind="ai-character", **{"casting-sheet": "yes", "status": "current"}),
        ])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, who="good"):
        return C.handoff(BRAND, BID, who, staging=self.staging, ids_file=self.ids, online=False,
                         catalog=self.cat, cards_path=self.cards, lane="creator")

    def test_pick_ranks_and_excludes(self):
        res = C.pick(BRAND, BID, lane="creator", cards_path=self.cards)
        self.assertEqual(res["picked"], "good")
        self.assertEqual([e["card"] for e in res["excluded"]], ["robot"])

    def test_handoff_writes_folder_with_draft_not_sent(self):
        root, m, _ = self.make()
        self.assertEqual(m["creator"]["card"], "good")
        self.assertFalse(m["creator"]["sent"])
        self.assertIn("NOT SENT", (root / "references/message-draft.md").read_text())
        self.assertIn("**Cast:**", (root / "handoff.md").read_text())
        self.assertEqual(json.loads((root / "manifest.json").read_text())["creator"]["card"], "good")
        self.assertFalse(m["drive"]["written"], "the creator hand-off is never copied to Drive by this tool")

    def test_handoff_refuses_uncastable_card(self):
        with self.assertRaises(H.Refused):
            self.make("robot")
        with self.assertRaises(H.Refused):
            self.make("nobody")
        self.assertFalse(list(self.staging.rglob("manifest.json")) if self.staging.exists() else [])

    def test_track_waits_then_takes_back_once(self):
        root, m, _ = self.make()
        res = C.track(staging=[self.staging], drive=False)
        row = next(r for r in res["handoffs"] if r["handoff"] == m["name"])
        self.assertEqual(row["status"], "waiting")
        (root / "returned" / f"{BID}_asset-01.mp4").write_bytes(b"x")
        res = C.track(staging=[self.staging], drive=False)
        row = next(r for r in res["handoffs"] if r["handoff"] == m["name"])
        self.assertEqual(row["status"], "footage back")
        self.assertEqual(row["took_back_now"]["files"], 1)
        rows = [json.loads(l) for l in (self.staging / "ledger.jsonl").read_text().splitlines()]
        self.assertEqual([r["verdict"]["event"] for r in rows].count("returned"), 1)
        res = C.track(staging=[self.staging], drive=False)
        row = next(r for r in res["handoffs"] if r["handoff"] == m["name"])
        self.assertIsNone(row["took_back_now"], "nothing new — no second take-back")


if __name__ == "__main__":
    unittest.main()
