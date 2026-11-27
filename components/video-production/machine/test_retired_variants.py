"""A retired (deprecated) variant never resolves, never matches, and never gets re-filed;
the live layout keeps one family per format and no variant shadows a family."""
import json
import os
import tempfile
import unittest
from pathlib import Path

import playbook as PB
import playbook_builder as B
import workflow_catalog as C

SIG = {"audio": "voice", "speakers": 1, "address": "to-camera", "settings": 1,
       "product_role": "none", "pacing": "medium", "capture": "studio", "story": "pitch"}


def fam(fid, variants):
    return {"format_id": fid, "name": fid, "status": "draft", "family": fid, "signature": dict(SIG),
            "stage_order": [], "stages": {}, "failures": [], "cost": {}, "quality_bar": [],
            "variants": variants}


class RetiredVariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.old = os.environ.get("VIDEO_PLAYBOOKS_DIR")
        os.environ["VIDEO_PLAYBOOKS_DIR"] = str(self.dir)
        PB.write(fam("talk-family", [
            {"id": "live-one", "status": "draft", "signature": dict(SIG)},
            {"id": "gone-one", "status": "deprecated", "state": "retired: test",
             "replaced_by": "talk-family", "signature": dict(SIG)}]))

    def tearDown(self):
        if self.old is None:
            os.environ.pop("VIDEO_PLAYBOOKS_DIR", None)
        else:
            os.environ["VIDEO_PLAYBOOKS_DIR"] = self.old
        self.tmp.cleanup()

    def test_retired_variant_does_not_resolve(self):
        self.assertEqual(PB.find_variant("live-one")[1]["id"], "live-one")
        self.assertEqual(PB.find_variant("gone-one"), (None, None))
        self.assertEqual(PB.playbook_for("gone-one")["_source"], "default")
        self.assertEqual(PB.retired_variant("gone-one")[1]["replaced_by"], "talk-family")

    def test_builder_never_matches_through_a_retired_variant(self):
        vias = [r["via"] for r in B.nearest(SIG)]
        self.assertNotIn("variant:gone-one", vias)

    def test_md_twin_marks_the_retirement(self):
        md = (self.dir / "talk-family.md").read_text()
        self.assertIn("**retired:** retired: test", md)
        self.assertIn("`talk-family`", md)


class LiveLayoutTests(unittest.TestCase):
    """Against the real folder."""

    def setUp(self):
        self.old = os.environ.pop("VIDEO_PLAYBOOKS_DIR", None)

    def tearDown(self):
        if self.old is not None:
            os.environ["VIDEO_PLAYBOOKS_DIR"] = self.old

    def test_no_live_variant_shadows_a_family(self):
        own = {p.stem for p in PB.root().glob("*.json")}
        for f in PB.families():
            for v in PB.live_variants(f):
                self.assertNotIn(PB.normalise_id(v.get("id")), own,
                                 "%s variant %s is shadowed by its own family" % (f["format_id"], v.get("id")))

    def test_each_live_variant_id_lives_in_one_family(self):
        seen = {}
        for f in PB.families():
            for v in PB.live_variants(f):
                vid = PB.normalise_id(v.get("id"))
                self.assertNotIn(vid, seen, "%s in %s and %s" % (vid, seen.get(vid), f["format_id"]))
                seen[vid] = f["format_id"]

    def test_retired_ids_resolve_as_intended(self):
        ws = Path(__file__).resolve().parents[3]
        self.assertEqual(C.resolve("micro-drama", ws)["family"], "micro-drama")
        self.assertEqual(C.resolve("meme", ws)["family"], "default")
        self.assertEqual(C.resolve("micro-drama", ws)["variant_matches"], [])
        with self.assertRaisesRegex(ValueError, "run it as narrator-montage"):
            C.resolve("vo-montage", ws)


if __name__ == "__main__":
    unittest.main()
