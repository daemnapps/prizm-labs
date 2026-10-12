"""Retag — add culture tags to rows already in the bank.

    python3 components/research-gatherer/gather.py retag --culture --brand B [--avatar A] [--limit N] [--apply] [--dry-run]

the owner, 2026-10-06 (the bottom-up culture build): the culture map is built
from the bank's own rows, so the rows people wrote in comment sections and
communities are re-read for the seven culture tags (`annotate.CULTURE_TAGS`:
taste, cringe, subculture, in-word, community-voice, role-claimed, and the
new `laugh`). The read is `prompts/culture-tags-v1-damon.md`, shown word for
word on every run's report.

Which rows: every row in the avatar bank (sub-avatar folders included, never
`used/`) whose `source.type` is comment, community or creator-comment and
that this read has not seen with these exact words
(`runs/research/<brand>/retag-culture-state.json`), most-liked first, up to
`--limit`. Rows are read in batches (`--batch`, default 40), `--jobs` batches
at a time, on the model and `claude -p` convention the intake read uses.

It only ever ADDS: the proposal carries `add_use` per row (a tag already on
the row is left out of it) and `gather.py apply` unions it into `use` —
never a tag removed, never the words touched. A batch the model cannot
answer is left unread and is picked up next run.
"""
import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import engine
from . import annotate as A

PROMPT = engine.ROOT / "prompts" / "culture-tags-v1-damon.md"
TYPES = ("comment", "community", "creator-comment")


def say(m):
    print(m, flush=True)


def sha(t):
    return hashlib.sha1((t or "").encode("utf-8")).hexdigest()[:12]


def uses(e):
    u = e.get("use")
    return [u] if isinstance(u, str) else [x for x in (u or []) if isinstance(x, str)]


def likes(e):
    v = (e.get("signal") or {}).get("likes")
    try:
        return int(str(v).replace(",", "")) if v is not None else 0
    except ValueError:
        return 0


def candidates(brand, avatar=None, root=None, seen=None, limit=None):
    """[(rel_file, index, entry)] — culture-readable rows not yet read, most-liked first."""
    root = Path(root) if root else engine.WORKSPACE
    seen = seen or {}
    base = root / "brands" / brand / "core-avatars"
    out = []
    for f in sorted(base.glob(f"{avatar or '*'}/**/*.json")):
        p = f.relative_to(root).as_posix()
        if "/language/" not in p or "/language/used/" in p:
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for i, e in enumerate(d.get("entries", []) if isinstance(d, dict) else []):
            if (e.get("source") or {}).get("type") not in TYPES or not e.get("id") or not (e.get("text") or "").strip():
                continue
            if seen.get(e["id"]) == sha(e["text"]):
                continue
            out.append((p, i, e))
    out.sort(key=lambda x: (-likes(x[2]), x[2]["id"]))
    return out[:limit] if limit else out


def avatar_note(brand, avatar):
    if not avatar:
        return f"(every avatar of this brand — read each row on its own words)"
    try:
        p = engine.WORKSPACE / "brands" / brand / "core-avatars" / avatar / "profile.md"
        return p.read_text()[:1500]
    except Exception:
        return f"(no profile on file for {avatar})"


def parse(txt, n):
    """The model's answer -> {i: [tags]} — only known tags, only rows in range."""
    try:
        got = json.loads(txt[txt.find("["): txt.rfind("]") + 1])
    except Exception:
        return None
    out = {}
    for v in got if isinstance(got, list) else []:
        if isinstance(v, dict) and isinstance(v.get("i"), int) and 0 <= v["i"] < n:
            tags = [t for t in v.get("add") or [] if t in A.CULTURE_TAGS]
            if tags:
                out[v["i"]] = list(dict.fromkeys(tags))
    return out


def read(rows, base, model, batch=40, jobs=4, claude=None):
    """{row index: [tags]} and the set of indexes actually read. `claude` is a seam for tests:
    a callable(prompt) -> text."""
    exe = shutil.which("claude")

    def ask(prompt):
        if claude:
            return claude(prompt)
        p = subprocess.run([exe, "-p", "--output-format", "text", "--model", model],
                           input=prompt, capture_output=True, text=True, timeout=900)
        return p.stdout

    if not claude and not exe:
        say("  culture read: MISSING (no `claude` command) — nothing read")
        return {}, set()
    chunks = [(s, rows[s:s + batch]) for s in range(0, len(rows), batch)]

    def one(c):
        s, ch = c
        listing = "\n".join(f"{k}. {e['text'][:800]}" for k, (_, _, e) in enumerate(ch))
        try:
            got = parse(ask(base.replace("{{ROWS}}", listing)), len(ch))
        except Exception as ex:
            say(f"  rows {s}-{s + len(ch) - 1} failed ({str(ex)[:80]}) — left unread")
            return s, ch, None
        return s, ch, got

    tags, done = {}, set()
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for n, (s, ch, got) in enumerate(ex.map(one, chunks), 1):
            if got is None:
                continue
            done.update(range(s, s + len(ch)))
            for k, t in got.items():
                tags[s + k] = t
            say(f"  batch {n}/{len(chunks)} read")
    return tags, done


def build(rows, tags):
    """Proposal rows: add_use = the tags the model gave that the row does not have yet."""
    out = []
    for i, t in sorted(tags.items()):
        f, idx, e = rows[i]
        new = [x for x in t if x not in uses(e)]
        if new:
            out.append(dict(file=f, index=idx, id=e["id"], text_sha=sha(e["text"]), add_use=new))
    return out


def counts(rows):
    c = {t: 0 for t in A.CULTURE_TAGS}
    for _, _, e in rows:
        for t in uses(e):
            if t in c:
                c[t] += 1
    return c


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gather.py retag")
    ap.add_argument("--culture", action="store_true", required=True)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--model")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cfg = engine._config().get("ownvoice", {})
    model = a.model or cfg.get("model") or "claude-sonnet-5"
    state_f = engine._deep_runs_root() / a.brand / "retag-culture-state.json"
    try:
        state = json.loads(state_f.read_text())
    except Exception:
        state = {"read": {}}
    rows = candidates(a.brand, a.avatar, seen=state["read"], limit=a.limit)
    say(f"retag --culture · {a.brand}{' · ' + a.avatar if a.avatar else ''} · {len(rows)} row(s) to read"
        f" · {(len(rows) + a.batch - 1) // a.batch} model call(s){' · DRY RUN' if a.dry_run else ''}")
    if a.dry_run or not rows:
        return 0
    base = PROMPT.read_text().split("\n---\n", 1)[-1].replace("{{AVATAR}}", avatar_note(a.brand, a.avatar))
    tags, done = read(rows, base, model, a.batch, a.jobs)
    prow = build(rows, tags)
    now = dt.datetime.now(dt.timezone.utc)
    run_label = now.strftime("%Y-%m-%d-%H%M")
    out = engine._deep_runs_root() / a.brand / f"retag-culture-{run_label}{'-' + a.avatar if a.avatar else ''}"
    out.mkdir(parents=True, exist_ok=True)
    prop = {"kind": "language-bank-proposal", "version": 1, "brand": a.brand,
            "tool": "research-gatherer retag --culture", "made_at": now.strftime("%Y-%m-%dT%H:%MZ"),
            "prompt": PROMPT.name, "model": model, "rows": prow}
    (out / "proposal.json").write_text(json.dumps(prop, indent=1, ensure_ascii=False) + "\n")
    text_of = {e["id"]: e["text"] for _, _, e in rows}
    added = {t: sum(t in r["add_use"] for r in prow) for t in A.CULTURE_TAGS}
    lines = [f"# Culture retag — {a.brand}{' / ' + a.avatar if a.avatar else ''} — {run_label}", "",
             f"Rows read: {len(done)} of {len(rows)} · rows gaining a tag: {len(prow)} · model: {model}", "",
             "## Tags added", ""] + [f"- {t}: {n}" for t, n in added.items()] + \
        ["", "## Examples", ""] + [f"- `{', '.join(r['add_use'])}` — {text_of[r['id']][:160]}" for r in prow[:25]] + \
        ["", "## The prompt, word for word", "", PROMPT.read_text()]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    for i in done:
        state["read"][rows[i][2]["id"]] = sha(rows[i][2]["text"])
    state_f.parent.mkdir(parents=True, exist_ok=True)
    state_f.write_text(json.dumps(state, indent=1) + "\n")
    say(f"  read {len(done)} · {len(prow)} rows gain tags · " + ", ".join(f"{t} +{n}" for t, n in added.items() if n))
    say(f"  proposal: {(out / 'proposal.json').relative_to(engine.WORKSPACE)}")
    if a.apply and prow:
        from . import bank_apply as BA
        try:
            r = BA.apply(out / "proposal.json")
            say(f"  applied {r['applied']} · skipped {r['skipped']}")
        except BA.Refused as e:
            say(f"  REFUSED — nothing written: {e}")
    return 0
