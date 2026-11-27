"""The full index of one email: every step that made it, in order, with what went in and what came out.

the owner, 2026-10-18: "moving forward we need to keep a full index of everything going on." A run already saves each
step to its own file (the plan in run.json, research/, every copy stage's prompt as sent and its output, the
reviewer's verdict in qc-log/, the moment research, the design prompts, the layout, a record per picture in
media/records/, the checks in klaviyo/card.json, the learnings it wrote). index() puts them in one ordered list and
writes it beside the run as index.json, so anyone can see exactly how the email came to be and fix the step that
caused something, never the one email.

    python3 tools/email-production/design/run_index.py runs/email-production/<brand>/<label>

Each entry: order, group, step, name, by (model or person), when, status, prompt_name, prompt (as sent where the run
kept it), output, review ({ok, severity, problems}), section (for a picture), files.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EM = HERE.parent
REPO = EM.parents[1]
CAP = 40000
COPY = {"stage0": "Triage: what this send has to do", "stage1": "Record: the swiped email's structure",
        "stage1b": "Brand context", "stage1c": "Live read: what the brand says today", "stage2": "Spec: the email's plan",
        "stage3": "First draft: the brand's message injected", "stage4": "Placement", "stage5": "Subject lines",
        "stage6": "Ad structure", "stage7": "Close", "stage8": "Blocks: the email as sections", "stage8c": "Copy check",
        "stage9": "Brief for design"}
ORDER = ["stage0", "stage1", "stage1b", "stage1c", "stage2", "stage3", "stage4", "stage5", "stage6", "stage7", "stage8", "stage8c", "stage9"]


def _t(p, cap=CAP):
    try:
        s = Path(p).read_text()
    except (OSError, UnicodeDecodeError):
        return None
    return s if len(s) <= cap else s[:cap] + "\n\n[… %d more characters in %s]" % (len(s) - cap, Path(p).name)


def _j(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def _review(run, stage):
    for f in sorted((run / "qc-log").glob("*-%s-r*.json" % stage)):
        d = (_j(f) or {}).get(stage)
        if d:
            return {"ok": d.get("ok"), "severity": d.get("severity"), "problems": d.get("problems") or [], "by": f.stem.split("-reviewer-")[-1]}
    return None


def index(run):
    run = Path(run).resolve()
    rj = _j(run / "run.json") or {}
    brand, label = rj.get("brand") or run.parent.name, rj.get("label") or run.name
    out = []
    def add(group, step, name, **k):
        out.append(dict({"order": len(out) + 1, "group": group, "step": step, "name": name}, **{a: b for a, b in k.items() if b not in (None, "", [])}))

    a = rj.get("assignment") or {}
    add("Plan", "plan", "The send, from the calendar", when=rj.get("generated_at"),
        output="\n".join("%s: %s" % (k, v) for k, v in a.items() if v) +
               ("\nformat: %s" % ", ".join("%s = %s" % (k, (v or {}).get("id")) for k, v in (rj.get("elements") or {}).items()) if rj.get("elements") else ""),
        files=[_rel(run / "run.json")])
    for f in sorted((run / "research").glob("*.md")):
        add("Research", "research:" + f.stem, "Research: " + f.stem.replace("-", " "), output=_t(f), files=[_rel(f)])

    st = rj.get("stages") or {}
    for k in ORDER + [x for x in st if x not in ORDER]:
        s = st.get(k)
        if not s:
            continue
        prompt = _t(run / s["sent"]) if s.get("sent") and (run / s["sent"]).is_file() else _t(EM / s["prompt_file"]) if s.get("prompt_file") else None
        add("Copy", k, COPY.get(k, k), by=s.get("model"), status=s.get("status") if s.get("status") != "done" else None,
            why=s.get("why"), seconds=s.get("seconds"), prompt_name=s.get("prompt_name"),
            prompt_kind="as sent" if s.get("sent") and (run / s["sent"]).is_file() else "the prompt file" if prompt else None,
            prompt=prompt, output=_t(run / s["out"]) if s.get("out") else None, review=_review(run, k),
            files=[_rel(run / x) for x in (s.get("out"), s.get("sent")) if x and (run / x).is_file()])

    spec = _j(run / "design" / "email.json") or {}
    job = _j(run / "design" / "job.json") or {}
    avatar = a.get("avatar") or (rj.get("avatar") or {}).get("id") if isinstance(rj.get("avatar"), dict) else a.get("avatar")
    occ = (a.get("occasion") or "").split(" ")[0]
    mw = REPO / "runs" / "moment-research" / brand / str(avatar) / ("%s.md" % occ)
    if mw.is_file():
        add("Design", "design0", "The moment, researched from her side", prompt=_t(mw.with_name(occ + ".prompt.md")),
            output=_t(mw), sources=_t(mw.with_name(occ + ".research.md"), 12000), files=[_rel(mw)])
    if (run / "design" / "design1--prompt.md").is_file() or job:
        add("Design", "design1", "Job card: one job, one belief, one proof, the concept", prompt=_t(run / "design" / "design1--prompt.md"),
            output=json.dumps(job, indent=1, ensure_ascii=False) if job else None, files=[_rel(run / "design" / "job.json")])
    if spec:
        add("Design", "design2", "Layout: the sections, their words and their pictures", prompt=_t(run / "design" / "design2--prompt.md"),
            output=json.dumps({"subject": spec.get("subject"), "theme": spec.get("theme"),
                               "sections": [s.get("s") for s in spec.get("sections", [])]}, indent=1, ensure_ascii=False),
            files=[_rel(run / "design" / "email.json")])

    for f in sorted((run / "media" / "records").glob("*/record.json"), key=lambda p: (p.stat().st_mtime, p.name)):
        r = _j(f) or {}
        j = r.get("judge") or {}
        probs = [x for v in j.values() if isinstance(v, dict) for x in v.get("problems") or []]
        add("Pictures", "picture:" + r.get("label", f.parent.name),
            ("Picture edit: " if r.get("edit_of") else "Picture: ") + (r.get("purpose") or ""),
            by=" · ".join(v for v in ((r.get("model") or {}).get("id"), (r.get("model") or {}).get("vendor_model")) if v),
            when=r.get("made_at"), status=r.get("state"), section=r.get("section"), prompt=r.get("prompt"),
            output=r.get("direction"), references=[{"kind": x.get("kind"), "name": Path(x["path"]).name,
                                                   "pin": (x.get("pinterest") or {}).get("pin")} for x in r.get("references") or []],
            parent=r.get("parent"), file=r.get("file"),
            review={"ok": not probs and r.get("state") == "made", "problems": probs} if j else None, files=[_rel(f)])

    card = _j(run / "klaviyo" / "card.json")
    if card:
        for key, name in (("product_check", "Product check: prices, claims, the guarantee"), ("final_check", "Final check: links, sizes, repeats")):
            rows = card.get(key) or []
            bad = [x["detail"] for x in rows if x.get("result") not in ("ok", "by-hand", "note")]
            add("Build & check", key, name, status="held" if bad else "pass",
                output="\n".join("%s · %s" % (x.get("result"), x.get("detail")) for x in rows),
                review={"ok": not bad, "problems": bad}, files=[_rel(run / "klaviyo" / "card.json")])
        if card.get("klaviyo"):
            add("Build & check", "klaviyo", "Klaviyo draft", by=(card.get("approval") or {}).get("by"),
                when=(card.get("approval") or {}).get("at"), output="campaign %s" % card["klaviyo"].get("campaign_id"))
        if card.get("scheduled"):
            add("Build & check", "scheduled", "Scheduled", by=card["scheduled"].get("by"), when=card["scheduled"].get("at"))

    lf = REPO / "runs" / "learnings" / ("%s.jsonl" % brand)
    taught = []
    if lf.is_file():
        for line in lf.read_text().splitlines():
            try:
                x = json.loads(line)
            except ValueError:
                continue
            if x.get("from") == label:
                taught.append("%s · %s · %s %s: %s" % (x.get("at"), x.get("by"), x.get("stage"), x.get("kind"), x.get("rule")))
    if taught:
        add("Learnings", "learnings", "Rules this email taught the chain", output="\n".join(taught))

    idx = {"brand": brand, "label": label, "steps": out}
    (run / "index.json").write_text(json.dumps(idx, indent=1, ensure_ascii=False) + "\n")
    return idx


if __name__ == "__main__":
    for r in sys.argv[1:]:
        i = index(r)
        print("%s  %d steps → %s" % (i["label"], len(i["steps"]), Path(r) / "index.json"))
