"""THE LINES — Gemini's words laid on Scribe's speakers and timings.

Each listener is used for what it proved good at on 2026-09-25:
    Gemini   the words, in every language, exactly as said
    Scribe   who is speaking, and exactly when

Out: numbered lines T1, T2… — {id, speaker, start, end, text, language, also,
flags} — the same shape the video chain's transcript.json already uses, plus
the language. Every line where the two listeners disagree carries a flag, so
a person can hear who was right; nothing is silently chosen.

Pure code, no network — tests/test_lines.py runs it on fixtures.
"""
import difflib
import re

CJK = {"zh", "ja"}


def norm(text):
    """Comparable tokens: Latin and Cyrillic words, Korean words, and each
    Chinese or Japanese character on its own — those scripts put no spaces
    between words, so a character is the only unit two listeners share."""
    t = text.lower().replace("’", "'")
    return re.findall(r"[぀-ヿ一-鿿]|[a-z0-9'а-яё]+|[가-힣]+", t)


def count_words(text, lang):
    """Words for the language share. Chinese and Japanese have no spaces, so
    characters stand in (about 1.5 per word)."""
    if lang in CJK:
        return max(1, round(len(re.findall(r"[぀-ヿ一-鿿]", text)) / 1.5))
    return len(re.findall(r"\w+", text))


# Scribe answers in three-letter codes (eng, spa, kor); Gemini in two (en, es, ko).
ISO3 = {"eng": "en", "spa": "es", "kor": "ko", "cmn": "zh", "zho": "zh", "yue": "zh", "jpn": "ja", "rus": "ru",
        "por": "pt", "fra": "fr", "deu": "de", "ita": "it", "hin": "hi", "ara": "ar", "vie": "vi", "tha": "th",
        "tgl": "tl", "fil": "tl", "ind": "id", "tur": "tr", "pol": "pl", "nld": "nl", "ukr": "uk", "heb": "he"}


def two(code):
    code = (code or "").lower()
    return ISO3.get(code, code[:2])


def merge(gem, scribe_words, scribe_lang=None, total=0.0):
    """gem: Gemini lines. scribe_words: Scribe words + audio events.

    Lined up by WHAT WAS SAID, not by Gemini's timestamps — those drift, and on
    a 35-line skit every line was compared with the line before it
    (2026-09-25). Every Gemini word is matched to Scribe's words; a line with
    matched words takes Scribe's exact times and voice. A line in a language
    Scribe dropped or translated has no match: it sits between its neighbours'
    times and takes its voice from Gemini's own label."""
    gem = sorted(gem, key=lambda x: x["start"])
    speech = [w for w in scribe_words if w.get("type") == "word"]
    stoks = [(norm(w["text"]) or [""])[0] for w in speech]
    gtoks, owner = [], []
    for i, g in enumerate(gem):
        for t in norm(g["text"]):
            gtoks.append(t); owner.append(i)
    got = {i: [] for i in range(len(gem))}          # line → matched scribe word indexes
    for blk in difflib.SequenceMatcher(None, gtoks, stoks, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            got[owner[blk.a + k]].append(blk.b + k)
    ntok = {i: len(norm(g["text"])) for i, g in enumerate(gem)}

    # who spoke, where Scribe clearly heard the line
    heard, pair = {}, {}
    for i, g in enumerate(gem):
        ws = [speech[j] for j in got[i]]
        dur = {}
        for w in ws:
            dur[w["speaker"]] = dur.get(w["speaker"], 0) + (w["end"] - w["start"])
        top = max(dur, key=dur.get) if dur else None
        if top and len(ws) >= 2 and dur[top] >= 0.6 * sum(dur.values()):
            heard[i] = top
            pair[(g["speaker"], top)] = pair.get((g["speaker"], top), 0) + dur[top]
    fallback = {}
    for (gs, ss), n in sorted(pair.items(), key=lambda x: -x[1]):
        fallback.setdefault(gs, ss)

    # times: matched lines take Scribe's; the rest sit between their neighbours
    times = {}
    for i in range(len(gem)):
        ws = [speech[j] for j in got[i]]
        if len(ws) >= 2 or (ws and ntok[i] <= 2):
            times[i] = (min(w["start"] for w in ws), max(w["end"] for w in ws))
    for i, g in enumerate(gem):
        if i in times:
            continue
        prev_end = max((times[k][1] for k in times if k < i), default=0.0)
        nxt = min((times[k][0] for k in times if k > i), default=max(total, g["end"], g["start"]))
        a = min(max(g["start"], prev_end), nxt)
        b = min(max(g["end"], a), nxt) if g["end"] else a
        times[i] = (a, b)

    out, names = [], {}
    sl = two(scribe_lang)
    for i, g in enumerate(gem):
        who = heard.get(i) or fallback.get(g["speaker"], "gemini:" + g["speaker"])
        names.setdefault(who, f"Speaker {len(names) + 1}")
        a, b = times[i]
        lang = two(g.get("language"))
        around = [w for w in speech if a - 0.2 <= (w["start"] + w["end"]) / 2 <= b + 0.2 and w not in [speech[j] for j in got[i]]]
        flags = []
        if lang and sl and lang != sl:
            if not around and not got[i]:
                flags.append("scribe-dropped")          # the Korean-as-[laughs] case
            elif around and not re.search(r"[a-z]{3}", g["text"].lower()):
                flags.append("scribe-translated")       # Scribe wrote English where another language was said
        elif ntok[i] >= 3 and len(got[i]) < 0.6 * ntok[i]:
            flags.append("heard-differently")
        if i not in heard:
            flags.append("speaker-from-words-model")
        scribe_heard = " ".join(speech[j]["text"] for j in sorted(got[i])) if got[i] else " ".join(w["text"] for w in around)
        out.append({"id": f"T{i + 1}", "speaker": names[who], "start": round(a, 2), "end": round(b, 2),
                    "text": g["text"], "language": lang, "also": [two(x) for x in (g.get("also") or [])],
                    "flags": flags, "scribe_heard": scribe_heard[:400]})
    return out


def from_scribe_only(scribe_words, scribe_lang, gap=1.2):
    """No Gemini answered: Scribe's own words, one line per turn, flagged —
    other languages may be missing or translated."""
    out, cur = [], None
    for w in scribe_words:
        if not cur or w["speaker"] != cur["sp"] or w["start"] - cur["end"] > gap:
            cur = {"sp": w["speaker"], "start": w["start"], "end": w["end"], "text": w["text"]}
            out.append(cur)
        else:
            cur["text"] += " " + w["text"]
            cur["end"] = w["end"]
    names = {}
    res = []
    for i, c in enumerate(out, 1):
        names.setdefault(c["sp"], f"Speaker {len(names) + 1}")
        res.append({"id": f"T{i}", "speaker": names[c["sp"]], "start": round(c["start"], 2),
                    "end": round(c["end"], 2), "text": re.sub(r"\s+", " ", c["text"]).strip(),
                    "language": two(scribe_lang), "also": [], "flags": ["scribe-only"], "scribe_heard": ""})
    return res


def languages(lines):
    """Share of spoken words per language, e.g. {"en": 80, "ko": 20}."""
    tally = {}
    for l in lines:
        lang = l.get("language") or "?"
        tally[lang] = tally.get(lang, 0) + count_words(l["text"], lang)
    total = sum(tally.values()) or 1
    return {k: round(100 * v / total) for k, v in sorted(tally.items(), key=lambda x: -x[1])}
