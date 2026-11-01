#!/usr/bin/env python3
"""LD-16 (email design by API): the design step reads `drive:` pictures and
lists the brand's photos through the Drive API when the mount does not read —
proven offline.

    python3 tools/email-production/test_look_drive_reach.py

The mount is patched in every test (a temp folder or None). The Drive is a
fake engine and a fake service under gdrive-creator's REAL reach.list_tree,
or a fake reach for Look.path(); no key, no network, no Google package. PIL
is stood in only when this interpreter has none (design/engine.py imports it;
nothing here draws). Stdlib only, 3.9.

  a  Look.path("drive:…") with no mount -> the API file, by its
     "Shared Assets/…" label
  b  with a mount that reads -> the mount path, and no API call
  c  NoDrive or SystemExit with no mount -> today's FileNotFoundError text;
     with a mount -> today's mount path
  d  photos_of with no mount (or one that does not list) -> the same refs, in
     the same order, from the Drive listing by name; never_names honoured;
     get_media never called
  e  photos_of with no key or an API error -> today's "not mounted" line
"""
import contextlib
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE / "design"))              # APPEND — never insert at 0
try:
    import PIL                                     # noqa: F401
except ImportError:
    PIL = types.ModuleType("PIL")
    for _n in ("Image", "ImageDraw", "ImageFilter"):
        setattr(PIL, _n, types.ModuleType("PIL." + _n))
        sys.modules["PIL." + _n] = getattr(PIL, _n)
    sys.modules["PIL"] = PIL
import look as L                                   # noqa: E402
import line as LI                                  # noqa: E402
import drive_index                                 # noqa: E402  (brandpath, put on the path by look)

R = L.reach()                                      # gdrive-creator's real reach

BRAND = "zz-brand"
FOLDER = "application/vnd.google-apps.folder"
# products/<product>/<kind>/... : what the brand's tree holds, on the mount and on the Drive alike
TREE = ["prod-b/lifestyle/b1.jpg", "prod-b/lifestyle/sub/b2.PNG", "prod-b/3d/render.png",
        "prod-b/packshot/Rival-shot.jpg", "prod-b/packshot/p1.webp", "prod-b/packshot/notes.txt",
        "prod-a/ugc/a1.jpeg", "prod-a/texture/t.jpg", "loose.jpg"]
WANT = ["prod-a/texture/t.jpg", "prod-a/ugc/a1.jpeg",
        "prod-b/lifestyle/b1.jpg", "prod-b/lifestyle/sub/b2.PNG", "prod-b/packshot/p1.webp"]
WANT_REFS = ["drive:brands/%s/products/%s" % (BRAND, w) for w in WANT]
NOT_MOUNTED = "(the shared drive is not mounted: no brand photos offered)"


class Exploding(object):
    def __getattr__(self, name):
        raise AssertionError("the Drive API was reached: %s" % name)


class FakeDrive(object):
    """A shared-drive tree by id: the engine half (folder_by_path, list_files,
    get_media) and the service half reach's _subfolders lists through."""

    def __init__(self, files):
        self.nodes = {"d-sa": ("Shared Assets", None, True)}
        self.media = []
        for rel in files:
            cur = self._dir("d-sa", "brands", BRAND, "products")
            bits = rel.split("/")
            cur = self._dir(cur, *bits[:-1])
            self.nodes["f%d" % len(self.nodes)] = (bits[-1], cur, False)

    def _dir(self, cur, *names):
        for name in names:
            hit = [i for i, (n, p, d) in self.nodes.items() if p == cur and n == name and d]
            if hit:
                cur = hit[0]
            else:
                nid = "d%d" % len(self.nodes)
                self.nodes[nid] = (name, cur, True)
                cur = nid
        return cur

    def kids(self, parent, folders):
        return [{"id": i, "name": n, "mimeType": FOLDER if d else "image/jpeg"}
                for i, (n, p, d) in self.nodes.items() if p == parent and d == folders]

    # the engine
    FOLDER_MIME = FOLDER

    def service(self):
        raise AssertionError("no service may be built: the fake svc is passed")

    def folder_by_path(self, label, svc=None):
        bits = label.split("/")
        if bits[0] != "Shared Assets":
            return None
        cur = "d-sa"
        for name in bits[1:]:
            hit = [k["id"] for k in self.kids(cur, True) if k["name"] == name]
            if not hit:
                return None
            cur = hit[0]
        return cur

    def list_files(self, folder_id, svc=None):
        return self.kids(folder_id, False)

    def get_media(self, file_id, dest_path, svc=None):
        self.media.append(file_id)
        raise AssertionError("a listing downloaded %s" % file_id)

    # the service
    def files(self):
        return self

    def list(self, q="", **kw):
        parent = q.split("'")[1]
        self.got = {"files": [{"id": k["id"], "name": k["name"]} for k in self.kids(parent, True)]}
        return self

    def execute(self):
        return self.got


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(os.path.realpath(t.name))
        self.mount_at(None)
        self.lk = L.Look(BRAND, {"check": {"never_names": ["rival"]}, "products": {"hero": "drive:fonts/x.ttf"}})

    def patch(self, target, name, value):
        p = mock.patch.object(target, name, value)
        p.start()
        self.addCleanup(p.stop)

    def mount_at(self, where):
        self.patch(drive_index, "mount", lambda: where)

    def a_mount(self, files=()):
        sa = self.tmp / "mnt" / "Shared Assets"
        sa.mkdir(parents=True)
        for rel in files:
            f = sa / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"m")
        self.mount_at(sa)
        return sa

    def reach_is(self, fake):
        self.patch(L, "reach", lambda: fake)

    def locked(self, p):
        """p no longer lists or opens for this user (as the mount under launchd)."""
        if os.geteuid() == 0:
            self.skipTest("root reads through chmod 000")
        mode = p.stat().st_mode
        p.chmod(0)
        self.addCleanup(p.chmod, mode)


class TestLookPath(Base):
    def api(self, local, raises=None):
        asked = []

        def readable(label):
            asked.append(label)
            if raises is not None:
                raise raises
            return local
        self.reach_is(types.SimpleNamespace(readable=readable, NoDrive=R.NoDrive))
        return asked

    def test_no_mount_is_the_api_file(self):
        local = self.tmp / "cache" / "fonts" / "x.ttf"
        asked = self.api(local)
        self.assertEqual(self.lk.path("drive:fonts/x.ttf"), local)
        self.assertEqual(asked, ["Shared Assets/fonts/x.ttf"])           # the label, never a stand-in path
        self.assertEqual(self.lk.path("product:hero"), local)            # a product picture goes the same way

    def test_a_reading_mount_is_the_mount_path_and_no_api_call(self):
        sa = self.a_mount(["fonts/x.ttf"])
        self.reach_is(Exploding())
        self.assertEqual(self.lk.path("drive:fonts/x.ttf"), sa / "fonts" / "x.ttf")

    def test_a_mount_that_does_not_read_goes_to_the_api(self):
        sa = self.a_mount(["fonts/x.ttf"])
        self.locked(sa / "fonts" / "x.ttf")
        local = self.tmp / "cache" / "x.ttf"
        asked = self.api(local)
        self.assertEqual(self.lk.path("drive:fonts/x.ttf"), local)
        self.assertEqual(asked, ["Shared Assets/fonts/x.ttf"])

    def test_nodrive_or_no_key_with_no_mount_is_todays_error(self):
        for exc in (R.NoDrive("not on the Drive"), SystemExit("no GDRIVE_SA_KEY")):
            self.api(None, raises=exc)
            with self.assertRaises(FileNotFoundError) as c:
                self.lk.path("drive:fonts/x.ttf")
            self.assertEqual(str(c.exception),
                             "drive:fonts/x.ttf: the Shared Assets drive is not mounted on this computer")

    def test_with_a_mount_and_nowhere_else_it_is_todays_mount_path(self):
        sa = self.a_mount()
        self.api(None, raises=R.NoDrive("not on the Drive"))
        self.assertEqual(self.lk.path("drive:fonts/missing.ttf"), sa / "fonts" / "missing.ttf")


class TestPhotosOf(Base):
    def drive(self):
        fake = FakeDrive(TREE)
        self.reach_is(types.SimpleNamespace(
            list_tree=lambda parts, **kw: R.list_tree(parts, svc=fake, find_engine=lambda: fake, **kw),
            NoDrive=R.NoDrive))
        return fake

    def test_no_mount_lists_the_same_refs_by_name_and_downloads_nothing(self):
        fake = self.drive()
        before = sorted(self.tmp.rglob("*"))
        refs, txt = LI.photos_of(self.lk)
        self.assertEqual(refs, set(WANT_REFS))
        self.assertEqual(txt.split("\n"), WANT_REFS)                    # same order as the mount's
        self.assertFalse(any("rival" in r.lower() for r in refs))       # never_names honoured
        self.assertEqual(fake.media, [])                                 # get_media never called
        self.assertEqual(sorted(self.tmp.rglob("*")), before)           # nothing written

    def test_the_mount_gives_the_same_refs_and_never_calls_the_api(self):
        self.a_mount("brands/%s/products/%s" % (BRAND, rel) for rel in TREE)
        self.reach_is(Exploding())
        refs, txt = LI.photos_of(self.lk)
        self.assertEqual(refs, set(WANT_REFS))
        self.assertEqual(txt.split("\n"), WANT_REFS)

    def test_a_mount_that_does_not_list_lists_by_name(self):
        sa = self.a_mount("brands/%s/products/%s" % (BRAND, rel) for rel in TREE)
        self.locked(sa / "brands" / BRAND / "products")
        fake = self.drive()
        refs, txt = LI.photos_of(self.lk)
        self.assertEqual(txt.split("\n"), WANT_REFS)
        self.assertEqual(fake.media, [])

    def test_the_limit_is_the_same(self):
        self.drive()
        refs, txt = LI.photos_of(self.lk, limit=2)
        self.assertEqual(refs, set(WANT_REFS))
        self.assertEqual(txt.split("\n"), WANT_REFS[:2])

    def test_no_key_or_an_api_error_is_todays_line(self):
        for exc in (SystemExit("no GDRIVE_SA_KEY"), RuntimeError("HttpError 500")):
            def list_tree(parts, **kw):
                raise exc
            self.reach_is(types.SimpleNamespace(list_tree=list_tree, NoDrive=R.NoDrive))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(LI.photos_of(self.lk), (set(), NOT_MOUNTED))
            self.assertIn(type(exc).__name__, err.getvalue())

    def test_no_products_folder_on_the_drive_is_none_offered(self):
        self.reach_is(types.SimpleNamespace(list_tree=lambda parts, **kw: None, NoDrive=R.NoDrive))
        self.assertEqual(LI.photos_of(self.lk), (set(), "(none on the drive)"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
