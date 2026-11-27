"""Tests for the free script checker. Neutral fixtures only: no brand, no real run."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "machine"))
import script_check as S  # noqa: E402

HEAD = "| # | Time | Tag | Speaker | Line | Scene |\n|---|---|---|---|---|---|\n"


def table(*rows):
    return HEAD + "\n".join("| %d | %s |" % (i + 1, " | ".join(r)) for i, r in enumerate(rows)) + "\n"


GOOD = table(
    ("0:00.0-0:02.5", "[SOURCE]", "Host", "Would you pay for this?", "Close shot, hand slams the table."),
    ("0:02.5-0:05.0", "[SOURCE]", "Guest", "Never again.", "She pushes the box across the counter."),
    ("0:05.0-0:09.0", "[SOURCE]", "Narrator (VO)", "It costs less than the thing it replaces and it lasts.", "Hands wash a cup, then lift it to the light."),
    ("0:09.0-0:12.0", "[SOURCE]", "Narrator (VO)", "Try it for thirty days.", "He opens the box and puts the cup on the shelf."),
    ("0:12.0-0:15.0", "[SOURCE]", "—", "HOLD: no words.", "She picks up the cup and drinks, walking out of frame."),
)


def level(report, code):
    return next(r["level"] for r in report["results"] if r["code"] == code)


class Parsing(unittest.TestCase):
    def test_reads_table_with_dash_times(self):
        rows = S.parse_rows(GOOD)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[1]["start"], 2.5)
        self.assertEqual(rows[4]["line"], "")           # HOLD row carries no speech

    def test_minute_times(self):
        rows = S.parse_rows(table(("1:05.5–1:07.0", "", "A", "Hi there friend", "She runs.")))
        self.assertAlmostEqual(rows[0]["start"], 65.5)
        self.assertAlmostEqual(rows[0]["end"], 67.0)

    def test_no_table_is_no_result_not_a_pass(self):
        rep = S.run("just prose, no table")
        self.assertEqual(rep["rows"], 0)
        self.assertEqual(rep["result"], "none")
        self.assertEqual(sum(rep["counts"].values()), 0)
        out = S.render(rep)
        self.assertIn("0 rows checked: no result", out)
        self.assertNotIn("PASS", out)
        self.assertNotIn("NOTE", out)

    def test_unreadable_times_are_no_result(self):
        t = table(("soon", "", "Host", "Would you pay for this?", "He points."))
        out = S.render(S.run(t))
        self.assertIn("0 rows checked: no result", out)

    def test_start_times_only(self):
        t = table(("0:00.1", "", "Host", "Would you pay for this?", "He points."),
                  ("0:02.5", "", "Guest", "Never again.", "She walks."),
                  ("0:04.0", "", "Guest", "Not today.", "She turns."))
        rows = S.parse_rows(t)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["end"], 2.5)
        self.assertTrue(rows[2]["open_end"])
        rep = S.run(t)
        self.assertEqual(level(rep, "T1"), "NOTE")      # continuity only partly checked
        self.assertIn("end is not written", next(r["detail"] for r in rep["results"] if r["code"] == "T1"))

    def test_other_tables_are_skipped(self):
        text = "| a | b |\n|---|---|\n| 1 | 2 |\n\n" + GOOD
        self.assertEqual(len(S.parse_rows(text)), 5)


class Checks(unittest.TestCase):
    def test_good_script_has_no_fail(self):
        rep = S.run(GOOD)
        self.assertEqual(rep["counts"]["FAIL"], 0, rep["results"])
        self.assertEqual(level(rep, "O1"), "PASS")
        self.assertEqual(level(rep, "E1"), "PASS")

    def test_flat_opening_fails_conflict(self):
        t = table(("0:00-0:04", "", "Host", "This is our product for the home.", "A shelf with a box on it."),
                  ("0:04-0:08", "", "Host", "It comes in two sizes and three colours.", "A hand lifts the box."))
        self.assertEqual(level(S.run(t), "O1"), "FAIL")

    def test_greeting_opening_fails(self):
        t = table(("0:00-0:03", "", "Host", "Hey guys, welcome back to the channel.", "She waves."))
        self.assertEqual(level(S.run(t), "O2"), "FAIL")

    def test_voiceover_in_first_three_seconds_warns(self):
        t = table(("0:00-0:03", "", "Narrator (VO)", "Nobody warned him.", "He drops the bag."))
        self.assertEqual(level(S.run(t), "O3"), "WARN")

    def test_long_sentence_fails_breath(self):
        long = "This is a thing that does a lot of useful work for you and your family every single day of the week without any fuss."
        t = table(("0:00-0:12", "", "Host", long, "She pours it."))
        self.assertEqual(level(S.run(t), "B1"), "FAIL")

    def test_fast_row_fails_rate(self):
        t = table(("0:00-0:01", "", "Host", "Which version are you giving your number to today?", "He points."))
        self.assertEqual(level(S.run(t), "B3"), "FAIL")

    def test_balance_band(self):
        all_talk = table(("0:00-0:10", "", "A", "Never again, I said to him.", "She walks."))
        self.assertEqual(level(S.run(all_talk), "A1"), "WARN")
        mixed = table(("0:00-0:05", "", "A", "Never again, I said.", "She walks."),
                      ("0:05-0:10", "", "A", "HOLD: no words.", "He turns and leaves."))
        self.assertEqual(level(S.run(mixed), "A1"), "PASS")

    def test_static_run_warns(self):
        rows = [("0:%02d-0:%02d" % (i, i + 1), "", "A", "Never again.", "Hold on her face.") for i in range(8)]
        self.assertEqual(level(S.run(table(*rows)), "A2"), "WARN")

    def test_micro_action_warns(self):
        t = table(("0:00-0:03", "", "A", "Never again.", "A slight flicker of the eyes."))
        self.assertEqual(level(S.run(t), "A3"), "WARN")

    def test_micro_next_to_real_action_passes(self):
        t = table(("0:00-0:03", "", "A", "Never again.", "A slight flicker of the eyes, then she slams the lid."))
        self.assertEqual(level(S.run(t), "A3"), "PASS")

    def test_repeated_line_warns(self):
        t = table(("0:00-0:03", "", "A", "You lied to me twice.", "He turns."),
                  ("0:03-0:06", "", "A", "You lied to me twice.", "She walks."))
        self.assertEqual(level(S.run(t), "R1"), "WARN")

    def test_gap_in_timing_warns(self):
        t = table(("0:00-0:03", "", "A", "Never again.", "He turns."),
                  ("0:05-0:08", "", "A", "Not today.", "She walks."))
        self.assertEqual(level(S.run(t), "T1"), "WARN")

    def test_ending_on_card_fails(self):
        t = table(("0:00-0:03", "", "A", "Never again.", "He turns."),
                  ("0:03-0:06", "", "A", "Thanks for watching.", "End card with the logo."))
        self.assertEqual(level(S.run(t), "E1"), "FAIL")

    def test_ending_with_no_action_warns(self):
        t = table(("0:00-0:03", "", "A", "Never again.", "He turns."),
                  ("0:03-0:06", "", "A", "Try it.", "The product on a white table."))
        self.assertEqual(level(S.run(t), "E1"), "WARN")


class Filmed(unittest.TestCase):
    LONG = "This is a thing that does a lot of useful work for you and your family every single day of the week."

    def test_filmed_fast_line_is_labelled_not_failed(self):
        t = table(("0:00-0:03", "", "Host", "Never again.", "He turns."),
                  ("0:03-0:03.6", "[SOURCE]", "Guest", "Because the skin is clear.", "Her filmed answer."))
        rep = S.run(t)
        self.assertEqual(level(rep, "B3"), "NOTE")
        detail = next(r["detail"] for r in rep["results"] if r["code"] == "B3")
        self.assertIn("filmed, can't change", detail)
        self.assertEqual(rep["filmed"], 1)

    def test_filmed_long_line_is_labelled_not_failed(self):
        t = table(("0:00-0:12", "[FILMED]", "Host", self.LONG, "She pours it."))
        rep = S.run(t)
        self.assertEqual(level(rep, "B1"), "NOTE")
        self.assertIn("filmed, can't change", S.render(rep))

    def test_interviewee_and_as_filmed_count_as_filmed(self):
        t = table(("0:00-0:03", "", "Interviewee", "The after.", "She answers."),
                  ("0:03-0:06", "", "Host", "Never again.", "As filmed."))
        self.assertTrue(all(r["filmed"] for r in S.parse_rows(t)))

    def test_unfilmed_fault_still_fails_beside_a_filmed_one(self):
        t = table(("0:00-0:01", "", "Host", "Which version are you giving your number to today?", "He points."),
                  ("0:01-0:01.6", "", "Interviewee", "Because the skin is clear.", "She answers."))
        rep = S.run(t)
        self.assertEqual(level(rep, "B3"), "FAIL")
        detail = next(r["detail"] for r in rep["results"] if r["code"] == "B3")
        self.assertIn("row 1:", detail)
        self.assertIn("filmed, can't change: row 2", detail)

    def test_header_counts_filmed_rows(self):
        t = table(("0:00-0:03", "", "Interviewee", "Never again.", "She turns."))
        self.assertIn("1 rows (1 filmed)", S.render(S.run(t)))


class Fixes(unittest.TestCase):
    def test_late_first_line_is_judged_by_the_silent_opening(self):
        t = table(("0:00-0:05", "", "—", "none", "She recoils from the mirror."),
                  ("0:05-0:08", "", "Host", "Hey guys, welcome back.", "He waves."))
        self.assertEqual(level(S.run(t), "O2"), "PASS")

    def test_ing_action_ends_mid_action(self):
        t = table(("0:00-0:03", "", "A", "Never again.", "He turns."),
                  ("0:03-0:06", "", "A", "Try it.", "A hand picking the box off the table."))
        self.assertEqual(level(S.run(t), "E1"), "PASS")


class ConflictPass(unittest.TestCase):
    def test_breath_fail_names_the_rows_over_14_too(self):
        long = "This is a thing that does a lot of useful work for you and your family every single day of the week without any fuss."
        mid = "It costs less than the thing it replaces and it lasts for years and years and years."
        t = table(("0:00-0:12", "", "Host", long, "She pours it."), ("0:12-0:20", "", "Host", mid, "He lifts it."))
        detail = next(r["detail"] for r in S.run(t)["results"] if r["code"] == "B1")
        self.assertIn("1 over 14", detail)
        self.assertIn("over 14: row 2", detail)

    def test_no_static_row_says_so(self):
        detail = next(r["detail"] for r in S.run(GOOD)["results"] if r["code"] == "A2")
        self.assertIn("no static row", detail)


class FilmedElsewhere(unittest.TestCase):
    """Round 3: a filmed line nobody can change is reported, never failed."""
    SOURCES = ("\n| Line | Source | Exact phrase | Final wording is |\n|---|---|---|---|\n"
               '| T1 | FILMED-CLIP (run ruling) | "Which version are you giving your number to today?" | verbatim (filmed) |\n'
               '| T2 | SWIPE-TRANSCRIPT T2 | "Never again." | verbatim |\n')

    def test_row_labelled_filmed_in_another_table_is_noted_not_failed(self):
        t = table(("0:00-0:01", "[SOURCE]", "Host", "Which version are you giving your number to today?", "He points."),
                  ("0:01-0:04", "[SOURCE]", "Narrator (VO)", "Never again.", "She walks.")) + self.SOURCES
        rep = S.run(t)
        rows = S.parse_rows(t)
        self.assertTrue(rows[0]["filmed"])
        self.assertFalse(rows[1]["filmed"])
        self.assertEqual(level(rep, "B3"), "NOTE")
        self.assertIn("filmed, can't change: row 1", S.render(rep))

    def test_without_the_other_table_the_same_row_still_fails(self):
        t = table(("0:00-0:01", "[SOURCE]", "Host", "Which version are you giving your number to today?", "He points."))
        self.assertEqual(level(S.run(t), "B3"), "FAIL")

    def test_filmed_greeting_opening_is_noted(self):
        t = table(("0:00-0:03", "[FILMED]", "Host", "Hey guys, welcome back to the channel.", "She waves."))
        rep = S.run(t)
        self.assertEqual(level(rep, "O2"), "NOTE")
        self.assertEqual(rep["counts"]["FAIL"], 0, rep["results"])

    def test_filmed_flat_opening_is_noted(self):
        t = table(("0:00-0:04", "[FILMED]", "Host", "This is our product for the home.", "A shelf with a box on it."))
        self.assertEqual(level(S.run(t), "O1"), "NOTE")

    def test_filmed_wrap_up_ending_is_noted(self):
        t = table(("0:00-0:03", "", "A", "Never again.", "He turns."),
                  ("0:03-0:06", "[FILMED]", "A", "Thanks for watching.", "She smiles at the lens."))
        self.assertEqual(level(S.run(t), "E1"), "NOTE")


AUDIT = """## CHECK TABLE

| # | Check | Result | Evidence |
|---|---|---|---|
| 2 | Source compressed | PASS | The opening holds at 0:00–0:04.0, as in the swipe. The timer beat grew from 2.1s to 2.6s. Nothing else moved. |
| 13 | Skit test | NOTE | One voice. The narrator's long run is the swipe's own. |
| — | Runtime sanity | HOLDS | Cut at 0:06 and what is left stands alone. The 28.0s piece has room. |

## OPEN SLOTS

| Slot | Who has it |
|---|---|
| Narrator voice, about 240 wpm | casting |
| Kitchen footage | footage index |

## WHAT I WOULD WATCH

The whole demo rides on one 1.9-second line. The rest is fine. If the cut is fast the timer reads as a toy.

## AUDIT PROVENANCE

The prompt was read in 30,000-character chunks at 4.0s each, an unmeasured read.
"""


class AuditQuotes(unittest.TestCase):
    """Round 3: the view quotes the audit's own caveats again, read from the audit, never hard-coded."""

    def quotes(self):
        return {a["where"]: a["quote"] for a in S.audit_lines(AUDIT)}

    def test_pace_checks_quote_their_timed_sentences(self):
        q = self.quotes()
        self.assertEqual(q["Check 2, Source compressed"],
                         "The opening holds at 0:00–0:04.0, as in the swipe. The timer beat grew from 2.1s to 2.6s.")
        self.assertEqual(q["Runtime sanity"], "The 28.0s piece has room.")

    def test_other_blocks_quote_only_caveats(self):
        q = self.quotes()
        self.assertEqual(q["Check 13, Skit test"], "The narrator's long run is the swipe's own.")
        self.assertEqual(q["Open slots"], "Narrator voice, about 240 wpm | casting")
        self.assertEqual(q["What I would watch"],
                         "The whole demo rides on one 1.9-second line. … If the cut is fast the timer reads as a toy.")
        self.assertEqual(len(q), 5)

    def test_provenance_is_never_quoted(self):
        self.assertFalse(any("chunks" in a["quote"] for a in S.audit_lines(AUDIT)))

    def test_view_keeps_every_check_line_and_adds_the_quotes(self):
        plain, quoted = S.render(S.run(GOOD)), S.render(S.run_with_audit(GOOD, AUDIT))
        self.assertTrue(quoted.startswith(plain + "\n"))
        self.assertIn('  - Open slots: "Narrator voice, about 240 wpm | casting"', quoted)

    def test_no_audit_prints_no_audit_line(self):
        self.assertNotIn("AUDIT", S.render(S.run(GOOD)))
        self.assertNotIn("audit_lines", S.run(GOOD))

    def test_audit_with_no_pace_line_says_so(self):
        out = S.render(S.run_with_audit(GOOD, "## VERDICT\n\nSHIP.\n"))
        self.assertIn("no line on breath or pace in the audit", out)


class Cli(unittest.TestCase):
    def run_cli(self, text, *args):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.md"
            p.write_text(text, encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = S.main([str(p), *args])
            return code, buf.getvalue()

    def test_report_only_exit_zero_even_with_fail(self):
        t = table(("0:00-0:04", "", "Host", "This is our product for the home.", "A shelf with a box on it."))
        code, out = self.run_cli(t)
        self.assertEqual(code, 0)
        self.assertIn("FAIL", out)

    def test_strict_is_opt_in(self):
        t = table(("0:00-0:04", "", "Host", "This is our product for the home.", "A shelf with a box on it."))
        code, _ = self.run_cli(t, "--strict")
        self.assertEqual(code, 1)

    def test_json(self):
        code, out = self.run_cli(GOOD, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["rows"], 5)

    def test_no_rows_prints_no_result(self):
        code, out = self.run_cli("just prose")
        self.assertEqual(code, 0)
        self.assertIn("0 rows checked: no result", out)
        self.assertNotIn("0 FAIL", out)

    def test_audit_beside_the_script_is_quoted(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "4e-close.md"
            p.write_text(GOOD, encoding="utf-8")
            (Path(d) / "4f-audit.md").write_text(AUDIT, encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = S.main([str(p)])
        self.assertEqual(code, 0)
        self.assertIn("1.9-second line", buf.getvalue())

    def test_missing_audit_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.md"
            p.write_text(GOOD, encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(S.main([str(p), "--audit", str(Path(d) / "none.md")]), 2)

    def test_missing_file(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(S.main(["/no/such/file.md"]), 2)


if __name__ == "__main__":
    unittest.main()
