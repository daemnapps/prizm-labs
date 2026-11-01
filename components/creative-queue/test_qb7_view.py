"""QB-7 (content queue Monday): view.py takes emails from the email line, keeps video read only, hides test pieces
and Christine, and makes titles readable.

The fixture tree (test_qb7_fixtures/) holds the owner's index (an email row, a video row, the zz- test piece and four
id-shaped titles), a shadow root, and a small runs/email-production tree: one card per state (ready, ready + the team's
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

    def check(self, label, status, turn, send, eve_due, eve_from, stage=None, brand="fxbrand", ok=True):
        r = self.email(label, brand)
        self.assertEqual((r["type"], r["read_only"], r["brand"], r["email_run"]), ("email", "email", brand, label))
        self.assertEqual((r["status"], r["turn"], r["send_date"], r["send_date_ok"]), (status, turn, send, ok))
        self.assertEqual((r["eve_due"], r["eve_due_from"]), (eve_due, eve_from))
        self.assertEqual(r["stage"], stage)
        self.assertEqual(r["email_link"], {"label": "open in the emails page",
                                           "url": "http://127.0.0.1:8765/#%s__%s" % (brand, label)})
        for f in ("who", "priority", "due", "note", "requested_stage", "decided_by", "removed", "in_damon"):
            self.assertIn(f, r)
        self.assertIs(r["in_damon"], False)
        self.assertIsNone(r["who"])                                  # a shadow decision on an email id is not read
        return r

    # ---------------------------------------------------------------- emails from the email line
    def test_ready_is_eve_pictures_with_the_5_working_day_default_across_a_weekend(self):
        r = self.check("fxbrand-nov-02", "ready", "the team: pictures", "2026-11-02", "2026-10-26", DEFAULT)
        self.assertEqual(r["title"], "Ready, waiting on the team")

    def test_deadlines_json_overrides_the_default(self):
        self.check("fxbrand-nov-04", "ready", "the team: pictures", "2026-11-04", "2026-10-27", "deadlines.json")

    def test_ready_with_eve_done_is_steph_words(self):
        self.check("fxbrand-nov-03", "ready", "the team: words, then Go", "2026-11-03", "2026-10-27", DEFAULT)

    def test_klaviyo_draft_is_steph_schedule(self):
        self.check("fxbrand-nov-05", "draft", "the team: schedule in Klaviyo", "2026-11-05", "2026-10-29", DEFAULT)

    def test_scheduled_ahead_and_scheduled_past(self):
        self.check("fxbrand-oct-24", "scheduled", "Scheduled · 2026-10-24", "2026-10-24", "2026-10-19", DEFAULT)
        r = self.check("fxbrand-oct-20", "scheduled", "Sent 2026-10-20 (date passed; no sent field on the card)",
                       "2026-10-20", "2026-10-13", DEFAULT, stage="live")
        self.assertEqual(r["title"], "Sat Oct 31 · Quick reminder!")

    def test_older_short_dates(self):
        # its own `year` wins; without one, the year of the brand's newest ISO send date (2026-11-05)
        self.check("fxbrand-oct-12", "scheduled", "Sent 2025-10-12 (date passed; no sent field on the card)",
                   "2025-10-12", "2025-10-06", DEFAULT, stage="live")
        self.check("fxbrand-oct-31", "ready", "the team: pictures", "2026-10-31", "2026-10-26", DEFAULT)
        # no year anywhere in its brand: shown as written, no deadline
        self.check("fybrand-oct-12", "ready", "the team: pictures", "12 Oct", None, None, brand="fybrand", ok=False)
        r = self.check("fxbrand-someday", "scheduled", "Scheduled · someday", "someday", None, None, ok=False)
        self.assertEqual(r["title"], "fxbrand-someday")              # no subject: the label

    def test_one_row_per_card(self):
        emails = sorted(i for i, r in self.rows.items() if r["type"] == "email")
        self.assertEqual(emails, sorted(["fxbrand__fxbrand-%s" % x for x in
                                         ("nov-02", "nov-03", "nov-04", "nov-05", "oct-12", "oct-20", "oct-24",
                                          "oct-31", "someday")] + ["fybrand__fybrand-oct-12"]))

    # ---------------------------------------------------------------- the owner's index
    def test_index_email_rows_gone_video_read_only_test_piece_gone(self):
        self.assertNotIn("fxbrand_email_fxbrand-oct-20", self.rows)
        v = self.rows["fxbrand_fx_brief-0001"]
        self.assertEqual((v["type"], v["read_only"], v["title"]), ("video-ad", "video", "A video"))
        self.assertFalse([i for i in self.rows if i.startswith("zz-")])
        r = self.rows["fxbrand_fx_brief-0048"]
        self.assertIsNone(r["read_only"])
        self.assertEqual((r["who"], r["title"]), ("eve", "Brief 0048 · fx"))

    def test_people_without_christine(self):
        self.assertEqual(self.d["people"], ["the owner", "the team", "the team", "Victoria"])
        self.assertEqual(sorted(self.d), ["damon_age_h", "damon_built", "people", "rows", "shadow_root", "stages"])

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


if __name__ == "__main__":
    unittest.main()
