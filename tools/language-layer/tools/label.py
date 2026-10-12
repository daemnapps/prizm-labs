#!/usr/bin/env python3
"""Label customer-language rows with the doctrine's awareness level, a
sophistication signal and the lane their words point to.

Ruled 2026-09-28 (the language bank upgrade — tools/language-layer/docs/
PROPOSAL.md): every row says what its speaker knows, so every hook, body
and close can pull words spoken from the level it is writing for.

    python3 tools/label.py sample --brand B --n 260 [--out <dir>]   # label a spread of rows to check
                                                                     # (default runs/language-layer/B/test-set/)
    python3 tools/label.py apply  --brand B [--avatar A] [--limit N] # label the bank: a proposal under runs/,
                                                                     # then the research gatherer applies it
    python3 tools/label.py origin --brand B [--where "ad comment"]   # recompute `origin` by rule, no model

The doctrine is bound by path (components/marketing-doctrine/slices/), never
restated. A row a person already labelled (`"by"` other than "model") is never
touched. `apply` labels `awareness` and `sophistication` for each row and the
lane the words point to as `lane_words` — it NEVER moves a row between lanes;
moves are listed for review.

`brands/` is read-only to machines (decision-log 2026-09-17). So `apply` and
`origin` write a PROPOSAL — `runs/language-layer/<brand>/<run>/proposal.json`
+ `proposal.md` — and hand it to the one machine ruled to write the bank, the
research gatherer (`gather.py apply --proposal …`), which checks it and writes
it. One command still does both; `--propose-only` stops at the proposal.
Every batch is saved into the proposal as it lands, so a stopped run picks up
where it left off (it reuses the newest proposal not yet applied).
"""
import argparse, json, os, random, re, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from language_layer import engine as E  # noqa: E402
from language_layer import proposal as P  # noqa: E402

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
        f = E.brand_dir(brand) / "channels" / "own-accounts.json"
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
    Ruled 2026-09-28: "internal customer language is different than reddit
    language" · "if a property where our brand name is clearly defined, that
    will count as internal"."""
    brand = brand or LAST_BRAND
    src = row.get("source") or {}
    t = (src.get("type") or "").lower()
    # a comment on one of our own ads sits on our property by definition
    # ("Instagram ad comment", "Facebook ad comment — <ad>", "ad comment — <ad>")
    if "ad comment" in str(src.get("name") or "").lower():
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
    fs = sorted(PROMPTS.glob("label-awareness-v*.md"),
                key=lambda p: int(re.search(r"-v(\d+)(?:-|\.)", p.name).group(1)))
    return fs[-1]


def product_names(brand):
    f = E.brand_dir(brand) / "products" / "heroes.json"
    try:
        d = json.loads(f.read_text())
        items = d if isinstance(d, list) else d.get("heroes") or d.get("products") or []
        names = [str(x.get("name") or x.get("title") or x) if isinstance(x, dict) else str(x) for x in items]
        return ", ".join(n for n in names if n) or brand
    except Exception:
        return brand



def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod


def gemini_key():
    """GEMINI_API_KEY, by NAME, from the environment (the name the mini's
    env.template and the dispatch grants know), then the repo's .env, through
    components/keys/loader.py — asked by NAME, never read from a path."""
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k
    try:
        k = _shared_keys().lookup("GEMINI_API_KEY")
    except Exception:
        k = None
    if not k:
        raise RuntimeError("This tool needs GEMINI_API_KEY. Add it to .env (see .env.example).")
    return k


def run_dir(brand, *parts):
    """Where this tool's output goes: the workspace's runs/language-layer/<brand>/
    — never under the bank root, never beside the code."""
    base = E.WORKSPACE / "runs" / "language-layer" / brand
    return base / Path(*parts) if parts else base


def gemini(text, model, limit=180):
    """The same prompt through Gemini's API — many calls can run at once."""
    import urllib.request
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
           f"?key={gemini_key()}")
    body = json.dumps({"contents": [{"parts": [{"text": text}]}],
                       "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=limit) as r:
        d = json.loads(r.read())
    out = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    return parse_labels(out)


def claude(text, model, limit=300):
    if model.startswith("gemini"):
        try:
            return gemini(text, model)
        except Exception as e:
            raise RuntimeError(f"gemini: {str(e)[:200]}")
    """One call. A call that outlives `limit` is killed with everything it
    started (2026-09-29: parallel calls hung for hours and a plain timeout
    could not stop them) and the batch is split and asked again."""
    import signal
    p = subprocess.Popen(["claude", "-p", "--model", model, "--allowed-tools", ""],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, start_new_session=True,
                         env={k: os.environ[k] for k in KEEP_ENV if k in os.environ})
    try:
        out, err = p.communicate(text, timeout=limit)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        raise RuntimeError(f"the call took over {limit}s — stopped")
    class R: pass
    r = R(); r.returncode, r.stdout, r.stderr = p.returncode, out, err
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


def label(rows, brand, model, batch=20):
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
        except (ValueError, KeyError, subprocess.TimeoutExpired, RuntimeError) as e:
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
    d = Path(a.out) if a.out else run_dir(a.brand, "test-set")
    d.mkdir(parents=True, exist_ok=True)
    (d / "test-set.json").write_text(json.dumps(dict(brand=a.brand, model=a.model, prompt=prompt_file().name,
                                                     sampled=len(pick), labelled=len(labels),
                                                     per_level={k: len(v) for k, v in by_level.items()},
                                                     test=test), indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: len(v) for k, v in by_level.items()}))
    print(d / "test-set.json")


def _same(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", (t or "").lower())).strip()


def bank_root(brand):
    """The tree that holds `brands/` — where the bank was read, so the gatherer
    applies the proposal to the same tree."""
    return E.brand_dir(brand).parent.parent


def open_run(brand, kind, run=None):
    """The run folder for a proposal: `--run` when named; else the newest
    `<kind>-*` run not yet applied (a stopped run resumes); else a new
    `<kind>-<today>` (with a -2, -3 … when that one was already applied)."""
    base = run_dir(brand)
    if run:
        return base / run
    old = sorted((d for d in base.glob(f"{kind}-*") if (d / "proposal.json").is_file()
                  and not (d / "applied.json").is_file()), key=lambda d: d.stat().st_mtime)
    if old:
        return old[-1]
    stamp, n = date.today().isoformat(), 1
    while (base / (f"{kind}-{stamp}" + (f"-{n}" if n > 1 else ""))).exists():
        n += 1
    return base / (f"{kind}-{stamp}" + (f"-{n}" if n > 1 else ""))


def bank_files(brand, avatar=None):
    files = []
    for lang in E._lang_dirs(brand, avatar):
        if lang.is_dir():
            files += [f for f in sorted(lang.rglob("*.json")) if E.USED_DIR not in f.relative_to(lang).parts]
    out = []
    for f in files:
        try:
            out.append((f, json.loads(f.read_text())))
        except Exception:
            continue
    return out


def finish(prop, a, summary, examples=None):
    """Save the proposal, then hand it to the research gatherer unless told not to."""
    path = prop.save(summary, examples)
    print(f"proposal: {path}")
    if getattr(a, "propose_only", False):
        print("proposal only — nothing applied. To apply: "
              f"python3 components/research-gatherer/gather.py apply --proposal {P.rel_run(path)}")
        return 0
    return P.hand_off(path, root=bank_root(a.brand))


def cmd_apply(a):
    """Label every unlabelled row, as a proposal. Identical words from the same
    source and file are read once and the label copied (a survey repeats
    "Results" hundreds of times); batches run --jobs at a time; the proposal is
    saved as rows land, then handed to the gatherer to write."""
    from concurrent.futures import ThreadPoolExecutor
    folder = open_run(a.brand, "label", a.run)
    prop = P.Proposal(a.brand, "language-layer tools/label.py apply", folder).load()
    already = {(r["file"], r["id"]) for r in prop.rows}
    if already:
        print(f"resuming {folder}: {len(already):,} rows already in the proposal", flush=True)
    groups = {}
    for f, d in bank_files(a.brand, a.avatar):
        for i, e in enumerate(d.get("entries") or []):
            if not e.get("id") or not (e.get("text") or "").strip():
                continue
            if (P.rel(f), e["id"]) in already:
                continue
            aw = e.get("awareness")
            if isinstance(aw, dict) and not (a.redo and aw.get("by") == "model"):
                continue
            k = (_same(e.get("text")), (e.get("source") or {}).get("id") or (e.get("source") or {}).get("name"), f.name)
            groups.setdefault(k, []).append((f, i, e))
    reps = []
    for k, members in groups.items():
        f, i, e = members[0]
        reps.append(dict(e, _file=f.name, _key=k))
    if a.limit:
        reps = reps[:a.limit]
    print(f"{sum(len(v) for v in groups.values()):,} rows to label · {len(reps):,} unique · {a.jobs} at a time", flush=True)
    chunks = [reps[i:i + a.batch] for i in range(0, len(reps), a.batch)]
    stamp = date.today().isoformat()
    moves, done = [], [0]

    def one(chunk):
        return chunk, label(chunk, a.brand, a.model, a.batch)

    def summary():
        return dict(labelled=done[0] + len(already), model=a.model, prompt=prompt_file().name,
                    lane_moves_listed=len(moves))

    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        for n, (chunk, labels) in enumerate(pool.map(one, chunks), 1):
            for rep in chunk:
                g = labels.get(rep["id"])
                if not g:
                    continue
                for f, i, e in groups[rep["_key"]]:
                    prop.row(f, i, e,
                             awareness={"level": g["awareness"], "why": g.get("why", ""), "by": "model",
                                        "model": a.model, "date": stamp},
                             sophistication={"signal": g["sophistication"], "by": "model", "date": stamp},
                             lane_words=g["lane_words"], origin=origin_of(e, a.brand), voice=voice_of(e))
                    now = lane_of({"_file": f.name, "funnel": e.get("funnel")})
                    if g["lane_words"] != now and e.get("speaker") != "customer":
                        moves.append({"id": e["id"], "file": P.rel(f), "now": now,
                                      "words_say": g["lane_words"], "text": e.get("text")})
                    done[0] += 1
            if n % 10 == 0 or n == len(chunks):
                prop.save(summary())
                print(f"  {n}/{len(chunks)} batches · {done[0]:,} rows labelled", flush=True)
    rep = run_dir(a.brand)
    rep.mkdir(parents=True, exist_ok=True)
    (rep / f"lane-moves-{stamp}.json").write_text(json.dumps(moves, indent=1, ensure_ascii=False) + "\n")
    print(f"labelled {done[0]:,} rows · {len(moves)} rows whose words point to another lane (listed, not moved): {rep}")
    return finish(prop, a, summary())


def cmd_origin(a):
    """Recompute `origin` by the rule in origin_of() — no model — for the rows
    whose source name contains --where (every row when --where is empty).
    Only rows whose origin would change go into the proposal."""
    folder = open_run(a.brand, "origin", a.run)
    prop = P.Proposal(a.brand, "language-layer tools/label.py origin", folder)
    where = (a.where or "").lower()
    before, after, seen = {}, {}, 0
    for f, d in bank_files(a.brand, a.avatar):
        for i, e in enumerate(d.get("entries") or []):
            if not e.get("id") or where not in str((e.get("source") or {}).get("name") or "").lower():
                continue
            seen += 1
            old, new = e.get("origin"), origin_of(e, a.brand)
            before[str(old)] = before.get(str(old), 0) + 1
            after[new] = after.get(new, 0) + 1
            if old != new:
                prop.row(f, i, e, origin=new)
    s = dict(rule="origin_of() in tools/language-layer/tools/label.py", where=a.where or "(every row)",
             rows_matched=seen, origin_before=before, origin_after=after, changed=len(prop.rows))
    print(json.dumps(s))
    if not prop.rows:
        print("nothing to change — no proposal written")
        return 0
    return finish(prop, a, s)


# the labeller's default model: the registry id (components/models/models.json,
# `claude-sonnet-5`, which the old alias `sonnet` resolves to) — the same model
# as before, named the way the registry names it
MODEL = "claude-sonnet-5"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "apply", "origin"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", default=None)
    ap.add_argument("--n", type=int, default=260)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--redo", action="store_true", help="relabel rows the model labelled before (never a person's)")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--run", default=None, help="the run folder under runs/language-layer/<brand>/ (default: resume or a new dated one)")
    ap.add_argument("--where", default="", help="origin: only rows whose source name contains this")
    ap.add_argument("--propose-only", action="store_true", help="write the proposal under runs/ and stop — nothing applied")
    a = ap.parse_args(argv)
    return {"sample": cmd_sample, "apply": cmd_apply, "origin": cmd_origin}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
