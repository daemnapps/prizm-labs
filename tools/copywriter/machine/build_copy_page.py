#!/usr/bin/env python3
"""The copy, on one page, ready to lift.

    python3 build_copy_page.py

output/ is the record; this is the reading surface. Every finished body,
headline and description for every source, with a copy button on each and
nothing else in the way — no stages, no prompts, no receipts.
"""
import html, json, re
from paths import HERE

OUT = HERE / "pages" / "copy-page.html"


def parse(md):
    """output/<x>/copy.md → [(format, [(label, text, note)])]"""
    md = re.sub(r"^<!--.*?-->\s*", "", md, flags=re.S)
    blocks, fmt, cur = [], None, []
    label = note = None
    buf = []

    def flush():
        nonlocal buf, label, note
        if label and buf:
            t = "\n".join(buf).strip()
            if t:
                cur.append((label, t, note))
        buf, note = [], None

    for line in md.splitlines():
        # The format header has three vintages: **`FORMAT: x`**, **FORMAT: x**
        # and, from stage-8 v2, a markdown heading `# FORMAT: \`x\`./`. The last
        # one silently parsed to nothing — a finished run reached output/ and
        # the page showed none of it, with no error anywhere. Accept all three.
        m = re.match(r"^#{0,3}\s*\*{0,2}`?FORMAT:?\s*`?([a-z-]+)`?", line)
        if m:
            flush()
            if fmt and cur:
                blocks.append((fmt, list(cur)))
            fmt, cur, label = m.group(1), [], None
            continue
        # Body labels have changed shape across runs — early ones say
        # "The copy", later ones "BODY A". A reader should not have to care
        # which vintage a file is, so both parse.
        m = re.match(r"^\*\*(BODY [A-Z]|The copy|HEADLINES?[^*]*|DESCRIPTIONS?[^*]*)\*\*", line)
        if m:
            flush()
            lab = m.group(1).strip()
            if lab.lower() == "the copy":
                lab = f"BODY {chr(65 + sum(1 for l, _, _ in cur if l.startswith('BODY')))}"
            label = lab
            continue
        # Word counts are a receipt, not copy. They arrive in several
        # shapes across runs; none of them get pasted into an ad.
        if re.match(r"^\**\(?\**\s*(word count|words)\b[:\s]*\d+", line, re.I) \
           or re.match(r"^\**\(?\s*\d+\s+words?\b", line, re.I):
            continue
        if line.startswith("*What") or line.startswith("*Leans") or line.startswith("**What"):
            note = re.sub(r"^\**[A-Za-z' ]+:?\**\s*", "", line).strip(" *")
            continue
        if line.strip() in ("---", "—"):
            continue
        if label:
            buf.append(line)
    flush()
    if fmt and cur:
        blocks.append((fmt, list(cur)))
    return blocks


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--line:#e6e3dd;--ink:#26241f;--body:#3b3833;
--dim:#7b766c;--accent:#2c6b60;--mono:ui-monospace,"SF Mono",Menlo,monospace;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#141311;--card:#1d1b18;--line:#332f29;--ink:#efeae1;--body:#ddd7cc;
--dim:#a49c8f;--accent:#63b5a6}}
:root[data-theme=dark]{--bg:#141311;--card:#1d1b18;--line:#332f29;--ink:#efeae1;
--body:#ddd7cc;--dim:#a49c8f;--accent:#63b5a6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--body);font:16px/1.6 var(--sans);
padding:0 18px 90px;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto}
header{padding:44px 0 6px}
h1{font-size:30px;margin:6px 0 0;color:var(--ink);letter-spacing:-.02em}
.eyebrow{font:600 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.sub{color:var(--dim);margin-top:10px}
h2{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);
margin:44px 0 4px;font-weight:650}
.src{border-top:2px solid var(--accent);padding-top:14px;margin-top:46px}
.src h3{font-size:20px;color:var(--ink);margin:0 0 4px;letter-spacing:-.01em}
.src .meta{font:11.5px var(--mono);color:var(--dim)}
.fmt{font:600 10.5px var(--mono);letter-spacing:.1em;text-transform:uppercase;
color:var(--accent);margin:30px 0 10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
margin-bottom:12px;overflow:hidden}
.card .top{display:flex;align-items:center;gap:10px;padding:9px 14px;
border-bottom:1px solid var(--line);font:600 11px var(--mono);color:var(--dim);
letter-spacing:.08em;text-transform:uppercase}
.card .top .wc{margin-left:auto;font-weight:400;text-transform:none;letter-spacing:0}
button{font:11px var(--sans);background:transparent;border:1px solid var(--line);
color:var(--dim);border-radius:6px;padding:3px 10px;cursor:pointer}
button:hover{color:var(--ink);border-color:var(--dim)}
button.ok{color:#fff;background:var(--accent);border-color:var(--accent)}
pre{margin:0;padding:16px 18px;white-space:pre-wrap;font:15.5px/1.68 var(--sans);
color:var(--body)}
.note{padding:10px 18px;border-top:1px dashed var(--line);font-size:13px;
color:var(--dim);line-height:1.5}
.chips{display:flex;flex-wrap:wrap;gap:8px;padding:14px 18px}
.chip{border:1px solid var(--line);border-radius:20px;padding:6px 13px;
font-size:14px;color:var(--ink);cursor:pointer;background:var(--card)}
.chip:hover{border-color:var(--accent);color:var(--accent)}
footer{margin-top:56px;padding-top:16px;border-top:1px solid var(--line);
font:11.5px var(--mono);color:var(--dim)}
"""

JS = """
function cp(el, text){
  navigator.clipboard.writeText(text).then(()=>{
    const o=el.textContent; el.textContent='copied'; el.classList.add('ok');
    setTimeout(()=>{el.textContent=o;el.classList.remove('ok')},1200);
  });
}
"""


def page_title():
    """Named after the brands whose copy is actually on the page — read from
    each published source's own record, never typed here."""
    brands = set()
    for d in sorted((HERE / "output").iterdir()) if (HERE / "output").is_dir() else []:
        src = d / "source.md"
        if not (d / "copy.md").is_file():
            continue
        m = re.search(r"\*\*Brand\*\*\s+([a-z0-9-]+)", src.read_text()) if src.is_file() else None
        if m:
            brands.add(m.group(1))
    if not brands:
        return "Ad copy"
    return " + ".join(b.replace("-", " ").title() for b in sorted(brands)) + " ad copy"


def main():
    parts = ['<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             f"<title>Copy Output</title><style>{CSS}</style>",
             "<div class='wrap'><header>",
             "<div class='eyebrow'>the copy machine · finished output</div>",
             f"<h1>{html.escape(page_title())}</h1>",
             "<p class='sub'>Every finished body, headline and description. "
             "Tap any block to copy it.</p></header>"]

    for d in sorted((HERE / "output").iterdir()):
        cf = d / "copy.md"
        if not cf.is_file():
            continue
        meta = ""
        sf = d / "source.md"
        if sf.is_file():
            m = re.search(r"\*\*Built from\*\* `([^`]+)`", sf.read_text(encoding="utf-8"))
            b = re.search(r"\*\*Brand\*\* (.+?)  ", sf.read_text(encoding="utf-8"))
            raw = (b.group(1) if b else "") + (" · " + m.group(1).split("/")[-1] if m else "")
            meta = html.escape(re.sub(r"\*+", "", raw)).strip(" ·")
        title = d.name.replace("-", " ")
        parts.append(f"<div class='src'><h3>{html.escape(title)}</h3>"
                     f"<div class='meta'>{meta}</div></div>")

        for fmt, items in parse(cf.read_text(encoding="utf-8")):
            parts.append(f"<div class='fmt'>{html.escape(fmt)}</div>")
            for label, text, note in items:
                esc = html.escape(text)
                js = json.dumps(text)
                if label.upper().startswith(("HEADLINE", "DESCRIPTION")):
                    chips = []
                    for ln in text.splitlines():
                        ln = re.sub(r"^\s*\d+\.\s*", "", ln).strip(" *")
                        ln = re.sub(r"\s*[—-]\s*\d+ words?.*$", "", ln).strip(" *")
                        if ln:
                            chips.append(f"<span class='chip' onclick='cp(this,{json.dumps(ln)})'>"
                                         f"{html.escape(ln)}</span>")
                    if chips:
                        parts.append(f"<div class='card'><div class='top'>{html.escape(label)}</div>"
                                     f"<div class='chips'>{''.join(chips)}</div></div>")
                    continue
                wc = len(text.split())
                parts.append(
                    f"<div class='card'><div class='top'>{html.escape(label)}"
                    f"<span class='wc'>{wc} words</span>"
                    f"<button onclick='cp(this,{html.escape(js)})'>copy</button></div>"
                    f"<pre>{esc}</pre>"
                    + (f"<div class='note'>{html.escape(note)}</div>" if note else "")
                    + "</div>")

    parts.append("<footer>generated from output/ · daemn/content-machine/copy</footer></div>")
    parts.append(f"<script>{JS}</script>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    print(main())
