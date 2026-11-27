"""calendar_view.month_items on a small made-up workspace: every status, the unwritten slots, the re-plan rules and the
local-only mark. No network, no git (the made-up folder is no repo, so nothing reads origin/main).
    python3 test_calendar_view.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calendar_view as CV  # noqa: E402

M = "2030-03"


def put(root, rel, obj):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


def card(date, slot=None, avatar=None, **kw):
    c = {"date": date, "status": "draft", "subjects": [{"subject": "Hello", "preview": "There"}]}
    if slot:
        c["calendar_handoff"] = {"expected": {"slot_id": slot, "avatar": avatar}}
    c.update(kw)
    return c


class MonthItems(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        r = self.root = Path(self.t.name) / "ws"
        E = "runs/email-production/brand-a/"
        put(r, "runs/marketing-calendar/brand-a/%s/slots.json" % M, [
            {"id": "mar-01", "date": "2030-03-04", "channel": "email", "variants": [{"avatar": "x", "angle": "one"}]},
            {"id": "mar-02", "date": "2030-03-05", "channel": "email",
             "variants": [{"avatar": "x", "angle": "two"}, {"avatar": "y", "angle": "two y"}]},
            {"id": "mar-03", "date": "2030-03-06", "channel": "email", "variants": [{"avatar": "x", "angle": "old angle"}]},
            {"id": "mar-04", "date": "2030-03-07", "channel": "email", "variants": [{"avatar": "x", "angle": "four"}]},
            {"id": "mar-05", "date": "2030-03-08", "channel": "sms"},
            {"id": "mar-06", "date": "2030-03-09", "channel": "sms"},
        ])
        put(r, E + "deadlines.json", {"_about": "x", "brand-a-mar-01": "2030-02-25"})
        for lab in ("brand-a-mar-01", "brand-a-mar-02", "brand-a-renumbered", "brand-a-gone", "brand-a-nocard",
                    "brand-a-april"):
            put(r, E + lab + "/run.json", {"assignment": {}})
        put(r, E + "brand-a-mar-01/klaviyo/card.json", card("2030-03-04", "mar-01", "x", status="scheduled"))
        put(r, E + "brand-a-mar-02/klaviyo/card.json", card("2030-03-05", "mar-02", "x", editor_done={"at": "now"}))
        # from before a re-plan: no slot id on the card, its own angle names the send
        put(r, E + "brand-a-renumbered/run.json", {"assignment": {"angle": "old angle", "send_date": "2030-03-06"}})
        put(r, E + "brand-a-renumbered/klaviyo/card.json", card("2030-03-06"))
        put(r, E + "brand-a-gone/klaviyo/card.json", card("2030-03-07", "mar-04", "x"))
        put(r, E + "brand-a-gone/off-page.json", {"why": "test"})
        put(r, E + "brand-a-nocard/run.json", {"assignment": {"send_date": "2030-03-07"},
                                               "calendar_handoff": {"slot_id": "mar-04", "avatar": "x"}})
        put(r, E + "brand-a-april/klaviyo/card.json", card("2030-04-01"))
        # a text with an old number, sending on mar-05's day; a superseded one on mar-06's day
        put(r, E + "brand-a-mar-09-sms/sms.json", {"slot": "mar-09", "date": "2030-03-08", "text": "Hi", "state": "ready"})
        put(r, E + "brand-a-mar-09-sms/sms-card.json", {"text": "Hi {link}", "state": "waiting"})
        put(r, E + "brand-a-mar-10-sms/sms.json", {"slot": "mar-10", "date": "2030-03-09", "state": "superseded 2030"})
        self.clone = Path(self.t.name) / "clone"
        put(self.clone, E + "brand-a-local-only/run.json", {"assignment": {"send_date": "2030-03-07"}})
        put(self.clone, E + "brand-a-local-only/klaviyo/card.json", card("2030-03-07"))

    def tearDown(self):
        self.t.cleanup()

    def items(self, clone=None):
        return CV.month_items(M, root=self.root, clone=clone)["items"]

    def by(self, label, clone=None):
        return next(i for i in self.items(clone) if i["label"] == label)

    def test_statuses(self):
        self.assertEqual(self.by("brand-a-mar-01")["status"], "scheduled")
        self.assertEqual(self.by("brand-a-mar-02")["status"], "done")
        self.assertEqual(self.by("brand-a-renumbered")["status"], "editor")
        self.assertEqual(self.by("brand-a-nocard")["status"], "nodesign")

    def test_off_page_and_other_months_are_left_out(self):
        labels = {i["label"] for i in self.items()}
        self.assertNotIn("brand-a-gone", labels)
        self.assertNotIn("brand-a-april", labels)

    def test_due_from_deadlines_only(self):
        self.assertEqual(self.by("brand-a-mar-01")["due"], "2030-02-25")
        self.assertIsNone(self.by("brand-a-mar-02")["due"])   # the page works out the default

    def test_unwritten_once_per_slot_and_replan_angle(self):
        un = [i["slot"] for i in self.items() if i["kind"] == "email" and i["status"] == "unwritten"]
        # one version per send (decision log 2026-11-04): mar-02's x version is written, so its y variant is not
        # still to write; mar-03 is the renumbered run's (angle + date); mar-04 is the run with no card
        self.assertEqual(un, [])
        self.assertEqual(self.by("brand-a-renumbered")["slot"], "mar-03")

    def test_unwritten_slot_is_one_item_whatever_its_variants(self):
        put(self.root, "runs/marketing-calendar/brand-a/%s/slots.json" % M, [
            {"id": "mar-07", "date": "2030-03-20", "channel": "email",
             "variants": [{"avatar": "x", "angle": "a"}, {"avatar": "y", "angle": "b"}, {"avatar": "z", "angle": "c"}]}])
        un = [(i["slot"], i["avatar"]) for i in self.items() if i["kind"] == "email" and i["status"] == "unwritten"]
        self.assertEqual(un, [("mar-07", None)])

    def test_off_page_siblings_of_a_written_version_are_not_to_write(self):
        E = "runs/email-production/brand-a/"
        put(self.root, "runs/marketing-calendar/brand-a/%s/slots.json" % M, [
            {"id": "mar-08", "date": "2030-03-21", "channel": "email",
             "variants": [{"avatar": "x", "angle": "a"}, {"avatar": "y", "angle": "b"}]}])
        for av, gone in (("x", False), ("y", True)):
            lab = "brand-a-mar-08--" + av
            put(self.root, E + lab + "/run.json", {"assignment": {}})
            put(self.root, E + lab + "/klaviyo/card.json", card("2030-03-21", "mar-08", av))
            if gone:
                put(self.root, E + lab + "/off-page.json", {"why": "keep one"})
        got = [(i["label"], i["status"]) for i in self.items() if i["send"] == "2030-03-21"]
        self.assertEqual(got, [("brand-a-mar-08--x", "editor")])
        # every version taken off the page: the send is to write again, once
        put(self.root, E + "brand-a-mar-08--x/off-page.json", {"why": "rewrite"})
        got = [(i["slot"], i["status"]) for i in self.items() if i["send"] == "2030-03-21"]
        self.assertEqual(got, [("mar-08", "unwritten")])

    def test_sms_by_date_and_superseded(self):
        sms = [i for i in self.items() if i["kind"] == "sms"]
        self.assertEqual([(i["label"], i["status"]) for i in sms if i["label"]], [("brand-a-mar-09-sms", "carded")])
        self.assertEqual([(i["slot"], i["status"]) for i in sms if not i["label"]], [("mar-06", "unwritten")])

    def test_local_only_from_the_clone(self):
        self.assertNotIn("brand-a-local-only", {i["label"] for i in self.items()})
        got = self.by("brand-a-local-only", clone=self.clone)
        self.assertTrue(got["local"])
        self.assertEqual(got["status"], "unpushed", "a card only on this Mac is not with editor yet")
        self.assertFalse(self.by("brand-a-mar-01", clone=self.clone)["local"])

    def test_planned_send_carries_its_fields_and_review(self):
        put(self.root, "runs/marketing-calendar/brand-a/%s/slots.json" % M, [
            {"id": "mar-09", "date": "2030-03-22", "channel": "email", "segment": "Core | Lead", "segments": ["Core | Lead"],
             "type": "moment", "category": "Seasonal", "product": "p", "offer": "none", "occasion": "spring",
             "why": "Spring starts here. Then a lot more reasoning.",
             "variants": [{"avatar": "x", "angle": "one"}, {"avatar": "y", "angle": "two"}]}])
        put(self.root, "runs/marketing-calendar/brand-a/%s/review.json" % M, {"slots": {"mar-09": {
            "status": "needs-work", "note": "softer", "by": "owner", "at": "2030-03-01T10:00:00", "edits": {"offer": "bf"},
            "identity": {"date": "2030-03-22", "segment": "Core | Lead", "type": "moment", "occasion": "spring"}}}})
        i = next(x for x in self.items() if x["slot"] == "mar-09" and x["kind"] == "email")
        self.assertEqual(i["angles"], [{"avatar": "x", "angle": "one"}, {"avatar": "y", "angle": "two"}])
        self.assertEqual((i["segments"], i["type"], i["category"], i["product"], i["occasion"]),
                         (["Core | Lead"], "moment", "Seasonal", "p", "spring"))
        self.assertEqual(i["offer"], "bf", "the reviewer's edit wins, as the board shows it")
        self.assertEqual(i["edited"], ["offer"])
        self.assertEqual((i["plan"]["offer"], i["orig"]["offer"]), ("bf", "none"), "now, and as the planner wrote it")
        self.assertEqual(i["plan"]["date"], "2030-03-22")
        self.assertEqual(i["why"], "Spring starts here.")
        self.assertEqual((i["review"]["status"], i["review"]["note"], i["review"]["by"]), ("needs-work", "softer", "owner"))
        self.assertFalse(i["review"]["for_another_send"])

    def test_a_review_for_another_send_is_not_laid_on(self):
        put(self.root, "runs/marketing-calendar/brand-a/%s/review.json" % M, {"slots": {"mar-02": {
            "status": "cut", "note": "", "edits": {}, "identity": {"date": "2030-01-01", "segment": "x", "type": "y",
                                                                   "occasion": "z"}}}})
        i = self.by("brand-a-mar-02")
        self.assertEqual(i["review"]["status"], "pending")
        self.assertTrue(i["review"]["for_another_send"])

    def test_no_machine_path_in_the_output(self):
        self.assertNotIn(self.t.name, json.dumps(CV.month_items(M, root=self.root, clone=self.clone)))


if __name__ == "__main__":
    unittest.main()
