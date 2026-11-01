#!/usr/bin/env python3
"""The run sheet: one brief, one Higgsfield core, three renderings, one return step.

    /usr/bin/python3 components/briefs/tests/test_runsheet.py

No key, no network, no model: a fixture repo in a temp folder and a stand-in chain that answers the way the chain's
builders do (model-inputs preview, the clip builder, the Model House), with machine paths in its answers so the test
proves none of them reaches the sheet.
"""
import importlib.util, json, re, shutil, sys, tempfile, unittest
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("runsheet_under_test", COMPONENT / "runsheet.py")
RS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RS)

MACHINE_PATH = re.compile(r"/Users/|/private/|/var/folders/|/tmp/|/Volumes/|~/")
SECTIONS = ("## The core", "## A · Higgsfield web app", "## B · Claude Code", "## C · Codex or any other agent")
ELEMENT = "11111111-2222-4333-8444-555555555555"


def touch(p, text="x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


class FakeChain(RS.Chain):
    """The chain's builders, answered from the fixture (shapes as model-inputs preview returns them)."""

    def __init__(self, repo, records):
        super().__init__(repo)
        self.records = records
        self.calls = []

    def lookup(self, what, brand=None):
        k = next((k for k in self.records if k == what or k.endswith("_" + what)), None)
        if not k:
            raise SystemExit(f"{what} not in the fixture register")
        return k, self.records[k]

    def house(self, job):
        return {"job": job, "registry": "gpt-image-2.5" if job.startswith("pictures") else "seedance-2.5",
                "door": "higgsfield", "higgsfield_model": "gpt_image_2_5" if job.startswith("pictures") else "seedance_2_5"}

    def picture(self, recipe):
        self.calls.append(recipe)
        b = recipe.get("brief", recipe)
        base = b.get("base")
        kit = self.repo / "runs" / "ai-elements" / "acme" / "products" / "crush-serum"
        first = base or str(self.repo / "tools" / "image-teardown" / "runs" / "acme-run-1" / "assets" / "source.jpg")
        inputs = [{"n": 1, "role": "the reference", "path": first}]
        if not base:
            inputs.append({"n": 2, "role": "the real CRUSH: its product casting sheet", "path": str(kit / "model" / "product-sheet.png")})
            inputs.append({"n": 3, "role": "the real CRUSH: its back", "path": str(kit / "model" / "back.png")})
        prompt = ("INPUTS\nIMAGE 1 is the reference.\n\nTHE PICTURE\n" + (b.get("swaps") or "The tub becomes the real CRUSH.")
                  + f"\nmade on {self.repo}")                # a machine path inside the prompt text itself
        return {"vendor_model": "gpt_image_2_5", "prompt": prompt, "inputs": inputs,
                "settings": {"variant": "sunburst", "quality": "high", "resolution": "2k", "aspect": "9:16"},
                "fields": {"words_mode": "set on top after", "zones": ["Headline"], "words_plain": [b.get("our_copy", ["SHAVE / CLEAN"])[0]]},
                "send": {"bars": [0.1, 0.0]}, "findings": []}

    def variation(self, brief, change, approved):
        return {**brief, "base": str(approved) if approved else None,
                "swaps": "THE ONE CHANGE to IMAGE 1: " + change.get("picture", ""), "our_copy": change.get("words")}

    def needs_picture(self, change):
        return bool(change.get("picture"))

    def set_change(self, brand, run, variation, change, brief):
        if not getattr(self, "set_on", False):
            return None
        return {"set": f"one--{variation}", "change": change.get("picture"), "credits": 2.5, "print_words": f"Print on {self.repo}",
                "steps": ["Copy the collection.", "File it."], "flags": ["the change names no real size in centimetres"],
                "kept_print": "runs/image-production/acme/prompt-bench/acme-run-1-20261027-120000.png",
                "product": {"sheet": "runs/ai-elements/acme/products/crush-serum/model/product-sheet.png"}}

    def slides(self, brief_file):
        m = re.search(r"```json\s*(\[.*?\])\s*```", Path(brief_file).read_text(), re.S)
        return (json.loads(m.group(1)), None) if m else ([], "no slide-deltas block in the brief")

    def slide(self, brand, n, change, keep):
        return {"instruction": f"Keep the reference exactly; change only this: {change}",
                "refused": "this asks for 3 changes at once." if "AND" in change else None}

    def clip(self, run, call=None):
        prod = self.repo / "runs" / "video-production" / run
        calls = [{"id": "G01-C1", "seconds": 6, "talking": True, "scenes": ["S1"]},
                 {"id": "G02-C1", "seconds": 4, "talking": False, "scenes": ["S2"]}]
        c = call or "G01-C1"
        talking = c == "G01-C1"
        inputs = [{"n": 1, "kind": "image", "role": "the start picture", "path": str(prod / "media" / "S1-F1.png")}]
        if talking:
            inputs.append({"n": 1, "kind": "audio", "role": "the voice read of S1", "path": str(prod / "vo" / "S1.mp3")})
        else:
            inputs.append({"n": 2, "kind": "image", "role": "the end picture", "path": "S2-FLAST (not made yet)"})
        return {"prompt": f"Image 1 is the first frame. {c}", "inputs": inputs, "calls": calls,
                "settings": {"duration": 6 if talking else 4, "aspect": "9:16", "resolution": "480p", "audio": talking},
                "fields": {"call": c}, "send": {"masters_people": ["THE BARBER"] if talking else [], "videos": []}}

    def elements(self):
        return {}


class RunSheetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        r = self.tmp
        # the picture brief: filed run, approved picture with recipe and plate, two variations
        touch(r / "runs/image-teardown/acme/acme-run-1/deliverable/06-brief.md",
              "# DOCUMENT ONE\n\n# BRIEF · ACME · CRUSH · The tub swap\n\n| | |\n")
        touch(r / "tools/image-teardown/runs/acme-run-1/assets/source.jpg")
        touch(r / "tools/image-teardown/runs/acme-run-1/out/variations.json", json.dumps({
            "source": "stage5", "variations": [
                {"id": "v1", "label": "words only", "words": ["NEW / WORDS"]},
                {"id": "v2", "label": "one picture change", "words": ["OTHER"], "picture": "The tub is wet."}]}))
        bench = r / "runs/image-production/acme/prompt-bench"
        touch(bench / "acme-run-1-20261027-120000.liked.json", "{}")
        touch(bench / "acme-run-1-20261027-120000.recipe.json", json.dumps({"brief": {"brand": "acme", "run": "acme-run-1", "product": "crush"}}))
        touch(bench / "acme-run-1-20261027-120000.plate.png")
        touch(bench / "acme-run-1-20261027-120000.png")
        kit = r / "runs/ai-elements/acme/products/crush-serum"
        touch(kit / "kit.json", json.dumps({"aliases": ["crush"]}))
        touch(kit / "model/product-sheet.png")
        touch(kit / "model/back.png")
        touch(r / "runs/ai-elements/PRODUCT-INDEX.json", json.dumps({"products": {"acme/crush-serum": {
            "name": "CRUSH", "assets": {"kit": "runs/ai-elements/acme/products/crush-serum/kit.json",
                                        "higgsfield_element": {"id": ELEMENT, "name": "acme-crush-master"},
                                        "drive": {"packshot": {"label": "Shared Assets/brands/acme/products/crush-serum/packshot", "files": 2}}}}}}))
        # the video brief: a writing deliverable and a production run named by the brief key
        touch(r / "runs/video-writing/acme/vid-1/deliverable/5-brief.md", "LANE: AI\n\n# The barber skit\n")
        prod = r / "runs/video-production/acme/acme_crush_brief-0002"
        touch(prod / "storyboard.json", "{}")
        touch(prod / "plan.json", "{}")
        touch(prod / "media/S1-F1.png")
        touch(prod / "vo/S1.mp3")
        touch(prod / "elements-lock.json", json.dumps({"items": ["person THE BARBER → runs/ai-elements/acme/casting/barber-1"]}))
        (r / "runs/ai-elements/acme/casting/barber-1").mkdir(parents=True)
        self.records = {
            "acme_crush_brief-0001": {"id": "acme_crush_brief-0001", "brief": "brief-0001", "type": "image-ai", "brand": "acme",
                                      "product": "crush", "run": "acme-run-1"},
            "acme_crush_brief-0002": {"id": "acme_crush_brief-0002", "brief": "brief-0002", "type": "video-ai", "brand": "acme",
                                      "product": "crush", "run": "vid-1"},
            "acme_crush_brief-0003": {"id": "acme_crush_brief-0003", "brief": "brief-0003", "type": "sequence-ai", "brand": "acme",
                                      "product": "crush", "run": "acme-seq-1"},
        }
        # the carousel brief: a written brief with its slide-deltas block, slide one not approved yet
        touch(r / "runs/image-teardown/acme/acme-seq-1/deliverable/06-brief.md",
              "# DOCUMENT ONE\n\n# Three bumps\n\n```json\n" + json.dumps([
                  {"slide": 2, "change": "Move the circles up.", "keep": ["the circles"],
                   "type": [{"element": "zone_a", "text": "NEVER\nTHE RAZOR"}, {"element": "zone_b", "text": "unchanged"}]},
                  {"slide": 3, "change": "Tint the ground green.", "keep": [], "type": []}]) + "\n```\n")
        self.chain = FakeChain(r, self.records)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sheet(self, key):
        return RS.build(key, repo=self.tmp, chain=self.chain)

    def assert_three_sections_and_return(self, md, sheet):
        for s in SECTIONS:
            self.assertIn(s, md, s)
        ret = RS.return_step(sheet)
        parts = md.split("## A · ")[1]
        for sec in ("Higgsfield web app", "B · Claude Code", "C · Codex or any other agent"):
            chunk = parts.split(sec, 1)[1] if sec in parts else parts
            nxt = re.split(r"\n## [A-C] · ", chunk)[0]
            self.assertTrue(nxt.rstrip().endswith(ret), f"{sec} does not end with the return step")
        self.assertEqual(md.count(ret), 3)
        self.assertIn(sheet["return"]["repo"], ret)
        self.assertIn(sheet["return"]["drive"], ret)

    # -------------------------------------------------------------------------------------------- pictures

    def test_picture_sheet_core(self):
        s = self.sheet("acme_crush_brief-0001")
        self.assertEqual(s["core"], "higgsfield")
        self.assertEqual(s["product"], "crush-serum")                 # the brief's word resolved by the kit's alias
        self.assertEqual(s["title"], "CRUSH · The tub swap")
        self.assertEqual([x["asset"] for x in s["steps"]],
                         [f"acme_crush_brief-0001_asset-{n:02d}.png" for n in (1, 2, 3)])
        one = s["steps"][0]
        self.assertEqual(one["higgsfield_model"], "gpt_image_2_5")
        self.assertEqual(one["settings"], {"aspect_ratio": "9:16", "variant": "sunburst", "quality": "high",
                                           "resolution": "2k", "count": 1})
        self.assertEqual(one["references"][0]["file"], "tools/image-teardown/runs/acme-run-1/assets/source.jpg")
        self.assertIsNone(one["references"][1]["element"]["element"])     # a product goes by its sheet file
        self.assertEqual(one["words_on_top"], [{"zone": "Headline", "words": "SHAVE / CLEAN"}])
        self.assertIn("approved picture's own recipe", one["prompt_source"])
        # a words-only variation makes no picture; a picture variation edits the plate
        self.assertEqual(s["steps"][1]["job"], "words-only")
        self.assertEqual(s["steps"][1]["words_on_top"], [{"zone": "Headline", "words": "NEW / WORDS"}])   # the main picture's zone names
        three = s["steps"][2]
        self.assertTrue(three["references"][0]["file"].endswith(".plate.png"))
        self.assertTrue(three["references"][0]["role"].startswith("the approved picture"))
        self.assertIn("THE ONE CHANGE", three["prompt"])
        self.assertEqual(s["return"]["repo"], "runs/handoffs/graphic-designer/acme/acme_crush_brief-0001/returned/")
        self.assertEqual(s["return"]["drive"], "Shared Assets/runs/handoffs/graphic-designer/acme/acme_crush_brief-0001/returned/")
        self.assertEqual(s["deliverable"], "runs/image-teardown/acme/acme-run-1/deliverable")

    def test_picture_sheet_renders_three_sections_and_return(self):
        s = self.sheet("acme_crush_brief-0001")
        md = RS.render_md(s)
        self.assert_three_sections_and_return(md, s)
        self.assertNotIn("@acme-crush-master", md)                    # a product's element is never offered
        self.assertNotIn(f"<<<{ELEMENT}>>>", md)
        self.assertIn('"model": "gpt_image_2_5"', md)                  # (b) the MCP call
        self.assertIn("higgsfield generate create gpt_image_2_5", md)  # (c) the command line
        self.assertIn("--image-references tools/image-teardown/runs/acme-run-1/assets/source.jpg", md)

    def test_return_asks_for_higgsfields_own_record_and_text_from_github(self):
        """2026-10-28: a retyped prompt came back corrupted and the Drive connector changed text; the proof is the
        generation record Higgsfield itself holds, saved unchanged beside the file, and text is read from GitHub."""
        s = self.sheet("acme_crush_brief-0001")
        rec = s["return"]["receipt"]["record"]
        self.assertEqual(rec["name_pattern"], "acme_crush_brief-0001_asset-NN.record.json")
        self.assertIn("exactly as the Higgsfield tool returns it", rec["what"])
        ret = RS.return_step(s)
        self.assertIn("acme_crush_brief-0001_asset-01.record.json", ret)
        self.assertIn("saved unchanged, never retyped", ret)
        for text in (ret, RS.LEAN):
            self.assertIn("Read BRIEF.md, RUN.md and run.json from GitHub (company-team/workspace", text)
            self.assertIn("Take pictures, clips and voice files from the Drive.", text)
        self.assertIn("Read each step's prompt out of run.json with code and pass that string unchanged; "
                      "never retype a prompt.", RS.LEAN)
        claude = RS.render_md(s).split("## B · ", 1)[1].split("\n## C · ", 1)[0]
        self.assertIn(RS.LEAN, claude)                                 # section B carries it

    def test_no_machine_paths_anywhere(self):
        for key in ("acme_crush_brief-0001", "acme_crush_brief-0002"):
            out = RS.write(key, self.tmp / "out" / key, repo=self.tmp, chain=self.chain)
            md, js = Path(out["md"]).read_text(), Path(out["json"]).read_text()
            self.assertIsNone(MACHINE_PATH.search(md), f"{key} RUN.md: {MACHINE_PATH.search(md)}")
            # the prompt is the chain's own text; the paths the SHEET writes (files, folders, return) are all repo-relative
            data = json.loads(js)
            files = [r["file"] for st in data["steps"] for r in st["references"]] + [data["return"]["repo"], data["brief_file"]]
            files += [e.get("folder") or "" for e in data["elements"]]
            for f in files:
                self.assertFalse(str(f).startswith("/"), f)
                self.assertIsNone(MACHINE_PATH.search(str(f)), f)

    # -------------------------------------------------------------------------------------------- video

    def test_video_sheet_core(self):
        s = self.sheet("acme_crush_brief-0002")
        self.assertEqual(s["kind"], "video")
        self.assertEqual(s["production_run"], "runs/video-production/acme/acme_crush_brief-0002")
        self.assertEqual(s["return"]["role"], "video-editor")
        a, b = s["steps"]
        self.assertEqual(a["asset"], "acme_crush_brief-0002_asset-01.mp4")
        self.assertEqual(a["higgsfield_model"], "seedance_2_5")
        self.assertEqual(a["settings"]["endpoint"], "bytedance/seedance-2.5/reference-to-video")
        self.assertEqual([r["media_role"] for r in a["references"]], ["image_references", "audio_references"])
        self.assertEqual(b["settings"]["endpoint"], "bytedance/seedance-2.5/image-to-video")
        self.assertEqual([r["media_role"] for r in b["references"]], ["start_image", "end_image"])
        self.assertEqual(a["cast"][0]["folder"], "runs/ai-elements/acme/casting/barber-1")
        self.assertIsNone(a["cast"][0]["element"])
        self.assertTrue(any("THE BARBER" in g and "no Higgsfield element" in g for g in s["gaps"]))
        self.assertTrue(any("S2-FLAST (not made yet)" in g for g in s["gaps"]))

    def test_video_sheet_renders_three_sections_and_return(self):
        s = self.sheet("acme_crush_brief-0002")
        md = RS.render_md(s)
        self.assert_three_sections_and_return(md, s)
        self.assertIn("Video → Create Video", md)
        self.assertIn('"mode": "omni_reference"', md)
        self.assertIn("POST `bytedance/seedance-2.5/reference-to-video`", md)

    # -------------------------------------------------------------------------------------------- the hand-off copy

    def test_pack_makes_the_folder_self_contained(self):
        s = self.sheet("acme_crush_brief-0001")
        out = RS.pack(s, repo=self.tmp)
        home = "runs/handoffs/graphic-designer/acme/acme_crush_brief-0001"
        root = self.tmp / home
        self.assertEqual(out["folder"], home)
        self.assertEqual(out["drive"], "Shared Assets/" + home)
        for f in ("BRIEF.md", "RUN.md", "run.json"):
            self.assertTrue((root / f).is_file(), f)
        self.assertIn("The tub swap", (root / "BRIEF.md").read_text())
        names = sorted(p.name for p in (root / "refs").iterdir())
        self.assertEqual(names, ["approved-plate.png", "product-crush-serum-back.png", "product-crush-serum-sheet.png",
                                 "step-01-image-1-swipe.jpg"])
        data = json.loads((root / "run.json").read_text())
        for st in data["steps"]:
            for r in st["references"]:
                self.assertTrue(r["local"].startswith("refs/"), r)
                self.assertEqual(r["file"], f"{home}/{r['local']}")
                self.assertEqual(r["drive"], f"Shared Assets/{home}/{r['local']}")
                self.assertTrue((root / r["local"]).is_file(), r)        # every file RUN.md names is in the folder
        one = data["steps"][0]["references"]
        self.assertEqual(one[0]["source"], "tools/image-teardown/runs/acme-run-1/assets/source.jpg")
        self.assertEqual(data["return"]["drive"], f"Shared Assets/{home}/returned/")
        self.assertFalse(any(g.startswith("Reference files are named by their repo path") for g in data["gaps"]))
        md = (root / "RUN.md").read_text()
        self.assert_three_sections_and_return(md, data)
        self.assertIsNone(MACHINE_PATH.search(md))
        web = md.split("## A · ")[1].split("## B · ")[0]
        claude = md.split("## B · ")[1].split("## C · ")[0]
        # a product goes by its sheet file in both sections, never its element, which falls behind the sheet
        self.assertNotIn("@acme-crush-master", web)
        self.assertNotIn(f"<<<{ELEMENT}>>>", claude)
        self.assertIn("refs/product-crush-serum-sheet.png", web)
        self.assertIn("refs/product-crush-serum-sheet.png", claude)
        self.assertIn("`refs/step-01-image-1-swipe.jpg`", web)
        self.assertIn(f"`refs/product-crush-serum-sheet.png` · `{home}/refs/product-crush-serum-sheet.png` · "
                      f"`Shared Assets/{home}/refs/product-crush-serum-sheet.png`", md)
        # a second pack writes over the same names and deletes nothing
        (root / "returned" / "keep.png").write_text("x")
        RS.pack(s, repo=self.tmp)
        self.assertTrue((root / "returned" / "keep.png").is_file())
        self.assertEqual(sorted(p.name for p in (root / "refs").iterdir()), names)

    def test_pack_video_carries_the_cast_picture(self):
        touch(self.tmp / "runs/ai-elements/acme/casting/barber-1/sheets/headshot.jpg")
        s = self.sheet("acme_crush_brief-0002")
        out = RS.pack(s, repo=self.tmp)
        locals_ = [x["local"] for x in out["refs"]]
        self.assertIn("refs/cast-barber-1-headshot.jpg", locals_)
        self.assertIn("refs/start-picture.png", locals_)                # one file two steps use: named by its role
        self.assertIn("refs/step-01-audio-2-voice-read-s1.mp3", locals_)
        md = (self.tmp / out["folder"] / "RUN.md").read_text()
        self.assertIn("upload `refs/cast-barber-1-headshot.jpg`", md)

    def test_pack_makes_the_folder_self_contained(self):
        s = self.sheet("acme_crush_brief-0001")
        out = RS.pack(s, repo=self.tmp)
        home = "runs/handoffs/graphic-designer/acme/acme_crush_brief-0001"
        root = self.tmp / home
        self.assertEqual(out["folder"], home)
        self.assertEqual(out["drive"], "Shared Assets/" + home)
        for f in ("BRIEF.md", "RUN.md", "run.json"):
            self.assertTrue((root / f).is_file(), f)
        self.assertIn("The tub swap", (root / "BRIEF.md").read_text())
        data = json.loads((root / "run.json").read_text())
        for st in data["steps"]:
            for r in st["references"]:
                self.assertTrue(r["local"].startswith("refs/"), r)
                self.assertEqual(r["file"], f"{home}/{r['local']}")
                self.assertEqual(r["drive"], f"Shared Assets/{home}/{r['local']}")
                self.assertTrue((root / r["local"]).is_file(), r)        # every file RUN.md names is in the folder
        self.assertEqual(data["return"]["drive"], f"Shared Assets/{home}/returned/")
        self.assertFalse(any(g.startswith("Reference files are named by their repo path") for g in data["gaps"]))
        md = (root / "RUN.md").read_text()
        self.assert_three_sections_and_return(md, data)
        self.assertIsNone(MACHINE_PATH.search(md))

    # -------------------------------------------------------------------------------------------- carousels

    def test_carousel_is_slide_one_then_one_edit_per_slide(self):
        s = self.sheet("acme_crush_brief-0003")
        self.assertEqual(s["kind"], "sequence")
        self.assertEqual(s["return"]["role"], "graphic-designer")
        self.assertEqual([x["asset"] for x in s["steps"]], [f"acme_crush_brief-0003_asset-0{n}.png" for n in (1, 2, 3)])
        one, two, three = s["steps"]
        self.assertIn("Move the circles up.", two["prompt"])
        self.assertEqual(two["higgsfield_model"], one["higgsfield_model"])
        self.assertEqual(two["references"][0]["file"], f"{one['asset']} (not made yet: step 1 makes it, before its words go on)")
        self.assertEqual(two["words_on_top"], [{"zone": "zone_a", "words": "NEVER / THE RAZOR"}])   # "unchanged" is no words
        self.assertEqual(three["words_on_top"], [])
        self.assertTrue(any(g.startswith("Slide one has no approved picture yet") for g in s["gaps"]))
        self.assertFalse(any("(not made yet" in g for g in s["gaps"]))                              # step 1 makes it: no gap
        self.assert_three_sections_and_return(RS.render_md(s), s)

    def test_carousel_edits_the_approved_plate_when_there_is_one(self):
        bench = self.tmp / "runs/image-production/acme/prompt-bench"
        touch(bench / "acme-seq-1-20261030-120000.liked.json", "{}")
        touch(bench / "acme-seq-1-20261030-120000.recipe.json", json.dumps({"brief": {"brand": "acme", "run": "acme-seq-1", "product": "crush"}}))
        touch(bench / "acme-seq-1-20261030-120000.plate.png")
        touch(bench / "acme-seq-1-20261030-120000.png")
        s = self.sheet("acme_crush_brief-0003")
        self.assertEqual(s["steps"][1]["references"][0]["file"],
                         "runs/image-production/acme/prompt-bench/acme-seq-1-20261030-120000.plate.png")
        self.assertTrue(s["steps"][1]["references"][0]["exists"])
        self.assertFalse(any(g.startswith("Slide one has no approved picture yet") for g in s["gaps"]))

    def test_carousel_with_no_deltas_block_says_so(self):
        touch(self.tmp / "runs/image-teardown/acme/acme-seq-1/deliverable/06-brief.md", "# Three bumps\n")
        s = self.sheet("acme_crush_brief-0003")
        self.assertEqual(len(s["steps"]), 1)
        self.assertTrue(any(g.startswith("Only slide 1 is on this sheet") for g in s["gaps"]))

    def test_carousel_refused_slide_is_said_by_name(self):
        touch(self.tmp / "runs/image-teardown/acme/acme-seq-1/deliverable/06-brief.md",
              "# Three bumps\n```json\n" + json.dumps([{"slide": 2, "change": "This AND that AND more."}]) + "\n```\n")
        s = self.sheet("acme_crush_brief-0003")
        self.assertTrue(any(g.startswith("slide 2: the edit rule refuses it") for g in s["gaps"]))

    def test_carousel_pack_writes_the_folder(self):
        s = self.sheet("acme_crush_brief-0003")
        out = RS.pack(s, repo=self.tmp)
        root = self.tmp / out["folder"]
        self.assertEqual(out["folder"], "runs/handoffs/graphic-designer/acme/acme_crush_brief-0003")
        for f in ("BRIEF.md", "RUN.md", "run.json"):
            self.assertTrue((root / f).is_file(), f)
        self.assertEqual(out["missing"], [])

    # -------------------------------------------------------------------------------------------- 3D set changes

    def test_a_picture_change_on_a_kept_set_is_a_set_step_never_a_flat_prompt(self):
        self.chain.set_on = True
        s = self.sheet("acme_crush_brief-0001")
        st = s["steps"][2]
        self.assertEqual(st["job"], "set-change")
        self.assertEqual(st["set_request"]["set"], "one--v2")
        self.assertIsNone(st["higgsfield_model"])
        self.assertNotIn("THE ONE CHANGE", st["prompt"])
        self.assertEqual([r["n"] for r in st["references"]], [1, 2])
        self.assertTrue(any("the set change: the change names no real size" in g for g in s["gaps"]))
        self.assertEqual(s["steps"][1]["job"], "words-only")                       # a words row stays a words row
        md = RS.render_md(s)
        self.assert_three_sections_and_return(md, s)
        self.assertEqual(md.count("in Higgsfield 3D Jutsu, never a flat picture"), 3)
        self.assertIsNone(MACHINE_PATH.search(md))
        out = RS.pack(s, repo=self.tmp)
        data = json.loads((self.tmp / out["folder"] / "run.json").read_text())
        self.assertTrue(all(r["local"].startswith("refs/") for r in data["steps"][2]["references"]))

    def test_a_run_with_no_kept_set_keeps_its_flat_step(self):
        s = self.sheet("acme_crush_brief-0001")
        self.assertEqual(s["steps"][2]["job"], "pictures.generate")

    def test_a_brief_no_sheet_covers_is_refused_by_name(self):
        with self.assertRaises(SystemExit):
            RS._kind({"id": "x", "type": "email"})

    def test_pack_refuses_without_a_written_brief(self):
        s = self.sheet("acme_crush_brief-0001")
        s["brief_file"] = None
        with self.assertRaises(ValueError):
            RS.pack(s, repo=self.tmp)

    def test_cast_element_from_elements_index(self):
        touch(self.tmp / "runs/ai-elements/ELEMENTS-INDEX.json", json.dumps({"elements": {
            "acme/casting/barber-1": {"higgsfield_element": {"id": "c0ffee00-0000-4000-8000-000000000001", "name": "acme-barber-1"}}}}))
        self.chain.elements = RS.Chain.elements.__get__(self.chain)    # read the real file this time
        s = self.sheet("acme_crush_brief-0002")
        self.assertEqual(s["steps"][0]["cast"][0]["element"]["name"], "acme-barber-1")
        self.assertIn("<<<c0ffee00-0000-4000-8000-000000000001>>>", RS.render_md(s))


class SongDraftTest(unittest.TestCase):
    def test_song_uses_master_slices_and_singing_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            chain = FakeChain(Path(tmp), {})
            house = chain.house
            chain.house = lambda job: ({"job": job, "registry": "seedance-2.0", "door": "higgsfield", "higgsfield_model": "seedance_2_0"} if job == "clips.song_ad" else house(job))
            data = {"piece": {"format": "song-ad"}, "scenes": [
                {"id": "S1", "to_camera": True, "voice": "sung", "first_frame": {"subject": "Singer"}, "shots": [{"id": "A", "lines": [{"say": "My lyric"}]}]},
                {"id": "S2", "to_camera": False, "voice": "sung over b-roll", "first_frame": {"subject": "Car"}}]}
            steps, _ = RS.draft_steps("acme_crush_brief-0001", {"brand": "acme"}, "```json\n" + json.dumps(data) + "\n```", chain, {}, {}, Path(tmp))
            self.assertEqual(len(steps), 4)
            self.assertEqual(steps[1]["job"], "clips.song_ad")
            self.assertIn("seedance-2.0/", steps[1]["settings"]["endpoint"])
            self.assertIn("Suno", steps[1]["references"][1]["file"])
            self.assertNotIn("Says:", steps[1]["prompt"])
            self.assertNotIn("banked voice", json.dumps(steps))
            self.assertEqual(steps[3]["job"], "clips.seedance")
            self.assertEqual(len(steps[3]["references"]), 1)
            self.assertTrue(steps[1]["findings"])
            cut = RS.cut_plan({"brief_key": "k", "format": "song-ad", "steps": steps})
            self.assertIn("Mute all generated clip audio", " ".join(cut["rules"]))


class CutStepTest(unittest.TestCase):
    """A video brief ends in one cut, in every rendering; a picture brief has none."""

    def test_video_sheet_ends_in_one_cut(self):
        sheet = {"brief_key": "b_p_brief-0001", "steps": [{"asset": "b_p_brief-0001_asset-01.mp4"},
                                                          {"asset": "b_p_brief-0001_asset-02.mp4"}]}
        c = RS.cut_plan(sheet)
        self.assertEqual(c["asset"], "b_p_brief-0001-control.mp4")
        self.assertEqual(c["order"], ["b_p_brief-0001_asset-01.mp4", "b_p_brief-0001_asset-02.mp4"])
        text = "\n".join(RS.cut_step({**sheet, "cut": c}))
        self.assertIn("b_p_brief-0001-control.mp4", text)
        self.assertIn("keeps its own sound", text)

    def test_no_cut_without_video(self):
        self.assertEqual(RS.cut_step({"brief_key": "k", "steps": []}), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
