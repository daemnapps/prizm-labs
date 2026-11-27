"""The judge (and the product read that uses it) is account agnostic: a key out of credit, rate-limited or over quota
falls through once to the next key the loader knows, and the key NAME that answered is recorded."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from image_production import judge as J, route as R  # noqa: E402

ENTRY = {"key": "GEMINI_API_KEY", "vendor_model": "m", "endpoint": "https://x/{model}:generate"}
OK = json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps({"ok": True})}]}}]}).encode()
QUOTA = json.dumps({"error": {"code": 402, "message": "Your prepayment credits are depleted.",
                              "status": "RESOURCE_EXHAUSTED"}}).encode()


class Fallthrough(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.img = Path(self.d.name) / "p.png"
        self.img.write_bytes(b"PNG")
        self.keys = {"GEMINI_API_KEY": "company-fake", "GEMINI_API_KEY_PERSONAL": "personal-fake"}
        self.p = mock.patch.object(R, "key_value", lambda n: self.keys.get(n))
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.d.cleanup()

    def transport(self, answers):
        seen = []

        def t(method, url, headers, body):
            seen.append(url.split("key=")[1])
            return answers[len(seen) - 1]
        return t, seen

    def test_a_key_out_of_credit_falls_through_to_the_backup(self):
        t, seen = self.transport([(402, {}, QUOTA), (200, {}, OK)])
        self.assertIn("ok", J.google_caller("q", self.img, ENTRY, transport=t))
        self.assertEqual(seen, ["company-fake", "personal-fake"])
        self.assertEqual(J.ANSWERED["key"], "GEMINI_API_KEY_PERSONAL")

    def test_a_rate_limit_falls_through_too(self):
        t, seen = self.transport([(429, {}, b"{}"), (200, {}, OK)])
        J.google_caller("q", self.img, ENTRY, transport=t)
        self.assertEqual(J.ANSWERED["key"], "GEMINI_API_KEY_PERSONAL")

    def test_the_first_key_answering_is_recorded_and_no_backup_is_tried(self):
        t, seen = self.transport([(200, {}, OK)])
        J.google_caller("q", self.img, ENTRY, transport=t)
        self.assertEqual(seen, ["company-fake"])
        self.assertEqual(J.ANSWERED["key"], "GEMINI_API_KEY")

    def test_any_other_error_fails_at_once(self):
        t, seen = self.transport([(400, {}, b'{"error": {"message": "bad request"}}'), (200, {}, OK)])
        with self.assertRaises(RuntimeError):
            J.google_caller("q", self.img, ENTRY, transport=t)
        self.assertEqual(seen, ["company-fake"])

    def test_every_key_refusing_fails_and_names_them(self):
        t, seen = self.transport([(402, {}, QUOTA), (402, {}, QUOTA)])
        with self.assertRaises(RuntimeError) as e:
            J.google_caller("q", self.img, ENTRY, transport=t)
        self.assertIn("GEMINI_API_KEY 402", str(e.exception))

    def test_no_backup_on_the_machine_is_the_old_behaviour(self):
        self.keys.pop("GEMINI_API_KEY_PERSONAL")
        t, seen = self.transport([(402, {}, QUOTA)])
        with self.assertRaises(RuntimeError):
            J.google_caller("q", self.img, ENTRY, transport=t)
        self.assertEqual(seen, ["company-fake"])


if __name__ == "__main__":
    unittest.main()
