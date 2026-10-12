#!/usr/bin/env python3
"""ad-handoff gate honest — SI-149 (ad-handoff gate honest), DCB-1 (the owner component bugs) part a.

    /usr/bin/python3 components/ad-handoff/tests/test_dcb1a_gate_honest.py

`--check` makes nothing on Drive, a partial run never prints READY, and
checks 1, 2 and 5 compare what they claim. Offline: Drive is an in-memory
Shared Assets tree whose service RECORDS every create call, and a fake
gdrive-creator engine exposing `_folder_by_name`, `_folder_listed`,
`shared_drive_id` and `folder` (which records too). No key, no network; the
verdict record goes to a temp runs root.
"""
import io, re, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import handoff as H
from test_ad_handoff import AD, build

FOR = "reader@example.com"
FOLDER_MIME = "application/vnd.google-apps.folder"
DROP_PATH = ("runs", "image-teardown", "acme", "260101a", "deliverable")


class _Call:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeDrive:
    """Shared Assets in memory: nodes by id, each with a name, a parent and a size."""
    def __init__(self, perms=()):
        self.nodes, self.creates, self.perms, self._n = {}, [], list(perms), 0

    # the tree
    def child(self, parent, name):
        for i, n in self.nodes.items():
            if n["parent"] == parent and n["name"] == name and n["mimeType"] == FOLDER_MIME:
                return i
        return None

    def mkdirs(self, parts, last_id=None):
        node = "SA"
        for k, p in enumerate(parts):
            got = self.child(node, p)
            if not got:
                self._n += 1
                got = last_id if (last_id and k == len(parts) - 1) else f"F{self._n}"
                self.nodes[got] = {"name": p, "parent": node, "mimeType": FOLDER_MIME, "size": None}
            node = got
        return node

    def put(self, parent, name, size):
        self._n += 1
        self.nodes[f"X{self._n}"] = {"name": name, "parent": parent,
                                     "mimeType": "application/octet-stream", "size": str(size)}

    def mirror(self, d, last_id="FAKEID"):
        """Upload the local drop as-is; the deliverable folder gets `last_id`."""
        top = self.mkdirs(DROP_PATH, last_id)
        for f in ("HANDOFF.md", "copy.csv"):
            if (d / f).is_file():
                self.put(top, f, (d / f).stat().st_size)
        for a in H.ad_folders(d):
            fid = self.mkdirs(DROP_PATH + (a.name,))
            for p in H.pictures(a):
                self.put(fid, p.name, p.stat().st_size)
        return top

    def rename(self, old, new):
        for n in self.nodes.values():
            if n["name"] == old:
                n["name"] = new

    # the service surface handoff.py touches
    def files(self):
        return self

    def permissions(self):
        return self

    def list(self, q="", fileId=None, **kw):
        if fileId is not None:
            return _Call({"permissions": self.perms})
        parent = re.search(r"'([^']+)' in parents", q).group(1)
        return _Call({"files": [dict(id=i, **{k: v for k, v in n.items() if k != "parent"})
                                for i, n in self.nodes.items() if n["parent"] == parent]})

    def create(self, **kw):
        self.creates.append(kw)
        return _Call({"id": "MADE"})


class FakeEngine:
    """gdrive-creator's engine, as far as the gate may see it."""
    def __init__(self, drive):
        self.drive, self.folder_calls = drive, []

    def shared_drive_id(self, name, svc=None):
        return "SA" if name == "Shared Assets" else None

    def _folder_by_name(self, svc, name, parent_id):
        return self.drive.child(parent_id, name)

    def _folder_listed(self, svc, name, parent_id):
        return self.drive.child(parent_id, name)

    def folder(self, name, parent_id, svc=None):     # CREATES — the gate must never call it
        self.folder_calls.append((name, parent_id))
        return (svc or self.drive).files().create(
            body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}).execute()["id"]


def no_drive():
    raise AssertionError("an offline run reached for Drive")


class Gate(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        t = Path(self._t.name)
        self.drop = t / "runs" / "image-teardown" / "acme" / "260101a" / "deliverable"
        self.runs = t / "verdicts"

    def tearDown(self):
        self._t.cleanup()

    def main(self, *args, drive=None):
        """main() on --dir <drop> plus args; (exit code, stdout, engine)."""
        engine = FakeEngine(drive) if drive is not None else None
        svc = mock.patch.object(H, "drive_service", return_value=(engine, drive)) \
            if drive is not None else mock.patch.object(H, "drive_service", side_effect=no_drive)
        argv = ["handoff.py", "--dir", str(self.drop)] + list(args)
        out, code = io.StringIO(), 0
        with svc, mock.patch.object(H, "RUNS", self.runs), \
                mock.patch.object(sys, "argv", argv), redirect_stdout(out):
            try:
                H.main()
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), engine

    def online_drop(self, **kw):
        build(self.drop, **kw)
        drive = FakeDrive(perms=[{"type": "user", "role": "reader", "emailAddress": FOR}])
        drive.mirror(self.drop)
        return drive

    # 1 · --check on a drop missing on Drive: nothing is made, the path is named
    def test_check_on_a_drop_missing_on_drive_creates_nothing_and_refuses(self):
        build(self.drop)
        drive = FakeDrive(perms=[{"type": "user", "role": "reader", "emailAddress": FOR}])
        drive.mkdirs(("runs", "image-teardown", "acme"))
        code, out, engine = self.main("--check", "--for", FOR, drive=drive)
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED", out)
        self.assertIn("not on Drive yet: Shared Assets/runs/image-teardown/acme/260101a", out)
        self.assertEqual(drive.creates, [])
        self.assertEqual(engine.folder_calls, [])
        self.assertIsNone(drive.child(drive.child(drive.child(drive.child(
            "SA", "runs"), "image-teardown"), "acme"), "260101a"))

    def test_the_walk_never_calls_the_creating_folder(self):
        src = (HERE.parent / "handoff.py").read_text()
        self.assertNotIn("engine.folder(", src)

    # 2 · a swapped picture with an equal count is refused, by name
    def test_a_swapped_picture_with_an_equal_count_is_refused(self):
        drive = self.online_drop()
        drive.rename(f"{AD}-a02.png", f"{AD}-a03.png")
        code, out, _ = self.main("--check", "--for", FOR, drive=drive)
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED", out)
        self.assertIn("1 picture(s) here are not on Drive", out)
        self.assertIn("-a02.png", out)
        self.assertIn("1 picture(s) on Drive are not in this folder", out)
        self.assertIn("-a03.png", out)

    def test_a_zero_byte_picture_on_drive_is_refused(self):
        drive = self.online_drop()
        for n in drive.nodes.values():
            if n["name"] == f"{AD}-a01.png":
                n["size"] = "0"
        code, out, _ = self.main("--check", "--for", FOR, drive=drive)
        self.assertEqual(code, 1, out)
        self.assertIn("have no bytes", out)

    # 1 (check) · online, the page must link THIS folder
    def test_a_page_linking_another_folder_is_refused_online(self):
        drive = self.online_drop()
        page = self.drop / "HANDOFF.md"
        page.write_text(page.read_text().replace("FAKEID", "SOMEOTHERID"))
        code, out, _ = self.main("--check", "--for", FOR, drive=drive)
        self.assertEqual(code, 1, out)
        self.assertIn("HANDOFF.md links Drive folder SOMEOTHERID", out)
        self.assertIn("FAKEID", out)

    # 3 · --offline is PARTIAL: exit 2, no link, never READY
    def test_offline_is_partial_with_no_link(self):
        build(self.drop)
        code, out, _ = self.main("--check", "--offline", "--for", FOR)
        self.assertEqual(code, 2, out)
        self.assertIn("PARTIAL — 4 of 7 checked", out)
        self.assertNotIn("READY", out)
        self.assertNotIn("drive.google.com", out)

    def test_offline_funnel_links_are_not_counted_as_checked(self):
        build(self.drop, links={"Offer page": "https://example.invalid/"})
        with mock.patch.object(H, "resolves", side_effect=AssertionError("resolved offline")):
            code, out, _ = self.main("--check", "--offline")
        self.assertEqual(code, 2, out)
        self.assertIn("PARTIAL — 3 of 7 checked", out)

    # 6 (instruction) · no --for, online: PARTIAL, exit 2, no link
    def test_no_for_online_is_partial(self):
        drive = self.online_drop()
        code, out, _ = self.main("--check", drive=drive)
        self.assertEqual(code, 2, out)
        self.assertIn("PARTIAL — 6 of 7 checked", out)
        self.assertNotIn("READY", out)
        self.assertNotIn("drive.google.com", out)
        self.assertEqual(drive.creates, [])

    def test_a_full_online_run_is_ready_with_its_link(self):
        """The control: the fake is honest enough to let a complete drop through."""
        drive = self.online_drop()
        code, out, engine = self.main("--check", "--for", FOR, drive=drive)
        self.assertIn(code, (0, None), out)
        self.assertIn("READY — every check passed", out)
        self.assertIn("https://drive.google.com/drive/folders/FAKEID", out)
        self.assertEqual((drive.creates, engine.folder_calls), ([], []))

    # 4 · --dir: brand and drop come from the path, or the run refuses
    def test_dir_derives_brand_and_drop(self):
        build(self.drop)
        with mock.patch.object(H, "run_checks", wraps=H.run_checks) as rc:
            code, out, _ = self.main("--check", "--offline")
        self.assertEqual(code, 2, out)
        args = rc.call_args[0]
        self.assertEqual((args[1], args[2]), ("acme", "260101a"))
        self.assertTrue((self.runs / "acme" / "260101a" / "run.json").is_file())

    def test_dir_that_does_not_end_in_deliverable_refuses(self):
        build(self.drop)
        odd = self.drop.parent / "elsewhere"
        odd.mkdir()
        self.drop = odd
        with mock.patch.object(H, "run_checks", side_effect=AssertionError("ran")):
            code, _, _ = self.main("--check", "--offline")
        self.assertIsInstance(code, str)
        self.assertIn(str(odd), code)
        self.assertIn("<brand>/<drop>/deliverable", code)

    def test_dir_disagreeing_with_brand_refuses(self):
        build(self.drop)
        with mock.patch.object(H, "run_checks", side_effect=AssertionError("ran")):
            code, _, _ = self.main("--check", "--offline", "--brand", "other")
        self.assertIsInstance(code, str)
        self.assertIn("not --brand other", code)

    # 5 · a naming import that fails refuses
    def test_a_naming_import_failure_refuses(self):
        build(self.drop)
        with mock.patch.dict(sys.modules, {"names": None}):
            code, out, _ = self.main("--check", "--offline")
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED", out)
        # a missing module raises ModuleNotFoundError, a subclass of ImportError
        prefix = "name check could not run — "
        line = next((l.strip() for l in out.splitlines() if prefix in l), "")
        self.assertTrue(line, out)
        self.assertIn(line[line.index(prefix) + len(prefix):],
                      ("ImportError", "ModuleNotFoundError"), out)

    # 7 (card change) · the HANDOFF.md fallback reads [text](url) links too
    def test_links_fall_back_to_markdown_links(self):
        build(self.drop)
        (self.drop / "HANDOFF.md").write_text(
            "[Folder](https://drive.google.com/drive/folders/FAKEID)\n\n"
            "See the [Offer page](https://example.com/offer/) and "
            "![hero](https://example.com/hero.png).\n")
        self.assertEqual(H.links(self.drop), {"Offer page": "https://example.com/offer/"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
