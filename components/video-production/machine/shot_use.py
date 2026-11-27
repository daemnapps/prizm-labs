"""THE PRODUCT'S USE, TRANSLATED — one shot's action, from the swipe's to ours (2026-11-10).

The shot swaps already turn the swipe's product into ours (`shot_swaps.py`: "a product in the shot → the real product"),
but nothing turned what the swipe's person DOES with their product into what ours does with ours. A swipe that rubs
cream into a forearm came out as our face brush on a forearm, when the brush is used on the face and the words over the
shot are about the face. This step is that missing row: the swipe's action, the words over our shot and the product's
truth kit (how it is held, what it does in use, what it cannot do, what is never shown) go in; our action comes out,
with the body part it is on and whether the product needs to be in the shot at all.

    translate(swipe, our_line, kit, run=None, ask=None) -> {"our_does", "body_part", "product_in_shot", "kept",
                                                             "changed", "problems"}
    python3 shot_use.py --does "<swipe action>" --line "<our words>" --kit <kit folder> [--camera ..] [--text ..] [--shows ..]

The read is the house judge (v2_checks.ask). `problems` is measured in code, never asked: our words name a body part the
action is not on, or the product sits on a body part its kit never names. Brand-agnostic: every fact comes from the kit.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT = HERE.parent / "prompts" / "v2" / "shot-use-v1-owner.md"

# a body word → the body part it belongs to (the cheek is the face); used only to compare the words with the action
PARTS = {"face": "face", "cheek": "face", "cheeks": "face", "jaw": "face", "jawline": "face", "chin": "face",
         "forehead": "face", "nose": "face", "pores": "face", "beard": "face", "skin": "skin",
         "neck": "neck", "arm": "arm", "arms": "arm", "forearm": "arm", "forearms": "arm", "wrist": "arm",
         "hand": "hand", "hands": "hand", "palm": "hand", "palms": "hand", "leg": "leg", "legs": "leg",
         "scalp": "scalp", "hair": "hair", "lips": "lips", "chest": "chest", "body": "body"}


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_su_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    spec.loader.exec_module(mod)
    return mod


def parts_in(text: str) -> set:
    return {PARTS[w] for w in re.findall(r"[a-z]+", str(text or "").lower()) if w in PARTS}


def kit_facts(kit_dir) -> dict:
    """The kit's own words for what the product is and how it is really used."""
    k = json.loads((Path(kit_dir) / "kit.json").read_text())
    b = k.get("behaviour") or {}

    def words(x):
        return "; ".join(str(i) for i in x) if isinstance(x, list) else str(x or "")
    return {"what": words(k.get("what")), "held": words(b.get("held")), "in_use": words(b.get("in_use")),
            "cannot": words(b.get("cannot") or k.get("cannot")), "never_show": words(b.get("never_show"))}


def _without_product(text: str, facts: dict) -> str:
    """The action's words with the product's own name taken out (a "face brush" on an arm is not on the face)."""
    name = re.sub(r"^(the|a|an)\s+", "", str(facts.get("what") or "").strip().lower())
    text = str(text or "").lower()
    for w in filter(None, {name, " ".join(name.split()[-2:])}):
        text = text.replace(w, " ")
    return text


def check(out: dict, our_line: str, facts: dict) -> list:
    """What the code can see is wrong with a translated action (no model asked)."""
    problems = []
    said, did = parts_in(our_line) - {"skin", "body"}, parts_in(_without_product(out.get("our_does"), facts))
    if said and not (said & did):
        problems.append(f"our words are about the {', '.join(sorted(said))}; the action is on the "
                        f"{', '.join(sorted(did)) or 'no body part'}")
    used = parts_in(" ".join((facts.get("what") or "", facts.get("held") or "", facts.get("in_use") or ""))) - {"hand", "skin", "body"}
    if out.get("product_in_shot") and used and (did - {"hand", "skin", "body"}) - used:
        problems.append(f"the product is used on the {', '.join(sorted(used))}; the action puts it on the "
                        f"{', '.join(sorted((did - {'hand', 'skin', 'body'}) - used))}")
    return problems


def translate(swipe: dict, our_line: str, kit_dir, run=None, ask=None, shows: str = "") -> dict:
    facts = kit_facts(kit_dir)
    prompt = PROMPT.read_text().format(
        swipe_does=swipe.get("does") or "", swipe_camera=swipe.get("camera") or "", swipe_text=swipe.get("text") or "",
        our_line=our_line or "", shows=shows or "", **facts)
    if ask is None:
        V = _load("v2_checks")
        text, info = V.ask(Path(run) if run else None, "shot-use", prompt, [], model=V.model_of("house:behind.judge"))
        got = V.json_of(text) or {}
        by = info.get("model")
    else:
        got, by = ask(prompt), "given"
    out = {"our_does": str(got.get("our_does") or "").strip(), "body_part": str(got.get("body_part") or "").strip(),
           "product_in_shot": bool(got.get("product_in_shot")), "kept": str(got.get("kept") or "").strip(),
           "changed": str(got.get("changed") or "").strip(), "by": by, "prompt": PROMPT.name}
    if not out["our_does"]:
        raise ValueError("the read gave no action for our shot")
    out["problems"] = check(out, our_line, facts)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--does", required=True); ap.add_argument("--line", required=True); ap.add_argument("--kit", required=True)
    ap.add_argument("--camera", default=""); ap.add_argument("--text", default=""); ap.add_argument("--shows", default="")
    a = ap.parse_args(argv)
    out = translate({"does": a.does, "camera": a.camera, "text": a.text}, a.line, a.kit, shows=a.shows)
    print(json.dumps(out, indent=1))
    return 1 if out["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
