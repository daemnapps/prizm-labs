import unittest
from make_voice import preview_text


class VoicePreviewText(unittest.TestCase):
    def test_short_actual_dialogue_meets_provider_minimum(self):
        line = "What you doing on my neck?"
        text = preview_text(line)
        self.assertGreaterEqual(len(text), 100)
        self.assertEqual(text.replace(line, "").strip(), "")

    def test_normal_dialogue_unchanged(self):
        line = "A line from the brief. " * 8
        self.assertEqual(preview_text(line), line.strip())

    def test_long_dialogue_capped(self):
        self.assertEqual(len(preview_text("A" * 1100)), 1000)

    def test_blank_refused(self):
        with self.assertRaises(ValueError):
            preview_text("  ")


if __name__ == "__main__":
    unittest.main()
