#!/usr/bin/env python3
"""proven_to_format.py — proven ad → new format, one batch at a time (the owner, 5 Oct 2026).

    python3 proven_to_format.py check <batch>            what is broken down, what is missing
    python3 proven_to_format.py prep  <batch> [--go]     the run.py commands that fill the gaps (--go runs them)
    python3 proven_to_format.py page  <batch> [--refresh] builds page/creative-run-builder.html from the batch
    python3 proven_to_format.py queue [<artifact url | requests.json>]   how a session works the page's queue
    python3 proven_to_format.py inject  <batch>   3 Injection prompts per square (chain's stage-3 prompt + winner slot)
    python3 proven_to_format.py squares <batch>   each written Injection becomes its own chain run
    python3 proven_to_format.py elements <batch>  Station 3.1 element lists (banked / to make) for every green ad
    python3 proven_to_format.py approve  <batch>  the owner's "elements ok" for every green ad at once (skips any with gaps)
    python3 proven_to_format.py produce  <batch> [--go]  hand approved ads to production (Station 4)
    python3 proven_to_format.py editor   <batch> [--go]  every ad with clips → the editor's queue folder, named by its brief
    python3 proven_to_format.py step  <batch> <square run name>   one step for a session writing Claude stages itself
                                      (prints WAITING <prompt> / FIX <run> <ids> / STOPPED / DONE)
    python3 proven_to_format.py run   <batch> --square <run name|all> [--to 5] [--limit N]
                                      squares through the chain, ONE model call per stage (no session hand-writing)

<batch> is a name in definitions/proven-to-format/ (or a path to one). Every subcommand takes --root <dir> to
read an alternate tree (a fuller extract of the shared repo) when this checkout is behind.

The batch is a grid: proven winners (rows, already torn down by the video chain) × fresh format swipes (columns).
Winner side needs 1 Teardown + 1b Doctrine (file 1c-doctrine.md) + the transcript. Format side needs
0 Triage → 1 Teardown → 2 Spec. Per square the chain then runs 3 Injection → the stage 4 loop (the owner's pick) →
5 Brief (AI lane) → Viewer Check → 6 Frames → 7 Final brief. Stage names are the chain's own
(tools/video-teardown/machine/chain.py). Nothing here queues a square; the owner picks them on the page.
Standard library only; ffmpeg/magick only for thumbnails.
"""
import argparse, base64, json, os, re, shlex, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.insert(0, str(COMP.parent / "run-kit"))
from run_kit import paths  # noqa: E402
REPO = paths.repo(HERE)
sys.path.append(str(REPO / "components" / "brandpath"))
import drive_index as DI  # noqa: E402  the one shared mount helper (O9 (Drive by fileId))
BATCHES = COMP / "definitions" / "proven-to-format"
BUILDER = COMP / "page" / "builder"
OUT_PAGE = COMP / "page" / "creative-run-builder.html"


def _no_mount():
    """No Shared Assets mount here: say so once, and hand back a path that can never exist."""
    print("proven_to_format: no Google Drive with Shared drives/Shared Assets is mounted on this machine — format "
          "videos and swipe notes on Drive will read as missing (a person's run, O9 (Drive by fileId))", file=sys.stderr)
    return Path(os.devnull) / "no-shared-assets-mount"


SA = DI.mount() or _no_mount()
# the swipe notes folder inside the shared drive (env SWIPE_NOTES_DIR)
SWIPE_NOTES = os.environ.get("SWIPE_NOTES_DIR", "swipes")
TEARDOWN = "tools/video-teardown/machine"
# A format's swipe video is read through the swipe home: the definition records
# keep the path they were written with, and swipe_home.resolve() maps it to today's.
for _r in HERE.parents:
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
try:
    import swipe_home  # noqa: E402
except ImportError:  # the swipe home (components/swipe-paid) is not in this repo: paths are read as written
    class swipe_home:  # noqa: N801
        @staticmethod
        def resolve(ref):
            return None


def _vt_workdir():
    """video-teardown's working-folder module, loaded by file (SI-56)."""
    m = sys.modules.get("vt_workdir")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "vt_workdir", REPO / "tools" / "video-teardown" / "machine" / "workdir.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["vt_workdir"] = m
        spec.loader.exec_module(m)
    return m


WINNER_NEEDS = [("1 Teardown", "stages/1-teardown.md"), ("1b Doctrine", "stages/1c-doctrine.md"),
                ("transcript", "stages/1-transcript.md")]
# format side: (stage name, --from id, file in a chain run, file in a swipe-organic record)
FORMAT_NEEDS = [("0 Triage", "0", "stages/0-triage.md", None),
                ("1 Teardown", "1", "stages/1-teardown.md", "stage1-teardown.md"),
                ("2 Spec", "2", "stages/2-spec.md", "stage2-spec.md")]
# the order a format run walks to 2 Spec, by the file each stage leaves (1b Doctrine writes 1c-doctrine.md)
RUN_ORDER = [("0", "0-triage.md"), ("1", "1-teardown.md"), ("1k", "1k-culture.md"), ("1b", "1c-doctrine.md"),
             ("2", "2-spec.md")]
OPEN_ITEM = ("3 Injection: the chain's filled stage-3 prompt for the format + the winner slot "
             "(prompts/stage-3-winner-slot/stage3-winner-slot-v1-damon.md: the winner's 1 Teardown transcript + "
             "1b Doctrine) — composed per square into runs/ad-variations/<brand>/p2f-<winner>__<code>/sent.md; "
             "the session writes 3-injection.md beside it. Approved by the owner 2026-10-05 (\"run them all\").")


# ---------- batch + files ----------

def load(name):
    p = Path(name)
    if not p.is_file():
        p = BATCHES / (name if name.endswith(".json") else name + ".json")
    b = json.loads(p.read_text())
    b.setdefault("batch", p.stem)
    return b


def rd(p):
    return p.read_text(errors="replace") if p.is_file() else ""


def short(w):
    return w["path"].rstrip("/").split("/")[-1]


def format_run(root, b, f):
    """The format's chain run folder: the batch's `run`, else any fmt-*-<code> run filed or in the chain's working folder."""
    if f.get("run") and (root / f["run"]).is_dir():
        return root / f["run"]
    tail = f["code"].lower()
    for base in (root / "runs/video-teardown" / b["brand"], _vt_workdir().root(root)):
        for d in sorted(base.glob(f"fmt-*{tail}")) if base.is_dir() else []:
            return d
    return None


def winner_state(root, w):
    d = root / w["path"]
    return [(n, (d / f).is_file()) for n, f in WINNER_NEEDS]


def format_state(root, b, f):
    run, rec = format_run(root, b, f), root / f["record"]
    out = []
    for n, _, rf, recf in FORMAT_NEEDS:
        where = ("chain run" if run and (run / rf).is_file() else
                 "swipe record" if recf and (rec / recf).is_file() else "")
        out.append((n, where))
    note = ("swipe record is a format read only" if (rec / "format.json").is_file()
            and not (rec / "stage1-teardown.md").is_file() and not out[1][1] else "")
    return out, run, note


def library(root, b):
    t = rd(root / b["sources"]["format_library"])
    return {a: n for a, n in re.findall(r"^- ([a-z0-9-]+) — ([^:]+): ", t, re.M)}


def fname(lib, f):
    i = f["format_id"]
    return lib.get(i) or (i.replace("new:", "") + " (proposed, not in the library yet)")


# ---------- check ----------

def cmd_check(a):
    b, root = load(a.batch), Path(a.root or REPO)
    lib = library(root, b)
    print(f"Batch {b['batch']} · {b['brand']} · {b['product']} · {b['avatar']} · {b['offer']} · {b['lane']}")
    print(f"Reading {root}\n\nWINNERS (rows) — need 1 Teardown, 1b Doctrine, transcript")
    gaps = 0
    for w in b["winners"]:
        st = winner_state(root, w)
        miss = [n for n, ok in st if not ok]
        gaps += bool(miss)
        if not (root / w["path"]).is_dir():
            line = "NOT FOUND in this tree"
        else:
            line = "ready" if not miss else "missing " + ", ".join(miss)
        print(f"  {w['ad'][:58]:58}  " + "  ".join(f"{n} {'✓' if ok else '✗'}" for n, ok in st) + f"  → {line}")
    print("\nFORMATS (columns) — need 0 Triage → 1 Teardown → 2 Spec")
    ready_f = 0
    for f in b["formats"]:
        st, run, note = format_state(root, b, f)
        has2 = dict(st)["2 Spec"]
        ready_f += bool(has2)
        gaps += not has2
        cells = "  ".join(f"{n} {'✓' if w else '✗'}" for n, w in st)
        where = f"from the {dict(st)['2 Spec']}" if has2 else "missing 2 Spec"
        extra = []
        if not dict(st)["0 Triage"] and has2:
            extra.append("no 0 Triage on file (the swipe record was torn down outside the chain)")
        if note:
            extra.append(note)
        print(f"  {f['code']} · {fname(lib, f)[:46]:46}  {cells}  → {'ready, ' if has2 else ''}{where}"
              + (f"\n      {'; '.join(extra)}" if extra else "")
              + (f"\n      run: {run.relative_to(root) if root in run.parents else run}" if run else ""))
    n_w = sum(1 for w in b["winners"] if all(ok for _, ok in winner_state(root, w)))
    print(f"\nGrid {len(b['winners'])} × {len(b['formats'])} = {len(b['winners']) * len(b['formats'])} squares. "
          f"Winners ready: {n_w} of {len(b['winners'])}. Formats at 2 Spec: {ready_f} of {len(b['formats'])}.")
    print("Nothing missing on either side." if not gaps else "Run `prep` for the commands that fill the gaps.")
    print("\n" + OPEN_ITEM)


# ---------- prep ----------

def winner_video(w):
    m = re.search(r"\*\*Source\*\* (.+?)\s*$", rd(SA / SWIPE_NOTES / short(w) / "asset.md"), re.M)
    return m.group(1) if m else f"<the winner's video — Source line of {SA.name}/{SWIPE_NOTES}/{short(w)}/asset.md>"


def run_cmd(video, b, label, start=None, stop="2", post_url=None):
    c = ["python3", "run.py", video, "--brand", b["brand"], "--label", label, "--route", b["route"],
         "--product", b["product"], "--for-avatar", b["avatar"]]
    if post_url:
        c += ["--post-url", post_url]
    if start:
        c += ["--from", start]
    return c + ["--to", stop]


def hand_dir(label):
    """Where a run's Claude stages wait for the session: hand/ inside the chain's own run folder."""
    return _vt_workdir().run_dir(label.lower(), REPO) / "hand"


def next_stage(run, stop_file):
    have = {p.name for p in (run / "stages").glob("*.md")} if run else set()
    for sid, fn in RUN_ORDER:
        if fn == stop_file:
            return sid if fn not in have else None
        if fn not in have:
            return sid
    return None


def cmd_prep(a):
    b, root = load(a.batch), Path(a.root or REPO)
    todo = []
    for f in b["formats"]:
        st, run, _ = format_state(root, b, f)
        if dict(st)["2 Spec"]:
            continue
        start = next_stage(run, "2-spec.md") if run else None
        label = f.get("run_label") or f"fmt-{f['format_id'].replace('new:', '')}-{f['code']}"
        todo.append((f"format {f['code']} → 2 Spec", run_cmd(str(swipe_home.resolve(f["video"]) or SA / f["video"]), b, label,
                     start if start and start != "0" else None, "2", f.get("post_url")), hand_dir(label)))
    for w in b["winners"]:
        miss = [n for n, ok in winner_state(root, w) if not ok]
        if not miss:
            continue
        start = "1" if "1 Teardown" in miss or "transcript" in miss else "1b"
        todo.append((f"winner {w['ad']} → 1b Doctrine", run_cmd(winner_video(w), b, short(w), start, "1b"),
                     hand_dir(short(w))))
    if not todo:
        print(f"Nothing to prep: every winner has 1 Teardown + 1b Doctrine + transcript, every format has 2 Spec.")
    for what, c, hand in todo:
        print(f"\n# {what}\ncd {REPO / TEARDOWN} && DAEMN_HAND_DIR={shlex.quote(str(hand))} {shlex.join(c)}")
        if a.go:
            r = subprocess.run(c, cwd=REPO / TEARDOWN, env=dict(os.environ, DAEMN_HAND_DIR=str(hand)))
            waiting = sorted(p.name for p in hand.glob("*.prompt.md") if not (hand / p.name.replace(".prompt", "")).is_file())
            print(f"  → exit {r.returncode}" + (f"; waiting for the session: {', '.join(waiting)} in {hand}" if waiting else ""))
    if todo:
        print("\nClaude stages are written by the session, always (the owner, 5 Oct 2026). Each command carries "
              "DAEMN_HAND_DIR (a hand/ folder inside its run): at a Claude stage the run stops and leaves "
              "<stage>.prompt.md there; the session writes <stage>.md beside it (same name, no .prompt) and runs "
              "the same command again with --from <that stage>. Every check still applies to what the session wrote.")
    print("\nNo square is queued by this. the owner picks squares on the page.\n" + OPEN_ITEM)


# ---------- page ----------

def enc(p):
    return "data:image/jpeg;base64," + base64.b64encode(Path(p).read_bytes()).decode()


def frames(video, tmp, key, n=6):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    d, out = float(r.stdout.strip() or 0), []
    for i in range(n):
        dst = tmp / f"{key}-{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{d * (0.04 + 0.92 * i / (n - 1)):.2f}", "-i",
                        str(video), "-frames:v", "1", "-vf", "scale=220:-2", "-q:v", "6", str(dst)], capture_output=True)
        if dst.is_file():
            out.append({"t": round(d * (0.04 + 0.92 * i / (n - 1)), 1), "src": enc(dst)})
    return out


def strip(sd, tmp, code):
    out = []
    for n, img in enumerate(sorted((sd / "strip").glob("*.jpg"))[:6]):
        dst = tmp / f"{code}-{n}.jpg"
        subprocess.run(["magick", str(img), "-resize", "220x", "-quality", "72", str(dst)], capture_output=True)
        if dst.is_file():
            out.append({"t": None, "src": enc(dst)})
    return out


def drive_link(p):
    r = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(p)], capture_output=True, text=True)
    return f"https://drive.google.com/file/d/{r.stdout.strip()}/view" if r.returncode == 0 and r.stdout.strip() else None


def stats(root, b):
    t, out = rd(root / b["sources"]["winner_record"]), {}
    rx = r'\{"run": "%s", "rank": (\d+), "name": ("(?:[^"\\]|\\.)*"), "sales": ([\d.]+), "spend": ([\d.]+), "cpa": ([\d.]+)'
    for w in b["winners"]:
        m = re.search(rx % re.escape(short(w)), t)
        if m:
            out[w["path"]] = {"rank": int(m.group(1)), "ad": json.loads(m.group(2)), "sales": int(float(m.group(3))),
                              "spend": float(m.group(4)), "cpa": float(m.group(5))}
    return out


def media(root, b, refresh):
    """Thumbnails, Drive play links and sales stats, cached per batch (page/builder/cache/<batch>/)."""
    cache = BUILDER / "cache" / b["batch"]
    files = {k: cache / f"{k}.json" for k in ("thumbs", "links", "stats")}
    if not refresh and all(p.is_file() for p in files.values()):
        return {k: json.loads(p.read_text()) for k, p in files.items()}
    tmp = cache / "frames"
    tmp.mkdir(parents=True, exist_ok=True)
    th, ln = {}, {}
    for w in b["winners"]:
        v = Path(winner_video(w))
        if v.is_file():
            th[w["path"]] = {"kind": "video", "frames": frames(v, tmp, short(w))}
            ln[w["path"]] = drive_link(v)
        print("  winner", short(w), "ok" if v.is_file() else "video not on the Drive mount")
    for f in b["formats"]:
        v = swipe_home.resolve(f["video"]) or SA / f["video"]
        fr = strip(v.parent, tmp, f["code"]) or (frames(v, tmp, f["code"]) if v.is_file() else [])
        if fr:
            th[f["record"]] = {"kind": "video", "frames": fr}
        if v.is_file():
            ln[f["record"]] = drive_link(v)
        print("  format", f["code"], "ok" if fr else "no strip or video on the Drive mount")
    for p in tmp.glob("*.jpg"):
        p.unlink()
    tmp.rmdir()
    data = {"thumbs": th, "links": {k: v for k, v in ln.items() if v}, "stats": stats(root, b)}
    for k, p in files.items():
        p.write_text(json.dumps(data[k], indent=None if k == "thumbs" else 1))
    return data


def norm(x):
    m = re.search(r"((?:runs|components)/.+?)/?$", x or "")
    return m.group(1) if m else x


def earlier(root, b):
    out = []
    for e in b.get("earlier_specs", []):
        d = root / e["run"]
        run, spec = json.loads(rd(d / "run.json") or "{}"), rd(d / "spec.md")
        out.append(dict(label=d.name.replace("swap-", "", 1), spec=spec, sent=rd(d / "sent.md"),
                        state="spec written" if spec else "waiting", opened=run.get("opened", ""),
                        cpath=norm(run.get("concept", "")), fpath=norm(run.get("format", "")),
                        product=run.get("product", ""), avatar=run.get("avatar", ""),
                        runtime=e.get("runtime", ""), plain=e.get("plain", "")))
    return out


STAGE_NAMES = [("stage4r", "4a Reading"), ("stage4b", "4b Hooks"), ("stage4a", "4c Placement"), ("stage4d", "4e Close"),
               ("stage4e", "4f Audit"), ("stage4g", "4g Spice"), ("stage5", "5 Brief")]


def _thumb(path, w=240):
    """A small data-URI picture for the page (never written to git)."""
    try:
        r = subprocess.run(["magick", str(path), "-resize", f"{w}x{w}>", "-quality", "70", "jpg:-"], capture_output=True, timeout=60)
        return "data:image/jpeg;base64," + base64.b64encode(r.stdout).decode() if r.returncode == 0 and r.stdout else ""
    except Exception:
        return ""


def element_picture(it, run_dir):
    """Banked: the element's own picture. To make: the swipe frame it will be made from."""
    if it.get("status") != "to make":
        f = REPO / (it.get("folder") or "")
        for pat in ("master.jpg", "master.png", "picture.jpg", "plates/wide.jpg", "model/reference-34-transparent.png",
                    "model/front-auto.png", "*.jpg", "*.png", "*/*.jpg", "*/*.png"):
            hit = sorted(f.glob(pat)) if f.is_dir() else []
            if hit:
                return _thumb(hit[0]), "banked"
        return "", "banked"
    fm = json.loads(rd(run_dir / "framemap" / "framemap.json") or "{}")
    cuts = [c for c in (fm.get("shots") or []) if isinstance(c, dict)]
    m = re.search(r"(\d+):(\d+(?:\.\d+)?)", " ".join(it.get("missing") or []))
    if m and cuts:
        t = int(m.group(1)) * 60 + float(m.group(2))
        for c in cuts:
            if c.get("start", 0) <= t < c.get("end", 0) or c is cuts[-1]:
                still = run_dir / "framemap" / "shots" / (c.get("stills") or {}).get("mid", "")
                if still.is_file():
                    return _thumb(still), f"from the swipe at {m.group(1)}:{m.group(2)}"
                break
    return "", "to make"


def squares(root, b):
    """Every square: its 3 Injection (runs/ad-variations/<brand>/p2f-*) and, once it runs on, its own chain run
    (runs/video-teardown/<brand>/sq-*) — the stage it reached, held or not, and the latest stage's text."""
    rec = {f["code"]: f["record"] for f in b["formats"]}
    rows = {w["path"] for w in b["winners"]}
    chain = {}
    for d in (root / "runs/video-teardown" / b["brand"]).glob("sq-*"):
        st = json.loads(rd(d / "run.json") or "{}").get("stages", {})
        w = (st.get("stage3") or {}).get("winner", "")
        code = d.name.split("-x-")[-1]
        chain[(w, code.lower())] = (d, st)
    out = []
    for d in sorted((root / "runs/ad-variations" / b["brand"]).glob("p2f-*")):
        run = json.loads(rd(d / "run.json") or "{}")
        code = run.get("format", "")
        if code not in rec or run.get("winner") not in rows:
            continue
        inj = rd(d / "3-injection.md")
        stage, state, text, held = "3 Injection", ("done" if inj else "writing"), inj, ""
        c = chain.get((run.get("winner", ""), code.lower()))
        if c:
            cd, st = c
            for k, n in STAGE_NAMES:
                s_ = (st.get(k) or {}).get("status")
                if s_ == "done":
                    stage, text = n, rd(cd / st[k]["out"]) or text
                elif s_ == "held":
                    held = n
                    break
                else:
                    break
            state = "ready" if stage == "5 Brief" else "inprogress"
            note = json.loads(rd(cd / "run.json") or "{}").get("hold_note", "")
            if held == "5 Brief" and (cd / "stages/5-brief.md").is_file():
                state, stage, held, text = "brief", "5 Brief written", note.split(" · ", 1)[-1], rd(cd / "stages/5-brief.md")
        els = []
        if c:
            ej = REPO / "runs/video-production" / b["brand"] / c[0].name.replace("sq-", "", 1) / "elements.json"
            if ej.is_file():
                for it in json.loads(ej.read_text()).get("items", []):
                    pic, src = element_picture(it, chain_runs() / c[0].name)
                    els.append({"kind": it.get("kind"), "id": it.get("id"), "banked": it.get("status") != "to make",
                                "describe": (it.get("describe") or "")[:220], "note": " ".join(it.get("missing") or [])[:220],
                                "pic": pic, "src": src})
        out.append(dict(label=d.name, elements=els, spec=text, sent="", sent_file=f"sent/{d.name}.md", stage=stage, state=state, held=held,
                        opened=run.get("opened", "2026-10-05"), cpath=run.get("winner", ""), fpath=rec[code],
                        product=run.get("product", ""), avatar=run.get("avatar", ""), runtime="", plain=""))
    return out


def cmd_page(a):
    b, root = load(a.batch), Path(a.root or REPO)
    lib, m = library(root, b), media(root, b, a.refresh)
    fm = [dict(path=f["record"], code=f["code"], format_id=f["format_id"], name=fname(lib, f), note=f.get("handle", ""))
          for f in b["formats"]]
    data = dict(kind="builder", batch={k: b[k] for k in ("batch", "brand", "product", "avatar", "offer", "route", "lane")},
                swaps=squares(root, b), thumbs=m["thumbs"], stats=m["stats"], links=m["links"],
                concepts=[dict(path=w["path"], name=w["ad"], note="") for w in b["winners"]], formats=fm,
                swap_prompt=rd(HERE.parent / "prompts/stage-3-winner-slot/stage3-winner-slot-v1-damon.md"),
                handoff="")
    ws = [winner_state(root, w) for w in b["winners"]]
    allok = lambda n: all(dict(s)[n] for s in ws)  # noqa: E731
    n_done = sum(all(ok for _, ok in s) for s in ws)
    st = lambda n: f'<span class="st{" ok" if allok(n) else ""}"><b>{n.split()[0]}</b>{n.split()[1]}{" ✓" if allok(n) else ""}</span>'  # noqa: E731
    fs = []
    for f, x in zip(b["formats"], fm):
        s, _, _ = format_state(root, b, f)
        last = [n for n, w in s if w]
        done = "2 Spec" in last
        colour = ' style="color:var(--done)"' if done else ""
        fs.append(f'<span>{x["name"]}</span><span{colour}>{"✓ " + last[-1] if last else "not started"}</span>')
    n_e = 0
    fill = {
        "{{BANKED}}": (b.get("banked") or {}).get("note", "") if isinstance(b.get("banked"), dict) else "",
        "{{TITLE}}": b.get("title") or " · ".join([b["brand"], b["product"], b["avatar"], b["offer"], b["lane"]]),
        "{{WINNER_STEPS}}": st("1 Teardown") + '<span class="ar">→</span>' + st("1b Doctrine"),
        "{{WINNER_NOTE}}": f"Done for all {len(ws)} winners." if n_done == len(ws) else f"Done for {n_done} of {len(ws)} winners.",
        "{{FMTSTAT}}": "".join(fs),
        "{{INJECT}}": f"{b['product'].replace('-', ' ')} + {b['offer']}",
        "{{EARLIER_NOTE}}": (f'<div class="small">The {n_e} green squares above were a shortcut that skipped this chain. '
                             "They'll be redone through it.</div>") if n_e else "",
    }
    page = (BUILDER / "proven_to_format_template.html").read_text()
    for k, v in fill.items():
        page = page.replace(k, v)
    page = page.replace("/*DATA*/null", json.dumps(data).replace("</", "<\\/"))
    out = Path(a.out) if a.out else OUT_PAGE
    out.write_text(page)
    print(f"built {out} — {len(b['winners'])} winners × {len(b['formats'])} formats, "
          f"{n_e} earlier specs, {round(out.stat().st_size / 1e6, 2)} MB. Not published.")


# ---------- queue ----------

QUEUE_DOC = """How a session works the queue (the owner says "run the queue"):

1. Read the requests the page saved: ArtifactData, action "list", collection "requests", url = the page's artifact
   url. Each doc is requests/<winner run>__<format code>:
     concept (winner run path) · concept_name (ad name) · format (swipe record path) · format_name · format_id
     target · product · avatar · offer · batch · state ("queued") · at · by
2. What each target means (stage names from tools/video-teardown/machine/chain.py):
     stage2  2 Spec — the format is broken down: 0 Triage → 1 Teardown → 2 Spec. `prep <batch>` prints the command.
     stage3  3 Injection — the winner's content (script, mechanism, proof, offer logic) + product + offer go INTO
             the format's 2 Spec. One chain run per square, label sq-<winner run>-x-<format code>: copy the
             format run's stages/ into that run folder, then run.py ... --from 3 --to 3. BLOCKED on the open item.
     stage5  through the stage 4 loop (4a Reading · 4b Hooks · 4c Placement · 4d Expansion · 4e Close · 4f Audit ·
             4g Spice — only the parts the owner picked, asked in chat) to 5 Brief, AI lane (--route ai). The Viewer
             Check (Marketing Chain Checks) runs by itself after every stage-5 brief. Then 6 Frames → 7 Final brief.
3. Questions go to the owner in chat, plainly. The page carries none.
4. When a square is done: set its doc's state to "done" (pin if_version), rebuild the page (`page <batch>`) and
   republish over the same url.
"""


def cmd_queue(a):
    print(QUEUE_DOC)
    if a.src and Path(a.src).is_file():
        rows = json.loads(Path(a.src).read_text())
        rows = rows.get("docs", rows) if isinstance(rows, dict) else rows
        print("Requests in", a.src)
        for r in rows:
            r = r.get("data", r)
            print(f"  {r.get('state', '?'):7} → {r.get('target', '?'):7}  {r.get('concept_name', r.get('concept'))}  ×  "
                  f"{r.get('format_name', r.get('format'))}")
    elif a.src:
        print(f"A session reads {a.src} with ArtifactData (list, collection \"requests\"); this script does not.")
    print("\n" + OPEN_ITEM)

# ---------- run: one square through the chain, one model call per stage ----------

ORDER4 = [("stage4r", "4a"), ("stage4b", "4b"), ("stage4a", "4c"), ("stage4c", "4d"), ("stage4d", "4e"),
          ("stage4e", "4f"), ("stage4g", "4g"), ("stage5", "5")]
RULE_CHECK = re.compile(r"claim|offer|rule|banned|compliance", re.I)


def chain_runs():
    """The chain's working folder, runs/video-teardown/_work/ (SI-56)."""
    return _vt_workdir().root(REPO)


def restore_squares(b):
    """Any machine can pick up where another left off: a square filed in the repo
    (runs/video-teardown/<brand>/sq-*) but missing from the chain's working folder is copied in."""
    import shutil
    filed = REPO / "runs/video-teardown" / b["brand"]
    for d in sorted(filed.glob("sq-*")):
        dst = chain_runs() / d.name
        if not dst.exists():
            shutil.copytree(d, dst)


def file_squares(b):
    """File each square run to the repo the chain's own way (video-teardown file_run.py): what was read off the
    swipe on runs/video-teardown/<brand>/<slug>/, everything written for the brand on runs/video-writing/<brand>/<slug>/
    — text only."""
    sys.path.insert(0, str(REPO / TEARDOWN))
    import file_run as FR
    for d in sorted(chain_runs().glob("sq-*")):
        try:
            FR.file_run(d)
        except Exception as e:  # filing never stops the work
            print(f"  could not file {d.name}: {type(e).__name__}: {e}")


def square_runs(b, which):
    """The squares' chain runs (runs/video-teardown/_work/sq-*), matched to this batch's formats."""
    restore_squares(b)
    codes = {f["code"].lower(): f for f in b["formats"]}
    out = []
    for d in sorted(chain_runs().glob("sq-*")):
        code = d.name.split("-x-")[-1]
        if code in codes and (which in ("all", d.name)):
            out.append((d, codes[code]))
    return out


def next_stage(st):
    skip = set((st.get("route") or {}).get("skipped") or [])
    for k, n in ORDER4:
        if k in skip:
            continue
        if (st["stages"].get(k) or {}).get("status") != "done":
            return k, n
    return None, None


def holds(d):
    """Ids in the run's hold notes: (pass — the swipe's own shape, per the owner 2026-10-06; fix — claims, offer, rules)."""
    ok, fix = set(), set()
    for f in d.glob("*.md"):
        if not re.fullmatch(r"[A-Z0-9-]+\.md", f.name):
            continue
        for line in f.read_text().splitlines():
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) >= 2 and re.fullmatch(r"(CF|[AHQV]?\d+|V)", c[0] or ""):
                (fix if c[0].startswith("A") and RULE_CHECK.search(c[1]) else ok).add(c[0])
    return sorted(ok), sorted(fix)


def fix_audit(d, ids, offer):
    """Rule fails are fixed, never passed: one call rewrites only the failing lines of the script (4e Close)."""
    script = d / "stages/4e-close.md"
    prompt = (f"An ad script failed its audit on claims, the offer or the brand's rules (checks {', '.join(ids)}).\n"
              "Make the smallest edits that clear exactly those checks — replace a banned word with the brand's approved "
              f"word named in the evidence, remove or correct an unsupported claim, make the offer read '{offer}' only. "
              "Change nothing else: the structure, timings and every other line stay as they are. Return ONLY the full "
              "corrected script, nothing before or after it.\n\n=== THE FAILED CHECKS ===\n" + rd(d / "AUDIT-HOLD.md") +
              "\n\n=== THE SCRIPT ===\n" + rd(script))
    r = subprocess.run(["claude", "-p", "--model", "opus", "--allowed-tools", ""], input=prompt, capture_output=True,
                       text=True, env=_chain_env(), timeout=900)
    if r.returncode or len(r.stdout.strip()) < 0.6 * len(rd(script)):
        raise SystemExit(f"  {d.name}: the audit fix did not come back whole — left held: {(r.stderr or r.stdout)[-300:]}")
    script.write_text(r.stdout.strip() + "\n")
    st = json.loads(rd(d / "run.json"))
    st["stages"].pop("stage4e", None)
    st.setdefault("fixed_audit", []).append(ids)
    (d / "run.json").write_text(json.dumps(st, indent=1))
    (d / "AUDIT-HOLD.md").rename(d / f"AUDIT-HOLD-fixed-{'-'.join(ids)}.md")


def _chain_env():
    sys.path.insert(0, str(REPO / TEARDOWN))
    import run as RUN  # the chain's own clean environment + long-life login
    return RUN._clean_env()


def run_square(b, d, f, stop="5", tries=6):
    video = swipe_home.resolve(f["video"]) or SA / f["video"]
    for _ in range(tries):
        st = json.loads(rd(d / "run.json"))
        k, n = next_stage(st)
        if not k or ORDER4.index((k, n)) > [x[1] for x in ORDER4].index(stop):
            return "reached " + stop
        ok, fix = holds(d)
        if fix and (d / "AUDIT-HOLD.md").is_file():
            print(f"  {d.name}: fixing audit {fix} (claims/offer/rules)")
            fix_audit(d, fix, b["offer"])
            continue
        cmd = [sys.executable, "run.py", str(video), "--brand", b["brand"], "--label", d.name, "--from", n, "--to", stop,
               "--route", b["route"], "--product", b["product"], "--for-avatar", b["avatar"]]
        if ok:
            cmd += ["--approve-structure", ",".join(ok)]
        print(f"  {d.name}: from {n}" + (f" · passing {','.join(ok)}" if ok else ""))
        r = subprocess.run(cmd, cwd=REPO / TEARDOWN, capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        if "HELD" not in (r.stdout + r.stderr) and "STOPPED" in (r.stdout + r.stderr):
            return "stopped: " + " ".join(tail)[-300:]
    st = json.loads(rd(d / "run.json"))
    k, n = next_stage(st)
    return f"at {n} after {tries} tries" if k else "reached " + stop


def cmd_run(a):
    b = load(a.batch)
    sq = square_runs(b, a.square)
    if not sq:
        raise SystemExit(f"no square run called {a.square!r} under {chain_runs()}")
    for d, f in sq[: a.limit or None]:
        print(f"{d.name}: {run_square(b, d, f, a.to)}")
    file_squares(b)
    print("filed to runs/video-teardown/" + b["brand"] + "/ — rebuild the page with: page " + a.batch)



def cmd_step(a):
    """One step of one square, for a session that writes the Claude stages itself (no chain sign-in).
    Prints exactly one line: WAITING <prompt file> (the session writes <same name>.md beside it, then steps
    again) · FIX <run folder> <ids> (an audit fail on claims/offer/rules: fix stages/4e-close.md and
    <run>/hand/4e-close.md, delete hand/4f-audit*, touch hand/fixed-<ids>, step again) · STOPPED <why> · DONE."""
    b = load(a.batch)
    hit = [x for x in square_runs(b, a.square)]
    if not hit:
        raise SystemExit(f"no square run called {a.square!r}")
    d, f = hit[0]
    hand = d / "hand"; hand.mkdir(exist_ok=True)
    for _ in range(3):
        st = json.loads(rd(d / "run.json"))
        k, n = next_stage(st)
        if not k or [x[1] for x in ORDER4].index(n) > [x[1] for x in ORDER4].index(a.to):
            print("DONE"); return
        ok, fix = holds(d)
        if fix and (d / "AUDIT-HOLD.md").is_file() and not (hand / f"fixed-{','.join(fix)}").exists():
            print(f"FIX {d} {','.join(fix)}"); return
        cmd = [sys.executable, "run.py", str(swipe_home.resolve(f["video"]) or SA / f["video"]), "--brand", b["brand"], "--label", d.name, "--from", n,
               "--to", a.to, "--route", b["route"], "--product", b["product"], "--for-avatar", b["avatar"]]
        if ok:
            cmd += ["--approve-structure", ",".join(ok)]
        env = dict(os.environ, AI_WORKSPACE=str(REPO), DAEMN_HAND_DIR=str(hand))
        r = subprocess.run(cmd, cwd=REPO / TEARDOWN, capture_output=True, text=True, env=env)
        out = r.stdout + r.stderr
        (hand / "last.log").write_text(out)
        waiting = [q for q in sorted(hand.glob("*.prompt.md"), key=lambda q: q.stat().st_mtime, reverse=True)
                   if not q.with_name(q.name.replace(".prompt.md", ".md")).exists()]
        if waiting:
            print(f"WAITING {waiting[0]}"); return
        if "HELD" not in out:
            break
        if holds(d)[0] == ok:   # a hold we can't pass ourselves
            break
    st = json.loads(rd(d / "run.json"))
    k, n = next_stage(st)
    if not k:
        print("DONE"); return
    tail = " ".join(l.strip() for l in out.splitlines() if "STOPPED" in l or "HELD" in l)[-400:]
    print(f"STOPPED {tail or 'at ' + n}")


# ---------- inject + squares: the two steps between "formats at 2 Spec" and the stage 4 loop ----------

WINNER_SLOT = COMP / "prompts" / "stage-3-winner-slot"
STRUCT_ANCHOR = "## THE SWIPE'S STRUCTURE IS LOCKED"


def p2f_name(w):
    """The Injection folder's winner part: the winner's run name without the top1-<brand>- prefix."""
    return re.sub(r"^top1-[a-z0-9]+-", "", Path(w["path"]).name)


def sq_name(w):
    """A winner's short name in square labels; the chain cuts run names at 40 characters."""
    if w.get("short"):
        return w["short"]
    base = Path(w["path"]).name
    base = re.sub(r"^top1-[a-z0-9]+-", "", base)
    return base[:23].rstrip("-")   # sq- + name + -x- + 11-char code = 40, the chain's limit


def fmt_run(f):
    return chain_runs() / Path(f.get("run", "")).name if f.get("run") else None


def winner_slot(b, w):
    slot = max(WINNER_SLOT.glob("stage3-winner-slot-v*-damon.md"),
               key=lambda q: int(re.search(r"-v(\d+)-", q.name).group(1))).read_text()
    st = (stats(REPO, b) or {}).get(w["path"], {})
    wd = REPO / w["path"] / "stages"
    return slot.format(product=b["product"].replace("-", " ").title(), offer=b["offer"], avatar=b["avatar"],
                       winner_name=w.get("ad") or Path(w["path"]).name,
                       winner_stats=f"#{st.get('rank', '?')} · {st.get('sales', '?')} sales · ${round(st.get('cpa', 0))} per sale",
                       winner_transcript=rd(wd / "1-transcript.md"), winner_doctrine=rd(wd / "1c-doctrine.md"))


def cmd_inject(a):
    """3 Injection per square: the chain fills its own stage-3 prompt for each format (once), the winner slot is
    added, and the result is saved as runs/ad-variations/<brand>/p2f-<winner>__<format>/sent.md. A square
    whose 3-injection.md is missing is printed as WAITING for the session to write it."""
    b = load(a.batch)
    for f in b["formats"]:
        fr = fmt_run(f)
        if not fr or not (fr / "run.json").is_file():
            print(f"{f['code']}: no chain run at 2 Spec yet — run `prep {a.batch} --go` first"); continue
        base = fr / "hand" / "3-injection.prompt.md"
        if not base.is_file():
            env = dict(os.environ, AI_WORKSPACE=str(REPO), DAEMN_HAND_DIR=str(fr / "hand"))
            subprocess.run([sys.executable, "run.py", str(swipe_home.resolve(f["video"]) or SA / f["video"]), "--brand", b["brand"], "--label", fr.name,
                            "--from", "3", "--to", "3", "--route", b["route"], "--product", b["product"],
                            "--for-avatar", b["avatar"]], cwd=REPO / TEARDOWN, capture_output=True, text=True, env=env)
        if not base.is_file():
            print(f"{f['code']}: the chain did not leave its stage-3 prompt — see {fr}/hand"); continue
        bt = base.read_text()
        for w in b["winners"]:
            out = REPO / "runs/ad-variations" / b["brand"] / f"p2f-{p2f_name(w)}__{f['code']}"
            out.mkdir(parents=True, exist_ok=True)
            if (out / "3-injection.md").is_file():   # already written — keep the prompt it was written from
                print("done    " + str(out / "sent.md")); continue
            slot = winner_slot(b, w)
            (out / "sent.md").write_text(bt.replace(STRUCT_ANCHOR, slot + "\n\n" + STRUCT_ANCHOR, 1)
                                         if STRUCT_ANCHOR in bt else bt + "\n\n" + slot)
            if not (out / "run.json").is_file():
                (out / "run.json").write_text(json.dumps({"chain": "proven ad -> new format", "winner": w["path"],
                    "winner_ad": w.get("ad"), "format": f["code"], "stage": "3 Injection", "route": b["route"],
                    "product": b["product"], "avatar": b["avatar"], "offer": b["offer"], "batch": b["batch"]}, indent=1))
            print(("done    " if (out / "3-injection.md").is_file() else "WAITING ") + str(out / "sent.md"))


def cmd_squares(a):
    """Each square with a written 3 Injection becomes its own chain run (runs/video-teardown/_work/sq-<winner>-x-<format>):
    a copy of the format's run with the Injection in place, ready for the stage 4 loop."""
    import shutil
    b = load(a.batch)
    for f in b["formats"]:
        fr = fmt_run(f)
        for w in b["winners"]:
            src = REPO / "runs/ad-variations" / b["brand"] / f"p2f-{p2f_name(w)}__{f['code']}"
            if not (src / "3-injection.md").is_file():
                continue
            label = f"sq-{sq_name(w)}-x-{f['code']}".lower()
            if len(label) > 40:
                raise SystemExit(f"{label} is over 40 characters — give the winner a 'short' name in the batch")
            dst = chain_runs() / label
            if not dst.exists():
                shutil.copytree(fr, dst, ignore=shutil.ignore_patterns("hand"))
                for q in (dst / "stages").glob("*"):
                    if q.name[:1] in "3456789":
                        q.unlink()
            shutil.copy(src / "3-injection.md", dst / "stages/3-injection.md")
            (dst / "prompts").mkdir(exist_ok=True)
            shutil.copy(src / "sent.md", dst / "prompts/3-injection.md")
            st = json.loads(rd(dst / "run.json"))
            st["slug"] = st["label"] = label
            keep = ("stage0", "stage1", "stage1k", "stage1c", "stage1b", "stage2", "stage2f")
            st["stages"] = {k: v for k, v in st["stages"].items() if k in keep}
            st["stages"]["stage3"] = {"status": "done", "name": "Injection", "out": "stages/3-injection.md",
                                      "sent": "prompts/3-injection.md", "engine": "claude", "model": "session",
                                      "prompt_name": "stage3-injection (chain) + " + max(WINNER_SLOT.glob("*.md")).name,
                                      "winner": w["path"]}
            st["declared_audience"] = dict(st.get("declared_audience") or {}, avatar=b["avatar"])
            st.pop("waiting_for", None)
            (dst / "run.json").write_text(json.dumps(st, indent=1))
            print("square ready for the stage 4 loop:", label)


# ---------- production hand-off: element lists → one approval → production ----------

VP = REPO / "tools" / "video-production" / "machine"


def prod_dir(b, d):
    """An ad's production folder: runs/video-production/<brand>/<square name without sq->."""
    return REPO / "runs" / "video-production" / b["brand"] / d.name.replace("sq-", "", 1)


def green_squares(b):
    out = []
    for d, f in square_runs(b, "all"):
        st = json.loads(rd(d / "run.json") or "{}").get("stages", {})
        w = (st.get("stage3") or {}).get("winner")
        if w in {x["path"] for x in b["winners"]} and (st.get("stage5") or {}).get("status") == "done":
            out.append((d, f))
    return out


def cmd_elements(a):
    """Station 3.1 for every green ad: the element list, banked or to make (free — nothing is generated)."""
    b = load(a.batch)
    for d, f in green_squares(b):
        out = prod_dir(b, d); out.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable, "elements_check.py", "sheet", str(d / "stages/5-brief.md"),
                            "--brand", b["brand"], "--out", str(out)], cwd=VP, capture_output=True, text=True)
        body = json.loads(rd(out / "elements.json") or "{}")
        tm = body.get("to_make") or []
        print(f"{d.name}: {len(body.get('items') or [])} elements · {len(tm)} to make"
              + ("" if body else f" · the sheet could not run: {(r.stderr or r.stdout)[-200:]}"))
        for i in tm:
            print(f"    to make  {i['kind']:8} {i['id']}")


def cmd_approve(a):
    """the owner's "elements ok" for every green ad at once (Station 3.3). An ad with anything still to make is
    skipped and named — never approved past a gap."""
    b = load(a.batch)
    for d, f in green_squares(b):
        out = prod_dir(b, d)
        r = subprocess.run([sys.executable, "elements_check.py", "confirm", str(out), "--by", a.by],
                           cwd=VP, capture_output=True, text=True)
        print(f"{d.name}: " + ("elements ok — locked" if r.returncode == 0 else "not yet — " + (r.stderr or r.stdout).strip()[-300:]))


def cmd_produce(a):
    """Hand every approved ad to production (Station 4): run.py start with the AI-lane brief. Dry run unless --go."""
    b = load(a.batch)
    for d, f in green_squares(b):
        out = prod_dir(b, d)
        if not (out / "elements-lock.json").is_file():
            print(f"{d.name}: waiting for 'elements ok'"); continue
        cmd = [sys.executable, "run.py", "start", str(d / "stages/5-brief.md"), "--brand", b["brand"],
               "--format", a.format, "--label", out.name] + ([] if a.go else ["--dry-run"])
        r = subprocess.run(cmd, cwd=VP, capture_output=True, text=True)
        print(f"{d.name}: " + ("started" if a.go else "dry run") + " — " + " ".join((r.stdout + r.stderr).strip().splitlines()[-2:])[-300:])


HANDOFF = Path(os.environ.get("HANDOFF_STANDARD") or REPO / "components" / "handoff-standard" / "skill" / "handoff.py")   # the team's hand-off standard
VE = REPO / "tools" / "video-edit" / "machine"
BRIEFS = REPO / "tools" / "image-teardown" / "tools" / "briefs.py"


def _register_row(b, d):
    """The ad's row in the brief register (tools/image-teardown/briefs.json), found by its chain run."""
    reg = json.loads(rd(REPO / "tools" / "image-teardown" / "briefs.json") or "{}").get("briefs") or {}
    rows = reg.values() if isinstance(reg, dict) else reg
    return next((x for x in rows if x.get("run") == d.name and x.get("brand") == b["brand"]), None)


def cmd_editor(a):
    """Station 4 → the editor (the owner, 2026-10-09: "I will just assign briefs to my editor to execute directly from
    the google drive"). Every ad whose clips are made gets ONE video-editor hand-off: its brief number in the
    register, its edit kit (video-edit `from-run`: clips in scene order, voice, music, sound, timing), and a folder
    named by the brief's short form, brand_product_brief, in $SHARED_DRIVE/handoffs/video-editor/<brand>/ — the
    editor's queue. An ad already handed off is skipped. Dry run unless --go."""
    b = load(a.batch)
    for d, f in green_squares(b):
        out = prod_dir(b, d)
        clips = sorted((out / "clips").glob("*.mp4")) if (out / "clips").is_dir() else []
        if not clips:
            print(f"{d.name}: no clips yet — nothing for the editor"); continue
        row = _register_row(b, d)
        if not row:
            if not a.go:
                print(f"{d.name}: {len(clips)} clips · would open a brief number, build the kit and hand it off"); continue
            cmd = [sys.executable, str(BRIEFS), "open", d.name, "--brand", b["brand"], "--product", b["product"],
                   "--avatar", b["avatar"], "--type", "video-ai"] + (["--link", b["link"]] if b.get("link") else [])
            r = subprocess.run(cmd, capture_output=True, text=True)
            row = _register_row(b, d)
            if not row:
                print(f"{d.name}: the brief register refused — {(r.stderr or r.stdout).strip()[-300:]}"); continue
            # the register points at the brief production made the clips from
            p = REPO / "tools" / "image-teardown" / "briefs.json"
            reg = json.loads(p.read_text())
            for x in (reg["briefs"].values() if isinstance(reg["briefs"], dict) else reg["briefs"]):
                if x.get("run") == d.name and x.get("brand") == b["brand"]:
                    x["brief_file"] = str((out / "brief.md").relative_to(REPO))
            p.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
        name = f"{b['brand']}_{row.get('product') or b['product']}_{row['brief']}"
        if (REPO / "runs" / "handoffs" / "video-editor" / b["brand"] / name).is_dir():
            print(f"{d.name}: already in the editor's queue as {name}"); continue
        kit = REPO / "runs" / "video-edit" / b["brand"] / out.name / "kit"
        if not a.go:
            print(f"{d.name}: {len(clips)} clips · would hand off as {name}"); continue
        if not (kit / "edit-kit.json").is_file():
            r = subprocess.run([sys.executable, "run.py", "from-run", str(out)], cwd=VE, capture_output=True, text=True)
            if not (kit / "edit-kit.json").is_file():
                print(f"{d.name}: the edit kit could not be built — {(r.stderr or r.stdout).strip()[-300:]}"); continue
        r = subprocess.run([sys.executable, str(HANDOFF), "video-editor", b["brand"], row["brief"], "--kit", str(kit)],
                           capture_output=True, text=True)
        print(f"{d.name}: " + ("in the editor's queue as " + name if r.returncode == 0
                               else "hand-off refused — " + (r.stderr or r.stdout).strip()[-400:]))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for n in ("check", "prep", "page"):
        p = sp.add_parser(n)
        p.add_argument("batch")
        p.add_argument("--root", help="read an alternate tree when this checkout is behind")
        if n == "prep":
            p.add_argument("--go", action="store_true", help="run the commands, not just print them")
        if n == "page":
            p.add_argument("--refresh", action="store_true", help="rebuild thumbnails, links and stats from the Drive")
            p.add_argument("--out", help="write the page here instead of page/creative-run-builder.html")
    r = sp.add_parser("run", help="take squares through the chain, one model call per stage")
    r.add_argument("batch"); r.add_argument("--square", default="all", help="a square's run name, or all")
    r.add_argument("--to", default="5", help="stop after this stage (default 5 = 5 Brief)")
    r.add_argument("--limit", type=int, help="only the first N squares")
    for n in ("inject", "squares"):
        x = sp.add_parser(n); x.add_argument("batch")
    e_ = sp.add_parser("elements", help="Station 3.1 element lists for every green ad"); e_.add_argument("batch")
    ap_ = sp.add_parser("approve", help="\"elements ok\" for every green ad at once"); ap_.add_argument("batch")
    ap_.add_argument("--by", default="damon")
    pr_ = sp.add_parser("produce", help="hand approved ads to production (dry run unless --go)"); pr_.add_argument("batch")
    pr_.add_argument("--format", default="demonstration", help="a row in video-production/formats/bank.json"); pr_.add_argument("--go", action="store_true")
    ed_ = sp.add_parser("editor", help="hand every ad with clips to the editor's queue (dry run unless --go)")
    ed_.add_argument("batch"); ed_.add_argument("--go", action="store_true")
    st_ = sp.add_parser("step", help="one step of one square, for a session writing the Claude stages itself")
    st_.add_argument("batch"); st_.add_argument("square"); st_.add_argument("--to", default="5")
    q = sp.add_parser("queue")
    q.add_argument("src", nargs="?")
    a = ap.parse_args()
    {"check": cmd_check, "prep": cmd_prep, "page": cmd_page, "queue": cmd_queue, "run": cmd_run, "step": cmd_step, "inject": cmd_inject, "squares": cmd_squares, "elements": cmd_elements, "approve": cmd_approve,
     "produce": cmd_produce, "editor": cmd_editor}[a.cmd](a)


if __name__ == "__main__":
    main()
