"""PF-21 (pictures reach every Mac): an email's pictures reach every Mac and page server that draws it (the team,
2026-10-29: the team's 47 designed pictures were on no other Mac and not on Drive, and a page server shot whole emails
with their cut pictures missing).

Offline: a fake Drive (put / get), no Chrome, no git, no network.

    /usr/bin/python3 test_pf21_pictures_reach.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "design"))
import layout_file as LF  # noqa: E402
import look  # noqa: E402
import ask  # noqa: E402
import sync as S  # noqa: E402

BRAND, LABEL = "fx", "fx-nov-03"


class Drive:
    """put records each call; fail=True makes it raise; files it holds can be got back."""

    def __init__(self, fail=False):
        self.puts, self.fail, self.held = [], fail, {}

    def put(self, files, parts):
        if self.fail:
            raise RuntimeError("Drive said 403")
        self.puts.append(([Path(f).name for f in files], list(parts)))
        return "api", ["Shared Assets/%s/%s" % ("/".join(parts), Path(f).name) for f in files], ""

    def get(self, parts, name, dest):
        b = self.held.get(name)
        if b is None:
            return None
        p = Path(dest) / name
        p.write_bytes(b)
        return str(p)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, str(self.root))
        self.run_dir = self.root / "runs" / "email-production" / BRAND / LABEL
        for d in ("design", "media", "klaviyo/assets"):
            (self.run_dir / d).mkdir(parents=True)
        (self.run_dir / "design" / "email.json").write_text(json.dumps({"sections": [
            {"s": "hero_photo", "photo": "run:media/hero.png"},
            {"s": "card", "photo": "run:media/routine.png", "more": {"photo": "run:media/hero.png"}},
            {"s": "proof", "photo": "drive:abc"}]}))
        (self.run_dir / "klaviyo" / "card.json").write_text(json.dumps({"brand": BRAND, "label": LABEL}))
        (self.run_dir / "klaviyo" / "email.html").write_text('<img src="assets/s01.jpg"><img src="assets/s02.jpg">')

    def media(self, *names):
        for n in names:
            (self.run_dir / "media" / n).write_bytes(n.encode())


class MirrorMedia(Base):
    def test_only_the_named_run_media_pictures_go_up_once(self):
        self.media("hero.png", "routine.png", "unused.png")
        drive = Drive()
        got = LF.mirror_media(BRAND, self.run_dir, reach=drive)
        self.assertEqual(drive.puts, [(["hero.png", "routine.png"], ["runs", "email-production", BRAND, LABEL, "media"])])
        self.assertEqual((got["put"], got["not_here"], got["error"]), (["hero.png", "routine.png"], [], None))
        self.assertEqual(sorted(LF.media_ledger(self.run_dir)), ["hero.png", "routine.png"])
        again = LF.mirror_media(BRAND, self.run_dir, reach=drive)
        self.assertEqual((len(drive.puts), again["already"]), (1, ["hero.png", "routine.png"]))

    def test_a_changed_picture_goes_up_again(self):
        self.media("hero.png", "routine.png")
        drive = Drive()
        LF.mirror_media(BRAND, self.run_dir, reach=drive)
        (self.run_dir / "media" / "hero.png").write_bytes(b"redone")
        got = LF.mirror_media(BRAND, self.run_dir, reach=drive)
        self.assertEqual((drive.puts[-1][0], got["put"]), (["hero.png"], ["hero.png"]))

    def test_a_picture_not_on_this_mac_is_named(self):
        self.media("hero.png")
        got = LF.mirror_media(BRAND, self.run_dir, reach=Drive())
        self.assertEqual(got["not_here"], ["routine.png"])

    def test_a_failed_put_is_named_and_nothing_is_ledgered(self):
        self.media("hero.png", "routine.png")
        got = LF.mirror_media(BRAND, self.run_dir, reach=Drive(fail=True))
        self.assertEqual(got["error"], "RuntimeError: Drive said 403")
        self.assertEqual((got["put"], LF.media_ledger(self.run_dir)), ([], {}))


class TheDone(Base):
    def done(self, drive):
        filed = []
        fake = types.ModuleType("review_request")
        fake.file_request = lambda **kw: filed.append(kw) or {"path": "review/x.json"}
        with mock.patch.dict(sys.modules, {"review_request": fake}), mock.patch.object(look, "reach", lambda: drive):
            ok, said = ask.mark_done({"brand": BRAND, "label": LABEL, "by": "the team", "code": "nov-03"}, root=self.root)
        card = json.loads((self.run_dir / "klaviyo" / "card.json").read_text())
        return ok, said, card, filed

    def test_the_done_puts_the_pictures_up_first(self):
        self.media("hero.png", "routine.png")
        drive = Drive()
        ok, said, card, filed = self.done(drive)
        self.assertTrue(ok)
        self.assertEqual(drive.puts[0][0], ["hero.png", "routine.png"])
        self.assertEqual(card["eve_done"]["by"], "the team")
        self.assertEqual(len(filed), 1)

    def test_a_picture_nowhere_stops_the_done_by_name(self):
        self.media("hero.png")
        ok, said, card, filed = self.done(Drive())
        self.assertFalse(ok)
        self.assertIn("routine.png", said)
        self.assertNotIn("eve_done", card)
        self.assertEqual(filed, [])

    def test_a_failed_put_stops_the_done_by_name(self):
        self.media("hero.png", "routine.png")
        ok, said, card, filed = self.done(Drive(fail=True))
        self.assertFalse(ok)
        self.assertIn("Drive said 403", said)
        self.assertIn("hero.png", said)
        self.assertNotIn("eve_done", card)

    def test_pictures_already_up_from_another_mac_let_the_done_through(self):
        """Up once (in the ledger), absent here: the team's Done on the team's email is not stopped."""
        (self.run_dir / "media" / LF.MEDIA_LEDGER).write_text(json.dumps({"put": {"hero.png": "a", "routine.png": "b"}}))
        ok, said, card, filed = self.done(Drive())
        self.assertTrue(ok, said)


class PushMedia(Base):
    def test_every_designed_email_one_line(self):
        self.media("hero.png", "routine.png")
        with mock.patch.object(S, "RUNS", self.root / "runs" / "email-production"):
            lines = S.push_media(reach=Drive())
        self.assertEqual(lines, ["%s/%s: 2 put · 0 already up" % (BRAND, LABEL)])


class ThePageServer(Base):
    def cuts(self, *names):
        for n in names:
            (self.run_dir / "klaviyo" / "assets" / n).write_bytes(n.encode())

    def test_a_shot_older_than_a_cut_is_not_kept(self):
        k = self.run_dir / "klaviyo"
        self.cuts("s01.jpg", "s02.jpg")
        shot = k / "whole-email.jpg"
        shot.write_bytes(b"jpg")
        future = time.time() + 5
        os.utime(str(shot), (future, future))
        self.assertTrue(S._shot_fresh(k / "email.html", shot))
        later = future + 5
        os.utime(str(k / "assets" / "s02.jpg"), (later, later))           # a cut landed after the shot
        self.assertFalse(S._shot_fresh(k / "email.html", shot))
        (k / "assets" / "s02.jpg").unlink()                             # a cut missing
        self.assertFalse(S._shot_fresh(k / "email.html", shot))

    def test_the_maker_brings_the_cuts_then_shoots(self):
        self.cuts("s01.jpg")
        drive = Drive()
        drive.held = {"s02.jpg": b"s02", "whole-email.jpg": b"old"}
        shot = []
        with contextlib.redirect_stdout(io.StringIO()):
            said = S.make_pictures([self.run_dir], pull=lambda b, r: LF.pull_build(b, r, reach=drive),
                              shoot=lambda r: shot.append(r), received=lambda runs: None)
        self.assertTrue((self.run_dir / "klaviyo" / "assets" / "s02.jpg").is_file())
        self.assertEqual((shot, said[str(self.run_dir)]), ([self.run_dir], "shot"))

    def test_the_maker_never_shoots_with_a_cut_still_missing(self):
        shot = []
        with contextlib.redirect_stdout(io.StringIO()):
            said = S.make_pictures([self.run_dir], pull=lambda b, r: LF.pull_build(b, r, reach=Drive()),
                              shoot=lambda r: shot.append(r), received=lambda runs: None)
        self.assertEqual(shot, [])
        self.assertEqual(said[str(self.run_dir)], "still missing on Drive: s01.jpg, s02.jpg")
        self.assertFalse((self.run_dir / "klaviyo" / "whole-email.jpg").exists())


if __name__ == "__main__":
    unittest.main()
