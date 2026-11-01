"""THE HOOK IS A FORMAT (2026-09-25).

the owner: "we're building out a format. It's a type of hook. There's a reason the
hook works, so we don't want to reinvent it. All we want to do is adjust its
variables a bit … all other variations of this headline need to follow that
format, and we just inject words from our language bank."

The hooks pass (v16) prints the source's opening as a format — its own words
with named [BLANKS] — and every version as that format filled:

    FORMAT LINE: I'm at [PLACE], which is crazy because I'm going to ask them about [PROBLEM].
    LINE V0: I'm at <our place>, which is crazy because I'm going to ask them about <our problem>.

This checks, without a model:
  1. the FORMAT LINE's fixed words are the source's own words, in order (the
     first line of the verbatim transcript) — the format may not paraphrase it;
  2. the FORMAT CARD's fixed words are the source card's own (teardown layer sheet);
  3. no blank swallowed the source's own words — two or more words the source and
     our control share at a blank's edge are the format's, not the blank's;
  4. every LINE Vn and CARD Vn keeps every fixed word of its format, in order.
A version that breaks it is returned as a finding (H0…H5, C0…C5); run.py holds
the step for the owner, who may pass one by number (`--approve-structure H3`).

Brand-agnostic: reads only the pass's own output and the run's transcript.
"""
import json, re, sys
from pathlib import Path

BLANK = re.compile(r"\[[^\]]*\]")


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[^a-z0-9\[\] ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def labelled(body, label):
    """The text after `LABEL:` on its own line, markdown stripped."""
    m = re.search(rf"^[\s>*`_-]*{re.escape(label)}\s*[*`_]*\s*:?\s*[*`_]*\s*(.+?)\s*[*`_]*\s*$", body, re.M | re.I)
    if not m:
        return None
    v = m.group(1).strip().strip("`*_ ").strip('"“”')
    return v


def fixed_parts(fmt):
    return [p for p in (norm(x) for x in BLANK.split(fmt)) if p]


def fits(fmt, line):
    parts = fixed_parts(fmt)
    if not parts:
        return True
    pat = r"(?:^|.*?\b)" + r".*?".join(re.escape(p) for p in parts)
    return re.match(pat, norm(BLANK.sub(" x ", line)), re.S) is not None


def fills(fmt, line):
    """What each blank holds in a line that fits the format, in order (normalised)."""
    parts = [norm(x) for x in BLANK.split(fmt)]
    pat = "^" + "(.*?)".join(re.escape(p) for p in parts) + "$"
    m = re.match(pat.replace(r"\ ", r"\s*"), norm(line))
    return [g.strip() for g in m.groups()] if m else None


def swallowed(fmt, src, ctrl):
    """Words a blank took from the source that the control keeps too — those are
    the format's own words and belong outside the blank ("STILL NOT RUSHING MY
    HOME" → "STILL NOT SELLING MY HOME": "my home" is fixed). Two words or more, at either edge."""
    a, b = fills(fmt, src), fills(fmt, ctrl)
    if not a or not b:
        return []
    out = []
    for x, y in zip(a, b):
        if x == y:          # the control kept the source's fill whole — nothing to lift out
            continue
        xw, yw = x.split(), y.split()
        pre = 0
        while pre < min(len(xw), len(yw)) and xw[pre] == yw[pre]:
            pre += 1
        suf = 0
        while suf < min(len(xw), len(yw)) - pre and xw[-1 - suf] == yw[-1 - suf]:
            suf += 1
        if pre >= 2:
            out.append(" ".join(xw[:pre]))
        if suf >= 2:
            out.append(" ".join(xw[-suf:]))
    return out


def repair(run_dir, body):
    """Mechanical fix, no model: words a blank swallowed at its edge are moved out
    of it, in the printed format, when the source and the control share them.
    Returns (body, notes). Only the FORMAT line changes; the versions already
    carry the words."""
    notes = []
    for label, orig, ctrl in (("FORMAT LINE", source_opening(run_dir, labelled(body, "FORMAT LINE")), labelled(body, "LINE V0")),
                              ("FORMAT CARD", source_card(run_dir), labelled(body, "CARD V0"))):
        fmt = labelled(body, label)
        if not fmt or not orig or not ctrl or norm(fmt) == "none":
            continue
        a, b = fills(fmt, orig), fills(fmt, ctrl)
        if not a or not b:
            continue
        new, blanks = fmt, BLANK.findall(fmt)
        for blank, x, y in zip(blanks, a, b):
            if x == y:
                continue
            xw, yw = x.split(), y.split()
            suf = 0
            while suf < min(len(xw), len(yw)) - 1 and xw[-1 - suf] == yw[-1 - suf]:
                suf += 1
            if suf >= 2:
                # the control's own words, in its own casing
                words = [w for w in (w.strip(".,!?;:") for w in ctrl.split()) if w][-suf:]
                new = new.replace(blank, blank + " " + " ".join(words), 1)
                notes.append(f"{label}: \"{' '.join(words)}\" moved out of {blank} — the swipe and our control both say it")
        if new != fmt:
            body = body.replace(fmt, new)
    return body, notes


def source_card(run_dir):
    """The opening's on-screen words, from the teardown record's layer sheet."""
    t = Path(run_dir) / "stages" / "1-teardown.md"
    if not t.exists():
        return None
    text = t.read_text()
    m = re.search(r"Hook text:\s*(.+?)\s*(?:\||$)", text, re.M)
    card = m.group(1).strip() if m else None
    if card and norm(card) not in ("none", ""):
        return card
    # No hook text — but the opening can still carry a card as a layer: a
    # platform comment-reply sticker, a stitched caption (found 2026-09-28 on
    # a proven ad whose whole card was a comment reply). The first quoted layer
    # on screen in the opening second is the card.
    sheet = text.split("**Layer sheet**", 1)[-1].split("**Sound sheet**", 1)[0]
    for lm in re.finditer(r"^\*\s+0:0(\d)(?:\.\d)?\s*·[^\n]*?\"(.+?)\"\s*$", sheet, re.M):
        if int(lm.group(1)) <= 1:
            return lm.group(2).strip()
    return card


def source_opening(run_dir, fmt=None):
    """The source's opening line — T1, or T1 run on through the next two lines
    when the format spans them. An opening beat can be two transcript turns
    ("Ladies and gentlemen, I need y'all to understand something." / "This man
    right here had a strong eye for talent."); checking the format against T1
    alone held a format that was word for word the source's own (2026-10-05,
    BRAND-A FLEX rebuild). Still the source's words, in order, from its first
    line — never a line from later in the swipe."""
    tj = Path(run_dir) / "transcript.json"
    if not tj.exists():
        return None
    lines = json.loads(tj.read_text())
    if not lines:
        return None
    # WHERE THE AD STARTS (the owner, 2026-10-09): a run opened later in the swipe (`--open-at`, run.json
    # `opening_at`) has its source opening at that line, not at T1.
    rj = Path(run_dir) / "run.json"
    at = norm((json.loads(rj.read_text()).get("opening_at") or "") if rj.exists() else "")
    if at:
        i = next((i for i, ln in enumerate(lines) if at[:40] in norm(ln.get("text") or "")
                  or norm(ln.get("text") or "")[:40] in at), None)
        if i is not None:
            lines = lines[i:]
    text = lines[0].get("text") or ""
    if fmt:
        joined = text
        for ln in lines[1:3]:
            if fits(fmt, joined):
                return joined
            joined = f"{joined} {ln.get('text') or ''}".strip()
        if fits(fmt, joined):
            return joined
    return text


# WHAT THE OPENING IS (the owner, 2026-10-09: "if something doesn't have a written hook or a voice hook … that's fine.
# It's just that you still should be making scroll stoppers" — the Cellimure 3D swipes opened on music and a "Hmm.",
# and every wordless version was held as "the control with words swapped"). Read off the swipe, never the pass:
# an opening is SPOKEN only when a line in its first seconds carries real words — not a sound in brackets, not an
# interjection, not a line the speech model barely heard (background TV the words model filled in).
OPENING_SECS = 3.5    # the hook window, from the first frame
INTERJECTIONS = {"hmm", "hm", "mm", "mhm", "uh", "um", "oh", "ah", "huh", "ooh", "aah", "eh", "ha", "haha", "wow", "whoa"}


def _real_words(ln):
    words = [w for w in norm(re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", ln.get("text") or "")).split() if w not in INTERJECTIONS]
    if "heard-differently" in (ln.get("flags") or []):
        heard = [w for w in norm(ln.get("scribe_heard") or "").split() if w not in INTERJECTIONS]
        if len(heard) * 2 < len(words):     # the words are the model's guess at noise, not a line anyone says
            return []
    return words


def opening(run_dir):
    """{"spoken": bool, "card": bool} for the swipe's opening. No transcript → spoken (the old behaviour)."""
    card = bool(source_card(run_dir))
    tj = Path(run_dir) / "transcript.json"
    if not tj.exists():
        return {"spoken": True, "card": card}
    lines = json.loads(tj.read_text()) or []
    early = [ln for ln in lines if (ln.get("start") or 0) <= OPENING_SECS]     # the first seconds of the VIDEO
    return {"spoken": any(len(_real_words(ln)) >= 2 for ln in early), "card": card}


def _none(s):
    return s is None or norm(s) in ("", "none") or norm(s).startswith("none ")


# FIVE DISTINCT TAKES (the owner, 2026-10-09: "unique scroll stoppers and unique hooks and unique thumbnails per
# variation to clearly have diverse takes into the ad itself" — the LeBron set came back as one sentence with one
# word swapped six times). Only the control is held to the swipe's format; every variation prints its own five
# slots, and two that are near-copies of each other (or of the control) are held.
SLOTS = ("TAKE", "LINE", "CARD", "SCROLL", "THUMB")
ALIKE = 0.6        # share of words two slots may have in common before they read as the same take


def _words(s):
    return {w for w in norm(s or "").split() if len(w) > 2}


def alike(a, b):
    x, y = _words(a), _words(b)
    return bool(x and y) and len(x & y) / min(len(x), len(y)) > ALIKE


def takes(body, spoken=True, card=True):
    """Findings for the five variations: every slot printed, none a near-copy of another or of the control.
    A wordless opening carries no LINE and a cardless one no CARD: `none` there is the swipe, and the take
    lives in its SCROLL and THUMB, which still have to differ."""
    out, got = [], {}
    quiet = {sl for sl, on in (("LINE", spoken), ("CARD", card)) if not on}
    for v in range(1, 6):
        for sl in SLOTS:
            val = labelled(body, f"{sl} V{v}")
            if sl in quiet and val is not None and _none(val):
                continue
            if val is None or (sl in ("CARD", "SCROLL", "THUMB") and norm(val) in ("", "none")):
                out.append({"n": f"{sl[0]}{v}", "element": f"version {v}", "status": "Dropped",
                            "why": f"no `{sl} V{v}:` printed — every variation carries its own {sl.lower()}"})
            else:
                got[(sl, v)] = val
    for sl in ("LINE", "SCROLL", "THUMB", "CARD"):
        ctrl = labelled(body, f"{sl} V0")
        for v in range(1, 6):
            a = got.get((sl, v))
            if a is None:
                continue
            if a.lstrip().startswith("["):
                continue    # a slot the format fills later (a sung line on a song swipe): the take lives in its other slots
            if sl in ("LINE", "SCROLL") and ctrl and alike(a, ctrl):
                out.append({"n": f"{sl[0]}{v}", "element": f"{sl} V{v}: {a[:80]}", "status": "Adapted",
                            "why": f"reads as the control's {sl.lower()} with words swapped — a variation is its own take"})
            for w in range(1, v):
                b = got.get((sl, w))
                if b is not None and alike(a, b):
                    out.append({"n": f"{sl[0]}{v}", "element": f"{sl} V{v}: {a[:80]}", "status": "Adapted",
                                "why": f"reads as V{w}'s {sl.lower()} with words swapped — every variation is its own take"})
                    break
    return out


def check(run_dir, body):
    """(formats, findings). A finding: {n, element, status, why} — the same shape
    as the structure lock's, so the same approvals and page read it."""
    out = []
    fl, fc = labelled(body, "FORMAT LINE"), labelled(body, "FORMAT CARD")
    op = opening(run_dir)
    if not op["spoken"] and (fl is None or _none(fl)):
        # A WORDLESS OPENING: no line to lock, no blanks to name — the hook is the scroll stopper.
        out += takes(body, spoken=False, card=op["card"])
        src_card, cd = source_card(run_dir), labelled(body, "CARD V0")
        if fc and not _none(fc) and src_card:      # the card, when the swipe has one, is still the swipe's own
            if not fits(fc, src_card):
                out.append({"n": "CF", "element": f"FORMAT CARD: {fc}", "status": "Adapted",
                            "why": f"its fixed words are not the source's own, in order — the source's card says: \"{src_card}\""})
            elif cd is not None and not _none(cd) and not fits(fc, cd):
                out.append({"n": "C0", "element": f"CARD V0: {cd}", "status": "Adapted",
                            "why": f"the control breaks the card format — every fixed word of \"{fc}\" must stay, in order"})
        if labelled(body, "SCROLL V0") is None:
            out.append({"n": "S0", "element": "version 0", "status": "Dropped",
                        "why": "a wordless opening still needs its scroll stopper — no `SCROLL V0:` printed"})
        return {"line": "none", "card": fc, "frame": labelled(body, "FORMAT FRAME"), "elements": [],
                "opening": "wordless"}, out
    if not fl:
        return {}, [{"n": "H", "element": "the hooks printed no FORMAT LINE", "status": "Dropped",
                     "why": "the hook pass must print the source's opening as a format before filling it (prompt v16)"}]
    src = source_opening(run_dir, fl)
    if src and not fits(fl, src):
        out.append({"n": "HF", "element": f"FORMAT LINE: {fl}", "status": "Adapted",
                    "why": f"its fixed words are not the source's own, in order — the source says: \"{src}\""})
    for label, fmt, orig, ctrl in (("LINE", fl, src, labelled(body, "LINE V0")),
                                   ("CARD", fc, source_card(run_dir), labelled(body, "CARD V0"))):
        if not fmt or norm(fmt) == "none" or not orig:
            continue
        if label == "CARD" and not fits(fmt, orig):
            out.append({"n": "CF", "element": f"FORMAT CARD: {fmt}", "status": "Adapted",
                        "why": f"its fixed words are not the source's own, in order — the source's card says: \"{orig}\""})
        gone = swallowed(fmt, orig, ctrl or "")
        if gone:
            out.append({"n": f"{label[0]}F", "element": f"FORMAT {label}: {fmt}", "status": "Adapted",
                        "why": f"a blank swallowed the source's own words ({'; '.join(gone)}) — they stay fixed, outside the blank"})
    ln0 = labelled(body, "LINE V0")
    if ln0 is None:
        out.append({"n": "H0", "element": "version 0", "status": "Dropped", "why": "no `LINE V0:` printed"})
    elif not fits(fl, ln0):
        out.append({"n": "H0", "element": f"LINE V0: {ln0}", "status": "Adapted",
                    "why": f"the control breaks the format — every fixed word of \"{fl}\" must stay, in order"})
    if fc and norm(fc) != "none":
        cd = labelled(body, "CARD V0")
        if cd is not None and norm(cd) != "none" and not fits(fc, cd):
            out.append({"n": "C0", "element": f"CARD V0: {cd}", "status": "Adapted",
                        "why": f"the control breaks the card format — every fixed word of \"{fc}\" must stay, in order"})
    out += takes(body)
    # EVERY BLANK IS A NAMED ELEMENT (the owner, 2026-09-25: "everything needs to be its
    # own unique element"). The pass prints one ELEMENTS line per element; every
    # blank in the formats must be one of them.
    m = re.search(r"ELEMENTS\s*[*`_]*\s*:?.*?\n(.*?)(?=\n\s*\n\s*(?:#|\*\*\d|---)|\Z)", body, re.S)
    els = [l.strip("-*` ").strip() for l in (m.group(1).splitlines() if m else []) if l.strip().startswith(("-", "*", "`", "["))]
    named = set(re.findall(r"\[([A-Z][A-Z0-9 '’/-]*)\]", "\n".join(els)))
    blanks = {b.strip("[]") for f in (fl, fc) if f for b in BLANK.findall(f) if not b.upper().startswith("[RESEARCH")}
    missing = sorted(b for b in blanks if b not in named)
    if not els:
        out.append({"n": "E", "element": "no ELEMENTS printed", "status": "Dropped",
                    "why": "every blank is a named element with what it must hold (prompt v16, rule 4)"})
    elif missing:
        out.append({"n": "E", "element": f"blanks with no ELEMENTS line: {', '.join(missing)}", "status": "Dropped",
                    "why": "every blank is a named element with what it must hold (prompt v16, rule 4)"})
    return {"line": fl, "card": fc, "frame": labelled(body, "FORMAT FRAME"), "elements": els}, out


if __name__ == "__main__":
    d = Path(sys.argv[1])
    f = Path(sys.argv[2]) if len(sys.argv) > 2 else d / "stages" / "4b-hooks.md"
    fm, found = check(d, f.read_text())
    print(json.dumps({"format": fm, "findings": found}, indent=1, ensure_ascii=False))
