#!/usr/bin/env python3
"""timeline_page.py — the page Damon looks at, at each stop: every layer of the
edit as bars on one clock, with the draft video beside it.

    write(run, sheet, stage, video=None, checks=None) -> Path   (run/timeline.html)

Read straight off the cut sheet, so what he sees IS what renders.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

E = html.escape
STAGES = {"timeline": ("Stop 1 — the timeline", "Dead space is out, every layer is laid. Approve it, or say what to change in plain words."),
          "captions": ("Stop 2 — the captions", "Same cut, captions on. Approve, switch the look, or fix a word. Switching the look never re-edits the video."),
          "done": ("Exported", "The final file, with the machine's own checks.")}


def _bar(start, dur, end, label, cls, title=""):
    return f'<div class="bar {cls}" style="left:{start / end * 100:.3f}%;width:{max(dur / end * 100, .3):.3f}%" title="{E(title or label)}"><span>{E(label)}</span></div>'


def write(run: Path, sheet: dict, stage: str, video: Path | None = None, checks: list | None = None) -> Path:
    end = max(c["start"] + c["duration"] for c in sheet["picture"])
    rows = []

    def row(name, bars, note=""):
        rows.append(f'<div class="row"><div class="name">{E(name)}<small>{E(note)}</small></div><div class="lane">{"".join(bars)}</div></div>')

    for o_kind, title in (("hook", "Hook text"), ("label", "Labels"), ("end-card", "End card")):
        bars = [_bar(o["start"], o["duration"], end, o.get("text", o_kind), "ov") for o in sheet.get("overlays") or [] if o.get("kind") == o_kind]
        if bars:
            row(title, bars)
    words = (sheet.get("captions") or {}).get("words") or []
    if words:
        import compose as C
        look = C.look_of(sheet)
        lines = C.caption_lines(words, look["max_words"])
        row("Captions", [_bar(l[0]["start"], l[-1]["end"] - l[0]["start"], end, " ".join(w["text"] for w in l), "cap") for l in lines], look.get("name", "match-swipe"))
    row("B-roll", [_bar(c["start"], c["duration"], end, c["id"], "b", c["why"]) for c in sheet["picture"] if c["roll"] == "b"], "covers the A-roll")
    row("A-roll", [_bar(c["start"], c["duration"], end, c["id"], "a", c["why"]) for c in sheet["picture"] if c["roll"] == "a"], "carries the line")
    marks = [f'<i class="w" style="left:{w["start"] / end * 100:.3f}%"></i>' for w in words]
    if sheet.get("voice"):
        v = sheet["voice"]
        row("Voice", [_bar(v.get("start", 0), end - v.get("start", 0), end, "one approved read", "v")] + marks, f'{v.get("volume_db", 0)} dB')
    else:
        row("Voice", [_bar(c["start"], c["duration"], end, "her own sound", "v", "the talking clip's own sound — that is what keeps the lips right") for c in sheet["picture"] if c.get("talks")] +
            [_bar(v["start"], v["duration"], end, "voice read", "v") for v in sheet.get("voice_cuts") or []] + marks, "her own sound on A-roll · the voice read under B-roll")
    if sheet.get("music"):
        row("Music", [_bar(sheet["music"].get("start", 0), end, end, "music bed", "m")], f'{sheet["music"]["volume_db"]} dB')
    if sheet.get("sfx"):
        row("Sound effects", [_bar(s["at"], .25, end, s["id"], "s", f'for {s["for"]}') for s in sheet["sfx"]])

    ticks = "".join(f'<i style="left:{t / end * 100:.3f}%">{t}s</i>' for t in range(0, int(end) + 1, max(1, int(end // 12) or 1)))
    cuts = "".join(f'<tr><td>{E(c["id"])}</td><td>{"A-roll" if c["roll"] == "a" else "B-roll"}</td><td>{c["start"]:.2f}s</td><td>{c["duration"]:.2f}s</td><td>{E(c["why"])}</td></tr>' for c in sorted(sheet["picture"], key=lambda c: c["start"]))
    ctl = sheet.get("controls") or {}
    dials = "".join(f"<li><b>{E(k.replace('_', ' '))}</b> {E(str(v.get('value') if isinstance(v, dict) and 'value' in v else ''))}</li>" for k, v in ctl.items() if isinstance(v, dict) and "value" in v)
    chk = "".join(f'<li class="{"ok" if c["pass"] else "held"}">{"PASS" if c["pass"] else "HELD"} — {E(c["check"])}: {E(c["detail"])}</li>' for c in checks or [])
    changes = run / "changes.jsonl"
    log = "".join(f'<li>{E(j["asked"])}{" — because " + E(j["why"]) if j.get("why") else ""}</li>' for j in map(json.loads, changes.read_text().splitlines())) if changes.exists() else ""
    title, sub = STAGES[stage]
    vid = f'<video controls playsinline src="{E(str(video.relative_to(run)))}"></video>' if video else ""
    page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(sheet['meta']['label'])} — {E(title)}</title>
<style>
:root{{--g:#EDF0F3;--p:#F8FAFB;--ink:#15202B;--soft:#566575;--line:#CBD3DB;--a:#0E6B8A;--b:#A8650C;--v:#1F7A4D;--m:#6B5CA5;--s:#A33A2A}}
@media (prefers-color-scheme:dark){{:root{{--g:#10171E;--p:#18222C;--ink:#E6ECF1;--soft:#93A2B1;--line:#2B3946;--a:#5CC0E0;--b:#EDB45C;--v:#6FD3A0;--m:#B3A6E8;--s:#F0907F}}}}
body{{margin:0;background:var(--g);color:var(--ink);font:16px/1.5 -apple-system,'Helvetica Neue',sans-serif}}
.wrap{{max-width:1240px;margin:0 auto;padding:28px 20px 60px;display:flex;flex-direction:column;gap:22px}}
h1{{margin:0;font-size:2rem}} h2{{margin:0;font-size:1.2rem}} .soft{{color:var(--soft)}}
.top{{display:grid;grid-template-columns:minmax(0,300px) 1fr;gap:24px;align-items:start}} @media(max-width:760px){{.top{{grid-template-columns:1fr}}}}
video{{width:100%;border:1px solid var(--line);background:#000}}
.tl{{border:1px solid var(--line);background:var(--p);overflow-x:auto}} .inner{{min-width:860px}}
.row{{display:grid;grid-template-columns:150px 1fr;border-bottom:1px solid var(--line)}} .row:last-child{{border:0}}
.name{{padding:10px 12px;font-weight:600;border-right:1px solid var(--line)}} .name small{{display:block;font-weight:400;color:var(--soft);font-size:.75rem}}
.lane{{position:relative;height:46px}} .ruler{{position:relative;height:22px;margin-left:150px;border-bottom:1px solid var(--line)}}
.ruler i{{position:absolute;font:11px ui-monospace,monospace;color:var(--soft);font-style:normal;border-left:1px solid var(--line);padding-left:3px;height:100%}}
.bar{{position:absolute;top:7px;height:32px;border-radius:3px;overflow:hidden;color:#fff;font-size:.72rem;box-shadow:inset 0 0 0 1px #0003}}
.bar span{{display:block;padding:8px 6px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}}
.a{{background:var(--a)}} .b{{background:var(--b)}} .v{{background:var(--v);opacity:.8}} .m{{background:var(--m)}} .s{{background:var(--s)}} .cap{{background:var(--ink);color:var(--g)}} .ov{{background:var(--s)}}
.w{{position:absolute;top:4px;bottom:4px;width:1px;background:#fff9}}
table{{border-collapse:collapse;width:100%;background:var(--p);border:1px solid var(--line);font-size:.92rem}} td,th{{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line)}}
ul{{margin:0;padding-left:18px}} .ok{{color:var(--v)}} .held{{color:var(--s)}}
.say{{background:var(--p);border-left:4px solid var(--a);padding:14px 16px}}
</style><div class="wrap">
<div><div class="soft">{E(sheet['meta']['brand'])} · {E(sheet['meta']['label'])} · {end:.1f}s · cut by {E(sheet.get('cut_by', 'model'))}</div><h1>{E(title)}</h1><p class="soft">{E(sub)}</p></div>
<div class="top"><div>{vid}</div><div style="display:flex;flex-direction:column;gap:14px">
<div class="say"><b>To change anything,</b> say it in plain words — "B-roll comes in a beat earlier", "lose the pause after 'sunscreen'", "captions in the clean look". It becomes a new version of the cut sheet; nothing is regenerated, and the reason is kept so the next cut starts closer.</div>
<div><h2>The dials this edit ran under</h2><ul>{dials}</ul></div>
{("<div><h2>The cutter’s notes for you</h2><ul>" + "".join(f"<li>{E(n)}</li>" for n in sheet.get("notes_for_damon") or []) + "".join(f"<li><b>Missing:</b> {E(n)}</li>" for n in sheet.get("missing") or []) + "</ul></div>") if (sheet.get("notes_for_damon") or sheet.get("missing")) else ""}
{f'<div><h2>The machine’s checks</h2><ul>{chk}</ul></div>' if chk else ''}
{f'<div><h2>What you have changed so far</h2><ul>{log}</ul></div>' if log else ''}</div></div>
<div class="tl"><div class="inner"><div class="ruler">{ticks}</div>{''.join(rows)}</div></div>
<div><h2>Every cut, and what it is for</h2><table><tr><th>Clip</th><th>Roll</th><th>In</th><th>Length</th><th>Why</th></tr>{cuts}</table></div>
</div>"""
    out = run / "timeline.html"
    out.write_text(page)
    return out
