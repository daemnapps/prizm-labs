"""Tests for the prompt upgrade test. Neutral fixtures; no model, no network."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "machine"))
import bakeoff as B  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.d = self.root / "test"
        self.inputs = self.root / "in"
        self.old_out, self.new_out = self.root / "old", self.root / "new"
        for p in (self.inputs, self.old_out, self.new_out):
            p.mkdir()
        for cid in ("s1", "s2", "s3", "h1"):
            (self.inputs / (cid + ".md")).write_text("swipe " + cid)
            (self.old_out / (cid + ".md")).write_text("OLD draft of %s from stage4e-audit-v11-owner\nline two" % cid)
            (self.new_out / (cid + ".md")).write_text("NEW draft of %s from stage4e-audit-v12-owner\nline two" % cid)

    def case(self, cid):
        return "%s=%s" % (cid, self.inputs / (cid + ".md"))

    def freeze(self):
        return B.freeze(self.d, "audit", "v11", "v12", [self.case(c) for c in ("s1", "s2", "s3")], [self.case("h1")])


class Freeze(Base):
    def test_freeze_records_hashes_and_hides_heldout_id(self):
        m = self.freeze()
        self.assertEqual([c["id"] for c in m["cases"]], ["s1", "s2", "s3"])
        st = B.status(self.d)
        self.assertNotIn("h1", json.dumps(st))
        self.assertIn("1 held back", st["heldout"])

    def test_refuses_second_freeze(self):
        self.freeze()
        with self.assertRaises(B.BakeoffError):
            self.freeze()

    def test_needs_a_heldout_case(self):
        with self.assertRaises(B.BakeoffError):
            B.freeze(self.d, "audit", "v11", "v12", [self.case("s1")], [])

    def test_same_label_refused(self):
        with self.assertRaises(B.BakeoffError):
            B.freeze(self.d, "audit", "v11", "V11", [self.case("s1")], [self.case("h1")])

    def test_tampered_manifest_detected(self):
        self.freeze()
        p = self.d / B.MANIFEST
        m = json.loads(p.read_text())
        m["cases"][0]["id"] = "other"
        p.write_text(json.dumps(m))
        with self.assertRaises(B.BakeoffError):
            B.status(self.d)


class Pack(Base):
    def test_blind_packet_has_no_version_labels(self):
        self.freeze()
        B.pack(self.d, self.old_out, self.new_out)
        text = (self.d / B.BLIND / "s1.md").read_text()
        for lab in ("v11", "v12", "stage4e-audit"):
            self.assertNotIn(lab, text)
        self.assertIn("## Draft A", text)
        self.assertNotIn("OLD draft of s1 from [version]\nline two\n\n## Draft B\n\nOLD", text)

    def test_key_maps_both_drafts_and_is_stable(self):
        self.freeze()
        B.pack(self.d, self.old_out, self.new_out)
        key = json.loads((self.d / B.KEY).read_text())
        for cid in ("s1", "s2", "s3"):
            self.assertEqual({key[cid]["A"], key[cid]["B"]}, {"old", "new"})
            text = (self.d / B.BLIND / (cid + ".md")).read_text()
            first = "NEW" if key[cid]["A"] == "new" else "OLD"
            self.assertIn("## Draft A\n\n%s draft" % first, text)

    def test_order_varies_across_cases(self):
        self.freeze()
        B.pack(self.d, self.old_out, self.new_out)
        key = json.loads((self.d / B.KEY).read_text())
        self.assertGreater(len({key[c]["A"] for c in key}), 0)

    def test_frozen_pack_does_not_include_heldout(self):
        self.freeze()
        r = B.pack(self.d, self.old_out, self.new_out)
        self.assertNotIn("h1", r["packed"])
        self.assertFalse((self.d / B.BLIND / "h1.md").exists())

    def test_heldout_runs_once(self):
        self.freeze()
        B.pack(self.d, self.old_out, self.new_out)
        r = B.pack(self.d, self.old_out, self.new_out, final=True)
        self.assertEqual(r["packed"], ["h1"])
        with self.assertRaises(B.BakeoffError):
            B.pack(self.d, self.old_out, self.new_out, final=True)

    def test_missing_output_refused(self):
        self.freeze()
        (self.new_out / "s2.md").unlink()
        with self.assertRaises(B.BakeoffError):
            B.pack(self.d, self.old_out, self.new_out)

    def test_leak_warning_for_heading_only_new_prints(self):
        self.freeze()
        for cid in ("s1", "s2", "s3"):
            (self.new_out / (cid + ".md")).write_text("**VERDICT**\n\n**COPY GATES**\nbody")
            (self.old_out / (cid + ".md")).write_text("**VERDICT**\n\nbody")
        r = B.pack(self.d, self.old_out, self.new_out)
        self.assertTrue(any("copy gates" in w for w in r["warnings"]))

    def test_bare_hook_ids_are_not_stripped(self):
        out, _ = B.strip_labels("V1 and V2 open the piece, stage4e-audit-v11-owner", ["v11", "v12"])
        self.assertIn("V1 and V2", out)
        self.assertNotIn("stage4e-audit", out)


class Reveal(Base):
    def packed(self):
        self.freeze()
        B.pack(self.d, self.old_out, self.new_out)
        return json.loads((self.d / B.KEY).read_text())

    def judgments(self, key, new_better, old_better, cases=("s1", "s2", "s3")):
        out = []
        for cid in cases:
            a_new = key[cid]["A"] == "new"
            out.append({"case": cid,
                        "a_better": new_better if a_new else old_better,
                        "b_better": old_better if a_new else new_better,
                        "gets_around": {"A": ["a loophole"], "B": []}})
        return out

    def test_fixed_and_broke_are_mapped_through_the_key(self):
        key = self.packed()
        rep = B.reveal(self.d, self.judgments(key, ["opens on conflict"], ["lost the ask"]))
        self.assertEqual(rep["cases"]["s1"]["fixed"], ["opens on conflict"])
        self.assertEqual(rep["cases"]["s1"]["broke"], ["lost the ask"])

    def test_gets_around_is_attached_to_old_or_new(self):
        key = self.packed()
        rep = B.reveal(self.d, self.judgments(key, ["x"], ["y"]))
        who = "new" if key["s1"]["A"] == "new" else "old"
        self.assertEqual(rep["cases"]["s1"]["gets_around"][who], ["a loophole"])

    def test_score_fields_refused(self):
        key = self.packed()
        j = self.judgments(key, ["x"], [])
        j[0]["score"] = 8
        with self.assertRaises(B.BakeoffError):
            B.reveal(self.d, j)

    def test_all_frozen_cases_must_be_judged(self):
        key = self.packed()
        with self.assertRaises(B.BakeoffError):
            B.reveal(self.d, self.judgments(key, ["x"], [], cases=("s1",)))

    def test_heldout_holds_when_nothing_broke(self):
        key = self.packed()
        B.pack(self.d, self.old_out, self.new_out, final=True)
        key = json.loads((self.d / B.KEY).read_text())
        j = self.judgments(key, ["x"], [], cases=("s1", "s2", "s3", "h1"))
        rep = B.reveal(self.d, j)
        self.assertTrue(rep["heldout"]["h1"]["holds"])

    def test_heldout_fails_to_hold_when_old_was_better(self):
        key = self.packed()
        B.pack(self.d, self.old_out, self.new_out, final=True)
        key = json.loads((self.d / B.KEY).read_text())
        j = self.judgments(key, ["x"], ["lost something"], cases=("s1", "s2", "s3", "h1"))
        self.assertFalse(B.reveal(self.d, j)["heldout"]["h1"]["holds"])

    def test_report_without_heldout_says_so_and_has_no_total(self):
        key = self.packed()
        text = B.render(B.reveal(self.d, self.judgments(key, ["x"], [])))
        self.assertIn("held-back case not run yet", text)
        self.assertIn("No score", text)


class Cli(Base):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = B.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_full_flow(self):
        code, out, _ = self.run_cli("freeze", "--dir", str(self.d), "--stage", "audit", "--old", "v11", "--new", "v12",
                                    "--case", self.case("s1"), "--heldout", self.case("h1"))
        self.assertEqual(code, 0, out)
        code, out, _ = self.run_cli("pack", "--dir", str(self.d), "--old-out", str(self.old_out), "--new-out", str(self.new_out))
        self.assertEqual(code, 0)
        key = json.loads((self.d / B.KEY).read_text())
        a_new = key["s1"]["A"] == "new"
        jf = self.root / "j.json"
        jf.write_text(json.dumps([{"case": "s1", "a_better": ["p"] if a_new else [], "b_better": [] if a_new else ["p"]}]))
        code, out, _ = self.run_cli("reveal", "--dir", str(self.d), "--judgments", str(jf))
        self.assertEqual(code, 0)
        self.assertIn("fixed 1 · broke 0", out)

    def test_error_is_exit_two(self):
        code, _, err = self.run_cli("status", "--dir", str(self.d))
        self.assertEqual(code, 2)
        self.assertIn("nothing frozen", err)


if __name__ == "__main__":
    unittest.main()
