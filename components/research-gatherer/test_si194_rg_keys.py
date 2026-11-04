#!/usr/bin/env python3
"""SI-194 (readers use loader), research-gatherer dispatch — voicepull.key,
ownvoice._vault and voiceprint.key_of read through rg_keys.key(), which asks
components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn. Values are fake-*.
voiceprint's and ownvoice's key names are fixed in their code, so their tests
use those names — with fake values only. No transport is ever reached: no
network. The real ~/.daemn, ~/.workflow-worker.env, ~/.gemini.env,
~/.apify.env and the Keychain are never read.

  (a) loader    — rg_keys loads components/keys/loader.py by path as
                  company_keys_loader, reuses it; voiceprint run as a script
                  loads rg_keys by path and shares the same loader.
  (b) via key   — the three readers ask rg_keys.key(NAME); none imports the
                  helper or appends ~/.daemn to sys.path; feedback, reviews and
                  surveys still ask V.key.
  (c) order     — env beats the Keychain, and the Keychain is found when the
                  env is empty, for all three readers.
  (d) mini      — with ~/.workflow-worker.env present, neither the helper nor
                  ~/.daemn/keys.env, ~/.gemini.env or ~/.apify.env is read.
  (e) empty     — V.key(None) and V.key('') are None; a missing name is None.
  (f) no raise  — a failing loader, helper or rg_keys is None, never raised.
  (g) alias     — ownvoice._vault('SUPABASE_DB_URL') still finds
                  SUPABASE_DB_URL when it is the only one set (G-A1).
  (h) messages  — no value in any message or output; voiceprint's missing-key
                  exit names ELEVENLABS_API_KEY and where the loader looked.

Run: python3 components/research-gatherer/test_si194_rg_keys.py
"""
import ast
import builtins
import contextlib
import importlib.util
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PKG = HERE / "research_gatherer"
REPO = next(r for r in HERE.parents if (r / "components" / "keys" / "loader.py").is_file())
sys.path.append(str(HERE))                         # APPEND — never insert at 0
from research_gatherer import rg_keys              # noqa: E402
from research_gatherer import voicepull as V       # noqa: E402
from research_gatherer import ownvoice as OV       # noqa: E402
from research_gatherer import voiceprint as VP     # noqa: E402

ELEVEN = "ELEVENLABS_API_KEY"
SUPA = "SUPABASE_DB_URL"
CANON_DB = "DATABASE_URL"
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"
KEY_FILES = (".gemini.env", ".apify.env", ".daemn/keys.env")
READERS = (PKG / "voicepull.py", PKG / "ownvoice.py", PKG / "voiceprint.py")

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


def _docstrings(tree):
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body \
                and isinstance(node.body[0], ast.Expr) \
                and isinstance(getattr(node.body[0], "value", None), ast.Constant):
            docs.add(id(node.body[0].value))
    return docs


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-rg-home-"))
        self.addCleanup(shutil.rmtree, str(self.home), True)
        loader = rg_keys._load_loader()
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

    @contextlib.contextmanager
    def opens(self):
        """Every path opened while inside, through Path.open / read_text / open."""
        seen = []
        real_open, real_read, real_bopen = pathlib.Path.open, pathlib.Path.read_text, builtins.open

        def p_open(path, *a, **k):
            seen.append(str(path))
            return real_open(path, *a, **k)

        def p_read(path, *a, **k):
            seen.append(str(path))
            return real_read(path, *a, **k)

        def b_open(f, *a, **k):
            seen.append(str(f))
            return real_bopen(f, *a, **k)

        with mock.patch.object(pathlib.Path, "open", p_open), \
                mock.patch.object(pathlib.Path, "read_text", p_read), \
                mock.patch.object(builtins, "open", b_open):
            yield seen

    def key_files_opened(self, seen):
        files = {str(self.home / f) for f in KEY_FILES + (MARKER,)}
        return sorted(files & set(seen))

    @contextlib.contextmanager
    def quiet(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield
        self.printed = out.getvalue() + err.getvalue()

    def voiceprint_exit(self):
        """Drive voiceprint.run_creator to its missing-key exit: one post on
        'the drive', audio extracted, no cached transcript, no key."""
        post = {"exists": True, "id": "p1", "video": str(self.home / "fake.mp4")}
        with mock.patch.object(VP, "extract_wav", return_value=(True, "")), \
                mock.patch.object(VP, "energy_profile", return_value={"duration_s": 1.0}), \
                mock.patch.object(VP, "read_json", return_value=None), \
                mock.patch.object(VP, "transcribe", side_effect=AssertionError("a transport was reached")):
            with self.assertRaises(SystemExit) as cm:
                VP.run_creator("fakebrand", "fakehandle", [post], VP.key_of(),
                               root=self.home / "ws", scratch=self.home / "scratch")
        return str(cm.exception.code)


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = rg_keys._load_loader()
        self.assertEqual(loader.__name__, "company_keys_loader")
        self.assertIs(sys.modules["company_keys_loader"], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertIs(rg_keys._load_loader(), loader, "loaded once, then reused")

    def test_rg_keys_has_no_relative_import_and_never_touches_sys_path(self):
        tree = ast.parse((PKG / "rg_keys.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0, "a relative import — rg_keys could not be loaded by path")
            if isinstance(node, ast.Attribute) and node.attr == "path" \
                    and isinstance(node.value, ast.Name) and node.value.id == "sys":
                self.fail("rg_keys touches sys.path")

    def test_voiceprint_holds_the_package_rg_keys(self):
        self.assertIs(VP._rg_keys(), rg_keys)

    def test_voiceprint_as_a_script_loads_rg_keys_by_path_and_shares_the_loader(self):
        name = "si194_rg_voiceprint_script"
        spec = importlib.util.spec_from_file_location(name, str(PKG / "voiceprint.py"))
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        self.addCleanup(sys.modules.pop, script._RG_KEYS, None)
        self.assertFalse(script.__package__)
        rk = script._rg_keys()
        self.assertEqual(Path(rk.__file__).resolve(), PKG / "rg_keys.py")
        self.assertIs(script._rg_keys(), rk, "loaded once, then reused")
        self.assertIs(rk._load_loader(), rg_keys._load_loader())
        os.environ[ELEVEN] = "fake-eleven-env"
        self.assertEqual(script.key_of(), "fake-eleven-env")


class ViaKey(Case):
    def test_the_three_readers_ask_rg_keys(self):
        with mock.patch.object(rg_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(V.key("FAKE_SI194_RG_A"), "fake-via-key")
            k.assert_called_once_with("FAKE_SI194_RG_A")
        with mock.patch.object(rg_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(OV._vault(SUPA), "fake-via-key")
            k.assert_called_once_with(SUPA)
        with mock.patch.object(rg_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(VP.key_of(), "fake-via-key")
            k.assert_called_once_with(ELEVEN)

    def test_ownvoice_sql_still_asks_for_supabase_db_url(self):
        asked = []
        with mock.patch.object(OV, "_vault", side_effect=lambda n: asked.append(n)), \
                mock.patch.object(OV.shutil, "which", return_value=None), self.quiet():
            self.assertIsNone(OV.sql("select 1"))
        self.assertEqual(asked, [SUPA], "G-A1: the name is not renamed")

    def test_no_reader_imports_the_helper_or_appends_daemn(self):
        banned = (HELPER, ".daemn", ".gemini.env", ".apify.env", "keys.env")
        for path in READERS + (PKG / "rg_keys.py",):
            text = path.read_text()
            tree = ast.parse(text)
            docs = _docstrings(tree)
            with self.subTest(file=path.name):
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        self.assertNotIn(HELPER, [a.name for a in node.names])
                    if isinstance(node, ast.ImportFrom):
                        self.assertNotEqual(node.module, HELPER)
                    if isinstance(node, ast.Name):
                        self.assertNotEqual(node.id, HELPER)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                            and id(node) not in docs:
                        for b in banned:
                            self.assertNotIn(b, node.value, "%s names %s in code" % (path.name, b))
                if path in READERS:
                    self.assertNotIn("import daemn_keys", text)
                    for line in text.splitlines():
                        self.assertFalse("sys.path" in line and ".daemn" in line, line)

    def test_feedback_reviews_surveys_still_ask_voicepull_key(self):
        for name in ("feedback.py", "reviews.py", "surveys.py"):
            with self.subTest(file=name):
                self.assertIn("V.key(", (PKG / name).read_text())


class Order(Case):
    def test_env_beats_keychain(self):
        self.helper({"FAKE_SI194_RG_A": "fake-keychain-a", SUPA: "fake-db-keychain",
                     ELEVEN: "fake-eleven-keychain"})
        os.environ["FAKE_SI194_RG_A"] = "fake-env-a"
        os.environ[SUPA] = "fake-db-env"
        os.environ[ELEVEN] = "fake-eleven-env"
        self.assertEqual(V.key("FAKE_SI194_RG_A"), "fake-env-a")
        self.assertEqual(OV._vault(SUPA), "fake-db-env")
        self.assertEqual(VP.key_of(), "fake-eleven-env")

    def test_keychain_found_when_env_empty(self):
        self.helper({"FAKE_SI194_RG_A": "fake-keychain-a", SUPA: "fake-db-keychain",
                     ELEVEN: "fake-eleven-keychain"})
        os.environ["FAKE_SI194_RG_A"] = ""
        self.assertEqual(V.key("FAKE_SI194_RG_A"), "fake-keychain-a")
        self.assertEqual(OV._vault(SUPA), "fake-db-keychain")
        self.assertEqual(VP.key_of(), "fake-eleven-keychain")

    def test_env_value_is_stripped(self):
        os.environ["FAKE_SI194_RG_A"] = "  fake-env-a \n"
        os.environ[ELEVEN] = " fake-eleven-env\n"
        self.assertEqual(V.key("FAKE_SI194_RG_A"), "fake-env-a")
        self.assertEqual(VP.key_of(), "fake-eleven-env")


class Mini(Case):
    def setUp(self):
        super().setUp()
        self.write(MARKER, "")
        self.helper({"FAKE_SI194_RG_A": "fake-keychain-a", SUPA: "fake-db-keychain",
                     ELEVEN: "fake-eleven-keychain"})
        for f in KEY_FILES:
            self.write(f, "FAKE_SI194_RG_A=fake-file-a\n%s=fake-db-file\n%s=fake-eleven-file\n" % (SUPA, ELEVEN))

    def test_marker_takes_env_only(self):
        os.environ["FAKE_SI194_RG_A"] = "fake-env-a"
        os.environ[SUPA] = "fake-db-env"
        os.environ[ELEVEN] = "fake-eleven-env"
        with self.opens() as seen:
            self.assertEqual(V.key("FAKE_SI194_RG_A"), "fake-env-a")
            self.assertEqual(OV._vault(SUPA), "fake-db-env")
            self.assertEqual(VP.key_of(), "fake-eleven-env")
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")

    def test_marker_and_no_env_reads_nothing_and_finds_nothing(self):
        with self.opens() as seen, self.quiet():
            self.assertIsNone(V.key("FAKE_SI194_RG_A"))
            self.assertIsNone(OV._vault(SUPA))
            self.assertIsNone(VP.key_of())
            msg = self.voiceprint_exit()
        self.assertIn(ELEVEN, msg)
        self.assertIn("skipped (managed file", msg)
        self.assertNotIn("fake-", msg)
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")
        self.assertNotIn("fake-", self.printed)


class Empty(Case):
    def test_none_and_empty_name_are_none_and_ask_nothing(self):
        loader = rg_keys._load_loader()
        os.environ["FAKE_SI194_RG_A"] = "fake-env-a"
        with mock.patch.object(loader, "key") as k:
            self.assertIsNone(V.key(None))
            self.assertIsNone(V.key(""))
            self.assertIsNone(rg_keys.key(None))
            self.assertIsNone(rg_keys.key(""))
            k.assert_not_called()

    def test_a_missing_name_is_none(self):
        self.helper({"FAKE_SI194_RG_OTHER": "fake-keychain-other"})
        self.write(".daemn/keys.env", "FAKE_SI194_RG_OTHER=fake-file-other\n")
        self.assertIsNone(V.key("FAKE_SI194_RG_MISSING"))
        self.assertIsNone(OV._vault("FAKE_SI194_RG_MISSING"))
        self.assertIsNone(VP.key_of())


class NeverRaises(Case):
    def test_a_failing_loader_is_none(self):
        loader = rg_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")), self.quiet():
            self.assertIsNone(V.key("FAKE_SI194_RG_A"))
            self.assertIsNone(OV._vault(SUPA))
            self.assertIsNone(VP.key_of())
            msg = self.voiceprint_exit()
        self.assertIn(ELEVEN, msg)
        self.assertIn("could not be asked", msg)

    def test_a_failing_helper_is_none(self):
        self.write(".daemn/daemn_keys.py", "def key(n, required=False):\n    raise RuntimeError('boom')\n")
        self.assertIsNone(V.key("FAKE_SI194_RG_A"))
        self.assertIsNone(OV._vault(SUPA))
        self.assertIsNone(VP.key_of())
        self._forget_helper()
        self.write(".daemn/daemn_keys.py", "this is not python (\n")
        self.assertIsNone(V.key("FAKE_SI194_RG_A"))
        self.assertIsNone(OV._vault(SUPA))
        self.assertIsNone(VP.key_of())

    def test_an_unreadable_loader_is_none(self):
        held = sys.modules.pop(rg_keys._LOADER_NAME)
        self.addCleanup(sys.modules.__setitem__, rg_keys._LOADER_NAME, held)
        with mock.patch.object(rg_keys, "_LOADER_PATH", self.home / "no-such" / "loader.py"), self.quiet():
            os.environ["FAKE_SI194_RG_A"] = "fake-env-a"
            self.assertIsNone(V.key("FAKE_SI194_RG_A"))
            self.assertIsNone(OV._vault(SUPA))
            self.assertIsNone(VP.key_of())
            self.assertIn("could not be asked", rg_keys.missing(ELEVEN))
            msg = self.voiceprint_exit()
        self.assertNotIn(rg_keys._LOADER_NAME, sys.modules, "a failed load is not left behind")
        self.assertIn(ELEVEN, msg)
        self.assertNotIn("fake-", msg + self.printed)

    def test_a_raising_rg_keys_is_none(self):
        with mock.patch.object(rg_keys, "key", side_effect=RuntimeError("boom")), \
                mock.patch.object(rg_keys, "missing", side_effect=RuntimeError("boom")), self.quiet():
            self.assertIsNone(V.key("FAKE_SI194_RG_A"))
            self.assertIsNone(OV._vault(SUPA))
            self.assertIsNone(VP.key_of())
            msg = self.voiceprint_exit()
        self.assertIn(ELEVEN, msg)
        self.assertIn("could not be asked", msg)

    def test_an_odd_name_or_value_is_none(self):
        for name in ("not a name!", "FAKE SI194", 42):
            with self.subTest(name=name):
                self.assertIsNone(V.key(name))
                self.assertIsNone(OV._vault(name))
        os.environ["FAKE_SI194_RG_A"] = "   "
        self.assertIsNone(V.key("FAKE_SI194_RG_A"))


class Alias(Case):
    def test_supabase_db_url_alone_is_still_found(self):
        os.environ[SUPA] = "fake-db-env"
        self.assertNotIn(CANON_DB, os.environ)
        self.assertEqual(OV._vault(SUPA), "fake-db-env")

    def test_supabase_db_url_alone_in_the_keychain_is_still_found(self):
        self.helper({SUPA: "fake-db-keychain"})
        self.assertEqual(OV._vault(SUPA), "fake-db-keychain")

    def test_the_canonical_name_also_answers_the_old_one(self):
        os.environ[CANON_DB] = "fake-db-canonical"
        self.assertEqual(OV._vault(SUPA), "fake-db-canonical")


class Messages(Case):
    def test_reads_print_nothing(self):
        self.helper({"FAKE_SI194_RG_A": "fake-keychain-a", SUPA: "fake-db-keychain"})
        self.write(".gemini.env", "%s=fake-eleven-file\n" % ELEVEN)
        with self.quiet():
            V.key("FAKE_SI194_RG_A")
            V.key("FAKE_SI194_RG_MISSING")
            OV._vault(SUPA)
            VP.key_of()
        self.assertEqual(self.printed, "")

    def test_voiceprint_missing_names_the_key_and_where_looked_never_a_value(self):
        self.helper({"FAKE_SI194_RG_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_RG_OTHER"] = "fake-secret-env"
        with self.quiet():
            msg = self.voiceprint_exit()
        self.assertIn(ELEVEN, msg)
        self.assertIn("looked in: environment", msg)
        self.assertIn("~/.daemn/daemn_keys.py", msg)
        self.assertIn("~/.gemini.env", msg)
        self.assertIn("nothing transcribed", msg)
        self.assertNotIn("Keychain vault", msg)
        self.assertNotIn("fake-", msg)
        self.assertNotIn("None", msg)
        self.assertNotIn("fake-", self.printed)

    def test_rg_keys_missing_never_carries_a_value(self):
        self.helper({"FAKE_SI194_RG_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_RG_OTHER"] = "fake-secret-env"
        msg = rg_keys.missing("FAKE_SI194_RG_MISSING")
        self.assertIn("FAKE_SI194_RG_MISSING", msg)
        self.assertIn("looked in: environment", msg)
        self.assertNotIn("fake-", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
