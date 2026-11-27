#!/usr/bin/env python3
"""Creator brief builder: talking points, shots and don'ts for a creator, from an accepted brief.

    python3 components/briefs/creator-brief/build.py inputs <5-brief.md> --brand brand_a --product flex \
        [--length 30] [--format problem_solution] [--rows id,id,...] [--label <brief label>] \
        [--ledger <ledger.json> [--ad <n>]] --out <dir>
        writes <dir>/creator-brief.inputs.json and <dir>/creator-brief.prompt.md (the prompt, inputs filled);
        with an ad-series ledger, the header's ask is the ledger's ask for that ad, word for word, as filed
    python3 components/briefs/creator-brief/build.py check <draft.md> --inputs <creator-brief.inputs.json> \
        [--ledger <ledger.json> [--ad <n>]]
        exits 1 and prints each failure when the draft breaks the prompt's output rules, including an Ask in the
        header that is not the ledger's ask (with a ledger) or the brief's ask (without one)

The draft itself is written by the stage model from creator-brief.prompt.md. Nothing is sent: a draft stays a draft
until owner sends it through Trybe. No model, no network, no key; stdlib only; Python 3.9.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROMPT = HERE / "creator-brief-v1-owner.md"
BEATS = ("Hook", "Problem", "Discovery", "Experience", "Result", "CTA")
SECTION_BEAT = {
    "hook": "Hook",
    "problem": "Problem", "failed-solutions": "Problem", "agitation": "Problem", "enemy": "Problem",
    "product": "Discovery", "solution": "Discovery", "unique-mechanism": "Discovery", "mechanism": "Discovery",
    "proof": "Experience", "demonstration": "Experience", "testimonial": "Experience",
    "offer": "Result", "guarantee": "Result", "result": "Result",
    "call-to-action": "CTA", "cta": "CTA",
}
FORMATS = ("problem_solution", "testimonial", "unboxing", "day_in_life")
SECTIONS = ("## Hook options", "## Talking points", "## Shots to film", "## Facts you can say", "## Do", "## Don't")
COPY_RUN = 8
STUDIO = ("ring light", "gimbal", "crew", "cinematic transition", "studio light")
PUSHY = ("limited time", "act now", "don't miss out", "dont miss out")
ASK_LINE = re.compile(r"^\*\*Format:\*\*.*\*\*Ask:\*\*\s*(.*?)\s*$", re.M)   # the OUTPUT header's last field


def same_ask(a, b):
    """Two asks are the same line when they match word for word (spacing and curly apostrophes aside)."""
    def n(s):
        return " ".join(str(s or "").replace("\u2019", "'").split())
    return n(a) == n(b)


def ledger_ask(ledger, ad=None):
    """(ad, ask) from an ad-series ledger's arc card: the named ad, else the ledger's `current`, else ad 1."""
    ad = int(ad) if ad else (ledger.get("current") if isinstance(ledger.get("current"), int) else 1)
    row = next((a for a in ledger.get("arc") or [] if a.get("ad") == ad), None)
    if row is None:
        raise SystemExit("the ledger's arc card has no ad %d" % ad)
    return ad, str(row.get("ask") or "")


def run_aim(brief):
    """The `aim` of the run a brief was written in (its own folder's run.json, or the folder above), or None."""
    for d in list(Path(brief).resolve().parents)[:2]:
        try:
            got = json.loads((d / "run.json").read_text()).get("aim")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(got, dict) and got.get("avatar"):
            return got
    return None


def who_line(aim):
    """The header's one line on who it is for: avatar, sub-avatar, demographic, the one doubt in plain words."""
    if not aim:
        return None
    says = aim.get("doubt")
    try:
        rows = json.loads((ROOT / "components" / "marketing-doctrine" / "frameworks.json").read_text())["belief"]["doubts"]
        says = next((r["says"] for r in rows if r.get("id") == says), says)
    except (OSError, ValueError, KeyError):
        pass
    parts = [aim.get("avatar"), aim.get("sub"), aim.get("demographic"), says and "doubt to close: %s" % says]
    return "**Who:** " + " · ".join(str(p) for p in parts if p)


def _who():
    """creative-strategist's shared reader (who.py), the one every writing chain uses."""
    p = str(ROOT / "components" / "creative-strategist" / "machine")
    if p not in sys.path:
        sys.path.append(p)
    import who
    return who


def who_args(brand, aim):
    """(brand, avatar, sub, demographic, what) for who.block / who.attach from the run's aim, or None."""
    if not (brand and aim and aim.get("avatar")):
        return None
    what = {k: aim.get(k) for k in ("desire", "awareness", "stage", "doubt", "claim") if aim.get(k)}
    what["creative"] = True
    return brand, aim["avatar"], aim.get("sub") or "", aim.get("demographic") or None, what


def who_block(brand, aim):
    """The full profile and what this piece says (who.block), with no prompt slot in it; "" when the run has no aim.
    A sub-avatar that is not on file stops here, named, the same as every other writing chain."""
    args = who_args(brand, aim)
    return re.sub(r"\{([a-z_]+)\}", r"(\1)", _who().block(*args)) if args else ""


def draft_ask(draft):
    """The Ask a finished draft's header names, or None when the header has no Ask field."""
    m = ASK_LINE.search(draft[:600])
    return m.group(1) if m else None


# ---- reading the accepted brief and the brand files ----

def brief_block(text):
    """The brief's fenced json block that carries its scenes (machine/model-inputs.json brief_schema)."""
    for m in re.finditer(r"```json\n(.*?)\n```", text, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("scenes"), list):
            return d
    raise SystemExit("no json block with scenes in the brief")


def md_section(text, title):
    m = re.search(r"^## %s\s*\n(.*?)(?=^## |\Z)" % re.escape(title), text, re.S | re.M)
    return m.group(1) if m else ""


def bullets(block):
    return [re.sub(r"\s+", " ", b).strip() for b in re.findall(r"^- (.+?)(?=^- |^\S|\Z)", block, re.S | re.M)]


def product_facts(text):
    """What may be said about the product: the product file's 'What it does' and 'What the live store says' bullets."""
    found = bullets(md_section(text, "What it does")) + bullets(md_section(text, "What the live store says"))
    return [f for f in found if not f.endswith(":")]


RULED_OUT = re.compile(r"[\"“]([^\"”]{3,60})[\"”]\s+(?:is wrong|is invented|is not on file|has been [^.;\"]*?invented)")


def banned_phrases(text):
    """Phrases the product file rules out: a quoted phrase whose own verb calls it wrong or invented."""
    out = [q.strip() for q in RULED_OUT.findall(re.sub(r"\s+", " ", text))]
    return sorted(set(out), key=out.index)


def guarantee_for(guarantees, product):
    """The product's guarantee: its key and verbatim wording only. Nothing stacked on it (a store credit) is carried:
    the creator brief names the guarantee as written and no other offer (round 3, 2026-11-07)."""
    for key, g in (guarantees.get("guarantees") or {}).items():
        if product.lower() in key.lower() or product.upper() in str(g.get("surface", "")).upper():
            return {"key": key, "verbatim": g.get("verbatim")}
    return None


def bank_rows(brand, ids):
    """Language-bank rows by id, searched across the brand's language files."""
    want, found = set(ids), {}
    if not want:
        return []
    for f in sorted((ROOT / "brands" / brand / "core-avatars").glob("**/language/**/*.json")):
        try:
            rows = json.loads(f.read_text())
        except ValueError:
            continue
        rows = rows if isinstance(rows, list) else (rows.get("entries") or rows.get("rows") or [])
        for r in rows:
            if isinstance(r, dict) and r.get("id") in want:
                found[r["id"]] = {"id": r["id"], "text": r.get("text"), "file": str(f.relative_to(ROOT))}
        if len(found) == len(want):
            break
    missing = want - set(found)
    if missing:
        raise SystemExit("bank rows not found: %s" % ", ".join(sorted(missing)))
    return [found[i] for i in ids]


def build_inputs(brief_text, product_text, guarantees, brand, product, length=30, ugc_format="problem_solution",
                 rows=(), label=None, ledger=None, ad=None, aim=None):
    if ugc_format not in FORMATS:
        raise SystemExit("format must be one of %s" % ", ".join(FORMATS))
    b = brief_block(brief_text)
    piece = b.get("piece") or {}
    series = None
    if ledger is not None:                  # the ledger's ask is used as filed: the header takes it word for word
        n, ask = ledger_ask(ledger, ad)
        series = {"series": ledger.get("series"), "ad": n, "ask": ask,
                  "rules": [r.get("rule") for r in ledger.get("rules") or [] if n in (r.get("ads") or [])]}
    beats = {k: [] for k in BEATS}
    shots = []
    for s in b["scenes"]:
        beat = SECTION_BEAT.get(str(s.get("section") or "").lower(), "Experience")
        if s.get("voice"):
            beats[beat].append({"scene": s.get("id"), "section": s.get("section"), "says": s["voice"]})
        ff = s.get("first_frame")
        if not s.get("to_camera") and isinstance(ff, dict) and ff.get("subject"):
            shots.append({"scene": s.get("id"), "beat": beat, "shows": ff["subject"]})
    openings = [{"id": o.get("id"), "say": o.get("say")} for o in (b.get("openings") or []) if o.get("say")]
    gaps = ["the brief has no %s scene: take it from the openings and rows" % k for k, v in beats.items() if not v]
    return {
        "schema": "creator-brief-inputs/v1",
        "label": label,
        "piece": {"brand": brand, "product": product, "title": piece.get("title"), "ask": piece.get("ask"),
                  "awareness": piece.get("awareness"), "aspect": piece.get("aspect_ratio") or "9:16"},
        "length": int(length),
        "ugc_format": ugc_format,
        "beats": beats,
        "openings": openings,
        "shots": shots,
        "facts": product_facts(product_text),
        "guarantee": guarantee_for(guarantees, product),
        "rows": list(rows),
        "banned": banned_phrases(product_text),
        "gaps": gaps,
        "ledger": series,
        "route": "trybe",
        "sent": False,
        **({"who": who_line(aim)} if aim else {}),
    }


# ---- checking a finished draft ----

def words(text):
    return re.findall(r"[a-z0-9']+", text.lower().replace("’", "'"))


def unquoted(text):
    """The draft with every sourced quote removed: "..." (guarantee) or "..." (row <id>) or "..." (brief <scene>)."""
    return re.sub(r"[\"“][^\"”]+[\"”]\s*\((?:guarantee|row [\w-]+|brief S\d+)\)", " ", text)


def ngrams(text, n):
    w = words(text)
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def copied_runs(draft, paragraphs, on_file=(), n=COPY_RUN):
    """Runs of n words a brief paragraph and the draft share, leaving out sourced quotes and lines on file."""
    grams = ngrams(unquoted(draft), n)
    allowed = set().union(*[ngrams(t, n) for t in on_file]) if on_file else set()
    hits = []
    for p in paragraphs:
        w = words(p)
        for i in range(len(w) - n + 1):
            g = tuple(w[i:i + n])
            if g in grams and g not in allowed:
                hits.append(" ".join(g))
                break
    return hits


def check(draft, inputs, ledger=None, ad=None):
    """Every way the draft breaks the prompt's OUTPUT and BANNED rules. With `ledger` (an ad-series ledger), the
    header's Ask is also held to that ledger's ask for the ad (the ad the inputs were built for, else `ad`)."""
    out = []
    head = draft[:400]
    if "DRAFT" not in head or "Not sent" not in head:
        out.append("the header must say DRAFT. Not sent.")
    if inputs.get("who") and inputs["who"] not in draft[:900]:
        out.append("the header lacks its who line: %s" % inputs["who"])
    said = draft_ask(draft)
    want = (inputs.get("piece") or {}).get("ask")
    led = inputs.get("ledger")
    if ledger is not None:
        n, ask = ledger_ask(ledger, ad or (led or {}).get("ad"))
        led = {"ad": n, "ask": ask}
    if said is None:
        out.append("the header names no Ask")
    elif not led and not same_ask(said, want):         # with a ledger, the ledger's ask is the one held
        out.append("the header's ask %r is not the brief's ask %r" % (said, want))
    if led and said is not None and not same_ask(said, led.get("ask")):
        out.append("the creator brief's ask %r differs from the ledger's ask for ad %s %r"
                   % (said, led.get("ad"), led.get("ask")))
    at = -1
    for title in SECTIONS:
        i = draft.find(title)
        if i < 0:
            out.append("missing section: %s" % title)
        elif i < at:
            out.append("section out of order: %s" % title)
        at = max(at, i)
    hooks = re.findall(r"^\d+\. ", md_section(draft, "Hook options (pick one, say it your way)") or "", re.M)
    if len(hooks) != 3:
        out.append("hook options: %d, want 3" % len(hooks))
    table = md_section(draft, "Talking points (your words, not a script)")
    for beat in BEATS:
        if not re.search(r"^\| %s \|" % beat, table, re.M):
            out.append("talking points lack the %s beat" % beat)
    shots = re.findall(r"^\d+\. ", md_section(draft, "Shots to film"), re.M)
    if not 4 <= len(shots) <= 6:
        out.append("shots: %d, want 4 to 6" % len(shots))
    paragraphs = [x["says"] for v in inputs["beats"].values() for x in v]
    on_file = list(inputs.get("facts") or []) + [r.get("text") or "" for r in inputs.get("rows") or []]
    on_file += [str((inputs.get("guarantee") or {}).get("verbatim") or "")]
    on_file += [str((inputs.get("piece") or {}).get("ask") or "")]      # the header carries the ask word for word
    on_file += [str((led or {}).get("ask") or "")]
    for run in copied_runs(draft, paragraphs, on_file):
        out.append("copies the brief word for word: \"%s\"" % run)
    low = draft.lower()
    dont = md_section(draft, "Don't").lower()
    for phrase in inputs.get("banned") or []:
        p = phrase.lower()
        if p not in dont:
            out.append("banned phrase not listed under Don't: %s" % phrase)
        if p in low.replace(dont, ""):
            out.append("banned phrase used outside Don't: %s" % phrase)
    allowed = set(re.findall(r"\$\d[\d,]*", json.dumps(inputs.get("guarantee") or {})))
    for amount in set(re.findall(r"\$\d[\d,]*", draft)) - allowed:
        out.append("a dollar amount not in the guarantee: %s" % amount)
    body = low.replace(dont, "")
    for w in STUDIO + PUSHY:
        if w in body:
            out.append("banned ask or close word: %s" % w)
    return out


# ---- command line ----

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inputs")
    i.add_argument("brief")
    i.add_argument("--brand", required=True)
    i.add_argument("--product", required=True)
    i.add_argument("--length", type=int, default=30)
    i.add_argument("--format", default="problem_solution", choices=FORMATS)
    i.add_argument("--rows", default="")
    i.add_argument("--label")
    i.add_argument("--ledger")
    i.add_argument("--ad", type=int)
    i.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("draft")
    c.add_argument("--inputs", required=True)
    c.add_argument("--ledger")
    c.add_argument("--ad", type=int)
    a = ap.parse_args(argv)
    ledger = json.loads(Path(a.ledger).read_text()) if a.ledger else None
    if a.cmd == "inputs":
        brand_dir = ROOT / "brands" / a.brand
        ids = [x.strip() for x in a.rows.split(",") if x.strip()]
        packet = build_inputs(Path(a.brief).read_text(), (brand_dir / "products" / ("%s.md" % a.product)).read_text(),
                              json.loads((brand_dir / "offers" / "guarantees.json").read_text()), a.brand, a.product,
                              a.length, a.format, bank_rows(a.brand, ids), a.label, ledger, a.ad, run_aim(a.brief))
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        js = json.dumps(packet, indent=1, ensure_ascii=False)
        (out / "creator-brief.inputs.json").write_text(js + "\n")
        head = "**Format:** <ugc_format>"                 # the who line goes into the OUTPUT header under it, word for word
        prompt = re.sub(r"(?m)^%s.*$" % re.escape(head), lambda m: m.group(0) + "\n" + packet["who"], PROMPT.read_text()) if packet.get("who") else PROMPT.read_text()
        aim = run_aim(a.brief)
        wb = who_block(a.brand, aim)                       # the person's full profile, on top, like every writing chain (2026-11-27)
        if wb:
            _who().attach(out, *who_args(a.brand, aim))     # and saved beside the prompt (profile.json, profile.md)
        else:
            print("  ! no avatar on the brief's run: written without a profile", file=sys.stderr)
        (out / "creator-brief.prompt.md").write_text((wb + "\n\n" if wb else "") + prompt.replace("{inputs_json}", "\n\n```json\n%s\n```\n" % js))
        print("wrote %s and %s" % (out / "creator-brief.inputs.json", out / "creator-brief.prompt.md"))
        return 0
    found = check(Path(a.draft).read_text(), json.loads(Path(a.inputs).read_text()), ledger, a.ad)
    for f in found:
        print("FAIL", f)
    if not found:
        print("pass")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
