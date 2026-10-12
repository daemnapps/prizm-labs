#!/usr/bin/env python3
"""HE-1 (fact rulings), the card's test: a held October email is cleared by
rulings alone and goes on to its Klaviyo DRAFT.

    python3 test_he1_held_email_rulings.py

The real held run (brand-b-oct-03--avatar-one: five product-fact problems, no
price) is COPIED into a temp workspace whose brands/ is a symlink to the
repo's, read only. Then: the build holds it with five items; every item is
ruled with rule.py (four true, the WRONG one true-once); the build passes with
five cleared; the uploader's dry run accepts. No network, no model, no
Klaviyo, no key; nothing is written under brands/ or the repo's records.
"""
import contextlib
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="he1-held-email-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
REPO = next(d for d in HERE.parents if (d / "components" / "brand-finder").is_dir())
BRAND, LABEL = "brand-b", "brand-b-oct-03--avatar-one"
SOURCE = (REPO / "platform/data/records/lab-runs/editor/editor-brand-b-oct-2026-mini-oct-05-07" / LABEL)
COPY = TMP / "runs" / "email-production" / BRAND / LABEL
RULE = REPO / "components" / "quality-checks" / "rule.py"
FACTS = ["SERUM goes on right after cleansing, while the face is still damp.",
         "SERUM holds water in and regulates oil.",
         "Aloe vera in SERUM calms post-shave irritation.",
         "A WIDGET session runs about sixty seconds."]


def brand_state():
    """(path, size, mtime) of every file in the brand folder the run reads."""
    out = []
    for d, _dirs, files in os.walk(REPO / "brands" / BRAND):
        for f in files:
            st = os.stat(os.path.join(d, f))
            out.append((os.path.join(d, f), st.st_size, st.st_mtime_ns))
    return sorted(out)


def run(*args):
    env = dict(os.environ, AI_WORKSPACE=str(TMP))
    return subprocess.run([sys.executable, *map(str, args)], cwd=HERE, env=env,
                          capture_output=True, text=True, timeout=240)


def delivery():
    return json.loads((COPY / "deliverable" / "check.json").read_text())["delivery"]


class TheHeldEmailIsClearedByRulings(unittest.TestCase):
    def test_rule_every_problem_then_the_draft_is_accepted(self):
        shutil.copytree(SOURCE, COPY)
        (TMP / "brands").symlink_to(REPO / "brands", target_is_directory=True)
        repo_rulings = REPO / "platform/data/records/fact-rulings"
        before_repo = sorted(repo_rulings.glob("*")) if repo_rulings.is_dir() else []
        before_brand = brand_state()

        # (a) held, five items, all product facts
        r = run("simple_email.py", COPY, "--brand", BRAND, "--no-images")
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("HELD — not sent to Klaviyo", r.stderr)
        d = delivery()
        self.assertEqual(d["result"], "HELD")
        self.assertEqual(len(d["items"]), 5)
        self.assertEqual([i["kind"] for i in d["items"]], ["fact"] * 5)
        self.assertEqual(d["problems"], [i["text"] for i in d["items"]])
        self.assertEqual(d["cleared"], [])

        # (b) rule every one: four true with the fact, the WRONG one true-once
        facts = iter(FACTS)
        for it in d["items"]:
            if it["text"].startswith("product fact WRONG"):
                args = [it["id"], "true-once", "--reason", "the routine order is right for this send"]
            else:
                args = [it["id"], "true", next(facts)]
            r = run(RULE, COPY, *args, "--by", "brand-editor")
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(list((TMP / "platform/data/records/fact-rulings").glob("*.json"))), 5)

        # (c) the build passes, every problem cleared and named
        r = run("simple_email.py", COPY, "--brand", BRAND, "--no-images")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = delivery()
        self.assertEqual((d["result"], d["problems"], d["items"]), ("pass", [], []))
        self.assertEqual(len(d["cleared"]), 5)
        self.assertEqual(sorted(c["ruling"] for c in d["cleared"]), ["true"] * 4 + ["true-once"])
        self.assertEqual(r.stdout.count("cleared by brand-editor's"), 5)

        # (d) the uploader's dry run accepts: no subprocess, no socket, nothing written
        media = COPY / "media"
        media.mkdir(exist_ok=True)
        (media / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n stand-in")
        before_deliv = sorted(p.name for p in (COPY / "deliverable").rglob("*"))
        sys.path.insert(0, str(HERE))
        import klaviyo_upload as K

        def refuse(*a, **k):
            raise AssertionError("the dry run reached out")
        out = io.StringIO()
        with mock.patch.object(socket.socket, "connect", refuse), \
                mock.patch.object(subprocess, "run", refuse), contextlib.redirect_stdout(out):
            code = K.main(["--run", str(COPY), "--dry-run"])
        self.assertEqual(code, 0, out.getvalue())
        st = json.loads(out.getvalue())
        gate = next(c for c in st["checks"] if c["check"] == "delivery gate")
        self.assertEqual(gate["result"], "ok", gate)
        self.assertEqual(sorted(p.name for p in (COPY / "deliverable").rglob("*")), before_deliv)

        # brands/ and the repo's records are untouched
        self.assertEqual(brand_state(), before_brand)
        after_repo = sorted(repo_rulings.glob("*")) if repo_rulings.is_dir() else []
        self.assertEqual(after_repo, before_repo)


if __name__ == "__main__":
    unittest.main()
