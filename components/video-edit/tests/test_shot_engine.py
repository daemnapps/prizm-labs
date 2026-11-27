import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "video-edit" / "machine"))
sys.path.insert(0, str(ROOT / "ad-variations" / "machine"))
import multiply as MU  # noqa: E402
import shot_engine as SE  # noqa: E402
import swipe_edit as SW  # noqa: E402


def clip(path, colours, sound=True):
    """A small video of solid colours, one second each."""
    src = []
    for c in colours:
        src += ["-f", "lavfi", "-i", "color=c=%s:s=180x320:d=1:r=30" % c]
    n = len(colours)
    cmd = ["ffmpeg", "-v", "error", "-y"] + src
    if sound:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=%d" % n]
    cmd += ["-filter_complex", "".join("[%d:v]" % i for i in range(n)) + "concat=n=%d:v=1:a=0[v]" % n, "-map", "[v]"]
    if sound:
        cmd += ["-map", "%d:a" % n, "-c:a", "aac"]
    subprocess.run(cmd + ["-pix_fmt", "yuv420p", str(path)], check=True)
    return path


class Both(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.TemporaryDirectory()
        cls.d = Path(cls.t.name)
        cls.ad = clip(cls.d / "ad.mp4", ["red", "blue", "green"])
        cls.own = clip(cls.d / "own.mp4", ["yellow", "white"], sound=False)

    @classmethod
    def tearDownClass(cls):
        cls.t.cleanup()

    def own_find(self, brand, seen, seconds, used, **kw):
        if len(used) >= 1:
            return None
        used.add(("own", 0))
        return {"file": str(self.own), "in": 0.0, "seconds": seconds, "rights": "allowed", "copy": "full", "shows": "yellow", "score": 1}

    def test_the_cuts_are_found(self):
        self.assertEqual([round(s["seconds"]) for s in SE.shots(self.ad)], [1, 1, 1])

    def test_one_change_is_free_keeps_the_length_and_the_sound(self):
        p = MU.plan(self.ad, "acme", changes=[{"do": "shot", "shot": "K02", "show": "yellow"}], find=self.own_find)
        self.assertEqual((p["credits"], p["ready"]), (0, 1))
        m = MU.make(p, self.d / "out")[0]
        self.assertTrue(all(m["checks"].values()), m)
        self.assertEqual(m["seconds"], 3.0)

    def test_a_person_swap_prices_only_its_own_shot_and_is_never_sent_here(self):
        p = MU.plan(self.ad, "acme", changes=[{"do": "person", "shot": "K02", "with": "cast.png"}], find=self.own_find)
        self.assertFalse(p["versions"][0]["ready"])
        self.assertEqual(p["credits"], MU.MIN_CLIP * MU.CREDITS_S)
        self.assertEqual(MU.make(p, self.d / "out2"), [])

    def test_a_clip_shorter_than_its_shot_is_refused_never_slowed(self):
        with self.assertRaisesRegex(ValueError, "never slowed"):
            SE.build([{"file": str(self.own), "in": 1.5, "seconds": 1.0}], self.d / "x.mp4")

    def test_the_swipe_edit_names_its_gaps_and_will_not_cut_with_one(self):
        ours = {"K01": "yellow", "K02": "blue", "K03": "green"}
        p = SW.plan(self.ad, "acme", ours=ours, find=self.own_find)
        self.assertEqual((p["owned"], p["gaps"], p["ready"]), (1, 2, False))
        self.assertEqual(p["credits"], 2 * SW.MIN_CLIP * SW.CREDITS_S)
        with self.assertRaises(SystemExit):
            SW.cut(p, self.d / "s.mp4")

    def test_the_swipe_edit_cuts_to_the_swipe_s_lengths(self):
        def many(brand, seen, seconds, used, **kw):
            f = clip(self.d / ("o%d.mp4" % len(used)), ["yellow", "white"], sound=False)
            used.add((str(f), 0))
            return {"file": str(f), "in": 0.2, "seconds": seconds, "rights": "allowed", "copy": "full"}
        p = SW.plan(self.ad, "acme", ours={"K01": "a", "K02": "b", "K03": "c"}, find=many)
        r = SW.cut(p, self.d / "s.mp4")
        self.assertTrue(r["checks"]["same shots"] and r["checks"]["no footage twice"] and r["checks"]["length"], r)


if __name__ == "__main__":
    unittest.main()
