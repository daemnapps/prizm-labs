"""image-edit — edits never overwrite (SI-158 (edits never overwrite)).

A second multi-roll edit is v2, never v1 again; a judge that answered part of
the test never passes; a missing judge key is a hold, not a crash; a fix row
that is not draft or approved is refused, naming its status; a destination
that already exists is never copied over.

No key, no network, no PIL; writes only under `tempfile`.

    /usr/bin/python3 tools/image-edit/tests/test_ref1_never_overwrite.py
"""
import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "image-production"))
import image_edit as RE  # noqa: E402
from image_edit import compare as CMP, engine as E  # noqa: E402

PROMPTS = HERE / "prompts"


def png_bytes(w=4, h=5):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def answering(payload):
    def caller(prompt, paths, entry):
        return payload if isinstance(payload, str) else json.dumps(payload)
    return caller


def compare(caller, extra=()):
    return CMP.compare("ref.png", "res.png", "the tube is in her left hand", list(extra),
                       entry={}, caller=caller, folder=PROMPTS)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="refedit-si158-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ------------------------------------------------------------- the version

class TestVersion(Tmp):
    def test_a_multi_roll_v1_makes_the_next_edit_v2(self):
        done = self.tmp / "s--edit"
        done.mkdir()
        for f in ("s--edit-v1-01.png", "s--edit-v1-02.png"):
            (done / f).write_bytes(png_bytes())
        self.assertEqual(E._version(self.tmp / "s--edit-again", "s"), 2)

    def test_single_and_multi_roll_names_both_count(self):
        (self.tmp / "s--edit-v3.png").write_bytes(png_bytes())
        (self.tmp / "s--logo-v4-07.png").write_bytes(png_bytes())
        self.assertEqual(E._version(self.tmp / "run", "s"), 5)


# ------------------------------------------------------------ the judge fold

class TestStrictFold(unittest.TestCase):
    def test_a_full_answer_still_passes_and_a_fail_still_rejects(self):
        n = len(CMP.STANDING)
        verdict, fails, tests, _raw = compare(answering(
            {"results": [{"test": i + 1, "verdict": "PASS"} for i in range(n)]}))
        self.assertEqual((verdict, fails, len(tests)), ("pass", [], n))
        verdict, fails, _t, _raw = compare(answering(
            {"results": [{"test": 1, "verdict": "PASS"}, {"test": 2, "verdict": "FAIL", "evidence": "moved"}]}))
        self.assertEqual(verdict, "reject")
        self.assertIn("NOTHING ELSE MOVED", fails[0])

    def test_an_answer_to_part_of_the_test_never_passes(self):
        extra = ["the logo is the brand's own"]
        for payload in ({}, {"results": []},
                        {"results": [{"test": 1, "verdict": "PASS"}]},               # 1 of 3
                        {"results": [{"test": 1, "verdict": "PASS"}, {"test": 1, "verdict": "PASS"},
                                     {"test": 2, "verdict": "PASS"}]},              # 3 is missing, 1 twice
                        {"results": [{"test": i, "verdict": "PASS"} for i in (1, 2, 3, 4)]},  # one extra
                        {"results": [{"test": 1, "verdict": "PASS"}, {"test": 2, "verdict": "PASS"},
                                     {"test": 3, "verdict": "MAYBE"}]}):
            verdict, fails, tests, raw = compare(answering(payload), extra)
            self.assertEqual(verdict, "reject", payload)
            self.assertEqual(len(fails), 1, payload)
            self.assertTrue(fails[0].startswith("judge answer incomplete"), fails[0])
            self.assertEqual(len(tests), 3)
            self.assertTrue(raw)

    def test_a_missing_key_is_a_hold_not_a_crash(self):
        def no_key(prompt, paths, entry):
            raise SystemExit("no GEMINI_API_KEY on this machine")
        verdict, fails, _tests, raw = compare(no_key)
        self.assertEqual(verdict, "reject")
        self.assertTrue(fails[0].startswith("compare judge did not run: SystemExit"), fails[0])
        self.assertIn("GEMINI_API_KEY", fails[0])
        self.assertEqual(raw, "")


# ---------------------------------------------------------- the fix status

class TestFixStatus(Tmp):
    def test_a_fix_that_is_not_draft_or_approved_is_refused_naming_its_status(self):
        table, _path = RE.fixes()
        status = table["text"]["status"]
        self.assertNotIn(status, ("draft", "approved"))
        pic = self.tmp / "p.png"
        pic.write_bytes(png_bytes())
        with self.assertRaises(RE.BadRequest) as cm:
            RE.resolve({"brand": "acme", "picture": str(pic), "out": str(self.tmp / "out"),
                        "fix": "text", "args": {"was": "SAALE", "now": "SALE"}})
        self.assertIn("text", str(cm.exception))
        self.assertIn(status, str(cm.exception))


# ----------------------------------------------------- the destination

class TestNeverCopiedOver(Tmp):
    def fake_ip(self, out):
        def make(req, **kw):
            p = Path(req["out"]) / "made.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(png_bytes(4, 5) + b"new")
            return {"model": "stub", "prompt": req["direction"], "held": [],
                    "pictures": [{"file": str(p), "content": str(p)}], "delivered": [str(p)]}
        return SimpleNamespace(make=make, route=SimpleNamespace(aspects=lambda: {}, judge_entry=lambda: {}))

    def test_a_pass_whose_destination_exists_is_held_and_the_file_is_untouched(self):
        pic = self.tmp / "p.png"
        pic.write_bytes(png_bytes())
        out = self.tmp / "run" / "p--edit"
        out.mkdir(parents=True)
        dest = out / "p--edit-v1.png"
        dest.write_bytes(b"the delivered file")
        n = len(CMP.STANDING)
        all_pass = answering({"results": [{"test": i + 1, "verdict": "PASS"} for i in range(n)]})
        with mock.patch.object(E.P, "image_production", lambda: self.fake_ip(out)), \
                mock.patch.object(E, "_version", lambda out, stem: 1):
            r = RE.edit({"brand": "acme", "picture": str(pic), "out": str(out),
                         "change": "the tube is in her left hand"},
                        compare_caller=all_pass, mirror=False)
        self.assertEqual(dest.read_bytes(), b"the delivered file")
        self.assertEqual(r["state"], "held")
        self.assertEqual(r["delivered"], [])
        self.assertEqual(len(r["rejected"]), 1)
        self.assertEqual(r["rejected"][0]["fails"], ["destination exists: p--edit-v1.png — never overwritten"])
        self.assertEqual(Path(r["rejected"][0]["file"]), out / "rejected" / "p--edit-v1.png")
        self.assertIn("never overwritten", (out / "rejected" / "p--edit-v1-why.md").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
