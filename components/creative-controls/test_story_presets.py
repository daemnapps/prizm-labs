"""Story presets: the bank is complete, brand-free and current, and its reader picks, renders and checks.
No model, no network.

    /usr/bin/python3 components/creative-controls/test_story_presets.py
"""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import story_presets as SP  # noqa: E402

DOC = SP.load()
OUR_BRANDS = [p.name for p in (SP.WS / "brands").iterdir() if p.is_dir()] if (SP.WS / "brands").is_dir() else []


class Bank(unittest.TestCase):
    def test_every_card_is_banked_once(self):
        cards = [f.stem for f in SP.CATALOG.glob("*.md") if not f.name.startswith("_")]
        self.assertEqual(len(cards), 47)
        self.assertEqual(sorted(cards), sorted(SP.ids()))

    def test_status_words_are_the_ruled_set(self):
        for shelf in ("presets", "shots", "formats", "looks"):
            for row in DOC[shelf]:
                self.assertIn(row["status"], ("draft", "approved", "deprecated"), (shelf, row["id"]))

    def test_the_manifest_is_current_with_its_captures(self):
        self.assertTrue(SP.build(check=True), "story_presets.json is stale: run story_presets.py build")

    def test_story_cards_carry_their_shape(self):
        for p in DOC["presets"]:
            self.assertTrue(p["source"].startswith(SP.CATALOG_REL), p["id"])
            if p["hf_style"] == "singing":
                continue
            self.assertGreaterEqual(len(p["beats"]), 5, p["id"])
            self.assertEqual(p["beats"][0]["from_pct"], 0, p["id"])
            self.assertEqual(p["beats"][-1]["to_pct"], 100, p["id"])
            for a, b in zip(p["beats"], p["beats"][1:]):
                self.assertEqual(a["to_pct"], b["from_pct"], "%s: beats must join" % p["id"])
            self.assertIsNotNone(p["product"]["enters_pct"], p["id"])
            self.assertTrue(p["cast"] and p["tone"] and p["seconds"], p["id"])
            self.assertIn(p["length"], ("short", "long"))

    def test_every_arc_and_device_exists_in_the_story_layer(self):
        c = json.loads((HERE / "controls.json").read_text())
        arcs, devs = {a["id"] for a in c["arcs"]}, {d["id"] for d in c["story_devices"]}
        for p in DOC["presets"]:
            if p["hf_style"] != "singing":
                self.assertIn(p["arc"], arcs, p["id"])
            for d in p["devices"]:
                self.assertIn(d, devs, p["id"])

    def test_format_links_use_only_locked_names(self):
        n = SP._names()
        for p in DOC["presets"]:
            f = p["format"]
            for k in ("production_format", "script_format", "style"):
                if f.get(k):
                    self.assertIn(f[k], n[k], (p["id"], k))
        for f in DOC["formats"]:
            for k in ("production_format", "script_format"):
                if f["ours"][k]:
                    self.assertIn(f["ours"][k], n[k], f["id"])

    def test_the_other_shelves_are_all_there(self):
        self.assertEqual(len(DOC["shots"]), 80)
        self.assertEqual({s["family"] for s in DOC["shots"]}, {"still", "product-motion", "person-effect"})
        self.assertGreaterEqual(len(DOC["formats"]), 30)
        self.assertTrue(any(f["state"] == "gap" for f in DOC["formats"]))
        self.assertGreaterEqual(len(DOC["looks"]), 100)
        self.assertEqual(len({l["id"] for l in DOC["looks"]}), len(DOC["looks"]), "a look is banked once")
        self.assertTrue(all(g["state"] in ("counted-not-captured", "widget-only") for g in DOC["galleries"]))

    def test_the_rendered_block_names_none_of_our_brands(self):
        for p in DOC["presets"]:
            text = SP.block(p).lower()
            for b in OUR_BRANDS:
                self.assertNotRegex(text, r"\b%s\b" % re.escape(b.lower()), (p["id"], b))


class Reader(unittest.TestCase):
    def test_block_times_beats_at_the_preset_length(self):
        t = SP.block(SP.get("shrink-the-creature"))
        self.assertIn("| 49–72% | 0:22–0:32 |", t)
        self.assertIn("Enters at 49% (0:22)", t)
        self.assertIn("hook-3s", t)
        self.assertIn("## END OF THE STORY PRESET", t)

    def test_block_rescales_to_another_length(self):
        self.assertIn("| 49–72% | 0:15–0:22 |", SP.block(SP.get("shrink-the-creature"), seconds=30))

    def test_pick_filters_by_format_and_skips_song_cards(self):
        got = SP.pick(script_format="micro-drama")
        self.assertTrue(got)
        self.assertTrue(all(p["format"]["script_format"] == "micro-drama" for p, _ in got))
        self.assertFalse(any(p["hf_style"] == "singing" for p, _ in SP.pick()))

    def test_pick_rotates_away_from_presets_already_used(self):
        first = SP.pick(script_format="personal-story", awareness="problem-aware", length="short")[0][0]["id"]
        again = SP.pick(script_format="personal-story", awareness="problem-aware", length="short",
                        used=[first])[0][0]["id"]
        self.assertNotEqual(first, again)

    def test_unknown_preset_is_refused(self):
        with self.assertRaises(KeyError):
            SP.get("no-such-preset")

    def test_check_brief_notes_a_missing_product_and_an_empty_ending(self):
        p = SP.get("shrink-the-creature")
        brief = {"scenes": [{"start": 0, "happens": "the creature fills the bathroom"},
                            {"start": 30, "happens": "the narrator sits"}, {"start": 40}]}
        notes = SP.check_brief(brief, p)
        self.assertTrue(any(n.startswith("product entry") for n in notes))
        self.assertTrue(any(n.startswith("ending") for n in notes))

    def test_check_brief_passes_a_brief_on_its_shape(self):
        p = SP.get("shrink-the-creature")
        brief = {"piece": {"seconds": 45},
                 "scenes": [{"start": 0, "happens": "the creature knocks the mirror off the wall"},
                            {"start": 22, "happens": "the product on the counter", "product": True},
                            {"start": 40, "happens": "he steps out the door", "action": "steps out"}]}
        self.assertEqual(SP.check_brief(brief, p), [])


if __name__ == "__main__":
    unittest.main()
