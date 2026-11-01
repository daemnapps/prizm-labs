#!/usr/bin/env python3
"""ad-handoff — the gate refuses what it should, and passes what it should.

    python3 components/ad-handoff/tests/test_ad_handoff.py

Offline: no network, no Drive, no model. Every case below is one of the
seven checks, built as the smallest folder that triggers it.
"""
import csv, json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import handoff as H

AD = "acme-thing-static-ai-none-buyer-problem-angle-concept-format-p001-9x16-260101a"
LINK_OK = "https://example.com/ok/"


def build(tmp, ads=((AD, 2),), copy=True, doc_link=True, links=None, blank_copy=False):
    d = Path(tmp)
    for name, n in ads:
        f = d / name
        f.mkdir(parents=True)
        for i in range(1, n + 1):
            (f / f"{name}-a{i:02d}.png").write_bytes(b"\x89PNG fake")
    if copy:
        with (d / "copy.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["brief", "ad_name", "primary_text"])
            for name, _ in ads:
                w.writerow(["p001", name, "" if blank_copy else "Some primary text."])
    page = "# handoff\n\nEverything is here.\n"
    if doc_link:
        page += "\n### https://drive.google.com/drive/folders/FAKEID\n"
    (d / "HANDOFF.md").write_text(page)
    if links is not None:
        (d / "links.json").write_text(json.dumps(links))
    return d


def problems(d, **kw):
    kw.setdefault("online", False)
    p, _, _ = H.run_checks(d, "acme", "260101a", None, **kw)
    return p


class TestGate(unittest.TestCase):
    def test_a_complete_drop_passes(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(problems(build(t)), [])

    def test_an_empty_ad_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p = problems(build(t, ads=((AD, 0),)))
            self.assertTrue(any("no picture" in x for x in p), p)

    def test_a_missing_copy_file_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p = problems(build(t, copy=False))
            self.assertTrue(any("no copy.csv" in x for x in p), p)

    def test_an_ad_with_no_copy_row_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            d = build(t)
            (d / (AD.replace("p001", "p002"))).mkdir()
            (d / AD.replace("p001", "p002") / "x-a01.png").write_bytes(b"x")
            p = problems(d)
            self.assertTrue(any("no copy row" in x for x in p), p)

    def test_a_copy_row_for_an_absent_ad_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            d = build(t)
            with (d / "copy.csv").open("a", newline="") as fh:
                csv.writer(fh).writerow(["p999", "acme-ghost-ad", "words"])
            p = problems(d)
            self.assertTrue(any("no pictures here" in x for x in p), p)

    def test_an_empty_primary_text_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p = problems(build(t, blank_copy=True))
            self.assertTrue(any("empty primary text" in x for x in p), p)

    def test_a_page_without_its_own_link_is_refused(self):
        """The failure that started this component (2026-09-24)."""
        with tempfile.TemporaryDirectory() as t:
            p = problems(build(t, doc_link=False))
            self.assertTrue(any("does not carry the Drive link" in x for x in p), p)

    def test_a_missing_page_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            d = build(t)
            (d / "HANDOFF.md").unlink()
            p = problems(d)
            self.assertTrue(any("no HANDOFF.md" in x for x in p), p)

    def test_links_are_read_from_links_json(self):
        with tempfile.TemporaryDirectory() as t:
            d = build(t, links={"Offer page": LINK_OK})
            self.assertEqual(H.links(d), {"Offer page": LINK_OK})

    def test_links_fall_back_to_the_page_table(self):
        with tempfile.TemporaryDirectory() as t:
            d = build(t)
            (d / "HANDOFF.md").write_text(
                "### https://drive.google.com/drive/folders/FAKEID\n\n"
                "| Destination | Link |\n|---|---|\n"
                f"| **Offer page** — the money page | `{LINK_OK}` |\n")
            self.assertEqual(H.links(d), {"Offer page": LINK_OK})

    def test_the_repo_root_is_found_by_walking_up(self):
        self.assertTrue((H.WS / "components").is_dir())
        self.assertTrue((H.WS / "brands").is_dir())


if __name__ == "__main__":
    unittest.main(verbosity=2)
