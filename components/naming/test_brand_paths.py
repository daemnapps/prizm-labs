"""SI-65 (naming brand paths) — the naming tools find the workspace through
run-kit's paths.repo() and every brand file through brandpath, so a renamed
brand folder keeps working. No network, no key, nothing written outside a
temp folder; the brand is a made-up one (workspace rule 7).

    python3 components/naming/test_brand_paths.py
"""
import json, os, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N  # noqa: E402
import record as R  # noqa: E402
import delivery_rule as D  # noqa: E402
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit import paths as RK  # noqa: E402

BRAND = "zz-test-brand"


class OneRootFinder(unittest.TestCase):
    @unittest.skipIf(os.environ.get("AI_WORKSPACE"), "AI_WORKSPACE overrides the walk")
    def test_names_ws_is_run_kits_repo(self):
        self.assertEqual(Path(N.WS).resolve(), Path(RK.repo(HERE)).resolve())
        self.assertEqual((Path(N.WS) / "components" / "naming").resolve(), HERE)

    def test_the_other_tools_share_names_ws(self):
        self.assertIs(R.WS, N.WS)
        self.assertIs(D.WS, N.WS)

    def test_no_private_root_finder_left(self):
        for name in ("record.py", "selfcheck.py", "delivery_rule.py"):
            self.assertNotIn("def _workspace_root", (HERE / name).read_text(), name)
        self.assertNotIn("WS  = _workspace_root()", (HERE / "names.py").read_text())
        self.assertNotIn("HERE.parent.parent", (HERE / "delivery_rule.py").read_text())

    def test_the_seam_still_answers_from_a_runs_path(self):
        self.assertEqual(N._workspace_root(HERE / "x").resolve(), HERE.parent.parent)
        td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        with self.assertRaises(RuntimeError):
            N._workspace_root(td / "x")


class BrandPaths(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        b = self.td / "brands" / BRAND
        (b / "old-briefs").mkdir(parents=True)
        (b / "plans").mkdir(parents=True)
        (b / "FOLDERS.json").write_text(json.dumps({"briefs": ["old-briefs"], "strategy": ["plans"]}))
        (b / "old-briefs" / "briefs.json").write_text(json.dumps(
            {"briefs": [{"brief": "brief-0001", "product": "thing", "title": "moved brief"}]}))
        (b / "old-briefs" / "delivery.json").write_text(json.dumps({"watch": ["Shared Assets/x"]}))
        (b / "plans" / "angles.json").write_text(json.dumps({"angles": [
            {"id": "zz-angle", "status": "active"},
            {"id": "zz-draft-angle", "status": "draft"}]}))
        saved = (N.WS, D.WS, D.REGISTER)
        N.WS, D.WS, D.REGISTER = self.td, self.td, self.td / "no-register.json"

        def restore():
            N.WS, D.WS, D.REGISTER = saved
            shutil.rmtree(self.td, ignore_errors=True)
        self.addCleanup(restore)

    def test_briefs_follow_the_folder_map(self):
        self.assertEqual([r["title"] for r in N.brand_briefs(BRAND)], ["moved brief"])

    def test_brief_header_sees_the_moved_register(self):
        self.assertEqual(N.brief_header(BRAND, "brief-0001", "thing")["title"], "moved brief")

    def test_signed_angles_follow_the_folder_map(self):
        self.assertEqual(set(N.signed_angles(BRAND)), {N.slug("zz-angle")})

    def test_delivery_rule_reads_the_moved_folder(self):
        reg, cfg = D.load(BRAND)
        self.assertEqual(cfg, {"watch": ["Shared Assets/x"]})
        self.assertEqual([b["brief"] for b in reg["briefs"]], ["brief-0001"])

    def test_todays_layout_still_reads(self):
        plain = self.td / "brands" / "zz-plain-brand" / "briefs"
        plain.mkdir(parents=True)
        (plain / "briefs.json").write_text(json.dumps({"briefs": [{"brief": "brief-0001", "title": "plain"}]}))
        self.assertEqual([r["title"] for r in N.brand_briefs("zz-plain-brand")], ["plain"])


if __name__ == "__main__":
    unittest.main()
