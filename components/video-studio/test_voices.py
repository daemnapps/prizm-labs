"""voices.py: every speaking role takes the voice set for its demographic (rule 2026-11-12)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voices as VO  # noqa: E402

ROWS = {"male/25-34/black": {"voice_id": "A" * 20, "name": "M", "model": "m2", "settings": {"speed": 1.2}},
        "female/25-34/black": {"voice_id": "B" * 20, "name": "F"}}


class Voices(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._briefs, self._reg = VO.ST.BRIEFS, VO.registry
        VO.ST.BRIEFS = self.tmp
        VO.registry = lambda brand: ROWS if brand == "acme" else {}
        b = self.tmp / "p1"
        (b / "voice").mkdir(parents=True)
        (b / "scenes" / "S1").mkdir(parents=True)
        json.dump({"brief_key": "acme_widget_brief-0001", "audience": {"face": "male/25-34/black"},
                   "order": ["S1"], "picks": {"S1": "take-1"}}, open(b / "brief.json", "w"))
        json.dump({"voice_id": "C" * 20, "lines": {}}, open(b / "voice" / "reads.json", "w"))
        json.dump({"steps": [{"tool": "gen.take", "params": {
            "cast": {"HOST": {"voice": "old host"}, "RATER": {"voice": "old rater"}},
            "script": [{"speaker": "HOST", "say": "hi"}, {"speaker": "RATER", "say": "no"}]}}]},
            open(b / "scenes" / "S1" / "take-1.json", "w"))

    def tearDown(self):
        VO.ST.BRIEFS, VO.registry = self._briefs, self._reg

    def test_face_from_a_library_path(self):
        self.assertEqual(VO.norm_face("/content-creators/male/black/25-34/devonte/"), "male/25-34/black")

    def test_no_voice_set_is_refused_by_name(self):
        with self.assertRaises(VO.NoVoice):
            VO.voice_for("acme", "female/45-54/asian", "RATER")

    def test_a_copied_production_never_keeps_its_old_voices(self):
        self.assertFalse(all(r["ok"] for r in VO.report("p1").values()))
        VO.apply("p1", {"HOST": "male/25-34/black", "RATER": "female/25-34/black"})
        rep = VO.report("p1")
        self.assertEqual(set(rep), {"narrator", "S1 HOST", "S1 RATER"})
        self.assertTrue(all(r["ok"] for r in rep.values()), rep)
        reads = json.load(open(self.tmp / "p1" / "voice" / "reads.json"))
        self.assertEqual((reads["voice_id"], reads["model"]), ("A" * 20, "m2"))


    def test_a_chain_made_ad_wants_its_speakers_banked_voice(self):
        # owner, 2026-11-20: a character speaks in their own saved voice; 2026-11-21 (brief-0380): the check wanted a
        # demographic stock voice for the speaker's reads
        from unittest import mock
        import chain_view as CV
        b = json.load(open(self.tmp / "p1" / "brief.json"))
        b["lane"] = "ai"
        json.dump(b, open(self.tmp / "p1" / "brief.json", "w"))
        with mock.patch.object(CV, "speaker_voice", lambda brief: {"voice_id": "C" * 20, "voice": "yai", "from": "x"}):
            rep = VO.report("p1")
        self.assertEqual((rep["narrator"]["wants"], rep["narrator"]["ok"]), ("C" * 20, True))


if __name__ == "__main__":
    unittest.main()
