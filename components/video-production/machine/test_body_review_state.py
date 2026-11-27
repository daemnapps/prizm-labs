"""Offline regressions: unavailable review holds media, never requests a new take."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import body_check as body
import v2_checks as memory


GOOD = json.dumps({'ok': True, 'people': [{'arms': 2, 'hands': 2}]})
BAD = json.dumps({'ok': False, 'people': [{'arms': 3, 'hands': 2}],
                  'problems': [{'what': 'Three distinct arms visible'}]})


class BodyReviewState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        self.media = self.run / 'existing.png'
        self.media.write_bytes(b'unchanged source media')
        self.probe = patch.object(body.subprocess, 'run', return_value=SimpleNamespace(returncode=0))
        self.probe.start()
        self.addCleanup(self.probe.stop)
        original = body._load
        loader = patch.object(body, '_load', side_effect=lambda name:
            memory if name == 'v2_checks' else SimpleNamespace(judge=lambda: 'fixture-model') if name == 'house' else original(name))
        loader.start()
        self.addCleanup(loader.stop)

    def test_provider_outage_requires_review_not_creative_retry(self):
        ask = Mock(side_effect=RuntimeError('provider unavailable'))
        before = self.media.read_bytes()
        result = body.check(self.run, self.media, ask=ask)
        self.assertEqual((result['state'], result['retry_kind'], result['ok']), ('unreviewed', 'review', False))
        self.assertEqual(ask.call_count, 1)
        self.assertEqual(self.media.read_bytes(), before)

    def test_malformed_cached_answer_is_invalidated_then_review_recovers(self):
        provider_answers = iter(['{"ok": true}', GOOD, GOOD])
        called = []
        def ask(run, job, prompt, files, model):
            fp = memory.fingerprint(model, prompt, *files)
            cached = memory.remembered(run, fp)
            if cached is not None:
                return cached['text'], {'remembered': True}
            called.append(job)
            text = next(provider_answers)
            memory.remember(run, fp, {'text': text, 'info': {}})
            return text, {}
        first = body.check(self.run, self.media, ask=ask)
        self.assertEqual(first['state'], 'unreviewed')
        saved = json.loads((self.run / 'v2-checks.json').read_text())
        self.assertEqual(len(saved), 1)
        self.assertTrue(next(iter(saved.values()))['invalidated'])
        second = body.check(self.run, self.media, ask=ask)
        self.assertEqual((second['state'], second['ok'], second['reads']), ('reviewed', True, 2))
        self.assertEqual(len(called), 3)
        third = body.check(self.run, self.media, ask=ask)
        self.assertTrue(third['ok'])
        self.assertEqual(len(called), 3)
        self.assertEqual(self.media.read_bytes(), b'unchanged source media')

    def test_confirmed_anatomy_defect_remains_creative_failure(self):
        ask = Mock(return_value=(BAD, {}))
        result = body.check(self.run, self.media, ask=ask)
        self.assertEqual((result['state'], result['retry_kind'], result['ok']), ('reviewed', 'creative', False))
        self.assertEqual(result['agreed'], ['arms'])
        self.assertEqual(ask.call_count, 2)

    def test_invalid_people_or_counts_cannot_be_creative_verdict(self):
        for people in ([None], [{'arms': 'many'}], [{'arms': -1}], [{'arms': True}], [{'hands': 2.5}], [{'fused': 'false'}]):
            with self.subTest(people=people):
                with self.assertRaises((ValueError, TypeError)):
                    body.verdict(json.dumps({'ok': True, 'people': people}))

    def test_unreadable_media_is_unreviewed_without_provider_call(self):
        ask = Mock()
        with patch.object(body.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            result = body.check(self.run, self.media, ask=ask)
        self.assertEqual(result['state'], 'unreviewed')
        self.assertEqual(result['retry_kind'], 'review')
        ask.assert_not_called()


class BodyReviewResume(unittest.TestCase):
    def test_body_outage_retries_review_without_a_second_generated_take(self):
        import test_v2_rulings as fixtures
        import clips_run as clips
        fixture = fixtures.ThreeTakes()
        fixture.setUp()
        try:
            made = []
            maker = fixture.make({})
            ledger = fixtures.LedgerFake()
            call = {'id': 'G01-C1', 'start_frame': 'S1-F1'}
            config = {**fixtures.CFG, 'takes': 1, 'max_tries': 3}
            def make(*args):
                made.append(args[1]['id'])
                return maker(*args)
            body_reviewer = SimpleNamespace(check=Mock(side_effect=[
                {'state': 'unreviewed', 'retry_kind': 'review', 'ok': False,
                 'problems': ['provider unavailable']},
                {'state': 'reviewed', 'retry_kind': 'creative', 'ok': True, 'problems': []}]))
            original = clips._load
            with patch.object(clips, '_load', side_effect=lambda name:
                              body_reviewer if name == 'body_check' else original(name)):
                judge = lambda *args: {'state': 'reviewed', 'score': 9, 'pass': True, 'problems': []}
                with self.assertRaisesRegex(RuntimeError, 'review unavailable'):
                    clips.make_picked(fixture.run, call, config, ledger, {}, make=make, judge=judge)
                self.assertEqual(len(made), 1)
                self.assertEqual(fixture.finished, [])
                result = clips.make_picked(fixture.run, call, config, ledger, {}, make=make, judge=judge)
            self.assertEqual(len(made), 1)
            self.assertEqual(result['picked'], 1)
            self.assertEqual(body_reviewer.check.call_count, 2)
        finally:
            fixture.tearDown()


if __name__ == '__main__':
    unittest.main()
