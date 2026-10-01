#!/usr/bin/env python3
"""Reading an answer the way a model writes one.

A slot's heading is accepted as `#`–`####` or bold, with or without a colon,
with or without a number in front. A slot's data block is accepted as a fence
tagged with the slot's name, as the slot's heading over a plain or ```json
fence, or as a bare JSON object that holds one of the expected keys. Nothing
here knows what any slot means.
"""
import json
import re


def _head(name):
    n = re.escape(name)
    return re.compile(rf"^[ \t]*(?:#{{1,4}}[ \t]*\**|\*\*)[ \t]*(?:\d+[.)][ \t]*)?{n}\b[^\n]*$", re.M | re.I)


ANY_HEAD = re.compile(r"^[ \t]*(?:#{1,4}[ \t]+\S|\*\*[A-Z][^a-z\n]{3,}\*\*[ \t]*:?[ \t]*$)", re.M)


def _json_object(s):
    try:
        got = json.loads(s)
    except ValueError:
        return None
    return got if isinstance(got, dict) else None


def block(text, tag, aliases=(), keys=()):
    """The JSON object a slot carries, however it was fenced. Raises ValueError
    saying what is wrong."""
    text = text or ""
    body = None
    for name in (tag, *aliases):
        m = re.search(rf"```[ \t]*{re.escape(name)}[ \t]*\n(.*?)```", text, re.S | re.I)
        if m:
            body = m.group(1)
            break
    if body is None:
        for name in (tag, *aliases):
            h = _head(name).search(text)
            if h:
                f = re.search(r"```[ \t]*\w*[ \t]*\n(.*?)```", text[h.end():], re.S)
                if f:
                    body = f.group(1)
                    break
    if body is None and keys:
        tries = [f.group(1) for f in re.finditer(r"```[ \t]*\w*[ \t]*\n(.*?)```", text, re.S)]
        a, b = text.find("{"), text.rfind("}")
        if 0 <= a < b:
            tries.append(text[a:b + 1])
        for t in tries:
            got = _json_object(t.strip())
            if got is not None and set(got) & set(keys):
                return got
    if body is None:
        raise ValueError(f"the answer carries no {tag} block")
    got = _json_object(body.strip())
    if got is None:
        raise ValueError(f"the {tag} block is not a valid JSON object")
    return got


def missing_heads(text, heads):
    """Which of the labelled parts the answer does not carry."""
    return [h for h in heads if not _head(h).search(text or "")]


def section(text, name):
    """The words under one heading, up to the next heading."""
    h = _head(name).search(text or "")
    if not h:
        return ""
    rest = text[h.end():]
    nxt = ANY_HEAD.search(rest)
    return (rest[:nxt.start()] if nxt else rest).strip()


def without_block(text, tag, aliases=()):
    """The answer with its data block (and that block's heading) taken out —
    what a person reads."""
    out = text or ""
    for name in (tag, *aliases):
        out = re.sub(rf"```[ \t]*{re.escape(name)}[ \t]*\n.*?```", "", out, flags=re.S | re.I)
        h = _head(name).search(out)
        if h:
            tail = out[h.end():]
            f = re.match(r"\s*```[ \t]*\w*[ \t]*\n.*?```", tail, re.S)
            out = out[:h.start()] + (tail[f.end():] if f else tail)
    return re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"


def bullets(text):
    """The list items under a heading, as plain strings."""
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"^[ \t]*(?:[-*•]|\d+[.)])[ \t]+(.*\S)", line)
        if m:
            out.append(m.group(1).strip())
    return out
