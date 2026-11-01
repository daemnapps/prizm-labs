#!/usr/bin/env python3
"""Tests for proof.extract()'s source pick (LD-20 (proof pictures by API)):
the run cache when it holds the item, never asking Drive; else the Drive-folder
path through gdrive-creator reach.readable() — that path itself when it reads,
the API copy by name when it does not; no route at all → an error naming the
item. A video item takes the same path. Offline: every picture is a tiny one
made in a temp dir, the Drive API is a fake engine.

    /usr/bin/python3 tools/asset-index/machine/test_proof_extract_reach.py

The pictures are written as binary PPM, which Pillow reads by content whatever
the extension. An interpreter without Pillow gets a stand-in `PIL.Image` that
reads and writes the same PPM, so the routing and the cut are still asserted.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import proof  # noqa: E402
from gdrive_creator import reach as R  # noqa: E402  (proof.py put gdrive-creator on the path)

BRAND = "test-brand"


def _ppm(path, w, h, rgb):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"P6\n%d %d\n255\n" % (w, h) + bytes(rgb) * (w * h))
    return path


try:
    from PIL import Image  # noqa: F401
    PILLOW = True
except ImportError:
    PILLOW = False

    class _Im:
        """Just enough of a Pillow image for extract(): RGB pixels in rows."""
        def __init__(self, w, h, px):
            self.width, self.height, self.px = w, h, px

        @property
        def size(self):
            return (self.width, self.height)

        def convert(self, mode):
            return self

        def crop(self, box):
            x0, y0, x1, y1 = box
            return _Im(x1 - x0, y1 - y0, [row[x0:x1] for row in self.px[y0:y1]])

        def resize(self, size, _filter=None):
            w, h = size
            return _Im(w, h, [[self.px[y * self.height // h][x * self.width // w] for x in range(w)] for y in range(h)])

        def getpixel(self, xy):
            return self.px[xy[1]][xy[0]]

        def save(self, out, quality=None):
            body = b"".join(bytes(p) for row in self.px for p in row)
            pathlib.Path(out).write_bytes(b"P6\n%d %d\n255\n" % (self.width, self.height) + body)

    def _open(path):
        raw = pathlib.Path(path).read_bytes()
        magic, dims, _max, body = raw.split(b"\n", 3)
        assert magic == b"P6", "stand-in reads PPM only"
        w, h = (int(v) for v in dims.split())
        px = [[tuple(body[(y * w + x) * 3:(y * w + x) * 3 + 3]) for x in range(w)] for y in range(h)]
        return _Im(w, h, px)

    _pil = types.ModuleType("PIL")
    _image = types.ModuleType("PIL.Image")
    _image.open, _image.LANCZOS = _open, None
    _pil.Image = _image
    sys.modules["PIL"], sys.modules["PIL.Image"] = _pil, _image

from PIL import Image  # noqa: E402,F811


def _colour(path):
    im = Image.open(path).convert("RGB")
    return im.size, im.getpixel((im.width // 2, im.height // 2))


def _near(a, b, tol=6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


class _FakeEngine:
    """The gdrive-creator engine as reach.readable() uses it, offline: the item
    is a file under its parent folder, read back by id."""
    def __init__(self, rgb):
        self.rgb, self.got = rgb, []

    def service(self):
        return object()

    def folder_by_path(self, label, svc=None):
        return None if label.endswith((".jpg", ".mp4")) else "folder-id"

    def find_file(self, svc, name, parent, mime=None):
        return {"id": "file-id:" + name, "size": "1"}

    def get_media(self, file_id, dest, svc=None):
        self.got.append(file_id)
        return str(_ppm(dest, 40, 20, self.rgb))


class ExtractSource(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="proof-extract-reach-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.runs = self.tmp / "runs"
        self.root = self.tmp / "Shared drives" / "Shared Assets"     # the Drive folder, by its real last name
        self.calls = []
        # LD-47 step 1.6: no key in a test — this machine's real key file never counts.
        env = {k: v for k, v in os.environ.items() if k != "GDRIVE_SA_KEY"}
        env["KEYS_NO_FALLBACK"] = "1"
        for p in (mock.patch.dict(os.environ, env, clear=True),
                  mock.patch.object(proof.SP, "runs_root", lambda: self.runs),
                  mock.patch.object(R, "cache_root", lambda: self.tmp / "api-cache")):
            p.start(); self.addCleanup(p.stop)

    def _item(self, item_id, media="image", ext=".jpg"):
        rel = "intake/organic/%s%s" % (item_id, ext)
        e = {"id": item_id, "ext": ext, "rel": rel, "media": media, "layout": "single", "seconds": 4}
        p = mock.patch.object(proof, "load", lambda brand, label="proof": {"items": [e]})
        p.start(); self.addCleanup(p.stop)
        return self.root / "brands" / BRAND / rel

    def _spy(self, inner):
        def seam(path):
            self.calls.append(path)
            got = inner(path)
            self.calls.append(got)
            return got
        return seam

    def _extract(self, item_id, **kw):
        out = self.tmp / "out" / (item_id + ".jpg")
        return proof.extract(BRAND, item_id, ratio="1:1", out=str(out), root=self.root, **kw)

    def test_cache_hit_never_calls_readable(self):
        self._item("cached-item")
        _ppm(self.runs / BRAND / "proof" / "src" / "cached-item.jpg", 40, 20, (200, 30, 30))
        seam = mock.Mock(side_effect=AssertionError("READABLE called on a cache hit"))
        with mock.patch.object(proof, "READABLE", seam):
            out = self._extract("cached-item")
        seam.assert_not_called()
        size, rgb = _colour(out)
        self.assertEqual(size, (20, 20))
        self.assertTrue(_near(rgb, (200, 30, 30)), rgb)

    def test_miss_folder_reads_returns_that_path_no_api(self):
        folder = _ppm(self._item("folder-item"), 40, 20, (30, 200, 30))
        boom = mock.Mock(side_effect=AssertionError("the API was reached for a folder path that reads"))
        seam = self._spy(lambda p: R.readable(p, find_engine=boom))
        with mock.patch.object(proof, "READABLE", seam):
            out = self._extract("folder-item")
        boom.assert_not_called()
        self.assertEqual(self.calls, [folder, folder])
        size, rgb = _colour(out)
        self.assertEqual(size, (20, 20))
        self.assertTrue(_near(rgb, (30, 200, 30)), rgb)

    def test_miss_folder_does_not_read_cuts_the_api_copy(self):
        folder = self._item("api-item")                        # nothing at the folder path: it does not open
        E = _FakeEngine((30, 30, 200))
        seam = self._spy(lambda p: R.readable(p, find_engine=lambda: E))
        with mock.patch.object(proof, "READABLE", seam):
            out = self._extract("api-item")
        self.assertEqual(E.got, ["file-id:api-item.jpg"])
        self.assertEqual(self.calls[0], folder)
        api_copy = self.calls[1]
        self.assertNotEqual(api_copy, folder)
        self.assertTrue(str(api_copy).startswith(str(self.tmp / "api-cache")), api_copy)
        self.assertEqual(api_copy.name, "api-item.jpg")
        size, rgb = _colour(out)
        self.assertEqual(size, (20, 20))
        self.assertTrue(_near(rgb, (30, 30, 200)), rgb)

    def test_no_drive_names_the_item(self):
        self._item("lost-item")
        with mock.patch.object(proof, "READABLE", mock.Mock(side_effect=R.NoDrive("no Drive here"))):
            with self.assertRaises(SystemExit) as cm:
                self._extract("lost-item")
        self.assertIn("'lost-item'", str(cm.exception))
        self.assertIn("no Drive here", str(cm.exception))
        self.assertFalse((self.tmp / "out" / "lost-item.jpg").exists())

    def test_missing_key_names_the_item(self):
        self._item("keyless-item")
        with mock.patch.object(proof, "READABLE", mock.Mock(side_effect=SystemExit("GDRIVE_SA_KEY is not set"))):
            with self.assertRaises(SystemExit) as cm:
                self._extract("keyless-item")
        self.assertIn("'keyless-item'", str(cm.exception))
        self.assertIn("GDRIVE_SA_KEY", str(cm.exception))

    def test_video_takes_the_same_path(self):
        folder = self._item("clip-item", media="video", ext=".mp4")
        E = _FakeEngine((120, 120, 0))
        seam = self._spy(lambda p: R.readable(p, find_engine=lambda: E))
        framed = []

        def frame_at(path, t, out):
            framed.append(pathlib.Path(path))
            _ppm(out, 40, 20, tuple(Image.open(path).convert("RGB").getpixel((0, 0))))
            return True

        with mock.patch.object(proof, "READABLE", seam), mock.patch.object(proof, "frame_at", frame_at):
            out = self._extract("clip-item")
        self.assertEqual(self.calls[0], folder)
        self.assertEqual(framed, [self.calls[1]])
        self.assertEqual(E.got, ["file-id:clip-item.mp4"])
        size, rgb = _colour(out)
        self.assertEqual(size, (20, 20))
        self.assertTrue(_near(rgb, (120, 120, 0)), rgb)


if __name__ == "__main__":
    print("Pillow:", "yes" if PILLOW else "no — the PPM stand-in")
    unittest.main()
