"""QB-7 (content queue Monday): view.py takes emails from the email line, keeps video read only, hides test pieces
and Christine, and makes titles readable.

The fixture tree (test_qb7_fixtures/) holds owner's index (an email row, a video row, the zz- test piece and four
id-shaped titles), a shadow root, and a small runs/email-production tree: one card per state (ready, ready + editor's
done, a Klaviyo draft, scheduled ahead, scheduled past, an older "12 Oct" card with its own year, one without a year,
an unreadable date) and a deadlines.json override. view.py runs on the fixtures in place, as the kit runs it (this
Python, from the repo root), and must leave the tree byte-identical with no new file. Stdlib only, no network, no git.

    python3 components/creative-queue/test_qb7_view.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402
import view  # noqa: E402

REPO = paths.repo(HERE)
FIX = HERE / "test_qb7_fixtures"
NOW = "2026-10-23T14:00:00Z"                       # today is Friday 2026-10-23
DEFAULT = "5 working days before the send"


def snapshot(top):
    """Every file under top with its bytes."""
    return {str(p.relative_to(top)): p.read_bytes() for p in sorted(Path(top).rglob("*")) if p.is_file()}


def run_view():
    p = subprocess.run([sys.executable, "-B", str(HERE / "view.py"), "--index", str(FIX / "index.json"),
                        "--root", str(FIX / "shadow"), "--emails", str(FIX / "email-production"), "--now", NOW],
                       cwd=str(REPO), capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


class View(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = snapshot(FIX)
        code, out, err = run_view()
        cls.after = snapshot(FIX)
        assert code == 0, err
        cls.d = json.loads(out)
        cls.rows = {r["id"]: r for r in cls.d["rows"]}

    def email(self, label, brand="fxbrand"):
        return self.rows["%s__%s" % (brand, label)]

    def check(self, label, status, turn, send, editor_due, editor_from, stage=None, brand="fxbrand", ok=True):
        r = self.email(label, brand)
        self.assertEqual((r["type"], r["read_only"], r["brand"], r["email_run"]), ("email", "email", brand, label))
        self.assertEqual((r["status"], r["turn"], r["send_date"], r["send_date_ok"]), (status, turn, send, ok))
        self.assertEqual((r["editor_due"], r["editor_due_from"]), (editor_due, editor_from))
        self.assertEqual(r["stage"], stage)
        self.assertEqual(r["email_link"], {"label": "open in the emails page",
                                           "url": "emails.html#%s__%s" % (brand, label)})
        for f in ("who", "priority", "due", "note", "requested_stage", "decided_by", "removed", "in_owner"):
            self.assertIn(f, r)
        self.assertIs(r["in_owner"], False)
        self.assertIsNone(r["who"])                                  # a shadow decision on an email id is not read
        return r

    # ---------------------------------------------------------------- emails from the email line
    def test_ready_is_editor_pictures_with_the_5_working_day_default_across_a_weekend(self):
        r = self.check("fxbrand-nov-02", "ready", "editor: pictures", "2026-11-02", "2026-10-26", DEFAULT)
        self.assertEqual(r["title"], "Ready, waiting on editor")

    def test_an_email_marked_off_page_is_not_a_row(self):
        # off-page.json beside the run (the emails page's own rule): replaced, kept for the record, never overdue on the board
        self.assertNotIn("fxbrand__fxbrand-nov-07", self.rows)

    def test_deadlines_json_overrides_the_default(self):
        self.check("fxbrand-nov-04", "ready", "editor: pictures", "2026-11-04", "2026-10-27", "deadlines.json")

    def test_ready_with_editor_done_is_email_lead_words(self):
        self.check("fxbrand-nov-03", "ready", "email_lead: words, then Go", "2026-11-03", "2026-10-27", DEFAULT)

    def test_the_day_email_lead_wrote_it_is_on_the_row_and_first_in_its_story(self):
        # email_lead, 2026-11-19: "que se vean en el board cuando le lleguen a editor y en el calendar como hechos"
        r = self.email("fxbrand-nov-03")
        self.assertEqual(r["written_at"], "2026-10-21T17:29:54")
        self.assertEqual(r["history"][0], {"step": "Written; on editor's page", "at": "2026-10-21T17:29:54", "by": "email_lead"})
        self.assertIsNone(self.email("fxbrand-nov-02")["written_at"], "no run.json: no day, nothing made up")

    def test_register_runs_name_the_brief_each_run_became(self):
        # email_lead, 2026-11-24: a writing job closes once owner wrote a brief from it; deprecated or dateless briefs never count
        reg = {"briefs": {"a": {"brief": "brief-0377", "key": "k77", "run": "brand_b-yai-a1v3", "opened": "2026-11-20", "status": "draft"},
                          "b": {"brief": "brief-0378", "run": "x-old", "opened": "2026-11-20", "status": "deprecated"},
                          "c": {"brief": "brief-0379", "run": "x-nodate", "opened": "before the register", "status": "draft"},
                          "d": {"brief": "brief-0380", "run": None, "opened": "2026-11-20", "status": "draft"}}}
        self.assertEqual(view.register_runs(reg), {"brand_b-yai-a1v3": {"brief": "0377", "key": "k77", "opened": "2026-11-20"}})
        self.assertEqual(view.register_runs(None), {})

    def test_klaviyo_draft_is_email_lead_schedule(self):
        self.check("fxbrand-nov-05", "draft", "email_lead: schedule in Klaviyo", "2026-11-05", "2026-10-29", DEFAULT)

    def test_scheduled_ahead_and_scheduled_past(self):
        self.check("fxbrand-oct-24", "scheduled", "Scheduled · 2026-10-24", "2026-10-24", "2026-10-19", DEFAULT)
        r = self.check("fxbrand-oct-20", "scheduled", "Sent 2026-10-20 (date passed; no sent field on the card)",
                       "2026-10-20", "2026-10-13", DEFAULT, stage="live")
        self.assertEqual(r["title"], "Sat Oct 31 · Quick reminder!")

    def test_older_short_dates(self):
        # its own `year` wins; without one, the year of the brand's newest ISO send date (2026-11-05)
        self.check("fxbrand-oct-12", "scheduled", "Sent 2025-10-12 (date passed; no sent field on the card)",
                   "2025-10-12", "2025-10-06", DEFAULT, stage="live")
        self.check("fxbrand-oct-31", "ready", "editor: pictures", "2026-10-31", "2026-10-26", DEFAULT)
        # no year anywhere in its brand: shown as written, no deadline
        self.check("fybrand-oct-12", "ready", "editor: pictures", "12 Oct", None, None, brand="fybrand", ok=False)
        r = self.check("fxbrand-someday", "scheduled", "Scheduled · someday", "someday", None, None, ok=False)
        self.assertEqual(r["title"], "fxbrand-someday")              # no subject: the label

    def test_held_by_the_emails_pages_own_rule(self):
        # email_lead, 2026-11-04 (the queue QC): a held email shows held, split by who fixes it, as the emails page does
        r = self.email("fxbrand-nov-06")
        self.assertEqual(r["status"], "held")
        self.assertEqual(r["held"], ["2 picture slot(s) still to fill"], "a picture problem is editor's; a note holds no one")
        self.assertEqual(r["held_email_lead"], ["price $9.99 · not in the brand's price list"], "ok and by-hand rows hold no one")
        self.assertEqual(r["turn"], "editor: pictures", "held changes no one's turn")
        m = self.email("fxbrand-nov-09")
        self.assertEqual((m["status"], m["held"], m["held_email_lead"]), ("held", [], ["copy repaired, rebuild the layout"]))
        clean = self.email("fxbrand-nov-02")
        self.assertEqual((clean["status"], clean["held"], clean["held_email_lead"]), ("ready", [], []))

    def test_one_row_per_card(self):
        emails = sorted(i for i, r in self.rows.items() if r["type"] == "email")
        self.assertEqual(emails, sorted(["fxbrand__fxbrand-%s" % x for x in
                                         ("nov-02", "nov-03", "nov-04", "nov-05", "nov-06", "nov-09", "oct-12",
                                          "oct-20", "oct-24", "oct-31", "someday")] + ["fybrand__fybrand-oct-12"]))

    # ---------------------------------------------------------------- owner's index
    def test_index_email_rows_gone_video_read_only_test_piece_gone(self):
        self.assertNotIn("fxbrand_email_fxbrand-oct-20", self.rows)
        v = self.rows["fxbrand_fx_brief-0001"]
        self.assertEqual((v["type"], v["read_only"], v["title"]), ("video-ad", "video", "A video"))
        self.assertFalse([i for i in self.rows if i.startswith("zz-")])
        r = self.rows["fxbrand_fx_brief-0048"]
        self.assertIsNone(r["read_only"])
        self.assertEqual((r["who"], r["title"]), ("editor", "Brief 0048 · fx"))

    def test_people_without_christine(self):
        self.assertEqual(self.d["people"], ["owner", "email_lead", "editor", "Victoria"])
        self.assertEqual(sorted(self.d), ["calendar", "owner_age_h", "owner_built", "from_register", "ledger", "loose", "people", "register_runs", "rows", "shadow_root", "stages", "towrite", "trail"])

    # ---------------------------------------------------------------- titles
    def test_title_fallback_for_the_three_id_shapes(self):
        t = {i: r["title"] for i, r in self.rows.items()}
        self.assertEqual(t["fxbrand_idea_fxbrand_brilliance-face-scrub_none_batch-2026-10-01-a"],
                         "Brilliance face scrub · batch 1 Oct")
        self.assertEqual(t["fxbrand_idea_fxbrand_glow-serum_static_batch-2026-10-14-b"],
                         "Glow serum · static · batch 14 Oct")
        self.assertEqual(t["fxbrand_glow-serum_idea_7"], "Glow serum idea")
        self.assertEqual(t["fxbrand_idea_fxbrand-creator-01--glow-serum"], "Glow serum idea")
        self.assertEqual(t["fxbrand_odd_shape"], "fxbrand_odd_shape")   # unparseable: the raw id
        self.assertEqual(view.readable("brand_b_brilliance-face-scrub_none_batch-2026-10-01-a"),
                         "Brilliance face scrub · batch 1 Oct")       # the card's own example
        self.assertEqual(view.title_of("x_y", "A real title"), "A real title")

    # ---------------------------------------------------------------- read only
    def test_view_writes_nothing(self):
        self.assertEqual(self.after, self.before)


class DamonsReview(unittest.TestCase):
    def test_a_month_owner_reviewed_counts_as_approved(self):
        """email_lead, 2026-11-11: owner approves by reviewing the month on the calendar's review page; his edits are saved
        "by: owner" and the status stays pending. Such a month's emails to write are approved; one he never reviewed is not."""
        import tempfile, shutil, json as J
        from datetime import date
        root = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, str(root))
        for brand, by in (("aaa", "owner"), ("bbb", "reviewer")):
            m = root / brand / "2026-12"; m.mkdir(parents=True)
            (m / "slots.json").write_text(J.dumps([{"id": "dec-01", "date": "2026-12-02", "channel": "email", "type": "x"}]))
            (m / "review.json").write_text(J.dumps({"slots": {"dec-09": {"by": by, "status": "pending", "edits": {"segment": "y"}}}}))
        got = {r["brand"]: r["approved"] for r in view.towrite(root, None, date(2026, 11, 11))}
        self.assertEqual(got, {"aaa": True, "bbb": False})

    def test_a_slot_cut_on_the_review_is_no_email_to_write(self):
        """email_lead, 2026-11-24: December drops to about two emails a week; the cut slots stay in slots.json with
        status "cut" in review.json and must leave the emails she has to write, even in a month owner reviewed."""
        import tempfile, shutil, json as J
        from datetime import date
        root = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, str(root))
        m = root / "aaa" / "2026-12"; m.mkdir(parents=True)
        (m / "slots.json").write_text(J.dumps([{"id": i, "date": "2026-12-0%d" % n, "channel": "email", "type": "x"}
                                               for n, i in ((2, "dec-01"), (3, "dec-02"))]))
        (m / "review.json").write_text(J.dumps({"slots": {"dec-01": {"by": "owner", "status": "pending"},
                                                          "dec-02": {"by": "email_lead", "status": "cut"}}}))
        self.assertEqual([r["slot"] for r in view.towrite(root, None, date(2026, 11, 24))], ["dec-01"])


class Register(unittest.TestCase):
    def test_the_register_fills_in_what_damons_list_has_not_caught_up_with(self):
        """email_lead, 2026-11-17: "a mí me llega en todo lo que está trabajando owner?" His list was last saved Oct 30; his
        brief register keeps going. Only briefs opened on or after his list's day, not deprecated, of a drawn kind,
        and not already in his list come in; a draft is his to approve."""
        index = {"built": "2026-10-30T17:49:00", "entries": [{"id": "b_p_brief-0300_batch-x", "stage": "making"}]}
        B = lambda n, **k: dict({"key": "b_p_brief-%s" % n, "brief": "brief-%s" % n, "brand": "b", "type": "video-ai",
                                 "status": "draft", "state": "for-review", "opened": "2026-11-16", "title": "T" + n}, **k)
        reg = {"briefs": {x["key"]: x for x in (
            B("0400"),                                              # new draft video: in, owner's to approve
            B("0401", type="image-ai", status="approved", state="in-production"),
            B("0402", status="approved", state="shipped"),
            B("0300"),                                              # already in his list (with a suffix): out
            B("0403", opened="2026-10-20"),                         # opened before his list: out
            B("0404", opened="before the register"),                # no date: out
            B("0405", status="deprecated", state="superseded"),     # dropped: out
            B("0406", type="concept"), B("0407", type="email"))}}   # not drawn on the board: out
        got = {e["id"][-4:]: (e["type"], e["stage"], e["title"]) for e in view.register_entries(reg, index)}
        self.assertEqual(got, {"0400": ("video-ad", "brief-needs-you", "T0400"), "0401": ("image-ad", "making", "T0401"),
                               "0402": ("video-ad", "live", "T0402")})
        self.assertEqual(view.register_entries(reg, {"built": None, "entries": []}), [], "no list date: nothing guessed")
        self.assertEqual(view.register_entries(None, index), [])


class PMTasks(unittest.TestCase):
    def test_eves_open_pm_tasks_are_rows(self):
        """email_lead, 2026-11-19: owner hands some design work out as PM tasks; editor sees only this page."""
        import tempfile, shutil, json as J
        root = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, str(root))
        pm = root / "new-workflow-design" / "builds" / "pm-tool"; pm.mkdir(parents=True)
        (pm / "mytasks.py").write_text((REPO / "new-workflow-design" / "builds" / "pm-tool" / "mytasks.py").read_text())
        (root / "platform" / "data" / "records" / "tasks").mkdir(parents=True)
        items = [{"id": "TSK-1-brand_b-a", "title": "Storefront art", "status": "todo", "assignees": ["editor"], "due": "2026-11-25", "priority": 1,
                  "links": [{"type": "url", "ref": "https://x/START.md"}]},
                 {"id": "TSK-2-brand_a-b", "title": "Done one", "status": "done", "assignees": ["editor"]},
                 {"id": "TSK-3-c", "title": "Not hers", "status": "todo", "assignees": ["owner"]},
                 {"id": "TSK-4-d", "title": "Designer role", "status": "in_progress", "assignees": [], "tags": ["role:graphic-designer"]}]
        (root / "platform" / "data" / "kinds").mkdir(parents=True)
        (root / "platform" / "data" / "kinds" / "tasks.json").write_text(J.dumps({"items": items}))
        got = {r["id"]: (r["who"], r["due"], r["priority"], r["read_only"], r["requested_stage"], [l["url"] for l in r["links"]]) for r in view.pm_tasks(root)}
        self.assertEqual(set(got), {"TSK-1-brand_b-a", "TSK-4-d"}, "open and editor's or the designer role's only")
        self.assertEqual(got["TSK-1-brand_b-a"], ("editor", "2026-11-25", None, "pm", None, ["https://x/START.md"]))
        self.assertEqual(got["TSK-4-d"][4], "editing", "in progress in the PM: In progress here")
        items[0]["waiting_on"] = "December offer decision"
        (root / "platform" / "data" / "kinds" / "tasks.json").write_text(J.dumps({"items": items}))
        held = {r["id"]: r for r in view.pm_tasks(root)}["TSK-1-brand_b-a"]
        self.assertEqual((held["due"], held["due_when_free"], held["note"]), (None, "2026-11-25", "On hold: December offer decision"),
                         "waiting_on holds it: no day, the reason as its note; cleared, it is back on Nov 25")
        self.assertEqual(view.pm_tasks(root / "nowhere"), [], "no PM: no rows, never a failed page")


class Trail(unittest.TestCase):
    def test_each_piece_carries_its_story(self):
        """email_lead, 2026-11-19: "en tal fecha se creó la tarea, en tal pasó de tal persona a tal persona"."""
        ds = [{"id": "x", "op": "set", "field": "who", "value": "creator", "by": "email_lead", "made": "2026-11-19T17:02:23Z"},
              {"id": "x", "op": "set", "field": "due", "value": "2026-11-20", "by": "email_lead", "made": "2026-11-19T16:00:00Z"},
              {"id": "x", "op": "set", "field": "title_set", "value": "t", "by": "email_lead", "made": "2026-11-19T15:00:00Z"},
              {"id": "y", "op": "remove", "by": "owner", "made": "2026-11-06T10:00:00Z"}]
        got = view.trail(ds, [{"id": "x", "since": "2026-11-16T00:00:00Z"}])
        self.assertEqual([e["what"] for e in got["x"]], ["opened", "due", "who"], "oldest first; only the fields a card tells")
        self.assertEqual(got["y"][0]["what"], "remove")


if __name__ == "__main__":
    unittest.main()
