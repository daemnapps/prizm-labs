"""Reusable 3D scene types for product stills: one fixed print prompt per scene type, only the words change.

The sets themselves are built by product_sets_blender.py inside the 3D Jutsu project. SCENES holds the values each ad
passes to it; print_words() gives the print step's words. Add a new ad by adding a row, never a new set by hand.
"""
import re
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parents[2] / "runs" / "image-teardown"

PRODUCT = ("The product is exactly as the reference shows it: the NOVA face brush, a matte black egg-shaped body with a soft "
           "silicone bristle face, a thin white ring above its rounded glossy base, 11.15 cm long, 6.98 cm wide and only 3.35 cm "
           "thick. It is flat, thin and slim like the SIDE photo, never bulbous or puffed. "
           "In the blockout the product is a plain placeholder: its straight white stripe and big black base are not the real product. "
           "Take every detail from the sheet instead: the white ring is a curved arc that dips at both ends, the base below it is a shallow "
           "cap, and the band above the ring carries the minus, power and plus marks exactly as on the FRONT photo.")
FLAT = (" Seen straight-on and flat, exactly like the FRONT photo, no side wall or back showing, turned only slightly in its own plane.")
HEAD = ("Two inputs: the first is a clean 3D blockout of {shot}; the second is the product's casting sheet of real studio photographs, which "
        "supplies its shape, materials and every detail. Keep the blockout's camera, layout, framing, sizes, depth and light exactly; nothing of "
        "its grey materials carries over. Each grey egg in the blockout is one NOVA, its grey zone the bristle face.")
TAIL = "A real, unretouched photograph, natural grain. No people, no hands. No writing anywhere except {allowed}."

PROMPTS = {
    "tabletop-notes": HEAD.format(shot="an overhead photo of a surface") + " " + PRODUCT + FLAT + " {concept} {dress} "
        "Each sticky note is handwritten in thick black marker, big and casual, spelled exactly letter for letter: top note "
        "\"{top}\", middle note \"{middle}\", bottom note \"{bottom}\". " + TAIL.format(allowed="the words on the three notes and the product's own marks"),
    "tabletop-ground": HEAD.format(shot="a high-angle studio product shot on a colour ground") + " " + PRODUCT + " {concept} {dress} "
        "The middle of the frame stays completely empty for type added later. " + TAIL.format(allowed="the product's own marks"),
    "float-ribbon": HEAD.format(shot="a level studio shot of a product floating in front of a flat backdrop") + " " + PRODUCT + FLAT
        + " The product floats in the air, touching nothing. {concept} {dress} The yellow band is one translucent gold satin ribbon "
        "wrapping around the product, in front of it and behind it, carrying printed ink letters spelled exactly letter for "
        "letter: on the run in front \"{front}\", on the run behind \"{back}\". The lower part of the frame stays clear for type "
        "added later. " + TAIL.format(allowed="the words on the ribbon and the product's own marks"),
}


def concept_of(run):
    """The brief's concept and dial levels, read from its brand step, so the picture gets what the writing asked for."""
    t = (RUNS / run.split("-batch-")[0] / run / "out" / "03-injection.md").read_text()
    concept = re.search(r"\*\*THE CONCEPT:\*\*\s*(.+)", t).group(1).strip()
    dials = [f"{k} {n} ({w})" for k in ("absurdity", "humor", "dressing")
             for n, w in re.findall(rf"`{k}:[^`]*?ours (\d) \(([^)]+)\)", t)[:1]]
    return f"The concept of this picture: {concept} Push the scene to these creative levels: {', '.join(dials)}."


SCENES = {
    "brand-a-batch-bf-flex-12": {
        "prompt": "tabletop-notes",
        "dress": "The surface is a coach's bone-white whiteboard draft desk with hand-drawn chalk-marker court lines, Xs, Os and play arrows "
                 "running from each note to its NOVA, as if the desk is drafting a face brush with every pick. The grey discs are a steel "
                 "stopwatch and a coach's whistle on a cord, the long dark bar a marker pen, the small discs round magnets. Soft window light from the upper left.",
        "words": {"top": "Black Friday DRAFT PICKS", "middle": "NOVA starting at $46", "bottom": "90-day money-back guarantee"},
        "set": {"name": "bf_notes2", "kind": "tabletop", "frame_w_cm": 27, "ground": "#EEE7D7",
                "notes": [{"x": .27, "y": .22, "w": .40, "h": .21, "spin": -2, "color": "#F0D860"},
                          {"x": .27, "y": .50, "w": .40, "h": .21, "spin": 1.5, "color": "#F0D860"},
                          {"x": .28, "y": .78, "w": .40, "h": .21, "spin": -1, "color": "#F0D860"}],
                "products": [{"x": .72, "y": .22, "spin": 5}, {"x": .73, "y": .50, "spin": -6}, {"x": .72, "y": .78, "spin": 4}],
                "props": [{"shape": "disc", "x": .90, "y": .055, "w": .10, "color": "#B9B9B9"}, {"shape": "disc", "x": .10, "y": .06, "w": .075, "color": "#8A8A8A"},
                          {"shape": "box", "x": .30, "y": .955, "w": .30, "h": .022, "color": "#1A1A1A", "spin": 3},
                          {"shape": "disc", "x": .50, "y": .36, "w": .04, "color": "#1A1A1A"}, {"shape": "disc", "x": .50, "y": .64, "w": .04, "color": "#F0D860"}]}},
    "brand-a-batch-bf-flex-06": {
        "prompt": "tabletop-ground",
        "dress": "The ground is a glossy warm gold draft-night stage floor under sports-announcement spotlights, one bright pool on the product, "
                 "a thin painted court line running under it. Ink and deep-gold confetti falls only in the top band and along the bottom edge. One gentle shadow under the product.",
        "words": {},
        "set": {"name": "bf_ground2", "kind": "tabletop", "view": "three_quarter", "frame_w_cm": 17, "ground": "#F0D860", "tilt": 22, "lens": 50,
                "products": [{"x": .5, "y": .76, "spin": -68, "roll": 12}],
                "bits": {"count": 22, "colors": ["#1A1A1A", "#908448"], "clear": [[.13, .60]]}}},
    "brand-a-batch-bf-flex-13": {
        "prompt": "float-ribbon",
        "dress": "A miniature arena in a studio: the backdrop is bone-white pebbled basketball leather, flat and even, with two narrow spotlight beams "
                 "crossing on the product. The orange ring at upper right is a tiny regulation basketball hoop with a white net, the dark panel at "
                 "upper left a tiny blank arena scoreboard with lit dots and no numbers. The flecks are tiny ink and gold confetti.",
        "words": {"front": "NOVA starting at $46", "back": "Black Friday"},
        "set": {"name": "bf_float2", "kind": "float_hero", "frame_w_cm": 14, "backdrop": "#EEE7D7", "x": .5, "y": .37, "tilt": 7, "sun": [15, -10, 0],
                "ribbon": {"radius_cm": 7.5, "width_cm": 1.9, "tilt": 14, "color": "#F0D860"},
                "props": [{"shape": "ring", "x": .84, "y": .10, "w": .17, "color": "#C8622A"}, {"shape": "box", "x": .16, "y": .09, "w": .24, "h": .13, "color": "#1A1A1A"}],
                "bits": {"count": 30, "colors": ["#1A1A1A", "#F0D860"], "clear": [[.60, 1]]}}},
}


def print_words(run):
    s = SCENES[run]
    return PROMPTS[s["prompt"]].format(concept=concept_of(run), dress=s["dress"], **s["words"])


if __name__ == "__main__":
    print(print_words(sys.argv[1]))
