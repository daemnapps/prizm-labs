"""Free, local integration fixtures: human dispatch, packet readiness and edit-kit return."""
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

COMP = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

RS = load('filming_runsheet', COMP / 'briefs/runsheet.py')
M = load('filming_make', COMP / 'briefs/make.py')
CLI = load('filming_handoff', COMP / 'image-edit/handoff.py')
DL = load('filming_delivery', COMP / 'image-edit/delivery.py')
KEY = 'acme_widget_brief-0001'

class Chain:
    def __init__(self, record): self.record = record
    def lookup(self, *args): return KEY, self.record
    def products(self): raise AssertionError('human route touched AI product bank')
    def elements(self): raise AssertionError('human route touched AI element bank')

class Register:
    def __init__(self, row): self.row = row
    def load(self): return {'briefs': {KEY: self.row}}
    def get(self, reg, what, brand=None): return KEY, self.row

class FilmingRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.brief = self.repo / 'runs/video-writing/acme/writing/deliverable/7-final-brief.md'
        self.brief.parent.mkdir(parents=True)
        self.brief.write_text('# Demo\n\n**Film:** Hold the product at eye level.\n**Say:** Exact words.\n')
        self.row = {'brand': 'acme', 'type': 'video-creator', 'brief': 'brief-0001', 'product': 'widget', 'run': 'writing'}
        self.folder = self.repo / 'runs/handoffs/video-editor/acme' / KEY

    def build(self): return RS.build(KEY, repo=self.repo, chain=Chain(self.row))
    def pack(self):
        sheet = self.build()
        RS.pack(sheet, folder=self.folder, repo=self.repo)
        return sheet
    def return_take(self):
        sheet = self.pack()
        m = json.loads(json.dumps(sheet['return_manifest']))
        take = m['takes'][0]
        src = self.folder / 'returned' / take['file']
        src.write_bytes(b'local fixture, media inspection belongs to video-edit start')
        take.update(sha256=hashlib.sha256(src.read_bytes()).hexdigest(), accepted=True, reviewer='fixture-review',
                    roll='a', talks=True, words=[{'text':'Exact', 'start':0.1, 'end':0.5}])
        self.manifest = self.folder / 'returned/return-manifest.json'
        self.manifest.write_text(json.dumps(m))
        return m

    def test_creator_and_founder_do_not_require_ai_production(self):
        for route in ('creator', 'founder'):
            self.row['type'] = 'video-' + route
            sheet = self.build()
            self.assertTrue(sheet['execution_ready'])
            self.assertEqual(sheet['production_route'], route)
            self.assertEqual(sheet['packet_kind'], 'filming-assignment')
            self.assertEqual(sheet['steps'], [])
            self.assertEqual(sheet['takes'][0]['asset_id'], KEY + '_asset-01')
            self.assertNotIn('Higgsfield', RS.render_md(sheet))

    def test_writing_route_dispatch_and_conflicting_claims(self):
        self.row['type'] = 'video'
        (self.brief.parent.parent / 'run.json').write_text(json.dumps({'production_route':'founder'}))
        self.assertEqual(self.build()['production_route'], 'founder')
        self.row['type'] = 'video-ai'
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            self.build()

    def test_actual_cli_uses_filming_packet_and_never_video_production(self):
        H = CLI.H
        with patch.object(H, '_register', return_value=Register(self.row)), patch.object(H.P, 'repo', return_value=self.repo), \
             patch.object(H, '_runsheet_module', return_value=RS), patch.object(RS.Chain, 'lookup', return_value=(KEY, self.row)), \
             patch.object(CLI, 'video', side_effect=AssertionError('AI dispatch')), patch.object(H, 'mirror_folder', side_effect=AssertionError('Drive write')), \
             patch.object(sys, 'argv', ['handoff.py', KEY, '--brand', 'acme', '--no-drive', '--out', str(self.folder)]), contextlib.redirect_stdout(io.StringIO()):
            CLI.main()
        self.assertEqual(json.loads((self.folder/'run.json').read_text())['packet_kind'], 'filming-assignment')
        self.assertTrue((self.folder/'RETURN-MANIFEST.template.json').is_file())

    def test_founder_forward_walk_keeps_existing_shots_and_expected_takes(self):
        self.row['type'] = 'video'
        (self.brief.parent.parent/'run.json').write_text(json.dumps({'production_route':'founder'}))
        scenes = [{'id':'founder-hook', 'film':'Founder holds the existing product.', 'voice':'My exact opening.', 'expected_takes':2},
                  {'id':'founder-proof', 'film':'Use the existing overhead demonstration.', 'voice':'My exact proof.'}]
        self.brief.write_text('# Founder recording\n```json\n' + json.dumps({'scenes':scenes}) + '\n```\n')
        sheet = self.pack()
        self.assertEqual(sheet['production_route'], 'founder')
        self.assertEqual([x['scene'] for x in sheet['takes']], ['founder-hook', 'founder-proof'])
        self.assertEqual([x['instructions'] for x in sheet['takes']], [x['film'] for x in scenes])
        self.assertEqual(len(sheet['return_manifest']['takes']), 3)
        self.assertEqual(sheet['steps'], [])
        with self.assertRaisesRegex(SystemExit, 'filming assignment'): M.plan(self.folder, 1)

    def test_no_final_or_no_film_instructions_stays_draft(self):
        self.brief.write_text('# Not a filming plan yet\n')
        sheet = self.build()
        self.assertFalse(sheet['execution_ready'])
        self.assertTrue(sheet['readiness']['blockers'])
        self.brief.rename(self.brief.with_name('5-brief.md'))
        self.assertFalse(self.build()['execution_ready'])

    def test_pack_preserves_returned_manifest(self):
        self.return_take()
        saved = self.manifest.read_bytes()
        self.pack()
        self.assertEqual(self.manifest.read_bytes(), saved)

    def test_local_intake_is_idempotent_and_matches_edit_kit_contract(self):
        self.return_take()
        dry = DL.ingest_filming(self.folder, 'acme', dry_run=True)
        self.assertFalse((self.folder/'edit-kit.json').exists())
        first = DL.ingest_filming(self.folder, 'acme')
        mtime = (self.folder/'edit-kit.json').stat().st_mtime_ns
        second = DL.ingest_filming(self.folder, 'acme')
        self.assertFalse(first['unchanged']); self.assertTrue(second['unchanged'])
        self.assertEqual(mtime, (self.folder/'edit-kit.json').stat().st_mtime_ns)
        kit = json.loads((self.folder/'edit-kit.json').read_text())
        clip = kit['clips'][0]
        self.assertTrue(clip['approved']); self.assertEqual(clip['roll'], 'a')
        self.assertTrue((self.folder/clip['src']).is_file()); self.assertTrue(clip['words'])
        self.assertNotIn('higgsfield', json.dumps(kit).lower())
        editor = load('filming_editor_contract', COMP / 'video-edit/machine/run.py')
        gathered, red = editor.gather(self.folder)
        self.assertEqual(red, [])
        self.assertEqual(gathered['clips'][0]['words'], clip['words'])
        self.pack()  # A repack must not turn the same accepted return into a new kit.
        self.assertTrue(DL.ingest_filming(self.folder, 'acme')['unchanged'])

    def test_changed_bytes_unaccepted_missing_or_duplicate_returns_refuse(self):
        original = self.return_take()
        for change in ('hash', 'acceptance', 'missing', 'duplicate', 'transcript', 'path'):
            manifest = json.loads(json.dumps(original))
            if change == 'hash': manifest['takes'][0]['sha256'] = 'stale'
            if change == 'acceptance': manifest['takes'][0]['accepted'] = False
            if change == 'missing': manifest['takes'] = []
            if change == 'duplicate': manifest['takes'] *= 2
            if change == 'transcript': manifest['takes'][0]['words'] = []
            if change == 'path': manifest['takes'][0]['file'] = '../BRIEF.md'
            self.manifest.write_text(json.dumps(manifest))
            with self.subTest(change=change), self.assertRaises(DL.Refused): DL.ingest_filming(self.folder)
        self.assertFalse((self.folder/'edit-kit.json').exists())

    def test_raw_takes_cannot_be_meta_delivery(self):
        self.pack()
        row = {'label':'video-editor/' + KEY, 'brief':'brief-0001', 'key':KEY, 'role':'video-editor'}
        with patch.object(DL, 'delivered', return_value=[row]), patch.object(DL, 'repo_folder', return_value=self.folder.parent):
            with self.assertRaisesRegex(DL.Refused, 'raw filming takes'):
                DL.send('acme', KEY, run=lambda args: self.fail('sent raw takes'))

    def test_make_refuses_draft_before_network_and_preserves_ready_ai_call(self):
        folder = self.repo / 'ai'; folder.mkdir()
        step = {'n':1, 'asset':'asset.png', 'job':'pictures.generate', 'medium':'image', 'what':'test',
                'higgsfield_model':'gpt_image_2_5', 'prompt':'EXACT', 'settings':{}, 'references':[]}
        sheet = {'steps':[step], 'packet_kind':'generation', 'execution_ready':False, 'readiness':{'blockers':['draft']}}
        (folder/'run.json').write_text(json.dumps(sheet))
        with patch.object(M, 'fetch_refs', side_effect=AssertionError('network')):
            with self.assertRaisesRegex(SystemExit, 'not execution-ready'): M.plan(folder, 1)
        sheet['execution_ready'] = True
        (folder/'run.json').write_text(json.dumps(sheet))
        with patch.object(M, '_runsheet', return_value=RS):
            plan = M.plan(folder, 1)
        self.assertEqual(plan['tool'], 'generate_image'); self.assertEqual(plan['params']['prompt'], 'EXACT')
        self.pack()
        with self.assertRaisesRegex(SystemExit, 'filming assignment'): M.plan(self.folder, 1)

if __name__ == '__main__': unittest.main()
