"""image-edit — the discipline, the libraries, both judges, the filing.

Every test builds a throwaway workspace under `tempfile`, points AI_WORKSPACE
at it, and stubs the image engine's provider and both judges. No network, no
model, no real key, nothing written outside `tempfile`.

    python3 tools/image-edit/tests/test_image_edit.py
"""
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "image-production"))
import image_edit as RE  # noqa: E402
from image_edit import discipline as D, engine as E, compare as CMP  # noqa: E402
import image_production as IP  # noqa: E402


# ------------------------------------------------------------------ fixtures

def png_bytes(w=4, h=5):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def stub_transport(calls, size=(4, 5)):
    """The image engine's provider door, answered locally with a PNG — and the
    9:16 finish's outpaint answered with a 1024x1536 one."""
    import base64
    def t(method, url, headers, body):
        calls.append({"url": url, "body": body})
        if b'name="mask"' in body:
            from PIL import Image
            import io
            buf = io.BytesIO(); Image.new("RGB", (1024, 1536), (200, 200, 200)).save(buf, "PNG")
            return 200, {}, json.dumps({"data": [{"b64_json": base64.b64encode(buf.getvalue()).decode()}]}).encode()
        b64 = base64.b64encode(png_bytes(*size)).decode()
        if "openai" in url:
            return 200, {}, json.dumps({"data": [{"b64_json": b64}], "id": "stub"}).encode()
        return 200, {}, json.dumps({"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "image/png", "data": b64}}]}}]}).encode()
    return t


def judge_saying(v):
    def caller(prompt, img_path, entry):
        return json.dumps({"results": [{"test": 1, "verdict": v, "evidence": "stub"}]})
    return caller


def compare_saying(verdicts, seen=None):
    """verdicts: list per test, e.g. ["PASS","PASS"] or ["PASS","FAIL"]. One
    result per numbered test in the prompt: these first, then PASS for the rest."""
    import re
    def caller(prompt, paths, entry):
        if seen is not None:
            seen.append({"prompt": prompt, "paths": list(paths)})
        n = len(re.findall(r"^\d+\. ", prompt, re.M))
        answer = (list(verdicts) + ["PASS"] * n)[:n]
        return json.dumps({"results": [{"test": i + 1, "verdict": v, "evidence": "stub"}
                                       for i, v in enumerate(answer)]})
    return caller


class StubLibrary:
    def get(self, element, asset, id_):
        return None


def fake_workspace(tmp):
    root = Path(tmp)
    (root / "components").mkdir(parents=True, exist_ok=True)
    b = root / "brands" / "acme"
    (b / "identity").mkdir(parents=True, exist_ok=True)
    (b / "products" / "widget" / "images").mkdir(parents=True, exist_ok=True)
    (b / "identity" / "palette.md").write_text("| Ink | `#112233` |\n")
    (b / "identity" / "fonts.md").write_text("A font.\n")
    (b / "identity" / "acme-logo.png").write_bytes(png_bytes())
    (b / "products" / "images.json").write_text(json.dumps({"products": {
        "widget": {"title": "The Widget", "cutout": "products/widget/images/packshot.png"}}}))
    (b / "products" / "widget" / "images" / "packshot.png").write_bytes(png_bytes())
    (b / "ai-elements").mkdir(parents=True, exist_ok=True)
    (b / "ai-elements" / "element-facts.json").write_text(json.dumps({"elements": {}}))
    return root


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="refedit-test-")
        self.root = fake_workspace(self.tmp)
        self._old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.root)
        self.pic = Path(self.tmp) / "p152-01.png"
        self.pic.write_bytes(png_bytes(4, 5))
        self.out = Path(self.tmp) / "out"
        self.calls = []

    def tearDown(self):
        if self._old is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def req(self, **kw):
        base = {"brand": "acme", "picture": str(self.pic), "out": str(self.out)}
        base.update(kw)
        return base

    def run_edit(self, compare=("PASS", "PASS"), judge="PASS", seen=None, **kw):
        return RE.edit(self.req(**kw), transport=stub_transport(self.calls),
                       judge_caller=judge_saying(judge),
                       compare_caller=compare_saying(list(compare), seen),
                       mirror=False, library=StubLibrary())


# ------------------------------------------------------------ the discipline

class TestDiscipline(unittest.TestCase):
    def test_one_change_counts_as_one(self):
        self.assertEqual(D.count_changes("she is front-on, not in profile"), 1)

    def test_five_edits_in_one_sentence_are_counted(self):
        n = D.count_changes("change the room, swap the jacket, move the shelves, add a lamp and turn her head")
        self.assertGreater(n, D.MAX_CHANGES)

    def test_the_instruction_carries_the_keeps_and_the_delta_only(self):
        t = D.instruction(["the face", "the layout"], "the tube is in her left hand.")
        self.assertIn("Keep the reference image exactly as it is — the face; the layout —", t)
        self.assertTrue(t.endswith("change only this: the tube is in her left hand."))

    def test_an_element_id_rides_along(self):
        t = D.instruction(["x"], "swap the tube", ["abc-123"])
        self.assertIn("<<<abc-123>>> is reproduced exactly from its own reference", t)

    def test_too_many_changes_are_refused_by_count(self):
        change = "change the room, swap the jacket, move the shelves, add a lamp and turn her head"
        self.assertIn("changes at once", D.guard(change, D.instruction(["x"], change)))

    def test_a_description_is_refused_by_length(self):
        change = "the " + "very " * 90 + "long room"
        self.assertIn("past the 400 band", D.guard(change, D.instruction(["x"], change)))

    def test_quoted_words_are_one_change_and_not_in_the_band(self):
        words = '"' + "a line, with commas, and an and, " * 20 + '"'
        change = "the hand turns palm-up; the words change to " + words
        self.assertLessEqual(D.count_changes(change), D.MAX_CHANGES)
        self.assertIsNone(D.guard(change, D.instruction(["x"], change)))

    def test_face_visible_is_not_a_change(self):
        self.assertLessEqual(D.count_changes(
            "he now wears over-ear headphones and a knit sweater, sitting back relaxed, "
            "looking off to the side, face visible"), D.MAX_CHANGES)
        self.assertEqual(D.count_changes("she faces the window"), 1)

    def test_the_default_splits_are_read_from_the_file(self):
        s = D.split_for("picture")
        self.assertIn("every person and their face", s["keep"])
        for k in ("frame-A", "frame-B", "frame-C", "slide"):
            self.assertTrue(D.split_for(k)["keep"])

    def test_an_unknown_kind_names_the_real_ones(self):
        with self.assertRaises(SystemExit) as cm:
            D.split_for("poster")
        self.assertIn("picture", str(cm.exception))

    def test_a_callers_own_split_outranks_the_default(self):
        s = D.split_for("picture", {"keep": ["only this"]})
        self.assertEqual(s["keep"], ["only this"])


# ------------------------------------------------------------- the request

class TestRequest(Base):
    def test_a_field_nobody_declared_is_refused(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(change="x", colour="red"))
        self.assertIn("colour", str(cm.exception))

    def test_change_or_fix_exactly_one(self):
        with self.assertRaises(RE.BadRequest):
            RE.resolve(self.req())
        with self.assertRaises(RE.BadRequest):
            RE.resolve(self.req(change="x", fix="logo"))

    def test_the_reference_must_be_on_this_machine(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(picture="/nowhere/p.png", change="x"))
        self.assertIn("not a file on this machine", str(cm.exception))

    def runnable_text_fix(self):
        """The library's `text` row as a draft — the real one is deprecated
        and refused (SI-158 (edits never overwrite)); its slots still test filling."""
        return {"text": dict(RE.fixes()[0]["text"], status="draft")}

    def test_a_fix_fills_its_slots_and_adds_its_checks(self):
        r = RE.resolve(self.req(fix="text", args={"was": "SAALE", "now": "SALE"}),
                       fix_table=self.runnable_text_fix())
        self.assertIn('reads "SAALE" so it reads "SALE"', r["asked"])
        self.assertTrue(any('"SALE"' in c for c in r["checks"]))
        self.assertIn("every other word in the picture", r["instruction"])

    def test_a_fix_missing_a_slot_is_refused_by_name(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(fix="text", args={"was": "SAALE"}), fix_table=self.runnable_text_fix())
        self.assertIn("now", str(cm.exception))

    def test_an_unknown_fix_names_the_real_ones(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(fix="sharpen"))
        self.assertIn("logo", str(cm.exception))

    def test_words_ride_on_the_change_but_the_guard_reads_the_change(self):
        r = RE.resolve(self.req(change="the hand turns palm-up and the cup is lifted",
                                words=["WASH YOUR FACE", "find your method"]))
        self.assertIsNone(r["refused"])
        self.assertIn('the words change to "WASH YOUR FACE" / "find your method"', r["asked"])
        self.assertIn('"WASH YOUR FACE"', r["instruction"])

    def test_the_logo_fix_asks_for_the_brand_logo(self):
        r = RE.resolve(self.req(fix="logo"))
        self.assertEqual(r["brand_refs"], ["logo"])

    def test_the_frame_is_read_off_the_picture(self):
        self.assertEqual(E.dims(self.pic), (4, 5))
        self.assertEqual(E.nearest_aspect((4, 5), IP.route.aspects()), "4:5")
        self.assertEqual(E.nearest_aspect((9, 16), IP.route.aspects()), "9:16")

    def test_a_4x5_or_9x16_reference_leaves_at_9x16_and_others_as_they_are(self):
        self.assertEqual(E.deliver_frame(self.pic), "9:16")
        tall = Path(self.tmp) / "asset.png"; tall.write_bytes(png_bytes(9, 16))
        self.assertEqual(E.deliver_frame(tall), "9:16")
        sq = Path(self.tmp) / "sq.png"; sq.write_bytes(png_bytes(4, 4))
        self.assertIsNone(E.deliver_frame(sq))

    def test_the_run_lands_under_runs_image_edit_brand_label(self):
        r = RE.resolve({"brand": "acme", "picture": str(self.pic), "change": "x"})
        self.assertTrue(r["out"].endswith("runs/image-edit/acme/p152-01--edit"))


# ----------------------------------------------------------------- the run

class TestEdit(Base):
    def test_a_refused_delta_spends_nothing_and_keeps_the_record(self):
        r = self.run_edit(change="change the room, swap the jacket, move the shelves, add a lamp and turn her head")
        self.assertEqual(r["state"], "refused")
        self.assertEqual(self.calls, [])
        rec = json.loads((self.out / "edit.json").read_text())
        self.assertIn("changes at once", rec["refused"])
        # a refusal is still a run that happened, and the index must see it
        run = json.loads((self.out / "run.json").read_text())
        self.assertEqual((run["machine"], run["state"]), ("image-edit", "refused"))

    def test_a_dry_run_resolves_the_engine_request_and_spends_nothing(self):
        r = self.run_edit(change="the tube is in her left hand", dry_run=True)
        self.assertEqual(r["state"], "dry")
        self.assertEqual(self.calls, [])
        self.assertEqual(r["engine_request"]["from_image"], str(self.pic))
        self.assertEqual(r["engine_request"]["aspect"], "9:16")     # assets are 9:16 only
        self.assertTrue(r["engine_request"]["direction"].startswith("Keep the reference image exactly"))

    def test_an_edit_goes_through_the_engine_as_an_edit_and_both_judges(self):
        seen = []
        r = self.run_edit(change="the tube is in her left hand", seen=seen)
        self.assertEqual(r["state"], "filed")
        self.assertEqual(r["engine"]["model"], "gpt-image-edit")
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["paths"][0], str(self.pic))        # reference first
        self.assertIn("the tube is in her left hand", seen[0]["prompt"])
        self.assertIn("NOTHING ELSE MOVED", seen[0]["prompt"])
        self.assertEqual(len(r["delivered"]), 1)
        self.assertTrue(r["delivered"][0]["file"].endswith("p152-01--edit-v1.png"))
        self.assertEqual(r["delivered"][0]["delivered_at"], "9:16")
        self.assertEqual(E.dims(r["delivered"][0]["file"]), (1080, 1920))     # finished: taped down, strips painted
        self.assertEqual(E.dims(r["delivered"][0]["content"]), (4, 5))        # what both judges saw

    def test_a_region_puts_everything_outside_it_back_from_the_original(self):
        """Three live fixes were held on 2026-09-22 because the model redrew the
        product's own label text. A region makes "nothing else moved" a fact
        about the file: outside the rectangle, the original's pixels."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent")
        orig = Path(self.tmp) / "orig.png"
        Image.new("RGB", (100, 125), (0, 0, 255)).save(orig)          # 4:5, blue
        res = Path(self.tmp) / "res.png"
        Image.new("RGB", (100, 125), (255, 0, 0)).save(res)           # the model repainted everything
        note = E._restore_outside(orig, res, [10, 20, 50, 60])
        with Image.open(res) as im:
            self.assertEqual(im.getpixel((30, 50)), (255, 0, 0))      # inside: the model's answer
            self.assertEqual(im.getpixel((80, 100)), (0, 0, 255))     # outside: the original
            self.assertEqual(im.getpixel((5, 5)), (0, 0, 255))
        self.assertIn("the rest is the original", note)

    def test_a_masked_edit_says_what_goes_in_the_hole_not_what_to_keep(self):
        r = RE.resolve(self.req(change="the headline reads DAY 3", region="4,10,96,34"))
        self.assertIn("Paint the transparent area only", r["instruction"])
        self.assertIn("the headline reads DAY 3", r["instruction"])
        self.assertNotIn("Keep the reference image exactly as it is", r["instruction"])
        plain = RE.resolve(self.req(change="the headline reads DAY 3"))
        self.assertIn("Keep the reference image exactly as it is", plain["instruction"])

    def test_a_bad_region_is_refused_by_name(self):
        for bad in ("10,20,5,60", "10,20,50", "10,20,50,600"):
            with self.assertRaises(RE.BadRequest) as cm:
                RE.resolve(self.req(change="x is y", region=bad))
            self.assertIn("percentages", str(cm.exception))

    def test_a_region_travels_with_the_request_and_is_recorded(self):
        r = self.run_edit(change="the headline reads DAY 3", region="4,10,96,34", dry_run=True)
        self.assertEqual(r["region"], [4.0, 10.0, 96.0, 34.0])

    def test_every_fix_row_that_needs_a_region_says_what_it_covers(self):
        table, path = RE.fixes()
        self.assertTrue(path.name.startswith("fixes-v3"), path.name)
        for wanted in ("logo", "text", "product", "layout", "remove"):
            self.assertIn("region_hint", table[wanted], wanted)

    def test_the_original_is_never_written_to(self):
        before = self.pic.read_bytes()
        self.run_edit(change="the tube is in her left hand")
        self.assertEqual(self.pic.read_bytes(), before)

    def test_a_result_that_moved_something_else_is_held_with_its_reason(self):
        r = self.run_edit(change="the tube is in her left hand", compare=("PASS", "FAIL"))
        self.assertEqual(r["state"], "held")
        self.assertEqual(r["delivered"], [])
        why = list((self.out / "rejected").glob("*-why.md"))
        self.assertEqual(len(why), 1)
        self.assertIn("NOTHING ELSE MOVED", why[0].read_text())

    def test_the_compare_judge_not_running_is_a_hold_not_a_pass(self):
        def broken(prompt, paths, entry):
            raise RuntimeError("no key")
        r = RE.edit(self.req(change="x is y"), transport=stub_transport(self.calls),
                    judge_caller=judge_saying("PASS"), compare_caller=broken,
                    mirror=False, library=StubLibrary())
        self.assertEqual(r["state"], "held")
        self.assertIn("did not run", r["rejected"][0]["fails"][0])

    def test_the_logo_fix_attaches_the_brands_logo(self):
        r = self.run_edit(fix="logo", dry_run=True)
        refs = r["engine_request"]["references"]
        self.assertEqual(len(refs), 1)
        self.assertTrue(refs[0].endswith("acme-logo.png"))

    def test_a_logo_fix_with_no_logo_on_file_is_refused_by_name(self):
        (self.root / "brands" / "acme" / "identity" / "acme-logo.png").unlink()
        r = self.run_edit(fix="logo", dry_run=True)
        self.assertEqual(r["state"], "refused")
        self.assertIn("no logo file", r["refused"])

    def test_the_product_fix_attaches_the_declared_product_photo(self):
        r = self.run_edit(fix="product", product="widget", dry_run=True)
        self.assertTrue(any(x.endswith("packshot.png") for x in r["engine_request"]["references"]))

    def test_versions_count_up_and_never_overwrite(self):
        a = self.run_edit(change="the tube is in her left hand")
        b = self.run_edit(change="the tube is in her left hand")
        self.assertEqual((a["version"], b["version"]), (1, 2))
        self.assertNotEqual(a["delivered"][0]["file"], b["delivered"][0]["file"])
        self.assertTrue(Path(a["delivered"][0]["file"]).is_file())


# ------------------------------------------------------------ the variations

class TestVary(Base):
    def run_vary(self, variations, compare=("PASS", "PASS", "PASS"), **kw):
        req = {"brand": "acme", "baseline": str(self.pic), "variations": variations,
               "out": str(self.out)}
        req.update(kw)
        return RE.vary(req, transport=stub_transport(self.calls), judge_caller=judge_saying("PASS"),
                       compare_caller=compare_saying(list(compare)), mirror=False,
                       library=StubLibrary())

    def test_each_variation_is_one_edit_judged_against_the_baseline(self):
        s = self.run_vary([{"id": "headline", "args": {"headline": "Stop the itch"}},
                           {"id": "person", "args": {"who": "a woman in her fifties"}}])
        self.assertEqual(s["delivered"], 2)
        self.assertEqual({v["id"] for v in s["variations"]}, {"headline", "person"})
        rec = json.loads((self.out / "headline" / "edit.json").read_text())
        self.assertIn('reads "Stop the itch"', rec["asked"])
        self.assertEqual(rec["picture"], str(self.pic))

    def test_a_variation_missing_its_slot_is_refused_by_name(self):
        with self.assertRaises(RE.BadRequest) as cm:
            self.run_vary(["headline"])
        self.assertIn("headline", str(cm.exception))

    def test_a_product_swap_needs_the_product_named(self):
        with self.assertRaises(RE.BadRequest) as cm:
            self.run_vary([{"id": "product", "args": {"product_name": "Widget"}}])
        self.assertIn("name `product`", str(cm.exception))

    def test_a_product_swap_attaches_the_product_photo(self):
        s = self.run_vary([{"id": "product", "args": {"product_name": "Widget"}}],
                          product="widget", dry_run=True)
        rec = json.loads((self.out / "product" / "edit.json").read_text())
        self.assertTrue(any(x.endswith("packshot.png") for x in rec["engine_request"]["references"]))

    def test_the_set_record_counts_what_happened(self):
        s = self.run_vary([{"id": "headline", "args": {"headline": "A"}}], compare=("PASS", "FAIL"))
        self.assertEqual((s["delivered"], s["rejected"]), (0, 1))
        self.assertTrue((self.out / "variations.json").is_file())

    def test_a_set_files_a_run_json_the_index_can_read(self):
        """The index looks at run-label depth and never descends.

        A set files its edits one level down, under the row that made them, so
        without a run.json at the top the whole set reads as a run that never
        happened — which is exactly how image-edit showed up as fifteen
        runs with no record (2026-09-23).
        """
        self.run_vary([{"id": "headline", "args": {"headline": "A"}}])
        rec = json.loads((self.out / "run.json").read_text())
        self.assertEqual(rec["machine"], "image-edit")
        self.assertEqual(rec["brand"], "acme")
        self.assertEqual(rec["state"], "filed")
        # the set's own record is untouched; four readers still open it by name
        self.assertTrue((self.out / "variations.json").is_file())


# ---------------------------------------------------------------- sequences

class TestSequence(Base):
    def brief_with_deltas(self):
        b = Path(self.tmp) / "06-brief.md"
        b.write_text("""# The brief

prose here

```json
{"elements": []}
```

```json
[{"slide": 2, "change": "the hand turns palm-up; the words change to Day 3", "keep": ["the tube"], "type": []},
 {"slide": 3, "change": "she looks down at the tube", "keep": [], "type": []}]
```
""")
        return b

    def test_the_deltas_are_read_out_of_the_briefs_own_block(self):
        rows = E.deltas_from(self.brief_with_deltas())
        self.assertEqual([r["slide"] for r in rows], [2, 3])

    def test_a_brief_with_no_deltas_block_is_refused_by_name(self):
        b = Path(self.tmp) / "06-brief.md"; b.write_text("# brief\n\n```json\n{\"elements\": []}\n```\n")
        with self.assertRaises(RE.BadRequest) as cm:
            E.deltas_from(b)
        self.assertIn("slide-deltas", str(cm.exception))

    def test_slide_one_is_the_plate_not_a_delta(self):
        j = Path(self.tmp) / "d.json"; j.write_text(json.dumps([{"slide": 1, "change": "x"}]))
        with self.assertRaises(RE.BadRequest):
            E.deltas_from(j)

    def test_every_slide_is_one_edit_off_slide_one_judged_for_the_thread(self):
        seen = []
        s = RE.sequence({"brand": "acme", "slide_one": str(self.pic), "deltas": str(self.brief_with_deltas()),
                         "out": str(self.out)},
                        transport=stub_transport(self.calls), judge_caller=judge_saying("PASS"),
                        compare_caller=compare_saying(["PASS", "PASS", "PASS"], seen),
                        mirror=False, library=StubLibrary())
        self.assertEqual(s["delivered"], 2)
        self.assertEqual([x["slide"] for x in s["slides"]], [2, 3])
        self.assertTrue(all(p["paths"][0] == str(self.pic) for p in seen))       # slide one, every time
        self.assertIn("same sequence as IMAGE 1", seen[0]["prompt"])
        rec = json.loads((self.out / "slide-02" / "edit.json").read_text())
        self.assertEqual(rec["kind"], "slide")
        self.assertIn("the tube", rec["instruction"])
        self.assertTrue((self.out / "sequence.json").is_file())


# --------------------------------------------------------------- the walls

class TestWalls(unittest.TestCase):
    def test_no_brand_product_or_person_named_in_code_or_library(self):
        """Read off the real brands tree, the same way image-production tests it."""
        root = HERE.parent.parent
        names = set()
        for b in (root / "brands").iterdir():
            if b.is_dir() and not b.name.startswith((".", "_")):
                names.add(b.name.lower())
                pj = b / "products" / "images.json"
                if pj.is_file():
                    try:
                        names |= {k.lower() for k in json.loads(pj.read_text())["products"]}
                    except Exception:  # noqa: BLE001
                        pass
        texts = []
        for f in list((HERE / "image_edit").glob("*.py")) + list((HERE / "library").glob("*.json")) \
                + [HERE / "splits.json", HERE / "edit.py", HERE / "vary.py"]:
            texts.append((f.name, f.read_text().lower()))
        import re
        for name in names:
            if len(name) < 4:
                continue
            for fname, t in texts:
                self.assertIsNone(re.search(rf"\b{re.escape(name)}\b", t),
                                  f"{name} is named in {fname}")

    def test_the_team_pages_and_the_team_skills_name_no_brand(self):
        """Workspace rule 7. The page the team is given, and every skill they
        say out loud, read for ANY brand — the brand is what you name when you
        say the sentence (the owner, 2026-09-22)."""
        import json as _json
        root = HERE.parent.parent
        names = {b.name.lower() for b in (root / "brands").iterdir()
                 if b.is_dir() and not b.name.startswith((".", "_"))}
        names = {n for n in names if len(n) > 3}
        if not names:
            self.skipTest("no brands on this machine")
        files = [root / "the team notes/team-desk.html", root / "the team notes/TEAM-DESK.md",
                 root / "the team notes/team-desk/page.py"]
        files += [root / f".claude/skills/{n}/SKILL.md" for n in (
            "swipe-intake", "video-teardown", "teardown-image", "teardown-copy",
            "teardown-page", "teardown-email", "outlier-brief", "produce-image",
            "produce-video", "image-draft", "image-edit", "image-variation",
            "image-sequence", "edit-video", "frame-edit", "recut", "caption-look",
            "rename")]
        import re
        for f in files:
            if not f.is_file():
                continue
            t = f.read_text().lower()
            for n in names:
                self.assertIsNone(re.search(rf"\b{re.escape(n)}\b", t),
                                  f"{n} is named in {f.name}")

    def test_no_key_by_value_or_path(self):
        for f in (HERE / "image_edit").glob("*.py"):
            t = f.read_text()
            self.assertNotIn("keys.env", t)
            self.assertNotIn("sk-", t)


if __name__ == "__main__":
    unittest.main(verbosity=1)
