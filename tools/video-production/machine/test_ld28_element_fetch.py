"""LD-28 (element fetch): a mini run of video-production gets its elements from
the Drive. Only in a worker spawn (DRIVE_MOUNT=off, LD-26 (mount switch)) the
elements lock fetches each runs/ai-elements/ folder's missing files from the
Drive mirror, counts the product's Drive packshot and Drive-held references,
and carries the owner's confirm from the brief's own folder. A person's own run
never touches the Drive. No network: a fake Drive behind the module seams."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import elements_check as ec

JPG = b"\xff\xd8\xff\xe0fake"
LOCAL = b"\xff\xd8\xff\xe0this machine's own"


def brief(doc: dict) -> str:
    return "# a brief\n\n```json\n" + json.dumps(doc) + "\n```\n"


def person_files(pid: str) -> dict:
    """Every file a banked person holds, {relative path: bytes}."""
    f = {"character.md": b"# x", "master.jpg": JPG, "reference/real.jpg": JPG,
         "looks.json": json.dumps({"looks": {"look-1": {"outfit": "o"}}}).encode(),
         "voice.json": json.dumps({"voice_id": "v-" + pid}).encode(),
         "provenance.json": json.dumps({
             "element": pid, "kind": "person", "rights": "r", "made_with": {"m": 1}, "drive": "d",
             "real_references": [{"file": "reference/real.jpg", "kind": "real photo", "from": "x"}]}).encode()}
    for s in ("turnaround", "angles-expressions", "details", "light-test", "colour-key", "look-1"):
        f["sheets/%s.jpg" % s] = JPG
    return f


def bank_set(root: Path, sid: str):
    h = root / "runs" / "ai-elements" / "_b" / "sets" / sid
    (h / "plates").mkdir(parents=True)
    (h / "reference").mkdir()
    (h / "set.md").write_text("# s")
    for p in ("wide", "angle-a", "angle-b"):
        (h / "plates" / ("%s.jpg" % p)).write_bytes(JPG)
    (h / "reference" / "real.jpg").write_bytes(JPG)
    (h / "provenance.json").write_text(json.dumps({
        "element": sid, "kind": "setting", "rights": "r", "made_with": {"m": 1}, "drive": "d",
        "real_references": [{"file": "reference/real.jpg", "kind": "real photo", "from": "x"}]}))


DOC = {"piece": {}, "cast": [{"id": "LEAD", "bank_id": "lead"}],
       "world": [{"id": "ROOM", "bank_id": "room"}],
       "scenes": [{"id": "S1", "who": "LEAD", "speaker": "LEAD", "to_camera": True, "voice": "hello there",
                   "looks": {"LEAD": "look-1"}, "setting_id": "ROOM"}]}

PDOC = {"piece": {"product": "scrub"}, "cast": [], "world": [],
        "scenes": [{"id": "S1", "kind": "card", "to_camera": False, "product": True}]}


class FakeReach(object):
    """The Drive, as {"Shared Assets/<folder>": {relative path: bytes}} and a
    set of labels that read. `forbid` = any call is a test failure."""

    def __init__(self, tree=None, reads=(), forbid=False):
        self.tree, self.reads, self.forbid, self.calls = tree or {}, set(reads), forbid, []

    def _call(self, *a):
        self.calls.append(a)
        if self.forbid:
            raise AssertionError("the Drive was asked: %r" % (a,))

    def list_tree(self, parts, **kw):
        self._call("list_tree", list(parts))
        files = self.tree.get("Shared Assets/" + "/".join(parts))
        return None if files is None else [(k, "id-" + k) for k in sorted(files)]

    def get(self, parts, name, dest_dir, **kw):
        self._call("get", list(parts), name)
        for label, files in self.tree.items():
            for rel, data in files.items():
                if "Shared Assets/" + "/".join(list(parts) + [name]) == label + "/" + rel:
                    Path(dest_dir).mkdir(parents=True, exist_ok=True)
                    out = Path(dest_dir) / name
                    out.write_bytes(data)
                    return out
        return None

    def readable(self, path, **kw):
        self._call("readable", str(path))
        if str(path) in self.reads:
            return Path(str(path))
        raise Exception("NoDrive: %s" % path)


class FakeBrandfiles(object):
    def __init__(self, shot=None, forbid=False):
        self.shot, self.forbid, self.calls = shot, forbid, []

    def packshot_of(self, brand, product, fetch=False):
        self.calls.append((brand, product, fetch))
        if self.forbid:
            raise AssertionError("brandfiles was asked: %r" % ((brand, product, fetch),))
        return (self.shot, "the fake Drive's packshot") if self.shot else (None, "none on the fake Drive")


def tree_of(p: Path) -> dict:
    return {str(f.relative_to(p)): f.read_bytes() for f in sorted(p.rglob("*")) if f.is_file()} if p.is_dir() else {}


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ld28-"))
        (self.root / "components").mkdir(); (self.root / "brands" / "_b").mkdir(parents=True)
        (self.root / "brands" / "_b" / "brand.md").write_text("# b")
        self.saved = (ec._workspace, ec.REACH, ec.BRANDFILES, os.environ.get("DRIVE_MOUNT"))
        ec._workspace = lambda: self.root
        self.outside = Path(tempfile.mkdtemp(prefix="ld28-out-"))
        self.run = self.root / "runs" / "video-production" / "_b" / "r1"
        self.run.mkdir(parents=True)
        # the confirm-carry tests prove the MANUAL lock; reused elements auto-confirm by default
        # since 2026-10-19 (the owner) — proven in test_elements_lock.ReusedApproveThemselves
        self.prev_auto = os.environ.get("VP_REUSED_AUTO")
        os.environ["VP_REUSED_AUTO"] = "0"

    def tearDown(self):
        if self.prev_auto is None:
            os.environ.pop("VP_REUSED_AUTO", None)
        else:
            os.environ["VP_REUSED_AUTO"] = self.prev_auto
        ec._workspace, ec.REACH, ec.BRANDFILES, dm = self.saved
        if dm is None:
            os.environ.pop("DRIVE_MOUNT", None)
        else:
            os.environ["DRIVE_MOUNT"] = dm
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.outside, ignore_errors=True)

    def worker(self, on=True):
        if on:
            os.environ["DRIVE_MOUNT"] = "off"
        else:
            os.environ.pop("DRIVE_MOUNT", None)


class PersonFetch(Base):
    """(a) a person folder with only character.md here, the rest on the Drive."""

    def setUp(self):
        Base.setUp(self)
        bank_set(self.root, "room")
        self.lead = self.root / "runs" / "ai-elements" / "_b" / "casting" / "lead"
        self.lead.mkdir(parents=True)
        (self.lead / "character.md").write_bytes(LOCAL)
        drive = person_files("lead")
        # the wall: a Drive name that walks out of the folder into brands/
        drive["../../../../../brands/_b/evil.txt"] = b"never"
        self.fake = FakeReach({"Shared Assets/runs/ai-elements/_b/casting/lead": drive})
        ec.REACH = self.fake
        ec.BRANDFILES = FakeBrandfiles(forbid=True)

    def test_worker_fetches_the_missing_files_and_the_person_is_banked(self):
        self.worker()
        brands_before = tree_of(self.root / "brands")
        fails, notes = ec.gate(self.run, brief(DOC), "_b", dry_run=False)
        for rel in person_files("lead"):
            self.assertTrue((self.lead / rel).is_file(), rel)
        self.assertEqual((self.lead / "master.jpg").read_bytes(), JPG)
        # a file that was here is never overwritten
        self.assertEqual((self.lead / "character.md").read_bytes(), LOCAL)
        self.assertFalse(any(c[0] == "get" and c[2] == "character.md" for c in self.fake.calls))
        # nothing written under brands/
        self.assertEqual(tree_of(self.root / "brands"), brands_before)
        self.assertFalse((self.root / "brands" / "_b" / "evil.txt").exists())
        self.assertTrue(any("not fetched" in n and "evil.txt" in n for n in notes), notes)
        # the person is banked; what is left is the owner's confirm
        body = json.loads((self.run / "elements.json").read_text())
        self.assertEqual(body["to_make"], [], body["to_make"])
        self.assertEqual({i["id"]: i["status"] for i in body["items"]}, {"LEAD": "banked", "ROOM": "banked"})
        self.assertEqual(len(fails), 1)
        self.assertIn("not confirmed", fails[0])
        self.assertTrue(any("fetched 11 file(s)" in n for n in notes), notes)
        # the set was asked for too, and nothing under brands/ ever was
        self.assertIn(["runs", "ai-elements", "_b", "sets", "room"],
                      [c[1] for c in self.fake.calls if c[0] == "list_tree"])
        self.assertFalse(any(c[1][:1] == ["brands"] for c in self.fake.calls if c[0] in ("list_tree", "get")))

    def test_a_folder_the_drive_does_not_have_is_refused_as_today(self):
        self.worker()
        ec.REACH = FakeReach({})
        fails, _ = ec.gate(self.run, brief(DOC), "_b", dry_run=False)
        self.assertTrue(any(f.startswith("person LEAD is not banked") for f in fails), fails)
        self.assertEqual(sorted(p.name for p in self.lead.iterdir()), ["character.md"])

    def test_no_drive_at_all_is_said_and_refused_never_skipped(self):
        self.worker()

        class NoDrive(FakeReach):
            def list_tree(self, parts, **kw):
                self._call("list_tree", list(parts))
                raise SystemExit("THE PACKAGE IS MISSING")
        ec.REACH = NoDrive()
        fails, notes = ec.gate(self.run, brief(DOC), "_b", dry_run=False)
        self.assertEqual(len([c for c in ec.REACH.calls if c[0] == "list_tree"]), 1)
        self.assertTrue(any(n.startswith("no Drive here") and "PACKAGE IS MISSING" in n for n in notes), notes)
        self.assertTrue(any(f.startswith("person LEAD is not banked") for f in fails), fails)


class PersonsOwnRun(PersonFetch):
    """(b) DRIVE_MOUNT unset: no Drive call at all — the fakes raise if asked."""

    def test_no_drive_call_and_refused_as_today(self):
        self.worker(on=False)
        ec.REACH = FakeReach({"Shared Assets/runs/ai-elements/_b/casting/lead": person_files("lead")},
                             forbid=True)
        before = tree_of(self.root / "runs" / "ai-elements")
        fails, notes = ec.gate(self.run, brief(DOC), "_b", dry_run=False, brief_dir=self.root)
        self.assertEqual(ec.REACH.calls, [])
        self.assertEqual(ec.BRANDFILES.calls, [])
        self.assertEqual(notes, [])
        self.assertEqual(tree_of(self.root / "runs" / "ai-elements"), before)
        self.assertTrue(any(f.startswith("person LEAD is not banked") for f in fails), fails)

    def test_dry_run_too(self):
        self.worker(on=False)
        ec.REACH = FakeReach(forbid=True)
        fails, notes = ec.gate(self.run, brief(DOC), "_b", dry_run=True)
        self.assertEqual((fails, ec.REACH.calls), ([], []))
        self.assertTrue(notes and all(n.startswith("(dry run) ") for n in notes), notes)

    # the inherited worker tests do not apply to a person's own run
    test_worker_fetches_the_missing_files_and_the_person_is_banked = None
    test_a_folder_the_drive_does_not_have_is_refused_as_today = None
    test_no_drive_at_all_is_said_and_refused_never_skipped = None


class Product(Base):
    """(c) the product: images/ absent here, the packshot through brandfiles,
    a reference read on the Drive by its drive_path."""

    def setUp(self):
        Base.setUp(self)
        self.prod = self.root / "brands" / "_b" / "products" / "scrub"
        self.prod.mkdir(parents=True)
        (self.prod / "product.md").write_text("# scrub")
        self.prov({"file": "images/packshot-front.png", "kind": "real packshot", "from": "studio",
                   "drive_path": "brands/_b/products/scrub/packshot/packshot-front.png"})
        self.shot = self.outside / "packshot.png"
        self.shot.write_bytes(JPG)
        ec.REACH = FakeReach(reads={"Shared Assets/brands/_b/products/scrub/packshot/packshot-front.png"})
        ec.BRANDFILES = FakeBrandfiles(shot=self.shot)

    def prov(self, *refs):
        (self.prod / "provenance.json").write_text(json.dumps({
            "element": "scrub", "kind": "product", "rights": "r", "made_with": {"m": 1}, "drive": "d",
            "real_references": list(refs)}))

    def item(self):
        body = json.loads((self.run / "elements.json").read_text())
        return next(i for i in body["items"] if i["kind"] == "product")

    def test_drive_packshot_and_readable_reference_bank_the_product(self):
        self.worker()
        before = tree_of(self.root / "brands")
        ec.gate(self.run, brief(PDOC), "_b", dry_run=False)
        it = self.item()
        self.assertEqual((it["status"], it["missing"]), ("banked", []))
        self.assertIn(("_b", "scrub", True), ec.BRANDFILES.calls)
        self.assertIn(("readable", "Shared Assets/brands/_b/products/scrub/packshot/packshot-front.png"),
                      ec.REACH.calls)
        self.assertFalse((self.prod / "images").exists())
        self.assertEqual(tree_of(self.root / "brands"), before)
        self.assertFalse(any(c[0] in ("list_tree", "get") for c in ec.REACH.calls))

    def test_a_reference_with_no_drive_path_is_the_named_gap(self):
        self.worker()
        self.prov({"file": "images/packshot-back.png", "kind": "real packshot", "from": "studio"})
        ec.gate(self.run, brief(PDOC), "_b", dry_run=False)
        it = self.item()
        self.assertEqual(it["status"], "to make")
        self.assertIn("reference images/packshot-back.png is named but not in the folder and has no drive_path",
                      it["missing"])

    def test_a_drive_path_that_does_not_read_is_a_gap(self):
        self.worker()
        ec.REACH = FakeReach()
        ec.gate(self.run, brief(PDOC), "_b", dry_run=False)
        it = self.item()
        self.assertEqual(it["status"], "to make")
        self.assertTrue(any("images/packshot-front.png" in m and "does not read" in m for m in it["missing"]),
                        it["missing"])

    def test_no_drive_packshot_stays_missing(self):
        self.worker()
        ec.BRANDFILES = FakeBrandfiles(shot=None)
        ec.gate(self.run, brief(PDOC), "_b", dry_run=False)
        it = self.item()
        self.assertTrue(any(m.startswith("real packshot") and "not on the Drive either" in m
                            for m in it["missing"]), it["missing"])

    def test_a_persons_own_run_checks_the_product_here_only(self):
        self.worker(on=False)
        ec.REACH = FakeReach(forbid=True)
        ec.BRANDFILES = FakeBrandfiles(forbid=True)
        ec.gate(self.run, brief(PDOC), "_b", dry_run=False)
        it = self.item()
        self.assertEqual(it["status"], "to make")
        self.assertTrue(any(m.startswith("real packshot") for m in it["missing"]), it["missing"])
        self.assertIn("reference images/packshot-front.png is named but not in the folder", it["missing"])
        self.assertEqual((ec.REACH.calls, ec.BRANDFILES.calls), ([], []))


class ConfirmCarries(Base):
    """(d) the owner's confirm from the brief's own folder."""

    def setUp(self):
        Base.setUp(self)
        bank_set(self.root, "room")
        lead = self.root / "runs" / "ai-elements" / "_b" / "casting" / "lead"
        for rel, data in person_files("lead").items():
            (lead / rel).parent.mkdir(parents=True, exist_ok=True)
            (lead / rel).write_bytes(data)
        self.bdir = self.root / "runs" / "video-writing" / "_b" / "three"
        self.bdir.mkdir(parents=True)
        ec.REACH = FakeReach({})
        ec.BRANDFILES = FakeBrandfiles(forbid=True)
        self.fp = ec.sheet(brief(DOC), "_b")["fingerprint"]

    def confirm_in_brief(self, fp):
        (self.bdir / "elements-lock.json").write_text(json.dumps(
            {"fingerprint": fp, "by": "the owner", "at": "2026-10-19T12:00:00", "items": ["person LEAD"]}))

    def test_an_equal_fingerprint_carries(self):
        self.worker()
        self.confirm_in_brief(self.fp)
        fails, notes = ec.gate(self.run, brief(DOC), "_b", dry_run=False, brief_dir=self.bdir)
        self.assertEqual(fails, [])
        self.assertFalse(any("not confirmed" in n for n in notes), notes)
        lock = json.loads((self.run / "elements-lock.json").read_text())
        self.assertEqual(lock["carried_from"], "runs/video-writing/_b/three")
        self.assertEqual((lock["fingerprint"], lock["by"]), (self.fp, "the owner"))
        # the owner's own lock is untouched
        self.assertNotIn("carried_from", json.loads((self.bdir / "elements-lock.json").read_text()))

    def test_a_different_fingerprint_is_refused_as_today(self):
        self.worker()
        self.confirm_in_brief("0000000000000000")
        fails, _ = ec.gate(self.run, brief(DOC), "_b", dry_run=False, brief_dir=self.bdir)
        self.assertEqual(len(fails), 1)
        self.assertTrue(fails[0].startswith("the elements are banked but not confirmed — "), fails)
        self.assertFalse((self.run / "elements-lock.json").exists())

    def test_no_brief_dir_is_refused_as_today(self):
        self.worker()
        self.confirm_in_brief(self.fp)
        fails, _ = ec.gate(self.run, brief(DOC), "_b", dry_run=False)
        self.assertTrue(any("not confirmed" in f for f in fails), fails)
        self.assertFalse((self.run / "elements-lock.json").exists())

    def test_a_persons_own_run_never_carries(self):
        self.worker(on=False)
        ec.REACH = FakeReach(forbid=True)
        self.confirm_in_brief(self.fp)
        fails, _ = ec.gate(self.run, brief(DOC), "_b", dry_run=False, brief_dir=self.bdir)
        self.assertTrue(any("not confirmed" in f for f in fails), fails)
        self.assertFalse((self.run / "elements-lock.json").exists())
        self.assertEqual(ec.REACH.calls, [])

    def test_a_run_lock_already_there_is_never_overwritten(self):
        self.worker()
        self.confirm_in_brief(self.fp)
        (self.run / "elements-lock.json").write_text(json.dumps({"fingerprint": "old", "by": "the owner"}))
        fails, _ = ec.gate(self.run, brief(DOC), "_b", dry_run=False, brief_dir=self.bdir)
        self.assertTrue(any("changed since the last confirm" in f for f in fails), fails)
        self.assertEqual(json.loads((self.run / "elements-lock.json").read_text())["fingerprint"], "old")


if __name__ == "__main__":
    unittest.main()
