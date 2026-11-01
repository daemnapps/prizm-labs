"""LD-60 (manifest reads Drive): the writing manifest and the elements lock read "is it banked?" the same way.

Found 2026-10-21 by the lead's mini dry run vp-grandma-dbmik-dry-20261021: on the mini the manifest said MISSING
(a person, a product) because their pictures are git-ignored, while the lock, which reads the Drive, would have
passed them. In a worker spawn (DRIVE_MOUNT=off) sheet() now counts a file the Drive LISTS by key: a runs/ folder's
twin through reach.list_tree, a product packshot through brands/<brand>/products/DRIVE-INDEX.json. Listing only,
nothing downloaded, nothing written. A person's own run still never asks the Drive (LD-28's rule). No network.

    cd tools/video-production/machine && /usr/bin/python3 -m unittest test_ld60_listed
"""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import elements_check as ec
from test_ld28_element_fetch import FakeReach, FakeBrandfiles, person_files, brief, tree_of

HERE = Path(__file__).resolve().parent
_sp = importlib.util.spec_from_file_location("ld60_manifest", HERE.parents[1] / "video-writing" / "machine" / "manifest.py")
M = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(M)

DOC = {"piece": {"product": "scrub"},
       "cast": [{"id": "LEAD", "bank_id": "lead"}], "world": [],
       "scenes": [{"id": "S1", "who": "LEAD", "speaker": "LEAD", "to_camera": True, "voice": "hello there",
                   "looks": {"LEAD": "look-1"}, "product": True, "kind": "card"}]}
TEXT_ONLY = ("character.md", "looks.json", "voice.json", "provenance.json")   # what git carries for a person


class Listed(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ld60-"))
        (self.root / "components").mkdir()
        b = self.root / "brands" / "_b"
        (b / "products" / "scrub").mkdir(parents=True)
        (b / "brand.md").write_text("# b")
        (b / "products" / "scrub" / "product.md").write_text("# scrub")
        (b / "products" / "scrub" / "provenance.json").write_text(json.dumps({
            "element": "scrub", "kind": "product", "rights": "r", "made_with": {"m": 1}, "drive": "d",
            "real_references": [{"file": "images/packshot-front.jpg", "kind": "real packshot", "from": "studio"}]}))
        self.index = {"files": [{"drive_id": "ID-PACK", "folder": "scrub", "kind": "packshot",
                                 "drive_path": "brands/_b/products/scrub/packshot/front.jpg",
                                 "old_path": "products/scrub/images/packshot-front.jpg"}]}
        # the person as a checkout has them: the text files only; the pictures are git-ignored
        self.lead = self.root / "runs" / "ai-elements" / "_b" / "casting" / "lead"
        self.lead.mkdir(parents=True)
        for rel, data in person_files("lead").items():
            if rel in TEXT_ONLY:
                (self.lead / rel).write_bytes(data)
        self.saved = (ec._workspace, ec.REACH, ec.BRANDFILES, os.environ.get("DRIVE_MOUNT"), M.EC)
        ec._workspace = lambda: self.root
        ec.BRANDFILES = FakeBrandfiles(forbid=True)      # the listing path never asks brandfiles
        M.EC = ec
        getattr(ec, "_TWINS", {}).clear(); del getattr(ec, "_NO_DRIVE", [])[:]

    def tearDown(self):
        ec._workspace, ec.REACH, ec.BRANDFILES, dm, M.EC = self.saved
        getattr(ec, "_TWINS", {}).clear(); del getattr(ec, "_NO_DRIVE", [])[:]
        if dm is None:
            os.environ.pop("DRIVE_MOUNT", None)
        else:
            os.environ["DRIVE_MOUNT"] = dm
        shutil.rmtree(self.root, ignore_errors=True)

    def on_drive(self, person=True, index=True):
        ec.REACH = FakeReach({"Shared Assets/runs/ai-elements/_b/casting/lead": person_files("lead")} if person else {})
        f = self.root / "brands" / "_b" / "products" / "DRIVE-INDEX.json"
        if index:
            f.write_text(json.dumps(self.index))
        elif f.exists():
            f.unlink()

    def status(self, body):
        return {i["kind"]: i["status"] for i in body["items"]}

    def test_listed_on_the_drive_is_banked_in_the_manifest_and_the_lock_alike(self):
        os.environ["DRIVE_MOUNT"] = "off"
        self.on_drive()
        before = tree_of(self.root)
        body = ec.sheet(brief(DOC), "_b")
        self.assertEqual(self.status(body), {"person": "banked", "product": "banked"},
                         [(i["id"], i["missing"]) for i in body["items"]])
        rows = M.elements_rows(brief(DOC), "_b")
        self.assertTrue(all(r["ok"] for r in rows), rows)
        # listing only: nothing fetched, nothing written, nothing asked of brands/ on the Drive
        self.assertEqual(tree_of(self.root), before)
        self.assertFalse([c for c in ec.REACH.calls if c[0] in ("get", "readable")], ec.REACH.calls)
        self.assertFalse([c for c in ec.REACH.calls if c[0] == "list_tree" and c[1][:1] == ["brands"]])
        # one listing per folder, however many doors ask
        lists = [c for c in ec.REACH.calls if c[0] == "list_tree"]
        self.assertEqual(len(lists), len({tuple(c[1]) for c in lists}), lists)

    def test_not_on_the_drive_is_missing_in_both(self):
        os.environ["DRIVE_MOUNT"] = "off"
        self.on_drive(person=False, index=False)
        body = ec.sheet(brief(DOC), "_b")
        self.assertEqual(self.status(body), {"person": "to make", "product": "to make"})
        rows = {r["what"].split(" · ")[0]: r["ok"] for r in M.elements_rows(brief(DOC), "_b")}
        self.assertEqual(rows, {"person": False, "product": False})

    def test_a_persons_own_run_never_asks_the_drive(self):
        os.environ.pop("DRIVE_MOUNT", None)
        self.on_drive()
        ec.REACH = FakeReach({"Shared Assets/runs/ai-elements/_b/casting/lead": person_files("lead")}, forbid=True)
        body = ec.sheet(brief(DOC), "_b")
        self.assertEqual(self.status(body)["person"], "to make")
        self.assertFalse(all(r["ok"] for r in M.elements_rows(brief(DOC), "_b")))
        self.assertEqual(ec.REACH.calls, [])

    def test_drive_true_asks_even_off_the_worker(self):
        os.environ.pop("DRIVE_MOUNT", None)
        self.on_drive()
        self.assertEqual(self.status(ec.sheet(brief(DOC), "_b", drive=True)), {"person": "banked", "product": "banked"})

    def test_no_drive_at_all_is_said_once_and_refused(self):
        os.environ["DRIVE_MOUNT"] = "off"
        self.on_drive(index=False)

        class NoDrive(FakeReach):
            def list_tree(self, parts, **kw):
                self._call("list_tree", list(parts))
                raise SystemExit("THE PACKAGE IS MISSING")
        ec.REACH = NoDrive()
        body = ec.sheet(brief(DOC), "_b")
        self.assertEqual(self.status(body)["person"], "to make")
        self.assertEqual(len([c for c in ec.REACH.calls if c[0] == "list_tree"]), 1)


if __name__ == "__main__":
    unittest.main()
