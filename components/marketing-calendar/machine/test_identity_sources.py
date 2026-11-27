"""The catalogue supplies formats; the selected brand supplies identity facts. No model calls."""
import json
import tempfile
import unittest
from pathlib import Path
import brandrecord as C

class IdentitySources(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  (self.root/'brand-identity').mkdir()
  self.catalog=self.root/'types.json'
  self.catalog.write_text(json.dumps({'types':[{'key':'behind-the-scenes','well':'brand','name':'Behind the scenes','role':'earns','what':'How the product is made','note':'A pharmacist formulating is a standing source most brands would have to invent.','arc_note':'The making leads to the launch.'}]}))
 def tearDown(self):self.tmp.cleanup()
 def test_catalogue_hint_cannot_become_identity_input(self):
  (self.root/'brand-identity/story.md').write_text('Grandma shared her recipe. Coco took it to Gotha Cosmetics in Milan.')
  got=C.planner_types(self.catalog,self.root)
  self.assertNotIn('A pharmacist formulating',got)
  self.assertIn('Coco took it to Gotha',got)
  self.assertIn('The making leads to the launch',got)
  self.assertTrue(C.identity_problems([{'id':'x','variants':[{'angle':'Coco is a pharmacist who formulated it.'}]}],self.root))
 def test_documented_credential_for_another_brand_stays_available(self):
  (self.root/'brand-identity/story.md').write_text('The founder’s father is a pharmacist. He formulated the products.')
  got=C.planner_types(self.catalog,self.root)
  self.assertIn('father is a pharmacist',got)
  self.assertEqual(C.identity_problems([{'id':'x','angle':'His father is a pharmacist who formulated it.'}],self.root),[])
 def test_missing_identity_does_not_fall_back_to_catalogue(self):
  got=C.planner_types(self.catalog,self.root)
  self.assertIn('No identity source supplied',got)
  self.assertNotIn('A pharmacist formulating',got)
  self.assertTrue(C.identity_problems([{'id':'x','angle':'I am a dermatologist.'}],self.root))
 def test_non_credential_origin_angle_is_not_blocked(self):
  self.assertEqual(C.identity_problems([{'id':'x','angle':'Coco took her family recipe to Gotha Cosmetics in Milan.'}],self.root),[])
if __name__=='__main__':unittest.main()
