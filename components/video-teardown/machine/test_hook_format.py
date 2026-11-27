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
# Without an explicit template, sentence copies with nouns swapped are held.
swaps = "".join(f"TAKE V{v}: {p}\nLINE V{v}: I'm at the {p}, which is crazy because I'm going to ask them about my {q}.\n"
                f"CARD V{v}: none\nSCROLL V{v}: wide, static: she walks into the {p} towards the front desk\nTHUMB V{v}: the {p}\n"
                for v, (p, q) in enumerate([("pool", "hips"), ("park", "back"), ("track", "ankles"), ("court", "wrists"), ("field", "neck")], 1))
f = h.takes(v0 + swaps)
ns = {x["n"] for x in f}
assert {"L1", "L2", "S1", "C1"} <= ns, sorted(ns)
# With the explicit template, its filled nouns differ, so LINE findings clear.
# The same near-copy set is still held for repeated visual takes.
_, f = h.check(d, fmt + v0 + swaps)
ns = {x["n"] for x in f}
assert {"S1", "S2"} <= ns, sorted(ns)
assert not {"L1", "L2"} & ns, sorted(ns)
# The original explicit-template case still rejects the repeated visual take.
_, templated_copies = h.check(d, fmt + v0 + swaps)
assert "S1" in {finding["n"] for finding in templated_copies}, templated_copies
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
# A WORDLESS OPENING (2026-10-09, owner: "if something doesn't have a written hook or a voice hook … that's fine.
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

# Explicit fixed wording is excluded from LINE/CARD diversity comparisons.
verdicts = ["Back tf up.", "An actual jumpscare.", "Ik that hurt.",
            "That was a star crunch, sir.", "Why is it lowkey satisfying? Pass."]
templated = ("FORMAT LINE: Smash or pass? [VERDICT]\n"
             "FORMAT CARD: Smash or pass? / [VERDICT]\n"
             "LINE V0: Smash or pass? Ew, gross, pass. Hard pass.\n"
             "CARD V0: Smash or pass? / Ew, gross, pass. Hard pass.\n"
             + "".join(f"TAKE V{v}: {t}\nLINE V{v}: Smash or pass? {verdicts[v-1]}\n"
                       f"CARD V{v}: Smash or pass? / {verdicts[v-1]}\n"
                       f"SCROLL V{v}: {s}\nTHUMB V{v}: {th}\n"
                       for v, (t, _, _, s, th) in enumerate(TAKES, 1)))
assert h.takes(templated) == [], h.takes(templated)
duplicates = templated.replace(verdicts[1], verdicts[0])
assert {"L2", "C2"} <= {x["n"] for x in h.takes(duplicates)}, h.takes(duplicates)
visual_copies = templated.replace(TAKES[1][3], TAKES[0][3]).replace(TAKES[1][4], TAKES[0][4])
assert {"S2", "T2"} <= {x["n"] for x in h.takes(visual_copies)}, h.takes(visual_copies)
assert h.alike("Smash or pass? No.", "Smash or pass? No.", "Smash or pass? [VERDICT]")
assert h.alike("Smash or pass? Take it away gross.", "Smash or pass? Take it away.",
               "Smash or pass? [VERDICT]")
# A nonmatching template or a literal format retains the original comparison.
assert h.alike("Before you go, what do you think?", "Before you go, what do you think?",
               "Smash or pass? [VERDICT]")
assert h.alike("Smash or pass? Back.", "Smash or pass? Gross.",
               "Smash or pass?")
print("OK — templated variable diversity")

# A declared literal banner is required unchanged across variations.
banner = "TRIPLE DISCOUNT / DEAL ENDS SOON"
fixed_cards = (f"FORMAT CARD: {banner}\n" + v0
               + "".join(f"TAKE V{v}: {t}\nLINE V{v}: {l}\nCARD V{v}: {banner}\n"
                         f"SCROLL V{v}: {s}\nTHUMB V{v}: {th}\n"
                         for v, (t, l, _, s, th) in enumerate(TAKES, 1)))
assert h.takes(fixed_cards) == [], h.takes(fixed_cards)
missing_card = fixed_cards.replace(f"CARD V2: {banner}\n", "")
assert {"C2"} <= {x["n"] for x in h.takes(missing_card)}, h.takes(missing_card)
mismatched_card = fixed_cards.replace(f"CARD V2: {banner}\n", f"CARD V2: {banner} TODAY\n")
assert {"C2"} <= {x["n"] for x in h.takes(mismatched_card)}, h.takes(mismatched_card)
for format_value in ("none", "A DIFFERENT BANNER", "TRIPLE DISCOUNT / [DETAIL]"):
    body = fixed_cards.replace(f"FORMAT CARD: {banner}\n", f"FORMAT CARD: {format_value}\n")
    assert {"C2"} <= {x["n"] for x in h.takes(body)}, (format_value, h.takes(body))
repeated_visuals = fixed_cards.replace(TAKES[1][3], TAKES[0][3]).replace(TAKES[1][4], TAKES[0][4])
assert {"S2", "T2"} <= {x["n"] for x in h.takes(repeated_visuals)}, h.takes(repeated_visuals)
print("OK — required literal banners")

# Spoken cardless sources permit explicit none, while every slot stays printed.
cardless_run = Path(tempfile.mkdtemp())
(cardless_run / "transcript.json").write_text(json.dumps([
    {"id": "T1", "text": "I'm at the corner bakery, which is crazy because I'm going to ask them about my knees."}]))
cardless = (fmt + v0
            + "".join(f"TAKE V{v}: {t}\nLINE V{v}: {l}\nCARD V{v}: none\n"
                      f"SCROLL V{v}: {s}\nTHUMB V{v}: {th}\n"
                      for v, (t, l, _, s, th) in enumerate(TAKES, 1)))
assert h.check(cardless_run, cardless)[1] == [], h.check(cardless_run, cardless)[1]
missing = h.check(cardless_run, cardless.replace("CARD V3: none\n", ""))[1]
assert [x["n"] for x in missing] == ["C3"], missing
# A source with a separate text card still requires cards in every variation.
(cardless_run / "stages").mkdir()
(cardless_run / "stages" / "1-teardown.md").write_text("* Hook text: A REQUIRED CARD | look: bold\n")
required = h.check(cardless_run, cardless)[1]
assert {f"C{v}" for v in range(1, 6)} <= {x["n"] for x in required}, required
print("OK — spoken cardless opening")
