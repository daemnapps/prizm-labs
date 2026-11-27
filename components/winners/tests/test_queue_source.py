"""Results reach the queue: every winner in the bank becomes one piece in the shadow queue, and the live queue is
refused while its switch is off. Offline, a scratch workspace.

    /usr/bin/python3 components/winners/tests/test_queue_source.py
"""
import contextlib, io, json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import bank  # noqa: E402
import queue_source as Q  # noqa: E402
from test_bank import audit, row, w  # noqa: E402

NOW = "2026-11-18T12:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.repo = Path(self._t.name)
        (self.repo / "components").mkdir()
        (self.repo / "brands").mkdir()
        rows = [row(1, "Script 30", ["111"], 1000, 50, 1500), row(2, "Touch Face", ["221"], 800, 20, 900),
                row(3, "Dud", ["441"], 900, 5, 300)]
        a1 = audit(self.repo, "2025", "2025-01-01", "2026-11-02", rows)
        bank.main(["--brand", "acme", "--root", str(self.repo), "--audit", str(a1)])
        self.shadow = self.repo / "runs" / "queue-shadow"

    def tearDown(self):
        self._t.cleanup()

    def set_bar(self, **bar):
        b = bank.load_bank(bank.bank_path(self.repo, "acme"), "acme")
        b["bar"].update(bar)
        bank.write(self.repo, b)

    def run_source(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = Q.main(["--repo", str(self.repo), "--now", NOW, *args])
        return code, out.getvalue()

    def observation(self):
        return json.loads((self.shadow / "observations" / "winners.json").read_text())


class OpenBar(Base):
    def test_an_open_bar_queues_nothing_and_writes_no_file(self):
        code, said = self.run_source()
        self.assertEqual(code, 0)
        self.assertIn("acme: nothing to queue (the bar is open, so no row is a winner)", said)
        self.assertFalse((self.shadow / "observations" / "winners.json").exists())


class Winners(Base):
    def setUp(self):
        super().setUp()
        self.set_bar(max_cpa=45)                                       # 111 (CPA 20) and 221 (CPA 40) clear; 441 does not

    def test_every_winner_is_one_piece_in_the_shadow_queue_top_first(self):
        code, said = self.run_source()
        self.assertEqual(code, 0, said)
        o = self.observation()
        self.assertEqual((o["source"], o["as_of"]), ("winners", NOW))
        self.assertEqual(sorted(o["entries"]), ["acme_idea_brand_iterate_111", "acme_idea_brand_iterate_221"])
        e = o["entries"]["acme_idea_brand_iterate_111"]
        self.assertEqual((e["lane"], e["type"], e["winner"], e["rank"], e["role"]),
                         ("iteration", "video-ad", "acme-111", 1, "video editor"))
        self.assertEqual(e["numbers"], {"purchases": 50, "spend": 1000.0, "cpa": 20.0, "roas": 1.5})
        self.assertEqual(e["bar"], "$45 a purchase or less")
        self.assertEqual(e["observed_stage"], "idea")
        self.assertIn("no variation plan yet", e["next_step"])
        self.assertIn("50 purchases, $20 a purchase, ROAS 1.50, 2025-01-01 to 2026-11-02", e["why"])

    def test_a_winner_with_a_plan_carries_its_next_ask(self):
        b = bank.load_bank(bank.bank_path(self.repo, "acme"), "acme")
        r = next(x for x in b["rows"] if x["id"] == "acme-111")
        r["run"], r["brief_key"] = "runs/video-writing/acme/proven-one", "acme_widget_brief-0007"
        bank.write(self.repo, b)
        plan = self.repo / "runs/ad-variations/acme/proven-one-matrix"
        w(plan, "variation-plan.json", {"source": {"teardown_run": "runs/video-teardown/acme/proven-one"}})
        w(plan, "next-ask.json", {"plan": "runs/ad-variations/acme/proven-one-matrix/variation-plan.json",
                                  "next": {"id": "V02", "ask": "runs/ad-variations/acme/proven-one-matrix/asks/x/ask.json"},
                                  "asked": ["V02"], "held": [], "left": []})
        self.run_source()
        e = self.observation()["entries"]["acme_idea_widget_iterate_111"]
        self.assertEqual((e["product"], e["variation"], e["observed_stage"]), ("widget", "V02", "brief"))
        self.assertEqual(e["ask"], "runs/ad-variations/acme/proven-one-matrix/asks/x/ask.json")
        self.assertEqual(e["next_step"], "the next ask is on file: variation V02")

    def test_a_paid_winner_with_no_run_reaches_its_plan_by_its_row_id(self):
        plan = self.repo / "runs/ad-variations/acme/top-one-matrix"
        w(plan, "variation-plan.json", {"source": {"teardown_run": "runs/video-teardown/acme/top-one"}})
        w(plan, "next-ask.json", {"winner": "acme-221", "next": {"id": "V01", "ask": "a/ask.json"},
                                  "asked": ["V01"], "held": [], "left": []})
        self.run_source()
        self.assertEqual(self.observation()["entries"]["acme_idea_brand_iterate_221"]["variation"], "V01")

    def test_the_same_results_write_nothing_new_and_a_lost_winner_leaves_the_file(self):
        self.run_source()
        first = (self.shadow / "observations" / "winners.json").read_text()
        _, said = self.run_source("--now", "2026-11-19T12:00:00Z")
        self.assertIn("unchanged", said)
        self.assertEqual((self.shadow / "observations" / "winners.json").read_text(), first)
        self.set_bar(max_cpa=1)                                        # now nothing clears
        self.run_source()
        self.assertEqual(self.observation()["entries"], {})

    def test_a_dry_run_writes_nothing(self):
        code, said = self.run_source("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("2 winners to iterate on", said)
        self.assertFalse(self.shadow.exists())

    def test_the_live_queue_is_refused_while_its_switch_is_off(self):
        code, said = self.run_source("--root", str(self.repo / "runs" / "queue"))
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", said)
        self.assertFalse((self.repo / "runs" / "queue").exists())

    def test_a_creator_video_is_a_video_piece_for_the_creator_manager(self):
        b = bank.load_bank(bank.bank_path(self.repo, "acme"), "acme")
        b["rows"].append({"id": "acme-trybe-ab12", "state": "candidate", "name": "creator one", "ad_ids": ["901"],
                          "trybe_id": "ab12cd34",
                          "snapshots": [{"kind": "creator", "since": "2026-10-01", "until": "2026-11-01",
                                         "pulled_at": "2026-11-02", "purchases": 3, "spend": 90.0, "cpa": 30.0,
                                         "roas": 2.0}]})
        bank.write(self.repo, b)
        self.run_source()
        e = self.observation()["entries"]["acme_idea_brand_iterate_trybe-ab12"]
        self.assertEqual((e["type"], e["role"]), ("video-ad", "creator manager"))


if __name__ == "__main__":
    unittest.main()
