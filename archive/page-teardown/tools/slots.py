#!/usr/bin/env python3
"""Reading a labelled slot out of a model's answer — tolerantly.

A prompt asks for `# SECTIONS AS READ` and a fenced ```STRIP block. A model
answers with `## Sections as read`, `**STRIP**` over a ```json fence, or the
bare object under its heading. All of those are the same answer. A too-strict
reader held the email teardown's first real run over exactly this, so every
reader in this tool goes through here.

    heading(name)              a regex for a slot heading, however it was dressed
    json_slot(text, names)     the JSON object filed under any of `names`
"""
import json
import re


def heading(name):
    """`# NAME`, `### Name:`, `**NAME**`, `## **Name**` — one slot heading."""
    words = r"[ \t]+".join(re.escape(w) for w in name.split())
    return re.compile(rf"^[ \t]*(?:#{{1,6}}[ \t]*\**|\*\*)[ \t]*(?:\d+[.)][ \t]*)?{words}[ \t]*:?[ \t]*\**[ \t]*:?[ \t]*$",
                      re.M | re.I)


def _loads(raw):
    raw = raw.strip()
    try:
        return json.loads(raw)
    except ValueError:
        return json.loads(re.sub(r",(\s*[}\]])", r"\1", raw))       # a trailing comma is not a different answer


def _balanced(text, start=0):
    """The first {...} at or after `start`, brace-matched outside strings."""
    i = text.find("{", start)
    if i < 0:
        return None
    depth, in_str, esc = 0, False, False
    for j in range(i, len(text)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    return None


def json_slot(text, names, keys=()):
    """The JSON object under any of `names` (the first is the fence tag).
    Tried in order: a fence tagged with a name · a heading with a name over a
    plain or ```json fence · that heading over a bare object · any fence or
    bare object carrying one of `keys`. Raises ValueError saying what is wrong."""
    text = text or ""
    tried = []
    for n in names:
        tag = r"[ \t_-]*".join(re.escape(w) for w in n.split())
        m = re.search(rf"```[ \t]*{tag}[ \t]*\n(.*?)```", text, re.S | re.I)
        if m:
            tried.append(m.group(1))
    for n in names:
        for h in heading(n).finditer(text):
            rest = text[h.end():]
            nxt = re.search(r"^[ \t]*#{1,6}[ \t]", rest, re.M)
            rest = rest[:nxt.start()] if nxt else rest
            f = re.search(r"```[A-Za-z]*[ \t]*\n(.*?)```", rest, re.S)
            if f:
                tried.append(f.group(1))
            else:
                b = _balanced(rest)
                if b:
                    tried.append(b)
    if keys:
        for f in re.finditer(r"```[A-Za-z]*[ \t]*\n(.*?)```", text, re.S):
            if any(f'"{k}"' in f.group(1) for k in keys):
                tried.append(f.group(1))
        b = _balanced(text)
        if b and any(f'"{k}"' in b for k in keys):
            tried.append(b)
    if not tried:
        raise ValueError(f"the answer carries no {names[0]} block")
    err = None
    for raw in tried:
        try:
            got = _loads(raw)
        except ValueError as e:
            err = e
            continue
        if isinstance(got, dict):
            return got
        err = "it is not a JSON object"
    raise ValueError(f"the {names[0]} block is not valid JSON ({err})")
