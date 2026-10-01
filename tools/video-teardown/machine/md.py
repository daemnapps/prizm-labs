#!/usr/bin/env python3
"""Markdown to HTML — enough of it that a brief reads like a document.

No library, no CDN: the board is a file on his Mac and has to work offline.
Tables matter most here; the briefs are largely tables.
"""

import html as H
import re


def _inline(t):
    t = H.escape(t)
    # Protect code spans first: a prompt that shows `![Scene N](—)` as an
    # example must render as text, not as a broken image.
    spans = []

    def _stash(m):
        spans.append(m.group(1))
        return f"\x00{len(spans)-1}\x00"

    t = re.sub(r"`([^`]+)`", _stash, t)
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", t)
    # Underscore emphasis only at word boundaries — prompts are full of
    # {variable_names} and a greedy rule turns two of them into one italic run.
    t = re.sub(r"(?<![\w_])_([^_\n]+)_(?![\w_])", r"<em>\1</em>", t)
    t = re.sub(r"~~(.+?)~~", r"<del>\1</del>", t)
    t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
               r'<img src="\2" alt="\1" loading="lazy">', t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    # Bare URLs and brand domains become real links too — a Doc that says
    # "<brand>.com" in plain text is a link she has to type (Damon,
    # 2026-09-18: "make sure any links are properly hyperlinked").
    t = re.sub(r'(?<!["=>/\w])(https?://[^\s<)]+?)(?=[.,;:!?]?(?:\s|$|<))',
               r'<a href="\1" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r'(?<![\w@/.:"=-])((?:[a-z0-9-]+\.)+(?:com|co|net|store|org)(?:/[^\s<)]*?)?)(?=[.,;:!?]?(?:\s|$|<))',
               lambda m: f'<a href="https://{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>',
               t, flags=re.I)
    t = re.sub(r'(?<![\w/"=])([\w.+-]+@[\w-]+\.[\w.]+\w)',
               r'<a href="mailto:\1">\1</a>', t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", t)
    return t


def _row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def render(src):
    if not src:
        return '<p class="none">Nothing here yet.</p>'
    src = re.sub(r"^<!--.*?-->\s*", "", src, count=1, flags=re.S)
    lines = src.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)

    while i < n:
        ln = lines[i]

        # fenced code
        if ln.lstrip().startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(H.escape(lines[i])); i += 1
            i += 1
            out.append("<pre class='block'>" + "\n".join(buf) + "</pre>")
            continue

        # table: a header row followed by a --- separator
        if "|" in ln and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
            head = _row(ln)
            i += 2
            body = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append(_row(lines[i])); i += 1
            t = ["<div class='tw'><table><thead><tr>"]
            t += [f"<th>{_inline(c)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in body:
                r = (r + [""] * len(head))[:len(head)]
                t.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            lvl = min(len(m.group(1)) + 1, 6)
            out.append(f"<h{lvl}>{_inline(m.group(2).strip())}</h{lvl}>")
            i += 1
            continue

        # horizontal rule
        if re.match(r"^\s*([-*_])\s*\1\s*\1[\s\-*_]*$", ln):
            out.append("<hr>"); i += 1; continue

        # blockquote
        if ln.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>" + render("\n".join(buf)) + "</blockquote>")
            continue

        # lists
        if re.match(r"^\s*([-*+]|\d+[.)])\s+", ln):
            ordered = bool(re.match(r"^\s*\d+[.)]\s+", ln))
            items, cur = [], None
            while i < n and (re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[i])
                            or (cur is not None and lines[i].startswith(("  ", "\t"))
                                and lines[i].strip())):
                m2 = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", lines[i])
                if m2:
                    if cur is not None:
                        items.append(cur)
                    cur = m2.group(1)
                else:
                    cur += " " + lines[i].strip()
                i += 1
            if cur is not None:
                items.append(cur)
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items)
                       + f"</{tag}>")
            continue

        # blank
        if not ln.strip():
            i += 1
            continue

        # paragraph
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|\s*([-*+]|\d+[.)])\s|\s*>|```)", lines[i]) \
                and not ("|" in lines[i] and i + 1 < n
                         and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1])):
            buf.append(lines[i]); i += 1
        if buf:
            out.append("<p>" + _inline(" ".join(buf)) + "</p>")

    return "\n".join(out)


if __name__ == "__main__":
    print(render("# Hi\n\n**bold** and `code`\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n- one\n- two"))
