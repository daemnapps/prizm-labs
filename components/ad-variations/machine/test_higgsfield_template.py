"""python3 machine/test_higgsfield_template.py — the Higgsfield hand-off is a brand-free template in prompts/,
its brand-filled copy lives in the brand's run folder (SI-88). No network, no model, writes nothing."""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
REPO = COMP.parent.parent
BRANDS = [p.name for p in (REPO / "brands").iterdir() if p.is_dir()]

HANDOFF = COMP / "prompts" / "higgsfield-handoff"
V1_NAME = "higgsfield-p2f-v1-damon.md"
V2 = HANDOFF / "higgsfield-p2f-v2-damon.md"
SLOTS = ("brand", "brand_folder", "product", "avatar", "offer", "look_rule", "core_topic")
SLOT_RE = re.compile(r"(\{(?:" + "|".join(sorted(SLOTS, key=len, reverse=True)) + r")\})")


def run_copies():
    return sorted(REPO.glob("runs/ad-variations/*/higgsfield/" + V1_NAME))


def split_block(text):
    """(before, block, after) around the first ```text fence."""
    start = text.index("```text\n") + len("```text\n")
    end = text.index("\n```", start)
    return text[:start], text[start:end], text[end:]


def slot_pattern(block):
    out, seen = [], set()
    for part in SLOT_RE.split(block):
        m = SLOT_RE.fullmatch(part)
        if not m:
            out.append(re.escape(part))
            continue
        name = part[1:-1]
        out.append("(?P=%s)" % name if name in seen else "(?P<%s>.+?)" % name)
        seen.add(name)
    return "".join(out)


class HiggsfieldTemplate(unittest.TestCase):
    def assertNamesNoBrand(self, f):
        t = f.read_text().lower()
        for b in BRANDS:
            self.assertNotIn(b.lower(), t, f"{f.relative_to(REPO)} names {b}")

    def test_brands_found(self):
        self.assertTrue(BRANDS, "no brand folders under brands/ — the no-brand checks would check nothing")

    def test_prompts_name_no_brand_folder(self):
        files = sorted((COMP / "prompts").rglob("*.md"))
        self.assertIn(V2, files)
        for f in files:
            self.assertNamesNoBrand(f)

    def test_format_swap_docstring_names_no_brand(self):
        self.assertNamesNoBrand(HERE / "format_swap.py")

    def test_v1_left_prompts_for_one_run_folder(self):
        self.assertFalse((HANDOFF / V1_NAME).exists())
        self.assertEqual(len(run_copies()), 1, run_copies())

    def test_template_slots_the_filled_copy_and_changes_nothing_else(self):
        v2_block = split_block(V2.read_text())[1]
        copy_block = split_block(run_copies()[0].read_text())[1]
        for name in SLOTS:
            self.assertIn("{%s}" % name, v2_block, name)
        self.assertIn("{brief_link}", v2_block)
        pattern = slot_pattern(v2_block)
        m = re.fullmatch(pattern, copy_block, re.S)
        self.assertIsNotNone(m, "the run copy's text block is not v2's block with its slots filled")
        self.assertIn(m.group("brand_folder"), BRANDS)
        filled = v2_block
        for name in SLOTS:
            filled = filled.replace("{%s}" % name, m.group(name))
        self.assertEqual(filled, copy_block)
        # the guard fires on any literal change outside a slot
        self.assertIsNone(re.fullmatch(pattern, "X" + copy_block, re.S))
        self.assertIsNone(re.fullmatch(pattern, copy_block + "X", re.S))

    def test_slot_table_present(self):
        before, _, after = split_block(V2.read_text())
        outside = before + after
        table = "\n".join(l for l in outside.splitlines() if l.startswith("|"))
        for name in SLOTS:
            self.assertEqual(table.count("{%s}" % name), 1, name)
            self.assertEqual(outside.count("{%s}" % name), 1, name)


if __name__ == "__main__":
    unittest.main()
