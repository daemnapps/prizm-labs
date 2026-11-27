import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import messages as M

READ = dict(core="It reaches.", beliefs=["Hands fail"], delivery="A man.", angle=["The sink"], load_bearing=["One take"], swappable=[], desire="Clear skin")


def row(run, n, missing=(), read=READ, call="keep"):
    return {"run": run, "label": "Winner · " + run, "copy_of": None, "proof": {"purchases": n, "cpa": 50}, "watch": None, "traits": {},
            "teardown": {"missing": list(missing)}, "message_read": read, "retire": {"call": call}}


class T(unittest.TestCase):
    def setUp(self):
        self.r = Path(tempfile.mkdtemp())
        self.w = self.r / "runs/winners/acme"
        (self.w / "messages").mkdir(parents=True)

    def put(self, rows, winners, parked=()):
        (self.w / "winner-index.json").write_text(json.dumps({"winners": rows}))
        (self.w / "messages/messages.json").write_text(json.dumps({"parked": list(parked), "messages": [
            {"id": "a", "message": "m", "state": "draft", "winners": winners}]}))

    def g(self, run, carries="whole", cut=(), briefs=()):
        return {"run": run, "carries": carries, "cut": list(cut), "fill": [], "briefs": list(briefs)}

    def stuck(self):
        return {x["run"]: x["stuck"] for x in M.walk(self.r, "acme")}

    def test_each_gate_holds(self):
        self.put([row("a", 0), row("b", 5, ["spec"]), row("c", 5, read=dict(READ, core="")), row("d", 5), row("e", 5), row("f", 5), row("p", 5)],
                 [self.g("e", "swap"), self.g("f")], [{"run": "p", "why": "x"}])
        self.assertEqual(self.stuck(), {"a": "proof", "b": "teardown", "c": "message", "d": "group", "e": "rules", "f": None, "p": "parked"})

    def test_an_ungrouped_winner_fails_the_check(self):
        self.put([row("d", 5)], [])
        self.assertIn("stuck at group", M.check(self.r, "acme")[0])

    def test_next_is_whole_first_then_sales_and_never_a_break_or_a_briefed_one(self):
        self.put([row(x, n) for x, n in (("s", 90), ("w1", 10), ("w2", 20), ("x", 99), ("done", 80))],
                 [self.g("s", "swap", ["p"]), self.g("w1"), self.g("w2"), self.g("x", "breaks", ["p"]), self.g("done", briefs=["B1"])])
        self.assertEqual([x["run"] for x in M.ready(M.walk(self.r, "acme"))], ["w2", "w1", "s"])
        self.assertEqual(M.main(["start", "x", "--brand", "acme", "--root", str(self.r)]), 2)
        self.assertEqual(M.main(["start", "w1", "--brand", "acme", "--root", str(self.r)]), 0)

    def test_copies_and_retired_ads_are_not_winners(self):
        self.put([row("a", 5, call="retire"), dict(row("b", 5), copy_of="a")], [])
        self.assertEqual(M.walk(self.r, "acme"), [])

    def test_a_proven_video_nobody_tore_down_is_listed(self):
        self.put([row("a", 5)], [self.g("a")])
        d = self.w / "audit/2025-01-01_2025-12-31"
        d.mkdir(parents=True)
        (d / "board.json").write_text(json.dumps([{"name": "New One", "format": "Video", "purchases": 7, "cpa": 40, "link": "u"},
                                                  {"name": "Still", "format": "Image", "purchases": 9, "cpa": 40}]))
        self.assertEqual([x["label"] for x in M.untorn(self.r, "acme", M.walk(self.r, "acme"))], ["New One"])

    def test_the_page_builds(self):
        self.put([row("a", 5)], [self.g("a")])
        self.assertIn("It reaches.", M.page(self.r, "acme").read_text())


if __name__ == "__main__":
    unittest.main()
