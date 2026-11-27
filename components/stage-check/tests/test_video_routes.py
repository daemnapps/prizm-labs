"""Route-specific video evidence and repair isolation; no model, subprocess or platform calls."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import stage_check as S

class VideoRoutes(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.reg=self.root/'register.json';self.patch=mock.patch.multiple(S,REPO=self.root,REGISTER=self.reg);self.patch.start()
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def piece(self,kind='video-creator',route='creator',bare=False):
  work=self.root/'runs/video-teardown/_work/test';(work/'stages').mkdir(parents=True,exist_ok=True)
  state={'brand':'testbrand','stages':{'stage5':{'status':'done'}}}
  if route:state['production_route']=route
  (work/'run.json').write_text(json.dumps(state));(work/'stages/2-spec.md').write_text('Source specification')
  (work/'stages/5-brief.md').write_text('Film: at the sink\nSay: hello\nHear: room tone\nWearing: plain shirt\nOn screen: name')
  self.reg.write_text(json.dumps({'briefs':{} if bare else {'testbrand_brief-0001':{'brief':'brief-0001','type':kind,'brand':'testbrand','run':'test'}}}))
  return S.Piece('test' if bare else 'testbrand_brief-0001')
 def test_creator_finishes_at_filming_brief_without_ai_media(self):
  p=self.piece()
  with mock.patch.object(S,'_sh',side_effect=AssertionError('must not run a command')):
   rows=S.check_piece(p,do_fix=True,quiet=True)
  self.assertEqual(p.lane,'video-creator');self.assertTrue(all(r['ok'] for r in rows),rows)
  self.assertFalse({'production','edit','card'} & {r['step'] for r in rows})
  rec=json.loads((self.root/'runs/stage-check/testbrand'/p.label/'latest.json').read_text())
  self.assertEqual(rec['maker_route'],'creator');self.assertIn('brief only',rec['completion_scope'])
 def test_missing_creator_writing_does_not_invoke_ai_repair(self):
  p=self.piece();state=json.loads((p.lane_run/'run.json').read_text());state['stages']={};(p.lane_run/'run.json').write_text(json.dumps(state))
  with mock.patch.object(S,'_sh',side_effect=AssertionError('must not run AI repair')):
   rows=S.check_piece(p,do_fix=True,quiet=True)
  self.assertFalse(next(r for r in rows if r['step']=='writing')['ok'])
 def test_ai_route_still_requires_generated_clips(self):
  p=self.piece('video-ai','ai')
  with mock.patch.object(S,'_cards',return_value=[]):rows=S.check_piece(p,quiet=True)
  self.assertEqual(p.lane,'video');self.assertFalse(next(r for r in rows if r['step']=='production')['ok'])
 def test_source_organic_is_not_a_maker_route(self):
  p=self.piece('video',None);(p.lane_run/'run.json').write_text(json.dumps({'route':{'lane':'ORGANIC'}}));p=S.Piece('testbrand_brief-0001')
  with mock.patch.object(S,'_sh',side_effect=AssertionError('must not guess a route')):
   rows=S.check_piece(p,do_fix=True,quiet=True)
  self.assertEqual(p.lane,'video-unresolved');self.assertEqual(len(rows),1);self.assertFalse(rows[0]['ok'])
 def test_conflicting_registry_and_run_stop_before_repairs(self):
  p=self.piece('video-ai','creator');self.assertEqual(p.lane,'video-unresolved')
  with mock.patch.object(S,'_sh',side_effect=AssertionError('must not repair a conflict')):
   rows=S.check_piece(p,do_fix=True,quiet=True)
  self.assertIn('conflict',rows[0]['why'])
 def test_founder_keeps_human_route(self):
  p=self.piece('video-creator','founder');self.assertEqual(p.maker_route,'founder');self.assertEqual(p.lane,'video-creator')
 def test_unregistered_video_is_found_on_video_plane(self):
  p=self.piece('video-creator','creator',bare=True);self.assertEqual(p.lane,'video-creator');self.assertEqual(p.brand,'testbrand')
 def test_explicit_image_path_is_not_a_video_run(self):
  folder=self.root/'runs/image-teardown/testbrand/image';folder.mkdir(parents=True)
  (folder/'run.json').write_text(json.dumps({'brand':'testbrand'}))
  self.assertEqual(S._video_runs(self.root,'runs/image-teardown/testbrand/image','testbrand'),[])
 def test_incomplete_filming_brief_is_held(self):
  p=self.piece();(p.lane_run/'stages/5-brief.md').write_text('Film: [UNFILLED]\nSay: hi')
  ok,why=S.check(p,'creator_brief');self.assertFalse(ok);self.assertIn('Hear',why);self.assertIn('unresolved',why)
 def test_direct_fix_cannot_bypass_route_guard(self):
  p=self.piece()
  with mock.patch.object(S,'_sh',side_effect=AssertionError('route bypass')):
   ok,why=S.fix(p,{'fix':'cmd:python3 components/video-production/machine/run.py start x'})
  self.assertFalse(ok);self.assertIn('no AI repair',why)
if __name__=='__main__':unittest.main()
