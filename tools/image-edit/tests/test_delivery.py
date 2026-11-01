"""delivery — checking every role's hand-off returned/ folders, matching each to its brief, bringing it in, the card.

Every test builds a throwaway workspace under `tempfile`, points AI_WORKSPACE at it, and hands the check a fake Drive
(a listing and bytes by id). No network, no key, nothing written outside `tempfile`.

    python3 tools/image-edit/tests/test_delivery.py
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
import delivery as DL  # noqa: E402

BRAND = "testbrand"
KEY = "testbrand_widget_brief-0325"


class FakeDrive:
    """What the real Drive.list gives back is only returned/ paths; this one hands back the package files too, so the
    check's own filter is tested."""

    def __init__(self, listing):
        self.listing = listing          # None = the folder is not there
        self.got, self.listed = [], []

    def list(self, label, returned="returned"):
        self.listed.append(label)
        return None if self.listing is None else list(self.listing)

    def get(self, fid, dest):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b"file " + fid.encode())
        self.got.append(fid)
        return str(dest)


def register(rows):
    B = DL.briefs()
    return {"briefs": B.Briefs(rows)}


ROWS = {
    KEY: {"brief": "brief-0325", "brand": BRAND, "product": "widget", "avatar": "spot-hider", "run": "testbrand-run-325"},
    "testbrand_widget_brief-0007": {"brief": "brief-0007", "brand": BRAND, "product": "widget", "run": "run-w7"},
    "testbrand_gadget_brief-0007": {"brief": "brief-0007", "brand": BRAND, "product": "gadget", "run": "run-g7"},
    "otherbrand_thing_brief-0400": {"brief": "brief-0400", "brand": "otherbrand", "product": "thing", "run": "run-o"},
}
CFG = {"state": "awaiting-steph", "note": "the team confirms the hand-off folders.", "folder": "handoffs/{role}/{brand}",
       "drive_root": "Shared Assets", "repo_root": "runs", "returned": "returned",
       "roles": {"graphic-designer": {"filled_by": "Pic", "delivers": "pictures", "lane": "image"},
                 "video-editor": {"filled_by": "Vid", "delivers": "videos", "lane": "video"}}}
GD = "graphic-designer"


class DeliveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "brands" / BRAND).mkdir(parents=True)
        (self.tmp / "components").mkdir()
        self.old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.tmp)
        self.reg = register(ROWS)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_check(self, listing, dry_run=False, role=GD):
        d = FakeDrive(listing)
        self.res = DL.check(BRAND, role, dry_run=dry_run, drive=d, reg=self.reg, cfg=CFG)
        return self.res["roles"][0], d

    def home(self, role=GD):
        return self.tmp / "runs/handoffs" / role / BRAND

    # ---------------------------------------------------------------- the folders: by role, the same words both sides
    def test_folders_by_role_same_words_on_drive_and_repo(self):
        self.assertEqual(DL.place(GD, BRAND, CFG), ("Shared Assets/runs/handoffs/graphic-designer/testbrand", False))
        self.assertEqual(DL.legacy_places(GD, BRAND, CFG), ["Shared Assets/handoffs/graphic-designer/testbrand"])
        self.assertEqual(DL.returned_folder(GD, BRAND, KEY, CFG),
                         f"Shared Assets/runs/handoffs/graphic-designer/testbrand/{KEY}/returned")
        self.assertEqual(DL.repo_folder(GD, BRAND, CFG), self.home())
        with self.assertRaises(DL.Refused):
            DL.role("nobody", CFG)

    def test_the_real_setting_names_roles_not_people(self):
        cfg = DL.setting()
        self.assertIn("{role}", cfg["folder"])
        self.assertIn("{brand}", cfg["folder"])
        lanes = {r["delivers"]: r["lane"] for r in cfg["roles"].values()}
        self.assertEqual(lanes, {"pictures": "image", "videos": "video"})
        self.assertNotIn("status", cfg)                               # rule 5: anything but draft/approved is `state`
        if cfg.get("state") != "confirmed":
            self.assertIn("the team", cfg["note"])
        people = [r.get("filled_by") for r in cfg["roles"].values() if r.get("filled_by")]
        src = (HERE / "delivery.py").read_text()
        for name in people:                                           # who fills a role lives only in the setting
            self.assertIsNone(re.search(r"\b%s\b" % re.escape(name), src), name)

    # ---------------------------------------------------------------- matching
    def test_the_folder_name_decides_the_brief(self):
        ok = lambda n: DL.brief_of(self.reg, BRAND, n)[:2]           # noqa: E731
        self.assertEqual(ok(KEY), ("ok", KEY))
        self.assertEqual(ok("Brief 0325 grandma"), ("ok", KEY))
        self.assertEqual(ok("P325"), ("ok", KEY))                     # the old code
        self.assertEqual(ok("gadget brief-0007"), ("ok", "testbrand_gadget_brief-0007"))
        self.assertIn("more than one", DL.brief_of(self.reg, BRAND, "brief-0007")[2])
        self.assertIn("another brand's", DL.brief_of(self.reg, BRAND, "otherbrand_thing_brief-0400")[2])
        self.assertIn("not a brief", DL.brief_of(self.reg, BRAND, "brief-0999")[2])
        self.assertIn("no brief ID", DL.brief_of(self.reg, BRAND, "final ones")[2])
        self.assertIsNone(DL.brief_tag("1080p100")[0])

    # ---------------------------------------------------------------- bringing it in
    def test_only_returned_is_read_and_lands_at_the_same_path(self):
        res, d = self.run_check([(f"{KEY}/prompts/01.md", "pk1"), (f"{KEY}/pictures/ref.png", "pk2"),
                                 (f"{KEY}/returned/{KEY}-v1.png", "f1"), (f"{KEY}/returned/b/{KEY}-v2.jpg", "f2"),
                                 (f"{KEY}/returned/notes.txt", "n1")])
        self.assertEqual([(n["key"], n["count"]) for n in res["new"]], [(KEY, 2)])
        self.assertEqual(sorted(d.got), ["f1", "f2"])                 # the package around returned/ is never read
        self.assertEqual(res["other"], [f"{KEY}/returned/notes.txt"])
        back = self.home() / KEY / "returned"
        self.assertTrue((back / f"{KEY}-v1.png").is_file() and (back / "b" / f"{KEY}-v2.jpg").is_file())
        self.assertEqual(res["new"][0]["folder"], f"runs/handoffs/graphic-designer/testbrand/{KEY}/returned")
        rec = json.loads((self.home() / KEY / "delivery.json").read_text())
        self.assertEqual((rec["role"], rec["lane"], rec["brief"]), (GD, "image", "brief-0325"))
        for f in rec["files"]:
            self.assertFalse(f["file"].startswith("/"), "a stored path is repo-relative, never a machine path")
            self.assertTrue(f["label"].startswith(f"Shared Assets/runs/handoffs/graphic-designer/testbrand/{KEY}/returned/"))

    def test_second_check_shows_only_whats_new(self):
        self.run_check([(f"{KEY}/returned/a.png", "f1")])
        res, d = self.run_check([(f"{KEY}/returned/a.png", "f1"), (f"{KEY}/returned/b.png", "f2")])
        self.assertEqual((res["already"], res["new"][0]["files"], d.got), (1, [f"{KEY}/returned/b.png"], ["f2"]))
        res, _ = self.run_check([(f"{KEY}/returned/a.png", "f1"), (f"{KEY}/returned/b.png", "f2")])
        self.assertEqual((res["new"], res["already"]), ([], 2))
        self.assertIn("nothing new", DL.say(self.res))

    def test_what_the_hand_off_road_took_back_is_already_in(self):
        back = self.home("video-editor") / KEY / "returned"
        back.mkdir(parents=True)
        (back / "here.mp4").write_bytes(b"x")
        (back / "index.json").write_text(json.dumps({"files": [{"file": "indexed.mp4"}]}))
        res, d = self.run_check([(f"{KEY}/returned/here.mp4", "v1"), (f"{KEY}/returned/indexed.mp4", "v2"),
                                 (f"{KEY}/returned/fresh.mp4", "v3")], role="video-editor")
        self.assertEqual((res["already"], d.got), (2, ["v3"]))

    def test_not_a_brief_asked_again_until_renamed(self):
        res, _ = self.run_check([("final ones/returned/a.png", "f9")])
        self.assertTrue(res["untagged"][0]["new"])
        res, _ = self.run_check([("final ones/returned/a.png", "f9")])
        self.assertFalse(res["untagged"][0]["new"])
        res, _ = self.run_check([(f"{KEY}/returned/a.png", "f9")])     # the folder renamed: same Drive id
        self.assertEqual((res["new"][0]["key"], res["untagged"]), (KEY, []))

    def test_dry_run_writes_nothing(self):
        res, d = self.run_check([(f"{KEY}/returned/a.png", "f1")], dry_run=True)
        self.assertEqual((res["new"][0]["count"], d.got), (1, []))
        self.assertFalse((self.tmp / "runs").exists())
        self.assertIn("Dry run", DL.say(self.res))

    def test_missing_folder_said_plainly(self):
        res, d = self.run_check(None)
        self.assertFalse(res["found"])
        self.assertEqual(d.listed, ["Shared Assets/runs/handoffs/graphic-designer/testbrand",   # the new place first
                                    "Shared Assets/handoffs/graphic-designer/testbrand"])       # the legacy place last
        self.assertIn("no hand-off folder on the Drive yet", DL.say(self.res))
        self.assertIn("not confirmed yet", DL.say(self.res))

    def test_every_role_in_one_check_named_by_role(self):
        d = FakeDrive([(f"{KEY}/returned/a.png", "f1"), (f"{KEY}/returned/a.mp4", "v1")])
        res = DL.check(BRAND, drive=d, reg=self.reg, cfg=CFG)
        self.assertEqual([(o["role"], o["new"][0]["count"]) for o in res["roles"]], [(GD, 1), ("video-editor", 1)])
        said = DL.say(res)
        self.assertIn("the graphic designer (Pic today)", said)
        self.assertIn("the video editor (Vid today)", said)

    # ---------------------------------------------------------------- one place back (2026-10-28)
    def test_repo_returned_is_read_first_and_recorded_without_a_drive_id(self):
        back = self.home() / KEY / "returned"
        back.mkdir(parents=True)
        (back / f"{KEY}-v1.png").write_bytes(b"x")
        res, d = self.run_check([])
        self.assertEqual([(n["key"], n["count"]) for n in res["new"]], [(KEY, 1)])
        self.assertEqual(d.got, [])                                    # nothing read from the Drive for it
        rec = json.loads((self.home() / KEY / "delivery.json").read_text())
        self.assertEqual([(f["name"], f["drive_id"]) for f in rec["files"]], [(f"{KEY}-v1.png", None)])
        self.assertFalse(rec["files"][0]["file"].startswith("/"))
        res, _ = self.run_check([])
        self.assertEqual(res["new"], [])                               # recorded once, never twice

    def test_legacy_place_is_read_last_and_one_drive_id_is_read_once(self):
        class TwoPlaces(FakeDrive):
            def list(self, label, returned="returned"):
                self.listed.append(label)
                if "/runs/" in label:
                    return [(f"{KEY}/returned/a.png", "f1")]
                return [(f"{KEY}/returned/a.png", "f1"), (f"{KEY}/returned/old.png", "f2")]
        d = TwoPlaces(None)
        res = DL.check(BRAND, GD, drive=d, reg=self.reg, cfg=CFG)["roles"][0]
        self.assertEqual(d.listed[0], "Shared Assets/runs/handoffs/graphic-designer/testbrand")
        self.assertEqual(sorted(d.got), ["f1", "f2"])                  # f1 once, though both places list it
        self.assertEqual(res["legacy"], ["Shared Assets/handoffs/graphic-designer/testbrand"])
        labels = {f["drive_id"]: f["label"] for f in json.loads((self.home() / KEY / "delivery.json").read_text())["files"]}
        self.assertTrue(labels["f1"].startswith("Shared Assets/runs/handoffs/"))
        self.assertTrue(labels["f2"].startswith("Shared Assets/handoffs/"))
        self.assertIn("OLD place", DL.say({"roles": [res], "dry_run": False}))

    def test_folder_matches_its_brief_by_number_and_brand_in_either_product_spelling(self):
        reg = register({"testbrand_flex_brief-0076": {"brief": "brief-0076", "brand": BRAND, "product": "flex"},
                        "testbrand_crush_brief-0076": {"brief": "brief-0076", "brand": BRAND, "product": "crush"}})
        self.assertEqual(DL.brief_of(reg, BRAND, "testbrand_flex-face-brush_brief-0076")[:2], ("ok", "testbrand_flex_brief-0076"))
        reg = register({"testbrand_flex-face-brush_brief-0076": {"brief": "brief-0076", "brand": BRAND, "product": "flex-face-brush"},
                        "testbrand_crush_brief-0076": {"brief": "brief-0076", "brand": BRAND, "product": "crush"}})
        self.assertEqual(DL.brief_of(reg, BRAND, "testbrand_flex_brief-0076")[:2], ("ok", "testbrand_flex-face-brush_brief-0076"))

    def test_a_check_rebuilds_the_hand_off_index(self):
        self.run_check([(f"{KEY}/returned/a.png", "f1")])
        idx = json.loads((self.tmp / "runs/handoffs/index.json").read_text())
        row = next(r for r in idx["rows"] if r["brief_key"] == KEY)
        self.assertEqual((row["role"], row["returned"], row["returned_count"]), (GD, True, 1))
        self.assertTrue((self.tmp / "runs/handoffs/INDEX.md").is_file() and (self.tmp / "runs/handoffs/START-HERE.md").is_file())

    # ---------------------------------------------------------------- onto the approval page
    def test_send_files_one_card_in_the_roles_lane(self):
        self.run_check([(f"{KEY}/returned/a.png", "f1"), (f"{KEY}/returned/b.png", "f2")])
        seen = []

        def fake(cmd):
            seen.append(cmd)
            return "  primary 3 · headlines 3 · descriptions 2 · pages 1\nfiled  meta/testbrand/1-check/image/the-ad\n"
        card = DL.send(BRAND, f"{GD}/{KEY}", run=fake, cfg=CFG)
        cmd = seen[0]
        self.assertTrue(cmd[0].endswith("meta-upload/to_check.py"))
        arg = lambda k: cmd[cmd.index(k) + 1]                         # noqa: E731
        self.assertEqual((arg("--brief"), arg("--lane"), arg("--tool")), ("brief-0325", "image", GD))
        self.assertEqual(arg("--run"), f"runs/handoffs/graphic-designer/testbrand/{KEY}")
        self.assertEqual([Path(m).name for m in cmd[cmd.index("--media") + 1:cmd.index("--tool")]], ["a.png", "b.png"])
        self.assertIn("--replace", cmd)
        self.assertEqual((card["name"], card["files"]), ("the-ad", 2))
        DL.send(BRAND, "brief-0325", run=fake, cfg=CFG)                # a second send keeps the batch: updates the card
        self.assertEqual(seen[1][seen[1].index("--batch") + 1], card["batch"])
        self.assertEqual(DL.delivered(BRAND, CFG)[0]["card"]["name"], "the-ad")

    def test_videos_go_on_the_video_lane_and_one_brief_on_two_roads_says_which(self):
        d = FakeDrive([(f"{KEY}/returned/a.png", "f1"), (f"{KEY}/returned/cut.mp4", "v1")])
        DL.check(BRAND, drive=d, reg=self.reg, cfg=CFG)
        with self.assertRaises(DL.Refused):
            DL.send(BRAND, "brief-0325", run=lambda c: "", cfg=CFG)
        seen = []
        DL.send(BRAND, f"video-editor/{KEY}", run=lambda c: seen.append(c) or "filed meta/x/1-check/video/v\n", cfg=CFG)
        cmd = seen[0]
        self.assertEqual((cmd[cmd.index("--lane") + 1], cmd[cmd.index("--tool") + 1]), ("video", "video-editor"))

    def test_send_refused_when_filer_refuses_or_nothing_delivered(self):
        with self.assertRaises(DL.Refused):
            DL.send(BRAND, "brief-0325", run=lambda c: "", cfg=CFG)
        self.run_check([(f"{KEY}/returned/a.png", "f1")])
        with self.assertRaises(DL.Refused):
            DL.send(BRAND, "brief-0325", run=lambda c: "REFUSED not a testbrand link\n", cfg=CFG)

    # ---------------------------------------------------------------- the walls
    def test_no_key_is_refused_by_name(self):
        class E:
            @staticmethod
            def has_key():
                return False
        real = DL._gdrive
        DL._gdrive = lambda: (E, None)
        try:
            with self.assertRaises(DL.Refused) as c:
                DL.Drive()
            self.assertIn("GDRIVE_SA_KEY", str(c.exception))
        finally:
            DL._gdrive = real

    def test_never_writes_deletes_moves_or_renames_on_drive(self):
        src = (HERE / "delivery.py").read_text()
        for bad in ("delete(", "emptyTrash", "trashed=True", "files().update", "files().create", "upload_file", "put_ids", "rmtree",
                    "unlink(", "addParents", "removeParents", "/Volumes", "CloudStorage", "mount()"):
            self.assertFalse(bad in src, f"delivery.py must never use {bad}")

    def test_no_brand_named_in_code(self):
        src = (HERE / "delivery.py").read_text().lower()
        brands = [p.name for p in (HERE.parent.parent / "brands").iterdir() if p.is_dir()] \
            if (HERE.parent.parent / "brands").is_dir() else []
        for b in brands:
            self.assertIsNone(re.search(r"\b%s\b" % re.escape(b.lower()), src), b)


if __name__ == "__main__":
    unittest.main(verbosity=1)
