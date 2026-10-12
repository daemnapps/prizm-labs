#!/usr/bin/env python3
"""SI-84 (paid pool bugs): the live bugs of swipe-paid#1 (five live bugs), held fixed.

    /usr/bin/python3 components/swipe-paid/test_live_bugs.py

Stdlib only, offline: no AdPlexity client, no Drive, no key. Every write lands
in a tempfile folder — never judgements.json, swipe.db or a brand folder here.
"""
import ast, importlib.util, io, json, os, sqlite3, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B   # noqa: E402
import serve as S   # noqa: E402
import corpus as C  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "swipe_teardown_run", os.path.join(HERE, "teardown", "run.py"))
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

JUDGED = "## Structural findings\n\nhand-written judgment\n"


class Brief(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "zz-brand")
        os.makedirs(self.root)
        with open(os.path.join(self.root, "teardown.md"), "w") as f:
            f.write(JUDGED)

    def test_brief_refuses_over_a_judged_teardown(self):
        with mock.patch.object(B, "HERE", self.tmp):
            with self.assertRaises(SystemExit) as cm:
                B.cmd_brief("zz-brand")
        self.assertIn("teardown.md", str(cm.exception.code))
        self.assertIn("--replace", str(cm.exception.code))
        with open(os.path.join(self.root, "teardown.md"), "rb") as f:
            self.assertEqual(f.read(), JUDGED.encode())
        self.assertFalse(os.path.exists(os.path.join(self.root, "_BRAND.md")))

    def test_brief_replace_rewrites(self):
        doc = {"brand": "zz-brand", "creatives": 2, "video": 1, "image": 1,
               "blocks": [{"nn": "01", "slug": "01_h", "headline": "H",
                           "primary_text": "b", "count": 2, "video_count": 1,
                           "image_count": 1, "landing_page": None}]}
        with open(os.path.join(self.root, "blocks.json"), "w") as f:
            json.dump(doc, f)
        with mock.patch.object(B, "HERE", self.tmp):
            B.cmd_brief("zz-brand", replace=True)
        with open(os.path.join(self.root, "teardown.md")) as f:
            md = f.read()
        self.assertIn("<!-- JUDGMENT SLOT", md)
        self.assertIn("H", md)
        self.assertNotIn("hand-written judgment", md)
        self.assertTrue(os.path.exists(os.path.join(self.root, "_BRAND.md")))


class Watch(unittest.TestCase):
    def test_watch_fold_keeps_the_list(self):
        doc = {"blocks": [{"headline": "H", "primary_text": B.norm_body("b"),
                           "count": 1, "video_count": 0, "image_count": 1,
                           "ad_ids": ["1"], "media": {}, "variants": 1,
                           "max_variants": 1}]}
        fresh = [{"id": "2", "title": "H", "description": "b", "image_url": "u"},
                 {"id": "3", "title": "New", "description": "other", "video_url": "v"}]
        self.assertEqual(B.fold_delta(doc, fresh, "2026-10-07"), 1)
        self.assertIsInstance(doc["blocks"], list)
        self.assertEqual(len(doc["blocks"]), 2)
        self.assertEqual(doc["block_count"], 2)
        self.assertEqual(doc["creatives"], 3)
        self.assertEqual(doc["video"], 1)
        self.assertEqual(doc["image"], 2)
        new = [a for a in doc["blocks"] if a["headline"] == "New"][0]
        self.assertEqual(new["first_seen"], "2026-10-07")
        json.dumps(doc)


class Board(unittest.TestCase):
    SID = "swipe:paid:zzbrand:123"

    def test_judgment_round_trip(self):
        tmp = tempfile.mkdtemp()
        db = os.path.join(tmp, "swipe.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE creatives (swipe_id TEXT, source_f TEXT, "
                    "verdict TEXT, known TEXT)")
        con.execute("INSERT INTO creatives VALUES (?, ?, NULL, ?)",
                    (self.SID, "unclassified", "unjudged"))
        con.commit(); con.close()
        jf = os.path.join(tmp, "judgements.json")
        with mock.patch.object(S, "DB", db), mock.patch.object(C, "JUDGEMENTS", jf):
            out = S.save_judgement({"swipe_id": self.SID, "verdict": "swipe"})
        self.assertEqual(out["swipe_id"], self.SID)
        self.assertEqual(out["verdict"], "swipe")
        with open(jf) as f:
            self.assertIn(self.SID, json.load(f))
        con = sqlite3.connect(db)
        row = con.execute("SELECT verdict FROM creatives WHERE swipe_id=?",
                          (self.SID,)).fetchone()
        con.close()
        self.assertEqual(row[0], "swipe")

    def _post(self, exc):
        h = S.Handler.__new__(S.Handler)
        h.path = "/api/judge"
        body = b'{"swipe_id": "x"}'
        h.headers = {"Content-Length": str(len(body))}
        h.rfile = io.BytesIO(body)
        h.wfile = io.BytesIO()
        calls = {"status": [], "errors": []}
        h.send_response = lambda code, msg=None: calls["status"].append(code)
        h.send_header = lambda k, v: None
        h.end_headers = lambda: None
        h.send_error = lambda code, msg=None: calls["errors"].append(code)
        with mock.patch.object(S, "save_judgement", side_effect=exc):
            h.do_POST()
        return calls, h.wfile.getvalue()

    def test_post_failure_is_named(self):
        calls, out = self._post(RuntimeError("boom"))
        self.assertEqual(calls["status"], [500])
        self.assertEqual(calls["errors"], [])
        self.assertEqual(json.loads(out), {"error": "RuntimeError: boom"})
        calls, out = self._post(ValueError("bad"))
        self.assertEqual(calls["status"], [400])
        self.assertEqual(json.loads(out), {"error": "bad"})


class Teardown(unittest.TestCase):
    def test_teardown_handoff_finds_the_repo_and_its_block(self):
        self.assertTrue(os.path.isdir(os.path.join(T.WS, "components")))
        self.assertTrue(os.path.isdir(os.path.join(T.WS, "brands")))
        self.assertTrue(T.MACHINE.endswith(os.path.join(
            "tools", "video-teardown", "machine", "run.py")))
        self.assertTrue(os.path.isfile(T.MACHINE))
        db = os.path.join(tempfile.mkdtemp(), "swipe.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE ads (ad_id, brand, block_slug, drive_file, "
                    "media_type, variants)")
        con.execute("CREATE TABLE blocks (brand, slug, headline, stage)")
        con.execute("INSERT INTO ads VALUES (?,?,?,?,?,?)",
                    ("9", "zz-brand", "01_h", "zz-brand/x.mp4", "video", 3))
        con.execute("INSERT INTO blocks VALUES (?,?,?,?)",
                    ("zz-brand", "01_h", "H", "top"))
        con.commit(); con.close()
        with mock.patch.object(T, "DB", db):
            ad, block = T.lookup("zz-brand", "9")
        self.assertEqual(ad["ad_id"], "9")
        self.assertEqual(block["headline"], "H")
        self.assertEqual(block["stage"], "top")


class Parse(unittest.TestCase):
    def test_three_files_parse(self):
        for rel in ("build.py", "serve.py", os.path.join("teardown", "run.py")):
            with open(os.path.join(HERE, rel)) as f:
                ast.parse(f.read(), rel)


if __name__ == "__main__":
    unittest.main()
