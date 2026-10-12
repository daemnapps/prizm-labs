"""Interviews and panels — new transcripts dropped in the brand's inbox, into
the avatar's bank.

    python3 components/research-gatherer/gather.py interviews --brand B [--dry-run] [--avatar A]

Built 2026-09-29 (free sources run on a trigger). The inbox is the brand's own
config — `operations/language-pulls.json` › `interviews`:

    {"inbox": "core-avatars/<avatar>/language/evidence/inbox",   (under brands/<brand>/)
     "company_speakers": ["<first name>", …]}                    (our side of the call)

Drop a transcript `.md` (or `.vtt` / `.txt`) in the inbox. Optional front
matter at the top of the file says what it is:

    ---
    kind: interview | panel          (default interview)
    date: 2026-09-30                 (default: a date in the file name, else undated)
    relationship: customer | unknown (default customer for an interview, unknown for a panel)
    company: [Sam, Alex]                  (added to company_speakers for this file)
    customers: [Robin]                (when given, ONLY these speakers are read)
    ---

The file is split into speaker turns (`Name: words`, `**Name:** words`,
WebVTT `<v Name>words`); consecutive lines by one speaker are one turn. Only
the customer's turns become rows — every speaker not on our side, or only the
named customers. A file where nobody's side is named is held, never guessed.
Speaker names are never stored; a turn is cited `<file> turn <n>`.
Source id `interview_<brand>_<date>` / `panel_<brand>_<date>`. Ingested files
are recorded in runs/research/<brand>/interviews-state.json (only when
nothing from them was held); a file already there is never read twice.
"""
import argparse
import hashlib
import re
from pathlib import Path

from . import annotate as A
from . import engine
from . import voicepull as V

say = V.say
FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
VTT_V = re.compile(r"^<v\s+([^>]+)>(.*?)(?:</v>)?$")
LABEL = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*|__)?([A-Z][\w.'’ -]{0,40}?)(?:\*\*|__)?\s*:\s*(?:\*\*|__)?\s*(.+)$")
NOISE = re.compile(r"^\s*(WEBVTT|NOTE\b|\d+\s*$|\d{1,2}:\d{2}(:\d{2})?([.,]\d+)?\s*-->.*|\[\d{1,2}:\d{2}(:\d{2})?\]\s*$|#+\s)", re.I)
STAMP = re.compile(r"^\s*[\[(]?\d{1,2}:\d{2}(:\d{2})?[\])]?\s*")
MIN_WORDS = 4


def front_matter(text):
    m = FRONT.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
        meta[k.strip().lower()] = v
    return meta, text[m.end():]


def turns(text):
    """[(speaker, words)] — consecutive lines by one speaker joined."""
    out = []
    for line in text.splitlines():
        if not line.strip() or NOISE.match(line):
            continue
        line = STAMP.sub("", line)
        m = VTT_V.match(line.strip()) or LABEL.match(line)
        if m:
            who, words = m.group(1).strip(), m.group(2).strip()
            if out and out[-1][0] == who:
                out[-1] = (who, out[-1][1] + " " + words)
            else:
                out.append((who, words))
        elif out:
            out[-1] = (out[-1][0], out[-1][1] + " " + line.strip())
    return out


def _is(name, names):
    n = name.lower()
    return any(n == x.lower() or n.split()[0] == x.lower().split()[0] for x in names if x)


def rows_from_transcript(rel, text, brand, today, company=(), default_date="undated"):
    """A transcript -> (rows, meta, why-held). Pure — the tests call it."""
    meta, body = front_matter(text)
    kind = "panel" if str(meta.get("kind", "")).lower() in ("panel", "focus-group", "focus group") else "interview"
    date = str(meta.get("date") or "") or (re.search(r"(\d{4}-\d{2}-\d{2})", rel) or [None, default_date])[1]
    ours = list(company) + (meta.get("company") if isinstance(meta.get("company"), list) else [])
    theirs = meta.get("customers") if isinstance(meta.get("customers"), list) else []
    if not ours and not theirs:
        return [], meta, "nobody's side is named (company_speakers in language-pulls.json, or company:/customers: in the file)"
    rel_default = "customer" if kind == "interview" else "unknown"
    relationship = "ordered" if str(meta.get("relationship") or rel_default).lower() in ("customer", "ordered") \
        else f"{kind} participant, relationship unknown"
    sid = f"{kind}_{brand}_{date}"
    out = []
    for n, (who, words) in enumerate(turns(body), 1):
        keep = _is(who, theirs) if theirs else not _is(who, ours)
        if not keep or len(words.split()) < MIN_WORDS:
            continue
        out.append(dict(kind=kind, text=A.clean(words), said=date if date != "undated" else None, pulled=today,
                        ref=f"{rel} turn {n}", item=f"turn-{n}",
                        source_name=(f"customer interview {date}" if kind == "interview" else f"panel {date}"),
                        source_type="interview" if kind == "interview" else "focus-group",
                        source_id=sid, source_kind=kind, property=brand, relationship=relationship))
    return out, meta, None


def main(argv=None, labeller=None, claude=None):
    ap = argparse.ArgumentParser(prog="gather.py interviews")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--dry-run", action="store_true", help="split and count; read and file nothing")
    a = ap.parse_args(argv)
    c = V.cfg("interviews")
    bj = V.brand_json(a.brand)
    label = bj.get("label") or a.brand
    conf = bj.get("interviews") or {}
    now, today, run_label = V.now_labels()
    say(f"interviews · {a.brand}{' · DRY RUN' if a.dry_run else ''}")
    if not conf.get("inbox"):
        say("  no interviews inbox in language-pulls.json — nothing to read")
        return 0
    avatar = V.avatar_for(a.brand, bj, a.avatar)
    if not avatar:
        say("  name the avatar (--avatar, or language_avatar in language-pulls.json)")
        return 2
    bdir = engine.WORKSPACE / "brands" / a.brand
    inbox = bdir / conf["inbox"]
    files = sorted(p for p in inbox.glob("*") if p.suffix.lower() in (".md", ".vtt", ".txt")
                   and p.name.lower() not in ("readme.md",)) if inbox.is_dir() else []
    state = V.load_state(a.brand, "interviews")
    done = state.get("ingested") or {}
    notes, rows, per_file = [], [], {}
    for f in files:
        rel = str(f.relative_to(engine.WORKSPACE))
        if rel in done:
            continue
        text = f.read_text(errors="replace")
        got, meta, why = rows_from_transcript(rel, text, a.brand, today, conf.get("company_speakers") or [])
        if why:
            notes.append(f"{f.name}: held — {why}")
            say(f"  {f.name}: HELD — {why}")
            continue
        per_file[rel] = dict(rows=len(got), sha=hashlib.sha1(text.encode()).hexdigest()[:12], refs={r["ref"] for r in got})
        say(f"  {f.name}: {len(got)} customer turns")
        rows += got
    if not files:
        say(f"  inbox empty ({inbox.relative_to(engine.WORKSPACE)})")
    fresh, filed, dropped, held = V.file_rows(a.brand, avatar, label, rows, "customer interview transcripts", c,
                                              run_label, a.dry_run, labeller=labeller, claude=claude)
    held_refs = {r["ref"] for r in held}

    def record():
        for rel, d in per_file.items():
            if not (d["refs"] & held_refs):
                done[rel] = {"sha": d["sha"], "rows": d["rows"], "at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        state["ingested"] = done
        V.save_state(a.brand, "interviews", state)

    if filed is None:
        say("  dry run — nothing read, nothing filed" if a.dry_run else "  nothing new")
        if not a.dry_run and per_file:
            record()
        return 0
    V.write_run(a.brand, "interviews", label, run_label, "files not yet ingested", filed, dropped, held, notes,
                extra={"avatar": avatar, "files": {k: v["rows"] for k, v in per_file.items()}},
                intro="New interview and panel transcripts from the brand's inbox — the customer's own turns only. "
                      "Every row below is now in the brand's language bank, with its lane, awareness level and "
                      "sophistication signal.")
    record()
    return 0
