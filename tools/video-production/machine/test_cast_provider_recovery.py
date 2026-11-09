"""Regression checks for cast sheet shape and completed-job recovery; no network."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parents[1] / 'image-production'))
from image_production import providers

def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class RecoveryTests(unittest.TestCase):
    def test_landscape_reaches_provider_without_quality_override(self):
        door = load('direct_openai')
        with patch.object(door, '_door', return_value='higgsfield'), patch.object(door, '_via_image_engine') as send:
            door.generate('reference sheet', [], Path('sheet.png'), overrides={'size':'1536x1024','quality':'low'})
            self.assertEqual(send.call_args.kwargs['aspect'], '3:2')
            self.assertNotIn('quality', send.call_args.kwargs)

    def test_cast_wide_request_names_dimensions(self):
        maker = load('make_character')
        from types import SimpleNamespace
        from unittest.mock import Mock
        door = SimpleNamespace(cfg=lambda: {'params':{}}, generate=Mock())
        maker._generate(door, 'sheet', [], Path('sheet.png'), True)
        self.assertEqual(door.generate.call_args.kwargs['overrides'], {'size':'1536x1024'})

    def test_face_free_wardrobe_uses_garments_and_real_body_without_face_master(self):
        maker = load('make_character')
        prompt_bank, _ = maker.prompts()
        spec = {'who':'owner','adjustments':['keep identity'],'base':'neutral shirt','details':'hands',
                'body_references':[{'file':'body.jpg'}],
                'looks':{'outfit-selected':{'outfit':'grey suit','face_free':True,'refs':['suit.jpg']}}}
        jobs = maker.jobs(spec, prompt_bank, [Path('real.jpg')], [], Path('out'), Path('.'))
        _, prompt, refs, _, wide = next(j for j in jobs if j[0]=='outfit-selected')
        self.assertEqual(refs, [Path('suit.jpg'),Path('body.jpg')])
        self.assertIn('Do not depict a head, face', prompt)
        self.assertTrue(wide)

    def test_download_failure_never_creates_a_second_job(self):
        calls = []
        class HF:
            def which(self): return 'provider-cli'
            def run(self, argv, timeout=900):
                if argv[1] == 'account': return 0, '{"credits":100}', ''
                calls.append(argv)
                return 0, json.dumps([{'id':'completed-1','status':'completed','result_url':'https://example.invalid/result.png'}]), ''
            def fetch(self, url, dest): raise TimeoutError('download stalled')
        entry = {'provider':'higgsfield','vendor_model':'fixture','params':{'quality':'high','resolution':'2k'},'must_name':[]}
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / 'sheet.png'
            with self.assertRaises(OSError):
                providers.generate_ladder([{'name':'first','entry':entry,'retry':True},{'name':'second','entry':entry}], 'sheet', [], dest, '3:2', transport=HF())
            self.assertEqual(len(calls), 1)
            self.assertEqual(json.loads(Path(str(dest)+'.provider.json').read_text())['id'], 'completed-1')

    def test_download_replaces_destination_only_after_success(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / 'sheet.png'
            dest.write_bytes(b'original')
            with patch('subprocess.run', return_value=SimpleNamespace(returncode=1)):
                with self.assertRaises(OSError): providers._HfShell().fetch('https://example.invalid/a',dest)
            self.assertEqual(dest.read_bytes(), b'original')
            self.assertEqual(list(Path(folder).iterdir()), [dest])

if __name__ == '__main__': unittest.main()
