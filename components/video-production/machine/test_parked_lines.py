"""Only the lines proven end to end are live; every other family is parked (kept, out of the owner's view)."""
import contextlib
import io
import os
import unittest
from pathlib import Path

import playbook as PB
import workflow as W
import workflow_catalog as C

LIVE = {'micro-drama', 'song-ad'}


class ParkedLines(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.pop("VIDEO_PLAYBOOKS_DIR", None)

    def tearDown(self):
        if self.old is not None:
            os.environ["VIDEO_PLAYBOOKS_DIR"] = self.old

    def test_every_family_but_the_live_lines_is_parked_and_keeps_its_status(self):
        for fam in PB.families():
            fid = fam['format_id']
            if fid in LIVE:
                self.assertFalse(PB.parked(fam), fid)
            else:
                self.assertTrue(PB.parked(fam), fid)
                self.assertIn(fam['status'], PB.STATUS)
                self.assertIn('not proven end to end', fam['state'])

    def test_inventory_puts_the_live_lines_first(self):
        rows = C.inventory(W.WS)
        live = [r['format_id'] for r in rows if r['line'] == 'live']
        self.assertEqual(set(live), LIVE)
        self.assertEqual([r['format_id'] for r in rows[:len(live)]], live)
        self.assertEqual(C.line_of('meme'), 'parked')  # the shared chain alone is not a proven line

    def test_list_shows_two_lines_and_one_parked_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(W.main(['list']), 0)
        lines = out.getvalue().strip().splitlines()
        self.assertEqual({l.split()[0] for l in lines[:-1]}, LIVE)
        self.assertTrue(lines[-1].startswith('parked: '))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            W.main(['list', '--parked'])
        self.assertGreater(len(out.getvalue().splitlines()), len(lines))

    def test_parked_formats_still_resolve_for_team_tools(self):
        self.assertEqual(C.resolve('single-presenter', W.WS)['family'], 'single-presenter')


if __name__ == '__main__':
    unittest.main()
