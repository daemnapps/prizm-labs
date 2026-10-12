#!/usr/bin/env python3
"""SI-161 (teardown runs honest): every teardown run, held or failed included,
reaches the plane with a true state under the right person and venue.

    /usr/bin/python3 tools/video-teardown/machine/test_vt6_runs_honest.py

  * TEARDOWN_RAN_BY / TEARDOWN_VENUE (set by the mini worker) name the person
    and the venue; unset, the machine account and `local` as before
  * runs_root(create=False) names the working folder and makes nothing;
    the default still makes it (SI-56 (teardown working home) unchanged)
  * line.py finds a run's source by the name run.json gives it (.mov too)
  * a run that stops at a held or failed stage saves its state and is filed

Stdlib only, no key, no network. Every tree is a temp folder; the real runs/
is never touched.
"""
import contextlib, io, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import workdir                                              # noqa: E402
import chain as C                                           # noqa: E402
import line as LINE                                         # noqa: E402
import run as R                                             # noqa: E402

ENV = ("TEARDOWN_RAN_BY", "TEARDOWN_VENUE")


def _without(*names):
    return {k: v for k, v in os.environ.items() if k not in names}


class Attribution(unittest.TestCase):
    def test_the_worker_names_the_person_and_the_venue(self):
        with mock.patch.dict(os.environ, {"TEARDOWN_VENUE": "mini",
                                          "TEARDOWN_RAN_BY": "x"}):
            self.assertEqual(C.venue(), "mini")
            self.assertEqual(C.operator(), C.person("x"))
            self.assertEqual(C.attribution(), {"ran_by": C.person("x"), "venue": "mini"})

    def test_the_name_passes_through_person(self):
        with mock.patch.dict(os.environ, {"TEARDOWN_RAN_BY": "the owner D!"}):
            self.assertEqual(C.operator(), C.person("the owner D!"))

    def test_unset_or_empty_is_local_and_the_account(self):
        with mock.patch.dict(os.environ, _without(*ENV), clear=True), \
                mock.patch.object(C.getpass, "getuser", return_value="someone"):
            self.assertEqual(C.venue(), "local")
            self.assertEqual(C.operator(), C.person("someone"))
        with mock.patch.dict(os.environ, {"TEARDOWN_VENUE": "", "TEARDOWN_RAN_BY": "  "}), \
                mock.patch.object(C.getpass, "getuser", return_value="someone"):
            self.assertEqual(C.venue(), "local")
            self.assertEqual(C.operator(), C.person("someone"))
        for k in ENV:                                       # restored after
            self.assertEqual(os.environ.get(k), _ORIG_ENV.get(k))


class RunsRootCreatesNothing(unittest.TestCase):
    def test_create_false_names_the_folder_and_makes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            ws = Path(t).resolve()
            (ws / "brands").mkdir()
            (ws / "components").mkdir()
            with mock.patch.object(C, "WS", ws), \
                    mock.patch.object(C.workdir, "legacy", return_value=ws / "none"), \
                    contextlib.redirect_stderr(io.StringIO()):
                d = C.runs_root(create=False)
                self.assertEqual(d, workdir.root(ws))
                self.assertFalse((ws / "runs").exists())
                self.assertEqual(sorted(p.name for p in ws.iterdir()),
                                 ["brands", "components"])
                # the default is unchanged: it still makes the folder
                self.assertEqual(C.runs_root(), d)
                self.assertTrue(d.is_dir())


class LineFindsTheSource(unittest.TestCase):
    def _resolve(self, files, record=None):
        """main() for the creator line, with run.py stubbed: what path does it
        hand run.py?"""
        with tempfile.TemporaryDirectory() as t:
            work = Path(t).resolve() / "_work"
            rd = work / "zz-label"
            rd.mkdir(parents=True)
            for f in files:
                (rd / f).write_bytes(b"\x00")
            if record is not None:
                (rd / "run.json").write_text(json.dumps(record))
            got = []
            argv = ["line.py", "creator", "--label", "zz-label", "--brand", "zz-brand"]
            with mock.patch.object(workdir, "root", lambda ws=None: work), \
                    mock.patch.object(LINE, "run", lambda a: got.append(list(a)) or 0), \
                    mock.patch.object(sys, "argv", argv), \
                    contextlib.redirect_stdout(io.StringIO()):
                try:
                    LINE.main()
                except SystemExit as e:
                    code = e.code
            return code, got, rd

    def test_a_mov_named_in_run_json(self):
        code, got, rd = self._resolve(["source.mov"], {"source": "source.mov"})
        self.assertEqual(code, 0)
        self.assertEqual(got[0][0], str(rd / "source.mov"))

    def test_run_json_wins_over_an_mp4_beside_it(self):
        code, got, rd = self._resolve(["source.mp4", "source.m4v"], {"source": "source.m4v"})
        self.assertEqual(got[0][0], str(rd / "source.m4v"))

    def test_an_older_run_without_the_field_is_found_by_extension(self):
        code, got, rd = self._resolve(["source.mov"], {"slug": "zz-label"})
        self.assertEqual(got[0][0], str(rd / "source.mov"))
        code, got, rd = self._resolve(["source.mp4"])
        self.assertEqual(got[0][0], str(rd / "source.mp4"))

    def test_nothing_there_still_stops_with_the_old_message(self):
        code, got, rd = self._resolve([], {"source": "source.mov"})
        self.assertEqual(got, [])
        self.assertIn("no run called 'zz-label'", str(code))


class AStoppedRunIsFiled(unittest.TestCase):
    """run_video with open_run and run_stage stubbed: the stage stops the run,
    and the stop is saved and filed rather than returned past."""

    def _stop(self, status):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name) / "zz-stop"
        d.mkdir()
        st = {"slug": "zz-stop", "label": "zz-stop", "opened": "x", "stages": {}}
        plan = [{"key": "stage1", "id": "1", "name": "Teardown", "engine": "gemini-video",
                 "version": "v1", "prompt": ""}]

        def stage(d_, st_, s, extras, redo=False):
            st_["stages"][s["key"]] = {"status": status, "name": s["name"]}
            return False

        filed = mock.Mock()
        with mock.patch.object(R, "open_run", lambda *a, **k: (d, st)), \
                mock.patch.object(R, "run_stage", stage), \
                mock.patch.object(R, "file_to_repo", filed), \
                mock.patch.object(R, "RUNS", Path(tmp.name)), \
                mock.patch.object(R.C, "stages", lambda *a, **k: [dict(p) for p in plan]), \
                mock.patch.object(R.C, "mirror_to_drive", mock.Mock(side_effect=AssertionError)), \
                mock.patch.dict(os.environ, _without("DAEMN_ONE_STEP"), clear=True), \
                contextlib.redirect_stdout(io.StringIO()) as buf:
            ok = R.run_video(None, "zz-stop", "zz-no-such-brand", only=["1"])
        self.assertIs(ok, False, buf.getvalue())
        return filed, json.loads((d / "run.json").read_text()), d

    def test_a_held_stage_is_saved_held_and_filed_once(self):
        filed, saved, d = self._stop("held")
        filed.assert_called_once_with(d)
        self.assertEqual(saved["state"], "held")
        self.assertEqual(saved["stopped_at"], "1")
        self.assertEqual(saved["stages"]["stage1"]["status"], "held")

    def test_a_failed_stage_is_saved_failed_and_filed_once(self):
        filed, saved, d = self._stop("error")
        filed.assert_called_once_with(d)
        self.assertEqual(saved["state"], "failed")
        self.assertEqual(saved["stopped_at"], "1")

    def test_a_filing_that_raises_never_takes_the_run_down(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name) / "zz-stop"
        d.mkdir()
        st = {"slug": "zz-stop", "label": "zz-stop", "opened": "x", "stages": {}}
        plan = [{"key": "stage1", "id": "1", "name": "Teardown", "engine": "gemini-video",
                 "version": "v1", "prompt": ""}]

        def stage(d_, st_, s, extras, redo=False):
            st_["stages"][s["key"]] = {"status": "held"}
            return False

        with mock.patch.object(R, "open_run", lambda *a, **k: (d, st)), \
                mock.patch.object(R, "run_stage", stage), \
                mock.patch.object(R, "file_to_repo", mock.Mock(side_effect=OSError("no"))), \
                mock.patch.object(R.C, "stages", lambda *a, **k: [dict(p) for p in plan]), \
                mock.patch.dict(os.environ, _without("DAEMN_ONE_STEP"), clear=True), \
                contextlib.redirect_stdout(io.StringIO()) as buf:
            ok = R.run_video(None, "zz-stop", "zz-no-such-brand", only=["1"])
        self.assertIs(ok, False)
        self.assertIn("record not filed", buf.getvalue())
        self.assertEqual(json.loads((d / "run.json").read_text())["state"], "held")


_ORIG_ENV = {k: os.environ.get(k) for k in ENV}

if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if r.wasSuccessful() else 1)
