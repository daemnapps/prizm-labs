import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import shared_shots as S


def frame(file, flip=False):
    im = Image.new("L", (64, 64))
    for x in range(64):
        for y in range(64):
            im.putpixel((x, y), ((63 - x if flip else x) * 4 + y) % 256)
    im.save(file)


def sec(gid, first, who="person · A · look"):
    return {"id": gid, "elements": [who, "place · ROOM"], "swipe": {"shots": [{"id": first, "first": first + ".jpg"}]},
            "scenes": [gid], "frames": [{"what": "first frame", "from": gid}]}


class Shared(unittest.TestCase):
    def run_group(self, sections):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            frame(t / "K1.jpg"); frame(t / "K2.jpg"); frame(t / "K3.jpg", flip=True)
            (t / "storyboard.json").write_text(json.dumps({"sections": sections}))
            got = S.group(t, frames=t)
            return got, json.loads((t / "storyboard.json").read_text())

    def test_alike_frames_share_the_first_picture(self):
        got, sb = self.run_group([sec("G1", "K1"), sec("G2", "K2")])
        self.assertEqual(got, {"G2": "G1"})
        self.assertEqual(sb["sections"][1]["start_picture"], "G1-F1")

    def test_a_different_frame_keeps_its_own_picture(self):
        got, _ = self.run_group([sec("G1", "K1"), sec("G2", "K3")])
        self.assertEqual(got, {})

    def test_another_person_keeps_their_own_picture(self):
        got, _ = self.run_group([sec("G1", "K1"), sec("G2", "K2", who="person · B · look")])
        self.assertEqual(got, {})


if __name__ == "__main__":
    unittest.main()
