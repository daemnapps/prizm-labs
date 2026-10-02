"""image-edit — the discipline, the libraries, the job, the judge, the filing.

Every test builds a throwaway repo under `tempfile`, points AI_WORKSPACE at
it, stands in for Higgsfield with a local `maker`, and stubs the judge. No
network, no model, no key, nothing written outside `tempfile`.

    python3 tools/image-edit/tests/test_image_edit.py
"""
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
import image_edit as RE  # noqa: E402
from image_edit import discipline as D, engine as E, compare as CMP, paths as P  # noqa: E402


# ------------------------------------------------------------------ fixtures

def png_bytes(w=4, h=5):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def maker_into(folder, calls, finish=False):
    """Higgsfield, stood in for: writes a picture per roll and returns it.
    With `finish`, also a 9:16 file — what resize-9x16 hands back."""
    def make(job):
        calls.append(job)
        out = []
        for i in range(job["count"]):
            c = Path(folder) / f"made-{len(calls)}-{i}.png"
            c.write_bytes(png_bytes(4, 5))
            if finish:
                f = Path(folder) / f"made-{len(calls)}-{i}-9x16.png"
                f.write_bytes(png_bytes(9, 16))
                out.append({"content": str(c), "file": str(f)})
            else:
                out.append(str(c))
        return out
    return make


def compare_saying(verdicts, seen=None):
    def caller(prompt, paths, entry):
        if seen is not None:
            seen.append({"prompt": prompt, "paths": list(paths)})
        return json.dumps({"results": [{"test": i + 1, "verdict": v, "evidence": "stub"}
                                       for i, v in enumerate(verdicts)]})
    return caller


def fake_repo(tmp):
    root = Path(tmp)
    (root / "components").mkdir(parents=True, exist_ok=True)
    b = root / "brands" / "acme"
    (b / "brand-identity").mkdir(parents=True, exist_ok=True)
    (b / "products" / "widget" / "images").mkdir(parents=True, exist_ok=True)
    (b / "brand-identity" / "logo-white.png").write_bytes(png_bytes())
    (b / "products" / "images.json").write_text(json.dumps({"products": {
        "widget": {"cutout": "products/widget/images/packshot.png"}}}))
    (b / "products" / "widget" / "images" / "packshot.png").write_bytes(png_bytes())
    return root


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="image-edit-test-")
        self.root = fake_repo(self.tmp)
        self._old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.root)
        self.pic = Path(self.tmp) / "draft-01.png"
        self.pic.write_bytes(png_bytes(4, 5))
        self.out = Path(self.tmp) / "out"
        self.made = Path(self.tmp) / "made"
        self.made.mkdir()
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

    def run_edit(self, compare=("PASS", "PASS"), seen=None, finish=False, **kw):
        return RE.edit(self.req(**kw), maker=maker_into(self.made, self.calls, finish),
                       compare_caller=compare_saying(list(compare), seen))


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
        self.assertEqual(D.split_for("picture", {"keep": ["only this"]})["keep"], ["only this"])


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

    def test_the_brand_must_be_a_folder_and_the_real_ones_are_named(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(brand="nobody", change="x"))
        self.assertIn("acme", str(cm.exception))

    def test_the_reference_must_be_on_this_machine(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(picture="/nowhere/p.png", change="x"))
        self.assertIn("not a file on this machine", str(cm.exception))

    def test_a_fix_fills_its_slots_and_adds_its_checks(self):
        r = RE.resolve(self.req(fix="layout", args={"element": "the badge", "where": "top right"}))
        self.assertEqual(r["asked"], "move the badge to top right")
        self.assertTrue(any("the badge is now top right" in c for c in r["checks"]))
        self.assertIn("every other element exactly where it is", r["instruction"])

    def test_a_fix_missing_a_slot_is_refused_by_name(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(fix="layout", args={"element": "the badge"}))
        self.assertIn("where", str(cm.exception))

    def test_a_parked_fix_is_not_run(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(fix="text", args={"was": "SAALE", "now": "SALE"}))
        self.assertIn("parked", str(cm.exception))

    def test_an_unknown_fix_names_the_real_ones(self):
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve(self.req(fix="sharpen"))
        self.assertIn("logo", str(cm.exception))

    def test_words_ride_on_the_change_but_the_guard_reads_the_change(self):
        r = RE.resolve(self.req(change="the hand turns palm-up and the cup is lifted",
                                words=["WASH YOUR FACE", "find your method"]))
        self.assertIsNone(r["refused"])
        self.assertIn('the words change to "WASH YOUR FACE" / "find your method"', r["asked"])

    def test_the_frame_is_read_off_the_picture(self):
        self.assertEqual(E.dims(self.pic), (4, 5))
        self.assertEqual(E.nearest_aspect((4, 5)), "4:5")
        self.assertEqual(E.nearest_aspect((9, 16)), "9:16")
        self.assertEqual(E.frame_for(self.pic), ("4:5", "resize-9x16"))
        tall = Path(self.tmp) / "asset.png"; tall.write_bytes(png_bytes(9, 16))
        self.assertEqual(E.frame_for(tall), ("9:16", None))
        sq = Path(self.tmp) / "sq.png"; sq.write_bytes(png_bytes(4, 4))
        self.assertEqual(E.frame_for(sq), ("1:1", None))
        self.assertIsNone(E.deliver_frame(sq))

    def test_the_run_lands_under_runs_image_edit_brand_label(self):
        r = RE.resolve({"brand": "acme", "picture": str(self.pic), "change": "x"})
        self.assertTrue(r["out"].endswith("runs/image-edit/acme/draft-01--edit"))

    def test_a_bad_region_is_refused_by_name(self):
        for bad in ("10,20,5,60", "10,20,50", "10,20,50,600"):
            with self.assertRaises(RE.BadRequest) as cm:
                RE.resolve(self.req(change="x is y", region=bad))
            self.assertIn("percentages", str(cm.exception))


# ------------------------------------------------------------------ the job

class TestJob(Base):
    def test_a_refused_delta_writes_no_job_and_keeps_the_record(self):
        r = RE.edit(self.req(change="change the room, swap the jacket, move the shelves, add a lamp and turn her head"))
        self.assertEqual(r["state"], "refused")
        self.assertFalse((self.out / "job.json").exists())
        self.assertIn("changes at once", json.loads((self.out / "edit.json").read_text())["refused"])
        run = json.loads((self.out / "run.json").read_text())
        self.assertEqual((run["machine"], run["state"]), ("image-edit", "refused"))

    def test_a_dry_run_resolves_the_job_and_writes_none(self):
        r = RE.edit(self.req(change="the tube is in her left hand", dry_run=True))
        self.assertEqual(r["state"], "dry")
        self.assertFalse((self.out / "job.json").exists())
        self.assertEqual(r["job"]["references"][0], str(self.pic))
        self.assertTrue(r["job"]["prompt"].startswith("Keep the reference image exactly"))

    def test_an_edit_writes_one_job_for_higgsfield(self):
        r = RE.edit(self.req(change="the tube is in her left hand"))
        self.assertEqual(r["state"], "ready")
        job = json.loads((self.out / "job.json").read_text())["jobs"][0]
        self.assertEqual(job["model"], E.MODEL["model"])
        self.assertEqual(job["aspect_ratio"], "4:5")
        self.assertEqual(job["finish"], "resize-9x16")
        self.assertEqual(job["references"], [str(self.pic)])
        self.assertIn("NOTHING ELSE MOVED", job["judge_prompt"])
        self.assertIn("the tube is in her left hand", job["judge_prompt"])

    def test_the_editing_skills_and_the_engine_name_the_same_model(self):
        for s in ("logo-swap", "avatar-swap", "element-swap"):
            self.assertIn(f"`{E.MODEL['model']}`", (HERE / "skills" / f"{s}.md").read_text(), s)

    def test_the_logo_fix_attaches_the_brands_logo(self):
        r = RE.edit(self.req(fix="logo", dry_run=True))
        self.assertEqual(len(r["job"]["references"]), 2)
        self.assertTrue(r["job"]["references"][1].endswith("logo-white.png"))

    def test_a_logo_fix_with_no_logo_on_file_is_refused_by_name(self):
        (self.root / "brands" / "acme" / "brand-identity" / "logo-white.png").unlink()
        r = RE.edit(self.req(fix="logo", dry_run=True))
        self.assertEqual(r["state"], "refused")
        self.assertIn("no logo file", r["refused"])

    def test_the_product_fix_attaches_the_declared_product_photo(self):
        r = RE.edit(self.req(fix="product", product="widget", dry_run=True))
        self.assertTrue(r["job"]["references"][1].endswith("packshot.png"))


# ------------------------------------------------------------- the ingest

class TestIngest(Base):
    def test_an_edit_made_and_judged_is_filed_as_a_new_version(self):
        seen = []
        r = self.run_edit(change="the tube is in her left hand", seen=seen, finish=True)
        self.assertEqual(r["state"], "filed")
        self.assertEqual(seen[0]["paths"][0], str(self.pic))              # reference first
        self.assertIn("NOTHING ELSE MOVED", seen[0]["prompt"])
        d = r["delivered"][0]
        self.assertTrue(d["file"].endswith("draft-01--edit-v1.png"))
        self.assertEqual(d["delivered_at"], "9:16")
        self.assertEqual(E.dims(d["file"]), (9, 16))                       # the finished asset
        self.assertEqual(E.dims(d["content"]), (4, 5))                     # what the judge saw

    def test_an_unfinished_4x5_result_says_it_still_needs_the_finish(self):
        r = self.run_edit(change="the tube is in her left hand")
        self.assertIn("resize-9x16", r["delivered"][0]["note"])

    def test_the_session_can_bring_back_its_own_judgement(self):
        RE.edit(self.req(change="the tube is in her left hand"))
        made = self.made / "x.png"; made.write_bytes(png_bytes(4, 5))
        verdict = {"results": [{"test": 1, "verdict": "PASS", "evidence": "a"},
                               {"test": 2, "verdict": "FAIL", "evidence": "the headline moved"}]}
        s = RE.ingest(self.out, {"draft-01--edit": {"content": str(made), "judge": verdict}},
                      compare_caller=compare_saying(["PASS", "PASS"]))
        self.assertEqual(s["ingested"][0]["state"], "held")
        rec = json.loads((self.out / "edit.json").read_text())
        self.assertEqual(rec["rejected"][0]["judged_by"], "session")

    def test_results_for_a_job_nobody_prepared_are_refused(self):
        RE.edit(self.req(change="the tube is in her left hand"))
        with self.assertRaises(RE.BadRequest):
            RE.ingest(self.out, {"some-other": str(self.pic)})

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
        r = RE.edit(self.req(change="x is y"), maker=maker_into(self.made, self.calls),
                    compare_caller=broken)
        self.assertEqual(r["state"], "held")
        self.assertIn("did not run", r["rejected"][0]["fails"][0])

    def test_with_no_key_the_default_judge_holds(self):
        os.environ.pop("GEMINI_API_KEY", None)
        home = os.environ.get("HOME")
        os.environ["HOME"] = self.tmp                       # no ~/.gemini.env here
        try:
            v, fails, _t, _r = CMP.compare(self.pic, self.pic, "x is y")
        finally:
            os.environ["HOME"] = home
        self.assertEqual(v, "reject")
        self.assertIn("did not run", fails[0])

    def test_a_region_puts_everything_outside_it_back_from_the_original(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent")
        orig = Path(self.tmp) / "orig.png"
        Image.new("RGB", (100, 125), (0, 0, 255)).save(orig)
        res = Path(self.tmp) / "res.png"
        Image.new("RGB", (100, 125), (255, 0, 0)).save(res)
        note = E._restore_outside(orig, res, [10, 20, 50, 60])
        with Image.open(res) as im:
            self.assertEqual(im.getpixel((30, 50)), (255, 0, 0))      # inside: the model's answer
            self.assertEqual(im.getpixel((80, 100)), (0, 0, 255))     # outside: the original
        self.assertIn("the rest is the original", note)

    def test_versions_count_up_and_never_overwrite(self):
        a = self.run_edit(change="the tube is in her left hand")
        b = self.run_edit(change="the tube is in her left hand")
        self.assertEqual((a["version"], b["version"]), (1, 2))
        self.assertNotEqual(a["delivered"][0]["file"], b["delivered"][0]["file"])
        self.assertTrue(Path(a["delivered"][0]["file"]).is_file())


# ------------------------------------------------------------ the variations

class TestVary(Base):
    def run_vary(self, variations, compare=("PASS", "PASS", "PASS"), maker=True, **kw):
        req = {"brand": "acme", "baseline": str(self.pic), "variations": variations, "out": str(self.out)}
        req.update(kw)
        extra = {"maker": maker_into(self.made, self.calls)} if maker else {}
        return RE.vary(req, compare_caller=compare_saying(list(compare)), **extra)

    def test_each_variation_is_one_edit_judged_against_the_baseline(self):
        s = self.run_vary([{"id": "headline", "args": {"headline": "Your new headline"}},
                           {"id": "person", "args": {"who": "a woman in her fifties"}}])
        self.assertEqual(s["delivered"], 2)
        rec = json.loads((self.out / "headline" / "edit.json").read_text())
        self.assertIn('reads "Your new headline"', rec["asked"])
        self.assertEqual(rec["picture"], str(self.pic))

    def test_a_set_writes_one_jobs_file_and_ingests_back(self):
        s = self.run_vary([{"id": "headline", "args": {"headline": "A"}},
                           {"id": "colour", "args": {"from_colour": "teal", "to_colour": "gold"}}],
                          maker=False)
        self.assertEqual(s["ready"], 2)
        jobs = json.loads((self.out / "jobs.json").read_text())["jobs"]
        self.assertEqual(len(jobs), 2)
        made = self.made / "h.png"; made.write_bytes(png_bytes(4, 5))
        out = RE.ingest(self.out, {jobs[0]["slug"]: str(made)},
                        compare_caller=compare_saying(["PASS", "PASS", "PASS"]))
        self.assertEqual(out["waiting"], [jobs[1]["slug"]])
        summary = json.loads((self.out / "variations.json").read_text())
        self.assertEqual((summary["delivered"], summary["ready"]), (1, 1))
        self.assertEqual(json.loads((self.out / "run.json").read_text())["state"], "filed")

    def test_a_variation_missing_its_slot_is_refused_by_name(self):
        with self.assertRaises(RE.BadRequest) as cm:
            self.run_vary(["headline"])
        self.assertIn("headline", str(cm.exception))

    def test_a_product_swap_needs_the_product_named(self):
        with self.assertRaises(RE.BadRequest) as cm:
            self.run_vary([{"id": "product", "args": {"product_name": "Widget"}}])
        self.assertIn("name `product`", str(cm.exception))

    def test_a_product_swap_attaches_the_product_photo(self):
        self.run_vary([{"id": "product", "args": {"product_name": "Widget"}}], product="widget", dry_run=True)
        rec = json.loads((self.out / "product" / "edit.json").read_text())
        self.assertTrue(any(x.endswith("packshot.png") for x in rec["job"]["references"]))

    def test_the_set_record_counts_what_happened(self):
        s = self.run_vary([{"id": "headline", "args": {"headline": "A"}}], compare=("PASS", "FAIL"))
        self.assertEqual((s["delivered"], s["rejected"]), (0, 1))
        rec = json.loads((self.out / "run.json").read_text())
        self.assertEqual((rec["machine"], rec["state"]), ("image-edit", "held"))


# ---------------------------------------------------------------- sequences

class TestSequence(Base):
    def brief_with_deltas(self):
        b = Path(self.tmp) / "06-brief.md"
        b.write_text("""# The brief

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
        self.assertEqual([r["slide"] for r in E.deltas_from(self.brief_with_deltas())], [2, 3])

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
                        maker=maker_into(self.made, self.calls),
                        compare_caller=compare_saying(["PASS", "PASS", "PASS"], seen))
        self.assertEqual(s["delivered"], 2)
        self.assertTrue(all(p["paths"][0] == str(self.pic) for p in seen))
        self.assertIn("same sequence as IMAGE 1", seen[0]["prompt"])
        rec = json.loads((self.out / "slide-02" / "edit.json").read_text())
        self.assertEqual(rec["kind"], "slide")
        self.assertIn("the tube", rec["instruction"])


# --------------------------------------------------------------- the walls

class TestWalls(unittest.TestCase):
    def files(self):
        return [f for f in HERE.rglob("*") if f.is_file() and f.suffix in (".py", ".json", ".md")
                and "__pycache__" not in f.parts]

    def test_no_brand_or_product_from_the_brands_tree_is_named(self):
        root = P.repo()
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
        for f in self.files():
            t = f.read_text().lower()
            for name in (n for n in names if len(n) >= 4):
                self.assertIsNone(re.search(rf"\b{re.escape(name)}\b", t), f"{name} is named in {f.name}")

    def test_no_private_path_or_key(self):
        for f in self.files():
            if f.name == Path(__file__).name:
                continue
            t = f.read_text()
            for bad in ("/Users/", "ai-workspace", "lab/damon", "keys.env", "sk-", "Shared Assets"):
                self.assertNotIn(bad, t, f"{bad!r} in {f.name}")


if __name__ == "__main__":
    unittest.main(verbosity=1)
