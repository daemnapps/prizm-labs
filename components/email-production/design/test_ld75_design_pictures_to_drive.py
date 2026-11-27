#!/usr/bin/env python3
"""LD-75 (design pictures to Drive): every picture the design line makes (or
reuses, or remakes) is put to the run's Drive mirror,
Shared Assets/runs/email-production/<brand>/<label>/media/<the layout's name>,
so look.py's run: fallback (LD-34 (run pictures from Drive)) finds it on any
other Mac — proven offline.

    cd tools/email-production/design && python3 test_ld75_design_pictures_to_drive.py

The Drive is a fake reach patched over look.reach(); no key, no network, no
Google package, no image engine. PIL is stood in only when this interpreter
has none (line.py imports engine.py, which imports it; nothing here draws).
Stdlib only, 3.9.

  1  mirror() on route api: put once with media/<name> and parts
     [runs, email-production, <brand>, <label>, media]; put's answer back; the placed path printed
  2  a path outside media/ whose name is in media/ -> the media/ file is put; none there -> the path itself
  3  put answers ("none", [], SKIP ... NoDrive) -> returned, printed as NOT mirrored
  4  put raises RuntimeError -> ("none", [], "RuntimeError: quota"), printed, never raised
  5  put raises SystemExit -> it propagates
  6  make_pictures on a reused picture calls mirror once with that path; the spec's photo is run:media/<name>
  7  what mirror put, look.py on a clean run folder reads back from the same fake Drive
"""
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
try:
    import PIL  # noqa: F401
except ImportError:
    PIL = types.ModuleType("PIL")
    for _n in ("Image", "ImageDraw", "ImageFilter"):
        setattr(PIL, _n, types.ModuleType("PIL." + _n))
        sys.modules["PIL." + _n] = getattr(PIL, _n)
    sys.modules["PIL"] = PIL
sys.path.insert(0, str(HERE))      # design/ FIRST; never tools/email-production (its email.py shadows the stdlib's)
import look as L                   # noqa: E402
import picture_record as PR        # noqa: E402

BRAND = "zz-brand"
LABEL = "zz-brand-nov-99"
NAME = "zz-brand-nov-99-pabc12345-01.png"
PARTS = ["runs", "email-production", BRAND, LABEL, "media"]
SKIP = "SKIP the rest of the Drive mirror — NoDrive: no key"


class NoDrive(Exception):
    pass


class TestMirror(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(os.path.realpath(t.name))
        self.run = self.tmp / "runs" / "email-production" / BRAND / LABEL
        (self.run / "media").mkdir(parents=True)

    def fake(self, answer=None, raises=None):
        asked = []

        def put(files, parts):
            asked.append((list(files), list(parts)))
            if raises is not None:
                raise raises
            return answer
        p = mock.patch.object(L, "reach", lambda: types.SimpleNamespace(put=put, NoDrive=NoDrive))
        p.start()
        self.addCleanup(p.stop)
        return asked

    def mirror(self, path):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = PR.mirror(BRAND, self.run, path)
        return got, out.getvalue()

    def test_1_route_api_puts_the_layouts_file_under_the_runs_media(self):
        f = self.run / "media" / NAME
        f.write_bytes(b"p")
        placed = ["Shared Assets/runs/email-production/%s/%s/media/%s" % (BRAND, LABEL, NAME)]
        asked = self.fake(("api", placed, ""))
        got, printed = self.mirror(f)
        self.assertEqual(asked, [([f], PARTS)])
        self.assertEqual(got, ("api", placed, ""))
        self.assertEqual(printed, "   drive: Shared Assets/runs/email-production/zz-brand/zz-brand-nov-99/media/%s\n" % NAME)

    def test_2_the_media_copy_wins_else_the_path_given(self):
        gen = self.run / "media" / "generated" / NAME
        gen.parent.mkdir()
        gen.write_bytes(b"g")
        asked = self.fake(("api", ["x"], ""))
        self.mirror(gen)
        self.assertEqual(asked[-1][0], [gen])                      # no media/ copy: the path itself
        (self.run / "media" / NAME).write_bytes(b"m")
        self.mirror(gen)
        self.assertEqual(asked[-1][0], [self.run / "media" / NAME])  # the exact file the layout names
        self.assertEqual(asked[-1][1], PARTS)

    def test_3_no_route_is_returned_and_named(self):
        f = self.run / "media" / NAME
        f.write_bytes(b"p")
        self.fake(("none", [], SKIP))
        got, printed = self.mirror(f)
        self.assertEqual(got, ("none", [], SKIP))
        self.assertEqual(printed, "   drive: NOT mirrored — %s\n" % SKIP)

    def test_4_a_failed_put_is_named_never_raised(self):
        f = self.run / "media" / NAME
        f.write_bytes(b"p")
        self.fake(raises=RuntimeError("quota"))
        got, printed = self.mirror(f)
        self.assertEqual(got[:2], ("none", []))
        self.assertIn("RuntimeError", got[2])
        self.assertIn("quota", got[2])
        self.assertEqual(printed, "   drive: NOT mirrored — %s\n" % got[2])

    def test_5_systemexit_stays_loud(self):
        f = self.run / "media" / NAME
        f.write_bytes(b"p")
        self.fake(raises=SystemExit("no google-api-python-client"))
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                PR.mirror(BRAND, self.run, f)

    def test_6_make_pictures_mirrors_a_reused_picture(self):
        import line as LINE
        todo, brief = "a jar on a sink", ""
        (self.run / "design").mkdir()
        (self.run / "design" / "email.json").write_text(json.dumps({"sections": [{"todo": todo, "brief": brief, "use": "story"}]}))
        label = "%s-p%s" % (LABEL, hashlib.sha1((todo + brief).encode()).hexdigest()[:8])
        done = self.run / "media" / ("%s-01.png" % label)
        done.write_bytes(b"p")

        def make(req):
            raise AssertionError("the image engine was asked")
        ip = types.SimpleNamespace(make=make)
        pins = types.SimpleNamespace(query_for=lambda *a: "q", for_picture=lambda *a: [])
        calls = []
        with mock.patch.dict(sys.modules, {"image_production": ip, "pins": pins}), \
                mock.patch.object(PR, "mirror", lambda *a: calls.append(a) or ("api", ["x"], "")), \
                contextlib.redirect_stdout(io.StringIO()):
            LINE.make_pictures(BRAND, self.run, {})
        self.assertEqual(calls, [(BRAND, self.run, done)])
        spec = json.loads((self.run / "design" / "email.json").read_text())
        self.assertEqual(spec["sections"][0]["photo"], "run:media/" + done.name)

    def test_7_look_reads_back_on_a_clean_run_what_mirror_put(self):
        drive = {}

        def put(files, parts):
            placed = []
            for f in files:
                label = "Shared Assets/%s/%s" % ("/".join(parts), Path(f).name)
                drive[label] = Path(f).read_bytes()
                placed.append(label)
            return "api", placed, ""

        def readable(label):
            if label not in drive:
                raise NoDrive(label)
            out = self.tmp / "cache" / Path(label).name
            out.parent.mkdir(exist_ok=True)
            out.write_bytes(drive[label])
            return out
        p = mock.patch.object(L, "reach", lambda: types.SimpleNamespace(put=put, readable=readable, NoDrive=NoDrive))
        p.start()
        self.addCleanup(p.stop)
        f = self.run / "media" / NAME
        f.write_bytes(b"picture")
        with contextlib.redirect_stdout(io.StringIO()):
            PR.mirror(BRAND, self.run, f)
        clean = self.tmp / "other-mac" / LABEL                    # the same run label, nothing on disk
        clean.mkdir(parents=True)
        got = L.Look(BRAND, {}, clean).path("run:media/" + NAME)
        self.assertNotEqual(got, clean / "media" / NAME)
        self.assertEqual(Path(got).read_bytes(), b"picture")


if __name__ == "__main__":
    unittest.main(verbosity=2)
