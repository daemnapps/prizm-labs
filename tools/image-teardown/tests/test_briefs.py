#!/usr/bin/env python3
"""briefs.py — the register under two spellings (Master Plan v2, 3.3).

    python3 tests/test_briefs.py

No network, no model. Every write goes to a temp copy of the register;
the real briefs.json is only ever READ (the last two tests, as the checker
would).
"""
import contextlib, io, json, shutil, sys, tempfile, unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import briefs as B  # noqa: E402
N = B.N

REAL = HERE / "briefs.json"


def fresh(**briefs):
    """A register with a brand-b-shaped block (starts at 1) and a second brand
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
    """the owner, 2026-10-01: "brief numbers count per brand AND product — each
    product starts at 1 inside its brand." """

    def put_products(self, rows, retired=None):
        reg = {"briefs": {}, "blocks": {"brand-a": 1, "brand-b": 140}, "retired": retired or {}}
        for k, brand, product in rows:
            reg["briefs"][k] = {"brand": brand, "product": product, "run": None, "opened": "x"}
        return self.put(reg)

    def test_each_product_counts_from_its_own_highest(self):
        reg = self.put_products([("p001", "brand-a", "widget"), ("p002", "brand-a", "widget"),
                                 ("p003", "brand-a", "brush"), ("p140", "brand-b", "scrub")])
        for kind in B.TYPES:
            self.assertEqual(B.next_id(reg, "brand-a", kind, "widget"), "brief-0003", kind)
        self.assertEqual(B.next_id(reg, "brand-a", None, "brush"), "brief-0004")
        self.assertEqual(B.next_id(reg, "brand-b", "video-creator", "scrub"), "brief-0141")
        self.assertEqual(set(B.TYPES) >= {"image-ai", "video-ai", "email", "page", "copy",
                                          "concept", "sequence-ai"}, True)

    def test_a_new_product_or_brand_starts_at_one(self):
        reg = self.put_products([("p001", "brand-a", "widget"), ("p140", "brand-b", "scrub")])
        self.assertEqual(B.next_id(reg, "brand-a", None, "gadget"), "brief-0001")
        self.assertEqual(B.next_id(reg, "brand-b", None, "widget"), "brief-0001")   # brands never share
        self.assertEqual(B.next_id(reg, "brand-c", None, "anything"), "brief-0001")
        self.assertNotIn("brand-c", reg["blocks"])                               # no more hundreds

    def test_old_briefs_with_no_product_do_not_block_a_product(self):
        reg = self.put_products([("p001", "brand-a", None), ("p002", "brand-a", None),
                                 ("p005", "brand-a", "widget")])
        self.assertEqual(B.next_id(reg, "brand-a", None, "widget"), "brief-0006")
        self.assertEqual(B.next_id(reg, "brand-a", None, "gadget"), "brief-0001")
        self.assertEqual(B.next_id(reg, "brand-a"), "brief-0003")      # the brand's product-less briefs

    def test_unknown_type_is_refused(self):
        reg = self.put(fresh(p001="brand-a"))
        with self.assertRaises(SystemExit):
            B.next_id(reg, "brand-a", "poster", "widget")

    def test_retired_numbers_stay_taken_in_their_product(self):
        reg = self.put_products([(f"p{n:03d}", "brand-a", "widget") for n in range(1, 11)],
                                retired={"p011": {"brand": "brand-a", "product": "widget", "why": "test"}})
        self.assertEqual(B.next_id(reg, "brand-a", None, "widget"), "brief-0012")    # p011 retired

    def test_a_new_per_product_brief_counts_and_never_reissues(self):
        reg = self.put_products([("p001", "brand-a", "widget")])
        dict.__setitem__(reg["briefs"], "brand-a_gadget_brief-0001",
                         {"brand": "brand-a", "product": "gadget", "brief": "brief-0001"})
        self.assertEqual(B.next_id(reg, "brand-a", None, "gadget"), "brief-0002")
        self.assertEqual(B.next_id(reg, "brand-a", None, "widget"), "brief-0002")



class PerProductKeys(TempRegister):
    def reg(self):
        reg = self.put({"briefs": {
            "p001": {"id": "p001", "brief": "brief-0001", "brand": "brand-a", "product": None},
            "p005": {"id": "p005", "brief": "brief-0005", "brand": "brand-a", "product": "widget"},
            "p140": {"id": "p140", "brief": "brief-0140", "brand": "brand-b", "product": "scrub"},
            "brand-a_gadget_brief-0001": {"id": "brand-a_gadget_brief-0001", "brief": "brief-0001",
                                         "brand": "brand-a", "product": "gadget"}}})
        return reg

    def test_old_ids_unchanged(self):
        reg = self.reg()
        self.assertEqual(B.key("brief-0005"), "p005")
        self.assertEqual(B.get(reg, "brief-0005")[0], "p005")
        self.assertEqual(B.get(reg, "p140", "brand-b")[0], "p140")
        self.assertIs(reg["briefs"]["brief-0001"], reg["briefs"]["p001"])   # a bare number in the table = the old row

    def test_a_per_product_key_is_its_own_key(self):
        reg = self.reg()
        k = "brand-a_gadget_brief-0001"
        self.assertEqual(B.key(k), k)
        self.assertEqual(B.get(reg, k)[1]["product"], "gadget")
        self.assertIn(k, reg["briefs"])
        self.assertEqual(N.brief_id(k), "brief-0001")

    def test_the_product_picks_between_briefs_sharing_a_number(self):
        reg = self.reg()
        self.assertEqual(B.get(reg, "brief-0001", "brand-a", "gadget")[0], "brand-a_gadget_brief-0001")
        self.assertEqual(B.get(reg, "p001", "brand-a", "widget")[0], "p001")       # no widget 0001: the old one

    def test_brand_and_number_alone_is_refused_when_shared(self):
        reg = self.reg()
        with self.assertRaises(N.AmbiguousBrief) as cm:
            B.get(reg, "brief-0001", "brand-a")
        self.assertIn("brief-0001 is used by more than one BRAND-A product", str(cm.exception))
        self.assertIn("say which", str(cm.exception))

    def test_open_brief_keys_a_new_brief_by_brand_product_number(self):
        reg = self.reg()
        runs = Path(self.td) / "runs"
        (runs / "brand-a" / "r1" / "out").mkdir(parents=True)
        (runs / "brand-a" / "r1" / "out" / "06-brief.md").write_text("# brief\n")
        (runs / "brand-a" / "r1" / "source.json").write_text("{}")
        real_runs, B.RUNS = B.RUNS, runs
        aliases = Path(self.td) / "aliases.json"
        aliases.write_text('{"aliases": {}}')
        real_al, B.ALIASES = B.ALIASES, aliases
        try:
            bid, rec = B.open_brief("r1", "brand-a", reg, product="gadget", kind="image-ai")
        finally:
            B.RUNS, B.ALIASES = real_runs, real_al
        self.assertEqual(bid, "brand-a_gadget_brief-0002")
        self.assertEqual((rec["id"], rec["brief"], rec["product"]), (bid, "brief-0002", "gadget"))
        self.assertEqual(B.load()["briefs"]["p001"]["brief"], "brief-0001")      # nothing old overwritten
        self.assertEqual(json.loads(aliases.read_text())["aliases"], {})          # the global map is old codes only



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
        try:
            bid, rec = B.open_brief("r1", "brand-a", reg, product="widget", kind="video-ai")
        finally:
            B.RUNS = real_runs
        # numbers count per brand AND product (2026-10-01): the old p001 has no
        # product, so the device starts at 1 — keyed by all three, never p001
        self.assertEqual(bid, "brand-a_widget_brief-0001")
        self.assertEqual((rec["id"], rec["brief"], rec["type"]), (bid, "brief-0001", "video-ai"))
        self.assertIs(reg["briefs"][bid], rec)
        self.assertIsNot(reg["briefs"]["brief-0001"], rec)


class Check(TempRegister):
    def test_check_takes_a_per_product_key_and_catches_a_wrong_one(self):
        reg = self.put(fresh(p003="brand-a"))
        B.stamp(reg)
        dict.__setitem__(reg["briefs"], "brand-a_gadget_brief-0003",
                         {"id": "brand-a_gadget_brief-0003", "brief": "brief-0003", "brand": "brand-a", "product": "gadget"})
        self.assertEqual(B.check(reg)[1], [])
        reg["briefs"]["brand-a_gadget_brief-0003"]["product"] = "widget"
        self.assertTrue(any("key says" in p for p in B.check(reg)[1]))

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


class RealRegister(unittest.TestCase):
    """Read-only against the lane's own briefs.json — what the checker does."""

    def test_all_briefs_resolve_under_both_spellings(self):
        reg = B.load()
        ok, probs, n = B.check(reg)
        self.assertEqual(probs, [])
        self.assertTrue(ok)
        self.assertGreaterEqual(n, 159)          # the register grows with every new brief
        for k, rec in dict.items(reg["briefs"]):
            if N.parse_brief_key(k):          # numbered per brand+product: no old code
                self.assertIs(reg["briefs"][k], rec)
                continue
            self.assertIs(reg["briefs"][N.brief_id(k)], rec)
            self.assertEqual(rec["brief"], N.brief_aliases()["aliases"][k])

    def test_the_brand_file_counts_too(self):
        """Brand B GADGET brief-0001..0003 live in brands/<brand>/briefs/briefs.json."""
        reg = B.load()
        # brief-0001..0003 are in the brand file only, so the next is past them;
        # the register's own GADGET briefs (from 0004, the first carousel) count too
        gadget = [int(r["brief"].split("-")[1]) for k, r in dict.items(reg["briefs"])
                 if r.get("brand") == "brand-b" and r.get("product") == "gadget" and r.get("brief")]
        self.assertEqual(B.next_id(reg, "brand-b", None, "gadget"), f"brief-{max([3] + gadget) + 1:04d}")
        self.assertEqual(B.next_id(reg, "brand-a", None, "glow-face-scrub"), "brief-0286")
        self.assertEqual(B.next_id(reg, "brand-a", None, "a-product-not-made-yet"), "brief-0001")
        self.assertEqual(B.next_id(reg, "brand-b", None, "widget"), "brief-0019")

    def test_cli_check_prints_the_count(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            sys.argv = ["briefs.py", "check"]; B.main()
        self.assertEqual(cm.exception.code, 0)
        self.assertIn(f"{len(B.load()['briefs'])} briefs · all resolve under both spellings", out.getvalue())


class Landing(TempRegister):
    """The landing page is chosen when the brief is written (page_pick); a
    brief that already has links keeps them; a failed pick never stops a brief."""
    def test_a_brief_with_no_page_gets_one(self):
        reg = fresh(p003="brand-a")
        reg["briefs"]["p003"]["product"] = "widget"
        self.put(reg)
        import page_pick as PP
        lp = {"link_ids": ["link_brand-a_cpk_quiz"], "why": "the main live page"}
        with mock.patch.object(PP, "pick", lambda *a, **k: lp):
            rec, got = B.with_landing("p003", "brand-a")
        self.assertEqual(got, lp)
        rec = B.load()["briefs"]["p003"]
        self.assertEqual(rec["landing_page"]["why"], "the main live page")
        self.assertEqual(rec["links"], ["link_brand-a_cpk_quiz"])

    def test_links_already_set_stay(self):
        reg = fresh(p003="brand-a")
        reg["briefs"]["p003"]["links"] = ["link_brand-a_x"]
        self.put(reg)
        import page_pick as PP
        with mock.patch.object(PP, "pick", side_effect=AssertionError("must not pick")):
            rec, got = B.with_landing("p003", "brand-a")
        self.assertIsNone(got)
        self.assertEqual(B.load()["briefs"]["p003"]["links"], ["link_brand-a_x"])

    def test_a_failed_pick_is_said_not_raised(self):
        self.put(fresh(p003="brand-a"))
        import page_pick as PP
        with mock.patch.object(PP, "pick", side_effect=RuntimeError("catalog unreadable")):
            rec, got = B.with_landing("p003", "brand-a")
        self.assertEqual(got["link_ids"], [])
        self.assertIn("catalog unreadable", got["why"])
        self.assertNotIn("landing_page", B.load()["briefs"]["p003"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
