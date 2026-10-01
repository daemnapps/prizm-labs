#!/usr/bin/env python3
"""briefs.py — the register under two spellings (Master Plan v2, 3.3).

    python3 tests/test_briefs.py

No network, no model. Every write goes to a temp copy of the register;
the real briefs.json is only ever READ (the last two tests, as the checker
would).
"""
import contextlib, io, json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import briefs as B  # noqa: E402
N = B.N

REAL = HERE / "briefs.json"


def fresh(**briefs):
    """A register with a <brand>-shaped block (starts at 1) and a second brand
    block at 140, in a temp file that briefs.py reads and writes instead."""
    reg = {"briefs": {}, "blocks": {"brand-a": 1, "brand-b": 140},
           "retired": {"p011": {"why": "test"}}}
    for k, v in briefs.items():
        reg["briefs"][k] = {"brand": v, "run": None, "opened": "x", "status": "open",
                            "declares": {}, "swipe": {}, "stages": [], "ads": []}
    return reg


class TempRegister(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self._real = B.REGISTER
        B.REGISTER = Path(self.td) / "briefs.json"
        self.addCleanup(lambda: setattr(B, "REGISTER", self._real))
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))

    def put(self, reg):
        B.REGISTER.write_text(json.dumps(reg))
        return B.load()


class Spellings(TempRegister):
    def test_key_and_get_take_either(self):
        reg = self.put(fresh(p003="brand-a", p140="brand-b"))
        self.assertEqual(B.key("brief-0003"), "p003")
        self.assertEqual(B.key("p003"), "p003")
        self.assertEqual(B.key("3"), "p003")
        for spelling in ("p140", "brief-0140", "140"):
            k, rec = B.get(reg, spelling)
            self.assertEqual(k, "p140")
            self.assertEqual(rec["brand"], "brand-b")
        self.assertEqual(B.get(reg, "brief-0099"), ("p099", None))

    def test_the_briefs_table_resolves_both_spellings_in_place(self):
        reg = self.put(fresh(p003="brand-a"))
        t = reg["briefs"]
        self.assertIsInstance(t, B.Briefs)
        self.assertIs(t["brief-0003"], t["p003"])
        self.assertIs(t.get("brief-0003"), t.get("p003"))
        self.assertIn("brief-0003", t)
        self.assertIn("p003", t)
        self.assertNotIn("brief-0004", t)
        self.assertIsNone(t.get("brief-0004"))
        with self.assertRaises(KeyError):
            t["brief-0004"]
        # one row per number, keyed on the old code, whatever it was written under
        t["brief-0005"] = {"brand": "brand-a"}
        self.assertEqual(sorted(t), ["p003", "p005"])
        self.assertEqual(t.pop("brief-0005")["brand"], "brand-a")
        self.assertEqual(list(t), ["p003"])
        self.assertIn("brief-0011", reg["retired"])

    def test_ids_maps_a_mixed_list_to_keys(self):
        self.assertEqual(B.ids({}, ["p003", " brief-0140 ", "", "7"]), ["p003", "p140", "p007"])

    def test_save_writes_a_plain_register_on_old_codes(self):
        reg = self.put(fresh(p003="brand-a"))
        reg["briefs"]["brief-0006"] = {"brand": "brand-a"}
        B.save(reg)
        raw = json.loads(B.REGISTER.read_text())
        self.assertEqual(sorted(raw["briefs"]), ["p003", "p006"])
        self.assertEqual(sorted(raw["retired"]), ["p011"])
        self.assertNotIn("brief-", "".join(raw["briefs"]))


class NextId(TempRegister):
    def test_new_spelling_for_every_type_in_one_block(self):
        reg = self.put(fresh(p001="brand-a", p002="brand-a"))
        for kind in B.TYPES:
            self.assertEqual(B.next_id(reg, "brand-a", kind), "brief-0003", kind)
        self.assertEqual(B.next_id(reg, "brand-a"), "brief-0003")          # default type
        self.assertEqual(B.next_id(reg, "brand-b", "video-creator"), "brief-0140")
        self.assertEqual(set(B.TYPES) >= {"image-ai", "video-ai", "email", "page", "copy",
                                          "concept", "sequence-ai"}, True)

    def test_unknown_type_is_refused(self):
        reg = self.put(fresh(p001="brand-a"))
        with self.assertRaises(SystemExit):
            B.next_id(reg, "brand-a", "poster")

    @unittest.skipUnless(N.brief_aliases().get("never_used"), "needs a filled brief register (the team's; the public kit starts empty)")
    def test_retired_and_never_used_numbers_stay_taken(self):
        reg = self.put(fresh(**{f"p{n:03d}": "brand-a" for n in range(1, 11)}))
        self.assertEqual(B.next_id(reg, "brand-a"), "brief-0012")           # p011 retired
        reg = self.put(fresh(**{f"p{n:03d}": "brand-a" for n in range(101, 128)}))
        reg["blocks"]["brand-a"] = 101
        # p128 / p130 / p134 were never used and never will be
        self.assertEqual(B.next_id(reg, "brand-a"), "brief-0129")
        reg["briefs"]["p129"] = {"brand": "brand-a"}
        self.assertEqual(B.next_id(reg, "brand-a"), "brief-0131")

    def test_a_record_filed_under_the_new_spelling_still_counts(self):
        reg = self.put(fresh(p001="brand-a"))
        dict.__setitem__(reg["briefs"], "brief-0002", {"brand": "brand-a", "brief": "brief-0002"})
        self.assertEqual(B.next_id(reg, "brand-a"), "brief-0003")

    def test_new_brand_gets_the_next_free_hundred(self):
        reg = self.put(fresh(p001="brand-a"))
        self.assertEqual(B.next_id(reg, "brand-c"), "brief-0101")
        self.assertEqual(reg["blocks"]["brand-c"], 101)


class Stamp(TempRegister):
    def test_every_entry_gets_id_and_brief_first(self):
        reg = self.put(fresh(p003="brand-a", p140="brand-b"))
        self.assertEqual(B.stamp(reg), 2)
        self.assertEqual(list(reg["briefs"]["p003"])[:2], ["id", "brief"])
        self.assertEqual(reg["briefs"]["p140"]["brief"], "brief-0140")
        self.assertEqual(B.stamp(reg), 0)                                    # idempotent

    def test_open_brief_writes_both_spellings_and_the_type(self):
        reg = self.put(fresh(p001="brand-a"))
        runs = Path(self.td) / "runs"
        (runs / "brand-a" / "r1" / "out").mkdir(parents=True)
        (runs / "brand-a" / "r1" / "out" / "06-brief.md").write_text("# brief\n")
        (runs / "brand-a" / "r1" / "source.json").write_text("{}")
        real_runs, B.RUNS = B.RUNS, runs
        real_aliases, B.ALIASES = B.ALIASES, Path(self.td) / "brief-aliases.json"
        try:
            bid, rec = B.open_brief("r1", "brand-a", reg, kind="video-ai")
        finally:
            B.RUNS, B.ALIASES = real_runs, real_aliases
            N._ALIASES = None
        self.assertEqual(bid, "p002")
        self.assertEqual((rec["id"], rec["brief"], rec["type"]), ("p002", "brief-0002", "video-ai"))
        self.assertIs(reg["briefs"]["brief-0002"], rec)


class Check(TempRegister):
    @unittest.skipUnless(N.brief_aliases().get("aliases"), "needs a filled brief register (the team's; the public kit starts empty)")
    def test_check_fails_on_a_register_that_is_not_stamped_or_doubled(self):
        reg = self.put(fresh(p003="brand-a"))
        ok, probs, n = B.check(reg)
        self.assertFalse(ok)
        self.assertTrue(any("not stamped" in p for p in probs))
        B.stamp(reg)
        self.assertTrue(B.check(reg)[0])
        dict.__setitem__(reg["briefs"], "brief-0003", dict(reg["briefs"]["p003"]))
        ok, probs, _ = B.check(reg)
        self.assertFalse(ok)
        self.assertTrue(any("also used" in p or "not the old code" in p for p in probs))


@unittest.skipUnless(N.brief_aliases().get("aliases"), "needs a filled brief register (the team's; the public kit starts empty)")
class RealRegister(unittest.TestCase):
    """Read-only against the lane's own briefs.json — what the checker does."""

    def test_all_briefs_resolve_under_both_spellings(self):
        reg = B.load()
        ok, probs, n = B.check(reg)
        self.assertEqual(probs, [])
        self.assertTrue(ok)
        self.assertGreaterEqual(n, 159)          # the register grows with every new brief
        for k, rec in dict.items(reg["briefs"]):
            self.assertIs(reg["briefs"][N.brief_id(k)], rec)
            self.assertEqual(rec["brief"], N.brief_aliases()["aliases"][k])

    def test_cli_check_prints_the_count(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            sys.argv = ["briefs.py", "check"]; B.main()
        self.assertEqual(cm.exception.code, 0)
        self.assertIn(f"{len(B.load()['briefs'])} briefs · all resolve under both spellings", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=1)
