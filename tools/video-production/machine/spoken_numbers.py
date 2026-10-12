#!/usr/bin/env python3
"""spoken_numbers.py — every figure in a line turned into the words a person
says, BEFORE the line goes to the voice or the song model.

the owner, 2026-09-23: "we need to get phonetic spelling for numbers when spoken".
Until today ElevenLabs decided how "$29" was said (its text normalisation was
never pinned). Now the voice and song doors send `apply_text_normalization:
"off"` and the text they send has already been through this file, so there
is ONE decider and it is written down: `spoken-rules.json`, a plain table the
team can read and change. Every row there carries examples; `test_spoken.py`
checks every one.

The SCRIPT keeps its digits — captions still show "$29". Only the text sent
to a model is converted, and the conversion is recorded beside the audio.

    python3 machine/spoken_numbers.py "Only $29.99 — 3× a week, every 28–40 days"
    → Only twenty-nine ninety-nine — three times a week, every twenty-eight to forty days

API:
  say(text) -> str                         the line as it is spoken
  say_logged(text) -> (str, [{from, to}])  plus what changed, for the record
  number_phrases(text) -> [(figure, spoken)] every figure in a line and how it
                                            is said — what the audio gate
                                            listens for
  words(n) -> str                          a whole number in words
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES_FILE = HERE / "spoken-rules.json"

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_SCALES = [(10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")]
_ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth",
        "nine": "ninth", "twelve": "twelfth"}
_DIGIT = ["oh", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_DIGIT_POINT = ["zero"] + _DIGIT[1:]
_FRACTION = {2: ("half", "halves"), 3: ("third", "thirds"), 4: ("quarter", "quarters"),
             5: ("fifth", "fifths"), 8: ("eighth", "eighths"), 10: ("tenth", "tenths")}

_rules_cache: dict | None = None


def rules() -> dict:
    global _rules_cache
    if _rules_cache is None:
        _rules_cache = json.loads(RULES_FILE.read_text())
    return _rules_cache


# ---------------------------------------------------------------- the words

def _under_100(n: int) -> str:
    if n < 20:
        return _ONES[n]
    t, o = divmod(n, 10)
    return _TENS[t] + (f"-{_ONES[o]}" if o else "")


def _under_1000(n: int) -> str:
    h, r = divmod(n, 100)
    if not h:
        return _under_100(r)
    return f"{_ONES[h]} hundred" + (f" {_under_100(r)}" if r else "")


def words(n: int) -> str:
    """A whole number in American words: 1250 → one thousand two hundred fifty."""
    n = int(n)
    if n < 0:
        return "minus " + words(-n)
    if n < 1000:
        return _under_1000(n)
    parts = []
    for size, name in _SCALES:
        if n >= size:
            q, n = divmod(n, size)
            parts.append(f"{words(q)} {name}")
    if n:
        parts.append(_under_1000(n))
    return " ".join(parts)


def hundreds_style(n: int) -> str:
    """1,200 → twelve hundred; 1,250 → twelve hundred fifty. Only for
    1,100–9,999 with a hundreds digit; otherwise the plain words."""
    if 1100 <= n <= 9999 and (n // 100) % 10:
        h, r = divmod(n, 100)
        return f"{_under_100(h)} hundred" + (f" {_under_100(r)}" if r else "")
    return words(n)


def year(n: int) -> str:
    if 2000 <= n <= 2009:
        return words(n)
    hi, lo = divmod(n, 100)
    if lo == 0:
        return f"{_under_100(hi)} hundred"
    return f"{_under_100(hi)} " + (f"oh {_ONES[lo]}" if lo < 10 else _under_100(lo))


def ordinal(n: int) -> str:
    w = words(n)
    head, _, last = w.rpartition(" ")
    pre, dash, tail = last.rpartition("-")
    if tail in _ORD:
        tail = _ORD[tail]
    elif tail.endswith("y"):
        tail = tail[:-1] + "ieth"
    else:
        tail += "th"
    last = f"{pre}{dash}{tail}"
    return f"{head} {last}".strip()


def decimal(s: str) -> str:
    whole, _, frac = s.replace(",", "").partition(".")
    out = words(int(whole or 0))
    if frac:
        out += " point " + " ".join(_DIGIT_POINT[int(d)] for d in frac)
    return out


def number(s: str) -> str:
    """Any figure as written (commas, decimals) in words."""
    s = s.replace(",", "")
    return decimal(s) if "." in s else words(int(s))


def digit_by_digit(s: str) -> str:
    return " ".join(_DIGIT[int(d)] for d in s if d.isdigit())


def money(sym: str, amount: str, mag: str | None = None) -> str:
    one, many, cent, cents = rules()["currency"][sym]
    if mag:
        return f"{number(amount)} {rules()['magnitudes'][mag]} {many}"
    whole_s, _, frac = amount.replace(",", "").partition(".")
    whole = int(whole_s or 0)
    c = int((frac + "00")[:2]) if frac else 0
    if not c:
        return f"{hundreds_style(whole)} {one if whole == 1 else many}"
    if not whole:
        return f"{_under_100(c)} {cent if c == 1 else cents}"
    if whole < 1000:
        # the way a price tag is read: twenty-nine ninety-nine, five oh five
        return f"{words(whole)} " + (f"oh {_ONES[c]}" if c < 10 else _under_100(c))
    return f"{words(whole)} {many} and {_under_100(c)} {cents}"


# ---------------------------------------------------------------- the rules

NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
DASH = r"\s*[–—-]\s*"


def _sub(pattern, fn, text, log, flags=0):
    def repl(m):
        out = fn(m)
        if out != m.group(0):
            log.append({"from": m.group(0).strip(), "to": out.strip()})
        return out
    return re.sub(pattern, repl, text, flags=flags)


def say_logged(text: str) -> tuple[str, list[dict]]:
    r = rules()
    t = text or ""
    log: list[dict] = []
    for sym, rep in (r.get("symbols") or {}).items():
        t = t.replace(sym, rep)

    # fixed phrases
    for k in sorted(r.get("fixed") or {}, key=len, reverse=True):
        t = _sub(r"(?<![\w/])" + re.escape(k) + r"(?![\w/])", lambda m, k=k: r["fixed"][k], t, log)

    # phone numbers — digit by digit, a pause between groups
    t = _sub(r"(?<!\w)\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-](\d{4})(?!\w)",
             lambda m: ", ".join(digit_by_digit(g) for g in m.groups()), t, log)

    # #1
    t = _sub(r"#\s?(\d+)", lambda m: f"number {words(int(m.group(1)))}", t, log)

    cur = "".join(re.escape(c) for c in r["currency"])
    # $300–600 → three hundred to six hundred dollars
    t = _sub(rf"([{cur}])({NUM}){DASH}[{cur}]?({NUM})(?![\w.])",
             lambda m: f"{number(m.group(2))} to {number(m.group(3))} {r['currency'][m.group(1)][1]}",
             t, log)
    # $29 · $29.99 · $1,200 · $10k
    mags = "".join(r["magnitudes"])
    t = _sub(rf"([{cur}])({NUM})([{mags}])?(?![\w])",
             lambda m: money(m.group(1), m.group(2), m.group(3)), t, log)

    # 7:30 · 7:05am · 9:00 · 7pm
    def clock(m):
        h, mm, ap = int(m.group(1)), m.group(2), m.group(3)
        out = words(h)
        if mm is not None:
            mi = int(mm)
            if mi == 0:
                out += "" if ap else " o'clock"
            else:
                out += " " + (f"oh {_ONES[mi]}" if mi < 10 else _under_100(mi))
        if ap:
            out += " " + " ".join(ap.replace(".", "").upper())
        return out
    t = _sub(r"(?<![\w:.])(\d{1,2}):(\d{2})\s?([ap]\.?m\.?)?(?![\w:])", clock, t, log, re.I)
    t = _sub(r"(?<![\w:.])(\d{1,2})()\s?([ap]\.?m\.?)(?!\w)",
             lambda m: clock(type("M", (), {"group": lambda self, i: [None, m.group(1), None, m.group(3)][i]})()),
             t, log, re.I)

    # 4.9/5 → four point nine out of five
    t = _sub(r"(?<![\w/])(\d+\.\d+)/(\d+)(?![\w/])",
             lambda m: f"{number(m.group(1))} out of {number(m.group(2))}", t, log)

    # 1/2 · 3/4 · 2/3
    def frac(m):
        a, b = int(m.group(1)), int(m.group(2))
        if b in _FRACTION and 0 < a < b:
            return f"{words(a)} {_FRACTION[b][0] if a == 1 else _FRACTION[b][1]}"
        return f"{words(a)} out of {words(b)}"
    t = _sub(r"(?<![\w/.])(\d{1,2})/(\d{1,2})(?![\w/])", frac, t, log)

    # SPF 30 · B3 · IPX7 · C14 — letters said as letters; the figure is left
    # as digits here so the range and number rules below say it
    letters = sorted(r.get("letters") or [], key=len, reverse=True)
    multi = [re.escape(x) for x in letters if len(x) > 1]
    if multi:
        t = _sub(rf"(?<![\w])({'|'.join(multi)})\s?(\d+)(?!\w)",
                 lambda m: f"{' '.join(m.group(1).upper())} {m.group(2)}", t, log)
        t = _sub(rf"(?<![\w])({'|'.join(multi)})(?!\w)",
                 lambda m: " ".join(m.group(1).upper()), t, log)
    t = _sub(r"(?<![\w])([A-Z]{1,4})(\d+)(?![\w.])", lambda m: f"{' '.join(m.group(1))} {m.group(2)}", t, log)

    # ranges: 28–40 → 28 to 40 (the figures are said by the rules below)
    t = _sub(rf"(?<![\w.,])({NUM}){DASH}({NUM})(?![\w.,-])",
             lambda m: f"{m.group(1)} to {m.group(2)}", t, log)
    t = _sub(rf"(?<![\w.,])({NUM}){DASH}({NUM})(%)",
             lambda m: f"{m.group(1)} to {m.group(2)}{m.group(3)}", t, log)

    # 2x · 3× → two times
    t = _sub(rf"(?<![\w.])({NUM})\s?[x×X](?!\w)", lambda m: f"{number(m.group(1))} times", t, log)

    # 95% → ninety-five percent
    t = _sub(rf"(?<![\w.])({NUM})\s?%", lambda m: f"{number(m.group(1))} percent", t, log)

    # 1st · 2nd · 23rd
    t = _sub(r"(?<![\w.])(\d+)(st|nd|rd|th)(?!\w)", lambda m: ordinal(int(m.group(1))), t, log, re.I)

    # 40B · 10k
    t = _sub(rf"(?<![\w.])({NUM})([{mags}])(?!\w)",
             lambda m: f"{number(m.group(1))} {r['magnitudes'][m.group(2)]}", t, log)

    # units: 100g · 3.53 fl oz · 1 oz
    units = sorted(r.get("units") or {}, key=len, reverse=True)
    if units:
        alt = "|".join(re.escape(u).replace(r"\ ", r"\s?") for u in units)

        def unit(m):
            u = re.sub(r"\s+", " ", m.group(2))
            one, many = r["units"].get(u) or r["units"].get(u.lower()) or [u, u]
            val = m.group(1)
            return f"{number(val)} {one if val in ('1', '1.0') else many}"
        t = _sub(rf"(?<![\w.])({NUM})\s?({alt})(?![\w])", unit, t, log)

    # 625+ → six hundred twenty-five plus
    t = _sub(rf"(?<![\w.])({NUM})\+", lambda m: f"{number(m.group(1))} plus", t, log)

    # 89101 → eight nine one oh one (a code); 12000 → twelve thousand (a count
    # ends in 00)
    t = _sub(r"(?<![\w.,])(\d{5,})(?![\w.,])",
             lambda m: m.group(1) if m.group(1).endswith("00") else digit_by_digit(m.group(1)), t, log)

    # 1998 → nineteen ninety-eight
    t = _sub(r"(?<![\w.,])(1[1-9]\d\d|20\d\d)(?![\w.,]\d|\d)", lambda m: year(int(m.group(1))), t, log)

    # 4.9 → four point nine; 64 → sixty-four; 12,000 → twelve thousand
    t = _sub(r"(?<![\w.])(\d+\.\d+)(?![\w.]*\d)", lambda m: decimal(m.group(1)), t, log)
    t = _sub(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?![\d])", lambda m: number(m.group(1)), t, log)
    return re.sub(r"[ \t]{2,}", " ", t), log


def say(text: str) -> str:
    return say_logged(text)[0]


def number_phrases(text: str) -> list[tuple[str, str]]:
    """Every figure in the line and the words it is said as — what the audio
    gate listens for. Each (from, to) comes from the rules above, so the gate
    and the voice never disagree about how a number is said."""
    _, log = say_logged(text)
    out = []
    for row in log:
        # a row still carrying digits (a range: "28 to 40") is not the final
        # word — its figures are said by their own rows
        if any(ch.isdigit() for ch in row["from"]) and not any(ch.isdigit() for ch in row["to"]):
            out.append((row["from"], row["to"]))
    return out


def figures_heard(line: str, heard: str) -> list[dict]:
    """[{figure, said, heard_ok}] for every figure in the line — the audio and
    song gates' number check. Heard means its words are in the transcript
    (both sides put through these same rules), or its digits are written
    there as digits (a transcriber may write "29.99" for "twenty-nine
    ninety-nine")."""
    def flat(t):
        return " ".join(re.sub(r"[^\w\s]", " ", t.lower()).split())
    got_words = flat(say(heard or "")).split()
    numberish = set(_ONES) | set(_TENS) | {"hundred", "thousand", "million", "billion", "point", "oh"}

    def said_in(phrase):
        # the words, in a row, and not the tail of a bigger number
        # ("twenty-nine dollars" inside "one hundred twenty-nine dollars" is not $29)
        want = flat(phrase).split()
        for i in range(len(got_words) - len(want) + 1):
            if got_words[i:i + len(want)] == want and (i == 0 or got_words[i - 1] not in numberish):
                return True
        return False
    heard_digits = re.findall(r"\d+", re.sub(r"(?<=\d)[,.](?=\d)", "", heard or ""))
    out = []
    for fig, said in number_phrases(line):
        digits = re.sub(r"\D", "", fig)
        ok = said_in(said) or bool(digits and digits in heard_digits)
        out.append({"figure": fig, "said": said, "heard_ok": ok})
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 3
    print(say(" ".join(argv)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
