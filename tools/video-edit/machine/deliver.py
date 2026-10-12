#!/usr/bin/env python3
"""deliver — the finished versions of one edit, named and carded, ready for the owner's Approve.

    deliver.py <edit run> <renders folder> [--brief brief-NNNN] [--batch batch-YYYY-MM-DD-x]
               [--links <link id> …] [--dry-run] [--replace]

Stations 11–12 of the video ad line (tools/video-production/VIDEO-AD-LINE.md),
for the edit-map line. the owner, 3 Oct 2026: "after an edit is finished, we have to
generate the variations … cut up as the variations, and then that's what is delivered
to the final folder, and then that is ready to be uploaded into Meta … with all of his
naming conventions set up."

In:  the edit run (`runs/video-edit/<brand>/<label>/`, with `edit-map.json` and one
     `edit-map-<hook clip id>.json` per hook) and a folder of rendered mp4s named
     `<version>.mp4` — `control` or a hook version (the name in its edit-map-<version>.json). Every mp4 pairs with
     its edit map; a hook's edit map carries `hook`.
Out: `<edit run>/deliverable/<ad name>/` — LOCAL staging, the same shape as the
     approval road's `meta/<brand>/1-check/video/<ad name>/` (CARD.md):
        <ad name>_asset-01.mp4 …   control first, then the hooks in order
        card.json                  meta-card/1, written by meta-upload's own card writer
        naming.json                which asset is which version, hook and edit map
        manifest.json              reserves the batch letter (names.batches_used reads it)
     Nothing goes to Drive and nothing goes to Meta here. The Drive copy and the
     upload stay on the owner's Approve.

The name is the short form (components/naming, the only naming authority):
`<brand>_<product>_<brief>_<batch>` for the ad, `_asset-NN` per file. The six
versions of one edit are one batch and run as one flexible ad (CONVENTION.md:
"a batch's variations run under one name"; card format `flexible`, up to 10 videos).
Every value is read, never made up:
    brand    the edit map
    product  the brief's own `piece.product` (cross-checked against the register)
    brief    the production run's run.json `brief` (written by `briefs.py open`), else
             the register record whose run is the production run, else --brief
             (which must resolve in the register to a brief of the same product)
    batch    the next free letter today (names.next_batch), or --batch
    ratio    the brief's aspect ratio; a render in another frame is refused
A naming field that cannot be read STOPS the run and is named. Fields the card
needs and the naming does not — primary text, headline, landing page, angle — are
listed as missing and the card is still staged: its check fails on the approval page
where the owner sees why. Words are never written here: a `words.json` in the edit run,
else the brief's own `words`, else the brief's copywriter runs (card_words).

`--dry-run` prints every name and the whole card and writes nothing.
"""
import argparse, json, os, re, shutil, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "components" / "naming"))
sys.path.insert(0, str(REPO / "components" / "meta-upload"))
import names as N  # noqa: E402
import delivery_rule as DR  # noqa: E402
import to_check as T  # noqa: E402
import card_words as W  # noqa: E402

CONTROL = "control"
MAX_FLEX = 10                       # meta-upload cards.py: a flexible ad holds up to 10 videos

UPSTREAM = {
    "brand": "the edit map's `brand` (edit_map.py writes it)",
    "product": "the brief's json block, `piece.product` (writing station)",
    "brief": "a brief number: open the brief in the register — `tools/image-teardown/tools/briefs.py "
             "open <production run> --brand <brand> --type video-ai` writes it into the production run's "
             "run.json as `brief`; or pass --brief with a registered brief of this product",
    "ratio": "the brief's json block, `piece.aspect_ratio`",
    "angle": "the brief header in brands/<brand>/briefs/briefs.json (`angle`, read from the editing brief / "
             "edit map, signed in brands/<brand>/strategy/angles.json) — names the ad set",
    "avatar": "the brief's json block, `piece.avatar`, or its header in brands/<brand>/briefs/briefs.json",
    "primary text": "the writing station: a words.json in the edit run, `words` in the brief's json block, or a "
                    "copywriter run labelled with the brief number (runs/copywriter/<brand>/…/stage8--render.md)",
    "headline": "same as primary text — the copywriter's stage 8 HEADLINES list (never the on-screen headline)",
    "landing page": "the brief's `landing_page` in the register (components/naming/page_pick.py picks it when "
                    "the brief is opened), or --links",
}


class Stop(Exception):
    """A naming field is missing or wrong: nothing is written."""


def _read(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.is_file() else None


def workspace_of(path):
    """The workspace a run sits in — the run may live in another checkout than this code."""
    try:
        return N._workspace_root(Path(path).resolve() / "x")
    except RuntimeError:
        return REPO


def brief_block(brief_md):
    """The json block of a video brief (the one carrying `piece`), or {}."""
    p = Path(brief_md)
    if not p.is_file():
        return {}
    for m in re.finditer(r"```json\s*(\{.*?\})\s*```", p.read_text(), re.S):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and isinstance(d.get("piece"), dict):
            return d
    return {}


def ratio_word(aspect):
    """`9:16` / `9x16` -> `9x16`; anything else None."""
    m = re.match(r"^\s*(\d+)\s*[:x]\s*(\d+)\s*$", str(aspect or ""))
    return f"{m.group(1)}x{m.group(2)}" if m else None


# ---------------------------------------------------------------- the versions
def versions(edit_run, renders):
    """[(version, mp4, edit map path, edit map)] control first, hooks in order — and
    the edit maps that have no render (listed, not delivered)."""
    edit_run, renders = Path(edit_run), Path(renders)
    if not renders.is_dir():
        raise Stop(f"renders folder not found: {renders}")
    mp4s = sorted(p for p in renders.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"
                  and not p.name.startswith("."))
    if not mp4s:
        raise Stop(f"no .mp4 in {renders}")
    out = []
    for f in mp4s:
        v = f.stem
        em_path = edit_run / ("edit-map.json" if v == CONTROL else f"edit-map-{v}.json")
        if v != CONTROL and not em_path.exists():
            raise Stop(f"{f.name}: a render is named <version>.mp4 — `control`, or a hook version with its own "
                       f"edit-map-<version>.json (edit_map.py --hooks writes them)")
        em = _read(em_path)
        if em is None:
            raise Stop(f"{f.name}: its edit map {em_path.name} is not in {edit_run}")
        if v == CONTROL and em.get("hook"):
            raise Stop(f"edit-map.json carries a hook ({em['hook']!r}) — the control has none")
        if v != CONTROL and not em.get("hook"):
            raise Stop(f"{em_path.name} carries no `hook` — it is not a hook version")
        out.append((v, f, em_path, em))
    out.sort(key=lambda r: (r[0] != CONTROL, [int(x) for x in re.findall(r"\d+", r[0])]))
    done = {r[0] for r in out}
    not_rendered = sorted(p.stem[len("edit-map-"):] for p in edit_run.glob("edit-map-*.json")
                          if p.stem[len("edit-map-"):] not in done)
    if (edit_run / "edit-map.json").is_file() and CONTROL not in done:
        not_rendered.insert(0, CONTROL)
    brands = {N.slug(r[3].get("brand") or "") for r in out}
    if len(brands) != 1 or "" in brands:
        raise Stop(f"brand: the edit maps say {sorted(brands)} — need one brand ({UPSTREAM['brand']})")
    labels = {r[3].get("label") for r in out}
    if len(labels) != 1:
        raise Stop(f"the edit maps belong to different edits: {sorted(map(str, labels))}")
    return out, not_rendered


def hook_lines(plan):
    """plan.json hooks: {"Opening 2 · …": text}."""
    return {h.get("id"): h.get("text") for h in (plan or {}).get("hooks") or [] if h.get("id")}


# ---------------------------------------------------------------- the brief number
def find_brief_number(brand, product, prod_run, prod_rel, override=None):
    """(brief id, where it was read) or (None, where it looked). Never coined."""
    if override:
        try:
            hit = N.find_brief(brand, override, product)
        except N.AmbiguousBrief as e:
            raise Stop(f"brief: {e}")
        if not hit:
            raise Stop(f"brief: {override} is not a registered {brand} brief of {product} — "
                       f"{UPSTREAM['brief']}")
        if hit.get("product") and N.slug(hit["product"]) != N.slug(product):
            raise Stop(f"brief: {override} is a {hit['product']} brief; this edit is {product}")
        reg = hit.get("register") or {}
        return (reg.get("brief") or hit.get("brief") or N.brief_id(override)), "--brief"
    rj = _read(Path(prod_run) / "run.json") or {}
    b = rj.get("brief")
    if b and N.is_brief_id(b):
        return N.brief_id(b), f"{prod_rel}/run.json"
    for r in N.register_rows(brand):
        if r.get("_table") == "briefs" and str(r.get("run") or "").rstrip("/") == prod_rel:
            if r.get("product") and N.slug(r["product"]) != N.slug(product):
                raise Stop(f"brief: the register's {r['key']} is a {r['product']} brief; "
                           f"the brief document says {product}")
            return (r.get("brief") or N.brief_id(r["key"])), f"register {r['key']}"
    return None, f"{prod_rel}/run.json has no `brief`; no register record has run = {prod_rel}"


# ---------------------------------------------------------------- the plan
def plan(edit_run, renders, *, brief=None, batch=None, links=(), dry_run=False, replace=False):
    """Everything deliver would write, written nowhere. Raises Stop on a naming gap
    (the Stop carries what was read so far as `.known`)."""
    edit_run = Path(edit_run).resolve()
    ws = workspace_of(edit_run)
    known = {"edit_run": str(edit_run)}
    try:
        vs, not_rendered = versions(edit_run, renders)
        em0 = vs[0][3]
        brand = N.slug(em0["brand"])
        known.update(brand=brand, versions=[(v, f.name, p.name, em.get("hook")) for v, f, p, em in vs],
                     not_rendered=not_rendered)
        prod_rel = str(em0.get("from_run") or "").rstrip("/")
        prod_run = ws / prod_rel if prod_rel else None
        if not prod_run or not prod_run.is_dir():
            raise Stop(f"the edit map's from_run ({prod_rel or 'none'}) is not a production run in {ws}")
        prun = _read(prod_run / "run.json") or {}
        bdoc = brief_block(prod_run / "brief.md")
        piece = bdoc.get("piece") or {}
        product = N.slug(piece.get("product") or "")
        if not product:
            raise Stop(f"product: not in {prod_rel}/brief.md — {UPSTREAM['product']}")
        known["product"] = product
        ratio = ratio_word(piece.get("aspect_ratio"))
        if not ratio:
            raise Stop(f"ratio: not in {prod_rel}/brief.md — {UPSTREAM['ratio']}")
        known["ratio"] = ratio
        hooks = hook_lines(_read(prod_run / "plan.json"))
        # the control's opening: the hook the plan marks `control`, else the plan's first hook (the planner lists
        # the swipe's own opening first)
        control_hook = next((k for k in hooks if "control" in k.lower()), next(iter(hooks), None))
        known["hook_text"] = {v: hooks.get(em.get("hook") or control_hook) for v, _, _, em in vs}
        bid, where = find_brief_number(brand, product, prod_run, prod_rel, brief)
        known["brief_from"] = where
        stops = []
        if not bid:
            if not dry_run:
                raise Stop(f"brief: {where}. {UPSTREAM['brief']}")
            # a dry run goes on to show the whole card, the brief marked as the gap
            stops.append(("brief", where))
        known["brief"] = bid
        if len(vs) > MAX_FLEX:
            raise Stop(f"{len(vs)} versions — one flexible ad holds at most {MAX_FLEX}")
        for v, f, _, _ in vs:
            if not dry_run and f.stat().st_size == 0:
                raise Stop(f"{f.name} is empty — a placeholder, not a render")
            r = DR.ratio_of(f) if f.stat().st_size else None
            if r and r != ratio:
                raise Stop(f"ratio: {f.name} is {r}; the brief says {ratio}")
        out_root = edit_run / "deliverable"
        prior = sorted(p for p in out_root.glob("*/card.json")) if out_root.is_dir() else []
        if prior and not replace:
            raise Stop(f"already delivered: {prior[0].parent.name} — pass --replace to stage it again "
                       f"under the same name, or --batch for a new batch")
        if not batch and prior and replace:
            batch = (_read(prior[0].parent / "manifest.json") or {}).get("batch")
        batch = N.norm_batch(batch) if batch else N.next_batch(brand)
        unit = N.short_unit(brand, product, bid or "none", batch)
        known["ad_name"] = unit
    except Stop as e:
        e.known = known
        raise

    try:
        header = (N.brief_header(brand, bid, product) or {}) if bid else {}
    except N.AmbiguousBrief:
        header = {}
    avatar = N.slug(piece.get("avatar") or header.get("avatar") or "") or None
    erj = json.loads((edit_run / "run.json").read_text()) if (edit_run / "run.json").is_file() else {}
    # the angle the owner signs for this ad can sit in the edit run's own record (brands/ is read-only to machines)
    angle = N.slug(header.get("angle") or piece.get("angle") or erj.get("angle") or "") or None
    # the words: never written here
    words_src, words = None, W.empty()
    if (edit_run / "words.json").is_file():
        words, words_src = W.from_file(edit_run / "words.json"), str(edit_run / "words.json")
    elif isinstance(bdoc.get("words"), dict):
        d = bdoc["words"]
        words = {k: list(d.get(k) or []) for k in ("primary", "headlines", "descriptions")}
        words_src = f"{prod_rel}/brief.md (words)"
    else:
        words, words_src = W.for_brief(brand, bid, product=product)
    run_rel = str(edit_run.relative_to(ws)) if edit_run.is_relative_to(ws) else str(edit_run)
    try:
        p = T.plan(brand, "video", "flexible", [f for _, f, _, _ in vs], words, list(links),
                   {"tool": "video-edit", "run": run_rel, "creator": None},
                   ad_name=unit, product=product, brief=bid, avatar=avatar, angle=angle,
                   root=edit_run / "deliverable", dry_run=True)
    except T.Refused as e:
        raise Stop(str(e))
    card = p["card"]
    files_named = p["files"]
    if stops:                     # dry run only: show the gap in the name, never a stand-in value
        gap = f"{brand}_{product}_<brief?>_{batch}"
        unit = gap
        card["ad_name"] = gap
        card["media"] = [m.replace(f"{brand}_{product}_none_{batch}", gap) for m in card["media"]]
        files_named = [(s_, n.replace(f"{brand}_{product}_none_{batch}", gap)) for s_, n in files_named]
    missing = []
    if not card["words"]["primary"]:
        missing.append("primary text")
    if not card["words"]["headlines"]:
        missing.append("headline")
    if not card["pages"]:
        missing.append("landing page")
    if not card.get("angle"):
        missing.append("angle")
    if not card.get("avatar"):
        missing.append("avatar")
    files = [{"version": v, "was": f.name, "now": name, "edit_map": emp.name,
              "hook": em.get("hook") or control_hook, "hook_text": known["hook_text"].get(v)}
             for (v, f, emp, em), (_, name) in zip(vs, files_named)]
    return {"ad_name": unit, "batch": batch, "brand": brand, "product": product, "brief": bid,
            "brief_from": where, "ratio": ratio, "target": edit_run / "deliverable" / unit,
            "sources": [f for _, f, _, _ in vs], "files": files, "card": card, "words_from": words_src or
            "nothing found", "missing": missing, "not_rendered": not_rendered, "replace": replace,
            "prior": [x.parent for x in prior], "stops": stops}


def write(pl):
    """Stage the plan under <edit run>/deliverable/<ad name>/ — whole or not at all."""
    if pl.get("stops"):
        raise Stop(f"not written: {', '.join(k for k, _ in pl['stops'])} missing")
    target = Path(pl["target"])
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".{target.name}.partial-{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    for src, row in zip(pl["sources"], pl["files"]):
        shutil.copy2(src, tmp / row["now"])
    (tmp / "card.json").write_text(json.dumps(pl["card"], indent=1, ensure_ascii=False) + "\n")
    (tmp / "naming.json").write_text(json.dumps(
        {"unit": pl["ad_name"], "brief": pl["brief"], "brief_from": pl["brief_from"], "named": date.today().isoformat(),
         "by": "tools/video-edit/machine/deliver.py", "files": pl["files"]}, indent=1, ensure_ascii=False) + "\n")
    (tmp / "manifest.json").write_text(json.dumps(
        {"ad_name": pl["ad_name"], "batch": pl["batch"], "brand": pl["brand"], "product": pl["product"],
         "brief": pl["brief"], "ratio": pl["ratio"], "media": "video", "lane": "video",
         "_join": "Meta's ad name is `ad_name` + `_<funnel>-<page>` (names.short_meta / page_pick.meta_page).",
         "ads": [{"name": Path(r["now"]).stem, "ad_name": pl["ad_name"], "file": r["now"], "version": r["version"],
                  "hook": r["hook"]} for r in pl["files"]]}, indent=1, ensure_ascii=False) + "\n")
    for old in pl["prior"]:
        if Path(old).resolve() != target.resolve():
            shutil.rmtree(old)
    if target.exists():
        shutil.rmtree(target)
    tmp.rename(target)
    gone = N.audit(target / "manifest.json")
    if gone:
        raise Stop(f"manifest lists files that do not exist: {gone}")
    return target


def show(pl, dry_run):
    c = pl["card"]
    lines = [f"{'WOULD STAGE' if dry_run else 'STAGED'}  {pl['ad_name']}"]
    for k, why in pl.get("stops") or []:
        lines.append(f"  STOP {k}: {why} — comes from {UPSTREAM[k]}. Nothing can be staged until it is read.")
    lines += [
             f"  brief {pl['brief']} (from {pl['brief_from']}) · batch {pl['batch']} · ratio {pl['ratio']}",
             f"  → {pl['target']}"]
    for r in pl["files"]:
        lines.append(f"    {r['was']:<14} → {r['now']}   [{r['hook']}]")
    if pl["not_rendered"]:
        lines.append(f"  edit maps with no render (not delivered): {', '.join(pl['not_rendered'])}")
    lines.append(f"  words from: {pl['words_from']}")
    for m in pl["missing"]:
        lines.append(f"  MISSING {m} — comes from {UPSTREAM[m]}")
    lines.append("  card.json:")
    lines.append("    " + json.dumps(c, indent=1, ensure_ascii=False).replace("\n", "\n    "))
    return "\n".join(lines)


def show_stop(e):
    k = getattr(e, "known", {}) or {}
    lines = [f"STOPPED  {e}"]
    if k.get("versions"):
        shape = "_".join([k.get("brand", "<brand?>"), k.get("product", "<product?>"),
                          k.get("brief", "<brief?>"), "<batch>"])
        lines.append(f"  the names would be {shape}_asset-NN — nothing is named until every value is read")
        for i, (v, f, emp, hook) in enumerate(k["versions"], 1):
            lines.append(f"    {f:<14} → {shape}_asset-{i:02d}.mp4   [{hook or 'control'}]  ({emp})")
    if k.get("not_rendered"):
        lines.append(f"  edit maps with no render: {', '.join(k['not_rendered'])}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("edit_run", help="runs/video-edit/<brand>/<label>")
    ap.add_argument("renders", help="a folder of <version>.mp4 — control.mp4, <hook>.mp4 …")
    ap.add_argument("--brief", help="a registered brief number, when the production run carries none")
    ap.add_argument("--batch", help="batch-YYYY-MM-DD-x (default: the next free letter today)")
    ap.add_argument("--links", nargs="*", default=[], help="catalog link ids (default: the brief's landing page)")
    ap.add_argument("--replace", action="store_true", help="stage again over an earlier delivery of this edit")
    ap.add_argument("--dry-run", action="store_true", help="print every name and the card; write nothing")
    a = ap.parse_args()
    try:
        pl = plan(a.edit_run, a.renders, brief=a.brief, batch=a.batch, links=a.links,
                  dry_run=a.dry_run, replace=a.replace)
        if not a.dry_run:
            write(pl)
    except Stop as e:
        print(show_stop(e))
        sys.exit(2)
    print(show(pl, a.dry_run))
    if pl.get("stops"):
        sys.exit(2)


if __name__ == "__main__":
    main()
