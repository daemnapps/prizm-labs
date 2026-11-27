"""Grouped jobs preserve independent acceptance and refresh reference redirects safely."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import group as G
import stage_handoff as SH
import pull


class Groups(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.folder = self.root / 'runs/handoffs/video-producer/test/test_product_brief-0001'
        self.folder.mkdir(parents=True)
        self.man = {'variants': []}
        for i in range(3):
            vid = 'A' + str(i + 1);f = self.folder / 'variants' / vid
            (f / 'writing').mkdir(parents=True);(f / 'BRIEF.md').write_text('Distinct brief ' + vid)
            h = G.digest(f / 'BRIEF.md')
            (f / 'writing/result.json').write_text(json.dumps({'accepted': True, 'source': {'sha256': h}}))
            self.man['variants'].append({'id': vid, 'source_run': 'source-' + vid, 'brief_sha256': h, 'writing_accepted': True})

    def test_build_keeps_accepted_variants_exact_and_adds_delivery_only_to_review(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'video-writing/machine'))
        import writing_result
        reg = self.root / 'components/image-teardown/briefs.json';reg.parent.mkdir(parents=True)
        key = self.folder.name
        reg.write_text(json.dumps({'briefs': {key: {'brand': 'test', 'product': 'product', 'type': 'video-ai'}}}))
        bank = self.root / 'components/video-production/formats/bank.json';bank.parent.mkdir(parents=True)
        bank.write_text(json.dumps({'formats': [{'id': 'demonstration', 'status': 'draft'}]}))
        variants = []
        hashes = {}
        for i in range(3):
            label = 'source-' + str(i);src = self.root / 'runs/video-teardown/_work' / label
            (src / 'stages').mkdir(parents=True)
            (src / 'stages/5-brief.md').write_text('Accepted fixture ' + label)
            (src / 'source.mp4').write_bytes(b'fixture swipe')
            (src / 'poster.jpg').write_bytes(b'fixture poster')
            (src / 'language-exposure.json').write_text('{\"queries\":{\"q\":[\"source-7\"]}}\n')
            (src / 'owner-controls.json').write_text('{\"schema\":1}\n')
            (src / 'owner-script.md').write_text('Exact owner source\n')
            for name in ('verbatim-sources.md', 'execution-decisions.md', 'claim-execution-2026-11-19.md', 'factual-copy-execution-2026-11-19.md', 'casting-continuity-2026-11-19.md', 'casting-continuity-2026-11-19.sources.json'):
                (src / name).write_text('Exact source evidence ' + name)
            (src / 'unrelated-private-note.md').write_text('Do not carry unrelated notes')
            (src / 'run.json').write_text(json.dumps({'brand': 'test', 'product': 'product', 'production_route': 'ai', 'format_id': 'demonstration', 'audience': {'_avatar': 'reader'}}))
            variants.append({'id': 'V' + str(i), 'source_run': label, 'title': label})
            hashes[label] = G.digest(src / 'stages/5-brief.md')
        spec = {'brand': 'test', 'product': 'product', 'avatar': 'reader', 'title': 'Three selected versions', 'variants': variants}
        def accepted(src):return {'accepted': True, 'source': {'path': 'stages/5-brief.md', 'sha256': hashes[src.name]}}
        with patch.object(writing_result, 'inspect_result', side_effect=accepted):
            out, man = G.build(spec, key, root=self.root, drive=False)
        self.assertTrue((out / 'VIDEO-DELIVERY.md').is_file())
        self.assertIn('video-delivery-instructions:start', (out / 'BRIEF.md').read_text())
        self.assertTrue(all(x['ok'] for x in G.checks(out, man)))
        self.assertEqual(len({v['production_label'] for v in man['variants']}), 3)
        for v in man['variants']:
            self.assertEqual(G.digest(out / v['folder'] / 'BRIEF.md'), hashes[v['source_run']])
            src = self.root / 'runs/video-teardown/_work' / v['source_run']
            for name in ('language-exposure.json', 'owner-controls.json', 'owner-script.md', 'verbatim-sources.md', 'execution-decisions.md', 'claim-execution-2026-11-19.md', 'factual-copy-execution-2026-11-19.md', 'casting-continuity-2026-11-19.md', 'casting-continuity-2026-11-19.sources.json'):
                self.assertEqual((out / v['folder'] / 'writing' / name).read_bytes(), (src / name).read_bytes())
                self.assertEqual(v['source_evidence_sha256'][name], G.digest(src / name))
            self.assertFalse((out / v['folder'] / 'writing/unrelated-private-note.md').exists())
        (out / man['variants'][0]['folder'] / 'writing/verbatim-sources.md').write_text('changed evidence')
        self.assertFalse(G.checks(out, man)[0]['ok'])
        with patch.object(writing_result, 'inspect_result', return_value={'accepted': False, 'blockers': ['held']}):
            with self.assertRaisesRegex(ValueError, 'writing is not accepted'):
                G.build(spec, key, root=self.root, drive=False)

    def test_three_separate_accepted_brief_bytes(self):
        self.assertTrue(all(x['ok'] for x in G.checks(self.folder, self.man)))
        (self.folder / 'variants/A2/BRIEF.md').write_text('A revised, unvalidated brief')
        rows = G.checks(self.folder, self.man)
        self.assertEqual([x['ok'] for x in rows], [True, False, True])

    def test_held_variant_cannot_hide_inside_group(self):
        p = self.folder / 'variants/A3/writing/result.json'
        r = json.loads(p.read_text());r['accepted'] = False;p.write_text(json.dumps(r))
        self.assertFalse(G.checks(self.folder, self.man)[2]['ok'])

    def test_distinct_variants_and_safe_paths(self):
        self.man['variants'][1]['id'] = 'A1'
        self.assertFalse(G.checks(self.folder, self.man)[0]['ok'])
        for bad in ('../outside', '/absolute', 'bad/name', 'bad;command'):
            with self.assertRaises(ValueError):G.safe(bad)

    def test_metadata_refresh_preserves_working_files(self):
        (self.folder / 'HANDOFF.json').write_text('{"state":"open"}')
        (self.folder / 'BRIEF.md').write_text('local work')
        class Engine:
            def service(self):return None
            def list_files(self, *a, **kw):return [{'name':'HANDOFF.json','id':'manifest'}, {'name':'BRIEF.md','id':'brief'}]
            def get_media(self, fid, dest, **kw):Path(dest).write_text('{"state":"superseded","superseded_by":{"key":"new"}}')
        with patch.object(SH, '_engine', return_value=Engine()):
            SH.fetch('folder', self.folder, only=('HANDOFF.json', 'START.md'), refresh_metadata=True)
            self.assertEqual(json.loads((self.folder / 'HANDOFF.json').read_text())['state'], 'superseded')
            self.assertEqual((self.folder / 'BRIEF.md').read_text(), 'local work')
            with self.assertRaises(ValueError):SH.fetch('folder', self.folder, refresh_metadata=True)

    def test_full_fetch_fallback_does_not_activate_superseded_source(self):
        def fetch(fid, dest, only=None, **kwargs):
            if only:raise RuntimeError('metadata request temporarily unavailable')
            (Path(dest) / 'HANDOFF.json').write_text(json.dumps({'key': self.folder.name, 'stage': 'video-writing', 'state': 'superseded', 'superseded_by': {'key': 'canonical'}}))
        with patch.object(SH, 'drive_handoffs', return_value=[('test', self.folder.name, 'folder')]), patch.object(SH, 'fetch', side_effect=fetch), patch.object(pull, 'place', side_effect=AssertionError('must not activate old work')):
            result = pull.opening('0001', 'video-producer', 'test', root=self.root)
        self.assertEqual(result['state'], 'superseded')
        self.assertEqual(result['redirect']['key'], 'canonical')

    def test_remote_child_folder_cannot_escape_packet(self):
        class Engine:
            def service(self):return None
            def list_files(self, *a, **kw):return []
        with patch.object(SH, '_engine', return_value=Engine()), patch.object(SH, '_subfolders', return_value=[{'name': '../outside', 'id': 'child'}]):
            with self.assertRaisesRegex(ValueError, 'Unsafe Drive folder'):
                SH.fetch('folder', self.folder)
        self.assertFalse((self.folder.parent / 'outside').exists())

    def test_active_revision_remains_visible_beside_superseded_source(self):
        active = self.folder.parent / 'test_product_brief-0002'
        active.mkdir();(active / 'HANDOFF.json').write_text(json.dumps({'key': active.name, 'stage': 'video-production'}))
        (active / 'delivery-state.json').write_text(json.dumps({'state': 'back-for-revision', 'revision_id': 'revision-2'}))
        (self.folder / 'HANDOFF.json').write_text(json.dumps({'key': self.folder.name, 'stage': 'video-writing', 'state': 'superseded', 'superseded_by': {'key': active.name}}))
        rows = pull.waiting('video-producer', root=self.root, drive=False)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['state'], rows[0]['revision_id']), ('back-for-revision', 'revision-2'))

    def test_explicit_hold_is_not_reported_open(self):
        (self.folder / 'HANDOFF.json').write_text(json.dumps({'key': self.folder.name, 'stage': 'video-writing', 'state': 'held'}))
        rows = pull.waiting('video-producer', root=self.root, drive=False)
        self.assertEqual(rows[0]['state'], 'held')

    def test_superseded_packet_is_not_another_assignment(self):
        record = {'key':self.folder.name,'stage':'video-writing','state':'superseded','superseded_by':{'key':'canonical'}}
        (self.folder / 'HANDOFF.json').write_text(json.dumps(record))
        self.assertEqual(pull.waiting('video-producer', root=self.root, drive=False), [])
        with patch.object(SH, 'drive_handoffs', return_value=[]):
            opened = pull.opening('0001', 'video-producer', 'test', root=self.root)
        self.assertEqual(opened['state'], 'superseded')
        self.assertEqual(opened['redirect']['key'], 'canonical')


if __name__ == '__main__':unittest.main()
