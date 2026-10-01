#!/usr/bin/env python3
"""Judge every roll of a draft against its swipe, keep the best one that passes.

    draft_judge.py --brand <brand> --dir drafts/<brand>/v6
    draft_judge.py --brand <brand> --dir drafts/<brand>/v6 --briefs p143,p158

Damon, 2026-09-17, after the v5 drafts reached him unjudged: a blue tube, a
"DermaWise" tube, Margaret in a golden doodle's pose, a neck-brace man cloned
off the swipe. *"There is product bottle slop, awkward usage of the avatar."*
Every one of those is a checkable fact, and the production flow has had a
judge for exactly this since 2026-09-05 — the drafts just never went through
one. Now they do, before anything reaches him.

For each brief, every `<bid>-roll-N.png` in the folder is put in front of a
vision model with the swipe and the product picture, and answers six tests.
A hedge is a FAIL. The best roll that passes everything becomes
`<bid>-draft.png`; the rest stay as rolls; a brief with no passing roll gets
no draft and a line in `rejects.md` saying why, which is the instruction for
the next run. `judge.json` holds every verdict verbatim.
"""
import argparse, base64, json, mimetypes, re, shutil, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path.home() / ".daemn"))
import paths as P
import briefs as B
import fal_drafts as F
import daemn_keys

ROOT = HERE.parent
BASE = "https://generativelanguage.googleapis.com"
MODEL = "gemini-3.1-pro-preview"

PROMPT_FILE = "stage8-draft-judge-v2-damon.md"


def _load():
    t = re.sub(r"<!--.*?-->\s*", "", (ROOT / "prompts" / PROMPT_FILE).read_text(), flags=re.S)
    tests, rules = t.split("ADULT IN THE SWIPE — ", 1)
    swap, rest = rules.split("\nORGANIC, NO ADULT — ", 1)
    keep, rest = rest.split("\nAD WITH NO PERSON — ", 1)
    prod, rest = rest.split("\nIMAGE 1 shows no product", 1)
    return tests.strip(), swap.strip(), keep.strip(), prod.strip(), \
        "IMAGE 1 shows no product" + rest.strip()


TESTS, SUBJECT_SWAP, SUBJECT_KEEP, SUBJECT_PRODUCT, NO_PRODUCT_RULE = _load()


def part(path: Path):
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return {"inline_data": {"mime_type": mime,
                            "data": base64.b64encode(path.read_bytes()).decode()}}


def ask(images, prompt, k, tries=3):
    parts = []
    for i, p in enumerate(images, 1):
        parts.append({"text": f"IMAGE {i}"})
        parts.append(part(p))
    parts.append({"text": prompt})
    body = json.dumps({"contents": [{"parts": parts}],
                       "generationConfig": {"temperature": 0.1,
                                            "response_mime_type": "application/json"}}).encode()
    last = None
    for n in range(1, tries + 1):
        try:
            req = urllib.request.Request(
                f"{BASE}/v1beta/models/{MODEL}:generateContent?key={k}",
                data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                res = json.load(r)
            txt = "".join(p.get("text", "") for p in
                          res["candidates"][0]["content"]["parts"])
            return json.loads(txt)
        except Exception as e:                      # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            time.sleep(5 * n)
    return {"error": last}


def words_for(job):
    m = re.findall(r'"([^"]+)"', job["prompt"].split("the words this ad carries")[-1]) \
        if "the words this ad carries" in job["prompt"] else []
    m = [w for w in m if not F.NOTE.search(w) and not F.DISCOUNT.search(w)]
    return "; ".join(m) if m else "none — the picture carries no words"


def judge_brief(bid, job, rolls, swipe, products, k, prior=None):
    offer = " · ".join(F.offer_facts(job["brand"], job.get("product"))) or "none"
    if "%" not in offer:
        offer += ". No percentage of any kind is allowed — a percentage anywhere is a FAIL"
    read = job.get("read") or {}
    bf = F.brand_facts(job["brand"], job.get("product"))
    rule = (SUBJECT_KEEP if job.get("leave_alone") else
            SUBJECT_PRODUCT if job.get("swipe_person") is False else SUBJECT_SWAP)
    if not job.get("swipe_product", True):
        rule += " " + NO_PRODUCT_RULE
    prompt = (TESTS.replace("{words}", words_for(job)).replace("{offer}", offer)
              .replace("{subject_rule}", rule)
              .replace("{swipe_read}", json.dumps({k: v for k, v in read.items() if k != "v"}))
              .replace("{accent_name}", bf["accent_name"]).replace("{accent_hex}", bf["accent_hex"])
              .replace("{type_hex}", bf["type_hex"])
              .replace("{swipe_accent}", str(read.get("accent_hex", "unknown")))
              .replace("{treats}", bf["treats"]).replace("{treats_short}", bf["treats_short"]))
    # A verdict, once given, stands. Re-judging a roll flipped p153's roll 6
    # from PASS to FAIL on a second look (2026-09-18) and un-shipped a draft
    # that had passed. Only rolls with no verdict on record are judged.
    out = dict(prior or {})
    for r in rolls:
        if r.name in out and (out[r.name].get("tests") or {}):
            continue
        out[r.name] = ask([swipe] + products + [r], prompt, k)
    return bid, out


def best_available(a):
    """Damon, 2026-09-17: "if a draft didn't make it then you need to
    generate." After the rounds are spent, the best roll ships anyway —
    highest match, then fewest fails — and `flags.json` says what it failed,
    which the board shows beside the picture. Never an empty slot."""
    d = Path(a.dir) if Path(a.dir).is_absolute() else ROOT / a.dir
    verdicts = json.loads((d / "judge.json").read_text()) if (d / "judge.json").is_file() else {}
    flags = json.loads((d / "flags.json").read_text()) if (d / "flags.json").is_file() else {}
    want = {x.strip() for x in a.briefs.split(",")} if a.briefs else set(verdicts)
    for bid in sorted(want):
        if (d / f"{bid}-draft.png").is_file() or bid not in verdicts:
            continue
        best = None
        for name, v in verdicts[bid].items():
            t = v.get("tests") or {}
            if not t or not (d / name).is_file():
                continue
            fails = [n for n, x in t.items() if x[0] != "PASS"]
            key = (-len(fails), v.get("match", 0))
            if best is None or key > best[0]:
                best = (key, name, fails, t)
        if not best:
            print(f"  ! {bid}: no roll on record"); continue
        _, name, fails, t = best
        shutil.copy(d / name, d / f"{bid}-draft.png")
        flags[bid] = {"roll": name, "failed": {n: t[n][1] for n in fails},
                      "rolls_tried": len(verdicts[bid])}
        print(f"  ~ {bid}  {name}  best of {len(verdicts[bid])} · failed {', '.join(fails)}")
    (d / "flags.json").write_text(json.dumps(flags, indent=1, ensure_ascii=False))


def pick(verdicts):
    """The best roll that passes everything; None if none does."""
    ok = []
    for name, v in verdicts.items():
        t = v.get("tests") or {}
        if t and all((x or ["FAIL"])[0] == "PASS" for x in t.values()):
            ok.append((v.get("match", 0), name))
    return max(ok)[1] if ok else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--briefs")
    ap.add_argument("--best-available", action="store_true",
                    help="no new judging: for each brief with no passing roll, ship "
                         "the best roll on record, flagged with what it failed")
    a = ap.parse_args()
    if a.best_available:
        return best_available(a)
    d = Path(a.dir) if Path(a.dir).is_absolute() else ROOT / a.dir
    jobs = {j["brief"]: j for j in
            json.loads((ROOT / "drafts" / a.brand / "jobs.json").read_text())["jobs"]}
    want = {x.strip() for x in a.briefs.split(",")} if a.briefs else set(jobs)
    k = daemn_keys.key("GEMINI_API_KEY")
    subj = F.swipe_has_person(a.brand, list(jobs.values()))
    for bid, j in jobs.items():
        slot = ROOT / "drafts" / a.brand / "slots" / f"{bid}.json"
        kind = json.loads(slot.read_text()).get("swipe_kind", "paid") if slot.is_file() else "paid"
        j["swipe_person"] = subj[bid]["person"]
        j["swipe_product"] = subj[bid].get("product", True)
        j["leave_alone"] = kind == "organic" and not j["swipe_person"]
        j["read"] = subj[bid]

    # the product pictures the generator saw: the clean tube, then the range
    # — per brief, since a variant run carries a different product
    def pics_for(job):
        bf = F.brand_facts(a.brand, job.get("product"))
        return bf, list(bf.get("views") or []) + [i for _, i in bf.get("range", [])]

    work = []
    for bid in sorted(want):
        rolls = sorted(d.glob(f"{bid}-roll-*.png"))
        if not rolls:
            continue
        swipe = P.RUNS / jobs[bid]["run"] / "assets/source.jpg"
        n = int(subj[bid].get("product_count") or 0) if subj[bid].get("product", True) else 0
        # the judge sees the same product pictures the generator saw
        bf, products = pics_for(jobs[bid])
        nv = len(bf.get("views") or [])
        pics = products[:nv] if n == 1 else (products[:nv + n - 1] if n > 1 else [])
        work.append((bid, jobs[bid], rolls, swipe, pics))
    print(f"{len(work)} briefs · {sum(len(w[2]) for w in work)} rolls · {MODEL}\n")

    on_record = json.loads((d / "judge.json").read_text()) if (d / "judge.json").is_file() else {}
    verdicts, kept, rejects = {}, {}, []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(judge_brief, *w, k, on_record.get(w[0])) for w in work]
        for f in as_completed(futs):
            bid, v = f.result()
            verdicts[bid] = v
            best = pick(v)
            if best:
                shutil.copy(d / best, d / f"{bid}-draft.png")
                kept[bid] = best
                print(f"  ✓ {bid}  {best}  match {v[best].get('match')}")
            elif (d / f"{bid}-draft.png").is_file():
                # a draft already picked stays picked
                kept[bid] = "(kept)"
                print(f"  ✓ {bid}  kept")
            else:
                fails = []
                for name, r in v.items():
                    t = r.get("tests") or {}
                    bad = [f"{n}: {x[1]}" for n, x in t.items() if x[0] != "PASS"]
                    fails.append(f"- `{name}` — " + ("; ".join(bad) if bad
                                 else r.get("error") or r.get("note", "?")))
                rejects.append(f"## {bid}\n" + "\n".join(fails))
                print(f"  ✗ {bid}  no roll passed")

    # a partial run (--briefs) updates the set's record rather than replacing it
    prior = json.loads((d / "judge.json").read_text()) if (d / "judge.json").is_file() else {}
    prior.update(verdicts); verdicts = prior
    rejects = []
    for bid in sorted(verdicts):
        if (d / f"{bid}-draft.png").is_file():
            continue
        fails = []
        for name, r in verdicts[bid].items():
            t = r.get("tests") or {}
            bad = [f"{n}: {x[1]}" for n, x in t.items() if x[0] != "PASS"]
            fails.append(f"- `{name}` — " + ("; ".join(bad) if bad
                         else r.get("error") or r.get("note", "?")))
        rejects.append(f"## {bid}\n" + "\n".join(fails))
    (d / "judge.json").write_text(json.dumps(verdicts, indent=1, ensure_ascii=False))
    (d / "rejects.md").write_text(
        "# Rejects — every brief with no passing roll, and why\n\n"
        "Each line is the instruction for the next run: the prompt is what "
        "gets fixed, never the picture.\n\n" + ("\n\n".join(rejects) or "none\n"))
    print(f"\n{len(kept)} of {len(work)} have a draft · {len(rejects)} rejected "
          f"· verdicts in {d.relative_to(ROOT)}/judge.json")


if __name__ == "__main__":
    main()
