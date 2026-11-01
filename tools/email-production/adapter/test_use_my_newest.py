#!/usr/bin/env python3
"""LD-90 (the team takes newest): "<id> P<n>: use my newest" — the newest picture in her team folder is MOVED into the run's
Drive media, placed, both refs and made_with stored, one model-outcome record, history appended — proven offline, on a
temp fixture run.

    python3 tools/email-production/adapter/test_use_my_newest.py     (from the repo root: never with the working
                                                                           folder inside tools/email-production,
                                                                           whose email.py shadows the stdlib's)

Faked at the seams take_newest exposes: the Drive lister (a dict of folders), the mover (LD-89 (tracked Drive moves)'s
move(): it takes the file out of the fake folder and writes a drive-move record under a temp root), the by-id fetcher;
and, under the REAL place(): as_jpeg (no PIL), the Drive put (gdrive-creator's reach.put_ids), the rebuild, the stamp
file and ask.share. No network, no key. Every record lands under a temp root, never the real plane.

  1  newest: the newest picture over older ones and over a subfolder's; one level down counts, two levels and
     non-pictures don't; an empty or missing folder is None
  2  the take: mover called exactly once with the run's media parts and the why; the file is gone from the fake folder
  3  both refs on the picture (original + email_copy, each {drive_id, label}) and made_with; a real photo is a photo
  4  an empty made_with is refused with the question before anything moves; a bad alt too; a refused move changes nothing
  5  exactly one model-outcome record: door own, picked true, never judged; the kind's verdict fields, in order
  6  history: a second take and a restore append, never rewrite
  7  ask.py: "use my newest (made with …): …" parses to the new action; a line with no picture is asked back; the
     reply names where it went and the drive-move record, and both records are committed with the email
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))      # this folder FIRST; never tools/email-production (its email.py)
import own_picture as OP           # noqa: E402
import try_picture as TP           # noqa: E402
import prepare                     # noqa: E402
import ask                         # noqa: E402

REPO = Path(OP.REPO)
sys.path.append(str(REPO / "components" / "gdrive-creator"))
from gdrive_creator import reach as REAL_REACH  # noqa: E402  (kind() only: stdlib, no network)

BRAND = "zz-brand"
LABEL = "zz-brand-nov-99"
EVE = ("runs", "handoffs", "graphic-designer", BRAND, LABEL, "returned")    # the email's returned/ for the role (2026-10-27)
MEDIA = ["runs", "email-production", BRAND, LABEL, "media"]
JPEG = b"\xff\xd8\xff\xe0"
QUESTION = "what made it — Higgsfield, Photoshop, a real photo…?"


class TestRole(unittest.TestCase):
    """The folder is the asker's ROLE, never their name (the owner, 2026-10-27: "make this name agnostic")."""
    def test_role_from_the_one_setting_and_a_default(self):
        roles = (json.loads(OP.ROLES.read_text()).get("roles") or {}) if OP.ROLES.is_file() else {}
        for role, v in roles.items():
            if (v or {}).get("filled_by"):
                self.assertEqual(OP.role_of(v["filled_by"]), role)
            self.assertEqual(OP.role_of(role), role)
        self.assertEqual(OP.role_of("someone new"), OP.ROLE)
        self.assertEqual(OP.returned_parts("b", "lbl"), ["runs", "handoffs", "graphic-designer", "b", "lbl", "returned"])

    def test_no_person_folder_in_the_code(self):
        src = Path(OP.__file__).read_text()
        self.assertNotIn('"team", ', src)
        self.assertNotIn("team/<person>", src)


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(os.path.realpath(t.name))
        self.run = self.tmp / "runs" / "email-production" / BRAND / LABEL
        for d in ("design", "media/records/zz-pic", "klaviyo"):
            (self.run / d).mkdir(parents=True)
        (self.run / "media" / "pic.png").write_bytes(JPEG + b"old")
        (self.run / "klaviyo" / "card.json").write_text("{}\n")
        (self.run / "media" / "records" / "zz-pic" / "record.json").write_text(json.dumps(
            {"label": "zz-pic", "file": "media/pic.png", "purpose": "email-story"}))
        self.spec = self.run / "design" / "email.json"
        self.spec.write_text(json.dumps({"brand": BRAND, "sections": [
            {"s": "band"},
            {"s": "hero_photo", "headline": "Hello", "picture": {"photo": "run:media/pic.png", "alt": "a jar on a sink",
                                                                 "record": "media/records/zz-pic/record.json"}},
            {"s": "photo_card", "text": "card", "picture": {"photo": "run:media/other.png", "alt": "another jar"}}]},
            indent=1))
        # the fake Drive: folder parts -> rows; a subfolder is a row with folder true
        self.drive = {
            EVE: [{"id": "id-old", "name": "old.jpg", "modified": "2026-10-20T09:00:00.000Z"},
                  {"id": "id-new", "name": "new.png", "modified": "2026-10-23T05:00:00.000Z"},
                  {"id": "id-note", "name": "notes.txt", "modified": "2026-10-23T06:00:00.000Z"},
                  {"id": "f-brief", "name": "nov-brief", "folder": True}],
            EVE + ("nov-brief",): [{"id": "id-sub", "name": "sub.jpg", "modified": "2026-10-22T09:00:00.000Z"},
                                   {"id": "f-deep", "name": "deeper", "folder": True}],
            EVE + ("nov-brief", "deeper"): [{"id": "id-deep", "name": "deep.jpg", "modified": "2026-10-24T00:00:00.000Z"}]}
        self.moves, self.fetched, self.puts, self.rebuilds = [], [], [], 0
        self.out = io.StringIO()

        def put_ids(files, parts, **k):
            self.puts.append((list(files), list(parts)))
            return {"how": "api", "placed": ["Shared Assets/%s/%s" % ("/".join(parts), Path(f).name) for f in files],
                    "note": None, "folder": "Shared Assets/" + "/".join(parts), "folder_id": "f-media",
                    "files": [{"name": Path(f).name, "id": "id-copy-%d" % len(self.puts), "kind": "image"} for f in files]}
        fake_reach = types.SimpleNamespace(SHARED_DRIVE="Shared Assets", kind=REAL_REACH.kind, put_ids=put_ids)

        def as_jpeg(src, dest):
            shutil.copy2(str(src), str(dest))
            return 1200, 1500

        def rebuild(run):
            self.rebuilds += 1
            return [{"step": "design/build.py", "ok": True, "said": ""}, {"step": "design/check.py", "ok": True, "said": ""}]

        def no_share(*a, **k):
            raise AssertionError("git was reached: %r" % (a,))
        for obj, name, value in ((OP, "_drive", lambda: (types.SimpleNamespace(), fake_reach)),
                                 (OP, "as_jpeg", as_jpeg), (OP, "rebuild", rebuild),
                                 (TP, "OUTCOME_ROOT", self.tmp / "plane"),
                                 (prepare, "STAMPS", self.tmp / "stamps.json"), (ask, "share", no_share)):
            p = mock.patch.object(obj, name, value)
            p.start()
            self.addCleanup(p.stop)

    # ---- the fakes
    def lister(self, parts):
        rows = self.drive.get(tuple(parts))
        return None if rows is None else [dict(r) for r in rows]

    def mover(self, file_id, to_parts, by, why=None, **k):
        """LD-89 (tracked Drive moves)'s move() at its fixed seam: one parent out, one in, a record written."""
        self.moves.append({"id": file_id, "to": list(to_parts), "by": by, "why": why, "k": k})
        for parts, rows in self.drive.items():
            hit = next((r for r in rows if r["id"] == file_id), None)
            if hit:
                rows.remove(hit)
                self.drive.setdefault(tuple(to_parts), []).append(hit)
                rec = self.tmp / "platform" / "data" / "records" / "drive-move" / (
                    "20261023T070000Z--%s--%s.json" % (by.lower(), file_id))
                rec.parent.mkdir(parents=True, exist_ok=True)
                rec.write_text(json.dumps({"drive_id": file_id, "why": why}) + "\n")
                return {"drive_id": file_id, "name": hit["name"], "from": "Shared Assets/" + "/".join(parts),
                        "to": "Shared Assets/" + "/".join(to_parts), "record": str(rec)}
        raise AssertionError("moved a file the fake Drive doesn't have: %s" % file_id)

    def refuse(self, file_id, to_parts, by, why=None, **k):
        self.moves.append({"id": file_id})
        raise RuntimeError("a file with more than one parent")

    def fetcher(self, fid, tmp):
        self.fetched.append(fid)
        f = Path(tmp) / ("drive-" + fid)
        f.write_bytes(JPEG + fid.encode())
        return f

    def take(self, made_with="Higgsfield", alt="a jar on a sink in morning light", **k):
        k.setdefault("mover", self.mover)
        with contextlib.redirect_stdout(self.out):
            return OP.take_newest(self.run, "P1", alt, "the team", made_with, lister=self.lister, fetcher=self.fetcher,
                                  outcome_root=self.tmp / "plane", **k)

    def picture(self):
        return json.loads(self.spec.read_text())["sections"][1]["picture"]

    def outcomes(self):
        d = self.tmp / "plane" / "platform" / "data" / "records" / "model-outcome"
        return [json.loads(f.read_text()) for f in sorted(d.glob("*.json"))] if d.is_dir() else []

    def names(self, parts=EVE):
        return [r["name"] for r in self.drive.get(tuple(parts), [])]


class TestNewest(Base):
    def test_1_newest_over_older_and_subfolder_files(self):
        got = OP.newest(list(EVE), lister=self.lister)
        self.assertEqual(got, {"id": "id-new", "name": "new.png", "modified": "2026-10-23T05:00:00.000Z",
                               "folder": "Shared Assets/" + "/".join(EVE)})       # not notes.txt, not deep.jpg
        self.drive[EVE + ("nov-brief",)][0]["modified"] = "2026-10-23T08:00:00.000Z"      # one level down counts
        got = OP.newest(list(EVE), lister=self.lister)
        self.assertEqual((got["id"], got["folder"]), ("id-sub", "Shared Assets/" + "/".join(EVE) + "/nov-brief"))
        self.assertIsNone(OP.newest(["handoffs", "graphic-designer", BRAND, "nobody", "returned"], lister=self.lister))
        self.drive[("handoffs", "graphic-designer", BRAND, "empty", "returned")] = [{"id": "x", "name": "a.txt", "modified": "z"}]
        self.assertIsNone(OP.newest(["handoffs", "graphic-designer", BRAND, "empty", "returned"], lister=self.lister))


class TestTake(Base):
    def test_2_moved_once_into_the_run_media_and_gone_from_her_folder(self):
        r = self.take()
        self.assertEqual(len(self.moves), 1)
        self.assertEqual(self.moves[0], {"id": "id-new", "to": MEDIA, "by": "the team",
                                         "why": LABEL + " P1: use my newest", "k": {}})
        self.assertNotIn("new.png", self.names())                                           # gone from her folder
        self.assertNotEqual(OP.newest(list(EVE), lister=self.lister)["id"], "id-new")
        self.assertIn("new.png", self.names(MEDIA))
        self.assertEqual(self.fetched, ["id-new"])                                          # read back by id
        self.assertTrue(Path(r["moved"]["record"]).is_file())
        self.assertEqual(r["moved"]["to"], "Shared Assets/" + "/".join(MEDIA))
        line = OP.moved_line(r)
        self.assertIn("to Shared Assets/" + "/".join(MEDIA), line)
        self.assertIn(r["moved"]["record"], line)
        self.assertEqual(self.rebuilds, 1)
        self.assertEqual(self.puts[0][1], MEDIA)                                            # the email copy, same folder
        self.assertTrue((self.run / "media" / Path(r["file"]).name).read_bytes().endswith(b"id-new"))

    def test_3_both_refs_and_made_with(self):
        r = self.take()
        p = self.picture()
        self.assertEqual(p["original"], {"drive_id": "id-new", "label": "Shared Assets/%s/new.png" % "/".join(MEDIA)})
        self.assertEqual(r["original"], p["original"])
        name = Path(p["photo"].split("run:", 1)[1]).name
        self.assertEqual(p["email_copy"], {"drive_id": "id-copy-1", "label": "Shared Assets/%s/%s" % ("/".join(MEDIA), name)})
        self.assertEqual(p["drive_id"], "id-copy-1")                                        # unchanged for old readers
        self.assertEqual((p["made_with"], p["source"], p["alt"], p["by"]),
                         ("Higgsfield", "made", "a jar on a sink in morning light", "the team"))
        self.assertFalse(any(str(v).startswith(("/private", "/var/", "/Users/", "/tmp")) for v in
                             (p["original"]["label"], p["email_copy"]["label"], p["photo"])))
        self.drive[EVE].append({"id": "id-cam", "name": "cam.heic", "modified": "2026-10-23T07:00:00.000Z"})
        r = self.take(made_with="a real photo")
        p = self.picture()
        self.assertEqual((p["made_with"], p["source"], p["original"]["drive_id"]), ("a real photo", "photo", "id-cam"))
        self.assertEqual(json.loads(Path(r["outcome"]).read_text())["verdict"]["model"], "real photo")

    def test_4_refusals_come_before_the_move(self):
        before = self.spec.read_bytes()
        for mw in ("", "   ", None):
            with self.assertRaises(SystemExit) as c:
                self.take(made_with=mw)
            self.assertEqual(str(c.exception), QUESTION)
        with self.assertRaises(SystemExit) as c:
            self.take(alt="to make: a jar")
        self.assertIn("alt text", str(c.exception))
        self.assertEqual(self.moves, [])
        with self.assertRaises(SystemExit) as c:
            self.take(mover=self.refuse)
        self.assertIn("new.png was not moved (a file with more than one parent)", str(c.exception))
        self.assertIn("new.png", self.names())
        self.assertEqual((self.spec.read_bytes(), self.fetched, self.outcomes(), self.rebuilds), (before, [], [], 0))
        self.drive[EVE] = []
        with self.assertRaises(SystemExit) as c:
            self.take()
        self.assertIn("no picture in Shared Assets/%s/" % "/".join(EVE), str(c.exception))

    def test_5_one_model_outcome_record(self):
        r = self.take()
        recs = self.outcomes()
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(r["outcome"], str(sorted((self.tmp / "plane").rglob("*.json"))[0]))
        self.assertEqual((rec["schema"], rec["kind"], rec["reviewer"], rec["via"]),
                         (1, "model-outcome", "eve", "email-production/own_picture"))
        self.assertRegex(rec["item"], r"^%s-P1-own-\d{8}T\d{6}Z$" % LABEL)
        self.assertEqual(rec["verdict"], {"model": "Higgsfield", "door": "own", "purpose": "email-story", "brand": BRAND,
                                          "judge": "not judged", "picked": True, "tries_before_pick": None,
                                          "cost": "not on record"})
        kind = json.loads((REPO / "platform" / "data" / "kinds" / "model-outcome.json").read_text())
        self.assertEqual(list(rec["verdict"]), [f["key"] for f in kind["verdict_fields"]])

    def test_6_history_appends_never_rewrites(self):
        self.take()
        first = self.picture()
        self.assertEqual(len(first["history"]), 1)
        self.assertEqual(first["history"][0]["was"]["photo"], "run:media/pic.png")
        self.take()                                                         # nov-brief/sub.jpg is the newest now
        second = self.picture()
        self.assertEqual(len(second["history"]), 2)
        self.assertEqual(second["history"][0], first["history"][0])                          # untouched
        self.assertEqual(second["history"][1]["was"]["original"], first["original"])         # the refs travel with it
        self.assertEqual(second["original"]["drive_id"], "id-sub")
        back = self.run / "media" / Path(first["photo"].split("run:", 1)[1]).name             # undo = place it back
        self.assertNotEqual(second["photo"], first["photo"])                                 # same second: not overwritten
        self.assertTrue(back.read_bytes().endswith(b"id-new"))
        with contextlib.redirect_stdout(self.out):
            OP.place(self.run, "P1", str(back), first["alt"], "the team", first["made_with"], "own", None, False)
        third = self.picture()
        self.assertEqual(third["history"][:2], second["history"])
        self.assertEqual(len(third["history"]), 3)
        self.assertEqual(len(self.outcomes()), 2)


class TestAsk(Base):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(ask, "REPO", self.tmp)
        p.start()
        self.addCleanup(p.stop)
        real = OP.take_newest

        def take_newest(run, code, alt, by, made_with, **k):          # her ask, on the fake Drive
            return real(run, code, alt, by, made_with, lister=self.lister, mover=self.mover, fetcher=self.fetcher, **k)
        p = mock.patch.object(OP, "take_newest", take_newest)
        p.start()
        self.addCleanup(p.stop)

    def line(self, rest, where="[%s/%s, section 1, picture 0]" % (BRAND, LABEL)):
        return "Email request (x): nov-99 P1 %s · %s" % (where, rest)

    def test_7_parse(self):
        k, why = ask.parse(self.line("use my newest (made with Higgsfield): a jar in morning light"))[0]
        self.assertIsNone(why)
        self.assertEqual((k["action"], k["made_with"], k["note"], k["section"], k["picture"]),
                         ("newest", "Higgsfield", "a jar in morning light", 1, 0))
        k, why = ask.parse(self.line("use my newest"))[0]
        self.assertEqual((why, k["action"], k.get("made_with"), k.get("note")), (None, "newest", None, None))
        got = ask.parse(self.line("use my newest", where="[%s/%s, section 1]" % (BRAND, LABEL)))
        self.assertEqual(got[0], (None, "nov-99 P1: no picture named"))

    def test_7b_the_reply_names_where_it_went_and_commits_both_records(self):
        shared = []
        f = self.tmp / "asked.txt"
        f.write_text(self.line("use my newest (made with Higgsfield): a jar in morning light") + "\n")
        with mock.patch.object(ask, "share", lambda paths, msg: shared.append(paths) or "shared"), \
                contextlib.redirect_stdout(self.out):
            code = ask.main([str(f)])
        said = self.out.getvalue()
        self.assertEqual(code, 0, said)
        self.assertIn("✓ nov-99 P1 · newest: a jar in morning light — new.png (newest in Shared Assets/%s) as P1; "
                      "new.png moved from Shared Assets/%s to " % ("/".join(EVE), "/".join(EVE)), said)
        self.assertIn("to Shared Assets/" + "/".join(MEDIA), said)
        self.assertIn("platform/data/records/drive-move/20261023T070000Z--graphic-designer--id-new.json", said)
        self.assertEqual(len(self.moves), 1)
        self.assertEqual(len(shared), 1)
        self.assertIn("runs/email-production/%s/%s" % (BRAND, LABEL), shared[0])
        self.assertIn("platform/data/records/drive-move/20261023T070000Z--graphic-designer--id-new.json", shared[0])
        self.assertEqual(len([p for p in shared[0] if p.startswith("plane/platform/data/records/model-outcome/")]), 1)

    def test_7c_no_made_with_is_asked_back_and_nothing_moves(self):
        f = self.tmp / "asked.txt"
        f.write_text(self.line("use my newest: a jar in morning light") + "\n")
        with contextlib.redirect_stdout(self.out):
            code = ask.main([str(f)])
        self.assertEqual(code, 1)
        self.assertIn(QUESTION, self.out.getvalue())
        self.assertEqual(self.moves, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
