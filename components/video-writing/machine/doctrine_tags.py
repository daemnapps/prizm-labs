#!/usr/bin/env python3
"""Every scene tagged to the marketing doctrine, so each take amplifies the feeling its moment exists to create.

    python3 components/video-writing/machine/doctrine_tags.py tag   <writing run dir> [--write]
    python3 components/video-writing/machine/doctrine_tags.py apply <writing run dir> <production dir>

`tag` reads the run's own doctrine read (stages/1c-doctrine.md: sections carried, techniques observed, awareness, desire,
mood), the teardown's phases (stages/1-teardown.md: each phase's emotion) and the frame map (each swipe shot's times and
the faces the swipe shows), and gives every scene of stages/5-brief.md a `doctrine` block:

    section          the scene's own section (as written)
    carried          the doctrine sections its swipe seconds carry, in order (a moment the doctrine marks as a bank
                     candidate keeps its own name, e.g. "the consequence")
    techniques       the techniques observed in those seconds: lever, technique and the line that carries it
    phase            the teardown phase it sits in and that phase's emotion
    beat             where it sits in the framework (e.g. life · tried · found · now)           (model)
    awareness        the viewer's awareness at that moment (unaware … most-aware)              (model)
    feel             what the viewer must feel here, said as a feeling to amplify                (model)
    show             what faces and bodies on screen do to carry that feeling, turned up         (model)

Times decide `carried`, `techniques` and `phase` (no model). One model call through the team's account door (run-kit
claude_door) writes `beat`, `awareness`, `feel` and `show` for every scene at once, grounded in the lines above and the
swipe's own faces. `--write` keeps the old brief beside it as 5-brief.before-doctrine.md.

`apply` copies each scene's block into a production's takes (scenes/<id>/take.json and every take-*.json gen.take step),
where take.py and the start picture read it. Agnostic: any brand, any swipe, any framework the doctrine names.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

FENCE = re.compile(r"```json\s*\n(.*?)\n```", re.S)
TIME = r"(\d+):(\d{2})\s*[–-]\s*(\d+):(\d{2})"
MODEL = "opus"            # the frontier model on the signed-in plan; the door picks the account


def _secs(m, i):
    return int(m.group(i)) * 60 + int(m.group(i + 1))


def doctrine(run):
    """The doctrine read as times: sections carried, techniques, plus the text blocks the model reads whole."""
    t = (Path(run) / "stages" / "1c-doctrine.md").read_text()
    carried, techniques = [], []
    block = t.split("**SECTIONS CARRIED:**", 1)[-1].split("**AWARENESS", 1)[0]
    for ln in block.splitlines():
        m = re.search(TIME, ln)
        if m:
            name = ln[:m.start()].strip().rstrip("·").strip()
            carried.append({"name": re.sub(r"\s*\(candidate for the bank\)", "", name), "bank": "candidate for the bank" in ln,
                            "from": _secs(m, 1), "to": _secs(m, 3)})
    tech = t.split("**TECHNIQUES OBSERVED:**", 1)[-1].split("**MOOD", 1)[0]
    for ln in tech.splitlines():
        parts = [p.strip() for p in ln.split(" · ")]
        m = re.search(TIME, ln)
        if m and len(parts) >= 4 and "none observed" not in ln:
            techniques.append({"section": parts[0], "lever": parts[1], "technique": parts[2], "from": _secs(m, 1),
                               "to": _secs(m, 3), "line": " · ".join(parts[4:])[:240]})
    return {"text": t, "carried": carried, "techniques": techniques}


def phases(run):
    """The teardown's phases: name, seconds and emotion."""
    t = (Path(run) / "stages" / "1-teardown.md").read_text()
    out = []
    for m in re.finditer(r"\*\*Phase \d+: ([^(*]+)\((\d+):(\d{2})\s*-\s*(\d+):(\d{2})\)\*\*(.*?)(?=\*\*Phase \d+:|\Z)", t, re.S):
        emo = re.search(r"Emotion:\s*(.+)", m.group(6))
        out.append({"name": m.group(1).strip(), "from": _secs(m, 2), "to": _secs(m, 4),
                    "emotion": emo.group(1).strip() if emo else ""})
    return out


def brief(run):
    f = Path(run) / "stages" / "5-brief.md"
    text = f.read_text()
    blocks = list(FENCE.finditer(text))
    for b in reversed(blocks):
        try:
            doc = json.loads(b.group(1))
        except ValueError:
            continue
        if isinstance(doc, dict) and doc.get("scenes"):
            return f, text, b, doc
    raise SystemExit(f"no scene list in {f}")


def shot_times(run):
    fm = json.loads((Path(run) / "framemap" / "framemap.json").read_text())
    return {s["id"]: s for s in fm["shots"]}


def scene_span(sc, shots):
    """The swipe seconds a scene copies, from its shots' sources or its `source` line (K27-K31, K45)."""
    ids = set()
    for src in [sc.get("source") or ""] + [str(sh.get("source") or "") for sh in sc.get("shots") or []]:
        for a, b in re.findall(r"K(\d+)(?:\s*[-–]\s*K?(\d+))?", src):
            ids.update(f"K{k:02d}" for k in range(int(a), int(b or a) + 1))
    got = [shots[k] for k in ids if k in shots]
    if not got:
        return None, []
    return (min(s["start"] for s in got), max(s["end"] for s in got)), sorted(ids)


def overlaps(a, b, x, y, least=0.3):
    return min(b, y) - max(a, x) >= least


PROMPT = """You tag each scene of a video ad to the marketing doctrine of the ad it copies, so every take amplifies the
feeling its moment exists to create. Facts below come from the ad's own doctrine read and teardown; use their words.

THE DOCTRINE READ OF THE SWIPE:
{doctrine}

THE TEARDOWN'S PHASES AND THEIR EMOTION:
{phases}

THE SCENES OF OUR AD (in order; seconds are the swipe seconds each scene copies; faces are what the swipe shows):
{scenes}

For every scene give:
- beat: where it sits in the doctrine's FRAMEWORK, using the framework's own beat words.
- awareness: the viewer's awareness at that moment (unaware, problem-aware, solution-aware, product-aware, most-aware),
  moving from the doctrine's AWARENESS ENTRY to its EXIT across the ad.
- feel: what the viewer must feel at this moment, one short phrase, turned up (e.g. "the itch of a secret she can't
  keep", not "interest"). Grounded in the phase emotion, the desire lines and the scene's words.
- show: what the faces and bodies on screen do to carry that feeling, amplified past the swipe but still real
  (eyes, mouth, hands, posture, a held beat). Our cast speaks in voice-over, so mouths stay closed unless the scene
  says otherwise.

Answer as JSON: {{"<scene id>": {{"beat": "...", "awareness": "...", "feel": "...", "show": "..."}}, ...}} for every
scene id listed."""


def ask(text):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "run-kit"))
    from run_kit import claude_door
    with tempfile.TemporaryDirectory() as d:
        r = claude_door.run(["--output-format", "json", "--model", MODEL, "--max-turns", "1", "--tools", "",
                             "--strict-mcp-config", "--setting-sources", ""],
                            text + "\n\nAnswer with the JSON only, no other words.", timeout=900, cwd=d)
    try:
        out = str(json.loads(r.stdout).get("result") or "")
    except ValueError:
        out = r.stdout or ""
    out = out.strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(out[out.find("{"):out.rfind("}") + 1])


def tag(run, write=False):
    D, P, S = doctrine(run), phases(run), shot_times(run)
    f, text, block, doc = brief(run)
    rows, spans = [], {}
    for sc in doc["scenes"]:
        span, ids = scene_span(sc, S)
        spans[sc["id"]] = span
        faces = [f"{m.get('who')}: {m.get('face')}" for k in ids if k in S for m in (S[k].get("map") or {}).get("moments") or []
                 if m.get("face")][:6]
        rows.append(f"{sc['id']} · section {sc.get('section')} · swipe {span[0]:.0f}-{span[1]:.0f} s" if span else f"{sc['id']} · section {sc.get('section')}")
        rows[-1] += f"\n  says: {sc.get('voice') or ''}\n  picture: {sc.get('picture') or ''}" + ("\n  swipe faces: " + "; ".join(faces) if faces else "")
    phase_text = "\n".join(f"- {p['name']} ({p['from']}-{p['to']} s): {p['emotion']}" for p in P)
    model = ask(PROMPT.format(doctrine=D["text"][:14000], phases=phase_text, scenes="\n".join(rows)))
    for sc in doc["scenes"]:
        span = spans.get(sc["id"])
        a, b = span if span else (None, None)
        got = model.get(sc["id"]) or {}
        sc["doctrine"] = {
            "section": sc.get("section"),
            "carried": [c["name"] for c in D["carried"] if span and overlaps(a, b, c["from"], c["to"])],
            "moments": [c["name"] for c in D["carried"] if c["bank"] and span and overlaps(a, b, c["from"], c["to"])],
            "techniques": [{k: t[k] for k in ("lever", "technique", "line")} for t in D["techniques"] if span and overlaps(a, b, t["from"], t["to"])],
            "phase": next(({"name": p["name"], "emotion": p["emotion"]} for p in P if span and p["from"] <= (a + b) / 2 < p["to"]), None),
            "beat": got.get("beat"), "awareness": got.get("awareness"), "feel": got.get("feel"), "show": got.get("show"),
        }
    if write:
        f.with_name(f.stem + ".before-doctrine" + f.suffix).write_text(text)
        f.write_text(text[:block.start(1)] + json.dumps(doc, indent=2, ensure_ascii=False) + text[block.end(1):])
    return {sc["id"]: sc["doctrine"] for sc in doc["scenes"]}


def apply(run, production):
    """Each scene's doctrine block into a production's takes, by scene id."""
    _, _, _, doc = brief(run)
    by = {sc["id"]: sc.get("doctrine") for sc in doc["scenes"] if sc.get("doctrine")}
    done = []
    for d in sorted((Path(production) / "scenes").iterdir()):
        tags = by.get(d.name)
        if not tags:
            continue
        for f in [d / "take.json"] + sorted(d.glob("take-*.json")):
            if not f.exists():
                continue
            j = json.loads(f.read_text())
            if "steps" in j:
                for st in j["steps"]:
                    if st.get("tool") == "gen.take":
                        st.setdefault("params", {})["doctrine"] = tags
            else:
                j["doctrine"] = tags
            f.write_text(json.dumps(j, indent=1, ensure_ascii=False))
        done.append(d.name)
    return done


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "tag":
        print(json.dumps(tag(a[1], "--write" in a), indent=1, ensure_ascii=False))
    elif len(a) >= 3 and a[0] == "apply":
        print("tagged:", " ".join(apply(a[1], a[2])))
    else:
        sys.exit(__doc__)
