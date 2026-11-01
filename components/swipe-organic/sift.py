#!/usr/bin/env python3
"""Sift a feed — throw out what the searches dragged in that doesn't belong.

Only feeds made from an ask carry a keep/drop rule (sources.json: ask,
keep_rule, drop_rule); avatar feeds built from receipts are left alone. Every
unsifted post gets one read: keep or drop, what it is, which format from the
bank (only when the caption makes it plain), and why. Dropped posts stay in
the catalog — nothing is deleted, the page just hides them.

    python3 sift.py --avatar damon--<name> [--batch 40] [--model haiku]
"""
import argparse, json
import desklib as D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--redo", action="store_true", help="re-read posts sifted under an older prompt")
    a = ap.parse_args()
    root = D.FEEDS / a.avatar
    S = json.loads((root / "sources.json").read_text())
    if not S.get("ask"):
        print(f"{a.avatar}: no ask on this feed — nothing to sift against")
        return
    cat = json.loads((root / "items.json").read_text())
    todo = [k for k, it in cat["items"].items()
            if not it.get("sift") or (a.redo and it["sift"].get("prompt") != "feed-sift-v3")]
    if not todo:
        print(f"{a.avatar}: nothing new to sift")
        return
    bank = json.loads((D.HERE / "formats.json").read_text())["formats"]
    formats = "\n".join(f'- {f["id"]} — {f["name"]}' for f in bank)
    ids = {f["id"] for f in bank}
    kept = dropped = failed = 0
    (root / "prompts-as-sent").mkdir(exist_ok=True)
    lang_ok = set(S.get("languages") or ["en", "none"])
    # Which lanes this feed keeps. The default is the avatar-feed rule — we want
    # what the person watches, not what is sold to them. A feed whose whole
    # subject IS the selling (a shop's own posts, a clipper's remakes) says so
    # in its sources.json, because dropping those would empty the feed it was
    # built to fill. the owner, 2 Oct: "Everything follows into a lane."
    keep_lanes = set(S.get("keep_lanes") or ["entertainment", "educational"])

    def one(chunk):
        posts = "\n".join(
            f'{n}. [{cat["items"][k]["platform"]}] @{cat["items"][k].get("author") or "?"} — '
            f'{(cat["items"][k].get("caption") or "(no caption)")[:260].replace(chr(10), " ")} '
            f'| tags: {", ".join((cat["items"][k].get("hashtags") or [])[:8])}'
            for n, k in enumerate(chunk, 1))
        text = D.prompt("feed-sift-v3.md", ask=(S["ask"] + ("\n" + S["whose"] if S.get("whose") else "")),
                        keep_rule=S.get("keep_rule", ""), drop_rule=S.get("drop_rule", ""),
                        formats=formats, posts=posts)
        (root / "prompts-as-sent" / "sift-latest.md").write_text(text)
        try:
            return chunk, D.json_from(D.ask_model(text, a.model))
        except Exception as e:
            print(f"  a batch failed: {str(e)[:100]} — left unsifted, retried next run")
            return chunk, None

    from concurrent.futures import ThreadPoolExecutor
    chunks = [todo[i:i + a.batch] for i in range(0, len(todo), a.batch)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, chunks))
    for chunk, rows in results:
        if rows is None:
            failed += len(chunk)
            continue
        for r in rows:
            n = r.get("N")
            if not isinstance(n, int) or not 1 <= n <= len(chunk):
                continue
            fmt, lang = r.get("FORMAT"), str(r.get("LANGUAGE") or "none").lower()[:4]
            lane = str(r.get("LANE") or "junk").lower().strip()
            in_lane = lane in keep_lanes
            keep = in_lane and lang in lang_ok     # the slots decide; the model never votes keep/drop
            cat["items"][chunk[n - 1]]["sift"] = {
                "keep": keep, "lane": lane, "kind": r.get("KIND"), "lang": lang, "what": r.get("WHAT"),
                "format": fmt if fmt in ids else "unread",   # never a coined name
                "why": r.get("WHY") if keep or not in_lane else f"language not in this feed ({lang})",
                "at": D.now(), "prompt": "feed-sift-v3"}
            kept += keep
            dropped += not keep
    (root / "items.json").write_text(json.dumps(cat, indent=1) + "\n")
    print(f"{a.avatar}: kept {kept} · dropped {dropped}" + (f" · {failed} unsifted" if failed else ""))


if __name__ == "__main__":
    main()
