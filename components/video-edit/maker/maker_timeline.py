#!/usr/bin/env python3
"""The editor's timeline page for a maker pack: TIMELINE.html in the hand-off folder, built every time it is packed.

Rule (owner, 16 Nov 2026): "editors work on timelines, not instruction lists." The page lays the ad out on its clock:
the picture track (each scene at its seconds, the swipe frame it copies, made / to make), the words track, the
on-screen text track and the voice track. Tap a block for its clip: the exact recipe, every swipe frame, the name to
return it under. One self-contained file (frames embedded), so it opens from the folder, the Drive or a phone.

    python3 maker_timeline.py <hand-off folder>        (maker_pack.py calls it by itself)
"""
import base64
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def _secs(src):
    """'0:29.4 - 0:31.0 · S · …' -> (29.4, 31.0), or None."""
    m = re.match(r"\s*(\d+):(\d+(?:\.\d+)?)\s*-\s*(\d+):(\d+(?:\.\d+)?)", src or "")
    if not m:
        return None
    a, b = int(m[1]) * 60 + float(m[2]), int(m[3]) * 60 + float(m[4])
    return (a, b) if b > a else None


def _thumb(p, width=220):
    """A small JPEG of one frame as a data URI (sips on a Mac; the frame as it is elsewhere)."""
    p = Path(p)
    try:
        with tempfile.TemporaryDirectory() as t:
            o = Path(t) / "t.jpg"
            r = subprocess.run(["sips", "-Z", str(width), "-s", "format", "jpeg", str(p), "--out", str(o)],
                               capture_output=True, timeout=30)
            data = o.read_bytes() if r.returncode == 0 and o.exists() else p.read_bytes()
    except (OSError, subprocess.SubprocessError):
        data = p.read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def build(folder):
    folder = Path(folder)
    doc = json.loads((folder / "clips.json").read_text())
    clips = {c["id"]: c for c in doc["clips"]}
    t, rows = 0.0, []
    for s in doc["scenes"]:
        span = _secs(s.get("swipe"))
        dur = s.get("secs") or (round(span[1] - span[0], 2) if span else 2.0)   # the pack's length: swipe, voice, captions
        cl = [clips[c] for c in s.get("clips") or [] if c in clips]
        pics = []
        for c in cl:
            for r in c.get("refs") or []:
                if r.endswith("-mid.jpg") and (folder / r).exists():
                    pics.append(_thumb(folder / r))
        if not pics:
            for c in cl:
                for r in (c.get("refs") or [])[:1]:
                    if (folder / r).exists():
                        pics.append(_thumb(folder / r))
        rows.append({"n": s["n"], "scene": s["scene"], "section": s.get("section") or "", "start": round(t, 2), "dur": dur,
                     "words": s.get("words") or "", "on_screen": s.get("on_screen") or "", "voice": s.get("voice"),
                     "made": s.get("file"), "pics": pics[:4],
                     "clips": [{"id": c["id"], "recipe": c.get("recipe") or "", "return": c.get("return"),
                                "swipe": c.get("swipe") or [], "our_cut": c.get("our_cut"),
                                "same": c.get("same_people_as"), "continues": c.get("continues"),
                                "how": c.get("make"), "hold": c.get("hold"), "secs": c.get("secs"),
                                "frames": [_thumb(folder / r, 360) for r in c.get("refs") or [] if (folder / r).exists()]}
                               for c in cl]})
        t += dur
    data = {"key": doc["key"], "title": doc.get("title"), "total": round(t, 1), "rows": rows,
            "nclips": len(doc["clips"]), "made": sum(1 for r in rows if r["made"])}
    page = PAGE.replace("__TITLE__", html.escape(doc["key"])).replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    (folder / "TIMELINE.html").write_text(page)
    return folder / "TIMELINE.html"


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · timeline</title>
<style>
:root{--bg:#f6f6f4;--panel:#fff;--ink:#18181b;--dim:#71717a;--line:#e4e4e7;--make:#c2410c;--makebg:#fff4ec;--made:#15803d;--madebg:#ecfdf3;--accent:#18181b}
@media (prefers-color-scheme:dark){:root{--bg:#0f0f10;--panel:#18181b;--ink:#f4f4f5;--dim:#a1a1aa;--line:#2e2e33;--makebg:#2a1a10;--madebg:#0f2418;--accent:#f4f4f5}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,system-ui,sans-serif}
header{padding:16px;border-bottom:1px solid var(--line);background:var(--panel)}
h1{margin:0;font-size:18px}.sub{color:var(--dim);margin-top:4px}
.chips{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}.chip{padding:3px 10px;border-radius:99px;font-size:12px;font-weight:600}
.chip.make{background:var(--makebg);color:var(--make)}.chip.made{background:var(--madebg);color:var(--made)}.chip.all{background:var(--line)}
.wrap{overflow-x:auto;padding:12px 16px 4px;-webkit-overflow-scrolling:touch}
.tl{position:relative}.ruler{position:relative;height:20px;color:var(--dim);font-size:11px}
.ruler span{position:absolute;top:0;border-left:1px solid var(--line);padding-left:3px;height:20px}
.track{position:relative;margin-bottom:6px}.lab{position:sticky;left:0;font-size:11px;font-weight:700;color:var(--dim);text-transform:uppercase;letter-spacing:.04em;margin:8px 0 4px}
.blk{position:absolute;top:0;bottom:0;border-radius:8px;overflow:hidden;cursor:pointer;border:2px solid transparent}
.pic .blk{background:var(--makebg);border-color:var(--make)}.pic .blk.made{background:var(--madebg);border-color:var(--made)}
.pic .blk img{width:100%;height:100%;object-fit:cover;display:block;opacity:.92}
.pic .blk .tag{position:absolute;left:4px;top:4px;font-size:10px;font-weight:700;background:rgba(0,0,0,.65);color:#fff;padding:1px 5px;border-radius:4px}
.pic .blk .st{position:absolute;left:4px;bottom:4px;font-size:10px;font-weight:700;padding:1px 5px;border-radius:4px;color:#fff;background:var(--make)}
.pic .blk.made .st{background:var(--made)}
.txt .blk{background:var(--panel);border:1px solid var(--line);padding:4px 6px;font-size:11px;line-height:1.3;cursor:pointer}
.voice .blk{background:#3f3f46;color:#fff}
.blk.sel{outline:3px solid var(--accent);outline-offset:1px}
#detail{margin:12px 16px 40px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
#detail h2{margin:0 0 4px;font-size:16px}.k{color:var(--dim);font-size:12px}
.clip{border-top:1px solid var(--line);margin-top:14px;padding-top:12px}
.clip h3{margin:0 0 6px;font-size:14px}.ret{display:inline-block;font:600 12px ui-monospace,monospace;background:var(--makebg);color:var(--make);padding:2px 8px;border-radius:6px}
.frames{display:flex;gap:6px;overflow-x:auto;margin:8px 0}.frames img{height:160px;border-radius:6px}
.recipe{white-space:pre-wrap;font-size:13px;background:var(--bg);border-radius:8px;padding:10px;max-height:260px;overflow:auto}
.sw{font-size:12px;color:var(--dim);margin:2px 0}
</style></head><body>
<header><h1 id="t"></h1><div class="sub" id="s"></div><div class="chips" id="c"></div></header>
<div class="wrap"><div class="tl" id="tl"></div></div>
<div id="detail"><div class="k">Tap any block on the timeline for its clip: the recipe, the swipe frames, the name to return it under.</div></div>
<script>
const D=__DATA__, PX=Math.max(46, Math.min(90, (innerWidth-40)/Math.max(D.total,1)*2.2));
const $=id=>document.getElementById(id), el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
$('t').textContent=D.title+' · '+D.key;
$('s').textContent=D.total+' s · '+D.rows.length+' scenes · cut it in this order, the clips you make go where the orange blocks are';
[['all',D.rows.length+' scenes'],['make',D.nclips+' clips to make'],['made',D.made+' made']].forEach(([k,v])=>$('c').append(el('span','chip '+k,v)));
const W=D.total*PX, tl=$('tl'); tl.style.width=W+'px';
const ru=el('div','ruler'); for(let s=0;s<=D.total;s+=2){const m=el('span',null,s+'s');m.style.left=s*PX+'px';ru.append(m)} tl.append(ru);
function track(name,cls,h,fill){tl.append(el('div','lab',name));const tr=el('div','track '+cls);tr.style.height=h+'px';tr.style.width=W+'px';
  D.rows.forEach((r,i)=>{const b=fill(r);if(!b)return;b.style.left=r.start*PX+1+'px';b.style.width=Math.max(r.dur*PX-2,24)+'px';b.dataset.i=i;b.onclick=()=>show(i);tr.append(b)});tl.append(tr)}
track('Picture','pic',150,r=>{const b=el('div','blk'+(r.made?' made':''));if(r.pics[0]){const im=el('img');im.src=r.pics[0];b.append(im)}
  b.append(el('div','tag',r.n+' · '+r.scene)); b.append(el('div','st',r.made?'made':'make '+r.clips.length)); return b});
track('Words','txt',58,r=>r.words?el('div','blk',r.words):null);
track('On screen','txt',58,r=>r.on_screen?el('div','blk',r.on_screen.replace(/\n/g,' / ')):null);
track('Voice','txt voice',26,r=>r.voice?el('div','blk','voice · '+r.voice.split('/').pop()):null);
function show(i){document.querySelectorAll('.blk').forEach(b=>b.classList.toggle('sel',b.dataset.i==i));const r=D.rows[i],d=$('detail');d.replaceChildren();
  d.append(el('h2',null,r.n+' · '+r.scene+' · '+r.section));d.append(el('div','k',r.start.toFixed(1)+'–'+(r.start+r.dur).toFixed(1)+' s'+(r.voice?' · voice: '+r.voice:'')));
  if(r.words)d.append(el('p',null,'Words: '+r.words)); if(r.on_screen)d.append(el('p',null,'On screen: '+r.on_screen.replace(/\n/g,' / ')));
  if(r.made)d.append(el('p',null,'Made: '+r.made+' (use as it is)'));
  r.clips.forEach(c=>{const x=el('div','clip');x.append(el('h3',null,c.id));x.append(el('span','ret','return → '+c.return));
    if(c.frames.length){const f=el('div','frames');c.frames.forEach(s=>{const im=el('img');im.src=s;f.append(im)});x.append(f)}
    c.swipe.forEach(s=>x.append(el('div','sw','Swipe '+s.k+' ('+(s.seconds||0).toFixed(2)+' s): '+(s.does||'')+(s.text?' · text: '+s.text:''))));
    if(c.same)x.append(el('div','sw','Same people and place as '+c.same)); if(c.continues)x.append(el('div','sw','Picks up where '+c.continues+' ends'));
    if(c.our_cut)x.append(el('div','sw','Our cut for timing only (do not use): '+c.our_cut));
    if(c.hold)x.append(el('p',null,'HOLD: '+c.hold)); if(c.how)x.append(el('p',null,'How: '+c.how)); if(c.secs)x.append(el('div','sw','Length: '+c.secs.toFixed(1)+' s'));
    x.append(el('div','recipe',c.recipe||'No recipe written: remake the swipe moment with our person and our product.'));d.append(x)});
  d.scrollIntoView({behavior:'smooth',block:'start'})}
show(0);
</script></body></html>
"""

if __name__ == "__main__":
    print(build(sys.argv[1]))
