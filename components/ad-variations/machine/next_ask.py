#!/usr/bin/env python3
"""next_ask: read a variation plan and file the next ask, so a plan becomes the next brief instead of stopping.

    next_ask.py <plan folder | variation-plan.json> [--dry-run] [--today YYYY-MM-DD] [--repo REPO]

Reads variation-plan.json (the ad-variations contract, definitions/variations.schema.json) and the plan's source run
record (runs/video-teardown/<brand>/<run>/run.json: product, avatar, funnel stage, brief). Read-only on both.

The next variation is the first in the plan's own order (V00 the control, then V01 ... highest estimated impact
first) that has no ask on file yet and that the plan itself does not hold. The plan holds a variation when its
recipe says what blocks it (`recipe.blocked_by`) or it needs a ruling (`needs_ruling`); a held variation is never
skipped silently: it is listed with the plan's own reason.

Writes, inside the plan's own run folder only:
  asks/<ask>/ask.json    the next ask, in the shape the writing tools read with --ask (creative-strategist
                         CONTRACT.md), plus `variation`: the one lever it moves, what stays locked, the hypothesis
                         and what confirms or kills it. `said` states that this reader wrote it from the plan; a
                         person's own ask for the same variation replaces it.
  next-ask.json          what is next, what is asked already, what is held and why, what is left
Nothing is generated, nothing is spent, and no variation is made here.
"""
import argparse, datetime as dt, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.append(str(COMP.parent / "run-kit"))     # appended, never ahead of this component
sys.path.append(str(COMP.parent / "brandpath"))
from run_kit import paths  # noqa: E402

SCHEMA = "ad-variations/1"
POINTER = "next-ask.json"
KEEP = ("id", "title", "changes", "locked", "hypothesis", "confirms_if", "kills_if", "audience", "cost")


class BadInput(Exception):
    pass


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def load_plan(where):
    """(plan folder, plan) for a folder or the plan file itself."""
    p = Path(where)
    f = p / "variation-plan.json" if p.is_dir() else p
    plan = _json(f)
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA or not isinstance(plan.get("variations"), list):
        raise BadInput(f"not a variation plan ({SCHEMA}): {f}")
    if not plan.get("brand"):
        raise BadInput(f"the plan names no brand: {f}")
    return f.parent, plan


def rel(repo, p):
    try:
        return str(Path(p).resolve().relative_to(Path(repo).resolve()))
    except ValueError:
        return str(p)


def ask_label(folder, vid):
    return "%s-%s" % (folder.name, str(vid).lower())


def held_why(v):
    """Why the plan itself holds this variation, or None."""
    blocked = (v.get("recipe") or {}).get("blocked_by")
    if blocked and str(blocked).strip().lower() not in ("none", "null", ""):
        return "blocked: %s" % " ".join(str(blocked).split())
    if v.get("needs_ruling"):
        return "needs a ruling: %s" % " ".join(str(v["needs_ruling"]).split())
    return None


def sort(folder, plan):
    """{"asked": [ids], "held": [{"id", "title", "why"}], "left": [ids]} in the plan's own order."""
    asked, held, left = [], [], []
    for v in plan["variations"]:
        vid = v.get("id")
        if not vid:
            continue
        if (folder / "asks" / ask_label(folder, vid) / "ask.json").is_file():
            asked.append(vid)
        elif held_why(v):
            held.append({"id": vid, "title": v.get("title"), "why": held_why(v)})
        else:
            left.append(vid)
    return {"asked": asked, "held": held, "left": left}


def offer_bank(repo, brand, product):
    """The brand's offer bank as the ask names it (repo-relative, `#section` when a product is known), or None."""
    try:
        import brandpath
        f = brandpath.brand_path(brand, "products", "offer-bank.md", root=Path(repo) / "brands")
    except Exception:                            # noqa: BLE001
        f = Path(repo) / "brands" / brand / "products" / "offer-bank.md"
    if not Path(f).is_file():
        return None
    return rel(repo, f) + ("#%s" % product if product else "")


def build(repo, folder, plan, v, today):
    """The ask for one variation, and what could not be found for it. Nothing is invented: a missing fact is empty
    in the ask and named in `missing`."""
    src = plan.get("source") or {}
    run = _json(Path(repo) / str(src.get("teardown_run") or "") / "run.json") or {}
    aud = run.get("audience") if isinstance(run.get("audience"), dict) else {}
    brand, product = plan["brand"], run.get("product")
    bank = offer_bank(repo, brand, product)
    label = ask_label(folder, v["id"])
    plan_rel = rel(repo, folder / "variation-plan.json")
    ask = {
        "brand": brand, "product": product, "avatar": aud.get("_avatar"),
        "asked": today, "ask": label,
        "said": "Written by the variation planner's reader from variation %s of %s; a person's own ask for this "
                "variation replaces it." % (v["id"], plan_rel),
        "funnel": aud.get("_funnel") or "",
        "offer": {"bank": bank, "lines": [], "never": []},
        "count": {"video_edits": 1},
        "variation": {**{k: v.get(k) for k in KEEP if v.get(k) is not None},
                      "plan": plan_rel,
                      "source": {"teardown_run": src.get("teardown_run"), "brief": run.get("brief"),
                                 "brief_key": run.get("brief_key"), "video": src.get("video")}},
    }
    if aud.get("_sub_avatar"):
        ask["sub_avatar"] = aud["_sub_avatar"]
    missing = [k for k, ok in (("product", product), ("avatar", aud.get("_avatar")), ("funnel", aud.get("_funnel")),
                               ("offer bank", bank)) if not ok]
    return ask, missing


def run(where, repo=None, today=None, dry_run=False, winner=None):
    """File the next ask for a plan. -> the pointer record (also written as next-ask.json unless dry_run)."""
    folder, plan = load_plan(where)
    repo = Path(repo) if repo else paths.repo(folder)
    today = today or dt.date.today().isoformat()
    s = sort(folder, plan)
    nxt = None
    if s["left"]:
        v = next(x for x in plan["variations"] if x.get("id") == s["left"][0])
        ask, missing = build(repo, folder, plan, v, today)
        out = folder / "asks" / ask["ask"] / "ask.json"
        nxt = {"id": v["id"], "title": v.get("title"), "ask": rel(repo, out), "missing": missing}
        if not dry_run:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(ask, indent=1, ensure_ascii=False) + "\n")
            s = sort(folder, plan)
    old = _json(folder / POINTER) or {}
    src = plan.get("source") or {}
    doc = {"plan": rel(repo, folder / "variation-plan.json"), "brand": plan["brand"],
           "winner": winner or src.get("winner") or old.get("winner"), "teardown_run": src.get("teardown_run"),
           "next": nxt, **s,
           "total": len([v for v in plan["variations"] if v.get("id")])}
    if not dry_run:
        (folder / POINTER).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", help="the plan's run folder, or its variation-plan.json")
    ap.add_argument("--today", help="YYYY-MM-DD; default is today")
    ap.add_argument("--repo", help="the workspace; default is found upward")
    ap.add_argument("--winner", help="the bank row id this plan iterates on (runs/winners/<brand>/bank.json); kept")
    ap.add_argument("--dry-run", action="store_true", help="say what the next ask would be; write nothing")
    a = ap.parse_args(argv)
    try:
        doc = run(a.plan, a.repo, a.today, a.dry_run, a.winner)
    except BadInput as e:
        print(f"bad input: {e}", file=sys.stderr)
        return 2
    n = doc["next"]
    if n:
        print("%s %s · %s -> %s" % ("would file" if a.dry_run else "filed", n["id"], n["title"], n["ask"])
              + (" (not found: %s)" % ", ".join(n["missing"]) if n["missing"] else ""))
    else:
        print("nothing to file: every variation is asked already or held by the plan")
    for h in doc["held"]:
        print("  held %s: %s" % (h["id"], h["why"][:160]))
    print("%d asked · %d held · %d left of %d" % (len(doc["asked"]), len(doc["held"]), len(doc["left"]), doc["total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
