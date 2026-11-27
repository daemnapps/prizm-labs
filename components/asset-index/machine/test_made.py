"""made.py: everything AI-made is listed, retired people never come back, spoken clips belong to their ad."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import made as M  # noqa: E402


class Made(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        ws = self.ws = Path(self.d.name)
        bank = ws / "runs" / "ai-elements"
        for rel in ("b/sets/sink/plates/wide.png", "b/casting/dre/master.jpg", "b/casting/old/master.jpg", "b/props/towel/picture.png"):
            (bank / rel).parent.mkdir(parents=True)
            (bank / rel).write_bytes(b"x")
        idx = {"people": {"b/dre": {"brand": "b", "id": "dre", "name": "Dre the barber", "folder": "runs/ai-elements/b/casting/dre", "working": True},
                          "b/old": {"brand": "b", "id": "old", "name": "Old barber", "folder": "runs/ai-elements/b/casting/old", "working": True}},
               "sets": {"b/sink": {"brand": "b", "id": "sink", "name": "bathroom sink", "what": "white bathroom sink and mirror", "folder": "runs/ai-elements/b/sets/sink"}},
               "props": {"b/towel": {"brand": "b", "id": "towel", "name": "grey towel", "folder": "runs/ai-elements/b/props/towel"}}}
        (bank / "ELEMENTS-INDEX.json").write_text(json.dumps(idx))
        (bank / "b" / "removal-list.json").write_text(json.dumps({"people": [{"person": "old"}]}))
        run = ws / "runs" / "video-production" / "b" / "r1" / "clips"
        run.mkdir(parents=True)
        calls = []
        for i, (people, lines, what) in enumerate([(["dre"], [], "man washes his face at a sink"), (["dre"], [{"text": "hi there", "on_camera": True}], "man talks"),
                                                   (["old"], [], "barber walks in")]):
            (run / ("C%d.mp4" % i)).write_bytes(b"x" * (i + 5))
            calls.append({"id": "C%d" % i, "prompt": what, "people": people, "lines": lines, "seconds": 6})
        (run / "plan.json").write_text(json.dumps({"calls": calls}))
        self.rows = M.build("b", ws)

    def tearDown(self):
        self.d.cleanup()

    def test_retired_people_never_come_back(self):
        text = json.dumps(self.rows)
        self.assertNotIn("casting/old", text)
        self.assertNotIn("C2", text)

    def test_a_spoken_clip_belongs_to_its_ad(self):
        r = {x["id"]: x["reuse"] for x in self.rows if x["kind"] == "clip"}
        self.assertEqual(r, {"clip:b/r1/C0": "any", "clip:b/r1/C1": "this ad"})

    def test_found_before_it_is_made_again(self):
        hit = M.close("b", "place", "a white bathroom sink with a mirror", rows=self.rows)
        self.assertEqual(hit[0]["name"], "sink")
        self.assertEqual(M.close("b", "place", "a snowy mountain road", rows=self.rows), [])
        self.assertEqual(M.find("b", "man talks", "clip", rows=self.rows), [r for r in M.find("b", "man talks", "clip", rows=self.rows) if r["reuse"] == "any"])

    def test_no_machine_paths_and_every_file_is_there(self):
        for r in self.rows:
            self.assertFalse(r["file"].startswith("/"))
            self.assertTrue((self.ws / r["file"]).is_file())

    def test_pull_adds_each_job_once(self):
        job = {"id": "j1", "status": "completed", "result_url": "u", "job_type": "m", "params": {"prompt": "b towel on a hook"}}
        ask = lambda kind: [job] if kind == "image" else []                         # noqa: E731
        self.assertEqual((M.pull(self.ws, ask), M.pull(self.ws, ask)), (1, 0))
        self.assertIn("job:j1", [r["id"] for r in M.build("b", self.ws)])


if __name__ == "__main__":
    unittest.main()
