import contextlib, io, json, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.insert(0, str(COMPONENT))
sys.path.insert(0, str(HERE))
import winners  # noqa: E402
import audit as A  # noqa: E402
import score as S  # noqa: E402
from test_bank import TEARDOWN, audit, row, w  # noqa: E402


def run(root, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = winners.main([*args, "--root", str(root)])
    return code, out.getvalue(), err.getvalue()


class T(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self._repo = A.REPO
        self.addCleanup(setattr, A, "REPO", self._repo)
        rows = [row(1, "Script 30", ["111", "112"], 1000, 50, 1500),
                row(2, "Touch Face", ["221"], 800, 20, 900),
                row(3, "Dud", ["441"], 900, 5, 300)]
        self.label = "2025-01-01_2026-11-02"
        self.a1 = audit(self.root, self.label, "2025-01-01", "2026-11-02", rows)
        w(self.a1, "teardowns/01-script-30/teardown.md", TEARDOWN)
        self.dir = self.root / "runs/winners/acme"
        self.bank = self.dir / "bank.json"
        self.feed = self.dir / "feed.md"

    def tearDown(self):
        self._t.cleanup()

    def test_bad_input_is_one_sentence_and_non_zero(self):
        for args in (["bank", "--brand", "nobrand"], ["feed"], ["bank", "--brand", "acme", "--window", "nope"],
                     ["audit", "--brand", "acme", "--since", "x", "--until", "2026-01-01"],
                     ["audit", "--brand", "acme", "--since", "2026-02-01", "--until", "2026-01-01"],
                     ["tag", "--brand", "acme", "--window", self.label, "--tags", "/no/such/file"],
                     ["videos", "--brand", "acme", "--window", self.label, "--top", "0"],
                     ["score", "--brand", "acme", "--days", "0"], ["nothing"], []):
            code, _, err = run(self.root, *args) if args else (winners.main([]), "", "x.")
            self.assertEqual(code, 2, args)
            self.assertEqual(len(err.strip().splitlines()), 1, args)
            self.assertTrue(err.strip().endswith("."), err)

    def test_bank_and_feed_are_byte_stable_and_newest_by_default(self):
        self.assertEqual(run(self.root, "bank", "--brand", "acme")[0], 0)
        first = self.bank.read_text()
        self.assertEqual(run(self.root, "bank", "--brand", "acme", "--window", self.label)[0], 0)
        self.assertEqual(self.bank.read_text(), first)
        self.assertEqual(run(self.root, "feed", "--brand", "acme")[0], 0)
        md = self.feed.read_text()
        self.assertEqual(run(self.root, "feed", "--brand", "acme")[0], 0)
        self.assertEqual(self.feed.read_text(), md)
        audit(self.root, "2026-01-01_2026-12-01", "2026-01-01", "2026-12-01", [row(1, "Fresh", ["999"], 100, 9, 200)])
        run(self.root, "bank", "--brand", "acme")
        self.assertIn("acme-999", {r["id"] for r in [*json.loads(self.bank.read_text())["rows"]]})

    def test_bar(self):
        run(self.root, "bank", "--brand", "acme")
        code, out, _ = run(self.root, "bar", "--brand", "acme")
        self.assertEqual(code, 0)
        self.assertIn("acme bar: open", out)
        code, out, _ = run(self.root, "bar", "--brand", "acme", "--max-cpa", "30")
        self.assertEqual(code, 0)
        self.assertIn("1 winners, 2 candidates", out)
        d = json.loads(self.bank.read_text())
        self.assertEqual(d["bar"], {"min_spend": None, "max_cpa": 30.0, "min_roas": None})
        self.assertEqual({r["id"]: r["state"] for r in d["rows"]},
                         {"acme-111": "winner", "acme-221": "candidate", "acme-441": "candidate"})
        md = self.feed.read_text()
        self.assertNotIn("acme-221", md[md.index("## Winners"):md.index("## Loser")])
        self.assertIn("$30 a purchase or less", run(self.root, "bar", "--brand", "acme")[1])
        code, out, _ = run(self.root, "bar", "--brand", "acme", "--min-spend", "900")   # adds to what's set
        self.assertIn("at least $900 spent, $30 a purchase or less", out)
        self.assertEqual(run(self.root, "bar", "--brand", "acme", "--open")[0], 0)
        d = json.loads(self.bank.read_text())
        self.assertTrue(all(r["state"] == "candidate" for r in d["rows"]))
        self.assertEqual(run(self.root, "bar", "--brand", "acme", "--max-cpa", "-1")[0], 2)

    def test_status(self):
        run(self.root, "bank", "--brand", "acme")
        for b in ("acme", "all"):
            code, out, _ = run(self.root, "status", "--brand", b)
            self.assertEqual(code, 0)
            self.assertIn("ACME", out)
            self.assertIn("Bank rows 3", out)
            self.assertIn("1. Script 30: 50 purchases", out)
            self.assertNotIn("runs/", out)
            self.assertNotIn("111", out)

    def test_audit_stops_at_missing_tags_and_tag_finishes(self):
        calls = []

        def stamp(name):
            def f(a):
                calls.append(name)
                if name == "sheets":
                    w(self.a1, "to_tag.json", [{"label": "R2", "name": "Touch Face", "format": "Video"}])
                if name == "pull":
                    w(self.a1, "cells.json", [{"name": "x"}])
            return f
        with mock.patch.multiple(A, **{n: stamp(n) for n in winners.AUDIT_STEPS}):
            code, out, _ = run(self.root, "audit", "--brand", "acme", "--since", "2025-01-01", "--until", "2026-11-02")
        self.assertEqual(code, 0)
        self.assertEqual(calls, list(winners.AUDIT_STEPS))
        self.assertIn("1 creatives still need tags", out)
        self.assertIn("Next step: tag", out)
        self.assertFalse(self.bank.exists())
        tags = self.root / "t.json"
        tags.write_text(json.dumps({"R2": {"on_screen": "Product shot", "message": "m"}}))
        with mock.patch.object(A, "build", lambda a: calls.append("build2")):
            code, out, _ = run(self.root, "tag", "--brand", "acme", "--window", self.label, "--tags", str(tags))
        self.assertEqual(code, 0)
        self.assertIn("build2", calls)
        self.assertTrue(self.bank.exists() and self.feed.exists())
        self.assertIn("Touch Face", json.loads((self.dir / "tags.json").read_text()))

    def test_audit_with_nothing_to_tag_banks_and_feeds(self):
        def noop(a):
            if not (self.a1 / "to_tag.json").exists():
                w(self.a1, "to_tag.json", [])
            w(self.a1, "cells.json", [{"name": "x"}])
        with mock.patch.multiple(A, **{n: noop for n in winners.AUDIT_STEPS}):
            code, out, _ = run(self.root, "audit", "--brand", "acme", "--since", "2025-01-01", "--until", "2026-11-02")
        self.assertEqual(code, 0)
        self.assertTrue(self.bank.exists() and self.feed.exists())

    def test_score_banks_chain_made_ads_and_rebuilds_the_feed(self):
        run(self.root, "bank", "--brand", "acme")
        fake = {"asof": "2026-11-04", "since": "2026-08-06", "data_through": "2026-11-03", "source": "warehouse meta_ad_insights",
                "used": "the warehouse, trailing 90 days", "ads": []}
        joined = {"brand": "acme", "asof": "2026-11-04", "since": "2026-08-06", "data_through": "2026-11-03",
                  "results_from": fake["used"], "sources": [], "counts": {"ads": 1, "matched": 1, "unmatched": 0, "matched_spend": 1, "unmatched_spend": 0, "brief_keys_in_register": 1},
                  "by_hook_prompt": [], "by_brief_prompt": [], "by_borrowed_from": [], "unmatched": [],
                  "matched": [{"ad_id": "777", "ad_name": "acme_x_brief-0001_batch-a", "spend": 10.0, "purchases": 1.0, "value": 20.0, "roas": 2.0,
                               "run": "runs/video-writing/acme/r1", "cpa": 10.0, "brief_key": "k", "joined_by": "x", "borrowed_from": ["none"],
                               "hook_prompt": {"label": "h"}, "brief_prompt": {"label": "b"}}]}
        with mock.patch.object(S, "results", lambda *a, **k: fake), mock.patch.object(S, "build", lambda *a, **k: joined):
            code, out, _ = run(self.root, "score", "--brand", "acme")
            self.assertEqual(code, 0, out)
            first = self.bank.read_text()
            self.assertEqual(run(self.root, "score", "--brand", "acme")[0], 0)
        self.assertEqual(self.bank.read_text(), first)
        self.assertIn("from the warehouse", out)
        d = json.loads((self.dir / "score/2026-11-04/score.json").read_text())
        self.assertEqual(d["asof"], "2026-11-04")
        self.assertIn("acme-777", {r["id"] for r in json.loads(first)["rows"]})
        self.assertTrue(self.feed.exists())

    def test_a_step_that_stops_is_one_sentence(self):
        def boom(a):
            raise SystemExit("Meta said no\nmore detail")
        with mock.patch.object(A, "pull", boom):
            code, _, err = run(self.root, "audit", "--brand", "acme", "--since", "2025-01-01", "--until", "2026-11-02")
        self.assertEqual(code, 1)
        self.assertEqual(err.strip(), "The step stopped: Meta said no.")


class Pictures(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self._repo = A.REPO
        A.REPO = self.root
        self.addCleanup(setattr, A, "REPO", self._repo)

    def tearDown(self):
        self._t.cleanup()

    def test_shrink_is_a_jpeg_no_larger_than_320(self):
        from PIL import Image
        src, dst = self.root / "a.src", self.root / "a.jpg"
        Image.new("RGB", (1080, 1920), "red").save(src, "PNG")
        A.shrink(str(src), str(dst))
        im = Image.open(dst)
        self.assertEqual(im.format, "JPEG")
        self.assertEqual(max(im.size), 320)

    def test_build_runs_when_a_picture_is_absent_and_says_so(self):
        from PIL import Image
        d = self.root / "runs/winners/acme/audit/L"
        d.mkdir(parents=True)
        (d / "pics").mkdir()
        Image.new("RGB", (50, 80), "red").save(d / "pics/here.jpg", "JPEG")
        base = dict(spend=10.0, purchases=1, value=20.0, first="2026-01", last="2026-02", months=2, ids=["1"], variants=["x"],
                    format="Video", cuts=1)
        (d / "ranked.json").write_text(json.dumps({"total_purchases": 2, "total_spend": 20.0, "creatives": 2, "names": 2, "core": 1,
                                                   "top50": 2, "top10": 2, "rows": [
            {**base, "rank": 1, "name": "A", "pic": "pics/here.jpg"}, {**base, "rank": 2, "name": "B", "pic": "pics/gone.jpg"}]}))
        (d / "window.json").write_text(json.dumps({"brand": "acme", "since": "2026-01-01", "until": "2026-02-01", "title": "Acme Co"}))
        a = winners.argparse.Namespace(brand="acme", label="L", title=None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            A.sheets(a)
            A.build(a)
        self.assertIn("1 without a picture on this machine", out.getvalue())
        html = (d / "board.html").read_text()
        self.assertIn("Acme Co Top Creatives", html)
        self.assertIn("No picture on the machine", html)
        rows = json.loads((d / "board.json").read_text())
        self.assertEqual([r["name"] for r in rows], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
