#!/usr/bin/env python3
"""The email machine's dashboard — the month, the line, and how to drive it.

    python3 build_dashboard.py [compose-2026-09]   # -> dashboard.html + dashboard.md

One page: the state of the machine, the composed month slot by slot, the
latest email off the line, and the three sentences that operate all of it.
Regenerated after every compose or chain run; the artifact republishes over
the same link.
"""
import html
import json
import re
import sys
from paths import WORKSPACE, calendar_tool
import drive_reach as DR
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

# the copy lane's roster reader — one implementation, every lane
from paths import lab_tool, component, WORKSPACE as _WS  # noqa: E402
sys.path.insert(0, str(component("copywriter", "machine")))
try:
    import language as L
except Exception:
    L = None

CAT = {
    "Promotional": ("promo", "made of our offer"),
    "Educational": ("edu", "made of our expertise"),
    "Cultural": ("cult", "made of the world outside"),
    "Community": ("comm", "made of our customers"),
    "Brand": ("brand", "made of us"),
    "Affiliate": ("aff", "made of a partner's offer"),
}


def e(s):
    return html.escape(str(s if s is not None else ""))


def load_month(label):
    d = HERE / "results" / label
    if not (d / "slots.json").is_file():
        # no composed month standing — the board shows the fresh-start state.
        # Brand falls back to the one brand folder that carries email records.
        brands = sorted(p.parent.parent.name for p in
                        (REPO / "brands").glob("*/email/audience-matrix.json"))
        return [], {"brand": brands[0] if brands else "unknown",
                    "label": label, "errors": 0, "warnings": 0}, []
    slots = json.loads((d / "slots.json").read_text())
    run = json.loads((d / "run.json").read_text())
    warns = []
    checks = (d / "checks.md")
    if checks.is_file():
        warns = [ln[2:] for ln in checks.read_text().splitlines()
                 if ln.startswith("- ")]
    return slots, run, warns


def load_chain(label):
    """The latest production run, if one exists."""
    d = HERE / "results" / label
    if not (d / "run.json").is_file():
        return None
    run = json.loads((d / "run.json").read_text())
    subjects = ""
    f = d / "stage5--subjects.md"
    if f.is_file():
        subjects = f.read_text().strip()
    return dict(run=run, subjects=subjects, dir=d)


def slot_row(s, warn_ids):
    d = date.fromisoformat(s["date"])
    cls, _ = CAT.get(s["category"], ("edu", ""))
    held = "HELD OPEN" in (s.get("occasion") or "").upper()
    segs = s.get("segments") or [s["segment"]]
    if len(segs) == 1:
        chips = [f'<span class="chip">{e(segs[0].replace("Core | ", ""))}</span>']
    else:
        chips = [f'<span class="chip multi" title="{e(", ".join(segs))}">one send · '
                 f'{len(segs)} segments</span>']
    variants = s.get("variants") or []
    if variants:
        for v in variants:
            chips.append(f'<span class="chip av">{e(v.get("avatar"))}</span>')
    elif s.get("avatar") and s["avatar"] not in ("none", "mixed"):
        chips.append(f'<span class="chip av">{e(s["avatar"])}</span>')
        sub = s.get("sub_avatar")
        if sub and sub != "none":
            short = re.sub(r"^sub-\d+-", "", sub)
            chips.append(f'<span class="chip av">{e(short)}</span>')
    else:
        chips.append('<span class="chip av">everyone</span>')
    chips.append(f'<span class="chip">{e(s["role"])}</span>')
    if s.get("anchored"):
        chips.append('<span class="chip anc" title="laid on its real date by code — a holiday or dated moment">anchored</span>')
    hour = f'{s["hour"]:02d}:00' + ("" if s.get("local") else " fixed")
    flag = ('<div class="flag">the checker flagged this one — read the note '
            'under the board</div>' if s["id"] in warn_ids else "")
    extra = []
    if s.get("product") and s["product"] != "none":
        extra.append(f"product: {s['product']}")
    if s.get("offer") and s["offer"] != "none":
        extra.append(f"offer: {s['offer']}")
    if s.get("follows"):
        extra.append(f"answers {s['follows']}")
    if s.get("then") and s["then"] != "contingent":
        extra.append(f"obliges {s['then']}")
    if s.get("then") == "contingent":
        extra.append("follow-up only if it stalls")
    return f'''<details class="slot {cls}{' held' if held else ''}">
<summary>
 <span class="d"><b>{d.day}</b><i>{d:%a}</i></span>
 <span class="body"><span class="t">{e(s["type"])}<em class="cat c-{cls}">{e(s["category"])}</em></span>
 <span class="occ">{e(s["occasion"])}</span></span>
 <span class="chips">{''.join(chips)}<span class="chip hr">{hour}</span></span>
</summary>
<div class="why">
 {f'<p class="k">To: {e(" · ".join(x.replace("Core | ", "") for x in segs))}</p>' if len(segs) > 1 else ''}
 <p>{e(s.get("why", ""))}</p>
 {("".join(f'<p class="k">{e(v.get("avatar"))}: {e(v.get("angle"))}</p>' for v in variants)) if variants else ''}
 {f'<p class="k">Built from: <code>{e(s["source"])}</code></p>' if s.get("source") and not s["source"].startswith("[UNFILLED") else '<p class="k unf">No source fits yet — marked, not forced.</p>'}
 {f'<p class="k">Ground not to reuse: {e(s["spent"])}</p>' if s.get("spent") else ''}
 {f'<p class="k">{" · ".join(e(x) for x in extra)}</p>' if extra else ''}
 {flag}
</div>
</details>'''


def mix_bar(slots):
    counts = {}
    for s in slots:
        counts[s["category"]] = counts.get(s["category"], 0) + 1
    total = len(slots) or 1
    segs, legend = [], []
    for name, (cls, _) in CAT.items():
        n = counts.get(name, 0)
        if not n:
            continue
        segs.append(f'<span class="seg c-{cls}" style="flex:{n}" title="{name} {n}"></span>')
        legend.append(f'<span class="lg"><span class="dot c-{cls}"></span>{e(name)} {n}</span>')
    return f'<div class="mix">{"".join(segs)}</div><div class="legend">{"".join(legend)}</div>'


def matrix_section(slots, brand):
    """The cells — every avatar and sub-avatar, served or cold. The unit of
    planning is the cell, not the day (the owner, 2026-08-29)."""
    if not slots:
        return ""
    roster = (L.avatars(brand) if L else []) or []
    if not roster:
        return ""
    by_cell = {}
    for s in slots:
        # a calendar-flow slot (2026-09+) carries variants[] instead of one
        # avatar — each variant is its own voice in the same send, so it
        # counts toward its own avatar's row, not a fictitious "mixed" cell.
        variants = s.get("variants") or []
        if variants:
            for v in variants:
                by_cell.setdefault((v.get("avatar") or "none", "none"), []).append(s)
        else:
            av = s.get("avatar") or "none"
            sub = s.get("sub_avatar") or "none"
            by_cell.setdefault((av, sub), []).append(s)
    rows = []
    for a in roster:
        whole = by_cell.get((a["key"], "none"), [])
        segs = sorted({y.replace("Core | ", "") for x in whole
                       for y in (x.get("segments") or [x["segment"]])})
        rows.append(f'''<div class="mrow head"><span class="mav">{e(a["key"])}</span>
<span class="mn">{len(whole) or "—"}</span>
<span class="ms">{"whole-avatar sends · " + ", ".join(segs) if whole else "no whole-avatar send this month"}</span></div>''')
        for sub in a.get("subs") or []:
            got = by_cell.get((a["key"], sub), [])
            short = re.sub(r"^sub-\d+-", "", sub)
            if got:
                what = " · ".join(f'{x["id"]} {x["type"]}' for x in got)
                rows.append(f'<div class="mrow"><span class="mav sub">{e(short)}</span>'
                            f'<span class="mn">{len(got)}</span><span class="ms">{e(what)}</span></div>')
            else:
                rows.append(f'<div class="mrow cold"><span class="mav sub">{e(short)}</span>'
                            f'<span class="mn">0</span><span class="ms">cold — never targeted this month</span></div>')
    bc = by_cell.get(("none", "none"), [])
    if bc:
        rows.append(f'<div class="mrow head"><span class="mav">everyone</span>'
                    f'<span class="mn">{len(bc)}</span>'
                    f'<span class="ms">broadcasts — {" · ".join(x["id"] for x in bc)}</span></div>')
    return f'''<section>
<div class="sh"><span class="kick">The matrix</span><h2>Who is being spoken to</h2></div>
<p class="sn">The unit of planning is the cell — segment × avatar × sub-avatar —
never emails-per-day. Volume scales with how many cells the database carries;
one person still only receives their own cell's stream. A cold row is a person
in the database nobody wrote to this month.</p>
<div class="matrix">{"".join(rows)}</div>
</section>'''


REPO = _WS                               # the workspace root, found not counted
STAGE_ORDER = ["stage0", "stage1", "stage2", "stage1b", "stage3", "stage4",
               "stage5", "stage6", "stage7", "stage8", "stage9"]
STAGE_NAMES = {"stage0": "Triage", "stage1": "Read", "stage2": "Spec",
               "stage1b": "Context scout", "stage3": "Injection",
               "stage4": "Placement", "stage5": "Subject lines",
               "stage6": "Expansion", "stage7": "Close", "stage8": "Build",
               "stage9": "Brief"}
STAGE_BLURB = {"stage0": "what the source IS — lane, format, voice, sender",
               "stage1": "the objective record of the source email",
               "stage2": "the argument, stripped brand-free",
               "stage1b": "picks which brand files THIS source needs",
               "stage3": "our nouns into their argument — substitution, never rewrite",
               "stage4": "where the product enters, scroll budget, CTA and image plan",
               "stage5": "every subject/preview pair — all ship, none ranked",
               "stage6": "commercial moves added, gated — organic sources only",
               "stage7": "the objection, the landing, the PS or NO PS",
               "stage8": "the email as typed blocks, ready to draw",
               "stage9": "the one page production opens"}


def catalogue_tab(catalogue, used_types, month_counts):
    """Every type the brand knows — browsable, with what it needs and what
    must follow it. The thing the board's '25 of 45' points into."""
    out = []
    for well, (cls, does) in {"ask": ("promo", "Promotional — made of our offer"),
                              "help": ("edu", "Educational — made of our expertise"),
                              "belong": ("cult", "Cultural — made of the world outside"),
                              "real": ("comm", "Community — made of our customers"),
                              "brand": ("brand", "Brand — made of us"),
                              "affiliate": ("aff", "Affiliate — made of a partner's offer")}.items():
        types = [t for t in catalogue if t["well"] == well]
        n_used = sum(1 for t in types if t["key"] in used_types)
        out.append(f'<div class="wellhd"><span class="dot c-{cls}"></span>'
                   f'<h3>{e(does)}</h3><span class="whn">{len(types)} types · '
                   f'{n_used} on this month\'s board</span></div>')
        out.append('<div class="tygrid">')
        for t in types:
            month_n = month_counts.get(t["key"], 0)
            badges = [f'<span class="tb u-{e(t.get("use", "new"))}">{e(t.get("use", "new"))}</span>',
                      f'<span class="tb">{t.get("n", 0)} ever sent</span>']
            if month_n:
                badges.append(f'<span class="tb on">{month_n} this month</span>')
            detail = [f'<p>{e(t["what"])}</p>']
            if t.get("note"):
                detail.append(f'<p class="k">{e(t["note"])}</p>')
            if t.get("arc_note"):
                detail.append(f'<p class="k">Arc: {e(t["arc_note"])}</p>')
            row2 = [f'role: <b>{e(t["role"])}</b>']
            if t.get("then"):
                row2.append("then: " + ", ".join(f"<b>{e(x)}</b>" for x in t["then"]))
            if t.get("needs"):
                row2.append("needs: " + ", ".join(f"<code>{e(x)}</code>" for x in t["needs"]))
            detail.append(f'<p class="k">{" · ".join(row2)}</p>')
            out.append(f'''<details class="ty c-b-{cls}">
<summary><span class="tyn">{e(t["name"])}</span><span class="tyk">{e(t["key"])}</span>
<span class="tbs">{"".join(badges)}</span></summary>
<div class="tyd">{"".join(detail)}</div></details>''')
        out.append('</div>')
    return "\n".join(out)


def cards_tab():
    """The stage-1 task cards, read from the build folder — the same record
    the team works from, rendered for reading here."""
    f = REPO / "new-workflow-design/builds/email-machine/task-cards.md"
    if not f.is_file():
        return "<p class='sn'>No cards found — the build folder is missing.</p>"
    text = f.read_text()
    state = {"EM-1": ("built", "BUILT"), "EM-8": ("built", "BUILT — draft you correct"),
             "EM-7": ("part", "PARTLY — your call open"),
             "CMP-1": ("part", "MOSTLY BUILT"), "CMP-8": ("part", "CHECKED, not yet its own step"),
             "CMP-11": ("built", "BUILT"), "CMP-12": ("built", "BUILT")}
    chunks = re.split(r"^### ", text, flags=re.M)[1:]
    out = ['''<div class="cardflow"><pre class="mermaid">
flowchart TD
  EM1["EM-1 audience matrix - BUILT"] --> SPLIT
  subgraph SPLIT["the six dimensions, split out discretely"]
    EM5["EM-5 segments"]
    EM6["EM-6 sub-avatars"]
    EM2["EM-2 awareness"]
    EM3["EM-3 pain points"]
    EM16["EM-16 products"]
    EM4["EM-4 angles"]
  end
  SPLIT --> EM7["EM-7 composition rules"] --> EM8["EM-8 the month, cell-first - BRIEFS. Stage 1 ends here"]
  EM7 -. decomposes into .-> CMP["CMP-1 to CMP-12: the composer, step by step"]
</pre></div>''']
    for c in chunks:
        title = c.splitlines()[0].strip()
        cid = title.split(" ", 1)[0]
        cls, badge = state.get(cid, ("todo", "TO DO"))
        fields = {}
        for name in ("Story", "Done when"):
            m = re.search(rf"^- {name}: (.*?)(?=^- [A-Z])", c, re.M | re.S)
            if m:
                fields[name] = re.sub(r"\s+", " ", m.group(1)).strip()
        m = re.search(r"^- Today:\n(.*?)(?=^- Proposal:)", c, re.M | re.S)
        today = re.sub(r"\s+", " ", m.group(1)).replace("- Process:", "").strip() if m else ""
        m = re.search(r"^- Proposal:\n(.*)", c, re.M | re.S)
        prop = re.sub(r"\s+", " ", m.group(1)).replace("- Process:", "").strip() if m else ""
        out.append(f'''<details class="card s-{cls}">
<summary><span class="cid">{e(cid)}</span><span class="ct">{e(title.split("—", 1)[1].strip() if "—" in title else title)}</span>
<span class="cb b-{cls}">{e(badge)}</span></summary>
<div class="cd">
<p><b>Story.</b> {e(fields.get("Story", ""))}</p>
<p><b>Done when.</b> {e(fields.get("Done when", ""))}</p>
<p class="k"><b>Today.</b> {e(today)}</p>
<p class="k"><b>Proposal.</b> {e(prop)}</p>
</div></details>''')
    m = re.search(r"## Open questions.*?(?=\n## )", text, re.S)
    if m:
        qs = [re.sub(r"\s+", " ", q).strip() for q in
              re.findall(r"^\d+\. (.*?)(?=^\d+\. |^\*\*|\Z)", m.group(0), re.M | re.S)]
        out.append("<h3>Open — waiting on a human</h3>")
        out += [f'<div class="warnrow">{e(q)}</div>' for q in qs]
    return "\n".join(out)


def runs_tab():
    """Every run, stage by stage, with the actual outputs — the progress a
    person can dig into, teardown-tool style."""
    runs = []
    rdir = HERE / "results"
    if rdir.is_dir():
        for d in sorted(rdir.iterdir()):
            f = d / "run.json"
            if f.is_file():
                runs.append((json.loads(f.read_text()), d))
    runs.sort(key=lambda x: x[0].get("generated_at", ""), reverse=True)
    if not runs:
        return "<p class='sn'>No runs yet.</p>"
    out = []
    for r, d in runs[:3]:
        if r.get("lane_kind") == "email-compose":
            month_f, checks_f = d / "composer--month.md", d / "checks.md"
            narr = ""
            if month_f.is_file():
                m = re.search(r"## THE MATRIX.*|## THE MONTH.*", month_f.read_text(), re.S)
                narr = m.group(0) if m else ""
            out.append(f'''<details class="run">
<summary><span class="cid">COMPOSE</span><span class="ct">{e(r["label"])} — {r.get("slots", "?")} slots ·
{r.get("errors", 0)} breaks · {r.get("warnings", 0)} warnings · {r.get("seconds", "?")}s</span></summary>
<div class="cd"><div class="outbox">{fmt_text(narr)}</div>
{f'<details class="sub"><summary>What the checker said</summary><div class="outbox">{fmt_text(checks_f.read_text())}</div></details>' if checks_f.is_file() else ''}
</div></details>''')
            continue
        done_n = sum(1 for v in r["stages"].values() if v.get("status") == "done")
        rows = []
        for k in STAGE_ORDER:
            st = r["stages"].get(k)
            nm, blurb = STAGE_NAMES[k], STAGE_BLURB[k]
            if not st:
                rows.append(f'<div class="strow wait"><span class="sn1">{nm}</span>'
                            f'<span class="sn2">{blurb}</span><span class="sn3">not reached</span></div>')
                continue
            if st.get("status") == "skipped":
                rows.append(f'<div class="strow skipd"><span class="sn1">{nm}</span>'
                            f'<span class="sn2">{e(st.get("why", ""))}</span><span class="sn3">skipped</span></div>')
                continue
            out_f = d / st.get("out", "_")
            sent_f = d / st.get("sent", "_")
            # the page shows the output, capped; the prompt as sent carries
            # the whole language bank and lives one click away (the page
            # went past 6MB embedding it for every stage of every run)
            raw = out_f.read_text() if out_f.is_file() else "(output file missing)"
            if len(raw) > 8000:
                raw = raw[:8000] + f"\n\n… ({len(raw):,} chars — open the file for the rest)"
            body = fmt_text(raw)
            rel = f"results/{e(r['label'])}"
            sent = (f'<p class="k"><a href="{rel}/{e(st.get("out", ""))}" target="_blank">the full output</a>'
                    + (f' · <a href="{rel}/{e(st.get("sent", ""))}" target="_blank">the prompt as actually sent</a>'
                       if sent_f.is_file() else "") + "</p>")
            rows.append(f'''<details class="strow done2">
<summary><span class="sn1">{nm}</span><span class="sn2">{blurb}</span>
<span class="sn3">{st.get("seconds", "?")}s · {st.get("chars_out", 0):,} chars</span></summary>
<div class="outbox">{body}</div>{sent}</details>''')
        tot = round(sum(v.get("seconds", 0) for v in r["stages"].values()) / 60, 1)
        final = (f' · <a href="results/{e(r["label"])}/email-final.html" style="color:var(--acc)">'
                 f'open the HTML email</a>' if (d / "email-final.html").is_file() else "")
        fig = d / "figma-brief.json"
        if fig.is_file():
            fj = json.loads(fig.read_text())
            if fj.get("url"):
                final += f' · <a href="{e(fj["url"])}" target="_blank" style="color:var(--acc)">the brief in Figma</a>'
        elif (d / "figma-brief.js").is_file():
            final += ' · <span class="ms">Figma brief ready to push</span>'
        out.append(f'''<details class="run" {"open" if r is runs[0][0] else ""}>
<summary><span class="cid">RUN</span><span class="ct">{e(r["label"])} — {done_n} of 11 stages · {tot} min ·
from <code>{e(Path(r.get("source_path", "")).name)}</code>{final}</span></summary>
<div class="cd">{"".join(rows)}</div></details>''')
    return "\n".join(out)


def formats_tab(brand):
    """The design formats — the brand's own templates, specs + real pictures.
    Thumbnails are embedded as data URIs so the page stands alone anywhere."""
    import base64
    root = REPO / "brands" / brand / "email-sms/design-formats"
    spec = root / "formats.md"
    if not spec.is_file():
        return "<p class='sn'>No formats extracted yet.</p>"
    thumbs = []
    def qa_card():
        """the sweep: every export rebuilt as clean HTML, checked against its source"""
        qf = HERE / "results" / "format-bank" / "qc.json"
        if not qf.is_file():
            return ""
        recs = json.loads(qf.read_text())
        n = len(recs)
        clean = sum(1 for r in recs if not r["n_missing"] and r["placed"] == r["assets"] and not r["ctas_missing"] and r["order_ok"])
        return (f'<div class="dr"><b>The rebuild — every export as clean HTML</b><p>{n} emails rebuilt on the bedrock, '
                f'each with its replication spec; checked line by line against the export: copy, pictures, buttons, order. '
                f'<b>{clean}/{n}</b> clean on every check. '
                f'<a href="/results/format-bank/qa-index.html">Open the QA (local)</a></p></div>')

    tdir = HERE / ".thumbs"
    if tdir.is_dir():
        for f in sorted(tdir.glob("*.png")):
            b64 = base64.b64encode(f.read_bytes()).decode()
            label = f.stem.replace("-", " ")
            thumbs.append(f'<figure class="fmt"><img src="data:image/png;base64,{b64}" '
                          f'alt="{e(label)} email design" loading="lazy">'
                          f'<figcaption>{e(label)}</figcaption></figure>')
    gallery = (f'<div class="fmtrow">{"".join(thumbs)}</div>' if thumbs else "")
    lay = root / "layouts.json"
    if lay.is_file():
        L = json.loads(lay.read_text())
        fam_chips = " ".join(f'<span class="tb">{e(F["name"])} · {F["count"]}</span>' for F in L["families"][:6])
        gallery = (f'<div class="drive" style="margin-bottom:18px">'
                   f'<div class="dr"><b>The layout index</b><p>{len(L["emails"])} real emails read for structure '
                   f'and theme — {len(L["families"])} families, {len(L["layouts"])} exact variants, every one as a '
                   f'picture. {fam_chips}<br><a href="/design/format-bank/index.html">Open the index (local)</a></p></div>'
                   f'<div class="dr"><b>The Format Library</b><p>The eight deduped templates and the shared '
                   f'modules, prefilled with the store\'s own product photos. '
                   f'<a href="/design/format-bank/library.html">Open the library (local)</a></p></div>'
                   + qa_card() + '</div>') + gallery
    census = root / "census.json"
    if census.is_file():
        c = json.loads(census.read_text())
        months = len({x.get("month") for x in c["emails"]})
        fams = list(c["families"].items())[:6]
        chips = " ".join(f'<span class="tb">{e(k)} · {v}</span>' for k, v in fams)
        gallery = (f'<p class="sn"><b>The census:</b> {len(c["emails"])} emails registered '
                   f'across {months} months of boards, every one kept in its month. '
                   f'Biggest recurring families: {chips}</p>') + gallery
    # render the spec doc with the same light renderer as the workflow tab
    out, table, code = [], [], False
    for ln in spec.read_text().splitlines():
        if ln.startswith("```"):
            code = not code
            out.append('<pre class="flow">' if code else "</pre>")
            continue
        if code:
            out.append(e(ln)); continue
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if set("".join(cells)) <= {"-", " ", ":"}: continue
            tag = "th" if not table else "td"
            table.append("<tr>" + "".join(f"<{tag}>{fmt_text(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if table:
            out.append('<div class="tw"><table>' + "".join(table) + "</table></div>"); table = []
        if ln.startswith("### "):
            out.append(f"<h3>{fmt_text(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f'<div class="sh" style="margin-top:34px"><h2>{fmt_text(ln[3:])}</h2></div>')
        elif ln.startswith("# "):
            continue
        elif ln.strip():
            out.append(f"<p class='wf'>{fmt_text(ln)}</p>")
    if table:
        out.append('<div class="tw"><table>' + "".join(table) + "</table></div>")
    return gallery + "\n" + "\n".join(out)


MONTH_KEYS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
              "oct", "nov", "dec"]


def board_sort_key(slug):
    m = re.match(r"(?:flow-)?(" + "|".join(MONTH_KEYS) + r")-(\d{4})", slug)
    if m:
        return (m.group(2), MONTH_KEYS.index(m.group(1)), slug)
    return ("9999", 99, slug)


_BANK_TOLD = set()


def board_order(brand):
    """The brand's own boards, in month order — read from its bank and its
    sweep records, never hardcoded (de-branded 2026-08-31). The bank is a
    folder listing, which the Drive API road (gdrive-creator) cannot make, so
    it is read off a mount only (SI-38 (email Drive reach)); never written."""
    seen = set()
    listed = False
    try:
        sa = DR.mount() if DR.route() == "mount" else None
        if sa is not None:
            bank = sa / "brands" / brand / "email-sms/design-formats/format-bank/boards"
            if bank.is_dir():
                seen |= {p.name for p in bank.iterdir() if p.is_dir()}
            listed = True
    except (DR.NoDrive, OSError):
        pass
    if not listed and not _BANK_TOLD:
        _BANK_TOLD.add(True)
        print("dashboard: the format bank's boards are listed off a Drive mount only; "
              "none here — the boards come from the sweep records", file=sys.stderr)
    sw = REPO / "brands" / brand / "email-sms/design-formats/sweep"
    if sw.is_dir():
        seen |= {p.stem for p in sw.glob("*.json")}
    return sorted(seen, key=board_sort_key)


def sweep_tab(brand):
    """The sweep, live — one card per board in month order, findings as they land."""
    root = REPO / "brands" / brand / "email-sms/design-formats/sweep"
    done = {}
    if root.is_dir():
        for f in root.glob("*.json"):
            done[f.stem] = json.loads(f.read_text())
    total_r = sum(d.get("registered", 0) for d in done.values())
    total_e = sum(len(d["emails"]) for d in done.values())
    total_a = sum(len(d["artifacts"]) for d in done.values())
    boards = board_order(brand)
    out = [f'<p class="sn"><b>{len(done)} of {len(boards)} boards swept</b> · '
           f'{total_r} emails on the registry · {total_e} deep-measured (pass 1, '
           f'still calibrating per board) · {total_a} artifact findings queued for '
           'visual verification. This page refreshes itself as each board finishes.</p>']
    for b in boards:
        d = done.get(b)
        if not d:
            out.append(f'<div class="strow wait"><span class="sn1">{e(b)}</span>'
                       f'<span class="sn2">queued</span><span class="sn3">-</span></div>')
            continue
        arts = "".join(f'<div class="warnrow">{e(x)}</div>' for x in d["artifacts"][:12]) \
               or '<div class="warnrow ok">clean - no artifacts detected</div>'
        miss = "".join(f'<div class="warnrow">missing asset: <code>{e(x)}</code> - placeholder stays</div>'
                       for x in d.get("missing_assets", []))
        rows = "".join(f'<div class="strow"><span class="sn1">{e(str(x["name"])[:34])}</span>'
                       f'<span class="sn2">{x["texts"]} text · {x["images"]} img · '
                       f'serif {x["serif_uses"]} · max {int(x["max_font"])}px</span>'
                       f'<span class="sn3">{x["w"]}×{x["h"]}</span></div>'
                       for x in d["emails"])
        out.append('<details class="run"><summary><span class="cid">BOARD</span>'
                   f'<span class="ct">{e(b)} - {d.get("registered", "?")} registered · '
                   f'{len(d["emails"])} measured · '
                   f'{len(d["artifacts"])} findings</span></summary>'
                   f'<div class="cd">{arts}{miss}{rows}</div></details>')
    return "\n".join(out)


CAL_STAGES = [
    ("cal1", "THE HOLIDAYS", "code", None,
     "The public holidays that land in this month, with their real dates — "
     "from the tool's holidays table, calendar facts that are the same for "
     "every brand. Which ones the brand plans against is its own call, made "
     "in its moments file. Layer 1 of the ground-up build (the owner, 2 Sep)."
     " -> results/calendar-<month>/1-holidays/"),
    ("cal2", "THE CULTURAL MOMENTS", "code", None,
     "The brand's own moments that land in this month — sports seasons, "
     "seasonal rhythms, its avatars' worlds — each resolved from its anchor "
     "to real dates. Together with layer 1 this is the month's skeleton: what "
     "the month IS. A moment not on it is not in this month."
     " -> results/calendar-<month>/2-cultural/"),
    ("cal3", "THE CELLS", "ai", "cal3-cells",
     "Who gets spoken to this month, and who rests — decided by what "
     "sending to it EARNS (revenue per recipient against unsubscribe cost, "
     "from the brand's own record) and by what the skeleton says the month "
     "is. No ceiling, no floor, no sign-off: this stage decides live or "
     "resting, never a count. Every why cites its evidence."
     " -> results/calendar-<month>/3-cells/"),
    ("cal4", "THE ANCHORS", "code", None,
     "Every dated holiday and moment laid onto the month AT ITS REAL DATE, as "
     "ONE send to every live segment it fits. A retail or season-opening "
     "holiday is a full arc around the day — a build-up, the ask, the close. "
     "The build-up is 1 to 4 sends depending on what that holiday has EARNED "
     "for this brand before (its past sends, joined to their revenue per "
     "recipient against the brand's median): no history one send, weak two, "
     "at par three, strong four — enough to liquidate the list in the window. "
     "An observance is one send on the day; a peaked window (Christmas) lands "
     "before the peak. Halloween is the 31st, so its arc ends on the 31st — "
     "never starts on the 2nd."
     " -> results/calendar-<month>/4-anchors/"),
    ("cal5", "THE CONCEPTS", "ai", "cal5-concepts",
     "The rest of the month, in order: an offer for every anchored ask (from "
     "the bank, nowhere else), then the concepts the month makes timely, then "
     "the educational, community and brand sends that keep it from being all "
     "asks. Every send names a preferred date; a moment may only be used inside "
     "its printed window. No send budget and no cap; every why cites."
     " -> results/calendar-<month>/5-concepts/"),
    ("cal6", "THE CATALOGUE", "code", None,
     "Every send typed against the catalogue — category and role read off the "
     "type, anything not in the catalogue dropped — and every offer-carrying "
     "ask completed into its arc from the catalogue's arc index."
     " -> results/calendar-<month>/6-catalogue/"),
    ("cal7", "THE OFFERS", "code", None,
     "Every offer on every send checked against products/offer-bank.md — the "
     "only place an offer can come from. An offer no variant can carry is a "
     "documented borrow if another avatar's section has it, and stripped if "
     "nothing does; an ask left with no offer collapses its arc to the holiday "
     "send alone."
     " -> results/calendar-<month>/7-offers/"),
    ("cal8", "THE AFFILIATE FLOOR", "code", None,
     "One affiliate partner featured a week, every week, if the brand has any "
     "on file — an investor commitment (ruled 1 Sep), not a data signal. "
     "Nothing here ever invents a partner."
     " -> results/calendar-<month>/8-affiliate/"),
    ("cal9", "THE ORDER", "code", None,
     "Dates resolved around the anchors (which keep theirs), hours from the "
     "findings, sources from the library, links along each arc. No two sends "
     "to one segment on adjacent days. No send budget exists — the only thing "
     "ever refused is an exact duplicate, and it is written down."
     " -> results/calendar-<month>/9-order/"),
    ("board", "THE BOARD", "code", None,
     "Every rule checked in code — including that every moment sits inside "
     "its real window — the per-person math, one brief per slot. The month "
     "lands on the board; adopting it stays your act."
     " -> results/calendar-<month>/checks.md + briefs/"),
]


def doc_md(path):
    """A brand doc rendered with the same light renderer as the other tabs."""
    if not path.is_file():
        return ""
    out, table, code = [], [], False
    for ln in path.read_text().splitlines():
        if ln.startswith("```"):
            out.append("</pre>" if code else '<pre class="flow">')
            code = not code
            continue
        if code:
            out.append(e(ln)); continue
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if set("".join(cells)) <= {"-", " ", ":"}: continue
            tag = "th" if not table else "td"
            table.append("<tr>" + "".join(f"<{tag}>{fmt_text(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if table:
            out.append('<div class="tw"><table>' + "".join(table) + "</table></div>"); table = []
        if ln.startswith("### "):
            out.append(f"<h3>{fmt_text(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f'<div class="sh" style="margin-top:30px"><h2>{fmt_text(ln[3:])}</h2></div>')
        elif ln.startswith("# "):
            continue
        elif ln.startswith("---"):
            continue
        elif ln.strip():
            out.append(f"<p class='wf'>{fmt_text(ln)}</p>")
    if table:
        out.append('<div class="tw"><table>' + "".join(table) + "</table></div>")
    return "\n".join(out)


def calflow_tab():
    """The calendar flow, teardown-style: each stage, its prompt verbatim,
    and its latest real output when a run exists."""
    runs = sorted((HERE / "results").glob("calendar-*/run.json"))
    latest_run = None
    if runs:
        latest_run = json.loads(runs[-1].read_text())
        latest_dir = runs[-1].parent
    out = []
    if latest_run:
        out.append(f'<p class="sn"><b>Latest run: {e(latest_run["label"])}</b> — '
                   f'ran start to finish, no sign-off. {latest_run.get("slots", 0)} '
                   f'slots, {latest_run.get("errors", 0)} rule breaks.</p>')
    for key, name, who, prompt_stem, blurb in CAL_STAGES:
        chip = {"code": '<span class="cb b-built">CODE</span>',
                "ai": '<span class="cb b-part">AI · PROMPT BELOW</span>',
                "you": '<span class="cb b-todo">YOU</span>'}[who]
        body = [f'<p>{e(blurb)}</p>']
        if prompt_stem:
            best, bv = None, -1
            for f in (HERE / "prompts").glob(f"{prompt_stem}-v*-*.md"):
                m = re.search(r"-v(\d+)-", f.name)
                if m and int(m.group(1)) > bv:
                    best, bv = f, int(m.group(1))
            if best:
                body.append(f'<details class="sub" open><summary>The prompt, '
                            f'verbatim ({e(best.name)})</summary>'
                            f'<div class="outbox">{fmt_text(best.read_text())}</div></details>')
        if latest_run:
            outfile = {"cal1": "1-holidays/holidays.md",
                       "cal2": "2-cultural/moments.md",
                       "cal3": "3-cells/reasoning.md",
                       "cal4": "4-anchors/anchors.md",
                       "cal5": "5-concepts/reasoning.md",
                       "cal6": "6-catalogue/catalogue.md",
                       "cal7": "7-offers/offers.md",
                       "cal8": "8-affiliate/affiliate.json",
                       "cal9": "9-order/order.md",
                       "board": "checks.md"}.get(key)
            if outfile and (latest_dir / outfile).is_file():
                body.append(f'<details class="sub"><summary>Latest output '
                            f'({e(latest_run["label"])})</summary>'
                            f'<div class="outbox">{fmt_text((latest_dir / outfile).read_text())}</div></details>')
        out.append(f'''<details class="card s-{"built" if who == "code" else ("part" if who == "ai" else "todo")}" open>
<summary><span class="cid">{e(key.upper())}</span><span class="ct">{e(name)}</span>{chip}</summary>
<div class="cd">{"".join(body)}</div></details>''')
    return "\n".join(out)


def wiring_rows():
    """Each brand's wiring, as the doctor reads it — rows connected / missing."""
    import subprocess
    out = []
    for b in sorted(p.name for p in (WORKSPACE / "brands").iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "CLAUDE.md").is_file()):
        try:
            r = subprocess.run([sys.executable, "doctor.py", "--brand", b], cwd=HERE, capture_output=True, text=True, timeout=120)
            rows = [ln for ln in r.stdout.splitlines() if ln.strip().startswith(("OK", "MISSING"))]
            ok = sum(1 for ln in rows if ln.strip().startswith("OK"))
            miss = [ln.split(None, 1)[1].rsplit("  ", 1)[0].strip() for ln in rows if ln.strip().startswith("MISSING")]
            out.append(f'<div class="dr"><b>{e(b)}</b><p>{ok}/{len(rows)} rows connected'
                       + (f' · missing: {e("; ".join(m.split("  ")[0] for m in miss))}' if miss else " · fully wired") + "</p></div>")
        except Exception as ex:
            out.append(f'<div class="dr"><b>{e(b)}</b><p>doctor could not run: {e(str(ex)[:80])}</p></div>')
    return '<div class="drive" style="margin-bottom:18px">' + "".join(out) + "</div>"


def md_render(f):
    out, table, code = [], [], False
    for ln in f.read_text().splitlines():
        if ln.startswith("```"):
            out.append("</pre>" if code else '<pre class="flow">')
            code = not code
            continue
        if code:
            out.append(e(ln))
            continue
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if set("".join(cells)) <= {"-", " ", ":"}:
                continue
            tag = "th" if not table else "td"
            table.append("<tr>" + "".join(f"<{tag}>{fmt_text(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if table:
            out.append('<div class="tw"><table>' + "".join(table) + "</table></div>")
            table = []
        if ln.startswith("### "):
            out.append(f"<h3>{fmt_text(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f'<div class="sh" style="margin-top:34px"><h2>{fmt_text(ln[3:])}</h2></div>')
        elif ln.startswith("# "):
            continue
        elif ln.strip():
            out.append(f"<p>{fmt_text(ln)}</p>")
    if table:
        out.append('<div class="tw"><table>' + "".join(table) + "</table></div>")
    return "\n".join(out)


def workflow_tab():
    """The five workflows (WORKFLOWS.md) with every brand's wiring, then the
    step-by-step flow (WORKFLOW.md)."""
    parts = []
    wf = HERE / "WORKFLOWS.md"
    if wf.is_file():
        parts.append('<div class="sh"><span class="kick">Run on an ongoing basis</span><h2>The five workflows</h2></div>')
        parts.append(wiring_rows())
        parts.append(md_render(wf))
        parts.append('<div class="sh" style="margin-top:44px"><span class="kick">Step by step</span><h2>Inside one email</h2></div>')
    f = HERE / "WORKFLOW.md"
    if not f.is_file():
        return "\n".join(parts) + "<p class='sn'>WORKFLOW.md is missing.</p>"
    return "\n".join(parts) + md_render(f)


def _old_workflow_tab():
    f = HERE / "WORKFLOW.md"
    if not f.is_file():
        return "<p class='sn'>WORKFLOW.md is missing.</p>"
    out, table, code = [], [], False
    for ln in f.read_text().splitlines():
        if ln.startswith("```"):
            out.append("</pre>" if code else '<pre class="flow">')
            code = not code
            continue
        if code:
            out.append(e(ln))
            continue
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if set("".join(cells)) <= {"-", " ", ":"}:
                continue
            tag = "th" if not table else "td"
            table.append("<tr>" + "".join(f"<{tag}>{fmt_text(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if table:
            out.append('<div class="tw"><table>' + "".join(table) + "</table></div>")
            table = []
        if ln.startswith("### "):
            out.append(f"<h3>{fmt_text(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f'<div class="sh" style="margin-top:34px"><h2>{fmt_text(ln[3:])}</h2></div>')
        elif ln.startswith("# "):
            continue
        elif ln.strip():
            out.append(f"<p class='wf'>{fmt_text(ln)}</p>")
    if table:
        out.append('<div class="tw"><table>' + "".join(table) + "</table></div>")
    return "\n".join(out)


def fmt_text(text):
    """Markdown-ish text, safely: escape, then bold/code, keep line breaks."""
    s = e(text.strip())
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", s)
    return s


def stage_list(run):
    order = STAGE_ORDER
    names = STAGE_NAMES
    out = []
    for k in order:
        st = run["stages"].get(k)
        if not st:
            out.append(f'<span class="stg wait">{names[k]}</span>')
        elif st.get("status") == "skipped":
            out.append(f'<span class="stg skip" title="{e(st.get("why", ""))}">{names[k]} — skipped</span>')
        else:
            out.append(f'<span class="stg done">{names[k]}</span>')
    return "".join(out)


def subjects_block(text):
    """Every subject/preview pair, verbatim, none marked better. Loose parse:
    bold/code stripped to text, lines kept."""
    if not text:
        return '<p class="k">Subject lines appear here the moment stage 5 finishes.</p>'
    lines = []
    for ln in text.splitlines():
        ln = re.sub(r"[*_#>`]", "", ln).strip()
        if ln:
            lines.append(f"<div class='sl'>{e(ln)}</div>")
    return "".join(lines)


def discover_calendar_months():
    """Every month the calendar flow has produced, oldest first — so a run of
    consecutive months (Sep, Oct, Nov) reads as one continuous plan, not a
    pile of unordered results folders."""
    out = []
    for d in sorted((HERE / "results").glob("calendar-*")):
        if (d / "slots.json").is_file():
            out.append(d.name)
    return out


def board_month(label):
    """One month's board, self-contained — tiles, mix, weeks, checker notes.
    Used both for the single current month and for the multi-month switcher,
    so the two never show a different picture of the same run."""
    slots, crun, warns = load_month(label)
    warn_ids = {w.split(":", 1)[0] for w in warns if ":" in w}
    month_name = f"{date.fromisoformat(slots[0]['date']):%B %Y}" if slots else label
    if crun and crun.get("brand"):
        month_name += f" · {crun['brand']}"         # two brands share one tree
    by_week = {}
    for s in sorted(slots, key=lambda x: x["date"]):
        wk = date.fromisoformat(s["date"]).isocalendar()[1]
        by_week.setdefault(wk, []).append(s)
    weeks = "".join(
        f'<div class="wk"><div class="wkh">Week of {date.fromisoformat(ss[0]["date"]):%-d %B}</div>'
        + "".join(slot_row(s, warn_ids) for s in ss) + "</div>"
        for ss in by_week.values())
    warn_html = "".join(f'<div class="warnrow">{e(w)}</div>' for w in warns) \
        or '<div class="warnrow ok">Nothing broken, nothing flagged.</div>'
    body = ((mix_bar(slots) + weeks + "<h3>What the checker said</h3>" + warn_html)
            if slots else
            '<div class="warnrow ok">No month is composed. The calendar flow '
            '(its own tab) builds the next one, start to finish — no '
            'checkpoint, no sign-off.</div>')
    return dict(label=label, slots=slots, crun=crun, month_name=month_name,
                body=body, matrix=matrix_section(slots, crun["brand"]))


def months_switcher(panels, active):
    if len(panels) < 2:
        return ""
    btns = "".join(
        f'<button class="mobtn{" active" if lb == active else ""}" data-month="{e(lb)}">'
        f'{e(p["month_name"])} <i>{len(p["slots"])}</i></button>'
        for lb, p in panels.items())
    return f'<div class="mo-switch">{btns}</div>'


def build(compose_label, chain_label):
    all_months = discover_calendar_months()
    month_panels = {lb: board_month(lb) for lb in all_months} if all_months else {}
    active_month = compose_label if compose_label in month_panels else (
        all_months[0] if all_months else compose_label)
    slots, crun, warns = load_month(compose_label)
    warn_ids = {w.split(":", 1)[0] for w in warns if ":" in w}
    chain = load_chain(chain_label) if chain_label else None
    month_name = f"{date.fromisoformat(slots[0]['date']):%B %Y}" if slots else "no month standing"
    by_week = {}
    for s in sorted(slots, key=lambda x: x["date"]):
        wk = date.fromisoformat(s["date"]).isocalendar()[1]
        by_week.setdefault(wk, []).append(s)
    weeks = "".join(
        f'<div class="wk"><div class="wkh">Week of {date.fromisoformat(ss[0]["date"]):%-d %B}</div>'
        + "".join(slot_row(s, warn_ids) for s in ss) + "</div>"
        for ss in by_week.values())

    warn_html = "".join(f'<div class="warnrow">{e(w)}</div>' for w in warns) \
        or '<div class="warnrow ok">Nothing broken, nothing flagged.</div>'

    # the line — five stations, states read off what exists
    chain_done = bool(chain and chain["run"]["stages"].get("stage9", {}).get("status") == "done")
    chain_running = bool(chain and not chain_done)
    stations = [
        ("The brand", "everything true about " + crun["brand"] + ", in one place", "on"),
        ("The calendar flow", (f"wrote {month_name}" if slots else "six stages, start to finish — no checkpoint"), "on"),
        ("The month", (f"{len(slots)} slots, fully specified" if slots else "lands once the flow runs"), "on" if slots else "off"),
        ("The briefs", "one page per slot — production opens nothing else", "on"),
        ("The chain", "ten stages turn a brief into a finished email",
         "on" if chain_done else ("run" if chain_running else "off")),
        ("Your pick", "every subject line ships to this page; choosing is yours", "you"),
    ]
    line = "".join(
        f'<div class="st {cls}"><b>{e(n)}</b><span>{e(d)}</span></div>'
        + ('<div class="ar">→</div>' if i < len(stations) - 1 else "")
        for i, (n, d, cls) in enumerate(stations))

    if chain:
        r = chain["run"]
        done_n = sum(1 for v in r["stages"].values() if v.get("status") == "done")
        first_state = ("finished" if chain_done else f"running — stage {done_n} of 11")
        first_tile = f'{e(r["label"])} · {first_state}'
        chain_panel = f'''<section>
<div class="sh"><span class="kick">Off the line</span><h2>The first email off the line</h2></div>
<p class="sn">Run <code>{e(r["label"])}</code> · built from
<code>{e(Path(r.get("source_path", "")).name)}</code> — one of our own sends,
stripped to structure and refilled with the slot's occasion. The first time
the whole line ran end to end. (Made against the board's earlier draft; the
board above has since been recomposed cell-first.)</p>
<div class="stages">{stage_list(r)}</div>
<h3>Every subject line, none ranked</h3>
<p class="sn">The machine writes them all. Choosing is yours — that is a rule,
not a shortcoming.</p>
<div class="subs">{subjects_block(chain["subjects"])}</div>
</section>'''
    else:
        first_tile = "not yet run"
        chain_panel = ""

    t_p = REPO / "brands" / crun["brand"] / "email-sms/email-types.json"
    if not t_p.is_file():
        t_p = calendar_tool("definitions/send-types.seed.json")
    catalogue = json.loads(t_p.read_text())["types"]
    used_types = {s.get("type") for s in slots}
    if slots:
        tiles = f"""
<div class="tile"><span class="tk">The calendar</span><b>{len(slots)}</b><span>slots on the board for {e(month_name)}</span></div>
<div class="tile"><span class="tk">The catalogue</span><b>{len(used_types)}<i class="of">/ {len(catalogue)}</i></b><span>email types drawn this month</span></div>
<div class="tile"><span class="tk">The checks</span><b>{crun.get("errors", 0)}</b><span>rule breaks · {crun.get("warnings", 0)} warning{"s" if crun.get("warnings", 0) != 1 else ""} for you to read</span></div>
<div class="tile"><span class="tk">Production</span><b class="sm">{first_tile}</b><span>the chain, end to end</span></div>"""
    else:
        tiles = f"""
<div class="tile"><span class="tk">The calendar</span><b class="sm">fresh slate</b><span>no month standing — the calendar flow builds the next one</span></div>
<div class="tile"><span class="tk">The catalogue</span><b>{len(catalogue)}</b><span>email types this brand knows</span></div>
<div class="tile"><span class="tk">Sign-off</span><b class="sm">none</b><span>the flow runs start to finish on the record — nobody approves the cells</span></div>
<div class="tile"><span class="tk">Proving runs</span><b class="sm">archived</b><span>the test months and test emails are filed away</span></div>"""

    drive = '''
<div class="dr"><b>&ldquo;Run November.&rdquo;</b><p>The calendar flow runs
start to finish on the record &mdash; state sheet, cells, moves, arcs, the
affiliate floor, order, checks, briefs. No stop, no sign-off (ruled
2026-08-31: &ldquo;I don&rsquo;t need to be involved at all, this is simply
based on data&rdquo;). The month lands on the board when it&rsquo;s done.</p></div>
<div class="dr"><b>Adopting the month is still your act.</b><p>The flow
decides the plan; running it into Klaviyo campaigns is a separate,
deliberate step you take, always.</p></div>
<div class="dr"><b>&ldquo;Tighten a stage.&rdquo;</b><p>Every prompt is on the calendar
flow tab, verbatim. Say what should change &mdash; the prompt is edited,
versioned, and the next run obeys. The page always shows the version that
actually runs.</p></div>'''

    month_counts = {}
    for s in slots:
        month_counts[s.get("type")] = month_counts.get(s.get("type"), 0) + 1

    css = CSS
    # A month's panel is built apart from the page: a same-quote f-string
    # nested inside another parses only on Python 3.12+, and the mini runs 3.9.
    month_html = "".join(f'''<div class="mo-panel{" active" if lb == active_month else ""}" id="mo-{e(lb)}">
{p["matrix"]}
<section>
<div class="sh"><span class="kick">{e(p["month_name"])}</span><h2>The board — {len(p["slots"])} moves{" , in order" if p["slots"] else ""}</h2></div>
<p class="sn">Every slot is a move in a sequence: it earns, sets up, asks,
recovers or closes. Tap one for why it exists, what it is built from, and the
ground it may not reuse. The five colors are the <b>categories</b>; the bold
word on each row is its <b>type</b> — the full {len(catalogue)}-type catalogue
is its own tab above. Dashed slots are <b>held open</b> — live moments cannot
be planned, so the month leaves room to catch them.</p>
{p["body"]}
</section>
</div>'''
        for lb, p in month_panels.items())
    doc = f'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Email Machine</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,640&family=Instrument+Sans:wght@400;500;600&family=Spline+Sans+Mono:wght@400;500&display=swap">
<style>{css}</style>
<div class="wrap">
<header>
<div class="kick">{e(crun["brand"].upper())} · email · the machine, live</div>
<h1>The Email Machine</h1>
<p class="lede">Brand in, a month out, an email off the line. This page is the
whole state of it — updated every time anything runs.</p>
</header>

<nav class="tabs" role="tablist">
<button class="tab active" data-tab="board">The board</button>
<button class="tab" data-tab="catalogue">The catalogue</button>
<button class="tab" data-tab="formats">The designs</button>
<button class="tab" data-tab="calflow">The calendar flow</button>
<button class="tab" data-tab="sweep">The sweep</button>
<button class="tab" data-tab="workflow">How it runs</button>
<button class="tab" data-tab="runs">Inside the runs</button>
</nav>

<div class="panel active" id="p-board">
<div class="tiles">{tiles}</div>

<section>
<div class="sh"><span class="kick">The line</span><h2>How an email happens</h2></div>
<div class="linewrap"><div class="line">{line}</div></div>
</section>

{months_switcher(month_panels, active_month)}

{month_html}

<section>
<div class="sh"><span class="kick">Driving it</span><h2>You say it, it happens</h2></div>
<div class="drive">{drive}</div>
</section>
</div>

<div class="panel" id="p-catalogue">
<section>
<div class="sh"><span class="kick">Every possible email</span><h2>The catalogue — {len(catalogue)} types</h2></div>
<p class="sn">Everything the brand knows how to send, in the five categories,
cut on one test: <b>whose material is this email made of?</b> Tap any type
for what it is, what it needs, and what must follow it. Badges show how often
it has ever been sent and whether it is on this month's board.</p>
{catalogue_tab(catalogue, used_types, month_counts)}
</section>
</div>

<div class="panel" id="p-formats">
<section>
<div class="sh"><span class="kick">The brand's own templates</span><h2>The designs</h2></div>
<p class="sn">Pulled straight from your design file — the real emails, their
shared design system, and each format's block order with its named image
slots. The full asset vault (about 1,700 product cutouts, photos and
textures from the file) lives on the shared Drive in this same design-formats
home, ready for the designer and for image generation.</p>
{formats_tab(crun["brand"])}
</section>
</div>

<div class="panel" id="p-calflow">
<section>
<div class="sh"><span class="kick">Six stages · three code, two AI, one index</span><h2>The calendar flow</h2></div>
<p class="sn">How a month gets made, teardown-style: every stage, who runs it,
the exact prompt where AI runs it, and the real output once it has run. The
AI decides <b>who</b> and <b>what</b>; code does every mechanical thing —
arcs, dates, budgets, sources — so the same inputs give the same calendar.</p>
{calflow_tab()}
</section>

<section>
<div class="sh"><span class="kick">The big domino, in full</span><h2>The cells decision</h2></div>
<p class="sn">How many emails go to which segment — the one stage everything
else is downstream of, documented to the nuance so any brand can be loaded
onto it.</p>
{doc_md(HERE / "CELLS.md")}
</section>
</div>

<div class="panel" id="p-sweep">
<section>
<div class="sh"><span class="kick">Board by board, in month order</span><h2>The sweep</h2></div>
<p class="sn">Every board from the format bank measured email by email, with
the handoff's three artifact checks: dead image boxes, heavy text overlaps,
missing assets. Findings queue for fixing; clean boards say so.</p>
{sweep_tab(crun["brand"])}
</section>
</div>

<div class="panel" id="p-workflow">
<section>
<div class="sh"><span class="kick">Documented, step by step</span><h2>How it runs</h2></div>
{workflow_tab()}
</section>
</div>

<div class="panel" id="p-runs">
<section>
<div class="sh"><span class="kick">Stage by stage</span><h2>Inside the runs</h2></div>
<p class="sn">What actually happened, the way the teardown tool shows it: each
run, each stage, its timing — and the real output of every stage, with the
exact prompt that produced it underneath. Nothing summarized away.</p>
{runs_tab()}
</section>
</div>

<footer>Generated {datetime.now():%-d %B %Y, %H:%M} · composer {e(crun.get("prompt_file", ""))} ·
every number on this page is read off the record, never typed.</footer>
</div>
<script>
(function() {{
  var tabs = document.querySelectorAll('.tab');
  function show(name) {{
    tabs.forEach(function(t) {{ t.classList.toggle('active', t.dataset.tab === name); }});
    document.querySelectorAll('.panel').forEach(function(p) {{
      p.classList.toggle('active', p.id === 'p-' + name);
    }});
    try {{ localStorage.setItem('em-tab', name); }} catch (err) {{}}
  }}
  tabs.forEach(function(t) {{ t.addEventListener('click', function() {{ show(t.dataset.tab); }}); }});
  var saved = null;
  try {{ saved = localStorage.getItem('em-tab'); }} catch (err) {{}}
  if (saved && document.getElementById('p-' + saved)) show(saved);
}})();
(function() {{
  var mobtns = document.querySelectorAll('.mobtn');
  mobtns.forEach(function(b) {{
    b.addEventListener('click', function() {{
      mobtns.forEach(function(x) {{ x.classList.toggle('active', x === b); }});
      document.querySelectorAll('.mo-panel').forEach(function(p) {{
        p.classList.toggle('active', p.id === 'mo-' + b.dataset.month);
      }});
      try {{ localStorage.setItem('em-month', b.dataset.month); }} catch (err) {{}}
    }});
  }});
  var savedMo = null;
  try {{ savedMo = localStorage.getItem('em-month'); }} catch (err) {{}}
  if (savedMo && document.getElementById('mo-' + savedMo)) {{
    mobtns.forEach(function(b) {{ b.classList.toggle('active', b.dataset.month === savedMo); }});
    document.querySelectorAll('.mo-panel').forEach(function(p) {{
      p.classList.toggle('active', p.id === 'mo-' + savedMo);
    }});
  }}
}})();
// Diagrams: the artifact host draws pre.mermaid itself (and blocks this CDN);
// the local live page needs mermaid loaded here. Failure is silent by design.
(function() {{
  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js';
  s.onload = function() {{
    try {{ mermaid.initialize({{startOnLoad: false, theme: 'neutral'}});
          mermaid.run({{querySelector: 'pre.mermaid'}}); }} catch (err) {{}}
  }};
  document.head.appendChild(s);
}})();
</script>'''
    (HERE / "dashboard.html").write_text(doc)

    # the Markdown mirror — the team's copy of the same picture
    md = [f"# The Email Machine — {month_name}", "",
          f"{len(slots)} slots · {crun.get('errors', 0)} rule breaks · "
          f"{crun.get('warnings', 0)} warnings.", "",
          "| # | Date | Hour | Segment | Avatar | Sub-avatar | Category | Type | Role | Occasion |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(slots, key=lambda x: x["date"]):
        md.append(f"| {s['id']} | {s['date']} | {s['hour']:02d} | "
                  f"{s['segment'].replace('Core | ', '')} | {s['avatar']} | "
                  f"{s.get('sub_avatar') or 'none'} | "
                  f"{s['category']} | {s['type']} | {s['role']} | {s['occasion']} |")
    md += ["", "## Checker", ""] + [f"- {w}" for w in warns or ["nothing flagged"]]
    if chain:
        md += ["", f"## First email — {chain['run']['label']}", "",
               "Subject lines (all ship, none ranked):", "```",
               chain["subjects"] or "(pending)", "```"]
    (HERE / "dashboard.md").write_text("\n".join(md) + "\n")
    print(f"dashboard.html ({len(doc):,} bytes) · dashboard.md")


CSS = """
:root{--bg:#F1F0EA;--card:#FFFFFF;--ink:#191B1D;--mut:#676C73;--line:#DBD9D2;--hair:#E9E7E1;
 --acc:#2E5D50;--acc-bg:#DFEBE6;
 --promo:#A8690C;--promo-bg:#F5EAD6;--edu:#39648F;--edu-bg:#E2EAF3;
 --cult:#7B58A8;--cult-bg:#ECE5F4;--comm:#37795A;--comm-bg:#E0EEE6;
 --brand:#A34E3B;--brand-bg:#F5E4DE;--aff:#2C7A87;--aff-bg:#DEEFF2;
 --ok:#1D6A4B;--warn:#8A5A10;--warn-bg:#F4EBD8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#0E1012;--card:#16191C;--ink:#E6E8EA;--mut:#8E959D;--line:#272B30;--hair:#1E2226;
 --acc:#74B4A2;--acc-bg:#12251F;
 --promo:#D8A253;--promo-bg:#2A2010;--edu:#84AEDA;--edu-bg:#14212F;
 --cult:#B598DD;--cult-bg:#231A30;--comm:#7DBD9C;--comm-bg:#122519;
 --brand:#D98A73;--brand-bg:#2B1813;--aff:#5FC3D6;--aff-bg:#0F262A;
 --ok:#5FBE94;--warn:#D2A24C;--warn-bg:#291F12}}
:root[data-theme="dark"]{
 --bg:#0E1012;--card:#16191C;--ink:#E6E8EA;--mut:#8E959D;--line:#272B30;--hair:#1E2226;
 --acc:#74B4A2;--acc-bg:#12251F;
 --promo:#D8A253;--promo-bg:#2A2010;--edu:#84AEDA;--edu-bg:#14212F;
 --cult:#B598DD;--cult-bg:#231A30;--comm:#7DBD9C;--comm-bg:#122519;
 --brand:#D98A73;--brand-bg:#2B1813;--aff:#5FC3D6;--aff-bg:#0F262A;
 --ok:#5FBE94;--warn:#D2A24C;--warn-bg:#291F12}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:15.5px/1.6 "Instrument Sans",system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:980px;margin:0 auto;padding:46px 20px 90px}
.kick{font:500 11px/1 "Spline Sans Mono",ui-monospace,Menlo,monospace;letter-spacing:.18em;
 text-transform:uppercase;color:var(--mut)}
h1{font-family:Fraunces,Georgia,serif;font-weight:640;font-size:clamp(34px,5.4vw,50px);
 line-height:1.04;letter-spacing:-.02em;margin:12px 0 0;text-wrap:balance}
h2{font-family:Fraunces,Georgia,serif;font-weight:600;font-size:25px;letter-spacing:-.014em;margin:6px 0 0}
h3{font-size:16.5px;font-weight:600;letter-spacing:-.01em;margin:30px 0 6px}
.lede{font-size:17.5px;color:var(--mut);max-width:56ch;margin:14px 0 0}
section{margin-top:56px}
.sh{border-top:2px solid var(--ink);padding-top:12px;margin-bottom:16px}
.sn{color:var(--mut);max-width:64ch;margin:8px 0 14px;font-size:14.5px}
code{font:13px "Spline Sans Mono",ui-monospace,monospace;background:var(--hair);
 padding:1px 5px;border-radius:4px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:34px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;
 display:flex;flex-direction:column;gap:2px}
.tk{font:500 10.5px/1 "Spline Sans Mono",monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
.tile b{font-family:Fraunces,Georgia,serif;font-weight:640;font-size:30px;margin-top:4px;
 font-variant-numeric:tabular-nums}
.tile b.sm{font-size:16px;line-height:1.3;font-family:"Instrument Sans",sans-serif;font-weight:600}
.tile b .of{font-size:16px;font-style:normal;color:var(--mut);font-weight:500}
.matrix{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.mrow{display:grid;grid-template-columns:200px 44px 1fr;gap:10px;padding:9px 14px;
 border-bottom:1px solid var(--hair);align-items:baseline;font-size:13.5px}
.mrow:last-child{border-bottom:none}
.mrow.head{background:var(--hair)}
.mrow.head .mav{font-weight:600}
.mav{font:500 12.5px "Spline Sans Mono",monospace}
.mav.sub{padding-left:16px;color:var(--ink)}
.mn{font-variant-numeric:tabular-nums;font-weight:600;text-align:right}
.ms{color:var(--mut);font-size:12.5px}
.mrow.cold .ms,.mrow.cold .mn{color:var(--warn)}
@media(max-width:640px){.mrow{grid-template-columns:130px 30px 1fr}}
.tile span:last-child{font-size:13px;color:var(--mut)}
.linewrap{overflow-x:auto;padding-bottom:6px}
.line{display:flex;align-items:stretch;gap:8px;min-width:840px}
.st{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:10px 12px;
 flex:1;display:flex;flex-direction:column;gap:3px}
.st b{font-size:14px;font-weight:600}
.st span{font-size:12px;color:var(--mut);line-height:1.4}
.st.on{border-top:3px solid var(--acc)}
.st.run{border-top:3px solid var(--warn);background:var(--warn-bg)}
.st.off{border-top:3px solid var(--line);opacity:.7}
.st.you{border-top:3px solid var(--ink)}
.ar{align-self:center;color:var(--mut);flex:0}
.mix{display:flex;height:12px;border-radius:6px;overflow:hidden;gap:2px;margin:6px 0 8px}
.seg{display:block}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:22px;font-size:12.5px;color:var(--mut)}
.lg{display:flex;align-items:center;gap:6px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.c-promo{background:var(--promo)}.c-edu{background:var(--edu)}.c-cult{background:var(--cult)}
.c-comm{background:var(--comm)}.c-brand{background:var(--brand)}.c-aff{background:var(--aff)}
em.cat{font:500 10.5px/1 "Spline Sans Mono",monospace;letter-spacing:.1em;text-transform:uppercase;
 font-style:normal;padding:3px 7px;border-radius:5px;margin-left:8px;vertical-align:2px}
em.c-promo{background:var(--promo-bg);color:var(--promo)}
em.c-edu{background:var(--edu-bg);color:var(--edu)}
em.c-cult{background:var(--cult-bg);color:var(--cult)}
em.c-comm{background:var(--comm-bg);color:var(--comm)}
em.c-brand{background:var(--brand-bg);color:var(--brand)}
em.c-aff{background:var(--aff-bg);color:var(--aff)}
.wkh{font:500 11px/1 "Spline Sans Mono",monospace;letter-spacing:.14em;text-transform:uppercase;
 color:var(--mut);margin:26px 0 8px}
.slot{background:var(--card);border:1px solid var(--line);border-radius:9px;margin-bottom:7px}
.slot.held{border-style:dashed;background:transparent}
.slot summary{display:flex;align-items:center;gap:14px;padding:10px 14px;cursor:pointer;list-style:none}
.slot summary::-webkit-details-marker{display:none}
.slot summary:focus-visible{outline:2px solid var(--acc);border-radius:9px}
.d{display:flex;flex-direction:column;align-items:center;width:34px;flex:none}
.d b{font-family:Fraunces,Georgia,serif;font-weight:640;font-size:19px;font-variant-numeric:tabular-nums}
.d i{font:500 10px/1 "Spline Sans Mono",monospace;text-transform:uppercase;color:var(--mut);font-style:normal;margin-top:1px}
.body{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}
.t{font-weight:600;font-size:14.5px}
.occ{font-size:13px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chips{display:flex;gap:5px;flex:none;flex-wrap:wrap;justify-content:flex-end;max-width:270px}
.chip{font:500 11px/1 "Spline Sans Mono",monospace;padding:4px 7px;border-radius:5px;
 background:var(--hair);color:var(--mut)}
.chip.av{background:var(--acc-bg);color:var(--acc)}
.chip.hr{background:transparent;border:1px solid var(--line)}
.why{padding:2px 16px 12px 62px;font-size:13.5px}
.why p{margin:6px 0}
.why .k{color:var(--mut)}
.why .unf{color:var(--warn)}
.flag{background:var(--warn-bg);color:var(--warn);border-radius:6px;padding:6px 10px;
 font-size:12.5px;margin-top:8px}
.warnrow{background:var(--warn-bg);color:var(--warn);border-radius:8px;padding:9px 13px;
 font-size:13.5px;margin-bottom:6px}
.warnrow.ok{background:var(--acc-bg);color:var(--ok)}
.stages{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 4px}
.stg{font:500 12px/1 "Spline Sans Mono",monospace;padding:6px 9px;border-radius:6px}
.stg.done{background:var(--acc-bg);color:var(--ok)}
.stg.skip{background:var(--hair);color:var(--mut);text-decoration:line-through}
.stg.wait{background:transparent;border:1px dashed var(--line);color:var(--mut)}
.subs{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin-top:10px}
.sl{padding:7px 0;border-bottom:1px solid var(--hair);font-size:14px}
.sl:last-child{border-bottom:none}
.drive{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px}
.dr{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.dr b{font-family:Fraunces,Georgia,serif;font-weight:600;font-size:17px}
.dr p{font-size:13.5px;color:var(--mut);margin:8px 0 0;line-height:1.55}
footer{margin-top:64px;padding-top:14px;border-top:1px solid var(--line);
 font-size:12px;color:var(--mut)}
.tabs{position:sticky;top:0;z-index:5;display:flex;gap:6px;margin-top:30px;padding:10px 0;
 background:var(--bg);border-bottom:1px solid var(--line)}
.tab{font:600 13.5px "Instrument Sans",sans-serif;color:var(--mut);background:transparent;
 border:1px solid var(--line);border-radius:99px;padding:8px 15px;cursor:pointer}
.tab.active{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.tab:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.panel{display:none}
.panel.active{display:block}
.mo-switch{display:flex;gap:8px;margin:22px 0 4px;flex-wrap:wrap}
.mobtn{font:600 13px "Instrument Sans",sans-serif;color:var(--ink);background:var(--card);
 border:1px solid var(--line);border-radius:99px;padding:7px 14px 7px 16px;cursor:pointer}
.mobtn i{font:500 11px "Spline Sans Mono",monospace;font-style:normal;color:var(--mut);margin-left:6px}
.mobtn.active{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.mobtn.active i{color:var(--bg);opacity:.7}
.chip.multi{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chip.anc{background:var(--acc-bg);color:var(--acc);border-color:var(--acc)}
.mo-panel{display:none}
.mo-panel.active{display:block}
.wellhd{display:flex;align-items:baseline;gap:9px;margin:34px 0 10px;border-bottom:1px solid var(--line);
 padding-bottom:8px}
.wellhd h3{margin:0;font-size:17px}
.wellhd .whn{margin-left:auto;font:500 11px "Spline Sans Mono",monospace;color:var(--mut)}
.tygrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:8px}
.ty{background:var(--card);border:1px solid var(--line);border-radius:9px}
.ty.c-b-promo{border-left:3px solid var(--promo)}.ty.c-b-edu{border-left:3px solid var(--edu)}
.ty.c-b-cult{border-left:3px solid var(--cult)}.ty.c-b-comm{border-left:3px solid var(--comm)}
.ty.c-b-brand{border-left:3px solid var(--brand)}
.ty summary{padding:10px 13px;cursor:pointer;list-style:none;display:flex;flex-wrap:wrap;gap:6px;
 align-items:baseline}
.ty summary::-webkit-details-marker{display:none}
.tyn{font-weight:600;font-size:14px}
.tyk{font:500 11px "Spline Sans Mono",monospace;color:var(--mut)}
.tbs{margin-left:auto;display:flex;gap:4px}
.tb{font:500 10px "Spline Sans Mono",monospace;padding:3px 6px;border-radius:4px;
 background:var(--hair);color:var(--mut)}
.tb.on{background:var(--acc-bg);color:var(--acc)}
.tb.u-new{background:var(--acc-bg);color:var(--acc)}
.tb.u-rare{background:var(--warn-bg);color:var(--warn)}
.tyd{padding:0 14px 12px;font-size:13.5px}
.tyd p{margin:6px 0}
.tyd .k{color:var(--mut);font-size:12.5px}
.card,.run{background:var(--card);border:1px solid var(--line);border-radius:9px;margin-bottom:7px}
.card.s-built{border-left:3px solid var(--ok)}
.card.s-part{border-left:3px solid var(--warn)}
.card.s-todo{border-left:3px solid var(--line)}
.card summary,.run summary{display:flex;gap:10px;align-items:baseline;padding:11px 14px;
 cursor:pointer;list-style:none;flex-wrap:wrap}
.card summary::-webkit-details-marker,.run summary::-webkit-details-marker{display:none}
.cid{font:600 11px "Spline Sans Mono",monospace;color:var(--mut);flex:none}
.ct{font-weight:600;font-size:14px;flex:1;min-width:200px}
.cb{font:500 10px "Spline Sans Mono",monospace;padding:3px 7px;border-radius:4px}
.cb.b-built{background:var(--acc-bg);color:var(--ok)}
.cb.b-part{background:var(--warn-bg);color:var(--warn)}
.cb.b-todo{background:var(--hair);color:var(--mut)}
.cd{padding:2px 16px 12px;font-size:13.5px}
.cd p{margin:7px 0}
.cd .k{color:var(--mut)}
.cardflow{background:var(--card);border:1px solid var(--line);border-radius:10px;
 padding:10px;margin-bottom:14px;overflow-x:auto}
.strow{display:flex;gap:10px;align-items:baseline;padding:9px 12px;border:1px solid var(--hair);
 border-radius:8px;margin:6px 0;flex-wrap:wrap}
details.strow{display:block}
details.strow summary{display:flex;gap:10px;align-items:baseline;cursor:pointer;list-style:none;flex-wrap:wrap}
details.strow summary::-webkit-details-marker{display:none}
.strow.done2{border-color:var(--line)}
.strow.skipd{opacity:.65}
.strow.wait{border-style:dashed;color:var(--mut)}
.sn1{font-weight:600;font-size:13.5px;min-width:110px}
.sn2{color:var(--mut);font-size:12.5px;flex:1;min-width:200px}
.sn3{font:500 11px "Spline Sans Mono",monospace;color:var(--mut)}
.outbox{background:var(--bg);border:1px solid var(--hair);border-radius:8px;padding:12px 14px;
 margin:8px 0;font-size:13px;line-height:1.6;white-space:pre-wrap;max-height:420px;overflow:auto}
details.sub{margin:6px 0}
details.sub summary{font:500 12px "Spline Sans Mono",monospace;color:var(--mut);cursor:pointer}
.fmtrow{display:flex;gap:12px;overflow-x:auto;padding-bottom:10px;margin:6px 0 20px}
.fmt{margin:0;flex:none;width:160px}
.fmt img{width:160px;border-radius:8px;border:1px solid var(--line);display:block}
.fmt figcaption{font:500 11px "Spline Sans Mono",monospace;color:var(--mut);margin-top:6px;
 text-transform:capitalize}
.tw{overflow-x:auto;margin:10px 0 18px}
.tw table{border-collapse:collapse;font-size:13px;min-width:640px}
.tw th{text-align:left;font:600 11px "Spline Sans Mono",monospace;text-transform:uppercase;
 letter-spacing:.06em;color:var(--mut);padding:8px 12px;border-bottom:2px solid var(--ink)}
.tw td{padding:8px 12px;border-bottom:1px solid var(--hair);vertical-align:top;max-width:220px}
p.wf{max-width:70ch;font-size:14.5px;margin:8px 0}
pre.flow{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:14px 16px;
 font:12.5px/1.6 "Spline Sans Mono",monospace;overflow-x:auto;color:var(--mut)}
.adopted{font:600 10.5px "Spline Sans Mono",monospace;letter-spacing:.1em;text-transform:uppercase;
 background:var(--acc-bg);color:var(--ok);padding:5px 9px;border-radius:5px;vertical-align:4px;margin-left:10px}
@media(max-width:640px){.chips{display:none}.occ{white-space:normal}}
@media(prefers-reduced-motion:no-preference){.slot{transition:border-color .15s}}
"""

if __name__ == "__main__":
    latest = sorted([p for p in (HERE / "results").iterdir()
                     if p.is_dir() and (p / "slots.json").is_file()],
                    key=lambda p: p.stat().st_mtime)
    compose_label = sys.argv[1] if len(sys.argv) > 1 else (
        latest[-1].name if latest else "compose-none")
    chain_label = sys.argv[2] if len(sys.argv) > 2 else "sep-01"
    build(compose_label, chain_label)
