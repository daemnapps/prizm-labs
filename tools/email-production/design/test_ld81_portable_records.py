#!/usr/bin/env python3
"""LD-81 (portable picture records): a picture record stores its picture and references as LD-79 (Drive ref
resolver) refs, and remake() reads them back through refs.local(); one that cannot be read is named, never dropped,
and the person is offered "remake from the brief instead?" — proven offline.

    python3 tools/email-production/design/test_ld81_portable_records.py     (from outside email-production:
                                                                                   its email.py shadows the stdlib's)

The Drive is a fake: refs.put and refs.local patched to one dict that serves bytes by id (and, for what mirror()
put, by label). The other Mac is a CLEAN run folder — its record.json and nothing in media/. The picture-edit tool
is a fake that checks what it is handed. No key, no network, no Google package. Stdlib only, 3.9.

  1  keep() on the maker's Mac: the picture's file_ref comes from media/drive.json (no put); every reference is a
     ref — an in-repo file its repo-relative path, a run media/ file put under the run's media/, anything else put
     under references/<hash>/ — and nothing in record.json is an absolute path
  2  remake() on a clean run: the picture is fetched by its id, every reference by its id, the fake edit runs with
     all of them (none dropped), the new picture is put on the run's Drive media/ and the new record holds refs only
  3  an old record holding /private/tmp references: CannotRemake naming each one, carrying the offer, nothing made
  4  no reference is dropped without being named: readable, machine-path and never-stored mixed -> the two unreadable
     ones are named, the readable one is not
  5  the picture itself unreadable (no file here, nothing on the Drive) -> CannotRemake naming it; no record -> the offer
  6  sync.py apply: CannotRemake's reason and offer are the call's result; a call with from_brief takes the brief path
     and never asks the record; ask.py's apply_one passes from_brief through
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))      # design/ FIRST; never tools/email-production (its email.py shadows the stdlib's)
import look as L                   # noqa: E402
import picture_record as PR        # noqa: E402

L.reach()                          # gdrive-creator on the path, as picture_record finds it
from gdrive_creator import reach as RCH, refs  # noqa: E402

REPO = Path(L.REPO)
BRAND = "zz-brand"
LABEL = "zz-brand-nov-99"
PIC = "zz-brand-nov-99-pabc12345-01.png"
GONE = "/private/tmp/ld81-not-on-this-mac"
ABS = re.compile(r'"(/private/|/var/folders|/Users/|/Volumes/|/tmp/)')


class Drive:
    """One fake Drive behind refs.put and refs.local: bytes by id, and by label for what is there with no id."""

    def __init__(self, cache):
        self.cache, self.by_id, self.by_label, self.puts, self.reads = cache, {}, {}, [], []

    def put(self, local, label):
        local = Path(str(local))
        fid = "id-%d" % (len(self.by_id) + 1)
        self.by_id[fid] = local.read_bytes()
        self.puts.append((local, label))
        return {"drive_id": fid, "label": "%s/%s" % (label, local.name), "bytes": local.stat().st_size}

    def local(self, ref):
        self.reads.append(ref)
        if isinstance(ref, dict):
            if ref.get("drive_id"):
                if ref["drive_id"] not in self.by_id:
                    raise RCH.NoDrive("%s: no such file id" % ref["drive_id"])
                data = self.by_id[ref["drive_id"]]
            elif ref.get("label") in self.by_label:
                data = self.by_label[ref["label"]]
            else:
                raise RCH.NoDrive("%s: not on the Drive" % ref.get("label"))
            out = self.cache / ref["label"].split("Shared Assets/", 1)[1]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            return out
        if os.path.isabs(ref):
            if os.path.exists(ref):
                return Path(ref)
            raise refs.Unportable(ref)
        p = REPO / ref
        if not p.exists():
            raise FileNotFoundError(ref)
        return p


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(os.path.realpath(t.name))
        self.drive = Drive(self.tmp / "cache")
        for name in ("put", "local"):
            p = mock.patch.object(refs, name, getattr(self.drive, name))
            p.start()
            self.addCleanup(p.stop)
        self.edits = []

        def edit(req):
            self.edits.append(dict(req))
            out = Path(req["out"])
            out.mkdir(parents=True, exist_ok=True)
            (out / "edited.png").write_bytes(b"edited:" + Path(req["picture"]).read_bytes())
            return {"delivered": [{"file": str(out / "edited.png")}], "instruction": "one change", "model": "fake-edit",
                    "out": req["out"]}
        p = mock.patch.dict(sys.modules, {"image_edit": types.SimpleNamespace(edit=edit)})
        p.start()
        self.addCleanup(p.stop)
        self.assertFalse(Path(GONE).exists())

    def run_dir(self, where):
        d = self.tmp / where / "runs" / "email-production" / BRAND / LABEL
        (d / "media").mkdir(parents=True)
        return d

    def quiet(self, fn, *a, **k):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*a, **k)

    def clean_copy(self, record):
        """The other Mac: the same run label, its record.json, nothing in media/ but the records."""
        clean = self.run_dir("other-mac")
        f = clean / "media" / "records" / record["label"] / "record.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps(record))
        self.assertEqual([x for x in (clean / "media").iterdir() if x.is_file()], [])
        return clean, str(f.relative_to(clean))


class TestKeep(Base):
    def made(self):
        """The maker's Mac: the picture in media/, the image engine's drive.json naming its id, a pin, and a product
        photo outside the run."""
        run = self.run_dir("maker")
        pic = run / "media" / PIC
        pic.write_bytes(b"picture")
        (run / "media" / "drive.json").write_text(json.dumps({
            "schema": 1, "folder": "Shared Assets/runs/image-production/%s/zz-label" % BRAND, "folder_id": "f1",
            "route": "api", "files": [{"path": PIC, "id": "id-engine", "kind": "image"}]}))
        self.drive.by_id["id-engine"] = b"picture"
        pin = run / "media" / "pins" / "pabc" / "pin1.jpg"
        pin.parent.mkdir(parents=True)
        pin.write_bytes(b"pin")
        product = self.tmp / "maker-home" / "products" / "jar" / "packshot" / "front.png"
        product.parent.mkdir(parents=True)
        product.write_bytes(b"product")
        inrepo = HERE / "brand-a.svg"                        # a tracked file under the repo, given as an absolute path
        req = {"purpose": "email-story", "direction": "a jar on a sink",
               "references": [str(product), str(inrepo), "tools/email-production/design/fonts.css"],
               "inspiration": [str(pin)]}
        rel = self.quiet(PR.keep, run, "zz-brand-nov-99-pabc12345", 0, req, made=pic)
        return run, rel, product, pin

    def test_1_keep_writes_refs_never_an_absolute_path(self):
        run, rel, product, pin = self.made()
        text = (run / rel).read_text()
        self.assertIsNone(ABS.search(text), text)
        rec = json.loads(text)
        self.assertEqual(rec["file"], "media/" + PIC)
        self.assertEqual(rec["file_ref"], {"drive_id": "id-engine", "bytes": 7,
                                           "label": "Shared Assets/runs/image-production/%s/zz-label/%s" % (BRAND, PIC)})
        by = {Path(r["path"]).name: r for r in rec["references"]}
        self.assertEqual(sorted(by), ["brand-a.svg", "fonts.css", "front.png", "pin1.jpg"])
        self.assertEqual(by["brand-a.svg"]["ref"], "tools/email-production/design/brand-a.svg")
        self.assertEqual(by["fonts.css"]["ref"], "tools/email-production/design/fonts.css")
        folder = "Shared Assets/runs/email-production/%s/%s" % (BRAND, LABEL)
        self.assertEqual(by["pin1.jpg"]["ref"]["label"], folder + "/media/pins/pabc/pin1.jpg")
        self.assertTrue(by["front.png"]["ref"]["label"].startswith(folder + "/references/"))
        for r in rec["references"]:
            self.assertTrue(refs.is_ref(r["ref"]), r)
            self.assertEqual(r["path"], r["ref"]["label"] if isinstance(r["ref"], dict) else r["ref"])
        self.assertEqual(by["front.png"]["kind"], "real product photo")
        self.assertEqual(by["pin1.jpg"]["kind"], "Pinterest pin (mood only)")
        self.assertEqual(sorted(p.name for p, _ in self.drive.puts), ["front.png", "pin1.jpg"])   # the picture: drive.json

    def test_1b_a_reference_that_cannot_be_placed_is_named_not_a_path(self):
        run = self.run_dir("maker")
        pic = run / "media" / PIC
        pic.write_bytes(b"picture")
        product = self.tmp / "maker-home" / "front.png"
        product.parent.mkdir(parents=True)
        product.write_bytes(b"product")

        def no_drive(local, label):
            raise RCH.NoDrive("%s: not placed — no route" % local)
        with mock.patch.object(refs, "put", no_drive):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rel = PR.keep(run, "zz-brand-nov-99-pabc12345", 0, {"references": [str(product)]}, made=pic)
        text = (run / rel).read_text()
        self.assertIsNone(ABS.search(text), text)
        rec = json.loads(text)
        self.assertIsNone(rec["file_ref"])
        self.assertEqual(rec["references"], [{"path": "front.png", "ref": None, "kind": "brand asset", "not_stored": "NoDrive"}])
        self.assertIn("NOT stored on the Drive — front.png: NoDrive", out.getvalue())


class TestRemake(Base):
    def test_2_a_mirrored_picture_is_fetched_by_id_and_edited_on_a_clean_run(self):
        run, rel, product, pin = TestKeep.made(self)
        rec = json.loads((run / rel).read_text())
        clean, rel2 = self.clean_copy(rec)
        self.drive.reads.clear()
        new = self.quiet(PR.remake, BRAND, clean, {"photo": "run:media/" + PIC, "record": rel2}, "warmer light", 0)
        self.assertEqual(len(self.edits), 1)
        req = self.edits[0]
        self.assertEqual(Path(req["picture"]).read_bytes(), b"picture")              # fetched by its id
        self.assertIn({"drive_id": "id-engine", "bytes": 7, "label": rec["file_ref"]["label"]}, self.drive.reads)
        got = sorted(Path(p).read_bytes() for p in req["references"])
        self.assertEqual(len(req["references"]), 3)                                 # every non-pin reference, none dropped
        self.assertIn(b"product", got)
        self.assertNotIn(b"pin", got)
        self.assertEqual(req["change"], "warmer light")
        made = clean / new["photo"].split("run:", 1)[1]
        self.assertEqual(made.read_bytes(), b"edited:picture")
        self.assertEqual(self.drive.puts[-1], (made, "Shared Assets/runs/email-production/%s/%s/media" % (BRAND, LABEL)))
        text = (clean / new["record"]).read_text()
        self.assertIsNone(ABS.search(text), text)
        out = json.loads(text)
        self.assertEqual(out["parent"], rel2)
        self.assertEqual(out["file_ref"]["drive_id"], "id-%d" % len(self.drive.by_id))
        self.assertEqual(out["references"][0], {"path": rec["file_ref"]["label"], "ref": rec["file_ref"],
                                                "kind": "earlier version of this picture"})
        self.assertEqual(len(out["references"]), 4)
        for r in out["references"]:
            self.assertTrue(refs.is_ref(r["ref"]), r)

    def legacy(self, refs_, file_ref=None):
        rec = {"label": "zz-brand-nov-99-pabc12345", "file": "media/" + PIC, "purpose": "email-story",
               "references": refs_}
        if file_ref:
            rec["file_ref"] = file_ref
        return self.clean_copy(rec)

    def mirrored(self):
        """What mirror() (LD-75 (design pictures to Drive)) put: the picture under the run's Drive media/, by label."""
        self.drive.by_label["Shared Assets/runs/email-production/%s/%s/media/%s" % (BRAND, LABEL, PIC)] = b"picture"

    def test_3_an_old_record_with_private_tmp_references_gets_the_offer(self):
        self.mirrored()
        a, b = GONE + "/products/jar/packshot/front.png", GONE + "/cast/ana.png"
        clean, rel = self.legacy([{"path": a, "kind": "real product photo"}, {"path": b, "kind": "brand cast"},
                                  {"path": GONE + "/media/pins/p1/pin.jpg", "kind": "Pinterest pin (mood only)"}])
        with self.assertRaises(PR.CannotRemake) as c:
            self.quiet(PR.remake, BRAND, clean, {"photo": "run:media/" + PIC, "record": rel}, "warmer light", 0)
        e = c.exception
        self.assertIsInstance(e, RuntimeError)                                     # old callers' except still holds
        self.assertEqual(e.offer, "remake from the brief instead?")
        self.assertEqual(len(e.missing), 2)
        self.assertTrue(e.missing[0].startswith(a + ": "), e.missing)
        self.assertTrue(e.missing[1].startswith(b + ": "), e.missing)
        self.assertIn("machine path", e.missing[0])
        msg = str(e)
        self.assertIn("remake from the brief instead?", msg)
        self.assertIn("front.png", msg)
        self.assertIn("ana.png", msg)
        self.assertLess(msg.index("remake from the brief instead?"), msg.index("front.png"))   # the offer survives a cut
        self.assertEqual(self.edits, [])
        self.assertEqual(sorted(x.name for x in (clean / "media" / "records").iterdir()), ["zz-brand-nov-99-pabc12345"])

    def test_4_no_reference_is_dropped_without_being_named(self):
        self.mirrored()
        self.drive.by_id["id-ok"] = b"product"
        ok = {"drive_id": "id-ok", "label": "Shared Assets/runs/x/ok.png", "bytes": 7}
        clean, rel = self.legacy([
            {"path": ok["label"], "ref": ok, "kind": "real product photo"},
            {"path": GONE + "/gone.png", "kind": "brand asset"},
            {"path": "never.png", "ref": None, "kind": "brand asset", "not_stored": "NoDrive"}])
        with self.assertRaises(PR.CannotRemake) as c:
            self.quiet(PR.remake, BRAND, clean, {"photo": "run:media/" + PIC, "record": rel}, "warmer light", 0)
        m = c.exception.missing
        self.assertEqual(len(m), 2, m)
        self.assertTrue(m[0].startswith(GONE + "/gone.png: "), m)
        self.assertEqual(m[1], "never.png: never stored on the Drive (NoDrive)")
        self.assertFalse(any("ok.png" in x for x in m))
        self.assertEqual(self.edits, [])

    def test_5_the_picture_itself_unreadable_or_no_record_gets_the_offer(self):
        clean, rel = self.legacy([])                                               # nothing on the fake Drive
        with self.assertRaises(PR.CannotRemake) as c:
            self.quiet(PR.remake, BRAND, clean, {"photo": "run:media/" + PIC, "record": rel}, "warmer light", 0)
        self.assertEqual(len(c.exception.missing), 1)
        self.assertIn("the picture itself", c.exception.missing[0])
        self.assertIn(PIC, c.exception.missing[0])
        with self.assertRaises(PR.CannotRemake) as c:
            self.quiet(PR.remake, BRAND, clean, {"photo": "run:media/" + PIC, "record": "media/records/nope/record.json"},
                       "warmer light", 0)
        self.assertIn("remake from the brief instead?", str(c.exception))
        self.assertEqual(self.edits, [])


class TestAdapter(Base):
    def setUp(self):
        super().setUp()
        sys.path.append(str(HERE.parent / "adapter"))
        import sync as S
        self.S = S
        self.runs = self.tmp / "runs" / "email-production"
        self.run = self.runs / BRAND / LABEL
        (self.run / "design").mkdir(parents=True)
        (self.run / "media" / "records" / "zz-old").mkdir(parents=True)
        (self.run / "media" / "records" / "zz-old" / "record.json").write_text(json.dumps(
            {"label": "zz-old", "file": "media/" + PIC, "references": [{"path": GONE + "/front.png", "kind": "brand asset"}]}))
        self.spec = self.run / "design" / "email.json"
        self.spec.write_text(json.dumps({"sections": [{"s": "picture", "photo": "run:media/" + PIC, "alt": "a jar",
                                                       "brief": "on a sink", "record": "media/records/zz-old/record.json"}]}))
        self.drive.by_label["Shared Assets/runs/email-production/%s/%s/media/%s" % (BRAND, LABEL, PIC)] = b"p"
        p = mock.patch.dict(sys.modules, {"image_production": types.SimpleNamespace()})   # never the real engine
        p.start()
        self.addCleanup(p.stop)
        for name, value in (("RUNS", self.runs), ("_ak", lambda: None), ("_rebuild", lambda run: None),
                            ("_learn", lambda *a, **k: None)):
            p = mock.patch.object(S, name, value)
            p.start()
            self.addCleanup(p.stop)

    def call(self, **k):
        c = {"id": "c1", "at": "2026-10-22T00:00:00+00:00", "brand": BRAND, "label": LABEL, "action": "picture",
             "section": 0, "picture": 0, "note": "warmer light", "by": "the team"}
        c.update(k)
        return self.quiet(self.S.apply, [c])[0]

    def test_6a_cannot_remake_comes_back_as_the_result_with_the_offer(self):
        got = self.call()
        self.assertEqual(got["state"], "failed")
        self.assertIn("can't be remade from its record", got["result"])
        self.assertIn("remake from the brief instead?", got["result"])
        self.assertIn("front.png", got["result"])
        self.assertEqual(self.edits, [])
        self.assertEqual(json.loads(self.spec.read_text())["sections"][0]["photo"], "run:media/" + PIC)   # nothing ran

    def test_6b_from_brief_takes_the_brief_path_and_never_asks_the_record(self):
        made = []
        line = types.SimpleNamespace(make_pictures=lambda b, run, lk: made.append((b, run)), L=types.SimpleNamespace(load=lambda b: {}))

        def remake(*a, **k):
            raise AssertionError("the record was asked")
        with mock.patch.dict(sys.modules, {"line": line}), mock.patch.object(PR, "remake", remake):
            got = self.call(from_brief=True)
        self.assertEqual(got["state"], "applied", got)
        self.assertEqual(made, [(BRAND, self.run)])
        sec = json.loads(self.spec.read_text())["sections"][0]
        self.assertEqual(sec, {"todo": "a jar. CHANGE: warmer light", "brief": "on a sink", "use": "story"})

    def test_6c_ask_passes_from_brief_through(self):
        import ask as A
        seen = []

        def run(cmd, **k):
            seen.extend(json.loads(Path(cmd[-1]).read_text()))
            return types.SimpleNamespace(stdout=json.dumps([{"state": "applied", "result": "done"}]), stderr="")
        with mock.patch.object(A.subprocess, "run", run):
            ok, _ = A.apply_one({"brand": BRAND, "label": LABEL, "action": "picture", "by": "the team", "section": 0,
                                 "picture": 0, "note": "warmer light", "from_brief": True})
        self.assertTrue(ok)
        self.assertIs(seen[0]["from_brief"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
