#!/usr/bin/env python3
"""SI-194 (readers use loader), dispatch 4 — image-production reads its keys
through ip_keys.key(), which asks components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn. Values are fake-*.
gemini_image.py's key name is fixed in its code, so its tests use that name —
with fake values only. No transport is ever reached: no network. The real
~/.daemn, ~/.workflow-worker.env, ~/.gemini.env, ~/.apify.env and the Keychain
are never read.

  (a) loader    — ip_keys loads components/keys/loader.py by path as
                  shared_keys_loader, reuses it; gemini_image shares it.
  (b) via key   — route.key_value and gemini_image.key() ask ip_keys.key(NAME);
                  neither imports the helper or names a key file in code;
                  judge, providers and dryrun still ask route.key_value.
  (c) order     — env beats the Keychain; the Keychain is found when the env
                  is empty; ~/.gemini.env still supplies gemini_image.
  (d) mini      — with ~/.workflow-worker.env present, neither the helper nor
                  ~/.gemini.env is read.
  (e) empty     — key_value(None) and key_value('') are None.
  (f) no raise  — a failing loader, helper or odd name is None, never raised.
  (g) messages  — no value in any message or output; a missing key exits
                  naming the key and where the loader looked.

Run: python3 tools/image-production/tests/test_si194_ip_keys.py
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
LANE = HERE.parent
ENGINE = LANE / "image_production"
GEMINI_IMAGE = LANE / "static" / "tools" / "gemini_image.py"
REPO = next(r for r in LANE.parents if (r / "components" / "keys" / "loader.py").is_file())
sys.path.append(str(LANE))                         # APPEND — never insert at 0
from image_production import ip_keys               # noqa: E402
from image_production import judge as J            # noqa: E402
from image_production import providers as PV       # noqa: E402
from image_production import route as R            # noqa: E402


def _load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# By path, as finish.py and ocr_copy.py run it — static/tools never on sys.path.
gemini_image = _load_by_path("si194_ip_gemini_image", GEMINI_IMAGE)

GEMINI = "GEMINI_API_KEY"
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"
KEY_FILES = (".gemini.env", ".apify.env", ".daemn/keys.env")

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-ip-home-"))
        self.addCleanup(shutil.rmtree, str(self.home), True)
        loader = ip_keys._load_loader()
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
        files = {str(self.home / f) for f in KEY_FILES}
        return sorted(files & set(seen))

    @contextlib.contextmanager
    def quiet(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield
        self.printed = out.getvalue() + err.getvalue()

    def gemini_exit(self):
        with self.assertRaises(SystemExit) as cm:
            gemini_image.key()
        return str(cm.exception.code)


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = ip_keys._load_loader()
        self.assertEqual(loader.__name__, "shared_keys_loader")
        self.assertIs(sys.modules["shared_keys_loader"], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertNotIn(str(REPO / "components" / "keys"), sys.path)
        self.assertIs(ip_keys._load_loader(), loader, "loaded once, then reused")

    def test_gemini_image_holds_the_engine_ip_keys_and_the_same_loader(self):
        ip = gemini_image._ip_keys()
        self.assertEqual(Path(ip.__file__).resolve(), ENGINE / "ip_keys.py")
        self.assertIs(gemini_image._ip_keys(), ip, "loaded once, then reused")
        self.assertIs(ip._load_loader(), ip_keys._load_loader())
        self.assertNotIn(str(GEMINI_IMAGE.parent), sys.path)


class ViaKey(Case):
    def test_key_value_asks_ip_keys(self):
        with mock.patch.object(ip_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(R.key_value("FAKE_SI194_A"), "fake-via-key")
            k.assert_called_once_with("FAKE_SI194_A")
        with mock.patch.object(ip_keys, "key", return_value="fake-via-key") as k:
            self.assertTrue(R.key_present({"key": "FAKE_SI194_B"}))
            k.assert_called_once_with("FAKE_SI194_B")
        with mock.patch.object(ip_keys, "key", return_value=None):
            self.assertFalse(R.key_present({"key": "FAKE_SI194_B"}))

    def test_gemini_image_asks_ip_keys(self):
        ip = gemini_image._ip_keys()
        with mock.patch.object(ip, "key", return_value="fake-via-key") as k:
            self.assertEqual(gemini_image.key(), "fake-via-key")
            k.assert_called_once_with(GEMINI)

    def test_no_reader_imports_the_helper_or_names_a_key_file(self):
        banned = (HELPER, ".daemn", ".gemini.env", ".apify.env", "keys.env")
        for path in (ENGINE / "route.py", ENGINE / "ip_keys.py", GEMINI_IMAGE):
            tree = ast.parse(path.read_text())
            docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body \
                        and isinstance(node.body[0], ast.Expr) \
                        and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                    docs.add(id(node.body[0].value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertNotIn(HELPER, [a.name for a in node.names], path.name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, HELPER, path.name)
                if isinstance(node, ast.Name):
                    self.assertNotEqual(node.id, HELPER, path.name)
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and id(node) not in docs:
                    for b in banned:
                        self.assertNotIn(b, node.value, "%s names %s in code" % (path.name, b))

    def test_judge_providers_dryrun_still_ask_key_value(self):
        for name, call in (("judge.py", "R.key_value("), ("providers.py", "R.key_value("),
                           ("dryrun.py", "R.key_present(")):
            with self.subTest(file=name):
                self.assertIn(call, (ENGINE / name).read_text())


class Order(Case):
    def test_env_beats_keychain(self):
        self.helper({"FAKE_SI194_A": "fake-keychain-a", GEMINI: "fake-gemini-keychain"})
        os.environ["FAKE_SI194_A"] = "fake-env-a"
        os.environ[GEMINI] = "fake-gemini-env"
        self.assertEqual(R.key_value("FAKE_SI194_A"), "fake-env-a")
        self.assertEqual(R.key_value(GEMINI), "fake-gemini-env")
        self.assertEqual(gemini_image.key(), "fake-gemini-env")

    def test_keychain_found_when_env_empty(self):
        self.helper({"FAKE_SI194_A": "fake-keychain-a", GEMINI: "fake-gemini-keychain"})
        os.environ["FAKE_SI194_A"] = ""
        self.assertEqual(R.key_value("FAKE_SI194_A"), "fake-keychain-a")
        self.assertEqual(R.key_value(GEMINI), "fake-gemini-keychain")
        self.assertEqual(gemini_image.key(), "fake-gemini-keychain")

    def test_env_value_is_stripped(self):
        os.environ["FAKE_SI194_A"] = "  fake-env-a \n"
        self.assertEqual(R.key_value("FAKE_SI194_A"), "fake-env-a")
        os.environ[GEMINI] = " fake-gemini-env\n"
        self.assertEqual(gemini_image.key(), "fake-gemini-env")

    def test_gemini_env_file_still_supplies_gemini_image(self):
        self.write(".gemini.env", "%s=fake-gemini-file\n" % GEMINI)
        self.assertEqual(gemini_image.key(), "fake-gemini-file")
        # the one-loader design: the engine's own reads find it there too
        self.assertEqual(R.key_value(GEMINI), "fake-gemini-file")
        self.helper({GEMINI: "fake-gemini-keychain"})
        self.assertEqual(gemini_image.key(), "fake-gemini-keychain")
        os.environ[GEMINI] = "fake-gemini-env"
        self.assertEqual(gemini_image.key(), "fake-gemini-env")


class Mini(Case):
    def setUp(self):
        super().setUp()
        self.write(MARKER, "")
        self.helper({GEMINI: "fake-gemini-keychain", "FAKE_SI194_A": "fake-keychain-a"})
        self.write(".gemini.env", "%s=fake-gemini-file\n" % GEMINI)
        self.write(".daemn/keys.env", "%s=fake-gemini-vault\nFAKE_SI194_A=fake-vault-a\n" % GEMINI)

    def test_marker_takes_env_only(self):
        os.environ[GEMINI] = "fake-gemini-env"
        os.environ["FAKE_SI194_A"] = "fake-env-a"
        with self.opens() as seen:
            self.assertEqual(R.key_value("FAKE_SI194_A"), "fake-env-a")
            self.assertEqual(R.key_value(GEMINI), "fake-gemini-env")
            self.assertEqual(gemini_image.key(), "fake-gemini-env")
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")

    def test_marker_and_no_env_reads_nothing_and_finds_nothing(self):
        with self.opens() as seen, self.quiet():
            self.assertIsNone(R.key_value("FAKE_SI194_A"))
            self.assertIsNone(R.key_value(GEMINI))
            msg = self.gemini_exit()
        self.assertIn(GEMINI, msg)
        self.assertIn("old locations skipped", msg)
        self.assertNotIn("fake-", msg)
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")
        self.assertNotIn("fake-", self.printed)


class Empty(Case):
    def test_none_and_empty_name_are_none_and_ask_nothing(self):
        loader = ip_keys._load_loader()
        os.environ["FAKE_SI194_A"] = "fake-env-a"
        with mock.patch.object(loader, "key") as k:
            self.assertIsNone(R.key_value(None))
            self.assertIsNone(R.key_value(""))
            self.assertFalse(R.key_present({}))
            k.assert_not_called()


class NeverRaises(Case):
    def test_a_failing_loader_is_none(self):
        loader = ip_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")):
            self.assertIsNone(R.key_value("FAKE_SI194_A"))
            msg = self.gemini_exit()
        self.assertIn(GEMINI, msg)
        self.assertIn("could not be asked", msg)

    def test_a_failing_helper_is_none(self):
        self.write(".daemn/daemn_keys.py", "def key(n, required=False):\n    raise RuntimeError('boom')\n")
        self.assertIsNone(R.key_value("FAKE_SI194_A"))
        self._forget_helper()
        self.write(".daemn/daemn_keys.py", "this is not python (\n")
        self.assertIsNone(R.key_value("FAKE_SI194_A"))

    def test_an_odd_name_or_value_is_none(self):
        for name in ("not a name!", "FAKE SI194", 42):
            with self.subTest(name=name):
                self.assertIsNone(R.key_value(name))
        os.environ["FAKE_SI194_A"] = "   "
        self.assertIsNone(R.key_value("FAKE_SI194_A"))

    def test_gemini_image_exits_when_ip_keys_cannot_load(self):
        with mock.patch.object(gemini_image, "_ip_keys", side_effect=ImportError("boom")):
            msg = self.gemini_exit()
        self.assertIn(GEMINI, msg)
        self.assertIn("could not be asked", msg)


class Messages(Case):
    def test_reads_print_nothing(self):
        self.helper({"FAKE_SI194_A": "fake-keychain-a"})
        self.write(".gemini.env", "%s=fake-gemini-file\n" % GEMINI)
        with self.quiet():
            R.key_value("FAKE_SI194_A")
            R.key_value("FAKE_SI194_MISSING")
            gemini_image.key()
        self.assertEqual(self.printed, "")

    def test_gemini_image_missing_names_the_key_and_where_looked_never_a_value(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"
        with self.quiet():
            msg = self.gemini_exit()
        self.assertIn(GEMINI, msg)
        self.assertIn("looked in: environment", msg)
        self.assertIn("~/.daemn/daemn_keys.py", msg)
        self.assertIn("~/.gemini.env", msg)
        self.assertNotIn("fake-", msg)
        self.assertNotIn("None", msg)
        self.assertNotIn("fake-", self.printed)

    def test_engine_callers_refuse_with_no_value_and_send_nothing(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"

        def transport(*a, **k):
            raise AssertionError("a transport was reached")
        with self.quiet():
            with self.assertRaises(SystemExit) as cm:
                PV.generate({"key": "FAKE_SI194_OPENAI", "provider": "openai"},
                            "fake prompt", [], str(self.home / "out.png"), "4:5",
                            transport=transport)
            gen = str(cm.exception.code)
            with self.assertRaises(SystemExit) as cm:
                J.google_caller("fake prompt", str(self.home / "none.png"),
                                {"key": "FAKE_SI194_GEMINI", "vendor_model": "stub"},
                                transport=transport)
            jud = str(cm.exception.code)
        self.assertIn("FAKE_SI194_OPENAI", gen)
        self.assertIn("FAKE_SI194_GEMINI", jud)
        for msg in (gen, jud, self.printed):
            self.assertNotIn("fake-", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
