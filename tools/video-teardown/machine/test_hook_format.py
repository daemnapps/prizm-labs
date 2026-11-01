"""The hook is a format (2026-09-25) for the CONTROL; every variation is its own take (2026-10-09)."""
import json, tempfile
from pathlib import Path
import hook_format as h

d = Path(tempfile.mkdtemp())
(d / "transcript.json").write_text(json.dumps([{"id": "T1", "text": "I'm at the corner bakery, which is crazy because I'm going to ask them about my knees."}]))
fmt = "FORMAT LINE: I'm at [PLACE], which is crazy because I'm going to ask them about [PROBLEM].\nELEMENTS:\n- [PLACE] · a place · holds [EXPERT] · research\n- [PROBLEM] · the problem · = what the body treats · bank\n- [AGE] · her age · = [SUBJECT] in the cast · cast\n- [REFUSAL] · a refusal · offered in the body · bank\n\n"
v0 = ("LINE V0: I'm at the gym, which is crazy because I'm going to ask them about my knees.\n"
      "SCROLL V0: wide, static: she walks into the gym towards the front desk\n")
TAKES = [("the doctor who laughed", "My doctor laughed when I told him what fixed it.", "HE LAUGHED", "a doctor's office, her rolling up a trouser leg mid-sentence", "her face mid-laugh, words: HE LAUGHED"),
         ("stairs at the station", "Forty-two stairs. I counted them every morning for a year.", "42 STAIRS", "a stairwell from above, her hand gripping the rail", "the stairwell from above, words: 42 STAIRS"),
         ("grandkid on the floor", "My grandson asked why I never sit on the floor with him.", "WHY GRANDMA?", "a toddler tugging her sleeve toward a rug of toys", "the toddler's hand on her sleeve, words: WHY GRANDMA?"),
         ("the drawer of braces", "There's a drawer in my kitchen just for knee braces.", "THE DRAWER", "a kitchen drawer sliding open, full of braces", "the open drawer, words: THE DRAWER"),
         ("dance at the wedding", "I sat out my own daughter's first dance.", "I SAT IT OUT", "a wedding dance floor, one empty chair at the edge", "the empty chair, words: I SAT IT OUT")]
good = "".join(f"TAKE V{v}: {t}\nLINE V{v}: {l}\nCARD V{v}: {c}\nSCROLL V{v}: {s}\nTHUMB V{v}: {th}\n"
               for v, (t, l, c, s, th) in enumerate(TAKES, 1))
_, f = h.check(d, fmt + v0 + good)
assert f == [], f
# the control is still locked to the swipe's format
_, f = h.check(d, fmt + v0.replace("I'm at the gym, which is crazy because", "I've tried everything, because") + good)
assert [x["n"] for x in f] == ["H0"], f
# the old set — one sentence, one word swapped — is held: not five takes
swaps = "".join(f"TAKE V{v}: {p}\nLINE V{v}: I'm at the {p}, which is crazy because I'm going to ask them about my {q}.\n"
                f"CARD V{v}: none\nSCROLL V{v}: wide, static: she walks into the {p} towards the front desk\nTHUMB V{v}: the {p}\n"
                for v, (p, q) in enumerate([("pool", "hips"), ("park", "back"), ("track", "ankles"), ("court", "wrists"), ("field", "neck")], 1))
_, f = h.check(d, fmt + v0 + swaps)
ns = {x["n"] for x in f}
assert {"L1", "L2", "S1", "C1"} <= ns, sorted(ns)
# a variation missing its thumbnail is held
_, f = h.check(d, fmt + v0 + good.replace("THUMB V3:", "NOTE V3:"))
assert [x["n"] for x in f] == ["T3"], f
# a format that paraphrases the source's own words is caught
_, f = h.check(d, "ELEMENTS:\n- [PLACE] · x\n- [PROBLEM] · x\n\nFORMAT LINE: I'm at [PLACE], which is wild since I came to see about [PROBLEM].\n" + v0 + good)
assert "HF" in [x["n"] for x in f], f
# no format printed at all
_, f = h.check(d, v0 + good)
assert f and f[0]["n"] == "H", f
print("OK")
# the run's start point moves the source opening (2026-10-09, --open-at)
(d / "transcript.json").write_text(json.dumps([{"id": "T1", "text": "Welcome everyone, settle in."},
                                               {"id": "T2", "text": "I'm at the corner bakery, which is crazy because I'm going to ask them about my knees."}]))
(d / "run.json").write_text(json.dumps({"opening_at": "I'm at the corner bakery, which is crazy"}))
_, f = h.check(d, fmt + v0 + good)
assert f == [], f
(d / "run.json").unlink()
(d / "transcript.json").write_text(json.dumps([{"id": "T1", "text": "I'm at the corner bakery, which is crazy because I'm going to ask them about my knees."}]))
print("OK — start point")
# a blank that swallows the source's own words is caught ("SELLING MY HOME" → "[REFUSAL]")
(d / "stages").mkdir(exist_ok=True)
(d / "stages" / "1-teardown.md").write_text("* Hook text: 3 AGENTS. 3 DIFFERENT PRICES. I'M 68 AND STILL NOT SELLING MY HOME. | look: bold\n")
card = "FORMAT CARD: 3 AGENTS. / 3 DIFFERENT PRICES. / I'M [AGE] AND STILL NOT [REFUSAL].\nCARD V0: 3 AGENTS. / 3 DIFFERENT PRICES. / I'M 64 AND STILL NOT RENTING MY HOME.\n"
_, f = h.check(d, fmt + v0 + good + card)
assert [x["n"] for x in f] == ["CF"], f
_, f = h.check(d, fmt + v0 + good + card.replace("[REFUSAL].", "[REFUSAL] MY HOME."))
assert f == [], f
print("OK — card")
nb, notes = h.repair(d, fmt + v0 + good + card)
assert notes and h.check(d, nb)[1] == [], (notes, h.check(d, nb)[1])
print("OK — repair")
# A WORDLESS OPENING (2026-10-09, the owner: "if something doesn't have a written hook or a voice hook … that's fine.
# It's just that you still should be making scroll stoppers"). Music, a "Hmm.", a line the speech model barely
# heard: no LINE to lock, `none` is the swipe — but every version still needs its own scroll stopper.
w = Path(tempfile.mkdtemp())
(w / "transcript.json").write_text(json.dumps([
    {"id": "T1", "start": 0.4, "text": "In any case, yeah, all our rights are offered.", "flags": ["heard-differently"], "scribe_heard": "case? offered."},
    {"id": "T2", "start": 2.6, "text": "Hmm.", "flags": []}, {"id": "T3", "start": 3.1, "text": "[sighs]", "flags": []}]))
assert h.opening(w) == {"spoken": False, "card": False}, h.opening(w)
SC = ["she snaps her own cheek in the queue, the camera roll fills with the same spot",
      "she steps from a pillar's shadow into window light and the spots sharpen",
      "the scanner's blue light sweeps her face, red boxes snap onto three spots",
      "a toddler in the queue points at her cheek, she pulls her hair across it",
      "the officer lifts a magnifying glass, the lens fills the frame with her temple"]
TH = ["camera roll grid of one cheek", "half her face in shadow", "blue scanner light, red boxes", "small pointing finger", "giant lens on a temple"]
quiet = ("FORMAT LINE: none — the opening is wordless\nLINE V0: none\nCARD V0: none\nSCROLL V0: she hands her passport across the counter\n"
         + "".join(f"TAKE V{v}: take {v}\nLINE V{v}: None. Heard: soft music\nCARD V{v}: none\nSCROLL V{v}: {s}\nTHUMB V{v}: {TH[v-1]}\n"
                   for v, s in enumerate(SC, 1)))
_, f = h.check(w, quiet)
assert f == [], f
# …and five copies of one scroll stopper are still held
_, f = h.check(w, quiet.replace(SC[1], SC[0]).replace(SC[2], SC[0]))
assert {"S2", "S3"} <= {x["n"] for x in f}, f
# a spoken opening is untouched by any of this
assert h.opening(d)["spoken"] is True
print("OK — wordless opening")
