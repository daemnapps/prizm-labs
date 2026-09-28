#!/usr/bin/env python3
"""THE VARIATION VIDEO CHAIN — one proven ad, grown into a tree of briefs.

Damon, 2026-09-28: "Once you've hit a winner, regardless of where it's at,
you're going to control for that existing awareness stage for sure. In this,
we want to also do the other awareness stages, and then each of those is
going to go through the rest of its writing process. Each of them is going to
get 6 different hooks and scroll stoppers. Each of them is going to go
through the placement, the expansion, the close audit, and spice, and get
their own briefs. This is how we multiply our ads." And: "we only run
variation on proven assets."

The tree, each level a run of this same machine on the VARIATION route:

    ROOT   <src>-v        0p proven gate · 0–2 copied (already done) ·
                          3v control · 4a reading · 4m awareness map
    LEVEL  <src>-v<lv>    4b hooks at that awareness level        ×5 levels
    LEAF   <src>-v<lv><n> 4c 4d 4e 4f 4g · 5 brief · 5u mark used  ×6 hooks

Every run is an ordinary run folder: its stages, its prompts as sent, its
run.json. A LEVEL is its ROOT copied plus 4b; a LEAF is its LEVEL copied plus
the rest — so nothing already written is ever written twice, and every stage
reads the same prompt folders the New video chain reads (one change reaches
every chain). The branch's inputs travel as per-run values:
`target_awareness`, `branch_sections` and `hook_pick`.

    python3 variation.py plan  <source slug> --brand B            (free: shows the tree)
    python3 variation.py start <source slug> --brand B [--route creator|ai]
            [--levels control|all|<level,…>] [--hooks 0-5] [--jobs 3]
            [--through map|hooks|briefs]
    python3 variation.py status <source slug> --brand B
    python3 variation.py leaf  <leaf slug> --brand B               (one leaf; used by --jobs)
"""
import argparse, json, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C  # noqa: E402

LEVELS = ["unaware", "problem-aware", "solution-aware", "product-aware", "most-aware"]
CODE = {"unaware": "ua", "problem-aware": "pa", "solution-aware": "sa",
        "product-aware": "pd", "most-aware": "ma"}
SHARED = ("stage0", "stage1", "stage1c", "stage1b", "stage2")
JSON_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.S)


def say(m):
    print(m, flush=True)


def runs():
    return C.runs_root()


def base_for(src, level=None, hook=None):
    """The run's label. Kept short: run.py cuts a label at 40 characters, and
    the root, a level and a leaf must never cut to the same name."""
    b = f"{src}-v" + ("" if level is None else CODE[level]) + ("" if hook is None else str(hook))
    if len(b) > 40:
        raise SystemExit(f"run label {b} is over 40 characters — run.py would cut it")
    return b


def slug_for(src, level=None, hook=None):
    """The run's folder name: the label, plus the operator for anyone but Damon."""
    return C.run_slug(base_for(src, level, hook))


def load(d):
    return json.loads((Path(d) / "run.json").read_text())


def save(d, st):
    (Path(d) / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")


def base_extras(brand):
    """What run.py's own command line always hands a run (see run.py main)."""
    return {"video_count": "3", "brand_name": brand.replace("-", " ").title(), "product": "",
            "declared_avatar": "", "declared_sub": "", "declared_audience": "NONE",
            "declared_awareness": ""}


# ------------------------------------------------------------------ the root

def source_dir(src):
    d = runs() / src
    if not (d / "run.json").is_file():
        sys.exit(f"no teardown run named {src} in {runs()}")
    st = load(d)
    missing = [k for k in SHARED if (st["stages"].get(k) or {}).get("status") != "done"]
    if missing:
        sys.exit(f"{src} is not fully torn down — stages not done: {', '.join(missing)}")
    if not (d / "transcript.json").is_file():
        sys.exit(f"{src} has no transcript.json — the control is built from it")
    return d, st


def copy_run(src_dir, dst_slug, keep, patch):
    """A new run folder: src's files, only the `keep` stages' records, patched."""
    dst = runs() / dst_slug
    if dst.exists():
        return dst, load(dst)
    ignore = shutil.ignore_patterns("versions", "frames", "*-gdoc.html", "deliverable",
                                    "STRUCTURE-CHECK*.md", "SWIPE-MATCH*.md", "HOOK-FORMAT*.md",
                                    "swipe-match.json", "manifest.json")
    shutil.copytree(src_dir, dst, ignore=ignore)
    st = load(dst)
    st["stages"] = {k: v for k, v in st["stages"].items() if k in keep}
    st.pop("gdoc_url", None); st.pop("library", None); st.pop("swipe_match", None)
    st.pop("used_lane", None)
    st.update(slug=dst_slug, label=patch.pop("_label", dst_slug), **patch)
    # a stage file copied in but not kept would read as that stage's output
    kept_files = {(v.get("out") or "") for v in st["stages"].values()}
    for f in (dst / "stages").glob("*.md"):
        if f"stages/{f.name}" not in kept_files:
            f.unlink()
    save(dst, st)
    return dst, st


def open_root(src, brand, route, product=None):
    import proven
    ok, proof, why = proven.check(brand, src)
    say(("  0p proven gate: PASSED — " if ok else "  0p proven gate: REFUSED — ") + why)
    for p in proof:
        nums = ", ".join(f"{k} {p[k]:,}" for k in ("views", "saves", "likes", "spend", "purchases")
                         if isinstance(p.get(k), (int, float)))
        say(f"      {p['kind']}: {nums}")
    if not ok:
        sys.exit(1)
    sd, sst = source_dir(src)
    d, st = copy_run(sd, slug_for(src), SHARED, dict(
        _label=base_for(src), triage_lane="VARIATION", variation_of=src, variation_role="root",
        proven_proof=proof, production_route=route, route_chosen_by_hand=True))
    st["proven_proof"] = proof
    # The product is the proven ad's own and stays locked in every branch
    # (only awareness moves); a brand with several products has to be told
    # which one, exactly as run.py's --product asks.
    if product:
        st["product"] = product.lower()
    save(d, st)
    return d


def run_through(slug, brand, stop, extras, route):
    """One run of this machine, through `stop` (a display id). `slug` is the
    run folder; the label handed to run.py is the one it was opened with, so
    run.py resolves the very same folder."""
    import run as R
    st = load(runs() / slug)
    ex = {**base_extras(brand), **extras}
    ex["product"] = st.get("product") or ex.get("product") or ""
    label = st.get("label") or slug
    return R.run_video(None, label, brand, stop=stop, extras=ex, want_frames=False, route=route,
                       product=st.get("product") or None)


def read_map(root):
    st = load(root)
    rec = st["stages"].get("stage4m") or {}
    if rec.get("status") != "done":
        return None
    text = (root / rec["out"]).read_text()
    blocks = JSON_BLOCK.findall(text)
    if not blocks:
        raise SystemExit("4m printed no json block — the map cannot be read")
    m = json.loads(blocks[-1])
    fw = C.WS / "components" / "marketing-doctrine" / "frameworks.json"
    known = {r["id"] for r in json.loads(fw.read_text()).get("sections") or [] if isinstance(r, dict) and r.get("id")}
    got = [lv.get("level") for lv in m.get("levels") or []]
    if sorted(got) != sorted(LEVELS):
        raise SystemExit(f"4m's map must carry each of the five levels once — it carries {got}")
    for lv in m["levels"]:
        bad = [s for s in lv.get("sections") or [] if s not in known]
        if bad:
            raise SystemExit(f"4m named sections the doctrine does not carry at {lv['level']}: {bad}")
    if m.get("control_level") not in LEVELS:
        raise SystemExit(f"4m's control level is not one of the five: {m.get('control_level')}")
    (root / "tree.json").write_text(json.dumps(dict(source=st["variation_of"], map=m, leaves={}),
                                               indent=1, ensure_ascii=False) + "\n")
    return m


def branch_text(lv):
    out = [", ".join(lv.get("sections") or [])]
    if lv.get("added"):
        out.append("ADDED at this level: " + "; ".join(f"{a['id']} ({a.get('why', '')})" for a in lv["added"]))
    if lv.get("dropped"):
        out.append("DROPPED at this level: " + "; ".join(f"{x['id']} ({x.get('why', '')})" for x in lv["dropped"]))
    if lv.get("opening"):
        out.append("THE OPENING SPEAKS TO: " + lv["opening"])
    if lv.get("product_enters"):
        out.append("PRODUCT ENTERS: " + lv["product_enters"])
    return "\n".join(out)


def level_extras(m, level):
    lv = next(x for x in m["levels"] if x["level"] == level)
    tgt = level + (" (the CONTROL level — the proven ad's own)" if level == m["control_level"] else "")
    return {"target_awareness": tgt, "branch_sections": branch_text(lv)}


# ------------------------------------------------------------------ the tree

def pick_levels(m, which):
    if which in ("all", None):
        return LEVELS
    if which == "control":
        return [m["control_level"]]
    got = [x.strip() for x in which.split(",")]
    bad = [x for x in got if x not in LEVELS]
    if bad:
        sys.exit(f"not an awareness level: {bad} — one of {LEVELS}")
    return got


def hooks_of(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def open_level(root, src, level, m, route):
    ex = level_extras(m, level)
    keep = SHARED + ("stage3v", "stage4r", "stage4m")
    d, st = copy_run(root, slug_for(src, level), keep, dict(
        _label=base_for(src, level), variation_role="level", variation_level=level, variation_extras=ex,
        production_route=route))
    return d, ex


def open_leaf(level_dir, src, level, n, ex, route):
    keep = SHARED + ("stage3v", "stage4r", "stage4m", "stage4b")
    ex = {**ex, "hook_pick": f"V{n}"}
    d, st = copy_run(level_dir, slug_for(src, level, n), keep, dict(
        _label=base_for(src, level, n), variation_role="leaf", variation_level=level, variation_leaf=f"{CODE[level]}{n}",
        hook_pick=f"V{n}", variation_extras=ex, production_route=route))
    return d, ex


def run_leaf(slug, brand):
    d = runs() / slug
    st = load(d)
    return run_through(slug, brand, "5u", st.get("variation_extras") or {}, st.get("production_route"))


def leaf_subprocess(slug, brand):
    r = subprocess.run([sys.executable, str(HERE / "variation.py"), "leaf", slug, "--brand", brand],
                       capture_output=True, text=True)
    (runs() / slug / "variation-leaf.log").write_text(r.stdout + r.stderr)
    return slug, r.returncode == 0


def fan_in(root, src):
    tf = root / "tree.json"
    tree = json.loads(tf.read_text())
    leaves = {}
    for level in LEVELS:
        for n in range(6):
            d = runs() / slug_for(src, level, n)
            if not (d / "run.json").is_file():
                continue
            st = load(d)
            s = st["stages"]
            brief = s.get("stage5") or {}
            leaves[f"{CODE[level]}{n}"] = dict(
                level=level, hook=f"V{n}", run=d.name,
                brief=(str((d / brief["out"]).relative_to(C.WS)) if brief.get("status") in ("done", "held") and brief.get("out") else None),
                brief_status=brief.get("status"), swipe_match=st.get("swipe_match"),
                used=(st.get("used_lane") or {}).get("rows"),
                stages={k: v.get("status") for k, v in s.items()})
    tree["leaves"] = leaves
    tf.write_text(json.dumps(tree, indent=1, ensure_ascii=False) + "\n")
    return tree


# ------------------------------------------------------------------ commands

def cmd_plan(a):
    import proven
    ok, proof, why = proven.check(a.brand, a.source)
    say(f"\nVARIATION VIDEO · {a.source} ({a.brand})")
    say(("  0p proven gate: PASSED — " if ok else "  0p proven gate: REFUSED — ") + why)
    sd, sst = source_dir(a.source)
    doc = json.loads((sd / "doctrine.json").read_text()) if (sd / "doctrine.json").is_file() else {}
    say(f"  control level (the doctrine read's entry): {(doc.get('awareness') or {}).get('entry')}")
    say(f"  sections the control carries: {', '.join(x['id'] for x in doc.get('sections_carried') or [])}")
    plan = {s["key"]: s for s in C.stages(a.brand, "", a.route, "VARIATION")}
    def row(k):
        s = plan.get(k)
        return f"{s['id']:<3} {s['name']:<14} {Path(s['prompt']).name if s and s['prompt'] else '—'}" if s else k
    say("\n  ROOT   " + slug_for(a.source))
    for k in ("stage3v", "stage4r", "stage4m"):
        say("         " + row(k))
    levels = LEVELS if a.levels == "all" else (a.levels.split(",") if a.levels != "control" else ["<control>"])
    hooks = hooks_of(a.hooks)
    say(f"\n  LEVELS ×{len(levels)}   {', '.join(levels)}")
    say("         " + row("stage4b"))
    say(f"\n  LEAVES ×{len(levels) * len(hooks)}   hooks {', '.join('V%d' % n for n in hooks)} at each level")
    for k in ("stage4a", "stage4c", "stage4d", "stage4e", "stage4g", "stage5", "stage5u"):
        say("         " + row(k))
    n_l, n_h = len(levels), len(levels) * len(hooks)
    say(f"\n  writing calls: 1 map + {n_l} hooks + {n_h} × 6 = {1 + n_l + n_h * 6}  "
        f"(+ swipe match and manifest checks on every brief). No image or video spend.")
    return 0 if ok else 1


def cmd_start(a):
    src, brand, route = a.source, a.brand, a.route
    say(f"\n▶ VARIATION VIDEO · {src} ({brand}) · route {route}")
    root = open_root(src, brand, route, a.product)
    if not run_through(root.name, brand, "4m", {}, route):
        say("  the root stopped before the map — see the run above"); return 1
    m = read_map(root)
    say(f"  map: control level {m['control_level']}")
    for lv in m["levels"]:
        say(f"    {lv['level']:<15} {' · '.join(lv.get('sections') or [])}")
    if a.through == "map":
        return 0
    levels = pick_levels(m, a.levels)
    lvl_dirs = {}
    for level in levels:
        d, ex = open_level(root, src, level, m, route)
        say(f"\n  LEVEL {level} → {d.name}")
        if not run_through(d.name, brand, "4b", ex, route):
            say(f"  {level}: hooks held or failed — its leaves wait"); continue
        lvl_dirs[level] = (d, ex)
    if a.through == "hooks":
        fan_in(root, src); return 0
    leaves = []
    for level, (d, ex) in lvl_dirs.items():
        for n in hooks_of(a.hooks):
            ld, _ = open_leaf(d, src, level, n, ex, route)
            leaves.append(ld.name)
    say(f"\n  {len(leaves)} leaves, {a.jobs} at a time")
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        for slug, ok in pool.map(lambda s: leaf_subprocess(s, brand), leaves):
            say(f"    {slug}: {'brief done' if ok else 'stopped — see variation-leaf.log in its folder'}")
    tree = fan_in(root, src)
    done = sum(1 for x in tree["leaves"].values() if x.get("brief_status") == "done")
    say(f"\n  tree: {done}/{len(tree['leaves'])} briefs done · {root / 'tree.json'}")
    return 0


def cmd_status(a):
    root = runs() / slug_for(a.source)
    if not (root / "tree.json").is_file():
        say("no map yet"); return 1
    tree = fan_in(root, a.source)
    say(f"control level: {tree['map']['control_level']}")
    for k, v in sorted(tree["leaves"].items()):
        say(f"  {k:<5} {v['level']:<15} {v['hook']}  brief {v.get('brief_status') or '—':<7} "
            f"swipe match {v.get('swipe_match') if isinstance(v.get('swipe_match'), str) else ('held' if v.get('swipe_match') else '—')}  "
            f"used {v.get('used') if v.get('used') is not None else '—'}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "start", "status", "leaf"])
    ap.add_argument("source")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--route", default="creator", choices=["creator", "ai", "founder"])
    ap.add_argument("--product", default=None,
                    help="the product the proven ad sells (a brand with several must say which); "
                         "it stays locked in every branch")
    ap.add_argument("--levels", default="all")
    ap.add_argument("--hooks", default="0-5")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--through", default="briefs", choices=["map", "hooks", "briefs"])
    a = ap.parse_args()
    if a.cmd == "leaf":
        sys.exit(0 if run_leaf(a.source, a.brand) else 1)
    sys.exit({"plan": cmd_plan, "start": cmd_start, "status": cmd_status}[a.cmd](a))


if __name__ == "__main__":
    main()
