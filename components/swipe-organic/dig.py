#!/usr/bin/env python3
"""A dig — one typed ask becomes a standing feed.

    python3 dig.py "what he wants to see" [--per 25] [--job <id>]

  1. PLAN    the ask → the searches, hashtags and keep/drop rule
             (prompts/feed-plan-v1.md, sent as written, saved beside the feed)
  2. PULL    feed.py sweeps TikTok, Instagram and YouTube for them
  3. SIFT    sift.py throws out what doesn't belong
  4. FOLLOW  hops.py seats the creators behind the winners, on probation
  5. SAVE    thumbnails cached; the feed now rides the daily run forever

The feed lands at records/avatar-feeds/damon--<name>/ — same four files as
every other feed, so nothing downstream needs to know it was asked for
rather than built from an avatar's receipts.
"""
import argparse, json, re, subprocess, sys, time
import desklib as D


def run(job, say, *cmd):
    D.job_write(job, step=say)
    r = subprocess.run([sys.executable, *cmd], cwd=str(D.HERE), capture_output=True, text=True)
    tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
    D.job_write(job, step=f"   → {tail[0][:160]}")
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ask")
    ap.add_argument("--per", type=int, default=25)
    ap.add_argument("--job", default=time.strftime("dig-%Y%m%d-%H%M%S"))
    ap.add_argument("--feed", help="force the feed folder name (sub-avatar feeds: <brand>--<sub>)")
    ap.add_argument("--meta", default="{}", help="JSON merged into sources.json (brand, core, sub, card)")
    a = ap.parse_args()
    job = a.job
    before, cap = D.apify_spend()
    D.job_write(job, kind="dig", ask=a.ask, status="running", step="Planning the searches")
    try:
        text = D.prompt("feed-plan-v3.md", ask=a.ask)
        reply = D.ask_model(text, "sonnet")
        plan = D.json_from(reply)
        name = re.sub(r"[^a-z0-9-]", "", (plan.get("NAME") or "feed").lower().replace(" ", "-"))[:40] or "feed"
        feed = a.feed or f"damon--{name}"
        root = D.FEEDS / feed
        if root.exists():                       # same ask twice → grow that feed, never a twin
            S = json.loads((root / "sources.json").read_text())
        else:
            root.mkdir(parents=True)
            S = {"brand": "damon", "avatar": name, "sources": [],
                 "entry": {"max_age_days": 540, "hashtag_min_views": 50000, "hashtag_min_likes": 5000}}
        S.update(json.loads(a.meta))
        langs = [str(x).lower()[:2] for x in plan.get("LANGUAGES") or ["en"]]
        S["languages"] = sorted(set(langs + ["en", "none"]))
        S.update(title=json.loads(a.meta).get("title") or plan.get("TITLE") or name, ask=a.ask, made=S.get("made") or D.now()[:10],
                 whose=plan.get("WHOSE_SCROLL", ""), keep_rule=plan.get("KEEP_RULE", ""), drop_rule=plan.get("DROP_RULE", ""))
        have = {(s["kind"], s["platform"], s["value"]) for s in S["sources"]}
        rc = f"from the ask, planned {D.now()[:10]}"
        def seat(kind, plat, vals):
            for v in vals or []:
                v = str(v).strip().lstrip("#@")
                if v and (kind, plat, v) not in have:
                    S["sources"].append({"kind": kind, "platform": plat, "value": v, "receipt": rc})
                    have.add((kind, plat, v))
        seat("search", "tiktok", plan.get("TIKTOK_SEARCHES"))
        seat("hashtag", "tiktok", plan.get("TIKTOK_HASHTAGS"))
        seat("hashtag", "instagram", [h.replace(" ", "") for h in plan.get("INSTAGRAM_HASHTAGS") or []])
        seat("search", "youtube", plan.get("YOUTUBE_SEARCHES"))
        for acc in plan.get("ACCOUNTS") or []:
            if acc.get("platform") in ("tiktok", "instagram"):
                seat("account", acc["platform"], [acc.get("handle")])
        (root / "sources.json").write_text(json.dumps(S, indent=1) + "\n")
        (root / "prompts-as-sent").mkdir(exist_ok=True)
        (root / "prompts-as-sent" / "plan.md").write_text(text)
        (root / "plan.json").write_text(json.dumps(plan, indent=1) + "\n")
        D.job_write(job, feed=feed, title=S["title"], plan=plan,
                    step=f"Feed “{S['title']}” — {len(S['sources'])} searches and hashtags seated")

        ok = run(job, "Pulling TikTok, Instagram and YouTube", "feed.py", "--avatar", feed, "--per", str(a.per))
        if not ok:
            raise RuntimeError("the pull failed — see the step above")
        run(job, "Sifting out what doesn't belong", "sift.py", "--avatar", feed)
        run(job, "Following the winners to their creators", "hops.py", "--avatar", feed, "--max", "8")
        D.job_write(job, step="Saving thumbnails")
        D.cache_covers(feed)
        items = json.loads((root / "items.json").read_text())["items"]
        kept = sum(1 for it in items.values() if (it.get("sift") or {}).get("keep"))
        after, _ = D.apify_spend()
        spend = round(after - before, 2) if before is not None and after is not None else None
        D.job_write(job, status="done", pulled=len(items), kept=kept, spend=spend,
                    step=f"Done — {kept} keepers out of {len(items)} pulled"
                         + (f" · ${spend:.2f} of scraping" if spend is not None else ""))
    except Exception as e:
        D.job_write(job, status="failed", step=f"Stopped: {str(e)[:200]}")
        raise


if __name__ == "__main__":
    main()
