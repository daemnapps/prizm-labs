#!/usr/bin/env python3
"""LD-14 (shared Drive reach): one reach — route by key, get, put, fetch a
folder, make any Drive path readable — proven offline.

    python3 components/gdrive-creator/tests/test_reach.py

The REAL engine runs against a fake Drive service (the engine's `svc` seam);
only the two Google media classes are stood in (`engine._google`), so no
Google package, no key and no network are needed. The mount is a temp folder
or None in every test — the real one is never touched. Stdlib only, 3.9.

  a  route: a key means the API even with a mount; no key and a mount means
     the mount; neither is a named NoDrive; an empty key is no key
  b  get: the mount file itself; through the API by id; missing is None
  c  put: folders made if missing, same name updated in place, and NOTHING
     is ever deleted, trashed, moved or renamed — on the calls and the source
  d  fetch_folder: flat (subfolders made, left empty), recursive, the
     max_bytes stop said out loud, a missing folder is None
  e  readable: a mount path that lists is itself; one that raises
     PermissionError is an API copy with the same names; a label with no
     mount is an API copy; a local path is itself
  f  list_tree (LD-16 (email design by API)): every file's relative path and
     id, recursive, by name — get_media never called, nothing written; the
     max_items stop said out loud; a missing folder is None
"""
import contextlib
import io
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.append(str(COMPONENT))                    # APPEND — never insert at 0

from gdrive_creator import engine as E, reach as R   # noqa: E402

FOLDER = E.FOLDER_MIME
NAME_RE = re.compile(r"name = '((?:[^'\\]|\\.)*)'")
ALLOWED = {"drives.list", "files.list", "files.create", "files.update",
           "files.get_media"}


class Req(object):
    def __init__(self, result=None, data=None):
        self.result, self.data = result, data

    def execute(self):
        return self.result


class FakeDrive(object):
    """A shared-drive tree by id. Every call is recorded; any method a reach
    must never use (delete, emptyTrash, copy, …) is recorded and FAILS."""

    def __init__(self, page=2):
        self.nodes = {"d-sa": {"id": "d-sa", "name": "Shared Assets",
                               "mimeType": FOLDER, "parent": None}}
        self.calls, self.page, self.n = [], page, 0

    def add(self, parent, name, data=None):
        self.n += 1
        nid = "n%d" % self.n
        self.nodes[nid] = {"id": nid, "name": name, "parent": parent,
                           "mimeType": FOLDER if data is None else "application/octet-stream",
                           "data": data}
        return nid

    def path(self, *names):
        cur = "d-sa"
        for name in names:
            cur = next(n["id"] for n in self.nodes.values()
                       if n["parent"] == cur and n["name"] == name)
        return cur

    def names(self):
        return sorted(c for c, _ in self.calls)

    def drives(self):
        d = self

        class Drives(object):
            def list(self, **kw):
                d.calls.append(("drives.list", kw))
                return Req({"drives": [{"id": "d-other", "name": "Other"},
                                       {"id": "d-sa", "name": "Shared Assets"}]})
        return Drives()

    def files(self):
        d = self

        class Files(object):
            def list(self, **kw):
                d.calls.append(("files.list", kw))
                q = kw["q"]
                parent = re.search(r"'([^']+)' in parents", q).group(1)
                rows = [n for n in d.nodes.values() if n["parent"] == parent]
                m = NAME_RE.search(q)
                if m:
                    want = m.group(1).replace("\\'", "'").replace("\\\\", "\\")
                    rows = [r for r in rows if r["name"] == want]
                if f"mimeType = '{FOLDER}'" in q:
                    rows = [r for r in rows if r["mimeType"] == FOLDER]
                if f"mimeType != '{FOLDER}'" in q:
                    rows = [r for r in rows if r["mimeType"] != FOLDER]
                size = min(kw.get("pageSize") or d.page, d.page)
                start = int(kw.get("pageToken") or 0)
                out = {"files": [{"id": r["id"], "name": r["name"],
                                  "mimeType": r["mimeType"]}
                                 for r in rows[start:start + size]]}
                if start + size < len(rows):
                    out["nextPageToken"] = str(start + size)
                return Req(out)

            def create(self, **kw):
                d.calls.append(("files.create", kw))
                body = kw["body"]
                media = kw.get("media_body")
                nid = d.add(body["parents"][0], body["name"],
                            None if media is None else media.data)
                if media is None:
                    d.nodes[nid]["mimeType"] = body.get("mimeType", FOLDER)
                return Req({"id": nid})

            def update(self, **kw):
                d.calls.append(("files.update", kw))
                d.nodes[kw["fileId"]]["data"] = kw["media_body"].data
                return Req({"id": kw["fileId"]})

            def get_media(self, **kw):
                d.calls.append(("files.get_media", kw))
                return Req(data=d.nodes[kw["fileId"]]["data"])

            def __getattr__(self, name):
                d.calls.append(("files." + name, {}))
                raise AssertionError("a reach called files().%s" % name)
        return Files()


class MediaFileUpload(object):
    def __init__(self, path, mimetype=None, resumable=False):
        self.data = Path(path).read_bytes()


class MediaIoBaseDownload(object):
    def __init__(self, fh, req):
        self.fh, self.req = fh, req

    def next_chunk(self, num_retries=0):
        self.fh.write(self.req.data)
        return None, True


FAKE_GOOGLE = types.SimpleNamespace(MediaFileUpload=MediaFileUpload,
                                    MediaIoBaseDownload=MediaIoBaseDownload)


class Exploding(object):
    def __getattr__(self, name):
        raise AssertionError("the API was reached: %s" % name)


class Base(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(R.KEY_ENV, None)
        os.environ["KEYS_NO_FALLBACK"] = "1"        # step 1.6: this machine's real key file never counts in a test
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(os.path.realpath(t.name))
        self.patch(E, "_google", lambda dotted: FAKE_GOOGLE)
        self.patch(tempfile, "tempdir", str(self.tmp / "tmp"))
        (self.tmp / "tmp").mkdir()
        c = mock.patch.dict(R._READABLE, clear=True)
        c.start()
        self.addCleanup(c.stop)
        self.mount_at(None)
        self.svc = FakeDrive()

    def patch(self, target, name, value):
        p = mock.patch.object(target, name, value)
        p.start()
        self.addCleanup(p.stop)

    def mount_at(self, where):
        self.patch(R, "mount", lambda: where)

    def a_mount(self):
        sa = self.tmp / "mnt" / "Shared Assets"
        sa.mkdir(parents=True)
        self.mount_at(sa)
        return sa

    def photos(self):
        """Shared Assets/swipe/brand-x/photos: three files, a subfolder with
        one file and a sub-subfolder with one more."""
        s = self.svc
        ph = s.add(s.add(s.add("d-sa", "swipe"), "brand-x"), "photos")
        s.add(ph, "02.png", b"two-two")
        s.add(ph, "01.jpg", b"one")
        s.add(ph, "03.jpg", b"three-three")
        sub = s.add(ph, "nested")
        s.add(sub, "04.jpg", b"four")
        s.add(s.add(sub, "deeper"), "05.jpg", b"five")
        return ["swipe", "brand-x", "photos"]

    def no_harm(self):
        """Nothing deleted, trashed, moved or renamed on the fake Drive."""
        for c, kw in self.svc.calls:
            self.assertIn(c, ALLOWED, c)
            if c == "files.update":
                for k in ("addParents", "removeParents", "body"):
                    self.assertNotIn(k, kw, "update carried %s" % k)


class TestRoute(Base):
    def test_key_means_api_even_with_a_mount(self):
        self.a_mount()
        os.environ[R.KEY_ENV] = "x"
        self.assertEqual(R.route(), "api")

    def test_no_key_with_a_mount_is_the_mount(self):
        self.a_mount()
        self.assertEqual(R.route(), "mount")

    def test_neither_is_a_named_refusal(self):
        with self.assertRaises(R.NoDrive) as c:
            R.route()
        self.assertIn("GDRIVE_SA_KEY", str(c.exception))
        self.assertIn("mount", str(c.exception))

    def test_an_empty_key_is_no_key(self):
        os.environ[R.KEY_ENV] = ""
        with self.assertRaises(R.NoDrive):
            R.route()

    def test_a_shim_mount_finder_is_used(self):
        self.assertEqual(R.route(find_mount=lambda: self.tmp), "mount")

    # LD-47 (Drive sweep) step 1.6: route() asks the same lookup sa_key() uses — env, host lookup,
    # else the one key loader — so a key that is only in a person's key file counts as present.
    def key_file(self, line):
        home = self.tmp / "home"
        home.mkdir()
        (home / ".company-keys.env").write_text(line + "\n")
        os.environ["HOME"] = str(home)
        os.environ.pop("KEYS_NO_FALLBACK", None)
        os.environ["GDRIVE_KEY_FILE_IN_TESTS"] = "1"     # opt in past the engine's test guard
        return home

    def test_the_test_guard_hides_a_key_file_unless_a_test_opts_in(self):
        self.key_file(R.KEY_ENV + "=from-the-file")
        self.a_mount()
        del os.environ["GDRIVE_KEY_FILE_IN_TESTS"]
        self.assertEqual(R.route(), "mount")         # a forgotten stub never reaches the real Drive
        os.environ["GDRIVE_KEY_FILE_IN_TESTS"] = "1"
        self.assertEqual(R.route(), "api")

    def test_no_key_anywhere_is_the_mount(self):
        self.key_file("OTHER_KEY=1")
        self.a_mount()
        self.assertEqual(R.route(), "mount")

    def test_a_key_only_in_the_key_file_is_api(self):
        self.key_file(R.KEY_ENV + "=from-the-file")
        self.a_mount()
        self.assertNotIn(R.KEY_ENV, os.environ)
        self.assertEqual(R.route(), "api")

    def test_a_key_in_the_environment_is_api(self):
        self.key_file("OTHER_KEY=1")
        self.a_mount()
        os.environ[R.KEY_ENV] = "x"
        self.assertEqual(R.route(), "api")

    def test_the_key_value_never_reaches_a_refusal(self):
        self.key_file(R.KEY_ENV + "=sekrit-value-123")
        self.assertTrue(E.has_key(R.KEY_ENV))
        os.environ["KEYS_NO_FALLBACK"] = "1"
        with self.assertRaises(R.NoDrive) as c:
            R.route()
        self.assertNotIn("sekrit-value-123", str(c.exception))


class TestGet(Base):
    def test_on_the_mount_it_is_the_file_itself(self):
        sa = self.a_mount()
        f = sa / "a" / "hero.png"
        f.parent.mkdir()
        f.write_bytes(b"on-the-mount")
        dest = self.tmp / "dest"
        self.assertEqual(R.get(["a"], "hero.png", dest, svc=Exploding(),
                               find_engine=Exploding), f)
        self.assertFalse(dest.exists())
        self.assertIsNone(R.get(["a"], "nope.png", dest, svc=Exploding()))

    def test_through_the_api_it_reads_by_id_and_makes_nothing(self):
        os.environ[R.KEY_ENV] = "x"
        self.svc.add(self.svc.add(self.svc.add("d-sa", "a"), "b"), "hero.png", b"bytes")
        dest = self.tmp / "dest"
        got = R.get(["a", "b"], "hero.png", dest, svc=self.svc)
        self.assertEqual(got, dest / "hero.png")
        self.assertEqual(got.read_bytes(), b"bytes")
        self.assertNotIn("files.create", self.svc.names())
        self.assertIsNone(R.get(["a", "x"], "hero.png", dest, svc=self.svc))
        self.assertIsNone(R.get(["a", "b"], "nope.png", dest, svc=self.svc))
        self.no_harm()


class TestPut(Base):
    def files(self, data, *names):
        src = self.tmp / "out"
        src.mkdir(exist_ok=True)
        out = []
        for n in names:
            (src / n).write_bytes(data)
            out.append(src / n)
        return out

    def test_api_makes_folders_and_updates_in_place_and_harms_nothing(self):
        os.environ[R.KEY_ENV] = "x"
        runs = self.svc.add("d-sa", "runs")
        keep = self.svc.add(runs, "keep.png", b"keep")
        how, placed, note = R.put(self.files(b"v1", "a.png", "b.png"),
                                  ["runs", "zz-tool", "lbl"], svc=self.svc)
        self.assertEqual((how, note), ("api", None))
        self.assertEqual(placed, ["Shared Assets/runs/zz-tool/lbl/a.png",
                                  "Shared Assets/runs/zz-tool/lbl/b.png"])
        leaf = self.svc.path("runs", "zz-tool", "lbl")
        a_id = self.svc.path("runs", "zz-tool", "lbl", "a.png")
        self.assertEqual(self.svc.nodes[a_id]["data"], b"v1")

        before = len(self.svc.nodes)
        how, placed, note = R.put(self.files(b"v2", "a.png"),
                                  ["runs", "zz-tool", "lbl"], svc=self.svc)
        self.assertEqual((how, note), ("api", None))
        self.assertEqual(len(self.svc.nodes), before)            # no new file, no new folder
        self.assertEqual(self.svc.path("runs", "zz-tool", "lbl", "a.png"), a_id)
        self.assertEqual(self.svc.nodes[a_id]["data"], b"v2")    # same id, new bytes
        self.assertEqual(self.svc.nodes[a_id]["parent"], leaf)
        self.assertEqual(self.svc.nodes[keep]["data"], b"keep")
        self.assertIn("files.update", self.svc.names())
        self.no_harm()

    def test_mount_copies_over_the_same_name_and_keeps_the_rest(self):
        sa = self.a_mount()
        dest = sa / "runs" / "lbl"
        dest.mkdir(parents=True)
        (dest / "keep.png").write_bytes(b"keep")
        (dest / "a.png").write_bytes(b"old")
        how, placed, note = R.put(self.files(b"new", "a.png"), ["runs", "lbl"],
                                  svc=Exploding(), find_engine=Exploding)
        self.assertEqual((how, placed, note), ("mount", [str(dest / "a.png")], None))
        self.assertEqual((dest / "a.png").read_bytes(), b"new")
        self.assertEqual((dest / "keep.png").read_bytes(), b"keep")

    def test_no_route_is_a_named_skip(self):
        how, placed, note = R.put(self.files(b"x", "a.png"), ["runs"])
        self.assertEqual((how, placed), ("none", []))
        self.assertTrue(note.startswith("SKIP the rest of the Drive mirror — NoDrive:"), note)

    def test_a_missing_package_is_never_caught(self):
        os.environ[R.KEY_ENV] = "x"
        eng = types.SimpleNamespace(service=mock.Mock(side_effect=SystemExit("no package")))
        with self.assertRaises(SystemExit):
            R.put(self.files(b"x", "a.png"), ["runs"], find_engine=lambda: eng)

    def test_no_delete_trash_or_rename_and_moves_only_through_move(self):
        """NARROWED by LD-89 (tracked Drive moves), a RULED change (the team ~04:25Z: "since the move is
        by machine anwayys, it should be fully tracked"), not a weakened assertion. Was
        test_no_delete_move_or_rename_in_the_source. Now: moves only through gdrive_creator move(),
        every move recorded; still no delete, trash or rename anywhere, and no move in reach.py or
        the two drive_reach.py files — the same regex as before holds over those three. move.py is
        checked for every delete, trash and rename pattern but NOT addParents/removeParents, which
        it alone may use; no other gdrive_creator module may carry them; and move.py's source must
        hold the drive-move record write."""
        harm = (r"\.delete\(|emptyTrash|trashed\s*[\"']?\s*[:=]\s*True|os\.remove|\.unlink\(|"
                r"rmtree|shutil\.move|\.rename\(|os\.replace|\.rmdir\(")
        parents = r"removeParents|addParents"
        bad = re.compile(harm + "|" + parents)
        root = COMPONENT.parent
        for f in (COMPONENT / "gdrive_creator" / "reach.py",
                  root / "image-production" / "image_production" / "drive_reach.py",
                  root / "email-production" / "drive_reach.py"):
            self.assertIsNone(bad.search(f.read_text()), f.name)
        mv = (COMPONENT / "gdrive_creator" / "move.py").read_text()
        self.assertIsNone(re.search(harm, mv), "move.py")
        for f in sorted((COMPONENT / "gdrive_creator").glob("*.py")):
            if f.name != "move.py":
                self.assertIsNone(re.search(parents, f.read_text()), f.name)
        self.assertEqual(mv.count("svc.files().update("), 1, "move.py: one update call")
        self.assertIn('KIND = "drive-move"', mv)
        self.assertIn('"platform" / "data" / "records" / KIND', mv)
        self.assertIn(".write_text(", mv)


class TestFetchFolder(Base):
    def test_flat_fetches_the_files_and_makes_subfolders_empty(self):
        parts = self.photos()
        dest = self.tmp / "local"
        got = R.fetch_folder(parts, dest, svc=self.svc)
        self.assertEqual(got, dest)
        self.assertEqual(sorted(p.name for p in dest.iterdir()),
                         ["01.jpg", "02.png", "03.jpg", "nested"])
        self.assertEqual((dest / "02.png").read_bytes(), b"two-two")
        self.assertEqual(list((dest / "nested").iterdir()), [])
        self.assertNotIn("files.create", self.svc.names())
        self.no_harm()

    def test_recursive_fills_every_subfolder(self):
        parts = self.photos()
        dest = self.tmp / "local"
        R.fetch_folder(parts, dest, recursive=True, svc=self.svc)
        self.assertEqual((dest / "nested" / "04.jpg").read_bytes(), b"four")
        self.assertEqual((dest / "nested" / "deeper" / "05.jpg").read_bytes(), b"five")

    def test_max_bytes_stops_and_says_so(self):
        parts = self.photos()
        dest = self.tmp / "local"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            R.fetch_folder(parts, dest, recursive=True, max_bytes=8, svc=self.svc)
        # 01.jpg (3) then 02.png (7) crosses 8 bytes: 03.jpg and below are left
        self.assertEqual(sorted(p.name for p in dest.iterdir() if p.is_file()),
                         ["01.jpg", "02.png"])
        # the folders are still made; no file below them is fetched
        self.assertTrue((dest / "nested" / "deeper").is_dir())
        self.assertEqual([p for p in (dest / "nested").rglob("*") if p.is_file()], [])
        said = err.getvalue()
        self.assertIn("STOPPED at max_bytes=8", said)
        self.assertIn("10 bytes in 2 files", said)
        for left in ("03.jpg", "nested/04.jpg", "nested/deeper/05.jpg"):
            self.assertIn(left, said)

    def test_a_missing_folder_is_none_and_writes_nothing(self):
        self.photos()
        dest = self.tmp / "local"
        self.assertIsNone(R.fetch_folder(["swipe", "nobody"], dest, svc=self.svc))
        self.assertFalse(dest.exists())


class TestReadable(Base):
    def mounted_photos(self):
        sa = self.a_mount()
        ph = sa / "swipe" / "brand-x" / "photos"
        ph.mkdir(parents=True)
        for n in ("01.jpg", "02.png", "03.jpg"):
            (ph / n).write_bytes(b"m")
        return sa, ph

    def test_a_mount_path_that_lists_is_itself(self):
        sa, ph = self.mounted_photos()
        os.environ.pop(R.KEY_ENV, None)             # no key: the mount route, read in place
        self.assertEqual(R.readable(ph, svc=Exploding(), find_engine=Exploding), ph)
        self.assertEqual(R.readable(ph / "01.jpg", svc=Exploding(),
                                    find_engine=Exploding), ph / "01.jpg")
        self.assertEqual(R.readable("Shared Assets/swipe/brand-x/photos",
                                    svc=Exploding(), find_engine=Exploding), ph)

    def test_a_key_reads_through_the_api_even_where_the_mount_lists(self):
        # LD-47 step 1.5 (the team, 2026-10-20: "all of the components use the key"): a key decides the
        # route for reads too, so the mount is never read when one is set — reversing the old
        # "a key does not send a readable path to the API" (this test's predecessor's assertion).
        sa, ph = self.mounted_photos()
        self.photos()
        os.environ[R.KEY_ENV] = "x"
        got = R.readable(ph, svc=self.svc)
        self.assertNotEqual(got, ph)
        self.assertTrue(str(got).startswith(str(R.cache_root())), got)   # LD-79 (Drive ref resolver): the lasting cache
        self.assertEqual(sorted(p.name for p in got.iterdir() if p.is_file()),
                         ["01.jpg", "02.png", "03.jpg"])
        self.no_harm()

    def test_a_mount_path_that_raises_permission_error_is_an_api_copy(self):
        sa, ph = self.mounted_photos()
        self.photos()
        real_listdir, real_open = os.listdir, open
        under = str(sa)

        def listdir(p="."):
            if str(p).startswith(under):
                raise PermissionError(1, "Operation not permitted", str(p))
            return real_listdir(p)

        def opener(p, *a, **kw):
            if str(p).startswith(under):
                raise PermissionError(1, "Operation not permitted", str(p))
            return real_open(p, *a, **kw)

        with mock.patch("os.listdir", listdir), mock.patch("builtins.open", opener):
            got = R.readable(ph, svc=self.svc)
            one = R.readable(ph / "02.png", svc=self.svc)
        self.assertNotEqual(got, ph)
        self.assertTrue(str(got).startswith(str(R.cache_root())), got)   # LD-79 (Drive ref resolver): the lasting cache
        self.assertEqual(sorted(p.name for p in got.iterdir() if p.is_file()),
                         sorted(p.name for p in ph.iterdir()))
        self.assertEqual(one.name, "02.png")
        self.assertEqual(one.read_bytes(), b"two-two")
        self.no_harm()

    def test_a_label_with_no_mount_is_an_api_copy(self):
        self.photos()
        got = R.readable("Shared Assets/swipe/brand-x/photos", svc=self.svc)
        self.assertTrue(str(got).startswith(str(R.cache_root())), got)   # LD-79 (Drive ref resolver): the lasting cache
        self.assertEqual(got.parts[-3:], ("swipe", "brand-x", "photos"))
        self.assertEqual(sorted(p.name for p in got.iterdir() if p.is_file()),
                         ["01.jpg", "02.png", "03.jpg"])
        f = R.readable("Shared Assets/swipe/brand-x/photos/nested/04.jpg", svc=self.svc)
        self.assertEqual(f.read_bytes(), b"four")
        media = self.svc.names().count("files.get_media")
        self.assertEqual(R.readable("Shared Assets/swipe/brand-x/photos", svc=self.svc), got)
        self.assertEqual(self.svc.names().count("files.get_media"), media)   # one copy per process
        self.no_harm()

    def test_nowhere_is_a_named_nodrive(self):
        self.photos()
        with self.assertRaises(R.NoDrive) as c:
            R.readable("Shared Assets/swipe/nobody", svc=self.svc)
        self.assertIn("Shared Assets/swipe/nobody", str(c.exception))

    def test_a_local_path_is_itself(self):
        p = self.tmp / "local.txt"
        self.assertEqual(R.readable(p, svc=Exploding(), find_engine=Exploding), p)



class TestDriveId(Base):
    """LD-47 (Drive sweep) step 2: one Drive-id lookup for every component — by the key, else the xattr."""

    def test_by_the_key_a_file_and_a_folder(self):
        self.photos()
        os.environ[R.KEY_ENV] = "x"
        fid = R.drive_id("Shared Assets/swipe/brand-x/photos/01.jpg", svc=self.svc)
        self.assertTrue(fid)
        self.assertTrue(R.drive_id("Shared Assets/swipe/brand-x/photos", svc=self.svc))
        self.assertIsNone(R.drive_id("Shared Assets/swipe/brand-x/photos/none.jpg", svc=self.svc))
        self.no_harm()

    def test_not_under_shared_assets_is_none(self):
        os.environ[R.KEY_ENV] = "x"
        self.assertIsNone(R.drive_id(self.tmp / "local.jpg", svc=Exploding(), find_engine=Exploding))

    def test_no_key_reads_the_xattr_and_never_the_api(self):
        p = self.tmp / "mnt" / "Shared Assets" / "a.jpg"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"x")
        self.assertIsNone(R.drive_id(p, svc=Exploding(), find_engine=Exploding))   # no xattr on a temp file

class TestListTree(Base):
    def setUp(self):
        super().setUp()
        self.patch(E, "get_media", mock.Mock(side_effect=AssertionError("list_tree downloaded a file")))

    def ids(self, *rels):
        return [(r, self.svc.path("swipe", "brand-x", "photos", *r.split("/"))) for r in rels]

    def test_every_file_recursive_by_name_and_nothing_downloaded(self):
        parts = self.photos()
        before = sorted(self.tmp.rglob("*"))
        got = R.list_tree(parts, svc=self.svc)
        self.assertEqual(got, self.ids("01.jpg", "02.png", "03.jpg",
                                       "nested/04.jpg", "nested/deeper/05.jpg"))
        self.assertNotIn("files.get_media", self.svc.names())
        self.assertNotIn("files.create", self.svc.names())
        E.get_media.assert_not_called()
        self.assertEqual(sorted(self.tmp.rglob("*")), before)    # nothing written anywhere
        self.no_harm()

    def test_max_items_stops_and_says_so(self):
        parts = self.photos()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = R.list_tree(parts, svc=self.svc, max_items=4)
        self.assertEqual(got, self.ids("01.jpg", "02.png", "03.jpg", "nested/04.jpg"))
        said = err.getvalue()
        self.assertIn("STOPPED at max_items=4", said)
        self.assertIn("4 files listed under Shared Assets/swipe/brand-x/photos", said)
        self.assertIn("nested/deeper/", said)
        listed = sum(1 for c, kw in self.svc.calls if c == "files.list"
                     and "'%s' in parents" % self.svc.path("swipe", "brand-x", "photos",
                                                           "nested", "deeper") in kw["q"])
        self.assertEqual(listed, 0)                              # the stop lists nothing more

    def test_exactly_max_items_is_no_stop(self):
        parts = self.photos()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = R.list_tree(parts, svc=self.svc, max_items=5)
        self.assertEqual(len(got), 5)
        self.assertEqual(err.getvalue(), "")

    def test_a_missing_folder_is_none(self):
        self.photos()
        self.assertIsNone(R.list_tree(["swipe", "nobody"], svc=self.svc))
        self.no_harm()


class TestPutIds(Base):
    """LD-64 (records Drive ids): put_ids keeps the ids the upload already
    gave back — no Drive call is added."""

    def files(self, data, *names):
        src = self.tmp / "out"
        src.mkdir(exist_ok=True)
        out = []
        for n in names:
            (src / n).write_bytes(data)
            out.append(src / n)
        return out

    def test_api_ids_are_the_uploads_own(self):
        os.environ[R.KEY_ENV] = "x"
        parts = ["runs", "zz-tool", "lbl"]
        r = R.put_ids(self.files(b"v1", "a.png", "b.mp4"), parts, svc=self.svc)
        self.assertEqual(r["how"], "api")
        self.assertEqual(r["folder"], "Shared Assets/runs/zz-tool/lbl")
        self.assertEqual(r["folder_id"], self.svc.path("runs", "zz-tool", "lbl"))
        self.assertEqual(r["files"], [
            {"name": "a.png", "id": self.svc.path("runs", "zz-tool", "lbl", "a.png"), "kind": "image"},
            {"name": "b.mp4", "id": self.svc.path("runs", "zz-tool", "lbl", "b.mp4"), "kind": "video"}])
        self.assertEqual((r["how"], r["placed"], r["note"]),
                         R.put(self.files(b"v1", "a.png", "b.mp4"), parts, svc=self.svc))
        self.no_harm()

    def test_mount_ids_are_null(self):
        self.a_mount()
        r = R.put_ids(self.files(b"x", "a.png", "b.mp4"), ["runs", "lbl"],
                      svc=Exploding(), find_engine=Exploding)
        self.assertEqual((r["how"], r["note"], r["folder_id"]), ("mount", None, None))
        self.assertEqual([f["name"] for f in r["files"]], ["a.png", "b.mp4"])
        self.assertTrue(all(f["id"] is None for f in r["files"]))
        self.assertEqual(len(r["placed"]), 2)

    def test_no_route_has_no_files(self):
        r = R.put_ids(self.files(b"x", "a.png"), ["runs"])
        self.assertEqual((r["how"], r["placed"], r["files"], r["folder_id"]),
                         ("none", [], [], None))
        self.assertTrue(r["note"].startswith("SKIP"), r["note"])

    def test_a_failure_part_way_keeps_the_rows_before_it(self):
        os.environ[R.KEY_ENV] = "x"
        real = E.upload_file
        seen = []

        def flaky(path, name, parent_id, svc=None, **kw):
            seen.append(name)
            if len(seen) == 2:
                raise RuntimeError("upload broke")
            return real(path, name, parent_id, svc=svc, **kw)
        self.patch(E, "upload_file", flaky)
        r = R.put_ids(self.files(b"x", "a.png", "b.png"), ["runs", "lbl"], svc=self.svc)
        self.assertEqual([f["name"] for f in r["files"]], ["a.png"])
        self.assertEqual(len(r["placed"]), 1)
        self.assertTrue(r["note"].startswith("SKIP"), r["note"])
        self.assertIn("upload broke", r["note"])

    def test_kind_table_and_drive_json(self):
        for name, want in (("a.PNG", "image"), ("b.jpeg", "image"), ("c.svg", "image"),
                           ("d.mp4", "video"), ("e.MOV", "video"), ("f.mp3", "audio"),
                           ("g.wav", "audio"), ("h.json", "text"), ("i.md", "text"),
                           ("j.srt", "text"), ("k.yml", "text"), ("x.bin", "other"),
                           ("noext", "other")):
            self.assertEqual(R.kind(name), want, name)
        self.assertEqual(R.DRIVE_JSON, "drive.json")
        rec = R.drive_json(["runs", "zz-tool", "zz-brand", "lbl"], "fid", "api",
                           [{"path": "media/s1.mp4", "id": "i2"},
                            {"path": "a.png", "id": "i1", "kind": "image"}])
        self.assertEqual(rec, {
            "schema": 1, "folder": "Shared Assets/runs/zz-tool/zz-brand/lbl",
            "folder_id": "fid", "route": "api",
            "files": [{"path": "a.png", "id": "i1", "kind": "image"},
                      {"path": "media/s1.mp4", "id": "i2", "kind": "video"}]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
