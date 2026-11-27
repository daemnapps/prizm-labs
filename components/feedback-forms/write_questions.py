#!/usr/bin/env python3
"""Write a brand's feedback questions from its own foundational research.

    python3 components/feedback-forms/write_questions.py --brand <b> [--label L] [--dry-run]
    python3 components/feedback-forms/write_questions.py --brand <b> --packet     the research packet only, no model

What to ask comes from the brand's people profiles (components/profiles): the parts still open and the questions
the research could not answer, put to the customers in a position to answer them. How to ask comes from the brand's
voice (position, story, core message) and its customers' own words (components/language-layer), which also give
the tap options. The stages, what each flow already knows and the starter spine come from the brand's
feedback-stages.json / feedback-questions.json, or the starter set in brands/_TEMPLATE.

Writes a PROPOSAL only: runs/feedback-forms/<b>/questions-<label>/ (packet.json, the prompt as sent, the model's
answer, deliverable/feedback-questions.json, PROPOSAL.md). brands/ is never written; a person applies it on the
owner's yes. Every cited line must be one the packet gave the model, and the result must pass build.check, or it
stops. Brand-agnostic: no brand is named here.
"""
import argparse
import copy
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components" / "run-kit"))
sys.path.insert(0, str(REPO / "components" / "language-layer"))
sys.path.insert(0, str(REPO / "components" / "profiles"))
import build as B  # noqa: E402

TOOL = "feedback-forms"
STEPS = [{"key": "questions", "name": "Write the questions", "tier": "designs", "label": "questions"}]
LANES = {"lead": ("lead", "prospect"), "customer": ("customer",), "churned": ("churned",)}
VOICE_FILES = ("position.md", "story.md", "core-message.json", "core-message/core-message.json", "compliance.json")
RULES = """- 4 to 9 always-shown questions per stage (follow-ups with show_if do not count); about two minutes.
- One idea per question. No leading questions, no yes/no where a choice tells more.
- Never ask what the stage already knows (orders, subscription, purchase status).
- Customer stages keep a 0–10 recommend question (id "recommend") so the score stays comparable over time.
- Choice questions offer 3–6 options in the customers' words, plus "other".
- Every question and option written from the customers' words cites those lines in language_used (ids from the
  list above only). A question the words cannot support may cite nothing; say so in "fills".
- The brand's claims rules apply (compliance): promise nothing, name no condition the brand may not name.
- Plain, warm, in the brand's register; first person only if the brand's voice is a founder's."""


def _read(p, limit=4000):
    try:
        return Path(p).read_text()[:limit]
    except OSError:
        return ""


def brand_dir(brand, root=REPO):
    return Path(root) / "brands" / brand


def voice(brand, root=REPO):
    b = brand_dir(brand, root)
    parts = []
    for base in (b / "brand-identity", b / "identity", b, b / "strategy"):
        for f in VOICE_FILES:
            p = base / f
            if p.is_file() and not any(f in x for x in parts):
                text = _read(p)
                if text.strip() and "<" not in text[:200]:
                    parts.append(f"### {f}\n{text.strip()}")
    return "\n\n".join(parts) or "(no voice files yet: write plainly and warmly)"


def people(brand):
    try:
        import profiles as PR
        rows = PR.audit(brand)
    except (Exception, SystemExit) as err:  # a brand without profiles still gets forms
        return f"(profiles could not be read: {str(err)[:80]})", []
    out, ids = [], []
    for r in rows:
        if "error" in r:
            continue
        try:
            p = PR.load(brand, r["id"])
        except (Exception, SystemExit):
            continue
        card = p.get("card") or {}
        filed = {k: v for k, v in p["parts"].items() if v.get("state") not in ("open", "n/a")}
        lines = [f"- {p['id']} ({p.get('label') or ''}): {p['own_lines']} own lines"]
        for k in ("desire", "opening", "doubt"):
            if (card.get(k) or {}).get("text"):
                lines.append(f"  {k}: {card[k]['text'][:200]}")
        lines.append("  open: " + (", ".join(sorted(r["open"])) or "nothing"))
        if filed:
            lines.append("  filed: " + ", ".join(sorted(filed)))
        for g in (p.get("gaps") or [])[:6]:
            lines.append(f"  unanswered: {str(g)[:160]}")
        out.append("\n".join(lines))
        ids.append(p["id"])
    return "\n".join(out) or "(no profiles yet: ask what a first profile needs — desire, the four doubts, awareness)", ids


def words(brand, per_lane=40):
    try:
        from language_layer import engine
    except Exception:
        return "(no language bank yet)", set()
    rows = []
    try:
        for a in engine.avatars(brand):
            rows += engine.load(brand, a["key"])
    except (Exception, SystemExit):
        return "(no language bank yet)", set()
    blocks, ids = [], set()
    for lane, funnels in LANES.items():
        sub = [r for r in rows if r.get("funnel") in funnels and r.get("text")]
        if not sub:
            continue
        ranked = engine.query(sub, limit=per_lane)
        blocks.append(f"### {lane}")
        for r in ranked:
            ids.add(r["id"])
            blocks.append(f"{r['id']} · {r['text'].strip()[:220]}")
    return "\n".join(blocks) or "(no language bank yet)", ids


def configs(brand, root=REPO):
    own = brand_dir(brand, root) / "operations"
    tpl = Path(root) / "brands" / "_TEMPLATE" / "operations"
    src = own if (own / "feedback-stages.json").is_file() and (own / "feedback-questions.json").is_file() else tpl
    return (json.loads((src / "feedback-stages.json").read_text()), json.loads((src / "feedback-questions.json").read_text()),
            "brand" if src == own else "template")


def packet(brand, root=REPO):
    st, qs, origin = configs(brand, root)
    ppl, pids = people(brand)
    wds, wids = words(brand)
    stages = "\n".join(f"- {s['stage']} · {s['label']} · lane {s['lane']} · status {s.get('status')}"
                       + (f" · why this form exists: {s['why']}" if s.get("why") else "")
                       + (f" · applies if {s['applies_if']}" if s.get("applies_if") else "")
                       + f" · already known: {json.dumps(s.get('known') or {}, ensure_ascii=False)}" for s in st["stages"])
    starter = "\n".join(f"- {sid}: " + "; ".join(f"{q['id']} ({q['type']}): {q['text']}" for q in s["questions"])
                        for sid, s in qs["stages"].items())
    return {"brand_voice": voice(brand, root), "people": ppl, "words": wds, "stages": stages, "starter": starter,
            "rules": RULES}, {"profiles": pids, "row_ids": sorted(wids), "config_from": origin}, (st, qs)


def parse(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise SystemExit("The model's answer held no JSON.")
    return json.loads(m.group(0))


def merge(qs, answer, row_ids):
    """The brand's questions file with each stage's questions, title, intro and email from the answer. Problems as sentences."""
    out, bad = copy.deepcopy(qs), []
    stages = answer.get("stages") or {}
    for sid, st in out["stages"].items():
        new = stages.get(sid)
        if not new:
            bad.append(f"{sid}: the answer has no questions for this stage")
            continue
        for q in new.get("questions") or []:
            if q.get("type") == "choice" and not 3 <= len(q.get("options") or []) <= 6:
                bad.append(f"{sid}/{q.get('id')}: {len(q.get('options') or [])} options (keep it to 3–6, plus other)")
            stray = [i for i in q.get("language_used") or [] if i not in row_ids]
            if stray:
                bad.append(f"{sid}/{q.get('id')}: cites lines it was not given ({', '.join(stray[:3])})")
        st["title"], st["intro"] = new.get("title", st.get("title")), new.get("intro", st.get("intro"))
        st["questions"] = new.get("questions") or st["questions"]
        st["email"] = {**(st.get("email") or {}), **(new.get("email") or {})}
        st["why"] = new.get("why", "")
    out["form_version"] = dt.date.today().isoformat() + ".research"
    return out, bad


def main(argv=None, runner=None):
    ap = argparse.ArgumentParser(description="Write a brand's feedback questions from its research.")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--packet", action="store_true", help="write the research packet only; no model")
    a = ap.parse_args(argv)
    from run_kit import filing
    from run_kit.stage import Chain
    label = a.label or dt.date.today().isoformat()
    out = filing.run_dir(TOOL, a.brand, f"questions-{label}")
    fields, meta, (st, qs) = packet(a.brand)
    (out / "packet.json").write_text(json.dumps({**meta, **fields}, indent=1, ensure_ascii=False) + "\n")
    print(f"packet: {len(meta['profiles'])} profiles, {len(meta['row_ids'])} customer lines, stages from the {meta['config_from']}")
    if a.packet:
        return 0
    chain = Chain(TOOL, a.brand, label, out, HERE / "prompts", STEPS, assignment={"brand": a.brand},
                  dry=a.dry_run, runner=runner)
    text = chain.run("questions", **fields)
    if a.dry_run:
        print(f"dry run -> {out}")
        return 0
    answer = parse(text)
    (out / "answer.json").write_text(json.dumps(answer, indent=1, ensure_ascii=False) + "\n")
    proposal, bad = merge(qs, answer, set(meta["row_ids"]))
    bad += B.check(st, proposal)
    deliver = out / "deliverable"
    deliver.mkdir(exist_ok=True)
    (deliver / "feedback-questions.json").write_text(json.dumps(proposal, indent=1, ensure_ascii=False) + "\n")
    lines = [f"# Feedback questions from research · {a.brand} · {label}", "",
             f"Target: brands/{a.brand}/operations/feedback-questions.json (applied by a person on the owner's yes).", ""]
    for sid, s in proposal["stages"].items():
        lines += [f"## {sid} — {s.get('title', '')}", f"_{s.get('why', '')}_", ""]
        lines += [f"{q['n']}. {q['text']}" + (f" — {' / '.join(q['options'])}" if q.get("options") else "")
                  + (f"  ·  fills {q['fills']}" if q.get("fills") else "") for q in s["questions"]] + [""]
    if bad:
        lines += ["## Held", ""] + [f"- {x}" for x in bad]
    (out / "PROPOSAL.md").write_text("\n".join(lines) + "\n")
    print(("HELD: " + "; ".join(bad[:3])) if bad else f"proposal -> {deliver / 'feedback-questions.json'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
