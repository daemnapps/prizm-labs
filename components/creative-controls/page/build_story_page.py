#!/usr/bin/env python3
"""The Story Playbook page: the story layer of controls.json (arcs, story devices, persuasion triggers, the edge
line), drawn for a person to read. Reads only controls.json; writes the page and its Markdown mirror.

    python3 components/creative-controls/page/build_story_page.py

Writes page/story-playbook.html (published as the Story Playbook artifact) and context/STORY-PLAYBOOK-owner.md.
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
OUT = HERE / "story-playbook.html"
MIRROR = COMP / "context" / "STORY-PLAYBOOK-owner.md"

# How each arc's line moves, left to right (0 = low, 1 = high): the picture of the shape, not data.
SHAPES = {
    "person-in-a-hole": [.62, .6, .25, .1, .45, .92], "rags-to-riches": [.1, .3, .48, .7, .92],
    "icarus": [.3, .6, .92, .55, .08], "cinderella": [.2, .62, .72, .18, .6, .95],
    "oedipus": [.6, .18, .6, .72, .2, .05], "save-the-cat": [.5, .55, .4, .62, .72, .82, .5, .15, .4, .92],
    "heros-journey": [.5, .4, .3, .5, .12, .7, .92], "kishotenketsu": [.45, .48, .52, .95, .62],
    "but-therefore": [.3, .1, .42, .2, .62, .4, .92], "cold-open": [.95, .3, .42, .62, .95, .8],
    "mystery-box": [.4, .48, .56, .66, .78, 1.0], "epiphany-bridge": [.4, .5, .18, .72, .6, .42, .92],
    "escalation-ladder": [.15, .15, .38, .38, .62, .62, .88, .88, .45], "micro-drama": [.9, .3, .72, .18, .95],
    "two-sides": [.6, .3, .62, .28, .85], "unreliable-narrator": [.75, .8, .86, .92, .1],
    "transformation-reveal": [.15, .15, .18, .18, .95],
}
AWARE = ["unaware", "problem-aware", "solution-aware", "product-aware", "most-aware"]
E = html.escape


def curve(aid):
    if aid == "story-circle":
        return ('<svg viewBox="0 0 120 48" aria-hidden="true"><circle cx="60" cy="24" r="18" class="ln"/>'
                '<circle cx="60" cy="6" r="3.2" class="dot"/></svg>')
    ys = SHAPES.get(aid, [.5, .5])
    n = len(ys) - 1
    pts = [(6 + 108 * i / n, 42 - 36 * y) for i, y in enumerate(ys)]
    d = "M%.1f %.1f " % pts[0] + " ".join("L%.1f %.1f" % p for p in pts[1:])
    end = pts[-1]
    return ('<svg viewBox="0 0 120 48" aria-hidden="true"><line x1="6" y1="24" x2="114" y2="24" class="mid"/>'
            '<path d="%s" class="ln"/><circle cx="%.1f" cy="%.1f" r="3.2" class="dot"/></svg>' % (d, end[0], end[1]))


DOCTRINE = COMP.parent / "marketing-doctrine" / "frameworks.json"
PLAYBOOKS = COMP.parent / "video-production" / "formats" / "playbooks"

# The one flow every ad runs, in order, on the tools that exist: (step, what it decides, the tool, who decides).
FLOW = [
    ("Avatar + product", "Who it is for and what the product honestly does", "brand files · research round · culture map", ""),
    ("The idea", "Door A: a swipe that already works. Door B: our own story, no swipe", "swipe pools + teardown · research bank (concept)", "the owner picks"),
    ("Awareness", "Where the ad is allowed to begin", "marketing rulebook", "the owner picks"),
    ("Arc", "The story's shape; each beat is a section", "Story Playbook", "the owner picks"),
    ("Format + style", "What kind of ad and what it looks like", "format and style banks · format playbook", ""),
    ("Writing", "Hooks, script, audit, spice, the brief; dials, spice and culture read in", "video writing (door B: from scratch)", ""),
    ("Brief review", "Is this the ad", "the board", "the owner OKs"),
    ("Audio first", "The song or the voice, made from the brief", "video production", "the owner OKs"),
    ("Cast, rooms, scene pictures", "Who is in it, the 3D sets, one picture per scene", "casting · the board", "the owner OKs each"),
    ("Hand-off", "Clips, B-roll, effects, the cut", "hand-off folder", "the team"),
    ("Launch", "Review, names, the approval card", "ad review · naming · Meta card", "the owner's click"),
]


def page(c):
    doc = json.loads(DOCTRINE.read_text())
    levels = doc["awareness"]["levels"][::-1]
    secs = {x["id"]: x for x in doc["sections"]}
    arcs = c["arcs"]
    flow = "".join('<li><b>%s</b><span>%s</span><em>%s</em>%s</li>' % (E(a), E(b), E(w), '<i class="who">%s</i>' % E(o) if o else "")
                   for a, b, w, o in FLOW)
    aw = "".join(
        '<div class="lvl"><h3>%s</h3><p><span>Knows</span>%s</p><p><span>The ad begins</span>%s</p>'
        '<div class="chips">%s</div></div>' % (
            E(l["name"]), E(l["knows"]), E(l["where_the_ad_may_begin"]),
            "".join('<a class="chip" href="#%s">%s</a>' % (x["id"], E(x["name"])) for x in arcs if l["id"] in x["best_for"]))
        for l in levels)
    cards = []
    for a in arcs:
        beats = "".join('<li>%s <i>%s</i></li>' % (E(b["beat"]), E(secs[b["section"]]["name"])) for b in a["beats"])
        cards.append(
            '<article class="arc" id="%s"><div class="arc-top">%s<div><h3>%s</h3><p class="shape">%s</p></div></div>'
            '<p>%s</p><ol class="beats">%s</ol><p class="src">%s · best for %s</p></article>' % (
                a["id"], curve(a["id"]), E(a["name"]), E(a["what"]), E(a["how"]), beats, E(a["source"]),
                E(", ".join(x.replace("-", " ") for x in a["best_for"]))))
    sec = "".join('<div class="sec"><b>%s</b><p>%s</p></div>' % (E(x["name"]), E(x["what"])) for x in doc["sections"])
    fams = []
    for d in c["story_devices"]:
        if d["family"] not in fams:
            fams.append(d["family"])
    devs = "".join(
        '<section class="fam"><h3>%s</h3>%s</section>' % (E(f), "".join(
            '<div class="dev"><b>%s</b><p>%s</p><p class="push"><span>How</span>%s</p><p class="src">%s</p></div>' % (
                E(d["name"]), E(d["what"]), E(d["how"]), E(d["source"])) for d in c["story_devices"] if d["family"] == f))
        for f in fams)
    trig = "".join(
        '<div class="trig"><b>%s</b><p>%s</p><div class="pl"><p class="push"><span>How</span>%s</p>'
        '<p class="line"><span>The line</span>%s</p></div><p class="src">%s</p></div>' % (
            E(t["name"]), E(t["what"]), E(t["how"]), E(t["line"]), E(t["source"])) for t in c["persuasion_triggers"])
    e = c["edge_line"]
    edge = ('<div class="edge"><div class="side go"><h3>Push it</h3><ul>%s</ul></div>'
            '<div class="side stop"><h3>Never</h3><ul>%s</ul></div></div>') % (
        "".join("<li>%s</li>" % E(x) for x in e["push"]), "".join("<li>%s</li>" % E(x) for x in e["never"]))
    wfs = []
    for pbf in sorted(PLAYBOOKS.glob("*.json")):          # every ad type that has a workflow you start by name
        pb = json.loads(pbf.read_text())
        wf = pb.get("workflow")
        if not wf:
            continue
        rows = "".join('<li><b>%s</b><span>%s</span><em>%s</em>%s</li>' % (
            E(st["name"]), E(st["does"]), E(st["component"]),
            '<i class="who">%s</i>' % E(st["gate"]) if st.get("gate") else "") for st in wf["steps"])
        bar = "".join("<li>%s</li>" % E(q) for q in pb.get("quality_bar") or [])
        wfs.append('<article class="wf"><h3>%s <code>%s</code></h3><p class="rule">%s Say "run the %s workflow".</p>'
                   '<ol class="flow">%s</ol><details class="bar"><summary>The quality bar (%d)</summary><ul>%s</ul></details></article>'
                   % (E(pb["name"]), E(pb["format_id"]), E(wf["what"]), E(pb["format_id"]), rows,
                      len(pb.get("quality_bar") or []), bar))
    return TEMPLATE.format(workflows="".join(wfs) or "<p class=\"rule\">None yet.</p>", flow=flow, aw=aw, arcs="".join(cards), sections=sec, arc_rule=E(c["arc_rule"]),
                           device_rule=E(c["device_rule"]), trigger_rule=E(c["trigger_rule"]),
                           devices=devs, triggers=trig, edge=edge, updated=E(c.get("updated", "")))


def mirror(c):
    doc = json.loads(DOCTRINE.read_text())
    secs = {x["id"]: x["name"] for x in doc["sections"]}
    out = ["# Story Playbook", "", "The flow every ad runs, and the story layer of the creative controls",
           "(`components/creative-controls/controls.json`); awareness and sections are the marketing rulebook's",
           "(`components/marketing-doctrine/frameworks.json`). Page: see `tools/image-teardown/context/artifacts.md`.", "",
           "## The flow", ""] + ["%d. **%s**: %s (%s)%s" % (i + 1, a, b, w, " — " + o if o else "") for i, (a, b, w, o) in enumerate(FLOW)]
    out += ["", "## Awareness → arcs", ""]
    for l in doc["awareness"]["levels"][::-1]:
        out.append("- **%s**: %s Begins: %s Arcs: %s" % (l["name"], l["knows"], l["where_the_ad_may_begin"],
                                                         ", ".join(a["name"] for a in c["arcs"] if l["id"] in a["best_for"])))
    out += ["", "## Arcs", "", c["arc_rule"], ""]
    for a in c["arcs"]:
        out += ["### %s (`%s`)" % (a["name"], a["id"]), "", a["what"] + " " + a["how"], "",
                "Beats → sections: " + " → ".join("%s (%s)" % (b["beat"], secs[b["section"]]) for b in a["beats"]), "",
                "Source: " + a["source"], ""]
    out += ["## Story devices", "", c["device_rule"], ""]
    out += ["- **%s** (%s): %s How: %s _(%s)_" % (d["name"], d["family"], d["what"], d["how"], d["source"]) for d in c["story_devices"]]
    out += ["", "## Persuasion triggers", "", c["trigger_rule"], ""]
    out += ["- **%s**: %s How: %s The line: %s _(%s)_" % (t["name"], t["what"], t["how"], t["line"], t["source"]) for t in c["persuasion_triggers"]]
    out += ["", "## The edge", "", "Push:", ""] + ["- " + x for x in c["edge_line"]["push"]]
    out += ["", "Never:", ""] + ["- " + x for x in c["edge_line"]["never"]]
    return "\n".join(out) + "\n"


TEMPLATE = """<title>Story Playbook</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap">
<style>
/* layout: a reading spine; arcs as a grid of shape cards, then devices, triggers, the edge */
:root{{--bg:#fafafa;--card:#fff;--fg:#18181b;--mut:#62626d;--line:#e4e4e9;--accent:#c2410c;--accentbg:#fdf0e8;--go:#0f766e;--gobg:#e6f4f2;--stop:#b91c1c;--stopbg:#fdecec;
--display:"Fraunces",Georgia,serif;--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0c0c0e;--card:#151518;--fg:#f4f4f5;--mut:#a1a1aa;--line:#2a2a30;--accent:#fb923c;--accentbg:#2a170c;--go:#5eead4;--gobg:#0d2a27;--stop:#f87171;--stopbg:#2c1212;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0c0c0e;--card:#151518;--fg:#f4f4f5;--mut:#a1a1aa;--line:#2a2a30;--accent:#fb923c;--accentbg:#2a170c;--go:#5eead4;--gobg:#0d2a27;--stop:#f87171;--stopbg:#2c1212;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font:16px/1.55 var(--sans)}}
.wrap{{max-width:1080px;margin:0 auto;padding-block:36px 72px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:48px}}
.eye{{font:500 12px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}}
h1{{font:800 clamp(36px,7vw,64px)/1.02 var(--display);letter-spacing:-.02em;margin:10px 0 12px;text-wrap:balance}}
h2{{font:800 clamp(24px,4vw,32px)/1.1 var(--display);margin:0 0 8px;text-wrap:balance}}
h3{{font:600 18px/1.25 var(--sans);margin:0}}
.lede{{color:var(--mut);max-width:62ch;margin:0;font-size:18px}}
.rule{{color:var(--mut);max-width:70ch;margin:0 0 18px}}
.counts{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}
.counts span{{font:500 13px var(--mono);border:1px solid var(--line);border-radius:99px;padding:6px 12px;background:var(--card)}}
.counts b{{color:var(--accent)}}
.flow{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;counter-reset:f}}
.flow li{{counter-increment:f;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;display:grid;gap:4px;min-width:0}}
.flow li::before{{content:counter(f);font:500 12px var(--mono);color:var(--accent)}}
.flow b{{font-size:17px}} .flow span{{font-size:14px}} .flow em{{font:12px var(--mono);color:var(--mut);font-style:normal}}
.flow li:last-child{{background:var(--accentbg);border-color:var(--accent)}}
.who{{justify-self:start;font:500 11px var(--mono);font-style:normal;letter-spacing:.04em;text-transform:uppercase;color:var(--go);background:var(--gobg);border-radius:99px;padding:3px 8px;margin-top:4px}}
.lvls{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.lvl{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;display:grid;gap:8px;align-content:start;min-width:0}}
.lvl p{{margin:0;font-size:14px}} .lvl p span{{display:block;font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--mut)}}
.beats i{{font:500 11px var(--mono);font-style:normal;color:var(--accent);background:var(--accentbg);border-radius:6px;padding:1px 6px;margin-left:4px;white-space:nowrap}}
.secs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}}
.sec{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;min-width:0}} .sec p{{margin:4px 0 0;font-size:14px}}
.arc>p{{margin:0;font-size:14px}}
.wf{{display:grid;gap:10px}} .wf h3{{font:800 22px/1.2 var(--display)}} .wf code{{font:500 13px var(--mono);color:var(--mut)}}
.bar summary{{cursor:pointer;font-weight:600}} .bar ul{{margin:8px 0 0;padding-left:18px;display:grid;gap:5px;font-size:15px}}
.picker{{display:grid;gap:10px}}
.aw{{display:grid;grid-template-columns:150px 1fr;gap:12px;align-items:start;padding:12px 0;border-top:1px solid var(--line)}}
.aw b{{text-transform:capitalize;font-weight:600;padding-top:4px}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;min-width:0}}
.chip{{font-size:14px;color:var(--fg);text-decoration:none;background:var(--card);border:1px solid var(--line);border-radius:99px;padding:4px 10px}}
.chip:hover,.chip:focus-visible{{border-color:var(--accent);color:var(--accent);outline:none}}
.arcs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:14px}}
.arc{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;display:grid;gap:12px;align-content:start;min-width:0;scroll-margin-top:16px}}
.arc:target{{border-color:var(--accent);box-shadow:0 0 0 3px var(--accentbg)}}
.arc-top{{display:grid;grid-template-columns:120px 1fr;gap:12px;align-items:center}}
.arc-top svg{{width:120px;height:48px;background:var(--accentbg);border-radius:8px}}
.ln{{fill:none;stroke:var(--accent);stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round}}
.mid{{stroke:var(--line);stroke-width:1;stroke-dasharray:3 3}}
.dot{{fill:var(--accent)}}
.shape{{margin:2px 0 0;color:var(--mut);font-size:14px}}
.beats{{margin:0;padding-left:20px;display:grid;gap:3px;font-size:15px}}
.beats li::marker{{color:var(--accent);font-family:var(--mono);font-size:12px}}
dl{{margin:0;display:grid;gap:4px;font-size:14px}}
dt{{font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--mut);margin-top:6px}}
dd{{margin:0}}
.src{{font:12px/1.4 var(--mono);color:var(--mut);margin:0}}
.fams{{display:grid;gap:22px}}
.fam{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
.fam h3{{grid-column:1/-1;font:500 12px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}}
.dev,.trig{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;display:grid;gap:6px;align-content:start;min-width:0}}
.dev p,.trig p{{margin:0;font-size:14px}}
.push span,.line span{{display:block;font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;margin-bottom:2px}}
.push span{{color:var(--go)}} .line span{{color:var(--stop)}}
.trigs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
.pl{{display:grid;gap:8px;padding:8px 0}}
.edge{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}
.side{{border-radius:14px;padding:18px}}
.side ul{{margin:10px 0 0;padding-left:18px;display:grid;gap:6px}}
.go{{background:var(--gobg)}} .go h3{{color:var(--go)}}
.stop{{background:var(--stopbg)}} .stop h3{{color:var(--stop)}}
.rules{{margin:0;padding-left:18px;display:grid;gap:8px;max-width:75ch}}
.foot{{color:var(--mut);font-size:13px}}
@media (max-width:560px){{.aw{{grid-template-columns:1fr;gap:6px}}.arc-top{{grid-template-columns:96px 1fr}}.arc-top svg{{width:96px;height:40px}}}}
@media (prefers-reduced-motion:no-preference){{.chip{{transition:border-color .15s,color .15s}}}}
</style>
<div class="wrap">
<header>
<div class="eye">The standard for every ad</div>
<h1>Story Playbook</h1>
<p class="lede">One flow, the same every time. Each step has its definitions in one place, and every chain reads them from there. Pick the awareness level, the arc follows, the arc gives the sections, and the copy, dials and spice fill them in.</p>
</header>

<section>
<h2>The flow</h2>
<p class="rule">Two doors in, one line out. Door A starts from a swipe (taken apart first). Door B starts from our own story with no swipe: the awareness level and the arc stand in for the swipe\'s structure. From the writing on, both run the same steps.</p>
<ol class="flow">{flow}</ol>
</section>

<section>
<h2>Workflows you start by name</h2>
<p class="rule">Each ad type's own line, station by station, on the components. Every station is a component's own command; the run stops at every sign-off for the person named.</p>
{workflows}
</section>

<section>
<h2>Awareness picks the arc</h2>
<p class="rule">{arc_rule}</p>
<div class="lvls">{aw}</div>
</section>

<section>
<h2>The arcs</h2>
<p class="rule">The line is the story's emotional shape, left to right: down is worse, up is better. Each beat names the section it fills.</p>
<div class="arcs">{arcs}</div>
</section>

<section>
<h2>The sections</h2>
<p class="rule">The job each beat does. Any arc uses some of them, in its own order.</p>
<div class="secs">{sections}</div>
</section>

<section>
<h2>Story devices</h2>
<p class="rule">{device_rule}</p>
<div class="fams">{devices}</div>
</section>

<section>
<h2>Persuasion triggers</h2>
<p class="rule">{trigger_rule}</p>
<div class="trigs">{triggers}</div>
</section>

<section>
<h2>The edge</h2>
<p class="rule">Right up to the line, never over.</p>
{edge}
</section>

<p class="foot">Definitions: the creative controls (arcs, devices, triggers, edge, updated {updated}) and the marketing rulebook (awareness, sections). Every row is a draft until approved.</p>
</div>
"""


def main():
    c = json.loads((COMP / "controls.json").read_text())
    OUT.write_text(page(c))
    MIRROR.parent.mkdir(exist_ok=True)
    MIRROR.write_text(mirror(c))
    print(OUT)
    print(MIRROR)


if __name__ == "__main__":
    main()
