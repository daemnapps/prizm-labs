#!/usr/bin/env python3
"""Any video brief -> the plan the boards read. The seam, standardised.

    plan_from_brief.py <brief.md> <run folder> --brand <b> [--cast <id>,<id>...]

WHY THIS EXISTS. A brief is written for a person; a board is read by a program.
Until now every machine invented its own answer to that, and they disagreed:

  · the teardown's stage 5 writes   ### Scene 1 · 0:00 – 0:01.8 · 1.8 s
                                    **On screen.** / **You say.** / **How.**
  · scenes.py expects              **Scene 1 · … · TYPE B**
                                    **Happens:** / > **Say:** / **Delivery:**
  · board.py expects               out/plan.json with cast.elements[] carrying
                                    slot·name·id·role·thumb, and cutaways[]
                                    carrying id·over·at·seconds·why·place·
                                    subject·action·look·generate

Three dialects for one document. Every new brief meant a person discovering the
fourth field a board wanted by reading a stack trace — which is exactly how
2026-09-14 went. This file is the one place that knows all three.

BRAND-AGNOSTIC. Nothing here names a brand, a person or a product. The brand is
an argument; the cast is read from that brand's own registry.

THE ANCHOR RULE, enforced here rather than hoped for: every identity a scene's
prose puts in frame gets its element attached to that scene. An identity that
is not attached is an identity the model invents — measured on the Braille set,
where her face was attached to 1 scene of 19 and 19 different women came back.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path

WS = Path(os.environ.get("AI_WORKSPACE", Path.home() / "Projects/ai-workspace"))

# a scene header, in either dialect
HEADS = [
    re.compile(r"^\*\*Scene (\d+) · ([0-9:.]+) – ([0-9:.]+) · ([\d.]+)s · TYPE ([ABC])\*\*", re.M),
    re.compile(r"^### Scene (\d+) · ([0-9:.]+) – ([0-9:.]+) · ([\d.]+) ?s", re.M),
]
FIELD = {
    "happens": [r"\*\*Happens:\*\* (.+?)(?=\n\n|\Z)", r"\*\*On screen\.\*\* (.+?)(?=\n\n|\Z)"],
    "say":     [r"> \*\*Say:\*\* (.+?)(?=\n\n|\Z)", r"\*\*You say\.\*\* (.+?)(?=\n\n|\Z)"],
    "delivery":[r"\*\*Delivery:\*\* (.+?)(?=\n\n|\Z)", r"\*\*How\.\*\* (.+?)(?=\n\n|\Z)"],
    "look":    [r"\*\*Still:\*\* (.+?)(?=\n\n|\Z)", r"^> \*\*Prompt\*\*[^\n]*\n((?:^>.*\n)+)"],
}


def secs(t):
    out = 0.0
    for p in str(t).split(":"):
        out = out * 60 + float(p)
    return out


def one(body, pats):
    for p in pats:
        m = re.search(p, body, re.S | re.M)
        if m:
            return " ".join(re.sub(r"^> ?", "", m.group(1), flags=re.M).split())
    return ""


def scenes_of(text):
    for rx in HEADS:
        heads = list(rx.finditer(text))
        if heads:
            break
    else:
        sys.exit("no scenes found — the brief uses a header shape this file does not know")
    out = []
    for i, m in enumerate(heads):
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        g = m.groups()
        out.append({"n": int(g[0]), "start": secs(g[1]), "seconds": float(g[3]),
                    "type": g[4] if len(g) > 4 else "B",
                    **{k: one(body, p) for k, p in FIELD.items()}})
    return out


def cast_of(brand):
    """The brand's own registry. Nothing is named here."""
    reg = WS / "brands" / brand / "core-avatars" / "casting"
    idx = json.loads((WS / "brands" / brand / "elements" / "index.json").read_text())
    items = idx.get("elements") if isinstance(idx.get("elements"), list) else \
        [v for v in idx.values() if isinstance(v, dict)]
    by_id = {e["element_id"]: e for e in items if e.get("element_id")}
    return by_id


def element_row(eid, by_id, slot, role):
    e = by_id.get(eid, {})
    return {"slot": slot, "name": e.get("name", eid[:8]), "id": eid,
            "role": role, "desc": role, "thumb": f"/element/{eid}"}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("brief"); a.add_argument("run")
    a.add_argument("--brand", required=True)
    a.add_argument("--voice", default="")
    o = a.parse_args()

    text = Path(o.brief).read_text()
    by_id = cast_of(o.brand)

    # the elements the brief itself declares, in its own attach table
    table = dict(re.findall(r"\| (.+?) \| \`<<<([0-9a-f-]{36})>>>\` \|", text))
    declared = {v: k for k, v in table.items()}

    ss = scenes_of(text)
    talking = [s for s in ss if s["type"] == "A"]
    inserts = [s for s in ss if s["type"] != "A"]

    def row(s, over):
        return {"id": f"S{s['n']}", "over": over, "at": round(s["start"], 1),
                "seconds": s["seconds"], "why": s["delivery"],
                "place": s["happens"], "subject": s["happens"],
                "action": s["happens"], "look": s["look"], "generate": {}}

    plan = {
        "brand": o.brand,
        "brief": Path(o.run).name,
        "cast": {
            "name": "", "resolution": "720p",
            "face": "", "hands": "", "room": "", "presenter": "", "who": "", "says": "",
            "also": [], "alternates": {},   # alternates is a MAP keyed by slot
            "elements": [element_row(eid, by_id, "ref", name)
                         for eid, name in declared.items()],
        },
        "scenes": [{"id": f"A{s['n']}", "name": s["happens"][:44], "seconds": s["seconds"],
                    "line": s["say"].strip('*"'), "delivery": s["delivery"],
                    "gesture": s["happens"], "generate": {}, "revoice": {}}
                   for s in talking],
        "cutaways": [row(s, (talking[0]["n"] if talking else "VO")) for s in inserts],
        # overrides is a MAP keyed by what was overridden, not a list — board.py
        # indexes into it. Measured 2026-09-14 against the run that works.
        "overrides": ({} if talking else {"aroll": {
            "agreed": 0, "ruled": "2026-09-14", "by": "the brief",
            "why": "Nobody speaks on camera. Every scene is an insert under one continuous "
                   "voice-over, because the source this was torn from never shows the speaker."}}),
    }
    for slot, key in (("face", "face"), ("hands", "hands"), ("room", "room"), ("voice", "voice")):
        pass
    if o.voice:
        plan["cast"]["voice"] = o.voice

    out = Path(o.run) / "out"; out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(plan, indent=1))
    print(f"{out/'plan.json'} — {len(plan['scenes'])} A-roll · {len(plan['cutaways'])} inserts · "
          f"{len(plan['cast']['elements'])} elements · "
          f"{round(sum(c['seconds'] for c in plan['cutaways']) + sum(s['seconds'] for s in plan['scenes']),1)}s")


if __name__ == "__main__":
    main()
