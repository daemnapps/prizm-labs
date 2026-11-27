#!/usr/bin/env python3
"""What a brand actually knows, indexed so a stage can choose from it.

The chain used to read four hard-wired files per brand. Everything else the
brand knew — objections, spent hooks, the creator's own profile, competitor
teardowns, raw voice-of-customer evidence — was invisible to it, so every
video got the same context and the copy came out generically on-brand. This
builds the menu; stage 0 does the choosing.

Nothing here writes to brands/. The index is derived at run time from the
files as they stand, so it can never drift from them.
"""

import re
from pathlib import Path

from paths import HERE, WORKSPACE

# Machine-readable dumps a language model cannot usefully read in full. They
# are named in the index anyway — a stage should know they exist and that a
# person has to go through them — but never loaded.
TOO_BIG = 120_000
SKIP_SUFFIX = {".json", ".csv"}

FRONT = ("status", "contested", "known-issues", "provenance", "authority")


def _is_bank(p):
    """A JSON verbatim bank, as opposed to config or scraped data."""
    try:
        import json as _j
        d = _j.loads(p.read_text())
        return isinstance(d, dict) and isinstance(d.get("entries"), list) and d["entries"]
    except Exception:
        return False


def _bank_meta(p):
    import json as _j
    d = _j.loads(p.read_text())
    return len(d.get("entries") or []), d


def _front_matter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([a-z-]+):\s*(.+)$", line.strip())
        if m and m.group(1) in FRONT:
            out[m.group(1)] = m.group(2).strip()
    return out


def _title(text, path):
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else path.stem.replace("-", " ")


def _gist(text):
    """First real sentence of the body — enough to tell what the file is."""
    body = text
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end >= 0:
            body = body[end + 4:]
    body = re.sub(r"^#.*$", "", body, flags=re.M)
    body = re.sub(r"\s+", " ", body).strip()
    return body[:220]


def entries(brand):
    """Every context file this brand has, with the standing it declares."""
    root = WORKSPACE / "brands" / brand
    if not root.is_dir():
        return []
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        rel = p.relative_to(WORKSPACE)
        size = p.stat().st_size
        rec = dict(path=str(rel), kb=round(size / 1024, 1), loadable=True)
        if p.suffix == ".json" and _is_bank(p):
            # a sourced-verbatim bank: readable, rendered to quotes on load
            n, meta = _bank_meta(p)
            rec.update(title=f"{meta.get('avatar','?')} · {meta.get('funnel','?')} verbatims",
                       gist=(meta.get("note") or
                             f"{n} sourced verbatims, each carrying who said it "
                             f"and where it came from."))
            out.append(rec)
            continue
        if p.suffix in SKIP_SUFFIX or size > TOO_BIG:
            rec.update(loadable=False, title=p.stem.replace("-", " "),
                       gist=f"{p.suffix.lstrip('.').upper()} data, "
                            f"{round(size/1024):,} KB — too large to read in a prompt; "
                            f"a person has to work through it")
            out.append(rec)
            continue
        try:
            text = p.read_text()
        except Exception:
            continue
        fm = _front_matter(text)
        rec.update(title=_title(text, p), gist=_gist(text))
        for k in FRONT:
            if fm.get(k):
                rec[k] = fm[k]
        out.append(rec)
    return out


def index(brand, always=()):
    """The menu, as a stage reads it. `always` marks the files the chain
    loads regardless, so the scout spends its attention on the rest."""
    lines = []
    for e in entries(brand):
        bits = [f"- `{e['path']}` ({e['kb']} KB) — **{e['title']}**"]
        if e["path"] in always:
            bits.append(" _[already loaded every run]_")
        if not e["loadable"]:
            bits.append(" _[NOT LOADABLE]_")
        lines.append("".join(bits))
        lines.append(f"  {e['gist']}")
        for k in ("status", "contested", "known-issues"):
            if e.get(k):
                lines.append(f"  _{k}_: {e[k]}")
    return "\n".join(lines)


def render_json_bank(path, cap=60_000):
    """A sourced-verbatim bank as readable evidence.

    Language banks arrive as JSON `entries` — each a real thing someone said,
    with its provenance. A prompt cannot read raw JSON usefully and the whole
    file is far too big, so entries become quoted lines carrying who said them
    and where it came from. Provenance travels with the quote: a verbatim
    whose source is unknown is worth less than one that names a panel, a
    ticket or an interview, and a stage should be able to tell them apart.
    """
    import json as _json
    try:
        d = _json.loads(Path(path).read_text())
    except Exception as e:
        return f"(could not read {path}: {e})"
    entries = d.get("entries") if isinstance(d, dict) else None
    if not entries:
        return ""
    head = (f"# {d.get('avatar','?')} · {d.get('funnel','?')} "
            f"· {len(entries)} sourced verbatims")
    if d.get("note"):
        head += f"\n_{d['note']}_"
    out, used = [head], len(head)
    for e in entries:
        t = (e.get("text") or "").strip()
        if not t:
            continue
        src = (e.get("source") or {}).get("name") or "source not recorded"
        who = e.get("speaker") or "unattributed"
        line = f'- "{t}"  \n  _{who} · {src}_'
        if used + len(line) > cap:
            out.append(f"\n_({len(entries)} entries total; the rest were over "
                       f"the reading budget and were not shown.)_")
            break
        out.append(line)
        used += len(line)
    return "\n".join(out)


def load(paths, budget=90_000):
    """Read what stage 0 chose, newest-first within a character budget.

    A stage that asks for 400 KB gets the first slice of it and a plain note
    saying what was dropped — silently truncating would read as though the
    whole thing had been considered."""
    chunks, used, dropped = [], 0, []
    for rel in paths:
        p = WORKSPACE / rel
        if not p.is_file():
            dropped.append(f"{rel} (not found)")
            continue
        if p.suffix == ".json":
            text = render_json_bank(p).strip()
            if not text:
                dropped.append(f"{rel} (json, no readable entries)")
                continue
        elif p.suffix in SKIP_SUFFIX or p.stat().st_size > TOO_BIG:
            dropped.append(f"{rel} (not loadable in a prompt)")
            continue
        else:
            text = p.read_text().strip()
        if used + len(text) > budget:
            dropped.append(f"{rel} ({round(len(text)/1024)} KB, over budget)")
            continue
        chunks.append(f"--- {rel} ---\n\n{text}\n")
        used += len(text)
    body = "\n".join(chunks) if chunks else "(nothing selected)"
    if dropped:
        body += ("\n\n--- NOT INCLUDED ---\n"
                 "These were selected but not loaded, so nothing below was written "
                 "with them in view:\n" + "\n".join(f"- {d}" for d in dropped) + "\n")
    return body, used, dropped


def parse_choice(text):
    """Pull the chosen paths out of stage 0's answer. It writes them one per
    line under a LOAD: heading; anything that is not a real brand path is
    ignored rather than guessed at."""
    picks = []
    for m in re.finditer(r"^\s*[-*]?\s*`?(brands/[^\s`]+\.(?:md|txt))`?\s*$",
                         text, re.M):
        rel = m.group(1)
        if rel not in picks:
            picks.append(rel)
    return picks
