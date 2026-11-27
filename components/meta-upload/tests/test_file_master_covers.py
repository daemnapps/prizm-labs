"""The approval-page filing route (feed_video.file_master) carries the covers: the ones the caller passes, else the
Video Studio's cover hand-off for those very masters (briefs/<production>/covers/to-file.json) when it is fresh. A
stale or missing hand-off files no covers and the card's cover check holds it. Everything is written into a temporary
root; no model, no network.

    python3 components/meta-upload/tests/test_file_master_covers.py
"""
import hashlib, json, os, random, shutil, sys, tempfile, time, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import to_check as T  # noqa: E402
import cards as C  # noqa: E402
import feed_video as F  # noqa: E402

VERSIONS = ("control", "H2", "H3")
AD = "acme_widget_brief-0001_batch-2026-11-12-a"


def picture(p, seed):
    from PIL import Image
    rnd = random.Random(seed)
    small = Image.new("L", (9, 16))
    small.putdata([rnd.randrange(256) for _ in range(9 * 16)])
    p.parent.mkdir(parents=True, exist_ok=True)
    small.resize((1080, 1920), Image.NEAREST).convert("RGB").save(p)
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.meta, self.data = self.tmp / "meta", self.tmp / "studio"
        self.index = self.tmp / "index"
        self.index.mkdir()
        (self.index / "covers.json").write_text(json.dumps([{"id": "ig-ABC123"}]))
        self.env = mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(self.meta), "NO_AD_WORDS": "1",
                                                "IMAGE_MADE_LEDGER": str(self.tmp / "made.jsonl"),
                                                "MADE_BY_TOOL_GATE_OFF": "all", "META_COVER_RULE_OFF": "",
                                                "META_COVER_INDEX": str(self.index), "VIDEO_STUDIO_DATA": str(self.data),
                                                "META_FILE_MASTER_COVERS_OFF": ""})
        self.env.start()
        self.copy = mock.patch.object(T, "_copy", lambda s, d, c: shutil.copy2(s, d))
        self.copy.start()
        self.prod = self.data / "briefs" / "acme-ad-1"
        self.videos = []
        for v in VERSIONS:
            f = self.prod / "renders" / f"{v}.mp4"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"video " + v.encode())
            self.videos.append(f)

    def tearDown(self):
        self.copy.stop()
        self.env.stop()
        shutil.rmtree(self.tmp)

    def hand_off(self, held=(), stamps=True, sha=False, running=False):
        """What the studio's cover stage writes: to-file.json and stage.json, a cover and its record per version. `sha`
        adds the video's sha256 to each record, as the image tool's own record carries it."""
        c = self.prod / "covers"
        thumbs, recs, rows = [], [], []
        for i, (v, f) in enumerate(zip(VERSIONS, self.videos)):
            cov = picture(c / "made" / v / f"cover-ad-1-{v}-01.png", v)
            rec = cov.with_suffix(".cover.json")
            frame = {"video": str(f), "t": 1.0, "file": f"{v}-frame.jpg"}
            if sha:
                frame["video_sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
            rec.write_text(json.dumps({"version": v, "swipe": "ig-ABC123", "headline": f"line {v}",
                                       "source_frame": frame}))
            ready = v not in held
            thumbs.append(str(cov) if ready else "")
            recs.append(str(rec) if ready else "")
            st = f.stat()
            rows.append({"version": v, "video": str(f), "ready": ready,
                         **({"video_stamp": {"mtime": st.st_mtime, "size": st.st_size}} if stamps else {})})
        (c / "to-file.json").write_text(json.dumps({"production": "acme-ad-1", "ready": not held and not running,
                                                    **({"running": True} if running else {}),
                                                    "media": [str(f) for f in self.videos], "versions": list(VERSIONS),
                                                    "thumbs": thumbs, "cover_records": recs,
                                                    "held": [{"version": v, "why": "no headline fits"} for v in held]}))
        (c / "stage.json").write_text(json.dumps({"production": "acme-ad-1", "versions": rows}))
        return thumbs

    def file(self, **kw):
        return F.file_master("acme", "brief-0001", "widget", "batch-2026-11-12-a", self.videos, root=str(self.meta),
                             replace=True, **kw)[0]

    def card(self, p):
        return C.load(p["target"])


class ReadsTheStudiosHandOff(Base):
    def test_the_fresh_hand_off_puts_a_cover_on_every_video_with_its_record(self):
        self.hand_off()
        p = self.file()
        c = self.card(p)
        self.assertEqual(len(c["thumbs"]), 3)
        self.assertEqual(sorted(r["swipe"] for r in c["cover_records"].values()), ["ig-ABC123"] * 3)
        self.assertTrue(p["covers_from"].endswith("to-file.json"))
        got = C.checks(p["target"], c, online=False)
        self.assertTrue(all(got[k]["ok"] for k in ("cover_each", "cover_swipe", "cover_frame")), got)

    def test_masters_in_any_order_get_their_own_covers(self):
        self.hand_off()
        self.videos.reverse()
        c = self.card(self.file())
        for i, m in enumerate(c["media"]):
            rec = c["cover_records"][c["thumbs"][m]]
            self.assertEqual(rec["version"], VERSIONS[::-1][i])

    def test_a_hand_off_with_a_held_version_files_no_covers_and_says_why(self):
        self.hand_off(held=("H2",))
        p = self.file()
        self.assertEqual(self.card(p).get("thumbs") or {}, {}, "the other versions' covers wait for the held one")
        self.assertIn("not ready", p["covers_from"])
        self.assertIn("H2: no headline fits", p["covers_from"])
        self.assertFalse(C.checks(p["target"], self.card(p), online=False)["cover_each"]["ok"])

    def test_a_hand_off_whose_run_is_still_going_files_no_covers(self):
        self.hand_off(running=True)
        p = self.file()
        self.assertEqual(self.card(p).get("thumbs") or {}, {})
        self.assertIn("not ready", p["covers_from"])

    def test_a_held_version_leaves_no_covers_on_the_card_so_the_stage_can_finish_it(self):
        """No partial filing: a card carrying the other versions' covers would read as covered, and the held version
        would never get its cover from the machine."""
        self.hand_off(held=("H2",))
        p = self.file()
        self.assertEqual(self.card(p).get("thumbs") or {}, {})
        self.hand_off()
        p = self.file()
        self.assertEqual(len(self.card(p)["thumbs"]), 3)

    def test_a_video_written_after_the_hand_off_is_stale(self):
        self.hand_off()
        later = time.time() + 30
        os.utime(self.videos[1], (later, later))
        p = self.file()
        self.assertEqual(self.card(p).get("thumbs") or {}, {})
        self.assertIn("written after the covers were handed off", p["covers_from"])

    def test_a_video_that_is_not_the_one_its_cover_was_made_from_is_stale(self):
        self.hand_off()
        self.videos[2].write_bytes(b"a new render, longer than the old one")
        old = (self.prod / "covers" / "to-file.json").stat().st_mtime
        os.utime(self.videos[2], (old - 5, old - 5))
        p = self.file()
        self.assertEqual(self.card(p).get("thumbs") or {}, {})
        self.assertIn("not the video its cover was made from", p["covers_from"])

    def test_no_hand_off_for_these_files_files_no_covers(self):
        p = self.file()
        self.assertEqual(self.card(p).get("thumbs") or {}, {})
        self.assertIn("no Video Studio cover hand-off", p["covers_from"])

    def test_the_production_can_be_named(self):
        self.hand_off()
        moved = [self.tmp / "out" / f.name for f in self.videos]
        for a, b in zip(self.videos, moved):
            b.parent.mkdir(exist_ok=True)
            shutil.copy2(a, b)
        self.videos = moved
        self.assertEqual(self.card(self.file()).get("thumbs") or {}, {}, "a copy is not found by its path")
        self.assertEqual(len(self.card(self.file(production="acme-ad-1"))["thumbs"]), 3)

    def test_copied_masters_of_a_named_production_pass_the_frame_check_on_the_videos_sha256(self):
        self.hand_off(sha=True)
        moved = [self.tmp / "out" / f.name for f in self.videos]
        for a, b in zip(self.videos, moved):
            b.parent.mkdir(exist_ok=True)
            shutil.copy2(a, b)
        self.videos = moved
        p = self.file(production="acme-ad-1")
        got = C.checks(p["target"], self.card(p), online=False)
        self.assertTrue(got["cover_frame"]["ok"], got["cover_frame"]["why"])


class TheCallersOwnWin(Base):
    def test_passed_covers_are_used_and_the_hand_off_is_not_read(self):
        self.hand_off()
        mine = [picture(self.tmp / "mine" / f"{v}.png", "mine-" + v) for v in VERSIONS]
        p = self.file(thumbs=mine, cover_records=[{"swipe": "ig-ABC123", "version": v,
                                                    "frame": {"video": str(f), "t": 2}} for v, f in zip(VERSIONS, self.videos)])
        self.assertEqual(p["covers_from"], "passed by the caller")
        recs = self.card(p)["cover_records"].values()
        self.assertEqual({r["frame"]["t"] for r in recs}, {2})


class Switch(Base):
    def test_off_on_one_machine_or_in_the_file(self):
        self.hand_off()
        with mock.patch.dict(os.environ, {"META_FILE_MASTER_COVERS_OFF": "1"}):
            self.assertEqual(self.card(self.file()).get("thumbs") or {}, {})
        with mock.patch.object(F, "HERE", self.tmp):
            (self.tmp / "cover-rule.json").write_text(json.dumps({"to_file": False}))
            self.assertFalse(F.to_file_on())

    def test_shipped_on(self):
        self.assertIs(json.loads((HERE / "cover-rule.json").read_text())["to_file"], True)
        self.assertTrue(F.to_file_on())

    def test_the_ready_part_off_puts_partial_filing_back(self):
        self.hand_off(held=("H2",))
        with mock.patch.dict(os.environ, {"META_FILE_MASTER_COVERS_OFF": "ready"}):
            self.assertTrue(F.to_file_on())
            self.assertEqual(len(self.card(self.file())["thumbs"]), 2)
        with mock.patch.object(F, "HERE", self.tmp):
            (self.tmp / "cover-rule.json").write_text(json.dumps({"to_file": True, "to_file_ready": False}))
            self.assertFalse(F.needs_ready())

    def test_shipped_files_only_a_ready_hand_off(self):
        self.assertIs(json.loads((HERE / "cover-rule.json").read_text())["to_file_ready"], True)
        self.assertTrue(F.needs_ready())


if __name__ == "__main__":
    unittest.main()
