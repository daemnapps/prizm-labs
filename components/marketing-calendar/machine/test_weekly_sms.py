import copy
import unittest
from weekly_sms import add_weekly_sms

CAD={'weekly':{'enabled':True,'start_date':'2026-11-09','preferred_weekday':1},'hour':12,'quiet_hours':{'to':9,'from':21}}
def email(n,date,hour=17):
 return {'id':'nov-%02d'%n,'date':date,'hour':hour,'type':'stack','offer':'the-set','segments':['Customers'],'channel':'email','then':None}
class WeeklySMS(unittest.TestCase):
 def test_one_weekly_from_start_and_stable_ids_on_replay(self):
  rows=[email(1,'2026-11-03'),email(2,'2026-11-10'),email(3,'2026-11-17'),email(4,'2026-11-24')]
  added=add_weekly_sms(rows,'2026-11',CAD)
  self.assertEqual([s['date'] for s in added],['2026-11-10','2026-11-17','2026-11-24'])
  self.assertEqual([s['follows'] for s in added],['nov-02','nov-03','nov-04'])
  self.assertEqual([s['hour'] for s in added],[18,18,18])
  self.assertEqual(add_weekly_sms(rows,'2026-11',CAD),[])
 def test_existing_reminders_are_preserved_and_get_no_same_day_extra(self):
  reminder=dict(email(3,'2026-11-10'),channel='sms',sms_beat='open')
  original=copy.deepcopy(reminder)
  rows=[email(1,'2026-11-10'),email(2,'2026-11-11'),reminder]
  added=add_weekly_sms(rows,'2026-11',CAD)
  self.assertEqual(added[0]['date'],'2026-11-11')
  self.assertEqual(reminder,original)
 def test_boundary_week_is_not_planned_twice(self):
  self.assertEqual(add_weekly_sms([email(1,'2026-11-30')],'2026-11',CAD),[])
  rows=[email(1,'2026-12-01')]
  self.assertEqual(add_weekly_sms(rows,'2026-12',CAD)[0]['cadence_week'],'2026-11-30')
 def test_quiet_hours_and_missing_companions(self):
  self.assertEqual(add_weekly_sms([email(1,'2026-11-10',20)],'2026-11',CAD),[])
  self.assertEqual(add_weekly_sms([],'2026-11',CAD),[])
 def test_offer_and_audience_come_from_the_email(self):
  e=email(1,'2026-11-10');e['offer_mix']=['the-set','tube']
  sms=add_weekly_sms([e],'2026-11',CAD)[0]
  self.assertEqual(sms['offer'],e['offer']);self.assertEqual(sms['segments'],e['segments'])
  self.assertNotIn('offer_mix',sms);self.assertEqual(sms['sms_job'],'engagement')
if __name__=='__main__':unittest.main()
