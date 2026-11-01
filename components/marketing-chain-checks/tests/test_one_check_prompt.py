"""SI-145 (one check prompt): the shared copy-check prompt nobody read is gone
with its dead folder constant, and no code names either — the copy check that
gates email is email-production's own step 8c. Offline, stdlib unittest
(python3 tests/test_one_check_prompt.py)."""
import importlib, os, sys, unittest
from pathlib import Path

COMP = Path(__file__).resolve().parents[1]
WS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(COMP))

# Built from parts so this file is not a hit in its own tree walk.
PROMPT_NAME = "copy-check" + "-v1"
CONST = "COPY_CHECK" + "_PROMPT"
SKIP = {".git", "runs", "platform/data", "new-workflow-design/builds/atlas"}
# The one name-reader left: a lab display list (:26) that skips a missing file
# (:54-56). Lab is not edited by this card.
EXCEPTION = "lab/damon/system-blueprint/prompts_page.py"


def readers():
    hits = []
    for root, dirs, files in os.walk(WS):
        rel = Path(root).relative_to(WS).as_posix()
        dirs[:] = [d for d in dirs
                   if (d if rel == "." else f"{rel}/{d}") not in SKIP]
        for f in files:
            if not f.endswith(".py"):
                continue
            p = Path(root) / f
            try:
                text = p.read_text(errors="ignore")
            except OSError:
                continue
            if PROMPT_NAME in text or CONST in text:
                hits.append(p.relative_to(WS).as_posix())
    return sorted(hits)


class OneCheckPrompt(unittest.TestCase):
    def test_prompt_file_is_gone(self):
        self.assertTrue((WS / "components").is_dir())
        self.assertFalse((COMP / "prompts" / f"{PROMPT_NAME}-damon.md").exists())
        self.assertEqual(sorted((COMP / "prompts").glob(f"{PROMPT_NAME}*")), [])

    def test_package_imports_without_the_constant(self):
        m = importlib.import_module("marketing_chain_checks")
        self.assertFalse(hasattr(m, CONST))
        self.assertTrue(callable(m.read_check_block))      # the check itself stays

    def test_no_code_names_the_prompt_but_the_lab_display_list(self):
        self.assertEqual(readers(), [EXCEPTION])

    def test_tombstone_still_imports(self):
        sys.path.insert(0, str(WS / "components" / "quality-checks"))
        qc = importlib.import_module("quality_checks")
        self.assertIs(qc, importlib.import_module("marketing_chain_checks"))
        self.assertFalse(hasattr(qc, CONST))


if __name__ == "__main__":
    unittest.main()
