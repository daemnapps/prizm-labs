"""SI-97 (brand research proposals) — every reader of the four writers reads the
brand file AND the open proposals under runs/, so nothing is researched or
picked twice. Temp workspace with a fixture brand `fx`; every file under
<tmp>/brands is byte-identical before and after each test. No network, no model.

    /usr/bin/python3 tools/video-teardown/machine/test_si97_read_back.py
"""
import hashlib, importlib.util, json, shutil, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.append(str(WS / "components" / "naming"))
sys.path.append(str(WS / "tools" / "language-layer"))
sys.path.append(str(WS / "components" / "meta-upload"))

import creator_profile as CP  # noqa: E402
import page_pick as PP  # noqa: E402
import card_words as W  # noqa: E402
from language_layer import engine as E  # noqa: E402

HEADER = {"brief": "brief-0005", "product": "x", "angle": "y"}


def load_slotfill():
    sp = importlib.util.spec_from_file_location(
        "_si97_slotfill_rb", WS / "tools" / "video-production" / "machine" / "slotfill.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def used_file(asset, row_ids):
    return json.dumps({"schema": 1, "kind": "language-used", "asset": asset, "run": asset,
                       "used": [{"row_id": r, "where": "5", "how": "matched"} for r in row_ids]})


def fixture(root):
    """The fixture brand `fx` — never a real brand."""
    b = root / "brands" / "fx"
    write(b / "intake" / "research" / "facts-found.md", "# Facts found\n\n- accepted row\n")
    write(b / "core-avatars" / "a1" / "language" / "leads.json", json.dumps(
        {"avatar": "a1", "entries": [{"id": "r1", "text": "one"}, {"id": "r2", "text": "two"}]}))
    write(b / "core-avatars" / "a1" / "language" / "used" / "run1.json", used_file("run1", ["r1"]))
    write(b / "briefs" / "briefs.json", json.dumps({"briefs": [HEADER]}))
    write(b / "creators" / "SPEC.md", "# Profile spec\n")


def snapshot(root):
    """{relative path: sha1} of every file under <root>/brands."""
    base = Path(root) / "brands"
    return {str(p.relative_to(root)): hashlib.sha1(p.read_bytes()).hexdigest()
            for p in sorted(base.rglob("*")) if p.is_file()}


class ReadBack(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        fixture(self.tmp)
        self.before = snapshot(self.tmp)

    def tearDown(self):
        self.assertEqual(snapshot(self.tmp), self.before, "a reader touched brands/")

    def test_slotfill_brand_files_reads_proposals(self):
        sf = load_slotfill()
        write(self.tmp / "runs/video-production/fx/research-proposals/facts-found.md", "- proposed row\n")
        with mock.patch.object(sf, "WS", self.tmp):
            files = sf.brand_files("fx")
        self.assertIn("brands/fx/intake/research/facts-found.md", files)
        self.assertEqual(files["runs/video-production/fx/research-proposals/facts-found.md"], "- proposed row\n")
        keys = list(files)
        self.assertLess(keys.index("brands/fx/intake/research/facts-found.md"),
                        keys.index("runs/video-production/fx/research-proposals/facts-found.md"))

    def test_language_used_reads_proposals(self):
        prop = self.tmp / "runs/video-writing/fx/run9/proposals/language-used/a1/run9.json"
        write(prop, used_file("run9", ["r2"]))
        self.assertEqual(E.used_ids("fx", root=self.tmp), {"r1", "r2"})
        recs = E.load_used("fx", root=self.tmp)
        self.assertEqual([r.get("_proposal") for r in recs if r["row_id"] == "r2"], [True])
        n = len(recs)
        # the same file already committed into the brand's used lane: counted once
        write(self.tmp / "runs/video-writing/fx/run1/proposals/language-used/a1/run1.json", used_file("run1", ["r1"]))
        self.assertEqual(len(E.load_used("fx", root=self.tmp)), n)
        self.assertNotIn("r2", E.used_ids("fx", avatar="a2", root=self.tmp))

    def test_creator_profile_inputs_reads_proposal(self):
        cfg = {"spec": "brands/fx/creators/SPEC.md", "home": "brands/fx/creators"}
        st = {"brand": "fx", "creator": "h1", "lane": "creator"}
        write(self.tmp / "runs/video-teardown/fx/_profiles/h1/profile.md", "proposed profile\n")
        with mock.patch.object(CP.C, "WS", self.tmp), mock.patch.object(CP, "home", lambda brand: cfg), \
                mock.patch.object(CP, "teardown_material", lambda h: ""), \
                mock.patch.object(CP, "creator_record", lambda h: ""):
            self.assertEqual(CP.inputs(st)["existing_profile"], "proposed profile\n")

    def test_creator_profile_inputs_brand_file_wins(self):
        # the accepted profile is part of the fixture, so the snapshot holds it unchanged
        write(self.tmp / "brands/fx/creators/h1/profile.md", "accepted profile\n")
        self.before = snapshot(self.tmp)
        cfg = {"spec": "brands/fx/creators/SPEC.md", "home": "brands/fx/creators"}
        st = {"brand": "fx", "creator": "h1", "lane": "creator"}
        write(self.tmp / "runs/video-teardown/fx/_profiles/h1/profile.md", "proposed profile\n")
        with mock.patch.object(CP.C, "WS", self.tmp), mock.patch.object(CP, "home", lambda brand: cfg), \
                mock.patch.object(CP, "teardown_material", lambda h: ""), \
                mock.patch.object(CP, "creator_record", lambda h: ""):
            self.assertEqual(CP.inputs(st)["existing_profile"], "accepted profile\n")

    def test_page_pick_landing_ids_reads_proposal(self):
        write(self.tmp / "runs/naming/fx/landing-proposals/briefs.json", json.dumps({"briefs": [
            {"brief": "brief-0005", "product": "x", "landing_page": {"link_ids": ["link_fx_quiz"]},
             "proposed": "2026-10-08"}]}))
        header = dict(HEADER)
        with mock.patch.object(PP, "brief_record", lambda *a: (None, None, header)):
            self.assertEqual(PP.landing_ids("fx", "brief-0005", root=self.tmp), ["link_fx_quiz"])
            self.assertEqual(PP.landing_page("fx", "brief-0005", root=self.tmp)["link_ids"], ["link_fx_quiz"])
        reg = {"landing_page": {"link_ids": ["link_fx_reg"]}}
        with mock.patch.object(PP, "brief_record", lambda *a: ("k", reg, header)):
            self.assertEqual(PP.landing_ids("fx", "brief-0005", root=self.tmp), ["link_fx_reg"])

    def test_card_words_reads_landing_page(self):
        seen = {}
        cs = types.ModuleType("copy_set")
        cs.approved = lambda *a, **k: {"id": "s1", "version": 1}

        def fill(s, page_type=None, link_id=None):
            seen.update(page_type=page_type, link_id=link_id)
            return {"primary": ["p"]}
        cs.fill = fill
        with mock.patch.dict(sys.modules, {"copy_set": cs}), \
                mock.patch.object(W.N, "brief_header", lambda *a, **k: dict(HEADER)), \
                mock.patch.object(PP, "landing_page", lambda *a, **k: {"link_ids": ["link_fx_quiz"], "page_type": "quiz"}):
            words, where = W.from_copy_set("fx", "brief-0005", repo=self.tmp)
        self.assertEqual(seen, {"page_type": "quiz", "link_id": "link_fx_quiz"})
        self.assertEqual(words["primary"], ["p"])
        self.assertEqual(where, "s1 v1 (copy set)")


if __name__ == "__main__":
    unittest.main()
