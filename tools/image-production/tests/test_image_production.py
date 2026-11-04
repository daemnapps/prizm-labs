#!/usr/bin/env python3
"""Tests for the image-production component.

    python3 tools/image-production/tests/test_image_production.py

Stdlib `unittest`. **No network, no model, no real key, and nothing written
outside a temporary directory.** Every test builds its own throwaway workspace
under `tempfile`, points `AI_WORKSPACE` at it, and passes a stub provider and
a stub judge — so a test never reaches `runs/`, `brands/`, a real endpoint or
the Drive mount (`mirror=False` everywhere, and the mount is never touched).
"""
import base64
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
import image_production as IP                      # noqa: E402


# ---------------------------------------------------------------- the stubs

class StubLibrary:
    """Stands in for components/elements/machine/elements.py."""

    class Unknown(KeyError):
        pass

    def __init__(self, rows=None):
        self.rows = rows or {
            ("style", "image"): {"candid-ugc": {"id": "candid-ugc", "name": "Candid UGC",
                                                "what": "a photograph a real person took"}},
            ("format", "image"): {"ugcselfie": {"id": "ugcselfie", "name": "UGC selfie",
                                                "what": "a selfie shape"}},
            ("template", "image"): {"pedestal": {"id": "pedestal", "name": "Pedestal",
                                                 "what": "product on a pedestal"},
                                    "reserved": {"id": "reserved", "name": "Reserved",
                                                 "what": "[TO DEFINE] nothing yet"}},
        }

    def get(self, element, asset, id_):
        book = self.rows.get((element, asset), {})
        if id_ not in book:
            raise self.Unknown(f"`{id_}` is not a {element} for {asset} — "
                               f"known: {', '.join(book) or 'none yet'}")
        return book[id_]


def png_bytes(w=2, h=3):
    """A real PNG of a given size, written with the stdlib — so the measured
    check has a true frame to read and the tests still import nothing."""
    import struct
    import zlib
    raw = b"".join(b"\x00" + b"\x7f\x7f\x7f" * w for _ in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


ONE_PIXEL_PNG = png_bytes(1, 1)


def stub_transport(calls, size=(3, 2)):
    """Answers like whichever door the url names, and records every call.
    It never opens a socket. `size` is the frame the made picture comes back
    at, so the measured check has something true to read."""
    blob = base64.b64encode(png_bytes(*size)).decode()

    def t(method, url, headers, body):
        calls.append({"method": method, "url": url, "headers": headers,
                      "len": len(body or b"")})
        if "googleapis" in url:
            return 200, {}, json.dumps({"candidates": [{"content": {"parts": [
                {"inline_data": {"mime_type": "image/png", "data": blob}}]}}],
                "usageMetadata": {"totalTokenCount": 1}}).encode()
        return 200, {"x-request-id": "req_stub"}, json.dumps(
            {"data": [{"b64_json": blob}], "usage": {"total_tokens": 1}}).encode()
    return t


def judge_saying(verdicts):
    """A stub judge. `verdicts` is a list of PASS/FAIL, one per call. It
    answers every test the prompt numbered — test 1 carries the call's
    verdict, the rest PASS — because an unanswered test is a reject now."""
    import re
    seq = list(verdicts)

    def caller(prompt, img_path, entry):
        v = seq.pop(0) if seq else "PASS"
        nums = sorted({int(m) for m in re.findall(r"(?m)^(\d+)\. ", prompt)}) or [1]
        return json.dumps({"results": [
            {"test": i, "verdict": v if i == 1 else "PASS", "evidence": "stub"}
            for i in nums]})
    return caller


# ------------------------------------------------------------ the workspace

def fake_workspace(tmp):
    """A throwaway workspace holding exactly the brand files this component
    reads. Nothing real is touched."""
    root = Path(tmp)
    (root / "components").mkdir(parents=True, exist_ok=True)
    b = root / "brands" / "acme"
    (b / "identity").mkdir(parents=True, exist_ok=True)
    (b / "products" / "widget" / "images").mkdir(parents=True, exist_ok=True)
    (b / "identity" / "palette.md").write_text("| Ink | `#112233` |\n| Gold | `#AABBCC` |\n")
    (b / "identity" / "fonts.md").write_text("A font.\n")
    (b / "identity" / "acme-logo.png").write_bytes(ONE_PIXEL_PNG)
    (b / "products" / "images.json").write_text(json.dumps({"products": {
        "widget": {"title": "The Widget",
                   "cutout": "products/widget/images/packshot.png"}}}))
    (b / "products" / "widget" / "images" / "packshot.png").write_bytes(ONE_PIXEL_PNG)
    (b / "ai-elements").mkdir(parents=True, exist_ok=True)
    (b / "ai-elements" / "element-facts.json").write_text(json.dumps({"elements": {
        "11111111-1111-1111-1111-111111111111": {
            "name": "acme-widget", "kind": "product", "canonical": True,
            "facts": ["a squat blue tube"], "forbids": ["have a pump"]}}}))
    (root / "brands" / "other").mkdir(parents=True, exist_ok=True)
    return root


def _legacy_table(path=None, house=True):
    """The OpenAI-door route table as it was before the Higgsfield switch (tests/route-openai-fixture.json), so the engine
    tests can drive the OpenAI transport stub. The real table is tested in TestRoute and TestHiggsfieldDoor."""
    import copy
    if path is not None:
        return _REAL_TABLE(path, house)
    return copy.deepcopy(json.loads((Path(__file__).resolve().parent / "route-openai-fixture.json").read_text()))


_REAL_TABLE = IP.route.table


class Base(unittest.TestCase):
    legacy_table = True

    def setUp(self):
        from unittest import mock
        if self.legacy_table:
            p = mock.patch.object(IP.route, "table", _legacy_table)
            p.start()
            self.addCleanup(p.stop)
        self.tmp = tempfile.mkdtemp(prefix="imgprod-test-")
        self.root = fake_workspace(self.tmp)
        self._old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.root)
        self.out = Path(self.tmp) / "out"
        self.lib = StubLibrary()

    def tearDown(self):
        if self._old is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def req(self, **kw):
        base = {"brand": "acme", "purpose": "email-hero",
                "direction": "a man holding the widget in a kitchen",
                "out": str(self.out), "people": False}
        base.update(kw)
        return base


# ----------------------------------------------------------------- the shape

class TestRequestShape(Base):
    def test_a_field_nobody_declared_is_refused(self):
        with self.assertRaises(IP.BadRequest) as e:
            IP.resolve(self.req(colour="blue"), library=self.lib)
        self.assertIn("colour", str(e.exception))

    def test_missing_required_fields_are_named(self):
        with self.assertRaises(IP.BadRequest) as e:
            IP.resolve({"brand": "acme", "purpose": "ad"}, library=self.lib)
        self.assertIn("direction", str(e.exception))
        self.assertIn("out", str(e.exception))

    def test_unknown_purpose_names_the_real_ones(self):
        with self.assertRaises(IP.BadRequest) as e:
            IP.resolve(self.req(purpose="billboard"), library=self.lib)
        self.assertIn("email-hero", str(e.exception))

    def test_brand_is_never_a_default(self):
        with self.assertRaises(SystemExit) as e:
            IP.resolve(self.req(brand="nope"), library=self.lib)
        self.assertIn("no brand folder", str(e.exception))

    def test_the_purpose_supplies_the_frame_when_the_request_does_not(self):
        req, _ctx, _p, _pp, _m, _e, _w = IP.resolve(self.req(), library=self.lib)
        self.assertEqual(req["_aspect"], "3:2")
        req, *_ = IP.resolve(self.req(aspect="1:1"), library=self.lib)
        self.assertEqual(req["_aspect"], "1:1")


# --------------------------------------------------------------- the context

class TestContext(Base):
    def test_brand_facts_come_from_the_brand(self):
        _r, ctx, *_ = IP.resolve(self.req(product="widget"), library=self.lib)
        self.assertEqual(ctx["product"]["title"], "The Widget")
        self.assertIn("squat blue tube", ctx["product"]["facts"])
        self.assertIn("#112233", ctx["palette"])
        self.assertTrue(ctx["logo"])
        self.assertTrue(ctx["product"]["photo_on_machine"])

    def test_a_brand_with_no_facts_gets_the_plain_test(self):
        (self.root / "brands" / "other" / "identity").mkdir(parents=True, exist_ok=True)
        _r, ctx, *_ = IP.resolve(self.req(brand="other"), library=self.lib)
        self.assertIn("one coherent, recognisable product", ctx["product"]["judge_tests"][0])

    def test_the_real_product_photo_is_attached_as_a_reference(self):
        _r, ctx, *_ = IP.resolve(self.req(purpose="email-offer", product="widget"),
                                 library=self.lib)
        self.assertEqual(len(ctx["references"]), 1)
        self.assertTrue(ctx["references"][0].endswith("packshot.png"))

    def test_a_remote_url_is_not_a_reference(self):
        """A url is a declaration the model never sees — nothing here
        downloads. A purpose made FROM the real photograph refuses it."""
        b = self.root / "brands" / "acme"
        (b / "products" / "images.json").write_text(json.dumps({"products": {
            "widget": {"title": "The Widget", "cutout": "https://cdn.example/widget.png"}}}))
        _r, ctx, *_ = IP.resolve(self.req(purpose="email-offer", product="widget"),
                                 library=self.lib)
        self.assertEqual(ctx["references"], [])
        fatal = [m for m in ctx["missing"] if m["fatal"]]
        self.assertTrue(fatal)
        self.assertIn("nothing here downloads one", fatal[0]["detail"])

    def test_the_same_url_is_only_a_note_when_the_photo_is_optional(self):
        b = self.root / "brands" / "acme"
        (b / "products" / "images.json").write_text(json.dumps({"products": {
            "widget": {"title": "The Widget", "cutout": "https://cdn.example/widget.png"}}}))
        _r, ctx, *_ = IP.resolve(self.req(product="widget"), library=self.lib)
        self.assertEqual([m for m in ctx["missing"] if m["fatal"]], [])

    def test_a_product_the_brand_does_not_declare_is_fatal(self):
        _r, ctx, *_ = IP.resolve(self.req(product="ghost"), library=self.lib)
        self.assertTrue(any(m["fatal"] and m["what"] == "product" for m in ctx["missing"]))


# --------------------------------------------------------------- the prompt

class TestPrompt(Base):
    def test_the_same_skeleton_whatever_the_purpose(self):
        _r, _c, hero, path_a, *_ = IP.resolve(self.req(), library=self.lib)
        _r, _c, ad, path_b, *_ = IP.resolve(self.req(purpose="ad"), library=self.lib)
        self.assertEqual(path_a, path_b)
        for text in (hero, ad):
            self.assertIn("a man holding the widget in a kitchen", text)
            self.assertIn("NO INVENTED TEXT", text)
            self.assertIn("THE PRODUCT IS OURS OR IT IS ABSENT", text)
            # the provenance table above the `---` is documentation and is
            # never sent — a prompt should not be naming our own file paths
            self.assertNotIn("simple_email.py", text)

    def test_a_fresh_9x16_asset_is_made_at_9x16_with_the_safe_zone_in_the_prompt(self):
        """the owner, 2026-10-26, reversing 2026-09-22: made 9:16 from the start, the zone asked of the model and
        measured by the judge; nothing is outpainted. (An EDIT still keeps its picture's frame, below.)"""
        from image_production import judge
        req, ctx, ad, *_ = IP.resolve(self.req(purpose="ad"), library=self.lib)
        self.assertEqual((req["_gen_aspect"], req["_aspect"]), ("9:16", "9:16"))
        self.assertIn("COMPOSITION FOR CROPPING", ad)
        self.assertNotIn("CONTENT of a", ad)
        self.assertIn(judge.SAFE_ZONE, judge.tests_for(req, ctx))
        req, ctx, hero, *_ = IP.resolve(self.req(), library=self.lib)
                # a safe-zone purpose asked for another frame is still made at 9:16
        req, ctx, sq, *_ = IP.resolve(self.req(purpose="ad", aspect="3:4"), library=self.lib)
        self.assertEqual((req["_gen_aspect"], req["_aspect"]), ("9:16", "9:16"))

    def test_a_wordless_purpose_says_so_and_an_ad_does_not(self):
        _r, _c, hero, *_ = IP.resolve(self.req(), library=self.lib)
        _r, _c, ad, *_ = IP.resolve(self.req(purpose="ad"), library=self.lib)
        self.assertIn("No words, letters, numbers or logos", hero)
        self.assertNotIn("No words, letters, numbers or logos anywhere in the picture.", ad)

    def test_an_edit_carries_the_keep_everything_clause(self):
        src = Path(self.tmp) / "approved.png"
        src.write_bytes(ONE_PIXEL_PNG)
        _r, _c, text, *_ = IP.resolve(self.req(from_image=str(src)), library=self.lib)
        self.assertIn("Change ONLY what the direction above asks for", text)

    def test_an_edit_keeps_the_references_composition_and_takes_no_assets(self):
        """Found live 2026-09-22: a headline swap grew hands. Two causes, both
        here — the cropping clause told the model to compose a scene, and the
        brand's matched packshots rode along as references."""
        src = Path(self.tmp) / "approved.png"
        src.write_bytes(ONE_PIXEL_PNG)
        req, ctx, text, *_ = IP.resolve(self.req(purpose="ad", from_image=str(src), aspect="3:4"),
                                        library=self.lib)
        self.assertNotIn("COMPOSITION FOR CROPPING", text)
        self.assertIn("The frame is 9:16", text)
        self.assertEqual(ctx["references"], [str(src)])
        # an edit leaving at 9:16 is asked for at 9:16 like any other picture
        req, ctx, text, *_ = IP.resolve(self.req(purpose="ad", from_image=str(src)), library=self.lib)
        self.assertEqual((req["_gen_aspect"], req["_aspect"]), ("9:16", "9:16"))

    def test_assets_is_a_declared_field(self):
        IP.resolve(self.req(assets=False), library=self.lib)

    def test_the_element_row_lands_in_the_prompt(self):
        _r, _c, text, *_ = IP.resolve(self.req(style="candid-ugc"), library=self.lib)
        self.assertIn("a photograph a real person took", text)


# ---------------------------------------------------------------- the route

class TestRoute(Base):
    legacy_table = False
    def test_an_edit_routes_to_the_edit_model(self):
        src = Path(self.tmp) / "a.png"
        src.write_bytes(ONE_PIXEL_PNG)
        *_x, model, _e, _w = IP.resolve(self.req(from_image=str(src)), library=self.lib)
        self.assertEqual(model, "gpt-image-edit")

    def test_a_person_in_frame_goes_to_gpt(self):
        *_x, model, _e, why = IP.resolve(self.req(people=True), library=self.lib)
        self.assertEqual(model, "gpt-image-person")

    def test_everything_else_goes_to_gpt_too_one_door(self):
        """Every picture goes to GPT Image 2.5 first, through one door; the other models are the ladder's later rungs, never
        a route of their own."""
        *_x, model, _e, why = IP.resolve(self.req(people=False), library=self.lib)
        self.assertEqual(model, "gpt-image-person")
        self.assertIn("one door", why)
        table = IP.route.table()
        routed = {r["model"] for r in table["route"]}
        self.assertNotIn("seedream-higgsfield", routed)
        self.assertNotIn("nano-banana-higgsfield", routed)
        self.assertNotIn("gpt-image-openai-net", routed)

    def test_a_forced_model_wins_and_still_has_to_be_declared(self):
        *_x, model, _e, why = IP.resolve(self.req(model="seedream-higgsfield"), library=self.lib)
        self.assertEqual(model, "seedream-higgsfield")
        self.assertIn("named by the caller", why)
        with self.assertRaises(SystemExit) as e:
            IP.resolve(self.req(model="midjourney"), library=self.lib)
        self.assertIn("not a model in this component's route table", str(e.exception))

    def test_every_route_model_names_a_key(self):
        t = IP.route.table()
        for name, entry in t["models"].items():
            if entry.get("provider") == "higgsfield":       # the command line signs in through a browser: no key exists
                self.assertTrue(entry.get("credential"), f"{name} declares no credential")
                self.assertNotIn("key", entry)
                continue
            self.assertTrue(entry.get("key"), f"{name} declares no key")
        self.assertTrue(t["judge"].get("key"))

    def test_no_key_value_is_written_into_the_table(self):
        raw = (IP.paths.home() / "models.json").read_text()
        self.assertNotIn("sk-", raw)
        self.assertNotIn("AIza", raw)


# ---------------------------------------------------------------- the gates

class TestGates(Base):
    def test_an_unknown_element_id_is_refused_naming_the_real_ids(self):
        _r, ctx, *_ = IP.resolve(self.req(style="made-up"), library=self.lib)
        self.assertTrue(ctx["elements"]["problems"])
        self.assertIn("candid-ugc", ctx["elements"]["problems"][0])

    def test_a_reserved_name_with_no_definition_is_refused(self):
        _r, ctx, *_ = IP.resolve(self.req(template="reserved"), library=self.lib)
        self.assertIn("named but not defined yet", ctx["elements"]["problems"][0])

    def test_an_undeclared_person_is_a_note_now_not_a_hold(self):
        """It used to be refused because the model route split on it. One door
        (the owner, 2026-09-22) means it no longer does — it only decides whether
        the brand's cast rides along, so it is said rather than held."""
        req = self.req()
        req.pop("people")
        notes = []
        problems = IP.gates.input_problems(
            *IP.resolve(req, library=self.lib)[:2], IP.purposes(), IP.route.aspects(), notes)
        self.assertEqual(problems, [])
        self.assertTrue(any("the brand's cast is not attached" in n for n in notes), notes)
        req["people"] = True
        notes = []
        problems = IP.gates.input_problems(
            *IP.resolve(req, library=self.lib)[:2], IP.purposes(), IP.route.aspects(), notes)
        self.assertEqual((problems, notes), ([], []))

    def test_a_purpose_that_has_decided_needs_no_declaration(self):
        req = self.req(purpose="product-shot", product="widget")
        req.pop("people")
        problems = IP.gates.input_problems(
            *IP.resolve(req, library=self.lib)[:2], IP.purposes(), IP.route.aspects())
        self.assertEqual(problems, [])

    def test_a_missing_direction_holds_at_inputs(self):
        req = self.req()
        req["direction"] = ""
        with self.assertRaises(IP.BadRequest):
            IP.resolve(req, library=self.lib)

    def test_gates_write_a_gate_keyed_check_json(self):
        calls = []
        IP.make(self.req(), library=self.lib, transport=stub_transport(calls),
                judge_caller=judge_saying(["PASS"]), mirror=False)
        check = json.loads((self.out / "check.json").read_text())
        self.assertEqual(set(check), {"inputs", "elements", "media"})
        self.assertEqual(check["inputs"]["result"], "pass")
        self.assertEqual(check["media"]["result"], "pass")

    def test_an_element_problem_holds_the_run_before_anything_is_made(self):
        calls = []
        with self.assertRaises(Exception) as e:
            IP.make(self.req(style="made-up"), library=self.lib,
                    transport=stub_transport(calls), judge_caller=judge_saying(["PASS"]),
                    mirror=False)
        self.assertIn("HELD", str(e.exception))
        self.assertEqual(calls, [], "a held run must not have called a model")


# ---------------------------------------------------------------- the judge

class TestJudge(Base):
    def test_a_picture_that_fails_its_judge_still_goes_forward_flagged_below_criteria(self):
        """Outputs are scored and never hold a flow (2026-10-26): the best attempt is delivered, flagged, with the failed
        checks in plain words; nothing is HELD."""
        calls = []
        r = IP.make(self.req(count=2, people=True), library=self.lib,
                    transport=stub_transport(calls),
                    judge_caller=judge_saying(["FAIL", "PASS"]), mirror=False)
        self.assertEqual(len(r["delivered"]), 2)
        self.assertEqual(r["held"], [])
        self.assertEqual(len(r["below_criteria"]), 1)
        bad, good = r["pictures"]
        self.assertTrue(bad["below_criteria"] and bad["verdict"] == "below_criteria")
        self.assertFalse(good["below_criteria"])
        note = next(self.out.glob("*-below-criteria.md")).read_text()
        self.assertIn("did not pass these checks", note)
        self.assertFalse((self.out / "rejected").exists())
        check = json.loads((self.out / "check.json").read_text())
        self.assertNotEqual(check.get("media", {}).get("result"), "HELD")

    def test_a_judge_that_did_not_run_scores_the_picture_zero_and_it_goes_forward_flagged(self):
        def broken(prompt, img, entry):
            raise RuntimeError("no key")
        r = IP.make(self.req(people=True), library=self.lib,
                    transport=stub_transport([]), judge_caller=broken, mirror=False)
        self.assertEqual(len(r["delivered"]), 1)
        self.assertTrue(r["pictures"][0]["below_criteria"])
        self.assertIn("judge did not run", r["pictures"][0]["fails"][0])

    def test_the_best_scoring_attempt_goes_forward_on_a_tie_the_later_one(self):
        """The ladder's slots are attempts (3 at most, a failed call counts): each judged and scored, the best chosen."""
        table = json.loads(json.dumps(IP.route.table()))          # the House-resolved rows
        table["ladder"] = {"generate": [{"name": "gpt", "model": "gpt-image-person", "retry": True},
                                         {"name": "backup", "model": "gpt-image-edit"}]}
        table["gate"] = {"max_attempts": {"pictures": 3}}
        calls = []
        # three attempts, the judge fails the first two (test 1 only) and the third too: all score the same, the LATER wins
        r = IP.make(self.req(people=True), library=self.lib, table=table, transport=stub_transport(calls),
                    judge_caller=judge_saying(["FAIL", "FAIL", "FAIL"]), mirror=False)
        row = r["pictures"][0]
        self.assertEqual(len(row["attempts"]), 3)
        self.assertEqual(row["chosen_attempt"], 3)
        self.assertTrue(row["below_criteria"])
        self.assertEqual(len(calls), 3)

    def test_a_passing_attempt_stops_the_ladder(self):
        table = json.loads(json.dumps(IP.route.table()))          # the House-resolved rows
        table["ladder"] = {"generate": [{"name": "gpt", "model": "gpt-image-person", "retry": True},
                                         {"name": "backup", "model": "gpt-image-edit"}]}
        calls = []
        r = IP.make(self.req(people=True), library=self.lib, table=table, transport=stub_transport(calls),
                    judge_caller=judge_saying(["FAIL", "PASS"]), mirror=False)
        row = r["pictures"][0]
        self.assertEqual((row["chosen_attempt"], row["below_criteria"], len(calls)), (2, False, 2))
        self.assertEqual([a["outcome"] for a in row["attempts"]], ["below_criteria", "pass"])

    def test_the_product_test_is_the_brands_own_words(self):
        _r, ctx, *_ = IP.resolve(self.req(product="widget"), library=self.lib)
        req, ctx2, *_ = IP.resolve(self.req(product="widget"), library=self.lib)
        tests = IP.judge.tests_for(req, ctx2)
        self.assertTrue(any("squat blue tube" in t for t in tests))
        self.assertTrue(any("never: " in t or "never does" in t for t in tests))

    def test_the_direction_match_test_quotes_the_direction(self):
        req, ctx, *_ = IP.resolve(self.req(), library=self.lib)
        tests = IP.judge.tests_for(req, ctx)
        self.assertTrue(any("a man holding the widget in a kitchen" in t for t in tests))

    def test_measured_catches_the_wrong_frame_without_a_model(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("no imaging library on this machine")
        p = Path(self.tmp) / "wide.png"
        Image.new("RGB", (160, 90)).save(p)
        self.assertTrue(IP.judge.measured(p, "9:16"))
        self.assertFalse(IP.judge.measured(p, "16:9"))


# -------------------------------------------------------------- the dry run

class TestConform(Base):
    def test_a_frame_the_vendor_cannot_make_is_cropped_back_to_the_request(self):
        """OpenAI answers 4:5 with 1024x1536 (2:3). The extra canvas is the
        vendor's; the crop takes it back so the measured check passes."""
        from image_production import providers
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent")
        p = Path(self.tmp) / "tall.png"
        Image.new("RGB", (1024, 1536), "white").save(p)
        note = providers.conform(p, {"w": 4, "h": 5})
        self.assertEqual(note, "1024x1536 -> 1024x1280")
        with Image.open(p) as im:
            self.assertEqual(im.size, (1024, 1280))
        self.assertIsNone(providers.conform(p, {"w": 4, "h": 5}))


class TestFinish(Base):
    """The 9:16 frame: made at 9:16 from the start, nothing painted."""

    def setUp(self):
        super().setUp()
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent")
        self.content = Path(self.tmp) / "content.png"
        Image.new("RGB", (400, 500), (0, 0, 255)).save(self.content)     # 4:5, solid blue

    def test_every_declared_size_is_the_exact_ratio_and_divides_by_16(self):
        """The 9:16 row used to say 1024x1536, which is 2:3 — a 9:16 request
        came back 2:3 and the side-crop clipped a headline on a live run."""
        t = IP.route.table()
        for mid in ("gpt-image-person", "gpt-image-edit"):
            for ratio, size in t["models"][mid]["sizes"].items():
                w, h = (int(x) for x in size.split("x"))
                aw, ah = (int(x) for x in ratio.split(":"))
                self.assertEqual((w % 16, h % 16), (0, 0), f"{mid} {ratio}={size}")
                self.assertAlmostEqual(h / w, ah / aw, places=3, msg=f"{mid} {ratio}={size}")

    def test_a_752x1344_native_frame_is_delivered_at_1080x1920(self):
        """Higgsfield's 9:16 at 1k is 752x1344 (0.5% off true 9:16): no crop, no paint, sized to the delivery frame."""
        from PIL import Image
        calls = []
        r = IP.make(self.req(purpose="ad"), library=self.lib, transport=stub_transport(calls, size=(752, 1344)),
                    judge_caller=judge_saying(["PASS"]), mirror=False)
        row = r["pictures"][0]
        self.assertEqual(row["verdict"], "pass", row["fails"])
        self.assertIsNone(row["conformed"])
        with Image.open(row["file"]) as im:
            self.assertEqual(im.size, (1080, 1920))

    def test_make_delivers_a_native_9x16(self):
        from PIL import Image
        calls = []
        r = IP.make(self.req(purpose="ad"), library=self.lib, transport=stub_transport(calls, size=(9, 16)),
                    judge_caller=judge_saying(["PASS"]), mirror=False)
        row = r["pictures"][0]
        self.assertEqual(row["verdict"], "pass", row["fails"])
        self.assertEqual((row["generated_at"], row["delivered_at"]), ("9:16", "9:16"))
        self.assertNotIn("finish", row)
        with Image.open(row["file"]) as im:
            self.assertEqual(im.size, (1080, 1920))       # made 9:16, delivered at 1080x1920


class TestHiggsfieldDoor(unittest.TestCase):
    """The Higgsfield command-line picture door (2026-10-26): checks the command line is installed and signed in, builds
    the argument list (no shell), runs it with --wait --json, downloads result_url."""

    ROW = {"provider": "higgsfield", "vendor_model": "gpt_image_2_5", "must_name": ["variant", "quality", "resolution"],
           "params": {"variant": "sunburst", "quality": "high", "resolution": "2k"}}

    def stub(self, calls, signed_in=True, installed=True, status="completed"):
        class HF:
            def which(s): return "/x/higgsfield" if installed else None
            def run(s, argv, timeout=900):
                calls.append(argv)
                if argv[1] == "account":
                    return (0, json.dumps({"credits": 100}), "") if signed_in else (1, "", "not signed in")
                return 0, json.dumps([{"id": "j1", "status": status, "result_url": "https://x/o.png", "params": {"width": 1504}}]), ""
            def fetch(s, url, dest): Path(dest).write_bytes(b"png")
        return HF()

    def test_the_command_is_a_list_with_variant_quality_resolution_aspect_and_repeated_references(self):
        import tempfile
        from image_production import providers
        calls, d = [], Path(tempfile.mkdtemp())
        r = providers.generate(self.ROW, "a prompt", [d / "a.png", d / "b.png"], d / "o.png", "9:16", transport=self.stub(calls))
        self.assertEqual(r["provider"], "higgsfield")
        argv = calls[-1]
        self.assertEqual(argv[:4], ["/x/higgsfield", "generate", "create", "gpt_image_2_5"])
        flat = " ".join(argv)
        for want in ("--aspect_ratio 9:16", "--variant sunburst", "--quality high", "--resolution 2k", "--wait", "--json"):
            self.assertIn(want, flat)
        self.assertEqual(argv.count("--image-references"), 2)
        self.assertTrue((d / "o.png").is_file())

    def test_not_installed_or_not_signed_in_is_refused_by_name_in_one_plain_line(self):
        import tempfile
        from image_production import providers
        d = Path(tempfile.mkdtemp())
        for kw in ({"installed": False}, {"signed_in": False}):
            with self.assertRaises(providers.ProviderError) as cm:
                providers.generate(self.ROW, "p", [], d / "o.png", "9:16", transport=self.stub([], **kw))
            self.assertIn("Higgsfield is not set up on this machine", str(cm.exception))
            self.assertIn("nothing was sent", str(cm.exception).lower().replace("nothing was sent and", "nothing was sent and"))

    def test_a_row_that_does_not_name_quality_and_resolution_is_refused(self):
        import tempfile
        from image_production import providers
        d = Path(tempfile.mkdtemp())
        with self.assertRaises(providers.ProviderError):
            providers.generate({**self.ROW, "params": {"quality": "high"}}, "p", [], d / "o.png", "9:16", transport=self.stub([]))

    def test_a_job_that_did_not_complete_raises_and_writes_nothing(self):
        import tempfile
        from image_production import providers
        d = Path(tempfile.mkdtemp())
        with self.assertRaises(providers.ProviderError):
            providers.generate(self.ROW, "p", [], d / "o.png", "9:16", transport=self.stub([], status="failed"))
        self.assertFalse((d / "o.png").exists())

    def test_the_cost_quote_asks_and_spends_nothing(self):
        from image_production import providers
        calls = []
        class HF:
            def which(s): return "/x/higgsfield"
            def run(s, argv, timeout=900):
                calls.append(argv)
                return 0, json.dumps({"credits": 2.75} if argv[1] == "generate" else {"credits": 9}), ""
            def fetch(s, u, d): raise AssertionError("a quote must not download")
        self.assertEqual(providers.higgsfield_cost(self.ROW, "p", ["/x/a.png"], "9:16", hf=HF()), 2.75)
        self.assertEqual(calls[-1][:4], ["/x/higgsfield", "generate", "cost", "gpt_image_2_5"])
        self.assertNotIn("--image-references", calls[-1])

    def test_every_real_higgsfield_row_names_everything_its_defaults_would_get_wrong(self):
        t = _REAL_TABLE()
        hf = {k: v for k, v in t["models"].items() if v.get("provider") == "higgsfield"}
        self.assertEqual(sorted(hf), ["gpt-image-edit", "gpt-image-person", "nano-banana-higgsfield", "seedream-higgsfield"])
        for k, row in hf.items():
            for need in row["must_name"]:
                self.assertIn(need, row["params"], (k, need))
            self.assertTrue(row.get("credential"))
            self.assertNotIn("key", row)
        self.assertEqual(sorted(hf["gpt-image-person"]["must_name"]), ["quality", "resolution", "variant"])
        self.assertEqual((hf["gpt-image-person"]["params"]["variant"], hf["gpt-image-person"]["params"]["quality"]), ("sunburst", "high"))

    def test_the_real_route_goes_to_higgsfield_first_and_openai_is_only_the_last_rung(self):
        t = _REAL_TABLE()
        self.assertEqual(t["models"]["gpt-image-person"]["provider"], "higgsfield")
        for kind in ("generate", "edit"):
            names = [r["model"] for r in t["ladder"][kind]]
            self.assertEqual(names[-1], "gpt-image-openai-net")
            self.assertEqual(t["models"][names[-1]]["provider"], "openai")
            self.assertEqual([t["models"][n]["vendor_model"] for n in names[:-1]], ["gpt_image_2_5", "seedream_v5_pro", "nano_banana_pro"])
            self.assertTrue(t["ladder"][kind][0]["retry"])
        self.assertEqual(t["models"]["seedream-higgsfield"]["max_images"], 10)
        self.assertEqual(t["models"]["nano-banana-higgsfield"]["max_images"], 14)

    def test_a_region_edit_on_a_door_with_no_mask_is_a_plain_edit_with_the_original_pasted_back(self):
        import tempfile
        from PIL import Image
        from image_production import providers
        d = Path(tempfile.mkdtemp())
        src = d / "src.png"
        Image.new("RGB", (360, 640), (0, 0, 255)).save(src)
        sent = []
        class HF:
            def which(s): return "/x/higgsfield"
            def run(s, argv, timeout=900):
                if argv[1] == "account": return 0, json.dumps({"credits": 5}), ""
                sent.append(argv)
                return 0, json.dumps([{"id": "j", "status": "completed", "result_url": "u", "params": {}}]), ""
            def fetch(s, url, dest): Image.new("RGB", (752, 1344), (255, 0, 0)).save(dest, "PNG")
        r = providers.edit_in_region(self.__class__.ROW, "change the headline", src, (10, 20, 50, 60), d / "o.png", transport=HF())
        self.assertEqual(r["region_px"], (36, 128, 180, 384))
        self.assertIsNone(r["mask"])
        self.assertIn("Change ONLY the area", sent[0][sent[0].index("--prompt") + 1])
        self.assertNotIn("--mask", sent[0])
        with Image.open(d / "o.png") as im:
            self.assertEqual(im.size, (360, 640))
            self.assertEqual(im.getpixel((100, 200)), (255, 0, 0))     # the model's answer inside the rectangle
            self.assertEqual(im.getpixel((330, 600)), (0, 0, 255))     # the original everywhere else


class TestRecipeGate(Base):
    """Every variable filled, or not applicable with a reason, before any door (2026-10-26). The sheet's dials, stays,
    feeling and techniques reach the model in their own sections; the filled sheet is recorded beside the picture."""

    def fake(self, calls):
        def gen(entry, prompt, refs, out, aspect, transport=None, key=None):
            calls.append(prompt); Path(out).write_bytes(b"png")
            return {"file": str(out), "model": "m", "provider": "x", "request_id": "r", "usage": None}
        return gen

    FULL = {"stays": "the kitchen and the counter", "emotion": "surprise", "dials": {"absurdity": "high"},
            "techniques": ["rhyme with the swipe"], "cast": {"na": "no person in this picture"}}

    def make(self, recipe, calls, **kw):
        from unittest import mock
        from image_production import plain
        out = Path(self.tmp) / "p.png"
        with mock.patch.object(plain.PR, "generate", self.fake(calls)), mock.patch.object(plain, "_key", lambda e: "k"):
            return plain.make("acme", "A tube on a counter.", out, recipe=recipe, **kw), out

    def test_every_filled_variable_has_its_own_section_and_na_ones_are_left_out(self):
        calls = []
        rec, out = self.make(self.FULL, calls)
        p = calls[0]
        for head, body in (("WHAT STAYS", "the kitchen"), ("THE FEELING", "surprise"), ("THE DIALS", "absurdity: high"),
                           ("TECHNIQUES", "rhyme with the swipe")):
            self.assertIn(head + "\n" + body, p)
        self.assertNotIn("CAST", p)
        self.assertNotIn("no person in this picture", p)

    def test_a_blank_or_an_na_without_a_reason_is_refused_by_name_before_any_call(self):
        from image_production import plain
        calls = []
        for bad in ({"emotion": ""}, {"dials": {"na": " "}}, {"stays": None}):
            with self.assertRaises(plain.RecipeRefused) as cm:
                self.make(bad, calls)
            self.assertIn("refuses this picture", str(cm.exception))
            self.assertIn("Nothing was sent", str(cm.exception))
        self.assertEqual(calls, [])

    def test_the_record_beside_the_picture_replays_it(self):
        calls = []
        rec, out = self.make(self.FULL, calls, people_lines=["The woman is 44."], rules_lines=["No second product."])
        r = json.loads(out.with_suffix(".recipe.json").read_text())
        self.assertEqual(r["recipe"], self.FULL)
        self.assertEqual(r["not_applicable"], {"cast": "no person in this picture"})
        self.assertEqual(r["request"]["people_lines"], ["The woman is 44."])
        self.assertEqual(r["prompt"], calls[0])
        self.assertIn("No second product.", r["prompt"].split("RULES")[1])
        self.assertIn("The woman is 44.", r["prompt"].split("THE PEOPLE")[1].split("THE FRAME")[0])

    def test_a_variable_sheet_recipe_is_validated_by_the_sheets_own_validator(self):
        from image_production import plain
        calls = []
        recipe = {"brief": {}, "sheet": {"brand": {"state": "filled", "value": "acme", "source": "the brief"},
                                         "offer": {"state": "not_applicable", "reason": "no offer on this ad"}}}
        with self.assertRaises(plain.RecipeRefused) as cm:
            self.make(recipe, calls)
        self.assertIn("missing", str(cm.exception))                    # the other variables are still blank
        self.assertEqual(calls, [])
        self.assertEqual(plain.na_of(recipe), {"offer": "no offer on this ad"})

    def test_a_below_criteria_base_is_allowed_and_its_flag_travels_onto_what_is_made_from_it(self):
        from image_production import approval
        calls = []
        base = Path(self.tmp) / "base.png"
        base.write_bytes(b"png")
        base.with_suffix(".recipe.json").write_text(json.dumps({"recipe": {"emotion": "x"}}))
        approval.write(base, gate_passed=True, judge="below_criteria", below_criteria=True, failed_checks=["the label is wrong"])
        rec, out = self.make({"emotion": "surprise"}, calls, references=[base])
        r = json.loads(out.with_suffix(".recipe.json").read_text())
        self.assertTrue(r["carries_below_criteria"])
        self.assertEqual(r["below_criteria_inputs"], [str(base)])

    def test_with_the_gate_on_a_picture_without_a_recipe_is_refused(self):
        from unittest import mock
        from image_production import plain, route
        real = route.table
        with mock.patch.object(route, "table", lambda path=None, house=True: {**real(path, house), "gate": {"recipe_required": True}}):
            with self.assertRaises(plain.RecipeRefused) as cm:
                self.make(None, [])
            self.assertIn("carries no recipe", str(cm.exception))

    def test_generate_takes_the_previews_send_and_returns_the_rung_and_attempts(self):
        from unittest import mock
        from image_production import plain
        calls = []
        send = {"brand": "acme", "text": "A tube on a counter.", "references": [], "products": [], "ref_roles": [], "people": None}
        out = Path(self.tmp) / "g.png"
        with mock.patch.object(plain.PR, "generate", self.fake(calls)), mock.patch.object(plain, "_key", lambda e: "k"):
            r = plain.generate(send, out, recipe={"emotion": "surprise"})
        self.assertEqual(set(r), {"file", "rung", "attempts", "below_criteria", "prompt", "checks"})
        self.assertTrue(out.is_file() and r["below_criteria"] == [])
        self.assertTrue(out.with_suffix(".recipe.json").is_file())

    def test_the_engine_takes_a_recipe_refuses_a_blank_and_records_the_sheet(self):
        with self.assertRaises(IP.BadRequest) as cm:
            IP.make(self.req(recipe={"emotion": ""}), library=self.lib, transport=stub_transport([], size=(9, 16)),
                    judge_caller=judge_saying(["PASS"]), mirror=False)
        self.assertIn("refuses this picture", str(cm.exception))
        r = IP.make(self.req(purpose="ad", recipe={"emotion": "surprise", "cast": {"na": "none"}}), library=self.lib,
                    transport=stub_transport([], size=(9, 16)), judge_caller=judge_saying(["PASS"]), mirror=False)
        rec = json.loads(Path(r["pictures"][0]["file"]).with_suffix(".recipe.json").read_text())
        self.assertEqual(rec["not_applicable"], {"cast": "none"})
        self.assertEqual(rec["recipe"]["emotion"], "surprise")


class TestApprovedBasesAndPairs(Base):
    """Slop is not passed forward: a picture of ours is a base only when approved. A scene's two frames come from one sheet."""

    def gate_on(self, **flags):
        from unittest import mock
        from image_production import route
        real = route.table
        return mock.patch.object(route, "table", lambda path=None, house=True: {**real(path, house), "gate": {"recipe_required": False, "approved_bases_required": True, **flags}})

    def made(self, name="a.png", recipe=True):
        p = Path(self.tmp) / name
        p.write_bytes(b"png")
        if recipe:
            p.with_suffix(".recipe.json").write_text(json.dumps({"recipe": {"emotion": "surprise"}}))
        return p

    def test_a_picture_of_ours_that_was_never_judged_is_refused_as_a_base_when_the_gate_is_on(self):
        from image_production import approval
        mine, swipe = self.made(), Path(self.tmp) / "swipe.jpg"
        swipe.write_bytes(b"jpg")
        approval.check_bases([mine])                                  # gate off: allowed
        with self.gate_on():
            approval.check_bases([swipe])                              # outside material has no record: allowed
            with self.assertRaises(approval.ApprovalRefused) as cm:
                approval.check_bases([mine, swipe])
            self.assertIn("a.png", str(cm.exception))
            self.assertIn("no record of being judged", str(cm.exception))
            approval.approve(mine, by="a person")
            approval.check_bases([mine])
            # a below-criteria picture was judged: it is allowed as a base and its flag is carried forward
            weak = self.made("weak.png")
            approval.write(weak, gate_passed=True, judge="below_criteria", below_criteria=True, failed_checks=["the label is wrong"])
            approval.check_bases([weak])
            self.assertTrue(approval.flag_of(weak))
            self.assertFalse(approval.flag_of(mine))

    def test_approval_needs_the_sheet_gate_and_the_judge(self):
        from image_production import approval
        p = self.made()
        self.assertTrue(approval.write(p, gate_passed=True, judge="pass")["approved"])
        self.assertTrue(approval.record_path(p).is_file())                  # <picture>.approved.json only for an approved picture
        self.assertFalse(approval.write(p, gate_passed=False, judge="pass")["approved"])
        self.assertFalse(approval.record_path(p).is_file())                 # never a false approval by file name
        self.assertTrue(approval.scored_path(p).is_file())
        self.assertFalse(approval.write(p, gate_passed=True, judge="below_criteria")["approved"])
        bare = self.made("b.png", recipe=False)
        with self.assertRaises(approval.ApprovalRefused):
            approval.approve(bare, by="owner")                        # not ours: no record to approve

    def test_the_engine_writes_the_approval_when_the_judge_passes_a_picture_that_carried_its_sheet(self):
        from image_production import approval
        r = IP.make(self.req(purpose="ad", recipe={"emotion": "surprise"}), library=self.lib,
                    transport=stub_transport([], size=(9, 16)), judge_caller=judge_saying(["PASS"]), mirror=False)
        self.assertTrue(approval.read(r["pictures"][0]["file"])["approved"])
        self.assertTrue(approval.record_path(r["pictures"][0]["file"]).is_file())
        r2 = IP.make(self.req(purpose="ad", label="norecipe"), library=self.lib,
                     transport=stub_transport([], size=(9, 16)), judge_caller=judge_saying(["PASS"]), mirror=False)
        self.assertFalse(approval.read(r2["pictures"][0]["file"])["approved"])    # no sheet: judge alone is not enough

    def test_the_engine_refuses_an_unapproved_edit_source_by_name(self):
        src = self.made("src.png")
        with self.gate_on():
            with self.assertRaises(IP.BadRequest) as cm:
                IP.make(self.req(purpose="ad", from_image=str(src)), library=self.lib,
                        transport=stub_transport([], size=(9, 16)), judge_caller=judge_saying(["PASS"]), mirror=False)
            self.assertIn("no record of being judged", str(cm.exception))

    def test_a_delta_that_touches_a_locked_variable_is_refused_before_anything_is_made(self):
        from image_production import pair
        sheet = {"scene": "a", "people_who": "a woman", "place_light": "kitchen, window light"}
        with self.assertRaises(pair.PairRefused):
            pair.make_frame_pair_sheet(sheet, {"people_who": "a man"})
        with self.assertRaises(pair.PairRefused):
            pair.make_frame_pair_sheet(sheet, {})
        self.assertEqual(pair.make_frame_pair_sheet(sheet, {"scene": "b"})["place_light"], "kitchen, window light")
        self.assertTrue(pair.validate_pair(sheet, {**sheet, "place_light": "night street"}))
        self.assertEqual(pair.validate_pair(sheet, {**sheet, "scene": "b"}), [])

    def test_a_pair_is_made_from_one_sheet_the_end_frame_takes_the_start_as_image_1_and_the_run_records_both(self):
        from unittest import mock
        from image_production import pair, plain
        sent = []
        def gen(entry, prompt, refs, out, aspect, transport=None, key=None):
            sent.append((prompt, [str(r) for r in refs])); Path(out).write_bytes(b"png")
            return {"file": str(out), "model": "m", "provider": "x", "request_id": "r", "usage": None}
        sheet = {"scene": "she holds the tube", "people_who": "a woman", "emotion": "surprise"}
        run = Path(self.tmp) / "run"
        with mock.patch.object(plain.PR, "generate", gen), mock.patch.object(plain, "_key", lambda e: "k"):
            out = pair.make_pair("acme", sheet, {"scene": "she smiles at the tube"}, ("first text", "last text"),
                                 Path(self.tmp) / "frames", "s1", run_dir=run)
        self.assertEqual(sent[1][1][0], str(Path(self.tmp) / "frames" / "s1-first.png"))
        self.assertIn("she smiles at the tube", sent[1][0])
        doc = json.loads((run / "frames.json").read_text())
        self.assertEqual(doc["s1"]["first"]["file"], str(Path(self.tmp) / "frames" / "s1-first.png"))
        self.assertEqual(doc["s1"]["delta"], {"scene": "she smiles at the tube"})
        self.assertEqual(json.loads((Path(self.tmp) / "frames" / "s1-last.recipe.json").read_text())["recipe"]["people_who"], "a woman")

    def test_with_the_gate_on_the_end_frame_takes_a_chosen_start_frame_and_refuses_one_never_chosen(self):
        from unittest import mock
        from image_production import approval, pair, plain
        def gen(entry, prompt, refs, out, aspect, transport=None, key=None):
            Path(out).write_bytes(b"png"); return {"file": str(out), "model": "m", "provider": "x", "request_id": "r", "usage": None}
        sheet = {"scene": "a", "people_who": "a woman"}
        with self.gate_on(), mock.patch.object(plain.PR, "generate", gen), mock.patch.object(plain, "_key", lambda e: "k"):
            out = pair.make_pair("acme", sheet, {"scene": "b"}, ("t1", "t2"), Path(self.tmp) / "f2", "s2")   # made here: chosen
            self.assertTrue(approval.read(Path(self.tmp) / "f2" / "s2-first.png")["chosen"])
            old = Path(self.tmp) / "old.png"                                   # a record from before records said `chosen`
            old.write_bytes(b"png"); old.with_suffix(".recipe.json").write_text(json.dumps({"recipe": {"x": 1}}))
            with self.assertRaises(approval.ApprovalRefused):
                plain.make("acme", "t", Path(self.tmp) / "x.png", references=[old], recipe={"emotion": "x"})


class TestTheGatesAreOnByDefault(Base):
    """The real route table has the recipe gate and the approved-bases gate ON (2026-10-26); the engine tests above run on
    the legacy fixture, so this class puts the real gate block on top of it."""

    def real_gate(self):
        from unittest import mock
        from image_production import route
        gate = _REAL_TABLE()["gate"]
        base = route.table
        return mock.patch.object(route, "table", lambda path=None, house=True: {**base(path, house), "gate": gate})

    def test_the_real_table_turns_both_gates_on_and_names_what_has_no_sheet_yet(self):
        g = _REAL_TABLE()["gate"]
        self.assertIs(g["recipe_required"], True)
        self.assertIs(g["approved_bases_required"], True)
        self.assertEqual(g["recipe_required_purposes"], ["ad", "video-still"])
        self.assertEqual(g["recipe_kinds_without_sheet"], ["slide"])
        self.assertEqual(g["max_attempts"]["pictures"], 3)

    def test_a_new_picture_without_a_recipe_is_refused_but_a_carousel_slide_is_not_yet(self):
        from unittest import mock
        from image_production import plain
        calls = []
        def gen(entry, prompt, refs, out, aspect, transport=None, key=None):
            calls.append(prompt); Path(out).write_bytes(b"png")
            return {"file": str(out), "model": "m", "provider": "x", "request_id": "r", "usage": None}
        with self.real_gate(), mock.patch.object(plain.PR, "generate", gen), mock.patch.object(plain, "_key", lambda e: "k"):
            with self.assertRaises(plain.RecipeRefused) as cm:
                plain.make("acme", "A tube.", Path(self.tmp) / "a.png")
            self.assertIn("carries no recipe", str(cm.exception))
            self.assertEqual(calls, [])
            plain.make("acme", "A slide.", Path(self.tmp) / "s.png", kind="slide")          # no slide sheet exists yet
            self.assertEqual(len(calls), 1)

    def test_the_engine_requires_a_recipe_for_a_new_ad_but_not_for_an_edit_or_an_email(self):
        with self.real_gate():
            with self.assertRaises(IP.BadRequest) as cm:
                IP.make(self.req(purpose="ad"), library=self.lib, transport=stub_transport([], size=(9, 16)),
                        judge_caller=judge_saying(["PASS"]), mirror=False)
            self.assertIn("carries no recipe", str(cm.exception))
            src = Path(self.tmp) / "src.png"
            src.write_bytes(ONE_PIXEL_PNG)                                  # outside material: no record, allowed as a base
            r = IP.make(self.req(purpose="ad", from_image=str(src)), library=self.lib,
                        transport=stub_transport([], size=(9, 16)), judge_caller=judge_saying(["PASS"]), mirror=False)
            self.assertEqual(len(r["delivered"]), 1)
            r = IP.make(self.req(), library=self.lib, transport=stub_transport([], size=(3, 2)),
                        judge_caller=judge_saying(["PASS"]), mirror=False)                # an email hero has no sheet
            self.assertEqual(len(r["delivered"]), 1)


class TestPictureLadder(unittest.TestCase):
    """GPT Image 2.5 first; busy or broken, one more try on GPT; refused, Seedream 5 Pro; then Nano Banana Pro; then the
    transitional net. The record says which rung made the picture."""

    def rungs(self):
        mk = lambda m, **kw: {"provider": "higgsfield", "vendor_model": m, "must_name": ["resolution"], "params": {"resolution": "2k"}, **kw}
        return [{"name": "gpt", "entry": mk("gpt_image_2_5", must_name=["variant", "quality", "resolution"], params={"variant": "sunburst", "quality": "high", "resolution": "2k"}), "retry": True, "max_images": 16},
                {"name": "backup", "entry": mk("seedream_v5_pro"), "retry": False, "max_images": 10},
                {"name": "third", "entry": mk("nano_banana_pro"), "retry": False, "max_images": 14}]

    def hf(self, plan, seen):
        """plan: {model: [outcome, ...]} outcome 'ok' | 'error' | 'refuse'."""
        class HF:
            def which(s): return "/x/higgsfield"
            def run(s, argv, timeout=900):
                if argv[1] == "account": return 0, json.dumps({"credits": 5}), ""
                m = argv[3]
                seen.append(m)
                o = plan[m].pop(0)
                if o == "ok": return 0, json.dumps([{"id": "j", "status": "completed", "result_url": "u", "params": {}}]), ""
                if o == "refuse": return 0, json.dumps([{"id": "j", "status": "nsfw", "result_url": None}]), ""
                return 1, "", "the service is busy"
            def fetch(s, url, dest): Path(dest).write_bytes(b"png")
        return HF()

    def run_ladder(self, plan, refs=(), rungs=None):
        import tempfile
        from image_production import providers
        seen, d = [], Path(tempfile.mkdtemp())
        r = providers.generate_ladder(rungs or self.rungs(), "p", list(refs), d / "o.png", "9:16", transport=self.hf(plan, seen))
        return r, seen

    def test_gpt_makes_it(self):
        r, seen = self.run_ladder({"gpt_image_2_5": ["ok"]})
        self.assertEqual((r["made_by"], seen), ("gpt", ["gpt_image_2_5"]))

    def test_busy_once_gets_one_more_try_on_gpt(self):
        r, seen = self.run_ladder({"gpt_image_2_5": ["error", "ok"]})
        self.assertEqual((r["made_by"], seen), ("gpt", ["gpt_image_2_5", "gpt_image_2_5"]))
        self.assertEqual([x["outcome"] for x in r["ladder"]], ["failed", "made"])

    def test_a_refusal_goes_straight_to_seedream_with_no_second_gpt_try(self):
        r, seen = self.run_ladder({"gpt_image_2_5": ["refuse"], "seedream_v5_pro": ["ok"]})
        self.assertEqual((r["made_by"], seen), ("backup", ["gpt_image_2_5", "seedream_v5_pro"]))
        self.assertEqual(r["ladder"][0]["outcome"], "refused")

    def test_broken_twice_then_seedream_then_nano_banana(self):
        r, seen = self.run_ladder({"gpt_image_2_5": ["error", "error"], "seedream_v5_pro": ["error"], "nano_banana_pro": ["ok"]})
        self.assertEqual((r["made_by"], seen), ("third", ["gpt_image_2_5", "gpt_image_2_5", "seedream_v5_pro", "nano_banana_pro"]))

    def test_a_rung_that_cannot_take_this_many_pictures_is_skipped_and_says_so(self):
        r, seen = self.run_ladder({"gpt_image_2_5": ["refuse"], "nano_banana_pro": ["ok"]}, refs=[f"/x/{i}.png" for i in range(11)])
        self.assertEqual(r["made_by"], "third")
        skipped = [x for x in r["ladder"] if x["outcome"] == "skipped"]
        self.assertEqual(skipped[0]["rung"], "backup")

    def test_when_nothing_works_it_raises_naming_every_attempt(self):
        from image_production import providers
        with self.assertRaises(providers.ProviderError) as cm:
            self.run_ladder({"gpt_image_2_5": ["refuse"], "seedream_v5_pro": ["refuse"], "nano_banana_pro": ["error"]})
        msg = str(cm.exception)
        for w in ("gpt refused", "backup refused", "third failed"):
            self.assertIn(w, msg)

    def test_the_route_table_ladder_is_read_by_route_rungs(self):
        t = {"models": {"a": {"vendor_model": "x"}, "b": {"vendor_model": "y", "max_images": 10}},
             "ladder": {"generate": [{"name": "gpt", "model": "a", "retry": True}, {"name": "backup", "model": "b"}]}}
        over = {"vendor_model": "x", "params": {"quality": "low"}}
        rs = IP.route.rungs("gpt-image-person", over, t)
        self.assertIs(rs[0]["entry"], over)
        self.assertEqual([r["name"] for r in rs], ["gpt", "backup"])
        self.assertEqual(rs[1]["max_images"], 10)
        self.assertEqual(len(IP.route.rungs("gpt-image-person", over, {"models": {}})), 1)


class TestRegionEdit(Base):
    """A region edit: the model may paint only inside the rectangle."""

    def setUp(self):
        super().setUp()
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent")
        self.pic = Path(self.tmp) / "ad.png"
        Image.new("RGB", (360, 640), (0, 0, 255)).save(self.pic)

    def test_the_mask_exposes_only_the_rectangle_and_the_rest_is_the_original(self):
        from PIL import Image
        from image_production import providers
        calls = []
        def t(method, url, headers, body):
            calls.append({"url": url, "body": body})
            import base64, io
            buf = io.BytesIO(); Image.new("RGB", (360, 640), (255, 0, 0)).save(buf, "PNG")
            return 200, {}, json.dumps({"data": [{"b64_json": base64.b64encode(buf.getvalue()).decode()}]}).encode()
        out = Path(self.tmp) / "out.png"
        r = providers.edit_in_region(IP.finish_entry(), "change the headline", self.pic,
                                     (10, 20, 50, 60), out, transport=t, key="stub")
        self.assertEqual(r["region_px"], (36, 128, 180, 384))
        self.assertIn(b'name="mask"', calls[0]["body"])
        with Image.open(r["mask"]) as m:
            self.assertEqual(m.getpixel((100, 200))[3], 0)        # inside: paint here
            self.assertEqual(m.getpixel((330, 600))[3], 255)      # outside: keep
        with Image.open(out) as im:
            self.assertEqual(im.getpixel((100, 200)), (255, 0, 0))   # the model's answer
            self.assertEqual(im.getpixel((330, 600)), (0, 0, 255))   # the original
            self.assertEqual(im.size, (360, 640))

    def test_make_routes_a_region_edit_through_the_mask(self):
        calls = []
        def t(method, url, headers, body):
            if b'name="mask"' in body:
                import base64, io
                from PIL import Image
                buf = io.BytesIO(); Image.new("RGB", (360, 640), (255, 0, 0)).save(buf, "PNG")
                return 200, {}, json.dumps({"data": [{"b64_json": base64.b64encode(buf.getvalue()).decode()}]}).encode()
            return stub_transport(calls, size=(9, 16))(method, url, headers, body)
        r = IP.make(self.req(purpose="ad", aspect="4:5", from_image=str(self.pic),
                             region=(10, 20, 50, 60)), library=self.lib, transport=t,
                    judge_caller=judge_saying(["PASS"]), mirror=False)
        row = r["pictures"][0]
        self.assertEqual(row["verdict"], "pass", row["fails"])
        self.assertEqual(row["region_px"], (36, 128, 180, 384))


class TestDryRun(Base):
    def test_it_spends_nothing_and_writes_nothing(self):
        ok, resolved = IP.dry_run(self.req(product="widget"), library=self.lib)
        self.assertIsNotNone(resolved)
        self.assertFalse(self.out.exists(), "the dry run must not create out/")

    def test_it_prints_the_prompt_as_it_would_be_sent(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            IP.dry_run(self.req(), library=self.lib)
        text = buf.getvalue()
        self.assertIn("a man holding the widget in a kitchen", text)
        self.assertIn("routes to", text)
        self.assertIn("where it would land", text)

    def test_a_broken_request_fails_the_dry_run(self):
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            ok, _ = IP.dry_run(self.req(purpose="nope"), library=self.lib)
        self.assertFalse(ok)


# ---------------------------------------------------------------- delivery

class TestDelivery(Base):
    def test_where_the_files_land(self):
        calls = []
        r = IP.make(self.req(label="sept-sale"), library=self.lib,
                    transport=stub_transport(calls),
                    judge_caller=judge_saying(["PASS"]), mirror=False)
        self.assertTrue((self.out / "sept-sale-01.png").is_file())
        self.assertTrue((self.out / "prompt-as-sent.txt").is_file())
        self.assertTrue((self.out / "elements.json").is_file())
        self.assertTrue((self.out / "run.json").is_file())
        run = json.loads((self.out / "run.json").read_text())
        self.assertEqual(run["machine"], "image-production")
        self.assertEqual(run["brand"], "acme")
        self.assertEqual(run["state"], "filed")
        self.assertEqual(r["model"], "gpt-image-person")

    def test_the_record_carries_no_key(self):
        IP.make(self.req(), library=self.lib, transport=stub_transport([]),
                judge_caller=judge_saying(["PASS"]), mirror=False)
        raw = (self.out / "run.json").read_text()
        for word in ("Bearer", "OPENAI_API_KEY=", "sk-"):
            self.assertNotIn(word, raw)

    def test_an_edit_sends_the_reference_to_the_edits_endpoint(self):
        src = Path(self.tmp) / "approved.png"
        src.write_bytes(ONE_PIXEL_PNG)
        calls = []
        IP.make(self.req(from_image=str(src)), library=self.lib,
                transport=stub_transport(calls), judge_caller=judge_saying(["PASS"]),
                mirror=False)
        self.assertTrue(calls[0]["url"].endswith("/images/edits"))

    def test_a_fresh_render_sends_no_reference(self):
        calls = []
        IP.make(self.req(people=True), library=self.lib,
                transport=stub_transport(calls), judge_caller=judge_saying(["PASS"]),
                mirror=False)
        self.assertTrue(calls[0]["url"].endswith("/images/generations"))


# ------------------------------------------------- the definitions are sane

class TestDefinitions(unittest.TestCase):
    def test_every_purpose_declares_the_fields_the_engine_reads(self):
        for pid, row in IP.purposes().items():
            for field in ("id", "name", "what", "aspect", "people",
                          "product_reference", "words", "frame", "status"):
                self.assertIn(field, row, f"{pid} is missing {field}")
            self.assertEqual(row["id"], pid)
            self.assertIn(row["product_reference"], ("none", "optional", "required"))
            self.assertIn(row["words"], ("never", "when_asked"))
            self.assertIn(row["aspect"], IP.route.aspects())

    def test_the_route_ends_in_a_catch_all(self):
        self.assertEqual(IP.route.table()["route"][-1]["when"], {})

    def test_no_brand_name_appears_in_any_code_or_prompt_file(self):
        home = IP.paths.home()
        brands = [p.name for p in (IP.paths.brands_dir()).iterdir()
                  if p.is_dir() and not p.name.startswith(("_", "."))]
        files = list((home / "image_production").glob("*.py")) \
            + list(home.glob("*.py")) + list((home / "prompts").glob("*.md")) \
            + [home / "models.json", home / "purposes.json"]
        for f in files:
            text = f.read_text().lower()
            for b in brands:
                self.assertNotIn(b.lower(), text, f"{f.name} names the brand `{b}`")

    def test_the_prompt_skeleton_asks_only_for_slots_that_exist(self):
        skeleton = IP.prompting.body(IP.prompting.latest("picture"))
        asked = set(IP.prompting.SLOT.findall(skeleton))
        self.assertEqual(asked - set(IP.prompting.ORDER), set())
        self.assertEqual(set(IP.prompting.ORDER) - asked, set())


class TestCli(Base):
    def test_people_is_tri_state_on_the_command_line(self):
        import make
        self.assertIsNone(make.build_parser().parse_args([]).people)
        self.assertTrue(make.build_parser().parse_args(["--people"]).people)
        self.assertFalse(make.build_parser().parse_args(["--no-people"]).people)

    def test_a_request_file_and_flags_merge(self):
        import make
        f = Path(self.tmp) / "req.json"
        f.write_text(json.dumps(self.req()))
        a = make.build_parser().parse_args(["--request", str(f), "--count", "3"])
        req = make.request_from(a)
        self.assertEqual(req["brand"], "acme")
        self.assertEqual(req["count"], 3)
        self.assertIs(req["people"], False)


class TestDriveJsonWritten(Base):
    """LD-64 (records Drive ids): make() writes the mirror's record as <out>/drive.json."""

    def test_a_mirror_writes_its_record(self):
        from unittest import mock
        rec = {"schema": 1, "folder": "Shared Assets/runs/image-production/acme/sept-sale",
               "folder_id": "fid-1", "route": "api",
               "files": [{"path": "sept-sale-01.png", "id": "id-1", "kind": "image"}]}
        got = (["Shared Assets/runs/image-production/acme/sept-sale/sept-sale-01.png"], None, rec)
        with mock.patch("image_production.filing.mirror_record", return_value=got) as m:
            IP.make(self.req(label="sept-sale"), library=self.lib, transport=stub_transport([]),
                    judge_caller=judge_saying(["PASS"]), mirror=True)
        self.assertTrue(m.called)
        self.assertEqual(json.loads((self.out / "drive.json").read_text(encoding="utf-8")), rec)

    def test_no_mirror_writes_no_record(self):
        IP.make(self.req(label="sept-sale"), library=self.lib, transport=stub_transport([]),
                judge_caller=judge_saying(["PASS"]), mirror=False)
        self.assertTrue(self.out.is_dir())
        self.assertFalse((self.out / "drive.json").exists())


class TestWordsOnTop(unittest.TestCase):
    """swaps rule 4: the picture is made with no words; the brief's type layer is set over it afterwards, the plate kept."""
    LAYER = {"layout": {}, "elements": [{"text": "HELLO THERE", "top_pct": 70, "left_pct": 9, "right_pct": 91, "align": "center",
                                        "cap_pct": 3, "color": "#FFFFFF", "case": "upper", "weight": "bold", "font": "humanist-sans",
                                        "letterform": "caption-outline, a hard black stroke"}]}

    def plate(self, d):
        from PIL import Image
        f = Path(d) / "pic.png"
        Image.new("RGB", (540, 960), (90, 90, 90)).save(f)
        return f

    def test_the_outlined_letterform_gets_the_outline_the_compositor_draws(self):
        from image_production import words
        self.assertEqual(words.prepare(self.LAYER)["elements"][0]["stroke"]["color"], "#000000")
        flat = {"elements": [{**self.LAYER["elements"][0], "letterform": "flat digital type"}]}
        self.assertNotIn("stroke", words.prepare(flat)["elements"][0])

    def test_words_go_on_and_the_plate_is_kept(self):
        import shutil
        if not shutil.which("magick"):
            self.skipTest("ImageMagick is not installed")
        from PIL import Image, ImageChops
        from image_production import words
        with tempfile.TemporaryDirectory() as d:
            pic = self.plate(d)
            r = words.set_on_top(pic, self.LAYER, plate=Path(d) / "plates" / "pic.png")
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["elements"], 1)
            plate = Image.open(r["plate"]).convert("RGB")
            self.assertEqual(plate.getpixel((270, 700)), (90, 90, 90))            # the plate has no words
            self.assertIsNotNone(ImageChops.difference(Image.open(pic).convert("RGB"), plate).getbbox())   # the result does

    def test_a_layer_with_no_words_changes_nothing(self):
        from image_production import words
        with tempfile.TemporaryDirectory() as d:
            pic = self.plate(d)
            before = pic.read_bytes()
            self.assertEqual(words.set_on_top(pic, {"elements": []})["elements"], 0)
            self.assertEqual(pic.read_bytes(), before)

    def test_generate_sets_the_layer_when_the_send_carries_one(self):
        import shutil
        if not shutil.which("magick"):
            self.skipTest("ImageMagick is not installed")
        from image_production import plain
        with tempfile.TemporaryDirectory() as d:
            made = self.plate(d)
            orig = plain.make
            plain.make = lambda *a, **k: {"file": str(made), "prompt": "p", "checks": []}
            try:
                got = plain.generate({"brand": "x", "text": "t", "type_layer": self.LAYER}, made, recipe={"x": "y"})
            finally:
                plain.make = orig
            self.assertTrue(got["words_on_top"]["ok"], got)


if __name__ == "__main__":
    unittest.main(verbosity=2)
