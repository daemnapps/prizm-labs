"""The re-edit hand-off reads everything from the editor brief: its shots, the files it names, what to deliver."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import reedit_handoff as RE  # noqa: E402

BRIEF = """# A cut

## Sources (all existing)
- Song: `runs/x/song.mp3`
- Clips: `runs/x/clips_hd/<shot>.mp4`

## Picture edit

| Cut in → out | Shot / source | What's on screen | Lyric over it |
|---|---|---|---|
| 0:00.00 → 0:05.37 | 001 | a table | words |
| 0:05.37 → 0:10.71 | 041 (4.0 s clip) | a brush | words |
| 0:10.71 → 0:12.00 | End card: real packshot | packshot | — |

## Deliver
- `cut.mp4`
- Same cut with the hook pictures (h-a 024, h-b 018, h-d 004) swapped in.

## Notes
- nothing
"""


class ReeditHandoff(unittest.TestCase):
    def test_shots_come_from_the_picture_table(self):
        self.assertEqual(RE.shots(BRIEF), ["001", "041"])

    def test_the_clip_folder_comes_from_the_brief(self):
        self.assertEqual(RE.clip_dir(BRIEF, None), "runs/x/clips_hd")

    def test_one_version_per_hook_the_brief_names(self):
        self.assertEqual(RE.deliverables("k", BRIEF), ["k-control.mp4", "k-v1.mp4", "k-v2.mp4", "k-v3.mp4"])
        self.assertEqual(RE.deliverables("k", BRIEF.replace("h-a 024, h-b 018, h-d 004", "")), ["k-control.mp4"])

    def test_a_run_sheet_says_never_regenerate(self):
        rec = {"title": "t", "brief": "k", "deliver": ["k-control.mp4"], "shots": ["001"], "clips": None,
               "refs": {"runs/x/song.mp3": "refs/song.mp3"}, "on_drive": {}}
        md = RE.run_md(rec, "Shared Assets/runs/handoffs/video-editor/b/k")
        self.assertIn("Never regenerate a clip", md)
        self.assertIn("## B · An agent", md)
        self.assertIn("No hook versions", md)


if __name__ == "__main__":
    unittest.main()
