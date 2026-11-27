#!/usr/bin/env python3
"""SI-50 (demo out guard): make_demo.py refuses an --out inside the workspace
that is not under runs/, so a picture-review demo can never land in brands/.

    python3 test_out_guard.py

Stdlib only, no key, no network, no npx; every case works in its own temp dir.
Runs under python3 and /usr/bin/python3 (3.9). Exit 0 only if every case passes.
"""
import contextlib, io, json, os, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import make_demo  # noqa: E402

PREFIX = 'refused: --out '
STATE = ('page.json', 'slots.json', 'pic-state.json')
DEMO = ('_preview-landing.html', 'pic-index.js', 'pic-marks.js')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


class OutGuard(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.ws = os.path.join(t, 'ws')
        for d in ('brands', 'components', 'runs'):
            os.makedirs(os.path.join(self.ws, d))
        self.elsewhere = os.path.join(t, 'elsewhere')
        os.makedirs(self.elsewhere)

    def tearDown(self):
        self.tmp.cleanup()

    def refused(self, why):
        self.assertIsNotNone(why)
        self.assertTrue(why.startswith(PREFIX), why)
        self.assertIn('outside its runs/ folder', why)

    def fixture(self):
        """A built page (as test_ppr1.py case_f) and its state in the fake brands/."""
        project = os.path.join(self.tmp.name, 'project')
        write(os.path.join(project, '_site', 's', 'p', 'index.html'),
              '<html><body><img src="/s/img/a.jpg"></body></html>')
        os.makedirs(os.path.join(project, 'src', 's', 'assets'))
        state = os.path.join(self.ws, 'brands', 'zz-brand', 'picture-review')
        write(os.path.join(state, 'page.json'), json.dumps({'slug': 's', 'page': 'p', 'kit': 'k'}))
        write(os.path.join(state, 'slots.json'), '{}')
        write(os.path.join(state, 'pic-state.json'), '{}')
        return project, state

    def test_brands_is_refused(self):
        self.refused(make_demo.refuse_out(
            os.path.join(self.ws, 'brands', 'zz-brand', 'picture-review'), workspace=self.ws))

    def test_inside_but_not_runs_is_refused(self):
        self.refused(make_demo.refuse_out(os.path.join(self.ws, 'components', 'x'),
                                          workspace=self.ws))

    def test_runs_is_allowed(self):
        self.assertIsNone(make_demo.refuse_out(
            os.path.join(self.ws, 'runs', 'page-picture-review', 'zz-brand', 'l1'),
            workspace=self.ws))

    def test_outside_the_workspace_is_allowed(self):
        self.assertIsNone(make_demo.refuse_out(os.path.join(self.elsewhere, 'review'),
                                               workspace=self.ws))

    def test_a_symlink_cannot_walk_around_it(self):
        os.makedirs(os.path.join(self.ws, 'brands', 'zz-brand'))
        sneak = os.path.join(self.ws, 'runs', 'sneak')
        os.symlink(os.path.join(self.ws, 'brands', 'zz-brand'), sneak)
        self.refused(make_demo.refuse_out(sneak, workspace=self.ws))
        self.refused(make_demo.refuse_out(
            os.path.join(self.ws, 'runs', '..', 'brands', 'zz-brand'), workspace=self.ws))

    def test_build_refuses_before_writing(self):
        project, state = self.fixture()
        with mock.patch.object(make_demo, 'WORKSPACE', os.path.realpath(self.ws)):
            with self.assertRaises(SystemExit) as cm, \
                    contextlib.redirect_stdout(io.StringIO()):
                make_demo.build(project, state, out_dir=state, run_build=False)
        self.assertTrue(str(cm.exception.code).startswith(PREFIX), cm.exception.code)
        for f in DEMO:
            self.assertFalse(os.path.lexists(os.path.join(state, f)), f'{f} written into brands/')
        self.assertEqual(sorted(os.listdir(state)), sorted(STATE))

    def test_build_writes_under_runs(self):
        project, state = self.fixture()
        out = os.path.join(self.ws, 'runs', 'page-picture-review', 'zz-brand', 'l1')
        with mock.patch.object(make_demo, 'WORKSPACE', os.path.realpath(self.ws)):
            with contextlib.redirect_stdout(io.StringIO()):
                make_demo.build(project, state, out_dir=out, run_build=False)
        for f in DEMO + ('pic-state.json',):
            self.assertTrue(os.path.isfile(os.path.join(out, f)), f'{f} missing from out')
        self.assertTrue(os.path.islink(os.path.join(out, 'pic-state.json')),
                        'out/pic-state.json is not a link')


if __name__ == '__main__':
    unittest.main()
