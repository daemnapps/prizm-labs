"""QC — every check the chain has, on one ad, in one pass (2026-10-02).

the owner: "You're the best checker of your own work. Maybe have something in
parallel that is always checking and updating your own work, QCing it … if it's
catching any issues, then it can trigger something else to go ahead and
dynamically update that chain or whatever the upstream issue is … so I can just
focus on output."

Runs, in chain order, every machine check that exists for the stations an ad has
reached, and writes one report — `QC.md` + `qc.json` in the production run —
where every finding names the STATION that made it, so the fix goes upstream:

    writing    production's brief contract · each person written as their
               element · every swipe shot carried (frame map) · spoken words
               are words · swipe-match / manifest / read stamps current
    elements   every element the brief names is banked (and, with --look, each
               one judged against the brief and the swipe frame — model calls)
    voices     every spoken scene has its recording; the recording's words are
               the line (with --listen: speech-to-text, a paid call)
    storyboard every scene in exactly one section; every filmed section has its
               pictures or reuses another's; the storyboard is for THIS brief

No finding is ever fixed here — QC finds and routes; the station fixes. Exit 0
clean, 1 with findings. Brand-agnostic.

    python3 qc.py <production run> --teardown <teardown run> [--look] [--listen]
"""
import argparse, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
VT = WS / "tools" / "video-teardown" / "machine"


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def _doc(text):
    return json.loads(re.findall(r"```json\s*\n(.*?)\n```", text, re.S)[-1])


def check(run, teardown, look=False, listen=False):
    run, tdir = Path(run), Path(teardown)
    brief_p = tdir / "stages" / "5-brief.md"
    text = brief_p.read_text()
    doc = _doc(text)
    F = []

    def add(station, what, fix):
        F.append({"station": station, "finding": what, "fix_at": fix})

    # ---- writing
    mi = _load("model_inputs", HERE / "model_inputs.py")
    for v in mi.brief_violations(doc):
        add("writing", v, "the brief (stage 5) — AI brief prompt")
    cm = _load("cast_match", VT / "cast_match.py")
    for m in cm.check(tdir)[1]:
        add("writing", f"{m['n']}: {m['element']} — {m['why']}", "the brief (stage 5); cast_match.repair for words")
    sb = _load("storyboard_plan", HERE / "storyboard_plan.py")
    for f in sb.swipe_carry(brief_p, tdir):
        add("writing", f["finding"], "the brief (stage 5) — written from the frame map")
    sc = _load("spoken_check", VT / "spoken_check.py")
    for f in sc.check_lines([(s["id"], s.get("voice") or "") for s in doc.get("scenes") or []]):
        add("writing", f"spoken fragment: {f}", "the line's stage (rewrite / spice)")
    sm = _load("swipe_match", VT / "swipe_match.py")
    if sm.stamp_of(text) != "PASSED":
        add("writing", f"swipe match is {sm.stamp_of(text) or 'missing'} for this brief", "swipe_match.py")
    mf = _load("manifest", VT / "manifest.py")
    if mf.status_of(text) != "COMPLETE":
        add("writing", f"manifest is {mf.status_of(text) or 'missing'} for this brief", "manifest.py")
    if sm.read_of(text) != "APPROVED":
        add("writing", "the owner's read is not current for this brief", "the owner reads the brief")

    # ---- elements
    ec = _load("elements_check", HERE / "elements_check.py")
    sheet = ec.sheet(text, doc.get("piece", {}).get("brand") or "brand-a")
    for it in sheet.get("items") or []:
        if it.get("status") != "banked" or it.get("missing"):
            add("elements", f"{it.get('kind')} {it.get('id')}: {'; '.join(it.get('missing') or ['not banked'])}", "Elements 3.2 (make)")
    if look:
        em = _load("element_match", HERE / "element_match.py")
        for r in em.check(brief_p, doc.get("piece", {}).get("brand") or "brand-a"):
            if r["verdict"] not in ("MATCH",):
                add("elements", f"{r['kind']} {r['id']} → {r['bank_id']}: {r['verdict']} — {r['why']}", "Elements 3.1/3.2")

    # ---- voices
    lines = json.loads((run / "lines.json").read_text()) if (run / "lines.json").exists() else {}
    vr = _load("voice_remap", HERE / "voice_remap.py")
    for s in doc.get("scenes") or []:
        v = (s.get("voice") or "").strip()
        if not v:
            continue
        f = run / "vo" / f"{s['id']}.mp3"
        if not f.exists():
            add("voices", f"{s['id']} has a line and no recording", "voices (voice.py / voice_remap.py)")
        elif vr.words(lines.get(s["id"], "")) != vr.words(v):
            add("voices", f"{s['id']}: the recording is of a different line (\"{lines.get(s['id'], '')[:50]}\")", "voice_remap.py or re-record")
        elif listen:
            tr = _load("vt_transcript", VT / "transcript.py")
            heard = vr.words(" ".join(w["text"] for w in tr.scribe_only(f).get("words") or [] if w.get("type", "word") == "word"))
            if heard != vr.words(v):
                add("voices", f"{s['id']}: heard \"{' '.join(heard)[:60]}\"", "re-record or re-cut")

    # ---- storyboard
    sbp = run / "storyboard.json"
    if not sbp.exists():
        add("storyboard", "no storyboard", "storyboard_plan.py")
    else:
        p = json.loads(sbp.read_text())
        bp = Path(p.get("brief", ""))
        if not bp.is_absolute():
            bp = HERE / bp   # the storyboard writes its brief relative to machine/
        if bp.resolve() != brief_p.resolve():
            add("storyboard", f"built from another brief file ({p.get('brief')})", "storyboard_plan.py")
        fresh = sb.build(None, tdir, brief_p)
        if [g["scenes"] for g in fresh["sections"]] != [g["scenes"] for g in p["sections"]]:
            add("storyboard", "out of date with the brief — its sections no longer match", "storyboard_plan.py")
        seen = [x for g in p["sections"] for x in g["scenes"]]
        for s in doc.get("scenes") or []:
            if seen.count(s["id"]) != 1:
                add("storyboard", f"{s['id']} is in {seen.count(s['id'])} sections", "storyboard_plan.py")
        for g in p["sections"]:
            filmed = g["maker"] not in ("plate", "packshot edit", "endcard plate")
            if filmed and not g["frames"] and not g.get("reuses"):
                add("storyboard", f"{sb.section_no(g['id'])} has no picture and reuses nothing", "storyboard_plan.py")
            for sid, sec in (g.get("voice") or {}).items():
                if not sec:
                    add("storyboard", f"{sid} has no voice length", "voices")
        for c in p.get("check") or []:
            add("storyboard", sb.relabel(c), "the station the finding names")
    return F


def report(F, out):
    by = {}
    for f in F:
        by.setdefault(f["station"], []).append(f)
    L = ["# QC — every check, one pass", ""]
    for st in ("writing", "elements", "voices", "storyboard"):
        rows = by.get(st) or []
        L.append(f"## {st} — {'clean' if not rows else str(len(rows)) + ' finding(s)'}")
        L += [f"- {f['finding']}  → fix at: {f['fix_at']}" for f in rows]
        L.append("")
    Path(out, "QC.md").write_text("\n".join(L))
    Path(out, "qc.json").write_text(json.dumps(F, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run"); ap.add_argument("--teardown", required=True)
    ap.add_argument("--look", action="store_true"); ap.add_argument("--listen", action="store_true")
    a = ap.parse_args()
    F = check(a.run, a.teardown, a.look, a.listen)
    report(F, a.run)
    # every run of QC files its own round in the repo (qc_log.py, 2026-10-02)
    _load("qc_log", HERE / "qc_log.py").add(
        a.run, "chain checks", "qc.py", F,
        method="every machine check" + (" + picture judges" if a.look else "") + (" + speech-to-text" if a.listen else ""))
    print(f"QC: {'clean' if not F else str(len(F)) + ' finding(s)'}")
    for f in F:
        print(f"  [{f['station']}] {f['finding'][:150]}")
    sys.exit(1 if F else 0)
