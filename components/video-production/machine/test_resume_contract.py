"""Offline behavior regressions for production intake, normalization and resume."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cache_contract as cache
import scenes
import intake_readiness

class CacheContract(unittest.TestCase):
    def test_camera_keeps_voice_line_invalidates_voice(self):
        doc={'scenes':[{'id':'S1','voice':'Hi','speaker':'A','camera':'wide','shots':[{'id':'S1.1','camera':'wide'}]}]}
        before=cache.input_hashes(doc); changed=copy.deepcopy(doc)
        changed['scenes'][0]['camera']='close'; changed['scenes'][0]['shots'][0]['camera']='close'
        after=cache.input_hashes(changed)
        self.assertEqual(before['voice'],after['voice']); self.assertNotEqual(before['storyboard'],after['storyboard'])
        changed['scenes'][0]['voice']='New line'
        self.assertNotEqual(before['voice'],cache.input_hashes(changed)['voice'])

    def test_receipt_reuse_and_tampered_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp); (run/'vo').mkdir(); (run/'vo/timing.json').write_text('{}')
            (run/'plan.json').write_text(json.dumps({'scenes':[{'id':'S1','voice':'Hi'}]}))
            self.assertEqual(cache.state(run,'voice'),'unbound')
            cache.seal(run,'voice'); self.assertEqual(cache.state(run,'voice'),'current')
            (run/'vo/timing.json').write_text('{"different":true}')
            self.assertEqual(cache.state(run,'voice'),'changed_outputs')
            with self.assertRaises(ValueError): cache.require_current(run,'voice')

    def test_normalization_preserves_identity(self):
        doc={'piece':{'style_id':'line-art','format':'meme'},'scenes':[
            {'id':'S1','kind':'talking','speaker':'A','voice':'Exact words','to_camera':True,'shots':[{'id':'S1.1','camera':'wide'}]},
            {'id':'S2','kind':'card','text':'Offer'}]}
        parsed=scenes.scenes_from_block(doc)
        self.assertEqual(parsed[0]['shots'],doc['scenes'][0]['shots'])
        self.assertEqual(parsed[0]['speaker'],'A'); self.assertEqual(parsed[0]['voice'],'Exact words')
        self.assertEqual(parsed[1]['kind'],'card'); self.assertEqual(scenes.piece_from_block(doc)['style_id'],'line-art')

    def test_read_only_intake_rejects_inherited_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp); (run/'stages').mkdir()
            (run/'run.json').write_text(json.dumps({'slug':'child','brief':'brief-0070','production_route':'creator'}))
            (run/'stages/5-brief.md').write_text('```json\n'+json.dumps({'piece':{'format':'testimonial'},'scenes':[{'id':'S1'}]})+'\n```')
            before={str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()}
            result=intake_readiness.inspect_intake(run)
            self.assertEqual(before,{str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()})
            self.assertFalse(result['ready']); self.assertFalse(result['identity']['verified'])
            self.assertFalse(result['writing']['accepted']); self.assertEqual(result['route'],'creator')

    def human_run(self, run, route, text, source='stages/5-brief.md'):
        p=run/source; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
        record={'slug':'human-fixture','brand':'fixture','production_route':route,'format_id':'testimonial',
                'stages':{'stage5':{'status':'done','out':source}}}
        writing=intake_readiness.load(Path(intake_readiness.__file__).parents[2]/'video-writing/machine/writing_result.py','fixture_writing')
        writing.record_acceptance(run,record)
        (run/'run.json').write_text(json.dumps(record))
        return record

    def test_human_prose_uses_public_filming_preview_without_ai_requirements(self):
        for route in ('creator','founder'):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as tmp:
                run=Path(tmp)
                self.human_run(run,route,'# Film this\n\n**Film:** Hold the product.\n**Say:** My exact line.\n\n**Film:** Show the label.\n')
                before={str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()}
                original=intake_readiness.load; loaded=[]
                def tracked(path,name):
                    loaded.append(Path(path).name)
                    module=original(path,name)
                    if Path(path).name=='runsheet.py':
                        module.Chain=lambda *a,**k: self.fail('AI bank/chain constructed')
                    return module
                with patch.object(intake_readiness,'load',side_effect=tracked):
                    result=intake_readiness.inspect_intake(run)
                self.assertTrue(result['ready'],result['gaps'])
                self.assertTrue(result['writing']['accepted'])
                self.assertEqual(result['next_action']['kind'],'filming_assignment')
                self.assertEqual(result['scene_count'],2)
                self.assertIn('runsheet.py',loaded)
                self.assertFalse(result['filming_packet']['execution_ready'])
                self.assertTrue(result['filming_packet']['validation_required'])
                self.assertEqual(before,{str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()})

    def test_human_final_source_and_ai_checks_do_not_become_ai_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)
            self.human_run(run,'founder','**Film:** Existing founder shot.\n',source='deliverable/7-final-brief.md')
            sha=intake_readiness.hashlib.sha256((run/'deliverable/7-final-brief.md').read_bytes()).hexdigest()
            (run/'writing-resume-checks.json').write_text(json.dumps({'source_sha256':sha,'checks':{'cast_findings':['no bank_id'],'production_contract':['no AI scenes']}}))
            result=intake_readiness.inspect_intake(run)
            self.assertTrue(result['ready'],result['gaps'])
            self.assertTrue(result['filming_packet']['execution_ready'])
            self.assertEqual(result['source']['path'],'deliverable/7-final-brief.md')

    def test_human_missing_instructions_and_unaccepted_writing_still_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp); self.human_run(run,'creator','# Intention only\n')
            result=intake_readiness.inspect_intake(run)
            self.assertFalse(result['ready'])
            self.assertIn('filming_instructions',[x['code'] for x in result['gaps']])
            (run/'stages/5-brief.md').write_text('**Film:** A real shot.\n')
            result=intake_readiness.inspect_intake(run)
            self.assertFalse(result['ready'])
            self.assertIn('writing_acceptance',[x['code'] for x in result['gaps']])

    def test_delivery_and_line_fields_invalidate_voice(self):
        doc={'scenes':[{'id':'S1','voice':'Hi','delivery_tag':'quiet','lines':[{'say':'Hi'}], 'shots':[{'id':'S1.1','delivery_tag':'quiet'}]}]}
        before=cache.input_hashes(doc)['voice']
        for field,value in [('delivery_tag','excited'),('lines',[{'say':'Bye'}]),('shots',[{'id':'S1.1','delivery_tag':'excited'}])]:
            changed=copy.deepcopy(doc); changed['scenes'][0][field]=value
            self.assertNotEqual(before,cache.input_hashes(changed)['voice'])

    def test_invalid_review_cache_can_retry_and_keeps_evidence(self):
        import v2_checks
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp); v2_checks.remember(run,'abc',{'text':'bad','info':{}})
            v2_checks.invalidate(run,'abc','invalid schema')
            self.assertIsNone(v2_checks.remembered(run,'abc'))
            v2_checks.remember(run,'abc',{'text':'valid','info':{}})
            result=v2_checks.remembered(run,'abc')
            self.assertEqual(result['text'],'valid'); self.assertEqual(result['prior_invalid_answers'][0]['text'],'bad')

    def test_start_dry_run_writes_no_run(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'plan.json'; source.write_text('{"scenes":[]}')
            command=[sys.executable,str(Path(__file__).parent/'run.py'),'start',str(source),'--brand','fixture','--format','single-presenter','--label','preview','--runs-root',str(root/'runs'),'--dry-run']
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr); self.assertFalse((root/'runs').exists())

class ReviewRecovery(unittest.TestCase):
    def test_retry_reviews_existing_take_without_regeneration(self):
        import test_v2_rulings as fixtures
        import clips_run as clips
        fixture=fixtures.ThreeTakes(); fixture.setUp()
        try:
            made=[]; maker=fixture.make({}); ledger=fixtures.LedgerFake()
            call={'id':'G01-C1','start_frame':'S1-F1'}; config={**fixtures.CFG,'takes':1,'max_tries':3}
            def make(*args): made.append(args[1]['id']); return maker(*args)
            with self.assertRaisesRegex(RuntimeError,'review unavailable'):
                clips.make_picked(fixture.run,call,config,ledger,{},make=make,
                    judge=lambda *a:{'state':'unreviewed','score':0,'pass':False,'problems':[{'what':'provider unavailable'}]})
            self.assertEqual(len(made),1); self.assertEqual(fixture.finished,[])
            class Body:
                check=staticmethod(lambda *a:{'ok':True})
            original=clips._load
            with patch.object(clips,'_load',side_effect=lambda name:Body if name=='body_check' else original(name)):
                result=clips.make_picked(fixture.run,call,config,ledger,{},make=make,
                    judge=lambda *a:{'state':'reviewed','score':9,'pass':True,'problems':[]})
            self.assertEqual(len(made),1); self.assertEqual(result['picked'],1)
        finally: fixture.tearDown()

if __name__=='__main__': unittest.main()
