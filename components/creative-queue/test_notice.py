"""notice.py: owner's session-start line for creator's cuts (email_lead, 2026-11-06: "Al abrir sesión"; owner's since 2026-11-11).

Each cut is named once, when its returned/ files grow; only the reviewer hears; no page server or a failed read says
nothing and never raises. Stdlib only, no network (the page server is a stub), no git.

    python3 components/creative-queue/test_notice.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import notice  # noqa: E402


def row(key, files, title="A cut", brand="brand_a"):
    return {"key": key, "brand": brand, "title": title, "returned_files": files, "returned_work": files,
            "drive_url": "https://drive.example/" + key}


class Brief(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="notice-"))
        (self.dir / "config.json").write_text(json.dumps({"person": "owner", "port": 8742}))
        self.rows = [row("brand_a_x_brief-0001", 0), row("brand_a_x_brief-0002", 3, "Barber Mission")]
        self.said = []

    def tearDown(self):
        shutil.rmtree(str(self.dir), ignore_errors=True)

    def run_brief(self, person="owner", fetch=None):
        return notice.brief(person, self.dir, fetch=fetch or (lambda port: {"rows": self.rows}), say=self.said.append)

    def test_a_cut_back_is_named_once(self):
        self.assertEqual(self.run_brief(), 1)
        self.assertIn("creator: 1 video back in returned/", self.said[0])
        self.assertIn("Barber Mission (brand_a, 3 files back) https://drive.example/brand_a_x_brief-0002", self.said[0])
        self.assertEqual(self.run_brief(), 0, "the next session says nothing new")
        self.assertEqual(len(self.said), 1)

    def test_more_files_back_is_new_again(self):
        self.run_brief()
        self.rows[1] = row("brand_a_x_brief-0002", 5, "Barber Mission")
        self.rows[0] = row("brand_a_x_brief-0001", 2, "Street interview")
        self.assertEqual(self.run_brief(), 2)
        self.assertIn("2 videos back", self.said[-1])

    def test_only_the_reviewer_hears(self):
        self.assertEqual(self.run_brief(person="email_lead"), 0, "email_lead facilitates; owner checks the cuts (2026-11-11)")
        self.assertEqual(self.run_brief(person="editor"), 0)
        self.assertEqual(self.said, [])
        self.assertFalse((self.dir / notice.SEEN).exists(), "nothing written for anyone else")

    def test_no_page_server_says_nothing(self):
        def down(port):
            raise OSError("connection refused")
        self.assertEqual(self.run_brief(fetch=down), 0)
        self.assertEqual(self.said, [])
        (self.dir / "config.json").unlink()
        self.assertEqual(self.run_brief(), 0, "no config: nothing")

    def test_the_hook_runs_it_for_the_session_start(self):
        hook = (HERE.parent.parent / ".claude" / "hooks" / "task-greeting.sh").read_text()
        self.assertIn('components/creative-queue/notice.py" brief 2>/dev/null', hook)


if __name__ == "__main__":
    unittest.main()
