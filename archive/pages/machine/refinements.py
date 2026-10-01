#!/usr/bin/env python3
"""Draw the page machine's refinement document: every run, what got in the
way at which stage, what it cost, the fix, and whether the fix landed. Reads
docs/refinements.md (the mirror the team edits) and each run's run.json for the
stage trail; writes pages/refinements.html. Never hand-edited. Republish over
the artifact link in context/artifacts.md after every change to the log.

    python3 refinements.py
"""
import html, json, re, sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "machine"))
from run import STAGES   # noqa: E402

SRC = HERE / "docs" / "refinements.md"
import page_paths as P   # noqa: E402
RUNS = P.RUNS
OUT = HERE / "pages" / "refinements.html"

def esc(s): return html.escape(s or "", quote=False)

def inline(t):
    t = esc(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", t)
    return t

def parse(text):
    """-> intro paragraphs, [run{label, date, job, rows[]}]"""
    intro, runs, cur = [], [], None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^## Run: `([^`]+)`\s*—\s*(.*)$", ln)
        if m:
            cur = dict(label=m.group(1), date=m.group(2).strip(), job="", rows=[])
            runs.append(cur); i += 1; continue
        if cur is None:
            if ln.startswith("# "): i += 1; continue
            intro.append(ln); i += 1; continue
        if ln.startswith("**The job.**"):
            job = [ln.replace("**The job.**", "").strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("|"):
                job.append(lines[i].strip()); i += 1
            cur["job"] = " ".join(job); continue
        if ln.startswith("|") and not re.match(r"^\|\s*#\s*\|", ln) and not re.match(r"^\|[-| ]+\|$", ln):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) >= 6:
                cur["rows"].append(dict(n=cells[0], stage=cells[1], what=cells[2], cost=cells[3], fix=cells[4], status=cells[5]))
        i += 1
    return "\n".join(intro).strip(), runs

def status_kind(s):
    s = s.lower()
    if s.startswith("fixed") or s.startswith("landed"): return "fixed"
    if "damon" in s or "needs" in s or "ok" in s: return "decide"
    if s.startswith("watching"): return "watch"
    if "in place" in s: return "part"
    return "open"

def stage_key(s):
    s = s.lower()
    if "before" in s: return "pre"
    m = re.search(r"stage\s*(2b|\d)", s)
    return m.group(1) if m else "pre"

def trail(label):
    d = P.find_run(label)
    p = (d or RUNS / label) / "run.json"
    if not p.exists(): return {}
    st = json.loads(p.read_text()).get("stages", {})
    out = {}
    for k, v in st.items():
        base = k.split("-")[0]
        out.setdefault(base, []).append(v)
    return out

def build():
    intro, runs = parse(SRC.read_text())
    today = datetime.date.today().isoformat()
    parts = []
    for r in runs:
        tr = trail(r["label"])
        issues_by = {}
        for row in r["rows"]:
            issues_by.setdefault(stage_key(row["stage"]), []).append(row)
        chips = []
        pre = issues_by.get("pre", [])
        chips.append(f'<div class="st {"has" if pre else ""}"><div class="id">in</div><div class="nm">Before the chain</div><div class="meta">{len(pre)} issue{"s" if len(pre)!=1 else ""}</div></div>')
        for s in STAGES:
            k = s["key"].replace("stage", "")
            runs_of = tr.get(s["key"], [])
            done = [x for x in runs_of if x.get("status") == "done"]
            secs = sum(x.get("seconds", 0) for x in done)
            iss = issues_by.get(k, [])
            state = "done" if done else ("dry" if runs_of else "notrun")
            meta = f'{secs:.0f}s · {sum(x.get("chars_out",0) for x in done):,} chars' if done else ("not run" if state == "notrun" else "dry")
            if iss: meta += f' · {len(iss)} issue{"s" if len(iss)!=1 else ""}'
            chips.append(f'<div class="st {state} {"has" if iss else ""}"><div class="id">{s["id"]}</div><div class="nm">{esc(s["name"])}</div><div class="meta">{meta}</div></div>')
        rows = []
        for row in r["rows"]:
            kind = status_kind(row["status"])
            rows.append(f'''<article class="issue" id="{r["label"]}-{row["n"]}">
  <div class="head"><span class="num">#{esc(row["n"])}</span><span class="where">{inline(row["stage"])}</span><span class="pill {kind}">{inline(row["status"])}</span></div>
  <div class="cols">
    <div><div class="lbl">What happened</div><p>{inline(row["what"])}</p></div>
    <div><div class="lbl">What it cost</div><p>{inline(row["cost"])}</p></div>
    <div><div class="lbl">The fix</div><p>{inline(row["fix"])}</p></div>
  </div>
</article>''')
        counts = {}
        for row in r["rows"]: counts[status_kind(row["status"])] = counts.get(status_kind(row["status"]), 0) + 1
        summary = " · ".join(f'{v} {dict(open="open", decide="need a ruling", watch="watching", part="partly fixed", fixed="fixed")[k]}' for k, v in counts.items())
        parts.append(f'''<section class="run">
  <div class="runhead"><h2>Run <code>{esc(r["label"])}</code></h2><span class="date">{esc(r["date"])}</span></div>
  <p class="job">{inline(r["job"])}</p>
  <div class="chain">{"".join(chips)}</div>
  <p class="summary">{len(r["rows"])} issues — {summary}</p>
  <div class="issues">{"".join(rows)}</div>
</section>''')

    page = f'''<title>Page Machine Refinements</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#F2F4F6;--surface:#FFFFFF;--ink:#1B222B;--muted:#5F6B78;--line:#D9DEE4;--accent:#0F6E74;--accent-soft:#DCEFF0;--warn:#9A5B12;--warn-soft:#FBEBD2;--bad:#A23A2C;--bad-soft:#F8DDD8;--good:#2F6B3A;--good-soft:#DCEFDF;--code:#EEF1F4;--radius:8px}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#11161B;--surface:#1A2129;--ink:#E7EBEF;--muted:#98A3AE;--line:#2C3540;--accent:#5FC3C9;--accent-soft:#143537;--warn:#E3A95B;--warn-soft:#3A2A12;--bad:#E48A7C;--bad-soft:#3E1F1A;--good:#8FCB9A;--good-soft:#1B3320;--code:#232B34}}}}
:root[data-theme="dark"]{{--bg:#11161B;--surface:#1A2129;--ink:#E7EBEF;--muted:#98A3AE;--line:#2C3540;--accent:#5FC3C9;--accent-soft:#143537;--warn:#E3A95B;--warn-soft:#3A2A12;--bad:#E48A7C;--bad-soft:#3E1F1A;--good:#8FCB9A;--good-soft:#1B3320;--code:#232B34}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px;padding-block:28px 64px}}
.wrap{{max-width:1080px;margin:0 auto}}
h1{{font-size:26px;font-weight:600;margin:0 0 6px;letter-spacing:-.01em;text-wrap:balance}}
h2{{font-size:19px;font-weight:600;margin:0}}
p{{margin:0}}
code{{font:13px/1.4 "IBM Plex Mono",ui-monospace,monospace;background:var(--code);padding:1px 5px;border-radius:4px}}
.lede{{color:var(--muted);max-width:68ch;margin-bottom:8px}}
.intro{{color:var(--muted);max-width:68ch;font-size:14px;margin-bottom:28px}}
.intro p{{margin-bottom:8px}}
.run{{margin-top:12px}}
.runhead{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:6px}}
.date{{color:var(--muted);font:13px "IBM Plex Mono",monospace}}
.job{{max-width:76ch;margin-bottom:18px}}
.chain{{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:6px;margin-bottom:10px}}
.st{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:8px 10px;min-height:74px}}
.st .id{{font:12px "IBM Plex Mono",monospace;color:var(--muted);letter-spacing:.04em}}
.st .nm{{font-weight:500;font-size:13px;margin:2px 0}}
.st .meta{{font-size:11.5px;color:var(--muted);line-height:1.35}}
.st.done{{border-color:var(--good)}}
.st.notrun{{opacity:.55;border-style:dashed}}
.st.has{{background:var(--warn-soft);border-color:var(--warn)}}
.st.has .id,.st.has .meta{{color:var(--warn)}}
.summary{{font-size:13px;color:var(--muted);margin:6px 0 16px}}
.issues{{display:grid;gap:10px}}
.issue{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px}}
.head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}}
.num{{font:13px "IBM Plex Mono",monospace;color:var(--muted)}}
.where{{font-weight:500}}
.pill{{margin-left:auto;font-size:12px;padding:2px 9px;border-radius:999px;font-weight:500}}
.pill.open{{background:var(--bad-soft);color:var(--bad)}}
.pill.decide{{background:var(--warn-soft);color:var(--warn)}}
.pill.watch{{background:var(--accent-soft);color:var(--accent)}}
.pill.part{{background:var(--accent-soft);color:var(--accent)}}
.pill.fixed{{background:var(--good-soft);color:var(--good)}}
.cols{{display:grid;grid-template-columns:1.4fr 1fr 1.2fr;gap:16px}}
.lbl{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:4px}}
.cols p{{font-size:14px}}
.foot{{margin-top:36px;font-size:12.5px;color:var(--muted)}}
@media (max-width:720px){{.cols{{grid-template-columns:1fr}}.pill{{margin-left:0}}}}
</style>
<div class="wrap">
<h1>Page Machine Refinements</h1>
<p class="lede">What got in the way, run by run — where in the chain it bit, what it cost, the fix, and whether the fix has landed.</p>
<div class="intro">{"".join(f"<p>{inline(x)}</p>" for x in intro.split(chr(10)+chr(10)) if x.strip())}</div>
{"".join(parts)}
<p class="foot">Built {today} from <code>pages/docs/refinements.md</code> — the Markdown mirror the team edits. The chain itself: <code>docs/the-chain.md</code>.</p>
</div>
'''
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page)
    print(OUT, f"{len(page):,} chars, {sum(len(r['rows']) for r in runs)} issues across {len(runs)} run(s)")

if __name__ == "__main__":
    build()
