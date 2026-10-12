"""The budget (2026-10-02): what a brief will likely cost before anything is
spent. A made-up two-person run and a made-up rate sheet — no model, no
network, no real run."""
import io
import json
import os
import tempfile
from datetime import datetime, timezone
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import budget as bd

REG = {
    "credits_per_dollar": {"higgsfield": 20},
    "doors": {"still": {"model": "img-model"}},
    "direct": {"openai": {"params": {"size": "1024x1536", "output_format": "png"},
                          "proven": {"img-model": "first live generation, sharp on 2,000 tokens vs 5,000"}},
               "google": {"image_model": "other-img"}},
    "models": {
        "img-model": {"provider": "openai", "station": "still",
                      "rates": [{"tier": "xhigh", "usd_per_m_in": 8, "usd_per_m_out": 30, "read": "2026-10-02"}]},
        "other-img": {"provider": "google", "station": "edit", "rates": [{"usd_per_job": 0.1, "read": "2026-10-02"}]},
        "seedance_2_5": {"provider": "higgsfield", "max_seconds": 30, "rates": [
            {"tier": "high", "resolution": "720p", "credits_per_second": 7, "read": "2026-10-02"},
            {"tier": "high", "resolution": "1080p", "credits_per_second": 12, "read": "2026-09-22"}]},
        "minimax_h3": {"provider": "higgsfield", "max_seconds": 15, "min_seconds": 4, "rates": [
            {"tier": "std", "resolution": "2K", "credits_per_second": 2, "read": "2026-09-22"}]},
        "elevenlabs": {"provider": "elevenlabs", "rates": []},
    },
}

SCENES = [
    {"id": "S1", "who": "HOST", "to_camera": True, "voice": "hello there friends"},
    {"id": "S2", "who": "HOST's hands", "to_camera": False, "voice": "we press it here"},
    {"id": "S3", "kind": "card", "to_camera": False, "voice": ""},
]

SB = {"sections": [
    {"id": "G01", "scenes": ["S1"], "maker": "lip-sync", "frames": [{"what": "start frame", "from": "S1"}],
     "clips": [{"scenes": ["S1"], "seconds": 7.6}], "voice": {"S1": 7.6}},
    {"id": "G02", "scenes": ["S2"], "maker": "motion transfer",
     "frames": [{"what": "start frame · set-up shot", "from": "S2", "copies": "K02", "own": False}],
     "clips": [{"scenes": ["S2"], "seconds": 5.72}], "voice": {"S2": 5.72}, "swipe": {"shots": []}},
    {"id": "G03", "scenes": ["S3"], "maker": "plate", "frames": [{"what": "card background", "from": "S3"}],
     "clips": [], "voice": {}},
    {"id": "G04", "scenes": ["S2"], "maker": "motion transfer", "reuses": "G02", "frames": [], "clips": [], "voice": {}},
]}

PNG = b"\x89PNG\r\n\x1a\n"
JPG = b"\xff\xd8\xff\xe0"


class Budget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / "demo-run"
        self.run.mkdir()
        (self.run / "plan.json").write_text(json.dumps({"scenes": SCENES}))
        (self.run / "lines.json").write_text(json.dumps({"S1": "a" * 600, "S2": "b" * 400}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_image_input_tokens(self):
        # 1024x1536 → short side 768 → 768x1152 → 2 x 3 tiles → 65 + 6 x 129
        self.assertEqual(bd.image_input_tokens(1024, 1536), 839)
        self.assertEqual(bd.image_input_tokens(512, 512), 65 + 4 * 129)

    def test_billed_seconds(self):
        sd, mm = REG["models"]["seedance_2_5"], REG["models"]["minimax_h3"]
        self.assertEqual(bd.billed(1.69, sd, "motion", "seedance_2_5"), [4])
        self.assertEqual(bd.billed(7.6, sd, "talking", "seedance_2_5"), [8])
        self.assertEqual(bd.billed(19.09, mm, "talking", "minimax_h3"), [10, 10])

    def test_counts_pictures_and_clips(self):
        n = bd.count(SB, SCENES)
        self.assertEqual(n["pictures"], ["S1-F1", "S2-F1", "S3-PLATE"])     # the reused section is not made twice
        self.assertEqual([(c["seconds"], c["talking"]) for c in n["clips"]], [(7.6, True), (5.72, False)])

    def test_clip_options_and_totals(self):
        b = bd.budget(self.run, SB, REG)
        price = {o["name"]: o["price"] for o in b["options"]}
        self.assertEqual(price["Seedance 2.5 · 720p"]["credits"], 8 * 7 + 6 * 7)
        self.assertEqual(price["Seedance 2.5 · 1080p"]["credits"], 8 * 12 + 6 * 12)
        self.assertEqual(price["MiniMax H3 · 2K"]["credits"], 8 * 2 + 6 * 2)
        mixed = next(v for k, v in price.items() if k.startswith("Mixed"))
        self.assertEqual(mixed["credits"], 8 * 2 + 6 * 7)                    # talking on MiniMax, motion on Seedance
        ruled = next(o for o in b["options"] if o["ruled"])
        self.assertEqual(b["lines"]["likely"]["clips"], round(ruled["price"]["usd"] * bd.CLIP_TRIES["likely"], 2))
        # the picture: prompt + refs in at $8/M, 2,000 out at $30/M (read off the note)
        want = round((bd.PROMPT_TOKENS["likely"] + bd.REFS_DEFAULT["likely"] * 839) / 1e6 * 8 + 2000 / 1e6 * 30, 4)
        self.assertEqual(b["picture"]["likely"], want)
        self.assertAlmostEqual(b["lines"]["likely"]["pictures"], 3 * bd.PICTURE_TRIES["likely"] * want, places=2)
        # voices: 1,000 characters at the research fallback rate
        self.assertEqual(b["chars"], 1000)
        self.assertAlmostEqual(b["lines"]["low"]["voices"], 0.10, places=2)
        lo, li, hi = (b["lines"][x]["total"] for x in bd.LEVELS)
        self.assertTrue(lo < li < hi)

    def test_the_omni_route_is_the_ruled_door_when_it_is_the_clips_default(self):
        """3 Oct: clips are Omni on fal at 1080p (providers.json direct.omni_route)."""
        reg = json.loads(json.dumps(REG))
        reg["direct"]["omni_route"] = {"default_for_clips": True, "resolution": "1080p",
                                       "usd_per_s": {"360p": 0.03, "1080p": 0.15}, "seconds_range": [3, 10]}
        b = bd.budget(self.run, SB, reg)
        ruled = [o for o in b["options"] if o["ruled"]]
        self.assertEqual([o["name"] for o in ruled], ["Omni Flash · 1080p (fal)"])
        self.assertEqual(ruled[0]["price"]["seconds"], 8 + 6)                  # 7.6 s → 8, 5.72 s → 6
        self.assertEqual(ruled[0]["price"]["usd"], round((8 + 6) * 0.15, 2))
        self.assertEqual(bd.omni_billed(19.09, [3, 10]), [10, 10])
        self.assertEqual(bd.omni_billed(1.2, [3, 10]), [3])

    def test_real_ledger_usd_becomes_likely(self):
        (self.run / "ledger.json").write_text(json.dumps([
            {"model": "img-model", "usd": 0.2, "tokens": {"in": 1, "out": 1}, "at": "2026-10-02T05:00:00+00:00"},
            {"model": "img-model", "usd": 0.1, "tokens": {"in": 1, "out": 1}, "at": "2026-10-02T05:01:00+00:00"}]))
        p = bd.picture_usd(REG, self.run)
        self.assertEqual(p["likely"], 0.15)
        self.assertEqual(p["measured"], 2)

    def test_refs_from_element_refs(self):
        (self.run / "element-refs.json").write_text(json.dumps({"S1-F1": [1, 2, 3], "S2-F1": [1, 2, 3, 4, 5]}))
        self.assertEqual(bd.refs_per_picture(self.run), {"low": 4, "likely": 5.0, "high": 6})

    def test_spent_counts_ledger_and_late_files(self):
        led = [{"model": "img-model", "at": "2026-10-02T05:00:00+00:00"} for _ in range(3)] + \
              [{"model": "other-img", "at": "2026-10-02T05:30:00+00:00"}]
        (self.run / "ledger.json").write_text(json.dumps(led))
        media = self.run / "media" / "versions"
        media.mkdir(parents=True)
        end = datetime(2026, 10, 2, 5, 30, tzinfo=timezone.utc).timestamp()
        for i in range(2):                                   # inside the ledger's time
            f = media / f"in-{i}.png"; f.write_bytes(PNG + bytes([i])); os.utime(f, (end - 600, end - 600))
        late = media / "late-fix.png"; late.write_bytes(PNG + b"late"); os.utime(late, (end + 3600, end + 3600))
        shaped = media / "late-fix-shaped.png"; shaped.write_bytes(PNG + b"shp"); os.utime(shaped, (end + 3600, end + 3600))
        for i in range(2):
            f = media / f"g-{i}.png"; f.write_bytes(JPG + bytes([i])); os.utime(f, (end - 600, end - 600))
        (self.run / "vo").mkdir()
        (self.run / "vo" / "skip.png").write_bytes(PNG + b"vo")   # not a picture of the run
        s = bd.spent(self.run, REG, {"low": 0.1, "high": 0.2})
        self.assertEqual(s["img-model"]["calls"], (4, 4))        # 3 logged + 1 made after; the reshape is no call
        self.assertEqual(s["img-model"]["usd"], (0.4, 0.8))
        self.assertEqual(s["other-img"]["calls"], (1, 2))        # 1 logged, 2 files on disk
        self.assertEqual(s["other-img"]["usd"], (0.1, 0.2))

    def test_write_page_and_line(self):
        (self.run / "storyboard.json").write_text(json.dumps(SB))
        with redirect_stdout(io.StringIO()):
            b = bd.write(self.run, reg=REG)
        page = (self.run / "BUDGET.md").read_text()
        for want in ("| **Total** |", "← the ruled door", "## Assumptions", "Mixed — MiniMax", "At scale"):
            self.assertIn(want, page)
        self.assertTrue(b["line"].startswith("budget: $"))
        self.assertIn("likely", b["line"])
        self.assertNotIn("Rough", page)

    def test_rough_from_the_brief_alone(self):
        brief = self.run / "brief.md"
        sc = [dict(s, seconds=s.get("seconds", 5.0)) for s in SCENES]
        brief.write_text("# brief\n\n```json\n" + json.dumps({"scenes": sc}) + "\n```\n")
        (self.run / "plan.json").unlink()
        b = bd.budget(self.run, None, REG, brief=brief)
        self.assertTrue(b["rough"])
        self.assertEqual(len(b["count"]["pictures"]), 3)
        self.assertEqual(len(b["count"]["clips"]), 2)             # the card gets a picture, no clip
        self.assertIn("Rough", bd.markdown(b))


if __name__ == "__main__":
    unittest.main()
