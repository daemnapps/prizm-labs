#!/usr/bin/env python3
"""angle_pick — read a brief, name its ONE angle from the brand's signed bank.

    angle_pick.py --brand <b> --brief brief-0036 [--product <p>]        read + show, writes nothing
    angle_pick.py --brand <b> --brief brief-0036 --write                 ... and record it on the brief
    angle_pick.py --brand <b> --missing --write                          every brief with no angle yet

the owner, 2026-10-12: "The angle should be derived from the brief itself through
analyzing what the brief actually even is. That's it. The angle should be in
the notes of the brief."

ONE WRITER. The angle is set here, once, when a brief is registered
(image-teardown `briefs.open_brief` calls `auto()` for every new number, whichever
lane or caller numbers it; NAMING_ANGLE_PICK=off skips it).
Every stage after reads it through `names.brief_record` / `names.brief_angle`
— nothing downstream picks or re-derives one. ANGLE.md is the map.

Where it is kept (brands/ is read-only to machines):
  - the brief register entry (tools/image-teardown/briefs.json): `angle`,
    `angle_why`, `angle_state`, `angle_by`
  - a NOTES line in the brief file itself (runs/…)
  - the prompt and the answer: runs/naming/<brand>/angle-<brief>/
  - a proposal for the brands/<brand>/briefs header, for a person to commit:
    runs/brands-proposals/<brand>/<date>-brief-angles/briefs/brief-angles.json

The bank is the brand's ACTIVE angles (strategy/angles.json), less rows marked
`misfiled` (formats, not claims — naming CLAUDE.md, "Four things"), narrowed to
the brief's avatar when the bank has angles for it (an angle belongs to one core
avatar), then to the angles whose ad set is already running in Meta (2026-10-27). Nothing is coined: an id not in the bank is refused; when nothing fits
the answer is state `no-fit`, recorded with no angle.
"""
import argparse, json, os, re, sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import names as N  # noqa: E402
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit import model as M  # noqa: E402

WS = N.WS
PROMPT = HERE / "prompts" / "angle-pick-v1.md"
PROMPT_VERSION = "angle-pick-v1"
MODEL_ALIAS = "sonnet"                 # registry alias: reads well, cheaper than the design tier
OFF_ENV = "NAMING_ANGLE_PICK"          # "off" / "0" skips the hook in briefs.py open
BRIEF_FILES = ("EDITOR-BRIEF.md", "AD-SCRIPT-v5.md", "brief.md", "06-brief.md")
NOTE_TAG = "- Angle:"


class NoPick(Exception):
    pass


# ---------------------------------------------------------------- inputs
def model_id(alias=MODEL_ALIAS):
    """The registry id (components/models/models.json) for an approved text model alias."""
    reg = json.loads((WS / "components" / "models" / "models.json").read_text())
    for m in reg["models"]:
        if (m["id"] == alias or alias in (m.get("aliases") or [])) and m.get("status") == "approved" \
                and "text" in m.get("modality", []):
            return m["id"]
    raise NoPick(f"no approved text model '{alias}' in the registry")


def bank(brand, avatar=None):
    """(angles, scope) — the brand's active, non-misfiled angles, every one of them for every avatar: an angle is
    the brand's, not an avatar's (the owner, 28 Oct 2026: "angles are just ways to start the conversation and each conversation varies by language of the avatar but the approach is the same"). The avatar's language and the swipe decide how
    it is said. `avatar` is kept for callers; it narrows nothing."""
    signed = N.signed_angles(brand) or {}
    seen, rows = set(), []
    for a in signed.values():
        aid = a.get("id")
        if aid in seen or a.get("misfiled"):
            continue
        seen.add(aid)
        rows.append(a)
    return rows, ""


def open_ad_sets(brand, avatar, rows):
    """The rows whose ad set is already open in Meta (meta-upload `ad_sets`, files only) — the owner, 2026-10-27:
    "our campaign is established so most new ads will go into existing ad sets unless a new angle or avatar is
    clearly defined." An avatar with no open ad set at all keeps the whole bank: the brief still gets its angle,
    and the card's ad set check says the ad set waits on the owner's signature."""
    if not avatar:
        return rows, ""
    try:
        import importlib.util
        f = WS / "components" / "meta-upload" / "ad_sets.py"
        spec = importlib.util.spec_from_file_location("_mu_ad_sets", f)
        A = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(A)
        ok = set(A.open_angles(brand, avatar, [a["id"] for a in rows]))
    except Exception:                            # noqa: BLE001 — no answer narrows nothing
        return rows, ""
    mine = [a for a in rows if a["id"] in ok]
    return (mine, " with an ad set already running") if mine else (rows, "")


def declared_id(value, rows):
    """A stage-6 declared angle on the bank's own id: `grandmasrecipe` and `grandmas-recipe` are one angle."""
    key = lambda s: re.sub(r"[^a-z0-9]", "", str(s or "").lower())
    if not key(value):
        return None
    return next((a["id"] for a in rows if key(value) in (key(a["id"]), key(a.get("was")))), None)


def bank_text(rows):
    return "\n\n".join(f"- id: {a['id']}\n  name: {a.get('name') or ''}\n  avatar: {a.get('avatar') or ''}\n"
                       f"  what: {(a.get('what') or '').strip()}" for a in rows)


def register():
    f = N.register_file()
    return f, json.loads(f.read_text())


def find_entry(reg, brand, brief, product=None):
    """(key, entry) on the register for this brief, or (None, None)."""
    hit = N.find_brief(brand, brief, product, reg=reg)
    r = (hit or {}).get("register")
    if not r:
        return None, None
    return r["key"], reg["briefs"][r["key"]]


def brief_file(entry):
    """The brief itself: the register's `brief_file`, else the run's brief by its usual names."""
    if entry.get("brief_file") and (WS / entry["brief_file"]).is_file():
        return WS / entry["brief_file"]
    name = str(entry.get("run") or "")
    # a picture brief's register `run` is the bare run name: its brief sits in the image-teardown run
    # (out/06-brief.md) or its filed copy (runs/image-teardown/<brand>/<run>/) — 2026-10-27
    # the run works in that same folder since 2026-10-28 (its out/); the old lane folder is read for one release
    rec_dir = WS / "runs" / "image-teardown" / N.slug(entry.get("brand") or "") / name
    for run in (WS / name, rec_dir, rec_dir / "out",
                WS / "tools" / "image-teardown" / "runs" / name / "out"):
        if not name or not run.is_dir():
            continue
        for bn in BRIEF_FILES:
            for p in (run / bn, run / "deliverable" / bn):
                if p.is_file():
                    return p
        d = sorted((run / "deliverable").glob("*.md")) if (run / "deliverable").is_dir() else []
        if d:
            return d[0]
    return None


HEADER_KEYS = ("brief", "type", "brand", "product", "avatar", "title", "format", "style", "problem", "concept")


def header_text(entry):
    return "\n".join(f"- {k}: {entry[k]}" for k in HEADER_KEYS if entry.get(k)) or "(none)"


def build_prompt(entry, text, rows, scope):
    t = PROMPT.read_text()
    return (t.replace("{header}", header_text(entry)).replace("{brief}", text.strip())
             .replace("{bank_scope}", scope).replace("{bank}", bank_text(rows)))


# ---------------------------------------------------------------- the answer
def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[*_`>#|]", " ", str(s or ""))).strip().lower()


def parse_answer(raw, rows, text):
    """The model's JSON → {state, angle, quote, why}. Refuses an id not in the bank or a
    quote that is not in the brief."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        raise NoPick(f"no JSON in the answer: {str(raw)[:160]}")
    try:
        d = json.loads(m.group(0))
    except ValueError as e:
        raise NoPick(f"answer is not JSON: {e}")
    state = d.get("state")
    if state not in ("picked", "no-fit"):
        raise NoPick(f"state must be picked or no-fit, got {state!r}")
    ids = {a["id"] for a in rows}
    angle = d.get("angle") if state == "picked" else None
    if state == "picked" and angle not in ids:
        raise NoPick(f"'{angle}' is not in the bank ({', '.join(sorted(ids))}) — nothing is coined")
    quote = str(d.get("quote") or "").strip().strip('"')
    if not quote or _norm(quote) not in _norm(text):
        raise NoPick(f"the quote is not in the brief: {quote[:120]!r}")
    why = re.sub(r"\s+", " ", str(d.get("why") or "")).strip()
    return {"state": state, "angle": angle, "quote": quote, "why": why}


def one_line(ans):
    return f'{ans["why"]} — "{ans["quote"]}"'


# ---------------------------------------------------------------- the step
def pick(brand, brief, product=None, runner=None, reg=None):
    """Read the brief, return {key, entry, state, angle, angle_why, quote, model, prompt, raw, file}.
    `runner(prompt, model) -> (code, out, err)` is the test seam (run_kit.model.call)."""
    brand = N.slug(brand)
    reg = reg if reg is not None else register()[1]
    key, entry = find_entry(reg, brand, brief, product)
    if not entry:
        raise NoPick(f"{brand} {brief}: not on the brief register")
    rows, scope = bank(brand, entry.get("avatar"))
    if not rows:
        raise NoPick(f"{brand} has no active angles in strategy/angles.json")
    rows, more = open_ad_sets(brand, entry.get("avatar"), rows)
    scope += more
    declared = declared_id((entry.get("declares") or {}).get("angle"), rows)
    if declared:
        # the brief already names its angle (image-teardown stage 6 declares it) — that IS the brief's own word
        return {"key": key, "entry": entry, "state": "declared", "angle": declared,
                "angle_why": "the brief declares it (stage 6 declares)", "quote": None,
                "model": None, "prompt": None, "raw": None, "file": None}
    f = brief_file(entry)
    if f is None:
        raise NoPick(f"{brand} {brief}: no brief file to read (register `brief_file` / run folder)")
    text = f.read_text(errors="replace")
    prompt = build_prompt(entry, text, rows, scope)
    mid = model_id()
    raw = M.call(prompt, mid, label=f"angle-pick-{brand}-{entry.get('brief')}", tries=2, wait=10,
                 timeout=600, runner=runner)
    ans = parse_answer(raw, rows, text)
    return {"key": key, "entry": entry, "state": ans["state"], "angle": ans["angle"],
            "angle_why": one_line(ans), "quote": ans["quote"], "model": mid, "prompt": prompt,
            "raw": raw, "file": f}


# ---------------------------------------------------------------- recording it
def write_note(path, res):
    """A NOTES line in the brief file itself — replaced, never stacked."""
    if path is None:
        return
    line = (f"{NOTE_TAG} `{res['angle']}` — {res['angle_why']}" if res["angle"]
            else f"{NOTE_TAG} none fits the bank (no-fit) — {res['angle_why']}")
    line += f"  _(read off this brief by components/naming/angle_pick.py, {PROMPT_VERSION}, {date.today()})_"
    t = path.read_text(errors="replace")
    lines = t.rstrip("\n").split("\n")
    lines = [l for l in lines if not l.startswith(NOTE_TAG)]
    if "## Notes" not in lines:
        lines += ["", "## Notes"]
    i = lines.index("## Notes")
    lines.insert(i + 1, line)
    path.write_text("\n".join(lines) + "\n")


def write_run(brand, res):
    d = WS / "runs" / "naming" / brand / f"angle-{res['entry'].get('brief')}"
    d.mkdir(parents=True, exist_ok=True)
    if res.get("prompt"):
        (d / "prompt.md").write_text(res["prompt"])
    (d / "answer.json").write_text(json.dumps(
        {k: (str(v) if isinstance(v, Path) else v) for k, v in res.items() if k not in ("entry", "prompt")},
        indent=1, ensure_ascii=False) + "\n")
    return d


def write_proposal(brand, res):
    """The brands/<brand>/briefs header change, as a proposal a person commits."""
    d = WS / "runs" / "brands-proposals" / brand / f"{date.today()}-brief-angles" / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "brief-angles.json"
    cur = json.loads(f.read_text()) if f.is_file() else {
        "_what": "Proposed `angle` + `angle_why` for brands/<brand>/briefs/briefs.json headers, read off each "
                 "brief by components/naming/angle_pick.py. brands/ is read-only to machines: a person commits "
                 "these. Until then every stage reads the same angle off the brief register.",
        "briefs": []}
    e = res["entry"]
    cur["briefs"] = [b for b in cur["briefs"] if b.get("key") != res["key"]]
    cur["briefs"].append({"key": res["key"], "brief": e.get("brief"), "product": e.get("product"),
                          "angle": res["angle"], "angle_state": res["state"], "angle_why": res["angle_why"]})
    f.write_text(json.dumps(cur, indent=1, ensure_ascii=False) + "\n")
    return f


def record(brand, res):
    """Write the angle onto the brief: register entry, brief NOTES line, run record, proposal."""
    f, reg = register()
    e = reg["briefs"][res["key"]]
    e["angle"] = res["angle"]
    e["angle_why"] = res["angle_why"]
    e["angle_state"] = res["state"]                      # picked | declared | no-fit
    e["angle_by"] = {"tool": "components/naming/angle_pick.py", "prompt": PROMPT_VERSION,
                     "model": res.get("model"), "at": datetime.now().isoformat(timespec="seconds")}
    f.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
    N._ALIASES = None
    write_note(res.get("file") or brief_file(e), res)
    write_run(brand, res)
    write_proposal(brand, res)


def off():
    return os.environ.get(OFF_ENV, "").strip().lower() in ("off", "0", "no", "false")


def auto(brand, brief, product=None, say=print, runner=None):
    """The hook at brief registration. Never raises — a brief is opened either way; a
    failure is said, and the brief has no angle until the step is run again."""
    if off():
        say(f"  angle: off ({OFF_ENV}=off) for {brief}")
        return None
    try:
        reg = register()[1]
        _, entry = find_entry(reg, brand, brief, product)
        if entry and entry.get("angle_state"):
            say(f"  angle: {entry.get('angle') or 'no-fit'} (already read off the brief)")
            return None
        res = pick(brand, brief, product, runner=runner, reg=reg)
        record(brand, res)
        say(f"  angle: {res['angle'] or 'NO-FIT'} — {res['angle_why']}")
        return res
    except Exception as e:                       # noqa: BLE001
        say(f"  angle: not read ({str(e)[:200]})")
        return None


def missing(brand, reg=None):
    reg = reg if reg is not None else register()[1]
    return [r for r in reg["briefs"].values()
            if isinstance(r, dict) and N.slug(r.get("brand") or "") == N.slug(brand) and not r.get("angle_state")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--brief", nargs="*", default=[])
    ap.add_argument("--product")
    ap.add_argument("--missing", action="store_true", help="every brief of the brand with no angle read yet")
    ap.add_argument("--write", action="store_true", help="record it on the brief (otherwise show only)")
    a = ap.parse_args()
    briefs = list(a.brief)
    if a.missing:
        briefs += [r["id"] for r in missing(a.brand)]
    if not briefs:
        sys.exit("name --brief or --missing")
    bad = 0
    for b in briefs:
        try:
            res = pick(a.brand, b, a.product)
        except (NoPick, M.StageFailed, N.AmbiguousBrief) as e:
            print(f"{b}: NOT READ — {e}")
            bad += 1
            continue
        if a.write:
            record(a.brand, res)
        print(f"{res['entry'].get('brief')}  {res['angle'] or 'NO-FIT':<24} {res['angle_why']}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
