"""file_record.py files one decision-log act, or refuses with the reason. Behaviour through the CLI seam (main(argv)),
never code position. Writes nothing: every passing case is --dry-run."""
import contextlib, io, json, subprocess, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import file_record  # noqa: E402

ROOT = HERE.parents[2]
SHA = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        file_record.main(list(argv))
    return out.getvalue()


class Refuses(unittest.TestCase):
    def refused(self, *argv):
        with self.assertRaises(SystemExit) as c:
            run(*argv)
        self.assertIn("refused", str(c.exception))
        return str(c.exception)

    def test_change_needs_commit_and_test(self):
        self.assertIn("--commit", self.refused("change", "--item", "intake#6", "--who", "pm"))
        self.assertIn("--test", self.refused("change", "--item", "intake#6", "--who", "pm", "--commit", SHA))

    def test_commit_is_a_sha_never_a_branch(self):
        self.assertIn("never a branch", self.refused("change", "--item", "intake#6", "--who", "pm", "--commit", "main", "--test", "t"))

    def test_close_evidence_is_pinned(self):
        self.assertIn("path:line@sha", self.refused("close", "--item", "intake#6", "--who", "pm", "--evidence", "README.md"))

    def test_undo_names_a_record(self):
        self.assertIn("names no record", self.refused("undo", "--item", "intake#6", "--who", "owner", "--undoes", "nope.json"))

    def test_why_is_one_line(self):
        self.refused("draft", "--item", "intake#6", "--who", "pm", "--why", "x" * 201)


class Files(unittest.TestCase):
    def test_change_record_shape(self):
        rec = json.loads(run("change", "--item", "intake #6", "--who", "the team", "--theme", "components", "--commit", SHA,
                             "--test", "t", "--areas", "path:components/intake", "--why", "w", "--dry-run"))
        self.assertEqual((rec["kind"], rec["item"], rec["reviewer"]), ("triage", "intake-6", "pm"))
        self.assertEqual(rec["verdict"]["act"], "change")
        self.assertEqual(rec["verdict"]["item"], "intake #6")
        self.assertEqual(rec["verdict"]["areas"], ["path:components/intake"])

    def test_operations_forward(self):
        rec = json.loads(run("forward", "--item", "movement:brand-b", "--who", "the team", "--forwarded-to", "engineer", "--dry-run"))
        self.assertEqual(rec["item"], "movement-brand-b")
        self.assertEqual(rec["verdict"]["forwarded_to"], "engineer")


if __name__ == "__main__":
    unittest.main()
