"""The hook is a format (2026-09-25): every version keeps the source's opening word for word except its blanks."""
import json, tempfile
from pathlib import Path
import hook_format as h

d = Path(tempfile.mkdtemp())
(d / "transcript.json").write_text(json.dumps([{"id": "T1", "text": "I'm at the corner bakery, which is crazy because I'm going to ask them about my knees."}]))
fmt = "FORMAT LINE: I'm at [PLACE], which is crazy because I'm going to ask them about [PROBLEM].\nELEMENTS:\n- [PLACE] · a place · holds [EXPERT] · research\n- [PROBLEM] · the problem · = what the body treats · bank\n- [AGE] · her age · = [SUBJECT] in the cast · cast\n- [REFUSAL] · a refusal · offered in the body · bank\n\n"
good = "".join(f"LINE V{v}: I'm at the {p}, which is crazy because I'm going to ask them about my {q}.\n"
               for v, (p, q) in enumerate([("gym", "knees"), ("pool", "hips"), ("park", "back"), ("track", "ankles"), ("court", "wrists"), ("field", "neck")]))
_, f = h.check(d, fmt + good)
assert f == [], f
bad = good.replace("LINE V3: I'm at the track, which is crazy because", "LINE V3: I've tried everything, because")
_, f = h.check(d, fmt + bad)
assert [x["n"] for x in f] == ["H3"], f
# a format that paraphrases the source's own words is caught
_, f = h.check(d, "ELEMENTS:\n- [PLACE] · x\n- [PROBLEM] · x\n\nFORMAT LINE: I'm at [PLACE], which is wild since I came to see about [PROBLEM].\n" + good)
assert "HF" in [x["n"] for x in f], f
# no format printed at all
_, f = h.check(d, good)
assert f and f[0]["n"] == "H", f
print("OK")
# a blank that swallows the source's own words is caught ("SELLING MY HOME" → "[REFUSAL]")
(d / "stages").mkdir(exist_ok=True)
(d / "stages" / "1-teardown.md").write_text("* Hook text: 3 AGENTS. 3 DIFFERENT PRICES. I'M 68 AND STILL NOT SELLING MY HOME. | look: bold\n")
card = "FORMAT CARD: 3 AGENTS. / 3 DIFFERENT PRICES. / I'M [AGE] AND STILL NOT [REFUSAL].\nCARD V0: 3 AGENTS. / 3 DIFFERENT PRICES. / I'M 64 AND STILL NOT RENTING MY HOME.\n"
_, f = h.check(d, fmt + good + card)
assert [x["n"] for x in f] == ["CF"], f
_, f = h.check(d, fmt + good + card.replace("[REFUSAL].", "[REFUSAL] MY HOME."))
assert f == [], f
print("OK — card")
nb, notes = h.repair(d, fmt + good + card)
assert notes and h.check(d, nb)[1] == [], (notes, h.check(d, nb)[1])
print("OK — repair")
