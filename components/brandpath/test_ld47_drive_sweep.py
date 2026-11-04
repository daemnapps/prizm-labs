#!/usr/bin/env python3
"""LD-47 (Drive sweep)'s declared test — every swept site finds the Drive
app's folders through this component's finder (drive_index.accounts() /
mount()), so LD-26 (mount switch) holds at each one.

    python3 components/brandpath/test_ld47_drive_sweep.py

Offline: no network, no real Drive, nothing written outside a temp folder.

    (1) static — none of the eleven site files still names the Drive app's
        folder (`Library/CloudStorage`, "CloudStorage") or globs
        `GoogleDrive-*` itself, outside a comment. A name filter over
        accounts()'s answer is allowed: it is the same filter, kept.
    (2) DRIVE_MOUNT=off — Path.home() is a temp home holding a real
        Library/CloudStorage/GoogleDrive-… account with Shared Assets in it;
        each site's finder still answers empty/None (or its own "no mount"
        failure) and no stat, listing, glob or open reaches that folder.
    (3) unset (a person's session) — the same finder answers the fake
        account exactly as before, so (2) is not a vacuous pass.
"""
import ast
import contextlib
import importlib.util
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
COMPONENTS = HERE.parent
ACCOUNT = "GoogleDrive-tester@company.com"

SITES = {
    "casting": "casting/casting/paths.py",
    "copywriter": "copywriter/library/build_library.py",
    "email": "email-production/section_email.py",
    "asks": "funnel-tracking/machine/asks_runner.py",
    "inventory": "image-production/machine_inventory.py",
    "static": "image-production/static/tools/paths.py",
    "naming": "naming/delivery_rule.py",
    "voiceprint": "research-gatherer/research_gatherer/voiceprint.py",
    "handoff": "video-edit/machine/handoff_run.py",
    "chain": "video-teardown/machine/chain.py",
    "storage": "video-teardown/tools/storage.py",
}


def site(key):
    return COMPONENTS / SITES[key]


def load(key, drop_main=False):
    """A site file as a fresh module under its own name. `drop_main` leaves
    out a bare top-level `main()` call (machine_inventory.py runs on import)."""
    path = site(key)
    name = "_ld47_" + key
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    if drop_main:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        tree.body = [n for n in tree.body
                     if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                             and getattr(n.value.func, "id", None) == "main")]
        exec(compile(tree, str(path), "exec"), mod.__dict__)
        return mod
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class Static(unittest.TestCase):
    """(1) No site names the Drive app's folder or globs its accounts itself."""

    def _module_strings(self, tree):
        """Module-level NAME = "string" constants, for a glob fed by a name."""
        out = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                    and isinstance(n.value.value, str):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        out[t.id] = n.value.value
        return out

    def test_no_site_names_the_drive_app_folder(self):
        for key in SITES:
            with self.subTest(site=SITES[key]):
                tree = ast.parse(site(key).read_text(encoding="utf-8"))
                said = [n.value for n in ast.walk(tree)
                        if isinstance(n, ast.Constant) and isinstance(n.value, str)
                        and "CloudStorage" in n.value]
                self.assertEqual(said, [], "%s still names the Drive app's folder" % SITES[key])

    def test_no_site_globs_drive_accounts_itself(self):
        for key in SITES:
            with self.subTest(site=SITES[key]):
                tree = ast.parse(site(key).read_text(encoding="utf-8"))
                consts = self._module_strings(tree)
                hits = []
                for n in ast.walk(tree):
                    if not isinstance(n, ast.Call):
                        continue
                    f = n.func
                    fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                    if fname not in ("glob", "rglob", "iglob"):
                        continue
                    for a in n.args:
                        words = [c.value for c in ast.walk(a)
                                 if isinstance(c, ast.Constant) and isinstance(c.value, str)]
                        words += [consts.get(c.id, "") for c in ast.walk(a) if isinstance(c, ast.Name)]
                        if any("GoogleDrive-" in w for w in words):
                            hits.append(n.lineno)
                self.assertEqual(hits, [], "%s globs GoogleDrive-* itself at line(s) %s"
                                 % (SITES[key], hits))


class Switch(unittest.TestCase):
    """(2) DRIVE_MOUNT=off: empty/None, nothing under the Drive app's folder touched.
    (3) unset: the fake account is found as today."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = pathlib.Path(cls.tmp.name) / "home"
        cls.cloud = cls.home / "Library" / "CloudStorage"
        cls.acct = cls.cloud / ACCOUNT
        cls.sa = cls.acct / "Shared drives" / "Shared Assets"
        (cls.sa / "brands" / "b" / "products").mkdir(parents=True)
        (cls.sa / "handoffs" / "x").mkdir(parents=True)
        (cls.sa / "lab" / "owner").mkdir(parents=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        p = mock.patch.object(pathlib.Path, "home", return_value=self.home)
        p.start()
        self.addCleanup(p.stop)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        for k in ("DRIVE_MOUNT", "DRIVE_ACCOUNT", "GDRIVE_SA_KEY", "DRIVE_ROUTE"):
            os.environ.pop(k, None)

    def off(self):
        os.environ["DRIVE_MOUNT"] = "off"

    @contextlib.contextmanager
    def no_touch(self):
        """Every stat, listing, glob or open of a path under the fake
        Library/CloudStorage fails loudly; anything else runs as usual."""
        cloud = str(self.cloud)

        def guard(name, orig):
            def f(*a, **k):
                target = a[0] if a else None
                if target is not None and str(target).startswith(cloud):
                    raise AssertionError("LD-47 (Drive sweep): %s touched %s" % (name, target))
                return orig(*a, **k)
            return f

        with contextlib.ExitStack() as stack:
            for n in ("stat", "lstat", "is_dir", "is_file", "exists", "glob", "rglob",
                      "iterdir", "open"):
                stack.enter_context(mock.patch.object(
                    pathlib.Path, n, guard("Path." + n, getattr(pathlib.Path, n))))
            for n in ("stat", "lstat", "scandir", "listdir"):
                stack.enter_context(mock.patch.object(os, n, guard("os." + n, getattr(os, n))))
            yield

    def test_the_guard_fires(self):
        with self.no_touch():
            with self.assertRaises(AssertionError):
                self.sa.is_dir()
        self.assertTrue(self.sa.is_dir())

    # casting/casting/paths.py — drive_runs()
    def test_casting(self):
        m = load("casting")
        self.off()
        with self.no_touch():
            with self.assertRaises(m.MountError):
                m.drive_runs()
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.drive_runs(), self.sa / "runs")

    # copywriter/library/build_library.py — _drive_root(), DRIVE
    def test_copywriter(self):
        self.off()
        with self.no_touch():
            m = load("copywriter")
            self.assertIsNone(m.DRIVE)
            self.assertIsNone(m._drive_root())
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m._drive_root(), self.sa)
        os.environ["DRIVE_ACCOUNT"] = "someone-else@example.org"
        self.assertIsNone(m._drive_root())
        os.environ["DRIVE_ACCOUNT"] = ACCOUNT[len("GoogleDrive-"):]
        self.assertEqual(m._drive_root(), self.sa)

    # email-production/section_email.py — drive_products(), product_photo()
    def test_email(self):
        self.off()
        with self.no_touch():
            m = load("email")
            self.assertIsNone(m.drive_products("b"))
            self.assertIsNone(m.product_photo("b", "p"))
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.drive_products("b"), self.sa / "brands" / "b" / "products")

    # funnel-tracking/machine/asks_runner.py — the --add-dir of the Drive folder
    def test_asks(self):
        self.off()
        with self.no_touch():
            m = load("asks")
            self.assertEqual(m.drive_dirs(), [])
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.drive_dirs(), ["--add-dir", str(self.sa)])

    # image-production/machine_inventory.py — mounts()
    def test_inventory(self):
        self.off()
        with self.no_touch():
            m = load("inventory", drop_main=True)
            self.assertEqual(m.mounts(), [])
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.mounts(), [(self.acct, "company")])
        self.assertEqual(m.mounts("other"), [])

    # image-production/static/tools/paths.py — drive(), DRIVE
    def test_static(self):
        self.off()
        with self.no_touch():
            m = load("static")
            with self.assertRaises(m.MountError):
                m.drive()
            self.assertFalse(str(m.DRIVE).startswith(str(self.cloud)), m.DRIVE)
            self.assertFalse(m._drive_or_absent().is_dir())
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.drive(), self.sa / "lab" / "owner")

    # naming/delivery_rule.py — resolve()
    def test_naming(self):
        self.off()
        with self.no_touch():
            m = load("naming")
            self.assertEqual(m.resolve("Shared Assets/handoffs/x"),
                             pathlib.Path("Shared Assets/handoffs/x"))
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.resolve("Shared Assets/handoffs/x"), self.sa / "handoffs" / "x")

    # research-gatherer/research_gatherer/voiceprint.py — _drive_mount(), DRIVE_ROOT
    def test_voiceprint(self):
        self.off()
        with self.no_touch():
            m = load("voiceprint")
            self.assertIsNone(m._drive_mount())
            self.assertIsNone(m.DRIVE_ROOT)
            self.assertEqual(m.selected_posts("b"), {})
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m._drive_mount(), self.acct)

    # video-edit/machine/handoff_run.py — drive_shared()
    def test_handoff(self):
        self.off()
        with self.no_touch():
            m = load("handoff")
            self.assertIsNone(m.drive_shared())
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.drive_shared(), self.sa)

    # video-teardown/machine/chain.py — drive_mounts(), drive_root()
    def test_chain(self):
        self.off()
        with self.no_touch():
            m = load("chain")
            self.assertEqual(m.drive_mounts(), [])
            with self.assertRaises(m.MountError):
                m.drive_root()
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.drive_mounts(), [self.acct])
        self.assertEqual(m.drive_root(), self.sa)

    # video-teardown/tools/storage.py — drive_root()
    def test_storage(self):
        self.off()
        with self.no_touch():
            m = load("storage")
            self.assertIsNone(m.drive_root())
        os.environ.pop("DRIVE_MOUNT")
        self.assertEqual(m.drive_root(), self.sa)


if __name__ == "__main__":
    unittest.main(verbosity=2)
