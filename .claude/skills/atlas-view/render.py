#!/usr/bin/env python3
"""Render one curated atlas page for one subject, from the compiled atlas ONLY.

    python3 .claude/skills/atlas-view/render.py <subject> [--out <file.html>]

<subject> is a workflow trace id (`dashboard`), a component (`video-teardown` or
`component:video-teardown`), or several components joined by `+`
(`qc-checks+quality-checks`). Every fact on the page comes from
platform/data/atlas/data.json (and its stamp, last-refresh.json). Nothing is
hand-held: where the atlas does not know something, the page says so instead of
filling it in. Refuses (exit 2) rather than guessing when a subject does not resolve.
"""
import os
import argparse, html, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import flowcheck  # noqa: E402
import picture  # noqa: E402


def root():
    try:
        return Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    except Exception:
        return Path.cwd()


ROOT = root()
DATA = Path(os.environ["ATLAS_DATA"]) if os.environ.get("ATLAS_DATA") else ROOT / "platform/data/atlas/data.json"  # ATL-53 (atlas daily): a fresh compile wins
STAMP = ROOT / "platform/data/atlas/last-refresh.json"
FLOWS = ROOT / "new-workflow-design/builds/atlas/flows"  # pilot home of flow files (atlas flow model, 2026-09-30)
BRIEFS = ROOT / "new-workflow-design/builds/atlas/triage/issue-briefs"  # ATL-27 (P0 P1 issue briefs) sidecars, SCHEMA §5
e = lambda s: html.escape(str(s if s is not None else "").replace("**", ""))


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the data
def load(path):
    d = json.loads(Path(path).read_text())
    stamp = None
    if STAMP.is_file():
        stamp = json.loads(STAMP.read_text()).get("refreshed_at")
    ch = d["chain"]
    nodes = {n["id"]: n for n in ch["nodes"]}
    traces = {t["id"]: t for t in ch["traces"]}
    tools = {t["path"].split("/")[-1]: t for t in d["system"]["tools"] if t.get("station") == "components"}
    residents = {c["name"]: c for c in d["system"]["components"]}
    findings = [dict(f, cls=c["title"], key=c["key"]) for c in d["orphan_drift"]["classes"] for f in c["findings"]]
    # The compiled flows (ATL-11 (compiler reads flows), SI-19 (ready drafts flow)): pilot files and run-folder
    # flow.json, newest per target, each with the compiler's claim checks. --flows overrides per component.
    compiled = [x for x in d["system"].get("flows") or [] if isinstance(x.get("flow"), dict)]
    return dict(d=d, stamp=stamp, cols=ch["columns"], nodes=nodes, traces=traces,
                tools=tools, residents=residents, findings=findings, legend=ch.get("type_legend", {}),
                flows={x["component"]: x["flow"] for x in compiled},
                checks={x["component"]: x["checks"] for x in compiled if isinstance(x.get("checks"), dict)},
                cards={c["id"]: c.get("state") for f in d["system"].get("card_families") or [] for c in f.get("cards") or []})


def attach_flows(A, flows_dir):
    """A local folder of flow files, checked here (flowcheck.py): an override on top of the compiled flows,
    for drafting before a flow reaches main."""
    fd = Path(flows_dir)
    if not fd.is_dir():
        return
    local = flowcheck.load_flows(fd)
    A["flows"].update(local)
    A["checks"].update({n: flowcheck.check_flow(f, A["d"]) for n, f in local.items()})


def resolve(A, subject):
    parts = [p.strip() for p in subject.split("+") if p.strip()]
    if not parts:
        raise Refused("no subject given")
    out = []
    for p in parts:
        name = p.split(":", 1)[1] if p.startswith("component:") else p
        if not p.startswith("component:") and p in A["traces"] and len(parts) == 1:
            out.append(("trace", p))
        elif f"component:{name}" in A["nodes"] or name in A["residents"] or name in A.get("flows", {}):
            out.append(("component", name))
        else:
            known = sorted(A["traces"]) + sorted(A["residents"])
            raise Refused(f"`{p}` is neither a workflow trace nor a component the atlas knows. "
                          f"Known: {', '.join(known)}")
    return out


def drift_for(A, keys):
    keys = set(keys)
    return [f for f in A["findings"] if f.get("subject") in keys]


# ---------------------------------------------------------------- pieces
SEV = {"crit": "crit", "warn": "warn", "note": "idle"}


def chips(types):
    return "".join(f'<span class="t t{e(t)}" title="{e(t)}">{e(t)}</span>' for t in (types or []))


def status_pill(s):
    cls = {"live": "ok", "building": "warn", "not wired": "crit"}.get(s or "", "idle")
    return f'<span class="pill p-{cls}">{e(s or "status unstated")}</span>'


def node_card(A, nid, mark="", does=None):
    n = A["nodes"].get(nid)
    if not n:
        return f'<div class="node miss"><b>{e(nid)}</b><span class="note">not a node on the atlas</span></div>'
    body = f'<p class="does">{e(does)}</p>' if does else (f'<p class="nn">{e(n.get("note"))}</p>' if n.get("note") else "")
    own = f'<span class="own">{e(n["owner"])}</span>' if n.get("owner") else ""
    return (f'<div class="node {mark}"><div class="nh"><b>{e(n["label"])}</b>{chips(n.get("types"))}</div>'
            f'<div class="nm">{status_pill(n.get("status"))}{own}</div>{body}</div>')


def chain_strip(A, by_col, highlight=()):
    cols = []
    for c in A["cols"]:
        ids = by_col.get(c["col"], [])
        inner = "".join(node_card(A, nid, "hit" if nid in highlight else "") for nid in ids) \
            or '<div class="empty">nothing on this route</div>'
        cols.append(f'<div class="col"><div class="ch"><span class="ci">{c["index"]}</span>'
                    f'<b>{e(c["label"])}</b></div>{inner}</div>')
    return f'<div class="cstrip">{"".join(cols)}</div>'


def legend(A):
    items = "".join(f'<span>{chips([k])} {e(v)}</span>' for k, v in A["legend"].items())
    return f'<div class="legend">{items}<span><span class="sw hit"></span> the subject</span></div>'


def drift_block(fs, what):
    if not fs:
        return f'<p class="note">The atlas raises no drift finding about {e(what)}.</p>'
    rows = "".join(f'<tr><td><span class="pill p-{SEV.get(f["severity"], "idle")}">{e(f["severity"])}</span></td>'
                   f'<td>{e(f["cls"])}</td><td>{e(f["detail"])}</td><td class="src">{e(f.get("source"))}</td></tr>'
                   for f in fs)
    return ('<div class="tw"><table><thead><tr><th>Severity</th><th>Kind</th><th>Finding</th><th>Where</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')


def e2e_block(t):
    if not t.get("e2e"):
        return '<p class="note">The atlas holds no end-to-end stage list for this workflow.</p>'
    lis = []
    for s in t["e2e"]:
        unc = ' <span class="u">uncertain</span>' if s.get("uncertain") else ""
        sop = ' <span class="sop">has SOP draft</span>' if s.get("sop") or s.get("sop_ref") else ""
        lis.append(f'<li class="{"unc" if s.get("uncertain") else ""}">{chips(s.get("types") or [s.get("who")])}'
                   f'<span>{e(s["text"])}{unc}{sop}</span></li>')
    return f'<ol class="stages">{"".join(lis)}</ol>'


def cards_block(t):
    c = t.get("cards") or {}
    if not c.get("families"):
        a = c.get("absent") or {}
        why = f' ({e(a.get("reason"))}: {e(a.get("detail"))})' if a else ""
        return f'<p class="note">No card family joins to this workflow{why}.</p>'
    fams = []
    for f in c["families"]:
        cnt = {k: v for k, v in (f.get("counts") or {}).items() if v and k != "total"}
        counts = " · ".join(f"{v} {e(k)}" for k, v in cnt.items())
        fams.append(f'<li><b>{e(f["label"])}</b> <span class="note">{counts}</span></li>')
    over = "".join(f'<li><b>{e(o["label"])}</b>: ' + ", ".join(f'{e(x["id"])} <span class="note">({e(x["state"])})</span>'
                                                              for x in o["cards"]) + "</li>"
                   for o in c.get("node_overlay") or [])
    over = f'<h3>Cards placed on a node of this route</h3><ul class="plain">{over}</ul>' if over else ""
    return f'<ul class="plain">{"".join(fams)}</ul>{over}'


def links_block(t):
    rows = [f'<li>feeds <b>{e(x["workflow"])}</b>: {e(x.get("what"))}</li>' for x in t.get("feeds") or []]
    rows += [f'<li>consumes <b>{e(x["workflow"])}</b>: {e(x.get("what"))}</li>' for x in t.get("consumes") or []]
    return f'<ul class="plain">{"".join(rows)}</ul>' if rows else '<p class="note">No workflow link in or out.</p>'


# ---------------------------------------------------------------- subjects
def trace_page(A, tid):
    t = A["traces"][tid]
    by_col = {}
    for r in t["resolved"]:
        by_col.setdefault(r["col"], []).append(r["node"])
    steps = "".join(
        f'<li><span class="sn">{i}</span>{node_card(A, r["node"], "" if r.get("wired", True) else "dead", r.get("does"))}'
        f'{"" if r.get("does") else "<span class=note>no per-step description on file; the node note is shown</span>"}</li>'
        for i, r in enumerate(t["resolved"], 1))
    dead = f'<p class="cckill">Value stops at: {e(", ".join(t["dead_at"]))}</p>' if t.get("dead_at") else ""
    skips = f'Skips: {e(", ".join(t.get("skips_columns") or []))}.' if t.get("skips_columns") else ""
    fs = drift_for(A, {tid, t.get("build")})
    head = dict(
        eyebrow="Upright Atlas · a workflow",
        name=tid.replace("-", " ").capitalize(),
        title=t.get("label") or tid,
        pills=[f'stage: {t.get("stage")}', f'{len(t["steps"])} steps', f'{t.get("e2e_stages", 0)} stages',
               f'{t.get("uncertain_stages", 0)} uncertain', "reaches a view" if t.get("reaches_views") else "never reaches a view"],
        lede=t.get("note") or "")
    body = [
        sec("1 · The chain", "Where this workflow runs across the org's resources",
            legend(A) + chain_strip(A, by_col) + f'<p class="note">{skips} Columns run in hop order, sources to people.</p>'),
        sec("2 · Step by step", "What this workflow does at each station", dead + f'<ol class="steps">{steps}</ol>'),
        sec("3 · End to end", "What actually happens, and who does it", e2e_block(t)),
        sec("4 · Around it", "Workflows it feeds and consumes", links_block(t)),
        sec("5 · Cards", "The work carded against it", cards_block(t)),
        sec("6 · Drift", "What the atlas flags about it", drift_block(fs, "this workflow")),
    ]
    return head, body


def component_parts(A, name):
    nid = f"component:{name}"
    crossing = [t for t in A["traces"].values() if nid in t["steps"]]
    up, down, by_col = [], [], {}
    for t in crossing:
        i = t["steps"].index(nid)
        for r in t["resolved"]:
            by_col.setdefault(r["col"], [])
            if r["node"] not in by_col[r["col"]]:
                by_col[r["col"]].append(r["node"])
        up += [r for r in t["resolved"][:i] if r["node"] not in [x["node"] for x in up]]
        down += [r for r in t["resolved"][i + 1:] if r["node"] not in [x["node"] for x in down]]
    if not crossing and nid in A["nodes"]:
        by_col = {"components": [nid]}
    return nid, crossing, up, down, by_col


def system_path(tool):
    """→ one line for the header, or None. compile.py sets `status` only for none/unreadable; a filed
    system-run record (SI-17 (system runs filed)) carries skill · verdict · label · record instead."""
    ss = tool.get("system_status") or {}
    if ss.get("status") in (None, "none") and not ss.get("skill"):
        return None
    if ss.get("status") == "unreadable":
        return f'record unreadable ({ss.get("record", "")})'
    words = {"fit": "fit", "ready": "ready check", "review": "system review"}
    head = words.get(ss.get("skill"), ss.get("skill") or "run")
    tail = " · ".join(str(x) for x in (ss.get("verdict"), ss.get("label")) if x)
    return head + (f" — {tail}" if tail else "") + (f' ({ss["memo_path"]})' if ss.get("memo_path") else "")


def facts(A, name):
    """The design copy's header block — Since · Owner · Run · Emits … — from data only."""
    nid, crossing, *_ = component_parts(A, name)
    tool = A["tools"].get(name) or {}
    res = A["residents"].get(name) or {}
    ss = system_path(tool) or "none yet"
    rb = tool.get("runs_by") or {}
    wf = ", ".join(f'{t.get("label") or t["id"]} (stage: {t.get("stage")})' for t in crossing)
    rows = [("Since", res.get("since")), ("Owner", tool.get("owner") or res.get("owner")),
            ("Takes", tool.get("takes")), ("Makes", tool.get("makes")), ("Does not", tool.get("does_not")),
            ("Run", tool.get("command")), ("Runs by", (rb.get("value") or "") + (" (default)" if rb.get("source") == "default" else "")),
            ("Contract", res.get("contract")), ("System path", ss),
            ("Workflows through it", f"{len(crossing)}" + (f" — {wf}" if wf else ""))]
    dl = "".join(f'<dt>{e(k)}</dt><dd>{e(v) if v else "<span class=gap>not in the atlas</span>"}</dd>' for k, v in rows)
    return f'<dl class="kv">{dl}</dl>'


def gaps(A, name):
    """What a reviewer needs that the compiled atlas does not hold — each one a proposal, never filled in."""
    nid, crossing, *_ = component_parts(A, name)
    tool = A["tools"].get(name) or {}
    res = A["residents"].get(name) or {}
    if name in A["flows"]:
        rv = (A["flows"][name].get("review") or {}).get("state") or "draft"
        g = [] if rv == "approved" else ["<b>email_lead's review.</b> The flow is a machine draft, not yet reviewed. "
                                         "She approves it and checks with the owner where she needs to (ruled 2026-09-30)."]
        g += [x for x in _other_gaps(A, name)]
        return '<ul class="gaps">' + "".join(f"<li>{x}</li>" for x in g) + "</ul>" if g else '<p class="note">None.</p>'
    has_stages = any(engine_parts(A, name))
    g = [("<b>What each stage does, and why.</b> The atlas lists the stages above but holds no plain-language account of them. "
          if has_stages else "<b>How it works.</b> The atlas holds no plain-language account of the mechanism. ")
         + "Proposal: a one-paragraph <code>how</code> line in the component's definition block, which the compiler already reads."]
    g += _other_gaps(A, name)
    return '<ul class="gaps">' + "".join(f"<li>{x}</li>" for x in g) + "</ul>"


def _other_gaps(A, name):
    nid, crossing, *_ = component_parts(A, name)
    tool = A["tools"].get(name) or {}
    res = A["residents"].get(name) or {}
    g = []
    if tool.get("definition") != "present":
        g.append(f"<b>What it takes, makes and refuses.</b> <code>components/{e(name)}</code> has no definition block, "
                 "so the atlas cannot say. Proposal: write the block (the owner's act).")
    if not crossing:
        g.append("<b>Where its inputs come from and who reads its output.</b> No workflow trace crosses it. "
                 "Proposal: a trace drafted from the code that calls it (update mode), for email_lead to approve.")
    if not res.get("since"):
        g.append("<b>Its place in the register.</b> No Residents row. Proposal: the lead adds one.")
    if not system_path(tool):
        g.append("<b>Its review and mini status.</b> No system-path run has filed a record for it yet; "
                 "the next /system-fit, /system-ready or /system-review files one (SI-17 (system runs filed)).")
    return g


def engine_parts(A, name):
    """The chain records the atlas compiles for this component: the stage list the chain-QA registry holds
    (system.chains, matched by repo or key) and any resolved copy a runner component holds (components[].chains)."""
    d = A["d"]["system"]
    own = [c for c in d.get("chains") or [] if c.get("repo") == f"components/{name}" or c.get("key") == name]
    held = [(c["name"], x) for c in d.get("components") or [] if (c.get("chains") or {}).get("list")
            for x in c["chains"]["list"] if x.get("key") == name and c["name"] != name]
    return own, held


def engine_summary(A, name):
    own, held = engine_parts(A, name)
    rows = []
    for c in own:
        cls = " · ".join(f"{v} {e(k)}" for k, v in sorted((c.get("stage_classes") or {}).items(), key=lambda kv: -kv[1]))
        rows.append(f'<div class="zi"><span class="k">stages</span>{len(c.get("stages") or [])}'
                    f'{" (" + cls + ")" if cls else ""}</div>')
    models = sorted({m for _, x in held for m in x.get("models") or []})
    if models:
        rows.append(f'<div class="zi"><span class="k">models</span>{e(", ".join(models))}</div>')
    return "".join(rows)


def engine_block(A, name):
    """Inside the engine: the stage list as the atlas compiles it, top to bottom, in record order."""
    own, held = engine_parts(A, name)
    if not own and not held:
        return (f'<p class="gap">The atlas holds no stage list for {e(name)}, so it cannot show what happens inside. '
                'That needs a chain record for it, or the <code>how</code> line proposed below.</p>')
    out = []
    for c in own:
        lis = "".join(f'<li>{chips([s.get("class")])}<span><b>{e(s.get("label"))}</b> '
                      f'<span class="note">{e(s.get("key"))}</span></span></li>' for s in c.get("stages") or [])
        fx = c.get("fixtures") or {}
        meta = [("Record", c.get("label")), ("Owner", c.get("owner")), ("Code", c.get("repo")),
                ("Pinned at", (c.get("ref") or "")[:9]), ("Judged by", ", ".join(c.get("judges") or [])),
                ("Test fixtures", f'{fx.get("count", 0)}' + (f' in {fx.get("dir")}' if fx.get("dir") else "")),
                ("Re-run", ", ".join(f"{k}: {v}" for k, v in (c.get("cadence") or {}).items()))]
        dl = "".join(f'<dt>{e(k)}</dt><dd>{e(v) if v else "<span class=gap>not in the atlas</span>"}</dd>' for k, v in meta)
        out.append(f'<ol class="stages eng">{lis}</ol><dl class="kv">{dl}</dl>'
                   '<p class="note">Stages in the order the chain record lists them. The record names each stage; '
                   'it does not say what a stage does or why.</p>')
    for comp, x in held:
        out.append(f'<p class="note">A second copy is held by <b>{e(comp)}</b>: {e(x.get("label"))}, '
                   f'{e(x.get("stages"))} stages, pinned at <code>{e((x.get("pin") or "")[:9])}</code>, '
                   f'models {e(", ".join(x.get("models") or []) or "none listed")}.</p>')
    for c in own:
        for comp, x in held:
            n1, n2 = len(c.get("stages") or []), x.get("stages")
            p1, p2 = (c.get("ref") or "")[:9], (x.get("pin") or "")[:9]
            if n1 != n2 or p1 != p2:
                out.append(f'<p class="cckill">The two records disagree: {n1} stages at <code>{e(p1)}</code> '
                           f'here, {e(n2)} at <code>{e(p2)}</code> in {e(comp)}. The atlas does not say which is current.</p>')
    return "".join(out)


def contract(A, name):
    nid, crossing, up, down, _ = component_parts(A, name)
    tool = A["tools"].get(name) or {}

    def zone(n, title, inner, main=False):
        return f'<div class="zone{" main" if main else ""}"><div class="zh">{e(title)}</div>{inner}</div>'

    def lst(rs, cols):
        items = [r for r in rs if r["col"] in cols]
        return "".join(f'<div class="zi"><b>{e(r["label"])}</b>{chips(A["nodes"].get(r["node"], {}).get("types"))}'
                       f'<span class="note">{e(r.get("does") or "")}</span></div>' for r in items)

    none_route = '<p class="gap">No workflow trace crosses it, so the atlas cannot say.</p>'
    feeds = lst(up, {"sources", "warehouses"}) or none_route
    runs = lst(up + down, {"integrations", "runtime", "ai-resources"}) or none_route
    engine = (f'<div class="zi"><b>components/{e(name)}</b>{chips(A["nodes"].get(nid, {}).get("types"))}</div>'
              f'<div class="zi"><span class="k">makes</span>{e(tool.get("makes") or "—")}</div>'
              f'<div class="zi"><span class="k">refuses</span>{e(tool.get("does_not") or "—")}</div>' + engine_summary(A, name))
    out = lst(down, {"views", "people", "components", "warehouses"}) or none_route
    arrow = '<div class="arr" aria-hidden="true">→</div>'
    return (f'<div class="flowrow">{zone(1, "Original feeds", feeds)}{arrow}{zone(2, "Keys and machines", runs)}{arrow}'
            f'{zone(3, "Engine", engine, True)}{arrow}{zone(4, "Published · read by", out)}</div>')


STATE_ORDER = ["conflicts", "draft-error", "stale", "stated", "agrees"]
STATE_WORD = {"conflicts": "conflicts", "draft-error": "draft errors", "stale": "stale", "stated": "stated, not checkable", "agrees": "agree with the code"}
STATE_CLS = {"conflicts": "crit", "draft-error": "crit", "stale": "warn", "stated": "idle", "agrees": "ok"}


def signal(A, name):
    """The summary signal (ruled 2026-09-30): says a component has conflicts or stale claims without the detail."""
    r = A["checks"].get(name)
    if not r:
        return '<span class="pill p-idle">no flow yet</span>'
    c = r["counts"]
    bad = [(k, c[k]) for k in ("conflicts", "draft-error", "stale") if c.get(k)]
    if r["sources_moved"]:
        bad.append(("stale", None))
    rev = (r["review"] or {}).get("state") or "draft"
    revs = f'<span class="pill p-{"ok" if rev == "approved" else "idle"}">{"approved by " + e(r["review"].get("by")) if rev == "approved" else "draft · not yet reviewed"}</span>'
    if not bad:
        return f'<a class="pill p-ok" href="#checks-{e(name)}">claims agree</a>{revs}'
    parts = " · ".join(f"{n} {STATE_WORD[k]}" if n else "sources moved" for k, n in bad)
    worst = "crit" if any(k in ("conflicts", "draft-error") for k, _ in bad) else "warn"
    return f'<a class="pill p-{worst}" href="#checks-{e(name)}">{e(parts)}</a>{revs}'


def node_states(A, name):
    worst = {}
    for c in (A["checks"].get(name) or {}).get("claims", []):
        k = c["id"]
        if k and (k not in worst or STATE_ORDER.index(c["state"]) < STATE_ORDER.index(worst[k])):
            worst[k] = c["state"]
    return {k: v for k, v in worst.items() if v in ("conflicts", "draft-error", "stale")}


HOME_WORD = {"supabase": "database", "repo": "repo", "drive": "Drive", "dashboard": "dashboard host", "mini": "the mini",
             "session": "a session", "browser": "the browser", "external": "outside"}


def split_label(it):
    """A box shows a short name; the sentence goes underneath. `name` wins when the flow declares one."""
    lab = str(it.get("label") or "")
    if it.get("name"):
        return it["name"], lab
    for sep in (": ", " — ", " - ", " (", ", "):
        if sep in lab and 3 <= len(lab.split(sep, 1)[0]) <= 48:
            a, b = lab.split(sep, 1)
            return a, (("(" + b) if sep == " (" else b)
    return (lab, "") if len(lab) <= 48 else (" ".join(lab.split()[:6]) + " …", lab)


def fcard(it, states, extra=""):
    name, detail = split_label(it)
    st = states.get(it.get("id")) or ""
    cls = " prop" if it.get("proposed") else ""
    cls += {"conflicts": " bad", "draft-error": " bad", "stale": " stale"}.get(st, "")
    tags = ""
    if it.get("proposed"):
        tags += f'<span class="ftag prop">proposed{(" · " + e(it.get("card"))) if it.get("card") else ""}</span>'
    if it.get("legacy"):
        tags += '<span class="ftag">legacy path</span>'
    if st in ("conflicts", "draft-error", "stale"):
        tags += f'<span class="ftag {"bad" if st != "stale" else "stale"}">{e(st)}</span>'
    home = f'<span class="fhome">{e(HOME_WORD.get(it.get("home"), it.get("home") or ""))}</span>' if it.get("home") else ""
    wb = it.get("writes_back")
    wb = (f'<div class="fwb">↩ writes back ({e(wb.get("who"))}): {e(", ".join(wb.get("events") or []))}</div>' if isinstance(wb, dict)
          else f'<div class="fwb">↩ writes back: {e(wb)}</div>' if wb else "")
    return (f'<div class="fcard{cls}"><div class="fname">{e(name)}{home}</div>'
            + (f'<div class="fdet">{e(detail)}</div>' if detail else "") + wb + extra
            + (f'<div class="ftags">{tags}</div>' if tags else "") + "</div>")


def fgroups(groups, states):
    out = []
    for g in groups or []:
        items = g.get("items") if "items" in g else [g]
        head = (f'<div class="fgh">{e(g.get("group"))}'
                + (f' <span class="fcap">· {e(g.get("caption"))}</span>' if g.get("caption") else "") + "</div>") if g.get("group") else ""
        if len(items) > 6:
            chips_ = "".join(f'<span class="fchip{" prop" if i.get("proposed") else ""}">{e(split_label(i)[0])}</span>' for i in items)
            out.append(f'<div class="fgroup">{head}<div class="fchips">{chips_}</div>'
                       f'<details class="fmore"><summary>What each of the {len(items)} is</summary>'
                       + "".join(fcard(i, states) for i in items) + "</details></div>")
        else:
            out.append(f'<div class="fgroup">{head}' + "".join(fcard(i, states) for i in items) + "</div>")
    return "".join(out)


def flow_html(F, states):
    """The flow as readable columns: where it starts → what comes in → the engine → what goes out → who reads it.
    Same data and order as the design copy's picture; text wraps, nothing is cut, one arrow per hop."""
    eng = F.get("engine") or {}
    cols = []
    if F.get("feeds"):
        cols.append(("Where the data starts", fgroups([{"items": F["feeds"]}], states)))
    cols.append(("What comes in", fgroups(F.get("sources"), states)))
    ed = []
    if eng.get("runs_on"):
        ed.append(f'<div class="fdet"><b>Runs</b> {e(eng["runs_on"])}</div>')
    for k, word in (("definitions", "Follows"), ("binding", "Per brand")):
        if eng.get(k):
            n, d = split_label(eng[k])
            ed.append(f'<div class="fsub"><div class="fname">{word}: {e(n)}</div>' + (f'<div class="fdet">{e(d)}</div>' if d else "") + "</div>")
    en, ed0 = split_label(eng)
    cols.append(("The engine", f'<div class="fcard eng"><div class="fname">{e(en)}</div>'
                 + (f'<div class="fdet">{e(ed0)}</div>' if ed0 else "") + "".join(ed) + "</div>"))
    cols.append(("What goes out", fgroups([{"items": F.get("outputs") or []}], states)))
    cols.append(("Who reads it", fgroups(F.get("used_by"), states)))
    arrow = '<div class="farr" aria-hidden="true"><span>→</span></div>'
    row = arrow.join(f'<div class="fcol"><div class="fch">{e(t)}</div>{b}</div>' for t, b in cols)
    out = [f'<div class="fflow" style="--n:{len(cols)}">{row}</div>']
    o = F.get("outcomes")
    if o:
        tone = {"workflow": "ok", "sources": "warn", "stop": "idle"}
        ex = "".join(f'<div class="fexit {tone.get(x.get("to"), "idle")}">{fcard({"label": x.get("label")}, {})}</div>' for x in o.get("exits") or [])
        out.append(f'<h3>How a run ends</h3><p class="plainw">{e(o.get("fold") or "")}</p><div class="fexits">{ex}</div>')
    if F.get("who"):
        out.append('<h3>Who owns what</h3><div class="tw"><table><tbody>' + "".join(
            f'<tr><td>{e(a)}</td><td><b>{e(b)}</b></td></tr>' for a, b in F["who"]) + "</tbody></table></div>")
    worth = [*(F.get("notes") or []), *(("Beside it, not produced by it: " + x) for x in (F.get("beside") or []))]
    if worth:
        out.append('<h3>Worth knowing</h3><ul class="plain">' + "".join(f"<li>{e(x)}</li>" for x in worth) + "</ul>")
    return "".join(out)


def _wrap(t, w):
    words, lines, cur = str(t or "").split(), [], ""
    for x in words:
        if cur and len(cur) + 1 + len(x) > w:
            lines.append(cur)
            cur = x
        else:
            cur = (cur + " " + x).strip()
    if cur:
        lines.append(cur)
    return lines


def flow_items(F):
    """Every detail item in a flow, by id: (section, group, item)."""
    out = {}
    for sec in ("feeds", "sources", "outputs", "used_by"):
        for g in F.get(sec) or []:
            for it in (g.get("items") if "items" in g else [g]):
                if it.get("id"):
                    out[it["id"]] = (sec, g.get("group"), it)
    eng = F.get("engine") or {}
    if eng.get("id"):
        out[eng["id"]] = ("engine", None, eng)
    for k in ("definitions", "binding"):
        if eng.get(k, {}).get("id"):
            out[eng[k]["id"]] = ("engine", None, eng[k])
    return out


def flow_block(A, name):
    """A flow without a picture block (not yet on the standard): the readable columns layout."""
    F = A["flows"].get(name)
    if not F:
        return None
    st = node_states(A, name)
    eng = F.get("engine") or {}
    summ = eng.get("summary") or eng.get("plain") or ""
    return (f'<p class="plainw">{e(summ)}</p>' if summ else "") + flow_html(F, st)


def checks_block(A, name):
    r = A["checks"].get(name)
    if not r:
        return ""
    rows = sorted(r["claims"], key=lambda c: STATE_ORDER.index(c["state"]))
    body = "".join(f'<tr><td><span class="pill p-{STATE_CLS[c["state"]]}">{e(c["state"])}</span></td><td>{e(c["label"] or c["id"])}</td>'
                   f'<td>{e(c["claim"])}</td><td class="src">{e(c["fact"])}</td></tr>' for c in rows)
    moved = (f'<p class="cckill">Files this flow restates have changed since it was drafted: {e(", ".join(r["sources_moved"]))}. Re-review.</p>'
             if r["sources_moved"] else "")
    d = r["drafted"]
    return (f'<details class="checks panel" id="checks-{e(name)}"><summary>Checks against the code: '
            + " · ".join(f'{v} {STATE_WORD[k]}' for k, v in sorted(r["counts"].items(), key=lambda kv: STATE_ORDER.index(kv[0])))
            + f'</summary>{moved}<p class="note">Drafted by {e(d.get("by"))} at {e(d.get("at"))} from {e(d.get("read_from"))}. '
            'A failing claim on an item nobody has edited is a draft error, fixed by redrafting. A failing claim on an item a person edited is a conflict, '
            'which becomes a decision on what the component is meant to do.</p>'
            f'<div class="tw"><table><thead><tr><th>State</th><th>Item</th><th>Claim</th><th>What the repo says</th></tr></thead><tbody>{body}</tbody></table></div></details>')


CARD_ID = re.compile(r"^([A-Z]+-[A-Za-z0-9]+)")
DONE = {"merged", "retired"}


def issue_state(A, it):
    """→ (state word, css class, sort rank). A card's state comes from the atlas; a resolved one drops."""
    k = it.get("kind")
    if it.get("resolved") or it.get("merged_into"):
        return "resolved", "ok", 9
    if k == "review-task":
        return "review task, not filed", "warn", 1
    if k == "skill":
        return "the next system review fixes it", "idle", 3
    if not it.get("tie"):
        return "needs a card", "warn", 0
    if k == "deferred":
        return "deferred by a ruling", "idle", 4
    m = CARD_ID.match(it["tie"])
    if k == "card" and m:
        st = A["cards"].get(m.group(1))
        if st is None:
            return "card not in the atlas", "warn", 1
        if st in DONE:
            return f"resolved ({st})", "ok", 9
        return f"open · card {st}", "idle", 3
    if k == "decision":
        st = A["cards"].get(m.group(1)) if m else None
        if st in DONE:
            return f"decided ({st})", "ok", 9
        return ("decision owed" + (f" · card {st}" if st else "")), "warn", 2
    return "open", "idle", 3


def issue_more(it):
    """The review's facts on an issue (SI-18 (review companion), narrowed): how it came about, the next step,
    who decides, how many read it. All optional; absent fields add nothing."""
    o = it.get("origin") or {}
    bits = []
    if o:
        bits.append("came about: " + " · ".join(str(o[k]) for k in ("who", "when", "commit") if o.get(k)))
    if it.get("readers") is not None:
        bits.append(f'{it["readers"]} readers')
    if it.get("decider"):
        bits.append(f'decides: {it["decider"]}')
    out = f'<div class="note">{e(" · ".join(bits))}</div>' if bits else ""
    if it.get("next"):
        out += f'<div class="note"><b>Next:</b> {e(it["next"])}</div>'
    return out

# SCHEMA §5 issue briefs (2026-10-02): eight fields, plus the decider the ATL-27 (P0 P1 issue briefs) sidecar carries
BRIEF_FIELDS = ("why", "impacts", "evidence", "fix", "fix_impact", "if_ignored", "lane", "severity")
SEV_CLS = {"P0": "crit", "P1": "warn"}
BRIEF_CSS = (".brief{margin-top:8px;padding:8px 10px;border-left:3px solid var(--accent);background:var(--panel-2);"
             "border-radius:0 6px 6px 0;display:flex;flex-direction:column;gap:6px;font-size:12.5px;color:var(--ink-2)}"
             ".brief .k{display:block;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}"
             ".brief ul{margin:2px 0 0;padding-left:16px}"
             ".brief code{font-size:11.5px;overflow-wrap:anywhere}"
             ".brief .fchips{margin-top:2px}.brief .fchip{font-size:11.5px;padding:1px 8px}"
             ".brief .fchip i{font-style:normal;color:var(--ink-3)}")


def _has(v):
    return v not in (None, "", [], {})


def with_briefs(F):
    """The flow's issues, each topped up from triage/issue-briefs/<component>.json by issue number where the flow
    issue lacks a brief field (the flow wins where both have it). No sidecar: the flow's own issues, untouched."""
    issues = F.get("issues") or []
    p = BRIEFS / f'{F.get("component", "")}.json'
    if not F.get("component") or not p.is_file():
        return issues
    try:
        side = json.loads(p.read_text())
    except (OSError, ValueError):
        return issues
    by_n = {b.get("n"): b for b in side.get("issues") or [] if isinstance(b, dict)}
    out = []
    for it in issues:
        b = by_n.get(it.get("n"))
        if b:
            it = dict(it)
            for k in BRIEF_FIELDS + ("decider",):
                if not _has(it.get(k)) and _has(b.get(k)):
                    it[k] = b[k]
        out.append(it)
    return out


def brief_pills(it):
    out = ""
    if _has(it.get("lane")):
        out += f' <span class="pill p-acc">lane: {e(it["lane"])}</span>'
    if _has(it.get("severity")):
        out += f' <span class="pill p-{SEV_CLS.get(str(it["severity"]).upper(), "idle")}">{e(it["severity"])}</span>'
    return out


def issue_brief(it):
    """The brief under an issue's headline, in reading order; an absent field shows nothing."""
    parts = []
    if _has(it.get("why")):
        parts.append(f'<div><span class="k">Why it matters</span>{e(it["why"])}</div>')
    imp = it.get("impacts")
    if isinstance(imp, dict):
        ch = "".join(f'<span class="fchip"><i>{lbl}</i> {e(x)}</span>'
                     for key, lbl in (("people", "person"), ("components", "component"), ("machines", "machine"))
                     for x in (imp.get(key) or []))
        if ch:
            parts.append(f'<div><span class="k">Who and what it affects</span><div class="fchips">{ch}</div></div>')
    ev = it.get("evidence")
    if isinstance(ev, str) and ev:
        ev = [ev]
    if ev:
        parts.append('<div><span class="k">What the run saw</span><ul>'
                     + "".join(f"<li><code>{e(x)}</code></li>" for x in ev) + "</ul></div>")
    # keys stay `fix`/`fix_impact`; shown as the response (developer, 2026-10-02: an item "may not just be fixes")
    for k, lbl in (("fix", "Response"), ("fix_impact", "What the response changes"), ("if_ignored", "If it is ignored")):
        if _has(it.get(k)):
            parts.append(f'<div><span class="k">{lbl}</span>{e(it[k])}</div>')
    return f'<div class="brief">{"".join(parts)}</div>' if parts else ""


def issues_block(A, F):
    rows, resolved, merged, by_email_lead = [], 0, [], 0
    for it in with_briefs(F):
        w, cls, rank = issue_state(A, it)
        if rank == 9:
            if it.get("merged_into"):
                merged.append(f'#{it.get("n")} → {it["merged_into"]}')
            else:
                resolved += 1
                by_email_lead += it.get("resolved_by") == "email_lead"   # SCHEMA §5a: email_lead may close with evidence (981094a4a)
            continue
        rows.append((rank, it, w, cls))
    # SCHEMA §5a: most readers first where known, the rest in number order below them
    rows.sort(key=lambda r_: (0, -r_[1]["readers"], r_[1].get("n") or 0) if isinstance(r_[1].get("readers"), int)
              else (1, 0, r_[1].get("n") or 0))
    comp = F.get("component", "")
    body = "".join(f'<tr id="issue-{e(it.get("n", ""))}"><td class="inum">{e(comp)} #{e(it.get("n", "?"))}</td>'
                   f'<td><b>{e(it["text"])}</b><div class="note">{e(it.get("affects", ""))}</div>{issue_more(it)}{issue_brief(it)}</td>'
                   f'<td>{e(it.get("tie") or "—")}</td><td><span class="pill p-{cls}">{e(w)}</span>{brief_pills(it)}</td><td>{e(it.get("owner", ""))}</td></tr>'
                   for _, it, w, cls in rows)
    if any(issue_brief(it) or brief_pills(it) for _, it, _w, _c in rows):
        A["brief_css"] = True
    need = sum(1 for r_ in rows if r_[0] == 0)
    unfiled = sum(1 for r_ in rows if r_[1].get("kind") == "review-task")
    lede = (f'<p class="note">{len(rows)} open{f", {need} with no card yet" if need else ""}'
            f'{f", {unfiled} a review task not yet filed" if unfiled else ""}'
            f'{f"; {resolved} resolved and hidden" if resolved else ""}'
            f'{f" ({by_email_lead} closed by email_lead)" if by_email_lead else ""}'
            f'{"; merged into one issue: " + ", ".join(merged) if merged else ""}. A row closes when its card merges, its decision is ruled, or email_lead closes it with its evidence; '
            'a row with no card stays amber until someone cards it. Numbers are fixed per component and never reused.</p>')
    return lede + ('<div class="tw"><table class="issues"><thead><tr><th>#</th><th>Issue</th><th>Tied to</th><th>State</th><th>Owner</th></tr></thead>'
                   f'<tbody>{body}</tbody></table></div>' if rows else '<p class="note">Nothing open.</p>')


def howto_block(F):
    H = F.get("howto") or {}
    if H.get("parts"):
        where = "copied into the README" if H.get("in_readme") else "not yet in the component's README (components rule 10)"
        dl = "".join(f"<dt>{e(a)}</dt><dd>{e(b)}</dd>" for a, b in H["parts"])
        return (f'<dl class="kv howto">{dl}</dl><p class="note">Generated {e(H.get("generated", ""))} from the code, '
                f'{where}. Source <code>{e(H.get("source", ""))}</code>.</p>')
    out = ""
    if H.get("skill"):
        k = H["skill"]
        out += (f'<dl class="kv howto"><dt>Ask for it</dt><dd>{e(k["text"])}</dd></dl>'
                f'<p class="note">From the {e(k["name"])} skill, <code>{e(k["cite"])}</code>.</p>')
    out += ('<p class="gap">No generated "How to use it" exists for this component. It comes from the system path '
            '(/system-ready or /system-review reads the code and writes the six parts); until then this is an open issue.</p>')
    return out


def standard_page(A, name):
    """One component to the component page standard (COMPONENT-PAGE-STANDARD.md, ruled 2026-09-30):
    header · open issues · how it works · how to use it · who owns it · core table · refusals · the atlas · reference."""
    F = A["flows"][name]
    nid, crossing, *_ = component_parts(A, name)
    tool = A["tools"].get(name) or {}
    res = A["residents"].get(name) or {}
    st = node_states(A, name)
    node = A["nodes"].get(nid, {})
    fx = F.get("facts") or {}
    wf = ", ".join(f'{t.get("label") or t["id"]} (trace stage: {t.get("stage")})' for t in crossing)
    rows = [("Since", res.get("since")), ("Owner", tool.get("owner") or res.get("owner")), ("Run", fx.get("Run") or tool.get("command")),
            ("Emits", fx.get("Emits"))] + [(k, v) for k, v in fx.items() if k not in ("Run", "Emits")] + [
            ("Workflows through it", f"{len(crossing)}" + (f" — {wf}" if wf else ""))]
    dl = "".join(f'<dt>{e(k)}</dt><dd>{e(v) if v else "<span class=gap>not in the atlas</span>"}</dd>' for k, v in rows)
    head = dict(eyebrow="Upright Atlas · " + ("lab work" if str(F.get("target", "")).startswith("lab/") else "a component"), name=name, title=name,
                pills=[f'stage: {F.get("stage") or "not set"}', f'{name}: {node.get("status") or "status unstated"}' if node else (F.get("target") or ""), F.get("character") or ""],
                signal=signal(A, name), lede="")
    eng = F.get("engine") or {}
    sha = (F.get("drafted") or {}).get("read_from", "")
    cap = (f'Solid runs at HEAD, drafted from the code at {e(sha)} and checked on every render; amber dashed is planned, or approved and still '
           'waiting on a fact; grey dotted is deferred, legacy, or beside; an amber outline runs today but is worth a look. '
           'Every box stands for items listed in full under Reference detail.')
    how = (f'<p class="plainw">{e(eng.get("summary") or eng.get("plain") or "")}</p>'
           f'<figure class="pf"><div class="scroll">{picture.svg(F, st)}</div>{picture.LEGEND}<figcaption>{cap}</figcaption>'
           f'{picture.bands(F, ("writes", "outcome", "never"))}</figure>')
    body = [sec("1 · Open issues", "What is not right yet, and who owes the next move", issues_block(A, F)),
            sec("2 · How it works", "What goes in, what runs it, what comes out", how),
            sec("3 · How to use it", "Asking for it, what you need, what you get", howto_block(F)),
            sec("4 · Who owns it", "Who owns what, and the rules that do the work", picture.bands(F, ("owners", "rules")))]
    n = 5
    T = F.get("table")
    if T:
        trs = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r_) + "</tr>" for r_ in T["rows"])
        body.append(sec(f"{n} · The core", T["title"], (f'<p class="note">{e(T.get("lede"))}</p>' if T.get("lede") else "")
                        + f'<div class="tw"><table><thead><tr>{"".join(f"<th>{e(c)}</th>" for c in T["columns"])}</tr></thead><tbody>{trs}</tbody></table></div>'))
        n += 1
    if F.get("refuses"):
        stc = {c["id"]: c["state"] for c in A["checks"][name]["claims"] if c["field"] == "code"}
        body.append(sec(f"{n} · Refusals", "What it refuses, by name", '<div class="tw"><table><thead><tr><th>Refuses</th><th>Meaning</th><th>In the code</th></tr></thead><tbody>' + "".join(
            f'<tr><td><code>{e(r_.get("code") or r_.get("label") or "—")}</code></td><td>{e(r_.get("means"))}</td><td>'
            + ('<span class="pill p-warn">planned</span>' if r_.get("proposed") else f'<span class="pill p-{STATE_CLS.get(stc.get(r_.get("code")), "idle")}">{e(stc.get(r_.get("code"), "stated"))}</span>')
            + "</td></tr>" for r_ in F["refuses"]) + "</tbody></table></div>"))
        n += 1
    fs = drift_for(A, {name, nid, f"components/{name}"})
    body.append(sec(f"{n} · The atlas", "What the atlas flags", drift_block(fs, name)))
    n += 1
    items = flow_items(F)
    claims_by = {}
    for c_ in A["checks"][name]["claims"]:
        claims_by.setdefault(c_["id"], []).append(c_)
    ref = []
    for col in picture.ORDER:
        boxes = [(g, it) for g in F["picture"]["groups"] if g["col"] == col for it in g["items"]]
        if not boxes:
            continue
        rows_ = ""
        for g, it in boxes:
            its = [items[k][2] for k in it.get("covers") or [] if k in items]
            stt = it.get("state") or g.get("state") or ""
            chips_ = ""
            if stt:
                chips_ += f'<span class="pill p-{"warn" if stt in ("proposed", "flag", "binding") else "idle"}">{e({"proposed": "planned", "flag": "worth a look", "legacy": "legacy", "binding": "per brand"}.get(stt, stt))}</span>'
            if it.get("manual"):
                chips_ += '<span class="pill p-idle">✍ by hand</span>'
            bad = [c_ for x in its for c_ in claims_by.get(x.get("id"), []) if c_["state"] in ("conflicts", "draft-error", "stale")]
            if bad:
                chips_ += f'<span class="pill p-crit">{len(bad)} to look at</span>'
            home = picture.HOME.get(g.get("home"), ("", ""))
            body_ = ""
            for x in its:
                nm, _det = split_label(x)
                full = x.get("label") or ""
                meta = []
                if x.get("path"):
                    meta.append(("Where", f'<code>{e(x["path"])}</code>'))
                if x.get("home"):
                    meta.append(("Lives", e(HOME_WORD.get(x["home"], x["home"]))))
                if x.get("runs_on"):
                    meta.append(("Runs", e(x["runs_on"])))
                if x.get("card"):
                    meta.append(("Card", e(x["card"])))
                if x.get("note"):
                    meta.append(("Note", e(x["note"])))
                if x.get("cite"):
                    meta.append(("Restates", f'<code>{e(x["cite"])}</code>'))
                cl = claims_by.get(x.get("id"), [])
                if cl:
                    meta.append(("Checked", "<br>".join(f'<span class="pill p-{STATE_CLS.get(c_["state"], "idle")}">{e(c_["state"])}</span> {e(c_["claim"])}: {e(c_["fact"])}' for c_ in cl)))
                dt = x.get("detail")
                dtab = ""
                if dt:
                    th = "".join(f"<th>{e(c_)}</th>" for c_ in dt.get("columns") or []) if any(dt.get("columns") or []) else ""
                    trs = "".join("<tr>" + "".join(f"<td>{e(v)}</td>" for v in r_) + "</tr>" for r_ in dt.get("rows") or [])
                    dtab = (f'<div class="ri-dt"><div class="ri-dth">{e(dt.get("title"))} <span class="note">· from <code>{e(dt.get("cite"))}</code></span></div>'
                            f'<div class="tw"><table class="dt">{("<thead><tr>" + th + "</tr></thead>") if th else ""}<tbody>{trs}</tbody></table></div></div>')
                body_ += (f'<div class="refitem"><div class="ri-head"><b>{e(nm)}</b></div>'
                          + (f'<p class="ri-full">{e(full)}</p>' if full and full != nm else "")
                          + ('<dl class="ri-meta">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in meta) + "</dl>" if meta else "")
                          + dtab + "</div>")
            rows_ += (f'<details class="refrow"><summary><span class="rr-name">{e(it["name"])}</span><span class="rr-sub">{e(it.get("sub", ""))}</span>'
                      f'<span class="rr-meta">{e((home[0] + " " + home[1]).strip())}</span><span class="rr-meta">{len(its)} item{"s" if len(its) != 1 else ""}</span>'
                      f'<span class="rr-chips">{chips_}</span></summary><div class="rr-body">{body_}</div></details>')
        ref.append(f'<div class="refblock"><div class="refh">{e(picture.COLUMNS[col])}</div>{rows_}</div>')
    more = '<details class="ref"><summary><b>What the atlas does not know yet</b></summary>' + gaps(A, name) + "</details>"
    body.append(sec(f"{n} · Reference", "Reference detail", '<p class="note">Every box in the picture, row by row. Open a row for each item it stands for: where it lives, what it restates, how it was checked, and its full list where it has one.</p>'
                    + "".join(ref) + f'<div class="refmore">{more}</div>' + checks_block(A, name)))
    return head, body, dl


def component_page(A, names):
    body, drifts, all_by_col, hl = [], [], {}, set()
    for name in names:
        nid, crossing, up, down, by_col = component_parts(A, name)
        hl.add(nid)
        for c, ids in by_col.items():
            all_by_col.setdefault(c, [])
            all_by_col[c] += [i for i in ids if i not in all_by_col[c]]
        drifts.append((name, drift_for(A, {name, nid, f"components/{name}"})))
    single = len(names) == 1
    n0 = A["nodes"].get(f"component:{names[0]}", {})
    head = dict(
        signal="".join((f'<span class="signame">{e(n)}</span>' if not single else "") + signal(A, n) for n in names),
        eyebrow="Upright Atlas · " + ("a component" if single else f"{len(names)} components"),
        name=names[0] if single else " and ".join(names),
        title=names[0] if single else " and ".join(names),
        pills=sum(([f'{n}: {A["nodes"].get("component:" + n, {}).get("status") or "status unstated"}',
                    f'{len(component_parts(A, n)[1])} traces cross {n}'] for n in names), []),
        lede=(n0.get("note") or "") if single else
        "Two components side by side, as the atlas records them. The atlas records components, traces and drift; it does not record what each check tests, so overlap between them is not visible here.")
    body.append(sec("1 · The chain", "Where it sits among the org's resources",
                    legend(A) + chain_strip(A, all_by_col, hl) +
                    ('<p class="note">Nodes from every workflow that crosses the subject.</p>'
                     if any(component_parts(A, n)[1] for n in names) else
                     '<p class="cckill">No workflow trace crosses this subject. On the atlas it stands alone '
                     '(an orphan node), so the chain shows only the component itself.</p>')))
    for i, name in enumerate(names):
        nid, crossing, *_ = component_parts(A, name)
        tr = "".join(f'<li><b>{e(t.get("label") or t["id"])}</b> <span class="note">({e(t.get("stage"))})</span>: '
                     f'{e(next((r.get("does") for r in t["resolved"] if r["node"] == nid), "") or "no per-step description at this node")}</li>'
                     for t in crossing) or '<li class="note">None.</li>'
        body.append(sec(f"{i + 2} · {name}", f"{name}, as the atlas records it",
                        facts(A, name) + "<h3>How it works</h3>"
                        + (flow_block(A, name) or (contract(A, name) + "<h3>Inside the engine</h3>" + engine_block(A, name)))
                        + checks_block(A, name)
                        + f'<h3>Workflows that cross it</h3><ul class="plain">{tr}</ul>'
                        + "<h3>What the atlas does not know yet</h3>" + gaps(A, name)))
    k = len(names) + 2
    body.append(sec(f"{k} · Drift", "What the atlas flags",
                    "".join((f"<h3>{e(n)}</h3>" if not single else "") + drift_block(fs, n) for n, fs in drifts)))
    if not single:
        shared = set.intersection(*[{t["id"] for t in component_parts(A, n)[1]} for n in names])
        classes = [set(f["key"] for f in fs) for _, fs in drifts]
        both = set.intersection(*classes) if classes else set()
        cls_names = sorted({f["cls"] for _, fs in drifts for f in fs if f["key"] in both})
        body.append(sec(f"{k + 1} · In common", "What the atlas says they share",
                        f'<ul class="plain"><li>Shared workflow traces: {e(", ".join(sorted(shared)) or "none")}</li>'
                        f'<li>Drift kinds raised on every one: {e(", ".join(cls_names) or "none")}</li></ul>'))
    return head, body


# ---------------------------------------------------------------- page
def sec(eyebrow, h2, inner):
    return f'<section><span class="eyebrow">{e(eyebrow)}</span><h2>{e(h2)}</h2>{inner}</section>'


CSS = (Path(__file__).with_name("atlas-view.css")).read_text()
FLOWJS_TAG = ("<script>" + (Path(__file__).with_name("flow.js")).read_text() +
              "\ndocument.querySelectorAll('.flowpic').forEach(function(h){var n=h.getAttribute('data-flow');"
              "h.innerHTML=window.avFlowSvg(n);window.avMark(h,(window.AV_STATES||{})[n]);});</script>")


def page(A, head, body, subject):
    pills = "".join(f'<span class="pill p-idle">{e(p)}</span>' for p in head["pills"] if p)
    stamp = A["stamp"] or "unknown"
    return f"""<title>{e(head.get("name") or head["title"])} on the Atlas</title>
<style>{CSS}{BRIEF_CSS if A.get("brief_css") else ""}</style>
<div class="wrap">
<header class="lede">
  <span class="eyebrow">{e(head["eyebrow"])}</span>
  <h1>{e(head["title"])}</h1>
  <div class="status">{pills}</div>
  {('<div class="signal">' + head["signal"] + '</div>') if head.get("signal") else ""}
  {('<p>' + e(head["lede"]) + '</p>') if head.get("lede") else ""}
  {('<dl class="kv">' + head["facts"] + '</dl>') if head.get("facts") else ""}
  <p class="note">Rendered by <code>/atlas-view {e(subject)}</code> from <code>platform/data/atlas/data.json</code>, compiled {e(stamp)}. Every fact on this page is from that file; where the atlas does not know something, the page says so.</p>
</header>
{"".join(body)}
</div>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--out")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--flows", default="", help="a local folder of flow files that overrides the compiled ones per component (the atlas lane, WM-115 (atlas view handler), passes none and draws the compiled flows)")
    a = ap.parse_args()
    A = load(a.data)
    if a.flows:
        attach_flows(A, a.flows)
    try:
        kinds = resolve(A, a.subject)
    except Refused as x:
        print(f"REFUSED: {x}", file=sys.stderr)
        sys.exit(2)
    dl = ""
    if kinds[0][0] == "trace":
        head, body = trace_page(A, kinds[0][1])
    elif len(kinds) == 1 and "picture" in (A["flows"].get(kinds[0][1]) or {}):
        head, body, dl = standard_page(A, kinds[0][1])
    else:
        head, body = component_page(A, [n for _, n in kinds])
    head["facts"] = dl
    out = Path(a.out or f"atlas-view-{a.subject.replace('+', '-and-').replace(':', '-')}.html")
    out.write_text(page(A, head, body, a.subject))
    print(out)


if __name__ == "__main__":
    main()
