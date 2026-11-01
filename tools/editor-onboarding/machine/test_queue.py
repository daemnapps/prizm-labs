#!/usr/bin/env python3
"""python3 machine/test_queue.py — from any cwd. Stdlib unittest only.

The work queue, end to end, on a temporary Drive tree that names no real
brand, product or person: rows for every role, every state read from the
folders and cards, brief numbers from a stand-in workspace, renamed and
messy delivery folders matched back to their package, and an image brief
shipped as a package.
"""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("work_queue_under_test", HERE / "queue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# A stand-in for the private workspace's naming tool: just enough of
# names.py's surface (parse_short, brief_candidates, register_rows, slug,
# brief_id, brief_code) over a tiny fixed table.
STUB_NAMES = textwrap.dedent('''
    import json, re
    from pathlib import Path
    WS = Path(__file__).resolve().parents[2]
    BRIEF_NEW = re.compile(r"^brief-(\\d{4})$")
    def slug(s):
        return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    def brief_id(x):
        m = re.match(r"^p(\\d{3})$", str(x or ""))
        return f"brief-{int(m.group(1)):04d}" if m else x
    def brief_code(x):
        m = BRIEF_NEW.match(str(x or ""))
        return f"p{int(m.group(1)):03d}" if m else x
    def parse_short(s):
        p = str(s).split("_")
        if len(p) in (4, 5) and BRIEF_NEW.match(p[2]) and p[3].startswith("batch-"):
            return {"brand": p[0], "product": p[1], "brief": p[2], "batch": p[3]}
        return None
    def _brand(brand):
        return json.loads((WS / "brands" / brand / "briefs.json").read_text())["briefs"]
    def register_rows(brand=None):
        reg = json.loads((WS / "register.json").read_text())["briefs"]
        return [{**r, "key": k, "_table": "briefs"} for k, r in reg.items() if brand in (None, r.get("brand"))]
    def brief_candidates(brand, q, product=None):
        q = str(q).lower()
        out = []
        for b in _brand(brand):
            if q == b.get("brief") or q in [a.lower() for a in b.get("aliases", [])]:
                out.append({"brief": b.get("brief"), "product": b.get("product"),
                            "per_product": b.get("count") == "brand+product", "header": b, "register": None})
        for r in register_rows(brand):
            if r.get("brief") == q and not any(o["brief"] == q for o in out):
                out.append({"brief": q, "product": r.get("product"), "per_product": False,
                            "header": None, "register": r})
        if product:
            out = [o for o in out if o["product"] == product] or out
        return out
''')


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = Path(self.td.name)
        self.sa = t / "Shared Assets"
        self.ws = t / "workspace"
        os.environ["SHARED_ASSETS"] = str(self.sa)
        os.environ.pop("META_CARDS_ROOT", None)
        self.q = load()
        self.q.WORKSPACE = self.ws
        b = self.sa / "brands/acme/briefs"
        (b / "ai-video-production").mkdir(parents=True)
        for n in ("ab-01-the-quiet-start", "ab-02-cold-open", "ab-03-last-look", "zz-plain"):
            (b / "ai-video-production" / f"{n}.zip").write_text("x")
        (b / "ai-video-production" / "kq07-premiere-handoff.zip").write_text("x")
        (b / "claims").mkdir()
        (b / "claims" / "ab-03-last-look — Sam").write_text("")
        # a renamed delivery: its old name kept in naming.json
        d1 = b / "delivered/acme_widget_brief-0001_batch-2026-09-30-a"
        d1.mkdir(parents=True)
        (d1 / "acme_widget_brief-0001_batch-2026-09-30-a_asset-01.mp4").write_text("v")
        (d1 / "naming.json").write_text(json.dumps({"unit": d1.name, "brief": "brief-0001",
                                                     "folder_was": "AB-01-The-Quiet-Start"}))
        # a messy editor folder, not renamed yet
        d2 = b / "delivered/AB-02 The Cold Open"
        d2.mkdir(parents=True)
        (d2 / "AB-02 The Cold Open v1.mp4").write_text("v")
        self.briefs = b
        # cards: brief 1 sent back with a note; a card with no package here is live
        self.card("sent-back", "video", "acme_widget_brief-0001_batch-2026-09-30-a", "widget", "brief-0001",
                  approval={"decision": "send-back", "note": "logo too small"}, run=str(d1))
        self.card("3-live", "video", "acme_gadget_brief-0140_batch-2026-09-29-a", "gadget", "brief-0140",
                  meta=[{"ad_id": "1"}, {"ad_id": "2"}])
        # a creator hand-off, sent, footage back
        h = self.sa / "handoffs/creator/acme/creator-handoff_acme_2026-10-01"
        (h / "returned").mkdir(parents=True)
        (h / "returned" / "brief-0150_asset-01.mov").write_text("v")
        (h / "manifest.json").write_text(json.dumps({"role": "creator", "briefs": [{"id": "brief-0150", "old_code": "p150"}],
                                                     "creator": {"name": "Jo", "sent": True}}))
        # the stand-in workspace
        (self.ws / "components/naming").mkdir(parents=True)
        (self.ws / "components/naming/names.py").write_text(STUB_NAMES)
        (self.ws / "brands/acme").mkdir(parents=True)
        (self.ws / "brands/acme/briefs.json").write_text(json.dumps({"briefs": [
            {"brief": "brief-0001", "product": "widget", "count": "brand+product", "aliases": ["ab-01", "AB-01"]},
            {"brief": "brief-0002", "product": "widget", "count": "brand+product", "aliases": ["ab-02", "AB-02"]},
            {"brief": "brief-0003", "product": "widget", "count": "brand+product", "aliases": ["ab-03", "AB-03"]},
            {"brief": None, "product": "gadget", "aliases": ["kq07"]}]}))
        (self.ws / "register.json").write_text(json.dumps({"briefs": {
            "p140": {"brand": "acme", "brief": "brief-0140", "product": "gadget", "run": "x"},
            "p150": {"brand": "acme", "brief": "brief-0150", "product": "gadget", "run": "y"},
            "p160": {"brand": "acme", "brief": "brief-0160", "product": "gadget",
                     "run": "runs/video-production/acme/kq07-full-run"}}}))

    def tearDown(self):
        os.environ.pop("SHARED_ASSETS", None)
        self.td.cleanup()

    def card(self, state, lane, ad, product, brief, approval=None, meta=None, run=""):
        f = self.sa / "meta/acme" / state / lane / ad
        f.mkdir(parents=True)
        (f / "card.json").write_text(json.dumps({"ad_name": ad, "product": product, "brief_id": brief,
                                                 "media": [f"{ad}_asset-01.mp4"], "approval": approval,
                                                 "meta": meta or [], "made_by": {"run": run, "creator": None}}))

    def rows(self, ws=True):
        B = self.q.Briefs(self.ws if ws else self.ws / "nothing-here")
        return {r["name"] + "|" + r["for"]: r for r in self.q.build("acme", briefs=B)}

    def test_states_and_numbers(self):
        r = self.rows()
        one = r["ab-01-the-quiet-start|Video editor"]
        self.assertEqual(one["label"], "widget brief-0001")
        self.assertEqual(one["old"], ["AB-01"])
        self.assertEqual(one["status_text"], "Sent back — logo too small")
        self.assertEqual(len(one["delivered"]), 1)          # the renamed folder found its package
        two = r["ab-02-cold-open|Video editor"]
        self.assertEqual(two["status"], "Delivered")        # the messy folder found its package
        three = r["ab-03-last-look|Video editor"]
        self.assertEqual((three["status"], three["who"]), ("Claimed", "Sam"))
        self.assertEqual(r["zz-plain|Video editor"]["status"], "Open")
        self.assertEqual(r["zz-plain|Video editor"]["label"], "no number yet")
        kq = r["kq07|Video editor"]                          # a number from the register's run name
        self.assertEqual((kq["label"], kq["old"]), ("gadget brief-0160", ["kq07", "p160"]))
        live = next(x for x in r.values() if x["key"] == ("gadget", "brief-0140"))
        self.assertEqual(live["status"], "Live")
        self.assertEqual(live["cards"][0]["ad_ids"], 2)
        cr = r["brief-0150|Creator"]
        self.assertEqual((cr["status"], cr["who"], len(cr["returned"])), ("Delivered", "Jo", 1))

    def test_queue_md(self):
        self.rows()
        md = (self.briefs / "QUEUE.md").read_text()
        self.assertIn("| For |", md)
        self.assertIn("Sent back — logo too small", md)
        self.assertIn("Live · 2 Meta ad ids", md)
        self.assertIn('"pull briefs for acme"', md)
        self.assertIn('"deliver"', md)
        self.assertIn("## No number yet", md)
        self.assertIn("`zz-plain`", md)
        self.assertTrue((self.briefs / "queue.json").is_file())

    def test_without_workspace_names_still_match(self):
        r = self.rows(ws=False)
        one = r["ab-01-the-quiet-start|Video editor"]
        self.assertEqual(one["status"], "Sent back")        # via folder_was, then the card's run folder
        self.assertEqual(r["ab-02-cold-open|Video editor"]["status"], "Delivered")
        self.assertEqual(one["label"], "no number yet")

    def test_hand_set_fields_survive(self):
        self.rows()
        meta = json.loads((self.briefs / "queue.json").read_text())
        meta["briefs"]["zz-plain"] = {"who": "Lee", "bounty": "$90"}
        (self.briefs / "queue.json").write_text(json.dumps(meta))
        r = self.rows()["zz-plain|Video editor"]
        self.assertEqual((r["who"], r["bounty"]), ("Lee", "$90"))

    def test_ship_image_brief(self):
        root = self.ws / "components/image-teardown"
        (root / "worksheets/acme/p170/prompts").mkdir(parents=True)
        (root / "worksheets/acme/p170/work-order.md").write_text("make it")
        (root / "briefs").mkdir()
        (root / "briefs/p170.html").write_text("<p>brief</p>")
        (root / "briefs.json").write_text(json.dumps({"briefs": {
            "p170": {"brand": "acme", "brief": "brief-0170", "product": "widget", "status": "approved",
                     "run": "acme-poster-01", "worksheet": "worksheets/acme/p170"},
            "p171": {"brand": "acme", "brief": "brief-0171", "status": "for-review", "run": "acme-poster-02"},
            "p172": {"brand": "acme", "brief": "brief-0172", "type": "video-creator", "lane": "video-teardown",
                     "status": "approved", "run": "z"}}}))
        recs = self.q.ready_design_briefs()
        self.assertEqual([x["key"] for x in recs], ["p170"])
        out = self.q.ship_design(recs[0])
        self.assertEqual(out, self.briefs / "image/p170-acme-poster-01.zip")
        names = zipfile.ZipFile(out).namelist()
        self.assertIn("p170-acme-poster-01/brief.html", names)
        self.assertIn("p170-acme-poster-01/worksheet/work-order.md", names)
        self.assertIsNone(self.q.ship_design(recs[0]))      # never twice
        r = self.rows()["p170-acme-poster-01|Graphic designer"]
        self.assertEqual((r["status"], r["type"]), ("Open", "image"))

    def test_ledger_writes_the_queue_when_it_is_here(self):
        # the private workspace carries the Asset Ledger: build hands QUEUE.md to it
        led = self.ws / "lab/damon/asset-ledger/db"
        led.mkdir(parents=True)
        (led / "ledger.db").write_text("")
        (led / "load.py").write_text("import pathlib; pathlib.Path('rebuilt').write_text('y')\n")
        (led / "render_queue.py").write_text(textwrap.dedent("""
            import sys, pathlib
            a = sys.argv[1:]
            b, sa = a[a.index('--brand') + 1], a[a.index('--drive') + 1]
            (pathlib.Path(sa) / 'brands' / b / 'briefs' / 'QUEUE.md').write_text('from the ledger')
            print(b + ': 3 row(s) — Open 3')
        """))
        out = self.q.write_queue("acme")
        self.assertEqual(out, "acme: 3 row(s) — Open 3 (from the ledger)")
        self.assertEqual((self.briefs / "QUEUE.md").read_text(), "from the ledger")
        self.assertFalse((led / "rebuilt").exists())
        self.q.write_queue("acme", rebuild=True)
        self.assertTrue((led / "rebuilt").exists())
        # a failing ledger, or QUEUE_FROM_FOLDERS, falls back to the folders
        (led / "render_queue.py").write_text("import sys; sys.exit(1)\n")
        import contextlib, io
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(self.q.write_queue("acme").endswith("(from the folders)"))
        self.assertIn("# Work queue — acme", (self.briefs / "QUEUE.md").read_text())
        os.environ["QUEUE_FROM_FOLDERS"] = "1"
        try:
            self.assertIsNone(self.q.ledger_render("acme"))
        finally:
            os.environ.pop("QUEUE_FROM_FOLDERS")

    def test_loose_match(self):
        lm = self.q.loose_match
        self.assertTrue(lm("ab-02-hens-coat", "AB-02 The Hen's Coat"))
        self.assertTrue(lm("tide", "tide-song-12345"))
        self.assertFalse(lm("ab-01-x", "ab-02-x"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
