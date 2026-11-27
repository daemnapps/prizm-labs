#!/usr/bin/env python3
"""google_copy — Google text ads written the way the Meta copy is: swipe → strip → fill → check.

    google_copy.py strip --brand <b> --swipes <competitor-ads.json> [--dry-run]
    google_copy.py write --brand <b> --groups <groups.json> --product <product.md> --label <name>
                         [--only <group>] [--allowed-host <host> ...] [--dry-run]

Ruled 2026-11-23: the first Google campaigns carried raw customer lines instead of ads; Google text ads now run
through a proper chain. The same pattern as format_copy.py (real ads stripped to
[BLANKS], filled with our words), for Google's text ads:

  strip  competitors' live Google ads (the swipe, longest-running first) → one format per headline and description,
         each with its slot (prompts/google-strip-vN-owner.md). Written once per brand to
         runs/copywriter/<brand>/google-formats/ (formats.json, formats.md, the prompt as sent, the answer).
  write  per ad group: its searches, the landing page's own promise (read live), the product file, the offer on the
         page, our customers' words for the topic → 15 headlines and 4 descriptions, every line one handed format
         (prompts/google-fill-vN-owner.md). Checked with no model (check()), sent back once with what broke, a line
         still broken dropped and named. Written to runs/copywriter/<brand>/<label>/<group>/ (ad.json, ad.md,
         prompt as sent, answer) and runs/copywriter/<brand>/<label>/ads.json for the whole campaign.

Nothing here calls Google or writes into a brand folder. Putting the ads into Google is the Google tool's job, after
a person has read them.
"""
import argparse, json, re, sys, urllib.request, html as H
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
COPY = HERE.parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
if str(WS / "components/run-kit") not in sys.path:
    sys.path.append(str(WS / "components/run-kit"))
from run_kit import tiers as _tiers  # noqa: E402  the one model table, entry "copywriter-formats" (2026-11-26)
sys.path.append(str(HERE))
RUNS = WS / "runs"                     # tests point this at a temp folder

HEADLINE, DESCRIPTION, PATH = 30, 90, 15
N_HEADLINES, N_DESCRIPTIONS = 15, 4
MIN_HEADLINES, MIN_DESCRIPTIONS, MIN_KEYWORD = 8, 2, 3
SLOTS = ["search", "problem", "result", "how-it-works", "proof", "offer", "guarantee", "who-its-for",
         "call-to-action", "brand", "objection"]
STRIP_MODEL = _tiers.model("copywriter-formats", "checks")    # stripping is rule-following: the checks tier
WRITE_MODEL = _tiers.model("copywriter-formats", "designs")   # writing: the designs tier
TOOL = "google_copy"
# Words Google's healthcare and misleading-claims policies hold, and that no product file here claims.
HELD_WORDS = ["cure", "cures", "cured", "heal", "heals", "healed", "medical", "medically", "clinically", "clinical",
              "dermatologist", "doctor", "prescription", "fda", "permanent", "permanently", "guaranteed results"]
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")
PRICE = re.compile(r"\$\s?\d[\d,]*(?:\.\d\d)?")


def now():
    return datetime.now().isoformat(timespec="seconds")


def prompt(name):
    files = sorted(COPY.glob(f"prompts/{name}-v*-owner.md"), key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not files:
        sys.exit(f"no prompt {name}")
    return files[-1]


def body(p):
    t = Path(p).read_text()
    return t.split("\n---\n", 1)[1].strip() if "\n---\n" in t else t


def fill(t, **kw):
    for k, v in kw.items():
        t = t.replace("{" + k + "}", str(v))
    return t


def ask(text, model):
    import copy_set as CS
    return CS.claude(text, model)


def parse_json(out):
    m = re.search(r"```json\s*(.*?)```", out, re.S)
    raw = m.group(1) if m else out
    s = min([i for i in (raw.find("["), raw.find("{")) if i >= 0] or [0])
    return json.loads(raw[s:])


def runs_dir(brand, label):
    d = RUNS / "copywriter" / brand / label
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------- strip ----------

def swipe_lines(ads):
    """Every distinct line of every ad, longest-running ad first: [(n, kind, text, ad)]."""
    seen, out = set(), []
    for a in sorted(ads, key=lambda a: -(a.get("days_running") or 0)):
        for kind, key in (("headline", "headlines"), ("description", "descriptions")):
            for t in a.get(key) or []:
                t = " ".join(str(t).split())
                if t.endswith("...") or t.endswith("…") or len(t) < 4 or t.lower() in seen:
                    continue
                seen.add(t.lower())
                out.append((len(out) + 1, kind, t, a))
    return out


def strip(brand, swipes, dry_run=False, say=print, ask_fn=None):
    ads = json.loads(Path(swipes).read_text())
    ads = [a for a in ads if (a.get("network") in (None, "search")) and (a.get("headlines") or a.get("descriptions"))]
    lines = swipe_lines(ads)
    text = "\n".join(f"{n}. [{kind}] \"{t}\" — {a.get('domain') or a.get('advertiser')}, {a.get('days_running') or 0} days running"
                     for n, kind, t, a in lines)
    p = prompt("google-strip")
    sent = fill(body(p), slots=", ".join(SLOTS), ads=text)
    say(f"{TOOL} strip: {len(ads)} ads, {len(lines)} lines → {RUNS / 'copywriter' / brand / 'google-formats'}")
    if dry_run:                                   # spends nothing, writes nothing
        return {"ads": len(ads), "lines": len(lines), "prompt": p.name}
    run = runs_dir(brand, "google-formats")
    (run / "strip--sent.md").write_text(sent)
    out = (ask_fn or (lambda t: ask(t, STRIP_MODEL)))(sent)
    (run / "strip--answer.md").write_text(out)
    got = {int(x["n"]): x for x in parse_json(out) if isinstance(x, dict) and "n" in x}
    formats = []
    for n, kind, t, a in lines:
        g = got.get(n) or {}
        f = (g.get("format") or "").strip()
        state = "ok" if f and "[" in f and fixed_words(f) else ("whole line" if f else "missing")
        formats.append({"id": ("h" if kind == "headline" else "d") + str(n), "kind": kind, "real": t, "format": f,
                        "blanks": g.get("blanks") or re.findall(r"\[([^\]]+)\]", f), "slot": g.get("slot") or "",
                        "from": a.get("domain") or a.get("advertiser"), "days": a.get("days_running") or 0,
                        "status": "draft", "state": state})
    rec = {"tool": TOOL, "step": "strip", "at": now(), "brand_dir": brand, "prompt": p.name, "model": STRIP_MODEL,
           "ads": len(ads), "formats": formats}
    (run / "formats.json").write_text(json.dumps(rec, indent=1))
    (run / "formats.md").write_text(formats_md(formats))
    ok = [f for f in formats if f["state"] == "ok"]
    say(f"{len(ok)} of {len(formats)} lines stripped to a usable format")
    return rec


def fixed_words(f):
    return re.sub(r"\[[^\]]*\]", " ", f).split()


def formats_md(formats):
    out = ["# Google ad formats (stripped from competitors' live Google ads)", ""]
    for kind in ("headline", "description"):
        out += [f"## {kind.title()}s", "", "| id | format | slot | from | days | state |", "|---|---|---|---|---|---|"]
        for f in formats:
            if f["kind"] == kind:
                out.append(f"| {f['id']} | {f['format'] or f['real']} | {f['slot']} | {f['from']} | {f['days']} | {f['state']} |")
        out.append("")
    return "\n".join(out)


# ---------- write ----------

def page_promise(url, fetch=None):
    """The landing page's own words: headings, then the lines that carry proof, offer or guarantee."""
    try:
        raw = fetch(url) if fetch else urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf8", "ignore")
    except Exception as e:  # a page that will not load is said, never guessed
        return {"text": f"(the page did not load: {e})", "prices": [], "promo": False}
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    clean = lambda s: " ".join(H.unescape(re.sub(r"<[^>]+>", " ", s)).split())
    heads = []
    for h in re.findall(r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>", t):
        c = clean(h)
        if c and c not in heads:
            heads.append(c)
    txt = clean(t)
    keys = r"(guarantee|money back|refund|reviews?|rated|\d+% off|% off|free|off |save|ends |customers|verified)"
    lines = []
    for m in re.finditer(keys, txt, re.I):
        s = txt[max(0, m.start() - 60): m.end() + 60].strip()
        if not any(s[:40] in x for x in lines):
            lines.append(s)
    prices = sorted(set(PRICE.findall(txt)))
    promo = bool(re.search(r"(black friday|cyber monday|\d+% off|sale ends|ends (nov|dec|jan|today))", txt, re.I))
    text = "Headings:\n" + "\n".join("- " + h for h in heads[:16]) + "\n\nProof, offer and guarantee lines:\n" + "\n".join("- …" + l + "…" for l in lines[:14])
    return {"text": text, "prices": prices, "promo": promo}


def product_text(path, limit=7000):
    return Path(path).read_text()[:limit]


def product_caps(path):
    """The product's own capitalised names (its title's all-capital words): the only capitals allowed mid-word."""
    first = next((l for l in Path(path).read_text().splitlines() if l.startswith("# ")), "")
    return {w.strip("™®").upper() for w in re.findall(r"[A-Z]{2,}[™®]?", first)}


def check(ad, *, formats, keywords, competitors, prices, promo, caps, final_url, allowed_hosts):
    """Every problem with one ad, in plain words; the ad unchanged. No model."""
    probs = []
    fid = {f["id"]: f for f in formats}
    hosts = [h.lower() for h in allowed_hosts or []]
    if hosts and not any(re.match(rf"https?://{re.escape(h)}(/|$)", final_url or "", re.I) for h in hosts):
        probs.append(f"landing page {final_url} is not on {', '.join(hosts)}")
    comp = [c.lower() for c in competitors if c]
    seen = set()
    for kind, lim in (("headlines", HEADLINE), ("descriptions", DESCRIPTION)):
        for i, x in enumerate(ad.get(kind) or []):
            t = (x.get("text") or "").strip()
            where = f"{kind[:-1]} {i + 1} \"{t}\""
            if not t:
                probs.append(f"{where}: empty"); continue
            if len(t) > lim:
                probs.append(f"{where}: {len(t)} characters, the limit is {lim}")
            if t.lower() in seen:
                probs.append(f"{where}: says the same as another line")
            seen.add(t.lower())
            if kind == "headlines" and "!" in t:
                probs.append(f"{where}: Google refuses an exclamation mark in a headline")
            if EMOJI.search(t):
                probs.append(f"{where}: emoji")
            low = " " + re.sub(r"[^a-z0-9 ]", " ", t.lower()) + " "
            for c in comp:
                if f" {c} " in low:
                    probs.append(f"{where}: names another brand ({c})")
            for w in HELD_WORDS:
                if f" {w} " in low:
                    probs.append(f"{where}: \"{w}\" is a claim not on file")
            for p in PRICE.findall(t):
                if not promo:
                    probs.append(f"{where}: a price ({p}) on an ad that is not a promotion")
                elif p.replace(" ", "") not in [q.replace(" ", "") for q in prices]:
                    probs.append(f"{where}: {p} is not a price on the landing page")
            for w in re.findall(r"\b[A-Z]{3,}\b", t):
                if w not in caps:
                    probs.append(f"{where}: \"{w}\" in capitals")
            f = fid.get(x.get("format"))
            if not f or f["kind"] != kind[:-1] or f["state"] != "ok":
                probs.append(f"{where}: not one of the {kind[:-1]} formats handed over ({x.get('format')})")
    hs = [(x.get("text") or "").lower() for x in ad.get("headlines") or []]
    kw_hits = sum(1 for h in hs if any(all(w in h for w in k.lower().split()) for k in keywords))
    if keywords and kw_hits < MIN_KEYWORD:
        probs.append(f"only {kw_hits} headlines carry the words of a search; {MIN_KEYWORD} are needed")
    if len(ad.get("headlines") or []) < N_HEADLINES:
        probs.append(f"{len(ad.get('headlines') or [])} headlines, {N_HEADLINES} are asked")
    if len(ad.get("descriptions") or []) < N_DESCRIPTIONS:
        probs.append(f"{len(ad.get('descriptions') or [])} descriptions, {N_DESCRIPTIONS} are asked")
    for k in ("path1", "path2"):
        v = ad.get(k) or ""
        if len(v) > PATH or " " in v:
            probs.append(f"{k} \"{v}\": at most {PATH} characters, no spaces")
    return probs


def keep_clean(ad, problems):
    """Drop every line a problem names; the counts after."""
    bad = set()
    for p in problems:
        m = re.match(r"(headline|description) (\d+) ", p)
        if m:
            bad.add((m.group(1) + "s", int(m.group(2)) - 1))
    out = dict(ad)
    for kind in ("headlines", "descriptions"):
        out[kind] = [x for i, x in enumerate(ad.get(kind) or []) if (kind, i) not in bad]
    return out, sorted(bad)


def fmt_list(formats, kind):
    rows = [f for f in formats if f["kind"] == kind and f["state"] == "ok"]
    rows.sort(key=lambda f: -f["days"])
    return "\n".join(f"- {f['id']} · {f['slot']} · {f['days']} days · {f['format']}" for f in rows)


def write_group(brand, g, *, formats, product, offer_note, competitors, caps, allowed_hosts, run, ask_fn, say, fetch=None,
                aim=None):
    page = page_promise(g["final_url"], fetch)
    kws = sorted(g.get("keywords") or [], key=lambda k: -(k.get("searches") or 0))
    keywords = [k["text"] for k in kws]
    kw_text = "\n".join(f"- {k['text']}" + (f" ({k['searches']:,})" if k.get("searches") else "") for k in kws[:25])
    words = "\n".join(f"- \"{w['text']}\"" + (f" [{w['row']}]" if w.get("row") else "") for w in (g.get("words") or [])[:40]) or "(none on file for this topic)"
    offer = (offer_note + "\n" if offer_note else "") + ("This page runs a PROMOTION today; its prices: " + ", ".join(page["prices"]) if page["promo"] else "Not a promotion: no price in the ad.")
    p = prompt("google-fill")
    base = fill(body(p), group=g["name"], keywords=kw_text, final_url=g["final_url"], page=page["text"],
                product=product_text(product), offer=offer, words=words,
                headline_formats=fmt_list(formats, "headline"), description_formats=fmt_list(formats, "description"),
                min_keyword=MIN_KEYWORD if g.get("echo_search", True) else "0 (these searches are other brands' names: never write them; answer what that person wants instead)", n_headlines=N_HEADLINES, n_descriptions=N_DESCRIPTIONS)
    # who it is for (2026-11-25): a group's own avatar, else the campaign's; a group that names none says nothing
    import copy_set as CS
    g_aim = {**(aim or {}), **{k: g[k] for k in ("avatar", "sub", "demographic") + CS.AIM_WHAT if g.get(k)}}
    who_block, stamp = CS.who_aim(brand, g_aim.get("avatar"), g_aim.get("sub"), g_aim.get("demographic"),
                                  dict({k: g_aim[k] for k in CS.AIM_WHAT if g_aim.get(k)}, product=str(product)))
    base = who_block + base
    gdir = run / re.sub(r"[^a-z0-9-]+", "-", g["name"].lower()).strip("-")
    gdir.mkdir(parents=True, exist_ok=True)
    echo = g.get("echo_search", True)        # a group bought on other brands' names never repeats the search
    kw = dict(formats=formats, keywords=keywords if echo else [], competitors=competitors, prices=page["prices"], promo=page["promo"],
              caps=caps, final_url=g["final_url"], allowed_hosts=allowed_hosts)
    tries, ad, problems = [], None, []
    for attempt in (1, 2):
        repair = "" if attempt == 1 else ("## What broke last time — fix every one, keep every line that was fine\n\n" +
                                          "\n".join("- " + x for x in problems) + "\n\nYour last answer:\n```json\n" + json.dumps(ad, indent=1) + "\n```")
        sent = fill(base, repair=repair)
        (gdir / f"write-{attempt}--sent.md").write_text(sent)
        out = ask_fn(sent)
        (gdir / f"write-{attempt}--answer.md").write_text(out)
        try:
            ad = parse_json(out)
        except Exception as e:
            problems = [f"the answer was not readable json: {e}"]
            tries.append({"try": attempt, "problems": problems}); continue
        problems = check(ad, **kw)
        tries.append({"try": attempt, "problems": problems})
        if not problems:
            break
    if not isinstance(ad, dict):
        ad = {"headlines": [], "descriptions": []}
    clean, dropped = keep_clean(ad, problems)
    left = check(clean, **kw)
    state = "ok" if not left else ("short" if len(clean.get("headlines", [])) >= MIN_HEADLINES and len(clean.get("descriptions", [])) >= MIN_DESCRIPTIONS else "held")
    rec = {"group": g["name"], "final_url": g["final_url"], "aim": stamp, "keywords": keywords[:25], "page_promo": page["promo"],
           "page_prices": page["prices"], "ad": clean, "written": ad, "dropped": [f"{k[:-1]} {i + 1}" for k, i in dropped],
           "tries": tries, "left": left, "state": state, "status": "draft", "prompt": p.name, "model": WRITE_MODEL}
    (gdir / "ad.json").write_text(json.dumps(rec, indent=1))
    (gdir / "ad.md").write_text(ad_md(rec, formats))
    say(f"  {g['name']}: {len(clean.get('headlines', []))} headlines · {len(clean.get('descriptions', []))} descriptions · {state}"
        + (f" · dropped {len(dropped)}" if dropped else ""))
    return rec


def ad_md(rec, formats):
    fid = {f["id"]: f for f in formats}
    out = [f"# {rec['group']}", "", f"Landing page: {rec['final_url']}", f"State: {rec['state']}", "", "## Headlines", "",
           "| # | headline | chars | slot | format (from) |", "|---|---|---|---|---|"]
    for i, x in enumerate(rec["ad"].get("headlines") or []):
        f = fid.get(x.get("format"), {})
        out.append(f"| {i + 1} | {x['text']} | {len(x['text'])} | {x.get('slot', '')} | {f.get('format', '')} ({f.get('from', '')}) |")
    out += ["", "## Descriptions", "", "| # | description | chars | slot | format (from) |", "|---|---|---|---|---|"]
    for i, x in enumerate(rec["ad"].get("descriptions") or []):
        f = fid.get(x.get("format"), {})
        out.append(f"| {i + 1} | {x['text']} | {len(x['text'])} | {x.get('slot', '')} | {f.get('format', '')} ({f.get('from', '')}) |")
    out += ["", f"Paths: /{rec['ad'].get('path1', '')}/{rec['ad'].get('path2', '')}"]
    if rec["dropped"] or rec["left"]:
        out += ["", "## Dropped or still open", ""] + ["- dropped " + d for d in rec["dropped"]] + ["- " + p for p in rec["left"]]
    return "\n".join(out) + "\n"


def write(brand, groups, product, label, only=None, allowed_hosts=None, dry_run=False, say=print, ask_fn=None, fetch=None,
          aim=None):
    G = json.loads(Path(groups).read_text())
    fmt_file = RUNS / "copywriter" / brand / "google-formats" / "formats.json"
    if not fmt_file.is_file():
        sys.exit("no Google formats yet: run `google_copy.py strip` first")
    formats = json.loads(fmt_file.read_text())["formats"]
    import copy_set as CS
    aim = {**{k: G[k] for k in ("avatar", "sub", "demographic") + CS.AIM_WHAT if G.get(k)},
           **{k: v for k, v in (aim or {}).items() if v}}
    gs = [g for g in G["groups"] if not only or g["name"] in only]
    say(f"{TOOL} write: {len(gs)} ad groups · {sum(1 for f in formats if f['state'] == 'ok')} formats · {Path(product).name}")
    if dry_run:
        for g in gs:
            say(f"  {g['name']}: {len(g.get('keywords') or [])} searches · {len(g.get('words') or [])} customer lines · {g['final_url']}")
        return {"groups": len(gs)}
    run = runs_dir(brand, label)
    comp = G.get("competitors") or []
    caps = product_caps(product) | {c.upper() for c in G.get("caps") or []}   # the brand's own capitals, from the run's input
    ask_fn = ask_fn or (lambda t: ask(t, WRITE_MODEL))
    recs = [write_group(brand, g, formats=formats, product=product, offer_note=G.get("offer_note", ""), competitors=comp,
                        caps=caps, allowed_hosts=allowed_hosts, run=run, ask_fn=ask_fn, say=say, fetch=fetch, aim=aim) for g in gs]
    prev = {}
    if (run / "ads.json").is_file():
        prev = {r["group"]: r for r in json.loads((run / "ads.json").read_text()).get("groups", [])}
    prev.update({r["group"]: r for r in recs})
    out = {"tool": TOOL, "at": now(), "campaign": G.get("campaign"), "product": Path(product).name, "groups": list(prev.values())}
    (run / "ads.json").write_text(json.dumps(out, indent=1))
    (run / "run.json").write_text(json.dumps({"tool": TOOL, "at": now(), "label": label, "groups": [r["group"] for r in recs],
                                              "states": {r["group"]: r["state"] for r in recs}, "model": WRITE_MODEL}, indent=1))
    say(f"→ {run}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("strip"); s.add_argument("--brand", required=True); s.add_argument("--swipes", required=True)
    s.add_argument("--dry-run", action="store_true")
    w = sub.add_parser("write"); w.add_argument("--brand", required=True); w.add_argument("--groups", required=True)
    w.add_argument("--product", required=True); w.add_argument("--label", required=True)
    w.add_argument("--only", action="append"); w.add_argument("--allowed-host", action="append")
    w.add_argument("--dry-run", action="store_true")
    w.add_argument("--avatar", help="who the campaign speaks to; a group in the groups file may name its own")
    w.add_argument("--sub"); w.add_argument("--demographic"); w.add_argument("--awareness")
    w.add_argument("--doubt", choices=["does-it-work", "for-me", "worth-it", "trust-you"])
    import importlib.util as _u, pathlib as _pl
    _s = _u.spec_from_file_location("profile_arg", next(q for q in _pl.Path(__file__).resolve().parents if q.name == "components") / "naming" / "profile_arg.py")
    _PA = _u.module_from_spec(_s); _s.loader.exec_module(_PA)   # --profile <avatar>[_<sub>][_<demographic>] (naming/PEOPLE.md)
    a = ap.parse_args(_PA.expand(None, has=('avatar', 'sub', 'demographic')))
    if a.cmd == "strip":
        strip(a.brand, a.swipes, a.dry_run)
    else:
        write(a.brand, a.groups, a.product, a.label, a.only, a.allowed_host, a.dry_run,
              aim={k: getattr(a, k) for k in ("avatar", "sub", "demographic", "awareness", "doubt")})


if __name__ == "__main__":
    main()
