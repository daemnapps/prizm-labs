"""image-edit — the no-logo note names the folder the lookup actually reads
(image-edit#7), and image_edit imports on Python 3.9 (image-edit#11).

No key, no network, no PIL. The brand-identity check reads the real
`brands/` tree and names no brand (workspace rule 7).

    /usr/bin/python3 tools/image-edit/tests/test_logo_note.py
"""
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "image-production"))
import image_edit as RE  # noqa: E402,F401
from image_edit import engine as E, paths as P  # noqa: E402


def fake_ip(logo):
    return SimpleNamespace(
        context=SimpleNamespace(build=lambda req, library=None: {"logo": logo, "product": {}}),
        purposes=lambda: {"ad": {}},
        paths=SimpleNamespace(brand=lambda b: {"identity": P.repo() / "brands" / b / "brand-identity"}))


class TestLogoNote(unittest.TestCase):

    def test_image_edit_imports_on_39(self):
        # the import at the top of this file is the test
        self.assertIn("image_edit", sys.modules)
        print(f"\n  image_edit imported on Python {sys.version_info[:2]}")

    def test_note_names_the_identity_folder(self):
        refs, notes = E._brand_refs(fake_ip([]), "zz-test-brand", ["logo"], None)
        self.assertEqual(refs, [])
        self.assertTrue(notes[0].startswith("brands/zz-test-brand/brand-identity holds no logo file"),
                        notes[0])
        self.assertNotIn("/identity holds", notes[0])

    def test_real_brands_resolve_to_brand_identity(self):
        ip = P.image_production()
        checked = 0
        for d in sorted((P.repo() / "brands").iterdir()):
            if not d.is_dir() or d.name.startswith(("_", ".")):
                continue
            identity = d / "brand-identity"
            if not identity.is_dir():
                continue
            self.assertEqual(Path(ip.paths.brand(d.name)["identity"]).resolve(), identity.resolve(),
                             d.name)
            checked += 1
        self.assertGreaterEqual(checked, 1, "no brand folder with a brand-identity/ dir to check")

    def test_logo_found_means_no_note(self):
        refs, notes = E._brand_refs(fake_ip(["/x/logo.png"]), "zz-test-brand", ["logo"], None)
        self.assertEqual(refs, ["/x/logo.png"])
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
