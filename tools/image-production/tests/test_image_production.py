#!/usr/bin/env python3
"""image-production — the rollout's proofs. stdlib only, no network, no model.

    python3 tests/test_image_production.py

  1  the dry run calls nothing and writes nothing
  2  an unknown template / style pack / picture format is refused with the
     library's real ids; a name with no definition is refused as not defined
  3  two brands resolve two different sets of assets, and no brand is an error
  4  the repo-root record carries no picture
  5  a picture the judge fails is held from delivery, with the reason
  6  the words burned into the picture pass the copy gate or are held

Every test works in a temp folder: fake brands, a fake batch, a fake records
root. Nothing under the real `runs/`, `brands/` or Drive is touched.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
REPO = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
os.environ["AI_WORKSPACE"] = str(REPO)          # a worktree must not read the main checkout
sys.path.insert(0, str(TOOLS))

import paths as P          # noqa: E402
import gates as G          # noqa: E402
import brand_facts as BF   # noqa: E402
import dryrun              # noqa: E402
import render              # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32            # bytes with a picture's name; nothing opens it
UID_A = "aaaaaaaa-0000-4000-8000-000000000001"
UID_B = "bbbbbbbb-0000-4000-8000-000000000002"


def boom(*a, **k):
    raise AssertionError(f"the dry run started something: {a[:1]}")


def make_brand(root, name, product, uid, fact, price):
    b = root / name
    (b / "identity").mkdir(parents=True)
    (b / "identity/palette.md").write_text(f"# {name}\n\nink #112233\n")
    (b / "identity/logo-white.png").write_bytes(PNG)
    (b / "offers").mkdir()
    (b / "offers/offer-bank.md").write_text(f"## main — The main offer\n\nOne for {price}.\n")
    img = b / "products" / product / "images"
    img.mkdir(parents=True)
    (img / "packshot-cutout.png").write_bytes(PNG)
    (b / "products/images.json").write_text(json.dumps({"products": {product: {
        "cutout": f"products/{product}/images/packshot-cutout.png"}}}))
    (b / "element-facts.json").write_text(json.dumps({"elements": {uid: {
        "name": f"{name}-product", "kind": "product", "canonical": True,
        "facts": [fact], "forbids": []}}}))
    return b


def make_batch(root, brand, ads, offer=None, name="t-260920a"):
    run = root / "runs" / brand / name
    (run / "prompts").mkdir(parents=True)
    spec = {"brand": brand, "product": "thing", "batch": name, "avatar": "someone",
            "problem": "aproblem", "ratio": "9x16",
            "offer": offer or {"id": "main", "bar_text": "One for $49."}, "ads": ads}
    (run / "batch.json").write_text(json.dumps(spec, indent=1))
    for ad in ads:
        (run / "prompts" / f"{ad['slug']}.txt").write_text(f"<<<{UID_A}>>> the product on a table. 4:5.")
    return run, spec


def tree(*roots):
    out = {}
    for r in roots:
        for f in sorted(Path(r).rglob("*")):
            if f.is_file():
                out[str(f)] = f.read_bytes()
    return out


class Sandbox(unittest.TestCase):
    """Two fake brands and a fake records root, swapped in for the real ones."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="image-production-test-"))
        self.brands = self.tmp / "brands"
        make_brand(self.brands, "brand-a", "thing", UID_A, "It is a red cube.", "$49")
        make_brand(self.brands, "brand-b", "thing", UID_B, "It is a blue ball.", "$19")
        self.records = self.tmp / "records"
        self.patches = [mock.patch.object(P, "BRANDS", self.brands),
                        mock.patch.object(P, "RECORDS", self.records)]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def quiet(self, fn, *a, **k):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            r = fn(*a, **k)
        return r, out.getvalue()


class DryRun(Sandbox):
    def test_dry_run_spends_nothing_and_writes_nothing(self):
        run, _ = make_batch(self.tmp, "brand-a", [
            {"slug": "01-a", "concept": "c", "format": "f", "template": "prompted",
             "copy": {"headline": "A line.", "subhead": "Now $49.00"}}])
        before = tree(self.tmp)
        import plates
        with mock.patch.object(subprocess, "run", boom), \
                mock.patch.object(subprocess, "Popen", boom), \
                mock.patch.object(urllib.request, "urlopen", boom), \
                mock.patch.object(plates, "prepare", boom), \
                mock.patch.object(plates, "ingest", boom), \
                mock.patch.object(G, "_gate", boom), \
                mock.patch.object(G, "file_record", boom):
            rc, said = self.quiet(dryrun.main, [str(run)])
        self.assertEqual(rc, 0, said)
        self.assertIn("would be sent", said)
        self.assertIn(UID_A, said)                       # the prompt, as it would be sent
        self.assertEqual(before, tree(self.tmp), "the dry run wrote a file")
        self.assertFalse(self.records.exists(), "the dry run filed a record")
        self.assertFalse((run / "inbox").exists())
        self.assertFalse((run / "check.json").exists())

    def test_dry_run_exits_nonzero_when_something_required_is_missing(self):
        run, _ = make_batch(self.tmp, "brand-a", [
            {"slug": "01-a", "concept": "c", "format": "f", "template": "prompted"}])
        (run / "prompts/01-a.txt").unlink()
        rc, said = self.quiet(dryrun.main, [str(run)])
        self.assertEqual(rc, 1)
        self.assertIn("MISSING  prompt", said)

    def test_dry_run_reports_the_packshot_a_layout_template_needs(self):
        run, _ = make_batch(self.tmp, "brand-b", [
            {"slug": "01-a", "concept": "c", "format": "f", "template": "photo-strip",
             "product_slug": "thing"}], offer={"id": "main", "bar_text": "One for $19."})
        rc, said = self.quiet(dryrun.main, [str(run)])
        self.assertIn("brand-b/products/thing/images/packshot-cutout.png", said)
        self.assertNotIn("brand-a", said)

    def test_the_entry_script_takes_the_flag(self):
        text = (HERE.parent / "machine.py").read_text()
        self.assertIn('"--dry-run"', text)
        self.assertIn("import dryrun", text)


class Elements(Sandbox):
    def ads(self, **k):
        return {"ads": [dict({"slug": "01-a"}, **k)]}

    def test_unknown_template_is_refused_with_the_real_ids(self):
        picked, problems = G.picked_in_batch(self.ads(template="not-a-template"))
        self.assertEqual(len(problems), 1)
        for real in ("confession", "full-photo", "pedestal", "photo-strip"):
            self.assertIn(real, problems[0])

    def test_unknown_style_pack_is_refused_with_the_real_ids(self):
        _, problems = G.picked_in_batch(self.ads(template="prompted", pack="not-a-pack"))
        self.assertEqual(len(problems), 1)
        for real in ("candid-ugc", "studio-object", "flat-vector"):
            self.assertIn(real, problems[0])

    def test_picture_format_is_asked_of_the_format_bank_list(self):
        bank = json.loads(P.FORMAT_BANK.read_text())["formats"]
        real = bank[0]["key"]
        picked, problems = G.picked_in_batch(self.ads(template="prompted", picture_format=real))
        self.assertEqual((picked["format"], problems), ([real], []))
        _, problems = G.picked_in_batch(self.ads(template="prompted", picture_format="not-a-format"))
        self.assertIn(real, problems[0])

    def test_a_name_with_no_definition_is_refused(self):
        rows = G.library().rows("format", "image")
        todo = next((r["id"] for r in rows if str(r.get("what") or "").startswith("[TO DEFINE")), None)
        if not todo:
            self.skipTest("the library holds no [TO DEFINE row today")
        _, problems = G.picked_in_batch(self.ads(template="prompted", picture_format=todo))
        self.assertEqual(len(problems), 1)
        self.assertIn("named but not defined yet", problems[0])

    def test_real_ids_pass_and_the_name_field_is_not_mistaken_for_a_picture_format(self):
        picked, problems = G.picked_in_batch(self.ads(
            template="templates/confession.json", pack="candid-ugc", format="productvoid"))
        self.assertEqual(problems, [])
        self.assertEqual(picked, {"template": ["confession"], "style": ["candid-ugc"], "format": []})

    def test_the_gate_holds_and_records_what_was_picked(self):
        run, spec = make_batch(self.tmp, "brand-a", [
            {"slug": "01-a", "concept": "c", "format": "f", "template": "nope", "pack": "candid-ugc"}])
        Held = G.quality().Held
        with self.assertRaises(Held):
            self.quiet(G.elements_gate, run, spec)
        rec = json.loads((run / "elements.json").read_text())
        self.assertEqual(rec["picked"]["style"], ["candid-ugc"])
        self.assertEqual(json.loads((run / "check.json").read_text())["elements"]["result"], "HELD")

    def test_a_brief_naming_an_unknown_template_is_refused(self):
        brief = self.tmp / "td/runs/swipe-1/out/06-brief.md"
        brief.parent.mkdir(parents=True)
        brief.write_text('# brief\n\n```json\n{"template": "nope", "content": {}}\n```\n')
        _, problems = G.picked_in_brief(brief)
        self.assertIn("photo-strip", problems[0])
        brief.write_text('# brief\n\n```json\n{"layout": {}, "elements": []}\n```\n')
        self.assertEqual(G.picked_in_brief(brief)[1], [])     # its own geometry: nothing named


class BrandThreading(Sandbox):
    def test_two_brands_resolve_two_packshots(self):
        a, b = P.product_cutout("brand-a", "thing"), P.product_cutout("brand-b", "thing")
        self.assertNotEqual(a, b)
        self.assertIn("brand-a", a.parts)
        self.assertIn("brand-b", b.parts)
        self.assertEqual(P.product_cutout("brand-b"), b)      # the only one on file

    def test_no_brand_is_an_error_not_a_default(self):
        for call in (lambda: P.product_cutout(),
                     lambda: P.need_brand(None, "x"),
                     lambda: P.need_brand("brand-z", "x"),
                     lambda: BF.product_checks(None)):
            with self.assertRaises(SystemExit):
                call()
        with mock.patch.object(render, "BRAND", None):
            with self.assertRaises(SystemExit):
                render.brand_dir()

    def test_the_renderer_reads_the_named_brands_logo_and_colours(self):
        with mock.patch.object(render, "BRAND", None), mock.patch.object(render, "BRAND_NAME", None):
            render.use_brand("brand-a")
            a = render.brand_dir()
            render.use_brand("brand-b")
            b = render.brand_dir()
            self.assertEqual((a.name, b.name), ("brand-a", "brand-b"))
            self.assertTrue((b / "identity/logo-white.png").is_file())
            self.assertEqual(render.brand_colors(b), {"#112233"})
            notes = []
            render.safe_color("#ff0088", set(), "#000000", "headline", notes)
            self.assertIn("brand-b", notes[0])

    def test_the_renderer_finds_the_brand_teardown_recorded(self):
        brief = self.tmp / "td/runs/swipe-1/out/06-brief.md"
        brief.parent.mkdir(parents=True)
        brief.write_text("x")
        self.assertIsNone(render.brand_for_brief(brief))
        (brief.parent.parent / "vars").mkdir()
        (brief.parent.parent / "vars/brand_name.md").write_text("Brand-B\n")
        self.assertEqual(render.brand_for_brief(brief), "brand-b")
        self.assertEqual(render.brand_for_brief(brief, "brand-a"), "brand-a")

    def test_the_judges_product_tests_come_from_the_brand(self):
        a, _ = BF.product_checks("brand-a")
        b, _ = BF.product_checks("brand-b")
        self.assertIn("red cube", a[0])
        self.assertIn("blue ball", b[0])
        self.assertNotIn("red cube", b[0])
        named, _ = BF.product_checks("brand-a", f"<<<{UID_A}>>> on a table")
        self.assertIn("red cube", named[0])
        (self.brands / "brand-b/element-facts.json").write_text('{"elements": {}}')
        plain, note = BF.product_checks("brand-b")
        self.assertEqual(plain, [BF.PLAIN_PRODUCT_CHECK])
        self.assertIn("no product facts", note)

    def test_no_brand_is_spelled_in_the_shipped_code(self):
        """Asked of the board's own reader, so this and the board cannot disagree."""
        board = REPO / "system-blueprint/greenlight.py"
        if not board.is_file():
            self.skipTest("the green-light board is not in this checkout")
        import importlib.util
        spec = importlib.util.spec_from_file_location("greenlight", board)
        gl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gl)
        code = gl.files(HERE.parent, [".", "tools"], "*.py")
        hits, _ = gl.brand_hits(code, [])
        self.assertEqual(hits, [])


class Filing(Sandbox):
    def test_the_record_carries_no_picture(self):
        run, _ = make_batch(self.tmp, "brand-a", [
            {"slug": "01-a", "concept": "c", "format": "f", "template": "prompted"}])
        (run / "inbox").mkdir()
        (run / "inbox/01-a.png").write_bytes(PNG)
        (run / "inbox/jobs.json").write_text("{}")
        unit = run / "ads/01-a"
        unit.mkdir(parents=True)
        (unit / "a-name-a01.png").write_bytes(PNG)
        (unit / "manifest.json").write_text('{"ad_name": "a-name"}')
        (run / "rejected").mkdir()
        (run / "rejected/02-b.png").write_bytes(PNG)
        (run / "rejected/02-b-why.md").write_text("# why\n")
        (run / "prompts/sneaky.png").write_bytes(PNG)
        (run / "verdicts.json").write_text("{}")
        (run / "report.md").write_text("# report\n")
        self.quiet(G.media_gate, run, [("02-b", ["garbled text"])])
        dst, _ = self.quiet(G.file_record, run)
        self.assertEqual(dst, self.records / "brand-a" / run.name)
        filed = sorted(str(f.relative_to(dst)) for f in dst.rglob("*") if f.is_file())
        self.assertEqual([f for f in filed if Path(f).suffix.lower() in G.PICTURES], [])
        self.assertTrue(all(Path(f).suffix in G.TEXT for f in filed), filed)
        for want in ("batch.json", "check.json", "verdicts.json", "report.md", "jobs.json", "run.json",
                     "prompts-as-sent/01-a.txt", "manifests/01-a.json", "rejected/02-b-why.md"):
            self.assertIn(want, filed)
        meta = json.loads((dst / "run.json").read_text())
        self.assertEqual((meta["machine"], meta["brand"], meta["state"]),
                         ("image-production", "brand-a", "held"))

    def test_a_filing_failure_is_a_skip_not_a_stop(self):
        _, said = self.quiet(G.file_quietly, G.file_record, self.tmp / "no-such-run")
        self.assertIn("SKIP", said)


class MediaGate(Sandbox):
    def test_a_failed_verdict_is_held_with_its_reason(self):
        run, _ = make_batch(self.tmp, "brand-a", [{"slug": "01-a", "concept": "c", "format": "f"}])
        clean, _ = self.quiet(G.media_gate, run, [("01-a", ["The offer bar is cut off"])])
        self.assertFalse(clean)
        st = json.loads((run / "check.json").read_text())["media"]
        self.assertEqual(st["result"], "HELD")
        self.assertIn("01-a", st["problems"][0])
        self.assertIn("The offer bar is cut off", st["problems"][0])
        self.assertIn("media", G.held(run))
        clean, _ = self.quiet(G.media_gate, run, [])
        self.assertTrue(clean)
        self.assertEqual(json.loads((run / "check.json").read_text())["media"]["result"], "pass")

    def test_finish_holds_the_failed_picture_and_ships_the_other(self):
        """The whole finisher with the judge stubbed: the verdict logic is its
        own; what is proved is that a fail is recorded as HELD and never delivered."""
        try:
            import finish
        except Exception as e:                       # noqa: BLE001 — naming / imaging library not importable here
            self.skipTest(f"finish.py could not be imported: {e}")
        run, _ = make_batch(self.tmp, "brand-a", [
            {"slug": "01-good", "concept": "c", "format": "f"},
            {"slug": "02-bad", "concept": "c", "format": "f"}])
        (run / "inbox").mkdir()
        for s in ("01-good", "02-bad"):
            (run / "inbox" / f"{s}.png").write_bytes(PNG)
        asked = []

        def seen(img, tests, model=None):
            asked.append(tests)
            return (["The text is READABLE — garbled"], "raw") if "02-bad" in str(img) else ([], "raw")

        delivered = []
        with mock.patch.object(finish, "seen", seen), \
                mock.patch.object(finish, "measured", lambda *a, **k: []), \
                mock.patch.object(finish, "price_pass", lambda *a, **k: []), \
                mock.patch.object(finish.PAD, "pad", lambda *a, **k: None), \
                mock.patch.object(finish.D, "deliver", lambda unit, *a, **k: delivered.append(Path(unit).name)), \
                mock.patch.object(finish, "R", mock.MagicMock()), \
                mock.patch.object(subprocess, "run", boom):
            (passed, killed), _ = self.quiet(finish.finish, run)
        self.assertEqual(passed, ["01-good"])
        self.assertEqual(delivered, ["01-good"])
        self.assertFalse((run / "ads/02-bad").exists())
        media = json.loads((run / "check.json").read_text())["media"]
        self.assertEqual(media["result"], "HELD")
        self.assertIn("02-bad", media["problems"][0])
        self.assertIn("garbled", media["problems"][0])
        verdicts = json.loads((run / "verdicts.json").read_text())
        self.assertEqual((verdicts["01-good"]["verdict"], verdicts["02-bad"]["verdict"]), ("pass", "reject"))
        self.assertTrue(any("red cube" in t for t in asked[0]), "the product test is brand-a's own")
        dst = self.records / "brand-a" / run.name
        self.assertTrue((dst / "check.json").is_file())
        self.assertEqual([f for f in dst.rglob("*") if f.suffix.lower() in G.PICTURES], [])


class CopyGate(Sandbox):
    def spec(self, **copy):
        return {"brand": "brand-a", "offer": {"id": "main", "bar_text": "One for $49."},
                "ads": [{"slug": "01-a", "copy": copy}]}

    def bank(self):
        return (self.brands / "brand-a/offers/offer-bank.md").read_text()

    def test_a_price_the_bank_sells_passes_in_either_spelling(self):
        self.assertEqual(G.copy_problems(self.spec(headline="Now $49.00"), self.bank()), [])

    def test_a_price_the_bank_does_not_sell_is_held(self):
        p = G.copy_problems(self.spec(headline="Now $59"), self.bank())
        self.assertEqual(len(p), 1)
        self.assertIn("$59.00", p[0])
        self.assertIn("01-a · headline", p[0])

    def test_an_unfilled_note_is_held(self):
        p = G.copy_problems(self.spec(subhead="[UNFILLED: the claim]"), self.bank())
        self.assertIn("UNFILLED", p[0])

    def test_no_offer_key_falls_back_to_the_whole_bank(self):
        s = self.spec(headline="Now $49")
        s["offer"] = {"id": "a-key-the-bank-does-not-use", "bar_text": "One for $49."}
        self.assertEqual(G.copy_problems(s, self.bank()), [])

    def test_the_gate_writes_check_json_and_holds(self):
        run, spec = make_batch(self.tmp, "brand-a", [
            {"slug": "01-a", "concept": "c", "format": "f", "copy": {"headline": "Now $1"}}])
        with self.assertRaises(G.quality().Held):
            self.quiet(G.copy_gate, run, spec)
        self.assertEqual(json.loads((run / "check.json").read_text())["copy"]["result"], "HELD")
        _, said = self.quiet(G.copy_gate, run, spec, "warn")      # warn: recorded, carries on
        self.assertIn("HELD", said)


if __name__ == "__main__":
    unittest.main(verbosity=2)
