#!/usr/bin/env python3
"""take_back.py — ad-handoff's home for a hand-off's take-back.

    /usr/bin/python3 components/ad-handoff/tests/test_take_back.py

SI-143 (take-back home): the Klaviyo uploader, meta-upload and video-edit
called take_back by executing the owner's lab hand-off file; they now load
`components/ad-handoff/take_back.py` by path. AI_WORKSPACE points at a temp
tree WITH brands/ and a decoy naming module, to prove naming is found by the
file's own location. Offline: no key, no network, no Drive.
"""
import ast, importlib.util, json, os, shutil, sys, tempfile, unittest
from pathlib import Path

COMP = Path(__file__).resolve().parent.parent
REPO = COMP.parent.parent
SOURCE = COMP / "take_back.py"

FAKE_WS = Path(tempfile.mkdtemp(prefix="take-back-ws-"))
(FAKE_WS / "brands").mkdir()
(FAKE_WS / "components" / "naming").mkdir(parents=True)
(FAKE_WS / "components" / "naming" / "names.py").write_text('raise ImportError("decoy: naming came from AI_WORKSPACE")\n')
os.environ["AI_WORKSPACE"] = str(FAKE_WS)

spec = importlib.util.spec_from_file_location("ad_handoff_take_back", SOURCE)
TB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TB)

ROLE, BRAND, BID = "graphic-designer", "testbrand", "brief-0999"
NAME = f"{ROLE}-handoff_{BRAND}_2099-01-01"
VIA = "components/ad-handoff/take_back.py"


class TakeBack(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="take-back-"))
        self.staging = self.tmp / "staging"
        self.ledger = self.staging / "ledger.jsonl"
        self.root = self.staging / ROLE / BRAND / NAME
        (self.root / "returned").mkdir(parents=True)
        (self.root / "manifest.json").write_text(json.dumps({
            "schema": "handoff/1", "name": NAME, "role": ROLE, "brand": BRAND,
            "briefs": [{"id": BID}], "ids": {}, "drive": {},
            "returned": {"expected": [], "received": []}}))
        ret = self.root / "returned"
        (ret / "README.md").write_text("returned\n")
        (ret / f"{BID}_asset-01.png").write_bytes(b"\x89PNG fake")
        (ret / f"{TB.N.brief_code(BID)}-a02.png").write_bytes(b"\x89PNG fake")
        (ret / "live-ids.json").write_text(json.dumps([{"ad_name": "x", "channel": "meta", "platform_id": "1234567890"},
                                                        {"ad_name": "y", "channel": "meta", "platform_id": None}]))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_naming_found_by_file_location(self):
        self.assertEqual(Path(TB.N.__file__).resolve(), REPO / "components" / "naming" / "names.py")

    def test_i_index_joins_files_and_live_ids(self):
        idx = TB.take_back(ROLE, BRAND, NAME, self.staging, self.ledger)
        by = {f["file"]: f for f in idx["files"]}
        code = TB.N.brief_code(BID)
        self.assertEqual(by[f"{BID}_asset-01.png"]["brief_id"], BID)
        self.assertEqual(by[f"{BID}_asset-01.png"]["asset_id"], "asset-01")
        self.assertEqual(by[f"{code}-a02.png"]["brief_id"], BID)
        self.assertEqual(by[f"{code}-a02.png"]["asset_id"], "asset-02")
        self.assertNotIn("README.md", by)
        self.assertEqual([l["live_id"] for l in idx["live_ids"]], ["live_meta_1234567890", None])
        self.assertEqual(json.loads((self.root / "returned" / "index.json").read_text()), idx)

    def test_ii_manifest_gains_returned_block(self):
        idx = TB.take_back(ROLE, BRAND, NAME, self.staging, self.ledger)
        m = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual(sorted(m["returned"]["received"]),
                         sorted([f"{BID}_asset-01.png", f"{TB.N.brief_code(BID)}-a02.png", "live-ids.json"]))
        self.assertEqual([l["live_id"] for l in m["returned"]["live_ids"]], ["live_meta_1234567890", None])
        self.assertEqual(m["returned"]["taken_back"], idx["taken_back"])

    def test_iii_one_returned_ledger_row_via_component(self):
        TB.take_back(ROLE, BRAND, NAME, self.staging, self.ledger)
        rows = [json.loads(l) for l in self.ledger.read_text().splitlines() if l.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["verdict"]["event"], "returned")
        self.assertEqual(rows[0]["via"], VIA)
        self.assertEqual(rows[0]["item"], NAME)
        self.assertEqual(rows[0]["briefs"], [BID])
        self.assertEqual(rows[0]["files"], 3)
        self.assertEqual(rows[0]["live_ids"], ["live_meta_1234567890"])

    def test_iv_missing_handoff_refused(self):
        with self.assertRaises(TB.Refused) as cm:
            TB.take_back(ROLE, BRAND, "no-such-handoff", self.staging, self.ledger)
        self.assertTrue(cm.exception.reasons)
        self.assertFalse(self.ledger.exists())


class CallersLoadTheComponent(unittest.TestCase):
    # upload.py's catalog reads still use the lab tool; they are not take-back
    EXCEPT = {"components/meta-upload/upload.py": {"_funnel_of", "link_url"}}
    CALLERS = ("tools/email-production/klaviyo_upload.py",
               "components/meta-upload/upload.py",
               "tools/video-edit/machine/handoff_run.py")

    def test_v_no_lab_handoff_on_a_take_back_line(self):
        for rel in self.CALLERS:
            text = (REPO / rel).read_text()
            excepted = set()
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.FunctionDef) and node.name in self.EXCEPT.get(rel, ()):
                    excepted.update(range(node.lineno, node.end_lineno + 1))
            bad = [n for n, line in enumerate(text.splitlines(), 1)
                   if "handoff-standard" in line and n not in excepted]
            self.assertEqual(bad, [], f"{rel} still names the lab hand-off at lines {bad}")
            self.assertIn("take_back.py", text, rel)
            self.assertIn("ad-handoff", text, rel)


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        shutil.rmtree(FAKE_WS, ignore_errors=True)
