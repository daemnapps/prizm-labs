#!/usr/bin/env python3
"""
drain.py — the board's queue, done on the direct doors.

    python3 machine/drain.py <run folder> [--only <id> ...] [--dry-run]

The board (`board.py`) was built when Higgsfield had no API on this
machine: pressing Generate wrote a work order to `cinema/queue.json` and a
Claude session drained it through the MCP, then `pull.py` wrote the URLs
back. Since 2026-09-18 every station is a direct door, so the queue can be
drained by code, on this machine, with nobody in a session — Damon:
"we were just updating the modes, prompts, flows, and how it works
together, so you need to make updates to the tools, not remove them."

One order at a time, oldest first:

  generate <scene id>   the talking beat —
                        1. the frame: the character's cast sheet (and the
                           room plate, if the plan names one) edited into
                           this beat's frame on GPT Image, direct
                           (`rushes/stills/<id>.png`; reused if present)
                        2. the line: `vo/<id>.mp3` if the Cinema line already
                           made it, else ElevenLabs direct on the character's
                           cloned voice
                        3. Omni, the controlled recipe (`omni.talk`): the line
                           performed from the prompt, re-voiced into hers,
                           parity checked twice → `rushes/clips/<id>.mp4`
                           (the board's "voiced" slot — the take IS her voice)
  broll    <cutaway id> the silent cutaway — a still from the product
                        references, then `omni.motion` → `rushes/broll/<id>.mp4`
  revoice  <scene id>   nothing to do on this door: an Omni take is already
                        in her voice. Marked done.

Every replaced take is archived with the note Damon typed (pull.py's own
`archive()`), the plan row gets `generate.status = completed`, `file`,
`model`, `job_id`, `seconds_out`, and the parity verdicts; the order is
marked done or failed with the reason. The board reads all of it live.

Element placeholders (`<<<uuid>>>`) are Higgsfield's; a direct door sees
them as literal text. Before a prompt leaves here each one becomes the
element's plain name from the plan's cast sheet (or the brand's
element-facts), or is dropped.

No brand, model or person name lives in this file as a literal.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
EL = re.compile(r"<<<([0-9a-fA-F-]{36})>>>")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


platform = _load("platform")
prompt_mod = _load("prompt")
voice_mod = _load("voice")
omni = _load("omni")
direct_openai = _load("direct_openai")
pull = _load("pull")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------- plan

def plan_path(run: Path) -> Path:
    for cand in (run / "cinema" / "plan.json", run / "out" / "plan.json", run / "plan.json"):
        if cand.exists():
            return cand
    raise SystemExit(f"no plan.json under {run} (cinema/, out/ or the run root)")


def load_plan(run: Path) -> dict:
    return json.loads(plan_path(run).read_text())


def save_plan(run: Path, d: dict) -> None:
    plan_path(run).write_text(json.dumps(d, indent=1))


def queue_path(run: Path) -> Path:
    return run / "cinema" / "queue.json"


def read_queue(run: Path) -> list:
    p = queue_path(run)
    return json.loads(p.read_text()) if p.exists() else []


def write_queue(run: Path, q: list) -> None:
    queue_path(run).parent.mkdir(parents=True, exist_ok=True)
    queue_path(run).write_text(json.dumps(q, indent=1))


# ------------------------------------------------------------- the words

def element_names(plan: dict) -> dict:
    """uuid -> plain name, from the plan's cast sheet first, the brand's
    element-facts second."""
    names = {}
    for el in (plan.get("cast") or {}).get("elements") or []:
        if el.get("id") and el.get("name"):
            names[el["id"]] = el["name"]
    try:
        book = json.loads(prompt_mod.facts_file().read_text()).get("elements", {})
        for uid, row in book.items():
            names.setdefault(uid, row.get("name") or "")
    except Exception:
        pass
    return names


def plain(text: str, names: dict) -> str:
    """A prompt with no Higgsfield placeholders left in it."""
    def sub(m):
        return names.get(m.group(1), "")
    out = EL.sub(sub, text)
    out = re.sub(r"The room is \.\s*", "", out)            # a room line with no name left
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out.strip()


# -------------------------------------------------------------- the cast

def cast_home(plan: dict) -> Path | None:
    brand = plan.get("brand")
    name = (plan.get("cast") or {}).get("name") or ""
    if not brand or not name:
        return None
    home = voice_mod.cast_root_of(brand) / voice_mod.slugify(name)
    return home if home.is_dir() else None


def cast_references(run: Path, plan: dict) -> list[Path]:
    """The pictures a frame is edited from: what the plan names, else the
    character's own sheet(s) in the brand's characters folder
    (ai-elements/characters/, old name ai-cast/)."""
    cast = plan.get("cast") or {}
    refs = []
    for key in ("references", "reference", "master", "sheet"):
        v = cast.get(key)
        for item in (v if isinstance(v, list) else [v] if v else []):
            p = Path(item)
            refs.append(p if p.is_absolute() else run / p)
    if not refs:
        home = cast_home(plan)
        if home:
            for n in ("master-sheet.png", "character-sheet.png", "master.png"):
                if (home / n).exists():
                    refs.append(home / n)
                    break
            for n in ("boards/character-sheet.png",):
                if (home / n).exists() and (home / n) not in refs:
                    refs.append(home / n)
    room = cast.get("room_plate") or cast.get("plate")
    if room:
        p = Path(room)
        refs.append(p if p.is_absolute() else run / p)
    return [r for r in refs if r.exists()]


def voice_id_of(plan: dict) -> str | None:
    cast = plan.get("cast") or {}
    if cast.get("voice_id"):
        return cast["voice_id"]
    home = cast_home(plan)
    if home and (home / "voice.json").exists():
        return json.loads((home / "voice.json").read_text()).get("voice_id")
    return None


# ------------------------------------------------------------- the frame

def frame_prompt(row: dict, plan: dict, kind: str) -> str:
    """The delta only — never what the sheet already shows (frames-by-edit)."""
    cast = plan.get("cast") or {}
    if kind == "scene":
        who = cast.get("who") or "speaking to camera"
        return (f"Same person, same clothes, same room. One frame: {who}, chest height, "
                f"facing the lens, mid-sentence. {row.get('gesture', '').strip()} "
                f"Phone-camera look, natural light. No text, no captions.")
    return (f"One frame: {row.get('place', '').strip()}. {row.get('subject', '').strip()} "
            f"{row.get('action', '').strip()} {row.get('look', '').strip()} "
            f"The only writing anywhere is the real label the product carries. No captions.")


def make_still(run: Path, row: dict, plan: dict, kind: str, dry_run: bool) -> Path:
    still_dir = run / "rushes" / ("broll" if kind == "cut" else "stills")
    out = still_dir / f"{row['id']}.png"
    if out.exists() and not row.get("change"):
        return out
    refs = cast_references(run, plan) if kind == "scene" else product_references(run, row, plan)
    names = element_names(plan)
    text = plain(frame_prompt(row, plan, kind), names)
    print(f"  still {row['id']}: GPT Image, {len(refs)} reference(s)")
    direct_openai.generate(text, refs, out, dry_run=dry_run)
    return out


def product_references(run: Path, row: dict, plan: dict) -> list[Path]:
    refs = []
    for key in ("references", "packshot", "reference"):
        v = row.get(key)
        for item in (v if isinstance(v, list) else [v] if v else []):
            p = Path(item)
            refs.append(p if p.is_absolute() else run / p)
    return [r for r in refs if r.exists()] or cast_references(run, plan)


# -------------------------------------------------------------- the line

def line_audio(run: Path, row: dict, plan: dict, dry_run: bool) -> Path | None:
    for cand in (run / "vo" / f"{row['id']}.mp3", run / "voice" / f"{row['id']}.mp3",
                 run / "vo" / f"{row['id'].lower()}.mp3"):
        if cand.exists():
            return cand
    home = cast_home(plan)
    if not home or not (home / "voice.json").exists():
        return None
    lines_path = run / "lines.json"
    lines = json.loads(lines_path.read_text()) if lines_path.exists() else {}
    lines[row["id"]] = row.get("line", "")
    lines_path.write_text(json.dumps(lines, indent=1))
    manifest = voice_mod.make_lines(run, home, dry_run, voice_mod.http_transport, voice_mod.key_of())
    f = manifest.get(row["id"], {}).get("file")
    return (run / f) if f else None


# ------------------------------------------------------------- the takes

def do_generate(run: Path, row: dict, plan: dict, dry_run: bool) -> dict:
    still = make_still(run, row, plan, "scene", dry_run)
    voice_id = voice_id_of(plan)
    if not voice_id:
        raise SystemExit(f"{row['id']}: no cloned voice for this character — bind voice_id in "
                         f"brands/<brand>/ai-elements/characters/<name>/voice.json")
    names = element_names(plan)
    perf = plain(f"{row.get('delivery', '')}. {row.get('gesture', '')}", names)
    out = run / "rushes" / "clips" / f"{row['id']}.mp4"
    if out.exists() and not dry_run:
        pull.archive(run, "clips", row["id"], row, row.get("change", ""))
    res = omni.talk(row.get("line", ""), still, voice_id, out, seconds=int(row.get("seconds") or 0) or None,
                    prompt_extra=perf, dry_run=dry_run)
    return res


def do_broll(run: Path, row: dict, plan: dict, dry_run: bool) -> dict:
    still = make_still(run, row, plan, "cut", dry_run)
    names = element_names(plan)
    text = plain(prompt_mod.broll(row)["prompt"], names)
    out = run / "rushes" / "broll" / f"{row['id']}.mp4"
    if out.exists() and not dry_run:
        pull.archive(run, "broll", row["id"], row, row.get("change", ""))
    return omni.motion(text, still, out, seconds=int(row.get("seconds") or 0) or None, dry_run=dry_run)


def seconds_of(path: Path) -> float | None:
    try:
        r = subprocess.run(["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(path)], capture_output=True, text=True)
        return round(float(r.stdout.strip()), 2)
    except Exception:
        return None


def drain(run: Path, only: list[str] | None = None, dry_run: bool = False) -> int:
    run = Path(run).resolve()
    prompt_mod.use_brand(load_plan(run).get("brand") or "")
    q = read_queue(run)
    open_orders = [o for o in q if o.get("state") == "open"]
    if not open_orders:
        print("queue empty")
        return 0
    failed = 0
    for order in open_orders:
        plan = load_plan(run)
        act = order.get("action")
        ids = [i for i in order.get("ids", []) if not only or i in only]
        if not ids:
            continue
        pool = plan.get("cutaways", []) if act == "broll" else plan.get("scenes", [])
        results = {}
        for rid in ids:
            row = next((r for r in pool if r["id"] == rid), None)
            if not row:
                results[rid] = {"error": "no such row"}
                continue
            print(f"{act} {rid}")
            try:
                if act == "generate":
                    res = do_generate(run, row, plan, dry_run)
                elif act == "broll":
                    res = do_broll(run, row, plan, dry_run)
                elif act == "revoice":
                    res = {"note": "already in her voice on this door", "file": None}
                else:
                    res = {"error": f"unknown action {act}"}
            except (SystemExit, RuntimeError) as e:
                res = {"error": str(e)}
            results[rid] = res
            if dry_run or res.get("error"):
                if res.get("error"):
                    failed += 1
                    print(f"  FAILED {rid}: {res['error']}")
                continue
            key = "generate"
            row.setdefault(key, {})
            f = res.get("file")
            row[key].update({"status": "completed", "file": str(Path(f).relative_to(run)) if f else None,
                             "model": res.get("model"), "job_id": res.get("request_id"),
                             "door": "direct", "recipe": res.get("recipe"),
                             "seconds_out": seconds_of(Path(f)) if f else None, "at": now()})
            for k in ("parity_native", "parity_final"):
                if res.get(k):
                    row[key][k] = res[k]
            row.pop("change", None)
            if act == "generate":
                row.setdefault("revoice", {}).update({"status": "completed", "note": "voice from the recipe"})
            save_plan(run, plan)
        if not dry_run:
            order["state"] = "failed" if any(r.get("error") for r in results.values()) else "done"
            order["results"] = {k: (v.get("error") or v.get("file") or v.get("note")) for k, v in results.items()}
            order["done"] = now()
            write_queue(run, q)
    return 1 if failed else 0


def run_in_background(run: Path) -> None:
    """What the board calls when Generate is pressed: this file, detached."""
    log = Path(run) / "cinema" / "drain.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as f:
        subprocess.Popen([sys.executable, str(HERE / "drain.py"), str(run)], stdout=f, stderr=f,
                         start_new_session=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="drain the board's queue on the direct doors")
    p.add_argument("run")
    p.add_argument("--only", nargs="*")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    return drain(Path(a.run), a.only, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
