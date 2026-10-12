#!/usr/bin/env python3
"""Turn a brand's hand-written teardown.md into teardown-content.json for build_page.py.

    python3 md_to_content.py <brand>

The judgments (findings, offer, stack, take, beat) are lifted verbatim from the
write-up, so the page and the Markdown always say the same thing. Only the
framing strings (standfirst, intros, metrics) are set per brand below.
"""
import html, json, os, re, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
for _r in Path(HERE).parents:          # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402


def inline(t):
    t = html.escape(t.strip(), quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", t)


def section(md, title):
    m = re.search(rf"^##\s+{re.escape(title)}.*?\n(.*?)(?=^##\s|\Z)", md, re.S | re.M)
    return m.group(1) if m else ""


def numbered(txt):
    out, cur = [], None
    for l in txt.splitlines():
        if re.match(r"^\d+\.\s", l):
            cur = [re.sub(r"^\d+\.\s+", "", l)]; out.append(cur)
        elif cur is not None and l.strip():
            cur.append(l.strip())
    return [" ".join(x) for x in out]


def bullets(txt):
    out, cur = [], None
    for l in txt.splitlines():
        if l.startswith("- "):
            cur = [l[2:]]; out.append(cur)
        elif cur is not None and l.startswith("  ") and l.strip():
            cur.append(l.strip())
        elif not l.strip():
            cur = None
    return [" ".join(x) for x in out]


FRAME = {
 "competitor-c": dict(
  eyebrow=["AdPlexity Social API + live page capture", "competitor-c.example", "swept 20 August 2026", "837 live creatives in a 30-day window"],
  standfirst="837 live creatives and <strong>162 copy blocks, 70 of them with a single creative.</strong> They write, ship, read and discard, mostly in statics (681 static against 156 video). The widest page estate in the library: 30 landing pages, one per persona and per endorser, and a mother watching her teenager is a different buyer from the teenager. Their claims are the most exposed in the set.",
  metrics=[("837","live creatives"),("162","copy blocks, 70 with one creative"),("81%","static (681 of 837)"),("30","landing pages, one per persona"),("461","variants on the most-cloned block, LOW STOCK WARNING")],
  hot=1,
  volume_intro="Ranked by creatives per copy block. The head is short, and the tail is long: most copy got one creative and one read.",
  funnel_intro="The 30 landing pages the 162 blocks send to, captured live at 390pt wide. Long-scroll pages: median 26,790px, tallest 45,667px.",
  wall_intro="Every block with 7 or more creatives, sampled evenly. Click any still to open the ad.",
  swipe_intro="All 162 blocks verbatim, as they run. Copy lifts the block to your clipboard.",
  footer=[f"Pulled 20 August 2026 from AdPlexity Social, advertiser sweep of <code>competitor-c.example</code>, 30-day window (~__ credits). Raw in <code>competitor-c/_raw/</code>, media on Drive at <code>{swipe_home.label('paid', 'competitor-c')}/</code>.",
          "The findings, offer, stack, take and beat are lifted from <code>teardown.md</code>, written when the sweep was pulled. This page was built from them on 21 September 2026, so it carries no newer read.",
          "Nothing here is spend data. Clone counts are the heat the tool reports."]),
 "competitor-b": dict(
  eyebrow=["AdPlexity Social API + live page capture", "competitor-b.example", "swept 20 August 2026", "463 creatives: the 20 August sweep plus a 24 August delta"],
  standfirst="463 creatives on 35 copy blocks (407 on 34 in the 20 August sweep, 56 more from a 24 August delta), and <strong>three blocks carry 83% of the brand</strong> in the August read. They sell anti-aging to men, and the quiz is the whole mid and bottom funnel: 22 steps that diagnose, prove and close, so the ads only have to interrupt. Italian copy is the test market and English the scale market.",
  metrics=[("463","creatives (407 + 56 from the 24 Aug delta)"),("35","copy blocks"),("83%","of the brand on three blocks"),("4 of 4","landing pages are quizzes"),("91%","of ad weight is top-of-funnel")],
  hot=2,
  volume_intro="Ranked by creatives per copy block. Three blocks are most of the library.",
  funnel_intro="The four landing pages, all quiz variants on the same subdomain, captured at the first screen at 390pt wide. There is no product page in the ad-facing funnel.",
  wall_intro="Every block with 7 or more creatives, sampled evenly. Click any still to open the ad.",
  swipe_intro="All 35 copy blocks verbatim, as they run. Copy lifts the block to your clipboard.",
  footer=[f"Pulled 20 August 2026 from AdPlexity Social, advertiser sweep of <code>competitor-b.example</code>, 30-day window. Raw in <code>competitor-b/_raw/</code>, media on Drive at <code>{swipe_home.label('paid', 'competitor-b')}/</code>.",
          "The findings, offer, stack, take and beat are lifted from <code>teardown.md</code>, written when the sweep was pulled. This page was built from them on 21 September 2026. The quiz pages were captured at their first screen; the quiz steps described are from that write-up.",
          "Nothing here is spend data. Clone counts are the heat the tool reports."]),
 "competitor-a": dict(
  eyebrow=["AdPlexity Social API + live page capture", "competitor-a.example", "swept 19 August, refreshed 21 September 2026", "1,830 creatives across both pulls"],
  standfirst="Two pulls, one file: 830 ads on 18 copy blocks in August, and the newest 1,000 in September, which added <strong>12 new copy blocks and no repeated ad ids</strong> (1,830 across 30). The model is unchanged and bigger: copy is a locked asset and the creative is the variable, with the viral foundation block at 924 ads. The lip stain went quiet, and the same claims came back with the number swapped (52 to 47, 50+ to 53+, 1.5M women 40+).",
  metrics=[("1,830","creatives in the file (830 + 1,000)"),("30","copy blocks (18 + 12 new)"),("924","ads on the viral foundation block, up from 332"),("0","old ad ids in the new pull"),("358","of the new 1,000 run under other page names")],
  hot=2,
  volume_intro="Ranked by creatives per copy block across both pulls. Old blocks keep their numbers; blocks 19–30 are new in September.",
  funnel_intro="Every landing page captured, at 390pt wide, from both pulls. The August captures of the older pages sit beside the newer ones on Drive in a dated folder.",
  wall_intro="Every block with 7 or more creatives, sampled evenly across both pulls. Click any still to open the ad.",
  swipe_intro="All 30 copy blocks verbatim. Blocks 1–18 are the August read, 19–30 are new.",
  footer=[f"First pulled 19 August 2026 (830 ads, ~__ credits) and refreshed 21 September 2026 (newest 1,000 ads, __ credits, plus 12 landing-page lookups). The September pull stopped at 1,000 and the library runs past that, so the newest numbers are a floor. Raw in <code>competitor-a/_raw/</code>, media on Drive at <code>{swipe_home.label('paid', 'competitor-a')}/</code>.",
          "The August findings, offer, stack, take and beat are lifted from <code>teardown.md</code> and have not been re-read against the 12 new blocks. The September changes are the first block of findings. The original August page is kept as <code>teardown-2026-08-19.html</code>.",
          "Nothing here is spend data. Clone counts and first-seen dates are what the tool reports."]),
}


def main(brand):
    f = FRAME[brand]
    md = open(os.path.join(HERE, brand, "teardown.md")).read()
    finds = [inline(x) for x in numbered(section(md, "Structural findings"))]
    upd = section(md, "Update")
    new = [inline(x) for x in bullets(section("## x\n" + upd.split("### What changed")[-1].split("### What is still open")[0], "x"))] if "### What changed" in upd else []
    model_src = re.search(r"\*\*Their whole model in one line:\*\*\s*(.+)", md)
    if brand == "competitor-a" and model_src:
        model = "<p>" + inline("**Their whole model in one line:** " + model_src.group(1)) + "</p>"
        findings = ["<i>September 2026 ·</i> " + x for x in new] + ["<i>August 2026 ·</i> " + x for x in finds]
    else:
        model = "<p>" + finds[0] + "</p>"
        findings = finds[1:]
    take_beat = section(md, "What to take, and what to beat")
    tk = re.split(r"\*\*Beat:\*\*", take_beat)
    take = [inline(x) for x in bullets(tk[0])]
    beat = [inline(x) for x in bullets(tk[1])] if len(tk) > 1 else []
    panels = []
    for title, lab in (("Offer mechanics", "How the offer is built"), ("Their stack", "The stack")):
        b = [inline(x) for x in bullets(section(md, title))]
        if b:
            panels.append({"h": lab, "items": b})
    c = {"title": f"{brand.capitalize()} Teardown" if brand != "competitor-b" else "the competitor Lab Teardown",
         "h1": {"competitor-c": "Competitor C, taken apart", "competitor-b": "the competitor Lab, taken apart", "competitor-a": "Competitor A, taken apart"}[brand],
         "eyebrow": f["eyebrow"], "standfirst": f["standfirst"],
         "toc": [["model", "The model"], ["findings", "Findings"], ["volume", "Volume"], ["map", "Angle → page"],
                 ["pages", "The funnel"], ["wall", "Creative wall"], ["stack", "Offer + stack"],
                 ["swipe", "Swipe file"], ["tb", "Take / beat"]],
         "metrics": [{"v": v, "k": k, **({"hot": True} if i == f["hot"] else {})} for i, (v, k) in enumerate(f["metrics"])],
         "model": model, "findings": [{"text": x} for x in findings],
         "volume_intro": f["volume_intro"], "funnel_intro": f["funnel_intro"], "pages": [],
         "wall_intro": f["wall_intro"], "panels": panels, "swipe_intro": f["swipe_intro"],
         "take": take, "beat": beat, "footer": f["footer"]}
    json.dump(c, open(os.path.join(HERE, brand, "teardown-content.json"), "w"), indent=1, ensure_ascii=False)
    print(brand, len(findings), "findings,", len(take), "take,", len(beat), "beat,", len(panels), "panels")


if __name__ == "__main__":
    main(sys.argv[1])
