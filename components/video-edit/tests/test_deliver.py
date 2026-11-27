"""The last stations of the edit-map line (machine/deliver.py): finished versions named
through components/naming and staged as one approval card. Fixtures only — no network,
no Drive, no Meta; the brand is a made-up one so nothing in the real register answers."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import deliver as D  # noqa: E402

BRAND, PRODUCT, LABEL, BATCH = "zzbrand", "zz-scrub", "zz-ad", "batch-2026-10-03-c"
BRIEF_JSON = {"lane": "ai", "piece": {"brand": BRAND, "product": PRODUCT, "avatar": "zz-avatar",
                                      "aspect_ratio": "9:16"},
              "edit": {"headline": "ON-SCREEN TEXT, NOT AD COPY"}}
HOOKS = [{"id": "Opening 1 · Control", "text": "control line"},
         {"id": "Opening 2 · Two", "text": "hook two line"},
         {"id": "Opening 3 · Three", "text": "hook three line"}]


def make(root: Path, *, brief="brief-0007", brief_json=None, renders=("control", "G01-H2", "G01-H3"),
         maps=("G01-H2", "G01-H3"), empty=False):
    """A tiny workspace: one production run, one edit run, one renders folder."""
    (root / "brands" / BRAND).mkdir(parents=True)
    (root / "CLAUDE.md").write_text("ws")
    prod = root / "runs/video-production" / BRAND / LABEL
    prod.mkdir(parents=True)
    (prod / "run.json").write_text(json.dumps({"brand": BRAND, "label": LABEL, **({"brief": brief} if brief else {})}))
    (prod / "brief.md").write_text("# a brief\n\n```json\n" + json.dumps(brief_json or BRIEF_JSON) + "\n```\n")
    (prod / "plan.json").write_text(json.dumps({"hooks": HOOKS}))
    edit = root / "runs/video-edit" / BRAND / LABEL
    edit.mkdir(parents=True)
    base = {"from_run": f"runs/video-production/{BRAND}/{LABEL}", "brand": BRAND, "label": LABEL}
    (edit / "edit-map.json").write_text(json.dumps(base))
    for i, h in enumerate(maps, 2):
        (edit / f"edit-map-{h}.json").write_text(json.dumps({**base, "hook": f"Opening {i} · {['Two', 'Three', 'Four'][i - 2]}"}))
    out = root / "renders"
    out.mkdir()
    for v in renders:
        (out / f"{v}.mp4").write_bytes(b"" if empty else b"not really a video")
    return edit, out


class TestDeliver(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.root = Path(self._d.name)

    def tearDown(self):
        self._d.cleanup()

    def test_dry_run_names_every_version_and_writes_nothing(self):
        edit, out = make(self.root)
        pl = D.plan(edit, out, batch=BATCH, dry_run=True)
        unit = f"{BRAND}_{PRODUCT}_brief-0007_{BATCH}"
        self.assertEqual(pl["ad_name"], unit)
        self.assertEqual([r["version"] for r in pl["files"]], ["control", "G01-H2", "G01-H3"])
        self.assertEqual([r["now"] for r in pl["files"]], [f"{unit}_asset-0{i}.mp4" for i in (1, 2, 3)])
        self.assertEqual(pl["files"][1]["hook_text"], "hook two line")
        self.assertEqual(pl["files"][0]["hook"], "Opening 1 · Control")
        c = pl["card"]
        self.assertEqual((c["schema"], c["lane"], c["format"], c["brief_id"], c["product"], c["avatar"]),
                         ("meta-card/1", "video", "flexible", "brief-0007", PRODUCT, "zz-avatar"))
        self.assertEqual(c["media"], [r["now"] for r in pl["files"]])
        self.assertEqual(c["made_by"]["run"], f"runs/video-edit/{BRAND}/{LABEL}")
        self.assertEqual(c["words"], {"primary": [], "headlines": [], "descriptions": []})
        self.assertEqual(pl["missing"], ["primary text", "headline", "landing page", "angle"])
        self.assertFalse((edit / "deliverable").exists())

    def test_the_on_screen_headline_is_never_ad_copy(self):
        edit, out = make(self.root)
        pl = D.plan(edit, out, batch=BATCH, dry_run=True)
        self.assertNotIn("ON-SCREEN TEXT, NOT AD COPY", json.dumps(pl["card"]))

    def test_stages_the_card_folder(self):
        edit, out = make(self.root)
        pl = D.plan(edit, out, batch=BATCH)
        target = D.write(pl)
        self.assertEqual(target, edit.resolve() / "deliverable" / pl["ad_name"])
        names = sorted(p.name for p in target.iterdir())
        self.assertEqual(names, sorted([r["now"] for r in pl["files"]] + ["card.json", "naming.json", "manifest.json"]))
        self.assertTrue((out / "control.mp4").is_file())            # copied, never moved
        card = json.loads((target / "card.json").read_text())
        self.assertIsNone(card["approval"])
        naming = json.loads((target / "naming.json").read_text())
        self.assertEqual([f["was"] for f in naming["files"]], ["control.mp4", "G01-H2.mp4", "G01-H3.mp4"])
        man = json.loads((target / "manifest.json").read_text())
        self.assertEqual(man["batch"], BATCH)
        self.assertEqual(D.N.audit(target / "manifest.json"), [])
        self.assertEqual(D.N.batches_used(D.N.dt.date(2026, 10, 3), roots=[self.root / "runs"]), {"c"})

    def test_words_json_in_the_edit_run_fills_the_card(self):
        edit, out = make(self.root)
        (edit / "words.json").write_text(json.dumps({"primary": ["A body."], "headlines": ["A headline"]}))
        pl = D.plan(edit, out, batch=BATCH, dry_run=True)
        self.assertEqual(pl["card"]["words"]["primary"], ["A body."])
        self.assertEqual(pl["card"]["words"]["headlines"], ["A headline"])
        self.assertNotIn("primary text", pl["missing"])
        self.assertNotIn("headline", pl["missing"])

    def test_no_brief_number_stops(self):
        edit, out = make(self.root, brief=None)
        with self.assertRaises(D.Stop) as e:
            D.plan(edit, out, batch=BATCH)
        self.assertIn("brief", str(e.exception))
        self.assertFalse((edit / "deliverable").exists())
        # a dry run still shows the card, with the gap in the name and a STOP
        pl = D.plan(edit, out, batch=BATCH, dry_run=True)
        self.assertEqual([k for k, _ in pl["stops"]], ["brief"])
        self.assertIn("<brief?>", pl["ad_name"])
        self.assertNotIn("_none_", json.dumps(pl["card"]))
        with self.assertRaises(D.Stop):
            D.write(pl)

    def test_no_product_stops(self):
        bj = json.loads(json.dumps(BRIEF_JSON))
        del bj["piece"]["product"]
        edit, out = make(self.root, brief_json=bj)
        with self.assertRaises(D.Stop) as e:
            D.plan(edit, out, batch=BATCH, dry_run=True)
        self.assertTrue(str(e.exception).startswith("product"))

    def test_an_unknown_brief_flag_is_refused(self):
        edit, out = make(self.root, brief=None)
        with self.assertRaises(D.Stop):
            D.plan(edit, out, brief="brief-9999", batch=BATCH, dry_run=True)

    def test_a_render_not_named_by_version_is_refused(self):
        edit, out = make(self.root, renders=("control", "final-v3"))
        with self.assertRaises(D.Stop):
            D.plan(edit, out, batch=BATCH, dry_run=True)

    def test_a_render_with_no_edit_map_is_refused(self):
        edit, out = make(self.root, renders=("control", "G01-H9"))
        with self.assertRaises(D.Stop):
            D.plan(edit, out, batch=BATCH, dry_run=True)

    def test_a_hook_map_without_its_hook_is_refused(self):
        edit, out = make(self.root)
        m = json.loads((edit / "edit-map-G01-H2.json").read_text())
        del m["hook"]
        (edit / "edit-map-G01-H2.json").write_text(json.dumps(m))
        with self.assertRaises(D.Stop):
            D.plan(edit, out, batch=BATCH, dry_run=True)

    def test_edit_maps_with_no_render_are_listed(self):
        edit, out = make(self.root, renders=("control", "G01-H3"))
        pl = D.plan(edit, out, batch=BATCH, dry_run=True)
        self.assertEqual(pl["not_rendered"], ["G01-H2"])
        self.assertEqual([r["version"] for r in pl["files"]], ["control", "G01-H3"])
        self.assertTrue(pl["files"][1]["now"].endswith("_asset-02.mp4"))

    def test_empty_placeholders_plan_but_never_stage(self):
        edit, out = make(self.root, empty=True)
        D.plan(edit, out, batch=BATCH, dry_run=True)
        with self.assertRaises(D.Stop):
            D.plan(edit, out, batch=BATCH)

    def test_a_second_delivery_needs_replace_and_keeps_its_name(self):
        edit, out = make(self.root)
        first = D.write(D.plan(edit, out, batch=BATCH))
        with self.assertRaises(D.Stop):
            D.plan(edit, out)
        again = D.write(D.plan(edit, out, replace=True))
        self.assertEqual(again, first)
        self.assertEqual(len(list((edit / "deliverable").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
