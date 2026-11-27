#!/usr/bin/env python3
"""frame_look.py — every shot looked at, frame by frame, before it is used (owner ruling 2026-11-16: editing is
frame by frame by default). One home for every editing path: the Video Studio's swipe cut and any chain step that
picks a clip for a shot read the look from here.

THE RULE: four frames across the stretch a shot will play go, side by side, to the team's vision judge
(vision_judge.ask). The shot is clean when
  - the product is in view and being used or held up, in most frames      (product_in_use; only a shot about the product)
  - no text is laid over the video (a label on a bottle is not text)       (text_on_screen)
  - no whip, smear, flash or cut between two pictures inside the shot      (blur_or_transition)
  - something happens: not a person standing still or an empty frame      (dead)
  - it reads as what the shot is meant to show                             (shows_it; a NOTE, never a miss: the swipe is
                                                                           the backbone, the shot is ours, owner 16 Nov)
A miss swaps to the next-best clip whose frames pass (`swap_for_look`); the first pick stays when none does, with
the reason on the shot. A judge that cannot answer is said, never counted as a miss. Answers are cached per clip,
start, length, shot and LOOK_V, so a change to the words below looks at every shot again.
MOMENTS FIRST: a stretch the asset index's moments pass already judged (components/asset-index/library/moments.py,
the same questions asked once per clip) is answered from there by `looked`; only a stretch with no moment is looked
at live.

    python3 frame_look.py <clip> <start> <seconds> "<what the shot shows>" [--product NAME] [--seen "how it looks"]

Brand-agnostic: the product's name and look come in from the brief (cfg).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

LOOK_V = "4"      # a change to the look's words looks at every shot again
LOOK = """Four frames, left to right, from ONE shot of a short ad for {product} ({product_seen}). The shot is meant to show:
{shows}

Look at every frame and answer JSON only:
{{"product_in_use": true | false (the {product_seen} is clearly in view and being used or held up, in most frames),
  "text_on_screen": true | false (text laid OVER the video: a caption, sticker, watermark, handle or app screen; print on
   things in the scene, such as a bottle label, packaging or a towel, is NOT text on screen),
  "blur_or_transition": true | false (a whip, smear, flash or cut between two different pictures inside these frames),
  "dead": true | false (nothing happens: a person standing still or an empty frame),
  "letterboxed": true | false (black bars above and below or at the sides: the picture does not fill the frame),
  "other_brand": true | false (another brand's product or packaging is in view: a jar, tube or box that is not {product}
   and not one of the brand's own products: {own}),
  "shows_it": true | false (it reads as what the shot is meant to show),
  "why": "one short line when anything above is wrong"}}"""
WANT = (("product_in_use", True), ("text_on_screen", False), ("blur_or_transition", False), ("dead", False),
        ("shows_it", True))
AT = (0.1, 0.37, 0.63, 0.9)      # where in the shot the four frames sit


def prompt(shows: str, cfg: dict | None = None) -> str:
    cfg = cfg or {}
    return LOOK.format(product=cfg.get("product") or "our product", product_seen=cfg.get("product_seen") or "the product",
                       shows=shows or "the product in use", own=", ".join(own_products(cfg)) or "none named")


def own_products(cfg: dict | None = None) -> list:
    """The brand's own products (brands/<brand>/footage-library.json own_products, or cfg["own_products"]): in our
    footage they are ours, never another brand's."""
    cfg = cfg or {}
    if cfg.get("own_products"):
        return list(cfg["own_products"])
    try:
        import json as _j
        p = Path(__file__).resolve().parents[3] / "brands" / str(cfg.get("brand") or "") / "footage-library.json"
        return list(_j.loads(p.read_text()).get("own_products") or [])
    except (OSError, ValueError):
        return []


def about_product(shows: str, cfg: dict | None = None) -> bool:
    """Is the shot about the product (its words name it, or the product's own words)? Only then must it be in view."""
    cfg = cfg or {}
    words = [w.lower() for x in (cfg.get("product_seen") or "", cfg.get("product") or "") for w in x.split() if len(w) > 3]
    return any(w in (shows or "").lower() for w in words + ["brush", "product", "device"])


def verdict(j: dict, shows: str = "", cfg: dict | None = None) -> tuple[bool, str]:
    """(clean, said) from the judge's answer. A clean picture always (no overlaid text, no blur or transition, not
    dead); the product in use only in a shot about the product; whether it repeats the swipe's exact move is a note."""
    j = j or {}
    # captioned footage is usable, marked (owner, 6 Nov 2026; again 20 Nov): on our own footage, text over the video
    # is a mark, never a refusal. A generated or composed picture still must be clean.
    footage = bool((cfg or {}).get("footage"))
    need = [w for w in WANT if w[0] in (("blur_or_transition", "dead") if footage else
                                        ("text_on_screen", "blur_or_transition", "dead"))]
    # never usable in our ad, whatever the shot (owner, 20 Nov 2026, on a real-footage cut: "so bad"): a letterboxed
    # clip, and another brand's product on screen
    need += [("letterboxed", False), ("other_brand", False)]
    if about_product(shows, cfg):
        need.append(("product_in_use", True))
    if (cfg or {}).get("shows_required"):        # a footage ad told by its words: the clip must show what is said
        need.append(("shows_it", True))
    bad = [k for k, want in need if k in j and bool(j[k]) != want]
    note = "" if j.get("shows_it", True) or (cfg or {}).get("shows_required") else " (differs from the swipe's move: noted)"
    if footage and j.get("text_on_screen"):
        note += " (captioned: marked)"
    return not bad, ("clean" + note if not bad else ", ".join(bad) + (": " + j.get("why", "") if j.get("why") else ""))


def key_of(path, start: float, need: float, shows: str) -> str:
    return hashlib.sha256(("%s|%.2f|%.2f|%s|%s" % (path, start, need, shows, LOOK_V)).encode()).hexdigest()[:16]


def strip(file, start: float, need: float, out) -> Path:
    """The four frames, side by side, in one picture (out)."""
    # one ffmpeg pass (owner, 17 Nov: fast): four evenly spaced frames of the stretch, tiled side by side
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % (start + need * AT[0]), "-t", "%.3f" % (need * (AT[-1] - AT[0]) + 0.05),
                    "-i", str(file), "-vf", "fps=%.4f,scale=-2:480,tile=%dx1" % (len(AT) / max(need * (AT[-1] - AT[0]), 0.1), len(AT)),
                    "-frames:v", "1", str(out)], check=True)
    return Path(out)


def _judge(q, pictures):
    if str(HERE) not in sys.path:          # the vision judge door reads its own neighbours from its folder
        sys.path.append(str(HERE))
    import vision_judge as VJ
    return VJ.json_of(str(VJ.ask(q, pictures, want_json=True)))


def look(path, start: float, need: float, shows: str, cfg: dict | None = None, cache_file=None, resolve=None,
         ask=None) -> tuple[bool, str]:
    """THE LOOK: (clean, said) for the `need` seconds of the clip from `start`. `path` names the clip (the cache key);
    resolve(path) gives the file to read (default: path itself); ask(prompt, [picture]) -> the judge's JSON (default:
    vision_judge). A look that cannot run is (True, "frame look not run: ..."): said, never a miss."""
    cache = {}
    if cache_file:
        Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
        try:
            cache = json.loads(Path(cache_file).read_text())
        except (OSError, ValueError):
            cache = {}
    k = key_of(path, start, need, shows)
    if k not in cache:
        try:
            f = resolve(path) if resolve else path
            with tempfile.TemporaryDirectory() as d:
                pic = strip(f, start, need, os.path.join(d, "strip.jpg"))
                j = (ask or _judge)(prompt(shows, cfg), [str(pic)])
        except Exception as e:  # noqa: BLE001 - not looked at here: said, never counted as a miss
            return True, "frame look not run: %s" % str(e)[:80]
        cache[k] = j
        if cache_file:
            Path(cache_file).write_text(json.dumps(cache, indent=1))
    return verdict(cache[k] or {}, shows, cfg)


def looked(brand: str, clip, start: float, need: float, shows: str, cfg: dict | None = None):
    """MOMENTS FIRST: the look the asset index's moments pass already took of this stretch (four frames, the same
    questions, asked once when the clip entered the index) -> (clean, said), or None when no judged moment covers it
    (look live). A shot about the product also needs the right product (the moment's product key)."""
    try:
        import importlib.util
        key = "chain_asset_index_moments"
        if key not in sys.modules:
            f = HERE.parents[1] / "asset-index" / "library" / "moments.py"
            if not f.is_file():
                return None
            spec = importlib.util.spec_from_file_location(key, f)
            m_ = importlib.util.module_from_spec(spec)
            sys.modules[key] = m_
            spec.loader.exec_module(m_)
        MO = sys.modules[key]
        m = MO.look_at(brand, clip, float(start), need) if brand else None
    except Exception:  # noqa: BLE001 - the index could not answer: look live
        return None
    if not m:
        return None
    j = dict(m.get("judge") or {})
    ok, said = verdict(j, shows, cfg)
    if ok and about_product(shows, cfg):
        want = MO.product_key((cfg or {}).get("product"), brand)
        if want and j.get("product") and str(j["product"]).lower() != want:
            ok, said = False, "product_in_use: another product (%s)" % j["product"]
    return ok, said + " (moments index, %s)" % m.get("id", "")


def swap_for_look(alternates, need: float, shows: str, fits, looks, used=()):
    """THE SWAP RULE: the next-best clip (the footage pass's order) that both plays the shot unbroken and passes the
    look. fits(path, start, need) -> start or None (shot_timing.busiest_in); looks(path, start, need, shows) ->
    (clean, said). Returns (alternate, start, said) or None."""
    for alt in alternates or []:
        if not alt.get("path") or alt["path"] in used:
            continue
        at = fits(alt["path"], alt.get("in") or 0, need)
        if at is None:
            continue
        ok, said = looks(alt["path"], at, need, shows)
        if ok:
            return alt, at, said
    return None


if __name__ == "__main__":
    a = [x for x in sys.argv[1:]]
    if len(a) < 4:
        sys.exit(__doc__)
    cfg = {}
    for flag, k in (("--product", "product"), ("--seen", "product_seen")):
        if flag in a:
            i = a.index(flag)
            cfg[k] = a[i + 1]
            del a[i:i + 2]
    ok, said = look(a[0], float(a[1]), float(a[2]), a[3], cfg)
    print(("clean" if ok else "miss") + ": " + said)
    sys.exit(0 if ok else 1)
