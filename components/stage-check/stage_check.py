#!/usr/bin/env python3
"""stage-check — every handoff of a piece of work, checked, verified and fixed, by its brief number.

    python3 stage_check.py <brief id | run>                      check every step, say what is missing
    python3 stage_check.py <brief id | run> --fix                act on each miss, then check again
    python3 stage_check.py <brief id | run> --fix --judge        also judge the written criteria (cheap reader;
                                                                 the 'checks' tier writes the fix note on a fail)
    python3 stage_check.py --batch <file of ids, or ids,comma> [--fix] [--judge]

the owner, 2026-10-25: "anytime we make assets or move one asset from one stage to the next stage there always needs
to be a check or verification ... and something that can actually action on making the update directly ... clear
criteria, and if it's not that, then activate sonnet". The lane's steps, in order, are written down in
`lanes/<lane>.json`: the file that proves each step happened, the checks it must pass, the fix that acts on a miss.
Judged criteria live in `criteria.json`. Nothing here is brand-specific: the brand comes off the brief or the run.

Every check run is written to runs/stage-check/<brand>/<brief or run>/latest.json (and one line per run in
history.jsonl), so the next person, machine or session reads where a piece stands instead of re-deriving it.
"""
import argparse, datetime as dt, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit.paths import repo  # noqa: E402

REPO = repo()
IT = REPO / "tools" / "image-teardown"
REGISTER = IT / "briefs.json"
PY = sys.executable
ANGLE = None                                     # --angle, for a card whose brief has no signed angle


# ---------------------------------------------------------------- the piece

def _teardown_run(repo, run, brand=None):
    """A picture run's folder on the image-teardown plane: runs/image-teardown/<brand>/<run>/, its one home since
    2026-10-28 (components/naming/WHERE-EVERYTHING-GOES-damon.md item 4). The old lane folder
    tools/image-teardown/runs/<run>/ is read for one release, for a checkout that has not moved its runs."""
    root = Path(repo) / "runs" / "image-teardown"
    run = Path(str(run)).name
    hits = ([root / str(brand).lower() / run] if brand else []) + sorted(root.glob(f"*/{run}"))
    work = [d for d in hits if (d / "out").is_dir() or (d / "vars").is_dir()]
    old = Path(repo) / "tools" / "image-teardown" / "runs" / run
    if work:
        return work[0]
    if old.is_dir():
        return old
    return next((d for d in hits if d.is_dir()), hits[0] if hits else root / "_unfiled" / run)


def _register():
    """The brief register, read safely: another run may be writing it at this very moment (2026-10-25, a read landed
    mid-write and stopped two checks), so a half-written file is read again, never trusted."""
    import time
    for i in range(10):
        try:
            return json.loads(REGISTER.read_text())["briefs"]
        except (ValueError, KeyError):
            time.sleep(1 + i)
    return json.loads(REGISTER.read_text())["briefs"]

class Piece:
    """One piece of work, found from its brief number or its run name."""

    def __init__(self, ref, brand=None, product=None, avatar=None):
        reg = _register()
        self.brief_id, self.rec = None, None
        key = ref.strip()
        if key in reg:
            self.brief_id, self.rec = key, reg[key]
        else:
            m = re.search(r"brief-(\d+)$", key)
            if m:
                hits = [(k, r) for k, r in reg.items() if r.get("brief") == f"brief-{m.group(1)}"
                        and (not brand or r.get("brand") == brand) and (not product or r.get("product") == product)]
                if len(hits) == 1:
                    self.brief_id, self.rec = hits[0]
                elif len(hits) > 1:
                    sys.exit(f"{key} names {len(hits)} briefs; add --brand and --product")
            if not self.rec:
                hit = next(((k, r) for k, r in reg.items() if r.get("run") == key), None)
                if hit:
                    self.brief_id, self.rec = hit
        self.run_name = (self.rec or {}).get("run") or key
        self.lane_run = _teardown_run(REPO, self.run_name, (self.rec or {}).get("brand") or brand)
        if not self.rec and not self.lane_run.is_dir():
            sys.exit(f"no brief and no image-teardown run called {key}")
        self.brand = (self.rec or {}).get("brand") or brand or self._brand_from_run()
        self.product = (self.rec or {}).get("product") or product
        self.avatar = (self.rec or {}).get("avatar") or avatar
        self._given = (brand, product, avatar)
        kind = (self.rec or {}).get("type") or ""
        self.lane = "video" if kind.startswith("video") else ("email" if kind == "email" else "image")
        self.record = REPO / "runs" / "image-teardown" / (self.brand or "_") / self.run_name
        self.pictures = self.record / "pictures"

    def _brand_from_run(self):
        f = self.lane_run / "vars" / "brand_name.md"
        return f.read_text().strip().lower() if f.is_file() else None

    @property
    def label(self):
        return self.brief_id or self.run_name

    def short(self):
        return (self.rec or {}).get("brief")

    def source(self):
        f = self.lane_run / "assets" / "source.json"
        try:
            return json.loads(f.read_text()) if f.is_file() else {}
        except ValueError:
            return {}

    def source_image(self):
        return next((p for p in (self.lane_run / "assets").glob("source.*")
                     if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)

    def out(self, name):
        return self.lane_run / "out" / name

    def places(self):
        """Where each stage of this piece lives, for the lanes whose steps are written as path templates."""
        b, slug = self.brand or "_", Path(self.run_name).name
        pl = {"brand": b, "slug": slug, "brief_key": self.brief_id or ""}
        if self.lane == "video":
            pl["work"] = REPO / "runs/video-teardown/_work" / slug
            pl["writing"] = REPO / "runs/video-writing" / b / slug
            prod = None
            for rj in sorted((REPO / "runs/video-production" / b).glob("*/run.json")):
                try:
                    if f"/{slug}/" in str(json.loads(rj.read_text()).get("brief_from") or ""):
                        prod = rj.parent
                except ValueError:
                    pass
            pl["production"] = prod
            ed = None
            for em in sorted((REPO / "runs/video-edit" / b).glob("*/edit-map.json")) if prod else []:
                try:
                    if Path(json.loads(em.read_text()).get("from_run") or "").resolve() == prod.resolve():
                        ed = em.parent
                except ValueError:
                    pass
            pl["edit"] = ed
        if self.lane == "email":
            run = REPO / self.run_name
            pl["email_run"] = run
            try:
                pl["month"] = (json.loads((run / "run.json").read_text()).get("assignment") or {}).get("send_date", "")[:7]
            except (ValueError, OSError):
                pl["month"] = None
        return pl

    def fill(self, template):
        """A path template with this piece's places; None when a place it names was not found."""
        pl = self.places()
        for k in re.findall(r"\{(\w+)\}", template):
            if not pl.get(k):
                return None, k
        return template.format(**{k: str(v) for k, v in pl.items() if v}), None


# ---------------------------------------------------------------- the checks
# Each check answers (ok, why). A check never fixes; a fix never checks itself — the engine checks again after it.

def _gate(piece, name):
    f = piece.lane_run / "check.json"
    try:
        g = json.loads(f.read_text()).get(name) if f.is_file() else None
    except ValueError:
        g = None
    if not g:
        return False, f"no {name} gate on record"
    return g.get("result") == "pass", "; ".join(g.get("problems") or []) or g.get("result")


def _cards(piece, lane="image"):
    """Every approval card that carries this brief, in any state."""
    sys.path.insert(0, str(REPO / "components" / "meta-upload"))
    import to_check as T
    root = Path(T.cards_root()) / (piece.brand or "_")
    out = []
    for cj in root.glob(f"*/{lane}/*/card.json"):
        try:
            c = json.loads(cj.read_text())
        except ValueError:
            continue
        if piece.short() and c.get("brief_id") == piece.short() and c.get("product") == piece.product:
            out.append((cj.parent, c))
    return out


def check(piece, cid, want=6):
    name, _, arg = cid.partition(":")
    if name in ("file", "glob", "json"):
        spec = arg if name != "json" else arg.rsplit(":", 1)[0]
        path, missing = piece.fill(spec)
        if path is None:
            return False, f"no {missing} found for this piece"
        f = Path(path) if Path(path).is_absolute() else REPO / path
        if name == "file":
            return f.is_file() and f.stat().st_size > 0, (f.name if f.is_file() else f"{f.name} missing")
        if name == "glob":
            hits = sorted(f.parent.glob(f.name))
            return bool(hits), (f"{len(hits)} × {f.name}" if hits else f"no {f.name}")
        key, _, want_v = arg.rsplit(":", 1)[1].partition("=")
        try:
            v = json.loads(f.read_text())
            for k in key.split("."):
                v = v.get(k) if isinstance(v, dict) else None
        except (ValueError, OSError):
            return False, f"{f.name} unreadable or missing"
        if want_v:
            return str(v).lower() == want_v.lower(), f"{key} = {v}"
        return bool(v), f"{key} = {v}" if v else f"no {key} in {f.name}"
    if name == "card":
        live = [(f, c) for f, c in _cards(piece, piece.lane) if not c.get("superseded_by")]
        return bool(live), (", ".join(f"{f.parent.parent.name}/{f.name}" for f, _ in live) if live else "no approval card")
    if name == "source_image":
        p = piece.source_image()
        return bool(p), (p.name if p else "no assets/source.* — the run was never opened on its swipe")
    if name == "source_record":
        s = piece.source()
        return bool(s), (f"swipe {s.get('swipe')} · kind {s.get('swipe_kind', 'unknown')}" if s else "no assets/source.json")
    if name == "stage_file":
        f = piece.out(arg)
        n = f.stat().st_size if f.is_file() else 0
        return n > 300, (f"{arg} · {n:,} bytes" if n else f"{arg} missing")
    if name == "has_words":
        w = piece.lane_run / "vars" / "wordless.md"
        return not w.is_file(), ("the swipe has words" if not w.is_file()
                                 else "the swipe has no words on it: a static from it carries none (pick a captioned post)")
    if name == "gate":
        return _gate(piece, arg)
    if name == "brand_lines":
        f = piece.out("03-injection.md")
        t = f.read_text() if f.is_file() else ""
        miss = [k for k in ("STAYS", "SWAPS", "INJECTED FRAME") if k not in t]
        return not miss, ("STAYS, SWAPS and the injected frame are written" if not miss else "missing: " + ", ".join(miss))
    if name == "dials_floor":
        f = piece.out("03-injection.md")
        if not f.is_file():
            return False, "no brand step"
        sys.path.insert(0, str(REPO / "components" / "creative-controls"))
        import creative_controls as CC
        bad = CC.floor_problems(f.read_text())
        return not bad, ("every dial at or above the floor" if not bad else "; ".join(bad))
    if name == "record_filed":
        f = piece.record / "deliverable" / "06-brief.md"
        return f.is_file(), (str(f.relative_to(REPO)) if f.is_file() else "the brief is not in the run's record yet")
    if name == "brief_number":
        return bool(piece.brief_id), (piece.brief_id or "no brief number for this run")
    if name == "brief_links":
        links = (piece.rec or {}).get("links") or []
        return bool(links), (", ".join(links) if links else "no landing page on the brief")
    if name == "headline_set":
        f = piece.out("04-headlines.md")
        tx = f.read_text() if f.is_file() else ""
        stopped = re.search(r"stage-2 defect|stop here|must be supplied before", tx, re.I)
        return not stopped, ("a full headline set" if not stopped else "the headline stage stopped itself: " + stopped.group(0))
    if name == "variation_set":
        # the variations record (image-writing stage 5): exactly five rows, each one change off the approved picture
        vf = piece.out("variations.json")
        rows = (json.loads(vf.read_text()).get("variations") or []) if vf.is_file() else []
        if rows:
            return len(rows) == 5, f"{len(rows)} of 5 variations written"
        if not approved_picture(piece):
            return False, "the five are written once the first picture is approved"
        return False, "no variations record yet"
    if name == "batch_six":
        n = len(six_pictures(piece))
        return n >= want, (f"{n} of {want}: the approved picture and its variations" if approved_picture(piece)
                           else "no approved first picture yet")
    if name == "picture_variants":
        vf = piece.pictures / "variants.json"
        v = json.loads(vf.read_text()) if vf.is_file() else {}
        live = {k: x for k, x in v.items() if (piece.pictures / k).is_file()}
        pairs = {(x["h"], x["c"]) for x in live.values()}
        return len(pairs) >= want, f"{len(pairs)} of {want} distinct headline × cast versions"
    if name == "picture_count":
        n = len([p for p in piece.pictures.glob("*.png")]) if piece.pictures.is_dir() else 0
        return n >= want, f"{n} of {want}"
    if name == "picture_finish":
        pics = sorted(piece.pictures.glob("*.png")) if piece.pictures.is_dir() else []
        if not pics:
            return False, "no pictures"
        raw = [p.name for p in pics if not (piece.pictures / "polished" / p.name).is_file()]
        return not raw, ("every picture matched to the swipe's fidelity" if not raw else f"{len(raw)} not matched: " + ", ".join(raw[:4]))
    if name == "card_filed":
        live = [(f, c) for f, c in _cards(piece) if not c.get("superseded_by")]
        return bool(live), (", ".join(f"{f.parent.parent.name}/{f.name}" for f, _ in live) if live else "no approval card")
    if name == "card_media":
        live = [(f, c) for f, c in _cards(piece) if not c.get("superseded_by")]
        if not live:
            return False, "no approval card"
        f, c = live[0]
        have = [m for m in c.get("media", []) if (f / m).is_file()]
        return len(have) >= want, f"{len(have)} of {want} pictures on the card"
    if name == "card_checks":
        live = [(f, c) for f, c in _cards(piece) if not c.get("superseded_by")]
        if not live:
            return False, "no approval card"
        ch = live[0][1].get("checks") or {}
        probs = ([f"{k}: {v.get('why')}" for k, v in ch.items() if isinstance(v, dict) and not v.get("ok")]
                 if isinstance(ch, dict) else [p for p in ch if isinstance(p, str)])
        return not probs, ("the card's own checks pass" if not probs else "; ".join(probs[:3]))
    return False, f"unknown check {cid}"


# ---------------------------------------------------------------- the judge

def _evidence(piece, specs):
    parts = []
    for s in specs:
        rel, _, n = s.partition(":")
        f = piece.lane_run / rel
        if f.is_file():
            t = f.read_text(errors="replace")
            parts.append(f"--- {rel} ---\n" + (t[:int(n)] if n else t))
    return "\n\n".join(parts)


def judge(piece, key, model_call=None):
    """(ok, why, failed lines) for one written criteria set, by the cheap reader."""
    from run_kit import model as MD
    crit = json.loads((HERE / "criteria.json").read_text())["criteria"][key]
    lines = "\n".join(f"{i}. {l}" for i, l in enumerate(crit["lines"], 1))
    prompt = ((HERE / "prompts" / "judge-v1-damon.md").read_text()
              .replace("{step}", crit["step"]).replace("{criteria}", lines)
              .replace("{evidence}", _evidence(piece, crit["evidence"])))
    call = model_call or MD.call
    raw = call(prompt, MD.TIERS["reads"], label=f"stage-check-{key}")
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        v = json.loads(m.group(0)) if m else {}
    except ValueError:
        v = {}
    if "pass" not in v:
        return False, "the reader's answer could not be read: " + raw[:160], []
    return bool(v["pass"]), v.get("why") or "", v.get("failed") or []


def fix_note(piece, key, why, model_call=None):
    """The 'checks' tier writes the note a re-make carries, from the failure."""
    from run_kit import model as MD
    crit = json.loads((HERE / "criteria.json").read_text())["criteria"][key]
    prompt = ((HERE / "prompts" / "fix-note-v1-damon.md").read_text()
              .replace("{step}", crit["step"]).replace("{failure}", why)
              .replace("{criteria}", "\n".join(f"- {l}" for l in crit["lines"]))
              .replace("{evidence}", _evidence(piece, crit["evidence"][-1:])))
    return (model_call or MD.call)(prompt, MD.TIERS["checks"], label=f"stage-check-fix-{key}").strip()


# ---------------------------------------------------------------- the fixes

def _sh(cmd):
    if any(x is None for x in cmd):                  # a missing value is a failed fix that says which, never a crash
        return False, "a value the fix needs is missing (argument " + str([i for i, x in enumerate(cmd) if x is None]) + ")"
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, cwd=str(REPO))
    tail = (r.stdout + r.stderr).strip().splitlines()
    return r.returncode == 0, (tail[-1][:200] if tail else "")


def fix(piece, step, note=None, links=None, words=None, want=6, replaces=None):
    """Act on one failed step. Returns (acted, what happened)."""
    kind, _, arg = (step.get("fix") or "").partition(":")
    av = ["--avatar", piece.avatar] if piece.avatar else []
    if kind == "run_stage":
        stages = {"1": "1,2,2b,3,4,5,6", "2": "2,2b,3,4,5,6", "2b": "2b,3,4,5,6", "3": "3,4,5,6",
                  "4": "4,5,6", "5": "5,6", "6": "6"}[arg]
        if note:
            # the viewer-notes hook rides on the end of the stage's prompt for one re-make (image-teardown run.py)
            (piece.lane_run / "vars" / f"viewer-notes-{arg}.md").write_text("THE STAGE CHECK SENT THIS STEP BACK:\n\n" + note + "\n")
        ok, msg = _sh([PY, str(IT / "tools" / "run.py"), piece.run_name, stages, "--brand", piece.brand,
                       "--product", piece.product or ""] + av)
        plan = piece.record / "variants-plan.json"
        if ok and plan.is_file():                       # the six were read off the stages just re-made
            plan.rename(plan.with_name(f"variants-plan.before-{dt.datetime.now():%Y%m%d%H%M%S}.json"))
        if ok and arg in ("1", "2", "2b", "3") and piece.pictures.is_dir() and any(piece.pictures.glob("*.png")):
            # pictures made from the old brand step no longer match it: set aside, never deleted, so the
            # pictures step makes them again from the new one
            old = piece.pictures.parent / f"pictures-before-{dt.datetime.now():%Y%m%d%H%M%S}"
            old.mkdir()
            for p in piece.pictures.glob("*.png"):
                shutil.move(str(p), str(old / p.name))
        if note:
            used = piece.lane_run / "vars" / f"viewer-notes-{arg}.md"
            if used.is_file():
                used.rename(used.with_name(f"viewer-notes-{arg}.used-{dt.datetime.now():%Y%m%d%H%M%S}.md"))
        return ok, (f"re-ran stages {stages}" if ok else f"re-running stages {stages} failed: {msg}")
    if kind == "file_record":
        sys.path.insert(0, str(IT / "tools"))
        import gates as G                      # image-teardown's filer, the one every run files through
        G.file_record(piece.brand, piece.run_name)
        return True, "filed the run's record"
    if kind == "open_brief":
        if piece.brief_id:                             # numbered already: only its pages (and what it replaces) missing
            if not links:
                return False, "the brief has no landing page: pass --links"
            ok, msg = _sh([PY, str(IT / "tools" / "briefs.py"), "link", piece.brief_id] + list(links))
            if ok and replaces:
                mark_replaced(piece.run_name, replaces)
            return ok, msg or "set the brief's landing pages"
        if not (piece.out("06-brief.md")).is_file():
            return False, "no brief to number yet (stage 6 first)"
        cmd = [PY, str(IT / "tools" / "briefs.py"), "open", piece.run_name, "--brand", piece.brand,
               "--product", piece.product or "", "--type", "image-ai"] + av
        for l in links or []:
            cmd += ["--link", l]
        ok, msg = _sh(cmd)
        if ok and replaces:
            mark_replaced(piece.run_name, replaces)
        return ok, msg or "opened the brief"
    if kind == "make_pictures":
        return make_batch(piece, want)
    if kind == "cmd":
        cmdline, missing = piece.fill(step["fix"].split(":", 1)[1])
        if cmdline is None:
            return False, f"no {missing} found to run the fix on"
        import shlex
        parts = shlex.split(cmdline)
        if parts and parts[0] == "python3":
            parts[0] = PY
        ok, msg = _sh(parts)
        return ok, msg or ("ran " + parts[1] if len(parts) > 1 else "ran")
    if kind == "file_card":
        return file_card(piece, words, links, want, angle=ANGLE)
    return False, step.get("why_no_fix") or "no fix for this step"


def mark_replaced(run_name, old_id):
    """The old brief is deprecated and points at the new one; the new one names what it replaced. One trail."""
    sys.path.insert(0, str(IT / "tools"))
    import briefs as B                         # the register's own load/save
    import fcntl, tempfile
    lock = open(Path(tempfile.gettempdir()) / "brief-register.lock", "a")   # the lock briefs.py open/link hold
    fcntl.flock(lock, fcntl.LOCK_EX)
    reg = B.load()
    new = next((k for k, r in reg["briefs"].items() if r.get("run") == run_name), None)
    if not new or old_id not in reg["briefs"] or new == old_id:
        return None
    reg["briefs"][old_id].update({"status": "deprecated", "state": "superseded", "superseded_by": new})
    reg["briefs"][new]["supersedes"] = old_id
    B.save(reg)
    return new


def six_plan(piece, model_call=None):
    """The six: three headlines × two people/scene versions, read off stages 3-5 by the cheap reader. Kept beside
    the pictures (variants-plan.json) so every machine makes the same six."""
    f = piece.record / "variants-plan.json"
    from run_kit import model as MD
    if f.is_file():
        return top_up(piece, json.loads(f.read_text()), f, model_call)
    rd = lambda n, k: (piece.out(n).read_text()[:k] if piece.out(n).is_file() else "")
    prompt = ((HERE / "prompts" / "variants-v1-damon.md").read_text()
              .replace("{injection}", rd("03-injection.md", 6000)).replace("{headlines}", rd("04-headlines.md", 6000))
              .replace("{variations}", rd("05-image-variations.md", 6000)))
    raw = (model_call or MD.call)(prompt, MD.TIERS["reads"], label="stage-check-six")
    m = re.search(r"\{.*\}", raw, re.S)
    plan = json.loads(m.group(0)) if m else {}
    if len(plan.get("headlines") or []) < 1 or len(plan.get("casts") or []) < 1:
        raise ValueError("the six-picture plan could not be read: " + raw[:160])
    piece.record.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    return top_up(piece, plan, f, model_call)


def top_up(piece, plan, f, model_call=None):
    """A plan short of three headlines gets the rest written in the same pattern by the 'checks' tier (a native
    caption often has one line and nothing else to read off); short of two casts, the first is reused with a
    different person of the same avatar. Saved, so every machine makes the same six."""
    from run_kit import model as MD
    hs = [h for h in plan.get("headlines") or [] if h]
    if 0 < len(hs) < 3:
        rd = piece.out("03-injection.md").read_text()[:5000] if piece.out("03-injection.md").is_file() else ""
        prompt = ((HERE / "prompts" / "more-headlines-v1-damon.md").read_text()
                  .replace("{need}", str(3 - len(hs))).replace("{zone}", plan.get("zone") or "the main word zone")
                  .replace("{have}", "\n".join(f"- {h}" for h in hs)).replace("{injection}", rd))
        raw = (model_call or MD.call)(prompt, MD.TIERS["checks"], label="stage-check-headlines")
        m = re.search(r"\[.*\]", raw, re.S)
        try:
            more = [x for x in json.loads(m.group(0)) if isinstance(x, str) and x.strip()] if m else []
        except ValueError:
            more = []
        plan["headlines"] = hs + more[:3 - len(hs)]
        plan["headlines_written_by_check"] = more[:3 - len(hs)]
    cs = [c for c in plan.get("casts") or [] if c]
    if len(cs) == 1:
        plan["casts"] = cs + [cs[0] + " The same scene with a different man of the same avatar: another face, age and build."]
    f.write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    return plan


def approved_picture(piece):
    """The first picture a person approved for this ad (its `.liked.json`), in the board's home or the chain's own
    pictures folder; None before anyone has."""
    homes = [REPO / "runs" / "image-production" / (piece.brand or "_") / "prompt-bench", piece.pictures]
    liked = sorted((f for h in homes if h.is_dir() for f in h.glob(f"{piece.run_name}*.liked.json")),
                   key=lambda f: f.stat().st_mtime)
    if not liked:
        return None
    pic = liked[-1].with_name(liked[-1].name.replace(".liked.json", ".png"))
    return pic if pic.is_file() else None


def batch_dir(piece):
    return REPO / "runs" / "image-edit" / (piece.brand or "_") / f"{piece.run_name}--batch"


def six_pictures(piece):
    """The six, in order (the owner, 2026-10-27: "6 total images in that batch: 5 unique variations from the initial one
    that we made"): the approved picture, then each of the brief's five variations image-edit made from it."""
    first = approved_picture(piece)
    if not first:
        return []
    vf = piece.out("variations.json")
    ids = [v["id"] for v in (json.loads(vf.read_text()).get("variations") or [])] if vf.is_file() else []
    made = [next(iter(sorted((batch_dir(piece) / i).glob(f"*--{i}.png"))), None) for i in ids]
    return [first] + [m for m in made if m]


def make_batch(piece, want=6):
    """The pictures step, the board's own order: one first picture (the chain's picture step), then a person's look
    (Looks good on the board), then the brief's five variations off it (image-edit). Never a set remade from the swipe."""
    first = approved_picture(piece)
    if not first:
        if not (piece.pictures.is_dir() and any(piece.pictures.glob("*.png"))):
            ok, msg = _sh([PY, str(IT / "tools" / "pictures.py"), piece.run_name, "--brand", piece.brand,
                           "--product", piece.product or "", "--count", "1"])
            if not ok:
                return False, msg or "the first picture could not be made"
        return False, "the first picture waits for a person's look (Looks good on the board); the 5 come from it"
    vf = piece.out("variations.json")
    if not vf.is_file():
        ok, msg = _sh([PY, str(REPO / "tools" / "image-writing" / "run.py"), piece.run_name, "5", "--brand",
                       piece.brand, "--product", piece.product or ""])
        if not ok or not vf.is_file():
            return False, msg or "the five variations could not be written"
    if len(six_pictures(piece)) < want:
        ok, msg = _sh([PY, str(REPO / "tools" / "image-edit" / "vary.py"), str(first), "--brand", piece.brand,
                       "--from-brief", str(vf), "--label", f"{piece.run_name}--batch"])
        if not ok:
            return False, msg or "the variations could not be made"
    have = len(six_pictures(piece))
    return have >= want, f"{have} of {want}: the approved picture and its variations"


def make_six(piece, want=6, model_call=None):
    """Every concept ships as six (the owner, 2026-10-25): each headline × each people/scene version, one picture each,
    retried until it lands. Pictures that are not part of the set are set aside, never deleted."""
    try:
        plan = six_plan(piece, model_call)
    except ValueError as e:
        return False, str(e)
    hs, cs = plan["headlines"][:3], plan["casts"][:2]
    combos = [(h, c) for c in cs for h in hs][:want]
    piece.pictures.mkdir(parents=True, exist_ok=True)
    vf = piece.pictures / "variants.json"
    v = json.loads(vf.read_text()) if vf.is_file() else {}
    loose = [p for p in piece.pictures.glob("*.png") if p.name not in v]
    if loose:
        old = piece.pictures.parent / f"pictures-before-{dt.datetime.now():%Y%m%d%H%M%S}"
        old.mkdir()
        for p in loose:
            shutil.move(str(p), str(old / p.name))
    made = 0
    for i, (h, c) in enumerate(combos, 1):
        if any(x["h"] == h and x["c"] == c and (piece.pictures / k).is_file() for k, x in v.items()):
            continue
        last = ""
        for attempt in range(5):
            before = set(piece.pictures.glob("*.png"))
            note = (f"THIS VERSION ({i} of {len(combos)}): the words in {plan.get('zone') or 'the main word zone'} read exactly "
                    f"\"{h}\" and nothing else changes in the words. The people and scene: {c}"
                    + (f" THE LAST TRY WAS HELD FOR THIS, FIX IT: {last}" if last else ""))
            seen = set((piece.pictures / "rejected").glob("*-why.md")) if (piece.pictures / "rejected").is_dir() else set()
            _sh([PY, str(IT / "tools" / "pictures.py"), piece.run_name, "--brand", piece.brand, "--product", piece.product or "",
                 "--count", "1", "--round", str(20 + i * 3 + attempt), "--note", note])
            new = sorted(set(piece.pictures.glob("*.png")) - before)
            held = sorted(set((piece.pictures / "rejected").glob("*-why.md")) - seen) if (piece.pictures / "rejected").is_dir() else []
            if held and not new:                       # the next try carries the reason this one was held
                why = next((l[2:] for l in held[-1].read_text().splitlines() if l.startswith("- ")), "")
                last = (why.split(" — ", 1)[-1] if " — " in why else why)[:300]
            if new:
                v[new[0].name] = {"h": h, "c": c}
                vf.write_text(json.dumps(v, indent=1, ensure_ascii=False))
                made += 1
                break
    have = len({(x["h"], x["c"]) for k, x in v.items() if (piece.pictures / k).is_file()})
    return have >= min(want, len(combos)), f"{made} new; {have} of {len(combos)} versions"


def review_sheet(pieces, brand):
    """The end-of-batch review: each piece's real post, then its pictures, one row each, with where it stands."""
    from PIL import Image, ImageDraw
    H, rows = 300, []
    for p in pieces:
        src = p.source_image()
        pics = sorted(p.pictures.glob("*.png"))[:6] if p.pictures.is_dir() else []
        ims = ([Image.open(src).convert("RGB")] if src else []) + [Image.open(x).convert("RGB") for x in pics]
        for im in ims:
            im.thumbnail((400, H))
        rows.append((p, ims, len(pics)))
    W = max([sum(i.width + 6 for i in ims) for _, ims, _ in rows] + [600])
    sheet = Image.new("RGB", (W, len(rows) * (H + 24)), "white")
    d = ImageDraw.Draw(sheet)
    for r, (p, ims, n) in enumerate(rows):
        rec = json.loads((REPO / "runs/stage-check" / (p.brand or "_") / p.label / "latest.json").read_text())
        d.text((4, r * (H + 24) + 5), f"{p.label}  ·  {n} pictures  ·  {'ready' if rec['next'] == 'done' else 'stops at: ' + rec['next']}"
               + "   (first = the real post)", fill="black")
        x = 0
        for im in ims:
            sheet.paste(im, (x, r * (H + 24) + 22)); x += im.width + 6
    out = REPO / "runs/stage-check" / (brand or "_") / "_batches" / f"{dt.datetime.now():%Y-%m-%d-%H%M}"
    out.mkdir(parents=True, exist_ok=True)
    sheet.save(out / "review.jpg", quality=82)
    (out / "summary.md").write_text("\n".join(
        [f"# Batch check {out.name}", ""] + [f"- **{p.label}** ({p.run_name}): {n} pictures, "
         + json.loads((REPO / 'runs/stage-check' / (p.brand or '_') / p.label / 'latest.json').read_text())['next'] for p, _, n in rows]) + "\n")
    return out


def passed_card(c):
    ch = c.get("checks") or {}
    return isinstance(ch, dict) and bool(ch) and all(isinstance(v, dict) and v.get("ok") for v in ch.values())


def signed_angle(piece):
    """The angle the brief declared, when it is one the brand signed active (brands/<brand>/strategy/angles.json);
    a card with no angle has no ad set."""
    f = REPO / "brands" / (piece.brand or "_") / "strategy" / "angles.json"
    try:
        a = json.loads(f.read_text())
    except (ValueError, OSError):
        return None
    active = {re.sub(r"[^a-z0-9]", "", x.get("id", "")): x["id"] for x in (a.get("angles", a) if isinstance(a, dict) else a)
              if isinstance(x, dict) and x.get("status") == "active" and x.get("id")}
    said = re.sub(r"[^a-z0-9]", "", str(((piece.rec or {}).get("declares") or {}).get("angle") or ""))
    return active.get(said)


def file_card(piece, words=None, links=None, want=6, angle=None):
    """The pictures onto an approval card under this brief, through meta-upload's one card writer. Words come from
    --words, else the card of the brief this one replaces (same concept, same audience). A replaced brief's card is
    marked superseded_by so the Approve list stops showing it; nothing is deleted."""
    pics = six_pictures(piece)[:want]
    if len(pics) < want:
        return False, f"the card waits for all {want} pictures ({len(pics)} so far)"
    if not piece.short():
        return False, "no brief number to file the card under"
    short_card = any(len(c.get("media") or []) < want for _, c in _cards(piece) if not c.get("superseded_by"))
    old = (piece.rec or {}).get("supersedes")
    old_cards = []
    if old:
        op = Piece(old)
        old_cards = [(f, c) for f, c in _cards(op) if not c.get("superseded_by")]
    if not words and old_cards:
        tmp = piece.record / "card-words.json"
        tmp.write_text(json.dumps(old_cards[0][1].get("words") or {}, indent=1))
        words = str(tmp)
    if not words:
        return False, "no words for the card: pass --words (a words.json or a copywriter run)"
    links = links or (piece.rec or {}).get("links") or []
    angle = angle or next((c.get("angle") for _, c in old_cards if c.get("angle")), None) or signed_angle(piece)
    cmd = [PY, str(REPO / "components" / "meta-upload" / "to_check.py"), "--brand", piece.brand, "--lane", "image",
           "--product", piece.product or "", "--brief", piece.short(), "--batch", f"batch-{dt.date.today()}-a",
           "--tool", "image-teardown", "--run", piece.run_name, "--words", words, "--media"] + [str(p) for p in pics]
    if piece.avatar:
        cmd += ["--avatar", piece.avatar]
    if links:
        cmd += ["--links"] + links
    if angle:
        cmd += ["--angle", angle]
    bad_card = any(not passed_card(c) for _, c in _cards(piece) if not c.get("superseded_by"))
    if short_card or bad_card:
        cmd.append("--replace")                     # same folder, same link, now with the whole set
    ok, msg = _sh(cmd)
    if ok:
        for f, c in old_cards:
            c["superseded_by"] = piece.brief_id
            c.setdefault("history", []).append({"at": dt.datetime.now().isoformat(timespec="seconds"),
                                                "what": "superseded", "by": piece.brief_id})
            (f / "card.json").write_text(json.dumps(c, indent=1, ensure_ascii=False))
    return ok, msg or "filed the card"


# ---------------------------------------------------------------- the run

def lane(name="image"):
    return json.loads((HERE / "lanes" / f"{name}.json").read_text())


def check_piece(piece, do_fix=False, do_judge=False, want=6, links=None, words=None, model_call=None, quiet=False,
                replaces=None):
    rows = []
    if (piece.rec or {}).get("superseded_by"):
        by = piece.rec["superseded_by"]
        if not quiet:
            print(f"  · replaced by {by}: check that one")
        write_record(piece, [{"step": "replaced", "name": "replaced", "ok": True, "why": f"replaced by {by}",
                              "judged": None, "note": None, "fixed": None}])
        return rows
    if replaces and piece.brief_id and do_fix:
        mark_replaced(piece.run_name, replaces)        # one trail, whichever pass numbered the brief
    blocked = None
    for step in lane(piece.lane)["steps"]:
        results = [(c, *check(piece, c, want)) for c in step["checks"]]
        ok = all(r[1] for r in results)
        why = " · ".join(dict.fromkeys(r[2] for r in results if not r[1])) or results[-1][2]
        judged, note = None, None
        if ok and do_judge and step.get("judge"):
            jok, jwhy, _ = judge(piece, step["judge"], model_call)
            judged = {"pass": jok, "why": jwhy}
            if not jok:
                ok, why = False, "criteria: " + jwhy
                if do_fix:
                    note = fix_note(piece, step["judge"], jwhy, model_call)
        acted = None
        soft = step["id"] == "format" and results[0][1]      # a wordless swipe is said loudly, never rebuilt
        if not ok and do_fix and not soft and blocked:
            why = why + f" · not fixed: waiting on {blocked}"
        elif not ok and do_fix and not soft:
            did, what = fix(piece, step, note=note, links=links, words=words, want=want, replaces=replaces)
            if did:
                piece.__init__(piece.run_name, *piece._given)              # the fix may have numbered or moved it
                results = [(c, *check(piece, c, want)) for c in step["checks"]]
                ok = all(r[1] for r in results)
                why = " · ".join(dict.fromkeys(r[2] for r in results if not r[1])) or results[-1][2]
                if ok and do_judge and step.get("judge"):
                    jok, jwhy, _ = judge(piece, step["judge"], model_call)
                    judged = {"pass": jok, "why": jwhy, "after_fix": True}
                    if not jok:
                        ok, why = False, "criteria, after the fix: " + jwhy
            else:
                ok = False
                why = why + " · fix failed: " + what
            acted = what
        if not ok and not soft and step.get("fix") and not blocked:
            blocked = step["name"]
        rows.append({"step": step["id"], "name": step["name"], "ok": ok, "why": why, "judged": judged,
                     "note": note, "fixed": acted})
        if not quiet:
            mark = "✓" if ok else ("·" if soft else "✗")
            print(f"  {mark} {step['name']:<24} {why[:110]}" + (f"\n      fix: {acted[:110]}" if acted else ""))
    write_record(piece, rows)
    return rows


def write_record(piece, rows):
    d = REPO / "runs" / "stage-check" / (piece.brand or "_") / piece.label
    d.mkdir(parents=True, exist_ok=True)
    rec = {"piece": piece.label, "brief": piece.brief_id, "run": piece.run_name, "brand": piece.brand,
           "product": piece.product, "at": dt.datetime.now().isoformat(timespec="seconds"),
           "next": next((r["name"] for r in rows if not r["ok"]), "done"), "steps": rows}
    (d / "latest.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    with open(d / "history.jsonl", "a") as h:
        h.write(json.dumps({"at": rec["at"], "next": rec["next"],
                            "fails": [r["step"] for r in rows if not r["ok"]]}) + "\n")
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ref", nargs="?", help="a brief id (brand_a_flex_brief-0243, or brief-0243 with --brand/--product) or a run name")
    ap.add_argument("--batch", help="several refs: a file with one per line, or comma-separated")
    ap.add_argument("--brand"); ap.add_argument("--product")
    ap.add_argument("--review", action="store_true", help="write the batch review sheet even for one piece")
    ap.add_argument("--avatar", help="the core avatar, for a run that has no brief number yet")
    ap.add_argument("--fix", action="store_true", help="act on every miss, then check that step again")
    ap.add_argument("--judge", action="store_true", help="also judge the written criteria (cheap reader; a fail gets a fix note)")
    ap.add_argument("--want", type=int, default=6, help="pictures a concept ships with (default 6)")
    ap.add_argument("--links", nargs="*", help="landing pages for a brief that has none")
    ap.add_argument("--angle", help="the signed angle for the card, when the brief carries none (ads without an angle have no ad set)")
    ap.add_argument("--replaces", help="the brief this run replaces (it is marked deprecated, superseded_by this one; its card leaves the Approve list once this one's card is filed)")
    ap.add_argument("--words", help="words for the card (words.json or a copywriter run), when the replaced brief's card has none")
    a = ap.parse_args()
    global ANGLE
    ANGLE = a.angle
    refs = []
    if a.batch:
        p = Path(a.batch)
        refs = [l.strip() for l in (p.read_text().splitlines() if p.is_file() else a.batch.split(",")) if l.strip()]
    elif a.ref:
        refs = [a.ref]
    else:
        ap.error("name a brief id or run, or --batch")
    bad, done = 0, []
    for r in refs:
        piece = Piece(r, a.brand, a.product, a.avatar)
        print(f"\n{piece.label}  ({piece.run_name})")
        rows = check_piece(piece, a.fix, a.judge, a.want, a.links, a.words, replaces=a.replaces)
        nxt = next((x["name"] for x in rows if not x["ok"] and x["step"] != "format"), None)
        print(f"  → {'every step passes' if not nxt else 'stops at: ' + nxt}")
        bad += bool(nxt)
        done.append(Piece(piece.run_name, a.brand, a.product, a.avatar))
    if len(refs) > 1 or a.review:
        out = review_sheet(done, done[0].brand if done else a.brand)
        print(f"\nreview: {out / 'review.jpg'}\n        {out / 'summary.md'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
