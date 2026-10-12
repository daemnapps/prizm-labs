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


class Base(unittest.TestCase):
    def setUp(self):
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

    def test_a_9x16_asset_is_content_at_4x5_plus_the_finish(self):
        """the owner, 2026-09-22: every asset 9:16, faces and words in a centred
        4:5 zone — done by geometry: content generated at 4:5, then taped down
        and the strips painted (finish_9x16). No zone test needed then."""
        from image_production import judge
        req, ctx, ad, *_ = IP.resolve(self.req(purpose="ad"), library=self.lib)
        self.assertEqual((req["_gen_aspect"], req["_aspect"], req["_finish"]), ("4:5", "9:16", True))
        self.assertIn("This is the CONTENT of a 9:16 asset", ad)
        self.assertNotIn("COMPOSITION FOR CROPPING", ad)
        self.assertNotIn(judge.SAFE_ZONE, judge.tests_for(req, ctx))
        req, ctx, hero, *_ = IP.resolve(self.req(), library=self.lib)
        self.assertFalse(req["_finish"])
        self.assertNotIn("CONTENT of a", hero)
        # a safe-zone purpose asked for another frame is MADE at that frame and
        # still LEAVES at 9:16 — the finish is a core step (the owner, 2026-09-29)
        req, ctx, sq, *_ = IP.resolve(self.req(purpose="ad", aspect="3:4"), library=self.lib)
        self.assertEqual((req["_gen_aspect"], req["_aspect"], req["_finish"]), ("3:4", "9:16", True))
        self.assertIn("This is the CONTENT of a 9:16 asset", sq)

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
        self.assertIn("The frame is 3:4", text)
        self.assertEqual(ctx["references"], [str(src)])
        # an edit leaving at 9:16 is edited at 4:5 and finished like any other
        req, ctx, text, *_ = IP.resolve(self.req(purpose="ad", from_image=str(src)), library=self.lib)
        self.assertTrue(req["_finish"])
        self.assertIn("This is the CONTENT of a 9:16 asset", text)

    def test_assets_is_a_declared_field(self):
        IP.resolve(self.req(assets=False), library=self.lib)

    def test_the_element_row_lands_in_the_prompt(self):
        _r, _c, text, *_ = IP.resolve(self.req(style="candid-ugc"), library=self.lib)
        self.assertIn("a photograph a real person took", text)


# ---------------------------------------------------------------- the route

class TestRoute(Base):
    def test_an_edit_routes_to_the_edit_model(self):
        src = Path(self.tmp) / "a.png"
        src.write_bytes(ONE_PIXEL_PNG)
        *_x, model, _e, _w = IP.resolve(self.req(from_image=str(src)), library=self.lib)
        self.assertEqual(model, "gpt-image-edit")

    def test_a_person_in_frame_goes_to_gpt(self):
        *_x, model, _e, why = IP.resolve(self.req(people=True), library=self.lib)
        self.assertEqual(model, "gpt-image-person")

    def test_everything_else_goes_to_gpt_too_one_door(self):
        """the owner, 2026-09-22: "everything image needs to just be gpt now."
        The person/object split is retired; the object door stays declared,
        approved and `routed: false` — forceable, never routed to — because
        run records name it."""
        *_x, model, _e, why = IP.resolve(self.req(people=False), library=self.lib)
        self.assertEqual(model, "gpt-image-person")
        self.assertIn("one door", why)
        table = IP.route.table()
        self.assertEqual(table["models"]["gemini-image-object"]["status"], "approved")
        self.assertIs(table["models"]["gemini-image-object"]["routed"], False)

    def test_a_forced_model_wins_and_still_has_to_be_declared(self):
        *_x, model, _e, why = IP.resolve(self.req(model="gemini-image-object"), library=self.lib)
        self.assertEqual(model, "gemini-image-object")
        self.assertIn("named by the caller", why)
        with self.assertRaises(SystemExit) as e:
            IP.resolve(self.req(model="midjourney"), library=self.lib)
        self.assertIn("not a model in this component's route table", str(e.exception))

    def test_every_route_model_names_a_key(self):
        t = IP.route.table()
        for name, entry in t["models"].items():
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
    def test_a_failed_picture_is_held_and_survivors_ship(self):
        calls = []
        r = IP.make(self.req(count=2, people=True), library=self.lib,
                    transport=stub_transport(calls),
                    judge_caller=judge_saying(["FAIL", "PASS"]), mirror=False)
        self.assertEqual(len(r["delivered"]), 1)
        self.assertEqual(len(r["held"]), 1)
        self.assertTrue((self.out / "rejected").is_dir())
        why = next((self.out / "rejected").glob("*-why.md"))
        self.assertIn("prompt to fix", why.read_text())
        check = json.loads((self.out / "check.json").read_text())
        self.assertEqual(check["media"]["result"], "HELD")

    def test_a_judge_that_did_not_run_holds_the_picture(self):
        def broken(prompt, img, entry):
            raise RuntimeError("no key")
        r = IP.make(self.req(people=True), library=self.lib,
                    transport=stub_transport([]), judge_caller=broken, mirror=False)
        self.assertEqual(r["delivered"], [])
        self.assertIn("judge did not run", r["held"][0]["fails"][0])

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


def outpaint_transport(calls):
    """The edit door answering an outpaint: a 1024x1536 PNG painted solid red,
    so a test can prove the content was taped back over it."""
    import base64
    from PIL import Image
    import io
    def t(method, url, headers, body):
        calls.append({"url": url, "body": body})
        buf = io.BytesIO(); Image.new("RGB", (1024, 1536), (255, 0, 0)).save(buf, "PNG")
        return 200, {"x-request-id": "stub"}, json.dumps({"data": [{"b64_json": base64.b64encode(buf.getvalue()).decode()}]}).encode()
    return t


class TestFinish(Base):
    """The 9:16 finish: content taped down, only the strips painted."""

    def setUp(self):
        super().setUp()
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent")
        self.content = Path(self.tmp) / "content.png"
        Image.new("RGB", (400, 500), (0, 0, 255)).save(self.content)     # 4:5, solid blue

    def test_the_canvas_is_an_exact_9x16_and_the_mask_exposes_only_the_strips(self):
        """The canvas is a size this door actually makes: 1152x2048 is exactly
        9:16 and both numbers divide by 16, which is the model's only rule
        (asked of the API 2026-09-22). The content spans the full width, so
        the only thing painted is above and below — no side strips, no crop."""
        from PIL import Image
        from image_production import providers
        self.assertEqual(providers._CANVAS, (1152, 2048))
        self.assertAlmostEqual(2048 / 1152, 16 / 9, places=3)
        self.assertEqual((providers._CANVAS[0] % 16, providers._CANVAS[1] % 16), (0, 0))
        canvas, mask = providers.outpaint_canvas(self.content, Path(self.tmp) / "w")
        with Image.open(canvas) as c, Image.open(mask) as m:
            self.assertEqual(c.size, (1152, 2048)); self.assertEqual(m.size, (1152, 2048))
            self.assertEqual(c.getpixel((576, 1024))[:3], (0, 0, 255))     # content in the middle
            self.assertEqual(c.getpixel((576, 100))[3], 0)                 # transparent strip
            self.assertEqual(m.getpixel((576, 1024))[3], 255)              # mask: keep
            self.assertEqual(m.getpixel((576, 100))[3], 0)                 # mask: paint here
            self.assertEqual(m.getpixel((20, 1024))[3], 255)               # full width is content now

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

    def test_the_asset_is_9x16_and_the_content_pixels_are_untouched(self):
        from PIL import Image
        from image_production import providers
        calls = []
        out = Path(self.tmp) / "asset.png"
        r = providers.finish_9x16(IP.finish_entry(), self.content, out,
                                  transport=outpaint_transport(calls), key="stub")
        self.assertEqual(len(calls), 1)
        self.assertIn(b'name="mask"', calls[0]["body"])
        self.assertIn(b"Paint only the transparent areas", calls[0]["body"])
        with Image.open(out) as im:
            self.assertEqual(im.size, (1080, 1920))
            x0, y0, x1, y1 = r["content_box"]
            self.assertEqual((x0, x1), (0, 1080))
            self.assertEqual(im.getpixel((540, 960)), (0, 0, 255))        # content, blue
            self.assertEqual(im.getpixel((540, y0 + 2)), (0, 0, 255))
            self.assertEqual(im.getpixel((540, 100)), (255, 0, 0))        # the painted strip
            self.assertEqual(im.getpixel((540, 1850)), (255, 0, 0))

    def test_any_ratio_is_kept_whole_inside_the_4x5_zone(self):
        """the owner, 2026-09-29: any asset in any ratio → 9:16 out, nothing
        cropped, nothing stretched, no bars — and the picture inside the 4:5
        safe zone (SAFE-ZONE.md). A 1:1 spans the width; a 2:3 is as tall as
        the zone with the sides painted too; a 4:5 fills it exactly."""
        from PIL import Image
        from image_production import providers
        self.assertEqual(providers.zone_box(400, 500, 1080, 1920), (0, 285, 1080, 1635))
        self.assertEqual(providers.zone_box(1000, 1000, 1080, 1920), (0, 420, 1080, 1500))
        l, t, r, b = providers.zone_box(1920, 1080, 1080, 1920)          # 16:9
        self.assertEqual((l, r), (0, 1080)); self.assertTrue(285 <= t and b <= 1635)
        l, t, r, b = providers.zone_box(1000, 1500, 1080, 1920)          # 2:3
        self.assertEqual((t, b), (285, 1635)); self.assertEqual(r - l, 900)
        for size, colour in (((600, 400), (0, 255, 0)), ((400, 600), (0, 255, 255))):
            src = Path(self.tmp) / f"src-{size[0]}.png"
            Image.new("RGB", size, colour).save(src)
            calls, out = [], Path(self.tmp) / f"out-{size[0]}.png"
            r = providers.finish_9x16(IP.finish_entry(), src, out, transport=outpaint_transport(calls),
                                      key="stub", fit="whole")
            x0, y0, x1, y1 = r["content_box"]
            with Image.open(out) as im:
                self.assertEqual(im.size, (1080, 1920))
                self.assertEqual(im.getpixel(((x0 + x1) // 2, (y0 + y1) // 2)), colour)
                self.assertEqual(im.getpixel((540, 50)), (255, 0, 0))    # painted, not a bar
            self.assertAlmostEqual((y1 - y0) / (x1 - x0), size[1] / size[0], places=2)
            self.assertEqual(r["sides_painted"], size[1] / size[0] > 1.25)
            if r["sides_painted"]:
                self.assertIn(b"on every side", calls[0]["body"])

    def test_a_2x3_from_the_openai_door_is_its_centre_4x5(self):
        from PIL import Image
        from image_production import providers
        with Image.new("RGB", (1024, 1536)) as im:
            self.assertEqual(providers.content_4x5(im).size, (1024, 1280))
        with Image.new("RGB", (1000, 1000)) as im:
            with self.assertRaises(providers.ProviderError):
                providers.content_4x5(im)

    def test_make_delivers_the_finished_9x16_and_keeps_the_content(self):
        from PIL import Image
        calls = []
        def both(method, url, headers, body):
            if b'name="mask"' in body:
                return outpaint_transport(calls)(method, url, headers, body)
            return stub_transport(calls, size=(4, 5))(method, url, headers, body)
        r = IP.make(self.req(purpose="ad"), library=self.lib, transport=both,
                    judge_caller=judge_saying(["PASS"]), mirror=False)
        row = r["pictures"][0]
        self.assertEqual(row["verdict"], "pass", row["fails"])
        self.assertEqual((row["generated_at"], row["delivered_at"]), ("4:5", "9:16"))
        self.assertIn("content_box", row["finish"])
        with Image.open(row["file"]) as im:
            self.assertEqual(im.size, (1080, 1920))
        with Image.open(row["content"]) as im:
            self.assertEqual(im.size, (4, 5))

    def test_a_finish_that_cannot_run_holds_the_picture(self):
        calls = []
        def both(method, url, headers, body):
            if b'name="mask"' in body:
                return 500, {}, b'{"error": "down"}'
            return stub_transport(calls, size=(4, 5))(method, url, headers, body)
        r = IP.make(self.req(purpose="ad"), library=self.lib, transport=both,
                    judge_caller=judge_saying(["PASS"]), mirror=False)
        self.assertEqual(r["delivered"], [])
        self.assertIn("the 9:16 finish did not run", r["held"][0]["fails"][0])


class TestRegionEdit(Base):
    """A region edit: the model may paint only inside the rectangle."""

    def setUp(self):
        super().setUp()
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent")
        self.pic = Path(self.tmp) / "ad.png"
        Image.new("RGB", (400, 500), (0, 0, 255)).save(self.pic)

    def test_the_mask_exposes_only_the_rectangle_and_the_rest_is_the_original(self):
        from PIL import Image
        from image_production import providers
        calls = []
        def t(method, url, headers, body):
            calls.append({"url": url, "body": body})
            import base64, io
            buf = io.BytesIO(); Image.new("RGB", (400, 500), (255, 0, 0)).save(buf, "PNG")
            return 200, {}, json.dumps({"data": [{"b64_json": base64.b64encode(buf.getvalue()).decode()}]}).encode()
        out = Path(self.tmp) / "out.png"
        r = providers.edit_in_region(IP.finish_entry(), "change the headline", self.pic,
                                     (10, 20, 50, 60), out, transport=t, key="stub")
        self.assertEqual(r["region_px"], (40, 100, 200, 300))
        self.assertIn(b'name="mask"', calls[0]["body"])
        with Image.open(r["mask"]) as m:
            self.assertEqual(m.getpixel((100, 200))[3], 0)        # inside: paint here
            self.assertEqual(m.getpixel((350, 450))[3], 255)      # outside: keep
        with Image.open(out) as im:
            self.assertEqual(im.getpixel((100, 200)), (255, 0, 0))   # the model's answer
            self.assertEqual(im.getpixel((350, 450)), (0, 0, 255))   # the original
            self.assertEqual(im.size, (400, 500))

    def test_make_routes_a_region_edit_through_the_mask(self):
        calls = []
        def t(method, url, headers, body):
            if b'name="mask"' in body:
                import base64, io
                from PIL import Image
                buf = io.BytesIO(); Image.new("RGB", (400, 500), (255, 0, 0)).save(buf, "PNG")
                return 200, {}, json.dumps({"data": [{"b64_json": base64.b64encode(buf.getvalue()).decode()}]}).encode()
            return stub_transport(calls, size=(4, 5))(method, url, headers, body)
        r = IP.make(self.req(purpose="ad", aspect="4:5", from_image=str(self.pic),
                             region=(10, 20, 50, 60)), library=self.lib, transport=t,
                    judge_caller=judge_saying(["PASS"]), mirror=False)
        row = r["pictures"][0]
        self.assertEqual(row["verdict"], "pass", row["fails"])
        self.assertEqual(row["region_px"], (40, 100, 200, 300))


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
