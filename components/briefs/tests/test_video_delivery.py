"""A brief's embedded openings survive packing and are not hidden by its index."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))
import ledger
import video_delivery


class VideoDelivery(unittest.TestCase):
    def test_legacy_handoff_keeps_its_nested_brief_and_asset_names(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            nested = folder / "briefs/brief-0001/brief.md"
            nested.parent.mkdir(parents=True)
            nested.write_text("# Original brief\n")
            (folder / "handoff.md").write_text("# Editor instructions\n")
            self.assertEqual(video_delivery.pack(folder, standalone=False), [])
            self.assertFalse((folder / "VIDEO-DELIVERY.md").exists())
            self.assertIn("one distinct thumbnail", nested.read_text())
            self.assertTrue(nested.read_text().startswith("# Original brief\n"))
            self.assertIn("one distinct thumbnail", (folder / "handoff.md").read_text())

    def test_embedded_openings_remain_visible_after_repeated_pack(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "runs/handoffs/video-editor/acme/acme_widget_brief-0001"
            folder.mkdir(parents=True)
            original = "# A game\n\n### The openings: generate every hook in the set\n\n**Opening 1 · Control**\n\n**Thumbnail:** A collision.\n\n**Opening 2 · Jump**\n\n**Thumbnail:** The jump.\n"
            (folder / "BRIEF.md").write_text(original)
            with patch.object(ledger, "ROOT", d):
                for _ in range(2):
                    ledger.write_pack(folder.name, "all AI", str(folder.relative_to(d)))
            text = (folder / "BRIEF.md").read_text()
            self.assertTrue(text.startswith(original))
            self.assertEqual(text.count(video_delivery.START), 1)
            index = (folder / "PACK.md").read_text()
            hooks = index.split("## 3 ")[1].split("## 4 ")[0]
            self.assertIn("inside `BRIEF.md`", hooks)
            self.assertNotIn("none in this pack", hooks)
            self.assertIn("VIDEO-DELIVERY.md", index)
            self.assertIn("covers_stage.py run", text)
            self.assertIn("Raw", text.replace("raw", "Raw"))

    def test_broken_marker_does_not_truncate_a_creative_brief(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "BRIEF.md"
            text = "# Ad\n" + video_delivery.START + "\nImportant creative instructions\n"
            p.write_text(text)
            with self.assertRaises(ValueError):
                video_delivery.pack(d)
            self.assertEqual(p.read_text(), text)


if __name__ == "__main__":
    unittest.main()
