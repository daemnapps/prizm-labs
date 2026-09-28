#!/usr/bin/env python3
"""Label customer-language rows with the doctrine's awareness level, a
sophistication signal and the lane their words point to.

Damon, 2026-09-28 (the language bank upgrade — lab/damon/language-bank/
PROPOSAL-damon.md): every row says what its speaker knows, so every hook, body
and close can pull words spoken from the level it is writing for.

    python3 tools/label.py sample --brand B --n 260 --out <dir>     # label a spread of rows for Damon to check
    python3 tools/label.py apply  --brand B [--avatar A] [--limit N] # label the bank, batch by batch, in place

The doctrine is bound by path (components/marketing-doctrine/slices/), never
restated. A row a person already labelled (`"by"` other than "model") is never
touched. `apply` writes `awareness` and `sophistication` onto each row and the
lane the words point to as `lane_words` — it NEVER moves a row between lanes;
moves are listed for Damon. Every batch is saved as it lands, so a stopped run
picks up where it left off.
"""
import argparse, json, os, random, re, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from language_layer import engine as E  # noqa: E402

WS = E.WORKSPACE
PROMPTS = HERE.parent / "prompts"
SLICES = WS / "components" / "marketing-doctrine" / "slices"
LEVELS = ["unaware", "problem-aware", "solution-aware", "product-aware", "most-aware",
          "unclear"]
INTERNAL_TYPES = ("survey", "ticket", "dm", "database", "email", "interview", "focus-group", "order-note")


_OWN = {}
LAST_BRAND = ""   # set by label(); lets origin_of() be called without a brand


def own_terms(brand):
    """The brand's own properties: its name and the accounts it runs, from
    brands/<brand>/channels/own-accounts.json (plus the brand slug itself)."""
    if brand not in _OWN:
        terms = {brand.lower()}
        f = WS / "brands" / brand / "channels" / "own-accounts.json"
        try:
            d = json.loads(f.read_text())
            terms |= {str(x).lower().lstrip("@") for x in (d.get("names") or []) + (d.get("handles") or [])}
        except Exception:
            pass
        _OWN[brand] = terms
    return _OWN[brand]


def origin_of(row, brand=""):
    """internal — our own relationship with the customer (surveys, tickets,
    DMs, our database) AND any property where our brand is clearly named (our
    accounts' posts and their comments, our campaign creators' posts);
    external — everyone else's spaces (Reddit, forums, other creators,
    competitors). Read off the row's source, no model.
    Damon, 2026-09-28: "internal customer language is different than reddit
    language" · "if a property where our brand name is clearly defined, that
    will count as internal"."""
    brand = brand or LAST_BRAND
    src = row.get("source") or {}
    t = (src.get("type") or "").lower()
    # a comment on one of our own ads sits on our property by definition
    if t == "comment" and str(src.get("name") or "").lower().startswith("ad comment"):
        return "internal"
    if brand and str(src.get("property") or "").lower().lstrip("@") in own_terms(brand):
        return "internal"
    if t in INTERNAL_TYPES or (row.get("speaker") or "") in ("brand", "creator"):
        return "internal"
    ref = str(src.get("ref") or "")
    # the source's own name and its web address — never a file path in our
    # brand folder, which names the brand whatever the words' origin
    hay = (str(src.get("name") or "") + " " + (ref if ref.startswith("http") else "")).lower()
    words = set(__import__("re").findall(r"@?([a-z0-9_.]+)", hay))
    if brand and (own_terms(brand) & words):
        return "internal"
    return "external"


def voice_of(row):
    return "brand" if (row.get("speaker") or "") in ("brand", "creator") else "audience"
SIGNALS = ["none", "claim-heard", "claim-discounted", "mechanism-heard", "believes-none"]
LANES = ["customer", "lead", "prospect"]
KEEP_ENV = ("HOME", "PATH", "TERM", "LOGNAME", "SHELL", "LANG", "LC_ALL", "TMPDIR")


def prompt_file():
    fs = sorted(PROMPTS.glob("label-awareness-v*-damon.md"),
                key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    return fs[-1]


def product_names(brand):
    f = WS / "brands" / brand / "products" / "heroes.json"
    try:
        d = json.loads(f.read_text())
        items = d if isinstance(d, list) else d.get("heroes") or d.get("products") or []
        names = [str(x.get("name") or x.get("title") or x) if isinstance(x, dict) else str(x) for x in items]
        return ", ".join(n for n in names if n) or brand
    except Exception:
        return brand


def claude(text, model):
    r = subprocess.run(["claude", "-p", "--model", model, "--allowed-tools", ""],
                       input=text, capture_output=True, text=True, timeout=900,
                       env={k: os.environ[k] for k in KEEP_ENV if k in os.environ})
    if r.returncode or not r.stdout.strip():
        raise RuntimeError((r.stderr or r.stdout or "claude failed")[-600:])
    return parse_labels(r.stdout)


def parse_labels(text):
    """The labels from a reply — a fenced block, or the outermost {…}. A reply
    cut off mid-way raises, and the batch is split and asked again."""
    m = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
    body = m[-1] if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(body)["labels"]


def lane_of(row):
    f = row.get("_file") or ""
    return {"prospects.json": "prospect", "leads.json": "lead"}.get(f, "customer" if row.get("funnel") == "customer" else row.get("funnel") or "?")


def label(rows, brand, model, batch=50):
    tpl = prompt_file().read_text()
    base = (tpl.replace("{awareness_levels}", (SLICES / "awareness.md").read_text())
               .replace("{sophistication_stages}", (SLICES / "sophistication.md").read_text())
               .replace("{product_names}", product_names(brand)))
    global LAST_BRAND
    LAST_BRAND = brand
    out = {}

    def ask(chunk):
        """One call; a reply that does not parse is split in half and asked
        again, down to single rows (2026-09-28: a 100-row reply came back
        malformed and held a whole pull)."""
        lines = "\n".join(json.dumps({"id": r["id"], "lane": lane_of(r), "speaker": r.get("speaker"),
                                      "source": (r.get("source") or {}).get("name"),
                                      "origin": origin_of(r, brand), "voice": voice_of(r),
                                      "words": (r.get("text") or "")[:600]}, ensure_ascii=False) for r in chunk)
        try:
            return claude(base.replace("{rows}", lines), model)
        except (ValueError, KeyError) as e:
            if len(chunk) <= 1:
                print(f"  could not label {chunk[0].get('id')}: {str(e)[:80]}", flush=True)
                return []
            h = len(chunk) // 2
            return ask(chunk[:h]) + ask(chunk[h:])

    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        got = ask(chunk)
        for g in got:
            if g.get("id") in {r["id"] for r in chunk}:
                g["awareness"] = g.get("awareness") if g.get("awareness") in LEVELS else "unclear"
                g["sophistication"] = g.get("sophistication") if g.get("sophistication") in SIGNALS else "none"
                g["lane_words"] = g.get("lane_words") if g.get("lane_words") in LANES else "prospect"
                out[g["id"]] = g
        print(f"  labelled {min(i + batch, len(rows))}/{len(rows)}", flush=True)
    return out


def cmd_sample(a):
    rows = [r for r in E.load(a.brand) if r.get("id") and (r.get("text") or "").strip()]
    rnd = random.Random(7)
    # a spread across what the rows ARE, so every level shows up: by use tag and by lane
    buckets = {}
    for r in rows:
        u = r.get("use"); u = u[0] if isinstance(u, list) and u else u
        buckets.setdefault((lane_of(r), u), []).append(r)
    pick = []
    for k, v in sorted(buckets.items(), key=lambda kv: str(kv[0])):
        rnd.shuffle(v); pick += v[:max(2, min(8, len(v) // 150 + 2))]
    rnd.shuffle(pick); pick = pick[:a.n]
    labels = label(pick, a.brand, a.model)
    by_level = {}
    for r in pick:
        g = labels.get(r["id"])
        if g:
            by_level.setdefault(g["awareness"], []).append({**g, "text": r.get("text"), "lane": lane_of(r),
                                                            "origin": origin_of(r, a.brand), "voice": voice_of(r),
                                                            "speaker": r.get("speaker"), "use": r.get("use"),
                                                            "source": (r.get("source") or {}).get("name")})
    test = {lv: by_level.get(lv, [])[:20] for lv in LEVELS}
    d = Path(a.out); d.mkdir(parents=True, exist_ok=True)
    (d / "test-set.json").write_text(json.dumps(dict(brand=a.brand, model=a.model, prompt=prompt_file().name,
                                                     sampled=len(pick), labelled=len(labels),
                                                     per_level={k: len(v) for k, v in by_level.items()},
                                                     test=test), indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: len(v) for k, v in by_level.items()}))
    print(d / "test-set.json")


def cmd_apply(a):
    base = E.bank_dir(E.brand_dir(a.brand))
    files = []
    for lang in E._lang_dirs(a.brand, a.avatar):
        files += [f for f in sorted(lang.rglob("*.json")) if E.USED_DIR not in f.relative_to(lang).parts]
    moves, done = [], 0
    for f in files:
        data = json.loads(f.read_text())
        todo = [e for e in data.get("entries") or []
                if e.get("id") and (e.get("text") or "").strip()
                and (not e.get("awareness") or (e["awareness"].get("by") == "model" and a.redo))]
        if a.limit:
            todo = todo[:max(0, a.limit - done)]
        if not todo:
            continue
        for e in todo:
            e["_file"] = f.name
        for i in range(0, len(todo), a.batch):
            chunk = todo[i:i + a.batch]
            labels = label(chunk, a.brand, a.model, a.batch)
            stamp = date.today().isoformat()
            for e in chunk:
                g = labels.get(e["id"])
                e.pop("_file", None)
                if not g:
                    continue
                e["awareness"] = {"level": g["awareness"], "why": g.get("why", ""), "by": "model",
                                  "model": a.model, "date": stamp}
                e["sophistication"] = {"signal": g["sophistication"], "by": "model", "date": stamp}
                e["lane_words"] = g["lane_words"]
                e["origin"] = origin_of(e, a.brand)
                e.setdefault("voice", voice_of(e))
                if g["lane_words"] != lane_of({"_file": f.name, "funnel": e.get("funnel")}) and e.get("speaker") != "customer":
                    moves.append({"id": e["id"], "file": str(f.relative_to(WS)), "now": f.name,
                                  "words_say": g["lane_words"], "text": e.get("text")})
            f.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")   # saved per batch
            done += len(chunk)
        if a.limit and done >= a.limit:
            break
    rep = WS / "runs" / "language-bank" / a.brand
    rep.mkdir(parents=True, exist_ok=True)
    (rep / f"lane-moves-{date.today().isoformat()}.json").write_text(json.dumps(moves, indent=1, ensure_ascii=False) + "\n")
    print(f"labelled {done} rows · {len(moves)} rows whose words point to another lane (listed, not moved): {rep}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "apply"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", default=None)
    ap.add_argument("--n", type=int, default=260)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--redo", action="store_true", help="relabel rows the model labelled before (never a person's)")
    ap.add_argument("--model", default="sonnet")
    a = ap.parse_args()
    {"sample": cmd_sample, "apply": cmd_apply}[a.cmd](a)


if __name__ == "__main__":
    main()
