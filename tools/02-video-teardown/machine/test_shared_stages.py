#!/usr/bin/env python3
"""One change reaches every chain (Damon, 2026-09-28: "when I'm making updates,
they're affecting all the tools that are using them").

Every chain — New video (ALREADY AN AD, ORGANIC), Variation video, Framework —
must run the SAME prompt file for the same stage: the highest `-vN-` in that
stage's one home. A chain pinned to an old version, or pointing at a copy
outside the prompt folders, fails here.

    python3 test_shared_stages.py
"""
import re, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C  # noqa: E402

CHAINS = {"New video · already an ad": "ALREADY AN AD", "New video · organic": "ORGANIC",
          "Variation video": "VARIATION", "Framework": "FRAMEWORK"}
PROMPTS = (C.CM / "prompts").resolve()


def plan(lane, route="creator"):
    return {s["key"]: s for s in C.stages("", "", route, lane)}


class SharedStages(unittest.TestCase):
    def test_every_chain_runs_the_same_prompt_for_a_shared_stage(self):
        plans = {name: plan(lane) for name, lane in CHAINS.items()}
        keys = set().union(*[set(p) for p in plans.values()])
        for key in sorted(keys):
            files = {name: p[key]["prompt"] for name, p in plans.items() if key in p}
            self.assertEqual(len(set(files.values())), 1,
                             f"{key}: chains run different prompts — {files}")

    def test_every_prompt_is_the_newest_in_its_home(self):
        for name, lane in CHAINS.items():
            for key, s in plan(lane).items():
                if key == "stage5" or not s["prompt"]:
                    continue
                best, v, _ = C.newest(key)
                self.assertEqual(Path(s["prompt"]), best, f"{name} · {key} is not the newest prompt")

    def test_no_chain_runs_a_copy_outside_the_prompt_folders(self):
        for name, lane in CHAINS.items():
            for key, s in plan(lane).items():
                if not s["prompt"]:
                    continue
                p = Path(s["prompt"]).resolve()
                self.assertTrue(str(p).startswith(str(PROMPTS)) and "archive" not in p.parts
                                and "parked" not in p.parts,
                                f"{name} · {key} runs {p}, outside the one home")

    def test_the_usage_list(self):
        """Which chains call each stage — printed, so a change shows its reach."""
        plans = {name: plan(lane) for name, lane in CHAINS.items()}
        keys = sorted(set().union(*[set(p) for p in plans.values()]),
                      key=lambda k: (C.read_extra().get("order") or []).index(k)
                      if k in (C.read_extra().get("order") or []) else -1)
        print()
        for k in keys:
            who = [n for n, p in plans.items() if k in p]
            print(f"  {C.DISPLAY_ID.get(k, k.replace('stage', '')):<3} {k:<8} {', '.join(who)}")


if __name__ == "__main__":
    unittest.main(verbosity=1)
