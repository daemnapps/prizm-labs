#!/usr/bin/env python3
"""Brief intake — the chain's steps 0.1–0.9, as code.

Parses a stage-5 brief (the teardown machine's strict eight-line frame
contract makes this deterministic: a parse failure IS a brief defect),
inventories it, runs the checks, classifies the shots, prices the
manifest, and writes two files into the run folder:

  intake.json        — the structured inventory (steps 0.2–0.9)
  intake-report.md   — the readable report: checks, gate list, manifest,
                       estimate

Judgment steps (0.3 person/room blocks, 0.4 master spec, hard-shot
rulings) are NOT automated — the report lists them as gate items for the
session/Damon. The model decides, the script executes.

  python3 intake.py <run>            # expects runs/<run>/brief.md
  python3 intake.py <run> --write-timeline   # also draft timeline-draft.json
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"

FIELDS = ["Source", "Film", "Hear", "Wearing", "On screen", "Say"]

# The AI lane stopped emitting frames on 2026-09-11 and started emitting typed
# scenes — a talking beat carries its line and its delivery and nothing else,
# because it needs one banked still and a voice take rather than a picture of
# its own. The contract between the two machines changed on one side only, and
# intake silently read six openings out of a thirty-three scene brief.
#
# Scenes are read here on their own terms. A field the scene's type does not
# have is absent rather than a defect: asking a talking beat for its wardrobe
# is the re-description this change existed to stop.
SCENE_FIELDS = ["Source", "Who", "Still", "Happens", "Camera", "Refs",
                "Hear", "Product", "Delivery", "On screen", "Hold", "Say"]
SCENE_NEEDS = {                     # what each type must carry to be complete
    "A": ["Say"],
    "B": ["Happens"],
    "C": ["Product"],
}
PRICE = {"still": 0.04, "vo": 0.01, "clip": 0.70, "card": 0.0, "master": 0.04}

HARD_RX = re.compile(r"phone screen|weather app|on a phone|phone showing|"
                     r"family photo|showing a photo|pinch to zoom|screen "
                     r"recording|held up to the lens, on a", re.I)
PRODUCT_RX = re.compile(r"\btube\b|\bbottle\b|\bjar\b|\bpump\b|packshot|"
                        r"squeeze|flip-top", re.I)


def mmss(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def norm(s):
    s = re.sub(r"[‘’']", "'", s or "")
    s = re.sub(r"[“”\"]", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def words(s):
    return len(re.findall(r"[\w']+", s or ""))


def parse(brief):
    doc = {"defects": []}
    m = re.search(r"^##\s+\**(.+?)\**\s*$", brief, re.M)
    doc["title"] = m.group(1).strip("* ") if m else ""
    if not m:
        doc["defects"].append("no title found")
    # concept = text between title and WHAT TO FILM
    concept = ""
    if m:
        rest = brief[m.end():]
        stop = re.search(r"###\s+\**WHAT TO FILM", rest)
        concept = rest[: stop.start() if stop else len(rest)].strip()
    doc["concept"] = re.sub(r"\s+", " ", concept)

    # openings
    doc["openings"] = []
    for om in re.finditer(
            r"\*\*Opening (\d+) · (.+?)\*\*\s*\*\*Film:\*\*\s*(.+?)"
            r"\*\*Say:\*\*\s*[\"“](.+?)[\"”]\s*$",
            brief, re.M | re.S):
        doc["openings"].append({
            "n": int(om.group(1)), "name": om.group(2).strip(),
            "film": re.sub(r"\s+", " ", om.group(3)).strip(),
            "say": re.sub(r"\s+", " ", om.group(4)).strip()})

    # scenes — the AI lane's contract: "Scene N · a–b · Ns · TYPE X"
    doc["frames"] = []
    sheads = list(re.finditer(
        r"^\**Scene (\d+) · ([\d:.]+)\s*[–-]\s*([\d:.]+) · ([\d.]+)s · TYPE ([ABC])\**\s*$",
        brief, re.M))
    for i, h in enumerate(sheads):
        end = sheads[i + 1].start() if i + 1 < len(sheads) else len(brief)
        block = brief[h.end():end]
        fr = {"n": int(h.group(1)), "t0": mmss(h.group(2)), "t1": mmss(h.group(3)),
              "tc": f"{h.group(2)}–{h.group(3)}", "seconds": float(h.group(4)),
              "shot_type": h.group(5)}
        for f in SCENE_FIELDS:
            fm = re.search(
                rf"\*\*{re.escape(f)}:\*\*\s*(.+?)(?=\n\s*\n|\*\*(?:{'|'.join(map(re.escape, SCENE_FIELDS))}):\*\*|^>|\Z)",
                block, re.S | re.M)
            fr[f.lower().replace(" ", "_")] = (
                re.sub(r"\s+", " ", fm.group(1)).strip() if fm else None)
        sm = re.search(r"^>\s*\*\*Say:\*\*\s*(.+)$", block, re.M)
        fr["say"] = (sm.group(1).strip().strip('"').strip("—").strip()
                     if sm else "")
        for k in ("film", "hear", "wearing", "on_screen", "source"):
            fr.setdefault(k, fr.get(k) or "")
        for need in SCENE_NEEDS[fr["shot_type"]]:
            if not fr.get(need.lower().replace(" ", "_")):
                doc["defects"].append(
                    f"scene {fr['n']} (type {fr['shot_type']}): missing {need}")
        # a talking beat is a still plus a voice take; the rest are their own shot
        fr["film"] = fr.get("happens") or fr.get("product") or ""
        doc["frames"].append(fr)
    doc["contract"] = "scenes" if doc["frames"] else "frames"
    # The frame parser below still runs. On a scene brief it finds the six
    # openings (which keep the frame contract) and nothing else, and they are
    # variants rather than body beats — so they are collected separately and
    # the scene list stays the inventory.
    heads = [] if doc["frames"] else list(re.finditer(
        r"^\**Frame (\d+) · (\d+:\d+)(?:\s*[–\-]\s*(\d+:\d+))?\**\s*$",
        brief, re.M))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(brief)
        block = brief[h.end():end]
        t0 = mmss(h.group(2))
        t1 = mmss(h.group(3)) if h.group(3) else t0 + 1
        fr = {"n": int(h.group(1)), "t0": t0, "t1": t1,
              "tc": f"{h.group(2)}–{h.group(3) or h.group(2)}"}
        for f in FIELDS:
            fm = re.search(
                rf"\*\*{re.escape(f)}:\*\*\s*(.+?)(?=\n\s*\n|\*\*(?:{'|'.join(map(re.escape, FIELDS))}):\*\*|\Z)",
                block, re.S)
            val = re.sub(r"\s+", " ", fm.group(1)).strip() if fm else None
            key = f.lower().replace(" ", "_")
            fr[key] = val
            if val is None:
                doc["defects"].append(f"frame {fr['n']}: missing {f}")
        say = fr.get("say") or ""
        say = re.sub(r"^>\s*", "", say).strip()
        fr["say"] = say.strip('"“” ')
        osc = fr.get("on_screen") or ""
        fr["on_screen"] = "" if norm(osc) == "nothing" else osc.strip('"“” ')
        # dedupe: header lines can also appear as captions
        if not any(x["n"] == fr["n"] and x.get("film") for x in doc["frames"]):
            doc["frames"].append(fr)
    # frames whose header matched twice with an empty body — drop empties
    # On the frame contract a frame with no Film line is a defect and is
    # dropped. On the scene contract a talking beat has no picture of its own
    # on purpose — it reuses another scene's still and carries only its line —
    # so dropping those silently removed eighteen of thirty-three scenes and
    # reported the remainder as a complete inventory.
    doc["frames"] = [f for f in doc["frames"]
                     if f.get("film") or f.get("shot_type") == "A"]
    doc["frames"].sort(key=lambda f: f["n"])

    # WHAT TO SAY
    ws = re.search(r"###\s+\**WHAT TO SAY\**\s*$(.+)\Z", brief, re.M | re.S)
    script = []
    if ws:
        paras = [re.sub(r"\s+", " ", p).strip()
                 for p in re.split(r"\n\s*\n", ws.group(1)) if p.strip()]
        script = [p for p in paras if not p.lower().startswith("every line in order")]
    doc["script"] = script

    # brand facts (compliance-exact strings found in lines)
    facts = []
    joined = " ".join(f["say"] for f in doc["frames"])
    for rx, label in [(r"[A-Z][a-z]+ Body Scrub", "product name"),
                      (r"(?:twenty-nine dollars|\$\d+)", "price"),
                      (r"every penny back", "guarantee"),
                      (r"[a-z]+\.com|on the site", "site")]:
        for hit in set(re.findall(rx, joined)):
            facts.append({"fact": hit, "kind": label})
    doc["brand_facts"] = facts
    credit = re.search(r"Built from a format that ran on (\w+)", brief)
    doc["format_credit"] = credit.group(1) if credit else None
    return doc


def check(doc):
    checks = []
    # timecode continuity
    fs = doc["frames"]
    cont = all(fs[i + 1]["t0"] - fs[i]["t1"] <= 1 for i in range(len(fs) - 1))
    checks.append(("timecodes continuous", cont))
    # say vs script
    if doc["script"]:
        match = (len(fs) == len(doc["script"]) and
                 all(norm(f["say"]) == norm(s) for f, s in zip(fs, doc["script"])))
        checks.append(("WHAT TO SAY matches the frames' Say lines 1:1", match))
        if not match:
            doc["defects"].append("script/say mismatch — brief defect")
    else:
        checks.append(("WHAT TO SAY section absent (older brief cut) — "
                       "script taken from the Say lines", True))
        doc["script"] = [f["say"] for f in fs if f.get("say")]
    checks.append((f"all frames carry all {len(FIELDS)} labeled fields",
                   not any("missing" in d for d in doc["defects"])))
    checks.append(("six openings present", len(doc["openings"]) == 6))
    return checks


def classify(doc):
    for f in doc["frames"]:
        flags = []
        if HARD_RX.search(f.get("film") or ""):
            flags.append("hard: screen/photo content")
        if PRODUCT_RX.search(f.get("film") or ""):
            flags.append("product in frame — needs real packshot")
        if f.get("shot_type"):          # the scene contract names it outright
            f["type"] = {"A": "talking", "B": "action", "C": "product"}[f["shot_type"]]
        else:
            f["type"] = ("card" if not f["say"] and f["on_screen"]
                         else "talking" if f["say"] else "action")
        f["flags"] = flags
    for o in doc["openings"]:
        o["flags"] = (["hard: screen/photo content"]
                      if HARD_RX.search(o["film"]) else [])
        o["shared_with_frame1"] = norm(o["say"]) == norm(doc["frames"][0]["say"]) \
            if doc["frames"] else False


def pacing(doc):
    total_words = sum(words(f["say"]) for f in doc["frames"])
    runtime = doc["frames"][-1]["t1"] if doc["frames"] else 0
    per = []
    for f in doc["frames"]:
        w = words(f["say"])
        sec = max(1, f["t1"] - f["t0"])
        per.append({"n": f["n"], "words": w, "sec": sec,
                    "wps": round(w / sec, 2)})
    return {"total_words": total_words, "runtime_sec": runtime,
            "target_wps": round(total_words / runtime, 2) if runtime else None,
            "per_frame": per,
            "hot_frames": [p["n"] for p in per if p["wps"] > 3.2]}


def manifest(doc):
    extra_openings = [o for o in doc["openings"] if not o["shared_with_frame1"]]
    gen_frames = [f for f in doc["frames"] if f["type"] != "card"]
    cards = [f for f in doc["frames"] if f["type"] == "card"]
    # Stills are counted per SETUP, not per scene. Eighteen talking beats in
    # one barbershop are one still and eighteen voice takes — that reuse is the
    # entire reason scenes carry a shot type, and counting one still each
    # priced a run at more than double what it costs.
    setups = len({(f.get("still") or f.get("film") or "").strip().lower() or f["n"]
                  for f in gen_frames if f.get("shot_type") == "A"}) or 0
    non_talking = [f for f in gen_frames if f.get("shot_type") != "A"]
    stills = (setups + len(non_talking) + len(extra_openings)) if doc.get("contract") == "scenes" \
        else len(gen_frames) + len(extra_openings)
    counts = {
        "masters": 1,
        "stills": stills,
        "vo_lines": len([f for f in doc["frames"] if f["say"]]) + len(extra_openings),
        # every beat is still its own clip — a shared still is animated once
        # per voice take, and the takes differ
        "clips": len(gen_frames) + len(extra_openings),
        "cards": len(cards),
        "variants (cuts of the film)": len(doc["openings"]) or 1,
    }
    est = (counts["masters"] * PRICE["master"] + counts["stills"] * PRICE["still"]
           + counts["vo_lines"] * PRICE["vo"] + counts["clips"] * PRICE["clip"])
    return counts, round(est, 2)


def gate(doc):
    items = []
    for f in doc["frames"]:
        for fl in f["flags"]:
            items.append(f"frame {f['n']}: {fl} — needs a ruling")
    for o in doc["openings"]:
        for fl in o["flags"]:
            items.append(f"opening {o['n']} ({o['name']}): {fl} — needs a ruling")
    if any("packshot" in i for i in items):
        items.append("MISSING ASSET: real product packshot reference")
    items += [f"BRIEF DEFECT: {d}" for d in doc["defects"]]
    items.append("JUDGMENT (0.3): person block — identity + load-bearing "
                 "body details, from the concept and Film lines")
    items.append("JUDGMENT (0.3): world block — fixed room objects across frames")
    items.append("JUDGMENT (0.3): camera block — realness ruling for this format")
    return items


def write_timeline(doc, rd):
    """Step 0.10 — the working copy, drafted from the inventory.

    Locked blocks and craft fields carry [DRAFT] / [SLOT] markers where
    judgment is still needed; an existing timeline.json is never touched —
    this writes timeline-draft.json for review/merge."""
    existing = {}
    tl = rd / "timeline.json"
    if tl.exists():
        try:
            existing = json.loads(tl.read_text())
        except Exception:
            pass
    # wardrobe: distinct Wearing strings, keyed by first distinctive word
    wardrobe, order = {}, []
    for f in doc["frames"]:
        w = f.get("wearing") or ""
        if w and w not in wardrobe.values():
            key = re.sub(r"[^a-z]", "", w.split(",")[0].split()[-1].lower()) \
                or f"outfit{len(wardrobe)+1}"
            while key in wardrobe:
                key += "x"
            wardrobe[key] = w
            order.append((w, key))
    def outfit_key(w):
        for full, k in order:
            if full == w:
                return k
        return order[0][1] if order else "outfit1"
    shots = []
    for f in doc["frames"]:
        shots.append({
            "id": f"s{f['n']}",
            "brief_time": f["tc"],
            "type": f["type"],
            "outfit": outfit_key(f.get("wearing") or ""),
            "on_screen": f.get("on_screen") or "",
            "say": f["say"],
            "still_action": "[DRAFT from Film — needs third-person pass] "
                            + (f.get("film") or ""),
            "motion": "[DRAFT from Film — needs third-person pass] "
                      + (f.get("film") or ""),
            "hear": f.get("hear") or "",
            "flags": f.get("flags", []),
        })
    variants = [{"n": o["n"], "name": o["name"], "control":
                 o["shared_with_frame1"], "film": o["film"], "say": o["say"],
                 "build": "with body" if o["shared_with_frame1"]
                 else "after body approval"}
                for o in doc["openings"]]
    draft = {
        "run": rd.name,
        "brief": doc["title"],
        "aspect": existing.get("aspect", "9:16"),
        "locked": existing.get("locked") or {
            "character": "[SLOT: person block — identity + load-bearing details]",
            "world": "[SLOT: world block — fixed room objects]",
            "camera": "[SLOT: camera block — realness ruling]"},
        "wardrobe": wardrobe,
        "voice": existing.get("voice") or
                 {"voice_id": "[SLOT: voice pick]", "speed": 1.0},
        "shots": shots,
        "variants": variants,
        "rulings": ["natural pace — smooth beats runtime",
                    "control opening first, variants after body approval",
                    "screens/photos: composite real artifacts"],
    }
    out = rd / "timeline-draft.json"
    out.write_text(json.dumps(draft, indent=2))
    return out


def report(doc, checks, pace, counts, est, gates):
    L = [f"# Intake report — {doc['title']}", "",
         f"Concept: {doc['concept'][:180]}…", "",
         "## Inventory",
         f"- frames: {len(doc['frames'])} · openings: {len(doc['openings'])}"
         f" · script lines: {len(doc['script'])}"
         f" · brand facts: {len(doc['brand_facts'])}"
         f" · format credit: {doc['format_credit']}", "",
         "## Checks"]
    L += [f"- {'PASS' if ok else 'FAIL'} · {name}" for name, ok in checks]
    L += ["", "## Pacing budget",
          f"- {pace['total_words']} words over {pace['runtime_sec']}s → "
          f"target {pace['target_wps']} words/sec",
          f"- frames that will run longer than their timecode at natural "
          f"pace (fine — ruling: smooth beats runtime): "
          f"{pace['hot_frames'] or 'none'}", "",
          "## Shot classification"]
    for f in doc["frames"]:
        fl = ("  ⚠ " + "; ".join(f["flags"])) if f["flags"] else ""
        L.append(f"- Frame {f['n']} ({f['tc']}): {f['type']}{fl}")
    for o in doc["openings"]:
        tag = "= frame 1" if o["shared_with_frame1"] else "extra variant"
        fl = ("  ⚠ " + "; ".join(o["flags"])) if o["flags"] else ""
        L.append(f"- Opening {o['n']} · {o['name']}: {tag}{fl}")
    L += ["", "## Manifest + estimate"]
    L += [f"- {k}: {v}" for k, v in counts.items()]
    L += [f"- **estimated draft cost ≈ ${est}** (current price table)", "",
          "## The gate — every item needs a ruling before money moves"]
    L += [f"- [ ] {g}" for g in gates]
    return "\n".join(L) + "\n"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = sys.argv[1]
    rd = RUNS / run
    brief = (rd / "brief.md").read_text()
    doc = parse(brief)
    checks = check(doc)
    classify(doc)
    pace = pacing(doc)
    counts, est = manifest(doc)
    gates = gate(doc)
    doc.update({"checks": [{"name": n, "ok": o} for n, o in checks],
                "pacing": pace, "manifest": counts, "estimate_usd": est,
                "gate": gates})
    (rd / "intake.json").write_text(json.dumps(doc, indent=2))
    tlpath = write_timeline(doc, rd)
    gates.append(f"review timeline-draft.json ({tlpath.name}) and merge into timeline.json")
    rep = report(doc, checks, pace, counts, est, gates)
    (rd / "intake-report.md").write_text(rep)
    print(rep)


if __name__ == "__main__":
    main()
