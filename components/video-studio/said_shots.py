#!/usr/bin/env python3
"""Said shots: everything the narration names, matched to footage we own (the asset index).

  python3 said_shots.py <production> [--demo /female/white/55-64/]    writes briefs/<p>/said-shots.json and SAID-SHOTS.md
  python3 said_shots.py <production> --place                           and places every ADD in picks.json (no hand step)

Rule (owner, 10 Nov 2026: "if we have the relevant asset for that B-roll, then we use that. That needs to be baked into
our system"): every concrete thing a line of narration names (an offer item, the product, an ingredient, a body part, an
action) gets a shot that shows it, on its words, when the index holds footage of it.

For each scene's narration (voice/reads.json, else the takes' voice lines) it splits the line into clauses, asks the
asset index for footage that shows each clause, and keeps the best clip that:
  - is a file on this machine (brief.json shot_fill.library_roots);
  - is not a finished or posted edit, intake, archive, generated or old-packaging clip (burned-in text, wrong pack);
  - has a person from the edit's demographic (--demo, else shot_fill.hands_like / person) or no creator at all
    (brand b-roll, product footage: fits any demographic).
It then says whether the cut already shows that clip (picks.json). A named thing with a clip and no shot on screen is
the one to add (picks.json "add", the owner's words in "why"). Without --place it lists and changes nothing.

--place (owner, 10 Nov: "go get the limit cleared, no limits"): each ADD goes on its own words. The clause's span of the
scene comes from the read's word times (voice/continuous/<scene>.words.json), else from its word count. The added shot
that overlaps that span most takes the clip (a swipe-copied shot is never replaced, so the swipe check holds); a scene
with no added shot there gets a new one sized to the clause. A clip already playing twice in the ad is passed over for
the next one that shows the thing. Brand-agnostic.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402
import shot_fill as SF  # noqa: E402

BAR = 0.2            # low on purpose: shows_it() is the real test (the clip must show the named thing)
PER = 3000
# never: finished or posted edits (burned-in text), intake, archive, generated folders, old packaging
SKIP_PATH = ("outdated-packaging", "superseded", "/archive/", "/intake/", "ready-posts", "/ig_", "_has-text",
             "fullritual_review", "/ai-elements/", "/generated/")
STOP = set("""a an the and or but so to of in on at by for with from is are be been it its this that these those you your
yours we our us they them their she her he his i me my mine just gonna going do does did don't dont can will would
which what when where who how here there then than if not no yes all any some more most very too also into out up
over off about because tap button below right now need hurry miss it's that's let's here's
discount discounts free first second third final deal deals sale unlock triple necessary code ends end today tonight
black friday cyber november december thirtieth sixty-day money back every penny week twice consistently get buy one two
three gonna fast-tracked use using""".split())
# the same thing said another way in the index's descriptions (plain English, no brand words)
SAME = {"pouch": ("pouch", "bag"), "bag": ("bag", "pouch"), "shipping": ("shipping", "box", "package", "parcel", "mailer"),
        "box": ("box", "package"), "tube": ("tube",), "tubes": ("tube",), "spots": ("spot", "spots", "marks"),
        "skin": ("skin",), "rinse": ("rinse", "rinses", "water"), "scrub": ("scrub",)}
PERSON = ("woman", "man ", "person", "she ", "he ", "her ", "his ", "people", "girl", "lady", "hand", "finger", "arm", "leg",
          "face", "smiles")


def clauses(text):
    parts = re.split(r"[,.;:!?…]+|\s+and\s+|\s+but\s+", text or "")
    return [p.strip() for p in parts if p.strip()]


def named(clause):
    """The words of a clause that name a thing (offer and filler words out); a clause naming nothing returns ''."""
    words = [w for w in re.findall(r"[A-Za-z$'-]+", clause.lower()) if w not in STOP and len(w) > 2]
    return " ".join(words)


def objects(words):
    """The words that name a known object (SAME's keys) when the line has any; else every named word."""
    ws = words.split()
    return [w for w in ws if w in SAME] or ws


def shows_it(words, shows):
    """True when what the clip shows names the thing the line names (or the same thing said another way)."""
    words = " ".join(objects(words))
    s = " " + shows.lower() + " "
    return any(any(re.search(r"\b%s" % re.escape(v), s) for v in SAME.get(w, (w.rstrip("s"),))) for w in words.split())


def subject_at(words, shows):
    """Where in the clip's description the named thing first appears (word index); 99 when it doesn't."""
    toks = re.findall(r"[a-z]+", shows.lower())
    vs = {v for w in objects(words) for v in SAME.get(w, (w.rstrip("s"),))}
    return next((i for i, t in enumerate(toks) if any(t.startswith(v) for v in vs)), 99)


def _sung_lines(brief):
    """{scene: its sung lines joined} when the production's writing brief is sung (its scenes carry `lyrics`), else {}."""
    try:
        import song_view as SV
        sb = SV.brief_of(Path(ST.WRITING) / str(brief.get("brief") or "")) or {}
    except Exception:  # noqa: BLE001 — no writing brief here: the takes' voice lines, as before
        return {}
    if not sb.get("song"):
        return {}
    return {sc.get("id"): " ".join(sc.get("lyrics") or []) for sc in sb.get("scenes") or [] if sc.get("lyrics")}


def lines_of(n, brief):
    rp = ST.BRIEFS / n / "voice" / "reads.json"
    if rp.is_file():
        reads = json.load(open(rp))["lines"]
        return {s: reads[s]["text"] for s in brief["order"] if s in reads}
    out = {}
    sung = _sung_lines(brief)
    if sung:                                # a sung ad: the song is the narration, each scene's lyrics are its words
        return {s: sung.get(s, "") for s in brief["order"]}
    for s in brief["order"]:
        wf = json.load(open(ST.BRIEFS / n / "scenes" / s / (brief["picks"][s] + ".json")))
        out[s] = " ".join(st.get("prompt") or "" for st in wf.get("steps") or [] if st["tool"] in ("voice.ai", "voice.read"))
    return out


def on_screen(picks, path, a, b):
    """The shot id in picks.json that already plays this clip over [a, b], if any."""
    keys = {k for k, v in (picks.get("sources") or {}).items() if v == path}
    rows = [(k, v) for k, v in (picks.get("shots") or {}).items()]
    rows += [(x["id"], x) for xs in (picks.get("add") or {}).values() for x in xs]
    for sid, v in rows:
        if v.get("source") in keys and a - 4 <= float(v.get("in") or 0) <= b + 1:
            return sid
    return None


def match(n, demo=None):
    brief = json.load(open(ST.BRIEFS / n / "brief.json"))
    cfg = brief.get("shot_fill") or {}
    pk = ST.BRIEFS / n / "picks.json"
    picks = json.load(open(pk)) if pk.is_file() else {}
    demos = [demo] if demo else (cfg.get("hands_like") or ([cfg["person"]] if cfg.get("person") else []))
    S = SF._search_mod()
    rows = []
    for s, text in lines_of(n, brief).items():
        for cl in clauses(text):
            q = named(cl)
            if not q:
                continue
            cands = []
            ask = " ".join(dict.fromkeys(v for w in objects(q) for v in SAME.get(w, (w,))))
            for h in S.search(ask, brand=cfg.get("brand") or "", per=PER):
                p = h.get("shared_path") or ""
                if h["score"] < BAR or any(x in p for x in SKIP_PATH):
                    continue
                if not shows_it(q, h.get("shows") or ""):
                    continue
                if "content-creators" in p:
                    if demos and not any(d in p for d in demos):
                        continue
                elif any(w in " " + (h.get("shows") or "").lower() for w in PERSON):
                    continue             # brand footage with someone in it is not the ad's avatar
                f = SF.local_file(h, cfg.get("library_roots") or [])
                if not f:
                    continue
                cands.append(dict(file=f, clip=p.split("/")[-1], creator=("content-creators" in p and p.split("content-creators/")[-1].rsplit("/", 2)[0]) or "brand footage, no creator",
                                  **{"in": h["in"], "out": h["out"], "shows": h.get("shows") or "", "score": round(h["score"], 2)}))
                if len(cands) == 12:
                    break
            # the thing as the shot's subject first: named early in what the clip shows beats named in passing
            cands.sort(key=lambda c: (subject_at(q, c["shows"]) // 6, -c["score"]))
            cands = cands[:5]
            # on screen when the cut already plays any of the clips that show it
            hit = next(((c, on_screen(picks, c["file"], float(c["in"]), float(c["out"]))) for c in cands
                        if on_screen(picks, c["file"], float(c["in"]), float(c["out"]))), None)
            best, shown = (hit if hit else ((cands[0] if cands else None), None))
            rows.append({"scene": s, "words": cl, "named": q, "clip": best, "on_screen": shown, "others": cands[1:],
                         "status": "no footage" if not best else ("on screen" if shown else "ADD")})
    out = {"production": n, "demographic": demos or "any", "rows": rows}
    json.dump(out, open(ST.BRIEFS / n / "said-shots.json", "w"), indent=1, ensure_ascii=False)
    open(ST.BRIEFS / n / "SAID-SHOTS.md", "w").write(markdown(out))
    return out


def markdown(d):
    L = ["# What the voice names, matched to our footage · %s" % d["production"], "",
         "Made by `said_shots.py`. Demographic: %s. ADD = we own footage of it and the cut doesn't show it yet." %
         (", ".join(d["demographic"]) if isinstance(d["demographic"], list) else d["demographic"]), "",
         "| Scene | Words | Status | Best clip | At | Shows | Score |", "|---|---|---|---|---|---|---|"]
    for r in d["rows"]:
        c = r["clip"] or {}
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            r["scene"], r["words"], r["status"] + (" (" + r["on_screen"] + ")" if r["on_screen"] else ""),
            (c.get("creator", "") + " · " + c.get("clip", "")) if c else "—",
            ("%s–%s" % (c["in"], c["out"])) if c else "", (c.get("shows") or "")[:90], c.get("score", "")))
    return "\n".join(L) + "\n"


def words_span(n, s, clause, text):
    """(f0, f1): where the clause sits in the scene, as fractions of its read."""
    toks = lambda t: [re.sub(r"[^a-z0-9$]", "", w.lower()) for w in t.split()]
    want = [t for t in toks(clause) if t]
    wf = ST.BRIEFS / n / "voice" / "continuous" / (s + ".words.json")
    if wf.is_file():
        d = json.load(open(wf)); W = d.get("words", d) if isinstance(d, dict) else d
        got = [re.sub(r"[^a-z0-9$]", "", (w.get("w") or w.get("text") or "").lower()) for w in W]
        for i in range(len(got) - len(want) + 1):
            if want and got[i:i + len(want)] == want:
                end = max(w["end"] for w in W) or 1.0
                return W[i]["start"] / end, W[i + len(want) - 1]["end"] / end
    allw = [t for t in toks(text) if t]
    for i in range(len(allw) - len(want) + 1):
        if want and allw[i:i + len(want)] == want:
            return i / len(allw), (i + len(want)) / len(allw)
    return None


def place(n, d):
    """Every ADD row of match() goes into picks.json on its own words. Returns what was placed."""
    import swipe_cut as SC
    brief, picks, scenes = SC.plan(n)
    picks.setdefault("add", {}); picks.setdefault("sources", {})
    text = lines_of(n, brief)

    def uses(path):
        keys = {k for k, v in picks["sources"].items() if v == path}
        rows = list(picks.get("shots", {}).values()) + [x for xs in picks["add"].values() for x in xs]
        return sum(1 for v in rows if v.get("source") in keys)
    done = []
    for r in d["rows"]:
        if r["status"] != "ADD":
            continue
        def used_at(path, cin):           # the same moment of a clip never plays twice in one ad (no_repeat, 20 Nov)
            keys = {k for k, v in picks["sources"].items() if v == path}
            rows = list(picks.get("shots", {}).values()) + [x for xs in picks["add"].values() for x in xs]
            return any(v.get("source") in keys and abs(float(v.get("in") or 0) - cin) < 6 for v in rows)
        clip = next((c for c in [r["clip"]] + r.get("others", [])
                     if c and uses(c["file"]) < 2 and not used_at(c["file"], float(c["in"]))), None)
        span = words_span(n, r["scene"], r["words"], text.get(r["scene"], ""))
        if not clip or not span or r["scene"] not in scenes:
            continue
        f0, f1 = span
        rows, at, iv = scenes[r["scene"]], 0.0, []
        for row in rows:
            iv.append((row, at, at + row["share"]))
            at += row["share"]
        key = "said-" + re.sub(r"[^a-z0-9]+", "-", clip["clip"].lower())[:40]
        picks["sources"][key] = clip["file"]
        why = ('the narration names "%s" and the asset index holds it (said_shots.py --place; owner, 10 Nov: "if we have '
               'the relevant asset for that B-roll, then we use that")' % r["named"])
        note = "%s (on '%s')" % (clip["shows"][:110], r["words"])
        adds = picks["add"].setdefault(r["scene"], [])
        mine = [(row, max(0.0, min(b, f1) - max(a, f0))) for row, a, b in iv if any(x["id"] == row["id"] for x in adds)]
        mine = [m for m in mine if m[1] > 0]
        if mine:
            row = max(mine, key=lambda m: m[1])[0]
            x = next(x for x in adds if x["id"] == row["id"])
            x.update({"source": key, "in": float(clip["in"]), "note": note, "why": why, "said": r["named"]})
            x.pop("params", None)
            done.append((r["scene"], r["words"], clip["clip"], "replaced " + row["id"]))
        else:
            host = next((row for row, a, b in iv if a <= f0 < b), iv[-1][0])
            hi = [row["id"] for row, _, _ in iv].index(host["id"])
            a0 = iv[hi][1]
            after = host["id"] if f0 - a0 > 0.5 * host["share"] or hi == 0 else iv[hi - 1][0]["id"]
            nid = "%s.said%d" % (r["scene"], len([x for x in adds if x.get("said")]) + 1)
            adds.append({"after": after, "id": nid, "share": round(min(0.45, max(0.12, f1 - f0)), 3), "source": key,
                         "in": float(clip["in"]), "note": note, "why": why, "said": r["named"]})
            done.append((r["scene"], r["words"], clip["clip"], "added " + nid))
    if done:                              # an untouched picks.json keeps its time, so the cut isn't redone for nothing
        json.dump(picks, open(ST.BRIEFS / n / "picks.json", "w"), indent=1, ensure_ascii=False)
    return done


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("production")
    ap.add_argument("--demo", help="the edit's demographic folder path, e.g. /female/white/55-64/")
    ap.add_argument("--place", action="store_true", help="put every ADD into picks.json on its own words")
    a = ap.parse_args()
    d = match(a.production, a.demo)
    if a.place:
        for sc, w, c, how in place(a.production, d):
            print("placed  %s  '%s'  %s  (%s)" % (sc, w, c, how))
        d = match(a.production, a.demo)       # read back: what is on screen now
    add = [r for r in d["rows"] if r["status"] == "ADD"]
    print("%d named things · %d on screen · %d to add from our footage · %d with no footage" % (
        len(d["rows"]), sum(r["status"] == "on screen" for r in d["rows"]), len(add),
        sum(r["status"] == "no footage" for r in d["rows"])))
