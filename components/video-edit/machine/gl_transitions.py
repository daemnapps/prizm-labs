#!/usr/bin/env python3
"""gl_transitions.py — the GL hand-offs (gl-transitions, MIT; the GLSL lives in
looks/gl-transitions/<id>.glsl, the rows in looks/transitions.json with engine: "gl").
compose.py calls it; nothing else knows about WebGL.

How it draws, and why this way (read from the HyperFrames engine 2026-09-23): the
registry's own shader blocks capture DOM scenes, which a <video> does not survive, and
@hyperframes/shader-transitions only knows its 14 built-in shaders. So the edit draws its
own: one full-frame <canvas> inside #picture (the grade still applies, text stays above),
shown only inside a transition's window, sampling the two pictures directly. At render
time the engine swaps each <video> for an injected <img class="__render_frame__"> and
then calls window.__hfReseekGpu(t) — the canvas redraws there, so it reads the frame the
engine just injected; in a browser preview it reads the <video> itself. A transition is
centred on the cut: the outgoing picture runs on past it and the incoming one starts
before it, each from a muted HELPER copy of its clip laid under the picture (so no
picture's timing on the sheet changes). Deterministic: every frame is drawn from t alone.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent

HEAD = """precision highp float;
varying vec2 _uv;
uniform sampler2D _from, _to;
uniform float progress, ratio, _fromR, _toR;
vec2 _cover(vec2 uv, float r){ vec2 s = r > 1.0 ? vec2(1.0 / r, 1.0) : vec2(1.0, r); return (uv - 0.5) * s + 0.5; }
vec4 getFromColor(vec2 uv){ return texture2D(_from, _cover(uv, _fromR)); }
vec4 getToColor(vec2 uv){ return texture2D(_to, _cover(uv, _toR)); }
"""
MAIN = "\nvoid main(){ gl_FragColor = transition(_uv); }\n"


def fragment(glsl_path: Path) -> str:
    """The gl-transitions source as a WebGL1 fragment shader: `uniform T name; // = v`
    becomes a constant with that default (a float literal gets its .0)."""
    body = []
    for line in glsl_path.read_text().splitlines():
        m = re.match(r"\s*uniform\s+(\w+)\s+(\w+)\s*;\s*//\s*=\s*(.+?)\s*$", line)
        if m:
            typ, name, val = m.groups()
            if typ == "float" and re.fullmatch(r"-?\d+", val):
                val += ".0"
            body.append(f"const {typ} {name} = {val};")
        else:
            body.append(line)
    return HEAD + "\n".join(body) + MAIN


def _probe(p: Path) -> float | None:
    import subprocess
    try:
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                    capture_output=True, text=True, check=True).stdout.strip())
    except Exception:
        return None


def cut(r: dict, row: dict, T: float, outs: list[dict], ins: list[dict], media_ids: dict, spans: dict) -> dict | None:
    """One GL hand-off at T: which pictures it samples and its window, centred on the cut."""
    if not outs or not ins:
        return None
    top = lambda xs: sorted(xs, key=lambda c: 0 if c.get("roll") == "b" else 1)[0]  # noqa: E731 — the picture on top is the one you see
    o, i = top(outs), top(ins)
    if o["id"] not in media_ids or i["id"] not in media_ids:
        return None
    d = float(row.get("seconds") or 0.5)
    half = min(d / 2, o["duration"] / 2, i["duration"] / 2)
    return {"id": row["id"], "T": T, "t0": round(T - half, 3), "t1": round(T + half, 3), "half": half,
            "glsl": row["glsl"], "out": o, "in": i, "out_media": media_ids[o["id"]], "in_media": media_ids[i["id"]]}


def build(cuts: list[dict], W: int, H: int, uid, media_el, sheet: dict) -> tuple[list[str], str]:
    """The helper media (laid under the pictures) and the script that draws every GL cut."""
    pics, data, progs = [], [], {}
    for n, g in enumerate(cuts):
        om, im = g["out_media"], g["in_media"]
        # the outgoing picture running on past the cut
        o_ss = float(om["source_start"]) + g["out"]["duration"]
        have = _probe(om["path"]) if not str(om["src"]).lower().endswith((".png", ".jpg", ".jpeg", ".webp")) else None
        if have is not None and o_ss + g["half"] > have - 0.05:
            o_ss = max(0.0, have - g["half"] - 0.05)
        oh = uid(f"glh-{g['id']}-{n}-out")
        pics.append(f'<div class="cam glh" style="z-index:0">{media_el(oh, om["src"], g["T"], g["half"], 0, "pic", round(o_ss, 3), None)}</div>')
        # the incoming picture starting before it
        i_ss = max(0.0, float(im["source_start"]) - g["half"])
        ih = uid(f"glh-{g['id']}-{n}-in")
        pics.append(f'<div class="cam glh" style="z-index:0">{media_el(ih, im["src"], g["t0"], g["half"], 0, "pic", round(i_ss, 3), None)}</div>')
        if g["id"] not in progs:
            progs[g["id"]] = fragment(TOOL / g["glsl"])
        data.append({"id": g["id"], "T": g["T"], "t0": g["t0"], "t1": g["t1"], "from": [om["el"], oh], "to": [ih, im["el"]]})
    pics.append(f'<canvas id="gltx" width="{W}" height="{H}" style="position:absolute;inset:0;width:100%;height:100%;z-index:14;visibility:hidden;pointer-events:none"></canvas>')
    script = GL_JS.replace("__CUTS__", json.dumps(data)).replace("__PROGS__", json.dumps(progs)).replace("__W__", str(W)).replace("__H__", str(H))
    return pics, script


# one hook for everything drawn per frame (GL cuts, confetti): the timeline's onUpdate, and
# the engine's post-injection re-seek (so a GL cut reads the frame just injected)
HOOK = r"""
window.__editDraws = window.__editDraws || [];
(function(){
  function run(t){ for (const f of window.__editDraws) { try { f(t); } catch (e) { console.error(e); } } }
  function wrap(){ const p = window.__hfReseekGpu; if (p && !p.__edit) { const w = function(t){ p(t); run(Math.max(0, +t || 0)); }; w.__edit = true; window.__hfReseekGpu = w; } }
  tl.eventCallback("onUpdate", function(){ wrap(); run(tl.time()); });
  wrap(); run(0);
})();
"""

GL_JS = r"""
(function(){
  const CUTS = __CUTS__, PROGS = __PROGS__, W = __W__, H = __H__;
  const cv = document.getElementById("gltx");
  const gl = cv && cv.getContext("webgl", { preserveDrawingBuffer: true, premultipliedAlpha: false });
  window.__editDraws = window.__editDraws || [];
  if (!gl) { console.warn("GL transitions: no WebGL — hard cuts instead"); return; }
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
  const vs = "attribute vec2 p; varying vec2 _uv; void main(){ _uv = p * 0.5 + 0.5; gl_Position = vec4(p, 0.0, 1.0); }";
  function sh(src, type){ const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) console.error("GL transition shader:", gl.getShaderInfoLog(s)); return s; }
  const P = {};
  for (const id in PROGS) { const pr = gl.createProgram(); gl.attachShader(pr, sh(vs, gl.VERTEX_SHADER)); gl.attachShader(pr, sh(PROGS[id], gl.FRAGMENT_SHADER)); gl.linkProgram(pr); P[id] = pr; }
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
  function tex(){ const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t); for (const k of [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T]) gl.texParameteri(gl.TEXTURE_2D, k, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR); return t; }
  const T0 = tex(), T1 = tex();
  function source(id){  // the frame the engine injected beside the <video>, else the element itself
    const el = document.getElementById(id); if (!el) return null;
    const s = el.nextElementSibling;
    if (s && s.classList && s.classList.contains("__render_frame__") && s.complete && s.naturalWidth) return s;
    if (el.tagName === "VIDEO") return el.readyState >= 2 ? el : null;
    return el.complete && el.naturalWidth ? el : null;
  }
  const dims = s => s.tagName === "VIDEO" ? [s.videoWidth, s.videoHeight] : [s.naturalWidth, s.naturalHeight];
  const ease = x => x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
  function draw(t){
    const g = CUTS.find(c => t >= c.t0 && t < c.t1);
    if (!g) { cv.style.visibility = "hidden"; return; }
    const before = t < g.T;
    const a = source(before ? g.from[0] : g.from[1]), b = source(before ? g.to[0] : g.to[1]);
    if (!a || !b) { cv.style.visibility = "hidden"; return; }
    const pr = P[g.id]; gl.useProgram(pr); gl.viewport(0, 0, W, H);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, T0); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, a);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, T1); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, b);
    gl.uniform1i(gl.getUniformLocation(pr, "_from"), 0); gl.uniform1i(gl.getUniformLocation(pr, "_to"), 1);
    const [aw, ah] = dims(a), [bw, bh] = dims(b), cr = W / H;
    gl.uniform1f(gl.getUniformLocation(pr, "_fromR"), (aw / ah) / cr); gl.uniform1f(gl.getUniformLocation(pr, "_toR"), (bw / bh) / cr);
    gl.uniform1f(gl.getUniformLocation(pr, "ratio"), cr);
    gl.uniform1f(gl.getUniformLocation(pr, "progress"), ease(Math.min(1, Math.max(0, (t - g.t0) / (g.t1 - g.t0)))));
    const loc = gl.getAttribLocation(pr, "p"); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    cv.style.visibility = "visible";
  }
  window.__editDraws.push(draw);
})();
"""
