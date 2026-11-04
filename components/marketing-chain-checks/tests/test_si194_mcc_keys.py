#!/usr/bin/env python3
"""SI-194 (readers use loader), dispatch for marketing-chain-checks — viewer.py
and review.py read their keys through mcc_keys.key(), which asks
components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn. Values are fake-*. The key
names are fixed in the readers' code, so the tests use those names — with fake
values only. urlopen is patched to capture the Request: no network. The real
~/.daemn, ~/.workflow-worker.env, ~/.gemini.env, ~/.apify.env and the Keychain
are never read. viewer.ask() short-circuits under unittest, so _key, _openai
and review._key are called directly.

  (a) loader    — mcc_keys loads components/keys/loader.py by path as
                  company_keys_loader; components/keys is never on sys.path.
  (b) via key   — no daemn_keys import left in marketing_chain_checks/; the
                  three reads ask mcc_keys.key(NAME).
  (c) order     — env beats the helper; the helper is found when the env is
                  empty, without ~/.daemn on sys.path beforehand; ~/.gemini.env
                  still supplies GEMINI_API_KEY on a person's machine.
  (d) mini      — with ~/.workflow-worker.env present, neither the helper nor
                  ~/.gemini.env is read; review._key is None; viewer._key and
                  _openai raise before any request is built.
  (e) no raise  — review._key is None when missing or the loader fails, and
                  after_stage with a caller still files without crashing.
  (f) messages  — no value in any message; a missing key names the key and
                  where the loader looked.

Run: python3 components/marketing-chain-checks/tests/test_si194_mcc_keys.py
"""
import ast
import builtins
import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
COMP = HERE.parent
PKG = COMP / "marketing_chain_checks"
REPO = next(r for r in COMP.parents if (r / "components" / "keys" / "loader.py").is_file())
sys.path.append(str(COMP))                         # APPEND — never insert at 0
from marketing_chain_checks import mcc_keys        # noqa: E402
from marketing_chain_checks import review as RV    # noqa: E402
from marketing_chain_checks import viewer as V     # noqa: E402

GEMINI = "GEMINI_API_KEY"
OPENAI = "OPENAI_API_KEY"
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"
KEY_FILES = (".gemini.env", ".apify.env", ".daemn/keys.env")
ANSWER = '{"answer": "fake"}'

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


class _Resp:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-mcc-home-"))
        self.addCleanup(shutil.rmtree, str(self.home), True)
        loader = mcc_keys._load_loader()
        env = {k: v for k, v in os.environ.items()
               if k != loader.NO_FALLBACK_ENV
               and not _credential_looking(k)
               and k not in loader.ALIASES
               and k not in loader.ALIASES.values()}
        env["HOME"] = str(self.home)
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._forget_helper)
        self._forget_helper()
        self.sent = []
        u = mock.patch.object(V.urllib.request, "urlopen", self._urlopen)
        u.start()
        self.addCleanup(u.stop)

    def _urlopen(self, req, *a, **k):
        self.sent.append(req)
        return _Resp(json.dumps({"choices": [{"message": {"content": ANSWER}}]}).encode())

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

    def openai_auth(self):
        """_openai's answer and the Authorization header of the Request it built."""
        got = V._openai("fake prompt", False, "fake-model")
        self.assertEqual(got, ANSWER)
        self.assertEqual(len(self.sent), 1)
        return self.sent[-1].get_header("Authorization")

    def raises(self, fn, *a):
        with self.assertRaises(RuntimeError) as cm:
            fn(*a)
        return str(cm.exception)


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = mcc_keys._load_loader()
        self.assertEqual(loader.__name__, "company_keys_loader")
        self.assertIs(sys.modules["company_keys_loader"], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertNotIn(str(REPO / "components" / "keys"), sys.path)
        self.assertIs(mcc_keys._load_loader(), loader, "loaded once, then reused")

    def test_mcc_keys_has_no_relative_import(self):
        tree = ast.parse((PKG / "mcc_keys.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0, "mcc_keys.py has a relative import")


class ViaKey(Case):
    def test_no_daemn_keys_import_left_in_the_package(self):
        for path in sorted(PKG.glob("*.py")):
            text = path.read_text()
            self.assertIsNone(re.search(r"^\s*(import|from)\s+%s\b" % HELPER, text, re.M), path.name)
            self.assertIsNone(re.search(r"\b%s\s*\.\s*key\s*\(" % HELPER, text), path.name)
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.Import):
                    self.assertNotIn(HELPER, [a.name for a in node.names], path.name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, HELPER, path.name)
                if isinstance(node, ast.Name):
                    self.assertNotEqual(node.id, HELPER, path.name)

    def test_the_three_reads_ask_mcc_keys(self):
        with mock.patch.object(mcc_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(V._key(), "fake-via-key")
            k.assert_called_once_with(GEMINI)
        with mock.patch.object(mcc_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(RV._key(), "fake-via-key")
            k.assert_called_once_with(GEMINI)
        with mock.patch.object(mcc_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(self.openai_auth(), "Bearer fake-via-key")
            k.assert_called_once_with(OPENAI)

    def test_openai_request_shape_unchanged(self):
        os.environ[OPENAI] = "fake-openai-env"
        self.assertEqual(V._openai("fake prompt", True, "fake-model"), {"answer": "fake"})
        req = self.sent[-1]
        self.assertEqual(req.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(req.get_header("Authorization"), "Bearer fake-openai-env")
        self.assertEqual(json.loads(req.data), {"model": "fake-model",
                                                "messages": [{"role": "user", "content": "fake prompt"}],
                                                "response_format": {"type": "json_object"}})


class Order(Case):
    def test_env_beats_the_helper(self):
        self.helper({GEMINI: "fake-gemini-keychain", OPENAI: "fake-openai-keychain"})
        os.environ[GEMINI] = "fake-gemini-env"
        os.environ[OPENAI] = "fake-openai-env"
        self.assertEqual(V._key(), "fake-gemini-env")
        self.assertEqual(RV._key(), "fake-gemini-env")
        self.assertEqual(self.openai_auth(), "Bearer fake-openai-env")

    def test_helper_found_when_env_empty_without_daemn_on_sys_path(self):
        self.helper({GEMINI: "fake-gemini-keychain", OPENAI: "fake-openai-keychain"})
        self.assertNotIn(str(self.home / ".daemn"), sys.path)
        self.assertNotIn(HELPER, sys.modules)
        self.assertEqual(V._key(), "fake-gemini-keychain")
        self._forget_helper()
        self.assertNotIn(str(self.home / ".daemn"), sys.path)
        self.assertEqual(RV._key(), "fake-gemini-keychain")
        self._forget_helper()
        self.assertNotIn(str(self.home / ".daemn"), sys.path)
        self.assertEqual(self.openai_auth(), "Bearer fake-openai-keychain")

    def test_env_value_is_stripped(self):
        os.environ[GEMINI] = "  fake-gemini-env \n"
        self.assertEqual(V._key(), "fake-gemini-env")
        self.assertEqual(RV._key(), "fake-gemini-env")

    def test_gemini_env_file_still_supplies_gemini(self):
        self.write(".gemini.env", "%s=fake-gemini-file\n" % GEMINI)
        self.assertEqual(V._key(), "fake-gemini-file")
        self.assertEqual(RV._key(), "fake-gemini-file")


class Mini(Case):
    def setUp(self):
        super().setUp()
        self.write(MARKER, "")
        self.helper({GEMINI: "fake-gemini-keychain", OPENAI: "fake-openai-keychain"})
        self.write(".gemini.env", "%s=fake-gemini-file\n" % GEMINI)
        self.write(".daemn/keys.env", "%s=fake-gemini-vault\n%s=fake-openai-vault\n" % (GEMINI, OPENAI))

    def test_marker_takes_env_only(self):
        os.environ[GEMINI] = "fake-gemini-env"
        os.environ[OPENAI] = "fake-openai-env"
        with self.opens() as seen:
            self.assertEqual(V._key(), "fake-gemini-env")
            self.assertEqual(RV._key(), "fake-gemini-env")
            self.assertEqual(self.openai_auth(), "Bearer fake-openai-env")
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")

    def test_marker_and_no_env_reads_nothing_and_sends_nothing(self):
        with self.opens() as seen, self.quiet():
            self.assertIsNone(RV._key())
            gem = self.raises(V._key)
            oai = self.raises(V._openai, "fake prompt", False, "fake-model")
        self.assertEqual(self.sent, [], "a request reached urlopen")
        self.assertIn(GEMINI, gem)
        self.assertIn(OPENAI, oai)
        for msg in (gem, oai):
            self.assertIn("skipped (managed file", msg)
            self.assertNotIn("fake-", msg)
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")
        self.assertNotIn("fake-", self.printed)


class NeverRaises(Case):
    def test_review_key_is_none_when_missing(self):
        self.assertIsNone(RV._key())

    def test_review_key_is_none_when_the_loader_fails(self):
        loader = mcc_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")):
            self.assertIsNone(RV._key())
            msg = self.raises(V._key)
        self.assertIn(GEMINI, msg)
        self.assertIn("could not be asked", msg)

    def test_review_key_is_none_when_the_helper_fails(self):
        self.write(".daemn/daemn_keys.py", "def key(n, required=False):\n    raise RuntimeError('boom')\n")
        self.assertIsNone(RV._key())
        self._forget_helper()
        self.write(".daemn/daemn_keys.py", "this is not python (\n")
        self.assertIsNone(RV._key())

    def test_after_stage_with_a_caller_still_files(self):
        run = self.home / "run"
        with self.quiet():
            got = RV.after_stage("fake-tool", "fake-stage", run,
                                 caller=lambda parts: {"fake-stage": {"ok": True, "severity": "NOTE", "problems": []}})
        self.assertEqual(got["fake-stage"]["ok"], True)
        self.assertTrue((run / "qc-log" / "QC-LOG.md").is_file())

    def test_after_stage_with_no_key_files_unchecked_naming_the_key(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"
        run = self.home / "run"
        with self.quiet():
            got = RV.after_stage("fake-tool", "fake-stage", run, caller=lambda parts: RV.ask(parts))
        row = got["fake-stage"]
        self.assertEqual(row["severity"], "UNCHECKED")
        self.assertIn(GEMINI, row["problems"][0])
        self.assertEqual(self.sent, [])
        log = (run / "qc-log" / "QC-LOG.md").read_text()
        filed = "".join(p.read_text() for p in (run / "qc-log").glob("*.json"))
        for text in (json.dumps(got), log, filed, self.printed):
            self.assertNotIn("fake-", text.replace("fake-tool", "").replace("fake-stage", ""))


class Messages(Case):
    def test_reads_print_nothing(self):
        self.helper({GEMINI: "fake-gemini-keychain", OPENAI: "fake-openai-keychain"})
        with self.quiet():
            V._key()
            RV._key()
            self.openai_auth()
            mcc_keys.key("FAKE_SI194_MISSING")
        self.assertEqual(self.printed, "")

    def test_missing_names_the_key_and_where_looked_never_a_value(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"
        with self.quiet():
            gem = self.raises(V._key)
            oai = self.raises(V._openai, "fake prompt", False, "fake-model")
            rev = self.raises(RV.ask, [{"text": "fake prompt"}])
            direct = mcc_keys.missing(GEMINI)
        self.assertEqual(self.sent, [], "a request reached urlopen")
        self.assertIn(OPENAI, oai)
        for msg in (gem, rev, direct):
            self.assertIn(GEMINI, msg)
        for msg in (gem, oai, rev, direct):
            self.assertIn("looked in: environment", msg)
            self.assertIn("~/.daemn/daemn_keys.py", msg)
            self.assertIn("~/.gemini.env", msg)
            self.assertNotIn("fake-", msg)
            self.assertNotIn("None", msg)
        self.assertNotIn("fake-", self.printed)

    def test_empty_name_is_none_and_asks_nothing(self):
        loader = mcc_keys._load_loader()
        with mock.patch.object(loader, "key") as k:
            self.assertIsNone(mcc_keys.key(None))
            self.assertIsNone(mcc_keys.key(""))
            k.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
