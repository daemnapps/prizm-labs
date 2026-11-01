#!/usr/bin/env python3
"""The element library's page, rebuilt from library/.

    python3 page.py        # -> ../library.html

Every element index.json carries gets a section: ORDER's eight first, then any
other element in index order (SI-135 (elements rows truthful)). `elements.py
build` calls render() itself, so the page never lags the library.
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ORDER = ["format", "placement", "structure", "framework", "style", "delivery", "template", "doctrine"]
QUESTION = {
    "format": "what kind of asset is it — its shape and who carries it?",
    "placement": "where does it run?",
    "structure": "what are its beats, in what order?",
    "framework": "what is the argument's plan?",
    "style": "what does it look like?",
    "delivery": "how does it sound?",
    "template": "which build layout?",
    "doctrine": "where is the reader, and how does the argument work?",
    "letterform": "what lettering does it use?",
}
FALLBACK = "what does this element name?"          # an element with no QUESTION line yet


def elements(idx):
    """ORDER's eight first, as always, then every other element in index.json's order."""
    rest = []
    for l in idx["lists"]:
        if l["element"] not in ORDER and l["element"] not in rest:
            rest.append(l["element"])
    return ORDER + rest


def question(el):
    return QUESTION.get(el, FALLBACK)


def e(s):
    return html.escape("" if s is None else str(s))


def render(library=None, out=None):
    """library/ -> library.html. `library` defaults to ROOT/library, `out` to
    the page beside it; a list's file is read from `library` by its name."""
    library = Path(library) if library else ROOT / "library"
    out = Path(out) if out else library.parent / "library.html"
    idx = json.loads((library / "index.json").read_text())
    total = sum(l["rows"] for l in idx["lists"])
    signed = sum(l["approved"] for l in idx["lists"])
    empty = [l for l in idx["lists"] if not l["rows"]]
    unenforced = [l for l in idx["lists"] if not l["enforced_by"] and l["rows"]]
    drafts_named = []
    by_el = {}
    for l in idx["lists"]:
        by_el.setdefault(l["element"], []).append(l)
    order = elements(idx)

    tiles = "".join(
        f'<a class="tile" href="#{el}"><b>{el}</b><span class="q">{e(question(el))}</span>'
        f'<span class="n">{sum(x["rows"] for x in by_el.get(el, []))}</span>'
        f'<span class="s">{sum(x["approved"] for x in by_el.get(el, []))} signed · '
        f'{len(by_el.get(el, []))} list{"s" if len(by_el.get(el, [])) != 1 else ""}</span></a>'
        for el in order)

    sections = []
    for el in order:
        blocks = []
        for l in by_el.get(el, []):
            data = json.loads((library / Path(l["file"]).name).read_text())
            rows = "".join(
                f'<tr><td><code>{e(r["id"])}</code></td><td>{e(r.get("name"))}</td>'
                f'<td>{e((r.get("what") or "")[:220])}</td>'
                f'<td><span class="st {"ok" if r["approved"] else ("todo" if "TO DEFINE" in (r.get("what") or "") else "draft")}">'
                f'{"signed" if r["approved"] else ("to define" if "TO DEFINE" in (r.get("what") or "") else e(r.get("state") or r.get("status") or "draft"))}</span></td></tr>'
                for r in data["rows"])
            enf = (f'<span class="enf yes">enforced by {e(l["enforced_by"])}</span>' if l["enforced_by"]
                   else '<span class="enf no">nothing refuses an unknown value yet</span>')
            body = (f'<div class="tw"><table><thead><tr><th>id</th><th>name</th><th>what</th><th>status</th></tr></thead>'
                    f'<tbody>{rows}</tbody></table></div>') if data["rows"] else '<p class="empty">No list exists yet.</p>'
            blocks.append(
                f'<details {"open" if l["rows"] <= 12 else ""}><summary><b>{e(l["asset"])}</b> '
                f'<span class="cnt">{l["rows"]} rows · {l["approved"]} signed</span> {enf}</summary>'
                f'<p class="src">source: <code>{e(l["source"])}</code>'
                + (f' — {e(l["note"])}' if l.get("note") else "") + f'</p>{body}</details>')
        sections.append(f'<section id="{el}"><h2>{el}</h2><p class="lead">{e(question(el))}</p>{"".join(blocks)}</section>')

    page = f"""<meta charset="utf-8">
<title>The Element Library</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--ground:#F2F3F1;--card:#FFFFFF;--ink:#15181A;--mut:#5B6468;--line:#D6DBD8;--hair:#E7EAE8;
--accent:#1F5B4A;--accent-bg:#DDEDE6;--ok:#1E6B3F;--ok-bg:#DFEFE5;--warn:#8A5A0B;--warn-bg:#F5EAD4;--off:#8A2E24;--off-bg:#F6E1DD}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--ground:#101312;--card:#181C1B;--ink:#E5E9E7;--mut:#98A29E;
--line:#29302E;--hair:#202725;--accent:#86CBB3;--accent-bg:#14261F;--ok:#79C99A;--ok-bg:#142A1D;--warn:#D9A955;--warn-bg:#2B2214;--off:#E58C7E;--off-bg:#2E1815}}}}
:root[data-theme="dark"]{{--ground:#101312;--card:#181C1B;--ink:#E5E9E7;--mut:#98A29E;--line:#29302E;--hair:#202725;
--accent:#86CBB3;--accent-bg:#14261F;--ok:#79C99A;--ok-bg:#142A1D;--warn:#D9A955;--warn-bg:#2B2214;--off:#E58C7E;--off-bg:#2E1815}}
*{{box-sizing:border-box}}
body{{background:var(--ground);color:var(--ink);font:16px/1.6 "IBM Plex Sans",system-ui,-apple-system,sans-serif;margin:0}}
.wrap{{max-width:1040px;margin:0 auto;padding-inline:18px;padding-block:44px 90px}}
.eyebrow{{font:500 12px/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}}
h1,h2{{font-family:"Bricolage Grotesque",system-ui,sans-serif;letter-spacing:-.02em;font-weight:700;text-wrap:balance}}
h1{{font-size:clamp(36px,6.4vw,58px);line-height:1;margin:10px 0 14px}}
h2{{font-size:26px;margin:0 0 4px;text-transform:capitalize}}
.lede{{font-size:18.5px;color:var(--mut);max-width:66ch;margin:0}}
.stats{{display:flex;flex-wrap:wrap;gap:10px;margin:26px 0}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;min-width:150px}}
.stat b{{display:block;font:700 30px/1 "Bricolage Grotesque",sans-serif;font-variant-numeric:tabular-nums}}
.stat span{{font-size:13px;color:var(--mut)}}
.stat.off b{{color:var(--off)}} .stat.ok b{{color:var(--ok)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin:8px 0 10px}}
.tile{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;display:grid;gap:4px;color:inherit;text-decoration:none}}
.tile:hover{{border-color:var(--accent)}}
.tile b{{font:700 18px "Bricolage Grotesque",sans-serif;text-transform:capitalize;color:var(--accent)}}
.tile .q{{font-size:13px;color:var(--mut);line-height:1.4}}
.tile .n{{font:700 26px/1 "Bricolage Grotesque",sans-serif;margin-top:4px}}
.tile .s{{font-size:12.5px;color:var(--mut)}}
section{{margin-top:44px;padding-top:14px;border-top:2px solid var(--ink)}}
.lead{{color:var(--mut);margin:0 0 12px}}
details{{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:8px 0;padding:10px 14px}}
summary{{cursor:pointer;display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
summary b{{font-size:16px}}
.cnt{{font:12.5px "IBM Plex Mono",monospace;color:var(--mut)}}
.enf{{font:500 11px/1 "IBM Plex Mono",monospace;padding:5px 7px;border-radius:3px}}
.enf.yes{{color:var(--ok);background:var(--ok-bg)}} .enf.no{{color:var(--off);background:var(--off-bg)}}
.src{{font-size:13px;color:var(--mut);margin:8px 0}}
.empty{{color:var(--off);margin:8px 0}}
code{{font:12.5px "IBM Plex Mono",ui-monospace,monospace;background:var(--hair);padding:1px 5px;border-radius:3px}}
.tw{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--hair)}}
th{{font:500 11px "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}}
td:nth-child(3){{color:var(--mut);max-width:60ch}}
.st{{font:500 11px/1 "IBM Plex Mono",monospace;padding:4px 6px;border-radius:3px;white-space:nowrap}}
.st.ok{{color:var(--ok);background:var(--ok-bg)}} .st.draft{{color:var(--warn);background:var(--warn-bg)}} .st.todo{{color:var(--off);background:var(--off-bg)}}
a{{color:var(--accent)}} :focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
footer{{margin-top:60px;border-top:1px solid var(--line);padding-top:16px;font:12.5px/1.8 "IBM Plex Mono",monospace;color:var(--mut)}}
</style>
<div class="wrap">
<div class="eyebrow">components/elements · built from the lists where they live</div>
<h1>The Element Library</h1>
<p class="lede">Every format, placement, structure, framework, style, delivery value, template and doctrine term in the system — one shape, one place to ask "is this a real one?". A value that isn't here is refused.</p>
<div class="stats">
<div class="stat"><b>{total}</b><span>rows in {len(idx["lists"])} lists</span></div>
<div class="stat {"ok" if signed else "off"}"><b>{signed}</b><span>signed by you</span></div>
<div class="stat off"><b>{total - signed}</b><span>still drafts</span></div>
<div class="stat off"><b>{len(empty)}</b><span>lists with nothing in them</span></div>
<div class="stat off"><b>{len(unenforced)}</b><span>lists nothing enforces</span></div>
</div>
<div class="tiles">{tiles}</div>
{"".join(sections)}
<footer>Rebuilt by components/elements/machine/page.py from library/ · the lists stay where their tools read them (sources.json) · the owner's new rows are drafts in additions.json until he defines and signs them.</footer>
</div>
"""
    out.write_text(page)
    return out


def main():
    print("->", render())


if __name__ == "__main__":
    main()
