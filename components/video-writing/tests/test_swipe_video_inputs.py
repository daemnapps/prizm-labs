"""The structure judge must receive fast cuts at the frame map's sampling rate."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('swipe_video_input_test', Path(__file__).parents[1]/'machine/swipe_match.py')
SM = importlib.util.module_from_spec(spec);spec.loader.exec_module(SM)


class SwipeVideoInputs(unittest.TestCase):
    def test_uploaded_swipe_retains_eight_fps_video_and_full_prompt(self):
        calls=[]
        def req(url, **kwargs):
            calls.append(json.loads(kwargs['data']))
            return {'candidates':[{'content':{'parts':[{'text':'{"shots":[],"added":[]}'}]}}]}
        g=SimpleNamespace(key=lambda:'test-only',upload_cached=lambda *a:('test-uri','video/mp4'),req=req,BASE='https://invalid.test')
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'source.mp4';video.write_bytes(b'fixture')
            with patch.object(SM,'_gemini_tools',return_value=g):
                SM.ask_judge('### 1. shot K27 at 32.600 seconds','Our complete brief',video)
        parts=calls[0]['contents'][0]['parts']
        self.assertEqual(parts[0]['video_metadata'],{'fps':8})
        self.assertEqual(parts[0]['file_data']['file_uri'],'test-uri')
        self.assertIn('32.600',parts[1]['text'])
        self.assertIn('Our complete brief',parts[1]['text'])

    def test_missing_video_cannot_fall_back_to_text_only(self):
        with self.assertRaisesRegex(RuntimeError,'never trusts the notes alone'):
            SM.ask_judge('notes','brief',None)


if __name__=='__main__':unittest.main()
