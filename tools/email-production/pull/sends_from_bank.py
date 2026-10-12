#!/usr/bin/env python3
"""The brand's designed emails, as its send library.

    python3 pull/sends_from_bank.py --brand brand-a

A brand whose Klaviyo history is not on file still has every email it ever
designed: the Figma file that went through workflow 2 (the format bank,
`results/format-bank-<brand>/`). This turns each of those into one file in
`email-sms/sends/`, proposed under
`runs/email-production/<brand>/facts-<YYYY-MM-DD>/` (K2 (brands write wall);
a person folds it into brands/), in the same shape as the emails pulled from
Klaviyo (`pull/index_sends.py`): subject, meta, then the copy, buttons and
pictures in reading order. The chain swipes them exactly like sent email;
`pull/classify.py` tags them; the calendar then finds a source per slot.

Dates: a Figma frame carries no send date. Frames named `NN-Month-…` get that
month's ordinal day of the file's year; everything else gets the board's
year with the frame's order as its day, and `date_note` says so. Sorting by
date still puts the newest designs first, which is all the calendar needs.
Written 2026-09-09.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import HERE  # noqa: E402
import facts_proposal  # noqa: E402

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:60] or "untitled"


def date_for(board, name, index, year):
    m = re.match(r"(\d{1,2})-([A-Za-z]+)", name or "")
    if m and m.group(2).lower() in MONTHS:
        return f"{year}-{MONTHS[m.group(2).lower()]:02d}-{min(int(m.group(1)), 28):02d}", None
    day = min(index, 28)
    return f"{year}-01-{day:02d}", "no send date on the frame — the board's order, not a date"


def body_of(spec):
    lines = []
    for sec in spec.get("sections", []):
        for b in sec.get("blocks", []):
            k = b.get("block")
            if k == "text":
                t = (b.get("text") or "").strip()
                if t:
                    lines.append(t.replace("\n", " / ") if b.get("role") in ("display", "headline") else t)
            elif k == "cta":
                lines.append(f"[BUTTON {b.get('label', '').strip()}]")
            elif k == "image":
                src = b.get("source") or ""
                m = re.search(r"baked-in copy: [“\"](.+?)[”\"]\s*$", src, re.S)
                alt = m.group(1) if m else "photo"
                lines.append(f"[IMAGE alt={alt}] ({b.get('size', '')})")
            elif k in ("panel", "glass", "tile"):
                for c in b.get("contains", []) or []:
                    if isinstance(c, dict) and c.get("text"):
                        lines.append(c["text"].strip())
                    elif isinstance(c, dict) and c.get("label"):
                        lines.append(f"[BUTTON {c['label'].strip()}]")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def first_display(spec):
    for sec in spec.get("sections", []):
        for b in sec.get("blocks", []):
            if b.get("block") == "text" and b.get("role") in ("display", "headline") and (b.get("text") or "").strip():
                return b["text"].strip().replace("\n", " ")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--subjects", default=None, help="json {frame name: subject} read off the board (optional)")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    a = ap.parse_args()
    bank = HERE / "results" / f"format-bank-{a.brand}"
    if not bank.is_dir():
        sys.exit(f"no bank at {bank} — run workflow 2 first")
    subjects = json.loads(Path(a.subjects).read_text()) if a.subjects else {}
    run = facts_proposal.run_dir(a.brand, a.label)
    index, seen = [], set()
    for board in sorted(p for p in bank.iterdir() if p.is_dir() and (p / "rects.json").is_file()):
        rects = json.loads((board / "rects.json").read_text())
        year = a.year - (1 if "2025" in board.name else 0)
        for i in range(1, len(rects) + 1):
            spec_f = board / f"{i:02d}-spec.json"
            if not spec_f.is_file():
                continue
            spec = json.loads(spec_f.read_text())
            # the spec's export picture is NN.png = rects[NN-1]: that is the frame it was read off
            m_ = re.match(r"(\d+)", spec.get("export_picture") or "")
            r = rects[int(m_.group(1)) - 1] if m_ and int(m_.group(1)) <= len(rects) else rects[i - 1]
            name = r.get("name") or f"{board.name} #{i}"
            sent, note = date_for(board.name, name, i, year)
            subject = subjects.get(name) or first_display(spec) or name
            body = body_of(spec)
            key = (subject, len(body))
            if key in seen:                       # the same design twice on the board
                continue
            seen.add(key)
            fname = f"{sent}--{slug(subject)}.md"
            n = 2
            while fname in {x["file"] for x in index}:
                fname = f"{sent}--{slug(subject)}-{n}.md"; n += 1
            flow = bool(re.search(r"flow|welcome|post.?purchase", board.name + " " + name, re.I))
            meta = [f"- sent: {sent}", f"- from: {a.brand}", f"- preview: ", f"- audiences: ",
                    f"- campaign: {'FLOW' if flow else 'CAMPAIGN'} | {name}",
                    f"- id: figma:{board.name}#{i:02d}",
                    f"- source: the brand's Figma file (workflow 2 intake), frame “{name}” on board “{board.name}”"]
            if note:
                meta.append(f"- date_note: {note}")
            facts_proposal.write(run, a.brand, f"email-sms/sends/{fname}", f"# {subject}\n\n" + "\n".join(meta) + "\n\n---\n\n" + body)
            index.append({"sent": sent, "subject": subject, "preview": "", "from": a.brand,
                          "campaign": f"{'FLOW' if flow else 'CAMPAIGN'} | {name}", "file": fname,
                          "chars": len(body), "board": board.name, "frame": name, "date_note": note})
    facts_proposal.write(run, a.brand, "email-sms/sends/index.json", json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(index)} sends proposed (from {bank.name})")
    print(f"proposal -> {facts_proposal.note(run, a.brand)}")


if __name__ == "__main__":
    main()
