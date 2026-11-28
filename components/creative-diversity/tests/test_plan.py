"""The plan: an ad that is the same creative as one taken is never added (made-up ads and folder; no model)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

W = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(W / "components" / "creative-diversity"))
import creative_plan as PL  # noqa: E402

A = {"profile": "p1", "awareness": "problem-aware", "angle": "a1", "format": "list", "face": "f1", "setting": "s1", "look": "l1"}


class Plan(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.m = [mock.patch.dict(os.environ, {"CREATIVE_PLAN_ROOT": self.t.name}), mock.patch.object(PL, "running", lambda b: ([], None))]
        for m in self.m:
            m.start()

    def tearDown(self):
        for m in self.m:
            m.stop()
        self.t.cleanup()

    def test_same_is_not_added_close_is_flagged_new_is_new(self):
        self.assertEqual(PL.claim("acme", "a", A)["verdict"], "new")
        self.assertEqual(PL.claim("acme", "b", dict(A, setting="s2"))["verdict"], "same")
        self.assertNotIn("b", PL.ledger("acme"))
        self.assertEqual(PL.claim("acme", "c", dict(A, setting="s2", look="l2"))["verdict"], "close")
        self.assertEqual(PL.claim("acme", "d", dict(A, profile="p2", angle="a2", face="f2"))["verdict"], "new")

    def test_the_same_ad_may_claim_again_and_a_dropped_one_frees_its_place(self):
        PL.claim("acme", "a", A)
        self.assertEqual(PL.claim("acme", "a", dict(A, look="l2"))["verdict"], "new")
        PL.tie("acme", "a", "brief-0001")
        PL.mark("acme", "brief-0001", "dropped")
        self.assertEqual(PL.claim("acme", "b", A)["verdict"], "new")

    def test_an_ad_we_know_little_about_is_never_called_the_same(self):
        PL.claim("acme", "a", {k: ("unclear" if k not in ("profile", "awareness") else v) for k, v in A.items()})
        self.assertEqual(PL.claim("acme", "b", A)["verdict"], "new")

    def test_running_ads_count(self):
        with mock.patch.object(PL, "running", lambda b: ([("live-1", A)], "2026-01-01")):
            v = PL.claim("acme", "a", dict(A, look="l2"))
            self.assertEqual((v["verdict"], v["where"], v["nearest"]), ("same", "running", "live-1"))

    def test_the_board_says_what_is_taken_and_what_is_worn(self):
        self.assertEqual(PL.board("acme", "p1"), "")
        PL.claim("acme", "a", A)
        b = PL.board("acme", "sub-02-p1")
        for x in ("Taken for this person", "list", "Worn the most", "s1 (1)"):
            self.assertIn(x, b)

    def test_a_runs_own_decisions_win(self):
        m = PL.known(dict(A, profile="unclear", face="male/25-34/white"), {"sub": "sub-02-bald", "awareness": "unaware", "demographic": "male-35-44-black"})
        self.assertEqual((m["profile"], m["awareness"], m["face"]), ("bald", "unaware", "male/35-44/black"))
        self.assertEqual(PL.known(dict(A, face="none"), {"demographic": "m/25-34/black"})["face"], "none")
        self.assertEqual(PL.known({}, {"demographic": "f/55-64/white"})["face"], "female/55-64/white")

    def test_another_tools_check_never_stands_in_for_ours(self):
        import subprocess
        code = ("import sys, types; sys.modules['check'] = types.ModuleType('check'); sys.path.insert(0, %r); import creative_plan as plan; "
                "assert hasattr(plan.K, 'library') and not hasattr(sys.modules['check'], 'library'); print(plan._own('brief_view').MIN)" % str(W / "components" / "creative-diversity"))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_all_seven(self):
        with self.assertRaises(ValueError):
            PL.claim("acme", "a", dict(A, look=""))

    def test_every_door_goes_through_it(self):
        c = W / "components"
        for f, x in (("creative-strategist/machine/who.py", "PL.board(brand, who)"), ("creative-strategist/machine/strategy.py", '"creative": True'),
                     ("image-writing/tools/writing.py", "PL.claim(brand, Path(run).name"), ("video-writing/machine/writing_v2.py", 'what["creative"] = True'),
                     ("marketing-chain-checks/marketing_chain_checks/viewer.py", "PL.look_at(brand, ident, mv)"), ("meta-upload/to_check.py", '.mark(brand, brief, "filed")')):
            self.assertIn(x, (c / f).read_text(), f)

    def test_the_image_step_is_sent_back_once_then_held(self):
        sys.path.insert(0, str(W / "components/image-writing/tools"))
        sys.path.insert(0, str(W / "components/image-teardown/tools"))
        import writing as IW
        d = Path(self.t.name) / "run-9"
        (d / "out").mkdir(parents=True)
        (d / "out" / IW.STAGES["3"][1]).write_text("x")
        PL.claim("acme", "a", A)
        back, held = [], []
        mods = {k: v for k, v in sys.modules.items() if k != "unittest"}
        with mock.patch.object(IW, "moves_of", lambda *a: dict(A, setting="s2")), mock.patch.object(IW, "_again", lambda *a: back.append(a)), \
                mock.patch.object(IW.G, "_gate", lambda *a: held.append(a)), mock.patch.object(IW, "_plan", lambda: PL), mock.patch.object(IW, "sys", mock.Mock(modules=mods, path=sys.path)):
            self.assertEqual(IW.diversity_gate(d, Path("p"), [], "acme")["verdict"], "same")
        self.assertEqual((len(back), len(held)), (1, 1))


if __name__ == "__main__":
    unittest.main()
