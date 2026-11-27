#!/usr/bin/env python3
"""PF-12 (code chips): on the emails page the picture's code chip sits ON the picture (the part's crop) and beside it,
one chip form for both; the part header is plain words with a small plain S<n>; a copy hands Claude the start of a
request ("oct-20 P1: ", "oct-20 S2: "), and own_picture.py pick() resolves both copied forms to the right picture.
Static over the template's markup functions. No network, no Chrome, no real run.

    python3 components/page-features/kit/test_pf12_code_chips.py

own_picture is imported by its file path, so nothing but its own folder is on sys.path (components/email-production
holds an email.py that would shadow the standard library's `email`).
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PAGE = os.path.join(REPO, "platform", "views", "viewers", "_templates", "emails.html")
_spec = importlib.util.spec_from_file_location(
    "own_picture", os.path.join(REPO, "components", "email-production", "adapter", "own_picture.py"))
own_picture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(own_picture)

# design/email.json, cut down, PF-11 (part codes S)'s fixture shape: a header with no picture, a hero with one,
# a grid with two
SPEC = {"brand": "brand", "sections": [
    {"s": "header", "logo": "logo.png"},
    {"s": "hero", "picture": {"alt": "the hero", "photo": "run:media/hero.jpg"}},
    {"s": "grid", "cells": [{"picture": {"alt": "left", "todo": "make it"}},
                            {"picture": {"alt": "right", "source": "made"}}]},
]}
ID = "oct-20"
RESULTS = []

with open(PAGE, encoding="utf-8") as fh:
    SRC = fh.read()


def check(name, fn):
    try:
        fn()
        RESULTS.append(True)
        print("PASS  " + name)
    except Exception as e:  # noqa: BLE001
        RESULTS.append(False)
        print("FAIL  %s: %s" % (name, e))


def const(name):
    """The template literal of a one-line `const name=(…)=>`…`;` in the page."""
    m = re.search(r"^const %s=\([^)]*\)=>`(.*)`;$" % re.escape(name), SRC, re.M)
    assert m, "const %s is not a one-line template arrow" % name
    return m.group(1)


def func(name):
    """The source of `function name(…){…}` up to the next top-level function."""
    m = re.search(r"^function %s\(.*?(?=^function |\Z)" % re.escape(name), SRC, re.M | re.S)
    assert m, "function %s not found" % name
    return m.group(0)


def render(tpl, n):
    """A code template with the email id and a number filled in, the way the page fills them."""
    out = tpl.replace("${SHORT(e)}", ID).replace("${picNo(e,s,k)}", str(n)).replace("${s.i+1}", str(n))
    assert "${" not in out, "unfilled placeholder left in %r" % out
    return out


def header():
    ed = func("sectionEditor")
    m = re.search(r'<div class="box" id="secbox">(.*?)id="okGo"', ed, re.S)
    assert m, "section header not found in sectionEditor"
    return m.group(1)


def one_chip_form():
    chip = const("picChip")
    assert chip.count('class="code"') == 1, "picChip makes %d .code chips" % chip.count('class="code"')
    assert 'data-copy="${esc(picAsk(e,s,k))}"' in chip, "picChip's data-copy is not picAsk"
    assert "${esc(picCode(e,s,k))}" in chip, "picChip's visible text is not picCode"
    for fn in ("cropOf", "sectionEditor"):
        body = func(fn)
        assert 'class="code"' not in body, "%s writes its own .code chip instead of picChip" % fn
        assert "picCode(" not in body, "%s builds a picture code itself instead of picChip" % fn
    assert "P.map((p,k)=>picChip(e,s,k))" in func("cropOf"), "the crop does not carry every picture's chip"
    assert re.search(r'<div class="pic" data-feature="22"><span>\$\{picChip\(e,s,k\)\}</span>', func("sectionEditor")), \
        "the chip beside the picture is not picChip"


def chip_on_the_picture():
    crop = func("cropOf")
    assert '<span class="onpic">' in crop and crop.index("<img") < crop.index('<span class="onpic">') < crop.rindex("</div>"), \
        "the chips are not inside the crop, over its picture"
    css = re.search(r"\.crop \.onpic\{([^}]*)\}", SRC)
    assert css and "position:absolute" in css.group(1) and "top:" in css.group(1), "the chip stack is not pinned to a top corner"
    assert "flex-direction:column" in css.group(1), "more than one chip does not stack"
    assert re.search(r"\.crop\{position:relative\}", SRC), "the crop is not the chips' frame"


def plain_header():
    h = header()
    assert 'class="code"' not in h, "the section header still carries a .code chip"
    assert "Part ${" not in h, "the section header still carries a 'Part n' eyebrow"
    assert 'class="eye"' not in h, "the section header still carries an eyebrow"
    assert '${esc(s.kind)}</span><span data-feature="44"> · Section ${s.i+1}</span>' in h, \
        "the header does not read '<kind> · Section <n>'"
    m = re.search(r'<span class="scode" data-feature="51" data-copy="\$\{esc\(partAsk\(e,s\)\)\}"[^>]*>S\$\{s\.i\+1\}</span>', h)
    assert m, "the small plain S<n> with data-copy is missing"
    css = re.search(r"\.scode\{([^}]*)\}", SRC)
    assert css and "border" not in css.group(1) and "background" not in css.group(1), "S<n> is chip-styled"


def copy_forms():
    for n in (1, 2, 12):
        p = render(const("picAsk"), n)
        assert re.fullmatch(r"%s P\d+: " % re.escape(ID), p), "picture copy %r" % p
        s = render(const("partAsk"), n)
        assert re.fullmatch(r"%s S\d+: " % re.escape(ID), s), "section copy %r" % s
    assert render(const("picCode"), 1) == ID + " · P1", "the visible chip text changed"


def placeholder():
    # The picture's change box (25, 53) was removed for everyone (email_lead, 2026-11-03,
    # from editor's 2026-11-04 feedback); picture changes are asked by code in Claude.
    ed = func("sectionEditor")
    assert 'data-pic="' not in ed and "data-picgo" not in ed and "data-own" not in ed, "the picture's change box is back"
    assert "picChip(e,s,k)" in ed, "the picture's code chip is gone"


def flash_unchanged():
    assert ('document.addEventListener("click",ev=>{const c=ev.target.closest("[data-copy]");if(!c)return;'
            'copyText(c.dataset.copy);const o=c.textContent;c.textContent="copied";'
            'setTimeout(()=>{c.textContent=o},900)});') in SRC, "the copied flash changed"


def picks(form_tpl, n, want_p, alt):
    def t():
        code = render(const(form_tpl), n)
        assert code.endswith(": ")
        got = own_picture.pick(SPEC, code[:-2])
        assert got[0] == want_p and got[3]["alt"] == alt, \
            "%r gave P%d (%s), wanted P%d (%s)" % (code[:-2], got[0], got[3]["alt"], want_p, alt)
    return t


def section_of_two_asks_which():
    code = render(const("partAsk"), 3)[:-2]
    try:
        got = own_picture.pick(SPEC, code)
    except SystemExit as e:
        assert "P2" in str(e) and "P3" in str(e), str(e)
        return
    raise AssertionError("%r was not refused (gave P%d)" % (code, got[0]))


check("one chip form per picture: picChip, on the crop and beside it, same data-copy", one_chip_form)
check("the chips sit on the crop's picture, in a top corner, stacked", chip_on_the_picture)
check("section header is plain words, no .code, no 'Part ${' eyebrow, small plain S<n>", plain_header)
check("picture copies '<id> P<n>: ', section copies '<id> S<n>: ', chip text stays '<id> · P<n>'", copy_forms)
check("the picture keeps its code chip; its change box stays removed", placeholder)
check("the 'copied' flash is unchanged", flash_unchanged)
check("copied 'oct-20 P1' picks the hero", picks("picAsk", 1, 1, "the hero"))
check("copied 'oct-20 P2' picks the grid's left picture", picks("picAsk", 2, 2, "left"))
check("copied 'oct-20 P3' picks the grid's right picture", picks("picAsk", 3, 3, "right"))
check("copied 'oct-20 S2' picks the hero (one picture in that part)", picks("partAsk", 2, 1, "the hero"))
check("copied 'oct-20 S3' asks which of P2 and P3", section_of_two_asks_which)

print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
