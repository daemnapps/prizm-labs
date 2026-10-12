"""image-edit — the fixes library v3: `text` parked -> deprecated (SI-73).

The status words are components rule 6's three; the `_parked` note is
retired; v2 stays on disk untouched; every fix resolves to the same
instruction from v3 as from v2; and the one hard-coded reader,
video-production's product_fix.py, reads the newest library.

No key, no network, no PIL; writes only under `tempfile`.

    python3 tools/image-edit/tests/test_fixes_v3.py
"""
import importlib.util
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "image-production"))
import image_edit as RE  # noqa: E402
from image_edit import engine as E  # noqa: E402,F401

LIB = HERE / "library"
V2 = LIB / "fixes-v2-damon.json"
V3 = LIB / "fixes-v3-damon.json"
PRODUCT_FIX = HERE.parent / "video-production" / "machine" / "product_fix.py"
RULE_6 = {"draft", "approved", "deprecated"}


# ------------------------------------------------------------------ fixtures

def png_bytes(w=4, h=5):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def fake_workspace(tmp):
    root = Path(tmp)
    (root / "components").mkdir(parents=True, exist_ok=True)
    b = root / "brands" / "acme"
    (b / "identity").mkdir(parents=True, exist_ok=True)
    (b / "products" / "widget" / "images").mkdir(parents=True, exist_ok=True)
    (b / "identity" / "palette.md").write_text("| Ink | `#112233` |\n")
    (b / "identity" / "fonts.md").write_text("A font.\n")
    (b / "identity" / "acme-logo.png").write_bytes(png_bytes())
    (b / "products" / "images.json").write_text(json.dumps({"products": {
        "widget": {"title": "The Widget", "cutout": "products/widget/images/packshot.png"}}}))
    (b / "products" / "widget" / "images" / "packshot.png").write_bytes(png_bytes())
    (b / "ai-elements").mkdir(parents=True, exist_ok=True)
    (b / "ai-elements" / "element-facts.json").write_text(json.dumps({"elements": {}}))
    return root


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="refedit-test-")
        self.root = fake_workspace(self.tmp)
        self._old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.root)
        self.pic = Path(self.tmp) / "p152-01.png"
        self.pic.write_bytes(png_bytes(4, 5))
        self.out = Path(self.tmp) / "out"

    def tearDown(self):
        if self._old is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def req(self, **kw):
        base = {"brand": "acme", "picture": str(self.pic), "out": str(self.out)}
        base.update(kw)
        return base


def doc(path):
    return json.loads(path.read_text())


def rows(path):
    return doc(path)["fixes"]


# ------------------------------------------------------------- the library

class TestFixesV3(unittest.TestCase):
    def test_v3_is_the_library_the_engine_reads(self):
        table, path = RE.fixes()
        self.assertEqual(path.name, "fixes-v3-damon.json")

    def test_every_row_status_is_a_rule_6_word(self):
        d = doc(V3)
        for r in d["fixes"]:
            self.assertIn(r["status"], RULE_6, r["id"])
            self.assertNotIn("parked", r["status"], r["id"])
        text = next(r for r in d["fixes"] if r["id"] == "text")
        self.assertEqual(text["status"], "deprecated")
        self.assertNotIn("_parked", d)

    def test_v3_is_v2_but_the_text_status(self):
        d2, d3 = doc(V2), doc(V3)
        r2, r3 = d2["fixes"], d3["fixes"]
        self.assertEqual([r["id"] for r in r2], [r["id"] for r in r3])
        changed = []
        for a, b in zip(r2, r3):
            a_rest = {k: v for k, v in a.items() if k != "status"}
            b_rest = {k: v for k, v in b.items() if k != "status"}
            self.assertEqual(a_rest, b_rest, a["id"])
            if a["status"] != b["status"]:
                changed.append((a["id"], a["status"], b["status"]))
        self.assertEqual(changed, [("text", "parked", "deprecated")])
        for key in ("_what", "_curator", "_region"):
            self.assertEqual(d3[key], d2[key], key)
        self.assertEqual(list(d3), ["_what", "_curator", "_v3", "fixes", "_region"])
        # v2's own format: indent 1, non-ASCII kept, no trailing newline
        self.assertEqual(V3.read_text(), json.dumps(d3, indent=1, ensure_ascii=False))

    def test_v2_is_untouched(self):
        d = doc(V2)
        text = next(r for r in d["fixes"] if r["id"] == "text")
        self.assertEqual(text["status"], "parked")
        self.assertIn("_parked", d)


# ------------------------------------------------------ behaviour unchanged

class TestSameBehaviour(Base):
    def test_every_fix_resolves_the_same_from_v3_as_from_v2(self):
        """A draft or approved fix resolves identically from v2 and v3; any
        other (today `text`) is refused by both, naming the status it carries."""
        v2_table = {r["id"]: r for r in rows(V2)}
        v3_table = {r["id"]: r for r in rows(V3)}
        self.assertIn("text", v2_table)
        refused = []
        for fid, row in v2_table.items():
            args = {n: "x" for n in row.get("needs", [])}
            runs = row["status"] in ("draft", "approved")
            self.assertEqual(v3_table[fid]["status"] in ("draft", "approved"), runs, fid)
            if not runs:
                for table, status in ((v2_table, row["status"]), (None, v3_table[fid]["status"])):
                    with self.assertRaises(RE.BadRequest, msg=fid) as cm:
                        RE.resolve(self.req(fix=fid, args=args), fix_table=table)
                    self.assertIn(fid, str(cm.exception))
                    self.assertIn(status, str(cm.exception))
                refused.append(fid)
                continue
            a = RE.resolve(self.req(fix=fid, args=args), fix_table=v2_table)
            b = RE.resolve(self.req(fix=fid, args=args))
            for k in ("asked", "instruction", "checks"):
                self.assertEqual(a[k], b[k], f"{fid}: {k}")
        self.assertIn("text", refused)

    def test_product_fix_reads_the_newest_library(self):
        spec = importlib.util.spec_from_file_location("product_fix", PRODUCT_FIX)
        pf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pf)
        table, path = RE.fixes()
        self.assertEqual(pf.FIXES.name, path.name)
        product = next(r for r in json.loads(pf.FIXES.read_text())["fixes"] if r["id"] == "product")
        self.assertEqual(product, table["product"])


if __name__ == "__main__":
    unittest.main()
