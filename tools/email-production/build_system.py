#!/usr/bin/env python3
"""The email system as one page — campaigns only, brand to email.

    python3 build_system.py     # -> email-production.html + email-production.md

Shape lives in model.py. Prompts are read off disk.
"""
import html, json, re
from pathlib import Path
import model as M

HERE = Path(__file__).resolve().parent
LANE = HERE          # the build is flat now: prompts/ and email-types.json sit here
STATE = {"built": ("Built", "s-built"), "part": ("Partly", "s-part"),
         "miss": ("To build", "s-miss"), "decide": ("Your call", "s-decide")}
FILL = {"full": "f-full", "thin": "f-thin", "stub": "f-stub", "none": "f-none"}
PROMPTS = [("0","Triage","stage0-triage"),("1","Read","stage1-read"),
 ("2","Spec","stage2-spec"),("2B","Context scout","stage1b-context-scout"),
 ("3","Injection","stage3-injection"),("4","Placement","stage4-placement"),
 ("5","Subject lines","stage5-subjects"),("6","Expansion","stage6-expansion"),
 ("7","Close","stage7-close"),("8","Build","stage8-build"),("9","Brief","stage9-brief")]


def e(s): return html.escape(str(s or ""))
def md(s):  # the models' **bold** and `code`, nothing more
    s = e(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def latest(stem):
    best, bv = None, -1
    for f in (LANE/"prompts").glob(f"{stem}-*.md"):
        m = re.search(r"-v(\d+)-", f.name)
        if m and int(m.group(1)) > bv: best, bv = f, int(m.group(1))
    return best


CSS = """
:root{--bg:#F0EFEB;--card:#FFF;--ink:#16181B;--mut:#61666E;--line:#D8D6D0;--hair:#E8E6E1;
 --root:#2F5D50;--root-bg:#E0EBE7;
 --built:#1D6A4B;--built-bg:#DFEEE7;--part:#8A5A10;--part-bg:#F4EBD8;
 --miss:#4A5568;--miss-bg:#E6E8EC;--decide:#8A3A2E;--decide-bg:#F6E4DF}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#0D0F11;--card:#171A1D;--ink:#E5E8EB;--mut:#8D949C;--line:#262A2F;--hair:#1E2226;
 --root:#6FB3A0;--root-bg:#132320;
 --built:#5FBE94;--built-bg:#0F2520;--part:#D2A24C;--part-bg:#291F12;
 --miss:#9AA5B4;--miss-bg:#1D2126;--decide:#DB8271;--decide-bg:#2A1714}}
:root[data-theme="dark"]{
 --bg:#0D0F11;--card:#171A1D;--ink:#E5E8EB;--mut:#8D949C;--line:#262A2F;--hair:#1E2226;
 --root:#6FB3A0;--root-bg:#132320;
 --built:#5FBE94;--built-bg:#0F2520;--part:#D2A24C;--part-bg:#291F12;
 --miss:#9AA5B4;--miss-bg:#1D2126;--decide:#DB8271;--decide-bg:#2A1714}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:880px;margin:0 auto;padding:54px 22px 92px}
.kick{font:600 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.2em;
 text-transform:uppercase;color:var(--mut)}
h1{font-size:clamp(35px,6.2vw,56px);line-height:1.02;letter-spacing:-.034em;font-weight:800;
 margin:14px 0 0;text-wrap:balance}
.lede{font-size:19px;line-height:1.55;color:var(--mut);max-width:58ch;margin:16px 0 0}
h2{font-size:26px;letter-spacing:-.024em;font-weight:780;margin:0}
section{margin-top:60px}
.sh{border-top:2px solid var(--ink);padding-top:13px;margin-bottom:22px}
.sh h2{margin-top:6px}
.sn{color:var(--mut);max-width:62ch;margin:10px 0 0;font-size:15.5px}

/* the three-step spine */
.spine{display:flex;flex-direction:column;gap:10px;margin-top:30px}
.sp{background:var(--card);border:1px solid var(--line);border-radius:5px;
 padding:18px 21px;display:flex;gap:16px;align-items:baseline}
.sp.r{background:var(--root-bg);border-color:var(--root);border-left:4px solid var(--root)}
.sp .n{font:700 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mut);
 letter-spacing:.14em;text-transform:uppercase;min-width:74px}
.sp.r .n{color:var(--root)}
.sp h3{margin:0;font-size:21px;letter-spacing:-.018em;font-weight:750}
.sp p{margin:5px 0 0;color:var(--mut);font-size:14.5px;max-width:52ch}
.sp .tx{flex:1}
.arw{text-align:center;color:var(--mut);font:600 13px/1 ui-monospace,monospace;margin:-4px 0}

.grp{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:13px;margin-top:6px}
.g{background:var(--card);border:1px solid var(--line);border-radius:5px;padding:17px 19px}
.g h4{margin:0 0 4px;font-size:16px;font-weight:720}
.g .badge{font:600 9.5px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 padding:5px 7px;border-radius:3px;float:right}
.f-full{color:var(--built);background:var(--built-bg)}
.f-thin{color:var(--part);background:var(--part-bg)}
.f-stub{color:var(--decide);background:var(--decide-bg)}
.f-none{color:var(--mut);background:var(--miss-bg)}
.g ul{margin:9px 0 0;padding-left:17px;color:var(--mut);font-size:13.5px}
.g li{margin-bottom:3px}

.fill{background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:8px}
.fr{display:grid;grid-template-columns:110px 1fr 74px 78px;gap:0;align-items:center;
 border-bottom:1px solid var(--hair);padding:9px 16px;font-size:13.5px}
.fr:last-child{border-bottom:0}
.fr .ln{font:600 11px/1 ui-monospace,monospace;color:var(--mut)}
.fr .bn{font:11px/1 ui-monospace,monospace}
.fr .bar{height:6px;background:var(--hair);border-radius:3px;overflow:hidden}
.fr .bar i{display:block;height:100%;border-radius:3px;background:var(--mut)}
.fr.full .bar i{background:var(--built)} .fr.thin .bar i{background:var(--part)}
.fr.stub .bar i{background:var(--decide)}
.fr .by{text-align:right;font:11px/1 ui-monospace,monospace;color:var(--mut);
 font-variant-numeric:tabular-nums}
.note{margin-top:16px;font-size:15px;max-width:62ch;border-left:3px solid var(--part);padding-left:14px}

.dims{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
 background:var(--line);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin:18px 0}
.dims .d{background:var(--card);padding:15px 17px}
.dims .v{font:700 25px/1 ui-monospace,monospace;letter-spacing:-.02em;color:var(--root)}
.dims .k{font:600 10px/1 ui-monospace,monospace;letter-spacing:.13em;text-transform:uppercase;
 color:var(--mut);margin-top:8px}
.dims .s{color:var(--mut);font-size:12.5px;margin-top:6px;line-height:1.45}

.wfs{background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:6px}
.wf{display:grid;grid-template-columns:56px 1fr auto;border-bottom:1px solid var(--hair);align-items:start}
.wf:last-child{border-bottom:0}
.wid{font:700 11px/1 ui-monospace,monospace;color:var(--mut);padding:18px 0 0 18px}
.wc{padding:16px 14px 16px 0}
.wn{font-weight:680;font-size:16.5px}
.wt{color:var(--mut);font-size:14.5px;margin-top:5px;max-width:54ch;line-height:1.55}
.wt b{color:var(--ink)}
.wm{padding:16px 17px 16px 0}
.chip{font:600 9.5px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 padding:6px 8px;border-radius:3px;white-space:nowrap}
.s-built{color:var(--built);background:var(--built-bg)}
.s-part{color:var(--part);background:var(--part-bg)}
.s-miss{color:var(--miss);background:var(--miss-bg)}
.s-decide{color:var(--decide);background:var(--decide-bg)}
code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--hair);
 padding:1px 5px;border-radius:3px}

.wells{display:flex;flex-direction:column;gap:12px;margin-top:8px}
.well{background:var(--card);border:1px solid var(--line);border-radius:5px;padding:20px 22px}
.well.empty{border-left:4px solid var(--decide)}
.well.stocked{border-left:4px solid var(--built)}
.wh{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.wh h4{margin:0;font-size:19px;font-weight:750;letter-spacing:-.015em}
.wh .does{font:600 10px/1 ui-monospace,monospace;letter-spacing:.11em;text-transform:uppercase;
 color:var(--root);background:var(--root-bg);padding:6px 8px;border-radius:3px}
.wh .stk{margin-left:auto;font:600 9.5px/1 ui-monospace,monospace;letter-spacing:.1em;
 text-transform:uppercase;padding:6px 8px;border-radius:3px}
.stocked .stk{color:var(--built);background:var(--built-bg)}
.empty .stk{color:var(--decide);background:var(--decide-bg)}
.well p{margin:10px 0 0;font-size:14.5px;max-width:60ch;line-height:1.55}
.well .src{color:var(--mut)}
.well .det{font:11.5px/1.5 ui-monospace,monospace;color:var(--mut);margin-top:11px;
 background:var(--bg);border-radius:4px;padding:9px 11px}
.well .nt{border-left:2px solid var(--line);padding-left:12px;color:var(--mut);font-size:14px}

.axes{background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:8px}
.ax{display:grid;grid-template-columns:118px 56px 1fr;border-bottom:1px solid var(--hair);
 padding:12px 17px;align-items:baseline;gap:6px}
.ax:last-child{border-bottom:0}
.ax .k{font-weight:670;font-size:15px}
.ax .v{font:700 17px/1 ui-monospace,monospace;color:var(--root);font-variant-numeric:tabular-nums}
.ax .s{color:var(--mut);font-size:13px;line-height:1.5}
.space{margin-top:14px;background:var(--root-bg);border:1px solid var(--root);border-radius:5px;
 padding:16px 19px;font-size:15px}
.space b{font:700 21px/1 ui-monospace,monospace;color:var(--root);letter-spacing:-.02em}

.rules{background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:8px}
.rl{display:grid;grid-template-columns:1fr auto;border-bottom:1px solid var(--hair);
 padding:16px 19px;gap:14px;align-items:start}
.rl:last-child{border-bottom:0}
.rl .n{font-weight:690;font-size:16px}
.rl p{margin:5px 0 0;color:var(--mut);font-size:14.5px;max-width:56ch;line-height:1.55}

.brief{background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:8px}
.bf{display:grid;grid-template-columns:190px 1fr;border-bottom:1px solid var(--hair);padding:11px 18px;gap:12px}
.bf:last-child{border-bottom:0}
.bf .k{font:600 12px/1.4 ui-monospace,monospace;color:var(--ink)}
.bf .v{color:var(--mut);font-size:14px}

.tgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(258px,1fr));gap:11px;margin-top:8px}
.ty{background:var(--card);border:1px solid var(--line);border-radius:5px;padding:15px 17px;
 border-left:3px solid var(--line)}
.ty.new{border-left-color:var(--root)} .ty.rare{border-left-color:var(--part)}
.ty h5{margin:0;font-size:15.5px;font-weight:710;display:flex;align-items:baseline;gap:8px}
.ty .u{font:600 9px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 padding:4px 6px;border-radius:3px;margin-left:auto;white-space:nowrap}
.u-proven{color:var(--mut);background:var(--hair)}
.u-rare{color:var(--part);background:var(--part-bg)}
.u-new{color:var(--root);background:var(--root-bg)}
.ty .w{margin:7px 0 0;font-size:13.5px;color:var(--mut);line-height:1.5}
.ty .nt{margin:9px 0 0;font-size:13px;line-height:1.5;border-left:2px solid var(--hair);padding-left:10px}
.wellhead{display:flex;align-items:baseline;gap:12px;margin:34px 0 6px;
 border-bottom:1px solid var(--line);padding-bottom:9px;flex-wrap:wrap}
.wellhead h3{margin:0;font-size:19px;font-weight:750;letter-spacing:-.015em}
.wellhead .c{font:600 10px/1 ui-monospace,monospace;letter-spacing:.11em;text-transform:uppercase;color:var(--mut)}
.fm{background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:8px}
.fmr{display:grid;grid-template-columns:200px 1fr 82px;border-bottom:1px solid var(--hair);
 padding:12px 17px;gap:12px;align-items:baseline}
.fmr:last-child{border-bottom:0}
.fmr .k{font-weight:670;font-size:14.5px}
.fmr .v{color:var(--mut);font-size:13.5px;line-height:1.5}
.fmr .sd{font:600 9.5px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 color:var(--mut);text-align:right}
.arcbox{background:var(--card);border:1px solid var(--line);border-radius:5px;padding:22px 24px;margin-top:8px}
.roles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1px;
 background:var(--line);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:16px}
.roles .r{background:var(--card);padding:14px 16px}
.roles .rk{font:700 10px/1 ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--root)}
.roles .rn{font:700 20px/1 ui-monospace,monospace;margin-top:9px;font-variant-numeric:tabular-nums}
.roles .rd{color:var(--mut);font-size:13px;margin-top:7px;line-height:1.5}
.chains{margin-top:18px}
.ch{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:11px 0;
 border-bottom:1px solid var(--hair);font:12px/1.4 ui-monospace,monospace}
.ch:last-child{border-bottom:0}
.ch b{background:var(--built-bg);color:var(--built);padding:6px 9px;border-radius:3px;font-weight:700}
.ch b.a{background:var(--miss-bg);color:var(--miss)}
.ch i{font-style:normal;color:var(--mut)}
.ch .w{color:var(--mut);font:13px/1.5 system-ui,sans-serif;flex-basis:100%;margin-top:2px}
.gaps{background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden;margin-top:8px}
.gp{display:grid;grid-template-columns:1fr 96px;border-bottom:1px solid var(--hair);
 padding:17px 20px;gap:14px;align-items:start}
.gp:last-child{border-bottom:0}
.gp .n{font-weight:700;font-size:16.5px;letter-spacing:-.01em}
.gp p{margin:6px 0 0;color:var(--mut);font-size:14.5px;max-width:58ch;line-height:1.55}
.gp .v{font:600 9.5px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
 padding:6px 8px;border-radius:3px;text-align:center;white-space:nowrap}
.v-verified{color:var(--built);background:var(--built-bg)}
.v-indicative{color:var(--part);background:var(--part-bg)}
.v-unverified{color:var(--mut);background:var(--hair)}
.parked{background:var(--card);border:1px solid var(--line);border-radius:5px;padding:20px 22px}
.parked .p{padding:11px 0;border-bottom:1px solid var(--hair)}
.parked .p:last-child{border-bottom:0;padding-bottom:0}
.parked b{font-size:16px} .parked p{margin:4px 0 0;color:var(--mut);font-size:14.5px;max-width:60ch}

.pr{background:var(--card);border:1px solid var(--line);border-radius:5px;margin-bottom:10px;overflow:hidden}
.prh{display:flex;justify-content:space-between;gap:12px;padding:13px 18px;align-items:baseline}
.prh h4{margin:0;font-size:15.5px;font-weight:700}
.prh .fn{font:11px ui-monospace,monospace;color:var(--mut)}
pre{margin:0;max-height:250px;overflow:auto;background:var(--bg);padding:16px 18px;
 white-space:pre-wrap;word-wrap:break-word;border-top:1px solid var(--line);
 font:12.5px/1.6 ui-monospace,monospace;color:var(--mut)}
footer{margin-top:66px;border-top:1px solid var(--line);padding-top:18px;
 font:12px/1.75 ui-monospace,monospace;color:var(--mut)}
:focus-visible{outline:2px solid var(--root);outline-offset:2px}
@media(max-width:620px){.wf{grid-template-columns:48px 1fr}.wm{grid-column:2;padding:0 16px 16px 0}
 .fr{grid-template-columns:92px 1fr 60px}.fr .by{display:none}}
"""


def build():
    B = M.BRAND
    groups = "".join(
        f'<div class="g"><span class="badge {FILL[st]}">{e(st)}</span>'
        f'<h4>{e(t)}</h4><ul>' + "".join(f"<li>{md(i)}</li>" for i in items)
        + "</ul></div>" for t, items, st in B["groups"])

    mxb = max(b for _, _, b, _ in B["fill"]) or 1
    fill = "".join(
        f'<div class="fr {st}"><span class="ln">{e(lane)}</span>'
        f'<span class="bn">{e(name)}</span>'
        f'<span class="bar"><i style="width:{max(2, round(100*b/mxb))}%"></i></span>'
        f'<span class="by">{b:,}</span></div>'
        for lane, name, b, st in B["fill"])

    body = ""
    for s in M.STAGES:
        dims = ""
        if s["dims"]:
            dims = '<div class="dims">' + "".join(
                f'<div class="d"><div class="v">{e(v)}</div><div class="k">{e(k)}</div>'
                f'<div class="s">{e(note)}</div></div>' for k, v, note in s["dims"]) + "</div>"
        rows = "".join(
            f'<div class="wf"><div class="wid">{e(fid)}</div>'
            f'<div class="wc"><div class="wn">{e(n)}</div><div class="wt">{md(w)}</div></div>'
            f'<div class="wm"><span class="chip {STATE[st][1]}">{e(STATE[st][0])}</span></div></div>'
            for fid, n, w, st in s["flows"])
        body += (f'<section><div class="sh"><div class="kick">Step {e(s["key"])}</div>'
                 f'<h2>{e(s["name"])}</h2></div>'
                 f'<p class="sn">{md(s["what"])}</p>'
                 + (f'<p class="note">{md(s["dynamic"])}</p>' if s["dynamic"] else "")
                 + dims + f'<div class="wfs">{rows}</div></section>')

    wells = "".join(
        f'<div class="well {w["stock"]}"><div class="wh"><h4>{e(w["name"])}</h4>'
        f'<span class="does">{e(w["does"])}</span>'
        f'<span class="stk">{"stocked" if w["stock"]=="stocked" else "empty"}</span></div>'
        f'<p>{md(w["what"])}</p>'
        f'<p class="src">{md(w["src"])}</p>'
        f'<div class="det">{e(w["detail"])}</div>'
        f'<p class="nt">{md(w["note"])}</p></div>' for w in M.WELLS)

    treatments = "".join(
        f'<div class="p"><b>{e(n)}</b><p>{e(d)}</p></div>' for n, d in M.TREATMENTS)
    _unused = "".join(
        f'<div class="well {w["stock"] if w["stock"]!="thin" else "empty"}">'
        f'<div class="wh"><h4>{e(w["name"])}</h4>'
        f'<span class="does">{e(w["does"])}</span>'
        f'<span class="stk">{e(w["stock"])}</span></div>'
        f'<p>{md(w["what"])}</p><p class="src">{md(w["src"])}</p>'
        f'<div class="det">{e(w["detail"])}</div>'
        f'</div>' for w in [])

    axes = "".join(f'<div class="ax"><span class="k">{e(k)}</span>'
                   f'<span class="v">{e(v)}</span><span class="s">{e(s)}</span></div>'
                   for k, v, s in M.AXES)

    rules = "".join(f'<div class="rl"><div><div class="n">{e(n)}</div>'
                    f'<p>{md(d)}</p></div>'
                    f'<span class="chip {STATE[st][1]}">{e(STATE[st][0])}</span></div>'
                    for n, d, st in M.RULES)

    brief = "".join(f'<div class="bf"><span class="k">{e(k)}</span>'
                    f'<span class="v">{e(v)}</span></div>' for k, v in M.BRIEF)

    calendar = f'''<section>
  <div class="sh"><div class="kick">Step 1, worked through</div>
    <h2>What an email is for</h2></div>
  <p class="sn">Four wells. Each one does something different to the
  relationship, and the reason to keep them apart is that only one of them
  asks for anything. Email, SMS and subscription are how a community gets
  built &mdash; they remind people you are here, that you care, and that you
  are real. A calendar that only asks is a channel that decays.</p>
  <div class="space" style="margin:0 0 18px">One test settles every email:
  <b>{e(M.CUT_TEST)}</b> There is exactly one answer, which is what stops the
  categories bleeding into each other.</div>
  <div class="wells">{wells}</div>

  <h3 style="margin:38px 0 4px;font-size:19px;letter-spacing:-.015em">Not categories &mdash; treatments</h3>
  <p class="sn" style="margin-bottom:12px">These cut across all five, and
  mistaking them for categories is what caused the overlap. A treatment has no
  material of its own &mdash; that is the tell.</p>
  <div class="parked">{treatments}</div>
</section>

<section>
  <div class="sh"><div class="kick">The space</div><h2>What a slot is picked from</h2></div>
  <p class="sn">Every number below is real &mdash; counted off the brand folder
  and the customer base, not estimated.</p>
  <div class="axes">{axes}</div>
  <div class="space">Crossed, that is <b>517,440</b> distinguishable slots.
  Nobody needs all of them. The point is that <b>running out of things to say
  is not the constraint</b> &mdash; choosing well is.</div>
</section>

<section>
  <div class="sh"><div class="kick">The engine</div><h2>How a month gets composed</h2></div>
  <p class="sn">This is the difference between a dynamic calendar and a list of
  dates someone filled in. Four rules, applied every cycle.</p>
  <div class="rules">{rules}</div>
</section>

<section>
  <div class="sh"><div class="kick">The output</div><h2>What production receives</h2></div>
  <p class="sn">One brief per slot. Fully specified before a word is written
  &mdash; which is what makes the writing stage a mechanical step rather than a
  blank page.</p>
  <div class="brief">{brief}</div>
</section>
'''

    # the type catalogue is the BRAND's knowledge now (moved 2026-08-31); it
    # stopped living flat beside this file, which is why the build broke
    import email as EM
    # --brand shows that brand's own catalogue; without one the page shows the
    # generic seed every brand starts from. No brand is assumed.
    import argparse
    _ap = argparse.ArgumentParser()
    _ap.add_argument("--brand", default=None, help="show this brand's own type catalogue")
    _brand = _ap.parse_known_args()[0].brand
    from paths import calendar_tool
    T = json.loads((EM.catalogue_path(_brand) if _brand
                    else calendar_tool("definitions/send-types.seed.json")).read_text())
    WELLNAME = {"ask":("Promotional","made of our offer"),
                "help":("Educational","made of our expertise"),
                "belong":("Cultural","made of the world outside"),
                "real":("Community","made of our customers"),
                "brand":("Brand","made of us"),
                "affiliate":("Affiliate","made of a partner's offer")}
    types_html = ""
    for wk in ("ask","help","belong","real","brand","affiliate"):
        rows = [x for x in T["types"] if x["well"] == wk]
        nm, does = WELLNAME[wk]
        # a type the brand has never sent carries no `use` — that IS "new"
        cards = "".join(
            f'<div class="ty {x.get("use", "new")}"><h5>{e(x["name"])}'
            f'<span class="u u-{x.get("use", "new")}">{e(x.get("use", "new"))}</span></h5>'
            f'<p class="w">{e(x["what"])}</p>'
            + (f'<p class="nt">{md(x["note"])}</p>' if x.get("note") else "")
            + "</div>" for x in rows)
        unsent = sum(1 for x in rows if x.get("use", "new") != "proven")
        types_html += (f'<div class="wellhead"><h3>{e(nm)}</h3>'
                       f'<span class="c">{e(does)}</span>'
                       f'<span class="c" style="margin-left:auto">{len(rows)} types'
                       + (f' &middot; {unsent} not yet sent' if unsent else '')
                       + '</span></div>'
                       f'<div class="tgrid">{cards}</div>')

    forms = "".join(f'<div class="fmr"><span class="k">{e(f["name"])}</span>'
                    f'<span class="v">{e(f["what"])}</span>'
                    f'<span class="sd">{e(f["sender"])}</span></div>' for f in T["forms"])
    mods = "".join(f'<div class="fmr"><span class="k">{e(x["name"])}</span>'
                   f'<span class="v">{e(x["what"])}</span><span class="sd"></span></div>'
                   for x in T["modifiers"])
    n_new = sum(1 for x in T["types"] if x.get("use", "new") == "new")
    n_rare = sum(1 for x in T["types"] if x.get("use", "new") == "rare")

    gaps = "".join(
        f'<div class="gp"><div><div class="n">{e(n)}</div><p>{e(d)}</p></div>'
        f'<span class="v v-{v}">{e(v)}</span></div>' for n, v, d in M.GAPS)

    A = T["arc"]
    roleroles = "".join(
        f'<div class="r"><div class="rk">{e(k)}</div>'
        f'<div class="rn">{sum(1 for x in T["types"] if x.get("role") == k)}</div>'
        f'<div class="rd">{e(v)}</div></div>' for k, v in A["roles"].items())
    byk = {x["key"]: x for x in T["types"]}
    chains = ""
    for x in T["types"]:
        if not x.get("then"):
            continue
        nxt = " ".join(f'<i>&rarr;</i> <b>{e(byk[n]["name"])}</b>'
                       for n in x["then"] if n in byk)
        cls = " a" if x.get("role") == "asks" else ""
        chains += (f'<div class="ch"><b class="{cls.strip()}">{e(x["name"])}</b> {nxt}'
                   + (f'<span class="w">{e(x["arc_note"])}</span>' if x.get("arc_note") else "")
                   + "</div>")

    arc_section = f'''<section>
  <div class="sh"><div class="kick">The arc</div><h2>Where a type sits, and what follows it</h2></div>
  <p class="sn">{md(A["note"])}</p>
  <div class="arcbox">
    <div class="roles">{roleroles}</div>
    <p class="sn" style="margin-top:20px"><b>{md(A["rule"])}</b></p>
  </div>
  <h3 style="margin:34px 0 4px;font-size:19px;letter-spacing:-.015em">What follows what</h3>
  <p class="sn" style="margin-bottom:8px">Sixteen types name the move that
  should come after them. Red is an ask.</p>
  <div class="arcbox chains">{chains}</div>
</section>

'''

    types_section = f'''<section>
  <div class="sh"><div class="kick">The catalogue</div><h2>Every type of email we could send</h2></div>
  <p class="sn">{len(T["types"])} types across the four wells &mdash;
  <b>{n_new} never sent</b> and <b>{n_rare} sent only a handful of times</b>.
  Marks come from a keyword pass over the 308 sends since January 2025, so
  they are indicative rather than exact: read &ldquo;rare&rdquo; as a prompt to
  look, not a verdict.</p>
  <p class="sn">This is a data file, not a table someone keeps. Adding a type
  is adding a row &mdash; no prompt edit, no code change.</p>
  <p class="sn" style="margin-bottom:0"><b>A type earns its place by being
  distinct under the test, never by filling out a column.</b> A thin category
  is a finding, not a hole to pad.</p>
  {types_html}
</section>

<section>
  <div class="sh"><div class="kick">Called out</div><h2>Where it is thin, and why</h2></div>
  <p class="sn">Gaps are information. Each one is marked by how solid the
  evidence is: <b>verified</b> means measured off disk, <b>indicative</b> means
  read off subject lines and worth confirming, <b>unverified</b> means it
  cannot be answered from what exists yet.</p>
  <div class="gaps">{gaps}</div>
</section>

<section>
  <div class="sh"><div class="kick">Multiplied by</div><h2>Form, and who it comes from</h2></div>
  <p class="sn">A type is <em>what the email is</em>. A form is <em>how it is
  built</em> &mdash; and the form decides the sender, not the other way round.</p>
  <div class="fm">{forms}</div>
  <h3 style="margin:32px 0 4px;font-size:18px;letter-spacing:-.015em">And by these</h3>
  <p class="sn" style="margin-bottom:10px">Not types. Ways the same type
  becomes a different email.</p>
  <div class="fm">{mods}</div>
</section>
'''

    parked = "".join(f'<div class="p"><b>{e(n)}</b><p>{e(d)}</p></div>' for n, d in M.PARKED)
    prompts = "".join(
        f'<div class="pr"><div class="prh"><h4>{e(i)} · {e(n)}</h4>'
        f'<span class="fn">{e(latest(st).name if latest(st) else "—")}</span></div>'
        f'<pre>{e(latest(st).read_text() if latest(st) else "")}</pre></div>'
        for i, n, st in PROMPTS)

    nwf = sum(len(s["flows"]) for s in M.STAGES)
    doc = f"""<title>The Email System</title>
<style>{CSS}</style>
<div class="wrap">
<div class="kick">Content machine &middot; campaigns &middot; the map, not the build</div>
<h1>Brand to Email</h1>
<p class="lede">Three steps and nothing else: read the brand, build a calendar
out of it, produce the email. {nwf} workflows to name before anything gets
built.</p>

<div class="spine">
  <div class="sp r"><span class="n">Root</span><div class="tx">
    <h3>Brand context</h3><p>The folder everything reads and nothing writes.</p></div></div>
  <div class="arw">&darr;</div>
  <div class="sp"><span class="n">Step 1</span><div class="tx">
    <h3>The dynamic calendar</h3><p>What is owed, to whom, and what job it does.</p></div></div>
  <div class="arw">&darr;</div>
  <div class="sp"><span class="n">Step 2</span><div class="tx">
    <h3>Email production</h3><p>One slot in, a finished email out.</p></div></div>
</div>

<section>
  <div class="sh"><div class="kick">The root</div><h2>What the brand folder actually holds</h2></div>
  <p class="sn">{md(B["what"])}</p>
  <p class="sn">{md(B["map"])}</p>
  <div class="grp">{groups}</div>
  <h3 style="margin:34px 0 4px;font-size:18px;letter-spacing:-.015em">How full is it, really</h3>
  <p class="sn" style="margin-bottom:12px">Every file measured, not assumed.</p>
  <div class="fill">{fill}</div>
  <p class="note">{md(B["finding"])}</p>
</section>

{calendar}

{types_section}

{arc_section}

{body}

<section>
  <div class="sh"><div class="kick">Parked, not dropped</div><h2>The rest of it</h2></div>
  <p class="sn">Real, and out of scope until the three steps above are settled.</p>
  <div class="parked">{parked}</div>
</section>

<section>
  <div class="sh"><div class="kick">Step 2, in full</div><h2>The prompts that run today</h2></div>
  <p class="sn">The files as they are on disk.</p>
  {prompts}
</section>

<footer>
  daemn &middot; content-machine &middot; generated from model.py &middot; 27 August 2026<br>
  Scope: campaigns only. Sender identity sits with the email&rsquo;s form, not the brand.
</footer>
</div>"""
    (HERE/"email-production.html").write_text(doc)
    lines = ["# Brand to email — campaigns", "",
             "Three steps: brand context → dynamic calendar → email production.", "",
             "| ID | Workflow | Step | State |", "|---|---|---|---|"]
    for s in M.STAGES:
        for fid, n, w, st in s["flows"]:
            lines.append(f"| {fid} | {n} | {s['name']} | {STATE[st][0]} |")
    lines += ["", "## Parked", ""] + [f"- **{n}** — {d}" for n, d in M.PARKED] + [""]
    (HERE/"email-production.md").write_text("\n".join(lines))
    print(f"email-production.html ({len(doc):,} bytes) · {nwf} workflows")


if __name__ == "__main__":
    build()
