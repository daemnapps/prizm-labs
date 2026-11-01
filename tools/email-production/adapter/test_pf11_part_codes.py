#!/usr/bin/env python3
"""PF-11 (part codes S): the emails page labels a part "nov-02 · S1" (never "part 1", which reads as picture P1),
and own_picture.py reads an S address S<part>.<picture> counted from 1, the way the page shows it. The old raw
0-based s5.0 is retired: a 0 in either place is refused naming the 1-based form. P codes are unchanged.
No network, no Chrome, no real run.

    python3 tools/email-production/adapter/test_pf11_part_codes.py

own_picture is imported by its file path, so nothing but this folder is on sys.path (tools/email-production
holds an email.py that would shadow the standard library's `email`). Its main() is __main__-guarded.
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
_spec = importlib.util.spec_from_file_location("own_picture", os.path.join(HERE, "own_picture.py"))
own_picture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(own_picture)

# design/email.json, cut down: a header with no picture, a hero with one, a grid with two
SPEC = {"brand": "brand", "sections": [
    {"s": "header", "logo": "logo.png"},
    {"s": "hero", "picture": {"alt": "the hero", "photo": "run:media/hero.jpg"}},
    {"s": "grid", "cells": [{"picture": {"alt": "left", "todo": "make it"}},
                            {"picture": {"alt": "right", "source": "made"}}]},
]}
RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append(True)
        print("PASS  " + name)
    except Exception as e:  # noqa: BLE001
        RESULTS.append(False)
        print("FAIL  %s: %s" % (name, e))


def resolves(code, n, alt):
    def t():
        got = own_picture.pick(SPEC, code)
        assert got[0] == n and got[3]["alt"] == alt, "%r gave P%d (%s), wanted P%d (%s)" % (code, got[0], got[3]["alt"], n, alt)
    return t


def refused(code, *must):
    def t():
        try:
            got = own_picture.pick(SPEC, code)
        except SystemExit as e:
            said = str(e)
            for w in must:
                assert w in said, "%r refused without %r: %s" % (code, w, said)
            return
        raise AssertionError("%r was not refused (gave P%d)" % (code, got[0]))
    return t


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


def page_codes(rel):
    def t():
        page = read(rel)
        assert "· S${s.i+1}" in page, "partCode does not read S${s.i+1}"
        assert "· part ${" not in page, "the old '· part ${…}' label is still there"
        assert re.search(r"const partCode=\(e,s\)=>`\$\{SHORT\(e\)\} · S\$\{s\.i\+1\}`;", page), "partCode line changed shape"
        assert "const picCode=(e,s,k)=>`${SHORT(e)} · P${picNo(e,s,k)}`;" in page, "picCode changed"
    return t


def help_line():
    page = read("platform/views/viewers/_templates/emails.html")
    line = next((x for x in page.splitlines() if "Every part and picture has a short code" in x), "")
    assert line, "help line missing"
    assert "oct-20 · S3" in line and "oct-20 · P2" in line, "help line lacks an S and a P example"
    assert "S is a part, P is a picture" in line, "help line does not say which is which"


def machine_bracket_kept():
    page = read("platform/views/viewers/_templates/emails.html")
    assert "`, section ${s.i}`+(c.picture!=null?`, picture ${c.picture}`" in page, "ask()'s raw bracket changed"


check("S2.1 is the hero (P1)", resolves("S2.1", 1, "the hero"))
check("s2.1 is the hero (P1)", resolves("s2.1", 1, "the hero"))
check("nov-02 · S2.1 is the hero (P1)", resolves("nov-02 · S2.1", 1, "the hero"))
check("nov-02 S2.1 is the hero (P1)", resolves("nov-02 S2.1", 1, "the hero"))
check("S3.1 is P2", resolves("S3.1", 2, "left"))
check("S3.2 is P3", resolves("S3.2", 3, "right"))
check("S2 alone is P1 (one picture in that part)", resolves("S2", 1, "the hero"))
check("S3 alone is refused, listing P2 and P3", refused("S3", "P2", "P3", "S3.1", "S3.2"))
check("S1 is refused: no picture in that part", refused("S1", "no picture in part S1"))
check("S1.1 is refused: no picture in that part", refused("S1.1", "no picture in part S1"))
check("s0.0 is refused naming the 1-based form", refused("s0.0", "count from 1", "S1.1"))
check("S2.0 is refused naming the 1-based form", refused("S2.0", "count from 1", "S3.1"))
check("S0 is refused naming the 1-based form", refused("S0", "count from 1"))
check("S3.3 is refused, listing that part's pictures", refused("S3.3", "P2", "P3"))
check("S4 is refused: no such part", refused("S4", "no part S4", "3 parts"))
check("P2 is unchanged", resolves("P2", 2, "left"))
check("2 is unchanged", resolves("2", 2, "left"))
check("nov-02 · P3 is unchanged", resolves("nov-02 · P3", 3, "right"))
check("P4 is refused as before", refused("P4", "no picture"))


def list_rows():
    rows = [{"code": "x · P%d" % n, "s": "x · S%d.%d" % (i + 1, j + 1)} for n, i, j, d in own_picture.slots(SPEC)]
    assert [r["s"] for r in rows] == ["x · S2.1", "x · S3.1", "x · S3.2"], rows
    for r in rows:   # every row's S address resolves back to its own P code
        assert own_picture.pick(SPEC, r["s"])[0] == own_picture.pick(SPEC, r["code"])[0], r
    src = read("tools/email-production/adapter/own_picture.py")
    assert '"s": "%s · S%d.%d" % (short, i + 1, j + 1)' in src, "list rows do not carry the 1-based S address"
    assert "s5.0 (section number as in design/email.json" not in src, "the docstring still teaches the raw s5.0"


check("list shows each picture's 1-based S address beside its P code", list_rows)
check("template partCode reads S, picCode unchanged", page_codes("platform/views/viewers/_templates/emails.html"))
check("the team's draft partCode reads S", page_codes("platform/views/viewers/steph/drafts/emails--final.html"))
check("help line names an S part and a P picture", help_line)
check("ask()'s machine bracket keeps the raw indexes", machine_bracket_kept)
def feature_51():
    note = "oct-20 · S6 (a part), oct-20 · P2 (a picture)"
    assert note in read("platform/views/viewers/_templates/emails.features.json"), "feature 51's note not updated"
    assert note in read("platform/views/viewers/_templates/emails.html"), "the page's features block was not re-synced"


check("feature 51's note names S and P, and the page carries it", feature_51)

print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
