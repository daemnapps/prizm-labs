"""Production briefs and SMS obey calendar corrections without replacing purchased offers."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief
import sms
sys.path.insert(0, str(brief.HERE / 'machine'))
import reviewed_plan as RP

class HolidayBriefs(unittest.TestCase):
    def slot(self):
        return {'id':'dec-01','date':'2026-12-03','hour':18,'local':True,
                'segment':'Core | Lead','type':'house-special','source':'source.md',
                'offer':'bundle','offer_mix':['bundle','other'],
                '_review':{'note':'Gift changes Dec 1; bundle price and checkout stay.'}}
    def test_email_command_carries_review_note_offer_mix_and_brand_label(self):
        s=self.slot()
        with mock.patch.object(brief,'moment_context',return_value=None), mock.patch.object(brief,'spent_ground',return_value=''):
            out=brief.build_brief(s,'testbrand',Path('/absent'),brief.WORKSPACE/'runs/marketing-calendar/testbrand/2026-12')
        self.assertIn('--offer bundle',out)
        self.assertIn('--offer-also other',out)
        self.assertIn('--label testbrand-dec-01',out)
        self.assertIn('--note',out)
        self.assertIn(s['_review']['note'],out)
        self.assertNotIn(str(brief.WORKSPACE),out)
        self.assertIn('--calendar-slot',out)
    def test_sms_has_sms_command_and_note_in_prompt(self):
        s=self.slot();s['channel']='sms'
        with mock.patch.object(brief,'moment_context',return_value=None), mock.patch.object(brief,'spent_ground',return_value=''):
            out=brief.build_brief(s,'testbrand',Path('/absent'),brief.WORKSPACE/'runs/marketing-calendar/testbrand/2026-12')
        self.assertIn('components/email-production/sms.py',out)
        self.assertNotIn('email_line.py',out)
        with mock.patch.object(sms,'section_for',return_value='Price: $79'):
            prompt,sec=sms.fill('{date} {segment}',s,'testbrand',{})
        self.assertIn(s['_review']['note'],prompt)
        self.assertEqual(sec,'Price: $79')
    def test_review_preserves_offer_but_changes_audience_and_removes_cut(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            (d/'review.json').write_text(json.dumps({'slots':{'dec-01':{'edits':{'segment':'Core | VIP Customer'},'note':'gift terms'},'dec-02':{'status':'cut'}},'copy':{}}))
            rows=RP.reviewed(d,[self.slot(),dict(self.slot(),id='dec-02')])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['segments'],['Core | VIP Customer'])
        self.assertEqual(rows[0]['offer'],'bundle')
        self.assertEqual(rows[0]['_review']['note'],'gift terms')

class HolidaySMSChecks(unittest.TestCase):
    def test_omitted_calendar_does_not_invent_beat_restrictions(self):
        self.assertFalse(sms.check('Early access. {link} Reply STOP to opt out','No code',{}))

    def test_last_day_must_match_sale_deadline(self):
        slot={'date':'2026-12-24','deadline':'2026-12-25','sms_beat':'last-chance'}
        problems=sms.check('Last day. {link} Reply STOP to opt out','No code',{},slot)
        self.assertTrue(any('calendar deadline' in p for p in problems))
        slot['date']='2026-12-25'
        self.assertFalse(sms.check('Last day. {link} Reply STOP to opt out','No code',{},slot))
    def test_shipping_cutoff_is_not_sale_end(self):
        slot={'date':'2026-12-17','order_by':'2026-12-17','sms_beat':'last-chance'}
        self.assertTrue(any('cutoff' in p for p in sms.check('Last day. {link} Reply STOP to opt out','No code',{},slot)))
        self.assertFalse(sms.check('Last day to order for Christmas. {link} Reply STOP to opt out','No code',{},slot))
    def test_required_lead_is_checked(self):
        slot={'required_lead':'Buy two, get a gift','sms_beat':'open'}
        self.assertTrue(any('required line' in p for p in sms.check('Sale is on. {link} Reply STOP to opt out','No code',{},slot)))
        self.assertFalse(sms.check('Buy two, get a gift. {link} Reply STOP to opt out','No code',{},slot))

if __name__=='__main__':unittest.main()
