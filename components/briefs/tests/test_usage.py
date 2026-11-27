import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('brief_usage', Path(__file__).parents[1] / 'usage.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class UsageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.attr = {'brief_key': 'acme_item_brief-0001', 'person': 'maker', 'stage': 'iteration',
                     'revision_id': 'acme_item_brief-0001-R01', 'account_ref': 'maker-subscription'}
        self.put('team/people/maker/identity.json', {'person': 'maker'})
        self.put('runs/handoffs/video-editor/acme/acme_item_brief-0001/delivery-state.json', {'revision_id': self.attr['revision_id']})
        self.put('team/work-allocation.json', {'people': {'maker': {'accounts': [{'id': 'maker-subscription', 'provider': 'anthropic'}]}}})
        self.put('platform/data/model-prices.json', {'models': {'model-a': {'input': 2, 'output': 10, 'cache_read': .2, 'cache_write': None}}})
        self.values = {'event.name': 'api_request', 'request_id': 'req-1', 'session.id': 's-1',
                       'model': 'model-a', 'input_tokens': 100, 'output_tokens': 20,
                       'cache_read_tokens': 200, 'cache_creation_tokens': 0, 'speed': 'normal',
                       'prompt': 'DO NOT STORE', 'user.email': 'DO NOT STORE'}

    def put(self, path, data):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))

    def payload(self, values=None):
        values = values or self.values
        return {'resourceLogs': [{'scopeLogs': [{'logRecords': [{'attributes': [
            {'key': k, 'value': {'intValue' if isinstance(v, int) else 'stringValue': v}} for k, v in values.items()]}]}]}]}

    def test_deduplication_and_token_classes(self):
        self.assertEqual(u.record_otlp(self.payload(), self.attr, self.root), 1)
        self.assertEqual(u.record_otlp(self.payload(), self.attr, self.root), 0)
        report = u.summarize(self.attr['brief_key'], self.root)
        self.assertEqual(report['tokens'], 320)
        self.assertEqual(report['requests'], 1)
        self.assertAlmostEqual(report['api_equivalent_usd'], .00044)
        event = next((self.root / 'runs/brief-usage/requests').glob('*.json')).read_text()
        self.assertNotIn('DO NOT STORE', event)

    def test_conflicting_brief_or_stage_cannot_double_count(self):
        u.record_otlp(self.payload(), self.attr, self.root)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            u.record_otlp(self.payload(), dict(self.attr, stage='storyboard'), self.root)

    def test_missing_tokens_refused_not_assumed_zero(self):
        del self.values['input_tokens']
        with self.assertRaisesRegex(ValueError, 'input_tokens'):
            u.record_otlp(self.payload(), self.attr, self.root)

    def test_unknown_and_partial_rates_are_not_totals(self):
        self.values['cache_creation_tokens'] = 50
        u.record_otlp(self.payload(), self.attr, self.root)
        report = u.summarize(self.attr['brief_key'], self.root)
        self.assertIsNone(report['api_equivalent_usd'])
        self.assertEqual(report['unpriced_tokens'], 50)
        self.assertAlmostEqual(report['priced_portion_usd'], .00044)

    def test_cache_lifetimes_use_distinct_rates_without_double_counting(self):
        self.put('platform/data/model-prices.json', {'models': {'model-a': {'input': 2, 'output': 10, 'cache_read': .2, 'cache_write': None, 'cache_write_5m': 2.5, 'cache_write_1h': 4}}})
        self.values.update(cache_creation_tokens=100, cache_creation_5m_tokens=60, cache_creation_1h_tokens=40)
        u.record_otlp(self.payload(), self.attr, self.root)
        report = u.summarize(self.attr['brief_key'], self.root)
        self.assertEqual(report['tokens'], 420)
        self.assertAlmostEqual(report['api_equivalent_usd'], .00075)

    def test_old_revision_refused(self):
        with self.assertRaisesRegex(ValueError, 'current'):
            u.record_otlp(self.payload(), dict(self.attr, revision_id='acme_item_brief-0001-R00'), self.root)

    def test_missing_usage_is_unknown(self):
        report = u.summarize(self.attr['brief_key'], self.root)
        self.assertIsNone(report['tokens'])
        self.assertIsNone(report['api_equivalent_usd'])

    def test_unrelated_events_ignored(self):
        self.values['event.name'] = 'user_prompt'
        self.assertEqual(u.record_otlp(self.payload(), self.attr, self.root), 0)

    def test_session_model_and_effort_switches_remain_distinct(self):
        self.values.update(effort='medium')
        u.record_otlp(self.payload(), self.attr, self.root)
        self.values.update(request_id='req-2', effort='high')
        u.record_otlp(self.payload(), self.attr, self.root)
        self.values.update(request_id='req-3', model='model-b')
        u.record_otlp(self.payload(), self.attr, self.root)
        report = u.summarize(self.attr['brief_key'], self.root)
        self.assertEqual(report['session_ids'], ['s-1'])
        self.assertEqual(len(report['breakdown']), 3)
        self.assertEqual({x['effort'] for x in report['breakdown']}, {'medium', 'high'})
        self.assertEqual({x['model'] for x in report['attempts']}, {'model-a', 'model-b'})
        self.assertEqual({x['request_id'] for x in report['attempts']}, {'req-1', 'req-2', 'req-3'})
        self.assertEqual(report['tokens'], 960)

    def test_unknown_person_refused(self):
        with self.assertRaisesRegex(ValueError, 'Unknown person'):
            u.record_otlp(self.payload(), dict(self.attr, person='unknown'), self.root)

    def test_no_predeclared_account_or_person_required(self):
        self.put('team/work-allocation.json', {'people': {}})
        context = {k: self.attr[k] for k in ('brief_key', 'stage', 'revision_id')}
        u.record_otlp(self.payload(), context, self.root)
        event = json.loads(next((self.root / 'runs/brief-usage/requests').glob('*.json')).read_text())
        self.assertIsNone(event['person'])
        self.assertIsNone(event['account_ref'])
        self.assertEqual(u.summarize(context['brief_key'], self.root)['tokens'], 320)

    def test_declared_context_is_not_observed_identity(self):
        u.record_otlp(self.payload(), self.attr, self.root)
        event = json.loads(next((self.root / 'runs/brief-usage/requests').glob('*.json')).read_text())
        self.assertIsNone(event['person'])
        self.assertIsNone(event['account_ref'])
        self.assertEqual(event['declared_person'], 'maker')
        self.assertEqual(event['declared_account_ref'], 'maker-subscription')

    def test_new_contributor_can_continue_same_brief_with_observed_identity(self):
        self.put('team/people/maker/identity.json', {'person': 'maker', 'emails': ['maker@example.test']})  # agnostic: ok — synthetic identity fixture
        self.values.update({'user.email': 'maker@example.test', 'user.account_uuid': 'raw-account-one'})  # agnostic: ok — synthetic identity fixture
        u.record_otlp(self.payload(), self.attr, self.root)
        self.put('team/people/editor/identity.json', {'person': 'editor', 'emails': ['second@example.test']})  # agnostic: ok — synthetic identity fixture
        self.values.update({'request_id': 'req-2', 'session.id': 's-2', 'user.email': 'second@example.test', 'user.account_uuid': 'raw-account-two'})  # agnostic: ok — synthetic identity fixture
        context = dict(self.attr, continued_from_session_id='s-1')
        u.record_otlp(self.payload(), context, self.root)
        report = u.summarize(self.attr['brief_key'], self.root)
        self.assertEqual({x['person'] for x in report['breakdown']}, {'maker', 'editor'})
        self.assertEqual(report['session_ids'], ['s-1', 's-2'])
        self.assertEqual(report['tokens'], 640)
        self.assertEqual(len({x['account_ref'] for x in report['breakdown']}), 2)
        second = next(x for x in report['attempts'] if x['session_id'] == 's-2')
        self.assertEqual(second['continued_from_session_id'], 's-1')
        self.assertEqual(second['person'], 'editor')
        stored = ''.join(p.read_text() for p in (self.root / 'runs/brief-usage/requests').glob('*.json'))
        self.assertNotIn('raw-account-', stored)
        self.assertNotIn('@example.test', stored)

    def test_continuation_cannot_claim_an_unknown_session(self):
        with self.assertRaisesRegex(ValueError, 'recorded session'):
            u.record_otlp(self.payload(), dict(self.attr, continued_from_session_id='not-recorded'), self.root)

    def test_launcher_collects_real_http_transport_without_model_call(self):
        fixture = self.root / 'sender.py'
        fixture.write_text('import os,json,urllib.request\n'
          'payload=' + repr(self.payload()) + '\n'
          'header=os.environ["OTEL_EXPORTER_OTLP_LOGS_HEADERS"].split("=",1)[1]\n'
          'req=urllib.request.Request(os.environ["OTEL_EXPORTER_OTLP_LOGS_ENDPOINT"], data=json.dumps(payload).encode(), headers={"Authorization":header,"Content-Type":"application/json"})\n'
          'assert urllib.request.urlopen(req).status==200\n')
        self.assertEqual(u.run_session([sys.executable, str(fixture)], self.attr, self.root), 0)
        report = u.summarize(self.attr['brief_key'], self.root)
        self.assertEqual(report['requests'], 1)
        self.assertEqual(report['sessions'], 1)
        session = json.loads(next((self.root/'runs/brief-usage/sessions').glob('*.json')).read_text())
        self.assertEqual(session['state'], 'process-ended')
        self.assertEqual(session['collection_errors'], [])


if __name__ == '__main__':
    unittest.main()
