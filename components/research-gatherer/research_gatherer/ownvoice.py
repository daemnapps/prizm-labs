"""Own voice — our own audience's words into the avatar's bank.

    python3 components/research-gatherer/gather.py ownvoice --brand B
    python3 components/research-gatherer/gather.py ownvoice --brand B --dry-run
    python3 components/research-gatherer/gather.py ownvoice --brand B --since 2026-07-01

The deep pull (engine.deep_for) files what OUTSIDE rooms say; `comments`
files the comments on any post; this files what OUR audience says: comments
under the brand's own ads and the customer emails in its support inbox.
Built 2026-09-28 on the owner's ruling ("build inside of there").

Sources, read from the brand's own `operations/brand.json`, never from here:
  - `ad_accounts[network=meta]` -> ad comments: the warehouse's
    `meta_ad_comments` first, then the account's top-spend ad posts scraped
    through `components/apify` (dark posts cannot be scraped; the warehouse
    only has comments for accounts whose pages it can read).
  - `accounts.helpdesk == "gorgias"` -> the warehouse's Gorgias tables,
    customer-written messages on real customer tickets only (the warehouse's
    own `ticket_class` view, the same filter cs-metrics counts on). A known
    order on the sender's email is the relationship the lane rule reads first.

Every row is read and filed by `annotate.py` — the intake read plus the
language layer's labeller (lane by language, awareness, sophistication) —
the same pipeline every gatherer mode files through. Never raises; brand-agnostic; the warehouse is
read-only; nothing is filed on a dry run; the verbatim is never reworded.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import engine
from . import annotate as A


def say(m):
    print(m, flush=True)


def _cfg():
    c = engine._config().get("ownvoice", {})
    c.setdefault("model", "claude-sonnet-5")
    c.setdefault("posts_per_run", 15)
    c.setdefault("comments_per_post", 400)
    c.setdefault("batch", 30)
    c.setdefault("first_run_since", "2026-07-01")
    return c


# ---------------------------------------------------------------- warehouse (read-only)

def _vault(name):
    if os.environ.get(name):
        return os.environ[name]
    try:
        sys.path.append(str(Path.home() / ".daemn"))
        import daemn_keys  # noqa: E402
        return daemn_keys.key(name)
    except Exception:
        return None


def sql(query):
    url = _vault("SUPABASE_DB_URL")
    psql = shutil.which("psql")
    if not url or not psql:
        say("  warehouse: MISSING (no SUPABASE_DB_URL or no psql) — skipped")
        return None
    env = dict(os.environ, PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=600000")
    wrapped = f"select coalesce(json_agg(t), '[]'::json) from ({query}) t"
    try:
        r = subprocess.run([psql, url, "-X", "-q", "-A", "-t", "-c", wrapped],
                           env=env, capture_output=True, text=True, timeout=900)
    except Exception as e:
        say(f"  warehouse: MISSING ({str(e)[:80]})")
        return None
    if r.returncode != 0:
        say(f"  warehouse: MISSING ({r.stderr.replace(url, '<db>')[:160].strip()})")
        return None
    try:
        return json.loads(r.stdout.strip() or "[]")
    except Exception:
        return None


def _q(s):
    return "'" + str(s).replace("'", "''") + "'"


# ---------------------------------------------------------------- brand

def brand_json(brand):
    try:
        return json.loads((engine.WORKSPACE / "brands" / brand / "operations" / "brand.json").read_text())
    except Exception:
        return {}


def meta_accounts(bj):
    return [a["account"] for a in bj.get("ad_accounts") or [] if a.get("network") == "meta" and a.get("account")]


def only_avatar(brand):
    d = engine.WORKSPACE / "brands" / brand / "core-avatars"
    avs = sorted(p.name for p in d.iterdir() if (p / "language").is_dir()) if d.is_dir() else []
    return avs[0] if len(avs) == 1 else None, avs


# ---------------------------------------------------------------- pulls

def pull_emails(since, today, brand):
    rows = sql(f"""
      with t as (select ticket_id, sender_has_ordered from gorgias_ticket_metrics
                 where ticket_class = 'customer' and not started_by_agent and created_at >= {_q(since)}::date - 60),
           m as (select id, ticket_id, created_datetime, subject, text from gorgias_ticket_messages
                 where from_agent = false and created_datetime > {_q(since)} and coalesce(text,'') <> '')
      select m.id, m.ticket_id, m.created_datetime::text as at, m.subject, m.text, t.sender_has_ordered
      from m join t using (ticket_id) order by m.created_datetime""")
    if rows is None:
        return None
    out = []
    for r in rows:
        if A.AUTO.search((r.get("subject") or "") + " " + (r.get("text") or "")[:300]):
            continue
        txt = A.clean(r.get("text"))
        if len(txt) < 2:
            continue
        out.append(dict(kind="email", text=txt, said=r["at"][:10], pulled=today,
                        ref=f"gorgias ticket {r['ticket_id']} msg {r['id']}", post=f"gorgias ticket {r['ticket_id']}",
                        source_name="support email (Gorgias)", source_type="ticket",
                        source_id=f"ticket_{brand}_gorgias", source_kind="ticket", property=brand,
                        relationship="ordered" if r.get("sender_has_ordered") else "no order on file for this email"))
    return out


def top_posts(accounts, since, n):
    ids = ",".join(_q(a) for a in accounts)
    return sql(f"""
      with s as (select ad_id, sum(spend) sp from meta_ad_insights where date >= {_q(since)}::date group by ad_id)
      select a.post_id, max(a.instagram_permalink_url) ig, max(a.ad_name) ad_name, sum(s.sp)::int spend,
             min(a.ad_id) ad_id
      from meta_ads a join s on s.ad_id = a.ad_id
      where a.account_id in ({ids}) and a.post_id is not null
      group by a.post_id order by spend desc limit {int(n)}""") or []


def fb_rows(items, names, today, ads=None, page_names=None):
    """ads: {pageid_postid: ad id}; page_names: {page id: account slug}."""
    ads, page_names = ads or {}, page_names or {}
    out = []
    for c in items or []:
        if c.get("error") or not c.get("text"):
            continue
        parts = (c.get("facebookUrl") or "").rstrip("/").split("/")
        post = f"{parts[-3]}_{parts[-1]}" if len(parts) >= 3 and parts[-2] == "posts" else (c.get("facebookUrl") or "")
        page, _, pid = post.partition("_")
        out.append(dict(kind="comment", text=A.clean(c["text"]), said=(c.get("date") or "")[:10], pulled=today,
                        ref=c.get("commentUrl") or f"facebook comment {c.get('commentId')}", post=post,
                        source_id=f"post_facebook_{A.slug(page_names.get(page, page))}_{pid}" if pid else None,
                        source_kind="post", property=A.slug(page_names.get(page, page)) or None,
                        ad=f"live_meta_{ads[post]}" if ads.get(post) else None,
                        source_name=f"Facebook ad comment — {names.get(post, 'ad')}", source_type="comment",
                        likes=c.get("likesCount"), replies=c.get("commentsCount"),
                        relationship="ad commenter, relationship unknown", _id=str(c.get("commentId"))))
    return out


def ig_rows(items, today, name="Instagram ad comment", account=None, ads=None):
    """account: the post's owner as a slug; ads: {post url: ad id}."""
    ads = ads or {}
    out = []
    for c in items or []:
        if c.get("error") or not c.get("text"):
            continue
        post = c.get("postUrl") or ""
        code = (re.search(r"/(?:p|reel|reels)/([^/?#]+)", post) or [None, ""])[1]
        acct = A.slug(account or (re.search(r"instagram\.com/([^/]+)/(?:p|reel)/", post) or [None, "unknown-account"])[1])
        out.append(dict(kind="comment", text=A.clean(c["text"]), said=(c.get("timestamp") or "")[:10], pulled=today,
                        ref=c.get("commentUrl") or f"{post}c/{c.get('id')}", post=post,
                        source_id=f"post_instagram_{acct}_{code}" if code else None, source_kind="post", property=acct,
                        ad=f"live_meta_{ads[post]}" if ads.get(post) else None,
                        source_name=name, source_type="comment",
                        likes=c.get("likesCount"), replies=c.get("repliesCount"),
                        relationship="commenter, relationship unknown", _id=str(c.get("id"))))
    return out


def pull_comments(accounts, since, cfg, today, scrape=True, brand=""):
    stats = {"warehouse": 0, "scraped": 0, "posts": 0}
    if not accounts:
        say("  ad comments: no meta ad account in brand.json — skipped")
        return [], stats
    ids = ",".join(_q(a) for a in accounts)
    wh = sql(f"""
      select c.comment_id, c.post_id, c.platform, c.created_time::text at, c.message, c.like_count, c.reply_count,
             c.permalink_url, a.ad_name, a.ad_id
      from meta_ad_comments c join meta_ads a on a.ad_id = c.ad_id
      where a.account_id in ({ids}) and c.created_time > {_q(since)} and coalesce(c.message,'') <> ''
      order by c.created_time""") or []
    out, seen = [], set()
    for c in wh:
        seen.add(str(c["comment_id"]))
        out.append(dict(kind="comment", text=A.clean(c["message"]), said=c["at"][:10], pulled=today,
                        ref=c.get("permalink_url") or f"meta comment {c['comment_id']}", post=c.get("post_id"),
                        source_id=f"post_{c.get('platform') or 'facebook'}_{A.slug(brand)}_{str(c.get('post_id') or '').split('_')[-1]}",
                        source_kind="post", property=A.slug(brand), ad=f"live_meta_{c['ad_id']}" if c.get("ad_id") else None,
                        source_name=f"ad comment — {c.get('ad_name') or 'ad'}", source_type="comment",
                        likes=c.get("like_count"), replies=c.get("reply_count"),
                        relationship="ad commenter, relationship unknown"))
    stats["warehouse"] = len(wh)
    if not scrape:
        return out, stats
    posts = top_posts(accounts, since, cfg["posts_per_run"])
    stats["posts"] = len(posts)
    if not posts:
        return out, stats
    try:
        ap = engine.apify_layer()
    except Exception as e:
        say(f"  scrape: MISSING (apify layer: {str(e)[:80]})")
        return out, stats
    acts = engine._config().get("actors", {}).get("comments", {})
    names = {p["post_id"]: p.get("ad_name") or "ad" for p in posts}
    fb = [{"url": f"https://www.facebook.com/{p['post_id'].split('_')[0]}/posts/{p['post_id'].split('_')[1]}"}
          for p in posts if "_" in p["post_id"]]
    try:
        items = ap.run(acts.get("facebook", "apify~facebook-comments-scraper"),
                       {"startUrls": fb, "resultsLimit": cfg["comments_per_post"], "includeNestedComments": True,
                        "viewOption": "RANKED_UNFILTERED", "onlyCommentsNewerThan": str(since)[:10]}) if fb else []
    except Exception as e:
        say(f"  facebook scrape: MISSING ({str(e)[:80]})")
        items = []
    ads = {p["post_id"]: p.get("ad_id") for p in posts}
    pages = {p["post_id"].split("_")[0]: brand for p in posts if "_" in p["post_id"]}
    for r in fb_rows(items, names, today, ads=ads, page_names=pages):
        if r.pop("_id") not in seen:
            out.append(r)
            stats["scraped"] += 1
    ig = [p["ig"] for p in posts if p.get("ig")]
    try:
        items = ap.run(acts.get("instagram", "apify~instagram-comment-scraper"),
                       {"directUrls": ig, "resultsLimit": cfg["comments_per_post"]}) if ig else []
    except Exception as e:
        say(f"  instagram scrape: MISSING ({str(e)[:80]})")
        items = []
    for r in ig_rows(items, today, account=brand, ads={p["ig"]: p.get("ad_id") for p in posts if p.get("ig")}):
        r.pop("_id", None)
        out.append(r)
        stats["scraped"] += 1
    return out, stats


# ---------------------------------------------------------------- page

AD_USE_TITLE = {
    "hook": "Hooks — words that could open an ad", "objection": "Objections — doubts an ad or page has to answer",
    "proof": "Proof — results and experiences to show", "offer": "Offer words — price, quantity, shipping, subscription",
    "question": "Questions people ask before they buy", "none": "Kept for the record",
}


def render_page(label, run_label, since, filed, dropped, rep, prompt_text, notes):
    e = html.escape
    tiles = "".join(f"<div><b>{v}</b>{e(k)}</div>" for k, v in rep["awareness"].items() if v or k != "none")
    lanes = "".join(f"<div><b>{v}</b>{e(k)}</div>" for k, v in sorted(rep["lanes"].items()))
    parts = [f"""<title>{e(label)} Voice Bank Intake</title>
<style>
:root{{--g:#f8f3ea;--p:#fffdf8;--i:#2b221b;--m:#76685a;--l:#e6dccb;--a:#b87512;--as:#f5e6c8}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{color-scheme:dark;--g:#1c1814;--p:#25201b;--i:#f1e9dc;--m:#b3a593;--l:#3a322a;--a:#e0a445;--as:#3b2d17}}}}
:root[data-theme="dark"]{{color-scheme:dark;--g:#1c1814;--p:#25201b;--i:#f1e9dc;--m:#b3a593;--l:#3a322a;--a:#e0a445;--as:#3b2d17}}
body{{background:var(--g);color:var(--i);font:16px/1.55 -apple-system,"Segoe UI",Roboto,sans-serif;padding-inline:16px;padding-block:28px 60px}}
.w{{max-width:880px;margin:0 auto;display:flex;flex-direction:column;gap:30px}}
h1,h2{{font-family:Georgia,serif;margin:0;line-height:1.15;text-wrap:balance}} h1{{font-size:clamp(28px,5vw,40px)}} h2{{font-size:22px}}
.e{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--a);font-weight:700}}
.m{{color:var(--m)}} section{{display:flex;flex-direction:column;gap:10px}}
.n{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}}
.n div{{background:var(--p);border:1px solid var(--l);border-radius:6px;padding:10px 12px;font-size:14px}} .n b{{display:block;font-size:24px;font-family:Georgia,serif}}
.thin{{background:var(--as);border-radius:6px;padding:12px 14px}}
.q{{background:var(--p);border:1px solid var(--l);border-radius:6px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}}
.q p{{margin:0;font-family:Georgia,serif;font-size:18px}} .r{{font:12px/1.45 ui-monospace,Menlo,monospace;color:var(--m);overflow-wrap:anywhere}}
.chip{{display:inline-block;font:600 11px/1.6 -apple-system,sans-serif;letter-spacing:.04em;text-transform:uppercase;background:var(--as);color:var(--i);border-radius:99px;padding:0 8px;margin-right:4px}}
details{{background:var(--p);border:1px solid var(--l);border-radius:6px;padding:12px 14px}} summary{{cursor:pointer;font-weight:600}}
pre{{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,monospace;overflow-x:auto}}
</style><div class="w">
<header style="display:flex;flex-direction:column;gap:10px"><div class="e">{e(label)} · voice bank intake · {e(run_label)}</div>
<h1>New words from our own audience</h1>
<p class="m">Ad comments and support emails since {e(since)}. Every row below is now in the brand's language bank, with its lane, awareness level and sophistication signal, so the copy and video tools can use it.</p></header>
<section><h2>Filed {rep['filed']} · dropped {rep['dropped']} · held {rep['held']}</h2><div class="n">{lanes}</div></section>
<section><h2>By awareness level</h2><div class="n">{tiles}</div>
<p class="thin"><b>Thin levels</b> (fewer than 3 rows): {e(', '.join(rep['thin_levels']) or 'none')}. These are the levels we can't yet write ads for in their own words.</p></section>"""]
    if notes:
        parts.append("<section><h2>What could not be read</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in notes) + "</ul></section>")
    for k in A.AD_USES:
        rows = [r for r in filed if r.get("ad_use") == k]
        if not rows:
            continue
        parts.append(f"<section><h2>{e(AD_USE_TITLE[k])} · {len(rows)}</h2>")
        for r in rows:
            s = r["source"]
            aw = (r.get("awareness") or {}).get("level") or "—"
            so = (r.get("sophistication") or {}).get("signal") or "—"
            parts.append(f'<div class="q"><p>“{e(r["text"])}”</p><div><span class="chip">{e(r["funnel"])}'
                         f'{" · assumed" if r.get("attribution") else ""}</span><span class="chip">{e(aw)}</span>'
                         f'<span class="chip">soph: {e(so)}</span></div>'
                         f'<span class="r">{e(s["name"])} · said {e(s.get("said", "?"))} · {e(r["id"])} · {e(", ".join(r["topics"]))}'
                         f'<br>{e(s["ref"])}</span></div>')
        parts.append("</section>")
    dl = "".join(f'<div class="q"><span class="r">{e(d.get("why", ""))} · {e(d.get("ref", ""))}</span>'
                 f'<p style="font-size:15px">{e(d.get("text", "")[:300])}</p></div>' for d in dropped[:250])
    parts.append(f"<details><summary>Dropped rows ({len(dropped)})</summary>{dl}</details>")
    parts.append(f"<details><summary>The prompt that read every row, word for word</summary><pre>{e(prompt_text)}</pre></details></div>")
    return "\n".join(parts)


# ---------------------------------------------------------------- run

def run_rows(brand, avatar, label, rows, source, cfg, run_label, dry_run=False):
    """Shared by ownvoice and comments: de-dupe, read, file, report."""
    ldir = A.lang_dir(brand, avatar)
    have = A.bank_refs(ldir)
    seen, fresh = set(), []
    for r in rows:   # the same words sent twice in one thread are one row
        key = (r.get("post"), r["text"].strip().lower())
        if r["ref"] in have or len(r["text"]) < 2 or key in seen:
            continue
        seen.add(key)
        fresh.append(r)
    say(f"  {len(rows)} pulled · {len(rows) - len(fresh)} already in the bank · {len(fresh)} new")
    if dry_run or not fresh:
        return None
    lane_entries, dropped, held = A.read_and_sort(fresh, brand, avatar, label, source, cfg, run_label)
    by_lane = {}
    for lane, entry in lane_entries:
        by_lane.setdefault(lane, []).append(entry)
    filed = A.file_lanes(ldir, by_lane)
    return filed, dropped, held


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gather.py ownvoice")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--since", help="YYYY-MM-DD; default = the last run, else the config's first_run_since")
    ap.add_argument("--no-scrape", action="store_true", help="warehouse only, spend nothing on Apify")
    ap.add_argument("--dry-run", action="store_true", help="pull and count; spend nothing on Apify, read and file nothing")
    a = ap.parse_args(argv)
    cfg = _cfg()
    bj = brand_json(a.brand)
    label = bj.get("label") or a.brand
    avatar = a.avatar or only_avatar(a.brand)[0]
    if not avatar:
        say(f"name the avatar with --avatar (found: {', '.join(only_avatar(a.brand)[1]) or 'none'})")
        return 2
    runs = engine._deep_runs_root() / a.brand
    state_f = runs / "ownvoice-state.json"
    try:
        state = json.loads(state_f.read_text())
    except Exception:
        state = {}
    since = a.since or state.get("last_run") or cfg["first_run_since"]
    now = dt.datetime.now(dt.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    run_label = now.strftime("%Y-%m-%d-%H%M")
    say(f"ownvoice · {a.brand} · {avatar} · since {since}{' · DRY RUN' if a.dry_run else ''}")

    notes, em = [], []
    if (bj.get("accounts") or {}).get("helpdesk") == "gorgias":
        em = pull_emails(since, today, a.brand)
        if em is None:
            notes.append("support emails: the warehouse could not be reached")
            em = []
    else:
        notes.append("support emails: brand.json names no gorgias helpdesk")
    cm, cst = pull_comments(meta_accounts(bj), since, cfg, today, scrape=not (a.no_scrape or a.dry_run), brand=a.brand)
    rows = em + cm
    if not cst["warehouse"]:
        notes.append("ad comments: none in the warehouse for this ad account — its pages are not connected for comments")
    if cst["posts"] and not cst["scraped"]:
        notes.append(f"ad comments: {cst['posts']} top ads scraped, none returned comments (dark posts cannot be read)")
    say(f"  {len(em)} emails · {len(cm)} comments ({cst['warehouse']} warehouse, {cst['scraped']} scraped from {cst['posts']} ads)")
    res = run_rows(a.brand, avatar, label, rows, "support emails and ad comments", cfg, run_label, a.dry_run)
    if res is None:
        say("  dry run — nothing read, nothing filed" if a.dry_run else "  nothing new")
        return 0
    filed, dropped, held = res
    rep = A.report(filed, dropped, held)
    out = runs / f"ownvoice-{run_label}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "filed.json").write_text(json.dumps(filed, indent=1, ensure_ascii=False))
    (out / "dropped.json").write_text(json.dumps(dropped, indent=1, ensure_ascii=False))
    (out / "held.json").write_text(json.dumps(held, indent=1, ensure_ascii=False))
    (out / "report.md").write_text(A.report_md(rep, f"{label} own voice · {run_label} · since {since}"))
    (out / "run.json").write_text(json.dumps({"brand": a.brand, "avatar": avatar, "since": since, "run": run_label,
                                              "emails": len(em), "comments": len(cm), **cst, "report": rep,
                                              "notes": notes}, indent=1))
    (out / "page.html").write_text(render_page(label, run_label, since, filed, dropped, rep,
                                               A.PROMPT.read_text(), notes))
    if not held:
        state_f.write_text(json.dumps({"last_run": now.strftime("%Y-%m-%dT%H:%M:%SZ")}, indent=1))
    say(f"  filed {len(filed)} · dropped {len(dropped)} · held {len(held)} · thin levels: {', '.join(rep['thin_levels']) or 'none'}")
    say(f"  page: {out / 'page.html'}")
    return 0
