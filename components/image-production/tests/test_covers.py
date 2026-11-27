#!/usr/bin/env python3
"""The cover job (2026-11-12): one cover per version of a video ad, made start to finish by this tool.

    python3 components/image-production/tests/test_covers.py

Four things, each with the case that was wrong before:
  1. a cover is a purpose of its own (it ran as `ad`): 9:16, one request per version, the record names the version, the
     swipe it follows and the source frame;
  2. the frame of the version's own video is the composition (it was refused as a base), and the filed 3D set is still
     required;
  3. a named product comes from its 3D kit even though a set is named (it was skipped whenever a base was set);
  4. the headline is set by the tool's words step, and every version of one ad is set in one type.

And the checks that keep a cover true to the rule (row COVER-CHECKS):
  5. the frame is a frame of the version's own video (checked with ffmpeg; the video is a real video stream, never a
     still picture), never a picture the tool made (by its bytes, its records, or its look for a re-saved copy);
  6. a single request names its ad and takes the ad's filed type, so every version is set in one type;
  7. the faces under the words are read on the plate, and a cover whose faces were not read is not fit to file;
  8. the swipe is a real cover's id, and a cover with no direction takes its concept from that cover's rated move.
  9. `make.py` with one cover request exits 1 when the cover it delivered is not fit to file.

Stdlib `unittest`, Pillow and ffmpeg. No network, no model, no key: a temp workspace (AI_WORKSPACE), a stub picture
door, a stub 3D product, a stub face reader, the Drive switched off. The stand-in videos are flat colours made locally.
"""
import base64
import copy
import io
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
sys.path.append(str(HERE.parent))                  # APPEND, never insert at 0
os.environ.pop("PICTURE_GATE_OFF", None)            # the set gate is part of what is tested here
os.environ.pop("IMAGE_COVER_OFF", None)
import image_production as IP                      # noqa: E402
from image_production import covers as CV, product3d as P3, set_gate as SG, words as W   # noqa: E402

HAVE_FACE = (W.faces_dir() / "tiktok-sans").is_dir()
HAVE_FFMPEG = bool(shutil.which("ffmpeg"))
_CLIPS = tempfile.TemporaryDirectory(prefix="cover-test-clips-")
DEFAULT = (30, 60, 90)


def clip_of(colour, size=(270, 480)):
    """A 3-second flat-colour stand-in video, made once per colour and size."""
    f = Path(_CLIPS.name) / ("%02x%02x%02x-%dx%d.mp4" % (*colour, *size))
    if not f.is_file():
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i",
                        "color=c=0x%02x%02x%02x:size=%dx%d:rate=10:duration=3" % (*colour, *size), "-pix_fmt", "yuv420p",
                        str(f)], check=True, capture_output=True)
    return f


def grab(video, dest, at=1.5):
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", "%.3f" % at, "-i", str(video), "-frames:v", "1",
                    str(dest)], check=True, capture_output=True)
    return Path(dest)


def picture(path, colour=(90, 120, 150), size=(540, 960)):
    from PIL import Image
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)
    return Path(path)


def door(calls, colour=(70, 90, 110)):
    """A picture door that answers with a flat 1152x2048 picture and records what it was sent."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (1152, 2048), colour).save(buf, "PNG")
    blob = base64.b64encode(buf.getvalue()).decode()

    def t(method, url, headers, body):
        calls.append({"url": url, "body": body or b""})
        return 200, {"x-request-id": "stub"}, json.dumps({"data": [{"b64_json": blob}]}).encode()
    return t


class Library:
    class Unknown(KeyError):
        pass

    def get(self, element, asset, id_):
        raise self.Unknown(id_)


def table(**cover):
    t = json.loads((HERE / "route-openai-fixture.json").read_text())
    t["judge"]["on"] = False
    t["gate"]["set_required"] = {"on": True, "lanes": {}}
    t["gate"]["cover"] = {"on": True, "source_frame": True, "product_with_set": True, "words_step": True, **cover}
    return t


@unittest.skipUnless(HAVE_FACE, "the type library (components/video-edit/looks/fonts) is not in this checkout")
@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg is not on this machine")
class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "components").mkdir()
        b = self.root / "brands" / "b"
        (b / "identity").mkdir(parents=True)
        (b / "identity" / "palette.md").write_text("| Ink | `#112233` |\n")
        (b / "identity" / "fonts.md").write_text("A font.\n")
        (b / "products" / "widget" / "images").mkdir(parents=True)
        picture(b / "products" / "widget" / "images" / "packshot.png", size=(40, 40))
        (b / "products" / "images.json").write_text(json.dumps({"products": {
            "widget": {"title": "The Widget", "cutout": "products/widget/images/packshot.png"},
            "gadget": {"title": "The Gadget"}}}))
        kit = self.root / "runs" / "ai-elements" / "b" / "products" / "widget"
        (kit / "model").mkdir(parents=True)
        (kit / "kit.json").write_text(json.dumps({"aliases": [], "what": "the object"}))
        (kit / "model" / "m.blend").write_bytes(b"x")
        (kit / "model" / "render3d.json").write_text(json.dumps({
            "status": "draft", "model": {"blend": "model/m.blend", "root": "product"},
            "default_pose": "rest", "poses": {"rest": {}}}))
        self._env = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.root)
        self.t = table()
        self.calls = []
        self.placed = []
        for target, attr, new in (
                (IP.route, "table", lambda path=None, house=True: copy.deepcopy(self.t)),
                (IP.route, "key_value", lambda name: "test-key"),
                (SG, "_drive_roots", lambda: []),
                (P3, "composite_into", self.fake_product),
                (CV, "face_reader", lambda: self.read_faces)):
            p = mock.patch.object(target, attr, new)
            p.start()
            self.addCleanup(p.stop)
        self.print = self.file_set()
        self.out = self.root / "out"
        self.faces_seen = []
        self.index([{"id": "swipe-042", "move": "wrong-scale"}, {"id": "swipe-001", "move": "impossible-object"},
                    {"id": "swipe-002", "move": "line-shown-literally"}, {"id": "swipe-003", "move": "face-at-limit"}])

    def read_faces(self, picture):
        """The stand-in face reader: no faces, and it says what it read."""
        self.faces_seen.append(str(picture))
        return []

    def index(self, rows):
        d = self.root / "runs" / "asset-index" / "swipes" / "covers"
        d.mkdir(parents=True, exist_ok=True)
        (d / "covers.json").write_text(json.dumps(rows))

    def clip(self, name, colour=DEFAULT, size=(270, 480)):
        dst = self.root / "videos" / name
        if not dst.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(clip_of(colour, size), dst)
        return dst

    def tearDown(self):
        if self._env is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self._env
        self.tmp.cleanup()

    def fake_product(self, scene_png, out_png, kit, pl, work_dir, ask=None):
        """Stands in for the Blender render and the placement: marks the picture and says where."""
        from PIL import Image, ImageDraw
        im = Image.open(scene_png).convert("RGB")
        box = [int(im.width * .4), int(im.height * .55), int(im.width * .6), int(im.height * .7)]
        ImageDraw.Draw(im).rectangle(box, fill=(250, 200, 20))
        im.save(out_png)
        self.placed.append({"kit": str(kit), "place": dict(pl)})
        return {"render": {"file": str(Path(work_dir) / "product.png"), "source": "3d-model"}, "placed": {"box": box}}

    def file_set(self, name="lineup", kept=True):
        d = self.root / "runs" / "image-production" / "b" / "sets" / name
        pr = picture(d / "print-v1.png", (200, 120, 40))
        (d / "set.json").write_text(json.dumps({"project": {"id": "p"}, "prints": [
            {"file": "print-v1.png", "note": "kept: the line-up" if kept else "faces off"}]}))
        return pr

    def frame(self, name="frame-h1.png", colour=DEFAULT, video=None):
        """A frame grabbed at 1.5 s from a stand-in video of that colour (ad-1_h1.mp4 for the default colour)."""
        dest = self.root / "frames" / name
        if not dest.is_file():
            grab(self.clip(video or ("ad-1_h1.mp4" if tuple(colour) == DEFAULT else "clip-%02x%02x%02x.mp4" % colour),
                           colour), dest)
        return dest

    def req(self, **k):
        cover = {"ad": "ad-1", "version": "h1", "headline": "She said no", "frame": str(self.frame()),
                 "video": str(self.clip("ad-1_h1.mp4")), "t": 1.5, "swipe": "swipe-042"}
        cover.update(k.pop("cover", {}))
        base = {"brand": "b", "purpose": "cover", "direction": "her face close, mid-reaction, the mirror cracked",
                "out": str(self.out), "set": "lineup", "people": True, "cover": cover}
        base.update(k)
        return {k_: v for k_, v in base.items() if v is not None}

    def make(self, req=None, **kw):
        return IP.make(req or self.req(), library=Library(), transport=door(self.calls), mirror=False, **kw)

    def resolve(self, req=None):
        return IP.resolve(req or self.req(), library=Library())

    def job(self, **k):
        versions = k.pop("versions", None) or [
            {"version": "control", "headline": "She said no",
             "frame": str(self.frame("c.png", (10, 20, 30), "ad-1_control.mp4")),
             "video": str(self.clip("ad-1_control.mp4", (10, 20, 30))), "t": 1.5, "swipe": "swipe-001",
             "direction": "her face close, mid-reaction"},
            {"version": "h1", "headline": "I asked ten women what they think about this one thing",
             "frame": str(self.frame("h1.png", (40, 50, 60), "ad-1_h1b.mp4")),
             "video": str(self.clip("ad-1_h1b.mp4", (40, 50, 60))), "t": 1.5, "swipe": "swipe-002",
             "direction": "his hand on the counter, the problem up close"},
            {"version": "h2", "headline": "Nobody tells you this",
             "frame": str(self.frame("h2.png", (70, 80, 90), "ad-1_h2.mp4")),
             "video": str(self.clip("ad-1_h2.mp4", (70, 80, 90))), "t": 1.5, "swipe": "swipe-003",
             "direction": "the two of them, she turns away"}]
        base = {"brand": "b", "ad": "ad-1", "out": str(self.out), "set": "lineup", "people": True,
                "versions": versions}
        base.update(k)
        return base

    def make_ad(self, job=None, **kw):
        return CV.make_ad(job or self.job(), library=Library(), transport=door(self.calls), mirror=False, **kw)


# ── 1. a cover is a purpose of its own ───────────────────────────────────────────────────────────────────────────────
class ACoverIsItsOwnPurpose(Workspace):
    def test_the_purpose_is_declared_9x16_and_runs_the_cover_job(self):
        row = IP.purposes()["cover"]
        self.assertEqual((row["aspect"], row["job"], row["words"]), ("9:16", "cover", "never"))
        self.assertTrue(CV.is_cover(row))
        self.assertFalse(CV.is_cover(IP.purposes()["ad"]))

    def test_one_request_makes_one_versions_cover_and_the_record_names_it(self):
        frame = self.frame()
        got = self.make()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(got["delivered"]), 1)
        from PIL import Image
        with Image.open(got["delivered"][0]) as im:
            self.assertEqual(im.size, (1080, 1920))
        run = json.loads((self.out / "run.json").read_text())
        self.assertEqual(run["purpose"], "cover")
        c = run["cover"]
        self.assertEqual((c["version"], c["ad"], c["swipe"], c["headline"]), ("h1", "ad-1", "swipe-042", "She said no"))
        self.assertEqual(c["source_frame"]["sha256"], SG.sha(frame))
        self.assertEqual((c["source_frame"]["video"], c["source_frame"]["t"]),
                         (str(self.clip("ad-1_h1.mp4").resolve()), 1.5))
        self.assertEqual(c["source_frame"]["video_sha256"], SG.sha(self.clip("ad-1_h1.mp4")))
        self.assertTrue(c["source_frame"]["file"].endswith("frame-h1.png"))
        self.assertEqual(c["set"]["name"], "lineup")
        self.assertEqual(c["set"]["sha256"], SG.sha(self.print))
        self.assertEqual(c["sha256"], SG.sha(got["delivered"][0]))                 # the delivered file, fingerprinted
        self.assertEqual(run["pictures"][0]["sha256"], c["sha256"])
        beside = json.loads(Path(got["delivered"][0]).with_suffix(".recipe.json").read_text())
        self.assertEqual(beside["cover"]["version"], "h1")
        self.assertEqual(beside["sha256"], c["sha256"])

    def test_a_cover_without_its_block_or_missing_a_part_is_refused_before_any_door(self):
        for cover in (None, {"swipe": ""}, {"version": None}, {"t": "soon"},
                      {"frame": str(self.root / "no-such.png")}, {"colour": "blue"}):
            req = self.req()
            if cover is None:
                req.pop("cover")
            else:
                req["cover"] = {k: v for k, v in {**req["cover"], **cover}.items() if v is not None}
            with self.assertRaises(IP.BadRequest) as ex:
                self.make(req)
            self.assertIn("Nothing was sent", str(ex.exception))
        self.assertEqual(self.calls, [])

    def test_the_approval_filer_reads_the_covers_record_and_its_fingerprint(self):
        """The cover rule and the made-by-tool gate (components/meta-upload) read what this job writes."""
        import importlib.util
        rule = HERE.parents[1] / "meta-upload" / "cover_rule.py"
        if not rule.is_file():
            self.skipTest("components/meta-upload/cover_rule.py is not in this checkout")
        spec = importlib.util.spec_from_file_location("cover_rule_under_test", rule)
        CR = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(CR)
        got = self.make()
        cover = Path(got["delivered"][0])
        rec, where = CR.read_record(cover)
        self.assertTrue(where.endswith(".cover.json"))
        self.assertEqual((rec["swipe"], rec["version"], rec["headline"]), ("swipe-042", "h1", "She said no"))
        self.assertTrue(rec["frame"]["video"].endswith("ad-1_h1.mp4"))
        self.assertEqual(rec["frame"]["t"], 1.5)
        self.assertTrue(CR._own_video(rec["frame"], rec["version"], str(self.clip("ad-1_h1.mp4").resolve())))
        cover.with_suffix(".cover.json").unlink()                                   # and from the run record alone
        rec, where = CR.read_record(cover)
        self.assertTrue(where.endswith("run.json"))
        self.assertTrue(rec["frame"]["video"].endswith("ad-1_h1.mp4"))
        try:
            from image_production import provenance as PV
        except ImportError:
            return
        self.assertTrue(PV.known(cover))                                            # a record of the delivered bytes
        plate = Path(got["cover"]["words"]["plate"])
        self.assertFalse(PV._in_ledger(PV.sha256(plate)))                           # the bare plate is not the cover

    def test_a_caller_with_nobody_in_the_loop_brings_its_video_and_gets_a_cover(self):
        """The video line's kind of call: a version id, a frame of its own video, that video and the second, the ad, the
        swipe id and the headline. No direction: the job writes its standing one, with the swipe's rated move."""
        import contextlib
        import make
        self.index([{"id": "ig-SCALE2", "move": "wrong-scale"}, {"id": "ig-PLAIN1", "move": "as-shot"}])
        video = self.clip("H2.mp4", (60, 30, 20))
        frame = self.frame("H2_frame.jpg", (60, 30, 20), "H2.mp4")
        folder = self.out / "H2"
        argv = ["--purpose", "cover", "--brand", "b", "--version", "H2", "--frame", str(frame), "--swipe", "ig-SCALE2",
                "--headline", "She said \"no\"", "--out", str(folder), "--set", "lineup", "--ad", "ad-1",
                "--video", str(video), "--frame-at", "1.5", "--no-mirror"]
        with mock.patch.object(IP.providers, "http_transport", door(self.calls)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(make.main(argv), 0)
        self.assertEqual(len(self.calls), 1)
        run = json.loads((folder / "run.json").read_text())
        self.assertTrue((folder / Path(run["pictures"][0]["file"]).name).is_file())
        said = run["request"]["direction"]
        self.assertIn("shows this line literally, without writing it: \"She said 'no'\"", said)
        self.assertIn("pushed about five times past real", said)
        self.assertIn("The move to make, taken from a real cover this audience already sees: wrong scale.", said)
        self.assertIn("standing direction", run["cover"]["direction_from"])
        self.assertTrue(run["cover"]["source_frame"]["video"].endswith("videos/H2.mp4"))
        self.assertTrue(run["cover"]["ok"], run["cover"])
        self.assertTrue((self.out / "cover-type.json").is_file())                  # the ad's type, for its other versions
        self.assertIsNone(CV.swipe_move("ig-PLAIN1"))                                # a cover that makes no move names none
        self.assertIsNone(CV.swipe_move("not-in-the-index"))

    def test_the_video_lines_call_as_it_stands_is_taken_or_refused_by_name(self):
        """Pins the video line's own words for the call (components/video-edit/machine/line.py cover_cmd): a call that
        names no video, second or ad is refused before anything is spent, saying what is missing."""
        import contextlib
        import importlib.util
        import make
        line = HERE.parents[1] / "video-edit" / "machine" / "line.py"
        if not line.is_file() or "def cover_cmd" not in line.read_text():
            self.skipTest("the video line's cover step is not in this checkout")
        spec = importlib.util.spec_from_file_location("line_under_test", line)
        LN = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(LN)
        frame = self.frame()
        try:
            theirs = LN.cover_cmd("b", "h1", frame, "swipe-042", "She said no", self.out / "h1", set_="lineup")
        except TypeError:
            self.skipTest("the line's cover_cmd takes more than the old call; its own suite pins it")
        err = io.StringIO()
        with mock.patch.object(IP.providers, "http_transport", door(self.calls)), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = make.main(theirs[2:] + ["--no-mirror"])
        if "--video" in theirs and "--frame-at" in theirs:
            self.assertEqual(code, 0, err.getvalue())
        else:
            self.assertEqual(code, 2)
            self.assertIn("missing video and t", err.getvalue())
            self.assertEqual(self.calls, [])

    def test_a_job_names_each_versions_video_and_may_leave_the_direction_out(self):
        job = self.job()
        job["versions"][0].pop("direction")
        reqs = self.make_ad(job, dry_run=True)["requests"]
        self.assertNotIn("direction", reqs[0])
        self.assertEqual(reqs[1]["direction"], "his hand on the counter, the problem up close")
        job["versions"][1].pop("video")
        with self.assertRaises(CV.CoverRefused) as ex:
            self.make_ad(job)
        self.assertIn("h1: missing video", str(ex.exception))

    def test_one_picture_per_request(self):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(count=2))
        self.assertIn("one request per version", str(ex.exception))

    def test_the_block_is_only_a_covers(self):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(purpose="ad"))
        self.assertIn("only taken by a cover purpose", str(ex.exception))

    def test_the_master_switch_refuses_the_purpose(self):
        self.t = table(on=False)
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve()
        self.assertIn("switched off", str(ex.exception))
        self.t = table()
        with mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": "all"}):
            with self.assertRaises(IP.BadRequest):
                self.resolve()

    def test_the_command_line_builds_the_block(self):
        import make
        a = make.build_parser().parse_args([
            "--brand", "b", "--purpose", "cover", "--set", "lineup", "--direction", "d", "--out", "o", "--ad", "ad-1",
            "--version", "h1", "--headline", "She said no", "--frame", "f.png", "--video", "v.mp4", "--frame-at", "1.5",
            "--swipe", "swipe-042"])
        self.assertEqual(make.request_from(a)["cover"], {"ad": "ad-1", "version": "h1", "headline": "She said no",
                                                         "frame": "f.png", "video": "v.mp4", "t": 1.5,
                                                         "swipe": "swipe-042"})
        self.assertEqual(make.build_parser().parse_args(["covers", "--job", "j.json", "--only", "h1"]).command, "covers")


# ── 2. the version's own video frame is the composition; the filed set is still required ─────────────────────────────
class TheFrameIsTheComposition(Workspace):
    def test_the_frame_is_accepted_as_the_base_with_the_set_print_beside_it(self):
        frame = self.frame()
        cast = picture(self.root / "cast" / "host.jpg", (5, 5, 5))
        req, ctx, prompt, *_ = self.resolve(self.req(references=[str(cast)]))
        self.assertEqual(req["from_image"], str(frame))
        self.assertEqual(ctx["references"][:3], [str(frame), str(self.print), str(cast)])
        self.assertIn("IMAGE 1 is a frame of this ad's own video", prompt)
        self.assertIn("IMAGE 2 is the filed 3D set print", prompt)
        self.assertNotIn(IP.prompting.EDIT_CLAUSE, prompt)                          # never "keep the picture exactly"
        self.assertIn("COMPOSITION FOR CROPPING", prompt)                           # a new composition, cropped in feed
        self.assertEqual(req["_cover"]["base"], "frame")

    def test_the_door_is_sent_the_frame_first_then_the_print(self):
        sent = []
        real = IP.providers.generate

        def spy(entry, prompt, references, out, aspect, transport=None, key=None):
            sent.append([str(r) for r in references])
            return real(entry, prompt, references, out, aspect, transport=transport, key=key)
        with mock.patch.object(IP.providers, "generate", spy):
            self.make()
        self.assertEqual(sent[0][:2], [str(self.frame()), str(self.print)])

    def test_no_filed_set_is_refused(self):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(set=None))
        self.assertIn("names no filed 3D set", str(ex.exception))
        self.assertTrue(ex.exception.set_refused)

    def test_a_set_with_no_kept_print_is_refused(self):
        self.file_set("rough", kept=False)
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(set="rough"))
        self.assertIn("no kept print", str(ex.exception))

    def test_no_people_is_no_exception(self):
        with self.assertRaises(IP.BadRequest):
            self.resolve(self.req(set=None, people=False))

    def test_a_frame_we_made_is_refused(self):
        ours = self.frame("made.png")
        ours.with_suffix(".recipe.json").write_text("{}")
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"frame": str(ours)}))
        self.assertIn("a picture we made", str(ex.exception))
        self.assertFalse(getattr(ex.exception, "set_refused", False))               # a wrong frame asks for no 3D print

    def test_the_set_print_as_the_frame_is_refused(self):
        self.t = table(own_video=False)                     # byte for byte; a resized print is the own-video check's
        copy_ = self.root / "frames" / "print-copy.png"
        copy_.parent.mkdir(parents=True, exist_ok=True)
        copy_.write_bytes(self.print.read_bytes())
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"frame": str(copy_)}))
        self.assertIn("a redraw of the set print is not a cover", str(ex.exception))

    def test_another_base_is_refused(self):
        other = picture(self.root / "other.png", (1, 2, 3))
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(from_image=str(other)))
        self.assertIn("takes no `from_image`", str(ex.exception))
        req = self.req(from_image=str(other))
        with self.assertRaises(SG.SetRefused):                                      # and the gate holds on its own
            SG.engine_gate(req, IP.purposes()["cover"], self.t)

    def test_an_ad_still_refuses_a_video_frame_as_its_base(self):
        """What a cover hit while it ran as purpose `ad`: the frame as the base is refused. Still true for an ad."""
        req = self.req(purpose="ad", from_image=str(self.frame()))
        req.pop("cover")
        with self.assertRaises(SG.SetRefused) as ex:
            SG.engine_gate(req, IP.purposes()["ad"], self.t)
        self.assertIn("not from set", str(ex.exception))

    def test_rolled_back_the_print_is_the_base_again_and_the_frame_rides_after_it(self):
        self.t = table(source_frame=False)
        req, ctx, prompt, *_ = self.resolve()
        self.assertEqual(req["from_image"], str(self.print))
        self.assertEqual(ctx["references"][:2], [str(self.print), str(self.frame())])
        self.assertIn(IP.prompting.EDIT_CLAUSE, prompt)
        self.assertEqual(req["_cover"]["base"], "print")


# ── 3. the product comes from its 3D kit even when a set is named ────────────────────────────────────────────────────
class TheProductComesFromItsKit(Workspace):
    def test_with_a_set_named_the_product_is_rendered_from_its_kit_and_placed(self):
        req, ctx, prompt, *_ = self.resolve(self.req(product="widget"))
        self.assertIn("product3d", ctx)
        self.assertTrue(ctx["product3d"]["place"]["fixed"])                         # where the plan says: no scene-reading call
        self.assertIn("THE PRODUCT IS NOT DRAWN IN THIS PICTURE", prompt)
        self.assertFalse([r for r in ctx["references"] if "packshot" in r])         # the model is not shown the product
        got = self.make(self.req(product="widget"))
        self.assertEqual(len(self.placed), 1)
        self.assertTrue(self.placed[0]["kit"].endswith("products/widget"))
        c = got["cover"]
        self.assertEqual(c["product"]["source"], "3d-model")
        self.assertEqual(CV.problems(c), [])
        self.assertEqual(c["words"]["type"]["zone"]["top"], 16)                    # the band moved clear of the product
        from PIL import Image
        with Image.open(got["delivered"][0]) as im:
            self.assertEqual(im.getpixel((540, 1200)), (250, 200, 20))              # the placed product is on the cover

    def test_an_ad_with_a_set_is_unchanged_no_3d_product(self):
        req = self.req(purpose="ad", product="widget")
        req.pop("cover")
        _req, ctx, *_ = self.resolve(req)
        self.assertNotIn("product3d", ctx)
        self.assertIsNone(P3.wanted({"product": "widget", "from_image": "a.png"}, "b")[0])
        self.assertIsNotNone(P3.wanted({"product": "widget", "from_image": "a.png", "_product_with_base": True}, "b")[0])

    def test_a_caller_cannot_claim_the_covers_exception(self):
        req = self.req(purpose="ad", product="widget", _product_with_base=True)
        req.pop("cover")
        _req, ctx, *_ = self.resolve(req)
        self.assertNotIn("product3d", ctx)

    def test_a_cover_that_names_no_product_stays_without_one(self):
        _req, ctx, prompt, *_ = self.resolve()
        self.assertNotIn("product3d", ctx)
        self.assertIn("THE PRODUCT IS NOT IN THIS PICTURE", prompt)
        got = self.make()
        self.assertEqual(self.placed, [])
        self.assertIsNone(got["cover"]["product"])

    def test_a_product_with_no_3d_kit_is_refused_never_drawn(self):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(product="gadget"))
        self.assertIn("comes from its 3D kit", str(ex.exception))
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(product="widget", product_3d=False))
        self.assertIn("never drawn by the picture model", str(ex.exception))

    def test_a_product_that_was_not_placed_makes_the_cover_unfit_to_file(self):
        def broken(*a, **k):
            raise RuntimeError("no renderer on this machine")
        with mock.patch.object(P3, "composite_into", broken):
            got = self.make(self.req(product="widget"))
        self.assertIn("no renderer", got["cover"]["product"]["error"])
        self.assertTrue(CV.problems(got["cover"]))

    def test_the_headline_and_the_product_never_land_on_each_other(self):
        band = {"zone": {"top": 58, "bottom": 80, "left": 6, "right": 94}}          # a band the caller insists on
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(product="widget", cover={"type": band}))
        self.assertIn("land on each other", str(ex.exception))
        self.resolve(self.req(product="widget", cover={"type": band},
                              product_place={"x": 0.5, "y": 0.5, "height": 0.2}))    # moved clear: taken

    def test_one_band_for_the_whole_ad_clear_of_every_versions_product(self):
        self.assertEqual(self.make_ad(dry_run=True)["type"]["zone"]["top"], 58)     # no product: the first band
        job = self.job()
        job["versions"][1]["product"] = "widget"                                    # one version shows the product
        got = self.make_ad(job)
        self.assertTrue(got["ok"], got)
        self.assertEqual({r["words"]["type"]["zone"]["top"] for r in got["covers"]}, {16})
        self.assertEqual([bool(r["product"]) for r in got["covers"]], [False, True, False])
        self.assertEqual(len(self.placed), 1)

    def test_rolled_back_the_product_is_not_brought_in_with_a_set(self):
        self.t = table(product_with_set=False)
        _req, ctx, prompt, *_ = self.resolve(self.req(product="widget"))
        self.assertNotIn("product3d", ctx)
        self.assertNotIn("THE PRODUCT IS NOT", prompt)


# ── 4. the words: set by the tool, one type for every version of an ad ───────────────────────────────────────────────
class TheWordsAreSetByTheTool(Workspace):
    def test_the_picture_model_is_told_no_words_and_the_tool_sets_the_headline(self):
        _req, _ctx, prompt, *_ = self.resolve()
        self.assertIn("NO WORDS ARE DRAWN IN THIS PICTURE", prompt)
        self.assertIn("from 58% to 80% down the frame", prompt)
        self.assertNotIn("She said no", prompt)                                     # the model never sees the words
        got = self.make()
        c = got["cover"]
        self.assertEqual(" ".join(c["words"]["lines"]), "She said no")              # exact, character for character
        self.assertIn("words step", c["words"]["by"])
        plate = Path(c["words"]["plate"])
        self.assertTrue(plate.is_file())
        self.assertNotEqual(SG.sha(plate), c["sha256"])                             # the delivered file carries the words
        self.assertEqual(c["words"]["plate_sha256"], SG.sha(plate))
        from PIL import Image
        with Image.open(got["delivered"][0]) as a, Image.open(plate) as b_:
            done, bare = a.convert("RGB"), b_.convert("RGB")
        l, t, r, b = c["words"]["box_px"]
        self.assertNotEqual(done.crop((l, t, r, b)).tobytes(), bare.crop((l, t, r, b)).tobytes())
        self.assertEqual(done.crop((0, 0, 1080, 1000)).tobytes(), bare.crop((0, 0, 1080, 1000)).tobytes())
        self.assertGreaterEqual(t, int(1920 * .148))                                # inside the safe zone
        self.assertLessEqual(b, int(1920 * .852) + 1)

    def test_every_version_of_one_ad_is_set_in_the_same_face_weight_size_and_band(self):
        got = self.make_ad()
        self.assertTrue(got["ok"], got)
        self.assertEqual([r["version"] for r in got["covers"]], ["control", "h1", "h2"])
        self.assertEqual(len(self.calls), 3)                                        # one request per version
        types = [r["words"]["type"] for r in got["covers"]]
        self.assertEqual(types[0], types[1])
        self.assertEqual(types[1], types[2])
        self.assertEqual(types[0], got["type"])
        style = CV.type_of()
        alone = [W.fit([v["headline"]], style) for v in self.job()["versions"]]
        self.assertLess(min(alone), max(alone))                                     # alone they would differ in size
        self.assertEqual(got["type"]["size_px"], min(alone))                        # together: the one size all fit at
        self.assertEqual(len({r["sha256"] for r in got["covers"]}), 3)              # three different pictures
        filed = json.loads((self.out / "cover-type.json").read_text())
        self.assertEqual(filed["type"], got["type"])
        rec = json.loads((self.out / "covers.json").read_text())
        self.assertEqual([c["swipe"] for c in rec["covers"]], ["swipe-001", "swipe-002", "swipe-003"])
        self.assertTrue(all(c["source_frame"]["sha256"] for c in rec["covers"]))

    def test_the_jobs_own_type_sets_them_all(self):
        mine = {"weight": 800, "zone": {"top": 60, "bottom": 82, "left": 8, "right": 92},
                "box": {"fill": "#FFFFFF", "pad_px": 18, "radius_px": 14}, "fill": "#000000", "stroke": None}
        got = self.make_ad(self.job(type=mine))
        for r in got["covers"]:
            self.assertEqual(r["words"]["type"]["weight"], 800)
            self.assertEqual(r["words"]["type"]["zone"]["top"], 60)
            self.assertGreaterEqual(r["words"]["box_px"][1], int(1920 * .60) - 1)

    def test_two_versions_from_the_same_frame_are_refused(self):
        job = self.job()
        job["versions"][1]["frame"] = job["versions"][0]["frame"]
        with self.assertRaises(CV.CoverRefused) as ex:
            self.make_ad(job)
        self.assertIn("the same source frame", str(ex.exception))
        self.assertEqual(self.calls, [])

    def test_one_refusal_stops_the_whole_ad_before_anything_is_spent(self):
        job = self.job()
        job["versions"][2]["set"] = "no-such-set"
        with self.assertRaises(CV.CoverRefused) as ex:
            self.make_ad(job)
        self.assertIn("h2:", str(ex.exception))
        self.assertIn("made none of them", str(ex.exception))
        self.assertEqual(self.calls, [])
        self.assertFalse((self.out / "covers.json").exists())

    def test_a_headline_too_long_for_a_cover_is_refused_before_anything_is_spent(self):
        job = self.job()
        job["versions"][0]["headline"] = " ".join(["everything"] * 40)
        with self.assertRaises(CV.CoverRefused) as ex:
            self.make_ad(job)
        self.assertIn("does not fit its band", str(ex.exception))
        self.assertEqual(self.calls, [])

    def test_a_face_that_is_not_on_this_machine_or_cannot_draw_the_words_is_refused(self):
        with self.assertRaises(CV.CoverRefused) as ex:
            self.make_ad(self.job(type={"face": "no-such-face"}))
        self.assertIn("not a font file", str(ex.exception))
        job = self.job()
        job["versions"][0]["headline"] = "She said no \U0001F600"
        with self.assertRaises(CV.CoverRefused) as ex:
            self.make_ad(job)
        self.assertIn("cannot draw", str(ex.exception))
        self.assertEqual(self.calls, [])

    def test_a_band_outside_the_safe_zone_or_an_unknown_key_is_refused(self):
        for bad in ({"zone": {"top": 2, "bottom": 20, "left": 6, "right": 94}}, {"colour": "red"}):
            with self.assertRaises(CV.CoverRefused):
                self.make_ad(self.job(type=bad))

    def test_one_version_made_again_keeps_the_ads_type_and_its_siblings(self):
        first = self.make_ad()
        again = self.make_ad(only="h1")
        self.assertEqual(len(self.calls), 4)
        self.assertEqual([r["version"] for r in again["covers"]], ["control", "h1", "h2"])
        self.assertEqual(again["type"], first["type"])
        job = self.job()
        job["versions"][2]["headline"] = "A much longer headline than before, long enough to change the one size"
        with self.assertRaises(CV.CoverRefused) as ex:
            self.make_ad(job, only="h1")
        self.assertIn("Make every version again", str(ex.exception))

    def test_a_headline_on_a_face_is_a_problem_when_a_detector_is_given(self):
        got = self.make_ad(faces=lambda pic: [(400, 1200, 700, 1500)])              # a face inside the band
        self.assertFalse(got["ok"])
        self.assertIn("the headline sits on a face", got["covers"][0]["problems"])
        clear = self.make_ad(faces=lambda pic: [(400, 300, 700, 600)])
        self.assertTrue(clear["ok"])
        self.assertTrue(clear["covers"][0]["faces_checked"])

    def test_a_dry_run_spends_and_writes_nothing(self):
        got = self.make_ad(dry_run=True)
        self.assertEqual(len(got["requests"]), 3)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.out.exists())

    def test_one_requests_dry_run_reads_the_cover_out(self):
        import contextlib
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            _ok, resolved = IP.dry_run(self.req(), library=Library())
        self.assertIn("the cover", said.getvalue())
        self.assertIn("set by the tool's words step", said.getvalue())
        self.assertEqual(resolved["request"]["_cover"]["version"], "h1")
        self.assertFalse(self.out.exists())

    def test_a_request_with_no_type_fits_its_own_headline_and_a_given_type_is_used_exactly(self):
        long = "I asked ten women what they think about this one thing"
        req, *_ = self.resolve(self.req(cover={"headline": long}))
        self.assertLess(req["_cover"]["words"]["type"]["size_px"], 100)
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"headline": long, "type": {"size_px": 100, "max_lines": 1}}))
        self.assertIn("does not fit its band at 100 px", str(ex.exception))
        filed = self.root / "cover-type.json"
        filed.write_text(json.dumps({"ad": "ad-1", "type": CV.ad_type([long, "She said no"])}))
        req, *_ = self.resolve(self.req(cover={"type": str(filed)}))               # the ad's filed type, by file
        self.assertEqual(req["_cover"]["words"]["type"]["size_px"], CV.ad_type([long])["size_px"])

    def test_the_command_makes_the_ad_and_says_which_covers_are_fit_to_file(self):
        import contextlib
        import make
        f = self.root / "job.json"
        f.write_text(json.dumps(self.job()))
        said, err = io.StringIO(), io.StringIO()
        with mock.patch.object(IP.providers, "http_transport", door(self.calls)), contextlib.redirect_stdout(said):
            self.assertEqual(make.main(["covers", "--job", str(f), "--dry-run"]), 0)
            self.assertEqual(self.calls, [])
            self.assertEqual(make.main(["covers", "--job", str(f), "--no-mirror"]), 0)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(said.getvalue().count("\u2713"), 3)
        self.assertIn("covers.json", said.getvalue())
        job = self.job()
        job["versions"][0].pop("swipe")
        f.write_text(json.dumps(job))
        with contextlib.redirect_stderr(err):
            self.assertEqual(make.main(["covers", "--job", str(f)]), 2)
        self.assertIn("missing swipe", err.getvalue())

    def test_a_version_that_fails_never_stops_its_siblings_and_the_ad_says_so(self):
        n = []
        real = IP.providers.generate

        def flaky(entry, prompt, references, out, aspect, transport=None, key=None):
            n.append(1)
            if len(n) == 2:
                raise IP.providers.ProviderError("the door is down")
            return real(entry, prompt, references, out, aspect, transport=transport, key=key)
        with mock.patch.object(IP.providers, "generate", flaky):
            got = self.make_ad()
        self.assertFalse(got["ok"])
        self.assertEqual([f["version"] for f in got["failed"]], ["h1"])
        self.assertEqual([r["version"] for r in got["covers"]], ["control", "h2"])

    def test_rolled_back_the_picture_model_is_handed_the_words(self):
        self.t = table(words_step=False)
        _req, _ctx, prompt, *_ = self.resolve()
        self.assertIn('exactly these, spelled letter for letter: "She said no"', prompt)
        self.assertNotIn("NO WORDS ARE DRAWN", prompt)
        self.assertNotIn(IP.prompting.NO_WORDS, prompt)
        got = self.make()
        self.assertIsNone(got["cover"]["words"]["type"])
        self.assertNotIn("plate", got["cover"]["words"])


# ── 5. the frame is a frame of the version's own video, never a picture the tool made (row COVER-CHECKS) ───────────
class TheFrameIsFromItsOwnVideo(Workspace):
    def refused(self, says, **cover):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover=cover))
        self.assertIn(says, str(ex.exception))
        self.assertIn("Nothing was sent", str(ex.exception))
        return str(ex.exception)

    def test_a_frame_of_its_own_video_is_taken_and_recorded_with_the_video(self):
        req, *_ = self.resolve()
        sf = req["_cover"]["source_frame"]
        self.assertEqual(sf["video"], str(self.clip("ad-1_h1.mp4").resolve()))
        self.assertEqual(sf["video_sha256"], SG.sha(self.clip("ad-1_h1.mp4")))

    def test_someone_elses_picture_is_refused(self):
        other = picture(self.root / "frames" / "their-cover.png", (220, 30, 140))
        self.refused("is not a frame of the version's own video", frame=str(other))

    def test_a_resized_set_print_is_refused(self):
        from PIL import Image
        small = self.root / "frames" / "print-small.png"
        small.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(self.print) as im:
            im.resize((270, 480)).save(small)
        self.refused("is not a frame of the version's own video", frame=str(small))

    def test_a_16x9_picture_is_refused(self):
        wide = picture(self.root / "frames" / "wide.png", DEFAULT, size=(960, 540))
        self.refused("not the same picture shape", frame=str(wide))

    def test_a_missing_video_or_second_is_refused(self):
        self.refused("is not a file on this machine", video=str(self.root / "videos" / "gone.mp4"))
        req = self.req()
        req["cover"].pop("video")
        req["cover"].pop("t")
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(req)
        self.assertIn("missing video and t", str(ex.exception))

    def test_a_frame_from_another_versions_video_is_refused(self):
        theirs = self.frame("other-version.png", (10, 20, 30), "ad-1_control.mp4")
        self.refused("is not a frame of the version's own video", frame=str(theirs))

    def test_a_frame_of_the_clean_twin_is_its_own_video(self):
        video = self.clip("v9.mp4", (200, 200, 200))                                  # captions on: a different picture
        shutil.copy2(clip_of((90, 40, 10)), self.root / "videos" / "v9.clean.mp4")
        clean = grab(self.root / "videos" / "v9.clean.mp4", self.root / "frames" / "v9.png")
        req, *_ = self.resolve(self.req(cover={"frame": str(clean), "video": str(video)}))
        self.assertEqual(str(req["_cover"]["source_frame"]["file"]), str(clean))

    def test_switched_off_the_video_is_optional_and_unchecked(self):
        self.t = table(own_video=False)
        req = self.req()
        req["cover"].pop("video")
        other = picture(self.root / "frames" / "their-cover.png", (220, 30, 140))
        req["cover"]["frame"] = str(other)
        self.resolve(req)
        with mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": "own_video"}):
            self.t = table()
            self.resolve(req)


class TheFrameIsNotOurs(Workspace):
    def test_a_covers_own_plate_fed_back_as_a_frame_is_refused(self):
        got = self.make()
        plate = Path(got["cover"]["words"]["plate"])
        with self.assertRaises(IP.BadRequest) as ex:                                 # where the job wrote it
            self.resolve(self.req(cover={"frame": str(plate)}))
        self.assertIn("generated/ folder", str(ex.exception))
        moved = self.root / "frames" / "h2-frame.png"                                # copied out of the run
        shutil.copy2(plate, moved)
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"frame": str(moved), "version": "h2"}))
        self.assertIn("a picture we made", str(ex.exception))
        self.assertIn("ledger", str(ex.exception))

    def test_a_delivered_cover_copied_elsewhere_is_refused(self):
        got = self.make()
        copied = self.root / "elsewhere" / "cover.png"
        copied.parent.mkdir()
        shutil.copy2(got["delivered"][0], copied)
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"frame": str(copied), "version": "h2"}))
        self.assertIn("ledger", str(ex.exception))

    def test_with_no_ledger_the_run_record_beside_it_says_so(self):
        got = self.make()
        plate = Path(got["cover"]["words"]["plate"])
        beside = self.out / "next-frame.png"                                         # beside run.json, ledger empty
        shutil.copy2(plate, beside)
        empty = self.root / "empty-ledger.jsonl"
        empty.write_text("")
        with mock.patch.dict(os.environ, {"IMAGE_MADE_LEDGER": str(empty)}):
            with self.assertRaises(IP.BadRequest) as ex:
                self.resolve(self.req(cover={"frame": str(beside), "version": "h2"}))
        self.assertIn("recorded as a made picture in run.json", str(ex.exception))

    def test_a_cover_record_beside_the_frame_is_refused(self):
        frame = self.frame("ours.png", (5, 90, 5))
        frame.with_suffix(".cover.json").write_text("{}")
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"frame": str(frame), "video": str(self.clip("clip-055a05.mp4", (5, 90, 5)))}))
        self.assertIn("a cover record sits beside it", str(ex.exception))

    def test_the_versions_own_frame_beside_its_last_cover_is_still_taken(self):
        """The line keeps a version's frame in that version's cover folder: remaking the cover reads it again."""
        frame = self.frame("h1_frame.png")
        mine = self.out / "h1_frame.png"
        self.out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(frame, mine)
        self.make(self.req(cover={"frame": str(mine)}))
        self.resolve(self.req(cover={"frame": str(mine)}))

    def test_switched_off_only_a_recipe_beside_it_counts(self):
        got = self.make()
        copied = self.root / "elsewhere" / "cover.png"
        copied.parent.mkdir()
        shutil.copy2(got["delivered"][0], copied)
        self.t = table(frame_not_made=False, own_video=False)
        self.resolve(self.req(cover={"frame": str(copied), "version": "h2"}))


class TheVideoIsAVideo(Workspace):
    """A still picture is never the version's video: ffmpeg reads a picture as a one-frame input (round 2, probe A)."""
    def test_someone_elses_picture_sent_as_the_video_is_refused(self):
        theirs = picture(self.root / "elsewhere" / "theirs.png", (220, 30, 140), size=(270, 480))
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"frame": str(theirs), "video": str(theirs), "t": 0}))
        self.assertIn("is a picture file, not a video", str(ex.exception))
        self.assertIn("Nothing was sent", str(ex.exception))

    def test_a_picture_renamed_as_a_video_is_refused(self):
        theirs = picture(self.root / "elsewhere" / "theirs.png", (220, 30, 140), size=(270, 480))
        named = self.root / "elsewhere" / "theirs.mp4"
        shutil.copy2(theirs, named)
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"frame": str(theirs), "video": str(named), "t": 0}))
        self.assertIn("is a still picture, not a video", str(ex.exception))

    def test_a_second_past_the_videos_end_is_refused(self):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"t": 9}))
        self.assertIn("is 3 s long, so it has no frame at 9 s", str(ex.exception))

    def test_a_real_video_is_taken(self):
        self.assertIsNone(CV.not_a_video(self.clip("ad-1_h1.mp4"), 1.5))
        self.resolve()

    def test_switched_off_a_still_picture_reads_as_a_video_as_before(self):
        theirs = picture(self.root / "elsewhere" / "theirs.png", (220, 30, 140), size=(270, 480))
        with mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": "video_stream"}):
            self.resolve(self.req(cover={"frame": str(theirs), "video": str(theirs), "t": 0}))


def textured_clip(dest, size=(270, 480)):
    """A 3-second stand-in video with detail in it (ffmpeg's test pattern), so a copy can be told from a new picture."""
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=%dx%d:rate=10:duration=3" % size, "-pix_fmt", "yuv420p", str(dest)],
                   check=True, capture_output=True)
    return Path(dest)


def keeps_the_moment(frame, calls):
    """A picture door whose model keeps the moment: it answers with the frame itself, at the made size (probe L)."""
    from PIL import Image
    buf = io.BytesIO()
    with Image.open(frame) as im:
        im.convert("RGB").resize((1152, 2048), Image.LANCZOS).save(buf, "PNG")
    blob = base64.b64encode(buf.getvalue()).decode()

    def t(method, url, headers, body):
        calls.append({"url": url})
        return 200, {"x-request-id": "stub"}, json.dumps({"data": [{"b64_json": blob}]}).encode()
    return t


def redrawn(frame, calls):
    """A picture door whose model redraws the scene: the frame mirrored and recoloured, at the made size."""
    from PIL import Image, ImageOps
    buf = io.BytesIO()
    with Image.open(frame) as im:
        ImageOps.mirror(ImageOps.invert(im.convert("RGB"))).resize((1152, 2048)).save(buf, "PNG")
    blob = base64.b64encode(buf.getvalue()).decode()

    def t(method, url, headers, body):
        calls.append({"url": url})
        return 200, {"x-request-id": "stub"}, json.dumps({"data": [{"b64_json": blob}]}).encode()
    return t


class TheFrameIsNotOursByLook(Workspace):
    """A re-saved or re-encoded copy of a cover or its plate is refused as a frame (round 2, probes L and D)."""
    def setUp(self):
        super().setUp()
        self.video = textured_clip(self.root / "videos" / "ad-1_h1.mp4")
        self.own = grab(self.video, self.root / "frames" / "h1.png")

    def made(self, transport=None):
        req = self.req(cover={"frame": str(self.own), "video": str(self.video)})
        return IP.make(req, library=Library(), transport=transport or keeps_the_moment(self.own, self.calls),
                       mirror=False)

    def copy(self, src, name, grade=None, blur=0, quality=90):
        from PIL import Image, ImageEnhance, ImageFilter
        dest = self.root / "elsewhere" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert("RGB").resize((270, 480), Image.LANCZOS)
            if grade:
                im = ImageEnhance.Contrast(ImageEnhance.Brightness(im).enhance(grade[0])).enhance(grade[1])
            if blur:
                im = im.filter(ImageFilter.GaussianBlur(blur))
            im.save(dest, "JPEG", quality=quality)
        return dest

    def refused(self, frame, **cover):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(cover={"frame": str(frame), "video": str(self.video), "version": "h2", **cover}))
        self.assertIn("looks like a cover or plate the tool made", str(ex.exception))
        self.assertIn("Nothing was sent", str(ex.exception))

    def test_a_cover_resaved_as_a_jpeg_in_another_folder_is_refused(self):
        got = self.made()
        self.refused(self.copy(got["delivered"][0], "cover.jpg"))

    def test_a_regraded_blurred_reencoded_copy_of_the_cover_is_refused(self):
        got = self.made()
        self.refused(self.copy(got["delivered"][0], "graded.jpg", grade=(1.15, 1.2), blur=1.2, quality=80))

    def test_a_resaved_plate_of_a_redrawn_cover_is_refused(self):
        got = self.made(redrawn(self.own, self.calls))
        self.refused(self.copy(got["cover"]["words"]["plate"], "plate.jpg"))

    def test_the_cover_record_and_its_ledger_line_carry_the_looks(self):
        got = self.made()
        self.assertEqual(set(got["cover"]["looks"]), {"cover", "plate", "source"})
        from image_production import provenance as PV
        rows = [json.loads(x) for x in PV.ledger_path().read_text().splitlines()]
        self.assertEqual(rows[-1]["looks"], got["cover"]["looks"])

    def test_the_versions_own_frame_is_still_taken_after_its_cover_was_made(self):
        self.made()
        again = grab(self.video, self.root / "frames" / "h1-again.jpg")              # the line grabs a jpg
        self.resolve(self.req(cover={"frame": str(again), "video": str(self.video)}))
        near = grab(self.video, self.root / "frames" / "h1-near.png", at=1.6)
        self.resolve(self.req(cover={"frame": str(near), "video": str(self.video), "t": 1.6}))

    def test_a_frame_at_another_second_is_taken_when_the_model_kept_the_moment(self):
        # the plate is almost the source frame, so "nearer the plate than its source" is a near-tie (round 3, probe2):
        # a real frame of the version's own video at its second is what decides, grabbed and compared
        got = self.made()
        folder = Path(got["delivered"][0]).parent
        for at in (0.5, 1.0, 2.0, 2.5):
            f = grab(self.video, folder / "h1_frame.jpg", at=at)                       # the line's layout
            self.resolve(self.req(cover={"frame": str(f), "video": str(self.video), "t": at}))
            sister = grab(self.video, self.root / "frames" / "h2_frame.jpg", at=at)
            self.resolve(self.req(cover={"frame": str(sister), "video": str(self.video), "t": at, "version": "h2"}))

    def test_a_copy_of_the_cover_is_refused_even_when_the_video_holds_that_moment(self):
        got = self.made()
        self.refused(self.copy(got["delivered"][0], "cover.jpg"), t=1.5)
        self.refused(self.copy(got["delivered"][0], "graded.jpg", grade=(1.15, 1.2), blur=1.2, quality=80), t=1.5)

    def test_with_no_video_named_the_source_frame_still_decides(self):
        got = self.made()
        copied = self.copy(got["delivered"][0], "cover.jpg")
        self.assertIsNotNone(CV.made_here(copied))
        self.assertIsNotNone(CV.made_here(copied, video=self.video, at=1.5))

    def test_with_no_ledger_the_looks_in_the_run_record_beside_it_say_so(self):
        got = self.made()
        beside = self.out / "next-frame.jpg"
        shutil.copy2(self.copy(got["delivered"][0], "cover.jpg"), beside)
        empty = self.root / "empty-ledger.jsonl"
        empty.write_text("")
        with mock.patch.dict(os.environ, {"IMAGE_MADE_LEDGER": str(empty)}):
            self.refused(beside)

    def test_a_picture_with_no_detail_is_told_by_its_bytes_not_its_look(self):
        flat = CV._vector(CV.look(picture(self.root / "flat-a.png", (40, 40, 40), size=(270, 480))))
        near = CV._vector(CV.look(picture(self.root / "flat-b.png", (42, 42, 42), size=(270, 480))))
        self.assertIsNone(CV.apart(flat, near))
        rich = CV._vector(CV.look(self.own))
        self.assertIsNone(CV.apart(rich, flat))
        self.assertLess(CV.apart(rich, rich), 0.001)

    def test_switched_off_a_reencoded_copy_is_judged_by_its_bytes_alone_as_before(self):
        got = self.made()
        copied = self.copy(got["delivered"][0], "cover.jpg")
        self.assertIsNone(CV.made_here(copied, table(made_look=False)))
        with mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": "made_look"}):
            self.assertIsNone(CV.made_here(copied))
        self.assertIsNotNone(CV.made_here(copied))


class TheSingleRequestStopsOnAnUnfitCover(Workspace):
    """`make.py` with one cover request exits non-zero when the cover it delivered is not `ok`, so the video line,
    which files whatever exits 0, stops on it (round 2, probes J and K)."""
    def run_make(self):
        import contextlib
        import make
        argv = ["--purpose", "cover", "--brand", "b", "--version", "h1", "--frame", str(self.frame()),
                "--swipe", "swipe-042", "--headline", "She said no", "--out", str(self.out), "--set", "lineup",
                "--ad", "ad-1", "--video", str(self.clip("ad-1_h1.mp4")), "--frame-at", "1.5", "--no-mirror",
                "--direction", "her face close, mid-reaction"]
        err = io.StringIO()
        with mock.patch.object(IP.providers, "http_transport", door(self.calls)), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = make.main(argv)
        return code, err.getvalue()

    def test_a_headline_on_a_face_exits_non_zero(self):
        with mock.patch.object(CV, "face_reader", lambda: (lambda pic: [(0.0, 0.0, 1080.0, 1920.0)])):
            code, err = self.run_make()
        self.assertEqual(code, 1)
        self.assertIn("not fit to file", err)
        self.assertIn("the headline sits on a face", err)

    def test_faces_never_read_exits_non_zero(self):
        with mock.patch.object(CV, "face_reader", lambda: None):
            code, err = self.run_make()
        self.assertEqual(code, 1)
        self.assertIn("faces not checked", err)

    def test_a_fit_cover_exits_zero(self):
        code, err = self.run_make()
        self.assertEqual(code, 0, err)

    def test_switched_off_an_unfit_cover_exits_zero_as_before(self):
        with mock.patch.object(CV, "face_reader", lambda: None), \
                mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": "unfit_exit"}):
            code, _ = self.run_make()
        self.assertEqual(code, 0)


# ── 6. one type per ad on the single request ─────────────────────────────────────────────────────────────────────────
class OneTypePerAdOnTheSingleRequest(Workspace):
    LONG = "I asked ten women what they think about this one thing"

    def single(self, version, headline, colour, **cover):
        video = self.clip(f"ad-1_{version}.mp4", colour)
        frame = self.frame(f"{version}.png", colour, f"ad-1_{version}.mp4")
        c = {"version": version, "headline": headline, "frame": str(frame), "video": str(video)}
        c.update(cover)
        return self.make(self.req(out=str(self.out / version), cover=c))

    def test_two_single_requests_of_one_ad_come_out_in_one_type(self):
        a = self.single("h1", self.LONG, (40, 50, 60))
        b = self.single("h2", "She said no", (70, 80, 90))
        ta, tb = a["cover"]["words"]["type"], b["cover"]["words"]["type"]
        self.assertEqual(ta["size_px"], tb["size_px"])
        self.assertEqual(ta, tb)
        filed = json.loads((self.out / "cover-type.json").read_text())
        self.assertEqual((filed["ad"], filed["type"]), ("ad-1", ta))
        self.assertEqual(b["cover"]["words"]["type_file"]["from"], "filed")

    def test_a_later_headline_that_does_not_fit_the_ads_type_is_refused_and_names_the_job(self):
        self.single("h1", "She said no", (40, 50, 60))
        with self.assertRaises(IP.BadRequest) as ex:
            self.single("h2", self.LONG, (70, 80, 90))
        self.assertIn("does not fit the ad's type", str(ex.exception))
        self.assertIn("make.py covers --job", str(ex.exception))
        self.assertEqual(len(self.calls), 1)

    def test_a_single_request_with_no_ad_and_no_type_is_refused(self):
        req = self.req()
        req["cover"].pop("ad")
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(req)
        self.assertIn("names no ad", str(ex.exception))
        self.t = table(one_type=False)
        self.resolve(req)

    def test_a_type_file_of_another_ad_is_refused(self):
        (self.out).mkdir(parents=True)
        (self.root / "cover-type.json").write_text(json.dumps({"ad": "ad-9", "type": CV.default_type()}))
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve()
        self.assertIn("is for another ad (ad-9)", str(ex.exception))

    def test_a_dry_run_files_no_type(self):
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            IP.dry_run(self.req(out=str(self.out / "h1")), library=Library())
        self.assertFalse((self.out / "cover-type.json").exists())


# ── 7. the faces under the words are read; a cover whose faces were not read is not fit to file ─────────────────────
class TheFacesAreRead(Workspace):
    def test_the_single_request_reads_the_plate_and_records_it(self):
        got = self.make()
        c = got["cover"]
        self.assertEqual(self.faces_seen[-1], c["words"]["plate"])                 # the plate: no words hide a face
        self.assertEqual(self.faces_seen[:-1], [c["source_frame"]["file"], c["file"]])  # frame and made picture: faces kept
        self.assertTrue(c["faces_checked"])
        self.assertTrue(c["ok"])
        beside = json.loads(Path(got["delivered"][0]).with_suffix(".cover.json").read_text())
        self.assertTrue(beside["ok"])

    def test_no_face_reader_means_not_fit_to_file(self):
        with mock.patch.object(CV, "face_reader", lambda: None):
            got = self.make()
            ad = self.make_ad()
        self.assertFalse(got["cover"]["ok"])
        self.assertIn("faces not checked", "; ".join(got["cover"]["problems"]))
        beside = json.loads(Path(got["delivered"][0]).with_suffix(".cover.json").read_text())
        self.assertFalse(beside["ok"])
        self.assertFalse(ad["ok"])
        self.assertTrue(all(not r["ok"] and not r["faces_checked"] for r in ad["covers"]))

    def test_a_reader_that_stops_means_not_fit_to_file(self):
        def broken(picture):
            raise OSError("no Vision here")
        got = self.make_ad(faces=broken)
        self.assertFalse(got["ok"])
        self.assertIn("the face reader stopped (OSError", got["covers"][0]["problems"][0])

    def test_a_face_under_the_words_on_the_plate_is_a_problem(self):
        with mock.patch.object(CV, "face_reader", lambda: (lambda pic: [(400.0, 1200.0, 700.0, 1500.0)])):
            got = self.make()
        self.assertFalse(got["cover"]["ok"])
        self.assertIn("the headline sits on a face", got["cover"]["problems"])

    def test_switched_off_a_cover_with_no_reader_can_be_fit(self):
        self.t = table(faces=False)
        with mock.patch.object(CV, "face_reader", lambda: None):
            got = self.make_ad()
        self.assertTrue(got["ok"], got)

    def test_the_command_line_uses_the_local_reader(self):
        import contextlib
        import make
        f = self.root / "job.json"
        f.write_text(json.dumps(self.job()))
        with mock.patch.object(IP.providers, "http_transport", door(self.calls)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(make.main(["covers", "--job", str(f), "--no-mirror"]), 0)
        self.assertEqual(len(self.faces_seen), 9)              # each version: its frame and made picture (faces kept), its plate

    def test_the_frame_prompt_moves_faces_out_of_the_word_band(self):
        _req, _ctx, prompt, *_ = self.resolve()
        said = " ".join(prompt.split())
        self.assertIn("any face, lips or hands inside the band kept clear for the words move out of that band", said)
        self.assertNotIn("the same people in the same places, the same framing", said)


class TheFaceReader(unittest.TestCase):
    def test_the_scene_tools_shares_become_pixel_boxes_for_faces_and_lips(self):
        from image_production import face_read as FR
        row = {"faces": [{"box": {"x": 0.25, "y": 0.5, "w": 0.5, "h": 0.25},
                          "lips": {"x": 0.4, "y": 0.65, "w": 0.2, "h": 0.05}}], "hands": []}
        self.assertEqual(FR.boxes(row, (1080, 1920)), [(270.0, 960.0, 810.0, 1440.0), (432.0, 1248.0, 648.0, 1344.0)])

    def test_the_reader_is_the_edit_lines_vision_tool(self):
        from image_production import face_read as FR
        if not FR.source().is_file():
            self.skipTest("components/video-edit/machine/vision is not in this checkout")
        self.assertTrue(str(FR.source()).endswith("video-edit/machine/vision/scene.swift"))
        if shutil.which("swiftc") or (FR.source().parent / ".build" / "scene").is_file():
            self.assertTrue(callable(FR.reader()))


# ── 8. the swipe is a real cover; with no direction its rated move is the concept ───────────────────────────────────
class TheSwipeCarriesAConcept(Workspace):
    def test_a_placeholder_swipe_id_is_refused_even_with_a_direction(self):
        for bad in ("none", "None.", "TBD", "x", "?", "swipe", "n/a", "  "):
            with self.assertRaises(IP.BadRequest, msg=bad) as ex:
                self.resolve(self.req(cover={"swipe": bad}))
            self.assertTrue("placeholder" in str(ex.exception) or "missing swipe" in str(ex.exception), bad)

    def test_an_unknown_swipe_with_no_direction_is_refused(self):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(direction=None, cover={"swipe": "ig-NOTINDEX"}))
        self.assertIn("has no move for its swipe (ig-NOTINDEX)", str(ex.exception))

    def test_a_swipe_whose_move_is_not_rated_with_no_direction_is_refused(self):
        self.index([{"id": "ig-PLAIN1", "move": "as-shot"}, {"id": "ig-UNRATED", "move": "unrated"}])
        for swipe in ("ig-PLAIN1", "ig-UNRATED"):
            with self.assertRaises(IP.BadRequest):
                self.resolve(self.req(direction=None, cover={"swipe": swipe}))

    def test_a_rated_swipe_with_no_direction_carries_its_move(self):
        req, _ctx, prompt, *_ = self.resolve(self.req(direction=None))
        self.assertIn("taken from a real cover this audience already sees: wrong scale.", req["direction"])

    def test_a_direction_brings_its_own_concept(self):
        self.resolve(self.req(cover={"swipe": "ig-NOTINDEX"}))

    def test_switched_off_any_swipe_is_taken(self):
        self.t = table(swipe_concept=False)
        self.resolve(self.req(direction=None, cover={"swipe": "ig-NOTINDEX"}))
        self.resolve(self.req(cover={"swipe": "none"}))


class TheCount(Workspace):
    def test_a_count_that_is_not_a_number_is_a_refusal(self):
        with self.assertRaises(IP.BadRequest) as ex:
            self.resolve(self.req(count="two"))
        self.assertIn("`count` is a number", str(ex.exception))


class TheType(unittest.TestCase):
    @unittest.skipUnless(HAVE_FACE, "the type library is not in this checkout")
    def test_the_default_type_is_whole_and_inside_the_safe_zone(self):
        style = CV.type_of()
        self.assertEqual(W.check_type(style), [])
        self.assertTrue(W.face_file(style["face"]).is_file())

    @unittest.skipUnless(HAVE_FACE, "the type library is not in this checkout")
    def test_fit_gives_one_size_and_layout_draws_nothing(self):
        style = CV.type_of()
        px = W.fit(["Short", "A longer headline that has to wrap onto a few lines to fit the band"], style)
        self.assertLessEqual(px, style["size_px"])
        self.assertGreaterEqual(px, style["min_size_px"])
        self.assertEqual(W.layout("Short", style, px=px)["size_px"], px)

    def test_the_switches_read_the_table_and_the_machine(self):
        self.assertTrue(CV.on("words_step", {"gate": {}}))                           # no block: the job is on
        self.assertFalse(CV.on("words_step", {"gate": {"cover": {"words_step": False}}}))
        self.assertFalse(CV.on("source_frame", {"gate": {"cover": {"on": False}}}))
        with mock.patch.dict(os.environ, {"IMAGE_COVER_OFF": "product_with_set"}):
            self.assertFalse(CV.on("product_with_set", {"gate": {}}))
            self.assertTrue(CV.on("words_step", {"gate": {}}))

    def test_the_real_table_has_every_switch_on(self):
        cfg = CV.config(IP.route.table(house=False))
        self.assertTrue(cfg.get("on"))
        self.assertTrue(all(cfg.get(p) for p in CV.PARTS))


if __name__ == "__main__":
    unittest.main(verbosity=1)
