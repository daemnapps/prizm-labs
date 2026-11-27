#!/usr/bin/env python3
"""feedback-forms — the docs page speaks for each panel's own brand
(feedback-forms#3): the empty kill list names the panel's brand, and the
end-to-end chips come from each brand's status, never a hard-coded name.
Fake brands only; nothing under runs/ is written.

    python3 components/feedback-forms/tests/test_tail_brand_words.py
"""
import importlib.util, re, sys, unittest
from pathlib import Path
from unittest import mock

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP))
import build as B  # noqa: E402

_spec = importlib.util.spec_from_file_location("make_page", COMP / "docs" / "make_page.py")
MP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MP)


def fake(brand, label, e2e):
    return dict(brand=brand, stages={"stages": [], "form": {"url": "https://example.test/f"}, "klaviyo": {"public_id": "PUB"}},
                questions={"label": label, "stages": [], "default_stage": ""}, kills=[], bank={}, cover={}, lp=None,
                status={"e2e": e2e}, runtime={"look": {}}, logo="", css=[])


class KillTable(unittest.TestCase):
    def test_empty_kill_list_names_the_panels_own_brand(self):
        out = MP.kill_table({"kills": [], "questions": {"label": "Zz Brand"}})
        self.assertIn("Zz Brand", out)
        for n in B.brands():
            self.assertNotIn(n.lower(), out.lower(), f"{n} named in the empty kill-list sentence")


class E2EChips(unittest.TestCase):
    def test_one_chip_per_brand_whose_e2e_ran(self):
        ds = [fake("aa-one", "Aa One", "Not run: no key"),
              fake("bb-two", "Bb Two", "One test response … landed")]
        with mock.patch.object(MP, "data", return_value=(ds, {})), \
                mock.patch.object(MP, "designer", return_value=([], "")):
            html = MP.page()
        chips = re.findall(r'<span class="chip ok">([^<]*) end-to-end test passed</span>', html)
        self.assertEqual(chips, ["Bb Two"])
        self.assertEqual(html.count("end-to-end test passed"), 1)

    def test_no_chip_when_no_brand_ran(self):
        ds = [fake("aa-one", "Aa One", "Not run: no key"), fake("bb-two", "Bb Two", "")]
        with mock.patch.object(MP, "data", return_value=(ds, {})), \
                mock.patch.object(MP, "designer", return_value=([], "")):
            html = MP.page()
        self.assertNotIn("end-to-end test passed", html)


if __name__ == "__main__":
    unittest.main()
