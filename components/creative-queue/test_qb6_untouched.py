"""QB-6 (content queue page): the page's read door writes nothing, and the page asks for nothing else.

Narrowed at merge by the dev-pm lead [2bdd01], 2026-10-23. The first form pinned runs/queue/, lab/, brands/,
emails.html, the team's page and both switch files by blob hash at the dispatch base, which proves the branch left them
alone but turns red on main at the next ordinary commit under any of them (the maker said so). That half was
checked once, on the branch diff, at merge. What stays true for good, and is checked here:

1. components/creative-queue/view.py contains no write: no open() for writing, no write_text / write_bytes, none of
   qcore's writers (write_observation, write_index, append_decision, commit_paths), no subprocess, no os.remove.
   (Running it on fixtures leaves them byte-identical: test_qb6_view.py.)
2. content-queue.sources.json declares the `queue` source, whose argv is view.py and nothing else. Narrowed for QB-9
   (the team statics), 2026-10-29: its one other source is `statics`, `statics.py list` (the team's hand-offs from Drive; it
   writes only its own picture cache), and its one runs/ folder is that cache, runs/creative-queue/statics/; never
   runs/queue/ or runs/queue-shadow/. QB-11 (the team view) adds `videos`, the same door with --role video-editor (no
   pictures, so no runs/ folder of its own).

    python3 components/creative-queue/test_qb6_untouched.py
"""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402

REPO = paths.repo(HERE)
VIEW = HERE / "view.py"
SOURCES = REPO / "platform/views/viewers/_templates/content-queue.sources.json"

WRITES = [
    r"open\([^)]*['\"][wax]\+?b?['\"]",
    r"\bwrite_text\(", r"\bwrite_bytes\(",
    r"\bwrite_observation\(", r"\bwrite_index\(", r"\bappend_decision\(", r"\bcommit_paths\(",
    r"\bsubprocess\b", r"\bos\.(remove|unlink|rename|replace)\(", r"\bshutil\.",
]


class ReadOnly(unittest.TestCase):
    def test_view_has_no_write(self):
        text = VIEW.read_text()
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
        found = [w for w in WRITES if re.search(w, code)]
        self.assertEqual(found, [], "view.py must write nothing")

    def test_page_reads_only_the_view(self):
        doc = json.loads(SOURCES.read_text())
        names = [k for k, v in doc.items() if isinstance(v, dict) and "argv" in v]
        self.assertEqual(names, ["queue", "statics", "videos"])   # videos: QB-11 (the team view), the same door by role
        self.assertEqual(doc["queue"]["argv"], ["components/creative-queue/view.py"])
        self.assertEqual(doc["statics"]["argv"], ["components/creative-queue/statics.py", "list"])
        self.assertEqual(doc["videos"]["argv"], ["components/creative-queue/statics.py", "list", "--role", "video-editor"])
        self.assertEqual(doc.get("runs"), ["creative-queue/statics/"], "the page reads only the statics picture cache")


if __name__ == "__main__":
    unittest.main()
