import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import Store, Refused, LANES
from pilot import demo_handler, ingest_returns
from decision import validate, classify, MODEL, suggested_route, MAX_CALL_USD


class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.counter = 0

    def event(self, job, action, payload=None, actor='worker'):
        self.counter += 1
        return self.store.change(job['id'], action, payload or {}, str(self.counter), actor)

    def approve(self, job):
        a = job['stages'][self.store.current(job)]
        return self.event(job, 'approve', {'sha': a['sha'], 'revision': job['revision']}, 'reviewer')

    def submit(self, job):
        stage = self.store.current(job)
        path = demo_handler(self.store)[(job['lane'],stage)](job)
        return self.event(job, 'submit', {'path':str(path), 'revision':job['revision'], 'stage':stage})

    def to_return(self, lane='email'):
        job = self.store.create(lane, 'handoff')
        for stage in LANES[lane][:-1]:
            self.store.tick(demo_handler(self.store))
            job = self.store.get(job['id'])
            self.assertEqual(job['state'], 'needs_review')
            self.assertEqual(self.store.current(job), stage)
            self.store.tick(demo_handler(self.store))
            self.assertEqual(self.store.get(job['id'])['index'], job['index'])
            job = self.approve(job)
        self.store.tick(demo_handler(self.store))
        return self.store.get(job['id'])

    def returned(self, job):
        folder = self.store.root / 'returns' / job['handoff']
        folder.mkdir(parents=True)
        filename = {'email':'finished.html','image':'finished.png','video':'finished.mp4','creator':'finished.mp4'}[job['lane']]
        # Synthetic transport fixtures, not media-quality evidence.
        (folder / filename).write_bytes(b'Synthetic returned content')
        (folder/'return.json').write_text(json.dumps({'handoff':job['handoff'],'file':filename}))
        ingest_returns(self.store)
        return self.store.get(job['id'])

    def test_all_requested_reviews_and_final_approval(self):
        for lane in LANES:
            job = self.to_return(lane)
            self.assertEqual(job['state'], 'awaiting_return')
            job = self.returned(job)
            self.assertEqual(job['state'], 'needs_review')
            self.assertEqual(self.store.current(job), 'finished_asset')
            job = self.approve(job)
            self.assertEqual(job['state'], 'ready_for_distribution')
            self.assertNotIn('published', job)

    def test_worker_cannot_approve(self):
        job = self.submit(self.store.create('image'))
        with self.assertRaises(Refused):
            self.event(job, 'approve', {'sha':job['stages']['image_draft']['sha'], 'revision':1})

    def test_observe_does_not_generate(self):
        job = self.store.create('video')
        self.store.tick(demo_handler(self.store))
        self.assertEqual(self.store.get(job['id'])['state'], 'awaiting_draft')

    def test_prepare_stops_before_handoff(self):
        job = self.store.create('image', 'prepare')
        self.store.tick(demo_handler(self.store))
        job = self.approve(self.store.get(job['id']))
        self.store.tick(demo_handler(self.store))
        self.assertEqual(self.store.get(job['id'])['state'], 'ready_for_handoff')
        with self.assertRaises(Refused):
            self.event(job, 'handoff')

    def test_stale_approval_refused(self):
        job = self.submit(self.store.create('image'))
        with self.assertRaises(Refused):
            self.event(job, 'approve', {'sha':'wrong', 'revision':1}, 'reviewer')

    def test_artifact_tampering_refused(self):
        job = self.submit(self.store.create('image'))
        (self.store.root/job['stages']['image_draft']['file']).write_text('changed')
        with self.assertRaises(Refused):
            self.approve(job)

    def test_revision_invalidates_downstream_and_old_handoff(self):
        job = self.to_return('video')
        old = job['handoff']
        sha = job['stages']['script']['sha']
        job = self.event(job, 'revise', {'stage':'script','sha':sha,'revision':1,'note':'New direction'}, 'reviewer')
        self.assertEqual(job['stages'], {})
        self.assertEqual(job['revision'], 2)
        self.assertIsNone(job['handoff'])
        with self.assertRaises(Refused):
            self.event(job, 'return', {'handoff':old,'path':'nope'}, 'operator')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM outbox WHERE id=?',(old,)).fetchone()[0], 'superseded')

    def test_duplicate_event_has_no_duplicate_effect(self):
        job = self.submit(self.store.create('image'))
        p={'sha':job['stages']['image_draft']['sha'],'revision':1}
        one=self.store.change(job['id'],'approve',p,'stable','reviewer')
        two=self.store.change(job['id'],'approve',p,'stable','reviewer')
        self.assertEqual(one,two)
        with self.assertRaises(Refused):
            self.store.change(job['id'],'approve',dict(p,revision=2),'stable','reviewer')

    def test_returns_are_idempotent_and_survive_reopen(self):
        job=self.returned(self.to_return())
        self.store=Store(self.tmp.name)
        self.assertEqual(ingest_returns(self.store),[])
        self.assertEqual(self.store.get(job['id'])['state'],'needs_review')

    def test_return_path_traversal_refused(self):
        job=self.to_return()
        folder=self.store.root/'returns'/job['handoff'];folder.mkdir(parents=True)
        (folder/'return.json').write_text(json.dumps({'handoff':job['handoff'],'file':'../outside.html'}))
        with self.assertRaises(Refused):ingest_returns(self.store)

    def test_wrong_return_type_refused(self):
        job=self.to_return()
        path=self.store.root/'bad.mp4';path.write_text('wrong lane')
        with self.assertRaises(Refused):self.event(job,'return',{'handoff':job['handoff'],'path':str(path)},'operator')

    def test_new_draft_cannot_use_old_revision(self):
        job=self.submit(self.store.create('image'))
        job=self.event(job,'reject',{'sha':job['stages']['image_draft']['sha'],'revision':1,'note':'revise'},'reviewer')
        p=self.store.root/'draft.md';p.write_text('draft')
        with self.assertRaises(Refused):self.event(job,'submit',{'path':str(p),'revision':1,'stage':'image_draft'})

    def test_missing_artifact_is_not_approval(self):
        job=self.submit(self.store.create('image'))
        (self.store.root/job['stages']['image_draft']['file']).unlink()
        with self.assertRaises(Refused):self.approve(job)

    def test_upstream_changes_block_final_approval(self):
        job=self.returned(self.to_return())
        (self.store.root/job['stages']['email_draft']['file']).write_text('tampered')
        with self.assertRaises(Refused):self.approve(job)

    def test_outbox_rebuild_uses_same_identity(self):
        job=self.to_return()
        self.store.export_outbox();self.store.export_outbox()
        self.assertEqual(len(list((self.store.root/'outbox').iterdir())),1)
        self.assertTrue((self.store.root/'outbox'/job['handoff']/'artifacts/email_draft.md').is_file())

    def test_budget_is_durable_and_conservative(self):
        self.store.reserve_call(MAX_CALL_USD, MAX_CALL_USD)
        fresh=Store(self.tmp.name)
        with self.assertRaises(Refused):fresh.reserve_call(MAX_CALL_USD,MAX_CALL_USD)
        with self.assertRaises(Refused):fresh.reserve_call(2,MAX_CALL_USD)

    def test_empty_output_refused(self):
        job=self.store.create('image');p=self.store.root/'empty';p.write_text('')
        with self.assertRaises(Refused):self.event(job,'submit',{'path':str(p),'revision':1,'stage':'image_draft'})


class Decisions(unittest.TestCase):
    def response(self):
        return {'model':MODEL, 'answers':{'scope':{'type':'choice','choice':'current_edit',
            'probabilities':{'current_edit':.96,'reusable_rule':.02,'needs_context':.02},'confidence':.94}},
            'usage':{'input_tokens':100}}

    def test_valid_typed_answer_remains_only_a_candidate(self):
        got=classify('Shorten this draft','test',lambda payload:self.response())
        self.assertEqual(suggested_route(got),'candidate_edit')
        self.assertNotIn('approved',got)

    def test_schema_model_and_nan_rejected(self):
        for key,value in [('model','jev-latest'),('usage',{'input_tokens':True}),('answers',{})]:
            raw=self.response();raw[key]=value
            with self.assertRaises((ValueError,KeyError)):validate(raw)
        raw=self.response();raw['answers']['scope']['confidence']=float('nan')
        with self.assertRaises(ValueError):validate(raw)

    def test_probability_contract(self):
        raw=self.response();raw['answers']['scope']['probabilities']['current_edit']=.1
        with self.assertRaises(ValueError):validate(raw)

    def test_failure_does_not_leak_provider_text(self):
        def fail(_):raise RuntimeError('secret credential response')
        result=classify('One edit','fake-key',fail)
        self.assertEqual(suggested_route(result),'needs_review')
        self.assertNotIn('secret',json.dumps(result))

    def test_uncertainty_abstains(self):
        raw=self.response();raw['answers']['scope']['confidence']=.2
        result=classify('Maybe update','test',lambda _:raw)
        self.assertEqual(suggested_route(result),'needs_review')

if __name__=='__main__':unittest.main()

class AdapterTest(unittest.TestCase):
    def test_existing_run_kit_executes_through_pilot_contract(self):
        from adapters import run_kit_handler
        # Fixture-compatible stand-in for the existing public Chain contract.
        class Chain:
            dry=False
            steps={'draft':{'label':'script'}}
            def __init__(self, root):self.out=Path(root)
            def run(self, key, **fields):
                (self.out/'draft--script.md').write_text(fields['source'])
        with tempfile.TemporaryDirectory() as folder:
            handler=run_kit_handler(lambda job:Chain(folder),'draft',lambda job:{'source':'draft'})
            self.assertEqual(handler({}).read_text(),'draft')

class RunKitIntegration(unittest.TestCase):
    def test_real_run_kit_with_offline_model_seam(self):
        from unittest.mock import patch
        from adapters import run_kit_handler
        kit = ROOT.parents[1] / 'components/run-kit'
        if not kit.exists():
            self.skipTest('Run in the Prizm checkout to exercise its existing run-kit')
        sys.path.insert(0,str(kit))
        from run_kit.stage import Chain
        with tempfile.TemporaryDirectory() as folder:
            prompts=Path(folder)/'prompts';prompts.mkdir()
            (prompts/'draft-v1-pilot.md').write_text('Write from {source}')
            chain=Chain('pilot','synthetic','trial',Path(folder)/'output',prompts,
                [{'key':'draft','tier':'reads','label':'script','depends':[]}],
                runner=lambda prompt,model:(0,'Offline generated script',''),echo=lambda *a:None)
            handler=run_kit_handler(lambda job:chain,'draft',lambda job:{'source':'synthetic brief'})
            with patch('run_kit.stage.creative_qc'):
                artifact=handler({})
            self.assertEqual(artifact.read_text().strip(),'Offline generated script')
            self.assertTrue((chain.out/'run.json').exists())


class KeyFileTest(unittest.TestCase):
    def test_shared_env_preserves_other_settings_and_symlink(self):
        from pilot import save_key
        with tempfile.TemporaryDirectory() as folder:
            real=Path(folder)/'main.env';alias=Path(folder)/'pilot.env'
            real.write_text('OTHER_SETTING=preserve\nTYPESAFE_API_KEY = old-placeholder\n')
            alias.symlink_to(real)
            save_key(alias,'synthetic-test-placeholder')
            self.assertTrue(alias.is_symlink())
            self.assertIn('OTHER_SETTING=preserve',real.read_text())
            self.assertEqual(real.read_text().count('TYPESAFE_API_KEY'),1)
            self.assertEqual(real.stat().st_mode & 0o777,0o600)

    def test_invalid_key_does_not_modify_file(self):
        from pilot import save_key
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'keys.env';p.write_text('OTHER_SETTING=preserve\n')
            with self.assertRaises(Refused):save_key(p,'bad\nkey')
            self.assertEqual(p.read_text(),'OTHER_SETTING=preserve\n')
