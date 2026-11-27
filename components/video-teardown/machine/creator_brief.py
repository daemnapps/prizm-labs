#!/usr/bin/env python3
"""
creator_brief.py — THE creator brief, filed as one file with its tags.

    python3 machine/creator_brief.py file  <run dir | label>     (re)write <run>/brief--video--creator.md
    python3 machine/creator_brief.py show  <brief--video--creator.md>    print the parsed brief as JSON
    python3 machine/creator_brief.py check <brief--video--creator.md>    exit 0 clean / 1 findings

**One creator brief** (2026-11-15, the creator system). The page stage 7b
writes is the brief a creator films from — the shape ruled 2026-09-18: format ·
inspired by · product · length · core idea · two hooks · five beats · must-have
shots · product points, then the script, no pictures. Stage 5 is OUR spec and
never goes to a creator. This module adds nothing to the words: it reads the
page and the run, puts the tags the rest of the system routes on at the top,
and writes ONE file per brief:

    <run>/brief--video--creator.md      → filed to runs/video-writing/<brand>/<slug>/brief--video--creator.md

The contract (fields, path, who reads it) is components/briefs/creator-brief/README.md.
Readers (delivery, the creator hub, the numbers loop) call `read(path)` and
never parse the page themselves. Python 3.9, stdlib only, no model, no network.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "brief--video--creator.md"     # the briefs naming rule: brief--<asset>--<actor>.md
CONTRACT = 1                       # bump when a field is renamed or removed

# The page's own bold field lines, in the order 7b writes them.
FIELD_LINES = {
    "Format": "format_name",
    "Inspired by": "inspired_by",
    "Primary product": "product_line",
    "Suggested length": "length",
    "Sound": "sound",
    "Swipe file": "swipe_link",
}
SECTIONS = {
    "Core Idea": "core_idea",
    "Suggested Hook Directions": "hooks",
    "Key Story Beats": "beats",
    "Must-Have Shots": "shots",
    "Product Points to Include": "product_points",
    "How to Say It": "how_to_say",
}
LIST_SECTIONS = {"hooks", "beats", "shots", "product_points", "how_to_say"}
SCRIPT_HEAD = re.compile(r"^##\s*The (?:script|cards)\b.*$", re.M)   # spoken formats / card formats

# The tags, in the order they are written. Every one is always present;
# an unknown value is "" — never guessed.
TAGS = ("contract", "brief_id", "brand", "product", "product_name", "format",
        "format_name", "angle", "avatar", "sub", "awareness", "lane", "length",
        "swipe_link", "source_post", "swipe_id", "creator", "run", "prompt",
        "written", "status", "open_notes")


# ── reading the run ──────────────────────────────────────────────────────

def _run_dir(arg):
    p = Path(arg)
    if (p / "run.json").is_file():
        return p
    sys.path.insert(0, str(HERE))
    import workdir                                     # noqa: E402
    return workdir.run_dir(arg)


def piece_of(text):
    """The `piece` block stage 5 ends on (avatar, angle, format, lane …) or {}."""
    for block in re.findall(r"```json\s*(\{.*?\})\s*```", text or "", re.S):
        try:
            d = json.loads(block)
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("piece"), dict):
            return d["piece"]
    return {}


AUDIT_ROW = re.compile(r"^\|\s*\**\s*(1b|1c|3|4[a-g])\s*\**\s*\|\s*(.+?)\s*\|\s*$", re.M)


def audit_fixes(text):
    """The audit's RE-RUN fixes: [{"at": "4d", "fix": "…"}] from its VERDICT table; [] when it ships.

    Read by the chain (the creator route's audit re-run sends these back) and by the
    brief file (a fix the owner passed by number stays on the brief as an open note)."""
    m = re.search(r"VERDICT\W*\s*(SHIP|RE-RUN|STOP)", text or "", re.I)
    if not m or m.group(1).upper() == "SHIP":
        return []
    # the verdict ends at the next heading, rule, or the check table (bold or ## heading)
    nxt = re.search(r"^(?:##\s|---\s*$|\**CHECK TABLE)", text[m.end():], re.M)
    section = text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]
    out = []
    for at, fix in AUDIT_ROW.findall(section):
        out.append({"at": at, "fix": " ".join(fix.replace("**", "").split())})
    if out:
        return out
    # audit v13 writes the verdict as prose: "RE-RUN 4e, the close pass … 1. … 2. …"
    stages = re.findall(r"RE-RUN\W*\s+((?:1b|1c|3|4[a-g])(?:\s*(?:,|and|\+)\s*(?:1b|1c|3|4[a-g]))*)",
                        text[m.start(1): m.end()] + section, re.I)
    body = " ".join(section.replace("**", "").split())
    for group in stages[:1]:
        for at in re.findall(r"1b|1c|3|4[a-g]", group):
            out.append({"at": at, "fix": body})
    return out


def _clean(v):
    v = str(v or "").strip()
    return "" if v.lower() in ("none", "null", "n/a", "unassigned") or v.startswith("⟨") else v


def tags_for(run_dir, page_fields, st=None):
    """Every tag, from run.json, stage 5's piece block and the page itself."""
    run_dir = Path(run_dir)
    st = st if st is not None else json.loads((run_dir / "run.json").read_text())
    stages = st.get("stages") or {}
    piece = {}
    rec5 = stages.get("stage5") or {}
    if rec5.get("out") and (run_dir / rec5["out"]).is_file():
        piece = piece_of((run_dir / rec5["out"]).read_text())
    aud = st.get("audience") or {}
    rec7b = stages.get("stage7b") or {}
    q = st.get("queue_item") or {}                  # set when the run came off the swipe-pick queue
    slug = st.get("slug") or run_dir.name
    product_line = page_fields.get("product_line", "")
    return {
        "contract": CONTRACT,
        "brief_id": slug,
        "brand": st.get("brand") or "",
        "product": _clean(st.get("product")),
        "product_name": product_line.split(" · ")[0].strip(),
        "format": _clean(piece.get("format")) or _clean(st.get("format_id")),
        "format_name": page_fields.get("format_name", ""),
        "angle": _clean(piece.get("angle")),
        "avatar": _clean(piece.get("avatar")) or _clean(aud.get("_avatar")),
        "sub": _clean(piece.get("sub")) or _clean(aud.get("_sub_avatar")),
        "awareness": _clean(piece.get("awareness")) or _clean((st.get("market_state") or {}).get("awareness")),
        "lane": _clean(piece.get("lane")) or _clean(st.get("lane")),
        "length": page_fields.get("length", ""),
        "swipe_link": _clean(page_fields.get("swipe_link")),
        "source_post": _clean(q.get("source_url")) or _clean(st.get("origin_url")),
        "swipe_id": _clean(q.get("swipe_id")),
        "creator": _clean(st.get("creator")),
        "run": f"runs/video-writing/{st.get('brand') or ''}/{slug}",
        "prompt": Path(str(rec7b.get("prompt_name") or rec7b.get("prompt_file") or "")).name,
        "written": (str(rec7b.get("finished") or "")[:10] or date.today().isoformat()),
        "status": "draft",                          # draft until the owner's yes (rule 6 words only)
        "open_notes": _open_notes(run_dir, stages),
    }


def _open_notes(run_dir, stages):
    """The audit fixes still open on this brief: it was passed by number, not re-written."""
    rec = stages.get("stage4e") or {}
    f = Path(run_dir) / (rec.get("out") or "stages/4f-audit.md")
    if not f.is_file():
        return []
    return [f"{x['at']}: {x['fix']}" for x in audit_fixes(f.read_text())]


# ── the page ─────────────────────────────────────────────────────────────

def parse_page(text):
    """The 7b page → {title, the field lines, the sections, script}."""
    out = {"title": "", "script": ""}
    m = re.search(r"^#\s+(.+)$", text, re.M)
    if m:
        out["title"] = m.group(1).strip()
    sm = SCRIPT_HEAD.search(text)
    head, script = (text[:sm.start()], text[sm.end():]) if sm else (text, "")
    if script:
        lines = [l for l in script.strip().split("\n\n") if l.strip()]
        if lines and lines[0].lower().startswith(("read it as-is", "nothing is spoken")):
            lines = lines[1:]
        out["script"] = "\n\n".join(l.strip() for l in lines)
    for label, key in FIELD_LINES.items():
        fm = re.search(r"^\*\*" + re.escape(label) + r":\*\*\s*(.+)$", head, re.M)
        out[key] = fm.group(1).strip() if fm else ""
    names = "|".join(re.escape(s) for s in SECTIONS)
    parts = re.split(r"^\*\*(" + names + r")\*\*\s*$", head, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        key, body = SECTIONS[parts[i]], parts[i + 1].strip()
        if key in LIST_SECTIONS:
            items = [re.sub(r"^(\d+\.|-)\s+", "", l).strip()
                     for l in body.splitlines() if re.match(r"^\s*(\d+\.|-)\s+", l)]
            out[key] = [x.strip('"“”') if key == "hooks" else x for x in items]
        else:
            out[key] = " ".join(body.split())
    for key in SECTIONS.values():
        out.setdefault(key, [] if key in LIST_SECTIONS else "")
    return out


def _front(tags):
    lines = ["---"]
    for k in TAGS:
        v = tags.get(k, "")
        if isinstance(v, list):
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
            continue
        lines.append(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, str) and (':' in v or v != v.strip()) else v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _unfront(text):
    m = re.match(r"\A---\n(.*?)\n---\n\n?", text, re.S)
    if not m:
        return {}, text
    tags = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        v = v.strip()
        if v.startswith('"') or v.startswith("["):
            try:
                v = json.loads(v)
            except ValueError:
                pass
        tags[k.strip()] = int(v) if k.strip() == "contract" and str(v).isdigit() else v
    return tags, text[m.end():]


# ── the three verbs ──────────────────────────────────────────────────────

def file(run_dir, st=None, page=None, prompt=None):
    """Write <run>/brief--video--creator.md from the run's 7b page. -> Path or None.
    The chain passes its live `st`, the page it just wrote and the prompt it
    sent, because run.json on disk is saved after this runs."""
    run_dir = Path(run_dir)
    st = st if st is not None else json.loads((run_dir / "run.json").read_text())
    rec = (st.get("stages") or {}).get("stage7b") or {}
    page = Path(page) if page else run_dir / (rec.get("out") or "stages/7b-page.md")
    if not page.is_file():
        return None
    body = page.read_text()
    tags = tags_for(run_dir, parse_page(body), st=st)
    if prompt:
        tags["prompt"] = Path(str(prompt)).name
    out = run_dir / NAME
    out.write_text(_front(tags) + body.lstrip())
    return out


def read(path):
    """A brief--video--creator.md → one dict: every tag, then the page's parts.

    {contract, brief_id, brand, product, …, status,
     title, format_name, inspired_by, product_line, length, sound, swipe_link,
     core_idea, hooks[], beats[], shots[], product_points[], how_to_say[],
     script, page}   — `page` is the brief's Markdown without the tags."""
    tags, body = _unfront(Path(path).read_text())
    parts = parse_page(body)
    out = dict(tags)
    for k, v in parts.items():
        if k in ("format_name", "length", "swipe_link") and out.get(k):
            continue                          # the tag wins; it was read off the same line
        out[k] = v
    out["page"] = body
    return out


def never_list(position_text):
    """The position's NEVER line, split into its phrases."""
    m = re.search(r"^NEVER:\s*(.+)$", position_text or "", re.M)
    if not m:
        return []
    out = []
    for p in m.group(1).split("·"):
        quoted = re.findall(r'["“]([^"”]+)["”]', p)
        if quoted:                                  # a quoted phrase is a phrase
            out.extend(q.strip() for q in quoted if q.strip())
            continue
        p = re.sub(r"\([^)]*\)", "", p).strip()
        if p and not p.startswith("a "):            # "a results claim …" is a rule, not a phrase
            out.append(p)
    return out


def check(path, position_text=None):
    """The contract, checked. -> list of findings (empty = clean)."""
    b = read(path)
    f = []
    for k in TAGS:
        if k not in b:
            f.append(f"tag missing: {k}")
    for k in ("brief_id", "brand", "product_name", "format_name", "length"):
        if not b.get(k):
            f.append(f"tag empty: {k}")
    if not b.get("title"):
        f.append("no title")
    if not b.get("core_idea"):
        f.append("no Core Idea")
    if not 2 <= len(b.get("hooks") or []) <= 3:
        f.append(f"hooks: {len(b.get('hooks') or [])} (2–3)")
    if not 4 <= len(b.get("beats") or []) <= 5:
        f.append(f"beats: {len(b.get('beats') or [])} (4–5)")
    if not 3 <= len(b.get("shots") or []) <= 6:
        f.append(f"shots: {len(b.get('shots') or [])} (3–6)")
    if not 2 <= len(b.get("product_points") or []) <= 3:
        f.append(f"product points: {len(b.get('product_points') or [])} (2–3)")
    if re.search(r"!\[|\.(png|jpe?g|webp)\b", b.get("page") or "", re.I):
        f.append("a picture in the brief")
    if b.get("status") not in ("draft", "approved", "deprecated"):
        f.append(f"status word: {b.get('status')!r}")
    if position_text is None and b.get("brand"):
        pos = HERE.parents[2] / "brands" / b["brand"] / "brand-identity" / "position.md"
        position_text = pos.read_text() if pos.is_file() else ""
    low = (b.get("page") or "").lower()
    for phrase in never_list(position_text or ""):
        if phrase.lower() in low:
            f.append(f"position NEVER phrase on the page: {phrase!r}")
    return f


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) != 2 or a[0] not in ("file", "show", "check"):
        print(__doc__)
        return 2
    verb, arg = a
    if verb == "file":
        out = file(_run_dir(arg))
        if not out:
            print("no 7b page in that run yet")
            return 1
        print(out)
        return 0
    if verb == "show":
        print(json.dumps(read(arg), indent=1, ensure_ascii=False))
        return 0
    found = check(arg)
    print("clean" if not found else "\n".join("- " + x for x in found))
    return 0 if not found else 1


if __name__ == "__main__":
    sys.exit(main())
