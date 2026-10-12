#!/usr/bin/env python3
"""SI-193 (video-teardown keys reader) — keys.py reads through components/keys.

OFFLINE and FAKE: every test runs under a temporary HOME with fake files, fake
names (FAKE_SI193_*) and fake values (fake-*); os.environ is patched per test.
The Keychain helper is a fake daemn_keys.py written into the temp ~/.daemn, so
the real ~/.daemn, ~/.workflow-worker.env, ~/.gemini.env, ~/.apify.env and the
Keychain are never read.

  (a) loader     — keys.py loads components/keys/loader.py by path under its
                   own module name, never via sys.path.
  (b) order      — the environment beats the Keychain beats ~/.daemn/keys.env
                   beats ~/.apify.env beats ~/.gemini.env, through get() and
                   all_keys() alike (the order keys.py always had).
  (c) mini rule  — with a managed file, the managed file is never opened, the
                   old files and the helper are not read, and all_keys() is
                   the environment's keys only.
  (d) missing    — get() of a missing required key exits naming the key and
                   the places looked, never a value.
  (e) union      — all_keys()/status() list every name a source holds, values
                   from the loader; status() shows lengths, never a value.
  (f) env names  — the environment's credential-looking names are listed; its
                   other names (PATH, HOME, a setting) are not.

Run: cd tools/video-teardown/machine && python3 test_si193_keys_via_loader.py
"""
import builtins
import contextlib
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
sys.path.insert(0, str(HERE))
import keys  # noqa: E402

A = "FAKE_SI193_ALPHA"
B = "FAKE_SI193_BRAVO"
C = "FAKE_SI193_CHARLIE"
D = "FAKE_SI193_DELTA"
E = "FAKE_SI193_ECHO"
F = "FAKE_SI193_ENV_ONLY"
MISSING = "FAKE_SI193_MISSING"
MANAGED_KEY = "FAKE_SI193_MANAGED_KEY"
ENV_KEY = "FAKE_SI193_ENV_KEY"

# Credential-looking environment names, stated here independently of keys.py,
# so the real environment's keys never enter a test.
_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


class KeysCase(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si193-home-"))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("FAKE_SI193_")
               and k != keys._loader.NO_FALLBACK_ENV
               and not _credential_looking(k)
               and k not in keys._loader.ALIASES
               and k not in keys._loader.ALIASES.values()}
        env["HOME"] = str(self.home)
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, str(self.home), True)
        self.addCleanup(self._forget_helper)
        self._forget_helper()

    def _forget_helper(self):
        sys.modules.pop("daemn_keys", None)
        folder = str(self.home / ".daemn")
        while folder in sys.path:
            sys.path.remove(folder)

    def write(self, rel, text):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def helper(self, values, names=None, known=None):
        lines = ["VALUES = %r" % (values,),
                 "def key(n):", "    return VALUES.get(n)"]
        if names is not None:
            lines += ["def names():", "    return %r" % (list(names),)]
        if known is not None:
            lines += ["KNOWN = %r" % (tuple(known),)]
        self.write(".daemn/daemn_keys.py", "\n".join(lines) + "\n")

    def assert_no_fake_value(self, text):
        self.assertNotIn("fake-", text)


class Loader(KeysCase):
    def test_loaded_by_path_under_its_own_name(self):
        self.assertEqual(keys._loader.__name__, "shared_keys_loader")
        self.assertIs(sys.modules["shared_keys_loader"], keys._loader)
        self.assertEqual(Path(keys._loader.__file__).resolve(),
                         HERE.parents[2] / "components" / "keys" / "loader.py")
        self.assertNotIn(str(HERE.parents[1] / "keys"), sys.path)
        self.assertNotIn("loader", sys.modules)

    def test_public_names_stay(self):
        for name in ("VAULT", "LEGACY", "KEYCHAIN", "all_keys", "get",
                     "export", "status"):
            self.assertTrue(hasattr(keys, name), name)


class Order(KeysCase):
    def test_keychain_beats_keys_env(self):
        self.write(".daemn/keys.env", A + "=fake-file\n")
        self.helper({A: "fake-keychain"}, names=[A])
        self.assertEqual(keys.get(A), "fake-keychain")
        self.assertEqual(keys.all_keys()[A], "fake-keychain")

    def test_env_beats_file(self):
        self.write(".daemn/keys.env", A + "=fake-file\n")
        os.environ[A] = "fake-env"
        self.assertEqual(keys.get(A), "fake-env")
        self.assertEqual(keys.all_keys()[A], "fake-env")

    def test_env_beats_keychain_and_file(self):
        self.write(".daemn/keys.env", A + "=fake-file\n")
        self.helper({A: "fake-keychain"}, names=[A])
        os.environ[A] = "fake-env"
        self.assertEqual(keys.get(A), "fake-env")
        self.assertEqual(keys.all_keys()[A], "fake-env")

    def test_keys_env_beats_apify_beats_gemini(self):
        self.write(".daemn/keys.env", A + "=fake-daemn\n")
        self.write(".apify.env", A + "=fake-apify\n" + B + "=fake-apify\n")
        self.write(".gemini.env", A + "=fake-gemini\n" + B + "=fake-gemini\n"
                   + C + "=fake-gemini\n")
        self.assertEqual(keys.get(A), "fake-daemn")
        self.assertEqual(keys.get(B), "fake-apify")
        self.assertEqual(keys.get(C), "fake-gemini")
        self.assertEqual(keys.all_keys(),
                         {A: "fake-daemn", B: "fake-apify", C: "fake-gemini"})


class MiniRule(KeysCase):
    def _spy_opens(self):
        """Record every path opened through pathlib or open(); still opens it."""
        opened = []

        def wrap(orig, method):
            if method:
                def spy(self_, *a, **k):
                    opened.append(str(self_))
                    return orig(self_, *a, **k)
            else:
                def spy(file, *a, **k):
                    opened.append(str(file))
                    return orig(file, *a, **k)
            return spy

        for target, attr, method in ((pathlib.Path, "open", True),
                                     (pathlib.Path, "read_text", True),
                                     (pathlib.Path, "read_bytes", True),
                                     (builtins, "open", False),
                                     (io, "open", False)):
            p = mock.patch.object(target, attr,
                                  wrap(getattr(target, attr), method))
            p.start()
            self.addCleanup(p.stop)
        return opened

    def test_managed_file_skips_old_files_and_helper(self):
        managed = self.write(".workflow-worker.env",
                             MANAGED_KEY + "=fake-managed\n")
        for rel in (".daemn/keys.env", ".apify.env", ".gemini.env"):
            self.write(rel, B + "=fake-personal\n")
        self.helper({C: "fake-keychain"}, names=[C])
        os.environ[ENV_KEY] = "fake-env"
        opened = self._spy_opens()
        got = keys.all_keys()
        text = keys.status()
        self.assertEqual(got, {ENV_KEY: "fake-env"})
        self.assertIsNone(keys.get(MANAGED_KEY, required=False))
        self.assertIsNone(keys.get(B, required=False))
        self.assertIsNone(keys.get(C, required=False))
        self.assertNotIn(MANAGED_KEY, text)
        self.assertNotIn(MANAGED_KEY, repr(got))
        self.assertNotIn("fake-managed", repr(got) + text)
        self.assertNotIn("daemn_keys", sys.modules, "Keychain helper was imported")
        self.assertNotIn(str(managed),
                         [str(Path(p).expanduser()) for p in opened],
                         "the managed file was opened")
        self.assertTrue(managed.exists())


class Missing(KeysCase):
    def test_required_missing_exits_naming_key_and_places_no_value(self):
        os.environ[A] = "fake-secret-env"
        self.write(".daemn/keys.env", B + "=fake-secret-file\n")
        self.helper({C: "fake-secret-keychain"}, names=[C])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                keys.get(MISSING)
        msg = str(cm.exception.code)
        self.assertIn(MISSING, msg)
        for place in ("environment",
                      "~/.daemn/daemn_keys.py", "~/.daemn/keys.env",
                      "~/.apify.env", "~/.gemini.env"):
            self.assertIn(place, msg)
        self.assertNotIn("secrets.py", msg)
        self.assert_no_fake_value(msg + out.getvalue() + err.getvalue())

    def test_not_required_returns_none(self):
        self.assertIsNone(keys.get(MISSING, required=False))


class Union(KeysCase):
    def seed(self):
        self.write(".daemn/keys.env", A + "=fake-aaaa\n# a comment\n")
        self.write(".apify.env", B + "=fake-bbbbbb\n" + E + "=\n")
        self.write(".gemini.env", C + "=fake-cc\n")
        os.environ[F] = "fake-env-only"

    def test_all_keys_is_the_union_with_loader_values(self):
        self.seed()
        self.helper({D: "fake-ddd"}, names=[D, E])
        os.environ[A] = "fake-env-a"
        got = keys.all_keys()
        self.assertEqual(got, {A: "fake-env-a", B: "fake-bbbbbb",
                               C: "fake-cc", D: "fake-ddd"})
        self.assertNotIn(E, got, "a name with no value is dropped")
        self.assertNotIn(F, got, "a non-credential environment name is not listed")

    def test_helper_known_used_when_names_absent(self):
        self.helper({D: "fake-ddd"}, known=[D])
        self.assertEqual(keys.all_keys(), {D: "fake-ddd"})

    def test_status_lists_names_and_lengths_never_values(self):
        self.seed()
        self.helper({D: "fake-ddd"}, names=[D])
        text = keys.status()
        for name, value in ((A, "fake-aaaa"), (B, "fake-bbbbbb"),
                            (C, "fake-cc"), (D, "fake-ddd")):
            self.assertIn(name, text)
            self.assertIn("set (%d chars)" % len(value), text)
        self.assertNotIn(E, text)
        self.assert_no_fake_value(text)

    def test_status_with_nothing(self):
        self.assertTrue(keys.status().startswith("No keys found"))

    def test_export_fills_only_missing_environment_names(self):
        self.seed()
        os.environ[A] = "fake-env-a"
        keys.export()
        self.assertEqual(os.environ[A], "fake-env-a")
        self.assertEqual(os.environ[B], "fake-bbbbbb")
        self.assertEqual(os.environ[C], "fake-cc")


class EnvNames(KeysCase):
    def test_only_credential_looking_environment_names_are_listed(self):
        listed = {"FAKE_SI193_X" + s: "fake-v" + s.lower()
                  for s in ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID",
                            "_KEY_SECRET", "_DB_URL")}
        listed["DATABASE_URL"] = "fake-db"
        not_listed = {"PATH": "/fake/bin", "FAKE_SETTING_LOCK": "fake-lock"}
        os.environ.update(listed)
        os.environ.update(not_listed)
        got = keys.all_keys()
        self.assertEqual(got, listed)          # fires: every key name listed
        for n in list(not_listed) + ["HOME"]:  # releases: the rest are not
            self.assertIn(n, os.environ)
            self.assertNotIn(n, got)
        self.assertNotIn("FAKE_SETTING_LOCK", keys.status())


if __name__ == "__main__":
    unittest.main(verbosity=2)
