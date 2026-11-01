"""Blocker 6 (Outlier lists on the mini), 2026-10-21: a teardown on a machine with no Outlier reads the lists Outlier
last gave (runs/video-teardown/lists.json), and REFUSES when that file is missing too — never the whole library,
parked rows included, which is what the mini used to offer.

    cd tools/video-teardown/machine && /usr/bin/python3 -m unittest test_lists_file

No network beyond a throwaway local server on 127.0.0.1 standing in for Outlier.
"""
import http.server
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

import layers as L

LIVE = {"format": [{"id": "meme", "name": "Meme", "swipes": 12, "ads": 6, "all_swipes": ["big"]}],
        "format_parked": ["era-roll-call"],
        "style": [{"id": "phone-ugc", "name": "Phone UGC"}], "style_parked": [],
        "structure": [{"id": "hook-proof-ask", "name": "Hook, proof, ask"}], "structure_parked": []}


class Lists(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lists-"))
        (self.tmp / "lib").mkdir()
        (self.tmp / "runs").mkdir()
        rows = {"format": ["meme", "era-roll-call", "letter-to-younger-self"], "style": ["phone-ugc", "glossy"],
                "structure": ["hook-proof-ask", "listicle"]}
        for el, ids in rows.items():
            (self.tmp / "lib" / ("%s.video.json" % el)).write_text(json.dumps(
                {"rows": [{"id": i, "name": i, "what": "w", "status": "draft"} for i in ids]}))
        self.saved = (L.LIB, L.TEARDOWN_RUNS, L.LISTS_URL)
        L.LIB, L.TEARDOWN_RUNS = self.tmp / "lib", self.tmp / "runs"
        L.LISTS_URL = "http://127.0.0.1:9/api/lists"          # nothing listens: Outlier is not reachable
        L._ACTIVE.clear()

    def tearDown(self):
        L.LIB, L.TEARDOWN_RUNS, L.LISTS_URL = self.saved
        L._ACTIVE.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def serve(self, answer):
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps(answer).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        L.LISTS_URL = "http://127.0.0.1:%d/api/lists" % srv.server_port

    def test_no_outlier_and_no_file_refuses_by_name(self):
        with self.assertRaises(L.ListsMissing) as cm:
            L.active("format")
        self.assertIn("runs/video-teardown/lists.json", str(cm.exception))
        self.assertIn("never offered", str(cm.exception))

    def test_outlier_answer_is_kept_and_read_back_when_it_is_gone(self):
        self.serve(LIVE)
        rows, where = L.active("format")
        self.assertEqual(([r["id"] for r in rows], where), (["meme"], "Outlier Lists tab"))
        snap = json.loads((self.tmp / "runs" / "lists.json").read_text())
        self.assertEqual(snap["format"], [{"id": "meme", "name": "Meme", "swipes": 12, "ads": 6}])   # no swipe lists
        self.assertEqual(snap["format_parked"], ["era-roll-call"])
        taken = snap["_taken"]["at"]
        # the same answer again does not rewrite the file
        L._ACTIVE.clear()
        L.active("format")
        self.assertEqual(json.loads((self.tmp / "runs" / "lists.json").read_text())["_taken"]["at"], taken)
        # Outlier gone: the file, named with its time, and the same ids as Outlier gave
        L.LISTS_URL = "http://127.0.0.1:9/api/lists"
        L._ACTIVE.clear()
        for el, want in (("format", ["meme"]), ("style", ["phone-ugc"]), ("structure", ["hook-proof-ask"])):
            rows, where = L.active(el)
            self.assertEqual([r["id"] for r in rows], want)
            self.assertIn("runs/video-teardown/lists.json", where)
            self.assertIn(taken, where)

    def test_parked_rows_never_offered_from_the_file(self):
        (self.tmp / "runs" / "lists.json").write_text(json.dumps(
            {"format": [{"id": "meme"}], "style": [], "structure": [], "_taken": {"at": "2026-10-21T01:00:00Z"}}))
        rows, _ = L.active("format")
        self.assertEqual([r["id"] for r in rows], ["meme"])     # era-roll-call and letter-to-younger-self stay out

    def test_unparked_rows_still_join(self):
        (self.tmp / "runs" / "lists.json").write_text(json.dumps({"format": [{"id": "meme"}]}))
        (self.tmp / "runs" / "unparked.json").write_text(json.dumps({"format": ["letter-to-younger-self"]}))
        rows, _ = L.active("format")
        self.assertEqual([r["id"] for r in rows], ["meme", "letter-to-younger-self"])


if __name__ == "__main__":
    unittest.main()
