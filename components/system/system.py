#!/usr/bin/env python3
"""The system: its words, its components, and the check that keeps them connected.

    python3 components/system/system.py check            # is everything connected, named once, owned once?
    python3 components/system/system.py word <term>      # the one meaning of a word, or what to call it instead
    python3 components/system/system.py place <folder>   # the row a new component needs before it joins
    python3 components/system/system.py map              # every component by workflow and stage
    python3 components/system/system.py export           # words + components + coverage as JSON (for a page)

system.json holds the words. components.json holds every component, once. The
roles are in components/roles/roles.json. All three are brand-agnostic. Reads only.
"""
import argparse
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SYSTEM = HERE / "system.json"
COMPONENTS = HERE / "components.json"
STAGE_LIST = ROOT / "components" / "naming" / "stages.json"
SKIP = {"__pycache__"}


def roles_mod():
    spec = importlib.util.spec_from_file_location("roles", ROOT / "components" / "roles" / "roles.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load():
    return json.loads(SYSTEM.read_text()), json.loads(COMPONENTS.read_text())["components"]


def folders():
    """Every component folder that exists (a link counts: it is still one folder to place)."""
    comp = ROOT / "components"
    return sorted("components/" + p.name for p in comp.iterdir()
                  if p.is_dir() and not p.name.startswith((".", "_")) and p.name not in SKIP)


def stage_names(system):
    names = set(system["stages"]["order"])
    if STAGE_LIST.exists():
        names |= {s["name"].lower() for s in json.loads(STAGE_LIST.read_text()).get("stages", [])}
    return names


def coverage(system, comps):
    R = roles_mod()
    roles = R.load()
    role_ids = {r["id"] for r in roles["roles"]}
    kinds = {k["id"] for k in system["kinds"]}
    chains = {c["id"] for c in system["workflows"]}
    stages = stage_names(system)
    problems, seen = [], {}
    for c in comps:
        p = c.get("path", "")
        if p in seen:
            problems.append(f"two rows claim {p}")
        seen[p] = c
        if not (ROOT / p).exists():
            problems.append(f"{p}: the folder is not there")
        if c.get("kind") not in kinds:
            problems.append(f"{p}: kind '{c.get('kind')}' is not one of {', '.join(sorted(kinds))}")
        if c.get("role") not in role_ids:
            problems.append(f"{p}: role '{c.get('role')}' is not a role")
        if c.get("workflow") not in chains:
            problems.append(f"{p}: workflow '{c.get('workflow')}' is not a workflow")
        if c.get("workflow") != "system" and c.get("stage") not in stages:
            problems.append(f"{p}: stage '{c.get('stage')}' is not a stage")
        if not c.get("does"):
            problems.append(f"{p}: says nothing under 'does'")
    for f in folders():
        if f not in seen and not any(k.startswith(f + "/") for k in seen):
            problems.append(f"{f} has no row: it is not connected to anything")
    for t in R.listed_tools():
        if t not in seen:
            problems.append(f"{t} is in the tool list but has no row")

    words = {}
    for w in system["words"]:
        k = w["word"].lower()
        if k in words:
            problems.append(f"the word '{w['word']}' is defined twice")
        words[k] = w
    for s in system["same_thing"]:
        if s["keep"].lower() not in words:
            problems.append(f"'{s['keep']}' is kept as a name but has no meaning written")

    rc = R.coverage(roles)
    problems += rc["problems"]
    return {
        "problems": problems,
        "components": len(comps),
        "folders": len(folders()),
        "draft_rows": [c["path"] for c in comps if c.get("basis") == "draft"],
        "words": len(words),
        "retire": sum(len(w.get("retire", [])) for w in system["words"]),
        "roles": rc,
    }


def cmd_check(_a):
    system, comps = load()
    c = coverage(system, comps)
    print(f"{c['components']} components, each with one row · {c['words']} words, one meaning each · "
          f"{c['roles']['roles']} roles, one number each")
    print(f"Rows placed as a first draft: {len(c['draft_rows'])} · other uses of a word still to retire: {c['retire']}")
    if c["problems"]:
        print("\nFIX:")
        for p in c["problems"]:
            print(" - " + p)
        sys.exit(1)
    print("OK")


def cmd_word(a):
    system, _ = load()
    q = a.term.strip().lower()
    for w in system["words"]:
        if w["word"].lower() == q:
            print(f"{w['word']}: {w['means']}")
            if w.get("list"):
                print(f"The list lives in: {w['list']}")
            for r in w.get("retire", []):
                print(f"  not: {r}")
            return
    hits = [(w["word"], r) for w in system["words"] for r in w.get("retire", []) if q in r.lower()]
    hits += [(s["keep"].capitalize(), f"another name for: {s['thing'].lower()}") for s in system["same_thing"] if q in [n.lower() for n in s["names"]]]
    if not hits:
        sys.exit(f"'{a.term}' is not a system word. If it is a creative word, see 'elsewhere' in system.json.")
    print(f"'{a.term}' is not kept as its own word. Say:")
    for word, why in dict(hits).items():
        print(f"  {word}  ({why})")


def cmd_place(a):
    system, comps = load()
    p = a.folder.strip().rstrip("/")
    if not p.startswith("components/") and "/" not in p:
        p = "components/" + p
    row = next((c for c in comps if c["path"] == p), None)
    if row:
        print(json.dumps(row, indent=1))
        print("\nAlready connected." + ("" if (ROOT / p).exists() else " But the folder is missing."))
        return
    print(f"{p} is not connected. Add this row to components/system/components.json, filled in:\n")
    print(json.dumps({"path": p, "kind": " | ".join(k["id"] for k in system["kinds"]), "does": "<what it does, in a few words>",
                      "role": "<a role id: roles.py list>", "workflow": " | ".join(c["id"] for c in system["workflows"]),
                      "stage": " | ".join(system["stages"]["order"]) + " (empty when workflow is system)",
                      "steps": [], "basis": "source"}, indent=1))
    print("\nThen: system.py check. " + system["connect"]["rule"])


def grid(system, comps):
    order = system["stages"]["order"]
    out = []
    for ch in system["workflows"]:
        row = {"chain": ch, "cells": {}}
        for c in comps:
            if c["workflow"] != ch["id"]:
                continue
            key = c["stage"] if ch["id"] != "system" else c["kind"]
            row["cells"].setdefault(key, []).append(c)
        out.append(row)
    return order, out


def cmd_map(_a):
    system, comps = load()
    order, rows = grid(system, comps)
    for row in rows:
        print(f"\n{row['chain']['name'].upper()}")
        keys = order if row["chain"]["id"] != "system" else [k["id"] for k in system["kinds"]]
        for k in keys:
            cs = row["cells"].get(k, [])
            if cs:
                print(f"  {k:<11} " + ", ".join(f"{c['path'].split('/', 1)[1]} ({c['role']})" for c in cs))


def cmd_export(_a):
    system, comps = load()
    print(json.dumps({"system": system, "components": comps, "coverage": coverage(system, comps)}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    p = sub.add_parser("word"); p.add_argument("term"); p.set_defaults(fn=cmd_word)
    p = sub.add_parser("place"); p.add_argument("folder"); p.set_defaults(fn=cmd_place)
    sub.add_parser("map").set_defaults(fn=cmd_map)
    sub.add_parser("export").set_defaults(fn=cmd_export)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
