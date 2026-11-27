"""Shot copy: does each shot we made show what its swipe shot shows? Judged on the pictures, every cut, never assumed.

  python3 shot_copy.py <production>          judges every made shot against the swipe shot it copies
                                              -> briefs/<p>/SHOT-COPY.json and SHOT-AUDIT.jpg (swipe left, ours right)
  python3 shot_copy.py <production> --fill [ids]   then (all misses, or only the shot ids named), for every shot that does not copy its swipe shot:
                                              1. owned footage first: the asset index searched with what the shot needs,
                                                 each candidate judged against the swipe shot; a passing clip goes into
                                                 picks.json (with the judge's reason)
                                              2. no owned clip and no product in the shot: an AI recipe (gen_ref.py's
                                                 house process) from the swipe shot's guide frame (faces and words covered)
                                                 and the production's face master, in sources/generated/recipes-<p>-copy.json;
                                                 a picture with people needs its filed 3D set first (image-production
                                                 RULE GATE-4), so the recipe waits for its `set`
                                              3. the product in the shot and no owned clip: listed as a SHOOT (a creator
                                                 brief line); the product is never drawn by AI
                                              -> briefs/<p>/SHOT-GAPS.json

Why (the owner, 10 Nov 2026: "with the scene and the shots did you go through everything we didn't have??? ... establish
in the chain where it needs to go so we don't have this problem again, it should happen automatically"): swipe_check only
proved each swipe shot had a clip at its length, not that the clip copies the shot; 5 of Smash or Pass's 22 body shots
showed something else and 7 were weak. swipe_check.py now runs this judge (cached per frame) and fails on any shot that
does not copy its swipe shot.

A shot the owner keeps as it is carries his words in picks.json (shots.<id>.owner_ok) and passes as OWNER.
Reads: shot-list.json (swipe_shots.py), picks.json, brief.json ("shot_fill": brand, person, hands_like, product,
product_seen, library_roots, bar, face_master), the swipe's frame map (framemap/shots/K??-mid.jpg). The judge is the
team's vision_judge door (Claude on the plan, then local, then Gemini). Brand-agnostic.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

MACHINE = ST.part("video-production") / "machine"
VERDICTS = ("COPIES", "WEAK", "MISSING")

JUDGE = """You check one shot of a short video ad against the shot it must copy from a proven ad (the swipe).

Image 1 is the SWIPE shot (middle frame). Image 2 is OUR shot (middle frame). You see one frame of each: judge what is
in the frame (who, how many, what they do, distance and angle, kind of place), not motion.

Our ad sells {product} ({product_seen}). Translate the swipe before you compare:
- its product becomes ours, and its product's use becomes ours (cream, spray, scent or drops on skin become the brush on
  the face, its bristles, foam, rinsing; a product macro becomes a macro of ours);
- a place or person our narration names replaces the swipe's (the narration over our shot is the brief: if it says
  "barber chair" where the swipe shows a bar, a barber chair is right);
- a body part our narration names replaces the swipe's (the swipe's hands on a chest over "smoothing shins" become hands
  working the product on the shins: the same moment, the woman treating her own skin where the line says);
- a body part our narration names replaces the swipe's (the swipe's hands on a chest over "smoothing shins" become hands
  working the product on the shins: the same moment, the woman treating her own skin where the line says);
- a page capture with a price becomes our page capture without a price (reviews, the product page);
- our cast replaces theirs (any look, same number of people, same roles).
The swipe shot shows: {does}
Its camera: {camera}
What our shot is meant to show (our shot list): {shows}
The narration over our shot's scene: "{words}"

After that translation, is ours the same moment: the same number of people in the same roles doing the same kind of
thing, at about the same distance and angle, in the same kind of place? A different moment, a repeat of the shot before,
or a still photo where the swipe films a person is not a copy.

Answer JSON only:
{{"verdict": "COPIES" | "WEAK" | "MISSING",
  "why": "one short sentence on what differs (empty when it copies)",
  "need": "what our shot must show to copy it, one line, with our cast; name our product only if image 1 shows the swipe's product",
  "swipe_product_visible": true | false (image 1 shows the swipe's product: a jar, bottle, cream, spray or its page),
  "ad_person_face": true | false (the shot needs our man's face),
  "search": "5 to 8 plain words a footage library would use for our shot, product called {product_seen}"}}
COPIES = same moment after the translation, framing close. WEAK = same moment, but distance, angle, people count or place
is clearly off. MISSING = a different moment."""
JUDGE_V = "3"     # a change to the judge's words judges every shot again



def _mod(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _vj():
    return _mod("shot_copy_vj", MACHINE / "vision_judge.py")


def _framemap(n):
    """The swipe's frame-map shots: the writing run the production's brief names (its framemap/, as swipe_shots.py reads it)."""
    import seed_from_brief as SB
    b = json.load(open(ST.BRIEFS / n / "brief.json"))
    p = SB.WORK / (b.get("run") or b["brief"]) / "framemap" / "shots"
    if not p.is_dir():
        raise SystemExit("no swipe frame map at " + str(p))
    return p.resolve()


def _frame(video, t, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2,format=yuvj420p",
                    str(out)], check=True)
    return out


def shots(n):
    """Every swipe shot of every made body scene: its row, our frame (middle of its slot in the made scene) and the swipe's."""
    import swipe_cut as SC
    import video_studio as VS
    brief, picks, scenes = SC.plan(n)
    fm = _framemap(n)
    out_dir = ST.BRIEFS / n / "shot-copy"
    out_dir.mkdir(exist_ok=True)
    words = {}
    for sid in scenes:
        wf = json.load(open(ST.BRIEFS / n / "scenes" / sid / (brief["picks"][sid] + ".json")))
        words[sid] = next((s.get("prompt") or "" for s in wf["steps"] if s["tool"] == "voice.read"), "")
    rows = []
    for sid, rs in scenes.items():
        take = brief["picks"][sid]
        v = ST.BRIEFS / n / "scenes" / sid / "out" / take / (sid + ".mp4")
        if not v.is_file():
            continue
        d, at = VS.probe_dur(str(v)), 0.0
        for r in rs:
            mid = (at + r["share"] / 2) * d
            at += r["share"]
            ours = _frame(v, mid, out_dir / (r["id"] + "-ours.jpg"))
            k = r.get("copies") or ""
            sw = fm / (k + "-mid.jpg") if k else None
            if k and r.get("swipe_span"):       # a scene that copies part of a swipe shot: the middle of its own part
                a, b = r["swipe_span"]
                sw = _frame(fm.parent.parent / "source.mp4", (a + b) / 2, out_dir / (r["id"] + "-swipe.jpg"))
            rows.append({"id": r["id"], "scene": sid, "copies": k, "ours": str(ours), "swipe": str(sw) if sw and sw.is_file() else None,
                         "swipe_span": r.get("swipe_span"),
                         "does": r.get("swipe_does", ""), "camera": r.get("swipe_camera", ""), "words": words.get(sid, ""),
                         "shows": "; ".join(x for x in [(picks["shots"].get(r["id"]) or {}).get("note", ""),
                                                         (r.get("shows") or "")[:200]] if x),
                         "pick": (picks["shots"].get(r["id"]) or {}), "owner_added": not k})
    return brief, picks, rows


def judge(n):
    brief, picks, rows = shots(n)
    cfg = brief.get("shot_fill") or {}
    cache_f = ST.BRIEFS / n / "shot-copy" / "cache.json"
    cache = json.load(open(cache_f)) if cache_f.is_file() else {}
    vj = _vj()
    for r in rows:
        if not r["swipe"]:
            r.update(verdict="ADDED", why="the owner's own shot, not in the swipe")
            continue
        if r["pick"].get("owner_ok"):          # the owner said this shot stands (picks.json shots.<id>.owner_ok: his words)
            r.update(verdict="OWNER", why="the owner's call: " + r["pick"]["owner_ok"])
            continue
        # brief.json shot_fill "any_place": the owner's call that this ad's shots may be in any place (its swipe was
        # filmed somewhere the library has no footage of; customer point-of-view shots stand in). Off by default.
        place = cfg.get("any_place")
        key = hashlib.sha256(open(r["ours"], "rb").read() + (r["copies"] + JUDGE_V + ("|any-place" if place else "")
                                                                       + ("|%s" % r["swipe_span"] if r.get("swipe_span") else "")).encode()).hexdigest()[:16]
        if key not in cache:
            q = JUDGE.format(product=cfg.get("product", "our product"), product_seen=cfg.get("product_seen", ""),
                             does=r["does"], camera=r["camera"], words=r["words"],
                             shows=r.get("shows") or r["pick"].get("note", ""))
            if place:
                q += ("\n\nThe owner's call for this ad: " + str(place) + " Any place is right: judge the moment, the "
                      "people and hands, the product and the framing, never the place.")
            try:
                a = vj.ask(q, [r["swipe"], r["ours"]], want_json=True)
                j = vj.json_of(str(a))
                j["checked_by"] = "%s (%s)" % (getattr(a, "backend", "?"), getattr(a, "model", "?"))
            except Exception as e:  # noqa: BLE001  a judge that cannot answer leaves the shot UNCHECKED, never passed
                j = {"verdict": "UNCHECKED", "why": "%s: %s" % (type(e).__name__, str(e)[:160])}
            if j.get("verdict") not in VERDICTS:
                j["verdict"] = "UNCHECKED"
            if j["verdict"] != "UNCHECKED":
                cache[key] = j
                json.dump(cache, open(cache_f, "w"), indent=1)   # kept shot by shot: a stopped run resumes where it was
        else:
            j = cache[key]
        r.update(j, key=key)
    json.dump(cache, open(cache_f, "w"), indent=1)
    res = {"production": n, "shots": rows,
           "counts": {v: sum(1 for r in rows if r["verdict"] == v) for v in VERDICTS + ("OWNER", "ADDED", "UNCHECKED")}}
    json.dump(res, open(ST.BRIEFS / n / "SHOT-COPY.json", "w"), indent=1, ensure_ascii=False)
    sheet(n, rows)
    return res


def sheet(n, rows):
    """The picture of it: every shot, swipe left, ours right, its verdict on top and what it needs under it."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        F = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 28)
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 19)
    except OSError:
        F = f = ImageFont.load_default()
    col = {"COPIES": (40, 170, 90), "OWNER": (40, 140, 170), "MISSING": (220, 60, 60), "WEAK": (230, 150, 30), "ADDED": (100, 100, 100),
           "UNCHECKED": (90, 90, 160)}
    W, H = 240, 427
    cells = []
    for r in rows:
        c = Image.new("RGB", (W * 2 + 10, H + 76), (18, 18, 18))
        d = ImageDraw.Draw(c)
        if r["swipe"]:
            c.paste(Image.open(r["swipe"]).convert("RGB").resize((W, H)), (0, 40))
        else:
            d.text((60, 220), "not in swipe", fill=(150, 150, 150), font=f)
        c.paste(Image.open(r["ours"]).convert("RGB").resize((W, H)), (W + 10, 40))
        d.rectangle([0, 0, W * 2 + 10, 36], fill=col.get(r["verdict"], (90, 90, 90)))
        d.text((8, 3), "%s   %s" % (r["id"], "OK" if r["verdict"] == "COPIES" else r["verdict"]), fill=(255, 255, 255), font=F)
        d.text((6, H + 44), "swipe", fill=(150, 150, 150), font=f)
        d.text((W + 16, H + 44), "ours", fill=(150, 150, 150), font=f)
        if r["verdict"] in ("WEAK", "MISSING") and r.get("need"):
            d.rectangle([0, H + 10, W * 2 + 10, H + 40], fill=(0, 0, 0))
            d.text((6, H + 13), ("need: " + r["need"])[:52], fill=(255, 255, 255), font=f)
        cells.append(c)
    cols = 4
    g = Image.new("RGB", (cols * (W * 2 + 20), ((len(cells) + cols - 1) // cols) * (H + 86)), (0, 0, 0))
    for i, c in enumerate(cells):
        g.paste(c, ((i % cols) * (W * 2 + 20), (i // cols) * (H + 86)))
    g.save(ST.BRIEFS / n / "SHOT-AUDIT.jpg", quality=82)


FIND = """Image 1 is a shot from a proven ad (the swipe). Image 2 is one frame of a clip we own, for our ad.
Our shot needs to show: {need}
Could this clip play that shot in our ad: the same kind of moment and roughly the same distance? Our product, people and
room may differ from image 1. Small framing differences are fine; a different moment, a face that is not our man's where
the need names him, the product where the need does not name it, a visible price, or on-screen text is not.
Answer JSON only: {{"fits": true | false, "why": "one short sentence"}}"""


def fill(n, only=None):
    """Every shot that does not copy its swipe shot (or only the ids named): owned footage first, then an AI recipe,
    else a creator shoot."""
    res = json.load(open(ST.BRIEFS / n / "SHOT-COPY.json"))
    brief = json.load(open(ST.BRIEFS / n / "brief.json"))
    cfg = brief.get("shot_fill") or {}
    import shot_fill as SF
    S = SF._search_mod()
    vj = _vj()
    picks_f = ST.BRIEFS / n / "picks.json"
    picks = json.load(open(picks_f))
    used = {(p.get("source"), round(float(p.get("in") or 0))) for p in picks["shots"].values()}
    gen = ST.SOURCES / "generated"
    guide = _mod("shot_copy_guide", MACHINE / "swipe_guide.py")
    recipes, gaps = [], []
    for r in res["shots"]:
        if r["verdict"] not in ("WEAK", "MISSING") or (only and r["id"] not in only):
            continue
        need = r.get("need") or r["does"]
        named = [w for w in (cfg.get("product"), cfg.get("product_seen"), "brush", "device") if w]
        # the product is in the shot when the swipe shows its own or the need names ours: never an AI shot (never drawn)
        product = bool(r.get("swipe_product_visible")) or any(w.lower() in need.lower() for w in named)
        kind = "face" if r.get("ad_person_face") else ("product" if product else SF.kind_of(need))
        q = SF.clean(r.get("search") or need, cfg)
        found, tries = None, 0
        for h in S.search(q, brand=cfg["brand"], per=SF.PER)[:400]:
            if h["score"] < float(cfg.get("bar") or SF.BAR) or not SF.fits(h, kind, cfg):
                continue
            f = SF.local_file(h, cfg.get("library_roots") or [])
            if not f or (h["shared_path"], round(float(h["in"] or 0))) in used:
                continue
            t = float(h["in"] or 0) + 0.5
            try:
                cand = _frame(f, t, ST.BRIEFS / n / "shot-copy" / (r["id"] + "-cand.jpg"))
            except subprocess.CalledProcessError:
                continue                     # a clip this machine cannot read (a cloud file not downloaded): the next one
            try:
                a = vj.json_of(str(vj.ask(FIND.format(need=need), [r["swipe"], str(cand)], want_json=True)))
            except Exception:  # noqa: BLE001
                a = {"fits": False}
            if a.get("fits"):
                found = {"source": h["clip_id"], "file": f, "in": float(h["in"] or 0), "why": a.get("why", "")}
                break
            tries += 1
            if tries >= 6:                   # the six best candidates judged; past that the index has nothing better
                break
        if found:
            key = "O-" + found["source"]
            picks.setdefault("sources", {})[key] = found["file"]
            picks["shots"][r["id"]] = {"source": key, "in": found["in"],
                                       "note": "owned clip found by shot_copy: " + need, "why": found["why"]}
            used.add((found["file"], round(found["in"])))
            gaps.append({"id": r["id"], "route": "OWNED", "need": need, "clip": found["source"]})
            continue
        # NOT FOUND: THE SHOT IS DEFINED BY ITS SPEC (owner, 10 Nov 2026), never by the swipe's own action: shot_spec.py runs the
        # route, translates the swipe's product use into ours (shot_use) and the team's per-shot teardown, swaps and breakdown.
        # A shot whose action needs the product goes to the shoot list with OUR action; only an AI-routed spec gets a recipe,
        # and the recipe carries no words of its own (gen_ref takes the clip's words from the spec).
        import shot_spec as SPEC
        try:
            sp = SPEC.make_spec(n, r["id"])
        except (Exception, SystemExit) as e:  # noqa: BLE001  a read that cannot run (a key out of credit) holds the shot
            gaps.append({"id": r["id"], "route": "HELD", "need": need, "why": "no shot spec yet: " + str(e)[:300]})
            continue
        ours = sp["use"]["our_does"]
        if sp["use"].get("problems"):
            gaps.append({"id": r["id"], "route": "HELD", "need": ours, "why": "; ".join(sp["use"]["problems"])})
            continue
        if sp["route"]["route"] != "AI":
            gaps.append({"id": r["id"], "route": sp["route"]["route"], "need": ours, "why": sp["route"]["why"]})
            continue
        name = "%s-%s-copy" % (n.replace("-", ""), r["id"].replace(".", "-"))
        g = gen / "refs" / ("swipe-%s-%s-guide.jpg" % (n.replace("-", ""), r["copies"]))
        if not g.is_file():
            guide.make(r["swipe"], g)
        master = cfg.get("face_master")
        recipes.append({"name": name, "brief": n, "shot": r["id"], "scene": r["scene"], "covers": "%s: %s" % (r["copies"], ours[:80]),
                        "ref": g.name, "refs": [master] if master else [], "master": master, "master_first": False,
                        "seconds": 4, "no_people": False})
        gaps.append({"id": r["id"], "route": "AI", "need": ours, "recipe": name,
                     "first": "a people picture needs its filed 3D set (image-production RULE GATE-4): build the set from the"
                              " shot spec's still words (shot-spec/%s.json), print it with the cast board, file it, then give"
                              " the recipe its `set`" % r["id"]})
    json.dump(picks, open(picks_f, "w"), indent=1, ensure_ascii=False)
    if recipes:
        rf = gen / ("recipes-%s-copy.json" % n.replace("-", ""))
        old = json.load(open(rf)) if rf.is_file() else []
        have = {x["name"] for x in old}
        json.dump(old + [x for x in recipes if x["name"] not in have], open(rf, "w"), indent=1, ensure_ascii=False)
    json.dump({"production": n, "gaps": gaps}, open(ST.BRIEFS / n / "SHOT-GAPS.json", "w"), indent=1, ensure_ascii=False)
    shoot_list(n, gaps, {r["id"]: r for r in res["shots"]})
    return gaps


def shoot_list(n, gaps, rows):
    """The creator's shot list: every SHOOT gap as one line he can film, with the swipe frame it copies (SHOOT-LIST.md
    + shoot/<id>-swipe.jpg). Data for a creator brief; sending it is the owner's step."""
    sh = [g for g in gaps if g["route"] == "SHOOT"]
    d = ST.BRIEFS / n / "shoot"
    d.mkdir(exist_ok=True)
    lines = ["# Shots to film · " + n, "",
             "Each shot copies one shot of the proven ad: film it like the picture beside it, with the product, in the "
             "same framing. Phone, vertical, 4 to 6 seconds each, no talking, no text on screen.", ""]
    for i, g in enumerate(sh, 1):
        r = rows.get(g["id"]) or {}
        if r.get("swipe"):
            import shutil
            shutil.copy(r["swipe"], d / (g["id"] + "-swipe.jpg"))
        lines += ["%d. **%s** — %s" % (i, g["id"], g["need"]), "   ![%s](shoot/%s-swipe.jpg)" % (g["id"], g["id"]), ""]
    (ST.BRIEFS / n / "SHOOT-LIST.md").write_text("\n".join(lines))


if __name__ == "__main__":
    a = sys.argv[1:] or sys.exit(__doc__)
    r = judge(a[0])
    for s in r["shots"]:
        print("%-8s %-9s %s" % (s["id"], s["verdict"], (s.get("why") or "")[:100]))
    print(r["counts"])
    if "--fill" in a:
        only = [x for x in a[1:] if not x.startswith("--")]
        for g in fill(a[0], only or None):
            print(g["route"], g["id"], g["need"][:90])
