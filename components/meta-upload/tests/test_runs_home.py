"""SI-27 (upload state home): the hand-off road's plan, state and live ids land
under runs/meta-upload/<brand>/<hand-off name>/upload/; the hand-off keeps its
returned/live-ids.json pointer; a half-done hand-off resumes from its legacy
returned/upload/state.json, which is never rewritten. Stdlib + fake_meta only:
no PIL, no network, no key."""
import json, os, sys, tempfile, time, types, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))
import upload
from fake_meta import FakeMeta

REPO = upload.REPO


def _files(root, skip=()):
    out = set()
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in skip]
        out.update(os.path.join(d, f) for f in files)
    return out


class Guarded(unittest.TestCase):
    """Every test: nothing under brands/ touched, nothing new in the component
    but __pycache__ — every write goes to a temporary folder."""

    def setUp(self):
        self.start = time.time()
        self.before = _files(HERE, skip=("__pycache__",))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.T = Path(self.tmp.name)
        self.R = self.T / "runs"
        self.folder = self.T / "handoff"
        self.folder.mkdir()

    def tearDown(self):
        touched = [f for f in _files(REPO / "brands") if os.path.getmtime(f) > self.start]
        self.assertEqual(touched, [], "a file under brands/ was written")
        self.assertEqual(_files(HERE, skip=("__pycache__",)) - self.before, set(),
                         "something new was created in components/meta-upload/")

    def home(self):
        return self.R / "meta-upload" / "brand-a" / "h1" / "upload"


class RunsHome(Guarded):
    def test_upload_home_shape(self):
        got = upload.upload_home("brand-a", "h1", runs_root=self.R)
        self.assertEqual(got, self.home())
        self.assertFalse(self.R.exists())
        for brand, name in (("../x", "h1"), ("a/b", "h1"), ("", "h1"), ("brand-a", ".."),
                            ("brand-a", ".hidden"), ("brand-a", "a\\b"), ("brand-a", None)):
            with self.assertRaises(SystemExit, msg=(brand, name)):
                upload.upload_home(brand, name, runs_root=self.R)
        default = upload.upload_home("brand-a", "h1")
        self.assertEqual(default.relative_to(REPO / "runs").parts, ("meta-upload", "brand-a", "h1", "upload"))
        self.assertNotIn("brands", default.relative_to(REPO).parts)
        self.assertFalse(default.exists())

    def test_plan_lands_under_runs(self):
        (self.folder / "manifest.json").write_text(json.dumps({"name": "h1", "brand": "brand-a"}))
        p = {"handoff": "h1", "brand": "brand-a", "campaigns": {}, "ads": [], "held": []}
        with mock.patch.object(upload, "plan", return_value=p), mock.patch("builtins.print"):
            upload.run(self.folder, None, False, runs_root=self.R)
        self.assertEqual(json.loads((self.home() / "plan.json").read_text())["handoff"], "h1")
        self.assertFalse((self.folder / "returned").exists())

    def test_go_state_default_is_runs(self):
        p = {"brand": "brand-a", "handoff": "h1", "campaigns": {"C1": {"ad_sets": {}}}, "ads": []}
        upload.go(self.folder, p, {"start": "PAUSED"}, m=FakeMeta("brand-a"), runs_root=self.R, log=lambda *a: None)
        st = json.loads((self.home() / "state.json").read_text())
        self.assertIn("C1", st["campaigns"])
        self.assertFalse((self.folder / "returned" / "upload" / "state.json").exists())

    def test_go_resumes_from_legacy_state(self):
        legacy = self.folder / "returned" / "upload" / "state.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({"campaigns": {"C1": "123"}, "ad_sets": {}, "media": {}, "ads": {}}, indent=1))
        before = legacy.read_bytes()
        p = {"brand": "brand-a", "handoff": "h1", "campaigns": {"C1": {"ad_sets": {}}}, "ads": []}
        m, said = FakeMeta("brand-a"), []
        upload.go(self.folder, p, {"start": "PAUSED"}, m=m, runs_root=self.R, log=said.append)
        self.assertNotIn("campaigns", [edge for edge, _ in m.posts])
        self.assertEqual(json.loads((self.home() / "state.json").read_text())["campaigns"]["C1"], "123")
        self.assertEqual(legacy.read_bytes(), before)
        self.assertTrue(any("legacy" in s for s in said))

    def test_write_back_keeps_handoff_pointer(self):
        (self.folder / "manifest.json").write_text(json.dumps({"role": "ad-uploader", "brand": "brand-a", "name": "h1"}))
        (self.folder / "returned").mkdir()
        stub = types.ModuleType("ad_handoff_take_back")
        stub.take_back = lambda *a, **k: None
        p = {"brand": "brand-a", "handoff": "h1", "ads": [{"meta_ad_name": "A", "unit": "u", "old_name": "o"}]}
        with mock.patch.object(upload, "_take_back_module", return_value=stub):
            rows = upload.write_back(self.folder, p, {"ads": {"A": "9"}}, runs_root=self.R)
        pointer = json.loads((self.folder / "returned" / "live-ids.json").read_text())
        home = json.loads((self.home() / "live-ids.json").read_text())
        self.assertEqual(pointer, home)
        self.assertEqual(home, rows)
        self.assertEqual(home[0]["platform_id"], "9")


if __name__ == "__main__":
    unittest.main()
