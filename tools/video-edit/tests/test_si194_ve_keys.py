#!/usr/bin/env python3
"""SI-194 (readers use loader), dispatch 2 — video-edit reads its one key through
ve_keys.key(), which asks components/keys/loader.py, and the key never rides on
curl's command line (video-edit#22).

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn. Values are fake-*. The
readers' key name is fixed in their code, so the reader tests use that name —
with fake values only. subprocess.run is patched: no real curl, no network.
The real ~/.daemn, ~/.workflow-worker.env, ~/.gemini.env, ~/.apify.env and the
Keychain are never read.

  (a) loader    — ve_keys loads components/keys/loader.py by path as
                  shared_keys_loader, reuses it, never raises.
  (b) via key   — every call site gets its key from ve_keys.key(); no reader
                  imports the helper or puts ~/.daemn on sys.path itself.
  (c) order     — env empty → the Keychain value; env beats the Keychain.
  (d) mini      — with ~/.workflow-worker.env present the helper is never imported.
  (e) argv      — at each of the four curl call sites the key is in NO argv
                  element and is in `input`; every other argv element and
                  keyword is as it was before this change.
  (f) missing   — exits before subprocess.run, naming the key and where the
                  loader looked, never a value.

Run: cd tools/video-edit/tests && python3 test_si194_ve_keys.py
"""
import ast
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MACHINE = HERE.parent / "machine"
REPO = HERE.parents[2]
sys.path.insert(0, str(MACHINE))
import ve_keys  # noqa: E402
import listen  # noqa: E402
import music_bed  # noqa: E402
import word_fix  # noqa: E402

NAME = "ELEVENLABS_API_KEY"
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"
READER_FILES = ("listen", "music_bed", "word_fix")
STT = "https://api.elevenlabs.io/v1/speech-to-text"

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-ve-home-"))
        self.addCleanup(shutil.rmtree, str(self.home), True)
        loader = ve_keys._load_loader()
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("FAKE_SI194_")
               and k != loader.NO_FALLBACK_ENV
               and not _credential_looking(k)
               and k not in loader.ALIASES
               and k not in loader.ALIASES.values()}
        env["HOME"] = str(self.home)
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._forget_helper)
        self._forget_helper()
        self.work = self.home / "work"
        self.work.mkdir()
        self.calls = []

    def _forget_helper(self):
        sys.modules.pop(HELPER, None)
        folder = str(self.home / ".daemn")
        while folder in sys.path:
            sys.path.remove(folder)

    def write(self, rel, text):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def helper(self, values):
        self.write(".daemn/daemn_keys.py",
                   "VALUES = %r\n"
                   "def key(n, required=False):\n"
                   "    return VALUES.get(n)\n" % (values,))

    # --- the four curl call sites, each with subprocess.run patched -------------

    def _fake_run(self, stdout):
        def run(argv, **kw):
            self.calls.append((list(argv), dict(kw)))
            return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")
        return run

    def site_listen(self):
        wav = self.work / "mix.wav"
        with mock.patch("subprocess.run", self._fake_run('{"words": []}')):
            listen.transcribe(wav)
        return (["curl", "-s", "-X", "POST", STT,
                 "-F", "model_id=scribe_v1", "-F", "timestamps_granularity=word", "-F", "file=@%s" % wav],
                5, {"capture_output": True, "text": True, "timeout": 600})

    def site_music(self):
        dest = self.work / "bed.mp3"
        with mock.patch("subprocess.run", self._fake_run("200")):
            music_bed.make({"model_id": "fake-model"}, dest)
        return (["curl", "-s", "-o", str(dest), "-w", "%{http_code}", "-X", "POST", music_bed.URL,
                 "-H", "Content-Type: application/json", "--data-binary", "@%s" % dest.with_suffix(".req.json")],
                9, {"capture_output": True, "text": True, "timeout": 900})

    def site_speak(self):
        dest = self.work / "take1-raw.mp3"
        with mock.patch("subprocess.run", self._fake_run("200")):
            word_fix.speak("fake-voice", "fake words", "", "", dest, seed=1)
        url = "https://api.elevenlabs.io/v1/text-to-speech/fake-voice?output_format=mp3_44100_192"
        return (["curl", "-s", "-o", str(dest), "-w", "%{http_code}", "-X", "POST", url,
                 "-H", "Content-Type: application/json", "--data-binary", "@%s" % dest.with_suffix(".req.json")],
                9, {"capture_output": True, "text": True, "timeout": 300})

    def site_heard(self):
        f = self.work / "take1.wav"
        with mock.patch("subprocess.run", self._fake_run('{"words": []}')):
            word_fix.heard(f)
        return (["curl", "-s", "-X", "POST", STT,
                 "-F", "model_id=scribe_v1", "-F", "timestamps_granularity=word", "-F", "file=@%s" % f],
                5, {"capture_output": True, "text": True, "timeout": 300})

    SITES = ("site_listen", "site_music", "site_speak", "site_heard")

    def assert_site(self, site, value):
        """One call; the key only in `input`; every other argv element and keyword unchanged."""
        self.calls = []
        expected, at, kw_expected = getattr(self, site)()
        self.assertEqual(len(self.calls), 1, self.calls)
        argv, kw = self.calls[0]
        for a in argv:
            self.assertNotIn(value, a, "the key is on the command line")
            self.assertNotIn("xi-api-key", a, "the header is on the command line")
        self.assertEqual(argv[at:at + 2], ["-H", "@-"], "the header comes from stdin, where the key header was")
        self.assertEqual(argv[:at] + argv[at + 2:], expected)
        self.assertEqual(kw.pop("input"), "xi-api-key: %s\n" % value)
        self.assertEqual(kw, kw_expected)


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = ve_keys._load_loader()
        self.assertEqual(loader.__name__, "shared_keys_loader")
        self.assertIs(sys.modules["shared_keys_loader"], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertNotIn(str(REPO / "components" / "keys"), sys.path)
        self.assertIs(ve_keys._load_loader(), loader, "loaded once, then reused")

    def test_never_raises(self):
        loader = ve_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")):
            self.assertIsNone(ve_keys.key("FAKE_SI194_ANY"))
            self.assertIn("FAKE_SI194_ANY", ve_keys.missing("FAKE_SI194_ANY"))
        self.assertIsNone(ve_keys.key("FAKE_SI194_ANY"))

    def test_env_beats_keychain(self):
        self.helper({"FAKE_SI194_A": "fake-keychain"})
        self.assertEqual(ve_keys.key("FAKE_SI194_A"), "fake-keychain")
        os.environ["FAKE_SI194_A"] = "fake-env"
        self.assertEqual(ve_keys.key("FAKE_SI194_A"), "fake-env")


class ViaKey(Case):
    def test_every_site_takes_its_key_from_ve_keys_key(self):
        for site in self.SITES:
            with self.subTest(site=site), \
                    mock.patch.object(ve_keys, "key", return_value="fake-via-key") as k:
                self.assert_site(site, "fake-via-key")
                k.assert_called_once_with(NAME)

    def test_every_reader_holds_the_one_ve_keys(self):
        for mod in (listen, music_bed, word_fix):
            with self.subTest(reader=mod.__name__):
                self.assertIs(mod.ve_keys, ve_keys)
                self.assertEqual(Path(mod.ve_keys.__file__).resolve(), MACHINE / "ve_keys.py")

    def test_no_reader_imports_the_helper_or_puts_it_on_sys_path(self):
        for name in READER_FILES:
            src = (MACHINE / (name + ".py")).read_text()
            self.assertNotIn(HELPER, src)
            self.assertNotIn(".daemn", src)
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    self.assertNotIn(HELPER, [a.name for a in node.names], name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, HELPER, name)


class Order(Case):
    def test_keychain_used_when_env_empty(self):
        self.helper({NAME: "fake-keychain-el"})
        for site in self.SITES:
            with self.subTest(site=site):
                self.assert_site(site, "fake-keychain-el")

    def test_env_beats_keychain(self):
        self.helper({NAME: "fake-keychain-el"})
        os.environ[NAME] = "fake-env-el"
        for site in self.SITES:
            with self.subTest(site=site):
                self.assert_site(site, "fake-env-el")


class Mini(Case):
    def test_marker_never_imports_the_helper(self):
        self.write(MARKER, "")
        self.helper({NAME: "fake-keychain-el"})
        os.environ[NAME] = "fake-env-el"
        for site in self.SITES:
            with self.subTest(site=site):
                self.assert_site(site, "fake-env-el")
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")

    def test_marker_and_no_env_stops_without_the_helper(self):
        self.write(MARKER, "")
        self.helper({NAME: "fake-keychain-el"})
        for site in self.SITES:
            with self.subTest(site=site):
                self.calls = []
                with self.assertRaises(SystemExit) as cm:
                    getattr(self, site)()
                self.assertEqual(self.calls, [], "subprocess.run was called")
                msg = str(cm.exception.code)
                self.assertIn(NAME, msg)
                self.assertIn("old locations skipped", msg)
                self.assertNotIn("fake-", msg)
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")


class Missing(Case):
    def test_missing_exits_before_any_call_and_names_no_value(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"
        out, err = io.StringIO(), io.StringIO()
        for site in self.SITES:
            with self.subTest(site=site):
                self.calls = []
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                        self.assertRaises(SystemExit) as cm:
                    getattr(self, site)()
                self.assertEqual(self.calls, [], "subprocess.run was called")
                msg = str(cm.exception.code)
                self.assertIn(NAME, msg)
                self.assertIn("looked in: environment", msg)
                self.assertIn("~/.daemn/daemn_keys.py", msg)
                self.assertNotIn("fake-", msg)
                self.assertNotIn("None", msg)
        self.assertNotIn("fake-", out.getvalue() + err.getvalue())
        self.assertEqual(list(self.work.iterdir()), [], "a request file was written before the stop")


if __name__ == "__main__":
    unittest.main(verbosity=2)
