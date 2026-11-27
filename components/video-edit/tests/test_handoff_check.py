"""The hand-off checklist and the editor's door read a Studio pack (no network, no live run)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import open_brief as OB  # noqa: E402
import handoff_check as HC  # noqa: E402


def studio_pack(root, key="acme_widget_brief-0001", blank=False):
    f = Path(root) / "runs" / "handoffs" / "video-editor" / "acme" / key
    for d in ("made", "voice", "returned", "edit", "hyperframes", "refs/S1-shot-1"):
        (f / d).mkdir(parents=True, exist_ok=True)
    (f / "BRIEF.md").write_text("# The Widget Story\n\n" + "x" * 80)
    for doc in ("RUN.md", "CLIPS.md", "TIMELINE.html", "handoff.md"):
        (f / doc).write_text("x" * 80)
    (f / "run.json").write_text(json.dumps({"steps": [1]}) + " " * 60)
    (f / "ELEMENTS.md").write_text("| Element | File |\n|---|---|\n| person | p.png |\n" + " " * 40)
    scenes = [{"scene": "S1", "status": "needs clips", "clips": ["S1-shot-1"]}]
    if blank:
        scenes.append({"scene": "S2", "status": "needs clips", "clips": ["S2-shot-1"]})
    (f / "clips.json").write_text(json.dumps({"key": key, "production": "idea-1", "title": "The Widget Story", "scenes": scenes}))
    (f / "refs" / "S1-shot-1" / "first.jpg").write_bytes(b"j")
    (f / "voice" / "01-S1.mp3").write_bytes(b"a")
    (f / "edit" / (key + ".premiere.xml")).write_text("<xmeml/>")
    (f / "hyperframes" / "index.html").write_text("<html></html>")
    return f


class StudioPackLayout(unittest.TestCase):
    def test_the_editors_door_sees_a_studio_pack(self):
        with tempfile.TemporaryDirectory() as t:
            f = studio_pack(t)
            i = OB.info(f)
            self.assertTrue(i["hyperframes"] and i["premiere"])
            self.assertEqual(OB.title_of(f), "The Widget Story")
            self.assertEqual(OB.hyperframes_dir(f), f / "hyperframes")

    def test_a_complete_pack_passes_its_pack_and_editor_checks(self):
        with tempfile.TemporaryDirectory() as t:
            f = studio_pack(t)
            r = HC.check(f, Path(t), None, None)
            bad = [c["check"] for c in r["checks"] if not c["ok"] and c["group"] in ("Pack", "Clips", "Edit files", "Editor")]
            self.assertEqual(bad, [])

    def test_a_clip_without_reference_frames_fails(self):
        with tempfile.TemporaryDirectory() as t:
            f = studio_pack(t, blank=True)
            r = HC.check(f, Path(t), None, None)
            refs = [c for c in r["checks"] if c["check"].startswith("Every clip to make")][0]
            self.assertFalse(refs["ok"])
            self.assertIn("S2-shot-1", refs["evidence"])

    def test_an_error_note_older_than_the_run_sheet_is_spent(self):
        with tempfile.TemporaryDirectory() as t:
            f = studio_pack(t)
            note = f / "RUN-SHEET-MISSING.txt"
            note.write_text("could not be written")
            old = os.path.getmtime(f / "RUN.md") - 60
            os.utime(note, (old, old))
            r = HC.check(f, Path(t), None, None)
            self.assertTrue([c for c in r["checks"] if c["check"] == "No build errors left in the pack"][0]["ok"])

    def test_a_pack_without_its_front_page_fails(self):
        with tempfile.TemporaryDirectory() as t:
            f = studio_pack(t)
            (f / "handoff.md").unlink()
            r = HC.check(f, Path(t), None, None)
            self.assertFalse([c for c in r["checks"] if c["check"] == "Front page (handoff.md)"][0]["ok"])

    def test_a_run_sheet_naming_other_clips_than_the_clip_list_fails(self):
        with tempfile.TemporaryDirectory() as t:
            f = studio_pack(t)
            doc = json.loads((f / "clips.json").read_text())
            doc["clips"] = [{"id": "S1", "tool": "gen.take", "return": "returned/k_asset-02.mp4"},
                            {"id": "S2.1-2", "tool": "gen.take", "return": "returned/k_asset-04-shots1-2.mp4"},
                            {"id": "END-card", "tool": "edit", "return": "returned/k_end-card.mp4"}]
            (f / "clips.json").write_text(json.dumps(doc))
            (f / "run.json").write_text(json.dumps({"steps": [
                {"medium": "image", "asset": "k_asset-01.png"}, {"medium": "video", "asset": "k_asset-02.mp4"},
                {"medium": "image", "asset": "k_asset-03.png"}, {"medium": "video", "asset": "k_asset-04.mp4"}]}))
            r = HC.check(f, Path(t), None, None)
            one = [c for c in r["checks"] if c["check"] == "Run sheet and clip list name the same clips"][0]
            self.assertFalse(one["ok"])
            self.assertIn("S2.1-2", one["evidence"])
            (f / "run.json").write_text(json.dumps({"steps": [
                {"medium": "video", "asset": "k_asset-02.mp4"}, {"medium": "video", "asset": "k_asset-04-shots1-2.mp4"}]}))
            r = HC.check(f, Path(t), None, None)
            self.assertTrue([c for c in r["checks"] if c["check"] == "Run sheet and clip list name the same clips"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
