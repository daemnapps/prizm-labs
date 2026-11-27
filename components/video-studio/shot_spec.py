"""THE SHOT SPEC — a missing swipe shot is defined by the team's own per-shot chain before anything is made (2026-11-10).

The owner, after four filled shots came out as a forearm being rubbed with a drawn face brush: a missing shot needs a
mini teardown, a replication spec and an injection for that one shot, from the chain that already exists, and that has
to be the only way a shot gets made. So a shot the Studio has no real clip for goes through, in order:

  1. route        components/video-production SHOT-ROUTES.md (`machine/shot_route.py`): real footage we own first; a shot
                  whose action needs the product is never generated (the product is never drawn), it goes to the shoot list
  2. use          `machine/shot_use.py`: the swipe's action → ours, its product's use → our product's use from the kit,
                  the body part our words name
  3. teardown     the team's per-shot job, exactly as the Prompt Bench runs it (`prompt_bench._open_job`): the swipe frame
                  opened as a picture run, picture teardown stages 1, 1k, 2 (replication spec), 2b (elements), then
                  `shot_swaps.py` (the injection, with our action from step 2) and `scene_breakdown.py` (camera, eyes,
                  handling, atmosphere)
  4. words        the still's words from the swaps and what stays; the clip's words from our action and the breakdown's
                  own clip lines (`scene_breakdown.prompt_lines`)

The spec lands in briefs/<idea>/shot-spec/<shot>.json and gen_ref.py makes nothing for a shot without one (`require`).
The production run the team's job reads is a view written from the Studio's own files under
runs/video-production/<brand>/studio-<idea>/; it holds no work of its own.

    python3 shot_spec.py <idea> <shot id> [<shot id> ...] [--person <cast slug>] [--dry-run]
    python3 shot_spec.py <idea> --show <shot id>

THE OWNER'S DIRECTION FIRST (2026-11-11). The swipe is inspiration; a shot follows our words and brand. When the owner
has given a direction for a shot (briefs/<idea>/directions.json, {"shots": {"<shot id>": {"does": "...", "produce":
true, "said": "<his words>", "product_in_shot": false}}}), step 2 takes our action from it instead of translating the
swipe's, and `"produce": true` routes the shot to be made even when the cut plays real footage there now. A shot with no
direction keeps the swipe-first behaviour. Switch: shot_spec.json "direction_first" ({"on": false} puts every lane
back; "lanes": {"<brand>": false} one brand); SHOT_DIRECTION_OFF=all or a comma list of brands on one machine.

Brand-agnostic: brand, product, swipe and words come from the idea's brief, its writing run and the product kit.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

VP = ST.part("video-production") / "machine"
REQUIRED = ("route", "use", "teardown", "replication", "elements", "swaps", "breakdown", "still_words", "clip_words")


def _mod(name, path):
    sp = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(sp)
    sys.path.insert(0, str(Path(path).parent))
    sp.loader.exec_module(m)
    return m


def _json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default if default is not None else {}


def spec_path(n, sid):
    return ST.BRIEFS / n / "shot-spec" / (sid + ".json")


SWITCH = HERE / "shot_spec.json"


def direction_on(brand):
    """Is the owner's-direction-first step on for this brand's lane (see the docstring's switch)?"""
    off = [x.strip() for x in os.environ.get("SHOT_DIRECTION_OFF", "").split(",") if x.strip()]
    if "all" in off or (brand and brand in off):
        return False
    s = _json(SWITCH).get("direction_first") or {}
    if s.get("on") is False:
        return False
    return (s.get("lanes") or {}).get(brand, True) is not False


def direction_of(n, sid, brand):
    """The owner's direction for this shot, or None (none given, or the brand's lane switched off)."""
    if not direction_on(brand):
        return None
    d = (_json(ST.BRIEFS / n / "directions.json").get("shots") or {}).get(sid)
    return d if d and str(d.get("does") or "").strip() else None


def direction_words(d):
    """The clip's words for a directed shot: his action, then his camera note when he gave one."""
    return (d["does"].strip().rstrip(".") + ". " + str(d.get("camera") or "").strip()).strip()


def use_from_direction(d, row):
    """Step 2 from the owner's direction: our action is his, nothing is translated from the swipe."""
    return {"our_does": d["does"].strip(), "body_part": d.get("body_part"), "product_in_shot": bool(d.get("product_in_shot")),
            "kept": [f"the swipe's timing ({row.get('seconds')} s) and camera ({row.get('swipe_camera') or 'as filmed'}), as reference"],
            "changed": ["the action: the owner's direction, not the swipe's"], "problems": [],
            "from": "direction", "direction": d}


def require(n, sid):
    """The spec gen_ref may make this shot from, or SystemExit naming what is missing. A shot whose action needs the
    product, or that we own footage for, is never generated."""
    p = spec_path(n, sid)
    s = _json(p)
    if not s:
        raise SystemExit(f"{sid}: no shot spec. A missing shot is defined first: shot_spec.py {n} {sid}")
    gaps = [k for k in REQUIRED if not s.get(k)]
    if gaps:
        raise SystemExit(f"{sid}: the shot spec is not complete ({', '.join(gaps)}): shot_spec.py {n} {sid}")
    if (s.get("use") or {}).get("problems"):
        raise SystemExit(f"{sid}: the shot spec has problems: " + "; ".join(s["use"]["problems"]))
    if s["route"]["route"] != "AI":
        raise SystemExit(f"{sid}: route {s['route']['route']} ({s['route']['why']}): this shot is not generated")
    return s


# ---- the idea's own files ---------------------------------------------------------------------------------------------
def writing_of(n):
    b = _json(ST.BRIEFS / n / "brief.json")
    w = ST.WRITING / (b.get("run") or b["brief"])
    return b, w, _json(w / "run.json")


def production_brief(w):
    t = (w / "stages" / "5-brief.md").read_text()
    return json.loads(re.findall(r"```json\s*\n(.*?)\n```", t, re.S)[-1])


def row_of(n, sid):
    rows = (_json(ST.BRIEFS / n / "shot-list.json").get("shots") or [])
    r = next((x for x in rows if x.get("id") == sid), None)
    if not r:
        raise SystemExit(f"{sid}: not in the idea's shot list")
    return r


def kit_of(brand, product):
    """The product's truth kit: runs/ai-elements/<brand>/products/<slug>/kit.json whose product or aliases name it."""
    want = str(product or "").lower()
    for k in sorted((ST.REPO / "runs" / "ai-elements" / brand / "products").glob("*/kit.json")):
        d = _json(k)
        names = [str(d.get("product") or "").split("/")[-1].lower(), k.parent.name.lower()] + [str(a).lower() for a in d.get("aliases") or []]
        if want in names:
            return k.parent
    raise SystemExit(f"no product kit for {brand}/{product}")


def swipe_shot(n, k):
    fm_dir = _mod("shot_copy_ss", HERE / "shot_copy.py")._framemap(n)
    fm = _json(fm_dir.parent / "framemap.json")
    s = next((x for x in fm.get("shots") or [] if x.get("id") == k), None)
    if not s:
        raise SystemExit(f"swipe shot {k} is not in the frame map")
    return s, fm_dir / s["stills"]["mid"]


def owned(n, sid):
    """Real footage for this shot, or None: a real clip the shot is cut from now (picks.json, any source that is not a
    generated `G-` one), or the one the Studio's footage search matched above its bar (shot-fill.json REAL / CAPTURE)."""
    pick = ((_json(ST.BRIEFS / n / "picks.json").get("shots") or {}).get(sid) or {})
    if pick.get("source") and not str(pick["source"]).startswith("G-"):
        return {"from": "picks", "source": pick["source"], "in": pick.get("in")}
    hit = next((x for x in _json(ST.BRIEFS / n / "shot-fill.json").get("shots") or [] if x.get("id") == sid), {})
    if hit.get("status") in ("REAL", "CAPTURE"):
        return {"from": "shot-fill", "clip": hit.get("clip"), "in": hit.get("in"), "out": hit.get("out"), "shows": hit.get("shows")}
    return None


# ---- the steps -----------------------------------------------------------------------------------------------------------
def route_of(row, use, mine):
    R = _mod("vm_shot_route", VP / "shot_route.py")
    facts = {"id": row["id"], "seconds": row.get("seconds"), "what": use["our_does"], "owned_footage": bool(mine),
             "motion_is_the_point": False, "swipe_shot": row.get("copies"), "clean_single_shot": True,
             "talks_to_camera": False, "needs_product": bool(use["product_in_shot"]), "product_slot_in_swipe": False}
    rt, why, cost = R.route(facts)
    if rt == "AI" and use["product_in_shot"]:      # SHOT-ROUTES: the hero product is never drawn
        rt, why, cost = "SHOOT", "the action needs the real product and we own no footage of it: film it", 0.0
    return {"route": rt, "why": why, "usd": round(cost, 2), "facts": facts, "owned": mine}


def write_view(n, sid, row, use, person, brand, product, b5, wrun, k):
    """The production-run view the team's per-shot job reads: one section per shot, from the Studio's own files."""
    view = ST.REPO / "runs" / "video-production" / brand / ("studio-" + n)
    (view / "brief").mkdir(parents=True, exist_ok=True)
    sb = _json(view / "storyboard.json", {"sections": []})
    who = re.sub(r"[-_\d]+", " ", str(person or "")).strip().upper() or "OUR PERSON"
    sec = {"id": sid, "elements": [f"person · {who}"] if person else [],
           "start_frame": {"subject": use["our_does"], "composition": row.get("swipe_camera") or "",
                           "location": "the swipe's own place", "action_from": "shot_use"},
           "swipe": {"span": [k["start"], k["end"]], "shots": [{"id": row.get("copies")}]},
           "frames": [{"what": "start frame", "from": sid}], "scenes": []}
    sb["sections"] = [x for x in sb["sections"] if x.get("id") != sid] + [sec]
    (view / "storyboard.json").write_text(json.dumps(sb, indent=1))
    doc = {"piece": b5.get("piece") or {}, "cast": [{"id": who, "bank_id": person, "look": ""}] if person else [],
           "world": [], "props": [], "product_lock": {"product": product}, "scenes": []}
    (view / "brief" / "brief.md").write_text("# The Studio's shot view\n\n```json\n" + json.dumps(doc, indent=1) + "\n```\n")
    (view / "run.json").write_text(json.dumps({"brief_from": str(view / "brief" / "brief.md"), "from_studio": n}, indent=1))
    if not (view / "source.mp4").exists():   # the scene breakdown cuts the swipe's own footage (effects.teardown_of)
        (view / "source.mp4").symlink_to(Path(wrun["video"]) if Path(wrun["video"]).is_absolute() else ST.WRITING.parents[2] / wrun["video"])
    return view


def words_of(swaps, breakdown, use, row):
    """The still's words are the injection (every swap and what stays); the clip's are our action and the breakdown's lines."""
    sl = swaps or {}
    still = ("IMAGE 1 is the swipe frame. Remake it with only these changes. " +
             " ".join(f"Replace {x.get('from')} with {x.get('to')}." for x in sl.get("swaps") or []) +
             " Keep " + "; ".join(sl.get("stays") or []) + ".")
    SBK = _mod("vm_sb_lines", VP / "scene_breakdown.py")
    clip = (use["our_does"].rstrip(".") + ". " + SBK.prompt_lines(breakdown or {})).strip()
    return still, clip


def make_spec(n, sid, person=None, dry_run=False):
    # every read in the spec goes through Claude (owner, 10 Nov 2026: Gemini only for swipe teardowns); the team's job
    # runs as child processes, so the setting reaches them too
    os.environ.setdefault("READS_VIA", "claude")
    os.environ.setdefault("VISION_JUDGE_ORDER", "claude,local")
    b, w, wrun = writing_of(n)
    brand, product = wrun.get("brand"), wrun.get("product")
    row = row_of(n, sid)
    k, frame = swipe_shot(n, row["copies"])
    kit = kit_of(brand, product)
    b5 = production_brief(w)
    person = person or Path(str(_json(ST.BRIEFS / n / "shot-fill.json").get("person") or "")).name or None
    plan = {"shot": sid, "swipe_shot": row["copies"], "swipe_frame": str(frame), "kit": str(kit), "person": person,
            "steps": ["route + use (shot_use, shot_route)", "prompt_bench._open_job: image-teardown 1,1k,2,2b → shot_swaps → scene_breakdown",
                      "words from swaps + breakdown"]}
    if dry_run:
        print(json.dumps(plan, indent=1))
        return plan
    d = direction_of(n, sid, brand)
    if d:
        use = use_from_direction(d, row)
    else:
        U = _mod("vm_shot_use", VP / "shot_use.py")
        use = U.translate({"does": row.get("swipe_does"), "camera": row.get("swipe_camera"), "text": row.get("swipe_text")},
                          row.get("phrase") or "", kit, shows=row.get("shows") or "")
    spec = {"schema": "shot-spec/v1", "idea": n, "shot": sid, "made": time.strftime("%Y-%m-%d %H:%M"),
            "swipe": {"shot": row["copies"], "frame": str(frame), "does": row.get("swipe_does"),
                      "camera": row.get("swipe_camera"), "text": row.get("swipe_text"), "seconds": row.get("seconds")},
            "our_line": row.get("phrase"), "use": use}
    # the owner asked for this shot to be produced: the real clip playing there now is what it replaces, not a reason to skip
    spec["route"] = route_of(row, use, None if (d and d.get("produce")) else owned(n, sid))
    out = spec_path(n, sid)
    out.parent.mkdir(exist_ok=True)
    if spec["route"]["route"] != "AI" or use["problems"]:
        out.write_text(json.dumps(spec, indent=1))
        return spec
    view = write_view(n, sid, row, use, person, brand, product, b5, wrun, k)
    PB = _mod("studio_prompt_bench", ST.part("model-inputs") / "prompt_bench.py")
    slug, name = PB._shot_slug(f"{brand}/studio-{n}", sid)
    PB._open_job("shot-spec", brand, product, str(frame), name, slug, str(view), sid)
    pic = _mod("vm_ss_tr", VP / "shot_swaps.py")._teardown_run(ST.REPO, slug, brand)
    outd = pic / "out"

    def first(*pats):
        for p in pats:
            hit = sorted(outd.glob(p))
            if hit:
                return str(hit[0])
        return None
    spec.update(picture_run=str(pic), teardown=first("01-*.md", "1-*.md"), replication=first("02-*.md", "2-*.md"),
                elements=first("02b-*.md", "2b-*.md", "*elements*.json"))
    spec["swaps"] = _json(outd / "swaps.json")
    spec["breakdown"] = _json(view / "scene-breakdown.json").get(sid) or {}
    spec["still_words"], spec["clip_words"] = words_of(spec["swaps"], spec["breakdown"], use, row)
    if use.get("from") == "direction":
        # the owner's direction carries the whole action, place and camera; the swipe's breakdown lines describe the
        # swipe's own room and people, so they stay in the spec as reference and never reach the clip
        spec["clip_words"] = direction_words(use["direction"])
    spec["fingerprint"] = hashlib.sha256(json.dumps({k: spec.get(k) for k in ("use", "swaps", "breakdown")}, sort_keys=True).encode()).hexdigest()[:12]
    out.write_text(json.dumps(spec, indent=1))
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("idea"); ap.add_argument("shots", nargs="*")
    ap.add_argument("--person"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--show")
    a = ap.parse_args(argv)
    if a.show:
        print(json.dumps(_json(spec_path(a.idea, a.show)), indent=1))
        return 0
    bad = 0
    for sid in a.shots:
        s = make_spec(a.idea, sid, a.person, a.dry_run)
        if not a.dry_run:
            r = s["route"]
            print(f"{sid}: {r['route']} · {r['why']} · ours: {s['use']['our_does']}" + (" · PROBLEMS: " + "; ".join(s["use"]["problems"]) if s["use"]["problems"] else ""))
            bad += bool(s["use"]["problems"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
