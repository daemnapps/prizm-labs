#!/usr/bin/env python3
"""SI-194 (readers use loader), meta-upload dispatch — meta.token() reads its
key through mu_keys.key(), which asks components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn. Values are fake-*.
PRIZM_META_TOKEN is the default name fixed in meta.token's signature, so tests
of the default use that name — with fake values only. subprocess is patched to
fail the test if anything starts a process; no network. The real ~/.daemn,
~/.workflow-worker.env, ~/.gemini.env, ~/.apify.env and the Keychain are never
read.

  (a) loader    — mu_keys loads components/keys/loader.py by path as
                  company_keys_loader, never on sys.path, only at call time.
  (b) surface   — token() keeps its name, signature and default; a brand's
                  token_key is the name asked; Meta(brand, tok=) never asks.
  (c) order     — env beats the Keychain helper; the helper is found, stripped,
                  when the env is empty.
  (d) mini      — with ~/.workflow-worker.env present the helper is neither
                  imported nor called, and token() exits.
  (e) missing   — SystemExit (not KeyError) naming the key, where the loader
                  looked, and the system-user-token hint; never a value.
  (f) no shell  — no `security` (no subprocess at all) is ever run.
  (g) mu_keys   — key(None)/key('') are None; key() never raises, never prints.

Run: python3 components/meta-upload/tests/test_si194_mu_keys.py
"""
import ast
import contextlib
import importlib
import inspect
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
LANE = Path(__file__).resolve().parent.parent
REPO = next(r for r in LANE.parents if (r / "components" / "keys" / "loader.py").is_file())
sys.path.insert(0, str(LANE))
import meta      # noqa: E402
import mu_keys   # noqa: E402
from brand import Brand  # noqa: E402

DEFAULT = "PRIZM_META_TOKEN"
BRAND_KEY = "FAKE_SI194_MU_BRAND_TOKEN"
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"
LOADER = "company_keys_loader"
HINT = "system-user token from Business Settings"

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


def fake_brand(token_key=None):
    """A Brand that never opens brands/ — only the fields Meta.__init__ reads."""
    b = Brand.__new__(Brand)
    b.name = "fake-si194-brand"
    b.d = {"page_id": "0"}
    if token_key:
        b.d["token_key"] = token_key
    return b


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-mu-home-"))
        self.addCleanup(shutil.rmtree, str(self.home), True)
        loader = mu_keys._load_loader()
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
        # (f) any process started anywhere fails the test — even one a caller swallows.
        self.processes = []
        self.addCleanup(self._no_process_started)

        def refuse(*a, **k):
            self.processes.append(a[0] if a else k.get("args"))
            raise AssertionError("a subprocess was started: %r" % (a[0] if a else k,))
        for fn in ("run", "Popen", "call", "check_call", "check_output"):
            sp = mock.patch.object(subprocess, fn, refuse)
            sp.start()
            self.addCleanup(sp.stop)

    def _no_process_started(self):
        self.assertEqual(self.processes, [], "a subprocess was started")

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
        """A FAKE ~/.daemn/daemn_keys.py; every name it is asked lands in ASKED."""
        self.write(".daemn/daemn_keys.py",
                   "VALUES = %r\n"
                   "ASKED = []\n"
                   "def key(n, required=False):\n"
                   "    ASKED.append(n)\n"
                   "    return VALUES.get(n)\n" % (values,))

    @contextlib.contextmanager
    def quiet(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield
        self.printed = out.getvalue() + err.getvalue()

    def token_exit(self, *a):
        with self.assertRaises(SystemExit) as cm:
            meta.token(*a)
        self.assertNotIsInstance(cm.exception, KeyError)
        return str(cm.exception.code)


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = mu_keys._load_loader()
        self.assertEqual(loader.__name__, LOADER)
        self.assertIs(sys.modules[LOADER], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertNotIn(str(REPO / "components" / "keys"), sys.path)
        self.assertIs(mu_keys._load_loader(), loader, "loaded once, then reused")

    def test_importing_meta_reads_no_key(self):
        saved = {n: sys.modules.pop(n) for n in ("meta", "mu_keys", LOADER) if n in sys.modules}
        try:
            with mock.patch.dict(os.environ, {}, clear=True):
                os.environ["HOME"] = str(self.home)
                with self.quiet():
                    fresh = importlib.import_module("meta")
            self.assertIsNot(fresh, meta)
            self.assertNotIn(LOADER, sys.modules, "importing meta loaded the key loader")
            self.assertNotIn(HELPER, sys.modules, "importing meta imported the Keychain helper")
            self.assertEqual(self.printed, "")
        finally:
            for n in ("meta", "mu_keys", LOADER):
                sys.modules.pop(n, None)
            sys.modules.update(saved)

    def test_meta_runs_no_security_and_names_no_key_place(self):
        tree = ast.parse((LANE / "meta.py").read_text())
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body \
                    and isinstance(node.body[0], ast.Expr) \
                    and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                docs.add(id(node.body[0].value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
                self.assertNotIn("subprocess", names)
                self.assertNotIn(HELPER, names)
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, ("subprocess", HELPER))
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                for banned in ("security", "find-generic-password", ".daemn", "daemn-", ".env"):
                    self.assertNotIn(banned, node.value, "meta.py names %s in code" % banned)


class Surface(Case):
    def test_token_keeps_name_signature_and_default(self):
        self.assertTrue(callable(meta.token))
        self.assertEqual(meta.token.__name__, "token")
        params = list(inspect.signature(meta.token).parameters.values())
        self.assertEqual([p.name for p in params], ["name"])
        self.assertEqual(params[0].default, DEFAULT)

    def test_token_asks_mu_keys_by_the_name_given(self):
        with mock.patch.object(mu_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(meta.token(), "fake-via-key")
            k.assert_called_once_with(DEFAULT)
        with mock.patch.object(mu_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(meta.token(BRAND_KEY), "fake-via-key")
            k.assert_called_once_with(BRAND_KEY)

    def test_a_brands_token_key_is_the_name_looked_up(self):
        self.helper({BRAND_KEY: "fake-brand-keychain", DEFAULT: "fake-default-keychain"})
        self.assertEqual(meta.token(BRAND_KEY), "fake-brand-keychain")
        self.assertEqual(sys.modules[HELPER].ASKED, [BRAND_KEY])

    def test_meta_with_tok_never_calls_token(self):
        with mock.patch.object(meta, "token", side_effect=AssertionError("token() asked")) as t:
            m = meta.Meta(fake_brand(BRAND_KEY), tok="fake-given")
        t.assert_not_called()
        self.assertEqual(m._t, "fake-given")

    def test_meta_without_tok_asks_the_brands_token_key(self):
        with mock.patch.object(meta, "token", return_value="fake-asked") as t:
            m = meta.Meta(fake_brand(BRAND_KEY))
        t.assert_called_once_with(BRAND_KEY)
        self.assertEqual(m._t, "fake-asked")
        with mock.patch.object(meta, "token", return_value="fake-asked") as t:
            meta.Meta(fake_brand())
        t.assert_called_once_with(DEFAULT)


class Order(Case):
    def test_env_beats_keychain(self):
        self.helper({DEFAULT: "fake-keychain", BRAND_KEY: "fake-brand-keychain"})
        os.environ[DEFAULT] = "fake-env"
        os.environ[BRAND_KEY] = "fake-brand-env"
        self.assertEqual(meta.token(), "fake-env")
        self.assertEqual(meta.token(BRAND_KEY), "fake-brand-env")

    def test_keychain_found_and_stripped_when_env_empty(self):
        self.helper({DEFAULT: "  fake-keychain \n"})
        os.environ[DEFAULT] = ""
        self.assertEqual(meta.token(), "fake-keychain")
        self.assertIn(DEFAULT, sys.modules[HELPER].ASKED)

    def test_env_value_is_stripped(self):
        os.environ[DEFAULT] = "  fake-env \n"
        self.assertEqual(meta.token(), "fake-env")


class Mini(Case):
    def setUp(self):
        super().setUp()
        self.write(MARKER, "")
        self.helper({DEFAULT: "fake-keychain"})
        self.write(".daemn/keys.env", "%s=fake-vault\n" % DEFAULT)

    def test_marker_and_no_env_neither_imports_nor_calls_the_helper(self):
        with self.quiet():
            msg = self.token_exit()
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")
        self.assertIn(DEFAULT, msg)
        self.assertIn("skipped (managed file", msg)
        self.assertIn(HINT, msg)
        self.assertNotIn("fake-", msg)
        self.assertNotIn("fake-", self.printed)

    def test_marker_takes_env_only(self):
        os.environ[DEFAULT] = "fake-env"
        self.assertEqual(meta.token(), "fake-env")
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")


class Missing(Case):
    def test_missing_is_systemexit_naming_key_places_and_hint_never_a_value(self):
        self.helper({"FAKE_SI194_MU_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_MU_OTHER"] = "fake-secret-env"
        with self.quiet():
            msg = self.token_exit()
        self.assertIn(DEFAULT, msg)
        self.assertIn("looked in: environment", msg)
        self.assertIn("~/.daemn/daemn_keys.py", msg)
        self.assertIn(HINT, msg)
        self.assertNotIn("fake-", msg)
        self.assertNotIn("None", msg)
        self.assertNotIn("fake-", self.printed)

    def test_missing_brand_key_names_that_key(self):
        with self.quiet():
            msg = self.token_exit(BRAND_KEY)
        self.assertIn(BRAND_KEY, msg)
        self.assertIn(HINT, msg)

    def test_meta_without_a_token_exits(self):
        with self.quiet():
            with self.assertRaises(SystemExit) as cm:
                meta.Meta(fake_brand(BRAND_KEY))
        self.assertIn(BRAND_KEY, str(cm.exception.code))

    def test_a_failing_loader_still_exits_with_the_hint(self):
        loader = mu_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")):
            with self.quiet():
                msg = self.token_exit()
        self.assertIn(DEFAULT, msg)
        self.assertIn("could not be asked", msg)
        self.assertIn(HINT, msg)


class MuKeys(Case):
    def test_none_and_empty_name_are_none_and_ask_nothing(self):
        loader = mu_keys._load_loader()
        with mock.patch.object(loader, "key") as k:
            self.assertIsNone(mu_keys.key(None))
            self.assertIsNone(mu_keys.key(""))
            k.assert_not_called()

    def test_never_raises(self):
        loader = mu_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")):
            self.assertIsNone(mu_keys.key(DEFAULT))
        self.write(".daemn/daemn_keys.py", "def key(n, required=False):\n    raise RuntimeError('boom')\n")
        self.assertIsNone(mu_keys.key(DEFAULT))
        self._forget_helper()
        self.write(".daemn/daemn_keys.py", "this is not python (\n")
        self.assertIsNone(mu_keys.key(DEFAULT))
        for name in ("not a name!", "FAKE SI194", 42):
            with self.subTest(name=name):
                self.assertIsNone(mu_keys.key(name))
        os.environ[DEFAULT] = "   "
        self.assertIsNone(mu_keys.key(DEFAULT))

    def test_never_prints(self):
        self.helper({DEFAULT: "fake-keychain"})
        with self.quiet():
            mu_keys.key(DEFAULT)
            mu_keys.key("FAKE_SI194_MU_MISSING")
            mu_keys.missing("FAKE_SI194_MU_MISSING")
            meta.token()
        self.assertEqual(self.printed, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
