"""The line's cover step (line.py step 5): one cover per version from image production's cover job, each from a frame
of that version's own video, following a different swipe from the cover index, with the version's headline; the record
beside each cover is the one the approval card's checks read. thumbs.py and thumbs_up.py refuse to run as the cover
step and name the new route. No image tool, no index pull, no network: the tool and the index are stand-ins.

    python3 components/video-edit/tests/test_cover_step.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
sys.path.insert(0, str(HERE.parents[1] / "meta-upload"))
import line as LN  # noqa: E402

try:
    from PIL import Image
except ImportError:                       # the line's own cover step needs Pillow too; without it nothing here can run
    Image = None

INDEX = {"scope": "avatar", "avatar": "night-worker", "covers": [
    {"id": "ig-PLAIN1", "move": "as-shot", "likes": 90000}, {"id": "ig-SCALE2", "move": "wrong-scale", "likes": 80000},
    {"id": "ig-FACE3", "move": "face-at-limit", "likes": 70000}, {"id": "ig-ODD4", "move": "one-odd-thing", "likes": 60000}]}


@unittest.skipUnless(Image, "Pillow not installed")
class Base(unittest.TestCase):
    versions = ("control", "H2", "H3")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.vm, self.out = self.tmp / "production", self.tmp / "edit"
        (self.out / "renders").mkdir(parents=True)
        self.vm.mkdir()
        for v in self.versions:
            m = {"brand": "acme", "label": "widget-ad", "text": [{"kind": "hook headline", "words": ["line", "for", v]}]}
            (self.out / ("edit-map.json" if v == "control" else f"edit-map-{v}.json")).write_text(json.dumps(m))
            (self.out / "renders" / f"{v}.mp4").write_bytes(b"video " + v.encode())
        self.rj = {"brand": "acme", "label": "widget-ad", "avatar": "night-worker", "product": "widget"}
        self.calls, self.asked, self.typed = [], [], []
        self.filed = {"kitchen-close", "lineup"}           # the stand-in's filed sets with a kept print
        self.env = mock.patch.dict(os.environ, {"COVER_JOB_OFF": ""})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp)

    def decisions(self, thumbs):
        (self.out / "decisions.json").write_text(json.dumps({"thumbs": thumbs}))

    # ---- the stand-ins
    def tool(self, size=(1080, 1920), deliver=True):
        def call(step, cmd, log):
            self.calls.append((step, cmd))
            folder = Path(cmd[cmd.index("--out") + 1])
            if deliver:
                Image.new("RGB", size, (len(self.calls) * 40 % 255, 90, 160)).save(folder / "cover.png")
                (folder / "run.json").write_text(json.dumps({"machine": "image-production", "pictures": [{"file": "cover.png"}]}))
        return call

    def find(self, answer=INDEX):
        def f(avatar, limit):
            self.asked.append(avatar)
            return answer
        return f

    @staticmethod
    def frame(out, version, t, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (108, 192), (5, 5, 5)).save(dest)
        return dest

    def kept(self, brand, name):
        return name in self.filed

    def typer(self, brand, product, headlines):
        self.typed.append(list(headlines))
        return {"face": "stand-in", "weight": 800, "size_px": 90}

    def make(self, want=None, **kw):
        kw = {"call": self.tool(), "find": self.find(), "moment": lambda video, tmp: 2.5, "frame": self.frame,
              "kept": self.kept, "typer": self.typer, "sets_home": self.tmp / "sets", **kw}
        return LN.make_covers(self.vm, self.out, self.rj, set(want or self.versions), [], **kw)

    @staticmethod
    def arg(cmd, name):
        return cmd[cmd.index(name) + 1]


def anyones_name():
    """A person's name (one folder per person in team/people, written as in a sentence) or a dated owner quote."""
    import re
    home = HERE.parents[2] / "team" / "people"
    people = sorted(p.name.capitalize() for p in home.iterdir() if p.is_dir()) if home.is_dir() else []
    assert people, f"no people folders in {home}"
    return re.compile(r"\b(?:%s)\b|\b[Oo]wner,? \d" % "|".join(map(re.escape, people)))


STAND_IN_TOOL = """import json, sys
from pathlib import Path
from PIL import Image
sys.path.append(sys.argv.pop(1))
import make
FIT = sys.argv.pop(1) == "fit"


def made(req, **kw):
    out = Path(req["out"])
    out.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1080, 1920), (30, 90, 160)).save(out / "cover.png")
    (out / "run.json").write_text(json.dumps({"machine": "image-production", "pictures": [{"file": "cover.png"}]}))
    return {"delivered": [str(out / "cover.png")], "pictures": [], "below_criteria": [], "model": "stand-in",
            "model_why": "a test", "drive": {"copied": []},
            "cover": {"ok": FIT, "problems": [] if FIT else ["the headline sits on a face"]}}


make.IP.make = made
sys.exit(make.main(sys.argv[1:]))
"""


class TheLineStopsOnAnUnfitCover(Base):
    """The cover step runs the image tool's own command line (make.py) and files nothing when that exits non-zero.
    make.py exits 1 when the cover it delivered is not `ok` (a headline on a face, faces never read), so a cover that
    is not fit to file stops the line before covers.json is written. The image tool's generation is a stand-in; its
    exit code is make.py's own."""
    versions = ("control",)

    def through_make(self, fit):
        tool = self.tmp / "make_stand_in.py"
        tool.write_text(STAND_IN_TOOL)
        real_cmd, real_tool = LN.cover_cmd, LN.IMAGE_TOOL

        def cmd(*a, **kw):                      # make.py's own argv, run through make.main with the stand-in maker
            c = real_cmd(*a, **kw)
            return [c[0], str(tool), str(real_tool.parent), "fit" if fit else "unfit"] + c[2:]
        with mock.patch.object(LN, "cover_cmd", cmd):
            return self.make(call=LN.run)

    def test_an_unfit_cover_stops_the_line_and_files_nothing(self):
        with mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": ""}):
            with self.assertRaises(LN.Red) as stop:
                self.through_make(fit=False)
        self.assertIn("5 covers control stopped the line", str(stop.exception))
        self.assertIn("not fit to file", str(stop.exception))
        self.assertIn("the headline sits on a face", str(stop.exception))
        self.assertFalse((self.out / "covers" / "covers.json").exists())
        self.assertFalse((self.out / "covers" / "control" / "cover.cover.json").exists())

    def test_a_fit_cover_goes_on_to_the_card(self):
        with mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": ""}):
            got = self.through_make(fit=True)
        self.assertEqual(sorted(got), ["control"])
        self.assertTrue((self.out / "covers" / "covers.json").exists())

    def test_with_the_image_tools_switch_off_an_unfit_cover_is_filed_as_before(self):
        with mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": "unfit_exit"}):
            got = self.through_make(fit=False)
        self.assertEqual(sorted(got), ["control"])


class TheCall(Base):
    def test_the_image_tools_cover_job_is_named_in_one_function(self):
        cmd = LN.cover_cmd("acme", "H2", Path("/x/H2_frame.jpg"), "ig-SCALE2", "line for H2", Path("/x/out"), product="widget")
        self.assertEqual(cmd[1:], [str(LN.IMAGE_TOOL), "--purpose", "cover", "--brand", "acme", "--version", "H2",
                                   "--frame", "/x/H2_frame.jpg", "--swipe", "ig-SCALE2", "--headline", "line for H2",
                                   "--out", "/x/out", "--product", "widget"])
        self.assertTrue(str(LN.IMAGE_TOOL).endswith("components/image-production/make.py"))

    def test_one_call_per_version_with_its_own_frame_swipe_and_headline(self):
        got = self.make()
        self.assertEqual([s for s, _ in self.calls], ["5 covers control", "5 covers H2", "5 covers H3"])
        for (_, cmd), v in zip(self.calls, self.versions):
            self.assertEqual(self.arg(cmd, "--purpose"), "cover")
            self.assertEqual(self.arg(cmd, "--version"), v)
            self.assertEqual(self.arg(cmd, "--headline"), f"line for {v}")
            self.assertEqual(Path(self.arg(cmd, "--frame")).name, f"{v}_frame.jpg")
            self.assertTrue(Path(self.arg(cmd, "--frame")).is_file())
            self.assertEqual(self.arg(cmd, "--swipe"), got[v]["swipe"])
        self.assertNotIn("thumbs.py", json.dumps([c for _, c in self.calls]))

    def test_each_version_follows_a_different_swipe_and_a_cover_that_makes_a_move_comes_first(self):
        got = self.make()
        self.assertEqual([got[v]["swipe"] for v in self.versions], ["ig-SCALE2", "ig-FACE3", "ig-ODD4"])
        self.assertEqual(self.asked, ["night-worker"])

    def test_the_frame_is_from_the_versions_own_video_at_the_strongest_moment(self):
        seen = []
        got = self.make(moment=lambda video, tmp: seen.append(video.name) or 3.5)
        self.assertEqual(seen, ["control.mp4", "H2.mp4", "H3.mp4"])
        h2 = self.out / "renders" / "H2.mp4"
        self.assertEqual(got["H2"]["frame"], {"video": str(h2), "video_sha256": LN._sha256(h2), "t": 3.5,
                                              "file": "H2_frame.jpg"})


class TheRecord(Base):
    def test_a_record_beside_each_cover_and_one_list_for_the_run(self):
        got = self.make()
        listed = json.loads((self.out / "covers" / "covers.json").read_text())
        self.assertEqual(sorted(listed), ["H2", "H3", "control"])
        for v in self.versions:
            pic = Path(got[v]["file"])
            self.assertEqual(pic, self.out / "covers" / v / "cover.png")
            rec = json.loads(pic.with_suffix(".cover.json").read_text())
            self.assertEqual((rec["version"], rec["swipe"], rec["headline"]), (v, got[v]["swipe"], f"line for {v}"))
            self.assertEqual(rec["frame"]["video"], str(self.out / "renders" / f"{v}.mp4"))
            self.assertEqual(rec["frame"]["video_sha256"], LN._sha256(self.out / "renders" / f"{v}.mp4"))

    def test_the_image_tools_own_record_is_kept_whole_and_only_completed(self):
        inner = self.tool()

        def call(step, cmd, log):
            inner(step, cmd, log)
            folder = Path(cmd[cmd.index("--out") + 1])
            (folder / "cover.cover.json").write_text(json.dumps(
                {"version": self.arg(cmd, "--version"), "swipe": self.arg(cmd, "--swipe"), "base": "frame",
                 "source_frame": {"file": self.arg(cmd, "--frame"), "sha256": "f" * 64}, "set": {"name": "kitchen"}}))
        got = self.make(want={"H2"}, call=call)
        rec = json.loads(Path(got["H2"]["file"]).with_suffix(".cover.json").read_text())
        self.assertEqual((rec["base"], rec["set"], rec["source_frame"]["sha256"]), ("frame", {"name": "kitchen"}, "f" * 64))
        self.assertEqual(Path(rec["source_frame"]["file"]).name, "H2_frame.jpg")
        h2 = str(self.out / "renders" / "H2.mp4")
        self.assertEqual((rec["source_frame"]["video"], rec["source_frame"]["t"], rec["headline"]), (h2, 2.5, "line for H2"))
        import cover_rule as CR
        said = CR.read_record(Path(got["H2"]["file"]))[0]
        self.assertEqual((said["swipe"], said["frame"]["video"], said["frame"]["t"]), (got["H2"]["swipe"], h2, 2.5))

    def test_the_approval_cards_checks_read_that_record_as_a_frame_of_the_covers_own_video(self):
        import cover_rule as CR
        got = self.make()
        pairs = [(self.out / "renders" / f"{v}.mp4", f"ad_asset-{i:02d}.mp4", Path(got[v]["file"]), f"ad_asset-{i:02d}_thumb.png")
                 for i, v in enumerate(self.versions, 1)]
        recs = CR.for_filing(pairs)
        for _, vname, _, cname in pairs:
            self.assertEqual(recs[cname]["frame"]["video"], vname)
            self.assertTrue(recs[cname]["swipe"].startswith("ig-"))

    def test_the_covers_to_file_come_back_in_version_order_or_not_at_all(self):
        got = self.make(want={"control", "H2"})
        self.assertEqual(LN.cover_files(self.out, ["control", "H2"]), [Path(got["control"]["file"]), Path(got["H2"]["file"])])
        self.assertIsNone(LN.cover_files(self.out, ["control", "H2", "H3"]))
        self.assertIsNone(LN.cover_files(self.tmp / "nowhere", ["control"]))


class OneTypeForEveryVersion(Base):
    def test_every_call_names_the_ad_its_video_the_second_and_one_type(self):
        self.make()
        types = {self.arg(cmd, "--type") for _, cmd in self.calls}
        self.assertEqual(types, {str(self.out / "covers" / "cover-type.json")})
        for (_, cmd), v in zip(self.calls, self.versions):
            self.assertEqual(self.arg(cmd, "--ad"), "widget-ad")
            self.assertEqual(self.arg(cmd, "--video"), str(self.out / "renders" / f"{v}.mp4"))
            self.assertEqual(self.arg(cmd, "--frame-at"), "2.5")
        filed = json.loads((self.out / "covers" / "cover-type.json").read_text())
        self.assertEqual(filed, {"ad": "widget-ad", "type": {"face": "stand-in", "weight": 800, "size_px": 90}})

    def test_the_type_is_fitted_to_every_versions_headline_even_when_one_is_made_again(self):
        self.make(want={"H2"})
        self.assertEqual(self.typed, [["line for control", "line for H2", "line for H3"]])

    def test_the_clean_twin_is_the_video_named_when_the_render_kept_one(self):
        (self.out / "renders" / "H2.clean.mp4").write_bytes(b"H2 without words")
        got = self.make(want={"H2"})
        self.assertEqual(self.arg(self.calls[0][1], "--video"), str(self.out / "renders" / "H2.clean.mp4"))
        self.assertEqual(got["H2"]["frame"]["video_sha256"], LN._sha256(self.out / "renders" / "H2.clean.mp4"))

    def test_no_size_fits_every_headline_stops_with_the_tools_reason(self):
        def refuses(brand, product, headlines):
            raise ValueError("the headline does not fit its band")
        with self.assertRaises(LN.Red) as e:
            self.make(typer=refuses)
        self.assertIn("no one type fits every version's headline (the headline does not fit its band)", str(e.exception))
        self.assertEqual(self.calls, [])

    def test_the_cover_cmd_extras_come_after_the_four_things_and_only_when_given(self):
        cmd = LN.cover_cmd("acme", "H2", Path("/x/f.jpg"), "ig-SCALE2", "h", Path("/x/out"), set_="lineup", ad="ad-1",
                           video=Path("/x/H2.mp4"), t=1.5, type_=Path("/x/cover-type.json"))
        self.assertEqual(cmd[-10:], ["--set", "lineup", "--ad", "ad-1", "--video", "/x/H2.mp4", "--frame-at", "1.5",
                                     "--type", "/x/cover-type.json"])
        self.assertNotIn("--ad", LN.cover_cmd("acme", "H2", Path("/x/f.jpg"), "s", "h", Path("/x/out")))

    def test_the_image_tools_own_fit_writes_a_type_file_the_tool_reads_back(self):
        try:
            CV = LN._image_tool().covers
        except Exception as ex:  # noqa: BLE001
            self.skipTest(f"the image tool is not importable here: {ex}")
        lines = ["She said no", "I asked ten women what they think about this one thing"]
        f = LN.cover_type("acme", "ad-1", None, lines, self.tmp / "cover-type.json")
        self.assertEqual(json.loads(f.read_text())["ad"], "ad-1")
        self.assertEqual(CV.type_of(f)["size_px"], CV.ad_type(lines)["size_px"])

    def test_switched_off_no_type_is_passed(self):
        with mock.patch.dict(os.environ, {"COVER_JOB_OFF": "one_type"}):
            self.make()
            self.assertTrue(LN.cover_job_on())
        self.assertEqual(self.typed, [])
        self.assertNotIn("--type", self.calls[0][1])


class TheAdsOwnSet(Base):
    """The cover job needs the ad's filed 3D set; with none in the ad's decisions it is found in the ad's own records."""

    def test_the_set_a_take_started_from_is_found_in_the_production_records(self):
        (self.vm / "takes").mkdir()
        (self.vm / "takes" / "s1.json").write_text(json.dumps({"made": {"from_print": "/sets/lineup/print-v2.png"}}))
        (self.vm / "takes" / "s2.json").write_text(json.dumps({"set": "not-filed"}))
        got = self.make(want={"control"})
        self.assertEqual(self.arg(self.calls[0][1], "--set"), "lineup")
        self.assertIn("the production's records", got["control"]["set_from"])

    def test_the_run_record_names_it(self):
        self.rj["set"] = "kitchen-close"
        self.make(want={"control"})
        self.assertEqual(self.arg(self.calls[0][1], "--set"), "kitchen-close")

    def test_a_filed_set_that_names_this_ad(self):
        sj = self.tmp / "sets" / "lineup" / "set.json"
        sj.parent.mkdir(parents=True)
        sj.write_text(json.dumps({"runs": ["widget-ad"]}))
        self.make(want={"control"})
        self.assertEqual(self.arg(self.calls[0][1], "--set"), "lineup")

    def test_two_filed_sets_for_one_product_is_no_answer(self):
        for name in ("lineup", "kitchen-close"):
            sj = self.tmp / "sets" / name / "set.json"
            sj.parent.mkdir(parents=True)
            sj.write_text(json.dumps({"products": ["widget"]}))
        self.assertEqual(LN.cover_set(self.vm, self.out, self.rj, {}, "acme", "widget", None, kept=self.kept,
                                      sets_home=self.tmp / "sets")[0], None)

    def test_none_filed_the_tool_is_still_asked_and_the_stop_says_where_the_line_looked(self):
        def refused(step, cmd, log):
            self.calls.append((step, cmd))
            raise LN.Red(f"{step} stopped the line:\nit names no filed 3D set")
        with self.assertRaises(LN.Red) as e:
            self.make(want={"control"}, call=refused)
        self.assertNotIn("--set", self.calls[0][1])
        msg = str(e.exception)
        self.assertIn("it names no filed 3D set", msg)
        self.assertIn("no filed 3D set for this ad", msg)
        self.assertIn("the run records", msg)
        self.assertIn("thumbs.set", msg)

    def test_switched_off_the_set_is_not_looked_for(self):
        self.rj["set"] = "kitchen-close"
        with mock.patch.dict(os.environ, {"COVER_JOB_OFF": "find_set"}):
            self.make(want={"control"})
        self.assertNotIn("--set", self.calls[0][1])


class TheAdsOwnDecisions(Base):
    def test_a_named_swipe_time_headline_and_set_win(self):
        self.decisions({"swipes": ["tt-LIST1"], "set": "kitchen-close",
                        "H2": {"swipe": "tt-MINE", "at": 4.0, "text": "my   own line"}})
        got = self.make(want={"control", "H2"})
        self.assertEqual((got["H2"]["swipe"], got["H2"]["frame"]["t"], got["H2"]["headline"]), ("tt-MINE", 4.0, "my own line"))
        self.assertEqual(got["control"]["swipe"], "tt-LIST1")
        self.assertEqual(self.arg(self.calls[0][1], "--set"), "kitchen-close")
        self.assertEqual(self.asked, [], "the index is not asked when the ad names enough swipes")


class WhoseCoversAndWhichProduct(Base):
    def test_the_avatar_and_product_come_from_the_production_brief_when_the_run_records_name_none(self):
        self.rj = {"brand": "acme", "label": "widget-ad"}
        (self.vm / "brief.md").write_text("# brief\n\n```json\n" + json.dumps(
            {"piece": {"avatar": "early-riser", "product": "gadget"}}) + "\n```\n")
        self.make(want={"control"})
        self.assertEqual(self.asked, ["early-riser"])
        self.assertEqual(self.arg(self.calls[0][1], "--product"), "gadget")

    def test_the_ads_own_decision_names_the_avatar_first(self):
        self.decisions({"avatar": "weekend-cook"})
        self.make(want={"control"})
        self.assertEqual(self.asked, ["weekend-cook"])

    def test_no_avatar_anywhere_stops_and_says_so(self):
        self.rj = {"brand": "acme", "label": "widget-ad"}
        with self.assertRaises(LN.Red) as e:
            self.make(want={"control"})
        self.assertIn("avatar (none named)", str(e.exception))
        self.assertEqual(self.asked, [])


class Stops(Base):
    def stopped(self, **kw):
        with self.assertRaises(LN.Red) as e:
            self.make(**kw)
        return str(e.exception)

    def test_no_headline_stops_and_names_the_version(self):
        (self.out / "edit-map-H2.json").write_text(json.dumps({"brand": "acme", "label": "widget-ad", "text": []}))
        msg = self.stopped()
        self.assertIn("H2 has no headline", msg)
        self.assertIn("thumbs.H2.text", msg)

    def test_no_cover_for_this_avatar_in_the_index_stops_and_says_how_to_get_one(self):
        msg = self.stopped(find=self.find({"scope": "general-fallback", "note": "no covers for that avatar",
                                           "covers": [{"id": "ig-GENERAL", "move": "wrong-scale"}]}))
        self.assertIn("no swipe for control's cover", msg)
        self.assertIn("night-worker", msg)
        self.assertIn("covers.py pull --avatar", msg)
        self.assertEqual(self.calls, [], "nothing is made from a cover the avatar does not see")

    def test_a_tool_that_delivers_nothing_stops(self):
        self.assertIn("delivered no picture", self.stopped(call=self.tool(deliver=False)))

    def test_a_cover_of_the_wrong_shape_stops(self):
        self.assertIn("a cover is 9:16", self.stopped(call=self.tool(size=(1080, 1080))))

    def test_a_missing_video_stops(self):
        (self.out / "renders" / "H3.mp4").unlink()
        self.assertIn("H3 has no finished video", self.stopped())

    def test_the_image_tools_own_refusal_stops_the_line(self):
        def refused(step, cmd, log):
            raise LN.Red(f"{step} stopped the line:\nno filed 3D set")
        self.assertIn("no filed 3D set", self.stopped(call=refused))


class TheMoment(Base):
    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_the_frame_with_the_biggest_face_is_the_moment(self):
        clip = self.tmp / "clip.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=108x192:rate=5", "-t", "6",
                        "-pix_fmt", "yuv420p", str(clip)], check=True)
        faces = [0.0, 0.02, 0.3, 0.1, 0.0, 0.05]         # share of the picture a face fills, frame by frame

        def read(frames):
            return [{"faces": [{"x": 0, "y": 0, "w": a, "h": 1.0}] if a else []} for a in faces[:len(frames)]]
        self.assertEqual(LN.cover_moment(clip, self.tmp, read), 2.5)
        self.assertEqual(LN.cover_moment(clip, self.tmp, lambda frames: [{"faces": []} for _ in frames]), 1.0)

    def test_no_reader_is_second_one_not_a_stop(self):
        def broken(frames):
            raise RuntimeError("no reader on this machine")
        self.assertEqual(LN.cover_moment(self.out / "renders" / "control.mp4", self.tmp, broken), 1.0)


class TheSwitch(Base):
    def test_shipped_on(self):
        steps = json.loads((HERE.parent / "machine" / "steps.json").read_text())["line"]
        self.assertIs(steps["cover_job"]["on"], True)
        self.assertTrue(LN.cover_job_on())
        self.assertIn("make.py --purpose cover", next(s for s in steps["steps"] if s["id"] == "thumbs")["what"])

    def test_off_on_one_machine(self):
        with mock.patch.dict(os.environ, {"COVER_JOB_OFF": "1"}):
            self.assertFalse(LN.cover_job_on())
        with mock.patch.dict(os.environ, {"COVER_JOB_OFF": "find_set"}):
            self.assertTrue(LN.cover_job_on())
            self.assertFalse(LN.cover_job_on("find_set"))
            self.assertTrue(LN.cover_job_on("one_type"))

    def test_the_parts_ship_on(self):
        steps = json.loads((HERE.parent / "machine" / "steps.json").read_text())["line"]["cover_job"]
        self.assertEqual((steps["find_set"], steps["one_type"]), (True, True))
        self.assertTrue(LN.cover_job_on("find_set") and LN.cover_job_on("one_type"))

    def run_line(self):
        ran = []
        with mock.patch.object(LN, "make_covers", lambda *a, **k: ran.append("cover job") or {}), \
                mock.patch.object(LN, "run", lambda step, cmd, log, env=None: ran.append((step, Path(cmd[1]).name)) or ""):
            LN.main([str(self.vm), "--out", str(self.out), "--from", "thumbs", "--versions", "--no-file"])
        return ran

    def test_the_line_runs_the_cover_job_at_step_five_and_never_the_frame_covers(self):
        (self.vm / "run.json").write_text(json.dumps(self.rj))
        ran = self.run_line()
        self.assertIn("cover job", ran)
        self.assertNotIn(("5 thumbs", "thumbs.py"), ran)

    def test_switched_off_the_line_runs_the_frame_covers_as_before(self):
        (self.vm / "run.json").write_text(json.dumps(self.rj))
        with mock.patch.dict(os.environ, {"COVER_JOB_OFF": "1"}):
            ran = self.run_line()
        self.assertIn(("5 thumbs", "thumbs.py"), ran)
        self.assertNotIn("cover job", ran)


@unittest.skipUnless(Image, "Pillow not installed")
class RetiredTools(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"COVER_JOB_OFF": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def refused(self, fn):
        with self.assertRaises(SystemExit) as e:
            fn()
        msg = str(e.exception)
        self.assertIn("retired as a cover step", msg)
        self.assertIn("components/image-production/make.py --purpose cover", msg)
        self.assertIn("line.cover_job", msg)
        return msg

    def test_the_frame_cover_step_refuses_and_names_the_new_route(self):
        import thumbs as TH
        self.assertIn("thumbs.py", self.refused(lambda: TH.main(["some-run"])))

    def test_the_styled_cover_refuses_by_either_door(self):
        import thumbs as TH
        import thumbs_up as TU
        self.assertIn("thumbs_up.py", self.refused(lambda: TU.main(["spec.json"])))
        self.assertIn("thumbs_up.py", self.refused(lambda: TH.main(["--spec", "spec.json"])))

    def test_switched_off_they_run_as_before(self):
        import thumbs as TH
        with mock.patch.dict(os.environ, {"COVER_JOB_OFF": "1"}):
            self.assertIsNone(TH.refuse_as_cover_step("thumbs.py"))
            with self.assertRaises(FileNotFoundError):       # past the refusal: it goes looking for the run
                TH.main([str(Path(tempfile.gettempdir()) / "no-such-run")])

    def test_the_docstrings_say_retired_and_name_the_route(self):
        import thumbs as TH
        import thumbs_up as TU
        for mod in (TH, TU):
            self.assertIn("RETIRED AS A COVER STEP", mod.__doc__)
            self.assertIn("make.py --purpose cover", " ".join(mod.__doc__.split()))

    def test_the_docstrings_carry_the_rule_not_anyones_words(self):
        import thumbs as TH
        import thumbs_up as TU
        name = anyones_name()
        for doc in (TH.__doc__, TU.__doc__, LN.__doc__, LN.approved.__doc__):
            self.assertIsNone(name.search(doc), doc[:200])

    def test_the_cover_files_carry_no_ones_name_or_quoted_words(self):
        machine = Path(LN.__file__).resolve().parent
        name = anyones_name()
        for f in ("thumbs.py", "thumbs_up.py", "line.py"):
            text = (machine / f).read_text()
            self.assertIsNone(name.search(text), f"{f}: {name.search(text) and name.search(text).group(0)}")
        row = next(x for x in (machine.parent / "EDIT-LINE.md").read_text().splitlines() if x.startswith("| 11 "))
        self.assertIsNone(name.search(row), row[:200])

    def test_the_readers_other_tools_import_are_still_there(self):
        import thumbs as TH
        for name in ("scene", "scenes", "frame_at", "place"):
            self.assertTrue(callable(getattr(TH, name)))


if __name__ == "__main__":
    unittest.main()
