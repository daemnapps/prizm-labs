"""Slang research: the room's own words, defined with receipts, for the avatar's culture map.

    python3 components/research-gatherer/slang.py --brand B --avatar A [--dry-run] [--limit 40]

the owner, 2026-10-27, on a picture swipe captioned "how to get the best NECK" the chain read as nonsense: "Getting neck
is slang ... we'll probably see more of the slang and things like that, mostly in comments on posts ... for
definitions of these things that you're uncertain of or not clear, then it's like have to go trigger research. There's
websites like Urban Dictionary ... And then that also is then loaded into a culture index per avatar." Then: "culture
index should already be a thing. comments should already come in on swipes anyways so it's really just slang research
from all sources."

Three steps:
1. HARVEST, one model call: the culture map's own evidence pack for the avatar (bank rows: comments and posts in
   their words; feed post captions; the teardowns' culture reads) goes in; out come the slang terms, in-jokes and
   double meanings an outsider could miss, each with the line it was used in and that line's evidence id.
2. LOOK UP, no model: each term on Urban Dictionary (its public definitions endpoint), the top definitions by votes,
   each with its link and vote count. Free; no key.
3. DEFINE, one model call: each term's meaning AS THIS ROOM USES IT, from its own line and the definitions, with a
   confidence (CONFIRMED: the definitions and the line agree; LIKELY; UNCLEAR: say what would settle it).

Writes runs/research/<brand>/slang-<avatar>-<stamp>/slang.json (+ slang.md to read). `culture_map.slang_evidence`
reads the newest one into the culture map's evidence pack, each term an item `slang:<term>`, so the map that every
writing stage reads carries it with its receipts. Nothing here writes into brands/.
"""
import datetime as _dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from . import culture_map as CM

UD = "https://api.urbandictionary.com/v0/define?term="

HARVEST = """You are reading what real people in one audience said and posted: comments, captions, and the culture reads
of posts they watched. List every slang term, in-joke, double meaning, abbreviation or phrase whose meaning an outsider
(a brand writer who is not in this room) could miss or get wrong. Include sexual or crude meanings plainly: a writer who
does not know them will walk into them or miss the joke. Leave out ordinary words.

THE EVIDENCE (each line starts with its id in brackets):
{pack}

Return only a fenced json list, at most {limit} items, the most used and most load-bearing first:
```json
[{{"term": "<the term as written>", "line": "<the exact line it was used in>", "ids": ["<evidence id>"]}}]
```"""

DEFINE = """For each term below: what it means AS THIS AUDIENCE USES IT in its own line, in one plain sentence (say a
sexual or crude meaning plainly), whether it carries a double meaning a writer could play on, and a confidence:
CONFIRMED (the dictionary definitions and the line agree), LIKELY (one fits the line), UNCLEAR (say what would settle it).
Never invent a meaning the definitions and the line do not support.

THE TERMS, each with its line and the top dictionary definitions:
{terms}

Return only a fenced json list, one per term, in order:
```json
[{{"term": "...", "meaning": "...", "double_meaning": "<the two readings, or none>", "confidence": "CONFIRMED|LIKELY|UNCLEAR", "why": "..."}}]
```"""


def _json_list(raw):
    m = re.search(r"```(?:json)?\s*(\[.*\])\s*```", raw, re.S) or re.search(r"(\[\s*\{.*\}\s*\])", raw, re.S)
    if not m:
        raise ValueError("no json list in the answer: " + raw[:200])
    return json.loads(m.group(1))


def lookup(term, fetch=None):
    """The top Urban Dictionary definitions for a term, by votes: [{definition, example, link, up, down}]."""
    def _get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (culture research)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    try:
        got = (fetch or _get)(UD + urllib.parse.quote(term)).get("list") or []
    except Exception as e:  # noqa: BLE001  a lookup that fails is said, never a guess
        return [{"error": str(e)[:160]}]
    got.sort(key=lambda d: -(int(d.get("thumbs_up") or 0) - int(d.get("thumbs_down") or 0)))
    clean = lambda s: re.sub(r"[\[\]]", "", s or "").strip()[:400]
    return [{"definition": clean(d.get("definition")), "example": clean(d.get("example")), "link": d.get("permalink"),
             "up": d.get("thumbs_up"), "down": d.get("thumbs_down")} for d in got[:3]]


TRENDS = """Search the web now. List the slang, memes and phrases that {who} use on TikTok and Instagram right now
(this month and the last few): new words, meme numbers and catchphrases, "-maxxing" style words, roast and hype words,
and anything crude or sexual they joke with. For each: the term, what it means, how they use it in a sentence, and the
page you found it on. Only what you found in a search; never invent. Return only a fenced json list:
```json
[{{"term": "...", "line": "<how they use it>", "meaning": "...", "source": "<url>"}}]
```"""


def trends(who, gemini=None):
    """The newest slang from the web (Gemini with Google Search): terms our own rows cannot hold yet."""
    import importlib.util
    import json as _j
    if gemini is None:
        kit = next(d for d in Path(__file__).resolve().parents if (d / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("_keys", kit / "components" / "keys" / "loader.py")
        K = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(K)
        key = K.key("GEMINI_API_KEY", required=False)
        if not key:
            return []

        def gemini(prompt):
            body = _j.dumps({"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]}).encode()
            req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:"
                                         "generateContent?key=" + key, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                d = _j.loads(r.read().decode())
            return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    try:
        return [t for t in _json_list(gemini(TRENDS.format(who=who))) if t.get("term")]
    except Exception:  # noqa: BLE001  the web step is extra evidence; it never stops the research
        return []


def research(brand, avatar, limit=40, dry_run=False, model=None, ws=None, ask=None, fetch=None, say=print,
             trends_for=None, gemini=None):
    model = CM.model_name(model)
    ask = ask or (lambda p: CM.call_model(p, model))
    pack = CM.build_pack(brand, avatar, ws)
    words = [i for i in pack["items"] if i["kind"] in ("bank-row", "feed-post", "culture-ref")]
    pack_text = CM.render_pack({**pack, "items": words, "notes": []})
    prompt1 = HARVEST.format(pack=pack_text, limit=limit)
    say(f"{brand}/{avatar}: {len(words)} lines of evidence · harvest {len(prompt1):,} chars · {model}")
    if dry_run:
        return {"evidence": len(words), "prompt": prompt1}
    ids = CM.pack_ids(pack)
    terms = [t for t in _json_list(ask(prompt1)) if t.get("term")]
    if trends_for:
        # cutting edge (the owner, 2026-10-27: "like this 6-7 thing, like, I don't even know what the fuck that is ... we want
        # to be cutting edge with our language awareness"): the web's newest terms for this audience join the room's own
        new = trends(trends_for, gemini)
        have = {x["term"].lower() for x in terms}
        for x in new:
            if x["term"].lower() not in have:
                terms.append({"term": x["term"], "line": x.get("line"), "ids": [], "web": x.get("source"),
                              "web_meaning": x.get("meaning")})
        say(f"  web: {len(new)} current terms found for {trends_for}")
    for t in terms:
        t["ids"] = [i for i in t.get("ids") or [] if i in ids]           # a receipt must resolve to the pack
        t["dictionary"] = lookup(t["term"], fetch)
    blocks = []
    for n, t in enumerate(terms, 1):
        defs = "\n".join(f"   - ({d.get('up')}↑) {d.get('definition')}" for d in t["dictionary"] if d.get("definition")) or "   - (no dictionary entry)"
        web = f"\n   - (web) {t.get('web_meaning')} ({t.get('web')})" if t.get("web") else ""
        blocks.append(f"{n}. {t['term']}\n   line: {t.get('line')}\n{defs}{web}")
    defined = _json_list(ask(DEFINE.format(terms="\n".join(blocks)))) if terms else []
    # matched by position: the answer is one per term, in order (by name it lost 37 of 40 to small rewordings)
    for t, d in zip(terms, defined):
        t.update({k: d.get(k) for k in ("meaning", "double_meaning", "confidence", "why")})
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M")
    out = CM.ws_root(ws) / "runs" / "research" / brand / f"slang-{avatar}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    rec = {"brand": brand, "avatar": avatar, "built_at": _dt.datetime.now().astimezone().isoformat(timespec="minutes"),
           "model": model, "terms": terms}
    (out / "slang.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    md = [f"# Slang — {brand} / {avatar}", "", f"Built {rec['built_at']}. Each term: what it means in this room, its line, "
          "and the dictionary's top definitions with links.", ""]
    for t in terms:
        md += [f"## {t['term']} · {t.get('confidence') or '?'}", "", f"**Means:** {t.get('meaning')}",
               f"**Double meaning:** {t.get('double_meaning') or 'none'}", f"**Said:** {t.get('line')} [{', '.join(t['ids'])}]"]
        md += [f"- {d.get('up')}↑ {d.get('definition')} ({d.get('link')})" for d in t["dictionary"] if d.get("definition")]
        md.append("")
    (out / "slang.md").write_text("\n".join(md))
    say(f"  {len(terms)} terms defined → {out.relative_to(CM.ws_root(ws))}")
    return {"terms": len(terms), "out": str(out)}


def told_path(brand, avatar, ws=None):
    return CM.ws_root(ws) / "runs" / "research" / brand / f"slang-{avatar}-told.json"


def tell(brand, avatar, term, meaning, by, double_meaning=None, line=None, ws=None):
    """A term a person tells us, in their words (the owner, 2026-10-27: "not everything's going to be in the culture map
    right away, but I'm telling you what it is now"). Kept apart from the research, never overwritten by it; its
    receipt is who said it and when."""
    f = told_path(brand, avatar, ws)
    rec = json.loads(f.read_text()) if f.is_file() else {"brand": brand, "avatar": avatar, "terms": []}
    rec["terms"] = [x for x in rec["terms"] if x["term"].lower() != term.lower()]
    rec["terms"].append({"term": term, "meaning": meaning, "double_meaning": double_meaning, "line": line,
                         "confidence": "CONFIRMED", "told_by": by,
                         "at": _dt.datetime.now().astimezone().isoformat(timespec="minutes"), "ids": [], "dictionary": []})
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    return f


def told(brand, avatar, ws=None):
    f = told_path(brand, avatar, ws)
    return json.loads(f.read_text()).get("terms") or [] if f.is_file() else []


def newest(brand, avatar, ws=None):
    got = sorted((CM.ws_root(ws) / "runs" / "research" / brand).glob(f"slang-{avatar}-*/slang.json"))
    return json.loads(got[-1].read_text()) if got else None
