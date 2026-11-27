"""Calendar identity, schedule and audience boundaries; temp files only, no model/network/media calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import calendar_handoff as C


class Handoff(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.brand='testbrand'
        self.cal=self.root/'runs/marketing-calendar'/self.brand/'2099-01';self.cal.mkdir(parents=True)
        self.run=self.root/'runs/email-production'/self.brand/'testbrand-jan-01';self.run.mkdir(parents=True)
        self.slot=dict(id='jan-02',date='2099-01-02',hour=17,local=True,segments=['Core | Lead'],segment='Core | Lead',
            type='stack',offer='none',variants=[{'avatar':'reader','angle':'How the routine works'}],channel='email')
        self.state={'assignment':{'send_date':'2099-01-02','avatar':'reader','angle':'How the routine works','offer':'none'}}
        self.save()
    def tearDown(self):self.tmp.cleanup()
    def save(self,others=None):
        (self.cal/'slots.json').write_text(json.dumps((others or [])+[self.slot]))
        (self.run/'run.json').write_text(json.dumps(self.state))
    def test_calendar_time_beats_conflicting_brand_default(self):
        self.assertEqual(C.schedule(self.slot,{'local':'08:00','recipient_time_zone':False}),{'local':'17:00','recipient_time_zone':True})
    def test_fixed_calendar_time_stays_fixed(self):
        self.slot.update(hour=18,local=False)
        self.assertEqual(C.schedule(self.slot)['recipient_time_zone'],False)
    def test_partial_calendar_time_never_falls_back(self):
        del self.slot['hour']
        with self.assertRaises(C.Held):C.schedule(self.slot,{'local':'08:00'})
    def test_date_matches_renumbered_folder_without_using_its_suffix(self):
        old=dict(self.slot,id='jan-01',date='2099-01-01');self.save([old])
        self.assertEqual(C.resolve(self.root,self.brand,self.run)['id'],'jan-02')
    def test_multiple_same_date_do_not_guess(self):
        other=copy.deepcopy(self.slot);other['id']='jan-03';self.save([other])
        with self.assertRaises(C.Held):C.resolve(self.root,self.brand,self.run)
    def test_explicit_binding_identifies_one_same_date_send(self):
        self.state['calendar_handoff']=C.snapshot(self.slot,self.brand,'reader')
        other=copy.deepcopy(self.slot);other['id']='jan-03';self.save([other])
        self.assertEqual(C.resolve(self.root,self.brand,self.run)['id'],'jan-02')
    def test_legacy_source_id_requires_date_angle_and_recorded_format(self):
        self.state['elements']={'format/email':{'id':'stack'}};self.state['source_reference']='jan-03: existing source'
        other=copy.deepcopy(self.slot);other['id']='jan-03';self.save([other])
        self.assertEqual(C.resolve(self.root,self.brand,self.run)['id'],'jan-03')
        self.state.pop('elements');self.save([other])
        with self.assertRaises(C.Held):C.resolve(self.root,self.brand,self.run)
    def test_review_edits_override_raw_plan(self):
        (self.cal/'review.json').write_text(json.dumps({'slots':{'jan-02':{'edits':{'hour':19,'segment':'Core | One-Time Customer'}}},'copy':{}}))
        s=C.resolve(self.root,self.brand,self.run)
        self.assertEqual(C.schedule(s)['local'],'19:00');self.assertEqual(C.segments(s),['Core | One-Time Customer'])
    def test_cut_bound_send_cannot_rebind(self):
        self.state['calendar_handoff']=C.snapshot(self.slot,self.brand);self.save()
        (self.cal/'review.json').write_text(json.dumps({'slots':{'jan-02':{'status':'cut'}},'copy':{}}))
        with self.assertRaises(C.Held):C.resolve(self.root,self.brand,self.run)
    def test_corrupt_review_is_a_hold(self):
        (self.cal/'review.json').write_text('[]')
        self.assertEqual(C.inspect(self.root,self.brand,self.run)['state'],'held')
    def test_lead_buyer_angle_stops_before_writer(self):
        self.slot['variants'][0]['angle']='She owns the scrub she bought'
        self.assertTrue(C.audience_problems(self.slot,avatar='reader'))
    def test_cli_rejects_contradictory_brief_before_creating_work(self):
        import subprocess,sys
        self.slot['variants'][0]['angle']='She owns the scrub'
        contract=C.snapshot(self.slot,self.brand,'reader')
        cmd=[sys.executable,str(Path(__file__).with_name('email_line.py')),'missing-source.md','--brand',self.brand,
             '--calendar-slot',json.dumps(contract),'--segment','Core | Lead','--send-date',self.slot['date'],'--avatar','reader']
        before=sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        p=subprocess.run(cmd,cwd=self.root,capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('HELD at calendar handoff',p.stdout+p.stderr)
        self.assertEqual(before,sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))
    def test_writing_handoff_carries_complete_calendar_and_checks_before_command(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        import brief
        self.slot['source']='existing.md'
        argv=brief.chain_argv(self.slot,self.brand,'reader','How the routine works')
        snap=json.loads(argv[argv.index('--calendar-slot')+1])
        self.assertEqual(snap['fields']['hour'],17);self.assertEqual(snap['fields']['segments'],['Core | Lead'])
        self.slot['variants'][0]['angle']='She owns the scrub'
        with self.assertRaises(C.Held):brief.chain_argv(self.slot,self.brand,'reader','She owns the scrub')
    def test_lead_buyer_copy_is_held_even_with_valid_plan(self):
        r=C.inspect(self.root,self.brand,self.run,copy={'body':['We sold you one tube.']})
        self.assertEqual(r['state'],'held');self.assertIn('copy assumes',r['problems'][0])
    def test_customer_copy_is_allowed_for_customers(self):
        self.slot['segments']=['Core | One-Time Customer']
        self.assertFalse(C.audience_problems(self.slot,copy={'body':['We sold you one tube.']}))
    def test_conditional_education_is_not_a_prior_purchase_assertion(self):
        self.assertFalse(C.audience_problems(self.slot,copy={'body':['If you already own the scrub, use the cream after it.']}))
    def test_competitor_purchase_and_email_receipt_do_not_imply_our_customer(self):
        self.assertFalse(C.audience_problems(self.slot,copy={'body':['Read the label on the last one you bought. We sent you an email yesterday.']}))
    def test_changed_offer_is_not_cleared_by_old_copy_pass(self):
        self.state['assignment']['offer']='old-offer';self.save()
        self.assertIn('calendar offer changed since writing',C.inspect(self.root,self.brand,self.run)['problems'])
    def test_unreleased_card_is_reconciled_from_calendar(self):
        old={'status':'draft','send_local':'08:00','recipient_time_zone':False,'segments':['Core | Lead']}
        m=C.metadata(self.root,self.brand,self.run,{'segments':['Core | Lead']},{'send':{'local':'08:00'}},old)
        self.assertEqual(m['send_local'],'17:00');self.assertTrue(m['recipient_time_zone'])
    def test_scheduled_metadata_is_preserved_and_divergence_held(self):
        old={'status':'scheduled','date':'2099-01-02','scheduled':{'by':'reviewer'},'send_local':'08:00','recipient_time_zone':False,'segments':['Core | Lead']}
        before=copy.deepcopy(old)
        m=C.metadata(self.root,self.brand,self.run,{'segments':['Core | Lead']},{},old)
        self.assertEqual(old,before);self.assertEqual(m['send_local'],'08:00');self.assertEqual(m['calendar_handoff']['state'],'held')
    def test_stale_card_is_blocked_at_approval_without_network(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        import approve_klaviyo as A
        c={'brand':self.brand,'label':self.run.name,'date':'2099-01-02','send_local':'08:00','recipient_time_zone':False,'segments':['Core | Lead']}
        with patch.object(A,'WORKSPACE',self.root),patch.object(A,'RUNS',self.root/'runs/email-production'),patch.object(A,'link_status',side_effect=AssertionError('network called')):
            self.assertIn('calendar/card mismatch: send_local',A.check(c))
    def test_another_released_version_blocks_duplicate_audience_release(self):
        other=self.run.with_name('other-version');(other/'klaviyo').mkdir(parents=True)
        (other/'run.json').write_text(json.dumps(self.state))
        (other/'klaviyo/card.json').write_text(json.dumps({'status':'scheduled','date':self.slot['date'],'segments':['Core | Lead']}))
        c=dict(date=self.slot['date'],send_local='17:00',recipient_time_zone=True,segments=['Core | Lead'])
        self.assertTrue(any('another version' in p for p in C.card_problems(self.root,self.brand,self.run,c)))
    def test_simple_strategy_uses_calendar_local_flag(self):
        import simple_email as S
        st=S.send_strategy({'send_time':{'local':'08:00','recipient_time_zone':False}},self.slot)
        self.assertIn('T17:00:00',st['datetime']);self.assertTrue(st['options']['is_local'])
    def test_invalid_build_stops_before_render_or_drive_and_keeps_existing_html(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent/'design'))
        import build as B
        (self.run/'design').mkdir();(self.run/'deliverable').mkdir();(self.run/'klaviyo').mkdir()
        (self.run/'design/email.json').write_text(json.dumps({'brand':self.brand,'label':self.run.name,'segments':['Core | Lead']}))
        (self.run/'deliverable/email.json').write_text(json.dumps({'body':['We sold you one tube.']}))
        html=self.run/'klaviyo/email.html';html.write_text('existing build')
        with patch.object(B.L,'REPO',self.root),patch.object(B.L,'load',return_value={}),patch.object(B.EN,'house',side_effect=AssertionError('render started')),patch.object(B,'layout_and_mirror',side_effect=AssertionError('Drive reached')):
            card=B.build(self.run)
        self.assertEqual(card['calendar_handoff']['state'],'held');self.assertEqual(html.read_text(),'existing build')
    def test_local_reconciliation_preserves_released_fields_and_backup_is_idempotent(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        import reconcile_calendar as R
        import simple_email as S
        (self.run/'deliverable').mkdir();(self.run/'klaviyo').mkdir()
        (self.run/'deliverable/email.json').write_text(json.dumps({'body':['Education'],'subjects':[{'subject':'Hello','preview':'More'}]}))
        (self.run/'deliverable/check.json').write_text(json.dumps({'delivery':{'result':'pass','problems':[]}}))
        old={'brand':self.brand,'label':self.run.name,'date':'2099-01-02','send_local':'08:00','recipient_time_zone':False,'segments':['Core | Lead'],'status':'scheduled','klaviyo':{'campaign_id':'existing'}}
        card=self.run/'klaviyo/card.json';card.write_text(json.dumps(old))
        with patch.object(S,'WORKSPACE',self.root),patch.object(S,'delivery_problems',return_value=[]):
            first=R.audit_brand(self.root,self.brand,'2099-01',write=True)
            backup=(self.run/'klaviyo/calendar-handoff-before.json').read_text()
            R.audit_brand(self.root,self.brand,'2099-01',write=True)
        after=json.loads(card.read_text())
        for key,value in old.items():self.assertEqual(after[key],value)
        self.assertEqual(first['counts']['existing-platform-work'],1)
        self.assertEqual(backup,(self.run/'klaviyo/calendar-handoff-before.json').read_text())
    def test_existing_fact_hold_is_not_silently_cleared_by_new_empty_checks(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        import reconcile_calendar as R
        import simple_email as S
        (self.run/'deliverable').mkdir()
        (self.run/'deliverable/email.json').write_text(json.dumps({'body':['Education'],'subjects':[{'subject':'Hello','preview':'More'}]}))
        (self.run/'deliverable/check.json').write_text(json.dumps({'delivery':{'result':'HELD','problems':['unsupported customer quote']}}))
        with patch.object(S,'WORKSPACE',self.root),patch.object(S,'delivery_problems',return_value=[]):r=R.audit_brand(self.root,self.brand,'2099-01')
        self.assertEqual(r['runs'][0]['review_state'],'held');self.assertIn('unsupported customer quote',r['runs'][0]['problems'])


if __name__=='__main__':unittest.main()
