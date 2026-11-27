"""covers_stage: after the versions render, the Studio makes every version's cover itself and hands them to the filer.
Nothing here is paid: the image tool, the cover index, the face reader, the frame grab, the cast face check, the
filer's gate, the filed 3D sets and the card tree are fakes or scratch folders. The card's own cover checks (meta-upload cover_rule) run for real on what the stage hands off.

    python3 -m unittest test_covers_stage      (from components/video-studio)
"""
import hashlib
import json
import os
import random
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from PIL import Image

import covers_stage as CS
import video_studio as VS
import checks_board as CB


def noise(path, seed, size=(90, 160)):
    """A picture no other seed makes (a distinct picture hash)."""
    rnd = random.Random(seed)
    im = Image.new("L", (9, 8))
    im.putdata([rnd.randrange(256) for _ in range(72)])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.resize(size, Image.NEAREST).convert("RGB").save(path)


def fake_grab(video, t, dest):
    noise(dest, "%s@%s" % (Path(video).name, t))
    return True


def fake_read(frames):
    """A face that is largest at 2.5 s in every opener; the cover pictures have one small face up top."""
    out = []
    for f in frames:
        name = Path(f).name
        if name.startswith("t0"):
            k = int(name[1:3])
            out.append({"faces": [{"x": .3, "y": .2, "w": .1 * (k + 1) if k <= 2 else .1, "h": .2}]})
        else:
            out.append({"faces": [{"x": .4, "y": .1, "w": .2, "h": .15}]})
    return out


def find_avatar(avatar, limit):
    return {"scope": "avatar", "avatar": avatar, "note": "", "covers": [
        {"id": "sw-plain", "move": "as-shot", "likes": 90000},
        {"id": "sw-scale", "move": "wrong-scale", "likes": 5000, "move_why": "a mug the size of a door"},
        {"id": "sw-face", "move": "face-at-limit", "likes": 4000},
        {"id": "sw-odd", "move": "one-odd-thing", "likes": 3000},
        {"id": "sw-lit", "move": "line-shown-literally", "likes": 2000},
        {"id": "sw-named", "move": "thing-to-lens", "likes": 1000}]}


def kept_print(brand, name):
    """The filed 3D sets: only `kitchen-set` has a kept print."""
    return "/sets/kitchen-set/print-v1.png" if name == "kitchen-set" else None


def gate_reads_all(ps):
    """The filer's gate (GATE-5), on: every picture is found in an image-production record."""
    return {p: {"sha256": "x", "record": "run.json"} for p in ps}, []


class FakeTool:
    """image production's cover job: writes each version's cover, its record and the ad's covers.json."""

    def __init__(self, same=None):
        self.calls, self.same = [], dict(same or {})

    def __call__(self, job_path, only):
        job = json.loads(Path(job_path).read_text())
        self.calls.append({"only": only, "versions": [dict(v) for v in job["versions"]]})
        out = Path(job["out"])
        old = json.loads((out / "covers.json").read_text())["covers"] if only and (out / "covers.json").exists() else []
        rows = [r for r in old if r["version"] not in (only or [])]
        for v in job["versions"]:
            if only and v["version"] not in only:
                continue
            slug = CS._slug(v["version"])
            pic = out / slug / ("cover-%s-%s-01.png" % (CS._slug(job["ad"]), slug))
            seed = self.same.pop(v["version"], None) or "%s|%s|%s" % (v["version"], v["frame"], len(self.calls))
            noise(pic, seed, size=(1080, 1920))
            rec = {"version": v["version"], "ad": job["ad"], "headline": v["headline"], "swipe": v["swipe"],
                   "source_frame": {"file": v["frame"], "video": v["video"], "t": v["t"]},
                   "words": {"box_px": [100, 1500, 980, 1700]}, "file": str(pic),
                   "sha256": hashlib.sha256(pic.read_bytes()).hexdigest(), "ok": True, "problems": []}
            pic.with_suffix(".cover.json").write_text(json.dumps(rec))
            rows.append(rec)
        (out / "covers.json").write_text(json.dumps({"ok": True, "covers": rows, "failed": [], "problems": []}))
        return 0, "made"


class Production(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.root = Path(self.d.name)
        self.briefs = self.root / "briefs"
        self.B = self.briefs / "p1"
        cast = self.root / "cast" / "acme" / "casting" / "host" / "full"
        cast.mkdir(parents=True)
        noise(cast / "master.png", "host")
        (self.root / "meta").mkdir()
        (self.root / "index").mkdir()
        # one cover index for the stage and the filer, as on a real machine: the avatar's covers are rows of it, so
        # the card's swipe check (meta-upload cover_rule, META_COVER_INDEX) reads the same ids the stage picked
        (self.root / "index" / "covers.json").write_text(json.dumps(
            [dict(c, avatar="busy-dad") for c in find_avatar("busy-dad", None)["covers"]]))
        self.env = mock.patch.dict(os.environ, {"VIDEO_STUDIO_CASTING": str(self.root / "cast"),
                                                "META_CARDS_ROOT": str(self.root / "meta"),
                                                "VIDEO_STUDIO_COVER_INDEX": str(self.root / "index"),
                                                "META_COVER_INDEX": str(self.root / "index")})
        self.env.start()
        CS._CARDS.clear()
        self.B.mkdir(parents=True)
        brief = {"brief": "acme-brief-1", "brief_key": "acme_widget_brief-0001", "order": ["S1", "S2"],
                 "hooks": ["H2", "H3"], "picks": {"S1": "take-1", "S2": "take-1", "H2": "take-1", "H3": "take-1"},
                 "shot_fill": {"brand": "acme"}, "audience": {"avatar": "busy-dad"}, "cast": ["host"]}
        (self.B / "brief.json").write_text(json.dumps(brief))
        for s, words in (("S1", "Would you try it? Look at this rash. Nope."),
                         ("H2", "Would you try it? Why is he scratching? Nope."),
                         ("H3", "Would you try it? What is under this beard, man, honestly, tell me right now please?")):
            (self.B / "scenes" / s).mkdir(parents=True)
            (self.B / "scenes" / s / "take-1.json").write_text(json.dumps({"words": words, "steps": [],
                                                                          "set": "kitchen-set" if s == "S1" else None}))
        for f in ("rough-cut-v1-sdr.mp4", "versions/H2/p1-H2.mp4", "versions/H3/p1-H3.mp4"):
            (self.B / f).parent.mkdir(parents=True, exist_ok=True)
            (self.B / f).write_bytes(b"video " + f.encode())
        self.vers = [{"id": "control", "label": "Control", "file": "p1/rough-cut-v1-sdr.mp4"},
                     {"id": "H2", "label": "V2", "file": "p1/versions/H2/p1-H2.mp4"},
                     {"id": "H3", "label": "V3", "file": "p1/versions/H3/p1-H3.mp4"}]
        self.said = []

    def tearDown(self):
        self.env.stop()
        self.d.cleanup()

    def run_stage(self, tool=None, find=find_avatar, face=None, **kw):
        self.tool = tool or FakeTool()
        kw.setdefault("refuse", gate_reads_all)
        kw.setdefault("kept", kept_print)
        kw.setdefault("cards", lambda brand, key: [])
        kw.setdefault("read", fake_read)
        kw.setdefault("grab_", fake_grab)
        return CS.run("p1", B=self.B, vers=self.vers, make=self.tool, find=find,
                      face_check=face or (lambda p, m: {"pass": True, "people": [{"master": m[0], "verdict": "SAME"}]}),
                      say=lambda *a: self.said.append(a), **kw)

    def brief(self, **change):
        b = json.loads((self.B / "brief.json").read_text())
        b.update(change)
        (self.B / "brief.json").write_text(json.dumps(b))

    def rerender(self, *files):
        for f in files or [x["file"].split("/", 1)[1] for x in self.vers]:
            (self.B / f).write_bytes(b"a new render of " + f.encode() + os.urandom(4))

    def hand(self):
        return json.loads((self.B / "covers" / "to-file.json").read_text())


class TheStage(Production):
    def test_every_version_gets_its_own_cover_in_one_job_and_goes_to_the_filer(self):
        st = self.run_stage()
        self.assertTrue(st["ready"], [r.get("held") for r in st["versions"]])
        self.assertEqual(len(self.tool.calls), 1)                         # one job, every version side by side
        sent = self.tool.calls[0]["versions"]
        self.assertEqual([v["version"] for v in sent], ["control", "H2", "H3"])
        self.assertEqual(len({v["frame"] for v in sent}), 3)              # three moments, one per version
        self.assertTrue(all(v["t"] == 2.5 for v in sent))                # the closest face of each opener
        self.assertEqual([v["swipe"] for v in sent], ["sw-scale", "sw-face", "sw-odd"])   # moves first, no repeats
        self.assertEqual([v["video"] for v in sent], [str((self.briefs / x["file"]).resolve()) for x in self.vers])
        self.assertEqual([v["headline"] for v in sent],                  # the line each opener alone says
                         ["Look at this rash.", "Why is he scratching?", "What is under this beard"])
        self.assertEqual(st["avatar"], "busy-dad")
        self.assertIn("a mug the size of a door", sent[0]["direction"])  # the concept rides in the direction
        job = json.loads((self.B / "covers" / "job.json").read_text())
        self.assertTrue(job["people"])
        self.assertEqual(job["set"], "kitchen-set")                       # the set its own take was made from
        self.assertTrue(job["references"][0].endswith("host/full/master.png"))
        hand = self.hand()
        self.assertTrue(hand["ready"])
        self.assertEqual(hand["media"], [v["video"] for v in sent])
        self.assertTrue(all(Path(t).is_file() for t in hand["thumbs"]))
        self.assertTrue(all(Path(c).is_file() for c in hand["cover_records"]))
        self.assertEqual([s[1] for s in self.said if s[0] == "file"][-1], "done")

    def test_the_card_checks_pass_on_what_is_handed_off(self):
        st = self.run_stage()
        self.assertEqual(set(st["card_checks"]), {"cover_each", "cover_swipe", "cover_frame", "cover_differs"})
        self.assertTrue(all(c["ok"] for c in st["card_checks"].values()), st["card_checks"])
        import importlib.util
        spec = importlib.util.spec_from_file_location("cr", CS.ST.part("meta-upload") / "cover_rule.py")
        cr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cr)
        hand = self.hand()
        recs = cr.for_filing([(m, Path(m).name, t, Path(t).name) for m, t in zip(hand["media"], hand["thumbs"])],
                             hand["cover_records"])
        for m, t in zip(hand["media"], hand["thumbs"]):
            self.assertEqual(recs[Path(t).name]["frame"]["video"], Path(m).name)   # its own video, by the card's name
            self.assertTrue(recs[Path(t).name]["swipe"].startswith("sw-"))

    def test_the_board_says_what_it_picked_and_why_for_each_version(self):
        self.run_stage()
        b = CS.state("p1", self.B)
        self.assertTrue(b["made"] and b["ready"])
        for v in b["versions"]:
            self.assertIn("closest face", v["frame"]["why"])
            self.assertTrue(v["frame"]["url"].startswith("/files/p1/covers/"))
            self.assertIn("busy-dad", v["swipe"]["why"])
            self.assertTrue(v["headline_why"])
            self.assertTrue(v["direction"])
            self.assertTrue(v["cover"].startswith("/files/p1/covers/made/"))
            self.assertEqual(sum(f["picked"] for f in v["sweep"]), 1)
            self.assertTrue({"faces", "differs", "made by the tool", "words off faces"} <= {c["name"] for c in v["checks"]})
        self.assertIn("the other versions do not say", b["versions"][1]["headline_why"])

    def test_no_explore_pull_for_the_avatar_holds_and_spends_nothing(self):
        st = self.run_stage(find=lambda a, n: {"scope": "general-fallback", "note": "busy-dad has no covers",
                                               "covers": [{"id": "general-1", "move": "wrong-scale"}]})
        self.assertEqual(self.tool.calls, [])                           # the image tool was never called
        self.assertFalse(st["ready"])
        hand = self.hand()
        self.assertEqual(hand["thumbs"], ["", "", ""])
        self.assertIn("Pull that avatar's Explore feed", hand["held"][0]["why"])

    def test_a_refusal_from_the_tool_is_said_as_it_is(self):
        st = self.run_stage(tool=lambda job, only: (2, "refuses these covers: no filed 3D set for acme"))
        self.assertFalse(st["ready"])
        self.assertIn("no filed 3D set", self.hand()["held"][0]["why"])

    def test_a_face_that_fails_the_cast_is_made_again_then_held(self):
        face = lambda p, m: {"pass": "/h2/" not in p, "people": [{"master": m[0], "verdict": "DIFFERENT"}]}  # noqa: E731
        st = self.run_stage(face=face)
        self.assertEqual(len(self.tool.calls), 2)
        self.assertEqual(self.tool.calls[1]["only"], ["H2"])             # only the miss is made again
        first = {v["version"]: v for v in self.tool.calls[0]["versions"]}["H2"]
        second = {v["version"]: v for v in self.tool.calls[1]["versions"]}["H2"]
        self.assertNotEqual(first["t"], second["t"])                     # from the next-strongest moment
        self.assertNotEqual(first["swipe"], second["swipe"])             # following the next swipe
        h2 = {r["version"]: r for r in st["versions"]}["H2"]
        self.assertFalse(h2["ready"])
        self.assertIn("faces", h2["held"])
        hand = self.hand()
        self.assertFalse(hand["ready"])
        self.assertEqual(hand["thumbs"], ["", "", ""])                   # a partial set is never handed over
        self.assertEqual(hand["withheld"], ["control", "H3"])            # ready, kept back until H2 is

    def test_two_versions_with_the_same_picture_are_told_apart(self):
        tool = FakeTool(same={"control": "twin", "H3": "twin"})
        st = self.run_stage(tool=tool)
        self.assertEqual(tool.calls[1]["only"], ["H3"])
        self.assertTrue(st["ready"], [r.get("held") for r in st["versions"]])

    def test_the_ads_own_choices_win(self):
        b = json.loads((self.B / "brief.json").read_text())
        b["covers"] = {"H2": {"headline": "Rash? Gone.", "swipe": "sw-named", "at": 4.0}, "product": "widget"}
        (self.B / "brief.json").write_text(json.dumps(b))
        self.run_stage()
        sent = {v["version"]: v for v in self.tool.calls[0]["versions"]}
        self.assertEqual((sent["H2"]["headline"], sent["H2"]["swipe"], sent["H2"]["t"]), ("Rash? Gone.", "sw-named", 4.0))
        self.assertEqual(json.loads((self.B / "covers" / "job.json").read_text())["product"], "widget")

    def test_the_filer_gets_thumbs_video_for_video_in_its_own_order(self):
        self.run_stage()
        hand = self.hand()
        media = [hand["media"][2], hand["media"][0]]
        k = CS.filer_kwargs("p1", media, B=self.B)
        self.assertEqual(k["thumbs"], [hand["thumbs"][2], hand["thumbs"][0]])
        self.assertEqual(k["cover_records"], [hand["cover_records"][2], hand["cover_records"][0]])
        self.assertEqual(CS.filer_kwargs("p1", ["/elsewhere/other.mp4"], B=self.B)["thumbs"], [""])

    def test_due_until_every_version_has_a_ready_cover_from_its_current_video(self):
        self.assertTrue(CS.due("p1", self.B, self.vers))
        self.run_stage()
        self.assertFalse(CS.due("p1", self.B, self.vers))
        (self.B / "versions" / "H2" / "p1-H2.mp4").write_bytes(b"a new render of H2")
        self.assertTrue(CS.due("p1", self.B, self.vers))

    def test_the_switch_turns_it_off(self):
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "1"}):
            self.assertFalse(CS.on())
            self.assertFalse(CS.due("p1", self.B, self.vers))
            self.assertEqual(self.run_stage(), {"on": False})
            self.assertEqual(CS.state("p1", self.B)["on"], False)
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "after_render"}):
            self.assertTrue(CS.on())
            self.assertFalse(CS.after_render())

    def test_the_checks_panel_shows_each_cover(self):
        self.run_stage()
        rows = [c for c in CB.checks("p1", self.B)["checks"] if c["group"] == "Covers"]
        self.assertEqual([r["name"] for r in rows], ["control", "H2", "H3"])
        self.assertTrue(all(r["ok"] for r in rows))
        self.assertEqual(len(rows[0]["pics"]), 2)



def failing_face(pic, masters):
    """The cast check: H2's cover never matches the cast."""
    return {"pass": "/h2/" not in pic, "people": [{"master": masters[0], "verdict": "DIFFERENT"}]}


class StaleCovers(Production):
    """A cover is only ever handed over for the render it was made from, by the run that made it."""

    def test_a_run_that_stops_half_way_leaves_no_cover_ready(self):
        self.assertTrue(self.run_stage()["ready"])
        self.rerender()

        def no_ffmpeg(video, t, dest):
            raise FileNotFoundError("ffmpeg")
        with self.assertRaises(FileNotFoundError):
            self.run_stage(grab_=no_ffmpeg)
        hand = self.hand()
        self.assertFalse(hand["ready"])
        self.assertEqual(hand["thumbs"], ["", "", ""])
        self.assertEqual(CS.filer_kwargs("p1", B=self.B)["thumbs"], ["", "", ""])
        self.assertTrue(CS.due("p1", self.B, self.vers))

    def test_the_filer_never_gets_a_cover_from_an_older_render(self):
        self.run_stage()
        self.rerender("versions/H2/p1-H2.mp4")
        k = CS.filer_kwargs("p1", B=self.B)
        self.assertEqual(k["thumbs"], ["", "", ""])                      # one stale cover: the set is not whole
        self.assertEqual(k["cover_records"], ["", "", ""])
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "whole_hand_off"}):
            k = CS.filer_kwargs("p1", B=self.B)
        self.assertEqual(k["thumbs"][1], "")
        self.assertTrue(k["thumbs"][0] and k["thumbs"][2])

    def test_a_record_from_an_earlier_run_is_never_read_as_made(self):
        self.run_stage()
        made = self.B / "covers" / "made" / "covers.json"
        old = made.stat().st_mtime - 60
        os.utime(made, (old, old))
        self.rerender()
        st = self.run_stage(tool=lambda job, only: (1, "Traceback (most recent call last): ..."))
        self.assertFalse(st["ready"])
        self.assertEqual(self.hand()["thumbs"], ["", "", ""])
        self.assertIn("no record of this run", st["versions"][0]["held"])

    def test_an_exit_other_than_0_or_1_is_never_made(self):
        tool = FakeTool()
        st = self.run_stage(tool=lambda job, only: (tool(job, only)[0] + 3, "killed"))
        self.assertFalse(st["ready"])
        self.assertEqual(self.hand()["thumbs"], ["", "", ""])
        self.assertIn("exit 3", st["versions"][0]["held"])

    def test_a_refused_remake_leaves_the_board_naming_what_the_cover_was_made_from(self):
        first = FakeTool()

        def tool(job, only):
            return first(job, only) if not only else (2, "refuses this cover: the headline does not fit")
        st = self.run_stage(tool=tool, face=failing_face)
        h2 = {r["version"]: r for r in st["versions"]}["H2"]
        rec = json.loads(Path(h2["record"]).read_text())
        self.assertEqual(h2["swipe"]["id"], rec["swipe"])
        self.assertEqual(h2["frame"]["t"], rec["source_frame"]["t"])
        self.assertFalse(h2["ready"])
        self.assertIn("the remake was not made", h2["held"])
        job = {v["version"]: v for v in json.loads((self.B / "covers" / "job.json").read_text())["versions"]}
        self.assertEqual(job["H2"]["swipe"], rec["swipe"])
        board = {v["version"]: v for v in CS.state("p1", self.B, cards=lambda b, k: [])["versions"]}
        self.assertEqual(board["H2"]["swipe"]["id"], rec["swipe"])


class Concept(Production):
    """Every cover takes its concept from a real Explore cover its avatar sees, with a rated move."""

    def test_a_swipe_the_ad_names_must_be_one_of_the_avatars_own_covers(self):
        self.brief(covers={"swipes": ["made-up-1", "made-up-2", "made-up-3"]})
        st = self.run_stage()
        self.assertFalse(st["ready"])
        self.assertEqual(self.tool.calls, [])
        self.assertIn("made-up-1 is not in the cover index", st["versions"][0]["held"])

    def test_a_version_swipe_from_another_avatar_is_held(self):
        (self.root / "index" / "covers.json").write_text(json.dumps([{"id": "other-1", "move": "wrong-scale",
                                                                       "avatar": "someone-else"}]))
        self.brief(covers={"H2": {"swipe": "other-1"}})
        st = self.run_stage()
        h2 = {r["version"]: r for r in st["versions"]}["H2"]
        self.assertIn("not one of avatar busy-dad's own Explore covers", h2["held"])
        self.assertEqual(self.tool.calls, [])

    def test_no_cover_is_made_without_a_rated_move(self):
        st = self.run_stage(find=lambda a, n: {"scope": "avatar", "covers": [
            {"id": "u1", "move": "unrated"}, {"id": "u2", "move": ""}, {"id": "u3", "move": "as-shot"}]})
        self.assertFalse(st["ready"])
        self.assertEqual(self.tool.calls, [])
        self.assertIn("no rated move", st["versions"][0]["held"])

    def test_a_named_swipe_with_no_rated_move_is_held(self):
        self.brief(covers={"H2": {"swipe": "sw-plain"}})
        st = self.run_stage()
        self.assertIn("sw-plain has no rated move", {r["version"]: r for r in st["versions"]}["H2"]["held"])

    def test_the_avatar_is_looked_up_as_the_index_files_it(self):
        self.brief(audience={"avatar": " Busy_Dad "})
        asked = []
        self.run_stage(find=lambda a, n: asked.append(a) or find_avatar(a, n))
        self.assertEqual(asked, ["busy-dad"])

    def test_the_index_exiting_never_takes_the_stage_down(self):
        def exits(a, n):
            raise SystemExit("covers: no avatar file")
        st = self.run_stage(find=exits)
        self.assertFalse(st["ready"])
        self.assertIn("no avatar file", st["versions"][0]["held"])


class Checks(Production):
    """A check that could not be read holds the version, with its reason."""

    def held_of(self, st, v="control"):
        return {r["version"]: r for r in st["versions"]}[v]["held"] or ""

    def test_no_words_box_holds(self):
        class NoBox(FakeTool):
            def __call__(self, job_path, only):
                code, said = super().__call__(job_path, only)
                f = Path(json.loads(Path(job_path).read_text())["out"]) / "covers.json"
                d = json.loads(f.read_text())
                for c in d["covers"]:
                    c["words"] = {}
                f.write_text(json.dumps(d))
                return code, said
        st = self.run_stage(tool=NoBox())
        self.assertFalse(st["ready"])
        self.assertIn("words off faces not read", self.held_of(st))

    def test_a_gate_that_stops_holds(self):
        def broken(ps):
            raise RuntimeError("ledger locked")
        st = self.run_stage(refuse=broken)
        self.assertFalse(st["ready"])
        self.assertIn("made by the tool not read", self.held_of(st))

    def test_a_gate_switched_off_is_not_a_pass(self):
        st = self.run_stage(refuse=lambda ps: ({}, []))
        self.assertFalse(st["ready"])
        self.assertIn("made by the tool not read", self.held_of(st))
        self.assertEqual(CS.made_by_tool(["a.png"], lambda ps: ({}, []))["a.png"][0], None)

    def test_a_brief_that_names_no_cast_holds_before_anything_is_sent(self):
        self.brief(cast=[])
        st = self.run_stage()
        self.assertFalse(st["ready"])
        self.assertEqual(self.tool.calls, [])
        self.assertIn("name the cast", self.held_of(st))

    def test_no_face_reader_holds_before_anything_is_sent(self):
        with mock.patch.object(CS, "face_reader", lambda: None):
            st = self.run_stage(read=None)
        self.assertEqual(self.tool.calls, [])
        self.assertIn("no face reader", self.held_of(st))

    def test_the_switch_puts_unread_checks_back(self):
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "hold_unread"}):
            self.assertTrue(self.run_stage(refuse=lambda ps: ({}, []))["ready"])


class Headline(Production):
    def test_a_line_is_never_cut_mid_clause(self):
        line = "Did you know most men over thirty lose half their hair by forty?"
        self.assertEqual(CS.headline_for("H2", line, [], 8)[0], None)
        self.assertIsNone(CS.headline_for("H2", "Look, this rash is not what you think it is at all.", [], 8)[0])
        self.assertEqual(CS.headline_for("H2", "Look at this rash, it is not what you think at all.", [], 8)[0],
                         "Look at this rash")
        self.assertEqual(CS.headline_for("H2", "Look at this rash.", [], 8)[0], "Look at this rash.")

    def test_a_version_with_no_line_that_fits_is_held_and_asks_the_brief(self):
        (self.B / "scenes" / "H2" / "take-1.json").write_text(json.dumps({"words": (
            "Would you try it? Did you know most men over thirty lose half their hair by forty? Nope."), "steps": []}))
        st = self.run_stage()
        self.assertEqual(self.tool.calls, [])
        self.assertIn("covers.H2.headline", {r["version"]: r for r in st["versions"]}["H2"]["held"])

    def test_a_version_that_opens_on_one_word_is_held_and_asks_the_brief(self):
        (self.B / "scenes" / "H2" / "take-1.json").write_text(json.dumps({"words": "Wow!! Nothing else works.",
                                                                          "steps": []}))
        st = self.run_stage()
        self.assertEqual(self.tool.calls, [])
        held = {r["version"]: r for r in st["versions"]}["H2"]["held"]
        self.assertIn("one word", held)
        self.assertIn("covers.H2.headline", held)


class Repress(Production):
    def test_a_second_press_makes_only_the_held_versions(self):
        first = {r["version"]: r for r in self.run_stage(face=failing_face)["versions"]}
        self.assertEqual(self.hand()["thumbs"][1], "")
        tool = FakeTool()
        st = self.run_stage(tool=tool)
        self.assertEqual([c["only"] for c in tool.calls], [["H2"]])
        self.assertTrue(st["ready"])
        after = self.hand()
        self.assertEqual((after["thumbs"][0], after["thumbs"][2]), (first["control"]["file"], first["H3"]["file"]))
        self.assertTrue({r["version"]: r for r in st["versions"]}["control"]["carried"])

    def test_nothing_is_made_again_when_every_cover_stands(self):
        self.run_stage()
        tool = FakeTool()
        st = self.run_stage(tool=tool)
        self.assertEqual(tool.calls, [])
        self.assertTrue(st["ready"] and self.hand()["ready"])


class TheSet(Production):
    def test_the_set_comes_from_the_productions_own_records(self):
        self.run_stage()
        self.assertEqual(json.loads((self.B / "covers" / "job.json").read_text())["set"], "kitchen-set")
        self.assertIn("scenes/S1/take-1.json", CS.state("p1", self.B, cards=lambda b, k: [])["set"]["why"])

    def test_a_start_frame_from_a_kept_print_names_the_set(self):
        (self.B / "scenes" / "S1" / "take-1.json").write_text(json.dumps({"words": "Look at this rash.", "steps": []}))
        rec = self.B / "scenes" / "S1" / "motion" / "run.json"
        rec.parent.mkdir(parents=True)
        rec.write_text(json.dumps({"request": {"references": ["/runs/image-production/acme/sets/kitchen-set/print-v1.png"]}}))
        self.run_stage()
        self.assertEqual(json.loads((self.B / "covers" / "job.json").read_text())["set"], "kitchen-set")

    def test_no_filed_set_holds_before_anything_is_sent(self):
        (self.B / "scenes" / "S1" / "take-1.json").write_text(json.dumps({"words": "Look at this rash.", "set": "garage"}))
        st = self.run_stage()
        self.assertEqual(self.tool.calls, [])
        self.assertIn("no filed 3D set", st["versions"][0]["held"])
        self.assertIn("garage", st["versions"][0]["held"])

    def test_the_ads_own_set_wins(self):
        self.brief(covers={"set": "studio-b"})
        self.run_stage()
        self.assertEqual(json.loads((self.B / "covers" / "job.json").read_text())["set"], "studio-b")


class ClosedCards(Production):
    """No covers are offered or made for an ad whose card is approved, live or already carries covers."""

    def card(self, state, **extra):
        d = self.root / "meta" / "acme" / state / "video" / "acme_widget_brief-0001_batch-a"
        d.mkdir(parents=True)
        (d / "card.json").write_text(json.dumps(dict({"brand": "acme", "lane": "video", "product": "widget",
                                                      "brief_id": "brief-0001",
                                                      "ad_name": "acme_widget_brief-0001_batch-a"}, **extra)))
        CS._CARDS.clear()

    def test_an_approved_card_is_left_alone(self):
        self.card("2-approved")
        self.assertFalse(CS.due("p1", self.B, self.vers))
        st = self.run_stage(cards=None)
        self.assertIn("approved", st["closed"])
        self.assertEqual(self.tool.calls, [])
        self.assertFalse((self.B / "covers").exists())

    def test_a_live_card_is_left_alone(self):
        self.card("3-live")
        self.assertIn("live", CS.closed("p1", self.B))

    def test_a_card_already_covered_is_left_alone(self):
        self.card("1-check", thumbs={"a.mp4": "a-cover.png"})
        self.assertIn("filed covers", CS.closed("p1", self.B))

    def test_a_waiting_card_with_no_covers_gets_them(self):
        self.card("1-check")
        self.assertIsNone(CS.closed("p1", self.B))
        self.assertTrue(CS.due("p1", self.B, self.vers))

    def test_a_card_tree_that_cannot_be_read_holds(self):
        with mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(self.root / "nowhere")}):
            self.assertIn("could not be read", CS.closed("p1", self.B))
            self.assertFalse(CS.due("p1", self.B, self.vers))

    def test_the_switch_puts_it_back(self):
        self.card("2-approved")
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "skip_closed"}):
            self.assertIsNone(CS.closed("p1", self.B))


class InTheStudio(Production):
    """The Studio's Next step: covers follow the render, and the board reads them at /api/covers/<production>."""

    def setUp(self):
        super().setUp()
        self.vs = mock.patch.object(VS, "BRIEFS", str(self.briefs))
        self.vs.start()
        B = self.B
        (B / "brief.json").write_text(json.dumps(dict(json.loads((B / "brief.json").read_text()), order=["S1"])))
        (B / "shot-list.json").write_text(json.dumps({"shots": [{"id": "a", "scene": "S1"}]}))
        (B / "picks.json").write_text(json.dumps({"shots": {"a": {"source": "x"}}}))
        (B / "shot-fill.json").write_text("{}")
        out = B / "scenes" / "S1" / "out" / "take-1" / "S1.mp4"
        out.parent.mkdir(parents=True)
        t = 1_700_000_000
        for i, f in enumerate([B / "picks.json", B / "scenes" / "S1" / "take-1.json", out, B / "SWIPE-CHECK.json",
                               B / "rough-cut-v1-sdr.mp4", B / "versions" / "H2" / "p1-H2.mp4",
                               B / "versions" / "H3" / "p1-H3.mp4"]):
            if not f.exists():
                f.write_text("{}")
            os.utime(f, (t + i * 10, t + i * 10))

    def tearDown(self):
        self.vs.stop()
        super().tearDown()

    def test_after_the_versions_render_the_next_step_is_the_covers(self):
        self.assertEqual(VS.next_due("p1"), "covers")
        self.assertEqual(VS.next_state("p1")["label"], "Make the covers")
        self.run_stage()
        self.assertIsNone(VS.next_due("p1"))
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "1"}):
            os.remove(self.B / "covers" / "stage.json")
            self.assertIsNone(VS.next_due("p1"))

    def test_the_render_job_runs_straight_on_into_the_covers(self):
        job = {"id": "j", "n": "p1", "stage": "render", "name": "Render the version", "steps": [
            {"id": "build", "name": "b", "state": "done", "said": ""}]}
        seen = {}

        def fake_run(n, B=None, say=None, vers=None, **kw):
            seen.update(n=n, B=B, vers=vers)
            say("frames", "done", "ok")
            return {"ready": True}
        with mock.patch.object(VS.CS, "run", fake_run):
            VS._run_covers(job)
        self.assertEqual([s["id"] for s in job["steps"]][1:], [i for i, _ in CS.STEPS])
        self.assertEqual(job["steps"][1]["state"], "done")
        self.assertEqual(job["open"], {"stage": "covers", "n": "p1"})
        self.assertEqual([v["id"] for v in seen["vers"]], ["control", "H2", "H3"])

    def test_the_board_reads_the_covers_from_the_studio(self):
        self.run_stage()
        srv = VS.ThreadingHTTPServer(("127.0.0.1", 0), VS.H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = "http://127.0.0.1:%d/api/covers/p1" % srv.server_address[1]
            got = json.loads(urllib.request.urlopen(url, timeout=10).read())
            self.assertTrue(got["ready"])
            self.assertEqual([v["version"] for v in got["versions"]], ["control", "H2", "H3"])
            pic = urllib.request.urlopen("http://127.0.0.1:%d%s" % (srv.server_address[1], got["versions"][0]["cover"]),
                                         timeout=10)
            self.assertEqual(pic.headers["Content-Type"], "image/png")
        finally:
            srv.shutdown()
            srv.server_close()

    def test_an_approved_production_keeps_open_versions(self):
        d = self.root / "meta" / "acme" / "2-approved" / "video" / "acme_widget_brief-0001_batch-a"
        d.mkdir(parents=True)
        (d / "card.json").write_text(json.dumps({"brand": "acme", "product": "widget", "brief_id": "brief-0001",
                                                 "ad_name": "acme_widget_brief-0001_batch-a"}))
        self.assertIsNone(VS.next_due("p1"))
        self.assertEqual(VS.next_state("p1")["label"], "Open Versions")
        srv = VS.ThreadingHTTPServer(("127.0.0.1", 0), VS.H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/api/covers/p1" % srv.server_address[1], data=b"{}",
                                         method="POST")
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(e.exception.code, 409)
            self.assertIn("approved", json.loads(e.exception.read())["error"])
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertFalse((self.B / "next-job.json").exists())

    def test_a_production_filed_straight_from_a_card_keeps_open_versions(self):
        """No brief_key in brief.json: the brand's brief list knows the number it went live under."""
        b = json.loads((self.B / "brief.json").read_text())
        b.pop("brief_key")
        b["brief"] = "acme-run-p1-slug"
        (self.B / "brief.json").write_text(json.dumps(b))
        reg = self.root / "brands" / "acme" / "briefs" / "briefs.json"
        reg.parent.mkdir(parents=True)
        reg.write_text(json.dumps({"briefs": [{"brief": "brief-0342", "product": "widget",
                                               "aliases": ["acme-run-p1-slug"]}]}))
        d = self.root / "meta" / "acme" / "3-live" / "video" / "acme_widget_brief-0342_batch-a"
        d.mkdir(parents=True)
        (d / "card.json").write_text(json.dumps({"brand": "acme", "product": "widget", "brief_id": "brief-0342",
                                                 "ad_name": "acme_widget_brief-0342_batch-a"}))
        CS._CARDS.clear()
        with mock.patch.object(VS, "_ws", lambda: self.root):
            self.assertEqual(VS.filed_brief(b, "p1"), "acme_widget_brief-0342")
            self.assertEqual(CS.brief_key(b, "p1"), "acme_widget_brief-0342")
            self.assertIn("live", CS.closed("p1", self.B) or "")
            self.assertIsNone(VS.next_due("p1"))
            self.assertEqual(VS.next_state("p1")["label"], "Open Versions")
            with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "filed_brief"}):
                CS._CARDS.clear()
                self.assertIsNone(CS.closed("p1", self.B))

    def test_a_neighbour_that_exits_never_takes_the_studio_down(self):
        def exits(*a, **k):
            raise SystemExit("covers: no such avatar")
        with mock.patch.object(VS.CS, "due", exits):
            self.assertIsNone(VS.next_due("p1"))
        job = {"id": "j", "n": "p1", "stage": "covers", "name": "Make the covers", "steps": []}
        with mock.patch.object(VS.CS, "run", exits):
            VS._run_covers(job)
        self.assertEqual(job["steps"][0]["state"], "stopped")
        self.assertIn("no such avatar", job["steps"][0]["said"])

    def test_the_studio_page_has_a_covers_tab(self):
        page = (Path(VS.HERE) / "studio.html").read_text()
        self.assertIn("['covers','Covers']", page)
        self.assertIn("/api/covers/", page)


def unanswered_face(pic, masters):
    """The cast check came back, but the judge did not answer for the face."""
    return {"pass": False, "people": [{"master": masters[0], "verdict": "UNCHECKED"}]}


class UnreadFaces(Production):
    """A face check that stops or comes back unanswered holds the version with its reason; nothing is made again."""

    def held_of(self, st, v):
        return {r["version"]: r for r in st["versions"]}[v]["held"] or ""

    def test_a_face_check_that_stops_holds_and_buys_no_remake(self):
        def stops(pic, masters):
            raise RuntimeError("the judge timed out")
        st = self.run_stage(face=stops)
        self.assertEqual(len(self.tool.calls), 1)                        # one job, no paid remake
        self.assertFalse(st["ready"])
        for v in ("control", "H2", "H3"):
            self.assertIn("faces not read", self.held_of(st, v))
            self.assertIn("the judge timed out", self.held_of(st, v))

    def test_an_unanswered_face_check_holds_and_buys_no_remake(self):
        st = self.run_stage(face=unanswered_face)
        self.assertEqual(len(self.tool.calls), 1)
        self.assertIn("faces not read", self.held_of(st, "H2"))
        self.assertIn("did not answer", self.held_of(st, "H2"))

    def test_a_face_that_differs_is_still_made_again(self):
        def mixed(pic, masters):
            return {"pass": False, "people": [{"master": masters[0], "verdict": "UNCHECKED"},
                                              {"master": masters[0], "verdict": "DIFFERENT"}]}
        self.run_stage(face=mixed)
        self.assertEqual(len(self.tool.calls), 2)

    def test_a_cached_unanswered_record_is_asked_again(self):
        asked = []

        class FG:
            @staticmethod
            def read(p):
                return {"pass": False, "people": [{"master": "m", "verdict": "UNCHECKED"}]}

            @staticmethod
            def stamp(p, m):
                asked.append(p)
                return {"pass": True, "people": [{"master": m[0], "verdict": "SAME"}]}
        with mock.patch.dict(CS._MODS, {"face_gate": FG}):
            self.assertTrue(CS.faces_against_cast("c.png", ["m.png"])[0])
        self.assertEqual(asked, ["c.png"])

    def test_the_switch_puts_the_remake_back(self):
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "face_unread"}):
            self.run_stage(face=unanswered_face)
        self.assertEqual(len(self.tool.calls), 2)

    def test_an_empty_or_unknown_verdict_is_not_read(self):
        for verdict in ("", None, "ERROR", "NO_FACE", "unchecked"):
            rec = {"pass": False, "people": [{"master": "/c/acme/casting/host/full/master.png", "verdict": verdict}]}
            ok, short = CS.faces_against_cast("c.png", ["m.png"], check=lambda p, m, rec=rec: rec)
            self.assertIsNone(ok, verdict)
            self.assertIn("did not answer", short)
            self.assertIn("host", short)

    def test_an_unknown_verdict_holds_and_buys_no_remake(self):
        def odd(pic, masters):
            return {"pass": False, "people": [{"master": masters[0], "verdict": "ERROR"}]}
        st = self.run_stage(face=odd)
        self.assertEqual(len(self.tool.calls), 1)                        # one job, no paid remake
        self.assertIn("faces not read", self.held_of(st, "H2"))

    def test_a_real_miss_beside_an_unknown_verdict_is_still_a_miss(self):
        rec = {"pass": False, "people": [{"master": "m", "verdict": ""}, {"master": "m", "verdict": "DIFFERENT"}]}
        self.assertIs(CS.faces_against_cast("c.png", ["m.png"], check=lambda p, m: rec)[0], False)

    def test_switched_off_a_check_with_no_record_is_a_miss_not_a_crash(self):
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "face_unread"}):
            ok, short = CS.faces_against_cast("c.png", ["m.png"], check=lambda p, m: None)
            self.assertIs(ok, False)
            self.assertIn("no record", short)
            rec = {"pass": False, "people": [{"master": "m", "verdict": "ERROR"}]}
            self.assertIs(CS.faces_against_cast("c.png", ["m.png"], check=lambda p, m: rec)[0], False)


class PartialHandOff(Production):
    """A hand-off is whole or empty, and a card carrying some versions' covers never locks the others out."""

    def card(self, state, thumbs):
        d = self.root / "meta" / "acme" / state / "video" / "acme_widget_brief-0001_batch-a"
        d.mkdir(parents=True)
        media = ["p1-control.mp4", "p1-H2.mp4", "p1-H3.mp4"]
        (d / "card.json").write_text(json.dumps({"brand": "acme", "lane": "video", "product": "widget",
                                                 "ad_name": "acme_widget_brief-0001_batch-a", "media": media,
                                                 "thumbs": {m: m + ".png" for m in media[:thumbs]}}))
        CS._CARDS.clear()

    def test_a_partial_set_is_never_handed_to_the_filer(self):
        st = self.run_stage(face=failing_face)
        self.assertFalse(st["ready"])
        hand = self.hand()
        self.assertEqual((hand["thumbs"], hand["cover_records"]), (["", "", ""], ["", "", ""]))
        self.assertEqual(CS.filer_kwargs("p1", B=self.B)["thumbs"], ["", "", ""])

    def test_a_card_with_some_covers_does_not_lock_the_rest_out(self):
        self.run_stage(face=failing_face)
        self.card("1-check", thumbs=2)
        self.assertIsNone(CS.closed("p1", self.B))
        self.assertTrue(CS.due("p1", self.B, self.vers))
        tool = FakeTool()
        st = self.run_stage(tool=tool, cards=None)
        self.assertEqual([c["only"] for c in tool.calls], [["H2"]])     # the held version is made, by itself
        self.assertTrue(st["ready"])
        self.assertTrue(all(self.hand()["thumbs"]))

    def test_a_card_with_every_cover_is_left_alone(self):
        self.card("1-check", thumbs=3)
        self.assertIn("filed covers", CS.closed("p1", self.B))

    def test_the_switch_puts_it_back(self):
        self.card("1-check", thumbs=2)
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "whole_hand_off"}):
            self.assertIn("filed covers", CS.closed("p1", self.B))
            self.run_stage(face=failing_face, cards=lambda b, k: [])
            self.assertTrue(self.hand()["thumbs"][0])


class WholeSentences(unittest.TestCase):
    """A headline is a whole sentence, or a whole first clause of three words or more; never a cut on an abbreviation,
    an ellipsis or an opening word."""

    def h(self, words, limit=8):
        return CS.headline_for("H2", words, [], limit)[0]

    def test_an_abbreviation_never_ends_a_line(self):
        self.assertEqual(self.h("Mr. Smith tried it. Then he stopped."), "Mr. Smith tried it.")
        self.assertEqual(CS.sentences("Dr. Lee said so. Ask her."), ["Dr. Lee said so.", "Ask her."])

    def test_an_ellipsis_is_a_pause_not_the_end(self):
        self.assertEqual(self.h("Okay so... this changed everything. Trust me."), "Okay so... this changed everything.")
        self.assertEqual(self.h("Okay so\u2026 this changed everything."), "Okay so\u2026 this changed everything.")
        self.assertEqual(self.h("Then it happened..."), "Then it happened...")

    def test_an_opening_word_is_not_a_headline(self):
        self.assertIsNone(self.h("Wait, did you know most men over thirty lose half their hair?"))
        self.assertIsNone(self.h("Okay so, this changed everything I thought I knew about it."))

    def test_a_quote_is_kept_whole(self):
        self.assertEqual(self.h('Last time it was "the price." Now it is not.'), 'Last time it was "the price."')
        self.assertIsNone(self.h('Last time it was "the price'))

    def test_a_held_version_asks_the_brief_for_its_headline(self):
        h, why = CS.headline_for("H2", "Wait, did you know most men over thirty lose half their hair?", [], 8)
        self.assertIsNone(h)
        self.assertIn("whole clause", why)

    def test_a_number_abbreviation_never_ends_a_line(self):
        self.assertEqual(self.h("No. 1 seller in the country. Try it."), "No. 1 seller in the country.")
        self.assertEqual(CS.sentences("Vol. 2 is out. Fig. 3 shows it. Gen. Lee came by."),
                         ["Vol. 2 is out.", "Fig. 3 shows it.", "Gen. Lee came by."])
        self.assertEqual(CS.sentences("No. I would never. Try it."), ["No.", "I would never.", "Try it."])

    def test_a_one_word_line_is_not_a_headline(self):
        for words in ("Stop. Then look at this.", "Wow!! It works.", "I. Am. Done.", "No. I would never."):
            h, why = CS.headline_for("H2", words, [], 8)
            self.assertIsNone(h, words)
            self.assertIn("one word", why)
        self.assertEqual(self.h("Stop scrolling. Look."), "Stop scrolling.")

    def test_the_switch_puts_the_old_cut_back(self):
        with mock.patch.dict(os.environ, {"VIDEO_STUDIO_COVERS_OFF": "whole_sentences"}):
            self.assertEqual(self.h("Wait, did you know most men over thirty lose half their hair?"), "Wait")
            self.assertEqual(self.h("Stop. Then look at this."), "Stop.")
            self.assertEqual(self.h("No. 1 seller in the country."), "No.")




class CoverCast(unittest.TestCase):
    def test_the_covers_own_cast_wins_over_the_whole_ad(self):
        import tempfile
        root = Path(tempfile.mkdtemp())
        for el in ("judge", "first-man", "narrator"):
            m = root / "brand-x" / "casting" / el / "full"
            m.mkdir(parents=True)
            (m / "master.png").write_bytes(b"png")
        old = os.environ.get("VIDEO_STUDIO_CASTING")
        os.environ["VIDEO_STUDIO_CASTING"] = str(root)
        try:
            brief = {"brand": "brand-x", "cast": ["narrator", "judge", "first-man"]}
            brief["covers"] = {"cast": ["judge", "first-man"]}
            got = [Path(p).parent.parent.name for p in CS.masters_of(dict(brief, brand="brand-x"))]
            self.assertEqual(got, ["judge", "first-man"])
            got = [Path(p).parent.parent.name for p in CS.masters_of({"brand": "brand-x", "cast": brief["cast"]})]
            self.assertEqual(got, ["narrator", "judge", "first-man"])
            brief["covers"]["H1"] = {"cast": ["narrator"]}
            got = [Path(p).parent.parent.name for p in CS.masters_of(brief, "H1")]
            self.assertEqual(got, ["narrator"])
            got = [Path(p).parent.parent.name for p in CS.masters_of(brief, "H2")]
            self.assertEqual(got, ["judge", "first-man"])
        finally:
            if old is None:
                os.environ.pop("VIDEO_STUDIO_CASTING", None)
            else:
                os.environ["VIDEO_STUDIO_CASTING"] = old


class MasterAtTheTop(unittest.TestCase):
    """brief-0380: Yai's master was casting/yai/master.jpg (no full/master.png) and the cover face check skipped her."""
    def test_a_master_at_the_casting_folders_top_is_found(self):
        import tempfile
        root = Path(tempfile.mkdtemp())
        (root / "b" / "casting" / "a" / "full").mkdir(parents=True)
        (root / "b" / "casting" / "a" / "full" / "master.png").write_bytes(b"a")
        (root / "b" / "casting" / "y").mkdir(parents=True)
        (root / "b" / "casting" / "y" / "master.jpg").write_bytes(b"y")
        (root / "b" / "casting" / "none").mkdir(parents=True)
        old = os.environ.get("VIDEO_STUDIO_CASTING")
        os.environ["VIDEO_STUDIO_CASTING"] = str(root)
        try:
            got = CS.masters_of({"brand": "b", "cast": ["a", "y", "none"]})
        finally:
            if old is None:
                os.environ.pop("VIDEO_STUDIO_CASTING", None)
            else:
                os.environ["VIDEO_STUDIO_CASTING"] = old
        self.assertEqual([Path(p).name for p in got], ["master.png", "master.jpg"])


if __name__ == "__main__":
    unittest.main()
