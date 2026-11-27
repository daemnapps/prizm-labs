"""No-spend regressions for the picture hold; all child tools are intercepted."""
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_month as M
sys.path.insert(0, str(Path(__file__).resolve().parent / 'design'))
import gaps as G


class PictureHold(unittest.TestCase):
    def test_month_writer_passes_hold_to_every_picture_capable_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / 'runs/email-production/zz/zz-nov-01'
            (run / 'design').mkdir(parents=True)
            (run / 'design/email.json').write_text('{}')
            (root / 'brands/zz/email-sms').mkdir(parents=True)
            (root / 'brands/zz/email-sms/design-system.json').write_text('{}')
            calls = []
            def child(argv, **kw):
                calls.append(argv)
                return types.SimpleNamespace(returncode=0, stdout='', stderr='')
            with mock.patch.object(M, 'WORKSPACE', root), mock.patch.object(M, 'NO_IMAGES', True), mock.patch.object(M, 'DESIGN', True), mock.patch.object(M.subprocess, 'run', side_effect=child), mock.patch.object(M, 'have_picture_key', side_effect=AssertionError('must not load image credentials')):
                M.one_run('zz-nov-01', ['writer'], 'zz', io.StringIO())
            simple = next(c for c in calls if 'simple_email.py' in c)
            gaps = next(c for c in calls if 'design/gaps.py' in c)
            design = next(c for c in calls if 'design/line.py' in c)
            self.assertIn('--no-images', simple)
            self.assertIn('--no-images', gaps)
            self.assertNotIn('--pictures', design)

    def test_gap_fill_cannot_make_pictures_even_after_a_word_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / 'design').mkdir()
            spec = {'sections': [{'s': 'picture'}, {'s': 'letter'}]}
            found = {'spec': spec, 'occasion': '', 'gaps': [
                {'section': 0, 'kind': 'picture', 'why': 'missing', 'field': 'picture'},
                {'section': 1, 'kind': 'words', 'why': 'missing copy', 'field': 'text'}]}
            fake = types.SimpleNamespace(make_pictures=mock.Mock(side_effect=AssertionError('image generation forbidden')))
            with mock.patch.dict(sys.modules, {'line': fake}), mock.patch.object(G, 'find', return_value=found), mock.patch.object(G, 'offer_bank', return_value={}), mock.patch.object(G, 'sale_offer', return_value=None), mock.patch.object(G, 'patch', return_value={'ops': [{'field': 'text'}]}):
                G.fill(run, brand='zz', lk={}, make_pictures=False)
            fake.make_pictures.assert_not_called()


if __name__ == '__main__':
    unittest.main()
