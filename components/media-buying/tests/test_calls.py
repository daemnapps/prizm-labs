"""calls.py: the desk's recorded calls, summarized, with every disagreement kept. No network, no warehouse.
Run: /usr/bin/python3 components/media-buying/tests/test_calls.py"""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import calls as C  # noqa: E402


def line(at, flag, suggested, call, why, agreed=None, **numbers):
    return {"at": at, "by": "owner", "asof": at[:10], "flag": flag, "kind": "ad", "id": "1", "name": f"ad {flag}",
            "suggested": suggested, "call": call, "said": call, "why": why,
            "agreed": (suggested == call) if agreed is None else agreed,
            "numbers": {"spend": 100.0, "cpa": 40.0, **numbers}, "lines": {"x": 1}}


ROWS = [line("2026-11-01T10:00:00", "F1", "off", "off", "over the line for a week"),
        line("2026-11-02T10:00:00", "F2", "off", "keep", "new page,   give it the week", purchases=3),
        line("2026-11-03T10:00:00", "F3", "budget_up", "budget_hold", "the store week is thin"),
        line("2026-11-04T10:00:00", "F4", "off", "keep", "same page as F2")]


class Summary(unittest.TestCase):
    def test_counts_and_keeps_every_disagreement_newest_first(self):
        s = C.summary(ROWS)
        self.assertEqual((s["calls"], s["agreed"], s["disagreed"]), (4, 1, 3))
        self.assertEqual([d["flag"] for d in s["disagreements"]], ["F4", "F3", "F2"])
        d = s["disagreements"][2]
        self.assertEqual((d["suggested"], d["call"]), ("off", "keep"))
        self.assertEqual(d["why"], "new page, give it the week")           # the reason on record, spaces tidied
        self.assertEqual(d["numbers"], {"spend": 100.0, "purchases": 3, "cpa": 40.0})

    def test_groups_by_what_the_desk_suggested(self):
        by = C.summary(ROWS)["by_suggestion"]
        self.assertEqual(by["off"], {"calls": 3, "agreed": 1, "overruled_to": {"keep": 2}})
        self.assertEqual(by["budget_up"], {"calls": 1, "agreed": 0, "overruled_to": {"budget_hold": 1}})

    def test_no_calls_is_an_empty_summary(self):
        s = C.summary([])
        self.assertEqual((s["calls"], s["disagreements"], s["last"]), (0, [], []))

    def test_last_is_capped_and_newest_first(self):
        self.assertEqual([r["flag"] for r in C.summary(ROWS, last=2)["last"]], ["F4", "F3"])


class Read(unittest.TestCase):
    def test_reads_the_plane_file_and_skips_a_broken_line(self):
        with tempfile.TemporaryDirectory() as t:
            p = C.decisions_path(t, "acme")
            self.assertEqual(C.read(p), [])                                  # no file is no calls
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(ROWS[0]) + "\nnot json\n\n" + json.dumps(ROWS[1]) + "\n")
            self.assertEqual([r["flag"] for r in C.read(p)], ["F1", "F2"])
            self.assertEqual(C.for_brand(t, "acme")["disagreed"], 1)
            self.assertEqual(C.main(["acme", "--root", t]), 0)


if __name__ == "__main__":
    unittest.main()
