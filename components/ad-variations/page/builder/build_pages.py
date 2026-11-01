#!/usr/bin/env python3
"""Builds The Variation Cycle + Format Bank pages from the swap runs and the Hua Jin pool."""
import json, html, re
from pathlib import Path

S = Path(__file__).parent
T = S / "tree"
RUNS = T / "runs/ad-variations/brand-b"
OUT = S / "pages"; OUT.mkdir(exist_ok=True)

SWAPS = [
    ("mofu-x-public-reaction", "MOFU showing hands", "static", "Public reaction, repeat demo", "Dbmik5RNWQV", "1 · filed earlier"),
    ("grandma-house-x-kitchen-fix", "Grandma House (face)", "video · top 1%", "Body scan → kitchen fix", "DavXLyHKZSB", "2 · kitchen fix"),
    ("melanin-vsl-x-kitchen-fix", "Melanin VSL", "video · top 1%", "Body scan → kitchen fix", "DavXLyHKZSB", "2 · kitchen fix"),
    ("grandma-static-x-public-reaction", "Grandma static", "static", "Public reaction, repeat demo", "Dbmik5RNWQV", "3 · public reaction"),
    ("hands-photostrip-x-public-reaction", "Hands photostrip (p140)", "static", "Public reaction, repeat demo", "Dbmik5RNWQV", "3 · public reaction"),
    ("grandma-house-x-huajin-signs-remedy", "Grandma House (face)", "video · top 1%", "Hua Jin · signs → remedy → book", "Ddh2x27iLY0", "4 · Hua Jin match"),
    ("grandma-house-x-huajin-purity-tests", "Grandma House (face)", "video · top 1%", "Asian grandma recipe (Hua Jin's most popular)", "Dd12vX6inUo", "4 · Hua Jin match"),
]

# Hua Jin top 10 vs the Grandma House winner (hand-read match, 5 Oct)
MATCH = {
    "Ddh2x27iLY0": ("strong", "Grandma points out the signs, granddaughter makes the recipe, both hold it up. Same cast and order as Grandma House.", "swap-grandma-house-x-huajin-signs-remedy"),
    "Dd12vX6inUo": ("strong", "Her biggest post. The named side-by-side tests carry the ingredient roll call one item at a time.", "swap-grandma-house-x-huajin-purity-tests"),
    "Dc_3JDZDnKa": ("strong", "Point at the problem → four-ingredient recipe → why it works → book. Nearly one-to-one with Grandma House. Next in line.", None),
    "DdKbAPNDg2n": ("strong", "The grandma's own age is the proof, three numbered secrets. Fits the lineage line and the granddaughter proof.", None),
    "DeBPt79DllY": ("medium", "Grandma talks over a gross-out close-up, then the recipe. Needs an honest face close-up in place of the gross-out.", None),
    "DdNDb37y2Ds": ("medium", "One unusual tip, short, then the book. Carries one ingredient well, not the full roll call.", None),
    "Dd5HtikDoO6": ("weak", "Hangs on an instant foaming reaction on skin. Our scrub can't honestly show an instant result.", None),
    "DdfEJsmiMxZ": ("weak", "Long anatomy-model explainer selling a supplement. Better match for the melanin VSL than for Grandma House.", None),
    "DdC6mkplOjS": ("weak", "Presenters keyed over medical animations. Melanin VSL territory, not Grandma House.", None),
    "DdzrUsBCVsP": ("weak", "Over two minutes of medical animation and a product pitch. Melanin VSL territory.", None),
}


def rd(p):
    return p.read_text(errors="replace") if p.is_file() else ""


def norm(x):
    m = re.search(r"((?:runs|components)/.+?)/?$", x or "")
    return m.group(1) if m else x


def swaps_data():
    out = []
    for label, concept, ckind, fmt, fcode, step in SWAPS:
        d = RUNS / f"swap-{label}"
        run = json.loads(rd(d / "run.json") or "{}")
        spec = rd(d / "spec.md")
        out.append(dict(label=label, concept=concept, ckind=ckind, fmt=fmt, fcode=fcode, step=step,
                        spec=spec, sent=rd(d / "sent.md"), state="spec written" if spec else "waiting",
                        opened=run.get("opened", ""), cpath=norm(run.get("concept", "")), fpath=norm(run.get("format", "")), product=run.get("product", ""), avatar=run.get("avatar", "")))
    return out


def huajin():
    pj = json.loads(rd(T / "components/swipe-organic/hua-jin/posts.json"))
    rows = []
    for p in pj["posts"][:10]:
        f = json.loads(rd(T / f"components/swipe-organic/records/swipe-videos/{p['id']}/format.json") or "{}")
        m = MATCH.get(p["id"], ("—", "", None))
        rows.append(dict(id=p["id"], rank=p["file"][:2], views=p["views"], eng=p.get("engagement"), secs=p["seconds"],
                         posted=p.get("posted"), url=p["url"], caption=p.get("caption", ""), format=f.get("format_id") or p.get("format"),
                         what=f.get("what_happens") or p.get("what"), why=f.get("why", ""), carries=f.get("carries_the_value", ""),
                         beats=f.get("beats", []), match=m[0], match_why=m[1], swap=m[2]))
    return rows


def library():
    t = rd(T / "components/swipe-organic/hua-jin/format-read-prompt.md")
    rows = re.findall(r"^- ([a-z0-9-]+) — ([^:]+): (.+)$", t, re.M)
    return [dict(id=a, name=b, mech=c) for a, b, c in rows]


def j(x):
    return json.dumps(x).replace("</", "<\\/")


TPL = (S / "page_template.html").read_text()
BTPL = S / "builder_template.html"

V = "runs/video-teardown/brand-b/"; I = "runs/image-teardown/brand-b/"
CONCEPTS = [
 (V+"top1-brand-b-01-grandma-house-face","Grandma House","video · 1:05"),
 (V+"top1-brand-b-02-vsl-melanin-overproducti","Melanin VSL","video · 6:48"),
 (V+"top1-brand-b-05-short-video-today-years","Today-years","video · 0:49"),
 (V+"top1-brand-b-06-scrub-task-43-hook-3","Scrub task 43 · hook 3","video · 0:59"),
 (V+"top1-brand-b-10-scrub-task-5-hook-2","Scrub task 5 · hook 2","video · 1:12"),
 (V+"top1-brand-b-03-scrub-task-86-hook-5-wt","Scrub task 86 · hook 5","video · 2:34"),
 (V+"top1-brand-b-07-scrub-task-4-hook-1","Scrub task 4 · hook 1","video · 4:08"),
 (I+"brand-b-batch-top-static-mofu-showing-hands","MOFU showing hands","static"),
 (I+"brand-b-batch-top-static-grandma-static","Grandma static","static"),
 (I+"brand-b-batch-top-static-hands-photostrip-p140","Hands photostrip (p140)","static"),
]
F = "components/swipe-organic/records/"
FORMATS = [
 (F+"teardowns/DavXLyHKZSB","Body scan → kitchen fix","@evergreen.america · 38.8M views · full teardown"),
 (F+"teardowns/Dbmik5RNWQV","Public reaction, repeat demo","@leahandersenphd · 52.8M views · full teardown"),
 (F+"swipe-videos/Dd7GVDvprzl","TV-shopping live demo (new)","@frankyshaw repost · AI-made mascara ad · 2:20 · format read only"),
]
QUESTIONS = {
 "mofu-x-public-reaction": [("product","The winner sold the body scrub on hands. This spec moves it to the face scrub. Which product?",["Face scrub, as written","Run it on the body scrub instead"])],
 "grandma-house-x-kitchen-fix": [("hook","Keep the hook “It works too well”? Nothing in the brand files backs it directly.",["Keep it","Cut it"])],
 "melanin-vsl-x-kitchen-fix": [("melanin","The brand rules ban the word “melanin”, so the spec says “too much color” instead. OK?",["OK as written","I want “melanin” back (rule change)"])],
 "grandma-static-x-public-reaction": [("laser","The elder scrubs one cheek while someone uses an at-home laser on the other, in front of a crowd. Keep the laser contrast?",["Keep it","Lose the laser"])],
 "hands-photostrip-x-public-reaction": [("words","All the words (headline, offer, guarantee) sit in the caption; the screen carries only small print. OK?",["Caption only","Put the headline on screen"])],
 "grandma-house-x-huajin-signs-remedy": [("cta","Her close is “comment BOOK”. The spec swaps it for the tube to the lens + “Tap below”. Which?",["Tap below","Run a real comment gate"])],
 "grandma-house-x-huajin-purity-tests": [("cta","Her close is “comment BOOK”. The spec swaps it for the tube to the lens + “Tap below”. Which?",["Tap below","Run a real comment gate"])],
}


def build(kind):
    data = dict(kind=kind, swaps=swaps_data(), huajin=huajin(), library=library(),
                swap_prompt=rd(T / "components/ad-variations/prompts/stage-format-swap/stage-format-swap-v1-damon.md"),
                read_prompt=rd(T / "components/swipe-organic/hua-jin/format-read-prompt.md"))
    if kind == "bank":
        data["swaps"] = [dict(s, sent="", spec=("written" if s["spec"] else "")) for s in data["swaps"]]
    page = TPL.replace("/*DATA*/null", j(data))
    page = page.replace("{{TITLE}}", "The Variation Cycle" if kind == "cycle" else "Format Bank")
    (OUT / ("variation-cycle.html" if kind == "cycle" else "format-bank.html")).write_text(page)


PLAIN = {
 "grandma-house-x-kitchen-fix": ("41s", "A see-through face: turmeric clears the dull layer on top while the grandma warns \u201cdon\u2019t use it more than twice a week \u2014 it works too well.\u201d Faceless hands grind turmeric, moringa, ginger, chamomile and walnut shell in a stone mortar, each with its one job. The tube dissolves into a glowing look under the skin, then a bright bare-faced woman, the guarantee and buy 2, get 1 free."),
 "melanin-vsl-x-kitchen-fix": ("40s", "A see-through face: the scrub lifts a dull film and the spots go a shade lighter. Faceless hands in a kitchen tell the cut-apple story, the peels and lasers that didn\u2019t fix it, and the four ingredients. A gold look under the skin shows turmeric stopping new spots. Ends on turmeric blooming in water: buy 2, get 1 free."),
 "_parked-grandma-house-x-huajin-signs-remedy": ("58s", "The grandma points at dark spots on a face \u2014 \u201cThis. This.\u201d \u2014 and warns it works too well. Her granddaughter makes the recipe at the table, one ingredient at a time, then uses the scrub on her own face. Both hold the tube to the camera the way Hua Jin holds her book: \u201cTap below,\u201d buy 2, get 1 free."),
 "grandma-house-x-huajin-purity-tests": ("65s", "Two women run quick side-by-side tests: each plant held next to its line on the face scrub label, body-scrub grain against face-scrub grain, and a real stain test \u2014 raw turmeric goes yellow, the scrub rinses clean. The grandma says why serums and peels don\u2019t last. Ends with the tube to the lens, \u201cTap below,\u201d buy 2, get 1 free."),
}


def builder():
    sw = [x for x in swaps_data() if x["label"] in PLAIN]
    for x in sw: x["runtime"], x["plain"] = PLAIN[x["label"]]
    for x in sw: x["questions"] = [dict(id=a, q=b, opts=c) for a, b, c in QUESTIONS.get(x["label"], [])]
    hj = huajin()
    fm = [dict(path=a, name=b, note=c) for a, b, c in FORMATS] + [
        dict(path=F + "swipe-videos/" + r["id"], name="Asian grandma recipe (Hua Jin's most popular)", note=f"{r['views']//1000}k views · {r['secs']}s · format read only") for r in hj[:1]]
    thumbs = json.loads(rd(S / "thumbs.json") or "{}"); stats = json.loads(rd(S / "stats.json") or "{}")
    lib = {x["id"]: x["name"] for x in library()}
    fid = {"DavXLyHKZSB": "new:body-scan-problem-kitchen-fix", "Dbmik5RNWQV": "public-reaction-repeat-demo",
           "Dd7GVDvprzl": "subtitled-monologue-evidence-cutaways", "Dd12vX6inUo": "captioned-steps-comment-gate"}
    hand = {"DavXLyHKZSB": "@evergreen.america", "Dbmik5RNWQV": "@leahandersenphd", "Dd7GVDvprzl": "@frankyshaw repost", "Dd12vX6inUo": "@hua_jin123"}
    for f in fm:
        code = f["path"].split("/")[-1]; i = fid.get(code, "")
        f.update(code=code, format_id=i, name=lib.get(i) or (i.replace("new:", "") + " (proposed, not in the library yet)"), note=hand.get(code, ""))
    links = json.loads(rd(S / "videolinks.json") or "{}")
    data = dict(kind="builder", swaps=sw, thumbs=thumbs, stats=stats, links=links, huajin=hj[:1], library=library(),
                concepts=[dict(path=a, name=b, note=c) for a, b, c in CONCEPTS if c.startswith("video")], formats=fm,
                products=["brilliance-face-scrub", "brilliance-body-scrub", "radiance-body-cream"], avatars=["spot-hider"],
                swap_prompt=rd(T / "components/ad-variations/prompts/stage-format-swap/stage-format-swap-v1-damon.md"),
                read_prompt=rd(T / "components/swipe-organic/hua-jin/format-read-prompt.md"))
    (OUT / "variation-cycle.html").write_text(BTPL.read_text().replace("/*DATA*/null", j(data)))


if __name__ == "__main__":
    builder()
    print("built", [p.name for p in OUT.iterdir()])
