import json,tempfile,unittest
from pathlib import Path
import workspace
class Contract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.brand=self.root/'brands/example';self.brand.mkdir(parents=True)
  (self.root/'offer-workspace.json').write_text(json.dumps({'schema_version':1,'brand_id':'example','brand_root':'brands/example','offers_root':'offers','runs_root':'runs'}))
  for f in ('operations/brand.json','core-avatars/primary/profile.md','strategy/angles.json','products/offer-bank.md','sources/index.json'):
   p=self.brand/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('[]' if f=='sources/index.json' else '{}')
  p=self.root/'offers/first';p.mkdir(parents=True);(p/'offer.json').write_text(json.dumps({'id':'first','brand_id':'example','version':1,'status':'hypothesis','outcome':'Useful result','deliverables':['Draft']}))
 def tearDown(self):self.tmp.cleanup()
 def test_valid_draft_and_other_brand(self):
  self.assertEqual(workspace.check(self.root)['status'],'pass')
  (self.root/'brands/another').mkdir();self.assertEqual(workspace.check(self.root)['status'],'fail')
 def test_path_escape_rejected(self):
  with self.assertRaises(ValueError):workspace.local(self.root,'../outside')
 def test_source_schema(self):
  (self.brand/'sources/index.json').write_text('[{"id":"evidence","status":"recovered"}]')
  self.assertEqual(workspace.check(self.root)['status'],'fail')
 def test_offer_brand_mismatch(self):
  p=self.root/'offers/first/offer.json';d=json.loads(p.read_text());d['brand_id']='different';p.write_text(json.dumps(d))
  self.assertEqual(workspace.check(self.root)['status'],'fail')
if __name__=='__main__':unittest.main()
