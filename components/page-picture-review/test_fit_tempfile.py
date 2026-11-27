#!/usr/bin/env python3
"""SI-130 (fit temp file): each fit stages its crop in its own temp file.

Offline, stdlib only: subprocess.run is replaced by a fake that records argv,
writes a few bytes where ffmpeg is asked to write the ppm (and where cjpeg is
asked to write the jpeg), so no ffmpeg, cjpeg or real image is needed.

    /usr/bin/python3 components/page-picture-review/test_fit_tempfile.py
"""
import contextlib, importlib.util, io, os, shutil, subprocess, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('fit', os.path.join(HERE, 'fit.py'))
fit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fit)

OLD = '/tmp/fit-stage.ppm'


class FakeRun:
    """Stands in for subprocess.run; `cjpeg_rc`/`ffmpeg_rc` pick the outcome."""

    def __init__(self, ffmpeg_rc=0, cjpeg_rc=0):
        self.ffmpeg_rc, self.cjpeg_rc = ffmpeg_rc, cjpeg_rc
        self.calls = []
        self.ppm_at_cjpeg = []        # did the stage file exist when cjpeg read it

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        if argv[0] == 'ffmpeg':
            with open(argv[-1], 'wb') as f:
                f.write(b'P6\n1 1\n255\n\x00\x00\x00')
            rc = self.ffmpeg_rc
        elif argv[0] == 'cjpeg':
            self.ppm_at_cjpeg.append(os.path.exists(argv[-1]))
            rc = self.cjpeg_rc
            if not rc:
                out = argv[argv.index('-outfile') + 1]
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, 'wb') as f:
                    f.write(b'\xff\xd8jpeg')
        else:
            raise AssertionError(f'unexpected command {argv[0]}')
        return subprocess.CompletedProcess(argv, rc, stdout='', stderr='boom' if rc else '')

    def ppm_paths(self):
        return [c[-1] for c in self.calls if c[0] == 'ffmpeg']

    def cjpeg_inputs(self):
        return [c[-1] for c in self.calls if c[0] == 'cjpeg']


class StagePath(unittest.TestCase):

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        self.cfg = {'kit': 'kit', 'slug': 'slug', 'assets_subdir': 'img'}
        desktop = {1: {'target': (100, 50), 'anchor': (0.5, 0.5), 'note': ''},
                   2: {'mode': 'native', 'min': [10, 10], 'note': ''}}
        slots = {'1': {'desktop': 'one.jpg'}, '2': {'desktop': 'two.jpg'}}
        for target, value in (('load_state', (desktop, {}, slots)),
                              ('page_config', self.cfg),
                              ('probe', (200, 80))):
            p = mock.patch.object(fit, target, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def run_fit(self, slot, fake):
        out = io.StringIO()
        with mock.patch.object(fit.subprocess, 'run', fake), contextlib.redirect_stdout(out):
            ok = fit.fit_one('/nowhere/master.png', slot, self.repo, '/nowhere/state')
        return ok, out.getvalue()

    def check_paths(self, fake, n):
        paths = fake.ppm_paths()
        self.assertEqual(len(paths), n)
        for p in paths:
            self.assertNotEqual(p, OLD)
            self.assertTrue(p.endswith('.ppm'), p)
            self.assertFalse(os.path.exists(p), f'stage file left behind: {p}')
        self.assertEqual(len(set(paths)), n, 'two calls shared a stage file')
        return paths

    def test_cover_two_calls_distinct_and_removed(self):
        fake = FakeRun()
        r1 = self.run_fit(1, fake)
        r2 = self.run_fit(1, fake)
        self.assertEqual(r1[0], True)
        self.assertEqual(r2[0], True)
        self.assertIn('      wrote one.jpg  0 KB', r1[1])
        paths = self.check_paths(fake, 2)
        self.assertEqual(fake.cjpeg_inputs(), paths)
        self.assertEqual(fake.ppm_at_cjpeg, [True, True])

    def test_native_two_calls_distinct_and_removed(self):
        fake = FakeRun()
        r1 = self.run_fit(2, fake)
        r2 = self.run_fit(2, fake)
        self.assertEqual(r1[0], True)
        self.assertEqual(r2[0], True)
        self.assertIn('      wrote two.jpg  0 KB', r1[1])
        paths = self.check_paths(fake, 2)
        self.assertEqual(fake.cjpeg_inputs(), paths)
        self.assertEqual(fake.ppm_at_cjpeg, [True, True])

    def test_cover_cjpeg_failure_removes_stage(self):
        fake = FakeRun(cjpeg_rc=1)
        ok, out = self.run_fit(1, fake)
        self.assertIs(ok, False)
        self.assertEqual(out.splitlines()[-1], '      cjpeg failed: boom')
        self.check_paths(fake, 1)
        self.assertEqual(fake.ppm_at_cjpeg, [True])

    def test_native_cjpeg_failure_removes_stage(self):
        fake = FakeRun(cjpeg_rc=1)
        ok, out = self.run_fit(2, fake)
        self.assertIs(ok, False)
        self.assertEqual(out.splitlines()[-1], '      cjpeg failed')
        self.check_paths(fake, 1)

    def test_ffmpeg_failure_removes_stage(self):
        for slot, msg in ((1, '      ffmpeg failed: boom'), (2, '      ffmpeg failed')):
            fake = FakeRun(ffmpeg_rc=1)
            ok, out = self.run_fit(slot, fake)
            self.assertIs(ok, False)
            self.assertEqual(out.splitlines()[-1], msg)
            self.assertEqual([c[0] for c in fake.calls], ['ffmpeg'])
            self.check_paths(fake, 1)


if __name__ == '__main__':
    unittest.main()
