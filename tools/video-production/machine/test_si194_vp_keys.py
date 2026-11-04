#!/usr/bin/env python3
"""SI-194 (readers use loader), dispatch 1 — video-production reads every key
through vp_keys.key(), which asks components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn; machine/.env is replaced
by a temp file. Values are fake-*; the vp_keys tests use fake names
(FAKE_SI194_*). The readers' own key names are fixed in their code, so the
reader tests use those names — with fake values only. The real ~/.daemn,
~/.workflow-worker.env, ~/.gemini.env, ~/.apify.env, machine/.env and the
Keychain are never read. No network: face_lock's one call is caught at urlopen.

  (a) loader   — vp_keys loads components/keys/loader.py by path as
                 upright_keys_loader, reuses it, never raises.
  (b) via key  — every reader finds a value that only the loader reads
                 (~/.daemn/keys.env); no reader imports the helper or puts
                 ~/.daemn on sys.path itself.
  (c) order    — the environment beats the Keychain for every reader; the
                 Keychain is found when the environment is empty.
  (d) mini     — with ~/.workflow-worker.env present the helper is never
                 imported and machine/.env is never read.
  (e) missing  — None (or the reader's existing exit), no value in any message.
  (f) .env     — sequence still finds a key that is only in
                 machine/.env on a person's machine; no other reader reads it.

Run: cd tools/video-production/machine && python3 test_si194_vp_keys.py
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
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"


def load(name):
    spec = importlib.util.spec_from_file_location("si194_" + name, HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vp_keys = load("vp_keys")
platform = load("provider_platform")
direct_google = load("direct_google")
direct_byteplus = load("direct_byteplus")
direct_openai = load("direct_openai")
make_bank = load("make_bank")
lineparity = load("lineparity")
clip_kit = load("clip_kit")
voice = load("voice")
sequence = load("sequence")
face_lock = load("face_lock")

# The files this dispatch switched (WRITABLE in the card's instruction).
READER_FILES = ("direct_byteplus", "direct_google", "direct_openai", "face_lock",
                "lineparity", "make_bank", "clip_kit", "provider_platform",
                "sequence", "voice")

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


def _exit_or_none(fn):
    """The value fn returns, or None when it exits (the raising readers)."""
    def get():
        try:
            return fn()
        except SystemExit:
            return None
    return get


# (label, key name, module, getter) — the getter returns the value the reader used.
READERS = [
    ("direct_google", "GEMINI_API_KEY", direct_google, direct_google.key_of),
    ("direct_byteplus", "BYTEPLUS_API_KEY", direct_byteplus, direct_byteplus.key_of),
    ("direct_openai", "OPENAI_API_KEY", direct_openai, direct_openai.key_of),
    ("make_bank", "ELEVENLABS_API_KEY", make_bank, make_bank.key_of),
    ("lineparity", "ELEVENLABS_API_KEY", lineparity, lineparity.key_of),
    ("voice", "ELEVENLABS_API_KEY", voice, voice.key_of),
    ("sequence", "FAL_KEY", sequence, _exit_or_none(sequence.key)),
    # face_lock left this list 2026-10-21: its one key read was the typed OpenAI fallback judge (gpt-5.5), removed
    # by the verify pass (row 17, VIDEO-RULINGS V2) — face_lock reads no key of its own now
]
RAISERS = [("sequence", sequence.key)]
PLATFORM_NAME = "FAKE_SI194_PLATFORM_KEY"


def _platform_source(name=PLATFORM_NAME):
    ok, why = platform._detect({"key_env": name})
    return why[0] if ok else None


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-home-"))
        loader = vp_keys._load_loader()
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
        self.addCleanup(shutil.rmtree, str(self.home), True)
        # machine/.env → a temp file, for every vp_keys this test can reach.
        self.local_env = self.home / "machine-dot-env"
        for m in {id(m.vp_keys): m.vp_keys for _, _, m, _ in READERS}.values():
            q = mock.patch.object(m, "LOCAL_ENV", self.local_env)
            q.start()
            self.addCleanup(q.stop)
        q = mock.patch.object(vp_keys, "LOCAL_ENV", self.local_env)
        q.start()
        self.addCleanup(q.stop)
        q = mock.patch.object(platform.vp_keys, "LOCAL_ENV", self.local_env)
        q.start()
        self.addCleanup(q.stop)
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

    def _spy_reads(self):
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
            p = mock.patch.object(target, attr, wrap(getattr(target, attr), method))
            p.start()
            self.addCleanup(p.stop)
        return opened


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = vp_keys._load_loader()
        self.assertEqual(loader.__name__, "upright_keys_loader")
        self.assertIs(sys.modules["upright_keys_loader"], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertNotIn(str(REPO / "components" / "keys"), sys.path)
        self.assertIs(vp_keys._load_loader(), loader, "loaded once, then reused")

    def test_never_raises(self):
        loader = vp_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")):
            self.assertIsNone(vp_keys.key("FAKE_SI194_ANY"))
            self.assertIsNone(vp_keys.key("FAKE_SI194_ANY", local_env=True))

    def test_env_beats_keychain_beats_local_env(self):
        self.write(self.local_env.name, "FAKE_SI194_A=fake-local\n")
        self.assertEqual(vp_keys.key("FAKE_SI194_A", local_env=True), "fake-local")
        self.assertIsNone(vp_keys.key("FAKE_SI194_A"), "machine/.env only on local_env=True")
        self.helper({"FAKE_SI194_A": "fake-keychain"})
        self.assertEqual(vp_keys.key("FAKE_SI194_A", local_env=True), "fake-keychain")
        os.environ["FAKE_SI194_A"] = "fake-env"
        self.assertEqual(vp_keys.key("FAKE_SI194_A", local_env=True), "fake-env")

    def test_no_fallback_flag_also_skips_local_env(self):
        self.write(self.local_env.name, "FAKE_SI194_A=fake-local\n")
        os.environ[vp_keys._load_loader().NO_FALLBACK_ENV] = "1"
        self.assertIsNone(vp_keys.key("FAKE_SI194_A", local_env=True))


class ViaKey(Case):
    def test_every_reader_finds_a_value_only_the_loader_reads(self):
        lines = sorted({"%s=fake-file-%s" % (n, n.lower()) for _, n, _, _ in READERS})
        self.write(".daemn/keys.env", "\n".join(lines + [PLATFORM_NAME + "=fake-file-p"]) + "\n")
        for label, name, _, get in READERS:
            with self.subTest(reader=label):
                self.assertEqual(get(), "fake-file-" + name.lower())
        self.assertEqual(_platform_source(), PLATFORM_NAME + " in vault")
        self.assertTrue(platform._vault_key(PLATFORM_NAME))

    def test_every_reader_holds_the_one_loader(self):
        loader = vp_keys._load_loader()
        for label, _, mod, _ in READERS + [("platform", None, platform, None)]:
            with self.subTest(reader=label):
                self.assertEqual(Path(mod.vp_keys.__file__).resolve(), HERE / "vp_keys.py")
                self.assertIs(mod.vp_keys._load_loader(), loader)

    def test_no_reader_imports_the_helper_or_puts_it_on_sys_path(self):
        for name in READER_FILES:
            src = (HERE / (name + ".py")).read_text()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                with self.subTest(file=name, line=getattr(node, "lineno", 0)):
                    if isinstance(node, ast.Import):
                        self.assertNotIn(HELPER, [a.name for a in node.names])
                    if isinstance(node, ast.ImportFrom):
                        self.assertNotEqual(node.module, HELPER)
                    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                            and node.func.attr in ("insert", "append")):
                        self.assertNotIn(".daemn", ast.get_source_segment(src, node) or "")


class Order(Case):
    def test_env_beats_keychain_for_every_reader(self):
        names = {n for _, n, _, _ in READERS} | {PLATFORM_NAME}
        self.helper({n: "fake-keychain" for n in names})
        for n in names:
            os.environ[n] = "fake-env"
        for label, _, _, get in READERS:
            with self.subTest(reader=label):
                self.assertEqual(get(), "fake-env")
        self.assertEqual(_platform_source(), PLATFORM_NAME + " in env")

    def test_keychain_found_when_env_empty(self):
        names = {n for _, n, _, _ in READERS} | {PLATFORM_NAME}
        self.helper({n: "fake-keychain" for n in names})
        for label, _, _, get in READERS:
            with self.subTest(reader=label):
                self.assertEqual(get(), "fake-keychain")
        self.assertEqual(_platform_source(), PLATFORM_NAME + " in vault")


class Mini(Case):
    def test_marker_skips_helper_old_files_and_local_env(self):
        marker = self.write(MARKER, "FAKE_SI194_MANAGED=fake-managed\n")
        names = {n for _, n, _, _ in READERS} | {PLATFORM_NAME}
        self.helper({n: "fake-keychain" for n in names})
        body = "".join("%s=fake-personal\n" % n for n in sorted(names))
        for rel in (".daemn/keys.env", ".apify.env", ".gemini.env", self.local_env.name):
            self.write(rel, body)
        opened = self._spy_reads()
        for label, _, _, get in READERS:
            with self.subTest(reader=label):
                self.assertIsNone(get())
        self.assertIsNone(_platform_source())
        self.assertFalse(platform._vault_key(PLATFORM_NAME))
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")
        seen = [str(Path(p).expanduser()) for p in opened]
        self.assertNotIn(str(self.local_env), seen, "machine/.env was read")
        self.assertNotIn(str(marker), seen, "the managed file was opened")

    def test_marker_still_lets_the_environment_through(self):
        self.write(MARKER, "")
        for _, n, _, _ in READERS:
            os.environ[n] = "fake-env"
        for label, _, _, get in READERS:
            with self.subTest(reader=label):
                self.assertEqual(get(), "fake-env")
        self.assertNotIn(HELPER, sys.modules)


class Missing(Case):
    def test_missing_is_none_for_every_reader(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            for label, _, _, get in READERS:
                with self.subTest(reader=label):
                    self.assertIsNone(get())
            self.assertIsNone(_platform_source())
        self.assertNotIn("fake-", out.getvalue() + err.getvalue())

    def test_raising_readers_keep_their_exit_and_name_no_value(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"
        for label, fn in RAISERS:
            with self.subTest(reader=label):
                with self.assertRaises(SystemExit) as cm:
                    fn()
                msg = str(cm.exception.code)
                self.assertIn("FAL_KEY", msg)
                self.assertIn(".env", msg)
                self.assertNotIn("upright", msg)
                self.assertNotIn("fake-", msg)


class LocalEnv(Case):
    def test_sequence_finds_a_key_only_in_machine_env(self):
        self.write(self.local_env.name, 'FAL_KEY="fake-local-fal"\n')
        self.assertEqual(sequence.key(), "fake-local-fal")

    def test_other_readers_never_read_machine_env(self):
        names = sorted({n for _, n, _, _ in READERS})
        self.write(self.local_env.name, "".join("%s=fake-local\n" % n for n in names))
        for label, _, _, get in READERS:
            if label == "sequence":
                continue
            with self.subTest(reader=label):
                self.assertIsNone(get())


if __name__ == "__main__":
    unittest.main(verbosity=2)
