"""Swipe shots: the production's shot list, made from the swipe, never by hand.

  python3 swipe_shots.py <production>            writes briefs/<production>/shot-list.json and SHOT-LIST.md
  python3 swipe_shots.py <production> --check    prints what the brief dropped or left unmatched; exit 1 if anything

Swipes are the baseline (owner, 10 Nov 2026: "unless directly otherwise we always leverage swipes"). Every scene's
`source` names the swipe shots it copies (K05–K10); every one of them becomes one shot in our cut, in the swipe's
order, at the swipe's share of the scene's time. Nothing is dropped and no shot is invented for pace:
  - a swipe shot the brief copies (a brief shot with "copies": K) takes that brief shot's picture;
  - a swipe shot the brief dropped is added back, its picture the swipe shot's own action from the frame map, marked
    "added from the swipe" so the storyboard and the Studio show it;
  - a script-backed scene (source "none") keeps the brief's own shots.
Each row carries the swipe's length and its share of the scene (`share`). The cut lays a scene's shots over that
scene's read by share: our length = share x our scene's seconds, so the swipe's run of quick and held shots survives
whatever the read's length. With briefs/<production>/studio-build/cutsheet.json present it also writes each shot's
`at` and `seconds` in our ad.

A brief written before its swipe had a frame map names swipe times instead ("record shot 2 (0:01.8–0:03): ..."): the
scene then copies the frame-map shots that span covers, each at the scene's slice of it (`swipe_span`), and its brief
shots copy the swipe shot under them in their own order; the source's words stand in for an unmapped shot's action.

A scene the writing held (no `source` in its brief) takes its swipe shots from brief.json "scene_sources": {"S1": "K01"}.
An owner's call for one shot ("don't copy K07") goes in brief.json "swipe_overrides": {"K07": "why"}; that shot is
then left out and listed as his call. shot_fill.py reads these rows (its "production shot list").
Brand-agnostic: reads only the production, its writing run's brief and the run's frame map.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402


def k_range(source):
    m = re.match(r"\s*K(\d{2,3})(?:\s*[–-]\s*K(\d{2,3}))?", str(source or ""))
    if not m:
        return []
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    return ["K%02d" % i for i in range(a, b + 1)]


def t_span(source):
    """A scene source written in swipe times ("0:03–0:11") instead of K-ids: a brief written before its frame map."""
    m = re.search(r"(\d+):(\d+(?:\.\d+)?)\s*[–-]\s*(\d+):(\d+(?:\.\d+)?)", str(source or ""))
    return (int(m.group(1)) * 60 + float(m.group(2)), int(m.group(3)) * 60 + float(m.group(4))) if m else None


def by_time(sc, fm):
    """A time-sourced scene: the frame-map shots its span covers, each cut to the scene's slice of it (k, from, to);
    which brief shot copies each (the brief's shots spread over the span in their own order, each copying the swipe
    shot under its middle); and the source's own words on what the span shows."""
    a, b = t_span(sc.get("source"))
    ks = [(k, max(a, s["start"]), min(b, s["end"])) for k, s in fm.items() if min(b, s["end"]) - max(a, s["start"]) > 0.1]
    mine, sh = {}, sc.get("shots") or []
    for i, x in enumerate(sh):
        t = a + (b - a) * (i + 0.5) / len(sh)
        k = next((k for k, s0, s1 in ks if s0 <= t < s1), ks[-1][0] if ks else None)
        if k:
            mine.setdefault(k, []).append(x)
    m = re.search(r"\)\s*:\s*(.+)$", str(sc.get("source") or ""))
    return ks, mine, (m.group(1).strip() if m else "")


def shot_shows(sh):
    """What a brief shot shows: its action and picture, or (briefs that write shots as gestures) its angle, gestures and
    end frame."""
    said = [sh.get("action"), sh.get("picture")]
    if not any(said):
        acts = [g for g in sh.get("gestures") or [] if not str(g).lower().startswith("n/a")]
        said = ["; ".join(acts) or sh.get("ends_on")]      # what happens, in few words: the library is searched with it
    return ". ".join(str(x) for x in said if x)


def framemap(run):
    import seed_from_brief as SB
    p = SB.WORK / run / "framemap" / "framemap.json"
    return {s["id"]: s for s in json.loads(p.read_text()).get("shots", [])} if p.is_file() else {}


def swipe_does(shot):
    mp = shot.get("map") or {}
    acts = "; ".join(x.get("does", "") for x in (mp.get("moments") or [])[:3] if x.get("does"))
    cam = mp.get("camera") or {}
    camera = ", ".join(str(cam[x]) for x in ("distance", "height", "move") if cam.get(x))
    text = " / ".join(o.get("text", "") for o in (mp.get("on_screen") or []) if o.get("text"))
    return acts, camera, text


def build(n):
    import seed_from_brief as SB
    brief = json.load(open(ST.BRIEFS / n / "brief.json"))
    run = brief.get("run") or brief["brief"]     # "run": the writing run, when the brief key is not its name
    doc = SB.brief_json(run)
    fm = framemap(run)
    skip = brief.get("swipe_overrides") or {}
    spans = {}
    sc_cut = ST.BRIEFS / n / "song-cut.json"      # a sung ad: every scene is laid on its time on the song (Cut to the song)
    if sc_cut.is_file():
        for sid_, t_ in (json.load(open(sc_cut)).get("scenes") or {}).items():
            if t_ and t_.get("seconds"):
                spans[sid_] = (t_["start"], t_["seconds"])
    cs = ST.BRIEFS / n / "studio-build" / "cutsheet.json"
    if cs.is_file() and not spans:
        for p in json.load(open(cs)).get("picture") or []:
            if p.get("scene"):
                spans[p["scene"]] = (p["start"], p["duration"])
    rows, dropped, owner = [], [], []
    for sc in doc.get("scenes") or []:
        sid = sc["id"]
        if sid not in brief.get("order", [sid]):
            continue
        if not sc.get("source") and (brief.get("scene_sources") or {}).get(sid):
            sc = dict(sc, source=brief["scene_sources"][sid])     # a scene the writing held: its swipe shot named by the production
        ks = k_range(sc.get("source"))
        if sc.get("joined_scenes"):          # a joined scene (same section tag, 16 Nov): every old scene's swipe shots, in order
            ks = list(dict.fromkeys(k for o in sc["joined_scenes"] for k in k_range(o.get("source")))) or ks
        by_k, spans_k, said = {}, {}, ""
        for sh in sc.get("shots") or []:
            if sh.get("copies"):
                by_k.setdefault(sh["copies"], []).append(sh)
        if not ks and fm and t_span(sc.get("source")):     # a brief written before the frame map names swipe times
            tk, by_k, said = by_time(sc, fm)
            ks = [k for k, _, _ in tk]
            spans_k = {k: (s0, s1) for k, s0, s1 in tk}
        scene_rows = []
        if ks and fm:
            for k in ks:
                if k in skip:
                    owner.append({"scene": sid, "k": k, "why": skip[k]})
                    continue
                s = fm.get(k)
                if not s:
                    continue
                acts, camera, text = swipe_does(s)
                acts = acts or said
                mine = by_k.get(k) or []
                picture = shot_shows(mine[0]) if mine else acts
                if not mine:
                    dropped.append({"scene": sid, "k": k})
                s0, s1 = spans_k.get(k, (s["start"], s["end"]))
                scene_rows.append({"scene": sid, "id": mine[0]["id"] if mine else "%s.%s" % (sid, k), "copies": k,
                                   "swipe_span": [round(s0, 3), round(s1, 3)],
                                   "swipe_seconds": round(s1 - s0, 2), "swipe_does": acts,
                                   "swipe_camera": camera, "swipe_text": text, "shows": picture,
                                   "status": "copied" if mine else "added from the swipe",
                                   "phrase": " / ".join(l.get("say", "") for l in (mine[0].get("lines") or [])) if mine else ""})
        else:
            for sh in sc.get("shots") or []:
                scene_rows.append({"scene": sid, "id": sh.get("id"), "copies": "", "swipe_seconds": None,
                                   "shows": shot_shows(sh),
                                   "status": "script-backed", "phrase": " / ".join(l.get("say", "") for l in sh.get("lines") or [])})
        total = sum(r["swipe_seconds"] or 0 for r in scene_rows)
        for r in scene_rows:
            r["share"] = round(r["swipe_seconds"] / total, 4) if total and r["swipe_seconds"] else round(1 / len(scene_rows), 4)
        if sid in spans:
            at, dur = spans[sid]
            for r in scene_rows:
                r["at"], r["seconds"] = round(at, 3), round(r["share"] * dur, 3)
                at += r["seconds"]
        rows += scene_rows
    import lips as LP
    pics = LP.labels(ST.WRITING / run)          # what each swipe shot's picture does with the voice (BRIEF-SPEC rule 9)
    for r in rows:
        p = pics.get(r.get("copies") or "")
        if p:
            r["picture"], r["lips"] = p["picture"], p["lips"]
    return {"production": n, "run": run,
            "note": "One row per swipe shot each scene copies, in the swipe's order (swipe_shots.py). share = the swipe "
                    "shot's part of its scene; our length = share x our scene's seconds. Never written by hand.",
            "shots": rows, "dropped_by_brief": dropped, "owner_overrides": owner}


def markdown(d):
    out = ["# Shot list, from the swipe · %s" % d["production"], "",
           "Made by `swipe_shots.py` from the brief and the swipe's frame map. One row per swipe shot; lengths are the "
           "swipe's share of each scene.", "",
           "| Scene | Shot | Copies | Picture | Swipe s | Share | Ours at · s | Status | Shows |", "|---|---|---|---|---|---|---|---|---|"]
    for r in d["shots"]:
        ours = "%.2f · %.2f" % (r["at"], r["seconds"]) if "at" in r else ""
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (r["scene"], r["id"], r["copies"] or "—", r.get("picture") or "—",
                   r["swipe_seconds"] if r["swipe_seconds"] is not None else "—", r["share"], ours, r["status"],
                   (r["shows"] or "")[:90].replace("|", "/")))
    if d["dropped_by_brief"]:
        out += ["", "Added back (the brief dropped them): " + ", ".join(x["k"] for x in d["dropped_by_brief"])]
    if d["owner_overrides"]:
        out += ["", "Left out on the owner's call: " + ", ".join("%s (%s)" % (x["k"], x["why"]) for x in d["owner_overrides"])]
    return "\n".join(out) + "\n"


def main():
    n = sys.argv[1]
    d = build(n)
    if "--check" in sys.argv:
        for x in d["dropped_by_brief"]:      # V57 (owner, 16 Nov): a note, never a fail — the shots are ours
            print("%s: noted — the brief leaves out swipe shot %s" % (x["scene"], x["k"]))
        sys.exit(0)
    (ST.BRIEFS / n / "shot-list.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))
    (ST.BRIEFS / n / "SHOT-LIST.md").write_text(markdown(d))
    print(markdown(d))


if __name__ == "__main__":
    main()
