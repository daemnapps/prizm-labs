"""SI-194 (readers use loader), audio-teardown — every key read goes through
components/keys/loader.py, and no key value rides on a curl command line.

A temp HOME (HOME and Path.home both point at it), fake names and fake values
only, a FAKE ~/.daemn/daemn_keys.py written into it, no network: curl is a
stand-in that records what it was handed. The real home folder, ~/.daemn and
the Keychain are never read.
    python3 tests/test_si194_at_keys.py"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import keys  # noqa: E402
import gemini as G  # noqa: E402
import music as M  # noqa: E402
import speakers as S  # noqa: E402

NAME = "SI194_AT_FAKE_KEY"
ENV_VALUE = "fake-env-value-111"
HELPER_VALUE = "fake-helper-value-222"
FILE_VALUE = "fake-file-value-333"
OTHER_VALUE = "fake-other-value-444"
FAKES = (ENV_VALUE, HELPER_VALUE, FILE_VALUE, OTHER_VALUE)
KEY_NAMES = (NAME, "GEMINI_API_KEY", "ELEVENLABS_API_KEY", "AUDD_API_TOKEN", "KEYS_NO_FALLBACK")

FAKE_HELPER = '''import json
from pathlib import Path
_HERE = Path(__file__).resolve().parent
def key(name):
    with open(str(_HERE / "calls.log"), "a") as f:
        f.write(name + "\\n")
    return json.loads((_HERE / "values.json").read_text()).get(name)
'''


class Home(unittest.TestCase):
    """Each test runs in its own fake home, with the key names cleared from the environment."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        env = {k: v for k, v in os.environ.items() if k not in KEY_NAMES}
        env["HOME"] = str(self.home)
        patches = [unittest.mock.patch.dict(os.environ, env, clear=True),
                   unittest.mock.patch.object(Path, "home", classmethod(lambda cls: self.home))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._forget_helper)
        self._forget_helper()

    def tearDown(self):
        self._tmp.cleanup()

    def _forget_helper(self):
        sys.modules.pop("daemn_keys", None)
        daemn = str(self.home / ".daemn")
        while daemn in sys.path:
            sys.path.remove(daemn)

    def helper(self, values):
        d = self.home / ".daemn"
        d.mkdir(exist_ok=True)
        (d / "daemn_keys.py").write_text(FAKE_HELPER)
        (d / "values.json").write_text(json.dumps(values))

    def helper_calls(self):
        log = self.home / ".daemn" / "calls.log"
        return log.read_text().split() if log.exists() else []

    def managed(self):
        (self.home / ".workflow-worker.env").write_text("# the mini marker; never opened\n")

    def raised(self, name):
        with self.assertRaises(RuntimeError) as cm:
            keys.key(name)
        return str(cm.exception)


class Order(Home):
    def test_env_beats_keychain(self):
        self.helper({NAME: HELPER_VALUE})
        os.environ[NAME] = ENV_VALUE
        self.assertEqual(keys.key(NAME), ENV_VALUE)

    def test_keychain_found_when_env_empty(self):
        self.helper({NAME: HELPER_VALUE})
        self.assertFalse((self.home / ".workflow-worker.env").exists())
        self.assertEqual(keys.key(NAME), HELPER_VALUE)
        self.assertIn(NAME, self.helper_calls())

    def test_gemini_env_still_supplies_gemini_key_on_a_persons_machine(self):
        (self.home / ".gemini.env").write_text("GEMINI_API_KEY=%s\n" % FILE_VALUE)
        self.assertEqual(keys.key("GEMINI_API_KEY"), FILE_VALUE)

    def test_managed_file_skips_helper_and_files(self):
        self.helper({NAME: HELPER_VALUE})
        (self.home / ".gemini.env").write_text("%s=%s\n" % (NAME, FILE_VALUE))
        self.managed()
        msg = self.raised(NAME)
        self.assertEqual(self.helper_calls(), [])
        self.assertNotIn("daemn_keys", sys.modules)
        self.assertIn("skipped", msg)
        for v in FAKES:
            self.assertNotIn(v, msg)

    def test_no_fallback_flag_skips_helper_and_files(self):
        self.helper({NAME: HELPER_VALUE})
        (self.home / ".gemini.env").write_text("%s=%s\n" % (NAME, FILE_VALUE))
        os.environ["KEYS_NO_FALLBACK"] = "1"
        msg = self.raised(NAME)
        self.assertEqual(self.helper_calls(), [])
        self.assertIn("skipped", msg)


class Missing(Home):
    def test_missing_names_key_and_places_never_a_value(self):
        self.helper({"SI194_AT_OTHER": OTHER_VALUE})
        (self.home / ".gemini.env").write_text("SI194_AT_OTHER=%s\n" % FILE_VALUE)
        (self.home / ".apify.env").write_text("SI194_AT_OTHER=%s\n" % FILE_VALUE)
        os.environ["SI194_AT_OTHER_ENV"] = ENV_VALUE
        msg = self.raised(NAME)
        self.assertIn(NAME, msg)
        for place in ("environment", "~/.daemn/daemn_keys.py", "~/.daemn/keys.env", "~/.apify.env",
                      "~/.gemini.env"):
            self.assertIn(place, msg)
        for v in FAKES:
            self.assertNotIn(v, msg)
        self.assertEqual(keys.missing(NAME), msg)

    def test_paste_placeholder_is_missing(self):
        os.environ[NAME] = "PASTE_YOUR_KEY_HERE"
        msg = self.raised(NAME)
        self.assertIn(NAME, msg)
        self.assertNotIn("PASTE_YOUR_KEY_HERE", msg)

    def test_paste_placeholder_from_keychain_is_missing(self):
        self.helper({NAME: "PASTE-" + HELPER_VALUE})
        msg = self.raised(NAME)
        self.assertNotIn(HELPER_VALUE, msg)

    def test_audd_missing_key_never_calls_curl(self):
        self.managed()
        with unittest.mock.patch.object(M.subprocess, "run") as run:
            self.assertEqual(M.audd("track.mp3"), (None, "no AudD key"))
        run.assert_not_called()


class Loader(Home):
    def test_reads_go_through_the_loader(self):
        os.environ[NAME] = ENV_VALUE
        sys.modules.pop("upright_keys_loader", None)
        self.assertEqual(keys.key(NAME), ENV_VALUE)
        mod = sys.modules.get("upright_keys_loader")
        self.assertIsNotNone(mod)
        self.assertEqual(Path(mod.__file__).resolve(),
                         (HERE.parent / "keys" / "loader.py").resolve())

    def test_keys_py_imports_no_helper(self):
        src = (HERE / "keys.py").read_text()
        self.assertIsNone(re.search(r"^\s*(import|from)\s+daemn_keys", src, re.M))
        self.assertNotIn("sys.path.insert", src)
        self.assertIn("upright_keys_loader", src)

    def test_callers_still_import_key_by_name(self):
        for f in ("gemini.py", "speakers.py", "music.py"):
            self.assertIn("\nfrom keys import key\n", (HERE / f).read_text(), f)


class Curl(Home):
    """No key value on any curl argv; each arrives by a pipe or stdin."""

    def fake_curl(self, reply):
        seen = {}

        def run(argv, **kw):
            seen["argv"], seen["input"], seen["pass_fds"] = list(argv), kw.get("input"), kw.get("pass_fds")
            hdr = [a for a in argv if a.startswith("@/dev/fd/")]
            if hdr:
                with open(hdr[0][1:]) as f:
                    seen["header"] = f.read()
            return subprocess.CompletedProcess(argv, 0, json.dumps(reply), "")
        return seen, run

    def assert_off_argv(self, argv, value):
        for a in argv:
            self.assertNotIn(value, a)

    def test_gemini_key_by_fd_body_on_stdin(self):
        os.environ["GEMINI_API_KEY"] = ENV_VALUE
        seen, run = self.fake_curl({"candidates": [{"content": {"parts": [{"text": "[]"}]}}]})
        audio = self.home / "clip.mp3"
        audio.write_bytes(b"\x00\x01" * 1000)
        with unittest.mock.patch.object(G.subprocess, "run", side_effect=run):
            self.assertEqual(G._one("gemini-fake", audio, "listen", 5), [])
        argv = seen["argv"]
        self.assert_off_argv(argv, ENV_VALUE)
        self.assertEqual(seen["header"], "x-goog-api-key: %s\n" % ENV_VALUE)
        rfd = int([a for a in argv if a.startswith("@/dev/fd/")][0][len("@/dev/fd/"):])
        self.assertEqual(seen["pass_fds"], (rfd,))
        self.assertEqual(argv[argv.index("@/dev/fd/%d" % rfd) - 1], "-H")
        with self.assertRaises(OSError):
            os.fstat(rfd)                                        # closed after the call
        self.assertIn("@-", argv)
        self.assertEqual(argv[argv.index("@-") - 1], "--data-binary")
        self.assertEqual(json.loads(seen["input"])["contents"][0]["parts"][1]["text"], "listen")
        self.assertFalse(any("key=" in a for a in argv))
        self.assertNotIn("?key=", G.URL)

    def test_speakers_key_on_stdin(self):
        os.environ["ELEVENLABS_API_KEY"] = ENV_VALUE
        seen, run = self.fake_curl({"words": [], "language_code": "eng"})
        with unittest.mock.patch.object(S.subprocess, "run", side_effect=run):
            S.listen("voices.mp3")
        self.assert_off_argv(seen["argv"], ENV_VALUE)
        self.assertEqual(seen["argv"][seen["argv"].index("@-") - 1], "-H")
        self.assertEqual(seen["input"], "xi-api-key: %s\n" % ENV_VALUE)
        self.assertIn("file=@voices.mp3", seen["argv"])

    def test_audd_token_as_stdin_form_value(self):
        os.environ["AUDD_API_TOKEN"] = ENV_VALUE
        seen, run = self.fake_curl({"status": "success", "result": None})
        with unittest.mock.patch.object(M.subprocess, "run", side_effect=run):
            self.assertEqual(M.audd("track.mp3"), (None, "not a known recording"))
        self.assert_off_argv(seen["argv"], ENV_VALUE)
        self.assertIn("api_token=<-", seen["argv"])
        self.assertEqual(seen["input"], ENV_VALUE)
        self.assertIn("file=@track.mp3", seen["argv"])


if __name__ == "__main__":
    unittest.main()
