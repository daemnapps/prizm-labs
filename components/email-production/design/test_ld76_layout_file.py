#!/usr/bin/env python3
"""LD-76 (email layout file): an email's section map is measured once at build and kept beside it as
<run>/klaviyo/layout.json, and adapter/sync.py reads it instead of running Chrome — proven offline.

    python3 tools/email-production/design/test_ld76_layout_file.py     (from any folder outside email-production)

Chrome is a fake on CHROME_BIN (a small script that writes one line per call to a counter file and, for --dump-dom,
prints a fixed position dump; for --screenshot, writes a PNG). The Drive is a fake reach patched over look.reach().
Stubbed: sync._gaps (it reads the brand's offer bank) and run_index (sys.modules["run_index"], it reads the run's
whole history). No key, no network, no real Chrome. sync.py is loaded by file path (its folder name has a hyphen).
PIL is stood in only when this interpreter has none, so build.py imports; test 7's shot() then skips by name.

  1  write(): layout.json is schema 1, height 900, both sections in pixels, "from" and "html" the two sha256s
  2  read(): returns it; after email.html changes -> None (and a wrong schema -> None)
  3  rows(): a fresh layout.json -> no --dump-dom call, fractions = layout / height; no file -> measured once, named
  4  stale(): design/email.json alone changes -> True, and the row says "layout_stale": true
  5  CLI: list --no-steps has no _steps; plain list still has them; steps <brand>__<label> prints them; unknown -> exit 2
  6  write_safe() on a Chrome that prints nothing -> one --no-sandbox retry, None, "layout: NOT written";
     build's step (layout_and_mirror) on the same Chrome prints it and returns, and still mirrors
  7  mirror_build(): assets/* under [runs, email-production, <brand>, <label>, klaviyo, assets], whole-email.jpg under
     [..., klaviyo]; a raising put -> "drive: NOT mirrored", never raised; shot() makes whole-email.jpg 600 wide
"""
import contextlib
import hashlib
import importlib.util
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
EM = HERE.parent
try:
    import PIL  # noqa: F401
    from PIL import Image
    HAVE_PIL = True
except ImportError:                                  # build.py and engine.py import PIL at the top
    HAVE_PIL = False
    _pil = types.ModuleType("PIL")
    for _n in ("Image", "ImageDraw", "ImageFilter"):
        setattr(_pil, _n, types.ModuleType("PIL." + _n))
        sys.modules["PIL." + _n] = getattr(_pil, _n)
    sys.modules["PIL"] = _pil
sys.path.insert(0, str(HERE))      # design/ FIRST; never tools/email-production (its email.py shadows the stdlib's)
import layout_file as LF           # noqa: E402
import look as L                   # noqa: E402

_spec = importlib.util.spec_from_file_location("sync_under_test", EM / "adapter" / "sync.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

BRAND = "zz-brand"
LABEL = "zz-brand-nov-99"
DUMP = '<html><body><pre id="pos">{"H": 900, "o": {"0": [0, 300], "1": [300, 900]}}</pre></body></html>'
HTML = ('<!doctype html><html><body><table class="wrap"><tbody>'
        '<tr data-sec="0"><td>Hello</td></tr><tr data-sec="1"><td>The letter</td></tr>'
        '</tbody></table></body></html>')
SPEC = {"brand": BRAND, "label": LABEL, "subject": "A subject", "preview": "A preview",
        "sections": [{"s": "headline", "headline": "Hello"}, {"s": "letter", "paras": ["The letter"]}]}
STEPS = [{"order": 1, "step": "plan", "name": "The send"}, {"order": 2, "step": "stage0", "name": "Triage"}]
FAKE = r'''#!%(py)s
import os, struct, sys, zlib
with open(%(count)r, "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
mode = os.environ.get("FAKE_CHROME_MODE", "dump")
if mode == "dump" and "--dump-dom" in sys.argv:
    sys.stdout.write(%(dump)r)
shot = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--screenshot=")]
if mode == "dump" and shot:
    h = int([a for a in sys.argv if a.startswith("--window-size=")][0].split(",")[1])
    w = 800                                   # headless Chrome draws wider than asked; shot() crops to 600
    raw = b"".join(b"\x00" + b"\x80\x40\x20" * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    open(shot[0], "wb").write(png)
if mode == "empty":
    sys.stderr.write("[0101/000000.000:ERROR] sandbox could not start\n")
'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(os.path.realpath(t.name))
        self.runs = self.tmp / "runs" / "email-production"
        self.run = self.runs / BRAND / LABEL
        (self.run / "design").mkdir(parents=True)
        (self.run / "klaviyo" / "assets").mkdir(parents=True)
        (self.run / "design" / "email.json").write_text(json.dumps(SPEC, indent=1))
        (self.run / "klaviyo" / "email.html").write_text(HTML)
        (self.run / "klaviyo" / "card.json").write_text(json.dumps(
            {"brand": BRAND, "label": LABEL, "date": "2026-11-01", "subjects": [{"subject": "A subject", "preview": "A preview"}]}))
        self.count = self.tmp / "chrome-calls.txt"
        fake = self.tmp / "fake-chrome"
        fake.write_text(FAKE % {"py": sys.executable, "count": str(self.count), "dump": DUMP})
        fake.chmod(0o755)
        for k, v in (("CHROME_BIN", str(fake)), ("FAKE_CHROME_MODE", "dump")):
            p = mock.patch.dict(os.environ, {k: v})
            p.start()
            self.addCleanup(p.stop)
        for p in (mock.patch.object(S, "RUNS", self.runs), mock.patch.object(S, "_gaps", lambda run: []),
                  mock.patch.dict(sys.modules, {"run_index": types.SimpleNamespace(index=lambda run: {"steps": STEPS})})):
            p.start()
            self.addCleanup(p.stop)

    def calls(self, flag=None):
        lines = self.count.read_text().splitlines() if self.count.is_file() else []
        return [ln for ln in lines if flag is None or flag in ln.split()]

    def picture(self):
        """A whole-email.jpg newer than email.html, so sync's _shot reuses it and never calls Chrome."""
        f = self.run / "klaviyo" / "whole-email.jpg"
        f.write_bytes(b"jpg")
        later = (self.run / "klaviyo" / "email.html").stat().st_mtime + 5
        os.utime(f, (later, later))
        return f

    def rows(self, **k):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = S.rows(**k)
        return got, err.getvalue()


class TestLayoutFile(Base):
    def test_1_write_keeps_the_measure_and_both_hashes(self):
        got = LF.write(self.run)
        on_disk = json.loads((self.run / "klaviyo" / "layout.json").read_text())
        self.assertEqual(on_disk, got)
        self.assertEqual(on_disk["schema"], 1)
        self.assertEqual(on_disk["height"], 900)
        self.assertEqual(on_disk["sections"], [{"i": 0, "top": 0, "bottom": 300}, {"i": 1, "top": 300, "bottom": 900}])
        self.assertEqual(on_disk["from"], sha(self.run / "design" / "email.json"))
        self.assertEqual(on_disk["html"], sha(self.run / "klaviyo" / "email.html"))
        dumps = self.calls("--dump-dom")
        self.assertEqual(len(dumps), 1)
        self.assertTrue(any(a.startswith("--user-data-dir=") for a in dumps[0].split()))   # LD-22 (Chrome in fenced runs)
        self.assertEqual([p.name for p in (self.run / "klaviyo").iterdir() if p.name.startswith(".measure")], [])

    def test_2_read_only_while_the_html_is_the_one_measured(self):
        LF.write(self.run)
        self.assertEqual(LF.read(self.run)["height"], 900)
        (self.run / "klaviyo" / "email.html").write_text(HTML.replace("Hello", "Hello again"))
        self.assertIsNone(LF.read(self.run))
        LF.write(self.run)
        f = self.run / "klaviyo" / "layout.json"
        f.write_text(f.read_text().replace('"schema": 1', '"schema": 2'))
        self.assertIsNone(LF.read(self.run))
        f.write_text("{not json")
        self.assertIsNone(LF.read(self.run))

    def test_3_rows_read_the_file_and_run_no_chrome(self):
        LF.write(self.run)
        self.count.unlink()
        self.picture()
        got, err = self.rows()
        self.assertEqual(self.calls("--dump-dom"), [])
        self.assertEqual(self.calls(), [])
        self.assertEqual(err, "")
        secs = got[0]["sections"]
        self.assertEqual([(s["i"], s["top"], s["bottom"]) for s in secs],
                         [(0, round(0 / 900, 4), round(300 / 900, 4)), (1, round(300 / 900, 4), round(900 / 900, 4))])
        self.assertEqual(secs[0]["bottom"], 0.3333)
        self.assertEqual(got[0]["ratio"], round(900 / 600, 4))
        self.assertIs(got[0]["layout_stale"], False)

    def test_3b_no_layout_file_is_measured_once_and_named(self):
        self.picture()
        got, err = self.rows()
        self.assertEqual(len(self.calls("--dump-dom")), 1)
        self.assertEqual(err, "layout: measured %s (no fresh layout.json)\n" % LABEL)
        self.assertEqual(got[0]["sections"][1]["top"], 0.3333)
        self.assertIs(got[0]["layout_stale"], False)                       # no file: nothing to be stale

    def test_4_stale_after_the_layout_alone_changes(self):
        LF.write(self.run)
        self.assertFalse(LF.stale(self.run))
        spec = dict(SPEC, subject="A new subject")
        (self.run / "design" / "email.json").write_text(json.dumps(spec, indent=1))
        self.assertTrue(LF.stale(self.run))
        self.assertIsNotNone(LF.read(self.run))                           # the email.html did not change: still read
        self.picture()
        got, _ = self.rows()
        self.assertIs(got[0]["layout_stale"], True)
        self.assertEqual(len(self.calls("--dump-dom")), 1)                  # only write()'s own call

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["sync.py"] + list(argv)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                S.main()
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def test_5_cli_list_no_steps_and_steps(self):
        LF.write(self.run)
        self.picture()
        code, out, _ = self.cli("list", "--no-steps")
        self.assertEqual(code, 0)
        rows = json.loads(out)
        self.assertEqual(len(rows), 1)
        self.assertNotIn("_steps", rows[0])
        self.assertIn("_picture", rows[0])
        code, out, _ = self.cli("list", "--brand", BRAND)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]["_steps"], STEPS)
        code, out, _ = self.cli("steps", "%s__%s" % (BRAND, LABEL))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), STEPS)
        code, out, err = self.cli("steps", "nope__x")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("nope__x", err)

    def test_6_a_failed_measure_never_fails_the_build(self):
        os.environ["FAKE_CHROME_MODE"] = "empty"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = LF.write_safe(self.run)
        self.assertIsNone(got)
        self.assertIn("layout: NOT written — RuntimeError: could not measure", out.getvalue())
        self.assertIn("sandbox could not start", out.getvalue())
        tries = self.calls("--dump-dom")
        self.assertEqual(len(tries), 2)
        self.assertNotIn("--no-sandbox", tries[0].split())
        self.assertIn("--no-sandbox", tries[1].split())
        self.assertFalse((self.run / "klaviyo" / "layout.json").exists())
        import build as B
        puts = []
        drive = types.SimpleNamespace(put=lambda files, parts: puts.append(parts) or ("api", ["x"], ""))
        out = io.StringIO()
        with mock.patch.object(L, "reach", lambda: drive), contextlib.redirect_stdout(out):
            B.layout_and_mirror(BRAND, self.run)                           # returns: nothing raised
        self.assertIn("layout: NOT written", out.getvalue())
        self.assertFalse((self.run / "klaviyo" / "whole-email.jpg").exists())   # no layout: no picture made


class TestMirrorBuild(Base):
    def setUp(self):
        super().setUp()
        k = self.run / "klaviyo"
        for n in ("s01.jpg", "s02.jpg"):
            (k / "assets" / n).write_bytes(n.encode())
        self.shot = self.picture()

    def fake(self, raises=None):
        asked = []

        def put(files, parts):
            asked.append((list(files), list(parts)))
            if raises is not None:
                raise raises
            return "api", ["Shared Assets/%s/%s" % ("/".join(parts), Path(f).name) for f in files], ""
        p = mock.patch.object(L, "reach", lambda: types.SimpleNamespace(put=put))
        p.start()
        self.addCleanup(p.stop)
        return asked

    def test_7_assets_and_the_whole_email_go_under_the_runs_klaviyo(self):
        asked = self.fake()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = LF.mirror_build(BRAND, self.run)
        base = ["runs", "email-production", BRAND, LABEL, "klaviyo"]
        k = self.run / "klaviyo"
        self.assertEqual(asked, [([k / "assets" / "s01.jpg", k / "assets" / "s02.jpg"], base + ["assets"]),
                                 ([self.shot], base)])
        self.assertEqual([g[0] for g in got], ["api", "api"])
        self.assertIn("   drive: Shared Assets/runs/email-production/%s/%s/klaviyo/assets/s01.jpg (+1 more)" % (BRAND, LABEL),
                      out.getvalue())
        self.assertIn("   drive: Shared Assets/runs/email-production/%s/%s/klaviyo/whole-email.jpg" % (BRAND, LABEL),
                      out.getvalue())

    def test_7b_an_older_whole_email_is_not_put(self):
        old = (self.run / "klaviyo" / "email.html").stat().st_mtime - 60
        os.utime(self.shot, (old, old))
        asked = self.fake()
        with contextlib.redirect_stdout(io.StringIO()):
            LF.mirror_build(BRAND, self.run)
        self.assertEqual([a[1][-1] for a in asked], ["assets"])

    def test_7c_a_failed_put_is_named_never_raised(self):
        asked = self.fake(raises=RuntimeError("quota"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = LF.mirror_build(BRAND, self.run)
        self.assertEqual(len(asked), 2)
        self.assertEqual(got, [("none", [], "RuntimeError: quota")] * 2)
        self.assertEqual(out.getvalue(), "   drive: NOT mirrored — RuntimeError: quota\n" * 2)

    @unittest.skipUnless(HAVE_PIL, "PIL is not on this interpreter: shot() crops with it")
    def test_7d_shot_makes_a_600_wide_whole_email(self):
        self.shot.unlink()
        f = LF.shot(self.run, 900)
        self.assertEqual(f, self.run / "klaviyo" / "whole-email.jpg")
        with Image.open(f) as im:
            self.assertEqual(im.size, (600, 900))
            self.assertEqual(im.format, "JPEG")
        shots = self.calls()
        self.assertEqual(len(shots), 1)
        self.assertIn("--window-size=600,902", shots[0].split())
        self.assertTrue(any(a.startswith("--user-data-dir=") for a in shots[0].split()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
