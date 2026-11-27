#!/usr/bin/env python3
"""Brand intake — index what a brand already has (a Google Drive of loose folders, its website) and map
every file to the brand-folder blank it can fill.

    python3 components/brand-intake/intake.py drive --brand <b> --folder <Drive folder link or id>
    python3 components/brand-intake/intake.py site  --brand <b> --url https://brand.com
    python3 components/brand-intake/intake.py plan  --brand <b>          which blanks are empty, and the files that can fill each
    python3 components/brand-intake/intake.py read  --brand <b> --file <Drive file id>   a Doc, Sheet or Slides as plain text

Drive: the folder must be shared with the brand's own Drive service account (GDRIVE_SA_KEY, in .env; its
email is in that key). Nothing is downloaded: every file is kept by its Drive id and link, and footage is
handed to the asset index by folder. Site: the home page, its sitemap and its product pages, read like a
browser would; it finds the store platform, the review apps and every outside review page it links to.

Writes only under runs/brand-intake/<brand>/ (git ignores runs/). It never writes the brand folder: the
`brand-intake` skill drafts each blank from the plan, marked as a draft, for the owner to confirm.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SLOTS = json.loads((HERE / "slots.json").read_text())
FOLDER_MIME = "application/vnd.google-apps.folder"
MAX_FILES = 20000
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
REVIEW_APPS = {
    "junip": r"junip", "judgeme": r"judge\.?me", "okendo": r"okendo", "yotpo": r"yotpo",
    "loox": r"loox\.io|loox-", "stamped": r"stamped\.io", "reviews.io": r"reviews\.io|reviewsio",
    "trustpilot": r"trustpilot", "kiwi": r"kiwisizing|kiwi-?reviews", "fera": r"fera\.ai",
}
REVIEW_SITES = r"((?:www\.)?(?:trustpilot\.com/review/[^\"'\s<>]+|amazon\.[a-z.]+/[^\"'\s<>]*(?:dp|stores)/[^\"'\s<>]+|g\.page/[^\"'\s<>]+|google\.com/maps/place/[^\"'\s<>]+|sitejabber\.com/reviews/[^\"'\s<>]+|reviews\.io/company-reviews/[^\"'\s<>]+|bbb\.org/[^\"'\s<>]+|yelp\.com/biz/[^\"'\s<>]+))"
SOCIAL = r"https?://(?:www\.)?(instagram\.com|tiktok\.com|facebook\.com|youtube\.com|x\.com|twitter\.com|pinterest\.com|reddit\.com)/[A-Za-z0-9_.@/-]+"
PLATFORMS = {"shopify": r"cdn\.shopify\.com|myshopify\.com|Shopify\.theme", "next-commerce": r"29next|next commerce",
             "woocommerce": r"woocommerce|wp-content", "bigcommerce": r"bigcommerce", "squarespace": r"squarespace",
             "wix": r"wixstatic|wix\.com"}


def out_dir(brand, root=REPO):
    d = Path(root) / "runs" / "brand-intake" / brand
    d.mkdir(parents=True, exist_ok=True)
    return d


def words(text):
    return " " + " ".join(re.findall(r"[a-z0-9.]+", text.lower())) + " "


def kind_of(mime):
    for kind, prefixes in SLOTS["kinds"].items():
        if any(mime.startswith(p) for p in prefixes):
            return kind
    return "other"


def matches(path, mime):
    """[(slot id, score)] for one file: a word in its path scores 2, the right type 1; type alone never places it."""
    text, kind = words(path), kind_of(mime)
    out = []
    for slot in SLOTS["slots"]:
        hits = [w for w in slot["words"] if f" {w} " in text]
        if hits:
            out.append((slot["id"], 2 * len(hits) + (1 if kind in slot["kinds"] else 0)))
    if kind == "video" and not any(s == "brand-assets" for s, _ in out):
        out.append(("brand-assets", 1))                       # loose footage still belongs in the library
    if kind == "form" and not any(s == "surveys-support" for s, _ in out):
        out.append(("surveys-support", 2))
    return sorted(out, key=lambda x: -x[1])


# --- Drive ---------------------------------------------------------------------------

def folder_id(value):
    m = re.search(r"/folders/([A-Za-z0-9_-]{10,})", value or "") or re.fullmatch(r"([A-Za-z0-9_-]{10,})", value or "")
    if not m:
        raise SystemExit("Give the Drive folder's link or id.")
    return m.group(1)


def drive_lister():
    sys.path.insert(0, str(REPO / "components" / "gdrive-creator"))
    from gdrive_creator import engine
    svc = engine.service()

    def children(fid):
        token, out = None, []
        while True:
            kw = dict(q=f"'{fid}' in parents and trashed = false", pageSize=1000, supportsAllDrives=True,
                      includeItemsFromAllDrives=True,
                      fields="nextPageToken, files(id,name,mimeType,size,modifiedTime,webViewLink)")
            if token:
                kw["pageToken"] = token
            r = svc.files().list(**kw).execute()
            out += r.get("files") or []
            token = r.get("nextPageToken")
            if not token:
                return out
    return children


def index_drive(root_id, children):
    files, folders, queue = [], 0, [(root_id, "")]
    while queue:
        fid, path = queue.pop(0)
        for f in children(fid):
            p = f"{path}/{f['name']}" if path else f["name"]
            if f["mimeType"] == FOLDER_MIME:
                folders += 1
                queue.append((f["id"], p))
                continue
            files.append({"id": f["id"], "path": p, "mime": f["mimeType"], "kind": kind_of(f["mimeType"]),
                          "size": int(f.get("size") or 0), "modified": f.get("modifiedTime"),
                          "link": f.get("webViewLink") or f"https://drive.google.com/file/d/{f['id']}/view",
                          "folder": fid, "slots": [s for s, _ in matches(p, f["mimeType"])]})
            if len(files) >= MAX_FILES:
                return files, folders, True
    return files, folders, False


# --- website -------------------------------------------------------------------------

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000).decode("utf-8", "replace")


def index_site(url, get=fetch, max_products=25):
    if not re.match(r"https?://", url or ""):
        raise SystemExit("Give the site's full address, like https://brand.com")
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    home = get(url)
    pages = {url: home}
    products = []
    for sm in (base + "/sitemap.xml", base + "/sitemap_products_1.xml"):
        try:
            xml = get(sm)
        except Exception:
            continue
        for loc in re.findall(r"<loc>([^<]+)</loc>", xml):
            loc = loc.strip()
            if loc.endswith(".xml") and "product" in loc and loc != sm:
                try:
                    xml2 = get(loc)
                    products += [x.strip() for x in re.findall(r"<loc>([^<]+)</loc>", xml2) if "/products/" in x]
                except Exception:
                    pass
            elif "/products/" in loc or "/product/" in loc:
                products.append(loc)
    products += [urllib.parse.urljoin(base, h) for h in re.findall(r"href=[\"']([^\"']*/products?/[^\"'#?]+)", home)]
    products = list(dict.fromkeys(p for p in products if p.startswith(base)))
    for p in products[:max_products]:
        try:
            pages[p] = get(p)
        except Exception:
            pass
    text = "\n".join(pages.values())
    apps = sorted(k for k, rx in REVIEW_APPS.items() if re.search(rx, text, re.I))
    platform = next((k for k, rx in PLATFORMS.items() if re.search(rx, text, re.I)), "unknown")
    shops = sorted(set(re.findall(r"([a-z0-9][a-z0-9-]*\.myshopify\.com)", text)))
    title = (re.search(r"<title>([^<]{1,200})", home, re.I) or [None, ""])[1].strip()
    return {
        "url": url, "title": title, "platform": platform, "myshopify": shops,
        "review_apps": apps,
        "review_pages": sorted(set("https://" + m if not m.startswith("http") else m for m in re.findall(REVIEW_SITES, text))),
        "social": sorted(set(m.group(0).rstrip("/") for m in re.finditer(SOCIAL, text) if not re.search(r"/(tr|sharer|plugins|share|intent|dialog)(/|$|\?)", m.group(0)))),
        "products": [{"url": p, "read": p in pages} for p in products],
        "pages_read": len(pages),
    }


# --- the plan --------------------------------------------------------------------------

def _blank(folder, fills):
    """A slot is blank when none of its files exist with real content (a <placeholder> doesn't count)."""
    for f in fills:
        if "<" in f or " " in f:
            continue
        p = folder / f
        if p.is_dir() and any(x for x in p.iterdir() if not x.name.startswith(".") and x.name != "README.md"):
            return False
        if p.is_file():
            text = p.read_text(errors="replace")
            if text.strip() and "<" not in text and "TODO" not in text:
                return False
    return True


def plan(brand, root=REPO):
    d = out_dir(brand, root)
    drive = json.loads((d / "drive-index.json").read_text()) if (d / "drive-index.json").exists() else {"files": []}
    site = json.loads((d / "site-index.json").read_text()) if (d / "site-index.json").exists() else None
    folder = Path(root) / "brands" / brand
    rows = []
    for slot in SLOTS["slots"]:
        scored = []
        for f in drive["files"]:
            for sid, score in matches(f["path"], f["mime"]):
                if sid == slot["id"]:
                    scored.append((score, f))
        scored.sort(key=lambda x: (-x[0], x[1]["path"]))
        found = [{"path": f["path"], "id": f["id"], "kind": f["kind"], "link": f["link"]} for _, f in scored]
        site_notes = []
        if site:
            if slot["id"] == "reviews":
                site_notes = [f"review app on the site: {a}" for a in site["review_apps"]] + [f"review page: {u}" for u in site["review_pages"]]
            elif slot["id"] == "best-seller":
                site_notes = [f"product page: {p['url']}" for p in site["products"][:25]]
            elif slot["id"] in ("story", "position", "look"):
                site_notes = [f"home page: {site['url']}"]
            elif slot["id"] == "creators":
                site_notes = [f"social: {s}" for s in site["social"]]
        blank = _blank(folder, slot["fills"]) if folder.is_dir() else True
        state = "filled" if not blank else ("can fill" if found or site_notes else "ask")
        rows.append({"slot": slot["id"], "name": slot["name"], "fills": slot["fills"], "state": state,
                     "files": found[:40], "more": max(0, len(found) - 40), "site": site_notes[:40]})
    result = {"brand": brand, "made": datetime.now(timezone.utc).isoformat(timespec="seconds"), "slots": rows,
              "unplaced": [f["path"] for f in drive["files"] if not f["slots"]][:200]}
    (d / "plan.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    md = [f"# Brand intake plan · {brand}", "", "| Blank | State | From |", "|---|---|---|"]
    for r in rows:
        src = "; ".join([x["path"] for x in r["files"][:3]] + r["site"][:2]) or "—"
        md.append(f"| {r['name']} | {r['state']} | {src} |")
    (d / "plan.md").write_text("\n".join(md) + "\n")
    return result


def read_file(file_id):
    sys.path.insert(0, str(REPO / "components" / "gdrive-creator"))
    from gdrive_creator import engine
    svc = engine.service()
    meta = svc.files().get(fileId=file_id, fields="mimeType,name", supportsAllDrives=True).execute()
    mime = meta["mimeType"]
    export = {"application/vnd.google-apps.document": "text/plain", "application/vnd.google-apps.presentation": "text/plain",
              "application/vnd.google-apps.spreadsheet": "text/csv"}.get(mime)
    if export:
        data = svc.files().export(fileId=file_id, mimeType=export).execute()
    elif mime.startswith("text/") or mime == "text/csv":
        data = svc.files().get_media(fileId=file_id).execute()
    else:
        raise SystemExit(f"{meta['name']} is {mime}; only Google Docs, Sheets, Slides and text files are read as text.")
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data


def main(argv=None, out=sys.stdout, root=REPO, children=None, get=fetch):
    ap = argparse.ArgumentParser(description="Index a brand's Drive and website; map them to its brand-folder blanks.")
    ap.add_argument("cmd", choices=["drive", "site", "plan", "read"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--folder")
    ap.add_argument("--url")
    ap.add_argument("--file")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a.brand):
        out.write("A brand name is lower-case letters, digits and dashes.\n")
        return 2
    try:
        if a.cmd == "drive":
            fid = folder_id(a.folder)
            files, folders, capped = index_drive(fid, children or drive_lister())
            data = {"folder": fid, "made": datetime.now(timezone.utc).isoformat(timespec="seconds"), "folders": folders,
                    "capped": capped, "files": files}
            (out_dir(a.brand, root) / "drive-index.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            kinds = Counter(f["kind"] for f in files)
            placed = sum(1 for f in files if f["slots"])
            out.write(f"Indexed {len(files)} files in {folders} folders{' (stopped at the cap)' if capped else ''}: "
                      + ", ".join(f"{n} {k}" for k, n in kinds.most_common()) + f". {placed} match a blank.\n")
        elif a.cmd == "site":
            data = index_site(a.url, get=get)
            (out_dir(a.brand, root) / "site-index.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            out.write(f"{data['title'] or a.url}: {data['platform']} store, {len(data['products'])} product pages, "
                      f"review apps: {', '.join(data['review_apps']) or 'none seen'}, "
                      f"outside review pages: {len(data['review_pages'])}, social: {len(data['social'])}.\n")
        elif a.cmd == "plan":
            p = plan(a.brand, root)
            for r in p["slots"]:
                mark = {"filled": "✓", "can fill": "→", "ask": "?"}[r["state"]]
                n = len(r["files"]) + r["more"]
                out.write(f"{mark} {r['name']:30} {r['state']:9} {n} file(s){', ' + str(len(r['site'])) + ' from the site' if r['site'] else ''}\n")
            out.write(f"Plan: runs/brand-intake/{a.brand}/plan.md\n")
        else:
            if not a.file:
                raise SystemExit("Give --file <Drive file id>.")
            out.write(read_file(a.file))
    except SystemExit as err:
        out.write(f"{err}\n")
        return 2
    except urllib.error.URLError as err:
        out.write(f"Couldn't read the site ({getattr(err, 'reason', err)}).\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
