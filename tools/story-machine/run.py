"""Story machine runner — fills a stage prompt, calls the model, and gates length.

The model cannot count its own words (first run, 2026-10-06: scripts claimed
816 words and were 1,157; the "45s" cut was 84s). So length is checked here,
in code, and a script outside its band goes back with the real count until it
fits or runs out of tries.

    python3 run.py <stage-prompt.md> <slots.json> <out.md> [--words MIN-MAX]

Over-long scripts and the paid cuts go through trim() / make_cuts(), which use
prompts/05-cut-v2-damon.md: the model ranks sentences, code fills the budget.

slots.json maps each {slot} in the prompt to its text.
Key: OPENAI_API_KEY in the environment, or the local key store if present.
"""
import json
import os
import re
import sys
import urllib.request

MODEL = os.environ.get("STORY_MODEL", "gpt-5.1")
TRIES = 3
CUT_PROMPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "05-cut-v2-damon.md")
CUT_BANDS = {"90": (400, 460), "60": (270, 320), "45": (200, 235)}  # ~290 words a minute


def key():
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    sys.path.insert(0, os.path.expanduser("~/.daemn"))
    import daemn_keys
    return daemn_keys.key("OPENAI_API_KEY")


def chat(messages):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({"model": MODEL, "messages": messages}).encode(),
        headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=600))["choices"][0]["message"]["content"]


def fill(prompt, slots):
    return prompt + "\n\n---\n## Inputs\n" + "\n".join(f"### {{{k}}}\n{v}\n" for k, v in slots.items())


def narration_words(text):
    body = text.split("NARRATION:", 1)[-1].split("BEAT MARKS", 1)[0]
    return len(body.split())


def cut_words(text):
    return {m.group(1): len(m.group(2).split())
            for m in re.finditer(r"CUT (\d+)s[^\n]*\n(.*?)(?=\nCUT \d+s|\nEND CARD|\Z)", text, re.S)}


def sentences(text):
    """Split narration into sentences, never inside a quote."""
    body = text.split("NARRATION:", 1)[-1].split("BEAT MARKS", 1)[0].strip()
    body = re.sub(r"\(length set in code.*?\)", "", body)
    out = []
    for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
        cur, depth = "", 0
        for i, ch in enumerate(para):
            cur += ch
            if ch in "“":
                depth += 1
            elif ch in "”":
                depth = max(0, depth - 1)
            elif ch == '"':
                depth = 0 if depth else 1
            nxt = para[i + 1:i + 3] if i + 1 < len(para) else "  "
            starts_new = len(nxt) < 2 or nxt[1].isupper() or nxt[1].isdigit() or nxt[1] in '"“'
            if depth == 0 and ch in '.!?…”"' and nxt[:1] == " " and starts_new and re.search(r'[.!?…]["”]?$', cur):
                out.append(cur.strip())
                cur = ""
        if cur.strip():
            out.append(cur.strip())
        out[-1] += "\n\n"
    return out


BEATS = ["hook", "setup", "pressure", "turn", "payoff", "sting"]


def trim(text, lo, hi, why, must=""):
    """Retry until every beat is labelled and `must` (the product name) survives."""
    for attempt in range(1, TRIES + 1):
        body, n, beats = _trim(text, lo, hi, why)
        missing = [b for b in BEATS if b not in beats]
        if not missing and (not must or must in body):
            return body, n
        print(f"  retry {attempt}: missing {missing or ''}{' product' if must and must not in body else ''}")
    raise RuntimeError(f"cut failed after {TRIES} tries: missing {missing}, product kept: {must in body}")


def _trim(text, lo, hi, why):
    """The model ranks and labels the sentences; code fills the word budget.
    The model never counts and never adds a word, so a cut is only ever made of
    lines already approved, it always lands in the band, and it keeps the best
    sentence of every beat."""
    sents = sentences(text)
    words = [len(x.split()) for x in sents]
    listing = "\n".join(f"{i}. {x.strip()}" for i, x in enumerate(sents))
    prompt = open(CUT_PROMPT).read().split("\n---\n", 1)[1].strip()
    prompt = prompt.replace("{count}", str(len(sents))).replace("{why}", why).replace("{listing}", listing)
    reply = chat([{"role": "user", "content": prompt}])
    try:
        data = json.loads(re.search(r"\{.*\}", reply, re.S).group(0))
        rank = [int(k) for k in data["rank"] if 0 <= int(k) < len(sents)]
        beat = {int(k): v for k, v in data.get("beat", {}).items()}
    except Exception:
        rank, beat = [], {}
    rank = list(dict.fromkeys(rank + list(range(len(sents)))))
    first_of_beat = [next((k for k in rank if beat.get(k) == b), None) for b in BEATS]
    order = list(dict.fromkeys([0, len(sents) - 1] + [k for k in first_of_beat if k is not None] + rank))
    keep, n = set(), 0
    for k in order:
        if n + words[k] <= hi:
            keep.add(k)
            n += words[k]
    kept_beats = {beat.get(k, "?") for k in keep}
    print(f"  trim: {n} words, beats kept: {sorted(kept_beats)}")
    return " ".join(sents[k] for k in sorted(keep)).replace("\n\n ", "\n\n").strip(), n, kept_beats


def run(stage, slots, out, band=None, cuts=False):
    messages = [{"role": "user", "content": fill(open(stage).read(), slots)}]
    for attempt in range(1, TRIES + 1):
        text = chat(messages)
        if band:
            n = narration_words(text)
            ok = band[0] <= n <= band[1]
            note = f"NARRATION is {n} words; it must be {band[0]}-{band[1]}."
        elif cuts:
            got = cut_words(text)
            bad = {k: v for k, v in got.items() if not (CUT_BANDS[k][0] <= v <= CUT_BANDS[k][1])}
            ok = not bad and len(got) == 3
            note = "; ".join(f"CUT {k}s is {v} words, must be {CUT_BANDS[k][0]}-{CUT_BANDS[k][1]}"
                             for k, v in bad.items()) or "Return all three cuts."
        else:
            ok, note = True, ""
        print(f"try {attempt}: {'ok' if ok else note}")
        if ok:
            break
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": f"Counted in code: {note} Rewrite to fit. "
                      "Cut inside beats, keep every beat, keep the first and last lines. "
                      "Return the whole thing in the same format, with the real word count."}]
    if band and not ok:
        body, n = trim(text, band[0], band[1], "It is too long for the format.")
        head = text.split("NARRATION:", 1)[0]
        text = head + "NARRATION:\n" + body + "\n\n(length set in code: " + str(n) + " words)\n"
        ok = band[0] <= n <= band[1]
    open(out, "w").write(text)
    return text, ok


def make_cuts(narration_text, out, end_card="", product=""):
    """Stage 5 done as selection: each paid length is a subset of the approved script."""
    parts = []
    ok = True
    for sec, (lo, hi) in CUT_BANDS.items():
        print(f"cut {sec}s")
        body, n = trim(narration_text, lo, hi, f"Cut it to a {sec}-second paid ad. The product stays at the turn.", must=product)
        ok &= lo <= n <= hi
        parts.append(f"CUT {sec}s — {n} words (≈{round(n / 290 * 60)}s)\n{body}\n")
    text = "\n".join(parts) + (f"\nEND CARD: {end_card}\n" if end_card else "")
    open(out, "w").write(text)
    return text, ok


if __name__ == "__main__":
    stage, slots, out = sys.argv[1:4]
    band = None
    if "--words" in sys.argv:
        lo, hi = sys.argv[sys.argv.index("--words") + 1].split("-")
        band = (int(lo), int(hi))
    _, ok = run(stage, json.load(open(slots)), out, band, "--cuts" in sys.argv)
    sys.exit(0 if ok else 1)
