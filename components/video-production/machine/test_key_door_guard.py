"""The keyed Higgsfield door (and the Kling backup rung on it) goes through the house spend guard (2026-11-27)."""
import importlib.util, os, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _api():
    s = importlib.util.spec_from_file_location("hf_api_t", HERE / "higgsfield_api.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


class KeyDoorGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["UPRIGHT_SPEND_LEDGER"] = self.tmp.name
        os.environ.pop("UPRIGHT_SPEND_OK", None)
        self.api, self.calls = _api(), []
        self.api._call = lambda url, payload=None, timeout=None: (self.calls.append(url) or (200, {"request_id": f"r{len(self.calls)}"}))

    def tearDown(self):
        os.environ.pop("UPRIGHT_SPEND_LEDGER", None); self.tmp.cleanup()

    def payload(self, **kw):
        return {"prompt": "a man rinses his face, the FLEX brush in his hand", "resolution": "480p", "duration": 5,
                "image_url": "https://example.test/a.png", **kw}

    def test_paid_call_logged_and_never_twice(self):
        self.assertEqual(self.api.submit("kling-video/v4/image-to-video", self.payload()), "r1")
        self.assertTrue(list(Path(self.tmp.name).glob("*.jsonl")), "the paid call wrote no ledger row")
        with self.assertRaises(Exception):
            self.api.submit("kling-video/v4/image-to-video", self.payload())
        self.assertEqual(len(self.calls), 1, "the same request was sent twice")

    def test_changed_input_goes(self):
        self.api.submit("kling-video/v4/image-to-video", self.payload())
        self.api.submit("kling-video/v4/image-to-video", self.payload(prompt="a man pats his face dry, FLEX on the sink"))
        self.assertEqual(len(self.calls), 2)


if __name__ == "__main__":
    unittest.main()
