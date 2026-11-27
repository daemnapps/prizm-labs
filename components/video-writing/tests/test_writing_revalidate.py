"""Frozen-brief revalidation: complete checks, no writing or source mutation."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from urllib.error import HTTPError
from test_writing_state import fixture, save, W, R, S, LAUNCH
import writing_revalidate as V


def complete(d, st, out):
    return [(name, {'passed': True}) for name in V.REQUIRED]


class Revalidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.st = fixture(self.d, 'held')
        self.st['writing_error'] = {'error_type': 'HTTPError', 'http_status': 402}
        self.st['missed_checks'] = {'checks': ['review unavailable']}
        self.st['writing_retry_budget'] = {'used': 2, 'limit': 2, 'pending': [], 'history': [{'round': 2}]}
        save(self.d, self.st)
        self.source = self.d / 'stages/5-brief.md'
        self.before = self.source.read_bytes()

    def test_legacy_held_becomes_accepted_only_after_all_checks(self):
        with mock.patch.object(W, 'run_writing', side_effect=AssertionError('writer forbidden')), \
                mock.patch.object(R, 'run_stage', side_effect=AssertionError('writer forbidden')):
            result = V.revalidate(self.d, gate_runner=complete)
        self.assertTrue(result['accepted'])
        self.assertEqual(self.source.read_bytes(), self.before)
        fresh = json.loads((self.d / 'run.json').read_text())
        self.assertEqual(fresh['writing_retry_budget'], self.st['writing_retry_budget'])
        report = json.loads((self.d / fresh['writing_revalidation']['report']).read_text())
        self.assertTrue(report['complete'])
        self.assertEqual(set(report['checks']), set(V.REQUIRED))
        self.assertEqual(report['source'], result['source'])
        self.assertTrue(S.inspect_result(self.d)['accepted'])

    def test_cli_provider_failure_stays_held_without_writer(self):
        def unavailable(*args):
            raise HTTPError('https://provider.invalid', 402, 'review credits unavailable', {}, None)
        with mock.patch.object(V, 'check_final', side_effect=unavailable), \
                mock.patch.object(W, 'run_writing', side_effect=AssertionError('writer forbidden')), \
                mock.patch.object(R, 'run_stage', side_effect=AssertionError('writer forbidden')), \
                mock.patch.object(sys, 'argv', ['writing_v2.py', str(self.d), '--revalidate']), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertFalse(W.main())
        result = json.loads(output.getvalue())
        self.assertFalse(result['ok'])
        fresh = json.loads((self.d / 'run.json').read_text())
        report = json.loads((self.d / fresh['writing_revalidation']['report']).read_text())
        self.assertEqual(report['error']['http_status'], 402)
        self.assertEqual(fresh['stages']['stage5']['status'], 'held')
        self.assertEqual(self.source.read_bytes(), self.before)
        self.assertEqual(fresh['writing_retry_budget'], self.st['writing_retry_budget'])

    def test_launcher_exits_nonzero_for_held_revalidation(self):
        with mock.patch.object(V, 'check_final', return_value=[('slots', {'passed': False})]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(LAUNCH.main([str(self.d), '--revalidate']), 1)
        self.assertEqual(self.source.read_bytes(), self.before)

    def test_missing_or_skipped_gate_never_issues_acceptance(self):
        for rows in (complete(None, None, None)[:-1],
                     [(n, {'passed': True, **({'skipped': 'disabled'} if n == 'owner' else {})}) for n in V.REQUIRED]):
            with self.subTest(rows=rows):
                result = V.revalidate(self.d, gate_runner=lambda *args: rows)
                self.assertFalse(result['accepted'])
                self.assertEqual(self.source.read_bytes(), self.before)

    def test_gate_content_edit_is_rejected_without_touching_original(self):
        def changes(d, st, out):
            out.write_text('Automatic rewritten words')
            return complete(d, st, out)
        result = V.revalidate(self.d, gate_runner=changes)
        self.assertFalse(result['accepted'])
        self.assertEqual(self.source.read_bytes(), self.before)

    def test_accepted_unchanged_revalidation_calls_no_checks(self):
        self.assertTrue(V.revalidate(self.d, gate_runner=complete)['accepted'])
        with mock.patch.object(V, 'check_final', side_effect=AssertionError('unchanged receipt must reuse')):
            self.assertTrue(V.revalidate(self.d)['accepted'])
        self.assertEqual(self.source.read_bytes(), self.before)

    def test_concurrent_owner_edit_cannot_receive_old_acceptance(self):
        def changes(d, st, out):
            self.source.write_text('New owner words')
            return complete(d, st, out)
        result = V.revalidate(self.d, gate_runner=changes)
        self.assertFalse(result['accepted'])
        self.assertEqual(self.source.read_text(), 'New owner words')

    def test_existing_gate_adapters_cover_complete_check_only_path(self):
        doc = {'scenes': [{'id': 'S1', 'voice': 'Exact words'}]}
        self.source.write_text('```json\n' + json.dumps(doc) + '\n```')
        st = json.loads((self.d / 'run.json').read_text())
        st['declared_audience'] = {'avatar': 'fixture-avatar'}
        save(self.d, st)
        def manifest(d, brand, name):
            (d / 'manifest.json').write_text(json.dumps({'core_missing': [], 'to_make': []}))
            return True, []
        modules = {
            'slotfill': SimpleNamespace(holes_of=lambda doc: []),
            'scenes': SimpleNamespace(json_block=lambda text: (doc, None)),
            'sectionfit': SimpleNamespace(plan_of=lambda out: doc, check=lambda *a, **k: {'pass': True, 'scenes': [{'id': 'S1'}]}),
            'spoken_check': SimpleNamespace(check_lines=lambda rows: []),
            'cast_match': SimpleNamespace(check=lambda *a: ([], [])),
            'model_inputs': SimpleNamespace(brief_violations=lambda doc: []),
            'storyboard_plan': SimpleNamespace(swipe_carry=lambda *a: []),
            'swipe_match': SimpleNamespace(check=lambda *a: (True, []), unstamped=lambda text: text),
            'manifest': SimpleNamespace(check=manifest)}
        viewer = SimpleNamespace(check=mock.Mock(return_value={'passed': True}))
        with mock.patch.object(V, 'module', side_effect=lambda component, name: modules[name]), \
                mock.patch.object(V, 'claims_check', return_value={'passed': True}), \
                mock.patch.dict(sys.modules, {'marketing_chain_checks': SimpleNamespace(viewer=viewer)}), \
                mock.patch.object(W, 'run_writing', side_effect=AssertionError('writer forbidden')), \
                mock.patch.object(W, 'owner_words_check', return_value=None):
            self.assertTrue(V.revalidate(self.d)['accepted'])
        viewer.check.assert_not_called()          # the viewer panel is not a gate (owner, 2026-11-06)
        self.assertEqual(self.source.read_text(), '```json\n' + json.dumps(doc) + '\n```')


    def test_snapshot_directory_links_do_not_write_through_to_source(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside)
            (external / 'receipt.json').write_text('{"before": true}')
            (self.d / 'linked-cache').symlink_to(external, target_is_directory=True)
            def reviewed(d, st, out):
                self.assertFalse((d / 'linked-cache').is_symlink())
                (d / 'linked-cache/receipt.json').write_text('{"after": true}')
                return complete(d, st, out)
            self.assertTrue(V.revalidate(self.d, gate_runner=reviewed)['accepted'])
            self.assertEqual((external / 'receipt.json').read_text(), '{"before": true}')


class ClaimsReview(unittest.TestCase):
    def test_claims_reader_checks_every_line_without_replacement_words(self):
        rows = [{'id': 'S1.voice', 'text': 'Exact source words'}]
        cf = SimpleNamespace(lines_of=lambda doc: rows, claim_rules=lambda *a: 'Only appearance claims allowed.')
        reader = SimpleNamespace(pick=mock.Mock(return_value=('fixture-check-model', None)),
                                 call=mock.Mock(return_value=json.dumps({'checked_ids': ['S1.voice'], 'violations': []})))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(V, 'module', return_value=cf), \
                mock.patch.dict(sys.modules, {'run_kit': SimpleNamespace(model=reader)}):
            result = V.claims_check({}, {'brand': 'fixture', 'product': 'device'}, Path(tmp))
        self.assertTrue(result['passed'])
        self.assertEqual(reader.pick.call_args.args[0], 'checks')
        prompt = reader.call.call_args.args[0]
        self.assertIn('Do not rewrite, propose replacement wording, or fix anything.', prompt)
        self.assertIn('Exact source words', prompt)
        reader.call.assert_called_once()

    def test_saved_request_carries_verbatim_full_sources_and_owner_confirmation(self):
        cf = V.module('video-production', 'claimfix')
        doc = {'scenes': [{'id': 'S1', 'voice': 'Refund this device.', 'on_screen': 'A forbidden assertion.'}]}
        verdict = {'checked_ids': ['S1.voice', 'S1.on_screen'], 'passed': True, 'violations': [
            {'id': 'S1.on_screen', 'words': 'A forbidden assertion.', 'rule': 'Forbidden assertion.'}]}
        reader = SimpleNamespace(pick=mock.Mock(return_value=('fixture', None)), call=mock.Mock(return_value=json.dumps(verdict)))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product = root / 'brands' / 'fixture' / 'products'
            product.mkdir(parents=True)
            (product / 'device.md').write_bytes(b'Forbidden assertion.\n')
            offer = ('Other SKU: separate terms.\r\n' + ('evidence · ' * 8000) + 'DEVICE ONLY: refund this device.\r\n').encode()
            (product / 'offer-bank.md').write_bytes(offer)
            rulings = ('# Original source pack\r\n' + ('raw source — café\r\n' * 8000) + 'OWNER CONFIRMATION: exact quote and attribution.\r\n').encode()
            evidence = root / 'review'; evidence.mkdir()
            (evidence / 'RULINGS.md').write_bytes(rulings)
            with mock.patch.object(cf, 'WS', root), mock.patch.object(V, 'module', return_value=cf), \
                    mock.patch.dict(sys.modules, {'run_kit': SimpleNamespace(model=reader)}):
                result = V.claims_check(doc, {'brand': 'fixture', 'product': 'device'}, evidence)
                rules = cf.claim_rules('fixture', 'device').encode()
            sent = reader.call.call_args.args[0].encode()
            self.assertEqual((evidence / 'claims-prompt.md').read_bytes(), sent)
            for source in (rulings, offer, rules, b'Selected brand: fixture\nSelected product: device'):
                self.assertIn(source, sent)
            context = json.loads((evidence / 'claims-context.json').read_text())
            for key, value in [('request', sent), ('rulings', rulings), ('rules', rules)]:
                self.assertEqual(context[key + '_sha256'], hashlib.sha256(value).hexdigest())
            self.assertEqual(context['request_bytes'], len(sent))
            # not a money or law rule: the judge's finding is kept as a note, never a stop (owner ruling, 2026-11-20)
            self.assertTrue(result['passed'])
            self.assertEqual(result['judge_violations'], verdict['violations'])
            self.assertEqual([n['id'] for n in result['notes']], ['S1.on_screen'])

    def test_missing_product_or_missing_product_source_holds_before_reviewer(self):
        cf = SimpleNamespace(lines_of=lambda doc: [{'id': 'S1.voice', 'text': 'Offer'}],
                             claim_rules=mock.Mock(return_value='(no claim rules on file)'))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(V, 'module', return_value=cf):
            self.assertFalse(V.claims_check({}, {'brand': 'fixture'}, Path(tmp))['passed'])
            cf.claim_rules.assert_not_called()
            self.assertFalse(V.claims_check({}, {'brand': 'fixture', 'product': 'missing'}, Path(tmp))['passed'])
            self.assertFalse((Path(tmp) / 'claims-prompt.md').exists())

    def test_partial_claims_coverage_cannot_pass(self):
        cf = SimpleNamespace(lines_of=lambda doc: [{'id': 'S1.voice', 'text': 'Exact words'}],
                             claim_rules=lambda *a: 'Rules')
        reader = SimpleNamespace(pick=lambda *a: ('fixture', None),
                                 call=lambda *a, **k: '{"checked_ids": [], "violations": []}')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(V, 'module', return_value=cf), \
                mock.patch.dict(sys.modules, {'run_kit': SimpleNamespace(model=reader)}):
            with self.assertRaisesRegex(ValueError, 'every line'):
                V.claims_check({}, {'brand': 'fixture', 'product': 'device'}, Path(tmp))


if __name__ == '__main__':
    unittest.main()
