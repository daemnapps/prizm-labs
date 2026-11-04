#!/usr/bin/env python3
"""LD-89 (tracked Drive moves): a move changes the file's parent, keeps its Drive id and leaves ONE
drive-move record; still no delete, trash or rename — proven offline.

    python3 components/gdrive-creator/tests/test_move.py

The fake Drive is test_reach.py's own, given files().get (parents and driveId) and a parent-changing
files().update; every other method it was not given is recorded and FAILS, so a delete or an
emptyTrash cannot pass unseen. Records land under a temp record_root, never the repo. No Google
package, no key, no network. Stdlib only, 3.9.

  a  a move: one files().update with addParents/removeParents and supportsAllDrives=True, no body;
     the id kept; from/to labels; missing target folders made; exactly one record with every field
  b  refused (MoveRefused, no update, no folder made, no record): a second parent; a file on another
     drive; a target that is not a list of folder names under Shared Assets; a file the key cannot
     see; the file already in the target
  c  a second move of the same file in the same second gets its own record (-2), the first kept
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))                         # test_reach, beside this file
import test_reach as TR                            # noqa: E402  (appends the component to sys.path)

from gdrive_creator.move import move, MoveRefused, KIND   # noqa: E402

FIELDS = {"drive_id", "name", "from", "to", "by", "why", "at"}


class NotFound(Exception):
    pass


class MoveDrive(TR.FakeDrive):
    """test_reach's fake Drive plus a second shared drive, a second parent on demand, files().get and
    a files().update that changes parents."""

    def __init__(self):
        super().__init__()
        self.nodes["d-other"] = {"id": "d-other", "name": "Other", "mimeType": TR.FOLDER, "parent": None}
        self.extra = {}                            # node id -> a second parent

    def drive_of(self, nid):
        while self.nodes[nid]["parent"] is not None:
            nid = self.nodes[nid]["parent"]
        return nid

    def files(self):
        d, base = self, super().files()

        class Files(object):
            def get(self, **kw):
                d.calls.append(("files.get", kw))
                n = d.nodes.get(kw["fileId"])
                if n is None:
                    raise NotFound("File not found: %s" % kw["fileId"])
                ps = ([n["parent"]] if n["parent"] else []) + ([d.extra[n["id"]]] if n["id"] in d.extra else [])
                return TR.Req({"id": n["id"], "name": n["name"], "parents": ps,
                               "driveId": d.drive_of(n["id"])})

            def update(self, **kw):
                d.calls.append(("files.update", kw))
                n = d.nodes[kw["fileId"]]
                assert kw["removeParents"] == n["parent"], kw
                n["parent"] = kw["addParents"]
                return TR.Req({"id": n["id"], "name": n["name"], "parents": [n["parent"]]})

            def __getattr__(self, name):
                return getattr(base, name)
        return Files()


class Base(TR.Base):
    def setUp(self):
        super().setUp()
        self.svc = MoveDrive()
        s = self.svc
        self.inbox = s.add(s.add(s.add(s.add(s.add("d-sa", "handoffs"), "graphic-designer"), "zz-brand"), "zz_nova_brief-0001"), "returned")
        self.fid = s.add(self.inbox, "hero.png", b"bytes")
        self.root = self.tmp / "repo"

    def records(self):
        d = self.root / "platform" / "data" / "records" / KIND
        return sorted(d.glob("*.json")) if d.is_dir() else []

    def updates(self):
        return [kw for c, kw in self.svc.calls if c == "files.update"]

    def no_harm(self):
        """No delete, trash, copy or any method the fake was not given; an update carries only the
        two parent changes."""
        for c, kw in self.svc.calls:
            self.assertIn(c, TR.ALLOWED | {"files.get"}, c)
            self.assertNotIn(c, ("files.delete", "files.emptyTrash"))
            if c == "files.update":
                self.assertNotIn("body", kw)
                self.assertNotIn("media_body", kw)

    def go(self, to=("runs", "image-production", "used"), **kw):
        return move(self.fid, list(to), kw.pop("by", "graphic-designer"), kw.pop("why", "used in p152"),
                    svc=self.svc, record_root=self.root, **kw)


class TestMove(Base):
    def test_one_update_changes_the_parent_and_keeps_the_id(self):
        got = self.go()
        target = self.svc.path("runs", "image-production", "used")
        ups = self.updates()
        self.assertEqual(len(ups), 1)
        self.assertEqual(ups[0]["fileId"], self.fid)
        self.assertEqual(ups[0]["addParents"], target)
        self.assertEqual(ups[0]["removeParents"], self.inbox)
        self.assertIs(ups[0]["supportsAllDrives"], True)
        self.assertEqual(got["drive_id"], self.fid)
        self.assertEqual(self.svc.nodes[self.fid]["parent"], target)
        self.assertEqual(self.svc.nodes[self.fid]["data"], b"bytes")
        self.assertEqual(got["name"], "hero.png")
        self.assertEqual(got["from"], "Shared Assets/handoffs/graphic-designer/zz-brand/zz_nova_brief-0001/returned")
        self.assertEqual(got["to"], "Shared Assets/runs/image-production/used")
        self.assertEqual(set(got), {"drive_id", "name", "from", "to", "record"})
        self.no_harm()

    def test_exactly_one_record_with_every_field(self):
        got = self.go(by="graphic-designer", why="used in p152")
        recs = self.records()
        self.assertEqual(len(recs), 1)
        self.assertEqual(str(recs[0]), got["record"])
        self.assertRegex(recs[0].name, r"^\d{8}T\d{6}Z--graphic-designer--%s\.json$" % self.fid)
        r = json.loads(recs[0].read_text())
        self.assertEqual((r["schema"], r["kind"], r["reviewer"], r["item"], r["via"]),
                         (1, "drive-move", "graphic-designer", self.fid, "gdrive-creator/move"))
        v = r["verdict"]
        self.assertEqual(set(v), FIELDS)
        self.assertEqual({k: v[k] for k in ("drive_id", "name", "from", "to", "by", "why")},
                         {"drive_id": self.fid, "name": "hero.png",
                          "from": "Shared Assets/handoffs/graphic-designer/zz-brand/zz_nova_brief-0001/returned",
                          "to": "Shared Assets/runs/image-production/used", "by": "graphic-designer",
                          "why": "used in p152"})
        self.assertRegex(v["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(r["created"], v["at"])

    def test_an_existing_target_is_found_not_made_again(self):
        s = self.svc
        used = s.add(s.add("d-sa", "done"), "used")
        before = s.names().count("files.create")
        got = self.go(to=("done", "used"))
        self.assertEqual(s.names().count("files.create"), before)
        self.assertEqual(s.nodes[self.fid]["parent"], used)
        self.assertEqual(got["to"], "Shared Assets/done/used")

    def test_a_second_move_in_the_same_second_keeps_both_records(self):
        self.go(to=("a",))
        self.go(to=("b",))
        recs = self.records()
        self.assertEqual(len(recs), 2)
        tos = sorted(json.loads(p.read_text())["verdict"]["to"] for p in recs)
        self.assertEqual(tos, ["Shared Assets/a", "Shared Assets/b"])
        self.no_harm()


class TestRefused(Base):
    def refused(self, *say, **kw):
        fid = kw.pop("fid", self.fid)
        to = kw.pop("to", ["runs", "used"])
        with self.assertRaises(MoveRefused) as c:
            move(fid, to, "graphic-designer", "why", svc=self.svc, record_root=self.root)
        for s in say:
            self.assertIn(s, str(c.exception))
        self.assertEqual(self.updates(), [])
        self.assertNotIn("files.create", self.svc.names())
        self.assertEqual(self.records(), [])
        self.no_harm()

    def test_a_second_parent_is_refused(self):
        self.svc.extra[self.fid] = self.svc.add("d-sa", "elsewhere")
        self.svc.calls.clear()
        self.refused("2 parents")

    def test_a_file_on_another_drive_is_refused(self):
        other = self.svc.add(self.svc.add("d-other", "x"), "a.png", b"a")
        self.refused("not on Shared Assets", fid=other)

    def test_a_target_outside_shared_assets_is_refused(self):
        for to in (["..", "x"], ["runs", ""], ["Other/x"], "Shared Assets/runs", ["runs", "."]):
            self.refused("to_parts" if isinstance(to, str) else "target outside", to=to)

    def test_a_file_the_key_cannot_see_is_refused(self):
        self.refused("cannot see", fid="no-such-id")

    def test_the_file_already_there_is_refused(self):
        with self.assertRaises(MoveRefused) as c:
            move(self.fid, ["handoffs", "graphic-designer", "zz-brand", "zz_nova_brief-0001", "returned"], "graphic-designer", "why",
                 svc=self.svc, record_root=self.root)
        self.assertIn("already in", str(c.exception))
        self.assertEqual(self.updates(), [])
        self.assertEqual(self.records(), [])

    def test_a_delete_or_empty_trash_call_cannot_pass_unseen(self):
        with self.assertRaises(AssertionError):
            self.svc.files().delete(fileId=self.fid)
        with self.assertRaises(AssertionError):
            self.svc.files().emptyTrash()
        self.assertEqual([c for c, _ in self.svc.calls], ["files.delete", "files.emptyTrash"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
