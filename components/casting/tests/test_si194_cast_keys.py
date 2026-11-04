#!/usr/bin/env python3
"""SI-194 (readers use loader), casting dispatch — casting reads its key
through cast_keys.key(), which asks components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn. Values are fake-*. The
key name is OPENAI_API_KEY because generate.KEY is fixed in code — with fake
values only. No runner is ever reached: no network, and no `security` process
is ever started. The real ~/.daemn, ~/.workflow-worker.env, ~/.gemini.env,
~/.apify.env and the Keychain are never read.

  (a) loader    — cast_keys loads components/keys/loader.py by path as
                  company_keys_loader, at CALL time only, and reuses it.
  (b) via key   — generate.key_value asks cast_keys.key(NAME); no `security`
                  subprocess, no helper import, no key file named in code.
  (c) order     — env beats the Keychain (the helper is never consulted);
                  the Keychain is found when the env is empty.
  (d) mini      — with ~/.workflow-worker.env present, or KEYS_NO_FALLBACK=1,
                  neither the helper nor any old file is read.
  (e) no raise  — a failing helper or an unloadable loader is None;
                  key_value('') and key_value(None) are None.
  (f) messages  — generate()'s missing-key error and the dry-run key line name
                  the key and where the loader looked, never a value; with no
                  key generate() returns file None and calls no runner.

Run: python3 components/casting/tests/test_si194_cast_keys.py
"""
import ast
import builtins
import contextlib
import importlib.util
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CASTING = HERE.parent
ENGINE = CASTING / "casting"
REPO = next(r for r in CASTING.parents if (r / "components" / "keys" / "loader.py").is_file())
sys.path.append(str(CASTING))                      # APPEND — never ahead of the stdlib
import casting as C                                # noqa: E402
from casting import cast_keys                      # noqa: E402
from casting import generate as G                  # noqa: E402


def _load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The fake workspace, stub library and stub reader test_casting.py already
# declares — loaded by path, never copied.
FIX = _load_by_path("si194_cast_fixtures", HERE / "test_casting.py")

_real_run, _real_popen = subprocess.run, subprocess.Popen   # held before any test patches them

KEY = G.KEY
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"
KEY_FILES = (".gemini.env", ".apify.env", ".daemn/keys.env")

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-cast-home-"))
        self.addCleanup(shutil.rmtree, str(self.home), True)
        loader = cast_keys._load_loader()
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
        # A `security` process for a key is a failure, wherever it starts.
        for name in ("run", "Popen", "check_output", "call"):
            s = mock.patch.object(subprocess, name, side_effect=AssertionError(
                "a subprocess was started for a key lookup"))
            s.start()
            self.addCleanup(s.stop)

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
                   "CALLS = []\n"
                   "def key(n, required=False):\n"
                   "    CALLS.append(n)\n"
                   "    return VALUES.get(n)\n" % (values,))

    def helper_calls(self):
        mod = sys.modules.get(HELPER)
        return list(getattr(mod, "CALLS", [])) if mod else []

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
        files = {str(self.home / f) for f in KEY_FILES}
        return sorted(files & set(seen))

    @contextlib.contextmanager
    def quiet(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield
        self.printed = out.getvalue() + err.getvalue()


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = cast_keys._load_loader()
        self.assertEqual(loader.__name__, "company_keys_loader")
        self.assertIs(sys.modules["company_keys_loader"], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertNotIn(str(REPO / "components" / "keys"), sys.path)
        self.assertIs(cast_keys._load_loader(), loader, "loaded once, then reused")

    def test_importing_casting_loads_no_loader_and_reads_no_key(self):
        code = ("import sys; sys.path.append(%r); import casting; "
                "assert 'company_keys_loader' not in sys.modules, 'loader loaded at import'; "
                "assert 'daemn_keys' not in sys.modules, 'helper imported at import'; "
                "print('ok')" % str(CASTING))
        env = {k: v for k, v in os.environ.items() if k != KEY}
        env["HOME"] = str(self.home)
        # the setUp patch guards key lookups; this child interpreter is the test itself
        with mock.patch.object(subprocess, "Popen", _real_popen):
            r = _real_run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ok", r.stdout)


class ViaKey(Case):
    def test_key_value_asks_cast_keys(self):
        with mock.patch.object(cast_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(G.key_value(), "fake-via-key")
            k.assert_called_once_with(KEY)
        with mock.patch.object(cast_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(G.key_value("FAKE_SI194_A"), "fake-via-key")
            k.assert_called_once_with("FAKE_SI194_A")
        with mock.patch.object(cast_keys, "key", return_value=None):
            self.assertFalse(G.key_present())

    def test_no_security_process_and_no_key_file_in_code(self):
        banned = (HELPER, ".daemn", ".gemini.env", ".apify.env", "keys.env",
                  "security", "find-generic-password")
        for path in (ENGINE / "generate.py", ENGINE / "cast_keys.py", ENGINE / "dryrun.py"):
            tree = ast.parse(path.read_text())
            docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body \
                        and isinstance(node.body[0], ast.Expr) \
                        and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                    docs.add(id(node.body[0].value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                    self.assertNotIn(HELPER, names, path.name)
                    self.assertNotIn("subprocess", names, "%s imports subprocess" % path.name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, HELPER, path.name)
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and id(node) not in docs:
                    for b in banned:
                        self.assertNotIn(b, node.value, "%s names %s in code" % (path.name, b))


class Order(Case):
    def test_env_beats_keychain_and_the_helper_is_never_consulted(self):
        self.helper({KEY: "fake-keychain-openai"})
        os.environ[KEY] = "fake-env-openai"
        self.assertEqual(G.key_value(), "fake-env-openai")
        self.assertTrue(G.key_present())
        self.assertNotIn(KEY, self.helper_calls())

    def test_keychain_found_when_env_empty(self):
        self.helper({KEY: "fake-keychain-openai"})
        os.environ[KEY] = ""
        self.assertEqual(G.key_value(), "fake-keychain-openai")
        self.assertIn(KEY, self.helper_calls())

    def test_env_value_is_stripped(self):
        os.environ[KEY] = "  fake-env-openai \n"
        self.assertEqual(G.key_value(), "fake-env-openai")


class Mini(Case):
    def plant(self):
        self.helper({KEY: "fake-keychain-openai"})
        for f in KEY_FILES:
            self.write(f, "%s=fake-file-openai\n" % KEY)

    def assert_reads_nothing(self):
        with self.opens() as seen, self.quiet():
            self.assertIsNone(G.key_value())
            self.assertFalse(G.key_present())
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")
        self.assertNotIn("fake-", self.printed)

    def test_marker_and_no_env_reads_nothing_and_finds_nothing(self):
        self.plant()
        self.write(MARKER, "")
        self.assert_reads_nothing()

    def test_no_fallback_env_reads_nothing_and_finds_nothing(self):
        self.plant()
        os.environ["KEYS_NO_FALLBACK"] = "1"
        self.assert_reads_nothing()

    def test_marker_takes_env_only(self):
        self.plant()
        self.write(MARKER, "")
        os.environ[KEY] = "fake-env-openai"
        with self.opens() as seen:
            self.assertEqual(G.key_value(), "fake-env-openai")
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules)


class NeverRaises(Case):
    def test_none_and_empty_name_are_none_and_ask_nothing(self):
        loader = cast_keys._load_loader()
        with mock.patch.object(loader, "key") as k:
            self.assertIsNone(G.key_value(None))
            self.assertIsNone(G.key_value(""))
            k.assert_not_called()

    def test_a_failing_helper_is_none(self):
        self.write(".daemn/daemn_keys.py", "def key(n, required=False):\n    raise RuntimeError('boom')\n")
        self.assertIsNone(G.key_value())
        self._forget_helper()
        self.write(".daemn/daemn_keys.py", "this is not python (\n")
        self.assertIsNone(G.key_value())

    def test_an_unloadable_loader_is_none_and_said_so(self):
        with mock.patch.dict(sys.modules), \
                mock.patch.object(cast_keys, "_LOADER_PATH", self.home / "no-loader-here.py"):
            sys.modules.pop("company_keys_loader", None)
            self.assertIsNone(G.key_value())
            self.assertFalse(G.key_present())
            msg = cast_keys.missing(KEY)
            self.assertNotIn("company_keys_loader", sys.modules)
        self.assertIn(KEY, msg)
        self.assertIn("could not be asked", msg)
        with mock.patch.object(cast_keys, "_load_loader", side_effect=RuntimeError("boom")):
            self.assertIsNone(G.key_value())


class Messages(Case):
    def setUp(self):
        super().setUp()
        self.ws = Path(tempfile.mkdtemp(prefix="si194-cast-ws-"))
        self.addCleanup(shutil.rmtree, str(self.ws), True)
        FIX.workspace(self.ws)
        os.environ["AI_WORKSPACE"] = str(self.ws)
        # another key, present — so a leak of ANY value would show
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"

    def frame(self):
        f = self.ws / "frame_01.jpg"
        f.write_bytes(FIX.png_bytes())
        return str(f)

    def req(self):
        return {"brand": "acme", "role": "night baker", "id": "nb", "kind": "authority",
                "noun": "man", "who": "a man in his fifties", "wardrobe": "an apron",
                "world": "a bakery at 4am, flat overhead light",
                "baseline": self.frame(), "out": str(self.ws / "run")}

    def test_reads_print_nothing(self):
        with self.quiet():
            G.key_value()
            G.key_value("FAKE_SI194_MISSING")
            cast_keys.missing(KEY)
        self.assertEqual(self.printed, "")

    def test_generate_without_a_key_fails_out_loud_and_calls_no_runner(self):
        calls = []

        def runner(*a, **k):
            calls.append(a)
            raise AssertionError("a runner was reached")
        with self.quiet():
            out = G.generate("master", "fake prompt", self.frame(), self.ws / "job",
                             runner=runner, echo=print)
        self.assertIsNone(out["file"])
        self.assertEqual(calls, [])
        self.assertFalse((self.ws / "job").exists(), "nothing written before the key")
        err = out["error"]
        self.assertIn(KEY, err)
        self.assertIn("looked in: environment", err)
        self.assertIn("~/.daemn/daemn_keys.py", err)
        self.assertNotIn("fake-", err)
        self.assertNotIn("None", err)
        self.assertNotIn("fake-", self.printed)

    def test_the_dry_run_key_line_names_the_key_and_where_looked(self):
        with self.quiet():
            r, _resolved = C.dry_run(self.req(), lib=FIX.StubLibrary(),
                                     reader=FIX.StubReader(described=[]))
        line = [ln for ln in self.printed.splitlines() if " key " in ln and KEY in ln]
        self.assertEqual(len(line), 1, self.printed[-2000:])
        self.assertIn("MISSING", line[0])
        self.assertIn("looked in: environment", line[0])
        self.assertIn("~/.daemn/daemn_keys.py", line[0])
        self.assertGreaterEqual(r.missing, 1)
        self.assertNotIn("fake-", self.printed)

    def test_the_dry_run_key_line_when_found_shows_no_value(self):
        os.environ[KEY] = "fake-env-openai"
        with self.quiet():
            C.dry_run(self.req(), lib=FIX.StubLibrary(), reader=FIX.StubReader(described=[]))
        line = [ln for ln in self.printed.splitlines() if " key " in ln and KEY in ln]
        self.assertEqual(len(line), 1, self.printed[-2000:])
        self.assertIn("OK", line[0])
        self.assertIn("through the key loader", line[0])
        self.assertNotIn("fake-", self.printed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
