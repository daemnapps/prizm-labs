"""handoff — the Higgsfield handoff: one approved picture ad packaged for a designer to finish by hand.

Every test builds a throwaway workspace under `tempfile` and hands the build a fake variation run (the chain's dry run,
as edit.json rows) and, for the Drive, a fake engine. No network, no key, nothing generated, nothing written outside
`tempfile`.

    python3 tools/image-edit/tests/test_handoff.py
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
from image_edit import handoff as H  # noqa: E402
from image_edit.engine import BadRequest  # noqa: E402

RUN, BRAND, KEY = "testbrand-run-325", "testbrand", "testbrand_widget_brief-0325"
PROMPT = "INPUTS\nIMAGE 1 is the reference.\nIMAGE 2 is our cast member.\n\nTHE PICTURE\nTHE ONE CHANGE to IMAGE 1: a spot.\n"
LAYER = {"elements": [{"text": "x", "top_pct": 65, "left_pct": 10, "right_pct": 90, "align": "center", "height_pct": 7,
                       "weight": "bold", "color": "#FFFFFF", "font": "humanist-sans", "max_lines": 2,
                       "letterform": "caption-outline — native social media text overlay"}]}
ROWS = [{"id": "v1", "label": "words", "words": ["LINE ONE"]},
        {"id": "v2", "label": "one spot", "words": ["LINE TWO / AND MORE"], "picture": "One spot is darker."}]


def picture(path, size=(30, 40)):
    from PIL import Image
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (120, 90, 80)).save(path)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="handoff-test-"))
        self.repo = self.tmp / "ws"
        run = self.repo / "tools" / "image-teardown" / "runs" / RUN
        (run / "out").mkdir(parents=True)
        (run / "out" / "variations.json").write_text(json.dumps({"variations": ROWS}))
        picture(run / "assets" / "source.jpg")
        pb = self.repo / "runs" / "image-production" / BRAND / "prompt-bench"
        self.approved = picture(pb / f"{RUN}-20261027-141533.png")
        self.plate = picture(pb / "generated" / f"{RUN}-20261027-141533.plate.png")
        self.cast = picture(self.repo / "runs" / "ai-elements" / BRAND / "casting" / "who" / "sheets" / "headshot.jpg")
        self.out = self.tmp / "out"
        self.asked = []

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def vary(self, refuse=None):
        """The chain's dry run as vary_recipe writes it: one edit.json per row under req["out"]."""
        def go(req):
            self.asked.append(req)
            rows = []
            for v in req["variations"]:
                pic = bool(v.get("picture"))
                r = {"id": v["id"], "state": "refused" if v["id"] == refuse else "dry", "makes_picture": pic,
                     "plate": str(self.plate.relative_to(self.repo)), "model": "a-model",
                     "settings": {"quality": "high", "aspect": "9:16", "size": None}, "bars": [12.4, 10.0],
                     "type_layer": LAYER, "lessons": [{"id": "L-1", "rule": "Bars stay.", "status": "draft"}],
                     "prompt": PROMPT,
                     "inputs": [{"n": 1, "role": "the reference", "path": str(self.plate.relative_to(self.repo))},
                                {"n": 2, "role": "our cast member", "path": str(self.cast)}] if pic else []}
                if v["id"] == refuse:
                    r["refused"] = "an input is missing"
                (Path(req["out"]) / v["id"]).mkdir(parents=True, exist_ok=True)
                (Path(req["out"]) / v["id"] / "edit.json").write_text(json.dumps(r))
                rows.append({"id": v["id"]})
            return {"variations": rows}
        return go

    def build(self, **kw):
        return H.build(RUN, BRAND, out=kw.pop("out", self.out), picture=self.approved, brief=(KEY, "brief-0325"),
                       vary=kw.pop("vary", self.vary()), guides=False, repo=self.repo, check_stage=kw.pop("check_stage", False))


class TestSetChange(Base):
    """A picture change on a run with a kept 3D set carries its set request, never a flat prompt."""

    def vary_set(self):
        sheet = picture(self.repo / "runs" / "ai-elements" / BRAND / "products" / "thing" / "model" / "product-sheet.png")
        kept = picture(self.repo / "runs" / "image-production" / BRAND / "sets" / "one" / "print-v1.png")
        ask = {"set": "one--v2", "kept_print": str(kept.relative_to(self.repo)), "change": "a bigger sign", "credits": 2.5,
               "print_words": "Print this.", "steps": ["Copy the collection."], "flags": [],
               "product": {"sheet": str(sheet.relative_to(self.repo))}}
        inner = self.vary()

        def go(req):
            s = inner(req)
            for r in s["variations"]:
                f = Path(req["out"]) / r["id"] / "edit.json"
                d = json.loads(f.read_text())
                d["route"] = "set" if d["makes_picture"] else "words"
                if d["makes_picture"]:
                    d["set_request"] = ask
                f.write_text(json.dumps(d))
            return s
        return go

    def test_a_set_row_has_its_request_and_pictures_and_no_flat_prompt(self):
        rec = self.build(vary=self.vary_set())
        row = next(v for v in rec["variations"] if v["makes_picture"])
        d = self.out / row["id"]
        self.assertFalse((d / "prompt.md").exists())
        self.assertEqual(json.loads((d / "set-request.json").read_text())["set"], "one--v2")
        for f in ("kept-print.png", "product-sheet.png"):
            self.assertTrue((d / f).is_file(), f)
        self.assertIsNone(row["prompt"])
        self.assertEqual(row["route"], "set")
        md = (self.out / "HANDOFF.md").read_text()
        self.assertIn("Variations that change the 3D set", md)
        self.assertIn(f"`{row['id']}/set-request.json`", md)
        self.assertNotIn(f"`{row['id']}/prompt.md`", md)

    def test_an_old_flat_prompt_is_replaced_by_a_pointer(self):
        old = self.out / "v2" / "prompt.md"
        old.parent.mkdir(parents=True)
        old.write_text(PROMPT)
        self.build(vary=self.vary_set())
        rows = json.loads((self.out / "handoff.json").read_text())["variations"]
        for v in rows:
            if v["makes_picture"]:
                self.assertIn("set-request.json", (self.out / v["id"] / "prompt.md").read_text()) if v["id"] == "v2" else None

    def test_a_run_with_no_set_keeps_its_flat_prompt(self):
        rec = self.build()
        row = next(v for v in rec["variations"] if v["makes_picture"])
        self.assertTrue((self.out / row["id"] / "prompt.md").is_file())
        self.assertFalse((self.out / row["id"] / "set-request.json").exists())


class TestFolder(Base):
    def test_runs_the_chain_dry_never_spends(self):
        self.build()
        self.assertEqual(len(self.asked), 1)
        self.assertTrue(self.asked[0]["dry_run"])
        self.assertEqual(self.asked[0]["variations"], ROWS)

    def test_approved_clean_swipe_and_bars(self):
        self.build()
        a = self.out / "00-approved"
        for name in (f"{KEY}-approved.png", f"{KEY}-approved-clean.png", "swipe.jpg", "black-bars-overlay.png"):
            self.assertTrue((a / name).is_file(), name)
        from PIL import Image
        bars = Image.open(a / "black-bars-overlay.png")
        self.assertEqual(bars.size, H.FRAME)
        h = H.FRAME[1]
        self.assertEqual(bars.getpixel((5, round(h * 0.124) - 2))[3], 255)     # inside the top bar
        self.assertEqual(bars.getpixel((5, h // 2))[3], 0)                      # the picture shows through
        self.assertEqual(bars.getpixel((5, h - 2))[3], 255)                     # the bottom bar

    def test_prompt_verbatim_and_pictures_named_as_the_prompt_numbers_them(self):
        self.build()
        v2 = self.out / "v2"
        self.assertEqual((v2 / "prompt.md").read_text(), PROMPT)
        self.assertEqual((v2 / "IMAGE-1.png").read_bytes(), self.plate.read_bytes())
        self.assertEqual((v2 / "IMAGE-2.jpg").read_bytes(), self.cast.read_bytes())

    def test_words_only_row_has_no_prompt(self):
        rec = self.build()
        self.assertFalse((self.out / "v1" / "prompt.md").exists())
        v1 = next(v for v in rec["variations"] if v["id"] == "v1")
        self.assertFalse(v1["makes_picture"])
        self.assertIsNone(v1["prompt"])

    def test_refused_row_stops_the_handoff(self):
        with self.assertRaises(BadRequest):
            self.build(vary=self.vary(refuse="v2"))
        self.assertFalse(self.out.exists())

    def test_no_variation_list_is_refused(self):
        (self.repo / "tools" / "image-teardown" / "runs" / RUN / "out" / "variations.json").unlink()
        with self.assertRaises(BadRequest):
            self.build()

    def test_record_holds_no_machine_paths(self):
        self.build()
        text = (self.out / "handoff.json").read_text()
        self.assertNotIn(str(self.tmp), text)
        rec = json.loads(text)
        self.assertEqual(rec["brief"], "brief-0325")
        self.assertEqual(rec["approved"], str(self.approved.relative_to(self.repo)))

    def test_second_run_writes_over_the_same_names(self):
        self.build()
        self.build()
        self.assertEqual((self.out / "v2" / "prompt.md").read_text(), PROMPT)


class TestRunSheetInTheFolder(Base):
    """Every hand-off folder carries BRIEF.md, the run sheet and refs/: nothing outside the folder is needed."""

    def sheet(self):
        brief = self.repo / "runs" / "image-teardown" / BRAND / RUN / "deliverable" / "06-brief.md"
        brief.parent.mkdir(parents=True, exist_ok=True)
        brief.write_text("# BRIEF · testbrand · widget · one spot\n")
        swipe = f"tools/image-teardown/runs/{RUN}/assets/source.jpg"
        cast = str(self.cast.relative_to(self.repo))
        ret = {"role": H.ROLE, "name_pattern": f"{KEY}_asset-NN.<ext>",
               "repo": f"runs/handoffs/{H.ROLE}/{BRAND}/{KEY}/returned/", "drive": "x"}
        step = {"n": 1, "asset": f"{KEY}_asset-01.png", "what": "the main picture", "medium": "image",
                "job": "pictures.generate", "model_house": {"registry": "a-model", "door": "higgsfield"},
                "higgsfield_model": "a_model", "model_name": "A Model", "prompt": PROMPT, "prompt_source": "the chain",
                "references": [{"n": 1, "kind": "image", "role": "the reference", "file": swipe, "exists": True, "element": None},
                               {"n": 2, "kind": "image", "role": "our cast member", "file": cast, "exists": True,
                                "element": {"kind": "cast", "id": "who", "name": "who", "folder": f"runs/ai-elements/{BRAND}/casting/who",
                                            "element": {"id": "e-1", "name": "testbrand-who"}}}],
                "settings": {"aspect_ratio": "9:16", "variant": "v", "quality": "high", "resolution": "2k", "count": 1},
                "words_on_top": [], "bars": None, "findings": []}
        return {"brief_key": KEY, "brief": "brief-0325", "brand": BRAND, "title": "one spot", "product": None,
                "brief_file": str(brief.relative_to(self.repo)), "built": "now", "run": RUN, "return": ret,
                "elements": [], "gaps": [], "steps": [step]}

    def test_brief_run_sheet_and_refs_land_in_the_folder(self):
        rec = H.build(RUN, BRAND, out=self.out, picture=self.approved, brief=(KEY, "brief-0325"), vary=self.vary(),
                      guides=False, repo=self.repo, check_stage=False, runsheet=self.sheet())
        for f in ("BRIEF.md", "RUN.md", "run.json", "refs/step-01-image-1-swipe.jpg", "refs/cast-who-headshot.jpg"):
            self.assertTrue((self.out / f).is_file(), f)
        self.assertEqual(rec["runsheet"]["refs"], 2)
        data = json.loads((self.out / "run.json").read_text())
        home = f"runs/handoffs/{H.ROLE}/{BRAND}/{KEY}"
        r = data["steps"][0]["references"][1]
        self.assertEqual((r["local"], r["drive"]), ("refs/cast-who-headshot.jpg", f"Shared Assets/{home}/refs/cast-who-headshot.jpg"))
        self.assertIn("`BRIEF.md`, `RUN.md`, `run.json` and `refs/`", (self.out / "HANDOFF.md").read_text())
        self.assertNotIn(str(self.tmp), (self.out / "run.json").read_text() + (self.out / "RUN.md").read_text())

    def test_a_run_sheet_that_cannot_be_made_is_said_never_stops_the_handoff(self):
        bad = self.sheet()
        bad["brief_file"] = None
        rec = H.build(RUN, BRAND, out=self.out, picture=self.approved, brief=(KEY, "brief-0325"), vary=self.vary(),
                      guides=False, repo=self.repo, check_stage=False, runsheet=bad)
        self.assertIn("no written brief", rec["runsheet"]["error"])
        self.assertTrue((self.out / "HANDOFF.md").is_file())

    def test_elsewhere_is_not_packed_unless_asked(self):
        rec = self.build()
        self.assertIsNone(rec["runsheet"])
        self.assertFalse((self.out / "RUN.md").exists())


class TestHandoffPage(Base):
    def test_names_every_output_with_the_brief_id(self):
        self.build()
        md = (self.out / "HANDOFF.md").read_text()
        for v in ROWS:
            self.assertIn(f"`{KEY}-{v['id']}.png`", md)
        # the delivery check finds the brief by this tag in the file name
        tag = re.compile(r"(?<![a-z0-9])brief[\s_-]?(\d{3,4})(?!\d)", re.I)
        self.assertEqual(tag.findall(f"{KEY}-v2.png"), ["0325"])

    def test_says_where_to_save_words_change_and_finish(self):
        self.build()
        md = (self.out / "HANDOFF.md").read_text()
        self.assertIn("`returned/` in this folder", md)
        self.assertIn("For the graphic designer.", md)
        self.assertIn("LINE TWO / AND MORE", md)
        self.assertIn("One spot is darker.", md)
        self.assertIn("top 12.4%, bottom 10.0%", md)
        self.assertIn("white", md)
        self.assertIn("1080x1920", md)

    def test_rules_carry_the_lessons(self):
        self.build()
        self.assertIn("**L-1** (draft): Bars stay.", (self.out / "rules.md").read_text())



class FakeEngine:
    def __init__(self):
        self.mirrored, self.folders = [], []

    def mirror_tree(self, local, dest, svc):
        self.mirrored.append((local, dest))
        return {p.relative_to(local).as_posix(): "id-" + p.name for p in Path(local).rglob("*") if p.is_file()}

    def folder(self, name, parent, svc=None):
        self.folders.append((name, parent))
        return "f-" + name


class TestDrive(Base):
    def setUp(self):
        super().setUp()
        sys.path.append(str(HERE.parent / "gdrive-creator"))
        from gdrive_creator import reach
        self.reach, self._fid = reach, reach.folder_id
        self.parts = []
        reach.folder_id = lambda parts, svc, make=False, find_engine=None, root=None: (self.parts.append((parts, make)) or "DEST")

    def tearDown(self):
        self.reach.folder_id = self._fid
        super().tearDown()

    def test_drive_path_is_the_repo_path_word_for_word(self):
        rec = self.build(out=H.folder_of(BRAND, KEY, repo=self.repo))
        E = FakeEngine()
        got = H.to_drive(rec, svc=object(), find_engine=lambda: E, repo=self.repo)
        self.assertEqual(self.parts, [(["runs", "handoffs", "graphic-designer", BRAND, KEY], True)])
        self.assertEqual(Path(rec["folder"]), self.repo / "runs" / "handoffs" / "graphic-designer" / BRAND / KEY)
        self.assertEqual(got["label"], f"Shared Assets/runs/handoffs/graphic-designer/{BRAND}/{KEY}")
        self.assertEqual(E.mirrored, [(rec["folder"], "DEST")])
        self.assertEqual(got["link"], "https://drive.google.com/drive/folders/DEST")
        self.assertIn("HANDOFF.md", got["files"])
        self.assertEqual(json.loads((Path(rec["folder"]) / "handoff.json").read_text())["drive"]["id"], "DEST")
        self.assertEqual(E.folders, [("returned", "DEST")])      # what comes back goes into the handoff's own folder
        self.assertTrue((Path(rec["folder"]) / "returned").is_dir())


class TestFinalStage(Base):
    """Only a brief that came out of its chain's final stage is handed off (the owner, 2026-10-27)."""
    STAGES = {"5": ("x", "05-image-variations.md"), "6": ("y", "06-brief.md")}

    def file_run(self, state="filed", stages=("05-image-variations.md", "06-brief.md"), brief=True, source="stage5"):
        filed = self.repo / "runs" / "image-teardown" / BRAND / RUN
        filed.mkdir(parents=True, exist_ok=True)
        (filed / "run.json").write_text(json.dumps({"state": state, "stages": list(stages)}))
        out = self.repo / "tools" / "image-teardown" / "runs" / RUN / "out"
        if brief:
            (out / "06-brief.md").write_text("the brief")
        (out / "variations.json").write_text(json.dumps({"source": source, "variations": ROWS}))

    def why(self, run=RUN):
        return H.final_stage(run, BRAND, repo=self.repo, stages=self.STAGES)

    def test_a_chain_made_brief_passes(self):
        self.file_run()
        self.assertIsNone(self.why())

    def test_never_filed_is_refused(self):
        self.assertIn("never filed", self.why())

    def test_short_of_the_last_stage_is_refused(self):
        self.file_run(stages=("05-image-variations.md",), brief=False)
        self.assertIn("06-brief.md", self.why())

    def test_variations_not_from_the_chain_are_refused(self):
        self.file_run(source="by hand")
        self.assertIn("variations stage", self.why())

    def test_a_test_run_is_refused(self):
        self.assertIn("test run", self.why("brand-v2test-thing"))

    def test_build_refuses_before_writing_anything(self):
        with self.assertRaises(BadRequest):
            self.build(check_stage=True)
        self.assertFalse(self.out.exists())


class TestResolve(Base):
    """One front door for both lanes: the brief register decides by the brief's type."""
    def reg(self, rows):
        return {"briefs": H._register().Briefs(rows)}

    def setUp(self):
        super().setUp()
        vm = self.repo / "runs" / "video-production" / BRAND / "video-run-9"
        vm.mkdir(parents=True)
        (vm / "run.json").write_text("{}")
        (vm / "storyboard.json").write_text("{}")
        self.vm = vm
        self.rows = {KEY: {"brief": "brief-0325", "type": "image-ai", "brand": BRAND, "product": "widget", "run": RUN},
                     "testbrand_widget_brief-0326": {"brief": "brief-0326", "type": "video-ai", "brand": BRAND,
                                                     "product": "widget", "run": "video-run-9"},
                     "testbrand_widget_brief-0327": {"brief": "brief-0327", "type": "video-ai", "brand": BRAND,
                                                     "product": "widget", "run": "not-made-yet"},
                     "testbrand_gadget_brief-0325": {"brief": "brief-0325", "type": "image-ai", "brand": BRAND,
                                                     "product": "gadget", "run": "other-run"}}

    def test_picture_brief_by_key(self):
        it = H.resolve(KEY, repo=self.repo, reg=self.reg(self.rows))
        self.assertEqual((it["lane"], it["run"], it["brand"], it["brief"]), ("graphic-designer", RUN, BRAND, "brief-0325"))

    def test_picture_by_its_run(self):
        self.assertEqual(H.resolve(RUN, repo=self.repo, reg=self.reg(self.rows))["key"], KEY)

    def test_video_brief_finds_its_production_run(self):
        it = H.resolve("testbrand_widget_brief-0326", repo=self.repo, reg=self.reg(self.rows))
        self.assertEqual((it["lane"], Path(it["run"])), ("video-editor", self.vm))

    def test_video_run_folder_finds_its_brief(self):
        it = H.resolve(str(self.vm), repo=self.repo, reg=self.reg(self.rows))
        self.assertEqual((it["lane"], it["brief"]), ("video-editor", "brief-0326"))

    def test_video_with_no_production_run_is_refused(self):
        with self.assertRaises(BadRequest):
            H.resolve("testbrand_widget_brief-0327", repo=self.repo, reg=self.reg(self.rows))

    def test_shared_number_is_refused_by_name_never_guessed(self):
        with self.assertRaises(BadRequest) as c:
            H.resolve("brief-0325", BRAND, repo=self.repo, reg=self.reg(self.rows))
        self.assertIn("full brief key", str(c.exception))

    def test_unknown_brief_is_refused(self):
        with self.assertRaises(BadRequest):
            H.resolve("testbrand_widget_brief-0999", repo=self.repo, reg=self.reg(self.rows))


class TestAgnostic(unittest.TestCase):
    def test_no_person_named_in_the_code(self):
        """Lanes, paths, commands and buttons name the role; who fills it is a setting (the owner, 2026-10-27)."""
        src = (HERE / "image_edit" / "handoff.py").read_text() + (HERE / "handoff.py").read_text()
        people = json.loads((HERE / "delivery.json").read_text()) if (HERE / "delivery.json").is_file() else {}
        names = {(v or {}).get(f) or "" for bag in ("people", "roles") for v in (people.get(bag) or {}).values()
                 for f in ("name", "filled_by")}
        for n in sorted(x for x in names if len(x) > 2):
            self.assertNotRegex(src, r"(?i)\b" + re.escape(n) + r"\b", n)

    def test_no_brand_named_in_the_code(self):
        brands = Path(H.P.repo()) / "brands"
        names = [d.name for d in brands.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))] if brands.is_dir() else []
        src = (HERE / "image_edit" / "handoff.py").read_text().lower() + (HERE / "handoff.py").read_text().lower()
        for n in names:
            self.assertNotIn(n.lower(), src, n)


if __name__ == "__main__":
    unittest.main(verbosity=1)
