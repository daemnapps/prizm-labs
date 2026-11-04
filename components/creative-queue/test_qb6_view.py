"""QB-6 (content queue page): view.py, the page's read door, and the new settable field `due`.

A fixture index (one entry of each type, one the owner removed, one gone) and a fixture shadow root (the team's set who /
priority and an add) are copied into a temp folder; view.py runs as the kit runs it (this Python, from the repo
root) and must leave both byte-identical with no new file. `due` goes through `cq.py set --no-commit` only.
Stdlib only, no network, no git.

    python3 components/creative-queue/test_qb6_view.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402

REPO = paths.repo(HERE)
FIX = HERE / "test_qb6_fixtures"
NOW = "2026-10-23T14:00:00Z"


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(HERE / script)] + list(args), cwd=str(REPO),
                       capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


def snapshot(top):
    """Every file under top with its bytes."""
    return {str(p.relative_to(top)): p.read_bytes() for p in sorted(Path(top).rglob("*")) if p.is_file()}


class View(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qb6-")).resolve()
        self.index = self.tmp / "index.json"
        shutil.copy(str(FIX / "index.json"), str(self.index))
        self.root = self.tmp / "shadow"
        shutil.copytree(str(FIX / "shadow"), str(self.root))

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def view(self):
        # QB-7 (content queue Monday): emails come from the email line; none here, so the fixtures alone decide
        code, out, err = run("view.py", "--index", str(self.index), "--root", str(self.root),
                             "--emails", str(self.tmp / "no-email-production"), "--now", NOW)
        self.assertEqual(code, 0, err)
        d = json.loads(out)
        return d, {r["id"]: r for r in d["rows"]}

    def test_rows_without_video_with_shadow_decisions_and_adds(self):
        d, rows = self.view()
        self.assertEqual(sorted(d), ["owner_age_h", "owner_built", "people", "rows", "shadow_root", "stages"])
        # QB-7 (content queue Monday): the index's email rows are dropped, video is kept read only
        self.assertEqual(sorted(set(r["type"] for r in rows.values())), ["carousel", "image-ad", "landing-page", "video-ad"])
        self.assertEqual(rows["fxbrand_fx_brief-0001"]["read_only"], "video")   # a video ad shows, read only
        # the team's set on a piece in the owner's index shows, with who decided it
        r = rows["fxbrand_fx_brief-0048"]
        self.assertEqual((r["who"], r["priority"], r["due"]), ("designer", "1", None))
        self.assertEqual(r["decided_by"]["who"], {"by": "pm", "made": "2026-10-23T13:40:00Z"})
        self.assertEqual(r["decided_by"]["priority"]["by"], "pm")
        self.assertEqual((r["stage"], r["flag"], r["since"], r["title"], r["brand"]),
                         ("final-needs-you", "stuck", "2026-10-16", "Brief 0048 · fx", "fxbrand"))
        self.assertIs(r["in_owner"], True)
        self.assertEqual(r["thumb"], "http://127.0.0.1:8795/thumb/fx.png")
        # links: 127.0.0.1 and localhost are the owner's Mac only; a real web link is not
        self.assertEqual(r["links"], [{"label": "Open in Launch to Meta", "url": "http://127.0.0.1:8795/", "local": True},
                                      {"label": "The brief", "url": "https://docs.google.com/document/d/fx/edit"}])
        self.assertIs(rows["fxbrand_fx_carousel-0002"]["links"][0]["local"], True)
        # a shadow add is a row of its own, not in the owner's list
        a = rows["fxbrand_image-ad_baseline-03"]
        self.assertEqual((a["title"], a["brand"], a["type"], a["who"], a["stage"]),
                         ("Baseline 03", "fxbrand", "image-ad", "designer", None))
        self.assertIs(a["in_owner"], False)
        self.assertEqual(a["added_by"]["by"], "pm")
        # QB-7 (content queue Monday): an email in the owner's index is gone (emails come from the email line);
        # removed and gone rows are kept, marked
        self.assertNotIn("fxbrand_email_fxbrand-oct-20", rows)
        gone = rows["fxbrand_page_fx-cpk-01"]
        self.assertEqual((gone["gone"], gone["removed"]), ("2026-10-18T14:26:54", False))
        rm = rows["fxbrand_idea_old-static"]
        self.assertIs(rm["removed"], True)
        self.assertEqual(rm["decided_by"]["removed"]["by"], "owner")
        for row in rows.values():
            for f in ("who", "priority", "due", "note", "requested_stage", "decided_by", "removed"):
                self.assertIn(f, row)

    def test_owner_built_and_age_come_from_the_index(self):
        d, _ = self.view()
        self.assertEqual(d["owner_built"], "2026-10-22T02:00:00+00:00")
        self.assertEqual(d["owner_age_h"], 36.0)
        self.assertEqual(d["people"], ["the owner", "the team", "the team"])     # QB-7 (content queue Monday): without Christine
        self.assertEqual(d["shadow_root"], str(self.root))
        self.assertEqual([s["id"] for s in d["stages"]][:2], ["idea", "brief"])

    def test_view_writes_nothing(self):
        before = snapshot(self.tmp)
        self.view()
        self.assertEqual(snapshot(self.tmp), before)
        self.assertEqual(sorted(str(p.relative_to(self.tmp)) for p in self.tmp.rglob("*")),
                         sorted(["index.json", "shadow", "shadow/decisions", "shadow/decisions/pm",
                                 "shadow/decisions/pm/2026-10-23.jsonl"]))

    def test_view_refuses_the_live_queue_as_root(self):
        code, out, err = run("view.py", "--index", str(self.index), "--root", str(REPO / "runs" / "queue"), "--now", NOW)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("REFUSED", err)

    def test_due_round_trips_and_a_bad_date_exits_2(self):
        base = ["--by", "pm", "--root", str(self.root), "--no-commit"]
        code, out, err = run("cq.py", "set", "fxbrand_fx_brief-0048", "due", "2026-10-27", *base)
        self.assertEqual(code, 0, err)
        _, rows = self.view()
        r = rows["fxbrand_fx_brief-0048"]
        self.assertEqual(r["due"], "2026-10-27")
        self.assertEqual(r["decided_by"]["due"]["by"], "pm")
        before = snapshot(self.root)
        for bad in ("27/10", "2026-10-32", "2026-1-27", "tomorrow"):
            code, out, err = run("cq.py", "set", "fxbrand_fx_brief-0048", "due", bad, *base)
            self.assertEqual(code, 2, (bad, err))
            self.assertIn("due", err)
        self.assertEqual(snapshot(self.root), before)                 # a refused date writes nothing
        code, out, err = run("cq.py", "set", "fxbrand_fx_brief-0048", "due", "", *base)
        self.assertEqual(code, 0, err)
        _, rows = self.view()
        self.assertEqual(rows["fxbrand_fx_brief-0048"]["due"], "")   # "" clears it


if __name__ == "__main__":
    unittest.main()
