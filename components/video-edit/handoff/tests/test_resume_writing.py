"""Unfinished writing travels at its actual stage; source runs and holds survive the handoff."""
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import resume_writing as RW
import stage_handoff as SH
import check as CK
import pull as PL


class WritingContinuation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / 'runs/video-teardown/_work/yai-test'
        (self.src / 'stages').mkdir(parents=True)
        (self.src / 'hand').mkdir()
        (self.src / 'qc-log').mkdir()
        (self.src / 'stages/1-teardown.md').write_text('beat\n' * 200)
        (self.src / 'stages/2-spec.md').write_text('spec\n' * 200)
        (self.src / 'stages/3-injection.md').write_text('finished injection')
        (self.src / 'hand/4ab-reading-hooks.prompt.md').write_text('full request, kept byte for byte')
        (self.src / 'qc-log/hold.json').write_text('{"accepted": false}')
        self.record = {'brand':'sample','state':'failed','production_route':'ai','stages':{
            'stage3':{'status':'done','out':'stages/3-injection.md'},
            'stage4v2a':{'status':'error','error':'waiting for the session hand: hand/4ab-reading-hooks.prompt.md'}}}
        self.save()

    def save(self):
        (self.src / 'run.json').write_text(json.dumps(self.record))

    def test_unaccepted_run_is_ready_for_writing_not_production(self):
        before = (self.src / 'run.json').read_bytes()
        out, rec = RW.build('yai-test', drive=False, root=self.root)
        self.assertEqual((rec['role'], rec['stage'], rec['writing_accepted'], rec['production_ready']),
                         ('video-producer', 'video-writing', False, False))
        self.assertEqual(rec['hand_prompts'], ['hand/4ab-reading-hooks.prompt.md'])
        self.assertEqual((out / 'teardown-run/run.json').read_bytes(), before)
        self.assertTrue((out / 'teardown-run/qc-log/hold.json').is_file())
        self.assertEqual((self.src / 'run.json').read_bytes(), before)
        checked = CK.check(out, SH.stage('video-writing'), drive=False, root=self.root)
        self.assertFalse([c for c in checked['checks'] if not c['ok']])
        rows = PL.waiting('video-producer', root=self.root, drive=False)
        self.assertEqual((rows[0]['stage'], rows[0]['state']), ('video-writing', 'open'))

    def test_accepted_writing_must_use_production_door(self):
        self.record['writing_acceptance'] = {'accepted':True}; self.save()
        with self.assertRaisesRegex(SystemExit, 'accepted writing'):
            RW.build('yai-test', drive=False, root=self.root)

    def test_held_brief_gets_revalidation_not_regeneration(self):
        (self.src / 'stages/5-brief.md').write_text('held brief')
        self.record['stages']['stage5']={'status':'held','out':'stages/5-brief.md'};self.save()
        _, rec = RW.build('yai-test', drive=False, root=self.root)
        self.assertTrue(rec['activate']['run'].endswith('--revalidate'))

    def test_winner_inputs_travel_and_existing_work_is_preserved(self):
        winner = self.root / 'runs/video-teardown/_work/winner'
        (winner / 'stages').mkdir(parents=True)
        (winner / 'stages/1-transcript.md').write_text('winner words')
        self.record['writing_lane']={'lane':'winner','winner':'winner'};self.save()
        out, rec = RW.build('yai-test', drive=False, root=self.root)
        shutil.rmtree(winner)
        (self.src / 'stages/3-injection.md').write_text('newer local work')
        PL.place(out, rec, self.root)
        self.assertEqual((winner / 'stages/1-transcript.md').read_text(), 'winner words')
        self.assertEqual((self.src / 'stages/3-injection.md').read_text(), 'newer local work')

    def test_bundled_frames_restore_without_overwriting_existing_work(self):
        (self.src / 'framemap').mkdir()
        (self.src / 'framemap/frame.jpg').write_bytes(b'original frame')
        out, rec = RW.build('yai-test', drive=False, root=self.root)
        self.assertFalse((out / 'teardown-run/framemap').exists())
        self.assertTrue((out / 'working-media.zip').is_file())
        shutil.rmtree(self.src)
        PL.place(out, rec, self.root)
        self.assertEqual((self.src / 'framemap/frame.jpg').read_bytes(), b'original frame')
        (self.src / 'framemap/frame.jpg').write_bytes(b'newer frame')
        PL.place(out, rec, self.root)
        self.assertEqual((self.src / 'framemap/frame.jpg').read_bytes(), b'newer frame')

    def test_media_parts_each_restore_their_original_files(self):
        (self.src / 'framemap').mkdir()
        for i in range(3):
            (self.src / ('framemap/%d.jpg' % i)).write_bytes(bytes([i]) * 8)
        out = self.root / 'packet'; out.mkdir()
        parts = RW.bundle_media(self.src, out, limit=10)
        self.assertEqual(len(parts), 3)
        destination = self.root / 'restored'; destination.mkdir()
        for part in parts:
            RW.restore_media(out, destination, part)
        for i in range(3):
            self.assertEqual((destination / ('framemap/%d.jpg' % i)).read_bytes(), bytes([i]) * 8)

    def test_rejects_archive_path_traversal_before_writing(self):
        out, rec = RW.build('yai-test', drive=False, root=self.root)
        with zipfile.ZipFile(out / rec['working_media'], 'w') as bundle:
            bundle.writestr('framemap/good.jpg', b'ok')
            bundle.writestr('../escaped.txt', b'bad')
        with self.assertRaisesRegex(SystemExit, 'unsafe'):
            PL.place(out, rec, self.root)
        self.assertFalse((self.src / 'framemap/good.jpg').exists())
        self.assertFalse((self.src.parent / 'escaped.txt').exists())

    def test_rejects_dependency_path_traversal(self):
        out, rec = RW.build('yai-test', drive=False, root=self.root)
        rec['working_dependencies']=[{'packet':'../outside','path':'runs/video-teardown/_work/x'}]
        with self.assertRaisesRegex(SystemExit, 'unsafe'):
            PL.place(out,rec,self.root)

if __name__ == '__main__':
    unittest.main()
