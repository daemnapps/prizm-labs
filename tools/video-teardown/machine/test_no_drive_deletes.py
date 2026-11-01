"""No machine delete on Drive (2026-10-18, LD-17 (Drive deletes out); the wall in
components/CLAUDE.md): a re-pull moves a post that left the top ten to
`<creator>/dropped/` and a document rebuild leaves the older frame pictures.
Offline: temp folders stand in for the Drive, through library's and chain's
own module attributes."""
import os, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library as L
import chain as C
import sourcing as S
import gdoc as G


class NoDeletes:
    """Every delete call fails the test the moment it is reached."""
    def __init__(self):
        self.calls = []

    def _spy(self, name):
        def hit(*a, **k):
            self.calls.append((name, a))
            raise AssertionError(f"{name} reached on the Drive side: {a}")
        return hit

    def __enter__(self):
        self.patches = [mock.patch.object(Path, "unlink", self._spy("Path.unlink")),
                        mock.patch.object(shutil, "rmtree", self._spy("shutil.rmtree")),
                        mock.patch.object(os, "remove", self._spy("os.remove")),
                        mock.patch.object(os, "unlink", self._spy("os.unlink"))]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        return False


class Reconcile(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.home = self.tmp / "creator"
        self.posts = self.home / "posts"
        self.posts.mkdir(parents=True)
        self.said = []
        self.patches = [
            mock.patch.object(L, "creator_dir", lambda handle, make=True: self.home),
            mock.patch.object(L, "post_dir", lambda handle, i, code, make=True: self.posts / f"{i:02d}-{code}"),
            mock.patch.object(S, "say", self.said.append)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        shutil.rmtree(self.tmp)

    def post(self, name, *marks):
        d = self.posts / name
        d.mkdir()
        (d / "video.mp4").write_bytes(b"\0" * 8)
        for m in marks:
            (d / m).mkdir() if m == "teardown" else (d / m).write_text("")
        return d

    def test_an_unkept_post_moves_to_dropped_and_marked_ones_stay(self):
        self.post("01-keep")
        self.post("02-gone")
        self.post("03-torn", "teardown")
        self.post("04-picked", "SELECTED")
        with NoDeletes() as spy:
            S.reconcile("someone", [{"shortCode": "keep"}])
        self.assertEqual(spy.calls, [])
        self.assertEqual(sorted(d.name for d in self.posts.iterdir()), ["01-keep", "03-torn", "04-picked"])
        self.assertTrue((self.home / "dropped" / "02-gone" / "video.mp4").is_file())
        self.assertEqual([m for m in self.said if "dropped/" in m], ["  moved 02-gone to dropped/02-gone — out of the top ten"])

    def test_a_second_drop_of_the_same_name_gets_a_suffix(self):
        with NoDeletes() as spy:
            for n in range(3):
                d = self.post("05-again")
                (d / "pull.txt").write_text(str(n))
                S.reconcile("someone", [])
        self.assertEqual(spy.calls, [])
        dropped = self.home / "dropped"
        self.assertEqual(sorted(d.name for d in dropped.iterdir()), ["05-again", "05-again-2", "05-again-3"])
        self.assertEqual([(dropped / x / "pull.txt").read_text() for x in ("05-again", "05-again-2", "05-again-3")],
                         ["0", "1", "2"])                    # never an overwrite


class DocRebuild(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.mirror = self.tmp / "drive" / "run-x"
        self.runs = self.tmp / "runs"
        self.src = self.runs / "run-x" / "frames" / "frames"
        self.src.mkdir(parents=True)
        self.patches = [
            mock.patch.object(C, "run_mirror_dir", lambda slug: self.tmp / "drive" / slug),
            mock.patch.object(C, "runs_root", lambda create=True: self.runs),
            mock.patch.object(G, "drive_id", lambda p: f"id-{p.name}")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        shutil.rmtree(self.tmp)

    def test_a_rebuild_leaves_old_pictures_and_names_only_current_frames(self):
        (self.src / "frame-01.png").write_bytes(b"first build")
        first = G.ids_from_drive("run-x")
        (self.src / "frame-01.png").write_bytes(b"second build")
        (self.src / "frame-02.png").write_bytes(b"new frame")
        doc = self.mirror / "frames" / "doc"
        (doc / "frame-09-0123456789.png").write_bytes(b"a frame this build no longer has")
        with NoDeletes() as spy:
            got = G.ids_from_drive("run-x")
        self.assertEqual(spy.calls, [])
        old = first["frame-01"][len("id-"):]
        self.assertTrue((doc / old).is_file(), "the older picture stays")
        self.assertTrue((doc / "frame-09-0123456789.png").is_file())
        self.assertEqual(sorted(got), ["frame-01", "frame-02"])
        self.assertNotEqual(got["frame-01"], first["frame-01"])      # the current picture, not the old one
        self.assertTrue(all((doc / v[len("id-"):]).is_file() for v in got.values()))
        self.assertEqual(len(list(doc.iterdir())), 4)


if __name__ == "__main__":
    unittest.main()
