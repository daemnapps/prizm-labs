"""The elements lock and the real-reference rule (2026-09-23).

Every element a brief names is banked to elements-standard.json, documented,
made from a real reference, and confirmed — or production refuses by name.
No network: a fake workspace in a temp folder."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import elements_check as ec
import make_character as mc

JPG = b"\xff\xd8\xff\xe0fake"


def brief(doc: dict) -> str:
    return "# a brief\n\n```json\n" + json.dumps(doc) + "\n```\n"


def bank_person(root: Path, pid: str, looks=("look-1",), voice=True, prov_kind="real photo"):
    h = root / "runs" / "ai-elements" / "_b" / "casting" / pid
    (h / "sheets").mkdir(parents=True)
    (h / "reference").mkdir()
    (h / "character.md").write_text("# x")
    (h / "master.jpg").write_bytes(JPG)
    for s in ("turnaround", "angles-expressions", "details", "light-test", "colour-key"):
        (h / "sheets" / f"{s}.jpg").write_bytes(JPG)
    for lk in looks:
        (h / "sheets" / f"{lk}.jpg").write_bytes(JPG)
    (h / "looks.json").write_text(json.dumps({"looks": {lk: {"outfit": "o"} for lk in looks}}))
    (h / "reference" / "real.jpg").write_bytes(JPG)
    (h / "provenance.json").write_text(json.dumps({
        "element": pid, "kind": "person", "rights": "r", "made_with": {"m": 1}, "drive": "d",
        "real_references": [{"file": "reference/real.jpg", "kind": prov_kind, "from": "somewhere real"}]}))
    if voice:
        (h / "voice.json").write_text(json.dumps({"voice_id": f"v-{pid}"}))
    return h


def bank_set(root: Path, sid: str):
    h = root / "runs" / "ai-elements" / "_b" / "sets" / sid
    (h / "plates").mkdir(parents=True)
    (h / "reference").mkdir()
    (h / "set.md").write_text("# s")
    for p in ("wide", "angle-a", "angle-b"):
        (h / "plates" / f"{p}.jpg").write_bytes(JPG)
    (h / "reference" / "real.jpg").write_bytes(JPG)
    (h / "provenance.json").write_text(json.dumps({
        "element": sid, "kind": "setting", "rights": "r", "made_with": {"m": 1}, "drive": "d",
        "real_references": [{"file": "reference/real.jpg", "kind": "real photo", "from": "x"}]}))


DOC = {"piece": {}, "cast": [{"id": "LEAD", "bank_id": "lead"}, {"id": "DOC", "bank_id": "doc"}],
       "world": [{"id": "ROOM", "bank_id": "room"}],
       "scenes": [{"id": "S1", "who": "LEAD", "speaker": "LEAD", "to_camera": True, "voice": "hello there",
                   "looks": {"LEAD": "look-1"}, "setting_id": "ROOM"},
                  {"id": "S2", "who": "DOC and LEAD", "speaker": "DOC", "to_camera": True, "voice": "and so",
                   "looks": {"LEAD": "look-1", "DOC": "look-1"}, "setting_id": "ROOM"}]}


class ElementsLock(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="el-"))
        (self.root / "components").mkdir(); (self.root / "brands").mkdir()
        self.saved = ec._workspace
        ec._workspace = lambda: self.root
        bank_person(self.root, "lead"); bank_person(self.root, "doc"); bank_set(self.root, "room")

    def tearDown(self):
        ec._workspace = self.saved
        shutil.rmtree(self.root, ignore_errors=True)

    def sheet(self, doc=DOC):
        return ec.sheet(brief(doc), "_b", root=self.root)

    def test_everything_banked_passes(self):
        s = self.sheet()
        self.assertEqual(s["to_make"], [], s["to_make"])
        self.assertEqual(s["brief_gaps"], [])

    def test_a_second_speaker_without_a_voice_is_to_make(self):
        (self.root / "runs/ai-elements/_b/casting/doc/voice.json").unlink()
        miss = {i["id"]: i["missing"] for i in self.sheet()["to_make"]}
        self.assertIn("DOC", miss)
        self.assertTrue(any("voice of their own" in m and "S2" in m for m in miss["DOC"]))

    def test_a_scene_with_words_and_no_speaker_is_a_brief_gap(self):
        doc = json.loads(json.dumps(DOC)); doc["scenes"][1].pop("speaker")
        self.assertTrue(any("S2" in g and "speaker" in g for g in self.sheet(doc)["brief_gaps"]))

    def test_a_look_not_on_the_sheet_is_to_make(self):
        doc = json.loads(json.dumps(DOC)); doc["scenes"][0]["looks"]["LEAD"] = "look-9"
        miss = {i["id"]: i["missing"] for i in self.sheet(doc)["to_make"]}
        self.assertTrue(any("look-9" in m for m in miss["LEAD"]))

    def test_a_reference_that_is_not_real_fails(self):
        shutil.rmtree(self.root / "runs/ai-elements/_b/casting/doc")
        bank_person(self.root, "doc", prov_kind="approved production frame")
        miss = {i["id"]: i["missing"] for i in self.sheet()["to_make"]}
        self.assertTrue(any("not a real source" in m for m in miss["DOC"]))

    def test_an_undocumented_element_fails(self):
        (self.root / "runs/ai-elements/_b/sets/room/provenance.json").unlink()
        ids = [i["id"] for i in self.sheet()["to_make"]]
        self.assertIn("ROOM", ids)

    def test_gate_refuses_until_confirmed_and_again_after_a_change(self):
        run = self.root / "run"; run.mkdir()
        fails, _ = ec.gate(run, brief(DOC), "_b", dry_run=False)
        self.assertTrue(any("not confirmed" in f for f in fails))
        ec.confirm(run, "the owner")
        fails, _ = ec.gate(run, brief(DOC), "_b", dry_run=False)
        self.assertEqual(fails, [])
        (self.root / "runs/ai-elements/_b/casting/lead/master.jpg").write_bytes(JPG + b"changed")
        fails, _ = ec.gate(run, brief(DOC), "_b", dry_run=False)
        self.assertTrue(any("changed since" in f for f in fails))

    def test_a_dry_run_refuses_nothing(self):
        run = self.root / "run"; run.mkdir()
        fails, notes = ec.gate(run, brief(DOC), "_b", dry_run=True)
        self.assertEqual(fails, [])
        self.assertTrue(notes)

    def test_confirm_refuses_while_something_is_to_make(self):
        run = self.root / "run"; run.mkdir()
        (self.root / "runs/ai-elements/_b/casting/doc/voice.json").unlink()
        ec.gate(run, brief(DOC), "_b", dry_run=False)
        with self.assertRaises(SystemExit):
            ec.confirm(run, "the owner")


class RealReferenceFirst(unittest.TestCase):
    def test_no_real_reference_and_no_adjustments_is_refused(self):
        gaps = mc.refuse({"id": "x", "brand": "b", "who": "w", "base": "b", "details": "d",
                          "looks": {"l": {"outfit": "o"}}, "character": {"title": "t"}}, Path("/"))
        self.assertTrue(any("no real reference" in g for g in gaps))
        self.assertTrue(any("no adjustments" in g for g in gaps))

    def test_a_generated_picture_is_not_a_real_reference(self):
        tmp = Path(tempfile.mkdtemp()); (tmp / "a.jpg").write_bytes(JPG)
        gaps = mc.refuse({"id": "x", "brand": "b", "who": "w", "base": "b", "details": "d",
                          "looks": {"l": {"outfit": "o"}}, "character": {"title": "t"},
                          "adjustments": ["hair"],
                          "real_references": [{"file": "a.jpg", "kind": "ai render", "from": "x"}]}, tmp)
        self.assertTrue(any("not a real source" in g for g in gaps))
        shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()


class StoryPeople(ElementsLock):
    def test_a_new_person_in_a_story_role_is_refused(self):
        a = self.root / "brands/_b/ai-cast/casting"; a.mkdir(parents=True)
        (a / "authority.json").write_text(json.dumps({"_story_roles": {"granny": ["grandmother", "who makes it"]}, "people": []}))
        doc = json.loads(json.dumps(DOC))
        doc["cast"].append({"id": "MARISOL", "bank_id": "NEW", "identity_block": "the woman who makes it, a grandmother in her kitchen"})
        doc["scenes"][1]["who"] = "DOC and LEAD and MARISOL"
        miss = {i["id"]: i["missing"] for i in self.sheet(doc)["to_make"]}
        self.assertTrue(any("story person `granny`" in m for m in miss["MARISOL"]))


class NoProductInCastSheets(unittest.TestCase):
    def test_a_product_in_a_cast_sheet_is_refused(self):
        tmp = Path(tempfile.mkdtemp()); (tmp / "a.jpg").write_bytes(JPG)
        gaps = mc.refuse({"id": "x", "brand": "b", "who": "w", "base": "a cream silk blouse",
                          "details": "her hand holding a skincare tube",
                          "looks": {"l": {"outfit": "cream top"}}, "character": {"title": "t"},
                          "adjustments": ["hair"],
                          "real_references": [{"file": "a.jpg", "kind": "real photo", "from": "x"}]}, tmp)
        self.assertTrue(any("tube" in g for g in gaps))
        self.assertFalse(any("cream" in g for g in gaps))   # a colour is not a product
        shutil.rmtree(tmp)
