import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Store, Refused
from creator_chain import prepare_inputs, handler, status, PROMPTS, CALL_RESERVE, reserve_subscription, codex_completion
from compare import compare
from pilot import registered_handlers
from decision import MODEL, POLICY, LABELS
from run_kit import prompts


class Connected(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.input = self.store.root/'input.json'
        fields = {k:'Fixture content' for k in prompts.wanted(prompts.latest(PROMPTS,'stage7b').read_text())}
        self.input.write_text(json.dumps(dict(fields=fields,script='Existing words.',provenance='Offline fixture')))
        self.hash = prepare_inputs(self.store,self.input)

    def job(self):
        return self.store.create('creator','handoff','creator-brief',self.hash)

    def test_real_prompt_to_review_then_revision_uses_note(self):
        calls=[]
        def runner(text):
            calls.append(text)
            return '# A creator brief', {'provider':'offline-test'}
        handlers={('creator','script'):handler(self.store,runner)}
        job=self.job();self.store.tick(handlers)
        job=self.store.get(job['id']);self.assertEqual(job['state'],'needs_review')
        self.assertIn('Write ONE video concept',calls[0])
        self.assertIn('Existing words.',(self.store.root/job['stages']['script']['file']).read_text())
        self.store.tick(handlers);self.assertEqual(len(calls),1)
        a=job['stages']['script']
        self.store.change(job['id'],'reject',dict(sha=a['sha'],revision=1,note='Shorten the opening.'),'reject','reviewer')
        self.store.tick(handlers);self.assertEqual(len(calls),2)
        self.assertIn('Shorten the opening.',calls[-1])
        self.assertEqual(self.store.get(job['id'])['state'],'needs_review')
        with self.store.connect() as db:
            self.assertAlmostEqual(db.execute('SELECT sum(reserved) FROM calls').fetchone()[0],2*CALL_RESERVE)

    def test_failed_generation_is_not_retried(self):
        calls=[]
        def fail(text): calls.append(text);raise RuntimeError('do not expose provider body')
        job=self.job();h=handler(self.store,fail)
        for _ in range(2):
            with self.assertRaises(Refused):h(job)
        self.assertEqual(len(calls),1)
        self.assertNotIn('provider body',json.dumps(status(self.store,job)))

    def test_successful_generation_reused_without_spend(self):
        calls=[]
        h=handler(self.store,lambda t:(calls.append(t) or '# Brief',{}));job=self.job()
        self.assertEqual(h(job),h(job));self.assertEqual(len(calls),1)

    def test_tampered_inputs_refuse_before_spend(self):
        job=self.job();(self.store.root/'inputs'/(self.hash+'.json')).write_text('{}')
        with self.assertRaises(Refused):handler(self.store)(job)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM calls').fetchone()[0],0)

    def test_budget_blocks_generation(self):
        self.store.reserve_call(1,.95)
        run=[]
        with self.assertRaises(Refused):handler(self.store,lambda t:run.append(t))(self.job())
        self.assertEqual(run,[])

    def test_demo_never_fills_real_job_and_approved_brief_packages_once(self):
        job=self.job();self.store.tick(registered_handlers(self.store,True,False))
        self.assertEqual(self.store.get(job['id'])['state'],'awaiting_draft')
        h=handler(self.store,lambda t:('# Brief',{}));self.store.tick({('creator','script'):h})
        job=self.store.get(job['id']);a=job['stages']['script']
        self.store.change(job['id'],'approve',dict(sha=a['sha'],revision=1),'approve','reviewer')
        self.store.tick(registered_handlers(self.store,True,True))
        self.assertEqual(self.store.get(job['id'])['state'],'awaiting_return')
        self.store.tick(registered_handlers(self.store,True,True))
        self.assertEqual(len(list((self.store.root/'outbox').iterdir())),1)
        self.assertNotIn('storyboard',self.store.get(job['id'])['stages'])

    def test_subscription_attempts_are_bounded_without_api_spend(self):
        job=self.job()
        for _ in range(5): reserve_subscription(self.store,job)
        with self.assertRaises(Refused):reserve_subscription(self.store,job)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT sum(reserved) FROM calls').fetchone()[0],0)

    def test_codex_runner_requires_completed_receipt_and_chatgpt_auth(self):
        import subprocess
        def fake(args, **kw):
            self.assertIn('forced_login_method="chatgpt"',args)
            self.assertNotIn('OPENAI_API_KEY',kw['env'])
            self.assertIn('--ignore-user-config',args)
            self.assertIn('shell_tool',args)
            Path(args[args.index('-o')+1]).write_text('# Concept')
            return subprocess.CompletedProcess(args,0,json.dumps({'type':'item.completed','item':{'type':'error','message':'nonfatal CLI diagnostic'}})+'\n'+json.dumps({'type':'turn.completed','usage':{'input_tokens':10}}),'')
        with patch('creator_chain.shutil.which',return_value='/tool/codex'),patch('creator_chain.subprocess.run',side_effect=fake):
            text,receipt=codex_completion('Supplied prompt')
        self.assertEqual(text,'# Concept');self.assertEqual(receipt['provider'],'codex-chatgpt-cli');self.assertEqual(receipt['nonfatal_event_count'],1)

    def test_comparison_keeps_labels_out_of_model_and_never_writes_rules(self):
        data=dict(label_status='Analyst frozen',cases=[dict(id='one',feedback='Specific input',context='Context only',
            expected='current_edit',source='local-note',label_basis='Secret expected reasoning')])
        p=self.store.root/'cases.json';p.write_text(json.dumps(data))
        sent=[]
        def caller(text,key):
            sent.append(text)
            return dict(status='answered',choice='current_edit',confidence=.9,estimated_usd=.0001,
                        seconds=.1,model=MODEL,policy=POLICY)
        r=compare(self.store,p,True,1,caller,'test-token')
        self.assertEqual(r['correct'],1);self.assertEqual(r['baseline']['correct'],0)
        self.assertNotIn('Secret expected reasoning',sent[0]);self.assertNotIn('expected',sent[0])
        self.assertEqual(self.store.jobs(),[])
        with self.assertRaises(Refused):compare(self.store,p,True,1,caller,'test-token')
        self.assertEqual(len(sent),1)

if __name__=='__main__':unittest.main()
