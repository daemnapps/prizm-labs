"""Live definition contracts and an offline author/review/resume integration."""
import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import workflow as W
import workflow_catalog as C
import workflow_runner as R


class CatalogTests(unittest.TestCase):
    def test_every_live_recipe_has_typed_outputs_and_reviews(self):
        for path in W.PB.root().glob('*.json'):
            data = json.loads(path.read_text())
            for field in ('workflow', 'creator_workflow'):
                if data.get(field):
                    self.assertEqual(C.validate(data[field]), [], str(path) + ':' + field)

    def test_named_gate_cannot_hide_in_authoring(self):
        broken = {'steps': [{'id': 'draft', 'executor': 'agent', 'gate': 'owner', 'evidence': ['draft.md']}]}
        self.assertIn('separate review', ' '.join(C.validate(broken)))

    def test_the_only_person_stop_is_the_quote(self):
        # Owner, 2026-11-27, across all briefs: "the only thing i need to see is quotes".
        draft = {'id': 'draft', 'executor': 'agent', 'evidence': ['draft.md']}
        review = {'id': 'draft-review', 'executor': 'review', 'gate': 'owner', 'review_asset': 'draft.md'}
        self.assertIn('not the quote', ' '.join(C.validate({'steps': [draft, review]})))
        decided = {'id': 'draft-review', 'executor': 'decided', 'review_asset': 'draft.md'}
        self.assertIn('overrule', ' '.join(C.validate({'steps': [draft, decided]})))
        self.assertEqual(C.validate({'steps': [draft, dict(decided, overrule='owner')]}), [])
        early = {'steps': [dict(decided, id='early', overrule='owner'), draft]}
        self.assertIn('authoring of its actual asset', ' '.join(C.validate(early)))
        paid = {'id': 'make', 'executor': 'agent', 'paid': True, 'evidence': ['made.md']}
        self.assertIn('quote', ' '.join(C.validate({'steps': [draft, paid]})))
        quote = {'id': 'price', 'executor': 'agent', 'quote': True, 'stops_for': 'owner: the quote',
                 'evidence': ['quote.json', 'go.json']}
        self.assertEqual(C.validate({'steps': [draft, quote, paid]}), [])
        self.assertIn('not the quote', ' '.join(C.validate({'steps': [dict(draft, stops_for='owner')]})))

    def test_every_playbook_previews_with_the_quote_as_its_only_stop(self):
        for fmt in ('testimonial-montage', 'single-presenter', 'song-ad', 'narrator-montage', 'ad-series', 'micro-drama'):
            for route in ('ai', 'creator'):
                if route == 'creator' and fmt in ('micro-drama',):
                    continue
                data = C.resolve(fmt, W.WS, route)
                steps = data['workflow']['steps']
                quotes = [s['id'] for s in steps if s.get('quote')]
                self.assertEqual([x['id'] for x in data['person_stops']], quotes, fmt + ':' + route)
                self.assertLessEqual(len(quotes), 1, fmt)
                self.assertFalse([s['id'] for s in steps if s['executor'] == 'review' and not s.get('quote')], fmt)
                for s in steps:
                    if s.get('quote'):
                        self.assertIn('quote', s['stops_for'])
                    if s['executor'] == 'decided':
                        self.assertEqual(s['overrule'], 'owner', fmt + ':' + s['id'])
                        self.assertIsNone(s.get('gate'))
        # song-ad's go is held by the Higgsfield lane (drama_lane.py open/check), not a go record of its own
        song = C.resolve('song-ad', W.WS)['workflow']['steps']
        song_ids = [s['id'] for s in song]
        self.assertIn('drama_lane.py check', next(s for s in song if s['id'] == 'go-check')['run'])
        self.assertFalse([s['id'] for s in song[:song_ids.index('price')] if s.get('paid')])
        for fmt in ('single-presenter', 'narrator-montage'):
            steps = C.resolve(fmt, W.WS)['workflow']['steps']
            ids = [s['id'] for s in steps]
            price = next(s for s in steps if s.get('quote'))
            self.assertTrue(price['go']['record'].endswith('go.json'))
            self.assertIn(price['go']['record'], price['evidence'])
            for s in steps:
                if s.get('paid'):
                    self.assertGreater(ids.index(s['id']), ids.index('price'), fmt + ':' + s['id'])

    def test_every_writing_station_runs_autonomously(self):
        for path in W.PB.root().glob('*.json'):
            data = json.loads(path.read_text())
            for field in ('workflow', 'creator_workflow'):
                for s in (data.get(field) or {}).get('steps', []):
                    if s.get('brief_check') and s['executor'] == 'command':
                        self.assertIn('--autonomous', s['run'], path.name + ':' + s['id'])
                    elif s.get('brief_check'):
                        self.assertIn('--autonomous', s['does'], path.name + ':' + s['id'])
                    if s.get('id') == 'launch':
                        # Going live stays the owner's click on the approval page, outside the run.
                        self.assertIn('approval page', s['does'], path.name)
                        self.assertIn('nothing is published here', s['does'], path.name)

    def test_brand_a_families_resolve_from_actual_bank(self):
        for fmt in ('testimonial-montage', 'dramatic-continuation', 'meme'):
            data = C.resolve(fmt, W.WS)
            self.assertEqual(data['format_id'], fmt)
            self.assertEqual(data['coverage'], 'draft-reviewed-intake')
            self.assertFalse(data['proven'])
            self.assertTrue((W.WS / data['family_source']).is_file())
        # meme's builder match into sports-interview was retired 2026-11-27 (it gave meme runs the
        # press-conference stage settings): meme now runs on the shared chain, with no variant to pick.
        meme = C.resolve('meme', W.WS)
        self.assertIsNone(meme['variant'])
        self.assertEqual(meme['family'], 'default')
        self.assertEqual(meme['variant_matches'], [])
        self.assertFalse(meme['selection_required'])
        tm = C.resolve('testimonial-montage', W.WS)
        self.assertEqual(tm['variant']['id'], 'testimonial-montage')
        self.assertEqual(tm['family'], 'multi-speaker-scene')

    def test_absent_format_is_a_gap_not_inferred_from_title(self):
        for fmt in (None, '', 'triple-discount-made-up-format'):
            with self.assertRaisesRegex(ValueError, 'no format has been inferred'):
                C.resolve(fmt, W.WS)

    def test_creator_and_founder_never_receive_ai_commands(self):
        for route in ('creator', 'founder'):
            data = C.resolve('single-presenter', W.WS, route)
            self.assertEqual(data['production_route'], route)
            self.assertEqual(data['workflow']['completion'], 'reviewed-maker-package')
            self.assertFalse(any(s['executor'] == 'command' for s in data['workflow']['steps']))

    def test_song_writing_resumes_instead_of_recreating_scratch(self):
        steps = C.resolve('song-ad', W.WS)['workflow']['steps']
        write = next(s for s in steps if s['id'] == 'brief')     # the song-ad line names it brief (2026-11-27)
        self.assertEqual(write['executor'], 'command')
        # Writing costs are never quoted or capped (owner, 2026-11-25); the decision layer decides its holds.
        self.assertFalse(write.get('paid'))
        self.assertIn('--autonomous', write['run'])
        self.assertNotIn('scratch.py', write['run'])
        self.assertIn('brief_check', write)

    def test_preview_never_calls_a_runner_or_writes(self):
        with patch.object(R.subprocess, 'run', side_effect=AssertionError('preview ran a process')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(W.main(['preview', 'meme', '--production-route', 'creator']), 0)
        self.assertEqual(json.loads(out.getvalue())['production_route'], 'creator')

    def test_actual_writing_reader_rejects_legacy_flags_and_stale_bytes(self):
        module = W.HERE.parents[1] / 'video-writing/machine/writing_result.py'
        spec = importlib.util.spec_from_file_location('fixture_writing_result', module)
        writing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(writing)
        with tempfile.TemporaryDirectory() as tmp, patch.object(W, 'WS', Path(tmp)):
            run = Path(tmp) / 'writing'
            (run / 'stages').mkdir(parents=True)
            brief = run / 'stages/5-brief.md'
            brief.write_text('fixture accepted by the writing test harness')
            record = {'production_route': 'ai', 'stages': {'stage5': {'status': 'done', 'out': 'stages/5-brief.md'}},
                      'swipe_match': 'passed'}
            (run/'run.json').write_text(json.dumps(record))
            step = {'brief_check': {'run': 'writing/run.json', 'brief': 'writing/stages/5-brief.md'}}
            self.assertFalse(W.writing_passed(step, {'production_route': 'ai'}))
            # Fixture receipt is produced by the owning helper, never in a real run.
            writing.record_acceptance(run, record)
            (run/'run.json').write_text(json.dumps(record))
            self.assertTrue(W.writing_passed(step, {'production_route': 'ai'}))
            self.assertFalse(W.writing_passed(step, {'production_route': 'creator'}))
            brief.write_text('changed after the fixture acceptance')
            self.assertFalse(W.writing_passed(step, {'production_route': 'ai'}))


class LiveRecipeResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.real_root = W.WS
        self.review = R.review_module()
        self.addCleanup(setattr, W, 'WS', self.real_root)
        W.WS = self.root
        # Keep actual catalog inputs while isolating mutable workflow artifacts.
        # A dirty family may contain extra variants; fixtures must not depend on it.
        for catalog_file in ('components/video-production/formats/bank.json',
                             'components/elements/library/format.video.json'):
            source = self.real_root / catalog_file
            if source.is_file():
                target = self.root / catalog_file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
        self.records = {}
        self.addCleanup(patch.stopall)
        patch.object(R, 'review_module', return_value=self.review).start()
        # The real decision layer, its queue and settings in the temp folder (never the house queue).
        self.decide = R.decision_module()
        self.decide.QUEUE = self.root / 'calls.jsonl'
        self.decide.SETTINGS = self.root / 'settings.json'
        (self.root / 'settings.json').write_text(json.dumps({'automation': {'writing': 'auto'}}))
        self.decide.precedents = lambda: {}
        patch.object(R, 'decision_module', return_value=self.decide).start()
        patch.object(self.review, 'read_records', side_effect=lambda **kw: self.records.get(kw['item'], [])).start()
        # Isolate writing's acceptance engine; this test exercises the real catalog,
        # coordinator, review fold and git byte proof, never a model.
        patch.object(W, 'writing_passed', side_effect=lambda step, values: not step.get('brief_check') or self.accepted).start()
        self.accepted = False
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.write('brief.md', 'accepted source')
        self.write('writing/run.json', '{}')
        self.args = ['--brand', 'test', '--label', 'story']

    def write(self, ref, data):
        p = self.root / ref
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data)

    def cli(self, action, *extra):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return R.main([action, 'testimonial-montage'] + self.args + list(extra))

    def calls(self):
        q = self.root / 'calls.jsonl'
        return [json.loads(x) for x in q.read_text().splitlines()] if q.is_file() else []

    def state(self):
        return json.loads((self.root / 'runs/video-production/test/workflow-story/workflow-state.json').read_text())

    def approve(self, item, ref):
        subprocess.run(['git', 'add', ref], cwd=self.root, check=True)
        subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', item], cwd=self.root, check=True)
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root).decode().strip()
        self.records[item] = [
            {'created': '1', 'verdict': {'event': 'request', 'asset': {'warehouse': 'repo', 'ref': ref, 'at': commit}}},
            {'created': '2', 'reviewer': 'owner', 'verdict': {'event': 'verdict', 'verdict': 'approve'}},
            {'created': '3', 'verdict': {'event': 'close', 'decision': 'accepted'}}]

    def test_ai_author_review_complete_resume_and_source_change(self):
        self.exercise_author_review_resume('ai', 'production-plan')

    def test_creator_author_review_complete_resume_and_source_change(self):
        self.exercise_author_review_resume('creator', 'maker-package')

    def exercise_author_review_resume(self, production_route, package_station):
        values = ['--set', 'brief=brief.md', '--set', 'writing_run=writing', '--set', 'route=swipe', '--production-route', production_route]
        self.assertEqual(self.cli('run', *values), 2)
        self.assertEqual(self.cli('complete', '--station', 'brief'), 2)
        self.accepted = True
        self.assertEqual(self.cli('complete', '--station', 'brief'), 0)
        self.assertEqual(self.cli('complete', '--station', 'brief-review'), 2)    # never completed by hand
        self.assertEqual(self.calls(), [])
        # Quotes only: the brief review is decided by the decision layer, filed, and the run goes on to the package.
        self.assertEqual(self.cli('run'), 2)
        self.assertEqual([c['gate'] for c in self.calls()], ['brief-review'])
        self.assertEqual(self.state()['next']['station'], package_station)
        self.assertEqual(self.state()['waiting_on'], 'assistant')
        plan = 'runs/video-production/test/workflow-story/' + package_station + '.md'
        self.write(plan, 'reviewed plan, no generation')
        self.assertEqual(self.cli('complete', '--station', package_station), 0)
        self.assertEqual(self.cli('run'), 0)
        self.assertEqual([c['gate'] for c in self.calls()], ['brief-review', package_station + '-review'])
        self.assertEqual(self.cli('run'), 0)
        self.assertEqual(len(self.calls()), 2)
        # An overrule filed later reopens that station; it is reworked, never decided again as it stands.
        self.decide.set_verdict(self.calls()[-1]['id'], 'overrule', 'missing the stop point')
        self.assertEqual(self.cli('run'), 2)
        self.assertEqual(self.state()['next']['station'], package_station + '-review')
        self.assertIn('missing the stop point', self.state()['next']['reason'])
        self.assertEqual(len(self.calls()), 2)
        self.write('brief.md', 'new unapproved source')
        self.assertEqual(self.cli('run'), 2)
        self.assertEqual(self.state()['next']['station'], 'brief')

    def test_review_manifest_rejects_changed_media_bytes(self):
        self.write('clip.mp4', 'first media bytes')
        manifest = {'files': {'clip.mp4': hashlib.sha256((self.root/'clip.mp4').read_bytes()).hexdigest()}}
        self.write('review.json', json.dumps(manifest))
        self.approve('RQ-media', 'review.json')
        step = {'id': 'media-review', 'gate': 'owner', 'review_asset': 'review.json', 'review_files': ['clip.mp4']}
        self.assertIn('clip.mp4', R.review_proof(step, {'media_review': 'RQ-media'})['evidence'])
        self.write('clip.mp4', 'replacement media bytes')
        with self.assertRaisesRegex(ValueError, 'current output bytes'):
            R.review_proof(step, {'media_review': 'RQ-media'})


if __name__ == '__main__':
    unittest.main()
