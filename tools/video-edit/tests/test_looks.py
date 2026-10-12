"""The settings the owner asked for on 2026-09-23 — word spacing, the font library, text
zones that move off a face, platform-UI styles, icons and drawn elements, and the
transitions catalogue. No renders, no downloads, no live runs."""
import copy, json, re, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose as C, cutsheet as CS, fonts as FT, icons as IC, placement as P  # noqa: E401
from test_elements import elements_sheet


class Spacing(unittest.TestCase):
    def page(self, look="bold-highlight"):
        d = tempfile.mkdtemp(); root = Path(d); s = elements_sheet(root)
        s["captions"]["look"] = look
        return C.compose(s, root, root / "proj").read_text()

    def test_one_space_between_words_and_no_margin(self):
        for look in ("bold-highlight", "clean-lower", "one-word"):
            page = self.page(look)
            self.assertNotIn("margin:0 .22em", page)                  # the old per-word margin that doubled every gap
            self.assertIn(".cap span{display:inline-block}", page)    # the spans carry no margin at all
            self.assertRegex(page, r"\.cap\{[^}]*word-spacing:(normal|0\.1em)")
            self.assertNotRegex(page, r"</span>\s{2,}<span")          # exactly one space between words
            if look != "one-word":  # one word a line has no gap to measure
                self.assertRegex(page, r'id="cap0w0">[^<]+</span> <span id="cap0w1"')

    def test_every_look_names_spacing(self):
        for r in json.loads((CS.TOOL / "looks/bank.json").read_text())["looks"]:
            self.assertIn("word_spacing", r); self.assertIn("letter_spacing", r)


class Zones(unittest.TestCase):
    def sheet(self):
        self.root = Path(tempfile.mkdtemp()); s = elements_sheet(self.root)
        s["layers"]["lower_thirds"][0].pop("y_pct"); s["layers"]["platform_ui"][0].pop("y_pct"); s["overlays"][0].pop("y_pct")
        return s

    def test_every_zone_clears_every_surface_and_sits_in_4x5(self):
        box = P.safe_box(None)
        self.assertGreaterEqual(box[1], 14.84); self.assertLessEqual(box[3], 85.16)
        for z in P.zones().values():
            self.assertTrue(P.zone_clear(z, box), z["id"])
        self.assertEqual(CS.settings_red(), [])

    def test_defaults_assigned(self):
        s = P.place(self.sheet())
        self.assertEqual(s["overlays"][0]["zone"], "top-headline")
        self.assertEqual(s["layers"]["lower_thirds"][0]["zone"], "lower-third")
        self.assertEqual(s["captions"]["zones"]["S1"]["zone"], "caption-band")
        self.assertEqual(s["placement"], [])

    def test_face_moves_captions_to_nearest_free_zone_and_says_why(self):
        s = self.sheet()
        for p in s["picture"]:
            if p["scene"] == "S1":
                p["subject_box"] = {"x": 20, "y": 45, "w": 60, "h": 20}  # a face low in frame, over the caption band
        s = P.place(s)
        z = s["captions"]["zones"]["S1"]
        self.assertNotEqual(z["zone"], "caption-band")
        self.assertEqual(z["zone"], "upper-third")      # first free zone in caption-band's moves_to, nearest
        self.assertIn("would cover the face", z["why"])
        self.assertTrue(any(m["layer"] == "captions" and m["scene"] == "S1" for m in s["placement"]))
        self.assertNotIn("S1", s["face_blind"])
        page = C.compose(s, self.root, self.root / "p")
        self.assertIn(C._box("upper-third"), page.read_text())  # and the words are drawn there

    def test_two_layers_never_share_a_zone_at_once(self):
        s = self.sheet()
        s["layers"]["icons"] = [{"id": "ic1", "scene": "S1", "icon": "checkmark", "zone": "upper-third", "size": "m", "start": 0.5, "duration": 1.0}]
        s = P.place(s)  # the comment reply already holds upper-third in S1
        self.assertEqual(s["layers"]["platform_ui"][0]["zone"], "upper-third")
        self.assertNotEqual(s["layers"]["icons"][0]["zone"], "upper-third")
        self.assertTrue(any("already holding platform_ui ui1" in m["why"] for m in s["placement"]))

    def test_per_frame_boxes_are_unioned(self):
        self.assertEqual(P.subject_box({"subject_box": [{"x": 10, "y": 10, "w": 10, "h": 10}, {"x": 40, "y": 30, "w": 10, "h": 10}]}), (10, 10, 50, 40))

    def test_face_blind_is_a_warning(self):
        s = P.place(self.sheet())
        self.assertIn("S1", s["face_blind"])
        self.assertTrue(any("face-blind for S1" in w for w in CS.warnings(s)))
        self.assertEqual(CS.check(s, Path(tempfile.mkdtemp()), probe=lambda p: 30.0) and [], [])  # a warning never reddens


class UnknownIds(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name); self.s = elements_sheet(self.root)
    def tearDown(self): self.t.cleanup()
    def has(self, needle):
        r = CS.check(self.s, self.root, probe=lambda p: 30.0); self.assertTrue(any(needle in x for x in r), f"no `{needle}` in {r}")

    def test_green(self): self.assertEqual(CS.check(self.s, self.root, probe=lambda p: 30.0), [])
    def test_layer_zone(self): self.s["layers"]["lower_thirds"][0]["zone"] = "bottom-bar"; self.has("zone `bottom-bar` is not a zone")
    def test_caption_zone(self): self.s["captions"]["zones"] = {"S1": {"zone": "nowhere"}}; self.has("captions.zones[S1]")
    def test_hook_zone(self): self.s["overlays"][0]["zone"] = "sky"; self.has("zone `sky`")
    def test_ui_style_unknown(self): self.s["layers"]["platform_ui"][0]["style"] = "tiktok-reply-neon"; self.has("not a platform-UI style")
    def test_ui_style_wrong_kind(self): self.s["layers"]["platform_ui"][0]["style"] = "search-pill-light"; self.has("draws a search, not a comment_reply")
    def test_ui_kind_needs(self):
        self.s["layers"]["platform_ui"][0].update(kind="x_post", handle=""); self.has("a x_post with no handle")
    def test_transition_not_installed(self): self.s["layers"]["transitions"][0]["kind"] = "glitch"; self.has("not installed")
    def test_punch_in_is_a_move(self): self.s["layers"]["transitions"][0]["kind"] = "punch-in"; self.has("move inside one shot")
    def test_match_swipe_look_needs_a_font_id(self):
        self.s["captions"]["look"] = {"id": "match-swipe", "font": "'Comic Sans MS'", "weight": 900, "size_px": 80, "color": "#fff", "highlight": "#fff", "max_words": 3, "zone": "caption-band"}
        self.has("never a CSS stack")
    def test_every_catalogue_row_says_what_triggers_it(self):
        for r in json.loads((CS.TOOL / "looks/transitions.json").read_text())["transitions"]:
            self.assertTrue(r.get("trigger") and r.get("when_to_use"), r["id"])
            if not r.get("drawn"):
                self.assertTrue(r.get("registry"), r["id"])


class Fonts(unittest.TestCase):
    def test_every_font_is_open_licence(self):
        for r in FT.rows().values():
            self.assertIn(r["licence"], ("OFL-1.1", "Apache-2.0"), r["id"])
            self.assertTrue(r["bundled"] or r["fetch"], r["id"])
            self.assertTrue(r["bundled"] or FT.rows()[r["fallback"]]["bundled"], r["id"])  # a stand-in always renders

    def test_missing_font_falls_back_with_a_warning(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(FT, "folder", lambda f: Path(d) / f):
            row, warn = FT.resolve("tiktok-sans")
            self.assertEqual(row["id"], "inter"); self.assertIn("not fetched yet", warn)
            self.assertEqual(FT.stack("tiktok-sans"), "'Inter',sans-serif")
            s = elements_sheet(Path(d))  # its comment_reply draws in the default style, set in tiktok-sans
            s["layers"]["platform_ui"][0]["style"] = "tiktok-reply-white"
            self.assertTrue(any("tiktok-sans" in w and "install" in w for w in CS.warnings(s)))

    def test_fetched_font_gets_a_local_font_face(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(FT, "folder", lambda f: Path(d) / f):
            f = Path(d) / "tiktok-sans"; f.mkdir()
            (f / "latin-1.woff2").write_bytes(b"x")
            (f / "manifest.json").write_text(json.dumps({"family": "TikTok Sans", "files": [{"file": "latin-1.woff2", "weight": "400 900", "style": "normal", "unicode_range": "U+0000-00FF"}]}))
            self.assertEqual(FT.status("tiktok-sans"), "fetched"); self.assertIsNone(FT.resolve("tiktok-sans")[1])
            root = Path(d); s = elements_sheet(root); s["layers"]["platform_ui"][0]["style"] = "tiktok-reply-white"
            page = C.compose(s, root, root / "proj").read_text()
            self.assertIn("@font-face{font-family:'TikTok Sans'", page)
            self.assertIn("assets/fonts/tiktok-sans-latin-1.woff2", page)
            self.assertTrue((root / "proj/assets/fonts/tiktok-sans-latin-1.woff2").is_file())

    def test_nothing_downloads_in_a_dry_run(self):
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("no network in tests")):
            self.assertEqual(FT.status("inter"), "bundled")  # lookups never touch the network


class IconLayer(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name); self.s = elements_sheet(self.root)
        self.s["layers"]["icons"] = [
            {"id": "ic1", "scene": "S1", "icon": "burst-sale", "text": "40% OFF", "zone": "left-rail", "size": "m", "start": 0.5, "duration": 1.5},
            {"id": "ic2", "scene": "S4", "icon": "star-rating", "value": 4.8, "zone": "upper-third", "size": "s", "start": 5.2, "duration": 1.5},
            {"id": "ic3", "scene": "S1", "icon": "fire", "zone": "left-rail", "size": 120, "start": 2.1, "duration": 1.0}]
    def tearDown(self): self.t.cleanup()
    def red(self): return CS.check(self.s, self.root, probe=lambda p: 30.0)
    def has(self, needle):
        r = self.red(); self.assertTrue(any(needle in x for x in r), f"no `{needle}` in {r}")

    def test_green(self): self.assertEqual(self.red(), [])
    def test_unknown_icon(self): self.s["layers"]["icons"][0]["icon"] = "unicorn"; self.has("icon `unicorn` is not in looks/icons.json")
    def test_burst_needs_words(self): self.s["layers"]["icons"][0]["text"] = ""; self.has("carries words")
    def test_rating_needs_value(self): del self.s["layers"]["icons"][1]["value"]; self.has("needs a number")
    def test_size(self): self.s["layers"]["icons"][0]["size"] = "huge"; self.has("size `huge`")
    def test_zone(self): self.s["layers"]["icons"][0]["zone"] = "right-rail"; self.has("zone `right-rail` is not a zone")
    def test_outside_video(self): self.s["layers"]["icons"][0]["start"] = 40; self.has("runs outside the video")
    def test_unfetched_icon_warns(self):
        with mock.patch.object(IC, "status", lambda i: "missing" if i == "fire" else "drawn"):
            self.assertTrue(any("icon `fire` is not fetched" in w for w in CS.warnings(self.s)))
    def test_drawn(self):
        page = C.compose(self.s, self.root, self.root / "proj").read_text()
        self.assertIn('id="ic1-in"', page); self.assertIn("40% OFF", page); self.assertIn('id="ic2-fill"', page)
        self.assertIn('attr:{width:499.2}', page)  # 4.8 of 5 stars filled

    def test_every_row_has_licence_and_motion(self):
        lib = json.loads((CS.TOOL / "looks/icons.json").read_text())
        for r in lib["icons"]:
            self.assertIn(r["kind"], ("icon", "emoji", "sticker", "drawn"))
            self.assertIn(r["anim_in"], lib["animations"]["in"], r["id"]); self.assertIn(r["anim_out"], lib["animations"]["out"])
            self.assertEqual(r["licence"], lib["sets"][r["set"]]["licence"] if r["set"] != "drawn" else "ours")


class PlatformUi(unittest.TestCase):
    def test_every_kind_draws(self):
        d = tempfile.mkdtemp(); root = Path(d); s = elements_sheet(root)
        ui = json.loads((CS.TOOL / "looks/platform_ui.json").read_text())
        s["layers"]["platform_ui"] = [{"id": f"u{j}", "scene": "S1", "kind": st["kind"], "style": st["id"], "text": "hello there\nhi back", "handle": "@a",
                                       "start": 0.2, "duration": 1.0, "zone": st["zone"]} for j, st in enumerate(ui["styles"])]
        self.assertEqual(CS.check(s, root, probe=lambda p: 30.0), [])
        page = C.compose(s, root, root / "proj").read_text()
        for j in range(len(ui["styles"])):
            self.assertIn(f'id="u{j}-in"', page)


if __name__ == "__main__":
    unittest.main()
