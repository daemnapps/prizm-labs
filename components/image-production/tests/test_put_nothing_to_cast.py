"""picture_sets.put: a kept print needs the product casting sheet as its reference, except a set that has nothing to cast
(a prop set, or a set whose request names no product and no person; 2026-11-21, a right print of an empty column was
refused). Nothing is called."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(str(Path(__file__).resolve().parents[1]))
import picture_sets as PS  # noqa: E402


class NothingToCast(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cast-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = mock.patch.object(PS, "home", lambda brand, name: self.tmp / "sets" / name)
        p.start()
        self.addCleanup(p.stop)
        self.png = self.tmp / "p.png"
        self.png.write_bytes(b"png")

    def put(self, name, req):
        d = self.tmp / "sets" / name
        d.mkdir(parents=True)
        (d / "set.json").write_text(json.dumps({"print": {"reference": "a blockout render, no references"}}))
        with mock.patch.object(PS, "_nothing_to_cast", lambda b, n: PS_nothing(req)):
            return PS.put("b", name, printed=str(self.png), note="kept: right")

    def test_a_set_with_no_product_and_no_person_is_kept(self):
        self.put("empty-column", {"products": [], "cast": []})
        self.assertTrue((self.tmp / "sets" / "empty-column" / "set.json").is_file())

    def test_a_set_with_a_product_still_needs_its_casting_sheet(self):
        with self.assertRaises(ValueError):
            self.put("with-product", {"products": ["tube"], "cast": []})

    def test_the_request_is_read_for_products_and_cast(self):
        q = mock.MagicMock()
        q.read.side_effect = lambda b, rid: {"a": {"products": [], "cast": []}, "b": {"products": [], "cast": ["yai"]},
                                             "c": {"id": "c"}}.get(rid)
        with mock.patch.dict(sys.modules, {"image_production.set_queue": q}), \
                mock.patch("image_production.set_queue", q, create=True):
            import image_production
            with mock.patch.object(image_production, "set_queue", q, create=True):
                self.assertTrue(PS._nothing_to_cast("x", "a"))
                self.assertFalse(PS._nothing_to_cast("x", "b"))        # a person is cast
                self.assertFalse(PS._nothing_to_cast("x", "c"))        # a request that never said
                self.assertFalse(PS._nothing_to_cast("x", "none"))


    def test_a_print_filed_wrong_releases_its_printing_hold(self):
        q = mock.MagicMock()
        q.read.return_value = {"printing": {"generation": "g"}}
        import image_production
        with mock.patch.object(image_production, "set_queue", q, create=True), \
                mock.patch.dict(sys.modules, {"image_production.set_queue": q}):
            d = self.tmp / "sets" / "wrong"; d.mkdir(parents=True)
            PS.put("b", "wrong", printed=str(self.png), note="wrong: the label is garbled")
        q.printing.assert_called_once()
        self.assertIn("filed not kept", q.printing.call_args.kwargs["clear"])


def PS_nothing(req):
    return "products" in req and not req["products"] and not req.get("cast")


if __name__ == "__main__":
    unittest.main()
