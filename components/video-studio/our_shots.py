"""Our shots: a real-footage production's shot list, made from OUR script, never from the swipe.

  python3 our_shots.py <production>      writes briefs/<production>/shot-list.json and SHOT-LIST.md

Owner, 20 Nov 2026: the swipe is baseline inspiration and structure for the writing only; once the script is ours,
production makes our own work from our words. So a Real or AI + Real production gets one shot per spoken beat of each
scene's line (a sentence, or a long sentence's clauses, about 4 to 14 words), in script order, each holding its share
of the scene's read by its words. What each shot shows is decided by what is said over it (shot_fill.py said_visuals);
nothing here copies, names or times a swipe shot. A scene with no spoken line (an end card) keeps the brief's own shots.
Same file shape as swipe_shots.py, so the cut (swipe_cut.py), the picks and the checks read it unchanged.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

MIN_WORDS, MAX_WORDS = 4, 14


def beats(line):
    """A scene's line cut into spoken beats: sentences, long ones cut again at commas, dashes and ellipses; a scrap
    under MIN_WORDS joins its neighbour."""
    parts = []
    for sent in re.split(r"(?<=[.!?])\s+", str(line or "").strip()):
        words = sent.split()
        if len(words) <= MAX_WORDS:
            parts.append(sent)
            continue
        cur = []
        for piece in re.split(r"(?<=[,;:])\s+|\s+(?:—|–|-{2})\s+|(?<=\.\.\.)\s*", sent):
            if not piece:
                continue
            if cur and len(" ".join(cur + [piece]).split()) > MAX_WORDS:
                parts.append(" ".join(cur))
                cur = []
            cur.append(piece)
        if cur:
            parts.append(" ".join(cur))
    out = []
    for p in (x.strip() for x in parts if x.strip()):
        if out and (len(p.split()) < MIN_WORDS or len(out[-1].split()) < MIN_WORDS):
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return out


def build(n):
    import seed_from_brief as SB
    brief = json.load(open(ST.BRIEFS / n / "brief.json"))
    doc = SB.brief_json(brief.get("run") or brief["brief"])
    scenes = {sc["id"]: sc for sc in doc.get("scenes") or []}
    rows = []
    for sid in brief.get("order") or []:
        sc = scenes.get(sid) or {}
        line = sc.get("voice") or " ".join(l.get("say", "") for l in sc.get("script") or [])
        bs = beats(line)
        if bs:
            total = sum(len(b.split()) for b in bs) or 1
            for i, b in enumerate(bs, 1):
                rows.append({"scene": sid, "id": "%s.%d" % (sid, i), "phrase": b, "shows": b, "status": "ours",
                             "share": round(len(b.split()) / total, 4), "picture": "present", "lips": "off"})
        else:                                   # no spoken line (an end card): the brief's own shots, as written
            own = sc.get("shots") or [{}]
            for i, sh in enumerate(own, 1):
                rows.append({"scene": sid, "id": sh.get("id") or "%s.%d" % (sid, i), "phrase": "",
                             "shows": sh.get("action") or sh.get("picture") or sc.get("happens") or "",
                             "status": "ours", "share": round(1 / len(own), 4), "swipe_seconds": 2.5,
                             "picture": "present", "lips": "off"})
    return {"production": n, "run": brief.get("run") or brief["brief"],
            "note": "Our shots (our_shots.py): one shot per spoken beat of our script; the swipe is not used in production.",
            "shots": rows, "dropped_by_brief": [], "owner_overrides": {}}


def main(n):
    sl = build(n)
    bd = ST.BRIEFS / n
    bj = json.load(open(bd / "brief.json"))      # our shots carry words, not pictures: the cut judges each clip on
    if not (bj.get("shot_fill") or {}).get("shows_required"):   # what its pick shows for the line (swipe_cut)
        bj.setdefault("shot_fill", {})["shows_required"] = True
        (bd / "brief.json").write_text(json.dumps(bj, indent=1, ensure_ascii=False))
    (bd / "shot-list.json").write_text(json.dumps(sl, indent=1, ensure_ascii=False))
    md = ["# Shot list: %s" % n, "", sl["note"], "", "| Shot | Words | Share |", "|---|---|---|"]
    md += ["| %s | %s | %.2f |" % (r["id"], (r["phrase"] or r["shows"])[:120], r["share"]) for r in sl["shots"]]
    (bd / "SHOT-LIST.md").write_text("\n".join(md) + "\n")
    print("%d shots across %d scenes, from our script" % (len(sl["shots"]), len({r["scene"] for r in sl["shots"]})))


if __name__ == "__main__":
    main(sys.argv[1])
