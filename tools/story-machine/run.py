"""Story machine runner — fills a stage prompt with its {slots} and calls the model.

No length limits (Damon, 2026-10-06): the story runs as long as it needs.
Nothing is shortened unless a shorter cut is asked for by name:

    python3 run.py <stage-prompt.md> <slots.json> <out.md>
    python3 run.py --cut <narration.md> <out.md> 60 [45 ...] [--product NAME]

--cut uses prompts/05-cut-v2-damon.md: the model ranks sentences, code fills
the requested time, so a cut is only ever made of lines from the full script.
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
WPM = 290  # measured narration speed of the swiped format


def band(seconds):
    words = round(int(seconds) * WPM / 60)
    return round(words * 0.92), words


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


def run(stage, slots, out):
    text = chat([{"role": "user", "content": fill(open(stage).read(), slots)}])
    open(out, "w").write(text)
    return text


def make_cuts(narration_text, out, seconds, end_card="", product=""):
    """Only on request: each asked-for length is a subset of the approved script."""
    parts = []
    ok = True
    for sec in seconds:
        lo, hi = band(sec)
        print(f"cut {sec}s")
        body, n = trim(narration_text, lo, hi, f"Cut it to a {sec}-second paid ad. The product stays at the turn.", must=product)
        ok &= lo <= n <= hi
        parts.append(f"CUT {sec}s — {n} words (≈{round(n / WPM * 60)}s)\n{body}\n")
    text = "\n".join(parts) + (f"\nEND CARD: {end_card}\n" if end_card else "")
    open(out, "w").write(text)
    return text, ok


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--cut":
        product = args[args.index("--product") + 1] if "--product" in args else ""
        rest = [x for x in args[1:] if x not in ("--product", product)]
        narration, out, secs = rest[0], rest[1], rest[2:]
        _, ok = make_cuts(open(narration).read(), out, secs, product=product)
        sys.exit(0 if ok else 1)
    stage, slots, out = args[:3]
    run(stage, json.load(open(slots)), out)
