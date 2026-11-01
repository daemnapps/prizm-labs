"""The elements page — the review before production (the owner, 2026-09-23: "the
system should prompt to confirm the elements before going into actual
production"; "show me references").

    python3 elements_page.py <brief.md> --brand B --out DIR [--title T]

Built from `elements_check.sheet()` — nothing on it is typed by hand. For
every element the brief uses: its status (banked / to make, with what is
missing), its pictures (master and sheets, set plates, prop photo, packshots),
the REAL references it was made from with where each came from, and — for a
person who speaks — their voice: the real recording and any designed options
waiting in `runs/voice-build/<brand>/<id>/`. Writes DIR/index.html plus
DIR/img/ and DIR/audio/ (small copies). Publishing it is the session's act.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    import importlib.util as ilu
    sp = ilu.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    m = ilu.module_from_spec(sp); sp.loader.exec_module(m)
    return m


EC = _load("elements_check")
sys.path.insert(0, str(EC._workspace() / "components" / "brandpath"))
import brandpath as BP                                  # noqa: E402
import drive_index as DI                                # noqa: E402
e = html.escape

CSS = """
:root{--g:#F3F1EC;--p:#fff;--ink:#1C1A18;--soft:#6B655E;--line:#DDD8D0;--ok:#1F7A4D;--okb:#E3F1E8;--todo:#A8650C;--todob:#FBF0DE}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--g:#141311;--p:#1D1B19;--ink:#EEEAE4;--soft:#A39C93;--line:#35312D;--ok:#7FD3A2;--okb:#1D3226;--todo:#EDB45C;--todob:#35290F}}
:root[data-theme="dark"]{color-scheme:dark;--g:#141311;--p:#1D1B19;--ink:#EEEAE4;--soft:#A39C93;--line:#35312D;--ok:#7FD3A2;--okb:#1D3226;--todo:#EDB45C;--todob:#35290F}
*{box-sizing:border-box}body{background:var(--g);color:var(--ink);font:16px/1.55 "Instrument Sans",-apple-system,Arial,sans-serif;padding-inline:18px;padding-block:30px 70px}
.wrap{max-width:1180px;margin:0 auto;display:flex;flex-direction:column;gap:26px}header{display:flex;flex-direction:column;gap:10px}
h1{font-size:clamp(2rem,5vw,3rem);margin:0;letter-spacing:-.02em;text-wrap:balance}h2{margin:0;font-size:1.4rem;text-wrap:balance}h3{margin:12px 0 6px;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:var(--soft)}
p{margin:0;max-width:72ch}.soft{color:var(--soft)}.eyebrow{font:400 .75rem "Space Mono",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--soft)}
.chip{display:inline-block;font:600 .75rem/1 "Instrument Sans";padding:5px 9px;border-radius:99px}.ok{background:var(--okb);color:var(--ok)}.todo{background:var(--todob);color:var(--todo)}
.card{background:var(--p);border:1px solid var(--line);border-radius:12px;padding:20px;display:flex;flex-direction:column;gap:10px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.tab{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:620px;font-size:.88rem}td{border-bottom:1px solid var(--line);padding:8px;vertical-align:top}
.cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:20px}@media(max-width:760px){.cols{grid-template-columns:1fr}}
.refs{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px}.refs img{width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:8px;border:1px solid var(--line);display:block}
.pics{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}.pics img{width:100%;border-radius:8px;border:1px solid var(--line);display:block;background:#fff}
figure{margin:0}figcaption{font-size:.74rem;color:var(--soft);margin-top:4px;overflow-wrap:anywhere}
.voices{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}audio{width:100%}
details{border-top:1px solid var(--line);padding-top:8px}summary{cursor:pointer;font-weight:600}
pre{white-space:pre-wrap;font:12px/1.5 "Space Mono",monospace;background:var(--g);padding:12px;border-radius:8px;max-width:100%;overflow-x:auto}
nav{display:flex;flex-wrap:wrap;gap:6px}nav a{font:600 .8rem "Instrument Sans";color:var(--ink);text-decoration:none;border:1px solid var(--line);border-radius:99px;padding:6px 10px}
"""


def drive_roots() -> list:
    """`Shared Assets` on this machine's Drive, if mounted — brandpath's one mount helper."""
    m = DI.mount()
    return [m] if m is not None else []


def _tree(root: Path, rel: str, depth: int = 2) -> str:
    """A folder drawn as a tree with file counts — what is actually on disk."""
    base = root / rel
    if not base.is_dir():
        return f"<p class='soft'>{e(rel)} — not found here</p>"
    lines = []

    def walk(d: Path, lvl: int):
        kids = sorted([k for k in d.iterdir() if not k.name.startswith(".")], key=lambda k: (k.is_file(), k.name))
        files = [k for k in kids if k.is_file()]
        for k in [k for k in kids if k.is_dir()]:
            n = sum(1 for x in k.rglob("*") if x.is_file())
            lines.append(("  " * lvl) + f"{k.name}/  ({n} files)")
            if lvl + 1 < depth:
                walk(k, lvl + 1)
        if files and lvl < depth:
            shown = ", ".join(f.name for f in files[:6]) + (f" … +{len(files)-6}" if len(files) > 6 else "")
            lines.append(("  " * lvl) + shown)
    walk(base, 0)
    return f"<pre>{e(rel)}/\n" + e("\n".join(lines)) + "</pre>"


def where_it_lives(ws: Path, brand: str, body: dict) -> str:
    drive = next(iter(drive_roots()), None)
    kinds = [("AI casting — people and their voices", f"runs/ai-elements/{brand}/casting"),
             ("AI elements — sets", f"runs/ai-elements/{brand}/sets"),
             ("AI elements — props", f"runs/ai-elements/{brand}/props"),
             ("Brand info — the real products", "brands/" + BP.rel(brand, "products", root=ws / "brands")),
             ("Brand info — the cast list", "brands/" + BP.rel(brand, "ai-elements/characters", "casting", root=ws / "brands"))]
    rows = "".join(f"<tr><td><b>{e(i['id'])}</b><br><span class='soft'>{e(i['kind'])}</span></td><td><code>{e(i['folder'])}/</code></td>"
                   f"<td><code>{e('Shared Assets/' + i['folder'] + '/' if i['folder'].startswith('runs/') else 'Shared Assets/' + i['folder'] + '/')}</code></td></tr>" for i in body["items"])
    trees = "".join(f"<details><summary>{e(label)} — repo</summary>{_tree(ws, rel)}</details>"
                    + (f"<details><summary>{e(label)} — Drive</summary>{_tree(drive, rel)}</details>" if drive else "")
                    for label, rel in kinds)
    return f"""<section class='card' id='where'><h2>Where everything lives</h2>
<p><b>The brand folder holds only facts about the brand</b> — its real products and packshots, and the cast list (who plays what). <b>Everything we generate lives in runs:</b> <code>runs/ai-elements/<code>runs/casting/</code> for people (each with their own voice), <code>runs/ai-elements/</code> for sets, props and every other kindlt;brand<code>runs/casting/</code> for people (each with their own voice), <code>runs/ai-elements/</code> for sets, props and every other kindgt;/</code> — <code>casting/</code> for people (each with their own voice), <code>sets/</code>, <code>props/</code> and every other kind beside it. Same paths on both planes: the <b>repo</b> holds each element's written record (who or what it is, the recipe, where every picture came from, every prompt sent) plus small copies; the <b>Drive</b> (<code>Shared Assets/runs/…</code>) holds the full-size pictures, audio and real footage.</p>
<h3>Each element in this ad</h3><div class='tab'><table><tr><td><b>Element</b></td><td><b>Repo</b></td><td><b>Drive</b></td></tr>{rows}</table></div>
<h3>Inside a person's folder</h3><pre>character.md      who they are, looks, movement, voice, real references, adjustments
spec.json         the recipe the character tool runs
provenance.json   every picture's source, model, prompt file, Drive path
looks.json        the outfits a brief may name, by id
voice.json        their own voice (once picked)
voice/            the real recording, the designed options, what was sent
master.jpg        the one identity picture everything starts from
sheets/           turnaround · angles + expressions · details · light test · each look · colour key
sheets/prompts/   the exact prompt sent for every picture
reference/        the REAL photos / frames / audio it was built from (reference/body/ = full-body frames)
versions/         every earlier version, kept</pre>
<h3>The folders, as they are on disk right now</h3>{trees}</section>"""


def voices_to_approve(ws: Path, brand: str, body: dict, brief: Path, aud) -> str:
    """Every character who speaks in this brief, their lines, their real voice
    and the designed options — the one place the owner approves voices."""
    doc = EC._json_block(brief.read_text())
    lines = {}
    for s in doc.get("scenes") or []:
        if (s.get("voice") or "").strip() and s.get("speaker"):
            lines.setdefault(s["speaker"], []).append((s["id"], s["voice"]))
    cards = []
    # EVERY CHARACTER ACCOUNTED FOR (the owner, 2026-09-23: "we should establish the
    # voices now… every character and element needs to be accounted for"): the
    # people this brief uses first, then everyone else in the brand's casting.
    people = [i for i in body["items"] if i["kind"] == "person" and i.get("speaks")]
    seen = {i["folder"] for i in people}
    root = _load("element_paths").casting_root(brand, ws)
    for f in sorted(root.iterdir()) if root.is_dir() else []:
        rel = str(f.relative_to(ws))
        if f.is_dir() and not f.name.startswith("_") and rel not in seen and (f / "spec.json").is_file():
            people.append({"id": f.name.upper(), "bank_id": f.name, "folder": rel, "speaks": [],
                           "voice_id": (json.loads((f / "voice.json").read_text()).get("voice_id") if (f / "voice.json").is_file() else None)})
    for i in people:
        folder = ws / i["folder"]
        spec = json.loads((folder / "spec.json").read_text()) if (folder / "spec.json").is_file() else {}
        v = spec.get("voice") or {}
        vr = v.get("real_reference") or {}
        persona = v.get("persona") or (spec.get("character") or {}).get("voice", "")
        parts = []
        if vr.get("file") and (folder / vr["file"]).is_file():
            parts.append(f"<figure><figcaption><b>Real voice it's built from</b><br>{e(vr.get('from','')[:110])}</figcaption><audio controls preload='none' src='{aud(folder / vr['file'], i['bank_id']+'-real.mp3')}'></audio></figure>")
        vb = folder / "voice"
        # the approved voice, played first — found by the id it was saved from
        if (vb / "voice-provenance.json").is_file():
            vp = json.loads((vb / "voice-provenance.json").read_text())
            gid = next((o["generated_voice_id"] for o in vp.get("options", []) if o["option"] == vp.get("picked")), None)
            for oj in [vb / "options.json", *sorted(vb.glob("versions/round-*/options.json"))]:
                if oj.is_file() and gid:
                    hit = next((o for o in json.loads(oj.read_text())["options"] if o["generated_voice_id"] == gid), None)
                    if hit and (oj.parent / hit["file"]).is_file():
                        parts.append(f"<figure><figcaption><b>✓ Approved voice</b><br><span class='soft'>saved as theirs</span></figcaption><audio controls preload='none' src='{aud(oj.parent / hit['file'], i['bank_id']+'-approved.mp3')}'></audio></figure>")
                        break
        qc = {o["option"]: o for o in json.loads((vb / "check.json").read_text())["options"]} if (vb / "check.json").is_file() else {}
        if (vb / "options.json").is_file():
            for r in json.loads((vb / "options.json").read_text())["options"]:
                q = qc.get(r["option"]) or {}
                tag = (f" <span class='chip todo'>fails check: {e(', '.join(q['fails']))}</span>" if q.get("fails") else (" <span class='chip ok'>passes check</span>" if q else ""))
                meas = (f"<br><span class='soft'>{q['hz']} Hz · " + (f"{q['age']['slower']}× slower, pitch ×{q['age']['pitch']} vs the baseline" if q.get('age') else f"highs {q['highs_pct']}%") + "</span>") if q else ""
                if r.get("note"):
                    meas += f"<br><span class='soft'>{e(r['note'])}</span>"
                parts.append(f"<figure><figcaption><b>Option {r['option']}</b>{tag}{meas}</figcaption><audio controls preload='none' src='{aud(vb / r['file'], i['bank_id']+'-option-'+str(r['option'])+'.mp3')}'></audio></figure>")
        if i.get("voice_id") and not (vb / "options.json").is_file():
            state, cls = "Approved — their own voice", "ok"
        elif i.get("voice_id"):
            state, cls = "Approved — alternatives below if you want to swap", "ok"
        elif (vb / "options.json").is_file():
            state, cls = "Pick one: 1, 2 or 3", "todo"
        else:
            state, cls = "Needs a real recording first", "todo"
        said = "".join(f"<li><b>{e(sid)}</b> — {e(txt)}</li>" for sid, txt in lines.get(i["id"], []))
        cards.append(f"""<div class='card' style='gap:8px'><div class='row'><span class='chip {cls}'>{e(state)}</span><span class='eyebrow'>{('speaks in ' + e(', '.join(i['speaks']))) if i['speaks'] else 'banked for future ads'}</span></div>
<h3 style='margin:0;color:var(--ink);font-size:1.1rem;text-transform:none;letter-spacing:0'>{e(i['id'])}{'' if i['speaks'] else ' · <span class=soft>not in this ad</span>'}</h3>
<p class='soft'>{e(persona)}</p>{('<p class=soft><b>Adjusted from the real voice:</b> '+e('; '.join(v.get('adjustments') or []))+'</p>') if v.get('adjustments') else ''}
<div class='voices'>{''.join(parts) or "<p class='soft'>No real recording of this person yet.</p>"}</div>
<details><summary>Their lines in this ad ({len(lines.get(i['id'], []))})</summary><ul>{said}</ul></details></div>""")
    return f"<section class='card' id='voices'><div class='eyebrow'>Approve first</div><h2>Voices to approve</h2><p>Every character in the brand's casting — the ones in this ad first. One voice each, built from a real recording and adjusted to be theirs.</p><div style='display:flex;flex-direction:column;gap:12px'>{''.join(cards)}</div></section>"


def frames_section(run: Path, doc: dict, pic) -> str:
    """Step 3 — every scene's first and last frame, what each was built from,
    and every frame remade (before → after)."""
    media = run / "media"
    refs = json.loads((run / "element-refs.json").read_text()) if (run / "element-refs.json").is_file() else {}
    remakes = []
    for f in sorted(run.glob("remakes-frames*.json")):
        try:
            remakes += json.loads(f.read_text())
        except Exception:
            pass
    remade = {r["id"] for r in remakes}
    cards = []
    for s in doc.get("scenes") or []:
        sid = s["id"]
        shots = [(n, media / f"{sid}-{n}.png") for n in ("F1", "FLAST", "PLATE", "PACKSHOT") if (media / f"{sid}-{n}.png").is_file()]
        if not shots:
            continue
        figs = "".join(f"<figure><img src='{pic(p, 700)}' alt=''><figcaption>{e(n)}{' · remade' if f'{sid}-{n}' in remade else ''}</figcaption></figure>" for n, p in shots)
        used = " · ".join(r["what"] for r in refs.get(f"{sid}-F1", []))
        cards.append(f"<div class='card' style='gap:6px'><div class='row'><b>{e(sid)}</b><span class='eyebrow'>{e(s.get('kind',''))} · {e(s.get('speaker') or '')} · {e(s.get('setting_id') or '')}</span></div>"
                     f"<p class='soft'>{e((s.get('voice') or '')[:180])}</p><div class='frames'>{figs}</div>"
                     + (f"<p class='soft'><b>Built from:</b> {e(used)}</p>" if used else "") + "</div>")
    fixes = ""
    for r in remakes:
        old = run / r.get("old", "") if r.get("old") else None
        new = media / f"{r['id']}.png"
        if old and old.is_file() and new.is_file():
            fixes += f"<figure><img src='{pic(old, 500)}' alt=''><figcaption>{e(r['id'])} before</figcaption></figure><figure><img src='{pic(new, 500)}' alt=''><figcaption>{e(r['id'])} after — {e(r['change'][:120])}</figcaption></figure>"
    return (f"<section class='card' id='frames'><div class='eyebrow'>Step 3 · frames</div><h2>Every frame, from the banked elements</h2>"
            f"<p>Each scene's first frame is built from its people, their outfits, the set, the real packshot and the props; the last frame is an edit of the first. Remade frames are marked.</p>"
            f"<style>.frames{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}}.frames img{{width:100%;border-radius:8px;border:1px solid var(--line)}}</style>"
            f"<div style='display:flex;flex-direction:column;gap:10px'>{''.join(cards)}</div>"
            + (f"<h3>Fixed frames — before and after</h3><div class='frames'>{fixes}</div>" if fixes else "") + "</section>")


def build(brief: Path, brand: str, out: Path, title: str | None = None, run: Path | None = None) -> Path:
    from PIL import Image
    ws = EC._workspace()
    body = EC.sheet(brief.read_text(), brand)
    (out / "img").mkdir(parents=True, exist_ok=True); (out / "audio").mkdir(exist_ok=True)
    n = [0]

    def pic(src: Path, w=1100) -> str:
        n[0] += 1
        name = f"{n[0]:03d}-{src.stem[:40]}.jpg"
        im = Image.open(src).convert("RGB"); im.thumbnail((w, w)); im.save(out / "img" / name, quality=82)
        return f"img/{name}"

    def aud(src: Path, name: str) -> str:
        shutil.copy2(src, out / "audio" / name); return f"audio/{name}"

    H = [f"<title>{e(title or 'Ad Elements')}</title>",
         "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;600;700&family=Space+Mono&display=swap'>",
         f"<style>{CSS}</style><div class='wrap'>"]
    tm = body["to_make"]
    H.append(f"""<header><div class='eyebrow'>Elements · {e(body.get('title') or '')} · {e(brand)}</div><h1>{e(title or 'Ad Elements')}</h1>
<p class='soft'>Every person, outfit, voice, place, product and prop this brief uses — each built from a real reference, documented, and shown beside that reference. Production does not start until every row is banked and you OK the set.</p>
<div class='row'><span class='chip {'ok' if not tm else 'todo'}'>{len(body['items'])-len(tm)} banked</span><span class='chip {'todo' if tm else 'ok'}'>{len(tm)} to make</span>{''.join("<span class='chip todo'>brief gap</span>" for _ in body['brief_gaps'][:1])}</div></header>""")
    rows = "".join(f"<tr><td><a href='#{EC.slug(i['kind']+'-'+i['id'])}'><b>{e(i['id'])}</b></a><br><span class='soft'>{e(i['kind'])}</span></td><td>{e(', '.join(x for x in i['scenes'] if x))}</td>"
                   f"<td><span class='chip {'ok' if i['status']=='banked' else 'todo'}'>{'Banked' if i['status']=='banked' else 'To make'}</span></td><td>{'<br>'.join(e(m[:180]) for m in i['missing']) or '—'}</td></tr>" for i in body["items"])
    gaps = "".join(f"<li>{e(g)}</li>" for g in body["brief_gaps"])
    if run and (run / "media").is_dir():
        H.append(frames_section(run, EC._json_block(brief.read_text()), pic))
    H.append(voices_to_approve(ws, brand, body, brief, aud))
    H.append(f"<section class='card'><h2>The list</h2><div class='tab'><table>{rows}</table></div>{('<h3>Brief gaps</h3><ul>'+gaps+'</ul>') if gaps else ''}</section>")

    for i in body["items"]:
        folder = ws / i["folder"] if i.get("folder") else None
        prov = json.loads((folder / "provenance.json").read_text()) if folder and (folder / "provenance.json").is_file() else {}
        refs = (prov.get("real_references") or []) + (prov.get("body_references") or [])
        refhtml = "".join(f"<figure><img src='{pic(folder / r['file'], 600)}' alt=''><figcaption><b>{e(r.get('kind',''))}</b>{(' · '+e(r['use'])) if r.get('use') else ''}<br>{e(str(r.get('from',''))[:150])}</figcaption></figure>"
                          for r in refs if folder and (folder / r["file"]).is_file() and (folder / r["file"]).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
        pics = []
        if i["kind"] == "person" and folder and folder.is_dir():
            for f, cap in [("master.jpg", "Master")] + [(f"sheets/{p.name}", p.stem.replace('-', ' ')) for p in sorted((folder / "sheets").glob("*.jpg"))]:
                if (folder / f).is_file():
                    pics.append((pic(folder / f), cap))
        elif i["kind"] == "setting" and folder and folder.is_dir():
            pics = [(pic(p, 700), p.stem.replace('-', ' ')) for p in sorted((folder / "plates").glob("*.jpg"))]
        elif i["kind"] == "prop" and folder and (folder / "picture.jpg").is_file():
            pics = [(pic(folder / "picture.jpg", 600), "the prop")]
        elif i["kind"] == "product" and folder:
            pics = [(pic(p, 600), p.name) for p in sorted((folder / "images").glob("packshot*"))[:4]]
        pichtml = "".join(f"<figure><img src='{s}' alt=''><figcaption>{e(c)}</figcaption></figure>" for s, c in pics)
        voice = ""
        if i["kind"] == "person" and i.get("speaks"):
            vb = folder / "voice" if folder else ws / "_none"
            spec = json.loads((folder / "spec.json").read_text()) if folder and (folder / "spec.json").is_file() else {}
            vr = ((spec.get("voice") or {}).get("real_reference") or {})
            parts = []
            if vr.get("file") and (folder / vr["file"]).is_file():
                parts.append(f"<figure><figcaption><b>Real reference</b> — {e(vr.get('from','')[:120])}</figcaption><audio controls preload='none' src='{aud(folder / vr['file'], i['bank_id']+'-real.mp3')}'></audio></figure>")
            if (vb / "options.json").is_file():
                for r in json.loads((vb / "options.json").read_text())["options"]:
                    parts.append(f"<figure><figcaption><b>Option {r['option']}</b></figcaption><audio controls preload='none' src='{aud(vb / r['file'], i['bank_id']+'-option-'+str(r['option'])+'.mp3')}'></audio></figure>")
            status = "banked — their own" if i.get("voice_id") else ("pick one" if (vb / "options.json").is_file() else ("needs a real recording to build from" if not parts else "to make"))
            voice = f"<h3>Voice · {e(status)} · speaks in {e(', '.join(i['speaks']))}</h3><div class='voices'>{''.join(parts) or '<p class=soft>No real recording yet.</p>'}</div>"
        looks = ""
        if i["kind"] == "person" and i.get("looks"):
            looks = "<h3>Wears in this ad</h3><p>" + e(", ".join(l for l in i["looks"] if l)) + "</p>"
        H.append(f"""<section class='card' id='{EC.slug(i['kind']+'-'+i['id'])}'><div class='row'><span class='chip {'ok' if i['status']=='banked' else 'todo'}'>{'Banked' if i['status']=='banked' else 'To make'}</span><span class='eyebrow'>{e(i['kind'])} · {e(', '.join(x for x in i['scenes'] if x))}</span></div>
<h2>{e(i['id'])}</h2>{('<p class=soft>'+e(i.get('describe','')[:400])+'</p>') if i.get('describe') else ''}
{('<p><b>Missing:</b> '+e('; '.join(i['missing']))+'</p>') if i['missing'] else ''}
<div class='cols'><div><h3>Built from (real)</h3><div class='refs'>{refhtml or '<p class=soft>—</p>'}</div></div><div><h3>What we made</h3><div class='pics'>{pichtml or '<p class=soft>Nothing yet.</p>'}</div>{looks}{voice}</div></div></section>""")
    H.append(where_it_lives(ws, brand, body))
    H.append("</div>")
    (out / "index.html").write_text("\n".join(H))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief"); ap.add_argument("--brand", required=True); ap.add_argument("--out", required=True); ap.add_argument("--title")
    ap.add_argument("--run", help="a production run folder — adds the frames step")
    a = ap.parse_args(argv)
    o = build(Path(a.brief), a.brand, Path(a.out), a.title, Path(a.run) if a.run else None)
    print(o / "index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
