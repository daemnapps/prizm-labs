#!/usr/bin/env python3
"""SI-194 (readers use loader), dispatch 3 — image-teardown reads its keys
through it_keys.key(), which asks components/keys/loader.py.

OFFLINE and FAKE: every test runs under a temporary HOME; os.environ is patched
per test and stripped of every credential-looking name; the Keychain helper is
a FAKE daemn_keys.py written into the temp ~/.daemn. Values are fake-*. The
readers' key names are fixed in their code, so the reader tests use those names
— with fake values only. Every model call is patched before it is reached: no
network. The real ~/.daemn, ~/.workflow-worker.env, ~/.gemini.env, ~/.apify.env
and the Keychain are never read.

  (a) loader    — it_keys loads components/keys/loader.py by path as
                  shared_keys_loader, reuses it, never raises.
  (b) import    — gpt_drafts, draft_judge and carousel import in a fresh process
                  whose HOME has NO ~/.daemn; no reader imports the helper, puts
                  ~/.daemn on sys.path or names a key file in code.
  (c) via key   — every read site gets its key from it_keys.key(NAME).
  (d) order     — GEMINI_API_KEY: env beats the Keychain beats ~/.gemini.env,
                  through every reader; ~/.apify.env still supplies APIFY_TOKEN.
  (e) mini      — with ~/.workflow-worker.env present, neither the helper nor
                  ~/.gemini.env / ~/.apify.env is read.
  (f) check     — check.api_key() reports present / missing without opening
                  ~/.daemn/keys.env or ~/.gemini.env itself; names no value.
  (g) missing   — the script readers exit naming the key and where the loader
                  looked, never a value; a carousel dry run asks for no key.

Run: cd tools/image-teardown && python3 tests/test_si194_it_keys.py
"""
import ast
import builtins
import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LANE = HERE.parent
TOOLS = LANE / "tools"
REPO = next(r for r in LANE.parents if (r / "components" / "keys" / "loader.py").is_file())
sys.path.insert(0, str(TOOLS))
import it_keys  # noqa: E402
import gpt_drafts  # noqa: E402
import draft_judge  # noqa: E402
import carousel  # noqa: E402
import check  # noqa: E402
import gemini_image  # noqa: E402
import gemini_text  # noqa: E402
import pull_ig_image  # noqa: E402

GEMINI = "GEMINI_API_KEY"
APIFY = "APIFY_TOKEN"
HELPER = "daemn_keys"
MARKER = ".workflow-worker.env"
KEY_FILES = (".gemini.env", ".apify.env", ".daemn/keys.env")
READER_FILES = ("gpt_drafts", "draft_judge", "carousel", "gemini_image",
                "gemini_text", "pull_ig_image", "check")

_CRED = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _credential_looking(n):
    return n.endswith(_CRED) or n == "DATABASE_URL"


class Stop(Exception):
    """Raised by a patched model call once the reader has handed it its key."""


class Case(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="si194-it-home-"))
        self.addCleanup(shutil.rmtree, str(self.home), True)
        loader = it_keys._load_loader()
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
        self.work = self.home / "work"
        self.work.mkdir()

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

    # --- each reader, driven to the point where it hands its key on ------------
    # Each returns the key value the reader holds; the script readers exit when
    # it is missing, as before.

    def via_gemini_image(self):
        return gemini_image.key()

    def via_gemini_text(self):
        return gemini_text.key()

    def via_read_swipe(self):
        got = {}

        def ask(images, prompt, k, tries=3):
            got["k"] = k
            return {}
        with mock.patch.object(draft_judge, "ask", ask):
            gpt_drafts.read_swipe(self.work / "fake-swipe.jpg")
        return got["k"]

    def via_swipe_has_person(self):
        got = {}
        d = self.work / "drafts" / "fake-brand"
        d.mkdir(parents=True, exist_ok=True)
        cache = d / "swipe-subjects.json"
        if cache.exists():
            cache.unlink()   # its own temp file: a kept read would skip the key

        def read_swipe(src, k=None):
            got["k"] = k
            return {"v": gpt_drafts.READ_VERSION, "person": True}
        with mock.patch.object(gpt_drafts, "ROOT", self.work), \
                mock.patch.object(gpt_drafts, "read_swipe", read_swipe):
            gpt_drafts.swipe_has_person("fake-brand", [{"brief": "fake-b1", "run": "fake-run"}])
        return got["k"]

    def via_draft_judge(self):
        got = {}
        d = self.work / "drafts" / "fake-brand"
        d.mkdir(parents=True, exist_ok=True)
        (d / "jobs.json").write_text(json.dumps({"jobs": [{"brief": "fake-b1", "run": "fake-run"}]}))

        def swipe_has_person(brand, jobs):
            got["k"] = sys._getframe(1).f_locals["k"]   # main()'s own k, at its point of use
            raise Stop
        argv = ["draft_judge.py", "--brand", "fake-brand", "--dir", str(d)]
        with mock.patch.object(draft_judge, "ROOT", self.work), \
                mock.patch.object(gpt_drafts, "swipe_has_person", swipe_has_person), \
                mock.patch.object(sys, "argv", argv), \
                self.assertRaises(Stop):
            draft_judge.main()
        return got["k"]

    def via_carousel(self):
        got = {}
        a = types.SimpleNamespace(dry_run=False, rounds=1, brand="fake-brand", swipe_for={})

        def read_swipe(src, k=None):
            got["k"] = k
            raise Stop
        with mock.patch.object(carousel, "ROOT", self.work), \
                mock.patch.object(carousel, "steps_for", lambda change: (["fake-step"], None)), \
                mock.patch.object(carousel, "say", lambda s="": None), \
                mock.patch.object(gpt_drafts, "read_swipe", read_swipe), \
                self.assertRaises(Stop):
            carousel.later_slides(a, "fake-b1", {}, [{"slide": 2, "change": "fake change"}],
                                  {2: self.work / "fake-slide-2.png"}, self.work / "fake-slide-1.png",
                                  self.work, "fake-label")
        return got["k"]

    def via_pull_ig_image(self):
        return pull_ig_image.token()

    GEMINI_SITES = ("via_gemini_image", "via_gemini_text", "via_read_swipe",
                    "via_swipe_has_person", "via_draft_judge", "via_carousel")
    EXITING = ("via_gemini_image", "via_gemini_text")


class Loader(Case):
    def test_loaded_by_path_under_its_own_name(self):
        loader = it_keys._load_loader()
        self.assertEqual(loader.__name__, "shared_keys_loader")
        self.assertIs(sys.modules["shared_keys_loader"], loader)
        self.assertEqual(Path(loader.__file__).resolve(), REPO / "components" / "keys" / "loader.py")
        self.assertNotIn(str(REPO / "components" / "keys"), sys.path)
        self.assertIs(it_keys._load_loader(), loader, "loaded once, then reused")

    def test_never_raises(self):
        loader = it_keys._load_loader()
        with mock.patch.object(loader, "key", side_effect=RuntimeError("boom")):
            self.assertIsNone(it_keys.key("FAKE_SI194_ANY"))
            self.assertIn("FAKE_SI194_ANY", it_keys.missing("FAKE_SI194_ANY"))
        self.assertIsNone(it_keys.key("FAKE_SI194_ANY"))

    def test_env_beats_keychain(self):
        self.helper({"FAKE_SI194_A": "fake-keychain"})
        self.assertEqual(it_keys.key("FAKE_SI194_A"), "fake-keychain")
        os.environ["FAKE_SI194_A"] = "fake-env"
        self.assertEqual(it_keys.key("FAKE_SI194_A"), "fake-env")


class Import(Case):
    def test_three_readers_import_with_no_daemn_folder(self):
        self.assertFalse((self.home / ".daemn").exists())
        code = ("import json, sys\n"
                "sys.path.insert(0, %r)\n"
                "import gpt_drafts, draft_judge, carousel\n"
                "print(json.dumps({'helper': %r in sys.modules,\n"
                "                  'on_path': [p for p in sys.path if '.daemn' in p]}))\n"
                % (str(TOOLS), HELPER))
        r = subprocess.run([sys.executable, "-B", "-c", code], cwd=str(LANE), env=dict(os.environ),
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got, {"helper": False, "on_path": []})

    def test_no_reader_imports_the_helper_or_names_a_key_file(self):
        banned = (HELPER, ".daemn", ".gemini.env", ".apify.env", "keys.env")
        for name in READER_FILES:
            tree = ast.parse((TOOLS / (name + ".py")).read_text())
            docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body \
                        and isinstance(node.body[0], ast.Expr) \
                        and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                    docs.add(id(node.body[0].value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertNotIn(HELPER, [a.name for a in node.names], name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, HELPER, name)
                if isinstance(node, ast.Name):
                    self.assertNotEqual(node.id, HELPER, name)
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and id(node) not in docs:
                    for b in banned:
                        self.assertNotIn(b, node.value, "%s names %s in code" % (name, b))

    def test_every_reader_holds_the_one_it_keys(self):
        for mod in (gpt_drafts, draft_judge, carousel, gemini_image, gemini_text, pull_ig_image):
            with self.subTest(reader=mod.__name__):
                self.assertIs(mod.it_keys, it_keys)
                self.assertEqual(Path(mod.it_keys.__file__).resolve(), TOOLS / "it_keys.py")


class ViaKey(Case):
    def test_every_gemini_site_takes_its_key_from_it_keys(self):
        for site in self.GEMINI_SITES:
            with self.subTest(site=site), \
                    mock.patch.object(it_keys, "key", return_value="fake-via-key") as k:
                self.assertEqual(getattr(self, site)(), "fake-via-key")
                k.assert_called_once_with(GEMINI)

    def test_apify_site_takes_its_key_from_it_keys(self):
        with mock.patch.object(it_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(self.via_pull_ig_image(), "fake-via-key")
            k.assert_called_once_with(APIFY)

    def test_check_asks_it_keys(self):
        with mock.patch.object(it_keys, "key", return_value="fake-via-key") as k:
            self.assertEqual(check.api_key(), (True, GEMINI + " present"))
            k.assert_called_once_with(GEMINI)
        with mock.patch.object(it_keys, "key", return_value=None):
            self.assertEqual(check.api_key(), (False, "missing: " + GEMINI))

    def test_carousel_dry_run_asks_for_no_key(self):
        a = types.SimpleNamespace(dry_run=True, rounds=1, brand="fake-brand", swipe_for={})
        with mock.patch.object(it_keys, "key") as k, \
                mock.patch.object(carousel, "ROOT", self.work):
            self.assertEqual(carousel.later_slides(a, "fake-b1", {}, [], {}, self.work / "s1.png",
                                                   self.work, "fake-label"), [])
            k.assert_not_called()


class Order(Case):
    def assert_gemini_everywhere(self, value):
        for site in self.GEMINI_SITES:
            with self.subTest(site=site):
                self.assertEqual(getattr(self, site)(), value)
        ok, msg = check.api_key()
        self.assertTrue(ok)
        self.assertNotIn("fake-", msg)

    def test_gemini_env_file_then_keychain_then_env(self):
        self.write(".gemini.env", "%s=fake-gemini-file\n" % GEMINI)
        self.assert_gemini_everywhere("fake-gemini-file")
        self.helper({GEMINI: "fake-gemini-keychain"})
        self.assert_gemini_everywhere("fake-gemini-keychain")
        os.environ[GEMINI] = "fake-gemini-env"
        self.assert_gemini_everywhere("fake-gemini-env")

    def test_apify_env_file_still_supplies_the_token(self):
        self.write(".apify.env", "%s=fake-apify-file\n" % APIFY)
        self.assertEqual(self.via_pull_ig_image(), "fake-apify-file")
        self.helper({APIFY: "fake-apify-keychain"})
        self.assertEqual(self.via_pull_ig_image(), "fake-apify-keychain")
        os.environ[APIFY] = "fake-apify-env"
        self.assertEqual(self.via_pull_ig_image(), "fake-apify-env")


class Mini(Case):
    def setUp(self):
        super().setUp()
        self.write(MARKER, "")
        self.helper({GEMINI: "fake-gemini-keychain", APIFY: "fake-apify-keychain"})
        self.write(".gemini.env", "%s=fake-gemini-file\n" % GEMINI)
        self.write(".apify.env", "%s=fake-apify-file\n" % APIFY)
        self.write(".daemn/keys.env", "%s=fake-gemini-vault\n" % GEMINI)

    def test_marker_takes_env_only(self):
        os.environ[GEMINI] = "fake-gemini-env"
        os.environ[APIFY] = "fake-apify-env"
        with self.opens() as seen:
            for site in self.GEMINI_SITES:
                with self.subTest(site=site):
                    self.assertEqual(getattr(self, site)(), "fake-gemini-env")
            self.assertEqual(self.via_pull_ig_image(), "fake-apify-env")
            self.assertEqual(check.api_key(), (True, GEMINI + " present"))
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")

    def test_marker_and_no_env_reads_nothing_and_finds_nothing(self):
        out, err = io.StringIO(), io.StringIO()
        with self.opens() as seen, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            for site in self.GEMINI_SITES:
                with self.subTest(site=site):
                    if site in self.EXITING:
                        with self.assertRaises(SystemExit) as cm:
                            getattr(self, site)()
                        msg = str(cm.exception.code)
                        self.assertIn(GEMINI, msg)
                        self.assertIn("old locations skipped", msg)
                        self.assertNotIn("fake-", msg)
                    else:
                        self.assertIsNone(getattr(self, site)())
            with self.assertRaises(SystemExit) as cm:
                self.via_pull_ig_image()
            self.assertIn(APIFY, str(cm.exception.code))
            self.assertIn("old locations skipped", str(cm.exception.code))
            self.assertNotIn("fake-", str(cm.exception.code))
            self.assertEqual(check.api_key(), (False, "missing: " + GEMINI))
        self.assertEqual(self.key_files_opened(seen), [])
        self.assertNotIn(HELPER, sys.modules, "the Keychain helper was imported")
        self.assertNotIn("fake-", out.getvalue() + err.getvalue())


class Check(Case):
    def setUp(self):
        super().setUp()
        self.write(".gemini.env", "%s=fake-gemini-file\n" % GEMINI)
        self.write(".daemn/keys.env", "%s=fake-gemini-vault\n" % GEMINI)

    def test_reports_without_opening_the_key_files(self):
        for value, want in (("fake-present", (True, GEMINI + " present")),
                            (None, (False, "missing: " + GEMINI))):
            with self.subTest(value=value), self.opens() as seen, \
                    mock.patch.object(it_keys, "key", return_value=value):
                got = check.api_key()
                self.assertEqual(got, want)
                self.assertNotIn("fake-", got[1])
            self.assertEqual(self.key_files_opened(seen), [])

    def test_env_present_through_the_real_loader_opens_nothing(self):
        os.environ[GEMINI] = "fake-gemini-env"
        with self.opens() as seen:
            got = check.api_key()
        self.assertEqual(got, (True, GEMINI + " present"))
        self.assertNotIn("fake-", got[1])
        self.assertEqual(self.key_files_opened(seen), [])


class Missing(Case):
    def test_script_readers_exit_naming_the_key_and_where_looked_never_a_value(self):
        self.helper({"FAKE_SI194_OTHER": "fake-secret-keychain"})
        os.environ["FAKE_SI194_OTHER"] = "fake-secret-env"
        out, err = io.StringIO(), io.StringIO()
        for site, name, place in (("via_gemini_image", GEMINI, "~/.gemini.env"),
                                  ("via_gemini_text", GEMINI, "~/.gemini.env"),
                                  ("via_pull_ig_image", APIFY, "~/.apify.env")):
            with self.subTest(site=site), contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                getattr(self, site)()
            msg = str(cm.exception.code)
            self.assertIn(name, msg)
            self.assertIn("looked in: environment", msg)
            self.assertIn("~/.daemn/daemn_keys.py", msg)
            self.assertIn(place, msg)
            self.assertNotIn("fake-", msg)
            self.assertNotIn("None", msg)
        self.assertNotIn("fake-", out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
