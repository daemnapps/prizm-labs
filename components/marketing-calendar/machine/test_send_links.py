#!/usr/bin/env python3
"""Every format link on the calendar opens its email (SI-28 (calendar send links)).

    python3 machine/test_send_links.py

    a  every brand's sends resolve through brandpath's `email-sms` key, and
       the board's /source opens each one
    b  a borrowed format resolves against `source_brand`; a placeholder or
       empty source has no link
    c  /source refuses anything that is not a real send file
    d  the old `email/sends` shape is gone from the code and its readers
    e  nothing under brands/ is written

No brand is named here: brands are found at run time.
"""
import calendar as _stdlib_calendar      # noqa: F401 — cached BEFORE machine/ joins the path,
import os                                # because this folder has a calendar.py of its own
import sys
import time
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
CHECKOUT = next((d for d in MACHINE.parents if (d / ".git").exists()), None)
if CHECKOUT and not os.environ.get("AI_WORKSPACE"):
    os.environ["AI_WORKSPACE"] = str(CHECKOUT)     # a worktree must read ITSELF
sys.path.insert(0, str(MACHINE))

import month as MONTH                    # noqa: E402
import serve                             # noqa: E402
import paths as P                        # noqa: E402

BRANDS = P.WORKSPACE / "brands"


def brand_folders():
    return sorted(d.name for d in BRANDS.iterdir()
                  if d.is_dir() and not d.name.startswith(("_", ".")))


def sends_of(b):
    d = MONTH.CH.BP.brand_path(b, "email-sms", "sends", root=BRANDS)
    return sorted(d.glob("*.md")) if d.is_dir() else []


def brands_with_sends():
    return [b for b in brand_folders() if sends_of(b)]


class SendLinks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.start = time.time()

    @classmethod
    def tearDownClass(cls):
        newer = [str(f) for f in BRANDS.rglob("*")
                 if f.is_file() and f.stat().st_mtime > cls.start]
        if newer:
            raise AssertionError(f"brands/ was written: {newer[:5]}")

    def test_every_send_link_resolves(self):
        checked = 0
        for b in brands_with_sends():
            for f in sends_of(b)[:5]:
                sp = MONTH.send_path(b, f.name)
                self.assertTrue((P.WORKSPACE / sp).is_file(), sp)
                self.assertNotIn("/email/sends/", sp)
                self.assertEqual(serve.send_target(sp), (P.WORKSPACE / sp).resolve())
            checked += 1
        self.assertGreater(checked, 0, "no brand with sends found — a vacuous pass")

    def test_slot_detail_uses_source_brand(self):
        withs = brands_with_sends()
        self.assertTrue(withs, "no brand with sends found")
        b2 = withs[0]
        f = sends_of(b2)[0]
        b1 = next((b for b in brand_folders() if b != b2), b2)
        d = MONTH.slot_detail({"id": "x", "source": f.name, "source_brand": b2}, b1, None)
        self.assertTrue(d["source_path"].startswith(f"brands/{b2}/"), d["source_path"])
        self.assertTrue((P.WORKSPACE / d["source_path"]).is_file())
        d = MONTH.slot_detail({"id": "x", "source": "[open]"}, b1, None)
        self.assertIsNone(d["source_path"])
        self.assertTrue(d["unfilled"])
        d = MONTH.slot_detail({"id": "x", "source": ""}, b1, None)
        self.assertIsNone(d["source_path"])

    def test_send_target_refuses(self):
        withs = brands_with_sends()
        self.assertTrue(withs, "no brand with sends found")
        b = withs[0]
        real = MONTH.send_path(b, sends_of(b)[0].name)
        for want in (real + "/../../CLAUDE.md",
                     real.rsplit("/", 1)[0] + "/../../CLAUDE.md",
                     "../x.md",
                     "/etc/passwd.md",
                     f"brands/{b}/strategy/x.md",
                     f"brands/{b}/email-sms/sends/no-such-send-zz.md",
                     "brands/.x/email-sms/sends/a.md",
                     f"brands/{b}/email-sms/sends/.hidden.md",
                     "",
                     None):
            self.assertIsNone(serve.send_target(want), want)

    def test_old_shape_gone(self):
        comp = MACHINE.parent
        for name in ("month.py", "serve.py"):
            self.assertNotIn("email/sends", (MACHINE / name).read_text(), name)
        self.assertNotIn("/email/sends/", (comp / "CONTRACT.md").read_text())
        delivery = P.WORKSPACE / "tools" / "email-production" / "DELIVERY.md"
        self.assertNotIn("brands/<brand>/email/sends", delivery.read_text())


if __name__ == "__main__":
    unittest.main()
