"""SI-48 (teardown drops home): the Meta readers find a drop at its new home,
runs/image-teardown/<brand>/<batch>/deliverable, first and at the legacy
runs/image-edit/ home second. Stdlib only: no PIL, no network, no key; temp
folders only."""
import sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))
import feed_image, drop


class FeedImage(unittest.TestCase):
    def test_feed_image_reads_both_homes(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self.assertEqual(feed_image.deliverables("zz-brand", "d1", repo=tmp), [])
            old = tmp / "runs/image-edit/zz-brand/d1/deliverable"
            old.mkdir(parents=True)
            self.assertEqual(feed_image.deliverables("zz-brand", "d1", repo=tmp), [old])
            new = tmp / "runs/image-teardown/zz-brand/d1/deliverable"
            new.mkdir(parents=True)
            self.assertEqual(feed_image.deliverables("zz-brand", "d1", repo=tmp), [new])

    def test_provenance_names_the_machine(self):
        src = (HERE / "feed_image.py").read_text()
        self.assertNotIn('"tool": "image-edit"', src)


class Deliverable(unittest.TestCase):
    def test_deliverable_for_prefers_the_new_home(self):
        m = {"brand": "zz-brand", "batch": "d1"}
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            with mock.patch.object(drop, "REPO", tmp):
                self.assertEqual(drop._deliverable_for(m),
                                 tmp / "runs/image-teardown/zz-brand/d1/deliverable")
                old = tmp / "runs/image-edit/zz-brand/d1/deliverable"
                old.mkdir(parents=True)
                self.assertEqual(drop._deliverable_for(m), old)
                new = tmp / "runs/image-teardown/zz-brand/d1/deliverable"
                new.mkdir(parents=True)
                self.assertEqual(drop._deliverable_for(m), new)


if __name__ == "__main__":
    unittest.main()
