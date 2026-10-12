#!/usr/bin/env python3
"""A run folder in, one email you can actually look at out.

    python3 render.py results/<label>          # -> results/<label>/email.html

Reads the fenced ```BLOCKS array stage 8 emits and draws it as a 600px
email — tables, inline styles, the way a mail client wants it. Above the
email it prints every subject/preview pair stage 5 wrote, so the thing that
decides whether the email is opened is the first thing on the page.

It invents nothing. A block type it does not know is drawn as a labelled gap,
not guessed at, because a silently dropped block is a block nobody notices is
missing. Image blocks have no picture yet by design — the image lane makes
those — so each one renders as its brief and its alt text.
"""
import html
import json
import re
import sys
from pathlib import Path

# The vocabulary. Adding a block type is adding a function here and a row in
# stage 8's table — never something a prompt decides at run time.
KNOWN = ("preheader", "headline", "subhead", "copy", "image", "quote",
         "bullets", "button", "product", "divider", "ps", "signoff", "footer")

BLOCKS_FENCE = re.compile(r"```(?:BLOCKS|blocks|json)\s*\n(.+?)\n```", re.S)
PAIR = re.compile(
    r"(?P<name>VERSION\s*\d+[^\n]*)\n+"
    r"(?:[^\n]*?\bsubject\b[^:\n]*:\s*(?P<subject>[^\n]+))\n+"
    r"(?:[^\n]*?\bpreview\b[^:\n]*:\s*(?P<preview>[^\n]+))",
    re.I)


def e(s):
    return html.escape(str(s or ""), quote=True)


def blocks_from(text):
    m = BLOCKS_FENCE.search(text or "")
    if not m:
        return None, "stage 8 wrote no ```BLOCKS fence — nothing to draw"
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as ex:
        return None, f"the BLOCKS fence is not valid JSON: {ex}"
    if not isinstance(data, list):
        return None, "the BLOCKS fence is not a JSON array"
    return data, None


def pairs_from(text):
    out = []
    for m in PAIR.finditer(text or ""):
        out.append(dict(name=m.group("name").strip(" *#:"),
                        subject=m.group("subject").strip(" *`"),
                        preview=m.group("preview").strip(" *`")))
    return out


# --- one function per block type ------------------------------------------

def _copy(t):
    # blank-line-separated paragraphs, so a run of them stays readable
    paras = [p.strip() for p in re.split(r"\n\s*\n", t or "") if p.strip()]
    return "".join(
        f'<tr><td class="pad"><p class="copy">{e(p)}</p></td></tr>' for p in paras)


def draw(b):
    t = (b.get("type") or "").strip().lower()
    if t == "preheader":
        return ('<tr><td class="pad"><div class="pre">preview text · '
                f'{e(b.get("text"))}</div></td></tr>')
    if t == "headline":
        return f'<tr><td class="pad"><h1>{e(b.get("text"))}</h1></td></tr>'
    if t == "subhead":
        return f'<tr><td class="pad"><h2>{e(b.get("text"))}</h2></td></tr>'
    if t == "copy":
        return _copy(b.get("text"))
    if t == "bullets":
        li = "".join(f"<li>{e(x)}</li>" for x in (b.get("items") or []))
        return f'<tr><td class="pad"><ul>{li}</ul></td></tr>'
    if t == "quote":
        who = b.get("attribution")
        cite = f'<div class="cite">— {e(who)}</div>' if who else ""
        return (f'<tr><td class="pad"><blockquote>{e(b.get("text"))}'
                f"{cite}</blockquote></td></tr>")
    if t == "button":
        href = b.get("href") or ""
        bad = "" if href and not href.startswith("[UNFILLED") else " unfilled"
        return ('<tr><td class="pad" align="center">'
                f'<a class="btn{bad}" href="{e(href)}">{e(b.get("label"))}</a>'
                + (f'<div class="dest">{e(href)}</div>' if href else "")
                + "</td></tr>")
    if t == "image":
        return ('<tr><td class="pad"><div class="img">'
                '<div class="img-tag">image · to be built by the image lane</div>'
                f'<div class="brief">{e(b.get("image_brief"))}</div>'
                f'<div class="alt"><b>alt:</b> {e(b.get("alt"))}</div>'
                "</div></td></tr>")
    if t == "product":
        return ('<tr><td class="pad"><div class="prod">'
                '<div class="img-tag">product image · image lane</div>'
                f'<div class="brief">{e(b.get("image_brief"))}</div>'
                f'<div class="alt"><b>alt:</b> {e(b.get("alt"))}</div>'
                f'<div class="pname">{e(b.get("name"))}</div>'
                f'<div class="price">{e(b.get("price"))}</div>'
                f'<a class="btn" href="{e(b.get("href"))}">{e(b.get("label"))}</a>'
                "</div></td></tr>")
    if t == "divider":
        return '<tr><td class="pad"><hr></td></tr>'
    if t == "ps":
        return f'<tr><td class="pad"><p class="ps">{e(b.get("text"))}</p></td></tr>'
    if t == "signoff":
        return f'<tr><td class="pad"><p class="sign">{e(b.get("text"))}</p></td></tr>'
    if t == "footer":
        return f'<tr><td class="pad"><div class="foot">{e(b.get("text"))}</div></td></tr>'
    # Unknown: say so on the page. Never drop it.
    return ('<tr><td class="pad"><div class="unknown">unrecognised block type '
            f'<code>{e(t or "(none)")}</code> — nothing was drawn for it<br>'
            f'<small>{e(json.dumps(b)[:400])}</small></div></td></tr>')


CSS = """
:root{--ink:#16130f;--mut:#6d635a;--line:#e2dcd3;--bg:#f4f1ec;--card:#fff;--acc:#8a5a2b}
@media (prefers-color-scheme:dark){:root{--ink:#ece7e0;--mut:#a49a8f;--line:#332e29;--bg:#141210;--card:#1c1917;--acc:#c98a4b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:720px;margin:0 auto;padding:32px 20px 80px}
h3.sec{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);
 margin:36px 0 12px;font-weight:700}
.meta{color:var(--mut);font-size:13px;margin:0 0 4px}
.inbox{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.row{padding:14px 16px;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}
.row .tag{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--acc);font-weight:700}
.row .subj{font-weight:700;margin-top:3px}
.row .prev{color:var(--mut);font-size:14px;margin-top:2px}
.email{background:var(--card);border:1px solid var(--line);border-radius:12px;
 max-width:600px;margin:0 auto;overflow:hidden}
table{width:100%;border-collapse:collapse}
.pad{padding:10px 28px}
h1{font-size:27px;line-height:1.25;margin:14px 0 6px}
h2{font-size:18px;line-height:1.35;margin:8px 0 4px;font-weight:600;color:var(--mut)}
p.copy{margin:0 0 2px}
ul{margin:4px 0;padding-left:20px}
blockquote{margin:8px 0;padding:14px 16px;border-left:3px solid var(--acc);
 background:rgba(138,90,43,.06);font-style:italic}
.cite{font-style:normal;font-size:13px;color:var(--mut);margin-top:6px}
.btn{display:inline-block;background:var(--acc);color:#fff;text-decoration:none;
 padding:14px 30px;border-radius:6px;font-weight:700;margin:10px 0 2px}
.btn.unfilled{background:#b3271e}
.dest{font-size:11px;color:var(--mut);margin-top:6px;word-break:break-all}
.img,.prod{border:1px dashed var(--line);border-radius:8px;padding:16px;margin:10px 0;
 background:rgba(127,127,127,.05)}
.img-tag{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--acc);font-weight:700}
.brief{margin-top:8px;font-size:14px}
.alt{margin-top:8px;font-size:13px;color:var(--mut)}
.pname{margin-top:12px;font-weight:700}
.price{color:var(--mut)}
.ps{margin:14px 0 0;font-style:italic}
.sign{margin:14px 0 0}
.foot{font-size:12px;color:var(--mut);border-top:1px solid var(--line);padding-top:14px;margin-top:10px}
hr{border:0;border-top:1px solid var(--line);margin:14px 0}
.unknown{border:1px solid #b3271e;border-radius:8px;padding:12px;color:#b3271e;font-size:13px}
.warn{border:1px solid #b3271e;border-radius:10px;padding:16px;color:#b3271e;background:rgba(179,39,30,.06)}
pre{white-space:pre-wrap;font-size:13px;color:var(--mut);background:var(--card);
 border:1px solid var(--line);border-radius:10px;padding:16px;overflow-x:auto}
"""


def build(run_dir):
    run_dir = Path(run_dir).resolve()
    b_file = run_dir / "stage8--blocks.md"
    s_file = run_dir / "stage5--subjects.md"
    if not b_file.is_file():
        sys.exit(f"no stage 8 output in {run_dir} — run the chain first")

    blocks, err = blocks_from(b_file.read_text())
    subj_text = s_file.read_text() if s_file.is_file() else ""
    pairs = pairs_from(subj_text)

    meta = {}
    rj = run_dir / "run.json"
    if rj.is_file():
        meta = json.loads(rj.read_text())

    if pairs:
        inbox = "".join(
            f'<div class="row"><div class="tag">{e(p["name"])}</div>'
            f'<div class="subj">{e(p["subject"])}</div>'
            f'<div class="prev">{e(p["preview"])}</div></div>' for p in pairs)
    elif subj_text:
        inbox = f'<div class="row"><pre>{e(subj_text)}</pre></div>'
    else:
        inbox = '<div class="row"><div class="prev">stage 5 has not run</div></div>'

    if err:
        body = f'<div class="warn">{e(err)}</div><pre>{e(b_file.read_text()[:4000])}</pre>'
    else:
        body = ('<div class="email"><table role="presentation">'
                + "".join(draw(b) for b in blocks) + "</table></div>")

    head = (f'<p class="meta">{e(meta.get("label", run_dir.name))} · '
            f'{e(meta.get("brand", ""))} · lane {e(meta.get("lane", "?"))} · '
            f'format {e(meta.get("format", "?"))} · sender {e(meta.get("sender", "?"))}</p>')

    out = (f"<!doctype html><meta charset=utf-8>"
           f"<meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>{e(meta.get('label', run_dir.name))} — email</title>"
           f"<style>{CSS}</style><div class=wrap>{head}"
           f'<h3 class="sec">Every subject line — all ship, nothing ranked</h3>'
           f'<div class="inbox">{inbox}</div>'
           f'<h3 class="sec">The email</h3>{body}</div>')

    dest = run_dir / "email.html"
    dest.write_text(out)
    n = 0 if blocks is None else len(blocks)
    print(f"{dest}  ({n} block(s), {len(pairs)} subject pair(s))")
    return dest


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 render.py results/<label>")
    build(sys.argv[1])
