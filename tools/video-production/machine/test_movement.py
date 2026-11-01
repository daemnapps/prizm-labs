"""movement.py: a real person's movement goes with every clip that has a person, picked by what the scene does."""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location("movement", HERE / "movement.py")
mv = importlib.util.module_from_spec(sp)
sp.loader.exec_module(mv)

BANK = [{"id": "lively", "file": "a.mp4", "seconds": 14, "talks": True, "does": ["hand gestures", "holds product"]},
        {"id": "calm", "file": "b.mp4", "seconds": 14, "talks": True, "does": ["points", "touches cheek", "calm"]},
        {"id": "silent", "file": "c.mp4", "seconds": 8, "talks": False, "does": ["points", "cheek"]}]


class Movement(unittest.TestCase):
    def test_picks_by_what_the_scene_does(self):
        self.assertEqual(mv.pick("she points to the cheek, calm", entries=BANK)[0]["id"], "calm")
        self.assertEqual(mv.pick("holds the product up", entries=BANK)[0]["id"], "lively")

    def test_a_talking_clip_never_gets_a_silent_performance(self):
        self.assertNotIn("silent", [e["id"] for e in mv.pick("points cheek", talking=True, entries=BANK, n=3)])

    def test_the_piece_is_five_to_ten_seconds(self):
        self.assertEqual(mv.piece(BANK[0], 3)["seconds"], 5.0)
        self.assertEqual(mv.piece(BANK[0], 12)["seconds"], 10.0)

    def test_no_person_no_movement(self):
        self.assertEqual(mv.for_call({"id": "C", "people": [], "duration": 6}, "points"), [])

    def test_prepared_without_sound_or_colour(self):
        import tempfile
        cmds = []
        with tempfile.TemporaryDirectory() as t:
            mv.prepare(Path("in.mp4"), Path(t) / "out.mp4", 0, 6, runner=cmds.append)
        self.assertIn("-an", cmds[0])
        self.assertIn("format=gray", cmds[0][cmds[0].index("-vf") + 1])

    def test_the_prompt_keeps_the_hands_on_the_prompt(self):
        self.assertIn("Where the hand goes and what it touches is what this prompt says", mv.LINE)

    def test_explicit_selection_is_stable_and_unknown_id_refused(self):
        from unittest.mock import patch
        call = {'id': 'G01-C1', 'people': ['yai'], 'talking': True, 'duration': 6}
        with patch.object(mv, 'bank', return_value=BANK):
            self.assertEqual(mv.for_call(call, 'product', 'calm')[0]['id'], 'calm')
            self.assertEqual(mv.for_call(call, 'product', 'none'), [])
            with self.assertRaises(ValueError): mv.for_call(call, 'product', 'missing')

    def test_prepared_motion_is_reused_across_runs_and_source_change_invalidates(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); src = root / 'source.mp4'; src.write_bytes(b'original')
            calls = []
            def prepare(src, dest, *args):
                calls.append(str(src)); dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b'prepared'); return dest
            ref = {'id': 'calm', 'file': 'refs/m.mp4', 'src': 'source.mp4', 'from': 0., 'seconds': 6.}
            with patch.object(mv, 'HERE', root / 'tools/video-production/machine'), patch.object(mv, 'prepare', side_effect=prepare):
                mv.make(root / 'run1', ref); mv.make(root / 'run2', ref)
                self.assertEqual(len(calls), 1)
                src.write_bytes(b'updated')
                mv.make(root / 'run1', ref)
                self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
