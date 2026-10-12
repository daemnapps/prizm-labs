"""The product truth kit standard (PRODUCT-KITS.md) — the parts that need no
network, no SAM and no Blender: kind routing, which photos are picked, the
list and the gate, product paths, size reads, label words, part lines."""
import json, os, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw
import product_kit as pk


class Kinds(unittest.TestCase):
    def test_words_route_to_kinds(self):
        for words, kind in [("tube", "tube"), ("squeeze tube", "tube"), ("pump bottle", "pump-bottle"),
                            ("airless pump bottle", "pump-bottle"), ("bottle", "bottle"), ("jar", "jar"),
                            ("supplement bottle with capsules", "jar"), ("box", "box"), ("device", "device"),
                            ("vibrating face brush", "device"), ("towel or soft goods", "soft"), ("zip pouch", "soft"),
                            ("pump-bottle", "pump-bottle"), ("other", None), (None, None)]:
            self.assertEqual(pk.kind_of(words), kind, words)

    def test_builders(self):
        self.assertEqual(pk.builder_of("tube"), "tube.py")
        for k in ("bottle", "pump-bottle", "jar"):
            self.assertEqual(pk.builder_of(k), "bottle.py")
        self.assertEqual(pk.builder_of("box"), "box.py")
        for k in ("device", "soft", None, "other"):
            self.assertIsNone(pk.builder_of(k))          # photo-only: no invented model
        for b in {v for v in pk.KINDS.values() if v}:
            self.assertTrue((pk.HERE / "blender" / b).exists(), b)


class Tree(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.drive = self.t / "brands"; self.bank = self.t / "bank"
        for b, s in [("brand-a", "thing-one"), ("brand-a", "thing-two"), ("brand-a", "bundles"),
                     ("brand-a", "_shared"), ("brand-b", "gadget"), ("brand-b", "archive")]:
            (self.drive / b / "products" / s / "packshot").mkdir(parents=True)

    def kit(self, b, s, status):
        d = self.bank / b / "products" / s; d.mkdir(parents=True, exist_ok=True)
        (d / "kit.json").write_text(json.dumps({"status": status, "kind": "tube", "outline": {"axis_ratio": 1.8}}))

    def test_products_skip_bundles_shared_archive(self):
        self.assertEqual(pk.drive_products(self.drive),
                         [("brand-a", "thing-one"), ("brand-a", "thing-two"), ("brand-b", "gadget")])

    def test_gate_and_list(self):
        self.kit("brand-a", "thing-one", "model")
        self.kit("brand-b", "gadget", "photo-only")
        self.kit("brand-a", "thing-two", "no real photos")
        self.assertIsNone(pk.gate("brand-a", "thing-one", self.bank))
        self.assertIsNone(pk.gate("brand-b", "gadget", self.bank))
        self.assertIn("NOT READY", pk.gate("brand-a", "thing-two", self.bank))
        rows = pk.listing(self.drive, self.bank)
        self.assertEqual([r["gate"] is None for r in rows], [True, False, True])
        (self.drive / "brand-b" / "products" / "new-thing").mkdir(parents=True)
        miss = [r for r in pk.listing(self.drive, self.bank) if r["slug"] == "new-thing"][0]
        self.assertFalse(miss["kit"]); self.assertIn("NO TRUTH KIT: brand-b/new-thing", miss["gate"])

    def test_product_of_path(self):
        self.kit("brand-a", "thing-one", "model")
        f = lambda p: pk.product_of_path(p, self.bank, self.drive)
        self.assertEqual(f(self.drive / "brand-a/products/thing-one/packshot/x.jpg"), ("brand-a", "thing-one"))
        self.assertEqual(f(self.bank / "brand-a/products/thing-one/sources/x.jpg"), ("brand-a", "thing-one"))
        self.assertEqual(f("/repo/brands/brand-a/products/thing-one/images/packshot-hero.webp"), ("brand-a", "thing-one"))
        self.assertEqual(f("/repo/brands/brand-a/products/images/thing-cutout.png"), None)   # no such key
        self.assertIsNone(f(self.drive / "brand-a/products/bundles/set/packshot/x.jpg"))
        self.assertIsNone(f(self.drive / "brand-a/products/_shared/packshot/x.jpg"))
        self.assertIsNone(f("/tmp/run/media/A1.png"))
        # a key the brand's own files use (kit "aliases") resolves to the slug
        k = json.loads((self.bank / "brand-a/products/thing-one/kit.json").read_text()); k["aliases"] = ["one"]
        (self.bank / "brand-a/products/thing-one/kit.json").write_text(json.dumps(k))
        self.assertEqual(f("/repo/brands/brand-a/products/images/one-cutout.png"), ("brand-a", "thing-one"))

    def test_run_gate_stops_a_product_with_no_kit(self):
        import importlib
        old = {k: os.environ.get(k) for k in ("PRODUCT_BANK", "PRODUCT_DRIVE")}
        os.environ["PRODUCT_BANK"] = str(self.bank); os.environ["PRODUCT_DRIVE"] = str(self.drive)
        try:
            import run
            ref = self.drive / "brand-b/products/gadget/packshot/front.jpg"
            with self.assertRaises(SystemExit) as e:
                run.product_gate([Path("/tmp/cast.png"), ref], "S1")
            self.assertIn("NO TRUTH KIT: brand-b/gadget", str(e.exception))
            self.kit("brand-b", "gadget", "photo-only")
            got = run.product_gate([ref], "S1")
            self.assertEqual(got[:2], ("brand-b", "gadget"))
            self.assertIsNone(run.product_gate([Path("/tmp/cast.png")], "S1"))
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_pick_sources(self):
        f = self.drive / "brand-a" / "products" / "thing-one"
        for rel in ["packshot/a-white.jpg", "packshot/b.jpg", "packshot/box-front.jpg", "packshot/cards/card.jpg",
                    "lifestyle/in-hand.jpg", "ugc/u1.jpg", "ai/fake.png", "cgi/render.png", "video/clip.mp4",
                    "packshot/2024-01_old/old.jpg"]:
            p = f / rel; p.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix == ".mp4":
                p.write_bytes(b"x")
            else:
                Image.new("RGB", (40, 40), "white").save(p)
        got = [p.name for p in pk.pick_sources(f)]
        self.assertEqual(got[0], "a-white.jpg")
        for bad in ("card.jpg", "fake.png", "render.png", "clip.mp4", "old.jpg"):
            self.assertNotIn(bad, got)                     # never AI, CGI, cards, video; old shoots only fill in
        self.assertIn("in-hand.jpg", got); self.assertIn("u1.jpg", got)
        self.assertLess(got.index("b.jpg"), got.index("box-front.jpg"))


class Measures(unittest.TestCase):
    def test_size_needs_three_agreeing_reads_and_takes_the_lower_quarter(self):
        self.assertIsNone(pk.size_from_reads([(20, "a", "hand"), (21, "b", "hand")], 2.0))
        s = pk.size_from_reads([(12, "a", "hand"), (13, "b", "hand"), (15, "c", "face"), (16, "d", "hand"), (4, "e", "hand")], 2.0)
        self.assertEqual(s["height"], 12); self.assertEqual(s["width"], 6.0)      # 4 dropped as the wrong hand
        self.assertGreaterEqual(s["plus_minus"], 3)

    def test_key_words_are_the_biggest_real_words(self):
        lines = [(0.01, "BE THE BEST YOU"), (0.03, "waaaan"), (0.04, "BRAND A"), (0.03, "BRAND™ NAME"),
                 (0.05, "NET WT. 100 g"), (0.002, "tiny print here")]
        self.assertEqual(pk.key_words(lines, 3), ["BRAND A", "waaaan", "BRAND NAME"])

    def test_cut_off(self):
        m = Image.new("L", (100, 100), 0); ImageDraw.Draw(m).rectangle([20, 20, 80, 99], fill=255)
        self.assertTrue(pk.cut_off(m))
        m = Image.new("L", (100, 100), 0); ImageDraw.Draw(m).rectangle([20, 20, 80, 90], fill=255)
        self.assertFalse(pk.cut_off(m))

    def test_part_line_runs_across_and_print_does_not(self):
        im = Image.new("RGB", (200, 400), "white"); d = ImageDraw.Draw(im)
        d.rectangle([50, 20, 150, 300], fill=(200, 180, 150)); d.rectangle([60, 300, 140, 380], fill=(150, 130, 100))
        d.text((70, 150), "WORDS", fill=(0, 0, 0))                # print covers part of a row only
        m = Image.new("L", im.size, 0); md = ImageDraw.Draw(m)
        md.rectangle([50, 20, 150, 300], fill=255); md.rectangle([60, 300, 140, 380], fill=255)
        lines = pk.full_width_lines(im, m, pk.bbox(m), lo=0.03, hi=0.97)
        self.assertEqual(len(lines), 1); self.assertAlmostEqual(lines[0], (300 - 20) / 360, delta=0.02)

    def test_profile(self):
        m = Image.new("L", (200, 400), 0); d = ImageDraw.Draw(m)
        d.polygon([(40, 20), (160, 20), (130, 300), (70, 300)], fill=255)
        prof, mw = pk.profile_of(pk.widths(m, pk.bbox(m)))
        self.assertAlmostEqual(prof[0][1], 1.0, delta=0.02); self.assertAlmostEqual(prof[-1][1], 0.5, delta=0.04)

    def test_readme_is_plain(self):
        kit = {"product": "brand-a/thing-one", "what": "the cream tube", "kind": "tube", "status": "model",
               "size_cm": {"height": 12.0, "width": 7.0, "plus_minus": 3.0}, "outline": {"axis_ratio": 1.79},
               "tube_rgb": [1, 0.5, 0], "cap_rgb": [0, 0, 0], "label_words": ["BRAND", "THE SCRUB"]}
        r = pk.readme(kit, ["README.md", "tube.blend", "reference-front.png", "reference-front-transparent.png", "packshot-cutout.png"])
        for w in ("12.0 cm tall", "1.79×", "#ff8000", "BRAND · THE SCRUB", "Blender", "Photoshop", "AI image tool"):
            self.assertIn(w, r)


if __name__ == "__main__":
    unittest.main()
