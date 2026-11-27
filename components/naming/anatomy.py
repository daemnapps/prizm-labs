#!/usr/bin/env python3
"""The human body, one list (anatomy.json): look a part up, open a group, find the parts a line talks about.

    anatomy.py list | part <id> | find "<words>" | say <part or group>
"""
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

FILE = Path(__file__).resolve().parent / "anatomy.json"


@lru_cache(None)
def _data():
    return json.loads(FILE.read_text())["groups"]


def parts():
    """{part id: part, with its group}"""
    return {p["id"]: dict(p, group=g["id"]) for g in _data() for p in g["parts"]}


def groups():
    return {g["id"]: [p["id"] for p in g["parts"]] for g in _data()}


def open_(name):
    """The parts a name means: a part is itself, a group is all of its parts, anything else is nothing."""
    g = groups()
    return [name] if name in parts() else g.get(name, [])


def find(text):
    """The parts a line talks about, the most exact first: "back of my neck" is the nape, never the neck or the back."""
    t, out = text.lower(), []
    hits = sorted(((m.start(), -len(m.group(0)), i, m.group(0)) for i, p in parts().items() for m in re.finditer(p["words"], t)), key=lambda x: (x[1], x[0]))
    taken = []
    for at, n, i, w in hits:
        span = range(at, at - n)
        if any(x in taken for x in span):
            continue
        taken += list(span)
        if i not in out:
            out.append(i)
    return out


def regions():
    return json.loads(FILE.read_text()).get("regions", {})


def together(name):
    """The parts that may be mentioned with a part (or any part of a group) in one piece: those in a region it sits in."""
    mine = open_(name)
    near = {x for r in regions().values() if any(m in r for m in mine) for x in r}
    return [x for x in parts() if x in near and x not in mine]


def phrases(name):
    """How people say a part (or every part of a group), as plain words to search with."""
    out = []
    for i in open_(name):
        depth, cur, alts = 0, "", []
        for ch in parts()[i]["words"] + "|":
            depth += (ch == "(") - (ch == ")")
            if ch == "|" and not depth:
                alts.append(cur)
                cur = ""
            else:
                cur += ch
        for a in alts:
            a = re.sub(r"\(([^()|]*)(\|[^()]*)?\)\??", lambda m: m.group(1), a)
            a = re.sub(r"\[(.)[^\]]*\]", r"\1", a).replace("\\b", "").replace(".?", " ").replace("?", "").strip()
            a = " ".join(a.split())
            if a and a not in out:
                out.append(a)
    return out


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if a[:1] == ["list"]:
        for g, ps in groups().items():
            print("%-8s %s" % (g, ", ".join(ps)))
    elif a[:1] == ["part"] and len(a) == 2:
        print(json.dumps(parts().get(a[1]), indent=1))
    elif a[:1] == ["say"] and len(a) == 2:
        print(", ".join(phrases(a[1])))
    elif a[:1] == ["find"]:
        print(find(" ".join(a[1:])))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
