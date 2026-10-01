#!/usr/bin/env python3
"""
board.py — the surface where an ad gets built, per brief.

    python3 board.py <run folder>        # then open http://127.0.0.1:8456

One page. The cast at the top — the four banked elements that stop the drift —
then one card per talking beat: the line she says, how she says it, the
gesture and where the hand goes afterwards, the duration, and THE PROMPT THAT
WILL BE SENT, verbatim. Edit any field and it saves to the brief's own
cinema/plan.json. The clip appears in the card the moment it lands.

HOW A TAKE GETS MADE (2026-09-18). Pressing Generate writes a work order to
cinema/queue.json — as it always did — and now starts `drain.py` on it in
the background: the frame on GPT Image (direct), the line on the
character's cloned ElevenLabs voice, the talking beat on fal Omni through
the controlled recipe (line performed, voice swapped to hers, parity
checked twice), a cutaway on the same door with the sound stripped. No
Higgsfield, no session at a keyboard. Before 2026-09-18 a Claude session
drained the queue through the Higgsfield MCP; `drain.log` beside the queue
is the record of each run now. The board never claims a take exists that
does not.

The prompt is the product, so the prompt is on screen. That is the whole
reason this page exists rather than a folder of files.
"""

from __future__ import annotations

def _drive_root():
    """The Google Drive mount holding Shared Assets.

    Set DRIVE_ACCOUNT to the Google account the drive is mounted under.
    Unset, the first GoogleDrive-* mount found is used.
    """
    import os
    cs = Path.home() / "Library/CloudStorage"
    acct = os.environ.get("DRIVE_ACCOUNT")
    if acct:
        return cs / f"GoogleDrive-{acct}"
    return next(iter(sorted(cs.glob("GoogleDrive-*"))), cs / "GoogleDrive")


import html
import json
import os
import mimetypes
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as CH
import prompt as PROMPT                                            # noqa: E402
import drain as DRAIN                                              # noqa: E402

PORT = int(os.environ.get("BOARD_PORT", 8456))   # a second run wants a second board
RUN: Path = Path()

EDITABLE = {"line", "delivery", "gesture", "name", "change"}
EDITABLE_CUT = {"place", "subject", "action", "look", "why", "change"}


# ----------------------------------------------------------------- state
def plan_path() -> Path:
    return RUN / "out" / "plan.json"


def load() -> dict:
    return json.loads(plan_path().read_text())


def save(d: dict) -> None:
    plan_path().write_text(json.dumps(d, indent=1))


def queue_path() -> Path:
    return RUN / "cinema" / "queue.json"


def queue_read() -> list:
    p = queue_path()
    return json.loads(p.read_text()) if p.exists() else []


def queue_add(action: str, ids: list[str]) -> list:
    q = queue_read()
    q.append({"action": action, "ids": ids, "state": "open",
              "asked": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    queue_path().write_text(json.dumps(q, indent=1))
    if not os.environ.get("BOARD_NO_DRAIN"):
        DRAIN.run_in_background(RUN)        # the direct doors do the work
    return q


# What the board calls a take, and where that take actually sits.
#
# finals/ holds what ships and iterations/ holds the working versions, so the
# card's vocabulary ("raw", "voiced") is mapped here once rather than every
# caller knowing the folder layout.
WHERE = {
    "raw":    ("iterations", "raw"),
    "voiced": ("rushes", "clips"),
    "clips":  ("rushes", "clips"),
    "broll":  ("rushes", "broll"),
    "offer":  ("rushes", "offer"),
    "openings": ("rushes", "openings"),
}


def clip_file(sid: str, kind: str) -> Path:
    parent, sub = WHERE.get(kind, ("finals", kind))
    return RUN / parent / sub / f"{sid}.mp4"


# ----------------------------------------------------------------- render
def e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def status_of(s: dict) -> tuple[str, str]:
    """(label, css class) — what this beat actually has on disk right now."""
    if clip_file(s["id"], "voiced").exists():
        return "revoiced", "ok"
    if clip_file(s["id"], "raw").exists():
        return "generated, not revoiced", "part"
    g = (s.get("generate") or {}).get("status")
    if g in ("pending", "queued", "in_progress"):
        return f"{g} — generating", "wait"
    if g == "failed":
        return "failed", "bad"
    return "nothing yet", "none"


def cast_html(d: dict) -> str:
    rows = []
    for el in (d["cast"].get("elements", []) + d["cast"].get("also", [])):
        thumb = (f'<img src="{e(el["thumb"])}" alt="{e(el["name"])}">'
                 if el.get("thumb") else '<div class="novis">voice</div>')
        rows.append(f"""
        <div class="el">
          <div class="elpic">{thumb}</div>
          <div class="elbody">
            <span class="slot">{e(el["slot"])}</span>
            <div class="elname">{e(el["name"])}</div>
            <div class="elrole">{e(el["role"])}</div>
            <div class="eldesc">{e(el["desc"])}</div>
            <code class="elid">{e(el["id"])}</code>
          </div>
        </div>""")
    alts = d["cast"].get("alternates", {}).get("room", [])
    altrow = ""
    if alts:
        chips = " ".join(
            f'<span class="chip"><b>{e(a["name"])}</b> {e(a["for"])}</span>'
            for a in alts)
        altrow = (f'<div class="alts"><span class="slot">other positions on '
                  f'the standing set</span><div>{chips}</div></div>')
    return f'<div class="cast">{"".join(rows)}</div>{altrow}'



def change_box(row: dict, kind: str) -> str:
    """What is wrong with the take that is on the card right now.

    Damon writes it here, in his words, and presses Regenerate. The note is
    kept against the take it rejects, so the card carries its own history of
    what was wrong and what was done about it — instead of that history living
    in a chat that gets archived.
    """
    vs = row.get("versions") or []
    hist = ""
    if vs:
        rows = "".join(
            f'<li><span class="vn">v{v["v"]}</span> '
            f'<a href="/version/{e(Path(v["file"]).name)}" target="_blank">take</a>'
            f'<span class="vr">{e(v.get("rejected_because"))}</span></li>'
            for v in vs)
        hist = f'<details class="hist"><summary>{len(vs)} earlier take' \
               f'{"s" if len(vs) != 1 else ""} and why each was replaced' \
               f'</summary><ul>{rows}</ul></details>'
    return f"""
      <span class="slot">what needs changing &mdash; plain words</span>
      <textarea class="fx" data-id="{e(row['id'])}" data-kind="{kind}"
        data-k="change" rows="2"
        placeholder="e.g. the FLEX is standing up, it has a rounded bottom">{e(row.get('change'))}</textarea>
      <div class="acts">
        <button class="go regen" data-id="{e(row['id'])}" data-kind="{kind}">Regenerate with this note</button>
      </div>
      {hist}"""


def scene_html(s: dict, d: dict) -> str:
    label, cls = status_of(s)
    try:
        prompt = PROMPT.payload(s, d["cast"])["prompt"]
        perr = ""
    except SystemExit as ex:
        prompt, perr = "", str(ex)
    g = s.get("generate") or {}
    v = s.get("revoice") or {}
    vids = ""
    for kind, cap in (("raw", "generated · its own voice"),
                      ("voiced", "her voice · Omni recipe, parity checked")):
        if clip_file(s["id"], kind).exists():
            vids += (f'<figure><video src="/clip/{e(s["id"])}/{kind}" controls '
                     f'preload="metadata" playsinline></video>'
                     f'<figcaption>{cap}</figcaption></figure>')
    if not vids:
        vids = '<div class="empty">no take on disk</div>'
    warn = (f'<p class="warn">{e(perr)}</p>' if perr else "")
    return f"""
    <article class="scene" id="s-{e(s['id'])}">
      <header>
        <div class="sid">{e(s['id'])}</div>
        <input class="f" data-id="{e(s['id'])}" data-k="name"
               value="{e(s.get('name'))}" aria-label="beat name">
        <label class="secs">{e(s['seconds'])}s</label>
        <span class="st {cls}">{e(label)}</span>
      </header>
      {warn}
      <div class="grid">
        <div class="col">
          <span class="slot">the line she says</span>
          <textarea class="f line" data-id="{e(s['id'])}" data-k="line"
            rows="4">{e(s.get('line'))}</textarea>
          <span class="slot">how she says it</span>
          <input class="f" data-id="{e(s['id'])}" data-k="delivery"
                 value="{e(s.get('delivery'))}">
          <span class="slot">the gesture — and where the hand goes after</span>
          <textarea class="f" data-id="{e(s['id'])}" data-k="gesture"
            rows="3">{e(s.get('gesture'))}</textarea>
          {change_box(s, "scene")}
          <div class="acts">
            <button class="go alt" data-act="generate" data-id="{e(s['id'])}">Generate</button>
            <button class="go alt" data-act="revoice" data-id="{e(s['id'])}">Revoice</button>
          </div>
          <div class="ids">
            <span>model <b>{e(g.get('model') or '—')}</b></span>
            <span>generate <code>{e((g.get('job_id') or '—')[:8])}</code></span>
            <span>revoice <code>{e((v.get('job_id') or '—')[:8] if v.get('job_id') else '—')}</code></span>
          </div>
        </div>
        <div class="col">
          <details class="pr"><summary>the prompt that gets sent, verbatim</summary>
          <pre class="prompt">{e(prompt)}</pre></details>
          {vids}
        </div>
      </div>
    </article>"""



def cut_html(c: dict) -> str:
    """One cutaway card. A cutaway is silent and sits ON a take, so the card
    leads with which take it covers and at what second."""
    f = RUN / "rushes" / "broll" / f"{c['id']}.mp4"
    still = RUN / "rushes" / "broll" / f"{c['id']}.png"
    g = c.get("generate") or {}
    if not f.exists() and still.exists():
        # A frame is not a clip, and the card says so rather than implying the
        # scene is done. Added 2026-09-14: nineteen stills existed and the board
        # read EMPTY, because it only ever looked for .mp4.
        vid = (f'<figure><img src="/still/{e(c["id"])}" alt="scene {e(c["id"])}" '
               f'style="width:100%;border-radius:6px;display:block">'
               f'<figcaption>still &middot; not yet a clip &middot; '
               f'{e(c["seconds"])}s</figcaption></figure>')
        label, cls = "still", "warn"
    elif f.exists():
        vid = (f'<figure><video src="/clip/{e(c["id"])}/broll" controls '
               f'preload="metadata" playsinline muted></video>'
               f'<figcaption>silent by design &middot; '
               f'{e(g.get("seconds_out") or c["seconds"])}s</figcaption></figure>')
        label, cls = "generated", "ok"
    else:
        vid = '<div class="empty">no take on disk</div>'
        st = g.get("status")
        label, cls = ((f"{st} — generating", "wait") if st in
                      ("pending", "queued", "in_progress")
                      else ("failed", "bad") if st == "failed"
                      else ("nothing yet", "none"))
    checks = g.get("checks") or []
    bad = [x for x in checks if x != "ok"]
    warn = f'<p class="warn">{e(" · ".join(bad))}</p>' if bad else ""
    prompt = PROMPT.broll(c)["prompt"]
    fields = ""
    for k, lab in (("place", "where it is"), ("subject", "what is in frame"),
                   ("action", "the one action, start to finish"),
                   ("look", "how close, how shallow, how lit")):
        fields += (f'<span class="slot">{lab}</span>'
                   f'<textarea class="fc" data-id="{e(c["id"])}" data-k="{k}" '
                   f'rows="3">{e(c.get(k))}</textarea>')
    return f"""
    <article class="scene cut" id="c-{e(c['id'])}">
      <header>
        <div class="sid">{e(c['id'])}</div>
        <span class="over">over <b>{e(c['over'])}</b> at {e(c['at'])}s
          &middot; {e(c['seconds'])}s</span>
        <span class="why">{e(c.get('why'))}</span>
        <span class="st {cls}">{e(label)}</span>
      </header>
      {warn}
      <div class="grid">
        <div class="col">{fields}
          {change_box(c, "cut")}
          <div class="acts">
            <button class="go alt" data-act="broll" data-id="{e(c['id'])}">Generate</button>
          </div>
          <div class="ids">
            <span>model <b>{e(g.get('model') or '—')}</b></span>
            <span>job <code>{e((g.get('job_id') or '—')[:8])}</code></span>
            <span>audio <b>off</b></span>
          </div>
        </div>
        <div class="col">
          <details class="pr"><summary>the prompt that gets sent, verbatim</summary>
          <pre class="prompt">{e(prompt)}</pre></details>
          {vid}
        </div>
      </div>
    </article>"""



def chain_html(d: dict) -> str:
    """The chain, gated on the brief.

    First thing on the page, because the question this board exists to answer
    is not "what have we made" but "what did the brief ask for and what is
    still missing". Those are different questions and only the second one
    catches six openings going out the door unmade.
    """
    try:
        rows = CH.read(RUN)
    except Exception as ex:
        return f'<div class="warn">chain unreadable: {e(ex)}</div>'
    JUMP = {"cast": "#cast", "openings": "#openings", "aroll": "#beats",
            "broll": "#cuts", "offer": "#offer", "captions": "#captions",
            "cut": "#thecut"}
    out = []
    for r in rows:
        n = (f'{r["brief"]}' if r["agreed"] == r["brief"]
             else f'{r["brief"]}&rarr;{r["agreed"]}')
        short = {"done": "done", "gap": "gap", "override": "agreed"}[r["state"]]
        det = f'<span class="cd">{e(r["detail"])}</span>' if r.get("detail") else ""
        href = "#prompts" if r.get("prompt") else JUMP.get(r["key"])
        name = (f'<a href="{href}">{e(r["name"])}</a>' if href
                else e(r["name"]))
        out.append(f"""
        <tr class="cr {r['state']}">
          <td class="cn">{name}</td>
          <td class="cw">{e(r["why"])}</td>
          <td class="cnum">{n}</td>
          <td class="cnum">{r["built"]}</td>
          <td class="cs"><span class="dot"></span>{short}</td>
        </tr>
        <tr class="cdet {r['state']}"><td></td><td colspan="4">{det}</td></tr>""")
    gaps = [r for r in rows if r["state"] == "gap"]
    head = (f'{len(gaps)} gap{"s" if len(gaps) != 1 else ""} against the brief'
            if gaps else "every stage meets the brief")
    ho = CH.handoff(RUN)
    owns = "".join(f"<li>{e(x)}</li>" for x in ho["owns"])
    ready = ("ready to hand over" if ho["ready"]
             else "not ready &mdash; " + e(", ".join(ho["gaps"])))
    hand = f"""
      <div class="hand">
        <div class="hl"><span class="arrow">&rarr;</span>
          <b>then the editor</b><span class="hs">{ready}</span></div>
        <ul class="ho">{owns}</ul>
        <p class="hc">{e(ho["control"])}</p>
      </div>"""
    return f"""
    <div class="chain">
      <div class="chead"><b>Brief &rarr; assets</b>
        <span>{head}</span>
        <span class="cend">this chain ends at the offer cards</span></div>
      <table class="ctab">
        <thead><tr><th>stage</th><th>what it is for</th>
        <th>brief</th><th>built</th><th></th></tr></thead>
        <tbody>{"".join(out)}</tbody>
      </table>
      {hand}
    </div>"""


def prompts_html(d: dict) -> str:
    """Every prompt that drives this chain, verbatim, on the page.

    The prompt is the product. A rule nobody can read is a rule nobody can
    correct, and the whole reason the shapes moved out of prompt.py and into
    ../prompts/ is so a tweak reaches every brief at once instead of being
    edited for one run and forgotten.
    """
    rows = []
    for r in CH.read(RUN):
        rel = r.get("prompt")
        if not rel:
            continue
        f = PROMPT.PROMPTS / rel
        if not f.exists():
            rows.append(f'<div class="pm miss"><b>{e(r["name"])}</b>'
                        f'<span>missing: {e(rel)}</span></div>')
            continue
        body = f.read_text()
        has_shape = "```shape" in body
        tag = ('<span class="ptag good">shape</span>' if has_shape
               else '<span class="ptag">mechanical</span>')
        rows.append(f"""
        <details class="pm">
          <summary><b>{e(r["name"])}</b> {tag}
            <code>{e(rel)}</code>
            <span class="plen">{len(body.splitlines())} lines</span></summary>
          <pre class="pbody">{e(body)}</pre>
        </details>""")
    return f'<div class="pms">{"".join(rows)}</div>'


def final_cut_html(d: dict) -> str:
    """The assembled ad, on the board that built it.

    Everything else here is an ingredient. Without this the board can tell you
    every part is fine and still never show you the thing they add up to,
    which is the only artefact anyone outside this room ever sees.
    """
    f = RUN / "cinema" / "CUT.mp4"
    if not f.exists():
        return ('<div class="cutbar" id="thecut"><div class="cutinfo"><b>No cut yet</b>'
                '<span>every beat needs a revoiced take before the ad can be '
                'assembled</span>'
                '<div class="acts"><button class="go" id="recut">Cut it</button>'
                '</div></div></div>')
    takes = [x for x in d["scenes"]
             if (RUN / "rushes" / "clips" / f"{x['id']}.mp4").exists()]
    cuts = [x for x in d.get("cutaways", [])
            if (RUN / "rushes" / "broll" / f"{x['id']}.mp4").exists()
            and not x.get("dropped")]
    total = sum((x.get("revoice") or {}).get("seconds_out") or x["seconds"]
                for x in takes)
    cov = sum((x.get("generate") or {}).get("seconds_out") or x["seconds"]
              for x in cuts)
    pct = round(cov / total * 100) if total else 0
    when = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d %b %H:%M")
    mb = f.stat().st_size / 1_000_000
    return f"""
    <div class="cutbar" id="thecut">
      <video class="cutvid" src="/cut" controls preload="metadata" playsinline></video>
      <div class="cutinfo">
        <b>The cut</b><span class="own">editor</span>
        <span>{total:.0f}s &middot; {len(takes)} takes &middot; {len(cuts)} cutaways
              &middot; {pct}% B-roll, her face {100 - pct}%</span>
        <span class="dim">{when} &middot; {mb:.0f} MB &middot; 1080&times;1920</span>
        <div class="acts">
          <button class="go" id="recut">Re-cut from what is on disk</button>
          <a class="go alt dl" href="/cut" download="CUT.mp4">Download</a>
        </div>
        <p class="dim">Her voice runs the whole way and is never cut &mdash; only
        the picture changes. Cutaway positions resolve against the real
        durations on disk, not the ones the brief asked for.</p>
      </div>
    </div>"""


def strip_html(d: dict) -> str:
    """Every row on one line, so the state of the whole ad is one glance."""
    cells = []
    for s in d["scenes"]:
        lab, cls = status_of(s)
        cells.append(f'<a class="pip {cls}" href="#s-{e(s["id"])}">'
                     f'<b>{e(s["id"])}</b><span>{e(s["seconds"])}s</span></a>')
    for c in d.get("cutaways", []):
        f = RUN / "rushes" / "broll" / f"{c['id']}.mp4"
        if c.get("dropped"):
            cls, tip = "bad", "dropped"
        elif f.exists():
            cls, tip = "ok", "generated"
        else:
            st = (c.get("generate") or {}).get("status")
            cls = "wait" if st in ("pending", "queued", "in_progress") else "none"
            tip = st or "nothing yet"
        cells.append(f'<a class="pip {cls}" href="#c-{e(c["id"])}" title="{e(tip)}">'
                     f'<b>{e(c["id"])}</b><span>&rarr;{e(c["over"])}</span></a>')
    return f'<div class="strip">{"".join(cells)}</div>'



def kit_html(d: dict) -> str:
    """The product kit: which elements exist, what is true of each, which
    shots use it, and which are blocked and why.

    This panel exists because the FLEX was wrong in three different ways
    across three shots and there was nowhere on the board to SEE which
    element was attached. A control surface that hides the inputs is not one.
    """
    try:
        book = json.loads(PROMPT.FACTS_FILE.read_text()).get("elements", {})
    except Exception:
        return ""
    # who uses what
    used = {}
    for c in d.get("cutaways", []):
        blob = " ".join(str(c.get(k) or "") for k in ("place", "subject", "action", "look"))
        for uid in set(PROMPT._EL.findall(blob)):
            used.setdefault(uid, []).append(c["id"])
    cards = []
    for uid, row in book.items():
        if row.get("kind") != "product":
            continue
        shots = used.get(uid, [])
        blocked = row.get("blocked")
        thumb = (f'<img src="{e(row["thumb"])}" alt="{e(row["name"])}">'
                 if row.get("thumb") else "")
        if blocked:
            body = f'<p class="block">{e(row["warning"])}</p>'
        else:
            facts = "".join(f"<li>{e(f)}</li>" for f in row.get("facts", []))
            forb = "".join(f'<li class="nf">{e(f)}</li>' for f in row.get("forbids", []))
            note = f'<p class="pnote">{e(row["note"])}</p>' if row.get("note") else ""
            body = f'{note}<ul class="pf">{facts}{forb}</ul>'
        tag = ('<span class="ptag bad">blocked</span>' if blocked else
               '<span class="ptag good">canonical</span>' if row.get("canonical") else "")
        inuse = (f'<span class="inuse">in {", ".join(shots)}</span>' if shots
                 else '<span class="inuse off">not used in this ad</span>')
        cards.append(f"""
        <div class="prod{' off' if blocked else ''}">
          <div class="ppic">{thumb}</div>
          <div class="pbody">
            <div class="pname">{e(row["name"])} {tag} {inuse}</div>
            {body}
            <code class="elid">{e(uid)}</code>
          </div>
        </div>""")
    return f'<div class="kit">{"".join(cards)}</div>'


def page() -> bytes:
    d = load()
    q = [x for x in queue_read() if x.get("state") == "open"]
    total = sum(s["seconds"] for s in d["scenes"])
    done = sum(1 for s in d["scenes"] if clip_file(s["id"], "voiced").exists())
    qbar = ""
    if q:
        items = ", ".join(f'{x["action"]} {"/".join(x["ids"])}' for x in q[-6:])
        qbar = (f'<div class="qbar"><b>{len(q)} work order'
                f'{"s" if len(q) != 1 else ""} waiting for a session</b>'
                f'<span>{e(items)}</span></div>')
    body = f"""<div class="wrap">
<header class="top">
  <span class="eyebrow">brief · {e(d.get('brief'))}</span>
  <h1>{e(d['cast']['name'])} &mdash; the talking spine</h1>
  <p class="sub">{len(d['scenes'])} beats &middot; {total}s of A-roll &middot;
     {done} revoiced &middot; {e(d['cast'].get('resolution','720p'))} &middot;
     <b>cinematic_studio_3_0</b>, the line in the prompt, then voice_change</p>
</header>
{qbar}
{chain_html(d)}
{final_cut_html(d)}
{strip_html(d)}
<section>
  <span class="eyebrow" id="cast">the cast — banked elements, so nothing gets described twice</span>
  {cast_html(d)}
</section>
<section>
  <span class="eyebrow" id="products">the product &mdash; what is attached, and what is true of it</span>
  {kit_html(d)}
</section>
<section>
  <span class="eyebrow" id="prompts">the prompts that drive this chain &mdash; edit the file, every brief changes</span>
  {prompts_html(d)}
</section>
<section>
  <span class="eyebrow" id="beats">the beats</span>
  {"".join(scene_html(s, d) for s in d['scenes'])}
</section>
<section>
  <span class="eyebrow" id="cuts">the cutaways &mdash; silent, laid over the take they cover</span>
  {"".join(cut_html(c) for c in d.get('cutaways', []))}
</section>
<div class="allbar">
  <button class="go big" data-act="generate" data-id="*">Generate every beat</button>
  <button class="go big alt" data-act="revoice" data-id="*">Revoice every beat</button>
  <button class="go big alt" data-act="broll" data-id="*">Generate every cutaway</button>
</div>
</div>"""
    return (HEAD + body + SCRIPT).encode()


HEAD = """<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cinema board</title>
<style>
:root{--f:#16181A;--f2:#101214;--f3:#1E2226;--c:#E6E8EA;--sg:#9AA0A6;
 --ms:#5C6368;--g:#7FA8D0;--g2:#A8C8E6;--r:rgba(154,160,166,.22)}
/* Neutral by rule (Damon, 2026-09-14): this surface serves every brand, so it
   carries none of their colour. A board painted in one brand's green reads as
   that brand's tool and quietly stops being used for the others. */
*{box-sizing:border-box}
body{margin:0;background:var(--f);color:var(--c);font:15px/1.55
 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:0 20px 90px}
.eyebrow{font:11px/1 ui-monospace,Menlo,monospace;letter-spacing:.16em;
 text-transform:uppercase;color:var(--sg);display:block;margin-bottom:10px}
.top{padding:40px 0 26px;border-bottom:1px solid var(--r)}
h1{margin:8px 0 0;font:600 34px/1.1 -apple-system,BlinkMacSystemFont,"Segoe UI",
 Helvetica,Arial,sans-serif;letter-spacing:-.02em}
.sub{color:var(--sg);margin:12px 0 0;font-size:14px}
.sub b{color:var(--g2)}
section{padding:34px 0 0}
.qbar{margin:22px 0 0;padding:12px 16px;border:1px solid var(--g);
 background:rgba(232,172,33,.09);font-size:13px;display:flex;gap:16px;
 flex-wrap:wrap;align-items:baseline}
.qbar b{color:var(--g2)} .qbar span{color:var(--sg)}
/* cast */
.cast{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
 gap:1px;background:var(--r);border:1px solid var(--r)}
.el{background:var(--f2);padding:16px;display:flex;gap:14px}
.elpic{flex:0 0 74px}
.elpic img{width:74px;height:100px;object-fit:cover;border:1px solid var(--r);display:block}
.novis{width:74px;height:100px;border:1px dashed var(--r);display:grid;
 place-items:center;font:10px ui-monospace,monospace;color:var(--ms);
 letter-spacing:.1em;text-transform:uppercase}
.slot{display:block;font:10px/1 ui-monospace,Menlo,monospace;letter-spacing:.14em;
 text-transform:uppercase;color:var(--ms);margin:0 0 6px}
.elname{font:600 14px/1.2 inherit;color:var(--g2)}
.elrole{font-size:12.5px;color:var(--sg);margin-top:3px}
.eldesc{font-size:12px;color:var(--sg);opacity:.72;margin-top:7px}
.elid{display:block;margin-top:8px;font:10.5px ui-monospace,monospace;color:var(--ms)}
.alts{margin-top:16px}
.chip{display:inline-block;border:1px solid var(--r);padding:5px 10px;
 margin:0 7px 7px 0;font-size:12px;color:var(--sg)}
.chip b{color:var(--c);margin-right:6px}
/* scene */
.scene{border:1px solid var(--r);margin:18px 0 0;background:var(--f2)}
.scene header{display:flex;gap:14px;align-items:center;padding:12px 16px;
 border-bottom:1px solid var(--r);background:var(--f3);flex-wrap:wrap}
.sid{font:600 13px ui-monospace,monospace;color:var(--g2);letter-spacing:.08em}
.scene header input{flex:1;min-width:140px;background:transparent;border:0;
 color:var(--c);font:400 19px Georgia,serif;padding:2px 0}
.scene header input:focus{outline:0;border-bottom:1px solid var(--g)}
.secs{font:11px ui-monospace,monospace;color:var(--sg)}
.st{font:10px ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 padding:4px 9px;border:1px solid var(--r);white-space:nowrap}
.st.ok{color:#8fe0a8;border-color:#8fe0a8} .st.part{color:var(--g2);border-color:var(--g)}
.st.wait{color:#9fc3ff;border-color:#9fc3ff} .st.bad{color:#ff9a8f;border-color:#ff9a8f}
.st.none{color:var(--ms)}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:1px;
 background:var(--r)}
.col{background:var(--f2);padding:16px;min-width:0}
textarea.f,input.f{width:100%;background:var(--f);border:1px solid var(--r);
 color:var(--c);font:14px/1.5 inherit;padding:9px 10px;margin:0 0 14px;resize:vertical}
textarea.f:focus,input.f:focus{outline:0;border-color:var(--g)}
textarea.line{font:15px/1.55 Georgia,serif}
.f.dirty{border-color:var(--g2)}
pre.prompt{margin:0 0 14px;background:var(--f);border:1px solid var(--r);
 padding:12px;font:11.5px/1.6 ui-monospace,Menlo,monospace;color:var(--sg);
 white-space:pre-wrap;word-break:break-word;max-height:330px;overflow:auto}
.acts{display:flex;gap:8px;margin-bottom:12px}
.go{background:linear-gradient(90deg,var(--g) 30%,var(--g2) 77%);color:#1A1A1A;
 border:0;border-radius:0;padding:9px 16px;font:600 13px inherit;cursor:pointer}
.go.alt{background:transparent;color:var(--g2);border:1px solid var(--g)}
.go:disabled{opacity:.45;cursor:default}
.go.big{padding:13px 24px;font-size:14px}
.ids{display:flex;gap:16px;flex-wrap:wrap;font:10.5px ui-monospace,monospace;
 color:var(--ms)}
.ids b{color:var(--sg);font-weight:400}
figure{margin:0 0 12px}
video{width:100%;max-width:280px;display:block;border:1px solid var(--r);background:#000}
figcaption{font:10px ui-monospace,monospace;color:var(--ms);margin-top:5px;
 letter-spacing:.08em;text-transform:uppercase}
.empty{border:1px dashed var(--r);padding:22px;text-align:center;
 font:11px ui-monospace,monospace;color:var(--ms);letter-spacing:.1em;
 text-transform:uppercase}
.warn{margin:0;padding:10px 16px;background:rgba(255,154,143,.12);
 color:#ff9a8f;font-size:13px;border-bottom:1px solid var(--r)}
.allbar{margin:30px 0 0;padding:20px;border:1px solid var(--r);
 background:var(--f2);display:flex;gap:12px;flex-wrap:wrap}
.cut header{background:#07301a}
.over{font:11px ui-monospace,monospace;color:var(--sg)} .over b{color:var(--g2)}
.why{flex:1;min-width:120px;font:italic 15px Georgia,serif;color:var(--sg)}
textarea.fc{width:100%;background:var(--f);border:1px solid var(--r);
 color:var(--c);font:13.5px/1.5 inherit;padding:9px 10px;margin:0 0 12px;resize:vertical}
textarea.fc:focus{outline:0;border-color:var(--g)}
textarea.fc.dirty{border-color:var(--g2)}
textarea.fx{width:100%;background:#0d2a18;border:1px solid var(--g);
 color:var(--c);font:13.5px/1.5 inherit;padding:9px 10px;margin:0 0 10px;resize:vertical}
textarea.fx:focus{outline:0;border-color:var(--g2)}
textarea.fx::placeholder{color:var(--ms)}
.go.regen{background:linear-gradient(90deg,var(--g) 30%,var(--g2) 77%);color:#1A1A1A}
.hist{margin:10px 0 0;font-size:12.5px}
.hist summary{cursor:pointer;color:var(--sg);font:11px ui-monospace,monospace;
 letter-spacing:.08em;text-transform:uppercase}
.hist ul{list-style:none;padding:10px 0 0;margin:0}
.hist li{padding:7px 0;border-top:1px solid var(--r);display:flex;gap:10px;
 align-items:baseline;flex-wrap:wrap}
.vn{font:10px ui-monospace,monospace;color:var(--g2)}
.vr{flex:1;min-width:160px;color:var(--sg)}
details.pr{margin:0 0 12px}
details.pr summary{cursor:pointer;font:10px ui-monospace,Menlo,monospace;
 letter-spacing:.14em;text-transform:uppercase;color:var(--ms);padding:4px 0}
details.pr[open] summary{color:var(--sg)}
.strip{display:flex;flex-wrap:wrap;gap:4px;margin:22px 0 0;
 position:sticky;top:0;background:var(--f);padding:10px 0;z-index:5;
 border-bottom:1px solid var(--r)}
.pip{display:flex;flex-direction:column;gap:1px;text-decoration:none;
 border:1px solid var(--r);padding:5px 9px;min-width:52px;
 font:10px ui-monospace,Menlo,monospace;color:var(--sg)}
.pip b{font-size:11px;font-weight:600;letter-spacing:.06em}
.pip span{opacity:.65;font-size:9px}
.pip.ok{border-color:#8fe0a8;color:#8fe0a8}
.pip.part{border-color:var(--g);color:var(--g2)}
.pip.wait{border-color:#9fc3ff;color:#9fc3ff}
.pip.bad{border-color:#ff9a8f;color:#ff9a8f}
.pip.none{color:var(--ms)}
.pip:hover{background:var(--f3)}
.kit{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));
 gap:1px;background:var(--r);border:1px solid var(--r)}
.prod{background:var(--f2);padding:16px;display:flex;gap:14px}
.prod.off{opacity:.62}
.ppic{flex:0 0 66px}
.ppic img{width:66px;height:90px;object-fit:contain;background:#fff;
 border:1px solid var(--r);display:block}
.pname{font:600 14px/1.3 inherit;color:var(--g2);display:flex;gap:8px;
 align-items:baseline;flex-wrap:wrap}
.ptag{font:9px ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;
 border:1px solid;padding:2px 6px}
.ptag.good{color:#8fe0a8;border-color:#8fe0a8}
.ptag.bad{color:#ff9a8f;border-color:#ff9a8f}
.inuse{font:10px ui-monospace,monospace;color:var(--ms);letter-spacing:.06em}
.inuse.off{opacity:.6}
.pnote{margin:7px 0 0;font-size:12.5px;color:var(--sg)}
ul.pf{margin:8px 0 0;padding:0 0 0 16px;font-size:12.5px;color:var(--sg)}
ul.pf li{margin:3px 0}
ul.pf li.nf{color:var(--g2)}
.block{margin:7px 0 0;font-size:12.5px;color:#ff9a8f}
.cutbar{display:flex;gap:22px;margin:22px 0 0;padding:20px;
 border:1px solid var(--g);background:rgba(232,172,33,.06);flex-wrap:wrap}
.cutvid{width:190px;flex:0 0 190px;border:1px solid var(--r);background:#000}
.cutinfo{flex:1;min-width:240px;display:flex;flex-direction:column;gap:6px;
 align-items:flex-start}
.cutinfo b{font:400 26px/1 Georgia,serif;color:var(--g2)}
.cutinfo span{font-size:13px;color:var(--sg)}
.cutinfo .dim{font-size:11.5px;color:var(--ms);max-width:60ch}
.cutinfo .acts{margin:6px 0 2px}
a.dl{text-decoration:none;display:inline-block}
.chain{margin:22px 0 0;border:1px solid var(--r);background:var(--f2)}
.chead{display:flex;gap:14px;align-items:baseline;padding:14px 18px;
 border-bottom:1px solid var(--r);flex-wrap:wrap}
.chead b{font:400 24px/1 Georgia,serif;color:var(--g2)}
.chead span{font:11px ui-monospace,monospace;color:var(--sg);letter-spacing:.08em;
 text-transform:uppercase}
.ctab{width:100%;border-collapse:collapse;font-size:13.5px}
.ctab thead th{text-align:left;padding:8px 18px;font:10px ui-monospace,monospace;
 letter-spacing:.14em;text-transform:uppercase;color:var(--ms);font-weight:400}
.ctab thead th:nth-child(3),.ctab thead th:nth-child(4){text-align:right}
.cr td{padding:9px 18px;border-top:1px solid var(--r)}
.cn{font-weight:600;white-space:nowrap}
.cn a{color:inherit;text-decoration:none;border-bottom:1px solid var(--r)}
.cw{color:var(--sg);font-size:12.5px}
.cnum{text-align:right;font:12px ui-monospace,monospace;
 font-variant-numeric:tabular-nums;white-space:nowrap}
.cs{white-space:nowrap;font:10px ui-monospace,monospace;letter-spacing:.1em;
 text-transform:uppercase}
.dot{display:inline-block;width:7px;height:7px;margin-right:7px;
 vertical-align:middle;border-radius:50%}
.cr.done{color:var(--c)} .cr.done .dot{background:#8fe0a8}
.cr.done .cs{color:#8fe0a8}
.cr.override .dot{background:var(--g2)} .cr.override .cs{color:var(--g2)}
.cr.gap .dot{background:#ff9a8f} .cr.gap .cs{color:#ff9a8f}
.cr.gap .cn{color:#ff9a8f}
.cdet td{padding:0 18px 9px;font-size:12px;color:var(--ms)}
.cdet .cd{display:block;max-width:78ch}
.cend{font:10px ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 color:var(--ms);border:1px solid var(--r);padding:3px 8px}
.hand{border-top:1px solid var(--r);padding:14px 18px;background:rgba(63,110,102,.10)}
.hl{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.hl b{color:var(--sg);font-size:14px}
.arrow{color:var(--moss);font-size:16px}
.hs{font:10px ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 color:var(--ms)}
ul.ho{margin:8px 0 0;padding:0 0 0 26px;font-size:12.5px;color:var(--ms)}
ul.ho li{margin:2px 0}
.hc{margin:9px 0 0 26px;font-size:12px;color:var(--sg);max-width:76ch}
.own{font:9px ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 color:var(--ms);border:1px solid var(--r);padding:2px 7px;margin-left:10px}
.pms{display:flex;flex-direction:column;gap:1px;background:var(--r);
 border:1px solid var(--r)}
.pm{background:var(--f2)}
.pm summary{cursor:pointer;padding:13px 16px;display:flex;gap:12px;
 align-items:baseline;flex-wrap:wrap;font-size:13px}
.pm summary b{color:var(--g2);font-size:14px}
.pm summary code{font:10.5px ui-monospace,monospace;color:var(--ms)}
.plen{font:10px ui-monospace,monospace;color:var(--ms);margin-left:auto}
.pm[open] summary{border-bottom:1px solid var(--r)}
pre.pbody{margin:0;padding:16px;font:11.5px/1.7 ui-monospace,Menlo,monospace;
 color:var(--sg);white-space:pre-wrap;word-break:break-word;
 max-height:560px;overflow:auto;background:var(--f)}
.pm.miss{padding:13px 16px;color:#ff9a8f;font-size:13px}
.pm.miss span{margin-left:10px;font:11px ui-monospace,monospace}
.saved{position:fixed;right:16px;bottom:16px;background:var(--g2);color:#1A1A1A;
 padding:9px 15px;font:600 12px inherit;opacity:0;transition:opacity .18s}
.saved.on{opacity:1}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
</style>
<div class="saved" id="saved">saved</div>
"""

SCRIPT = """<script>
const flash=(t)=>{const s=document.getElementById('saved');s.textContent=t;
  s.classList.add('on');setTimeout(()=>s.classList.remove('on'),1200)};
let timer=null;
document.addEventListener('input',ev=>{
  const el=ev.target;
  const isCut=el.classList.contains('fc');
  const isFix=el.classList.contains('fx');
  if(isFix){el.classList.add('dirty');clearTimeout(timer);
    timer=setTimeout(()=>{
      fetch((el.dataset.kind==='cut'?'/api/cut/':'/api/scene/')+el.dataset.id,
        {method:'POST',headers:{'Content-Type':'application/json'},
         body:JSON.stringify({change:el.value})})
       .then(()=>{el.classList.remove('dirty');flash('note saved')});},700);
    return;}
  if(!el.classList.contains('f')&&!isCut)return;
  el.classList.add('dirty'); clearTimeout(timer);
  timer=setTimeout(()=>{
    fetch((isCut?'/api/cut/':'/api/scene/')+el.dataset.id,{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({[el.dataset.k]:el.value})})
     .then(r=>r.json()).then(()=>{el.classList.remove('dirty');
        flash('saved'); refreshPrompt(el.dataset.id,isCut)});
  },700);
});
function refreshPrompt(id,isCut){
  fetch((isCut?'/api/cutprompt/':'/api/prompt/')+id).then(r=>r.text()).then(t=>{
    const card=document.getElementById((isCut?'c-':'s-')+id);
    if(card) card.querySelector('pre.prompt').textContent=t;
  });
}
document.addEventListener('click',ev=>{
  if(ev.target.id==='recut'){
    const b=ev.target; b.disabled=true; b.textContent='cutting…';
    fetch('/api/recut',{method:'POST'}).then(x=>x.json()).then(d=>{
      flash(d.ok?'cut':'cut failed'); setTimeout(()=>location.reload(),700);});
    return;}
  const r=ev.target.closest('button.regen');
  if(r){
    const card=document.getElementById((r.dataset.kind==='cut'?'c-':'s-')+r.dataset.id);
    const box=card.querySelector('textarea.fx');
    if(!box.value.trim()){box.focus();flash('say what needs changing first');return;}
    r.disabled=true;
    fetch('/api/regen/'+r.dataset.id,{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({kind:r.dataset.kind,change:box.value})})
     .then(x=>x.json()).then(()=>{flash('queued with your note');
        r.disabled=false;setTimeout(()=>location.reload(),900)});
    return;}
  const b=ev.target.closest('button.go'); if(!b)return;
  b.disabled=true;
  fetch('/api/queue',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({action:b.dataset.act,id:b.dataset.id})})
   .then(r=>r.json()).then(d=>{
     flash('queued — a session picks it up');
     b.disabled=false;
     setTimeout(()=>location.reload(),900);
   });
});
</script>"""


# ----------------------------------------------------------------- server
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(200, page(), "text/html; charset=utf-8")
        if u.path == "/api/plan":
            return self._send(200, load())
        if u.path.startswith("/api/cutprompt/"):
            cid = u.path.rsplit("/", 1)[-1]
            d = load()
            row = next((c for c in d.get("cutaways", []) if c["id"] == cid), None)
            if not row:
                return self._send(404, "no such cutaway", "text/plain")
            return self._send(200, PROMPT.broll(row)["prompt"],
                              "text/plain; charset=utf-8")
        if u.path.startswith("/api/prompt/"):
            sid = u.path.rsplit("/", 1)[-1]
            d = load()
            row = next((s for s in d["scenes"] if s["id"] == sid), None)
            if not row:
                return self._send(404, "no such beat", "text/plain")
            try:
                return self._send(200, PROMPT.payload(row, d["cast"])["prompt"],
                                  "text/plain; charset=utf-8")
            except SystemExit as ex:
                return self._send(200, str(ex), "text/plain; charset=utf-8")
        if u.path.startswith("/element/"):
            # The cast strip was a row of empty boxes because thumb was blank.
            # The element images live on Drive, not in git (workspace rule 3),
            # so the board serves them from there by element id. 2026-09-14.
            eid = u.path.rsplit("/", 1)[-1]
            try:
                import json as _j
                brand = load().get("brand")
                ws = Path(__file__).resolve().parents[4]
                idx = _j.loads((ws / "brands" / brand / "elements" / "index.json").read_text())
                items = idx.get("elements") if isinstance(idx.get("elements"), list) else \
                    [v for v in idx.values() if isinstance(v, dict)]
                src = next((x["source"] for x in items if x.get("element_id") == eid), None)
                dr = (_drive_root() / "Shared drives" / "Shared Assets"
                      / "brands" / brand / src) if src else None
                if dr and dr.is_file():
                    ct = {"png": "image/png", "jpg": "image/jpeg",
                          "webp": "image/webp"}.get(dr.suffix.lstrip(".").lower(), "image/png")
                    return self._send(200, dr.read_bytes(), ct)
            except Exception:
                pass
            return self._send(404, "no element image", "text/plain")
        if u.path.startswith("/still/"):
            sid = u.path.rsplit("/", 1)[-1]
            f = RUN / "rushes" / "broll" / f"{sid}.png"
            if "/" in sid or ".." in sid or not f.exists():
                return self._send(404, "no still", "text/plain")
            # Serve a downscaled JPEG, keep the PNG as the master. The stills are
            # ~6.4MB each and nineteen of them is 120MB on one page, which is not
            # a board, it is a download — and it is why the page went blank on
            # scroll. Cached beside the master, rebuilt when the master changes.
            web = RUN / "rushes" / "web" / f"{sid}.jpg"
            if not web.exists() or web.stat().st_mtime < f.stat().st_mtime:
                web.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["sips", "-Z", "900", "-s", "format", "jpeg",
                                "-s", "formatOptions", "72", str(f), "--out", str(web)],
                               capture_output=True)
            if web.exists():
                return self._send(200, web.read_bytes(), "image/jpeg")
            return self._send(200, f.read_bytes(), "image/png")
        if u.path == "/cut":
            f = RUN / "cinema" / "CUT.mp4"
            if not f.exists():
                return self._send(404, "no cut yet", "text/plain")
            return self._send(200, f.read_bytes(), "video/mp4")
        if u.path.startswith("/version/"):
            name = u.path.rsplit("/", 1)[-1]
            f = RUN / "iterations" / "versions" / name
            if "/" in name or ".." in name or not f.exists():
                return self._send(404, "no such version", "text/plain")
            return self._send(200, f.read_bytes(), "video/mp4")
        if u.path.startswith("/clip/"):
            _, _, sid, kind = u.path.split("/", 3)
            f = clip_file(sid, kind)
            if not f.exists():
                return self._send(404, "no clip", "text/plain")
            data = f.read_bytes()
            return self._send(200, data,
                              mimetypes.guess_type(f.name)[0] or "video/mp4")
        if u.path == "/api/queue":
            return self._send(200, queue_read())
        return self._send(404, {"error": "no such endpoint"})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if u.path.startswith("/api/cut/"):
            cid = u.path.rsplit("/", 1)[-1]
            d = load()
            row = next((c for c in d.get("cutaways", []) if c["id"] == cid), None)
            if not row:
                return self._send(404, {"error": "no such cutaway"})
            for k, v in body.items():
                if k in EDITABLE_CUT:
                    row[k] = v
            save(d)
            return self._send(200, {"ok": True, "id": cid})
        if u.path.startswith("/api/scene/"):
            sid = u.path.rsplit("/", 1)[-1]
            d = load()
            row = next((s for s in d["scenes"] if s["id"] == sid), None)
            if not row:
                return self._send(404, {"error": "no such beat"})
            for k, v in body.items():
                if k in EDITABLE:
                    row[k] = v
            save(d)
            return self._send(200, {"ok": True, "id": sid})
        if u.path == "/api/recut":
            # Assembly is local ffmpeg and does not go through the queue.
            r = subprocess.run(
                [sys.executable, str(HERE / "(retired — editing is the editor's)"), str(RUN)],
                capture_output=True, text=True)
            return self._send(200, {"ok": r.returncode == 0,
                                    "out": (r.stdout or r.stderr)[-1200:]})
        if u.path.startswith("/api/regen/"):
            rid = u.path.rsplit("/", 1)[-1]
            d = load()
            kind = body.get("kind")
            pool = d.get("cutaways", []) if kind == "cut" else d["scenes"]
            row = next((r for r in pool if r["id"] == rid), None)
            if not row:
                return self._send(404, {"error": "no such row"})
            note = (body.get("change") or row.get("change") or "").strip()
            if not note:
                return self._send(400, {"error": "say what needs changing first"})
            row["change"] = note
            save(d)
            act = "broll" if kind == "cut" else "generate"
            return self._send(200, {"ok": True, "queue": queue_add(act, [rid])})
        if u.path == "/api/queue":
            d = load()
            ids = ([s["id"] for s in d["scenes"]] if body.get("id") == "*"
                   else [body.get("id")])
            act = body.get("action")
            if act == "broll":
                ids = ([c["id"] for c in d.get("cutaways", [])]
                       if body.get("id") == "*" else [body.get("id")])
            elif act not in ("generate", "revoice"):
                return self._send(400, {"error": "generate, revoice or broll"})
            return self._send(200, {"ok": True, "queue": queue_add(act, ids)})
        return self._send(404, {"error": "no such endpoint"})


def main():
    global RUN
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    RUN = Path(sys.argv[1]).expanduser().resolve()
    if not plan_path().exists():
        sys.exit(f"no cinema/plan.json in {RUN}")
    # Bind the run's brand before serving. prompt.py keeps BRAND as module
    # state and its own load() sets it — but this board reads the plan itself,
    # so nothing set it and every page build died on SystemExit inside the
    # request thread. A dead thread returns an empty reply, so the browser
    # showed ERR_EMPTY_RESPONSE with no error anywhere. (2026-09-13)
    PROMPT.use_brand(load().get("brand"))
    (RUN / "cinema" / "raw").mkdir(parents=True, exist_ok=True)
    (RUN / "rushes" / "clips").mkdir(parents=True, exist_ok=True)
    (RUN / "rushes" / "broll").mkdir(parents=True, exist_ok=True)
    print(f"cinema board · {RUN.name} · http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
