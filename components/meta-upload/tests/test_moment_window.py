"""A promo ad stops at the end of its moment's window (2026-11-03).

The brief's register record names its run; the run's vars/ask.md names the ask;
the ask's moment is read through the marketing calendar's moment_window, which
reads brands/<brand>/strategy/moments.json. No date is kept in this component.
Stdlib only: no PIL, no network, no key."""
import json, sys, tempfile, unittest
from datetime import date
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import build


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class MomentWindow(unittest.TestCase):

    def _repo(self, tmp, home="runs/image-teardown/zz-brand/bf-run", moment={"key": "black-friday"}):
        _write(tmp / "runs/creative-strategist/zz-brand/bf-2026/ask.json",
               json.dumps({"ask": "bf-2026", "asked": "2026-10-20", "moment": moment,
                           "offer": {"lines": ["Buy 2, get 1 free"]}}))
        _write(tmp / home / "vars" / "ask.md", "runs/creative-strategist/zz-brand/bf-2026/ask.json\n")

    def _brief(self, run="bf-run", opened="2026-10-31"):
        return {"brief": "brief-0311", "register": {"run": run, "opened": opened}}

    def _cal(self, win):
        cal = mock.Mock()
        cal.moment_window.return_value = win
        return cal

    def test_a_promo_brief_is_held_after_its_window(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._repo(tmp)
            cal = self._cal(("2026-11-27", "2026-11-30"))
            with mock.patch.object(build, "REPO", tmp), \
                 mock.patch.object(build.N, "find_brief", return_value=self._brief()), \
                 mock.patch.object(build, "_calendar", return_value=cal):
                during = build.moment_ended("zz-brand", "brief-0311", when=date(2026, 11, 30))
                after = build.moment_ended("zz-brand", "brief-0311", when=date(2026, 12, 1))
        self.assertIsNone(during)
        self.assertIn("black-friday ended 2026-11-30", after)
        self.assertIn("bf-2026", after)
        # the window asked for is the one the brief was made for: read from the day it was opened
        cal.moment_window.assert_called_with("zz-brand", "black-friday", date(2026, 10, 31))

    def test_a_video_run_names_its_ask_the_same_way(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._repo(tmp, home="runs/video-teardown/_work/bf-video")
            with mock.patch.object(build, "REPO", tmp), \
                 mock.patch.object(build.N, "find_brief", return_value=self._brief(run="bf-video")), \
                 mock.patch.object(build, "_calendar", return_value=self._cal(("2026-11-27", "2026-11-30"))):
                after = build.moment_ended("zz-brand", "brief-0311", when=date(2026, 12, 1))
        self.assertIn("black-friday ended", after)

    def test_a_brief_with_no_ask_or_no_moment_is_not_a_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._repo(tmp, moment=None)
            cal = self._cal(("2026-11-27", "2026-11-30"))
            with mock.patch.object(build, "REPO", tmp), \
                 mock.patch.object(build, "_calendar", return_value=cal):
                with mock.patch.object(build.N, "find_brief", return_value=self._brief()):
                    no_moment = build.moment_ended("zz-brand", "brief-0311", when=date(2027, 1, 1))
                with mock.patch.object(build.N, "find_brief", return_value=self._brief(run="no-ask-run")):
                    no_ask = build.moment_ended("zz-brand", "brief-0311", when=date(2027, 1, 1))
                with mock.patch.object(build.N, "find_brief", return_value=None):
                    no_brief = build.moment_ended("zz-brand", "brief-0311", when=date(2027, 1, 1))
        self.assertEqual((no_moment, no_ask, no_brief), (None, None, None))
        cal.moment_window.assert_not_called()

    def test_a_moment_with_no_dated_window_never_holds(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._repo(tmp)
            with mock.patch.object(build, "REPO", tmp), \
                 mock.patch.object(build.N, "find_brief", return_value=self._brief()), \
                 mock.patch.object(build, "_calendar", return_value=self._cal(None)):
                self.assertIsNone(build.moment_ended("zz-brand", "brief-0311", when=date(2027, 1, 1)))

    def test_the_window_comes_from_the_brands_moments_file(self):
        # the real reader, on a brand folder of its own: Black Friday through Cyber Monday 2026
        cal = build._calendar()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "brands" / "zz-brand"
            _write(root / "strategy" / "moments.json", json.dumps({"avatars": {"a": {"moments": [
                {"key": "black-friday", "stream": "fixed", "evidence": "proven", "audience": "all",
                 "anchor": {"holiday": "black-friday", "through": "cyber-monday"}},
                {"key": "spring-reset", "stream": "seasonal", "evidence": "proposed", "audience": "all",
                 "anchor": {"window": ["03-20", "04-10"]}},
                {"key": "always-on", "stream": "seasonal", "evidence": "proposed", "audience": "all",
                 "anchor": {"any": True}}]}}}))
            with mock.patch.object(cal, "paths") as P:
                P.brand_root.return_value = root
                got = cal.moment_window("zz-brand", "black-friday", date(2026, 10, 31))
                none = cal.moment_window("zz-brand", "no-such-moment", date(2026, 10, 31))
                spring = cal.moment_window("zz-brand", "spring-reset", date(2026, 10, 31))
                undated = cal.moment_window("zz-brand", "always-on", date(2026, 10, 31))
        self.assertEqual(got, ("2026-11-27", "2026-11-30"))
        self.assertEqual(spring, ("2027-03-20", "2027-04-10"))     # any moment, any kind of anchor
        self.assertIsNone(none)
        self.assertIsNone(undated)

    def test_build_keeps_no_dates_of_its_own_for_a_moment(self):
        src = (HERE / "build.py").read_text()
        self.assertIn("moment_window", src)
        self.assertNotIn("black-friday", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
