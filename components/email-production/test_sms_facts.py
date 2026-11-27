"""SMS facts (2026-11-04): the platform comes from the brand's own record, the key by name, and only counts
are kept. No network, no key."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sms_facts as F  # noqa: E402


def _pages():
    sub = lambda i, ok, day: {"id": f"s{i}", "phone_number": "15550000000", "email": f"p{i}@example.test",
                              "created_at": f"{day}T00:00:00", "subscriptions": {"promotional": {"can_send": ok}}}
    return {
        "/api/v2/subscribers": {"subscribers": [sub(1, True, "2021-01-02"), sub(2, False, "2020-10-06")],
                                "next_cursor": "c2"},
        "/api/v2/subscribers?cursor=c2": {"subscribers": [sub(3, True, "2022-05-05")], "next_cursor": None},
    }


class SmsFacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / "brands" / "zz" / "operations").mkdir(parents=True)
        self.p = mock.patch.object(F, "WORKSPACE", self.ws)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def _brand(self, **rec):
        (self.ws / "brands" / "zz" / "operations" / "brand.json").write_text(json.dumps(dict(brand="zz", **rec)))

    def test_postscript_counts_every_page_and_keeps_no_contact_details(self):
        pages = _pages()
        got = F.postscript("k", get=pages.__getitem__, say=lambda s: None)
        self.assertEqual((got["records"], got["promotional_can_send"], got["oldest_record"], got["complete"]),
                         (3, 2, "2020-10-06", True))
        self.assertIn("not readable", got["campaigns"])
        d = F.write("zz", dict(got, brand="zz", state="read", read_at="2026-11-04T00:00:00+00:00"))
        stored = (d / "sms-facts.json").read_text() + (d / "sms-facts.md").read_text()
        for private in ("15550000000", "example.test", "s1"):
            self.assertNotIn(private, stored)

    def test_the_platform_and_the_key_name_come_from_the_brand(self):
        self._brand(sms_platform="postscript")
        with mock.patch.object(F, "_key", return_value=None) as k:
            got = F.read("zz")
        k.assert_called_with("POSTSCRIPT_ZZ_KEY")
        self.assertEqual(got["state"], "not readable yet: POSTSCRIPT_ZZ_KEY is empty")

    def test_a_brand_with_no_platform_says_so(self):
        self._brand()
        self.assertIn("no sms_platform", F.read("zz")["state"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
