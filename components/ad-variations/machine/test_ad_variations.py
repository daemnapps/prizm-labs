"""python3 machine/test_ad_variations.py — no network, no model, no media."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import assemble  # noqa: E402
import corpus  # noqa: E402
import index as IX  # noqa: E402

COMP = HERE.parent
TEARDOWN = """**Sound form:** SPOKEN
**Music:** none

**CAST**

**Creator**
*   **Role:** lead

**PLACES**

**Home Bathroom**
*   **What it is:** Home bathroom

**PROPS**

*   **Item One:** a jar.

| Timestamp | Roll | Section | Visuals | On-Screen Text | Transcript | Sound | Layers |
|---|---|---|---|---|---|---|---|
| 0:00.0 - 0:02.0 | G · opener: true | hook | Camera: handheld selfie, phone-grade | none | Speaker 1: Hi | music: none / effects: none | platform: comment_reply: "a question" / transition out: none |
| 0:02.0 - 0:05.0 | B-silent | solution | Camera: propped, phone-grade | none | [silence] | music: none / effects: none | none |

**Layer sheet**
*   Hook text: none
*   Captions: none

**Sound sheet**
*   Music: none
"""


def fake_run(tmp):
    d = Path(tmp) / "brand-1"
    (d / "stages").mkdir(parents=True)
    (d / "stages/0-triage.md").write_text("LANE: ALREADY AN AD\nRUNTIME: 0:05\nSOUND FORM: SPOKEN\nAI ASSESSMENT: LIKELY HUMAN.\n")
    (d / "stages/1-teardown.md").write_text(TEARDOWN)
    (d / "stages/1b-audience.md").write_text("AVATAR: some-avatar\nFUNNEL: prospect\nTOPICS: a, b\n")
    (d / "stages/2-spec.md").write_text("### 1. FORMAT\nx")
    (d / "doctrine.json").write_text(json.dumps({"sections_carried": [{"id": "hook", "span": "0:00.0-0:02.0"},
                                                                       {"id": "call-to-action", "span": "0:04.5-0:05.0"}],
                                                  "awareness": {"entry": "problem-aware", "exit": "product-aware"}}))
    (d / "transcript.json").write_text(json.dumps([{"id": "T1", "start": 0.4, "text": "Hi"}]))
    return corpus.Run(d, {"views": 100, "saves": 5, "duration_s": 5})


class T(unittest.TestCase):
    def test_rules_read_the_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = fake_run(tmp)
            self.assertTrue(r.complete)
            self.assertEqual(corpus.rule("first_roll", r), "G")
            self.assertEqual(corpus.rule("hook_platform", r), "comment-reply + picture-in-picture")
            self.assertEqual(corpus.rule("cast_count", r), 1)
            self.assertEqual(corpus.rule("settings", r), ["bathroom"])
            self.assertEqual(corpus.rule("captions", r), "none")
            self.assertEqual(corpus.rule("hook_text", r), "none")
            self.assertEqual(corpus.rule("ask_position", r), "ask in last 15%")
            self.assertEqual(corpus.rule("silent_broll", r), 3.0)
            self.assertEqual(corpus.rule("camera_grade", r), "phone-grade")

    def test_every_rule_in_the_definitions_exists(self):
        for v in IX.definitions()["variables"]:
            kind, key = v["how"].split(":", 1)
            if kind == "rule":
                self.assertIn(key, corpus.RULES, v["id"])

    def test_element_list_points_at_real_variables(self):
        ids = {v["id"] for v in IX.definitions()["variables"]}
        els = json.loads((COMP / "definitions/elements.json").read_text())["elements"]
        self.assertEqual(len(els), 19)
        for e in els:
            for vid in e["variables"]:
                self.assertIn(vid, ids)

    def test_costs_are_units_times_rate(self):
        self.assertEqual(assemble.item_cost("gpt-image", 1)["usd"], 0.63)            # 0.21 × 3 rolls
        self.assertEqual(assemble.item_cost("seedance-hf", 7)["usd"], 3.18)          # 0.35 × 7 × 1.3 = 3.185
        self.assertEqual(assemble.item_cost("local-matte", 1)["usd"], 0)
        self.assertIsNone(assemble.item_cost("creator-reshoot", 1)["usd"])

    def test_shared_piece_costed_once_and_test_route(self):
        rec = [{"id": "V01", "make": [{"what": "clip", "route": "genjutsu-hf", "units": 3},
                                      {"what": "still of the man", "route": "gpt-image", "units": 1, "shared": "S1"}],
                "cheaper_test": {"replaces_route": "genjutsu-hf", "route": "wan-animate-fal", "units": 8}}]
        shared = [{"key": "S1", "piece": "still of the man", "route": "gpt-image", "units": 1, "used_by": ["V01"]}]
        out = assemble.cost_recipes(rec, shared)[0]
        self.assertEqual(out["cost"]["usd_own"], 8.58)
        self.assertEqual(out["cost"]["usd_standalone"], 9.21)
        self.assertEqual(out["cost"]["usd_with_test"], 1.25)

    def test_forced_gates_follow_routes(self):
        r = {"id": "V01", "make": [{"what": "the new man reacting", "route": "seedance-hf", "units": 7}]}
        f = assemble.forced_for(r, [])
        for g in ("identity", "smoothness", "safe-zones", "brand-rules"):
            self.assertIn(g, f)
        self.assertNotIn("lip-sync", f)

    def test_chained_clips_force_the_seams_gate(self):
        r = {"id": "V02", "make": [{"what": "morph part one", "route": "seedance-hf", "units": 4, "chain_order": 1},
                                   {"what": "morph part two", "route": "seedance-hf", "units": 4, "chain_order": 2}]}
        self.assertIn("seams", assemble.forced_for(r, []))
        one = {"id": "V03", "make": [{"what": "one clip", "route": "seedance-hf", "units": 4}]}
        self.assertNotIn("seams", assemble.forced_for(one, []))

    def test_every_prompt_field_is_supplied(self):
        src = (HERE / "run.py").read_text()
        from run_kit import prompts as P
        for key in ("stage1", "stage2", "stage3", "stage4", "stage5", "stage6", "stage7"):
            call = re.search(rf'chain\.run\("{key}",(.*?)\)\n', src, re.S).group(1)
            given = set(re.findall(r"(\w+)=", call)) | ({"metrics"} if "**common" in call else set())
            wanted = set(P.wanted(P.latest(COMP / "prompts", key).read_text()))
            self.assertLessEqual(wanted, given, key)

    def test_prompts_name_no_brand(self):
        brands = [p.name for p in (COMP.parent.parent / "brands").iterdir() if p.is_dir()]
        for f in (COMP / "prompts").rglob("*.md"):
            t = f.read_text().lower()
            for b in brands:
                self.assertNotIn(b.lower(), t, f"{f.name} names {b}")

    def test_extract_json_takes_the_fenced_block(self):
        self.assertEqual(IX.extract_json('noise\n```json\n{"a": 1}\n```\n'), {"a": 1})


if __name__ == "__main__":
    unittest.main(verbosity=1)
