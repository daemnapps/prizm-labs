"""A hand-request hash is not a provider status code."""
import sys
import json
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP / 'machine'))
sys.path.insert(0, str(COMP.parent / 'video-teardown/machine'))
import writing_v2 as W
import run as R


class HandPromptRetry(unittest.TestCase):
    def test_status_like_request_hash_is_not_retried(self):
        for digest in ('ad5004f7abcd0', 'ab503ab12abc'):
            with self.subTest(digest=digest):
                error = W.HandPromptMismatch('session hand held: read hand/stage.request-' + digest + '.prompt.md')
                work = Mock(side_effect=error)
                with patch.object(R.time, 'sleep') as sleep, patch.object(R, 'say'):
                    with self.assertRaises(W.HandPromptMismatch) as caught:
                        R.with_retry(work, 'fixture hand request')
                self.assertIs(caught.exception, error)
                self.assertEqual(work.call_count, 1)
                sleep.assert_not_called()
                self.assertFalse(R.transient(error))

    def test_actual_missing_answer_path_with_status_like_directory_stops_once(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            (d / 'stages').mkdir()
            (d / 'prompts').mkdir()
            (d / 'run.json').write_text('{}')
            hand = d / 'corrective-build-ad5004f7'
            out = d / 'stages/4g-spice.md'
            limited = SimpleNamespace(stdout=json.dumps({'is_error': True, 'result': 'weekly limit'}), stderr='')
            with patch.object(W, '_HAND', [str(hand)]), \
                 patch.object(W, '_CURRENT', {'key': 'stage4g'}), \
                 patch.object(W, 'slim', return_value=('complete configured request', [])), \
                 patch.object(W, 'prior_language_block', return_value=''), \
                 patch.object(R, '_claude_run', return_value=limited) as provider, \
                 patch.object(R.time, 'sleep') as sleep, patch.object(R, 'say'):
                with self.assertRaises(W.SessionHandRequired) as caught:
                    R.with_retry(lambda: W.claude_v2('complete configured request', out), 'fixture waiting')
            self.assertNotIsInstance(caught.exception, W.HandPromptMismatch)
            self.assertEqual(provider.call_count, 1)
            sleep.assert_not_called()
            self.assertEqual((hand / '4g-spice.prompt.md').read_text(), 'complete configured request')
            self.assertFalse((hand / '4g-spice.md').exists())

    def test_real_provider_503_still_uses_existing_retry(self):
        work = Mock(side_effect=[RuntimeError('provider returned HTTP 503 unavailable'), 'complete'])
        with patch.object(R.time, 'sleep') as sleep, patch.object(R, 'say'):
            self.assertEqual(R.with_retry(work, 'fixture provider', wait=7), 'complete')
        self.assertEqual(work.call_count, 2)
        sleep.assert_called_once_with(7)


if __name__ == '__main__':
    unittest.main()
