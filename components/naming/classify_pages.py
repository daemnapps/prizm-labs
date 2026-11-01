#!/usr/bin/env python3
"""Sort a captured page library into funnel types and read the codes off the slugs.

    python3 classify_pages.py <brand-slug> [assets-folder]

Reads assets/<brand>/pages/_capture.json, writes _classified.json and a
by-type/ index of markdown pointers. Type comes from the page's own shape
(headline pattern, quiz markup, product markup), never from the slug alone —
the slug supplies the channel and product codes the operator encoded in it.
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))

CHANNEL = [("-google", "google"), ("_google", "google"), ("-ga", "google-ads"),
           ("-applovin", "applovin"), ("-nago", "no-google"), ("meta", "meta"),
           ("-amazon", "amazon")]
PRODUCT = [("ooo", "oil-of-oregano"), ("oregano", "oil-of-oregano"),
           ("ebso", "black-seed-oil"), ("bso", "black-seed-oil"),
           ("garlic", "aged-garlic"), ("lym", "lymphatic")]
# the operator's own suffix vocabulary, read off ~210 slugs
VARIANT = [("-cc", "cc"), ("-comp", "comp"), ("-compl", "comp"), ("-ps", "ps"),
           ("-ds", "ds"), ("-v2", "v2"), ("-v3", "v3"), ("-short", "short"),
           ("-long", "long"), ("-old", "old")]
AUDIENCE = [("women", "women"), ("men", "men"), ("w40", "women-40"),
            ("m40", "men-40"), ("menopause", "menopause"), ("35", "35-plus"),
            ("40", "40-plus"), ("50", "50-plus"), ("60", "60-plus"),
            ("glp-1", "glp-1"), ("pet", "pet-owners")]

def tags(slug, table):
    return sorted({v for k, v in table if k in slug})

def page_type(row):
    slug, t, txt = row["slug"], (row.get("title") or ""), row.get("text", "")
    low = txt.lower()
    if "/blogs/" in row["url"]:
        return "blog"
    if "/products/" in row["url"]:
        return "product-page"
    if re.search(r"\b(quiz)\b", slug) or ("question 1" in low and "quiz" in low):
        return "quiz"
    if any(k in slug for k in ("contact", "track", "subscription", "membership",
                               "opt-out", "dispute", "welcome-guide", "subscriber-hub",
                               "about-us", "history", "pwcontact", "reviews", "pdp")):
        return "utility"
    if re.match(r"^\s*(top\s*\d|\d+\s+(reasons|benefits|things|warning|rules|gut))", t, re.I) \
       or re.search(r"^\s*\d+\s+(reasons|benefits|things)", txt[:400], re.I):
        return "listicle"
    if "comparison" in slug or " vs " in t.lower() or "-vs-" in slug:
        return "comparison"
    if re.search(r"(review|honest)", slug) and "google" in slug:
        return "review-page"
    # An advertorial is an ARTICLE — it carries a byline, a publication or a
    # read time, and it reads as editorial. Length alone never made one, and
    # using length as the test silently labelled every long page an
    # advertorial (the owner, 2026-09-11: "it's clearly not an advertorial").
    # Test the markers an advertorial actually carries, not a stray "by X" —
    # "Trusted By Leading Doctors" matched that and made Norse's sales page an
    # advertorial. These four are the real tells.
    bylined = re.search(r"sponsored content|paid content|\badvertorial\b|\d+\s*min read", txt[:4000], re.I)
    if bylined:
        return "advertorial"
    # A long page that carries the whole argument itself and hands off rather
    # than taking the money: hero, mechanism, proof, guarantee, no cart.
    if len(txt) > 6000:
        return "salespage"
    return "prelander"

def file_by_type(d, out):
    """One folder per page under by-type/<type>/, carrying its own _PAGE.md."""
    import shutil
    root = os.path.join(d, "by-type")
    for p in out:
        dest = os.path.join(root, p["type"], p["slug"])
        os.makedirs(dest, exist_ok=True)
        for ext in ("html", "txt"):
            src = os.path.join(d, p["slug"] + "." + ext)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dest, "page." + ext))
        open(os.path.join(dest, "_PAGE.md"), "w").write(
            f"# {p['title'] or p['slug']}\n\n- **URL:** {p['url']}\n- **Type:** {p['type']}\n"
            f"- **Length:** {p['chars']:,} characters of text\n"
            f"- **Channel code:** {', '.join(p['channel']) or '—'}\n"
            f"- **Product code:** {', '.join(p['product']) or '—'}\n"
            f"- **Audience code:** {', '.join(p['audience']) or '—'}\n"
            f"- **Variant code:** {', '.join(p['variant']) or '—'}\n"
            f"- **Stack:** {', '.join(sorted(p['stack'])) or '—'}\n")
    types = collections.Counter(p["type"] for p in out)
    with open(os.path.join(root, "README.md"), "w") as fh:
        fh.write("# Page library — by type\n\nEvery live page captured from the site, filed by what it "
                 "structurally is (numbered list / narrative / cart / quiz), not by how it looks.\n\n"
                 "```\nby-type/\n  <type>/\n    <slug>/\n      _PAGE.md   what it is, URL, codes, stack\n"
                 "      page.html · page.txt\n```\n\n| type | pages |\n|---|---:|\n")
        for t, n in types.most_common():
            fh.write(f"| {t} | {n} |\n")
        fh.write(f"\n**Total:** {len(out)} live pages.\n")
    print(f"filed into {root}")

def main(brand, assets=None):
    # The captures are a source of record and stay where they are captured;
    # a component never holds one (components/CLAUDE.md rule 5). Before this
    # file graduated out of lab the two happened to sit together and `HERE`
    # found both — so the caller now says where the captures are, and running
    # from the capture folder still works with no argument.
    root = assets or os.path.join(os.getcwd(), "assets")
    d = os.path.join(root, brand, "pages")
    if not os.path.isdir(d):
        sys.exit(f"no captures at {d} — pass the assets folder as the second argument")
    rows = json.load(open(os.path.join(d, "_capture.json")))
    out = []
    for r in rows:
        if not r.get("text") or r.get("status") != 200:
            continue  # 404s are dead slugs, not pages
        slug = r["url"].lower()
        out.append({"url": r["url"], "slug": r["slug"], "title": r.get("title"),
                    "status": r.get("status"), "chars": r.get("text_chars"),
                    "type": page_type(r), "channel": tags(slug, CHANNEL),
                    "product": tags(slug, PRODUCT), "variant": tags(slug, VARIANT),
                    "audience": tags(slug, AUDIENCE),
                    "stack": {k: v for k, v in (r.get("stack") or {}).items() if k != "scripts" and v}})
    json.dump(out, open(os.path.join(d, "_classified.json"), "w"), indent=1)
    file_by_type(d, out)
    by = collections.Counter(p["type"] for p in out)
    print("pages:", len(out))
    for t, n in by.most_common():
        print(f"  {n:4}  {t}")
    print("\nchannel:", collections.Counter(c for p in out for c in p["channel"]).most_common())
    print("product:", collections.Counter(c for p in out for c in p["product"]).most_common())
    print("audience:", collections.Counter(c for p in out for c in p["audience"]).most_common())
    print("variant:", collections.Counter(c for p in out for c in p["variant"]).most_common())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
