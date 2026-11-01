"""The variation matrix's customer words come from the language layer (the owner, 2026-10-27: "awareness levels and
verbatims and spice are the foundation of what we're doing here"): the run's avatar, at the ad's awareness level
first, hooks + injection + spice — never the raw bank files ranked by likes. A failed or empty query is said.
Offline; every tree is a temp folder. Read-only on brands/."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "run-kit"))
from run_kit import paths  # noqa: E402

sys.path.insert(0, str(HERE))
import brandctx  # noqa: E402

BRAND, AVATAR = "zz-brand", "a1"


def row(rid, text, use, level=None):
    r = {"id": rid, "text": text, "status": "active", "use": [use], "source": {"name": "a test"}}
    if level:
        r["awareness"] = {"level": level}
    return r


class LanguageLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):      # one clone for the class: brandpath is imported from it once and stays cached
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name).resolve() / "clone"
        bp = cls.root / "components" / "brandpath"
        bp.mkdir(parents=True)
        shutil.copy(paths.repo(HERE) / "components" / "brandpath" / "brandpath.py", bp / "brandpath.py")
        lang = cls.root / "brands" / BRAND / "core-avatars" / AVATAR / "language"
        lang.mkdir(parents=True)
        (lang / "bank.json").write_text(json.dumps({"entries": [
            row("language_p1", "the problem-aware line we want", "hook", "problem-aware"),
            row("language_m1", "the most-aware line we must not get", "hook", "most-aware"),
            row("language_s1", "the room's own spice word", "in-word"),
        ]}))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_level_and_the_avatar_reach_the_query(self):
        with contextlib.redirect_stderr(io.StringIO()):
            got = brandctx.BrandContext(self.root, BRAND, AVATAR, "`problem-aware` — must not …").language()
        self.assertIn("the problem-aware line we want", got)
        self.assertNotIn("the most-aware line we must not get", got)       # a row at another level is held back
        self.assertIn("spoken at the problem-aware level first", got)
        self.assertIn("the room's own spice word", got)                     # spice comes with it
        self.assertIn("[language_p1]", got)                                 # cited by id

    def test_no_level_reads_every_level(self):
        with contextlib.redirect_stderr(io.StringIO()):
            got = brandctx.BrandContext(self.root, BRAND, AVATAR).language()
        self.assertIn("the most-aware line we must not get", got)

    def test_an_empty_stage_is_said(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = brandctx.BrandContext(self.root, BRAND, AVATAR, "unaware").language()
        self.assertIn("injection: NO ROWS", got)
        self.assertIn("no rows for a1", err.getvalue())

    def test_a_failed_layer_is_said_never_a_raw_read(self):
        err = io.StringIO()
        with mock.patch.object(brandctx.subprocess, "run", side_effect=OSError("no python")), \
                contextlib.redirect_stderr(err):
            got = brandctx.BrandContext(self.root, BRAND, AVATAR, "unaware").language()
        self.assertIn("FAILED", got)
        self.assertNotIn("the problem-aware line we want", got)
        self.assertIn("language layer failed", err.getvalue())

    def test_plan_passes_the_runs_awareness(self):
        src = (HERE / "run.py").read_text()
        self.assertIn('brandctx.level_of(corpus.kv(run.audience, "AWARENESS"))', src)
        self.assertIn("brandctx.BrandContext(repo, brand, avatar, awareness)", src)


if __name__ == "__main__":
    unittest.main()
