#!/usr/bin/env python3
"""lowpoly.py — a blocky early-2000s console game world, drawn entirely in code. No video model.

The voice track and the beat list go in; a finished 9:16 video comes out. three.js draws the world
(world.js), a HyperFrames page steps it frame by frame, and the game screen (money, health, map,
shop menu, subtitles) sits on top. Same doors as stick.py, whose word timing and pause tightening
it uses.

    python3 lowpoly.py track <run>              lay each read and each silent beat into vo/, in the order of ad.json `timeline`
    python3 lowpoly.py build <run>              write the HyperFrames page under <run>/page/
    python3 lowpoly.py render <run>             render it and mix voice, music and effects into <run>/final.mp4
    python3 lowpoly.py all <run>                build and render

<run> is runs/video-edit/<brand>/<label>/ and holds lines.json, vo/ and ad.json. The beat grammar is
in README.md. No brand is named here: words come from ad.json.
"""
import array
import base64
import json
import math
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stick"))
import stick as S  # noqa: E402

W, H = 1080, 1920
FPS = 30
THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"
RATE = 22050

CSS = """*{margin:0;padding:0;box-sizing:border-box}html,body{width:1080px;height:1920px;background:#000;overflow:hidden}
#root{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:Impact,'Arial Black',sans-serif;color:#fff}
#gl{position:absolute;left:0;top:0;width:1080px;height:1920px;filter:contrast(1.1) saturate(.95) sepia(.14)}
#lb1,#lb2{position:absolute;left:0;right:0;height:210px;background:#000}#lb1{top:0}#lb2{bottom:0}
.o{text-shadow:-3px -3px 0 #000,3px -3px 0 #000,-3px 3px 0 #000,3px 3px 0 #000,0 5px 0 #000}
#money{position:absolute;right:44px;top:252px;font-size:76px;color:#79c15b;letter-spacing:2px}
#clock{position:absolute;right:44px;top:176px;font-size:64px;color:#e8e2d0;letter-spacing:2px}
.bar{position:absolute;right:44px;width:300px;height:30px;background:#000;border:5px solid #000}
.bar i{display:block;height:100%}#hp{top:350px}#hp i{background:#b5271f}
#mapw{position:absolute;left:46px;bottom:300px;width:220px;height:220px;border-radius:50%;background:#2b3a2c;border:7px solid #000;overflow:hidden;opacity:.92}
#menu{position:absolute;left:44px;top:176px;width:640px;background:rgba(10,10,16,.86);border:4px solid #e8e2d0;padding:20px 24px;display:none}
#menu h3{font-size:44px;color:#d6c7a0;font-weight:400;letter-spacing:2px;margin-bottom:12px}
.it{display:flex;justify-content:space-between;font-size:47px;padding:7px 12px;color:#e8e2d0}.it.on{background:#d6c7a0;color:#111}.it b{font-weight:400}
.it.off{color:#6d6a63;text-decoration:line-through}
#sub{position:absolute;left:50px;right:50px;bottom:70px;text-align:center;font-size:54px;line-height:1.08;font-family:Arial,sans-serif;font-weight:700;color:#fff}
#pop{position:absolute;left:0;right:0;top:760px;text-align:center;font-size:118px;color:#e23b2b;display:none;line-height:1}
#end{position:absolute;left:0;right:0;bottom:250px;display:none;flex-direction:column;align-items:center;gap:18px}
#end img{width:520px}#end .n{font-size:128px;color:#fff}#end .l{font-size:60px;color:#79c15b;text-align:center;line-height:1.12;padding:0 50px}
#slot{position:absolute;right:44px;top:398px;background:rgba(10,10,16,.86);border:3px solid #e8e2d0;padding:8px 16px;font-size:36px;color:#e8e2d0}
#cards{position:absolute;left:0;right:0;top:640px;height:560px;display:none}
.cd{position:absolute;left:390px;top:40px;width:300px;height:430px;background:#f1ead8;border:6px solid #111;color:#111;text-align:center;padding-top:60px;font-size:50px;transform-origin:50% 120%}
.cd b{display:block;font-weight:400;font-size:88px;color:#b5271f;margin-top:40px}
#quote{position:absolute;left:80px;right:80px;top:560px;background:#f1ead8;border:6px solid #111;color:#111;font:700 58px/1.18 Georgia,serif;padding:44px;display:none}#quote i{display:block;font:600 36px Arial,sans-serif;margin-top:24px;font-style:normal}
#lab{position:absolute;left:0;right:0;top:300px;text-align:center;font-size:84px;color:#fff;display:none}
#wst{position:absolute;inset:0;display:none;background:radial-gradient(ellipse at center,rgba(0,0,0,.25),rgba(0,0,0,.82));align-items:center;justify-content:center}
#wst b{font:900 150px 'Arial Black',Impact,sans-serif;letter-spacing:-2px;color:#b5231c;text-transform:lowercase;-webkit-text-stroke:3px #2a0605}
#hd{position:absolute;left:60px;right:60px;top:40px;text-align:center;font:400 84px/1.08 Impact,'Arial Black',sans-serif;color:#fff;display:none}
body.skit #lb1,body.skit #lb2{display:none}body.skit #sub{bottom:560px;left:60px;right:60px;font:400 70px/1.1 Impact,'Arial Black',sans-serif;letter-spacing:1px}body.skit #gl{filter:none}body.skit #hd{z-index:5;top:236px;left:70px;right:70px;font:700 62px/1.16 Arial,sans-serif;letter-spacing:0;text-shadow:-3px -3px 0 #000,3px -3px 0 #000,-3px 3px 0 #000,3px 3px 0 #000,0 0 8px #000}body.skit #lab{top:800px;font-size:120px;color:#ffe9a8}body.skit #wst{background:radial-gradient(ellipse at center,rgba(60,0,0,.2),rgba(0,0,0,.72))}body.skit #wst b{font-size:190px}
#spec{position:absolute;left:60px;right:60px;top:1130px;display:none;text-align:center;font:400 62px/1.3 Impact,sans-serif;color:#fff}body.skit #quote{top:430px;left:70px;right:70px;background:#101014;color:#fff;border:5px solid #e8d27a;font:700 62px/1.16 Arial,sans-serif;padding:42px}body.skit #quote i{color:#e8d27a;font-size:36px}#cardt{display:block;font:400 40px Impact,sans-serif;color:#79c15b;letter-spacing:2px;margin-bottom:16px}
#ba{position:absolute;left:0;top:800px;width:1080px;height:1080px;object-fit:cover;display:none}body.skit #quote.up{top:250px}
#stars{position:absolute;right:46px;top:236px;font:400 74px Impact,sans-serif;color:#fff;letter-spacing:6px;display:none}body.skit #pop{top:1000px;font-size:104px}
#sm{position:absolute;left:0;right:0;bottom:18px;text-align:center;font:700 36px Arial,sans-serif;color:#fff;text-shadow:0 2px 4px #000;display:none}"""

JS = r"""const $=i=>document.getElementById(i);const A=window.AD;
const mapSvg=$('mp');
function moneyAt(t){let m=A.money;for(const b of A.beats){if(b.money==null)continue;if(t<b.t)break;const k=Math.min(1,(t-b.t)/.45);m+= (t>=b.t+.45)?b.money:b.money*k}return Math.round(m)}
window.hud=function(t,b,u){
 $('slot').textContent=b.slot||'';$('slot').style.display=(b.slot&&b.scene!=='cross'&&b.scene!=='end')?'block':'none';
 $('cards').style.display=b.cards?'block':'none';[...document.querySelectorAll('.cd')].forEach((e,i)=>{const k=Math.min(1,u*3);e.style.transform='rotate('+((i-1.5)*14*k)+'deg)'});
 $('ba').style.display=b.ba?'block':'none';if(b.ba){const k=(b.ba[0]+Math.floor((t-b.t)/.42))%A.ba.length;$('ba').src=A.ba[k]}$('quote').className=b.ba?'up':'';$('quote').style.display=b.quote?'block':'none';if(b.quote)$('quote').innerHTML='<span id=cardt>REVIEW UNLOCKED</span>'+b.quote;$('spec').style.display=b.spec?'block':'none';if(b.spec){const n=Math.ceil(u*b.spec.length*1.3);$('spec').innerHTML=b.spec.slice(0,n).join('<br>')}
 $('lab').style.display=b.lab?'block':'none';if(b.lab)$('lab').textContent=b.lab;
 $('money').textContent='$'+String(Math.max(0,moneyAt(t))).padStart(8,'0');
 const c=b.scene==='clock'?Math.floor(u*1440*5)%1440:9*60+Math.floor(t*4);
 $('clock').textContent=String(Math.floor(c/60)%24).padStart(2,'0')+':'+String(c%60).padStart(2,'0');
 $('hpi').style.width=Math.max(4,100-(b.bumps||0)/1.75)+'%';
 mapSvg.style.transform='rotate('+(t*9)+'deg)';
 const hide=b.nohud||b.scene==='cross'||b.scene==='end'||b.quote;
 for(const i of ['money','clock','hp','mapw'])$(i).style.opacity=hide?0:1;
 const m=$('menu');m.style.display=b.menu!=null?'block':'none';
 if(b.menu!=null){const sel=Math.min(b.menu,Math.floor(u*A.menu.length*2.2)>=b.menu?b.menu:Math.floor(u*A.menu.length*2.2));
  [...m.querySelectorAll('.it')].forEach((e,i)=>{e.className='it'+(i===sel?' on':'')+((b.spent||0)>i?' off':'')+(i>=(b.show||99)?' hid':'');e.style.display=i>=(b.show||99)?'none':'flex'})}
 const p=$('pop');const pt=t-b.t;if(b.pop&&pt<1.15){p.style.display='block';p.textContent=b.pop;p.style.color=b.popc||'#e23b2b';p.style.transform='scale('+(pt<.12?1.5-pt*4.2:1)+')'}else p.style.display='none';
 $('hd').style.display=(A.head_end&&t<A.head_end)?'block':'none';$('stars').style.display=b.stars?'block':'none';if(b.stars)$('stars').textContent=b.stars;
 const wz=$('wst');wz.style.display=b.wasted?'flex':'none';if(b.wasted){wz.style.opacity=Math.min(1,u*2.2);wz.querySelector('b').textContent=b.wasted}
 const c2=b.scene==='black'?null:A.subs.find(x=>t>=x.t&&t<x.e);const s=$('sub');s.textContent=c2?c2.x:'';s.style.color=c2&&c2.c?c2.c:'#fff';
 const e=$('end');e.style.display=b.scene==='end'?'flex':'none';e.style.opacity=1;
 const sm=A.small.find(x=>t>=x.t&&t<x.e);$('sm').style.display=sm?'block':'none';if(sm)$('sm').textContent=sm.x;
};
const prox={t:0};const tl=gsap.timeline({paused:true});
tl.to(prox,{t:A.dur,duration:A.dur,ease:'none',onUpdate(){draw(prox.t)}},0);
window.ready.then(()=>{draw(0);window.__timelines=window.__timelines||{};window.__timelines['main']=tl;window.RIGGED=1});"""

MAP = """<svg id="mp" viewBox="0 0 220 220" width="220" height="220"><path d="M-20 60 L240 40 M30 -20 L60 240 M-20 170 L240 150 M150 -20 L170 240" stroke="#c9b48a" stroke-width="9" fill="none"/><path d="M60 -20 L130 110 L240 120" stroke="#8d9b86" stroke-width="5" fill="none"/></svg><div style="position:absolute;left:96px;top:92px;width:0;height:0;border-left:13px solid transparent;border-right:13px solid transparent;border-bottom:26px solid #fff"></div>"""


def fit(src, dst, height):
    im = Image.open(src).convert("RGBA")
    im.resize((int(im.width * height / im.height), height), Image.LANCZOS).save(dst)


def mask(text, ad):
    for bad, shown in ad.get("mask", {}).items():
        text = re.sub(bad, shown, text, flags=re.I)
    return text


def subs_of(words, ad):
    voices = ad.get("subtitle_colour", {})
    out = []
    for chunk in S.captions([w for w in words if w["sid"] not in ad.get("no_subs", [])], [], max_chars=int(ad.get("sub_chars", 26))) if words else []:
        out.append({"t": chunk[0]["t"], "e": chunk[-1]["e"] + .08, "x": mask(" ".join(x["w"] for x in chunk), ad), "c": voices.get(chunk[0]["sid"])})
    for a, b in zip(out, out[1:]):
        a["e"] = min(a["e"] + .25, b["t"])
    return out


def track(run):
    """Every read cleaned of its silence and laid in the order of `timeline`, with the silent beats between. The voice sheet gets every beat, so beats are named by id."""
    ad = S.read(run / "ad.json")
    who = {s["id"]: s["speaker"] for s in S.read(run / "plan.json")["scenes"]}
    lines = S.read(run / "lines.json")
    chains = ad.get("voice_chain", {})
    vo = run / "vo"
    vo.mkdir(exist_ok=True)
    t, sheet, parts = 0.0, {}, []
    for row in ad["timeline"]:
        sid = row["id"]
        if sid in lines:
            out = vo / (sid + ".wav")
            chain = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
            if chains.get(who[sid]):
                chain += "," + chains[who[sid]]
            if row.get("max"):
                chain += ",atrim=end=%s,afade=t=out:st=%s:d=0.15" % (row["max"], round(float(row["max"]) - .15, 2))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(run / "voice" / (sid + ".mp3")), "-af", chain, "-ar", "44100", "-ac", "1", str(out)], check=True)
            d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)]))
            lead = float(row.get("lead", .12))
            sheet[sid] = {"start": round(t, 3), "end": round(t + lead + d + float(row.get("pad", .22)), 3),
                          "lines": [{"text": lines[sid], "start": round(t + lead, 3), "end": round(t + lead + d, 3)}]}
            parts.append((out, t + lead))
            t = sheet[sid]["end"]
        else:
            sheet[sid] = {"start": round(t, 3), "end": round(t + float(row["hold"]), 3), "lines": []}
            t = sheet[sid]["end"]
    inputs, fx = [], []
    for n, (p_, at) in enumerate(parts):
        inputs += ["-i", str(p_)]
        fx.append("[%d]adelay=%d|%d[a%d]" % (n, at * 1000, at * 1000, n))
    fx.append("".join("[a%d]" % n for n in range(len(parts))) + "amix=inputs=%d:normalize=0:duration=longest,aformat=sample_fmts=fltp,asetnsamples=n=1152:p=1[o]" % len(parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(fx), "-map", "[o]", "-b:a", "192k", str(vo / "track.mp3")], check=True)
    (vo / "timing.json").write_text(json.dumps({"track": "vo/track.mp3", "scenes": sheet}, indent=1))
    print("track %.1f s" % t)


def spoken_times(run, words):
    """Captions land on the voice itself: script words take the times heard in vo/words.json; a word not heard sits between its neighbours."""
    path = run / "vo" / "words.json"
    if not path.exists():
        return words
    import difflib
    heard = [w for w in S.read(path) if w.get("type", "word") == "word"]
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    script = [norm(w["w"]) for w in words]
    match = difflib.SequenceMatcher(None, script, [norm(h["text"]) for h in heard], autojunk=False)
    got = {}
    for a, b, n in match.get_matching_blocks():
        for k in range(n):
            got[a + k] = heard[b + k]
    out = [dict(w) for w in words]
    for i, w in enumerate(out):
        if i in got:
            w["t"], w["e"] = round(got[i]["start"], 3), round(got[i]["end"], 3)
    return out


def lips_of(run, ad, scenes, dur, key="lip_lines"):
    """One mouth value per frame, read off the voice itself. Only the lines said on camera move his lips."""
    frames = [0.0] * (int(dur * FPS) + 2)
    for sid in ad.get(key, []):
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(run / "vo" / (sid + ".wav")), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"])
        a = array.array("h", raw)
        step = 8000 // FPS
        level = [math.sqrt(sum(x * x for x in a[i:i + step]) / max(1, len(a[i:i + step]))) for i in range(0, len(a), step)]
        top = max(level) or 1.0
        at = int(scenes[sid]["lines"][0]["start"] * FPS)
        for i, v in enumerate(level):
            frames[min(at + i, len(frames) - 1)] = min(1.0, (v / top) ** .7 * 1.15) if v / top > .08 else 0.0
    return [round(max(frames[i], (frames[i - 1] + frames[min(i + 1, len(frames) - 1)]) * .4 if i else 0), 2) for i in range(len(frames))]


def build(run):
    ad = S.read(run / "ad.json")
    words = spoken_times(run, S.words_of(run))
    scenes = S.read(run / "vo" / "timing.json")["scenes"]
    dur = round(list(scenes.values())[-1]["end"], 2)
    beats = []
    for b in ad["beats"]:
        sc = scenes[b.get("of", b["id"])]
        i, n = b.get("part", [0, 1])
        beats.append(dict(b, t=round(sc["start"] + (sc["end"] - sc["start"]) * i / n, 3)))
    for a, b in zip(beats, beats[1:]):
        a["e"] = b["t"]
    beats[-1]["e"] = dur + .1
    page = run / "page"
    (page / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "world.js", page / "world.js")
    shutil.copy(HERE / "gltf-global.js", page / "gltf-global.js")
    if ad.get("lead_glb"):
        text = "window.TRE_GLB='%s';" % base64.b64encode((run / ad["lead_glb"]).read_bytes()).decode()
        text += "window.CLIPS=%s;" % (run / ad["clips_json"]).read_text()
        for name, key in (("FLEX_GLB", "product_glb"), ("DRE_GLB", "second_glb")):
            if ad.get(key):
                text += "window.%s='%s';" % (name, base64.b64encode((run / ad[key]).read_bytes()).decode())
        (page / "tre.js").write_text(text)
    turn = []
    for k, src in enumerate(ad["product_turn"]):
        fit(src, page / "assets" / ("turn%d.png" % k), 560)
        im = Image.open(page / "assets" / ("turn%d.png" % k))
        turn.append({"src": "assets/turn%d.png" % k, "w": round(im.width / im.height / .625, 3)})
    ba = []
    for k, src in enumerate(ad.get("before_after", [])):
        shutil.copy(run / src, page / "assets" / ("ba%d.jpg" % k))
        ba.append("assets/ba%d.jpg" % k)
    small = []
    for s in ad.get("small_print", []):
        small.append({"t": scenes[s["at"]]["start"], "e": scenes[s.get("until", s["at"])]["end"], "x": s["text"]})
    data = {"beats": beats, "dur": dur, "money": ad.get("money", 0), "menu": ad.get("menu", []), "subs": subs_of(words, ad), "small": small,
            "product_turn": turn, "solo": ad.get("solo"), "lips": lips_of(run, ad, scenes, dur), "lipsB": lips_of(run, ad, scenes, dur, "lip_lines_b"), "head_end": scenes[ad["headline_until"]]["end"] if ad.get("headline_until") else 0, "lead_shirt": ad.get("lead_shirt"),
            "skit": ad.get("skit"), "res": ad.get("res"), "ba": ba, "drops": [dict(d, t=round(scenes[d["at"]]["start"] + d.get("off", 0), 3)) for d in ad.get("drops", [])]}
    items = "".join('<div class="it"><span>%s</span><b>%s</b></div>' % (m["name"], m["price"]) for m in ad.get("menu", []))
    e = ad.get("end", {})
    doc = """<!doctype html>
<html><head><meta charset="utf-8"><script src="%s"></script><script src="%s"></script><script src="gltf-global.js"></script><script src="tre.js"></script><style>%s</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="%.2f" data-width="%d" data-height="%d">
<canvas id="gl" width="486" height="864"></canvas><div id="lb1"></div><div id="lb2"></div>
<div id="clock" class="o"></div><div id="money" class="o"></div><div id="hp" class="bar"><i id="hpi"></i></div>
<div id="mapw">%s</div>
<div id="menu"><h3>%s</h3>%s</div>
<div id="slot"></div><div id="lab" class="o"></div>
<div id="cards">%s</div><div id="quote">%s<i>%s</i></div>
<div id="hd" class="o">%s</div><div id="wst"><b></b></div><div id="pop" class="o"></div>
<div id="end"><div class="n o">%s</div><div class="l o">%s</div></div>
<img id="ba" alt=""><div id="stars" class="o"></div><div id="spec" class="o"></div><div id="sub" class="o"></div><div id="sm"></div>
</div>
<script>window.AD=%s</script><script>WORLD_CODE</script><script>%s</script></body></html>
""" % (S.GSAP, THREE, CSS, dur, W, H, MAP, ad.get("menu_title", ""), items,
       "".join('<div class="cd">%s<b>%s</b></div>' % (c["name"], c["reach"]) for c in ad.get("cards", [])), ad.get("quote", ""), ad.get("quote_by", ""), ad.get("headline", ""),
       e.get("name", ""), e.get("line", ""), json.dumps(data), JS)
    (page / "index.html").write_text(doc.replace("WORLD_CODE", (HERE / "world.js").read_text().replace("/*SKIT*/", (HERE / "skit.js").read_text())))
    (page / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}))
    (run / "beats.json").write_text(json.dumps(beats, indent=1))
    print("page written: %d beats, %.1f s" % (len(beats), dur))
    return dur, beats


def tension(path, dur, drop, stop, bpm=112.3):
    """An original tense synth loop that builds to a hard drop and stops dead: minor pulse, rising filter, drums only after the drop."""
    beat = 60.0 / bpm
    root = 58.27
    seq = [1, 1, 1.189, 1, 1.498, 1.335, 1.189, 1.122]
    n = int(dur * RATE)
    a = array.array("h", bytes(2 * n))
    for i in range(n):
        t = i / RATE
        s = 0.0
        if t < stop:
            step = int(t / (beat / 2))
            f = root * seq[step % 8] * (2 if step % 16 > 11 else 1)
            pos = t % (beat / 2)
            rise = min(1, t / max(drop, .1))
            saw = sum(math.sin(2 * math.pi * f * h * t) / h for h in range(1, 3 + int(rise * 6)))
            s += saw * math.exp(-pos * 7) * (.14 + .12 * rise)
            q = t % beat
            if t >= drop:
                s += math.sin(2 * math.pi * (46 + 90 * math.exp(-q * 30)) * q) * math.exp(-q * 7) * .5
                s += math.sin(2 * math.pi * root * .5 * t) * .24
                if int(t / beat) % 2:
                    s += ((math.sin(i * 12.9898) * 43758.5453) % 1 * 2 - 1) * math.exp(-q * 18) * .22
                h = (t + beat / 4) % (beat / 2)
                s += ((math.sin(i * 78.233) * 12543.123) % 1 * 2 - 1) * math.exp(-h * 60) * .07
            elif int(t / beat) % 4 == 3:
                s += math.sin(2 * math.pi * 44 * q) * math.exp(-q * 6) * .15
        a[i] = int(max(-1, min(1, s)) * 30000)
    _save(path, a)


def groove(path, dur, bpm=94):
    """An original slow funk loop, written sample by sample: sub bass, a thin sliding lead, kick, snare and hat."""
    beat = 60.0 / bpm
    bass = [(0, 41.2, 1.5), (1.5, 41.2, .5), (2, 49.0, 1), (3, 55.0, 1), (4, 36.7, 1.5), (5.5, 36.7, .5), (6, 41.2, 2)]
    lead = [(0, 659.3, 1), (1, 587.3, 1), (2, 493.9, 2), (4, 440.0, 1), (5, 493.9, 3)]
    n = int(dur * RATE)
    a = array.array("h", bytes(2 * n))
    for i in range(n):
        t = i / RATE
        bpos = (t / beat) % 8
        s = 0.0
        for st, f, ln in bass:
            if st <= bpos < st + ln:
                p = (bpos - st) * beat
                s += (math.sin(2 * math.pi * f * t) + .5 * math.sin(4 * math.pi * f * t)) * math.exp(-p * 1.2) * .24
        for st, f, ln in lead:
            if st <= bpos < st + ln and int(t / (beat * 8)) % 2:
                vib = 1 + .012 * math.sin(2 * math.pi * 5.2 * t)
                s += math.sin(2 * math.pi * f * vib * t) * .045
        qpos = t % beat
        q = int(t / beat) % 4
        if q in (0, 2):
            s += math.sin(2 * math.pi * (50 + 80 * math.exp(-qpos * 34)) * qpos) * math.exp(-qpos * 8) * .34
        else:
            s += ((math.sin(i * 12.9898) * 43758.5453) % 1 * 2 - 1) * math.exp(-qpos * 22) * .15
        hp = (t + beat / 4) % (beat / 2)
        s += ((math.sin(i * 78.233) * 12543.123) % 1 * 2 - 1) * math.exp(-hp * 70) * .05
        a[i] = int(max(-1, min(1, s)) * 30000)
    _save(path, a)


def _save(path, a):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(a.tobytes())


def effects(path, beats, dur, bleeps=()):
    """A whoosh on every barber swing, a till on every money drop, a blip through every menu, a game chime on a win."""
    n = int(dur * RATE)
    a = [0.0] * n

    def add(start, length, fn):
        s = int(start * RATE)
        for i in range(int(length * RATE)):
            if 0 <= s + i < n:
                a[s + i] += fn(i / RATE, i)
    for x in bleeps:
        add(x["at"], x["to"] - x["at"], lambda t, i: math.sin(2 * math.pi * 1000 * t) * .32)
    for b in beats:
        if b.get("swing"):
            add(b["t"] - .17, .34, lambda t, i: ((math.sin(i * 91.7) * 9631.1) % 1 * 2 - 1) * math.sin(math.pi * t / .34) * .4)
        if b.get("money"):
            add(b["t"], .14, lambda t, i: math.sin(2 * math.pi * 1760 * t) * math.exp(-t * 18) * .25)
            add(b["t"] + .1, .3, lambda t, i: math.sin(2 * math.pi * 2637 * t) * math.exp(-t * 11) * .25)
        if b.get("menu") is not None:
            for k in range(int(b["menu"]) + 1):
                add(b["t"] + k * .16, .06, lambda t, i: (1 if math.sin(2 * math.pi * 880 * t) > 0 else -1) * .09)
        if b.get("thud"):
            add(b["t"], .35, lambda t, i: math.sin(2 * math.pi * (70 + 200 * math.exp(-t * 20)) * t) * math.exp(-t * 7) * .75)
        if b.get("bump"):
            add(b["t"] + .08, .12, lambda t, i: math.sin(2 * math.pi * (300 + 1400 * t) * t) * math.exp(-t * 26) * .5)
        if b.get("chime"):
            for k, f in enumerate((523.3, 659.3, 784.0, 1046.5)):
                add(b["t"] + k * .1, .42, lambda t, i, f=f: (1 if math.sin(2 * math.pi * f * t) > 0 else -1) * math.exp(-t * 6) * .11)
    _save(path, array.array("h", [int(max(-1, min(1, x)) * 30000) for x in a]))


def skit_mix(run, ad, beats, dur):
    """Room tone, every effect on its beat and the music in its pieces, ducked under the voice. Rows: ad.sound and ad.music_cues, timed by beat id."""
    sc = dict(S.read(run / "vo" / "timing.json")["scenes"])
    for b in beats:
        sc.setdefault(b["id"], {"start": b["t"], "end": b["e"]})
    at = lambda row, key="at": sc[row[key]]["start"] + float(row.get("off", 0))
    inputs, fx, names, under = [], [], [], []
    def add(path, chain, loop=False, into=names):
        n = len(inputs) // (4 if False else 1)
        inputs.append((path, loop))
        tag = "s%d" % n
        fx.append("[%d]%s[%s]" % (n + 1, chain, tag))
        into.append(tag)
    for b in ad.get("beds", []):
        t0, t1 = at(b), sc[b["until"]]["end"]
        add(run / "sfx" / (b["file"] + ".mp3"), "atrim=end=%.3f,afade=t=in:d=0.4,afade=t=out:st=%.3f:d=0.3,volume=%s,adelay=%d|%d" % (t1 - t0, t1 - t0 - .3, b.get("vol", .5), t0 * 1000, t0 * 1000), True)
    for m in ad.get("music_cues", []):
        t0, t1 = at(m), sc[m["until"]]["start"] + float(m.get("until_off", 0))
        add(run / "sfx" / (m["file"] + ".mp3"), "atrim=start=%s:end=%.3f,asetpts=PTS-STARTPTS,afade=t=in:d=%s,afade=t=out:st=%.3f:d=%s,volume=%s,adelay=%d|%d" % (m.get("start", 0), float(m.get("start", 0)) + t1 - t0, m.get("in", .05), t1 - t0 - float(m.get("out", .05)), m.get("out", .05), m.get("vol", .4), t0 * 1000, t0 * 1000), False, under)
    ends = {b["id"]: b["e"] for b in beats}
    for x in ad.get("sound", []):
        t0 = max(0, at(x))
        room = ends.get(x["at"], t0 + 9) - t0 + .04
        if room < .08:
            continue
        add(run / "sfx" / (x["file"] + ".mp3"), "atrim=end=%.3f,afade=t=out:st=%.3f:d=0.06,volume=%s,adelay=%d|%d" % (room, room - .06, x.get("vol", .8), t0 * 1000, t0 * 1000))
    mute = "".join(",volume=0:enable='between(t,%s,%s)'" % (x["at"], x["to"]) for x in ad.get("bleeps", []))
    args = ["ffmpeg", "-v", "error", "-y", "-i", str(run / "vo" / "track.mp3")]
    for p_, loop in inputs:
        args += (["-stream_loop", "-1"] if loop else []) + ["-i", str(p_)]
    args += ["-i", str(run / "fx.wav")]
    nfx = len(inputs) + 1
    g = ";".join(fx)
    g += ";[0]volume=1.15" + mute + ",asplit[v][k]"
    g += ";" + "".join("[%s]" % u for u in under) + "amix=inputs=%d:normalize=0:duration=longest[mm]" % len(under)
    g += ";[mm][k]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=260[m]"
    g += ";[v][m]" + "".join("[%s]" % u for u in names) + "[%d]amix=inputs=%d:normalize=0:duration=longest,alimiter=limit=0.95[a]" % (nfx, len(names) + 3)
    out = run / "mix.wav"
    subprocess.run(args + ["-filter_complex", g, "-map", "[a]", "-t", "%.2f" % dur, "-ar", "48000", "-ac", "2", str(out)], check=True)
    return out


def render(run):
    dur, beats = build(run)
    silent = run / "silent.mp4"
    subprocess.run(["npx", "hyperframes", "render", "--fps", str(FPS), "--output", str(silent.resolve())], cwd=str(run / "page"), check=True)
    ad = S.read(run / "ad.json")
    if ad.get("skit"):
        effects(run / "fx.wav", beats, dur, ad.get("bleeps", []))
        mix = skit_mix(run, ad, beats, dur)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(mix), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-t", "%.2f" % dur, str(run / "final.mp4")], check=True)
        return
    if ad.get("music_file"):
        sc = S.read(run / "vo" / "timing.json")["scenes"]
        drop, stop = sc[ad["drop_at"]]["start"], sc[ad["stop_at"]]["start"]
        lead = drop - float(ad["music_drop"])
        chain = ("atrim=start=%.3f,asetpts=PTS-STARTPTS" % -lead) if lead < 0 else ("adelay=%d|%d" % (lead * 1000, lead * 1000))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(run / ad["music_file"]), "-af",
                        chain + ",atrim=end=%.3f,afade=t=out:st=%.3f:d=0.04,apad" % (stop, stop - .04), "-ar", "44100", "-ac", "2", "-t", "%.2f" % dur, str(run / "bed.wav")], check=True)
    elif ad.get("drop_at"):
        sc = S.read(run / "vo" / "timing.json")["scenes"]
        tension(run / "bed.wav", dur, sc[ad["drop_at"]]["start"], sc[ad["stop_at"]]["start"])
    else:
        groove(run / "bed.wav", dur)
    effects(run / "fx.wav", beats, dur, ad.get("bleeps", []))
    mute = "".join(",volume=0:enable='between(t,%s,%s)'" % (x["at"], x["to"]) for x in ad.get("bleeps", []))
    final = run / "final.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(run / "vo" / "track.mp3"), "-i", str(run / "bed.wav"), "-i", str(run / "fx.wav"),
                    "-filter_complex", "[1]volume=1.0" + mute + ",asplit[v][k];[2]volume=%s[m0];[m0][k]sidechaincompress=threshold=0.03:ratio=5:attack=20:release=300[m];[3]volume=0.9[x];[v][m][x]amix=inputs=3:duration=longest:normalize=0,alimiter=limit=0.95[a]" % ad.get("music", "0.42"),
                    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", "%.2f" % dur, str(final)], check=True)
    print("final:", final)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("track", "build", "render", "all"):
        raise SystemExit(__doc__)
    run = Path(sys.argv[2]).resolve()
    cmd = sys.argv[1]
    if cmd == "track":
        track(run)
    if cmd == "build":
        build(run)
    if cmd in ("render", "all"):
        render(run)


if __name__ == "__main__":
    main()
