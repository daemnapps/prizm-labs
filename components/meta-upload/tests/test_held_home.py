"""SI-54 (held calls home): the cleared headline-audit calls live at
runs/meta-upload/<brand>/held/held.json, not in the component; build.py reads the
brand's file (blocked(brand)) and image-production's static/queue/triage.py writes
there (meta-upload#14). Stdlib only: no PIL, no network, no key."""
import importlib.util, inspect, json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))
import build


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class HeldHome(unittest.TestCase):

    def test_held_file_is_per_brand_under_runs(self):
        self.assertEqual(build.held_file("zz-brand"),
                         build.REPO / "runs/meta-upload/zz-brand/held/held.json")

    def test_cleared_calls_ship_and_the_rest_block(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            _write(tmp / "queue" / "headline-audit.json",
                   {"ad-a": {"verdict": "MISMATCH", "why": "x. y"},
                    "ad-b": {"verdict": "MISMATCH", "why": "z"}})
            _write(tmp / "runs/meta-upload/zz-brand/held/held.json",
                   {"calls": {"ad-a": {"call": "bad-call"}}})
            with mock.patch.object(build, "REPO", tmp), \
                 mock.patch.object(build, "QUEUE", tmp / "queue"):
                mine = build.blocked("zz-brand")
                other = build.blocked("other-brand")
        self.assertIn("ad-b", mine)
        self.assertNotIn("ad-a", mine)
        self.assertIn("ad-a", other)
        self.assertIn("ad-b", other)

    def test_the_component_keeps_no_brand_calls(self):
        self.assertFalse((build.HERE / "held.json").exists())
        self.assertNotIn('HERE / "held.json"', inspect.getsource(build))

    def test_the_moved_file_is_whole(self):
        found = sorted(build.REPO.glob("runs/meta-upload/*/held/held.json"))
        self.assertEqual(len(found), 1, found)
        held = found[0]
        brand = held.parent.parent.name
        calls = json.loads(held.read_text())["calls"]
        self.assertEqual(len(calls), 11)
        for name in calls:
            self.assertTrue(name.startswith(brand + "-"), name)
        run = json.loads((held.parent / "run.json").read_text())
        self.assertEqual(run["machine"], "meta-upload")
        self.assertEqual(run["label"], "held")

    def test_triage_writes_the_brand_file(self):
        path = build.REPO / "tools/image-production/static/queue/triage.py"
        spec = importlib.util.spec_from_file_location("triage_si54", path)
        triage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(triage)
        self.assertEqual(triage.HELD, build.REPO / "runs/meta-upload" / triage.RUNS.name
                         / "held" / "held.json")


if __name__ == "__main__":
    unittest.main()
