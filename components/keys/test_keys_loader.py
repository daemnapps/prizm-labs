#!/usr/bin/env python3
"""SI-192 (keys loader) — declared test for components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME with fake files,
fake names (FAKE_SI192_*) and fake values (fake-*); os.environ is patched per
test. The real ~/.workflow-worker.env, ~/.daemn, ~/.gemini.env, ~/.apify.env
and the Keychain are never read — the loader resolves every path from HOME
at call time, and HOME points at the temp folder.

  (a) order        — env beats fallback; the fallback's own order (Keychain
                     helper, keys.env, apify, gemini) — SI-192b (loader skips
                     key file).
  (b) aliases      — G-A1 (no renames): old name and canonical name each
                     find the other's value; the seeded table is well formed.
  (c) mini rule    — a managed file present, or KEYS_NO_FALLBACK=1, skips
                     every old location (a fallback-only name returns None,
                     the Keychain helper is never called).
  (d) missing key  — KeyError names the key and the places looked, no value.
  (e) file format  — malformed lines skipped; an undecodable file ignored.
  (f) no leaks     — load()'s result shows names only in repr/str.
  (g) managed file — SI-192b (loader skips key file): ~/.workflow-worker.env
                     is never opened; on the mini a job's keys are exactly
                     the ones in its environment (WM-14 (scoped job env)).

Run: cd components/keys && python3 test_keys_loader.py
"""
import builtins
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loader  # noqa: E402

A = "FAKE_SI192_ALPHA"
OLD = "FAKE_SI192_OLD"
NEW = "FAKE_SI192_NEW"
FB_ONLY = "FAKE_SI192_FALLBACK_ONLY"
MISSING = "FAKE_SI192_MISSING"
FAKE_A = "FAKE_SI192_A"
FAKE_B = "FAKE_SI192_B"


class LoaderCase(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si192-home-"))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("FAKE_SI192_") and k != loader.NO_FALLBACK_ENV}
        env["HOME"] = str(self.home)
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, str(self.home), True)
        self.addCleanup(self._forget_helper)

    def _forget_helper(self):
        sys.modules.pop("daemn_keys", None)
        folder = str(self.home / ".daemn")
        while folder in sys.path:
            sys.path.remove(folder)

    def write(self, rel, text):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            p.write_bytes(text)
        else:
            p.write_text(text)
        return p

    def helper(self, values):
        lines = ["VALUES = %r" % (values,), "CALLS = []",
                 "def key(n):", "    CALLS.append(n)", "    return VALUES.get(n)"]
        self.write(".daemn/daemn_keys.py", "\n".join(lines) + "\n")


class Order(LoaderCase):
    def test_env_wins_with_managed_file_present(self):
        self.write(".workflow-worker.env", A + "=fake-managed\n")
        os.environ[A] = "fake-env"
        self.assertEqual(loader.key(A), "fake-env")

    def test_managed_file_value_is_never_used(self):
        self.write(".workflow-worker.env", A + "=fake-managed\n")
        self.assertIsNone(loader.key(A, required=False))

    def test_empty_env_value_falls_through(self):
        self.write(".apify.env", A + "=fake-apify\n")
        os.environ[A] = ""
        self.assertEqual(loader.key(A), "fake-apify")

    def test_env_beats_fallback(self):
        self.write(".daemn/keys.env", A + "=fake-fallback\n")
        os.environ[A] = "fake-env"
        self.assertEqual(loader.key(A), "fake-env")

    def test_fallback_used_without_managed_file(self):
        self.write(".apify.env", A + "=fake-apify\n")
        self.assertEqual(loader.key(A), "fake-apify")

    def test_fallback_tuple_is_keychain_first(self):
        self.assertEqual(loader.FALLBACK, ("keychain", "~/.daemn/keys.env",
                                           "~/.apify.env", "~/.gemini.env"))

    def test_fallback_order(self):
        self.write(".daemn/keys.env", A + "=fake-daemn\n")
        self.write(".gemini.env", A + "=fake-gemini\n")
        self.write(".apify.env", A + "=fake-apify\n")
        self.helper({A: "fake-keychain"})
        self.assertEqual(loader.key(A), "fake-keychain")
        self.helper({})
        self._forget_helper()
        self.assertEqual(loader.key(A), "fake-daemn")
        (self.home / ".daemn" / "keys.env").unlink()
        self.assertEqual(loader.key(A), "fake-apify")
        (self.home / ".apify.env").unlink()
        self.assertEqual(loader.key(A), "fake-gemini")

    def test_load_reads_each_in_order(self):
        self.write(".apify.env", A + "=fake-apify\n")
        os.environ[NEW] = "fake-env"
        self.assertEqual(dict(loader.load([A, NEW])),
                         {A: "fake-apify", NEW: "fake-env"})


class Aliases(LoaderCase):
    def setUp(self):
        super().setUp()
        p = mock.patch.dict(loader.ALIASES, {OLD: NEW})
        p.start()
        self.addCleanup(p.stop)

    def test_old_name_finds_canonical_value(self):
        os.environ[NEW] = "fake-new"
        self.assertEqual(loader.key(OLD), "fake-new")

    def test_canonical_name_finds_old_value(self):
        os.environ[OLD] = "fake-old"
        self.assertEqual(loader.key(NEW), "fake-old")

    def test_canonical_name_finds_old_value_in_fallback(self):
        self.write(".daemn/keys.env", OLD + "=fake-old\n")
        self.assertEqual(loader.key(NEW), "fake-old")

    def test_aliases_both_ways_on_the_mini(self):
        self.write(".workflow-worker.env", NEW + "=fake-managed\n")
        os.environ[OLD] = "fake-old"
        self.assertEqual(loader.key(NEW), "fake-old")
        del os.environ[OLD]
        os.environ[NEW] = "fake-new"
        self.assertEqual(loader.key(OLD), "fake-new")

    def test_canonical_wins_within_one_source(self):
        self.write(".daemn/keys.env",
                   OLD + "=fake-old\n" + NEW + "=fake-new\n")
        self.assertEqual(loader.key(OLD), "fake-new")

    def test_source_order_beats_name_order(self):
        os.environ[OLD] = "fake-old-env"
        self.write(".daemn/keys.env", NEW + "=fake-new-daemn\n")
        self.assertEqual(loader.key(NEW), "fake-old-env")

    def test_load_keys_by_the_name_asked(self):
        os.environ[NEW] = "fake-new"
        self.assertEqual(dict(loader.load([OLD])), {OLD: "fake-new"})

    def test_seeded_table_is_well_formed(self):
        real = {k: v for k, v in loader.ALIASES.items() if k != OLD}
        self.assertEqual(real, {
            "SUPABASE_DB_URL": "DATABASE_URL",
            "HF_API_KEY_ID": "HIGGSFIELD_KEY_ID",
            "HF_API_KEY_SECRET": "HIGGSFIELD_KEY_SECRET",
        })
        for old, new in loader.ALIASES.items():
            self.assertNotEqual(old, new)
            self.assertNotIn(new, loader.ALIASES, "canonical name is itself an alias")


class MiniRule(LoaderCase):
    def seed_fallback(self):
        for rel in (".daemn/keys.env", ".gemini.env", ".apify.env"):
            self.write(rel, FB_ONLY + "=fake-personal\n")
        self.helper({FB_ONLY: "fake-keychain"})

    def assert_no_fallback(self):
        self.assertTrue(loader.fallback_skipped())
        self.assertIsNone(loader.key(FB_ONLY, required=False))
        self.assertEqual(dict(loader.load([FB_ONLY], required=False)), {})
        self.assertNotIn("daemn_keys", sys.modules, "Keychain helper was imported")

    def test_managed_file_present_skips_fallback(self):
        self.write(".workflow-worker.env", A + "=fake-managed\n")
        self.seed_fallback()
        self.assert_no_fallback()
        self.assertIsNone(loader.key(A, required=False))
        os.environ[A] = "fake-env"
        self.assertEqual(loader.key(A), "fake-env")

    def test_empty_managed_file_still_marks_the_mini(self):
        self.write(".workflow-worker.env", "")
        self.seed_fallback()
        self.assert_no_fallback()

    def test_keys_no_fallback_env_skips_fallback(self):
        os.environ[loader.NO_FALLBACK_ENV] = "1"
        self.seed_fallback()
        self.assert_no_fallback()

    def test_fallback_read_when_neither_marker(self):
        self.seed_fallback()
        self.assertFalse(loader.fallback_skipped())
        self.assertEqual(loader.key(FB_ONLY), "fake-keychain")

    def test_mini_missing_message_says_fallback_skipped(self):
        os.environ[loader.NO_FALLBACK_ENV] = "1"
        with self.assertRaises(KeyError) as cm:
            loader.key(MISSING)
        msg = str(cm.exception)
        self.assertIn("skipped", msg)
        self.assertNotIn(".gemini.env", msg)


class Missing(LoaderCase):
    def seed_other_values(self):
        os.environ[A] = "fake-secret-env"
        self.write(".daemn/keys.env", NEW + "=fake-secret-daemn\n")
        self.write(".gemini.env", OLD + "=fake-secret-gemini\n")

    def assert_clean(self, msg):
        for v in ("fake-secret-env", "fake-secret-daemn", "fake-secret-gemini"):
            self.assertNotIn(v, msg)

    def test_message_names_key_and_places_never_a_value(self):
        self.seed_other_values()
        with self.assertRaises(KeyError) as cm:
            loader.key(MISSING)
        msg = str(cm.exception)
        self.assertIn(MISSING, msg)
        for place in ("environment", "~/.daemn/keys.env",
                      "~/.daemn/daemn_keys.py", "~/.gemini.env", "~/.apify.env"):
            self.assertIn(place, msg)
        self.assertNotIn("~/.workflow-worker.env", msg)
        self.assert_clean(msg)

    def test_message_names_aliases_looked(self):
        with mock.patch.dict(loader.ALIASES, {OLD: NEW}):
            with self.assertRaises(KeyError) as cm:
                loader.key(NEW)
        self.assertIn(NEW, str(cm.exception))
        self.assertIn(OLD, str(cm.exception))

    def test_not_required_returns_none(self):
        self.assertIsNone(loader.key(MISSING, required=False))

    def test_load_names_every_missing_key(self):
        self.seed_other_values()
        with self.assertRaises(KeyError) as cm:
            loader.load([A, MISSING, FB_ONLY])
        msg = str(cm.exception)
        self.assertIn(MISSING, msg)
        self.assertIn(FB_ONLY, msg)
        self.assert_clean(msg)


class FileFormat(LoaderCase):
    def test_malformed_fallback_lines_are_skipped(self):
        self.write(".daemn/keys.env", "\n".join([
            "# a comment",
            "",
            "this line has no equals sign",
            "=fake-orphan",
            "BAD NAME=fake-bad",
            "1BAD=fake-digit",
            A + "=",
            NEW + " = 'fake-quoted' ",
            OLD + "=fake-old=with-equals",
        ]) + "\n")
        self.assertEqual(loader.key(NEW), "fake-quoted")
        self.assertEqual(loader.key(OLD), "fake-old=with-equals")
        self.assertIsNone(loader.key(A, required=False))
        self.assertIsNone(loader.key("BAD NAME", required=False))
        self.assertIsNone(loader.key("1BAD", required=False))

    def test_undecodable_fallback_file_is_ignored_not_raised(self):
        self.write(".gemini.env", b"\xff\xfe\x00" + A.encode() + b"=\xff\n")
        os.environ[NEW] = "fake-env"
        self.assertIsNone(loader.key(A, required=False))
        self.assertEqual(loader.key(NEW), "fake-env")

    def test_broken_keychain_helper_is_silent(self):
        self.write(".daemn/daemn_keys.py", "raise RuntimeError('fake broken helper')\n")
        self.write(".apify.env", A + "=fake-apify\n")
        self.assertEqual(loader.key(A), "fake-apify")


class NoLeaks(LoaderCase):
    def test_load_result_repr_and_str_show_names_only(self):
        os.environ[A] = "fake-leak-env"
        self.write(".daemn/keys.env", NEW + "=fake-leak-daemn\n")
        got = loader.load([A, NEW])
        self.assertIsInstance(got, dict)
        for text in (repr(got), str(got), "%s" % (got,), "{}".format(got)):
            self.assertIn(A, text)
            self.assertIn(NEW, text)
            self.assertNotIn("fake-leak", text)

    def test_key_returns_the_plain_string(self):
        os.environ[A] = "fake-plain"
        got = loader.key(A)
        self.assertIs(type(got), str)
        self.assertEqual(got, "fake-plain")

    def test_nothing_is_printed(self):
        import contextlib
        os.environ[A] = "fake-quiet"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            loader.key(A)
            loader.load([A])
            loader.key(MISSING, required=False)
            try:
                loader.key(MISSING)
            except KeyError:
                pass
        self.assertEqual(out.getvalue() + err.getvalue(), "")


class ManagedFileNeverRead(LoaderCase):
    """SI-192b (loader skips key file) MUST NOT CHANGE: on the mini a job's
    keys are exactly the ones in its environment (WM-14 (scoped job env))."""

    def setUp(self):
        super().setUp()
        self.managed = self.write(".workflow-worker.env",
                                  FAKE_A + "=fake-managed-secret\n")
        os.environ[FAKE_B] = "fake-env-b"
        self.opened = []
        self._spy()

    def _record(self, target):
        if isinstance(target, (str, bytes, os.PathLike)):
            self.opened.append(os.path.realpath(os.fsdecode(target)))

    def _spy(self):
        real_open, real_io_open = builtins.open, io.open
        real_read_text = pathlib.Path.read_text
        real_read_bytes = pathlib.Path.read_bytes
        real_path_open = pathlib.Path.open
        case = self

        def spy_open(file, *a, **kw):
            case._record(file)
            return real_open(file, *a, **kw)

        def spy_io_open(file, *a, **kw):
            case._record(file)
            return real_io_open(file, *a, **kw)

        def spy_read_text(self, *a, **kw):
            case._record(self)
            return real_read_text(self, *a, **kw)

        def spy_read_bytes(self, *a, **kw):
            case._record(self)
            return real_read_bytes(self, *a, **kw)

        def spy_path_open(self, *a, **kw):
            case._record(self)
            return real_path_open(self, *a, **kw)

        for p in (mock.patch.object(builtins, "open", spy_open),
                  mock.patch.object(io, "open", spy_io_open),
                  mock.patch.object(pathlib.Path, "read_text", spy_read_text),
                  mock.patch.object(pathlib.Path, "read_bytes", spy_read_bytes),
                  mock.patch.object(pathlib.Path, "open", spy_path_open)):
            p.start()
            self.addCleanup(p.stop)

    def assert_managed_never_opened(self):
        self.assertNotIn(os.path.realpath(str(self.managed)), self.opened,
                         "the managed file was opened")

    def test_spy_sees_a_read(self):
        # The spy works: reading a fallback file is recorded.
        os.environ.pop(loader.NO_FALLBACK_ENV, None)
        self.managed.unlink()
        fb = self.write(".apify.env", FAKE_A + "=fake-apify\n")
        del self.opened[:]
        self.assertEqual(loader.key(FAKE_A), "fake-apify")
        self.assertIn(os.path.realpath(str(fb)), self.opened)

    def test_key_named_only_in_managed_file_is_none(self):
        self.assertTrue(loader.fallback_skipped())
        self.assertIsNone(loader.key(FAKE_A, required=False))
        self.assert_managed_never_opened()

    def test_load_has_only_the_environment_key(self):
        got = loader.load([FAKE_A, FAKE_B], required=False)
        self.assertEqual(dict(got), {FAKE_B: "fake-env-b"})
        self.assert_managed_never_opened()

    def test_required_missing_never_opens_or_leaks(self):
        with self.assertRaises(KeyError) as cm:
            loader.load([FAKE_A, FAKE_B])
        msg = str(cm.exception)
        self.assertIn(FAKE_A, msg)
        for text in (msg, repr(cm.exception)):
            self.assertNotIn("fake-managed-secret", text)
            self.assertNotIn("fake-env-b", text)
        got = loader.load([FAKE_A, FAKE_B], required=False)
        for text in (repr(got), str(got)):
            self.assertNotIn("fake-", text)
        self.assert_managed_never_opened()

    def test_personal_files_and_keychain_skipped_too(self):
        for rel in (".daemn/keys.env", ".gemini.env", ".apify.env"):
            self.write(rel, FAKE_A + "=fake-personal\n")
        self.helper({FAKE_A: "fake-keychain"})
        self.assertIsNone(loader.key(FAKE_A, required=False))
        self.assertNotIn("daemn_keys", sys.modules, "Keychain helper was imported")
        self.assert_managed_never_opened()


if __name__ == "__main__":
    unittest.main(verbosity=2)
