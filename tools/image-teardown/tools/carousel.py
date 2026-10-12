#!/usr/bin/env python3
"""The carousel road — a carousel swipe to a finished carousel, in one command.

    chain.py carousel --brand brand-b --product gadget --run <run> --links <catalog link id>
    chain.py carousel --brand brand-b --product gadget --avatar avatar-one --file s1.jpg --file s2.jpg …
    … --dry-run       what it would make and how many pictures it would buy; spends nothing
    … --rounds N      rounds before the best roll ships flagged (default: the draft standard's)
    … --swipe-for 7=8 our slide 7 is judged against the swipe's slide 8 (the brief dropped one)

the owner, 2026-10-02: "a cleaner process … most stuff is always a swipe in some
capacity, and we just recreate. All images AI, carousel AI." A carousel is an
image ad with an order (WORK-QUEUE-damon.md, "Carousel, the clean way"). It
uses the same swipe, teardown, brief, hand-off and delivery as the image lane;
only the brief and the slides differ. Every step is a tool that already
existed — this file only runs them in order and files what they make:

  1 teardown + AI sequence brief   the chain's own stages (run.py) — only when --file opens a new run
  2 the brief number               per brand + product, filed as `sequence-ai`, so the
                                   work queue shows it as a carousel row for the designer
  3 slide one                      THE DRAFT STANDARD (DRAFT-STANDARD.md), unchanged: rolls with
                                   the swipe's first slide as the reference, every roll judged,
                                   the best passing one kept; after the rounds, the best roll
                                   ships flagged with what it failed
  4 slides two onward              each the brief's ONE change off slide one (tools/image-edit,
                                   kind `slide`, the slide's words carried verbatim), judged twice:
                                   against slide one for the thread (the compare judge) and against
                                   the swipe's own slide (the draft judge — slide one's prompt)
  5 in order                       runs/image-edit/<brand>/<run>--carousel/: sequence.json, every
                                   verdict, and sheet.png (the swipe's slides over ours)
  6 the designer's copy            deliverable/carousel-prompts.md in the brief's record: every
                                   slide's prompt as sent, so "pull briefs" in Higgsfield makes the
                                   same carousel by hand
  7 delivered                      brands/<brand>/briefs/delivered/<unit>/<unit>_asset-NN.png on the
                                   Drive ($SHARED_ASSETS) — the queue reads it as Delivered
  8 the card                       meta/<brand>/1-check/carousel/<unit>/ ($META_CARDS_ROOT): format
                                   carousel, the brief's own words, the landing page

Nothing reaches Meta: the card waits for the owner's approve.
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import paths as P                      # noqa: E402
import briefs as B                     # noqa: E402
import draft as DR                     # noqa: E402  the standard's own rolls, rounds and loop helpers
import gpt_drafts as F                 # noqa: E402
import draft_judge as J                # noqa: E402
import it_keys                         # noqa: E402  every key by NAME through components/keys — SI-194 (readers use loader)

REPO = P.REPO
sys.path.append(str(REPO / "tools/image-edit"))
import image_edit as RE                # noqa: E402
from image_edit import discipline as D, engine as E   # noqa: E402
sys.path.insert(0, str(REPO / "components/meta-upload"))
import feed_carousel as FC             # noqa: E402
import card_words as W                 # noqa: E402
T, N = FC.T, FC.N

SHARED = Path(os.environ.get("SHARED_ASSETS") or T.SHARED)


def say(s=""):
    print(s, flush=True)


# ------------------------------------------------------------------ the run

def open_run(a):
    """The run the carousel is made from: --run, or a new one opened on the
    files and torn down by the chain's own stages (stage 1 reads every slide,
    stage 6 writes the AI sequence brief)."""
    if a.run:
        return a.run
    cmd = [sys.executable, str(ROOT / "chain.py"), "open", "--brand", a.brand, "--form", "sequence"]
    for f in a.file:
        cmd += ["--file", f]
    slug = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
    if a.dry_run:
        return slug
    say(f"── 1 · teardown + AI sequence brief · {slug}")
    cmd = [sys.executable, str(HERE / "run.py"), slug, "all", "--brand", a.brand, "--product", a.product]
    if a.avatar:
        cmd += ["--avatar", a.avatar]
    subprocess.run(cmd, check=False)
    return slug


def swipe_slides(run):
    """{n: the swipe's slide n}, off assets/source-NN.* (the chain copies every
    slide there, in order). source.jpg — what the draft standard reads — is
    slide one; a run filed before that copy existed gets it here."""
    a = P.RUNS / run / "assets"
    got = {int(m.group(1)): p for p in sorted(a.glob("source-*"))
           if (m := re.fullmatch(r"source-(\d+)", p.stem)) and p.suffix.lower() in (".jpg", ".jpeg", ".png")}
    if got and not (a / "source.jpg").is_file():
        shutil.copy(got[min(got)], a / "source.jpg")
    return got


def brief_file(run):
    return P.RUNS / run / "out/06-brief.md"


def register(a, run):
    """The brief number, per brand + product, filed as a sequence."""
    reg = B.load()
    bid, rec = B.open_brief(run, a.brand, reg, a.product, a.avatar, kind="sequence-ai")
    if not str(rec.get("type") or "").startswith("sequence"):
        reg = B.load()
        reg["briefs"][bid]["type"] = "sequence-ai"
        B.save(reg)
        rec = reg["briefs"][bid]
    return bid, rec


def clean_product(brand, product):
    """The draft standard renders our product from its clean picture
    (drafts/<brand>/products/<slug>-tube.png, DRAFT-STANDARD.md: "a clean tube
    picture in drafts/<brand>/products/"). A product whose brand file lists
    only web links gets the brand's own cutout copied there, once."""
    if (F.brand_facts(brand, product).get("views") or []):
        return None
    for name in (f"{product}-cutout.png", f"{product}-upright.png"):
        src = P.BRANDS / brand / "products/images" / name
        if src.is_file():
            dst = ROOT / "drafts" / brand / "products" / f"{product}-tube.png"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
            return dst
    return None


# --------------------------------------------------------------- slide one

def slide_one(a, bid):
    """THE DRAFT STANDARD, as draft.py runs it, for this one brief: three
    rolls a round, every roll judged, the best passing one is the draft;
    after the rounds, the best roll ships flagged. `--rounds` only lowers the
    number of rounds (a spend cap); nothing else here differs from draft.py."""
    # A run stopped part-way picks up its own rolls rather than buying new ones.
    have = sorted((x for x in (ROOT / "drafts" / a.brand).glob("v*")
                   if x.is_dir() and any(x.glob(f"{bid}-roll-*.png"))),
                  key=lambda x: int(x.name[1:]) if x.name[1:].isdigit() else 0)
    out = str(have[-1].relative_to(ROOT)) if have else DR.next_version(a.brand)
    d = ROOT / out
    rounds = a.rounds or DR.ROUNDS
    for rnd in range(1, rounds + 1):
        if (d / f"{bid}-draft.png").is_file():
            break
        if rnd == 1 and have and not (d / "judge.json").is_file():
            say(f"   round 1 · the rolls already made in {out}")
            DR.sh(HERE / "draft_judge.py", "--brand", a.brand, "--dir", out, "--briefs", bid)
            continue
        if rnd > 1 and bid not in DR._left(d):
            break
        say(f"   round {rnd} · {DR.ROLLS} rolls, the swipe's slide 1 as the reference")
        DR.sh(HERE / "gpt_drafts.py", "--brand", a.brand, "--count", str(DR.ROLLS),
              "--match-swipe", "--out", out, "--briefs", bid)
        DR.sh(HERE / "draft_judge.py", "--brand", a.brand, "--dir", out, "--briefs", bid)
        if (d / f"{bid}-draft.png").is_file():
            break
    if not (d / f"{bid}-draft.png").is_file():
        DR.sh(HERE / "draft_judge.py", "--brand", a.brand, "--dir", out, "--briefs", bid, "--best-available")
    judge = json.loads((d / "judge.json").read_text()).get(bid, {}) if (d / "judge.json").is_file() else {}
    flags = json.loads((d / "flags.json").read_text()).get(bid) if (d / "flags.json").is_file() else None
    picked = (flags or {}).get("roll") or J.pick(judge)
    return d / f"{bid}-draft.png", {"dir": str(d), "rolls": len(judge), "picked": picked,
                                     "verdict": judge.get(picked) if picked else None,
                                     "flagged": bool(flags), "failed": (flags or {}).get("failed")}


# ------------------------------------------------------------ slides 2 + on

def steps_for(change):
    """The brief's change as edits. One edit when the guard takes it; else,
    as the guard says, one at a time — each sentence its own edit, in order,
    when every sentence passes alone. None (and why) when it cannot be made."""
    why = D.guard(change, change)
    if not why:
        return [change], None
    parts = [s.strip() for s in re.split(r"(?<=\.)\s+(?=[A-Z])", change) if s.strip()]
    if len(parts) > 1 and all(not D.guard(p, p) for p in parts):
        return parts, None
    return None, why


def pics_for(brand, job, read):
    """The product pictures the draft judge is shown — exactly as draft_judge does."""
    bf = F.brand_facts(brand, job.get("product"))
    products = list(bf.get("views") or []) + [i for _, i in bf.get("range", [])]
    nv = len(bf.get("views") or [])
    n = int(read.get("product_count") or 0) if read.get("product", True) else 0
    return products[:nv] if n == 1 else (products[:nv + n - 1] if n > 1 else [])


def against_swipe(bid, job, swipe, read, words, picture, k):
    """The draft judge, slide one's own prompt, with the swipe's slide as IMAGE 1
    and this slide's words as the only words allowed."""
    j = dict(job)
    j["prompt"] = ("the words this ad carries: " + " ".join(f'"{w}"' for w in words)) if words else ""
    j.update(read=read, swipe_person=read.get("person"), swipe_product=read.get("product", True),
             leave_alone=False)
    _, out = J.judge_brief(bid, j, [Path(picture)], Path(swipe), pics_for(job["brand"], job, read), k)
    v = out.get(Path(picture).name) or {}
    if isinstance(v, list):          # the model now and then wraps its answer in a list
        v = next((x for x in v if isinstance(x, dict)), {})
    return v


def swipe_fails(v):
    return [n for n, x in ((v or {}).get("tests") or {}).items() if (x or ["FAIL"])[0] != "PASS"]


def slide_requests(a, bid, label, root, n, row, picture, rnd, steps):
    words = [str(e.get("text")) for e in row.get("type") or [] if e.get("text")]
    reqs = []
    for i, step in enumerate(steps, 1):
        r = {"brand": a.brand, "picture": str(picture), "change": step, "kind": "slide",
             "keep": list(row.get("keep") or []), "checks": [E.thread_check(n)],
             "label": f"{label}--slide-{n:02d}",
             "out": str(root / f"slide-{n:02d}" / (f"r{rnd}" + (f"-step{i}" if len(steps) > 1 else ""))),
             "count": 1}
        if i == len(steps) and words:
            r["words"] = words
        reqs.append(r)
    return reqs, words


def made_before(req):
    """A step this run already paid for (its edit.json, same picture in,
    same change) is read back, not bought again — a run stopped part-way
    resumes where it stood."""
    f = Path(req["out"]) / "edit.json"
    if not f.is_file():
        return None
    r = json.loads(f.read_text())
    if r.get("state") in ("filed", "held") and r.get("picture") == req["picture"] \
            and r.get("asked", "").startswith(req["change"].rstrip(".")[:60]):
        return r
    return None


def not_kept(er):
    """(why, the picture) for an edit nothing was delivered from: the compare
    judge's reject, else the picture the engine's own gate held (it is kept
    in engine/rejected/ with its reasons) — so a slide always has its best
    roll to ship flagged, the draft standard's rule."""
    rej = er.get("rejected") or []
    if rej:
        return list(rej[0].get("fails") or []), Path(rej[0]["file"])
    eng = Path(er.get("out", "")) / "engine"
    for h in (er.get("engine") or {}).get("held") or []:
        f = eng / "rejected" / h["name"]
        if f.is_file():
            return ["held by the engine's gate: " + "; ".join(x.split(" — ")[-1] for x in h.get("fails") or [])], f
    return ["the engine returned no picture"], None


def later_slides(a, bid, job, rows, swipes, slide1, root, label):
    k = None if a.dry_run else it_keys.key("GEMINI_API_KEY")
    rounds = a.rounds or DR.ROUNDS
    cache_f = ROOT / "drafts" / a.brand / "swipe-subjects.json"
    cache = json.loads(cache_f.read_text()) if cache_f.is_file() else {}
    out = []
    for row in rows:
        n = int(row["slide"])
        m = a.swipe_for.get(n, n)
        swipe = swipes.get(m)
        steps, why = steps_for(str(row["change"]).strip())
        rec = {"slide": n, "swipe_slide": m, "change": row["change"], "steps": steps,
               "delivered": [], "rejected": [], "refused": why, "attempts": []}
        out.append(rec)
        if not steps:
            say(f"   ! slide {n:02d} refused — {why}")
            continue
        if a.dry_run:
            reqs, words = slide_requests(a, bid, label, root, n, row, slide1, 1, steps)
            rec["instructions"] = [RE.resolve(r)["instruction"] for r in reqs]
            say(f"   slide {n:02d} · {len(steps)} edit(s) off slide 1 · words {words} · judged against swipe slide {m}")
            continue
        key = f"{bid}#slide-{m:02d}"
        if swipe and cache.get(key, {}).get("v") != F.READ_VERSION:
            cache[key] = F.read_swipe(swipe, k)
            cache_f.write_text(json.dumps(cache, indent=1))
        read = cache.get(key) or {}
        for rnd in range(1, rounds + 1):
            reqs, words = slide_requests(a, bid, label, root, n, row, slide1, rnd, steps)
            pic, thread_fails, instructions = Path(slide1), [], []
            for r in reqs:
                r["picture"] = str(pic)
                er = made_before(r) or RE.edit(r)
                instructions.append(er.get("instruction"))
                if er.get("refused"):
                    thread_fails.append(f"refused: {er['refused']}")
                    pic = None
                    break
                kept = er.get("delivered") or []
                if kept:
                    pic = Path(kept[0]["file"])
                else:
                    fails, pic = not_kept(er)
                    thread_fails += fails
                    if pic is None:
                        break
            rec["instructions"] = instructions
            if pic is None:
                rec["attempts"].append({"round": rnd, "file": None, "thread": thread_fails})
                continue
            sv = against_swipe(bid, job, swipe, read, words, pic, k) if swipe else {}
            att = {"round": rnd, "file": str(pic), "thread": thread_fails, "swipe": sv,
                   "swipe_fails": swipe_fails(sv) if swipe else []}
            rec["attempts"].append(att)
            mark = "✓" if not thread_fails and not att["swipe_fails"] else "✗"
            say(f"   {mark} slide {n:02d} round {rnd} · thread "
                f"{'held' if not thread_fails else 'MOVED'} · against swipe slide {m}: "
                + (", ".join(att["swipe_fails"]) + " failed" if att["swipe_fails"] else "all passed")
                + (f" · match {sv.get('match')}" if sv.get("match") else ""))
            if not thread_fails and not att["swipe_fails"]:
                break
        made = [x for x in rec["attempts"] if x.get("file")]
        if made:
            # the same rule as slide one: a pass if there is one, else the best
            # roll ships flagged — the thread first, then fewest fails, then match
            best = max(made, key=lambda x: (not x["thread"], -len(x["swipe_fails"]),
                                            (x.get("swipe") or {}).get("match", 0)))
            rec["delivered"] = [best["file"]]
            rec["flagged"] = bool(best["thread"] or best["swipe_fails"])
            rec["failed"] = best["thread"] + best["swipe_fails"]
            rec["rejected"] = [x["file"] for x in made if x is not best]
    return out


# ---------------------------------------------------------------- the words

def card_words(a, rec, job, brief):
    """The card's words, from the brief and never written here: the headlines
    are slide one's words and the brief's alternates, verbatim; primary text
    from the brief's ad-copy block when it carries one, else the copywriter's
    runs for this brief, else none (the card says so)."""
    if a.words:
        return W.from_file(a.words), f"given ({a.words})"
    t = brief.read_text(errors="replace")
    heads = []
    layer = F.type_layer(job) or []
    if layer:
        heads.append(" ".join(str(e["text"]).strip() for e in layer if e.get("text")))
    alt = re.search(r"^## The alternates\s*\n(.*?)(?=^## |\Z)", t, re.S | re.M)
    if alt:
        heads += [x.strip() for x in re.findall(r"`([^`\n]+)`", alt.group(1))]
    primary, src = [], "slide one + the alternates"
    for m in re.finditer(r"```json\s*(\{.*?\})\s*```", t, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("primary_text"):
            primary = [d["primary_text"]] if isinstance(d["primary_text"], str) else list(d["primary_text"])
            heads = list(d.get("headlines") or heads)
            src = "the brief's ad-copy block"
            break
    if not primary:
        w, where = W.for_brief(a.brand, rec["brief"], REPO, a.product)
        if w.get("primary"):
            primary, src = w["primary"], f"copywriter: {where}"
    return {"headlines": list(dict.fromkeys(h for h in heads if h)), "primary": primary,
            "descriptions": []}, src


def landing(a, rec, brief):
    if a.links:
        return a.links
    if rec.get("links"):
        return [x if isinstance(x, str) else x.get("id") for x in rec["links"]]
    m = re.search(r'"landing_page"\s*:\s*"(link_[a-z0-9_-]+)"', brief.read_text(errors="replace"))
    return [m.group(1)] if m else []


# ------------------------------------------------------------- the filings

def sheet(order, swipes, slides, out):
    """The swipe's slides over ours, in order — the picture the owner reads."""
    from PIL import Image, ImageDraw
    H, pad, lab = 480, 12, 36
    cols = []
    for n, f in order:
        s = slides.get(n, {})
        sw = swipes.get(s.get("swipe_slide", n))
        pair = [Image.open(x).convert("RGB") for x in (sw, f) if x and Path(x).is_file()]
        pair = [im.resize((int(im.size[0] * H / im.size[1]), H)) for im in pair]
        cols.append((n, pair, s))
    W_ = sum(max(p.size[0] for p in pair) + pad for _, pair, _ in cols) + pad
    canvas = Image.new("RGB", (W_, 2 * H + 3 * pad + 2 * lab), (245, 242, 236))
    dr = ImageDraw.Draw(canvas)
    x = pad
    for n, pair, s in cols:
        w = max(p.size[0] for p in pair)
        dr.text((x, pad), f"swipe {s.get('swipe_slide', n)}", fill=(60, 60, 60))
        if len(pair) == 2:
            canvas.paste(pair[0], (x, pad + lab))
        canvas.paste(pair[-1], (x, 2 * pad + lab + H + lab))
        mark = "FLAGGED: " + ", ".join(x.split(" — ")[0] for x in s.get("failed") or [])[:60] \
            if s.get("flagged") else "passed"
        dr.text((x, 2 * pad + H + lab + 4), f"ours {n} · {mark}", fill=(150, 30, 30) if s.get("flagged") else (20, 110, 60))
        x += w + pad
    canvas.save(out)
    return out


def designer_prompts(a, bid, rec, job, slide1_info, slides):
    """Every slide's prompt as it was sent, into the brief's record, so the
    package the queue ships carries it: the designer's "pull briefs" in
    Higgsfield makes the same carousel by hand."""
    d = B.RUNS / a.brand / rec["run"] / "deliverable"
    if not d.parent.is_dir():
        return None
    d.mkdir(exist_ok=True)
    jj = dict(job)
    reads = json.loads((ROOT / "drafts" / a.brand / "swipe-subjects.json").read_text()) \
        if (ROOT / "drafts" / a.brand / "swipe-subjects.json").is_file() else {}
    jj["read"] = reads.get(bid) or {}
    try:
        prompt, refs, used = F.assemble(jj)
    except Exception as e:                       # noqa: BLE001
        prompt, used = f"(could not assemble: {e})", []
    L = [f"# {bid} — the carousel, slide by slide", "",
         "In Higgsfield: Image → GPT Image 2.5 → 9:16. Slide 1 first; every later slide is an",
         "EDIT of slide 1 (attach slide 1, paste its prompt), never a fresh picture.", "",
         "## Slide 1 — the draft standard", "",
         "Attach in this order: " + ", ".join(f"{i}. {u}" for i, u in enumerate(used, 1)), "",
         "```", prompt or "", "```", ""]
    for s in slides:
        L += [f"## Slide {s['slide']} — one change off slide 1"
              + (f" (judged against the swipe's slide {s['swipe_slide']})" if s.get("swipe_slide") else ""), ""]
        if s.get("refused"):
            L += [f"Not made by the machine: {s['refused']}", ""]
            continue
        for i, ins in enumerate(s.get("instructions") or [], 1):
            if len(s.get("instructions") or []) > 1:
                L.append(f"Edit {i} of {len(s['instructions'])} (each off the one before):")
            L += ["", "```", ins or "", "```", ""]
    f = d / "carousel-prompts.md"
    f.write_text("\n".join(L))
    return f


def deliver(a, rec, unit, order):
    """The finished slides into the brand's delivered/ folder, already in the
    delivery rule's own short naming, so the hourly rule leaves them alone and
    the queue reads the row as Delivered."""
    folder = SHARED / "brands" / a.brand / "briefs"
    if not folder.is_dir():
        return None, f"no briefs folder at {folder} — delivery skipped"
    from PIL import Image
    dd = folder / "delivered" / unit
    dd.mkdir(parents=True, exist_ok=True)
    for n, f in order:
        dst = dd / f"{N.short_file(unit, n)}.png"
        with Image.open(f) as im:
            im.save(dst, "PNG")
    (dd / "naming.json").write_text(json.dumps({"brief": rec["brief"], "unit": unit, "folder_was": None,
                                                "made_by": "image-teardown chain.py carousel",
                                                "run": rec["run"]}, indent=1))
    return dd, None


# ----------------------------------------------------------------- the road

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--product", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--run", help="a run already torn down (its AI sequence brief written)")
    ap.add_argument("--file", action="append", help="the swipe's slides, in order — opens and tears down a new run")
    ap.add_argument("--links", nargs="*", help="landing page(s), catalog link ids (default: the brief's)")
    ap.add_argument("--words", help="words.json for the card (default: from the brief)")
    ap.add_argument("--rounds", type=int, help=f"rounds before the best ships flagged (default {DR.ROUNDS})")
    ap.add_argument("--swipe-for", action="append", default=[], metavar="N=M",
                    help="judge our slide N against the swipe's slide M")
    ap.add_argument("--no-card", action="store_true", help="stop before the delivery and the card")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not (a.run or a.file):
        sys.exit("say --run <run> or --file <slide> … (the swipe's slides, in order)")
    a.swipe_for = {int(x.split("=")[0]): int(x.split("=")[1]) for x in a.swipe_for}

    run = open_run(a)
    swipes = swipe_slides(run)
    brief = brief_file(run)
    if not brief.is_file():
        sys.exit(f"{run} has no AI sequence brief yet (out/06-brief.md)")
    route = json.loads((P.RUNS / run / "vars/route.json").read_text()) \
        if (P.RUNS / run / "vars/route.json").is_file() else {}
    if route.get("form") != "sequence":
        sys.exit(f"{run} is not a sequence (vars/route.json) — a single still goes through chain.py draft")
    rows = RE.deltas_from(str(brief))
    say(f"carousel · {a.brand} {a.product} · {run} · {1 + len(rows)} slides, swipe has {len(swipes)}")

    if a.dry_run:
        reg = B.load()
        bid = next((b for b, r in reg["briefs"].items() if r.get("run") == run), "(new number)")
        rounds = a.rounds or DR.ROUNDS
        say(f"── 2 · brief {bid} (sequence-ai)")
        say(f"── 3 · slide 1 · the draft standard · up to {rounds} round(s) of {DR.ROLLS} rolls")
        label = f"{run}--carousel"
        root = E.P.runs(a.brand, label)
        made = later_slides(a, bid, {"brand": a.brand, "product": a.product}, rows, swipes,
                            swipes.get(1) or brief, root, label)
        n_pics = rounds * DR.ROLLS + rounds * sum(len(s["steps"] or []) for s in made)
        say(f"\nat most {n_pics} pictures from GPT Image ({rounds} round(s)); nothing spent")
        return

    say("── 2 · the brief number")
    bid, rec = register(a, run)
    say(f"   {bid} ({rec['brief']}) · sequence-ai — the queue's carousel row once approved")
    cp = clean_product(a.brand, a.product)
    if cp:
        say(f"   the product's clean picture for the standard: {cp.relative_to(ROOT)}")

    say("── 3 · slide 1 · the draft standard")
    subprocess.run([sys.executable, str(ROOT / "chain.py"), "drafts", "--brand", a.brand, "--briefs", bid],
                   check=True, capture_output=True)
    subprocess.run([sys.executable, str(HERE / "worksheet.py"), "--brand", a.brand, "--briefs", bid],
                   cwd=str(ROOT), check=False, capture_output=True)
    slide1, s1 = slide_one(a, bid)
    if not slide1.is_file():
        sys.exit(f"no slide 1 for {bid} — {s1}")
    v = s1.get("verdict") or {}
    s1_fails = swipe_fails(v)
    say(f"   slide 1 = {s1['picked']} of {s1['rolls']} rolls · "
        + ("FLAGGED, failed " + ", ".join(s1_fails) if s1["flagged"] else "passed every test")
        + (f" · match {v.get('match')}" if v.get("match") else ""))

    jobs = json.loads((ROOT / "drafts" / a.brand / "jobs.json").read_text())["jobs"]
    job = next(j for j in jobs if j["brief"] == bid)
    label = f"{run}--carousel"
    root = E.P.runs(a.brand, label)
    root.mkdir(parents=True, exist_ok=True)
    say("── 4 · slides 2+ · one change each off slide 1")
    later = later_slides(a, bid, job, rows, swipes, slide1, root, label)

    slides = {1: {"slide": 1, "swipe_slide": 1, "delivered": [str(slide1)], "flagged": s1["flagged"],
                  "failed": s1_fails, "verdict": v}}
    slides.update({s["slide"]: s for s in later})
    record = {"brand": a.brand, "product": a.product, "brief": rec["brief"], "brief_key": bid, "run": run,
              "slide_one": str(slide1), "slide_one_standard": s1, "label": label, "out": str(root),
              "slides": later, "rounds": a.rounds or DR.ROUNDS,
              "delivered": sum(1 for s in later if s["delivered"]),
              "rejected": sum(len(s["rejected"]) for s in later),
              "refused": sum(1 for s in later if s["refused"]),
              "flagged": [n for n, s in sorted(slides.items()) if s.get("flagged")]}
    E._file_batch(root, record, "sequence.json")
    order, gaps = FC.slides(root)
    say(f"── 5 · in order · {len(order)} slide(s)" + (f" · missing {gaps}" if gaps else ""))
    sh = sheet(order, swipes, slides, root / "sheet.png")
    say(f"   {sh}")
    dp = designer_prompts(a, bid, rec, job, s1, later)
    if dp:
        say(f"── 6 · the designer's copy · {dp.relative_to(REPO)}")
    if gaps or a.no_card:
        say("   not filed: " + (f"slide(s) {gaps} have no picture" if gaps else "--no-card"))
        return

    words, src = card_words(a, rec, job, brief)
    links = landing(a, rec, brief)
    rootp = T.cards_root(None)
    batch = FC.batch_for(rootp, N.slug(a.brand), N.slug(a.product), rec["brief"], FC._rel(root))
    unit = N.short_unit(a.brand, a.product, rec["brief"], batch)
    dd, note = deliver(a, rec, unit, order)
    say(f"── 7 · delivered · {dd or note}")
    p, _ = FC.feed(root, a.brand, a.product, brief=rec["brief"], batch=batch, links=links, words=words)
    say(f"── 8 · the card · words from {src}")
    say("   " + T.show(p).replace("\n", "\n   "))


if __name__ == "__main__":
    main()
