"""The cover rule as card checks (cover_rule.py): a waiting video card is held until every video has its own cover,
each cover's record names the swipe it follows and a frame of its own video, and no two covers are the same picture.
A card already approved or live is never checked. Everything is written into a temporary root; no model, no network.

    python3 components/meta-upload/tests/test_cover_rule.py
"""
import json, os, random, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import to_check as T  # noqa: E402
import cards as C  # noqa: E402
import cover_rule as CR  # noqa: E402
import made_by_tool as MBT  # noqa: E402

AD = "acme_widget_brief-0001_batch-2026-11-12-%s"
WORDS = {"primary": ["Body"], "headlines": ["H"], "descriptions": ["D"]}
VERSIONS = ("control", "H2", "H3")
SWIPES = ["ig-ABC123", "tt-XYZ789", "ig-DICT", "tt-FILE", "ig-ROW", "ig-SHA1", "ig-LEDGER", "ig-RUN1"]


def cover(p, seed, size=(1080, 1920)):
    """A 9:16 picture of big blocks; a different seed is a different picture, the same seed the same one."""
    from PIL import Image
    rnd = random.Random(seed)
    small = Image.new("L", (9, 16))
    small.putdata([rnd.randrange(256) for _ in range(9 * 16)])
    p.parent.mkdir(parents=True, exist_ok=True)
    small.resize(size, Image.NEAREST).convert("RGB").save(p)
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.meta = self.tmp / "meta"
        self.index = self.tmp / "index"
        self.index.mkdir()
        (self.index / "covers.json").write_text(json.dumps([{"id": s, "platform": s[:2]} for s in SWIPES]))
        self.env = mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(self.meta), "NO_AD_WORDS": "1",
                                                "IMAGE_MADE_LEDGER": str(self.tmp / "made.jsonl"),
                                                "MADE_BY_TOOL_GATE_OFF": "all", "META_COVER_RULE_OFF": "",
                                                "META_COVER_INDEX": str(self.index)})
        self.env.start()
        self.copy = mock.patch.object(T, "_copy", lambda s, d, c: shutil.copy2(s, d))   # no ffmpeg on stand-in videos
        self.copy.start()
        self.renders = self.tmp / "renders"
        self.renders.mkdir()
        self.videos = []
        for v in VERSIONS:
            f = self.renders / f"{v}.mp4"
            f.write_bytes(b"video " + v.encode())
            self.videos.append(f)

    def tearDown(self):
        self.copy.stop()
        self.env.stop()
        shutil.rmtree(self.tmp)

    def record(self, v, swipe="ig-ABC123", t=1.5, **over):
        """A cover's record as the makers write it: the frame's video by its full path."""
        return {"version": v, "swipe": swipe, "headline": f"line for {v}",
                "frame": {"video": str(self.renders / f"{v}.mp4"), "t": t, "file": f"{v}_frame.jpg"}, **over}

    def covers(self, records=True, seeds=None):
        out = []
        for i, v in enumerate(VERSIONS):
            c = cover(self.renders / f"{v}_cover.jpg", (seeds or VERSIONS)[i])
            if records:
                c.with_suffix(".cover.json").write_text(json.dumps(self.record(v)))
            out.append(c)
        return out

    def file(self, thumbs=None, lane="video", batch="a", **kw):
        return T.to_check("acme", lane, "flexible", self.videos, WORDS, [], None, ad_name=AD % batch,
                          product="widget", root=str(self.meta), thumbs=thumbs, **kw)

    def checks(self, p):
        return CR.checks(p["target"], C.load(p["target"]))


class EveryVideoHasACover(Base):
    def test_a_video_card_with_no_covers_is_not_ready_and_says_why(self):
        p = self.file()
        got = C.checks(p["target"], C.load(p["target"]), online=False)
        self.assertFalse(got["cover_each"]["ok"])
        why = got["cover_each"]["why"]
        self.assertIn("3 of 3 video(s) with no cover", why)
        self.assertIn("asset-01", why)
        self.assertIn("make.py --purpose cover", why)
        self.assertTrue(got["cover_swipe"]["ok"] and got["cover_frame"]["ok"] and got["cover_differs"]["ok"])

    def test_a_card_missing_one_cover_names_the_video(self):
        c = self.covers()
        got = self.checks(self.file(thumbs=[c[0], None, c[2]]))
        self.assertFalse(got["cover_each"]["ok"])
        self.assertIn("1 of 3", got["cover_each"]["why"])
        self.assertIn("asset-02", got["cover_each"]["why"])
        self.assertNotIn("asset-01", got["cover_each"]["why"])

    def test_a_cover_for_every_video_passes_all_four(self):
        got = self.checks(self.file(thumbs=self.covers()))
        self.assertEqual({k: v["ok"] for k, v in got.items()}, {k: True for k in CR.KEYS}, got)

    def test_the_filing_says_what_holds_the_card(self):
        p = self.file()
        self.assertFalse(p["cover_checks"]["cover_each"]["ok"])
        self.assertIn("NOT READY — A cover for every video", T.show(p))

    def test_a_card_already_approved_or_live_is_left_alone(self):
        p = self.file()
        for state in ("2-approved", "3-live"):
            dest = self.meta / "acme" / state / "video" / p["target"].name
            dest.parent.mkdir(parents=True)
            shutil.copytree(p["target"], dest)
            got = C.checks(dest, C.load(dest), online=False)
            self.assertEqual([k for k in got if k.startswith("cover_")], [], state)
            self.assertTrue(got["thumbs"]["ok"])

    def test_pictures_and_other_lanes_are_not_checked(self):
        p = T.to_check("acme", "image", "flexible", [cover(self.tmp / "a.png", 1)], WORDS, [], None,
                       ad_name=AD % "b", product="widget", root=str(self.meta))
        self.assertEqual(self.checks(p), {})
        self.assertEqual(self.checks(self.file(lane="creator", batch="c")), {})


class Switch(Base):
    def test_off_in_the_file_or_the_environment(self):
        p = self.file()
        with mock.patch.object(CR, "conf", lambda: {"on": False}):
            self.assertEqual(self.checks(p), {})
        with mock.patch.dict(os.environ, {"META_COVER_RULE_OFF": "all"}):
            self.assertEqual(self.checks(p), {})
            self.assertEqual([k for k in C.checks(p["target"], C.load(p["target"]), online=False) if k.startswith("cover_")], [])

    def test_one_check_off_leaves_the_rest(self):
        p = self.file()
        with mock.patch.dict(os.environ, {"META_COVER_RULE_OFF": "cover_each"}):
            self.assertEqual(sorted(self.checks(p)), ["cover_differs", "cover_frame", "cover_swipe"])
        with mock.patch.object(CR, "conf", lambda: {"on": True, "checks": {"cover_differs": False}, "lanes": {"video": True}}):
            self.assertNotIn("cover_differs", self.checks(p))
            self.assertIn("cover_each", self.checks(p))

    def test_a_lane_is_checked_only_when_the_switch_names_it(self):
        p = self.file(lane="creator")
        with mock.patch.object(CR, "conf", lambda: {"on": True, "lanes": {"video": False, "creator": True}}):
            self.assertFalse(self.checks(p)["cover_each"]["ok"])
            self.assertEqual(self.checks(self.file(batch="b")), {})

    def test_cards_filed_before_since_are_left_as_filed(self):
        p = self.file()
        with mock.patch.object(CR, "conf", lambda: {"on": True, "lanes": {"video": True}, "since": "2999-01-01T00:00:00"}):
            self.assertEqual(self.checks(p), {})

    def test_the_shipped_switch_file_is_on_for_the_video_lane(self):
        c = json.loads(CR.CONF.read_text())
        self.assertIs(c["on"], True)
        self.assertEqual(c["checks"], {k: True for k in CR.KEYS})
        self.assertEqual(c["lanes"], {"video": True, "creator": False})


class TheRecordNamesTheSwipe(Base):
    def test_a_cover_with_no_record_fails_and_names_the_video(self):
        got = self.checks(self.file(thumbs=self.covers(records=False)))
        self.assertTrue(got["cover_each"]["ok"])
        self.assertFalse(got["cover_swipe"]["ok"])
        self.assertIn("asset-01: its cover's record names no swipe", got["cover_swipe"]["why"])

    def test_a_placeholder_is_not_a_swipe(self):
        c = self.covers()
        c[1].with_suffix(".cover.json").write_text(json.dumps(self.record("H2", swipe="none")))
        got = self.checks(self.file(thumbs=c))
        self.assertFalse(got["cover_swipe"]["ok"])
        self.assertIn("asset-02", got["cover_swipe"]["why"])
        self.assertNotIn("asset-01", got["cover_swipe"]["why"])

    def test_the_pass_line_lists_the_swipes(self):
        c = self.covers()
        c[2].with_suffix(".cover.json").write_text(json.dumps(self.record("H3", swipe="tt-XYZ789")))
        why = self.checks(self.file(thumbs=c))["cover_swipe"]["why"]
        self.assertIn("ig-ABC123", why)
        self.assertIn("tt-XYZ789", why)


class TheRecordNamesAFrameOfItsOwnVideo(Base):
    def test_no_frame_fails(self):
        c = self.covers()
        c[0].with_suffix(".cover.json").write_text(json.dumps({"swipe": "ig-ABC123", "version": "control"}))
        got = self.checks(self.file(thumbs=c))
        self.assertTrue(got["cover_swipe"]["ok"])
        self.assertFalse(got["cover_frame"]["ok"])
        self.assertIn("asset-01: its cover's record names no source frame", got["cover_frame"]["why"])

    def test_a_frame_from_another_version_fails_and_names_both(self):
        c = self.covers()
        c[1].with_suffix(".cover.json").write_text(json.dumps(
            self.record("H2", frame={"video": str(self.renders / "control.mp4"), "t": 2})))
        got = self.checks(self.file(thumbs=c))
        self.assertFalse(got["cover_frame"]["ok"])
        self.assertIn("asset-02: its cover's frame is from control.mp4, not from its own video", got["cover_frame"]["why"])

    def test_the_card_names_the_frame_by_the_cards_own_video_name(self):
        p = self.file(thumbs=self.covers())
        c = C.load(p["target"])
        for v, t in c["thumbs"].items():
            fr = c["cover_records"][t]["frame"]
            self.assertEqual(fr["video"], v)
            self.assertEqual(fr["t"], 1.5)
        self.assertEqual(c["cover_records"][c["thumbs"][c["media"][1]]]["frame"]["source"], "H2.mp4")

    def test_a_plain_frame_path_counted_by_version_only_when_rolled_back_to_names(self):
        c = self.covers()
        c[1].with_suffix(".cover.json").write_text(json.dumps(
            {"swipe": "ig-ABC123", "version": "H2", "frame": "/somewhere/H2_frame.jpg"}))
        with mock.patch.object(CR, "conf", lambda: {"on": True, "lanes": {"video": True}, "frame_check": "name"}):
            self.assertTrue(self.checks(self.file(thumbs=c))["cover_frame"]["ok"])
            c[1].with_suffix(".cover.json").write_text(json.dumps(
                {"swipe": "ig-ABC123", "version": "H9", "frame": "/somewhere/H9_frame.jpg"}))
            self.assertFalse(self.checks(self.file(thumbs=c, replace=True))["cover_frame"]["ok"])

    def test_a_frame_at_second_zero_is_a_frame(self):
        c = self.covers()
        c[0].with_suffix(".cover.json").write_text(json.dumps(
            self.record("control", frame={"video": str(self.renders / "control.mp4"), "t": 0})))
        self.assertTrue(self.checks(self.file(thumbs=c))["cover_frame"]["ok"])


class TheFrameIsProvedToBeFromItsOwnVideo(Base):
    """A record proves its video by the video's sha256, or by a path that is the filed file; a same-named video of
    another ad, or a version id alone, proves nothing."""

    def other_ad(self, name="H2.mp4"):
        f = self.tmp / "elsewhere" / "adB" / "renders" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"another ad's video")
        return f

    def one(self, frame, v="H2", **rec):
        c = self.covers()
        c[1].with_suffix(".cover.json").write_text(json.dumps(self.record(v, frame=frame, **rec)))
        return self.checks(self.file(thumbs=c, replace=True))["cover_frame"]

    def test_case_a_another_ads_same_named_video_fails(self):
        got = self.one({"video": str(self.other_ad()), "t": 1.5, "file": "H2_frame.jpg"})
        self.assertFalse(got["ok"])
        self.assertIn("asset-02: its cover's frame is from H2.mp4, not from its own video", got["why"])

    def test_a_path_to_no_file_fails(self):
        self.assertFalse(self.one({"video": "/nowhere/adA/renders/H2.mp4", "t": 1.5})["ok"])

    def test_case_c_a_version_id_and_a_frame_alone_fail(self):
        c = self.covers()
        c[1].with_suffix(".cover.json").write_text(json.dumps(
            {"swipe": "ig-ABC123", "version": "H2", "frame": "/somewhere/H2_frame.jpg"}))
        got = self.checks(self.file(thumbs=c))["cover_frame"]
        self.assertFalse(got["ok"])
        self.assertIn("asset-02", got["why"])

    def test_the_full_path_of_its_own_video_or_its_clean_twin_passes(self):
        self.assertTrue(self.one({"video": str(self.renders / "H2.mp4"), "t": 1.5})["ok"])
        twin = self.renders / "H2.clean.mp4"
        twin.write_bytes(b"H2 without words")
        self.assertTrue(self.one({"video": str(twin), "t": 1.5})["ok"])

    def test_a_relative_path_is_read_from_the_covers_own_folder(self):
        self.assertTrue(self.one({"video": "../renders/H2.mp4", "t": 1.5})["ok"])
        self.assertFalse(self.one({"video": "../elsewhere/H2.mp4", "t": 1.5})["ok"])

    def test_the_videos_sha256_decides(self):
        sha = MBT.pv().sha256
        self.assertTrue(self.one({"video": "H2.mp4", "video_sha256": sha(self.renders / "H2.mp4"), "t": 1})["ok"])
        twin = self.renders / "H2.clean.mp4"
        twin.write_bytes(b"H2 without words")
        self.assertTrue(self.one({"video": str(twin), "video_sha256": sha(twin), "t": 1})["ok"])
        got = self.one({"video": "H2.mp4", "video_sha256": sha(self.other_ad()), "t": 1})
        self.assertFalse(got["ok"])

    def test_rolled_back_to_names_the_old_reading_holds(self):
        with mock.patch.object(CR, "conf", lambda: {"on": True, "lanes": {"video": True}, "frame_check": "name"}):
            self.assertTrue(self.one({"video": str(self.other_ad()), "t": 1.5})["ok"])

    def test_the_shipped_switch_proves_the_video(self):
        self.assertEqual(json.loads(CR.CONF.read_text())["frame_check"], "own-video")


class ABareFileNameIsNoProof(Base):
    """A record that names its video by file name only (no folder, no video_sha256) proves no video: another ad's
    control.mp4 has the same name."""

    def one(self, frame, i=1):
        c = self.covers()
        c[i].with_suffix(".cover.json").write_text(json.dumps(self.record(VERSIONS[i], frame=frame)))
        return self.checks(self.file(thumbs=c, replace=True))["cover_frame"]

    def test_the_same_file_name_from_another_ad_fails_and_says_why(self):
        got = self.one({"video": "H2.mp4", "t": 1.5, "file": "H2_frame.jpg"})
        self.assertFalse(got["ok"])
        self.assertIn("asset-02: its cover's record names its video by file name only (H2.mp4)", got["why"])

    def test_the_cards_own_file_name_alone_fails(self):
        self.assertFalse(self.one({"video": "control.mp4", "t": 1.5}, i=0)["ok"])
        self.assertFalse(self.one({"video": "asset-01.mp4", "t": 1.5}, i=0)["ok"])

    def test_a_bare_name_with_the_videos_sha256_passes(self):
        sha = MBT.pv().sha256(self.renders / "H2.mp4")
        self.assertTrue(self.one({"video": "H2.mp4", "video_sha256": sha, "t": 1.5})["ok"])

    def test_rolled_back_a_bare_name_is_read_as_before(self):
        with mock.patch.object(CR, "conf", lambda: {"on": True, "lanes": {"video": True}, "bare_name": True}):
            self.assertTrue(self.one({"video": "H2.mp4", "t": 1.5})["ok"])
            self.assertFalse(self.one({"video": "H3.mp4", "t": 1.5})["ok"])

    def test_the_shipped_switch_refuses_a_bare_name(self):
        self.assertIs(json.loads(CR.CONF.read_text())["bare_name"], False)


class TheImageToolsRecordIsMatchedOnItsVideoSha256(Base):
    """The image tool's own `<cover>.cover.json` (its `source_frame` carries the video's full path and `video_sha256`):
    the sha256 decides, wherever the path points, so a master copied to another folder still proves its cover."""

    def tool_record(self, v, video, digest):
        return {"ad": "acme-brief-1", "version": v, "headline": f"line for {v}", "swipe": "ig-ABC123", "base": "frame",
                "source_frame": {"file": str(self.tmp / "studio" / f"{v}-frame.png"), "video": str(video),
                                 "video_sha256": digest, "t": 2.0, "sha256": "f" * 64, "size": [1080, 1920]},
                "set": {"name": "kitchen-set", "print": "/sets/kitchen-set/print-v1.png", "sha256": "e" * 64},
                "words": {"box_px": [100, 1500, 980, 1700]}, "product": None,
                "file": "cover-01.png", "sha256": "d" * 64, "problems": [], "ok": True}

    def one(self, digest_of, said=None):
        studio = self.tmp / "studio" / "H2.mp4"                # the render the cover was made from, in another folder
        studio.parent.mkdir(parents=True, exist_ok=True)
        studio.write_bytes((self.renders / "H2.mp4").read_bytes())
        c = self.covers()
        sha = MBT.pv().sha256
        c[1].with_suffix(".cover.json").write_text(json.dumps(self.tool_record("H2", said or studio, sha(digest_of))))
        p = self.file(thumbs=c, replace=True)
        return self.checks(p)["cover_frame"], C.load(p["target"])

    def test_a_copy_of_the_master_in_another_folder_passes_by_sha256(self):
        got, card = self.one(self.renders / "H2.mp4")
        self.assertTrue(got["ok"], got["why"])
        rec = card["cover_records"][card["thumbs"][card["media"][1]]]
        self.assertEqual(rec["frame"]["video_sha256"], MBT.pv().sha256(self.renders / "H2.mp4"))
        self.assertEqual(rec["frame"]["video"], card["media"][1])

    def test_the_sha256_of_another_video_fails_even_with_the_right_path(self):
        other = self.tmp / "elsewhere" / "H2.mp4"
        other.parent.mkdir(parents=True)
        other.write_bytes(b"another ad's video")
        got, _ = self.one(other, said=self.renders / "H2.mp4")
        self.assertFalse(got["ok"])


class TheSwipeIsARowOfTheCoverIndex(Base):
    def one(self, swipe):
        c = self.covers()
        c[1].with_suffix(".cover.json").write_text(json.dumps(self.record("H2", swipe=swipe)))
        return self.checks(self.file(thumbs=c, replace=True))["cover_swipe"]

    def test_placeholders_fail_by_name(self):
        for s in ("?", "x", "swipe", "none.", "ig-?"):
            got = self.one(s)
            self.assertFalse(got["ok"], s)
            self.assertIn(f'"{s}", a placeholder', got["why"])
            self.assertIn("asset-02", got["why"])

    def test_an_id_not_in_the_index_fails_with_its_name(self):
        got = self.one("ig-NOTHERE9")
        self.assertFalse(got["ok"])
        self.assertIn("swipe ig-NOTHERE9 is not in the cover index", got["why"])

    def test_an_id_in_the_index_passes(self):
        self.assertTrue(self.one("tt-XYZ789")["ok"])

    def test_the_index_decides_whatever_the_ids_shape(self):
        (self.index / "covers.json").write_text(json.dumps([{"id": i} for i in SWIPES + ["sw-odd"]]))
        self.assertTrue(self.one("sw-odd")["ok"])

    def test_no_index_on_the_machine_holds_and_says_so(self):
        with mock.patch.dict(os.environ, {"META_COVER_INDEX": str(self.tmp / "none")}):
            got = self.one("tt-XYZ789")
        self.assertFalse(got["ok"])
        self.assertIn("the cover index is not on this machine", got["why"])

    def test_the_shipped_index_is_the_team_cover_index(self):
        with mock.patch.dict(os.environ, {"META_COVER_INDEX": ""}):
            self.assertEqual(CR.index_file(), REPO / "runs/asset-index/swipes/covers/covers.json")
        c = json.loads(CR.CONF.read_text())
        self.assertEqual((c["swipe_check"], c["swipe_index"]), ("index", "runs/asset-index/swipes/covers"))

    def test_rolled_back_to_names_any_name_passes(self):
        with mock.patch.object(CR, "conf", lambda: {"on": True, "lanes": {"video": True}, "swipe_check": "named"}):
            self.assertTrue(self.one("x")["ok"])
            self.assertFalse(self.one("none")["ok"])


class WhereTheRecordIsRead(Base):
    def one(self, **kw):
        c = self.covers(records=False)
        p = self.file(thumbs=c, **kw)
        card = C.load(p["target"])
        return card.get("cover_records") or {}, card, c

    def test_passed_to_the_filer_as_dicts_or_files(self):
        f = self.tmp / "h2.json"
        f.write_text(json.dumps(self.record("H2", swipe="tt-FILE")))
        recs, card, _ = self.one(cover_records=[self.record("control", swipe="ig-DICT"), str(f), None])
        t = [card["thumbs"][m] for m in card["media"]]
        self.assertEqual((recs[t[0]]["swipe"], recs[t[1]]["swipe"]), ("ig-DICT", "tt-FILE"))
        self.assertNotIn(t[2], recs)

    def test_the_run_record_beside_the_cover(self):
        c = self.covers(records=False)
        (self.renders / "run.json").write_text(json.dumps({"machine": "image-production", "pictures": [
            {"file": c[0].name, "cover": self.record("control", swipe="ig-ROW")},
            {"file": "x.png", "sha256": MBT.pv().sha256(c[1]), "cover": self.record("H2", swipe="ig-SHA")}]}))
        p = self.file(thumbs=c)
        card = C.load(p["target"])
        t = [card["thumbs"][m] for m in card["media"]]
        self.assertEqual(card["cover_records"][t[0]]["swipe"], "ig-ROW")
        self.assertEqual(card["cover_records"][t[1]]["swipe"], "ig-SHA")
        self.assertTrue(card["cover_records"][t[0]]["record"].endswith("run.json"))

    def test_a_run_record_for_one_cover(self):
        d = self.tmp / "cover-run" / "out"
        c = cover(d / "cover.png", "solo")
        (d.parent / "run.json").write_text(json.dumps({"machine": "image-production", "purpose": "cover",
                                                       "cover": self.record("control", swipe="ig-RUN")}))
        rec, where = CR.read_record(c)
        self.assertEqual(rec["swipe"], "ig-RUN")
        self.assertEqual(Path(rec["frame"]["video"]).name, "control.mp4")

    def test_the_tools_ledger_line(self):
        c = self.covers(records=False)
        MBT.pv().stamp(c[2], "engine", purpose="cover", **self.record("H3", swipe="ig-LEDGER"))
        p = self.file(thumbs=c)
        card = C.load(p["target"])
        self.assertEqual(card["cover_records"][card["thumbs"][card["media"][2]]]["swipe"], "ig-LEDGER")

    def test_other_spellings_of_the_same_fields(self):
        got = CR.normalize({"swipe_id": "ig-A", "version_id": "H2", "source_frame": {"from": "H2.mp4", "at": 3.0, "path": "f.jpg"}})
        self.assertEqual(got, {"swipe": "ig-A", "version": "H2", "frame": {"video": "H2.mp4", "t": 3.0, "file": "f.jpg"}})
        self.assertIsNone(CR.normalize({"prompt": "a picture"}))


class CoversDiffer(Base):
    def test_the_same_picture_twice_holds_the_card_and_names_both(self):
        got = self.checks(self.file(thumbs=self.covers(seeds=("one", "one", "two"))))
        self.assertFalse(got["cover_differs"]["ok"])
        self.assertIn("asset-01 ≈ asset-02", got["cover_differs"]["why"])
        self.assertNotIn("asset-03", got["cover_differs"]["why"])
        self.assertTrue(got["cover_each"]["ok"])

    def test_a_redraw_a_few_bits_apart_is_the_same_picture(self):
        from PIL import Image
        c = self.covers()
        im = Image.open(c[0]).convert("RGB")
        im.paste((255, 255, 255), (0, 0, 120, 240))            # one block of 72 changed
        im.save(c[1])
        d = CR.apart(CR.dhash(c[0]), CR.dhash(c[1]))
        self.assertTrue(0 < d <= 8, d)
        self.assertFalse(self.checks(self.file(thumbs=c))["cover_differs"]["ok"])

    def test_different_pictures_pass(self):
        got = self.checks(self.file(thumbs=self.covers()))
        self.assertTrue(got["cover_differs"]["ok"])
        self.assertIn("3 cover(s), no two alike", got["cover_differs"]["why"])

    def test_the_number_is_pre_flights_where_pre_flight_is_installed(self):
        pf = self.tmp / "preflight.json"
        pf.write_text(json.dumps({"covers": {"same_at_bits": 3}}))
        with mock.patch.object(CR, "PREFLIGHT", pf):
            self.assertEqual(CR.same_at_bits(), 3)
        with mock.patch.object(CR, "PREFLIGHT", self.tmp / "none.json"):
            self.assertEqual(CR.same_at_bits(), 8)

    def test_through_the_card_checks_a_failing_cover_check_fails_the_card(self):
        p = self.file(thumbs=self.covers(seeds=("one", "one", "one")))
        card = C.check_and_save(p["target"], online=False)
        self.assertFalse(card["checks"]["cover_differs"]["ok"])
        self.assertFalse(C.passed(card))
        self.assertEqual(C.LABELS["cover_differs"], CR.LABELS["cover_differs"])


if __name__ == "__main__":
    unittest.main()
