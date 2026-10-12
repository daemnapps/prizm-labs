#!/usr/bin/env python3
"""Live swipe browser.

Serves the copy library straight out of swipe.db and streams the creatives from
the Drive mirror, so the page always shows current data — rebuild the db
and refresh, nothing to regenerate.

    python3 serve.py [port]        default 8765

Stdlib only. Nothing is copied: media is streamed from the Drive mount in
place, with Range support so video scrubbing works.
"""
import http.server, json, mimetypes, os, re, socketserver, sqlite3, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "naming"))
import names as N          # the vocabulary — imported, never re-declared
from pathlib import Path
for _r in Path(HERE).parents:          # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
DB = os.path.join(HERE, "swipe.db")
DRIVE = str(swipe_home.root("paid"))


def signed_angle_brands(root=None):
    """{brand: its signed angles} for every brand folder under brands/ that has
    signed any (rule 7: brands are discovered, never named here). `_` folders
    are templates, not brands."""
    root = Path(root) if root else N.WS / "brands"
    out = {}
    for d in sorted(root.iterdir()) if root.is_dir() else ():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        signed = N.signed_angles(d.name)
        if signed is not None:
            out[d.name] = sorted(signed or {})
    return out


def q(sql, args=()):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p, qs = u.path, urllib.parse.parse_qs(u.query)

        if p == "/":
            body = open(os.path.join(HERE, "app.html"), "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # The four endpoints below answer for ANY lane in one shape, so the
        # three built views — synopsis, angles, pages — render every lane
        # without a second copy of themselves. What changes per lane is only
        # the belief signal: a competitor's is how many variants they cloned,
        # ours is what we paid, organic's is how much of the room it is.
        BELIEF = {"paid": ("variants", "vars"), "own": ("spend", "spend"),
                  "organic": ("posts", "posts")}

        if p == "/api/brands":
            lane = qs.get("lane", ["paid"])[0]
            if lane == "paid":
                return self._json(q("SELECT * FROM brands ORDER BY creatives DESC"))
            rows = q(
                "SELECT c.source AS brand, s.label AS domain, COUNT(*) creatives, "
                "  COUNT(DISTINCT c.group_slug) blocks, "
                "  SUM(c.media='video') video, "
                "  ROUND(SUM(COALESCE(c.spend,0))) spend, "
                "  ROUND(COUNT(*)*1.0/COUNT(DISTINCT c.group_slug),2) per_block, "
                # `url` on our own ads is the Meta preview link, not a
                # destination — counting it gave one "page" per ad. Pages are
                # the funnel pages we captured, or the creator accounts.
                "  0 pages "
                "FROM creatives c JOIN sources s "
                "  ON s.lane=c.lane AND s.source=c.source "
                "WHERE c.lane=? GROUP BY c.source ORDER BY creatives DESC", (lane,))
            for r in rows:
                r["pages"] = (len(self._own_pages(r["brand"])) if lane == "own"
                              else r["blocks"])
            return self._json(rows)

        if p == "/api/blocks":
            b = qs.get("brand", [""])[0]
            lane = qs.get("lane", ["paid"])[0]
            if lane == "paid":
                rows = q("SELECT a.*, p.page_type, p.height AS page_height, "
                         "       a.variants AS belief, 'vars' AS belief_label "
                         "FROM blocks a LEFT JOIN pages p "
                         "  ON p.brand = a.brand AND p.slug = a.page_slug "
                         "WHERE a.brand = ? ORDER BY a.variants DESC", (b,))
                return self._json(rows)
            col, label = BELIEF[lane]
            order = "spend" if lane == "own" else "creatives"
            return self._json(q(
                f"SELECT group_slug AS slug, group_label AS headline, "
                f"  MAX(body) AS primary_text, COUNT(*) creatives, "
                f"  SUM(media='video') video_count, SUM(media!='video') image_count, "
                f"  MAX(COALESCE(variants,1)) max_variants, "
                f"  ROUND(SUM(COALESCE(spend,0))) spend, "
                f"  ROUND(SUM(COALESCE(revenue,0))) revenue, "
                f"  COUNT(*) posts, SUM(COALESCE(variants,1)) variants, "
                f"  ROUND({'SUM(COALESCE(spend,0))' if lane=='own' else 'COUNT(*)'}) belief, "
                f"  ? AS belief_label, "
                f"  (SELECT stage FROM creatives x WHERE x.lane=c.lane AND x.source=c.source "
                f"     AND x.group_slug=c.group_slug GROUP BY stage "
                f"     ORDER BY COUNT(*) DESC LIMIT 1) stage, "
                f"  MAX(seasonal) seasonal, MIN(url) landing_page, "
                f"  NULL page_type, NULL page_height, "
                f"  ROW_NUMBER() OVER (ORDER BY "
                f"    {'SUM(COALESCE(spend,0))' if lane=='own' else 'COUNT(*)'} DESC) nn "
                f"FROM creatives c WHERE lane=? AND source=? "
                f"GROUP BY group_slug ORDER BY belief DESC, creatives DESC",
                (label, lane, b)))

        if p == "/api/ads":
            b, slug = qs.get("brand", [""])[0], qs.get("block", [""])[0]
            lane = qs.get("lane", ["paid"])[0]
            if lane == "paid":
                return self._json(q(
                    "SELECT * FROM ads WHERE brand = ? AND block_slug = ? "
                    "ORDER BY variants DESC", (b, slug)))
            return self._json(q(
                "SELECT ref AS ad_id, media AS media_type, "
                "  COALESCE(variants,1) variants, file AS drive_file, "
                "  thumb, url, spend, swipe_id "
                "FROM creatives WHERE lane=? AND source=? AND group_slug=? "
                "ORDER BY COALESCE(spend,0) DESC, ref DESC LIMIT 200",
                (lane, b, slug)))

        if p == "/api/pages":
            b = qs.get("brand", [""])[0]
            lane = qs.get("lane", ["paid"])[0]
            if lane == "paid":
                return self._json(q(
                    "SELECT * FROM pages WHERE brand = ? ORDER BY ads_served DESC", (b,)))
            if lane == "own":
                rows = self._own_pages(b)
                return self._json([
                    {"brand": b, "slug": r["slug"], "url": r["url"],
                     "page_type": r.get("type", "unknown"), "height": r.get("height"),
                     "blocks_served": r.get("blocks", 0), "ads_served": r["ads"],
                     "spend": r["spend"]} for r in rows])
            # organic: the creator account is the destination
            return self._json(q(
                "SELECT source AS brand, group_slug AS slug, MIN(url) url, "
                "  'creator account' page_type, NULL height, "
                "  1 blocks_served, COUNT(*) ads_served, MAX(group_label) label "
                "FROM creatives WHERE lane='organic' AND source=? "
                "GROUP BY group_slug ORDER BY ads_served DESC", (b,)))

        if p == "/api/brief":
            # The synopsis reads the committed teardown, so the tool and the
            # written record can never drift apart.
            b = qs.get("brand", [""])[0]
            lane = qs.get("lane", ["paid"])[0]
            f = (os.path.join(HERE, "own", b, "teardown.md") if lane == "own"
                 else os.path.join(HERE, "organic", b, "teardown.md") if lane == "organic"
                 else os.path.join(HERE, b, "teardown.md"))
            if not os.path.isfile(f):
                return self._json({})
            md, out, cur = open(f).read(), {}, None
            for line in md.splitlines():
                if line.startswith("## "):
                    cur = line[3:].strip()
                    out[cur] = []
                elif cur:
                    out[cur].append(line)
            head = md.split("## ")[0]
            return self._json({
                "meta": head.strip(),
                "sections": {k: "\n".join(v).strip() for k, v in out.items()}})

        if p == "/api/steps":
            # A walked quiz funnel, if walk_quiz.py has captured one.
            b, slug = qs.get("brand", [""])[0], qs.get("page", [""])[0]
            d = os.path.join(DRIVE, b, "_pages", slug, "steps")
            if not os.path.isdir(d):
                return self._json([])
            out = []
            for f in sorted(x for x in os.listdir(d) if x.endswith(".txt")):
                n = f[5:7]
                out.append({"step": n,
                            "text": open(os.path.join(d, f)).read(),
                            "png": f"{b}/_pages/{slug}/steps/{f[:-4]}.png"})
            return self._json(out)

        # ---- the three lanes -------------------------------------------
        if p == "/api/lanes":
            return self._json(q(
                "SELECT lane, COUNT(*) creatives, COUNT(DISTINCT source) sources, "
                "  SUM(known != 'unjudged') known, SUM(verdict='swipe') swiped, "
                "  ROUND(SUM(COALESCE(spend,0))) spend "
                "FROM creatives GROUP BY lane ORDER BY "
                "  CASE lane WHEN 'own' THEN 0 WHEN 'paid' THEN 1 ELSE 2 END"))

        if p == "/api/sources":
            lane = qs.get("lane", [""])[0]
            return self._json(q(
                "SELECT s.*, ROUND(COALESCE(SUM(c.spend),0)) spend "
                "FROM sources s LEFT JOIN creatives c "
                "  ON c.lane = s.lane AND c.source = s.source "
                "WHERE s.lane = ? GROUP BY s.lane, s.source "
                "ORDER BY s.creatives DESC", (lane,)))

        if p == "/api/groups":
            lane = qs.get("lane", [""])[0]
            src = qs.get("source", [""])[0]
            return self._json(q(
                "SELECT group_slug, group_label, COUNT(*) creatives, "
                "  SUM(known = 'unjudged') unjudged, SUM(verdict='swipe') swiped, "
                "  MAX(variants) top_variants, ROUND(SUM(COALESCE(spend,0))) spend "
                "FROM creatives WHERE lane = ? AND source = ? "
                "GROUP BY group_slug ORDER BY spend DESC, creatives DESC", (lane, src)))

        if p == "/api/creatives":
            lane = qs.get("lane", [""])[0]
            src = qs.get("source", [""])[0]
            grp = qs.get("group", [""])[0]
            only = qs.get("unjudged", ["0"])[0] == "1"
            cond = "AND known = 'unjudged'" if only else ""
            return self._json(q(
                f"SELECT * FROM creatives WHERE lane=? AND source=? AND group_slug=? "
                f"{cond} ORDER BY COALESCE(spend,0) DESC, variants DESC, ref DESC "
                f"LIMIT 200", (lane, src, grp)))

        if p == "/api/profile":
            # The synopsis, straight off the regenerated PROFILE.md, so the
            # page and the committed record can never disagree.
            lane, src = qs.get("lane", [""])[0], qs.get("source", [""])[0]
            # Which record: the teardown (the read) or the brand card (the
            # counts). Both are committed files, so the page and the repo can
            # never drift apart.
            doc = {"teardown": "teardown.md", "brand": "_BRAND.md"}.get(
                qs.get("doc", ["profile"])[0], "PROFILE.md")
            base = (os.path.join(HERE, "own", src) if lane == "own"
                    else os.path.join(HERE, "organic", src) if lane == "organic"
                    else os.path.join(HERE, src))
            f = os.path.join(base, doc)
            return self._json({"md": open(f).read()} if os.path.isfile(f)
                              else {"md": ""})

        if p == "/api/lanepages":
            lane, src = qs.get("lane", [""])[0], qs.get("source", [""])[0]
            f = os.path.join(HERE, "own", src, "pages.json") if lane == "own" else None
            if not f or not os.path.isfile(f):
                return self._json([])
            caps = json.load(open(f))
            ads = json.load(open(os.path.join(HERE, "own", src, "ads.json")))["ads"]
            import collections as _c
            n, sp = _c.Counter(), _c.defaultdict(float)
            for a in ads:
                u = (a.get("landing_page") or "").split("?")[0]
                if u:
                    k = re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
                    n[k] += 1; sp[k] += a.get("spend") or 0
            out = []
            for sl, c in caps.items():
                k = re.sub(r"^https?://(www\.)?", "", c.get("url", "")).rstrip("/")
                out.append({**c, "slug": sl, "ads": n.get(k, 0),
                            "spend": round(sp.get(k, 0))})
            return self._json(sorted(out, key=lambda r: -r["spend"]))

        if p == "/api/vocab":
            # The fields and the values, served rather than hardcoded in the
            # page. `source` and `media` are closed sets the namer owns; the
            # rest are open, and their suggestions are learned from what has
            # already been judged, so the vocabulary grows from use instead of
            # from someone guessing a list up front.
            seen = {f: sorted({r["v"] for r in q(
                        f"SELECT DISTINCT {f} AS v FROM ads "
                        f"WHERE {f} NOT IN ('unclassified','unknown','')") if r["v"]})
                    for f in N.CREATIVE_FIELDS}
            return self._json({
                "fields": N.CREATIVE_FIELDS,
                "unclassified": N.UNCLASSIFIED,
                "closed": {"media": sorted(N.MEDIA), "source": sorted(N.SOURCE)},
                "signed_angles": signed_angle_brands(),
                "seen": seen,
                "judged_fields": ["source", "talent", "problem", "angle",
                                  "concept", "format"]})

        if p == "/api/queue":
            # What still needs a person, biggest angles first — and inside an
            # angle, the most-cloned creative first. You judge the ad they
            # believed in most, not whichever one the id sort put on top.
            b = qs.get("brand", [""])[0]
            where = "AND a.brand = ?" if b else ""
            args = (b,) if b else ()
            return self._json(q(
                "SELECT a.brand, a.block_slug, g.nn, g.headline, g.creatives, "
                "  SUM(a.source = 'unclassified') AS unjudged, "
                "  SUM(a.verdict = 'swipe') AS swiped, "
                "  SUM(a.verdict = 'pass') AS passed "
                "FROM ads a JOIN blocks g "
                "  ON g.brand = a.brand AND g.slug = a.block_slug "
                f"WHERE 1=1 {where} "
                "GROUP BY a.brand, a.block_slug "
                "ORDER BY unjudged = 0, g.creatives DESC", args))

        if p == "/api/next":
            b = qs.get("brand", [""])[0]
            slug = qs.get("block", [""])[0]
            only = qs.get("unjudged", ["1"])[0] == "1"
            cond = "AND a.source = 'unclassified'" if only else ""
            rows = q(
                "SELECT a.*, g.headline, g.primary_text, g.stage, g.landing_page, "
                "       g.nn, g.creatives AS angle_creatives "
                "FROM ads a JOIN blocks g "
                "  ON g.brand = a.brand AND g.slug = a.block_slug "
                f"WHERE a.brand = ? AND a.block_slug = ? {cond} "
                "ORDER BY a.variants DESC, a.ad_id DESC LIMIT 40", (b, slug))
            return self._json(rows)

        if p == "/thumb":
            return self._thumb(qs.get("u", [""])[0])

        if p.startswith("/media/"):
            return self._media(urllib.parse.unquote(p[len("/media/"):]))

        self.send_error(404)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/api/judge":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.send_error(400, "bad json")
        try:
            saved = save_judgement(body)
        except ValueError as e:
            body = json.dumps({"error": str(e)}).encode()
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        except Exception as e:
            body = json.dumps({"error": f"{type(e).__name__}: {e}"}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        return self._json(saved)

    # Covers on organic posts are hotlink-protected and time-limited: the
    # browser gets a 403 or an expired signature, so the judging view shows an
    # empty box. Fetching them here (once, then cached) is the difference
    # between a lane you can judge and a lane you cannot.
    THUMB_HOSTS = ("tiktokcdn.com", "tiktokcdn-us.com", "ytimg.com",
                   "cdninstagram.com", "fbcdn.net", "facebook.com",
                   "ggpht.com", "twimg.com")
    THUMB_DIR = os.path.join(HERE, ".build", "thumbs")

    def _own_pages(self, src):
        f = os.path.join(HERE, "own", src, "pages.json")
        if not os.path.isfile(f):
            return []
        caps = json.load(open(f))
        ads = json.load(open(os.path.join(HERE, "own", src, "ads.json")))["ads"]
        import collections as _c
        n, sp, blk = _c.Counter(), _c.defaultdict(float), _c.defaultdict(set)
        for a in ads:
            u = (a.get("landing_page") or "").split("?")[0]
            if not u:
                continue
            k = re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
            n[k] += 1; sp[k] += a.get("spend") or 0
            blk[k].add((a.get("body") or a.get("title") or "")[:200])
        out = []
        for sl, c in caps.items():
            k = re.sub(r"^https?://(www\.)?", "", c.get("url", "")).rstrip("/")
            out.append({**c, "slug": sl, "ads": n.get(k, 0),
                        "blocks": len(blk.get(k, [])), "spend": round(sp.get(k, 0))})
        return sorted(out, key=lambda r: -r["spend"])

    def _thumb(self, url):
        import hashlib, urllib.request
        try:
            host = urllib.parse.urlparse(url).hostname or ""
        except ValueError:
            return self.send_error(400)
        if not url.startswith("https://") or not any(
                host == h or host.endswith("." + h) for h in self.THUMB_HOSTS):
            return self.send_error(403, "not a thumbnail host")
        os.makedirs(self.THUMB_DIR, exist_ok=True)
        cache = os.path.join(self.THUMB_DIR,
                             hashlib.sha1(url.encode()).hexdigest() + ".jpg")
        if not os.path.exists(cache):
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/126.0 Safari/537.36",
                "Referer": f"https://{host}/"})
            try:
                with urllib.request.urlopen(req, timeout=20) as r, open(cache, "wb") as f:
                    f.write(r.read())
            except Exception:
                return self.send_error(404, "thumbnail gone")
        body = open(cache, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=86400")
        self.end_headers()
        self.wfile.write(body)

    def _media(self, rel):
        """Stream a file from the Drive mirror, honouring Range for video.

        Path conventions meet here: swiped media is stored by a pool path
        (`swipe-paid/...`, old or new form, read through swipe_home.resolve),
        or relative to the paid swipe root; our own produced media relative to
        the lab folder (`video-production/...`). Try the swipe home first, then
        the lab root, then the paid root, and refuse anything that escapes them.
        """
        lab = os.path.normpath(str(swipe_home.shared_assets() / "lab" / "damon"))
        roots = [os.path.normpath(str(swipe_home.root(p))) for p in swipe_home.POOLS]
        hit = swipe_home.resolve(rel)
        cands = [os.path.normpath(str(hit))] if hit else []
        cands += [os.path.normpath(os.path.join(base, rel))
                  for base in (lab, os.path.normpath(DRIVE))]
        full = None
        for cand in cands:
            if any(cand.startswith(b) for b in (lab, *roots)) and os.path.isfile(cand):
                full = cand
                break
        if not full:
            return self.send_error(404)
        size = os.path.getsize(full)
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else 0
            end = int(b) if b else size - 1
            end = min(end, size - 1)
        length = end - start + 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(full, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(262144, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return          # viewer seeked or closed the video
                remaining -= len(chunk)


def save_judgement(j):
    """One judgement, for any lane, keyed by swipe_id.

    Written to the shared record (corpus.judgements) and mirrored into the
    table so the page reflects it without a rebuild. The lane files are left
    exactly as their own systems wrote them — a judgement is ours, not theirs.
    """
    sid = (j.get("swipe_id") or "").strip()
    if not re.match(r"^swipe:(paid|own|organic):[a-z0-9]+:[A-Za-z0-9_.:-]+$", sid):
        raise ValueError(f"not a swipe id: {sid!r}")
    fields = {k: N.slug(v) for k, v in (j.get("fields") or {}).items()
              if k in N.CREATIVE_FIELDS and str(v).strip()}
    if "source" in fields and fields["source"] not in N.SOURCE:
        raise ValueError(f"source must be one of {sorted(N.SOURCE)}")
    if "media" in fields and fields["media"] not in N.MEDIA:
        raise ValueError(f"media must be one of {sorted(N.MEDIA)}")
    verdict = N.slug(j.get("verdict", "")) or None
    if verdict and verdict not in ("swipe", "pass"):
        raise ValueError("verdict is swipe or pass")

    con = sqlite3.connect(DB)
    if not con.execute("SELECT 1 FROM creatives WHERE swipe_id=?", (sid,)).fetchone():
        con.close()
        raise ValueError(f"{sid} is not in the corpus")
    import corpus  # this folder (the script's own folder is on sys.path)
    entry = corpus.save_judgement(sid, fields, verdict)
    sets, args = [], []
    for k, v in fields.items():
        sets.append(f"{'source_f' if k == 'source' else k} = ?"); args.append(v)
    if verdict:
        sets.append("verdict = ?"); args.append(verdict)
    if fields.get("source"):
        sets.append("known = CASE WHEN known='named' THEN 'named' ELSE 'judged' END")
    if sets:
        con.execute(f"UPDATE creatives SET {', '.join(sets)} WHERE swipe_id = ?",
                    (*args, sid))
        con.commit()
    con.close()
    return {"swipe_id": sid, **entry}


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True           # video streams must not block shutdown


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    if not os.path.exists(DB):
        sys.exit("no swipe.db — run `python3 build.py db` first")
    if not os.path.isdir(DRIVE):
        print("WARNING: Drive mirror not mounted — creatives will 404")
    n = q("SELECT COUNT(*) c FROM creatives")[0]["c"]
    lanes = ", ".join(f"{r['lane']} {r['creatives']}" for r in
                      q("SELECT lane, COUNT(*) creatives FROM creatives GROUP BY lane"))
    print(f"swipe browser · {n} creatives · {lanes} · http://localhost:{port}")
    Server(("127.0.0.1", port), Handler).serve_forever()
