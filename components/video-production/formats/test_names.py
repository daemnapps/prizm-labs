"""The video names are locked (owner, 2026-11-19: "hold this naming list, do not change it ever again").
This test fails on any change to formats/names.json. Change it only on the owner's own word, and change
this test in the same commit, quoting him."""
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
LOCKED = {
    "production_format": ["Single presenter", "Song ad", "Narrator montage", "Multi-speaker scene", "Short movie",
                          "Text thread"],
    "style": ["Phone-camera UGC", "Family 3D animation", "Low poly", "Anime", "1950s hand-drawn cel", "Stick explainer",
              # + four on the owner's word, 2026-11-21 (Preset Library page, "Yes, add all 4")
              "Claymation", "Needle felt", "Art toy", "Cinematic live action"],
    # + five added on the owner's word, 2026-11-19 (formats page, "Add it" on D1-D5)
    "script_format": ["Remedy", "Demonstration", "Expert consultation", "Comedy skit", "Meme", "Micro-drama",
                      "Testimonial montage", "Era roll call", "Street interview", "Founder story",
                      "Personal story, then the fix", "Tips, then the pitch", "Deal walkthrough", "Glow-up"],
    # the scroll stoppers, a fourth list on the owner's word, 2026-11-19 ("Yes, add those 4")
    "hook_format": ["VFX stunt", "Fake billboard stunt", "Dramatic continuation", "Weird stunt, then the pitch",
                    "Green screen reaction", "Dramatized object", "Up close body part",
                    "Swiped viral clip", "Split screen", "3D body animation"],
    "headline_format": ["Question", "Story open", "Bold claim", "Problem callout", "Command interrupt", "How-to promise",
                        "Curiosity gap", "Relatable moment", "List promise", "Result first", "Skit line", "Song lyric",
                        "Label text", "Regret open", "Reaction line", "POV caption", "Comment reply"],
    "length": ["Short", "Long"],   # owner, 2026-11-19
}


class VideoNamesLocked(unittest.TestCase):
    def setUp(self):
        self.names = json.loads((HERE / "names.json").read_text(encoding="utf-8"))

    def test_the_names_are_the_locked_names(self):
        for kind, want in LOCKED.items():
            self.assertEqual([n["name"] for n in self.names[kind]["names"]], want, kind)

    def test_the_page_uses_only_these_names(self):
        calls = json.loads((REPO / "components" / "stage-handoff" / "chains" / "video-format-style-calls.json").read_text(encoding="utf-8"))
        lists = calls["lists"]
        self.assertTrue({x["name"] for x in lists["production"]} <= set(LOCKED["production_format"]))
        self.assertTrue({x["name"] for x in lists["looks"]} <= set(LOCKED["style"]))
        self.assertTrue({x["name"] for x in lists["script"]} <= set(LOCKED["script_format"]))
        self.assertTrue({x["name"] for x in lists.get("hook") or []} <= set(LOCKED["hook_format"]))


if __name__ == "__main__":
    unittest.main()
