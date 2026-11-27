"""A prop with no kept 3D print is queued for the print (in the ad's style), never left "could not be made"."""
import json
import tempfile
import types
import unittest
from pathlib import Path

import auto_elements as AE


class PropWaitsForItsPrint(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "run.json").write_text(json.dumps({"style_id": "family-3d"}))
        (self.tmp / "frame.jpg").write_bytes(b"x")
        self.filed = []
        gate = types.SimpleNamespace(kept_print=lambda brand, name: None)
        queue = types.SimpleNamespace(file=lambda brand, what, **kw: self.filed.append(dict(kw, what=what)))
        sc = types.SimpleNamespace(canonical=lambda s: s, _set_queue=lambda: (gate, queue),
                                   formula=lambda s: "the style's words", look_reference=lambda s, run=None: {"file": "swatch.jpg"})
        self.saved = {k: getattr(AE, k) for k in ("_mod", "prop_definition", "prop_references", "_is_product", "_twin_prop")}
        real_mod = AE._mod
        AE._mod = lambda path, name: sc if name == "vm_ae_style_chain" else real_mod(path, name)
        AE.prop_definition = lambda doc, pid: {"name": "bowling pin", "look": "white with two red stripes", "size": "38 cm"}
        AE.prop_references = lambda brand, item, doc, td: [("swipe", self.tmp / "frame.jpg", "the swipe at 0:10")]
        AE._is_product = lambda doc, pid: False
        AE._twin_prop = lambda brand, item, doc, run: None

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(AE, k, v)

    def test_no_print_queues_one_in_the_ads_style(self):
        dec, why = AE.make_prop("brand", {"id": "bowling pin", "bank_id": "bowling-pin"}, {}, self.tmp, "run", False)
        self.assertEqual(dec, "")
        self.assertIn("queued for the 3D print", why)
        self.assertEqual(len(self.filed), 1)
        rq = self.filed[0]
        self.assertEqual(rq["name"], "prop-bowling-pin-family-3d")
        self.assertEqual(rq["style"], "family-3d")
        self.assertFalse(rq["people_in_it"])
        self.assertEqual(rq["look_reference"], "swatch.jpg")

    def test_dry_run_says_it_would_queue_and_files_nothing(self):
        dec, why = AE.make_prop("brand", {"id": "bowling pin", "bank_id": "bowling-pin"}, {}, self.tmp, "run", True)
        self.assertEqual(dec, "would queue its 3D print")
        self.assertEqual(self.filed, [])


if __name__ == "__main__":
    unittest.main()
