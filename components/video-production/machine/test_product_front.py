"""product_front.py: the front view comes off the sheet, big, and is the sheet's own picture."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import product_front as PF  # noqa: E402


class Front(unittest.TestCase):
    def test_the_front_tile_only_and_big(self):
        with tempfile.TemporaryDirectory() as d:
            for w in (1656, 828):                                        # the grid, and the same sheet at half size
                k = w / 1656
                sheet, out = Path(d) / ("s%d.png" % w), Path(d) / ("o%d.png" % w)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=white:s=%dx%d" % (w, round(1856 * k)), "-vf",
                                "drawbox=x=%d:y=%d:w=%d:h=%d:color=red:t=fill,drawbox=x=%d:y=%d:w=%d:h=%d:color=blue:t=fill" % tuple(
                                    round(x * k) for x in (200, 200, 150, 300, 800, 200, 150, 300)), "-frames:v", "1", str(sheet)], check=True)
                PF.front(sheet, out)
                px = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-vf", "scale=40:40", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
                dots = [tuple(px[i:i + 3]) for i in range(0, len(px), 3)]
                self.assertTrue(any(r > 200 and g < 60 and b < 60 for r, g, b in dots))
                self.assertFalse(any(b > 200 and r < 60 for r, g, b in dots))
                h = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=height", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
                self.assertEqual(h, "1600")


if __name__ == "__main__":
    unittest.main()
