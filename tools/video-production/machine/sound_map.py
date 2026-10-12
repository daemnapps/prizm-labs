#!/usr/bin/env python3
"""The sound map — how every voice attaches to the clips, per section, for any ad.

    python3 sound_map.py <run> [--media media.json]

Reads <run>/clips/plan.json + <run>/storyboard.json and writes
  <run>/clips/sound-map.html  — a page section (time bars per section: picture · voice in the
                                clip · own track), ready to drop into the ad's page
  <run>/clips/SOUND-MAP.md    — the same, as a table, for the team
Three kinds of sound (the owner, 3 Oct 2026: "show me how audio is attached to certain clips"):
  voice in the clip — said on camera, lip-synced, swapped to the cloned voice; moves with the clip
  own track         — off-camera voice in the cloned voice, laid in at the edit
  sounds            — "mm-hmm", "um": never in a clip; the person nods; laid in at the edit
"""
import argparse, html, json, os, sys
from pathlib import Path

e = html.escape


def nm(pid):
    return str(pid or "someone").title()


def build(run: Path, M: "dict | None" = None):
    M = M or {}
    p = json.loads((run / "clips" / "plan.json").read_text())
    sb = json.loads((run / "storyboard.json").read_text())
    bysec, tts = {}, {}
    for c in p["calls"]:
        bysec.setdefault(c["section_id"], []).append(c)
    for t in p["tts"]:
        sid = next((g["id"] for g in sb["sections"] if t["scene"] in g["scenes"]), None)
        tts.setdefault(sid, []).append(t)
    md = ["# Sound map", "", "How every voice attaches to the clips. **In clip** = said on camera, lip-synced, "
          "swapped to the cloned voice, moves with the clip · **Own track** = off-camera voice, laid in at the edit · "
          "**Sound** = mm-hmm/um, never in a clip: the person nods, the sound is laid in at the edit.", "",
          "| Section | Who | Line | Kind | Where |", "|---|---|---|---|---|"]
    def blk(a, z, g0, gl, cls, label, tip):
        l = max(0, (a - g0) / gl * 100); w = max(2.5, (z - a) / gl * 100)
        w = min(w, 100 - l)
        return f"<div class='ab {cls}' style='left:{l:.2f}%;width:{w:.2f}%' title='{e(tip)}'><span>{e(label)}</span></div>"


    rows = []; counts = {"in": 0, "own": 0, "snd": 0}
    for i, g in enumerate(sb["sections"], 1):
        gid = g["id"]; clips = bysec.get(gid, []); tl = tts.get(gid, [])
        lines_in = [(c, l) for c in clips for l in c["lines"] if l.get("on_camera")]
        nods = [(c, l) for c in clips for l in c["lines"] if l.get("sound") and l.get("nod")]
        if not (lines_in or tl):
            continue
        g0 = float(g.get("starts") or 0); gl = float(g.get("seconds") or 1)
        lane_clip = "".join(blk(c["at"], c["at"] + c["seconds"], g0, gl, "abc" + (" cut" if c.get("clip_is") == "cutaway" else ""),
                                c["id"], f"{c['id']} · {c['seconds']} s") for c in clips) or \
            f"<div class='ab abp' style='left:0;width:100%'><span>{'same clip as an earlier section' if g.get('reuses') else 'still picture'}</span></div>"
        lane_in = "".join(blk(c["at"] + l["at"], c["at"] + l["until"], g0, gl, "abi", nm(l["speaker"]),
                              f"{nm(l['speaker'])}: {l['text']}") for c, l in lines_in)
        lane_own = "".join(blk(t["at"], t["at"] + max(0.6, float(t.get("seconds") or 1)), g0, gl, "abs" if t.get("sound") else "abo",
                               nm(t["speaker"]) + (" · sound" if t.get("sound") else ""),
                               f"{nm(t['speaker'])}: {t['text']}") for t in tl)
        items = []
        for c, l in lines_in:
            counts["in"] += 1
            items.append(f"<li><i class='dot abi'></i><b>{nm(l['speaker'])}</b> “{e(l['text'])}” "
                         f"<span class='soft'>inside clip {e(c['id'])} · lips move · moves with the clip</span></li>")
        for t in tl:
            k = "snd" if t.get("sound") else "own"; counts[k] += 1
            nod = next((c["id"] for c, l in nods if l["scene"] == t["scene"]), None)
            how = (f"own track · {nm(t['speaker'])} nods in {nod}, lips closed" if nod else "own track · laid in at the edit") \
                if t.get("sound") else "own track · nobody's lips move · laid in at the edit"
            play = f" <audio controls preload='none' src='{M[k2]}'></audio>" if (k2 := 'tts-' + os.path.basename(t['out'])[:-4]) in M else ""
            items.append(f"<li><i class='dot {'abs' if t.get('sound') else 'abo'}'></i><b>{nm(t['speaker'])}</b> "
                         f"“{e(t['text'])}” <span class='soft'>{how}</span>{play}</li>")
        rows.append(f"""<div class='am'><div class='amh'><span class='sn'>{i}</span><b>{e(g.get('setting', '').title())}</b>
    <span class='soft'>{gl:.1f} s</span></div>
    <div class='amlanes'><div class='amln'><em>Picture</em><div class='amtr'>{lane_clip}</div></div>
    <div class='amln'><em>Voice in the clip</em><div class='amtr'>{lane_in}</div></div>
    <div class='amln'><em>Own track</em><div class='amtr'>{lane_own}</div></div></div>
    <ul class='aml'>{''.join(items)}</ul></div>""")

    sec = f"""<section class='card' id='audiomap'><div class='eyebrow'>How the sound attaches · every section</div>
    <h2>Which voice is inside a clip, and which sits on its own track</h2>
    <div class='key3'>
    <div><i class='dot abi'></i><b>Voice in the clip</b> · {counts['in']} lines<br><span class='soft'>The person is talking on screen. Omni says the line so the lips match, then the voice is swapped for the person's cloned voice. It is baked into that clip: move the clip, the voice moves with it.</span></div>
    <div><i class='dot abo'></i><b>Own track</b> · {counts['own']} lines<br><span class='soft'>The speaker isn't talking on screen (their hands, someone else's face, a phone shot). Made in their cloned voice and laid in at the edit at that time. Nobody's lips move in the clip.</span></div>
    <div><i class='dot abs'></i><b>Sounds</b> · {counts['snd']}<br><span class='soft'>“Mm-hmm”, “um”: never inside a clip. The person just nods, lips closed. The sound is made in their cloned voice and laid in at the edit.</span></div>
    </div>
    <p class='soft'>Bars are drawn to time inside each section. Hover a bar to read the line.</p>
    <div class='ams'>{''.join(rows)}</div></section>
    <style>.key3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:10px 0}}
    .dot{{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
    .abi{{background:#2f9e6e}}.abo{{background:#3b6fd6}}.abs{{background:#d99a1e}}.abc{{background:var(--ink)}}.abc.cut{{background:#6b6b78}}.abp{{background:#9a9aa6}}
    .ams{{display:flex;flex-direction:column;gap:10px}}.am{{border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:8px;min-width:0}}
    .amh{{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}}
    .amlanes{{display:flex;flex-direction:column;gap:4px}}.amln{{display:grid;grid-template-columns:120px minmax(0,1fr);justify-items:stretch;text-align:left;gap:8px;align-items:center}}
    .amln em{{font-style:normal;font-size:.72rem;color:var(--soft);text-transform:uppercase;letter-spacing:.04em}}
    .amtr{{width:100%;position:relative;height:24px;background:color-mix(in srgb,var(--line) 45%,transparent);border-radius:5px;min-width:0}}
    .ab{{position:absolute;top:2px;bottom:2px;border-radius:4px;overflow:hidden;color:#fff;font-size:.68rem;display:flex;align-items:center;padding:0 5px;box-sizing:border-box}}
    .ab span{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.abc span{{color:var(--p)}}
    .aml{{margin:0;padding-left:4px;list-style:none;font-size:.85rem;display:flex;flex-direction:column;gap:5px}}.aml audio{{height:28px;vertical-align:middle;max-width:220px}}
    @media (max-width:560px){{.amln{{grid-template-columns:1fr}}}}</style>
    """
    for i, g in enumerate(sb["sections"], 1):
        for c in bysec.get(g["id"], []):
            for l in c["lines"]:
                if l.get("on_camera"):
                    md.append(f"| {i} | {nm(l['speaker'])} | {l['text']} | in clip | {c['id']} at {l['at']}–{l['until']} s |")
        for t in tts.get(g["id"], []):
            md.append(f"| {i} | {nm(t['speaker'])} | {t['text']} | {'sound' if t.get('sound') else 'own track'} | "
                      f"{t['out']} at {t['at']} s in the ad |")
    return sec, "\n".join(md) + "\n", counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--media", help="json: {'tts-<name>': playable url}")
    a = ap.parse_args(argv)
    run = Path(a.run)
    M = json.loads(Path(a.media).read_text()) if a.media else {}
    sec, md, counts = build(run, M)
    (run / "clips" / "sound-map.html").write_text(sec)
    (run / "clips" / "SOUND-MAP.md").write_text(md)
    print(f"sound map: {counts['in']} in clips · {counts['own']} own track · {counts['snd']} sounds → "
          f"{run / 'clips' / 'SOUND-MAP.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
