"""Shot fill: the brief's shot list -> the best real clip for each shot from the asset index -> the gaps that go to AI.

  python3 shot_fill.py <production>        writes briefs/<production>/shot-fill.json and SHOT-FILL.md

For every shot a scene names it asks the asset index (components/asset-index/machine/search.py: local, deterministic,
usage rights checked) for owned footage that shows it, and keeps the best hit no earlier shot already took.
  - the production brief's shots (their action, picture and start_picture text), from the writing run's stage-5 brief
  - the brief's roll-sheet rows adapted to that scene (the swipe's continuity: what each beat showed)
  - the production's own shot list, `briefs/<production>/shot-list.json`, made by swipe_shots.py: one row per swipe
    shot each scene copies, with its length share of the scene; these rows are the ones a cut is built from
An ad whose style is not photoreal (the production's style, video-production styles/style_chain.py) takes no real
footage at all: every shot is a GAP made in the style. A shot of a face only takes footage of the ad's own person; hands-only shots only take hands that match the person;
product shots are open. A page, card or capture is made, not searched, and is listed as CAPTURE.
The GAP list (no hit at or above the bar, or none of the ad's person) is exactly what goes to AI (gen_ref.py).
MOMENTS FIRST (17 Nov): each REAL shot is placed on a clean moment of its clip from the asset index's moments
(components/asset-index/library/moments.py), its alternatives reordered the same way (`on_moments`).

Everything about the ad comes from the production's brief.json, key "shot_fill":
  {"brand", "person": path part of the ad's person's footage, "hands_like": [path parts whose hands match],
   "product": the product's name in the brief, "product_seen": how the index describes it,
   "library_roots": [folders a record's "folder"/"filename" sit under on this machine], "bar": 0.4}
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

BAR = 0.4            # a hit under this score does not show the shot
PER = 3000         # hits read per query (one per clip) before the person, hands and reuse filters
# words of the brief's slot language that say how a shot is made, not what it shows
BOILER = set("""cut slot named owned original actual recorded current cleared existing verified unaltered independent
native crop source geometry target measured asset job selected file subject bounds frame position follows take
construction same identity before use separate composited exact plain picture unchanged detail complete clause stays
here there treatment confirmed newly made""".split())
FACE = ("face", "head", "reaction", "double take", "double-take", "barber", "date", "cheek", "walk", "creator", "mirror",
        "car ", "smile", "points", "before/after", "before and after")
HANDS = ("hand", "hands", "fingers", "palm")
PAGE = ("page", "capture", "card", "reviews", "gq", "logo", "survey")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _search_mod():
    return _load("shot_fill_search", ST.part("asset-index") / "machine" / "search.py")


def _library_mod():
    f = ST.part("asset-index") / "library" / "library.py"
    return _load("shot_fill_library", f) if f.is_file() else None


def marked(hits, brand, LB):
    """The hits with the footage library's text marks on them (asset-index library.enrich); unchanged without one."""
    if LB is None:
        return hits
    try:
        return LB.enrich(hits, brand)
    except Exception:                                  # noqa: BLE001 - a broken library judges nothing
        return hits


def caption_free(h, brand, LB):
    """No words burned into the clip (owner, 16 Nov 2026): a caption, offer text, handle or app screen already on a
    clip is someone else's edit, never a shot of ours. The library's text marks decide; a clip a built library does
    not know is unknown, so it is out too."""
    if "text_marks" in h:
        return list(h.get("text_marks") or []) == ["clean"]
    try:
        return LB is None or not LB.rows_of(brand)
    except Exception:                                  # noqa: BLE001
        return True


def clean(text, cfg):
    """A shot's words as a description of what it shows: the slot brackets opened, the making words dropped."""
    t = re.sub(r"\[SLOT:\s*([^\]]*)\]", r" \1 ", str(text or ""))
    if cfg.get("product") and cfg.get("product_seen"):
        t = re.sub(r"\b%s\b" % re.escape(cfg["product"]), cfg["product_seen"], t, flags=re.I)
        t = re.sub(r"\bdevice\b", cfg["product_seen"], t, flags=re.I) if cfg["product_seen"] not in t else t
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'/-]*", t) if w.lower() not in BOILER]
    return " ".join(dict.fromkeys(words))


def kind_of(text):
    s = " " + str(text or "").lower() + " "
    if any(w in s for w in FACE):
        return "face"
    if any(re.search(r"\b%s\b" % w, s) for w in HANDS):
        return "hands"
    if any(re.search(r"\b%s\b" % w, s) for w in PAGE):
        return "page"
    return "product"


def shots_of(n, cfg):
    """Every shot to fill, scene by scene: the brief's shots, its continuity rows, and the production's own list."""
    brief = json.load(open(ST.BRIEFS / n / "brief.json"))
    import seed_from_brief as SB
    doc = SB.brief_json(brief.get("run") or brief["brief"])
    out = []
    for sc in doc.get("scenes") or []:
        if sc["id"] not in brief.get("order", []):
            continue
        olds = {o.get("id"): o for o in sc.get("joined_scenes") or []}
        for sh in sc.get("shots") or []:
            sp = sh.get("start_picture")
            moves = sh.get("gestures")
            moves = "; ".join(moves) if isinstance(moves, list) else (moves or "")
            own = (olds.get(sh.get("of_scene")) or {}).get("happens") if sh.get("of_scene") else ""
            text = " ".join(str(x) for x in [sh.get("action"), sh.get("picture"), own, moves, sp if sp not in ("first_frame", None) else ""] if x)
            out.append({"scene": sc["id"], "id": sh.get("id"), "from": "brief shot", "phrase": " / ".join(l.get("say", "") for l in sh.get("lines") or []),
                        "text": text, "kind": kind_of(text),
                        "as_written": sh.get("of_scene") or str(sh.get("was_id") or sh.get("id") or "").split(".")[0]})
        for r in doc.get("roll_sheet") or []:
            if r.get("adapted_scene") != sc["id"]:
                continue
            m = re.search(r"\[shows:\s*([^\]]+)\]", r.get("row", ""))
            if m:
                out.append({"scene": sc["id"], "id": "continuity " + r["row"].split("·")[0].strip(), "from": "continuity row",
                            "phrase": "", "text": m.group(1), "kind": kind_of(m.group(1))})
    own = ST.BRIEFS / n / "shot-list.json"
    if own.exists():
        for i, r in enumerate(json.load(open(own))["shots"], 1):
            out.append({"scene": r["scene"], "id": r.get("id") or "%s.p%d" % (r["scene"], i), "from": "production shot list",
                        "phrase": r.get("phrase", ""), "from_word": r.get("from_word"), "refines": r.get("refines"),
                        "text": r["shows"], "kind": r.get("kind") or kind_of(r["shows"]),
                        # the swipe shot it copies and its time in our cut (swipe_shots.py)
                        **{k: r[k] for k in ("copies", "swipe_seconds", "share", "at", "seconds", "status") if k in r}})
    return brief, out


def local_file(hit, roots):
    """The clip as a file on this machine: the record's own path, else its folder and file name under a library root."""
    try:
        c = json.load(open(Path(hit["record_dir"]) / "clip.json")) if hit.get("record_dir") else {}
    except (OSError, ValueError):
        return None
    if c.get("path") and os.path.isfile(c["path"]):
        return c["path"]
    for root in roots:
        for p in ((os.path.join(root, c.get("folder") or "", c.get("filename") or "") if c else "\0"),
                  os.path.join(root, hit.get("shared_path") or "\0")):   # a root that holds the "Shared Assets" drive
            if os.path.isfile(p):
                return p
    return None


NOT_OURS = ("/intake/", "/archive/", "/references/", "/swipe/", "/competitors/")
RETIRED = ("outdated-packaging",)       # footage of packaging we no longer sell (20 Nov): never in an ad


def off_product(path, product):
    """True for a clip an ad must not use: retired packaging, or another of the brand's products' own footage folders
    (a face-scrub clip in a body-scrub ad), read off the clip's file name."""
    p = str(path or "").lower()
    if any(x in p for x in RETIRED):
        return True
    prod = str(product or "").lower()
    name = p.rsplit("/", 1)[-1]
    if "body" in prod and "scrub" in prod and name.startswith("brilliance-face-scrub"):
        return True
    if "face" in prod and "scrub" in prod and name.startswith("brilliance-body-scrub"):
        return True
    return False


def fits(hit, kind, cfg):
    p = hit.get("shared_path") or ""
    # OUR footage only (16 Nov): swipes, references and archived posts are other people's videos, never a shot of ours
    if any(x in p for x in NOT_OURS) or off_product(p, cfg.get("product")):
        return False
    # ONE DEMOGRAPHIC PER EDIT, hands-only and product-in-hand shots included (10 Nov): a creator's clip plays a product
    # shot only when the creator is in the ad's band; the brand's own footage (no creator folder) still serves
    if kind == "product" and "/content-creators/" in p and (cfg.get("hands_like") or cfg.get("person")):
        return any(x in p for x in cfg.get("hands_like") or []) or (cfg.get("person") or "\0") in p
    if kind == "face" and not cfg.get("person"):
        kind = "hands"                   # an ad with no one on camera: a "face" word (points, smile) is the hand's
    if kind == "face":
        return cfg.get("person", "\0") in p
    if kind == "hands":
        if not cfg.get("person") and not cfg.get("hands_like"):
            return True                  # no one on camera and no hands named: any customer's hands (POV shots)
        return any(x in p for x in cfg.get("hands_like") or []) or (cfg.get("person") or "\0") in p
    return True


def ad_style(n):
    """The production's style ({id, from, photoreal}) from video-production styles/style_chain.py; None where the
    chain is not installed. A style the bank does not hold stops the fill by name."""
    f = ST.part("video-production") / "styles" / "style_chain.py"
    if not f.is_file():
        return None
    SC = _load("shot_fill_style_chain", f)
    st = SC.ad_style(n, briefs=ST.BRIEFS, writing=ST.WRITING)
    return dict(st, photoreal=SC.footage_allowed(st["id"]))


def chain_footage(brief, cfg):
    """The writing chain's footage decision for every scene as written (video-production footage.py storyboard_pass:
    the production chain's gate, i.e. the clip must do the shot's action, show the named product, sit in the scene's
    place and carry no burned-in words). Read from the run's storyboard-footage.json; asked for when the run has none
    (free, reads only). None when the chain is not installed or the run is not found."""
    run = brief.get("run") or brief.get("brief")
    stages = Path(ST.WRITING) / str(run) / "stages"
    f = stages / "storyboard-footage.json"
    if not f.is_file():
        fp = ST.part("video-production") / "machine" / "footage.py"
        src = stages / "5-brief.before-fold.md"
        src = src if src.is_file() else stages / "5-brief.md"
        if not (fp.is_file() and src.is_file()):
            return None
        _load("shot_fill_footage", fp).storyboard_pass(src, cfg["brand"])
    try:
        return json.load(open(f))
    except (OSError, ValueError):
        return None


def from_chain(rows, chain, cfg, lane="ai"):
    """Each shot's footage as the chain decided it: CUT = the clip the gate passed (REAL), anything else a GAP made with
    AI, the nearest clip of ours kept as its picture reference. A production-list row takes its brief shot's call."""
    scenes = chain.get("scenes") or {}
    of = {r["id"]: r.get("as_written") for r in rows if r.get("from") == "brief shot"}
    out = []
    for r in rows:
        r = dict(r, query="(the chain's footage gate)")
        if r.get("kind") == "page":
            out.append(dict(r, status="CAPTURE", reason="a page, card or capture: made in the Studio as a card, not searched"))
            continue
        d = scenes.get(r.get("as_written") or of.get(r["id"]) or "") or {}
        c, near = d.get("clip") or {}, d.get("nearest") or {}
        if lane == "real" and not c and near:       # Real (picked on the storyboard): our closest clip, passed or not
            c = near
        if c and (d.get("plan") == "cut" or lane == "real"):
            hit = {"record_dir": None, "shared_path": c.get("shared_path")}
            r.update(status="REAL", clip=c.get("clip_id"), **{"in": c.get("in"), "out": c.get("out")}, score=float(c.get("score") or near.get("score") or 0),
                     rights=None, shows=(c.get("shows") or "") + ("" if d.get("plan") == "cut" else " (closest of ours)"),
                     shared_path=c.get("shared_path"),
                     file=local_file(hit, cfg.get("library_roots") or []),
                     alternatives=[{"clip": x.get("clip_id"), "in": x.get("in"), "out": x.get("out"), "score": x.get("score"),
                                    "shows": x.get("shows"), "path": x.get("shared_path")} for x in d.get("alternates") or []])
        else:
            why = {"presenter": "a person on camera saying the line: made, never library footage",
                   "made": "made, not filmed (card, screen or end card)", "held": "held from the swipe"}.get(d.get("plan"))
            r.update(status="GAP", reason=why or ("no clip of ours does this shot (the chain's gate); nearest: %s %.2f"
                                                  % ((near.get("shows") or "")[:70], float(near.get("score") or 0))
                                                  if near else "no clip of ours does this shot (the chain's gate)"),
                     reference=(d.get("ref") or {}).get("file"), alternatives=[])
        out.append(r)
    return out


def _moments_mod():
    """The asset index's moments (components/asset-index/library/moments.py), through the chain's loader; None when
    the index has none."""
    try:
        return ST.chain("video-edit", "shot_timing")._moments()
    except Exception:  # noqa: BLE001
        return None


def on_moments(rows, cfg):
    """MOMENTS FIRST (owner, 17 Nov: editing is a lookup on the asset index). Each REAL shot's in/out is placed on a
    clean moment of its own clip (no text over the video, no blur or transition, not dead, the right product in use on
    a product shot, one clip section per shot), measured and judged once when the clip entered the index. Its
    alternatives are reordered: clips with a clean moment first, placed on it; a clip the pass read and found no clean
    moment in is dropped. The chain's choice of clip is kept; a clip with no moments yet is left as placed (the cut
    measures it live). Off with shot_fill.moments: false."""
    MO = _moments_mod()
    if MO is None or cfg.get("moments") is False or not cfg.get("brand"):
        return rows
    brand = cfg["brand"]
    try:
        pk_all = MO.product_key(cfg.get("product"), brand)
    except Exception:  # noqa: BLE001
        pk_all = None
    taken = {}
    for r in rows:
        if r.get("status") != "REAL" or not r.get("shared_path"):
            continue
        need = min(float(r.get("seconds") or 2.5), 3.0 if r.get("kind") == "endcard" else 2.5)
        pk = pk_all if r.get("kind") == "product" else None
        path = r["shared_path"]
        if MO.known(brand, path):
            got = MO.place(brand, path, float(r.get("in") or 0), need, pk, avoid=taken.get(path, []))
            if got:
                r["in"], r["out"], r["moment"] = got[0], round(got[0] + need, 2), got[1]["id"]
                r["moment_shows"] = (got[1].get("judge") or {}).get("shows")
                taken.setdefault(path, []).append((got[0], got[0] + need))
            else:
                r["moment"] = None
                r["moment_why"] = "no clean moment of %.1f s in this clip%s: the cut takes the next alternative" % (
                    need, " with the product in use" if pk else "")
        alts = []
        for a in r.get("alternatives") or []:
            if not a.get("path") or not MO.known(brand, a["path"]):
                alts.append((1, a))
                continue
            got = MO.place(brand, a["path"], float(a.get("in") or 0), need, pk, avoid=taken.get(a["path"], []))
            if got:
                alts.append((0, dict(a, **{"in": got[0], "out": round(got[0] + need, 2), "moment": got[1]["id"]})))
        r["alternatives"] = [a for _, a in sorted(alts, key=lambda x: x[0])]
    return rows


SAID_BAR = 0.25    # a clip that shows the words over the shot, scored on a short plain picture of them


def said_words(rows, brief):
    """The words that play over each shot: its own lines, else its share of its scene's line, in the scene's shot order."""
    import seed_from_brief as SB
    try:
        doc = SB.brief_json(brief.get("run") or brief["brief"])
    except Exception:  # noqa: BLE001
        return {}
    line = {sc["id"]: sc.get("voice") or " ".join(l.get("say", "") for l in sc.get("script") or []) for sc in doc.get("scenes") or []}
    out, by = {}, {}
    for r in rows:
        by.setdefault(r.get("scene"), []).append(r)
    for sc, rs in by.items():
        words = str(line.get(sc) or "").split()
        k = len(rs)
        for i, r in enumerate(rs):
            own = (r.get("phrase") or "").strip()
            out[r["id"]] = own if own else " ".join(words[len(words) * i // k: len(words) * (i + 1) // k])
    return out


NEG_LOOK = ("smile", "smiling", "smiles", "laugh", "laughing", "laughs", "happy", "glowing", "glow", "thumbs up",
            "poses", "posing", "beaming", "delighted", "cheerful", "confident", "joy", "excited", "dances", "dancing")
POS_LOOK = ("frown", "frowning", "unhappy", "frustrated", "upset", "worried", "sad", "disappointed", "scratches",
            "irritated", "red patch", "flaky", "dry, rough")


def tone_ok(shows, feeling):
    """EMOTION MAPPING (owner, 20 Nov 2026: "we're using positive imagery for negative words"): a clip carries the
    feeling of the words over it. A negative beat never plays a smiling, glowing, posing clip; a positive beat never a
    frowning or flaky one. Neutral beats take either."""
    t = " " + str(shows or "").lower() + " "
    if feeling == "negative":
        return not any(w in t for w in NEG_LOOK)
    if feeling == "positive":
        return not any(w in t for w in POS_LOOK)
    return True


def said_beats(n, rows, brief, cfg):
    """{shot id: {"picture", "feeling", "emotion"}}: for each shot's words, one plain picture of real footage that shows
    what is said AND the feeling it carries (the story's emotion map: the problem looks like the problem, the payoff
    looks like the payoff). One cheap model call per production, kept in briefs/<n>/said-visuals.json and reused while
    the words are the same."""
    words = said_words(rows, brief)
    for r in rows:
        r["said_words"] = words.get(r["id"], "")
    want = {i: w for i, w in words.items() if w.strip()}
    f = ST.BRIEFS / n / "said-visuals.json"
    try:
        have = json.load(open(f))
    except (OSError, ValueError):
        have = {}
    if have.get("words") == want and have.get("beats"):
        return have["beats"]
    who = ", ".join(cfg.get("hands_like") or []) or "the ad's customer"
    prompt = ("These are the lines of a voiceover for a short story ad, in order. The pictures under them are real "
              "footage of customers (%s) using %s (%s). Map the story's emotion line by line, then for each line give "
              "the real footage that shows it. \"picture\": ONE plain description, 6 to 12 words, of what a camera "
              "sees (the person, the body part, the action, the product only if the line names it; never a metaphor), "
              "and it must CARRY the line's feeling: a problem line shows the problem and the frustration (dry flaky "
              "skin, covering up, frowning at her arm), a payoff line shows the relief (smooth skin, a real smile). "
              "\"feeling\": negative, positive or neutral. \"emotion\": one or two words (frustrated, embarrassed, "
              "hopeful, relieved, proud).\n\nAnswer with only a JSON object mapping each id to an object with "
              "picture, feeling and emotion.\n\n%s" % (who, cfg.get("product") or "the product",
              cfg.get("product_seen") or "", json.dumps(want, indent=1, ensure_ascii=False)))
    try:
        sys.path.insert(0, str(ST.part("run-kit")))
        from run_kit import claude_door
        txt = claude_door.ask(prompt, model="sonnet", timeout=600)
        beats = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        beats = {k: (v if isinstance(v, dict) else {"picture": str(v), "feeling": "neutral"}) for k, v in beats.items()}
    except Exception as e:  # noqa: BLE001 -- no map: the shots are searched as before
        print("said_beats: %s" % str(e)[:200], file=sys.stderr)
        return {}
    json.dump({"words": want, "beats": beats}, open(f, "w"), indent=1, ensure_ascii=False)
    return beats


def said_visuals(n, rows, brief, cfg):
    """{shot id: picture} from said_beats; each row keeps its feeling (r["feeling"]) for the tone filter."""
    beats = said_beats(n, rows, brief, cfg)
    for r in rows:
        b = beats.get(r["id"]) or {}
        r["feeling"], r["emotion"] = b.get("feeling") or "neutral", b.get("emotion") or ""
    return {k: v.get("picture") for k, v in beats.items() if v.get("picture")}

def search_shot(sh, row, cfg, S, LB, bar, taken, more=(), pov=True):
    """One shot through the asset index's search (components/asset-index/machine/search.py): the shot's words, each
    clause on its own, and any plainer words handed in (the line it plays over, what it plainly shows). Fills `row`
    with the best clip of ours over the bar (REAL) or the nearest ones (GAP), and books the clip section in `taken`."""
    # the whole description, then each of its clauses on its own: the index scores a long sentence low even when one
    # clause of it ("lifts the device off its base") is exactly a clip it holds (10 Nov: 1 of 7 found on long text)
    qs = [row["query"]] + [q for q in (clean(x, cfg) for x in re.split(r"[;.]", sh["text"])) if len(q.split()) >= 3] \
        + [q for q in (clean(x, cfg) for x in more) if len(q.split()) >= 2]
    best_of = {}
    for q in dict.fromkeys(qs):
        for h in S.search(q, brand=cfg["brand"], per=PER, drop={w.lower() for w in cfg.get("drop") or []}):
            k = (h["shared_path"], h["in"])
            if k not in best_of or h["score"] > best_of[k]["score"]:
                best_of[k] = h
    hits = sorted(marked(list(best_of.values()), cfg["brand"], LB), key=lambda h: -h["score"])
    seen = set()
    cands = []
    for h in hits:
        if h["shared_path"] in seen:
            continue                     # one record per file (a clip can sit in the index under two keys)
        seen.add(h["shared_path"])
        if not fits(h, sh["kind"], cfg) or not caption_free(h, cfg["brand"], LB) or not tone_ok(h.get("shows"), sh.get("feeling")):
            continue
        if any(h["shared_path"] == t[0] and h["in"] is not None and t[1] < h["out"] and h["in"] < t[2] for t in taken):
            continue
        cands.append(h)
    best = next((h for h in cands if h["score"] >= bar), None)
    if not best and pov and (sh["kind"] in ("hands", "product") or (sh["kind"] == "face" and not cfg.get("person"))) and cfg.get("product_seen") and not cfg.get("person"):
        # nothing matched the brief's words: the plain POV shot of the product (the shot every customer films) is
        # the owned stand-in, judged against the swipe shot at the check like any other (rule, 10 Nov: a hands-and-
        # product shot is customer point-of-view footage; the step fills itself instead of stopping)
        pov = ["hand holds %s toward camera" % cfg["product_seen"], "close-up of %s held in hand" % cfg["product_seen"]]
        for q in pov:
            for h in marked(S.search(q, brand=cfg["brand"], per=400), cfg["brand"], LB):
                if h["score"] < bar or not fits(h, sh["kind"], cfg) or not caption_free(h, cfg["brand"], LB) or any(
                        h["shared_path"] == t[0] and h["in"] is not None and t[1] < h["out"] and h["in"] < t[2] for t in taken):
                    continue
                if local_file(h, cfg.get("library_roots") or []):
                    best = dict(h, shows=h["shows"] + " (POV stand-in)")
                    break
            if best:
                break
    alts = [{"clip": h["clip_id"], "in": h["in"], "out": h["out"], "score": h["score"], "shows": h["shows"],
             "path": h["shared_path"]} for h in cands[:4]]
    if best:
        taken.append((best["shared_path"], best["in"], best["out"]))
        row.update(status="REAL", clip=best["clip_id"], **{"in": best["in"], "out": best["out"]}, score=best["score"],
                   rights=best["rights"].get("state"), shows=best["shows"], shared_path=best["shared_path"],
                   file=local_file(best, cfg.get("library_roots") or []), alternatives=alts[1:])
    else:
        near = cands[0] if cands else None
        who = {"face": "the ad's person" if cfg.get("person") else "matching hands", "hands": "matching hands"}.get(sh["kind"], "any owned footage")
        row.update(status="GAP", reason=("best hit of %s scores %.2f, under the bar %.2f (%s)" % (who, near["score"], bar, near["shows"][:80])
                                         if near else "no footage of %s shows it" % who), alternatives=alts)
    return row


def fill(n):
    brief = json.load(open(ST.BRIEFS / n / "brief.json"))
    cfg = brief.get("shot_fill") or {}
    if not cfg.get("brand"):
        raise SystemExit("brief.json has no shot_fill.brand: say which brand's index to search")
    brief, shots = shots_of(n, cfg)
    # THE AD'S STYLE (owner ruling, 12 Nov 2026): real footage only goes into a photoreal ad. In any other style
    # every shot is made in the style (its people, product and set as style variants), so nothing is searched.
    style = ad_style(n)
    if style and not style.get("photoreal", True):
        rows = [dict(sh, query=clean(sh["text"], cfg), status="GAP",
                     reason=f"the ad is made in the {style['id']} style (not photoreal): real footage would break the "
                            "look; made in the style from the elements' style variants") for sh in shots]
        out = {"production": n, "brief": brief["brief"], "bar": float(cfg.get("bar") or BAR), "person": cfg.get("person"),
               "style": style, "shots": rows,
               "gaps": [r["id"] for r in rows if r["from"] == "production shot list"]
               or [r["id"] for r in rows if r["from"] == "brief shot"]}
        json.dump(out, open(ST.BRIEFS / n / "shot-fill.json", "w"), indent=1, ensure_ascii=False)
        (ST.BRIEFS / n / "SHOT-FILL.md").write_text(markdown(out))
        return out
    chain = chain_footage(brief, cfg)
    if chain is not None:
        rows = from_chain(shots, chain, cfg, brief.get("lane") or "ai")
        # EVERY SHOT SHOWS WHAT IS SAID OVER IT (owner, 20 Nov 2026: "we are not matching the B-roll to what's being said
        # ... that needs to be in the chain"): each shot's words become one plain picture of real footage (said_visuals),
        # the asset index is searched for that picture first, and the gate's pick stays only where nothing of ours shows
        # it. The gate's own empty shots go through the same search. Cards (kind page) stay made.
        if (brief.get("lane") or "ai") != "ai":
            S, LB, sbar = _search_mod(), _library_mod(), float(cfg.get("bar") or BAR)
            pics = said_visuals(n, rows, brief, cfg)
            taken = []
            for r in rows:
                if r.get("status") == "CAPTURE" or r.get("kind") == "page":
                    continue
                keep = {k: r.get(k) for k in ("status", "clip", "in", "out", "score", "rights", "shows", "shared_path",
                                              "file", "alternatives", "reason")}
                pic = pics.get(r["id"])
                if pic:
                    probe = dict(r, text=pic, query=clean(pic, cfg), status="GAP", kind="hands", feeling=r.get("feeling"))  # our customers, this ad's demographic
                    search_shot(probe, probe, cfg, S, LB, SAID_BAR, taken, more=[], pov=False)
                    better = probe.get("status") == "REAL" and (keep["status"] != "REAL" or float(probe.get("score") or 0)
                                                                 >= float(keep.get("score") or 0) - 0.05)
                    if better:
                        r.update({k: probe.get(k) for k in ("status", "clip", "in", "out", "score", "rights", "shows",
                                                             "shared_path", "file", "alternatives")})
                        r["shows"] = (r.get("shows") or "") + " (shows what is said: %s)" % pic[:80]
                        r["said_picture"] = pic
                        continue
                if keep["status"] == "REAL" and keep.get("in") is not None and fits({"shared_path": keep.get("shared_path")}, "hands", cfg) and not any(
                        keep["shared_path"] == t[0] and t[1] is not None and t[1] < keep["out"] and keep["in"] < t[2] for t in taken):
                    taken.append((keep["shared_path"], keep["in"], keep["out"]))     # nothing closer: the gate's pick stays, once
                    continue
                r.update(status="GAP", query=clean(r.get("text"), cfg), kind="hands")   # our customers only, as above
                search_shot(r, r, cfg, S, LB, sbar, taken, more=[r.get("phrase") or ""] + str(r.get("phrase") or "").split(" / "), pov=False)
        rows = on_moments(rows, cfg)
        out = {"production": n, "brief": brief["brief"], "bar": chain.get("confident_at"), "person": cfg.get("person"),
               "decided_by": "writing chain footage gate (storyboard-footage.json, %s)" % chain.get("made"), "shots": rows,
               "gaps": [r["id"] for r in rows if r["status"] == "GAP" and r["from"] == "production shot list"]
               or [r["id"] for r in rows if r["status"] == "GAP" and r["from"] == "brief shot"]}
        json.dump(out, open(ST.BRIEFS / n / "shot-fill.json", "w"), indent=1, ensure_ascii=False)
        (ST.BRIEFS / n / "SHOT-FILL.md").write_text(markdown(out))
        return out
    S = _search_mod()
    LB = _library_mod()
    bar = float(cfg.get("bar") or BAR)
    taken_by = {}        # per shot list: (shared_path, in, out) already given to a shot, so no clip section plays twice
    rows = []
    for sh in shots:
        row = dict(sh, query=clean(sh["text"], cfg))
        taken = taken_by.setdefault(sh["from"], [])
        if sh["kind"] == "page":
            row.update(status="CAPTURE", reason="a page, card or capture: made in the Studio as a card, not searched")
            rows.append(row)
            continue
        search_shot(sh, row, cfg, S, LB, bar, taken)
        rows.append(row)
    rows = on_moments(rows, cfg)
    out = {"production": n, "brief": brief["brief"], "bar": bar, "person": cfg.get("person"), "shots": rows,
           "gaps": [r["id"] for r in rows if r["status"] == "GAP" and r["from"] == "production shot list"]
           or [r["id"] for r in rows if r["status"] == "GAP" and r["from"] == "brief shot"]}
    json.dump(out, open(ST.BRIEFS / n / "shot-fill.json", "w"), indent=1, ensure_ascii=False)
    (ST.BRIEFS / n / "SHOT-FILL.md").write_text(markdown(out))
    return out


def markdown(d):
    L = ["# Shot fill · " + d["production"], "",
         "Each shot the brief names, the best owned clip the asset index has for it, or GAP. "
         "Face shots take only the ad's person; GAP is what goes to AI. Made by `shot_fill.py`.", ""]
    for scene in dict.fromkeys(r["scene"] for r in d["shots"]):
        L += ["## " + scene, "", "| Shot | From | Shows (brief) | Kind | Result | Clip · in–out | Score | Rights |", "|---|---|---|---|---|---|---|---|"]
        for r in d["shots"]:
            if r["scene"] != scene:
                continue
            text = (r.get("phrase") + " → " if r.get("phrase") else "") + r["text"]
            text = text.replace("|", "/")[:140]
            if r["status"] == "REAL":
                res = "REAL · " + r["shows"].replace("|", "/")[:70]
                clip = "%s · %s–%s s" % (r["shared_path"].rsplit("/", 1)[-1], r["in"], r["out"])
                L.append("| %s | %s | %s | %s | %s | %s | %.2f | %s |" % (r["id"], r["from"], text, r["kind"], res, clip, float(r.get("score") or 0), r.get("rights")))
            else:
                L.append("| %s | %s | %s | %s | %s | – | – | – |" % (r["id"], r["from"], text, r["kind"], r["status"] + " · " + r["reason"][:90]))
        L.append("")
    L += ["## Gaps (what goes to AI)", ""] + ["- " + g for g in d["gaps"]] + [""]
    return "\n".join(L)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("name the production, e.g. " + os.path.basename(__file__) + " idea-1")
    r = fill(sys.argv[1])
    for x in r["shots"]:
        print("%-8s %-22s %-7s %-7s %s" % (x["scene"], x["id"][:22], x["kind"], x["status"],
                                           (x.get("shows") or x.get("reason") or "")[:90]))
    print("gaps:", ", ".join(r["gaps"]) or "none")
