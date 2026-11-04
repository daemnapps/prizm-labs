#!/usr/bin/env python3
"""real_formats — the brand's own winning ads, stripped to formats the copy is written in.

    real_formats.py build --brand brand-a [--dry-run]       strip every real ad in the pull into a format
    real_formats.py show  --brand brand-a [--slot primary]  the formats, best numbers first
    real_formats.py pick  --brand brand-a --awareness problem-aware [--promo]   what a writer would be handed

the owner, 2026-10-27 (Tella, on the picture board): "right now we keep writing brand new ad copy over and over and
over again per ad, and that's not necessary at all ... when I read some of this copy back, it's not in a proven
format ... we're just freeballing it based off of the brief." And 2 Oct (docs/copy-format-bank-owner.md): "We're
first going to use the formats that directly came from the ad account, nothing that we generated or wrote."

The raw material is the warehouse pull `library/meta_copy.py --from-db` already made (top 25 by spend + top 25 by
lowest CPA, the words exactly as they ran, with their numbers): `runs/copywriter/<brand>/meta-copy/<date>/copy.json`.
Nothing here reads the ad account. Each ad's words go through `prompts/copy-format-strip-vN-owner.md` and come back
as the same words with named [BLANKS] — the way the video hook is a format (tools/video-teardown
`hook_format`, its declared public helper, checks it here the same way: the format's fixed words must be the ad's
own, in order). A format that is not the ad's own words is kept with `state: broken` and never handed to a writer.

The bank: `runs/copywriter/<brand>/copy-formats/formats.json` (+ `formats.md` to read). Not in brands/ (read-only to
machines) and not in bank/ (brand-agnostic). Ids follow the 2 Oct grammar, `copyformat_<brand>_<slot>_NN`; each
format is named by the real ad it came from (its Meta ad name), never a name made up here. Every entry is
`status: draft` until the owner approves it.
"""
import argparse, importlib.util, json, re, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
COPY = HERE.parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
PROMPTS = COPY / "prompts"
SLOTS = ("primary", "headlines", "descriptions")
CHUNK = {"primary": 10, "headlines": 25, "descriptions": 25}


def _hook_format():
    spec = importlib.util.spec_from_file_location("_hook_format", WS / "tools/video-teardown/machine/hook_format.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


HF = _hook_format()


def latest_prompt(stage):
    got = [(int(m.group(1)), f) for f in PROMPTS.glob(f"{stage}-v*-owner.md") for m in [re.search(r"-v(\d+)-", f.name)] if m]
    if not got:
        sys.exit(f"no prompt {stage}-vN-owner.md in {PROMPTS}")
    return max(got)[1]


def slug(brand):
    return re.sub(r"[^a-z0-9-]+", "-", str(brand).lower()).strip("-")


def pull(brand, ws=WS):
    """The newest warehouse pull for the brand, or None."""
    got = sorted((Path(ws) / "runs/copywriter" / slug(brand) / "meta-copy").glob("*/copy.json"))
    return got[-1] if got else None


def bank_path(brand, ws=WS):
    return Path(ws) / "runs/copywriter" / slug(brand) / "copy-formats" / "formats.json"


def load(brand, ws=WS):
    p = bank_path(brand, ws)
    return json.loads(p.read_text()) if p.is_file() else None


def cpa(row):
    return round(row["spend"] / row["purchases"], 2) if row.get("purchases") else None


def fits(fmt, text):
    """True when `text` keeps every fixed word of `fmt`, in order (the video hook's own check)."""
    return HF.fits(fmt, text)


def keeps(fmt, text, share=0.7):
    """True when `text` is the format with its elements changed (the owner, 2026-10-27: "we're just using the formats and
    changing elements, that's it"): its paragraphs one for one, and at least `share` of the format's own words still
    there, in order. Stricter `fits` is for the strip, where the format must be the ad's words exactly."""
    import difflib
    paras = lambda s: len([b for b in re.split(r"\n\s*\n", s.strip()) if b.strip()])
    if paras(fmt) != paras(text):
        return False
    want = " ".join(HF.fixed_parts(fmt)).split()
    if not want:
        return True
    got = HF.norm(HF.BLANK.sub(" ", text)).split()
    m = difflib.SequenceMatcher(None, want, got, autojunk=False)
    return sum(b.size for b in m.get_matching_blocks()) / len(want) >= share


def fixed_share(fmt):
    """How much of a format is the ad's own words (0–1): a format that is mostly blanks has lost the ad."""
    fixed = len(" ".join(HF.fixed_parts(fmt)).split())
    blanks = len(HF.BLANK.findall(fmt))
    return fixed / max(1, fixed + blanks)


def check(entry):
    """What is wrong with one stripped format ([] when it is usable)."""
    bad = []
    f = entry.get("format") or ""
    if not f.strip():
        return ["no format came back"]
    if not fits(f, entry["original"]):
        bad.append("the format's fixed words are not the ad's own, in order")
    if HF.BLANK.findall(f) and fixed_share(f) < 0.4 and entry["slot"] == "primary":
        bad.append("mostly blanks: the ad's own words were not kept")
    if entry["slot"] == "primary" and cut_off(entry["original"]):
        bad.append("the ad's words on file stop mid-sentence (cut off in the pull), so its format is not whole")
    return bad


def cut_off(text):
    """A primary text that ends on a word, not on a stop, a link, an emoji or a quote: the pull kept part of it."""
    last = (text or "").rstrip()[-1:]
    return bool(last) and (last.isalnum() or last in ",;:-") and not re.search(r"(https?://|\.com|/)\S*$", text.rstrip())


def _ads_block(rows, slot):
    out = []
    for i, r in enumerate(rows, 1):
        out.append(f"### Ad {i}\n\n{r['text']}\n")
    return "\n".join(out)


def _prompt(rows, slot, awareness_ids):
    t = latest_prompt("copy-format-strip").read_text()
    return (t.replace("{awareness_ids}", ", ".join(awareness_ids))
             .replace("{slot}", {"primary": "primary text", "headlines": "headlines", "descriptions": "descriptions"}[slot])
             .replace("{ads}", _ads_block(rows, slot)))


def _parse(out):
    m = re.search(r"```(?:json)?\s*(\[.*\])\s*```", out, re.S) or re.search(r"(\[\s*\{.*\}\s*\])", out, re.S)
    if not m:
        raise ValueError("the strip returned no json list")
    return json.loads(m.group(1))


def _ask(text, model):
    sys.path.append(str(HERE))
    import copy_set as CS
    return CS.claude(text, model)


def build(brand, *, dry_run=False, model="claude-opus-5-5", ask=None, ws=WS, say=print):
    """Strip every row of the newest pull into the bank. Returns the bank (written unless dry_run)."""
    sys.path.append(str(HERE))
    import copy_set as CS
    src = pull(brand, ws)
    if not src:
        raise FileNotFoundError(f"no warehouse pull for {brand}: run library/meta_copy.py --brand {brand} --from-db first")
    d = json.loads(src.read_text())
    levels = list(CS.awareness_levels())
    ask = ask or (lambda text: _ask(text, model))
    entries = []
    for slot in SLOTS:
        rows = sorted((r for r in d["copy"] if r["slot"] == slot and r.get("text", "").strip()),
                      key=lambda r: -float(r.get("spend") or 0))
        n = 0
        for i in range(0, len(rows), CHUNK[slot]):
            part = rows[i:i + CHUNK[slot]]
            text = _prompt(part, slot, levels)
            if dry_run:
                say(f"  {slot} {i + 1}-{i + len(part)}: one call, {len(text):,} characters, {model}")
                continue
            got = _parse(ask(text))
            if len(got) != len(part):
                say(f"  ! {slot} {i + 1}-{i + len(part)}: {len(got)} formats back for {len(part)} ads — matched in order")
            for r, g in zip(part, got):
                n += 1
                e = {"id": f"copyformat_{slug(brand)}_{slot}_{n:02d}", "slot": slot,
                     "name": (r.get("ads") or [{}])[0].get("ad_name", ""),
                     "original": r["text"], "format": (g.get("format") or "").replace("\\n", "\n"),
                     "blanks": g.get("blanks") or [], "awareness": g.get("awareness") if g.get("awareness") in levels else None,
                     "offer": str(g.get("offer", "")).lower() == "yes", "season": g.get("season") or "",
                     "structure": g.get("structure") or "", "why_it_works": g.get("why_it_works") or "",
                     "numbers": {"spend": round(float(r.get("spend") or 0), 2), "purchases": r.get("purchases"),
                                 "cpa": cpa(r), "value": r.get("value"), "why_in": r.get("why") or [],
                                 "ads": len(r.get("ads") or [])},
                     "source_ads": [{"ad_id": a.get("ad_id"), "ad_name": a.get("ad_name")} for a in r.get("ads") or []],
                     "status": "draft"}
                bad = check(e)
                e["state"] = "broken" if bad else "fits"
                if bad:
                    e["problems"] = bad
                entries.append(e)
            say(f"  {slot} {i + 1}-{i + len(part)}: {sum(1 for e in entries if e['slot'] == slot and e['state'] == 'fits')} fit so far")
    if dry_run:
        return None
    bank = {"schema": 1, "brand": slug(brand), "built": datetime.now().isoformat(timespec="seconds"),
            "source": str(src.relative_to(ws)), "prompt": latest_prompt("copy-format-strip").name,
            "rule": d.get("rule"), "window": d.get("window"), "formats": entries}
    p = bank_path(brand, ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(bank, indent=1, ensure_ascii=False) + "\n")
    p.with_suffix(".md").write_text(render_md(bank))
    return bank


def render_md(bank):
    out = [f"# {bank['brand']} — copy formats from our own winning ads", "",
           f"Built {bank['built']} from `{bank['source']}` ({bank.get('rule') or ''}) with `{bank['prompt']}`.",
           "Every format is the real ad's own words with [BLANKS]; status draft until the owner approves.", ""]
    for slot in SLOTS:
        out += [f"## {slot}", ""]
        for e in [e for e in bank["formats"] if e["slot"] == slot]:
            n = e["numbers"]
            out += [f"### {e['id']} — from \"{e['name']}\"",
                    f"${n['spend']:,.0f} spend · {n['purchases']} purchases · CPA ${n['cpa'] or 0:,.2f} · "
                    f"{e['awareness'] or 'level not read'} · {'offer' if e['offer'] else 'no offer'}"
                    + (f" · {e['season']}" if e['season'] else "") + f" · {e['state']}", "",
                    f"*How it's built:* {e['structure']}", "", "```", e["format"], "```", ""]
    return "\n".join(out)


def recheck(brand, ws=WS):
    """Re-run the no-model checks over a built bank (after a check is added) and save it."""
    b = load(brand, ws)
    for e in b["formats"]:
        bad = check(e)
        e["state"] = "broken" if bad else "fits"
        e.pop("problems", None)
        if bad:
            e["problems"] = bad
    p = bank_path(brand, ws)
    p.write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n")
    p.with_suffix(".md").write_text(render_md(b))
    return b


def usable(brand, slot, ws=WS):
    b = load(brand, ws) or {}
    return [e for e in b.get("formats") or [] if e["slot"] == slot and e.get("state") == "fits"
            and e.get("status") != "deprecated"]


ENDING = re.compile(r"(?i)\bend of (?:era|stock)\b|final (?:inventory|\w+ inventory)|last (?:chance|batch|\[product\])|"
                    r"let(?:ting)? (?:it all )?go|downsiz|liquidat|clos(?:e|ing) (?:down|shop)|reorganiz|clean the slate")


def pick(brand, slot, *, awareness=None, promo=False, n=6, ws=WS, levels=None, moment=None):
    """The formats a writer is handed for one slot: offers only on a promotion, no season-tied ad out of season,
    the ad's own awareness level first, then the nearest level, best spend first within each.
    A promotion for a MOMENT (the order names one: Black Friday, a holiday) takes the season formats that sell a sale
    first, and never a closing-down one (2026-10-28, :
    every season format was dropped as "out of season" and the shortlist was all closing-down ads)."""
    if levels is None:
        sys.path.append(str(HERE))
        import copy_set as CS
        levels = {k: v["level"] for k, v in CS.awareness_levels().items()}
    want = levels.get(awareness) if awareness else None
    if moment:
        rows = [e for e in usable(brand, slot, ws) if (promo or not e["offer"]) and not ENDING.search(e["format"] or "")
                # a season format is ours only when its season is a generic holiday sale or our moment itself; one cut
                # for another holiday (St. Patrick's, its clover) never sells Black Friday
                and (not e["season"] or re.search(r"(?i)^\s*(?:holiday|holidays|sale|seasonal)\s*$|" + re.escape(str(moment)),
                                                  str(e["season"])))]
    else:
        rows = [e for e in usable(brand, slot, ws) if not e["season"] and (promo or not e["offer"])]

    def rank(e):
        dist = abs(levels.get(e["awareness"], 9) - want) if want is not None and e["awareness"] else 0
        held = 0 if (moment and e["season"]) else 1                 # the moment's own sale formats first
        return (held, dist, -e["numbers"]["spend"])
    seen, out = set(), []
    for e in sorted(rows, key=rank):
        key = HF.norm(e["format"])[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out[:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("build", "recheck", "show", "pick"))
    ap.add_argument("--brand", required=True)
    ap.add_argument("--slot", choices=SLOTS)
    ap.add_argument("--awareness")
    ap.add_argument("--promo", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="claude-opus-5-5")
    a = ap.parse_args()
    if a.cmd == "build":
        b = build(a.brand, dry_run=a.dry_run, model=a.model)
        if b:
            fit = sum(e["state"] == "fits" for e in b["formats"])
            print(f"{fit} of {len(b['formats'])} formats fit their ad → {bank_path(a.brand).relative_to(WS)}")
    elif a.cmd == "recheck":
        b = recheck(a.brand)
        print(f"{sum(e['state'] == 'fits' for e in b['formats'])} of {len(b['formats'])} formats fit their ad")
    elif a.cmd == "show":
        b = load(a.brand)
        if not b:
            sys.exit(f"no formats yet for {a.brand}: real_formats.py build --brand {a.brand}")
        print(render_md({**b, "formats": [e for e in b["formats"] if not a.slot or e["slot"] == a.slot]}))
    else:
        for slot in ([a.slot] if a.slot else SLOTS):
            print(f"== {slot}")
            for e in pick(a.brand, slot, awareness=a.awareness, promo=a.promo):
                print(f"  {e['id']}  ${e['numbers']['spend']:>9,.0f}  {e['awareness'] or '?':15} {e['format'][:90]!r}")


if __name__ == "__main__":
    main()
