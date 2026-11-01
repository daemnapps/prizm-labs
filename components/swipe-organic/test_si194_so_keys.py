#!/usr/bin/env python3
"""SI-194 (readers use loader), dispatch for swipe-organic — pull_creator_posts.py
reads APIFY_TOKEN through so_keys.key(), which asks components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn. Values are fake-*.
pull_creator_posts.py's key name is fixed in its code, so its tests use that
name — with fake values only. urlopen is patched to fail if touched: no
network. The real ~/.daemn, ~/.workflow-worker.env, ~/.apify.env and the
Keychain are never read.

  (a) loader   — so_keys loads components/keys/loader.py by path as
                 upright_keys_loader, never via sys.path; the reader shares it.
  (b) via key  — pull_creator_posts.key() asks so_keys; no `security`,
                 `find-generic-password` or subprocess call is left (AST).
  (c) order    — env beats the Keychain (the one intended change: the old
                 key() ignored the environment); the fake helper supplies the
                 key when the env is empty and there is no mini marker.
  (d) mini     — with ~/.workflow-worker.env present, neither the helper nor
                 ~/.apify.env is read; key() exits naming APIFY_TOKEN.
  (e) empty    — so_keys.key(None) and so_keys.key('') are None.
  (f) no raise — so_keys.key and so_keys.missing never raise.
  (g) messages — no fake value in any message, SystemExit text or output.
  (h) import   — importing pull_creator_posts.py makes no network call.

Run: python3 components/swipe-organic/test_si194_so_keys.py
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
import urllib.request
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
READER = HERE / "pull_creator_posts.py"
SO_KEYS = HERE / "so_keys.py"
REPO = next(r for r in HERE.parents if (r / "components" / "keys" / "loader.py").is_file())

APIFY = "APIFY_TOKEN"
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"
KEY_FILES = (".apify.env", ".gemini.env", ".daemn/keys.env")

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


def _no_network(*a, **k):
    raise AssertionError("urlopen was reached")


def _load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# By path — this folder is never put on sys.path. urlopen fails if touched.
with mock.patch.object(urllib.request, "urlopen", _no_network):
    reader = _load_by_path("si194_so_pull_creator_posts", READER)
so_keys = reader.so_keys


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-so-home-"))
        self.addCleanup(shutil.rmtree, str(self.home), True)
        loader = so_keys._load_loader()
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
        net = mock.patch.object(urllib.request, "urlopen", _no_network)
        net.start()
        self.addCleanup(net.stop)
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
        files = {str(self.home / f) for f in KEY_FILES}
        return sorted(files & set(seen))

    @contextlib.contextmanager
    def quiet(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield
        self.printed = out.getvalue() + err.getvalue()

    def reader_exit(self):
        with self.assertRaises(SystemExit) as cm:
            reader.key()
        return str(cm.exception.code)


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = so_keys._load_loader()
        self.assertEqual(loader.__name__, "upright_keys_loader")
        self.assertIs(sys.modules["upright_keys_loader"], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertNotIn(str(REPO / "components" / "keys"), sys.path)
        self.assertIs(so_keys._load_loader(), loader, "loaded once, then reused")

    def test_reader_holds_this_folders_so_keys_and_neither_touches_sys_path(self):
        self.assertEqual(Path(so_keys.__file__).resolve(), SO_KEYS)
        for path in (SO_KEYS, READER):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in ("insert", "append"):
                    base = node.value
                    self.assertFalse(isinstance(base, ast.Attribute) and base.attr == "path"
                                     and isinstance(base.value, ast.Name) and base.value.id == "sys",
                                     "%s touches sys.path" % path.name)


class ViaKey(Case):
    def test_reader_key_asks_so_keys(self):
        with mock.patch.object(so_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(reader.key(), "fake-via-key")
            k.assert_called_once_with(APIFY)

    def test_no_security_call_left_in_the_reader(self):
        text = READER.read_text()
        tree = ast.parse(text)
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body \
                    and isinstance(node.body[0], ast.Expr) \
                    and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                docs.add(id(node.body[0].value))
        key_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertNotIn("subprocess", [a.name for a in node.names])
                self.assertNotIn(HELPER, [a.name for a in node.names])
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, ("subprocess", HELPER))
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, ("subprocess", HELPER))
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and id(node) not in docs:
                for b in ("security", "find-generic-password", ".daemn", ".apify.env"):
                    self.assertNotIn(b, node.value, "pull_creator_posts.py names %s in code" % b)
            if isinstance(node, ast.FunctionDef) and node.name == "key":
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                            and isinstance(sub.func.value, ast.Name) and sub.func.value.id == "so_keys":
                        key_calls.append(sub.func.attr)
        self.assertIn("key", key_calls, "key() does not call so_keys.key")
        self.assertIn("missing", key_calls, "key() does not call so_keys.missing")

    def test_the_run_is_behind_main(self):
        tree = ast.parse(READER.read_text())
        names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
        self.assertIn("main", names)
        last = tree.body[-1]
        self.assertIsInstance(last, ast.If)
        self.assertIn("__main__", ast.dump(last.test))
        for n in tree.body:
            if isinstance(n, (ast.Assign, ast.Expr)):
                self.assertNotIn("urlopen", ast.dump(n))
                self.assertNotIn("post", [c.func.id for c in ast.walk(n)
                                          if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)])


class Order(Case):
    def test_env_beats_keychain(self):
        self.helper({APIFY: "fake-apify-keychain"})
        os.environ[APIFY] = "fake-apify-env"
        self.assertEqual(so_keys.key(APIFY), "fake-apify-env")
        self.assertEqual(reader.key(), "fake-apify-env")

    def test_keychain_found_when_env_empty_and_no_marker(self):
        self.helper({APIFY: "fake-apify-keychain"})
        os.environ[APIFY] = ""
        self.assertEqual(so_keys.key(APIFY), "fake-apify-keychain")
        self.assertEqual(reader.key(), "fake-apify-keychain")

    def test_env_value_is_stripped(self):
        os.environ[APIFY] = "  fake-apify-env \n"
        self.assertEqual(reader.key(), "fake-apify-env")


class Mini(Case):
    def setUp(self):
        super().setUp()
        self.write(MARKER, "")
        self.helper({APIFY: "fake-apify-keychain"})
        self.write(".apify.env", "%s=fake-apify-file\n" % APIFY)
        self.write(".daemn/keys.env", "%s=fake-apify-vault\n" % APIFY)

    def test_marker_takes_env_only(self):
        os.environ[APIFY] = "fake-apify-env"
        with self.opens() as seen:
            self.assertEqual(reader.key(), "fake-apify-env")
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")

    def test_marker_and_no_env_reads_nothing_and_exits(self):
        with self.opens() as seen, self.quiet():
            self.assertIsNone(so_keys.key(APIFY))
            msg = self.reader_exit()
        self.assertIn(APIFY, msg)
        self.assertIn("old locations skipped", msg)
        self.assertNotIn("fake-", msg)
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")
        self.assertNotIn("fake-", self.printed)


class Empty(Case):
    def test_none_and_empty_name_are_none_and_ask_nothing(self):
        loader = so_keys._load_loader()
        os.environ["FAKE_SI194_A"] = "fake-env-a"
        with mock.patch.object(loader, "key") as k:
            self.assertIsNone(so_keys.key(None))
            self.assertIsNone(so_keys.key(""))
            k.assert_not_called()


class NeverRaises(Case):
    def test_a_failing_loader_is_none_and_missing_still_answers(self):
        loader = so_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")):
            self.assertIsNone(so_keys.key(APIFY))
            m = so_keys.missing(APIFY)
            msg = self.reader_exit()
        self.assertIn(APIFY, m)
        self.assertIn("could not be asked", m)
        self.assertIn(APIFY, msg)

    def test_a_failing_helper_is_none(self):
        self.write(".daemn/daemn_keys.py", "def key(n, required=False):\n    raise RuntimeError('boom')\n")
        self.assertIsNone(so_keys.key("FAKE_SI194_A"))
        self._forget_helper()
        self.write(".daemn/daemn_keys.py", "this is not python (\n")
        self.assertIsNone(so_keys.key("FAKE_SI194_A"))

    def test_odd_names_and_values_never_raise(self):
        for name in ("not a name!", "FAKE SI194", 42, None, ""):
            with self.subTest(name=name):
                self.assertIsNone(so_keys.key(name))
                self.assertIsInstance(so_keys.missing(name), str)
        os.environ["FAKE_SI194_A"] = "   "
        self.assertIsNone(so_keys.key("FAKE_SI194_A"))


class Messages(Case):
    def test_reads_print_nothing(self):
        self.helper({APIFY: "fake-apify-keychain"})
        with self.quiet():
            so_keys.key(APIFY)
            so_keys.key("FAKE_SI194_MISSING")
            reader.key()
        self.assertEqual(self.printed, "")

    def test_missing_names_the_key_and_where_looked_never_a_value(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"
        self.write(".apify.env", "FAKE_SI194_OTHER=fake-secret-file\n")
        with self.quiet():
            msg = self.reader_exit()
            m = so_keys.missing(APIFY)
        for text in (msg, m):
            self.assertIn(APIFY, text)
            self.assertIn("looked in: environment", text)
            self.assertIn("~/.daemn/daemn_keys.py", text)
            self.assertIn("~/.apify.env", text)
            self.assertNotIn("fake-", text)
            self.assertNotIn("None", text)
        self.assertNotIn("fake-", self.printed)


class Import(Case):
    def test_importing_the_reader_makes_no_network_call(self):
        with self.quiet():
            mod = _load_by_path("si194_so_pull_creator_posts_again", READER)
        self.assertTrue(callable(mod.main))
        self.assertEqual(self.printed, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
