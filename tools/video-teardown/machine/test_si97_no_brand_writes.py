"""SI-97 (brand research proposals) — the four machine writers that wrote into
brands/ write a proposal under runs/ instead. Each test runs one writer in a
temp workspace with a fixture brand `fx` and asserts every file under
<tmp>/brands is byte-identical before and after, and the proposal exists.
No network, no model; nothing written outside the temp folder.

    /usr/bin/python3 tools/video-teardown/machine/test_si97_no_brand_writes.py
"""
import hashlib, importlib.util, json, shutil, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.append(str(WS / "components" / "naming"))

import slot_research as SR  # noqa: E402
import mark_used as M  # noqa: E402
import creator_profile as CP  # noqa: E402
import page_pick as PP  # noqa: E402

HEADER = {"brief": "brief-0005", "product": "x", "angle": "y"}
LINE = "i stopped getting razor bumps"


def load_slotfill():
    sp = importlib.util.spec_from_file_location(
        "_si97_slotfill", WS / "tools" / "video-production" / "machine" / "slotfill.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def fixture(root):
    """The fixture brand `fx` — never a real brand."""
    b = root / "brands" / "fx"
    (b / "intake" / "research").mkdir(parents=True)
    (b / "intake" / "research" / "facts-found.md").write_text("# Facts found\n\n- accepted row\n")
    (b / "core-avatars" / "a1" / "language").mkdir(parents=True)
    (b / "core-avatars" / "a1" / "language" / "leads.json").write_text(json.dumps(
        {"avatar": "a1", "entries": [{"id": "r1", "text": LINE}]}))
    (b / "briefs").mkdir(parents=True)
    (b / "briefs" / "briefs.json").write_text(json.dumps({"briefs": [HEADER]}))
    (b / "creators").mkdir(parents=True)
    (b / "creators" / "SPEC.md").write_text("# Profile spec\n")


def snapshot(root):
    """{relative path: sha1} of every file under <root>/brands."""
    base = Path(root) / "brands"
    return {str(p.relative_to(root)): hashlib.sha1(p.read_bytes()).hexdigest()
            for p in sorted(base.rglob("*")) if p.is_file()}


class NoBrandWrites(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        fixture(self.tmp)
        self.before = snapshot(self.tmp)
        self.sf = load_slotfill()

    def tearDown(self):
        self.assertEqual(snapshot(self.tmp), self.before, "a writer touched brands/")

    def test_slotfill_document_writes_proposals(self):
        brief = self.tmp / "brief.md"
        brief.write_text("brief\n")
        with mock.patch.object(self.sf, "WS", self.tmp):
            self.sf.document("fx", brief, {"scenes": [{"id": "S3", "section": "failed-solutions"}]},
                             [{"scene": "S3", "field": "voice", "now": "x", "source": "web", "receipt": "r"}])
        rdir = self.tmp / "runs" / "video-production" / "fx" / "research-proposals"
        self.assertTrue((rdir / "facts-found.md").is_file())
        self.assertTrue((rdir / "failed-solutions.md").is_file())

    def test_slot_research_fill_writes_proposal(self):
        run = self.tmp / "run1"
        (run / "stages").mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"brand": "fx", "product": None}))
        (run / "stages" / "3-injection.md").write_text("1. THE INJECTED SCRIPT\nA tub costs [SLOT: rival price] here.\n")
        fake = lambda prompt: json.dumps({"holes": [{"id": "H1", "fill": "$__", "source": "web",
                                                     "receipt": "https://example.com/p"}]})
        with mock.patch.object(self.sf, "WS", self.tmp), mock.patch.object(SR, "_slotfill", lambda: self.sf):
            got = SR.fill(run, call=fake)
        self.assertEqual(len(got["filled"]), 1)
        ff = self.tmp / "runs" / "video-production" / "fx" / "research-proposals" / "facts-found.md"
        self.assertIn("$__", ff.read_text())

    def test_mark_used_writes_proposal(self):
        lang = types.ModuleType("language")
        lang.load = lambda brand: [{"id": "r1", "text": LINE, "avatar": "a1"}]
        lang.brand_dir = lambda brand: self.tmp / "brands" / "fx"
        lang.bank_dir = lambda p: Path(p) / "core-avatars"
        run = self.tmp / "run9"
        (run / "stages").mkdir(parents=True)
        (run / "stages" / "5-brief.md").write_text(f"# Brief\n\nShe says: {LINE}.\n")
        st = {"brand": "fx", "slug": "run9", "stages": {"stage5": {"status": "done", "out": "stages/5-brief.md"}}}
        with mock.patch.object(M.C, "WS", self.tmp), mock.patch.dict(sys.modules, {"language": lang}):
            M.run(run, st)
        rel = "runs/video-writing/fx/run9/proposals/language-used/a1/run9.json"
        self.assertTrue((self.tmp / rel).is_file())
        self.assertEqual(st["used_lane"]["files"], [rel])
        self.assertEqual([u["row_id"] for u in json.loads((self.tmp / rel).read_text())["used"]], ["r1"])

    def test_creator_profile_publish_writes_proposal(self):
        cfg = {"spec": "brands/fx/creators/SPEC.md", "home": "brands/fx/creators"}
        with mock.patch.object(CP.C, "WS", self.tmp), mock.patch.object(CP, "home", lambda brand: cfg):
            got = CP.publish({"brand": "fx", "creator": "h1", "lane": "creator"}, "profile")
        self.assertEqual(got, Path("runs/video-teardown/fx/_profiles/h1/profile.md"))
        self.assertEqual((self.tmp / got).read_text(), "profile\n")

    def test_page_pick_record_writes_proposal(self):
        header = json.loads((self.tmp / "brands/fx/briefs/briefs.json").read_text())["briefs"][0]
        lp = {"link_ids": ["link_fx_quiz"], "why": "w"}
        with mock.patch.object(PP, "brief_record", lambda *a: (None, None, header)):
            got, where = PP.record("fx", "brief-0005", lp=lp, root=self.tmp)
        self.assertEqual(where, ["runs/naming/fx/landing-proposals/briefs.json#brief-0005"])
        d = json.loads((self.tmp / "runs/naming/fx/landing-proposals/briefs.json").read_text())
        self.assertEqual(len(d["briefs"]), 1)
        e = d["briefs"][0]
        self.assertEqual((e["brief"], e["product"]), ("brief-0005", "x"))
        self.assertEqual(e["landing_page"]["link_ids"], ["link_fx_quiz"])
        self.assertRegex(e["proposed"], r"^\d{4}-\d{2}-\d{2}$")
        with mock.patch.object(PP, "brief_record", lambda *a: (None, None, header)):
            PP.record("fx", "brief-0005", lp={"link_ids": ["link_fx_offer"], "why": "v"}, root=self.tmp)
        d = json.loads((self.tmp / "runs/naming/fx/landing-proposals/briefs.json").read_text())
        self.assertEqual([e["landing_page"]["link_ids"] for e in d["briefs"]], [["link_fx_offer"]])  # replaced, not added


if __name__ == "__main__":
    unittest.main()
