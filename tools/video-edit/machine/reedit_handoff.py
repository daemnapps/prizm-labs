"""THE RE-EDIT HAND-OFF — a video brief that generates nothing (a new cut of clips and a song that already exist)
packaged for the video editor in the Hand-off Standard's shape (the owner, 2026-10-28: "fill in the gap. We need to
program the gap"; the front door refused the first two re-edit briefs because they never passed the writing chain).

A re-edit run is a video-production run whose `deliverable/EDITOR-BRIEF.md` is the whole brief (shot table, sound
splices, words on screen, the ask). Everything this hand-off needs is read from that brief, never written into the code:

    runs/handoffs/video-editor/<brand>/<brief key>/
        BRIEF.md     the editor brief, word for word
        RUN.md       how to make it: A, a person in an editor; B, an agent, step by step
        run.json     the same for a machine: shots, refs, what to deliver, where it goes back
        refs/        every file the brief names that is small or not on the Drive yet, copied
        returned/    the finished cuts come back here

Files the brief names that already sit on the Drive at the same path are POINTED AT (never copied twice); the folder is
mirrored to Shared Assets/ at the same path. Spends nothing; generates nothing.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROLE = "video-editor"
BRIEF_FILE = Path("deliverable") / "EDITOR-BRIEF.md"
COPY_UNDER = 50 * 1024 * 1024        # a file over this is pointed at on the Drive, never copied into refs/


def is_reedit(vm: Path) -> bool:
    """A run is a re-edit when its editor brief is its whole brief and no writing-chain brief made it."""
    vm = Path(vm)
    return (vm / BRIEF_FILE).is_file() and not (vm / "storyboard.json").is_file()


def key_of(vm: Path) -> str:
    """The register key of the brief whose run is this folder (tools/image-teardown/briefs.json)."""
    rel = str(Path(vm).resolve().relative_to(REPO))
    reg = json.loads((REPO / "tools" / "image-teardown" / "briefs.json").read_text())
    rows = reg if isinstance(reg, list) else list((reg.get("briefs") or reg).values())
    hit = next((r for r in rows if isinstance(r, dict) and str(r.get("run") or "").rstrip("/") == rel), None)
    if not hit:
        raise ValueError(f"{rel}: no brief in the register names this run")
    return str(hit.get("id") or hit.get("key"))


def named_files(brief: str, production: str | None) -> list[str]:
    """Every repo path the brief names in backticks; a path relative to the production folder is resolved against it."""
    out = []
    for p in re.findall(r"`([^`]+)`", brief):
        p = p.strip()
        if " " in p or "<" in p or not re.search(r"\.[a-z0-9]{2,4}$|/$", p):
            continue
        cand = p if p.startswith("runs/") else (f"{production.rstrip('/')}/{p}" if production else None)
        if cand and (REPO / cand).exists() and cand not in out:
            out.append(cand)
    return out


def shots(brief: str) -> list[str]:
    """The clip numbers of the brief's picture table (`| in → out | NNN …`)."""
    return sorted(set(re.findall(r"^\|\s*[0-9:.]+\s*→\s*[0-9:.]+\s*\|\s*(\d{3})\b", brief, re.M)))


def clip_dir(brief: str, production: str | None) -> str | None:
    """Where the brief says the clips are (`…/<shot>.mp4`)."""
    m = re.search(r"`([^`]+)/<shot>\.mp4`", brief)
    if not m:
        return None
    d = m.group(1)
    return d if d.startswith("runs/") else (f"{production.rstrip('/')}/{d}" if production else d)


def deliverables(key: str, brief: str) -> list[str]:
    """The cut, and one version per hook the brief's Deliver section names (`h-a`, `h-b` …)."""
    deliver = brief.split("## Deliver", 1)[1].split("\n## ", 1)[0] if "## Deliver" in brief else ""
    hooks = sorted(set(re.findall(r"\bh-[a-z]\b", deliver)))
    return [f"{key}-control.mp4"] + [f"{key}-v{i}.mp4" for i in range(1, len(hooks) + 1)]


def _on_drive(rel: str) -> bool:
    sys.path.insert(0, str(REPO / "components" / "gdrive-creator"))
    from gdrive_creator import reach
    parts = rel.rstrip("/").split("/")
    try:
        if reach.route() == "mount":
            return Path(reach.mount()).joinpath(*parts).exists()
        names = {n for n, _ in (reach.list_tree(parts[:-1]) or [])}
        return parts[-1] in names or any(n.startswith(parts[-1] + "/") for n in names)
    except Exception:                                     # noqa: BLE001 — unknown is treated as not there: copied
        return False


def build(vm: Path, no_drive: bool = False, on_drive=_on_drive, put=None) -> dict:
    vm = Path(vm).resolve()
    run = json.loads((vm / "run.json").read_text()) if (vm / "run.json").is_file() else {}
    brand = run.get("brand") or vm.parent.name
    brief = (vm / BRIEF_FILE).read_text()
    key = key_of(vm)
    title = next((ln[2:].strip() for ln in brief.splitlines() if ln.startswith("# ")), key)
    production = run.get("production")
    d = REPO / "runs" / "handoffs" / ROLE / brand / key
    (d / "refs").mkdir(parents=True, exist_ok=True)
    (d / "returned").mkdir(exist_ok=True)
    drive = f"Shared Assets/runs/handoffs/{ROLE}/{brand}/{key}"
    refs, pointed = {}, {}
    for rel in named_files(brief, production):
        src = REPO / rel
        if src.is_file() and src.stat().st_size < COPY_UNDER and not on_drive(rel):
            name = Path(rel).name
            shutil.copyfile(src, d / "refs" / name)
            refs[rel] = f"refs/{name}"
        else:
            if src.is_file() and not on_drive(rel) and not no_drive:
                # a big file the Drive does not have yet goes up at its OWN path (the Drive mirrors the repo), so the
                # pointer below is true for whoever opens the folder
                _put(put)(src, "Shared Assets/" + str(Path(rel).parent))
            pointed[rel] = f"Shared Assets/{rel}"
    cd = clip_dir(brief, production)
    if cd:
        pointed.setdefault(cd + "/", f"Shared Assets/{cd}/")
    deliver = deliverables(key, brief)
    (d / "BRIEF.md").write_text(f"<!-- {key} · the editor brief, word for word, from {vm.relative_to(REPO)}/{BRIEF_FILE} -->\n\n"
                                + brief)
    rec = {"brief": key, "title": title, "kind": "re-edit (nothing generated)", "source_run": str(vm.relative_to(REPO)),
           "shots": shots(brief), "clips": f"Shared Assets/{cd}/<shot>.mp4" if cd else None,
           "refs": refs, "on_drive": pointed, "deliver": deliver,
           "returned": {"repo": f"runs/handoffs/{ROLE}/{brand}/{key}/returned/", "drive": f"{drive}/returned/"},
           "generation_cost_usd": 0}
    (d / "run.json").write_text(json.dumps(rec, indent=1) + "\n")
    (d / "RUN.md").write_text(run_md(rec, drive))
    if no_drive:
        return {**rec, "folder": str(d), "drive": None}
    put = _put(put)
    for f in sorted(p for p in d.rglob("*") if p.is_file()):
        rel = f.relative_to(d)
        put(f, drive + ("/" + str(rel.parent) if str(rel.parent) != "." else ""))
    return {**rec, "folder": str(d), "drive": drive}


def _put(put):
    if put is not None:
        return put
    sys.path.insert(0, str(REPO / "components" / "gdrive-creator"))
    from gdrive_creator import refs as R
    return R.put


def run_md(rec: dict, drive: str) -> str:
    rows = "\n".join(f"| `{Path(k).name}` | `{v}` (copied here) |" for k, v in rec["refs"].items())
    rows += ("\n" if rows else "") + "\n".join(f"| `{k}` | Drive `{v}` |" for k, v in rec["on_drive"].items())
    hooks = rec["deliver"][1:]
    return f"""# RUN SHEET · {rec['title']} · {rec['brief']}

A **re-edit**: nothing is generated, so no Higgsfield. It is cut from clips and sound that already exist. `BRIEF.md`
says exactly what goes where; this sheet says how, and where everything is.

| | |
|---|---|
| **Brief** | `BRIEF.md` in this folder |
| **Makes** | {', '.join(f'`{x}`' for x in rec['deliver'])} · 1080x1920 · -14 LUFS |
| **Shots used** | {', '.join(rec['shots']) or 'see BRIEF.md'}{(' · each at `' + rec['clips'] + '`') if rec['clips'] else ''} |
| **This folder** | repo `runs/handoffs/{ROLE}/…/{rec['brief']}/` · Drive `{drive}/` |
| **Return to** | `returned/` here (repo and Drive) |
| **Cost** | $0 generated, editing time only |

## What is where

| File the brief names | Where it is |
|---|---|
{rows}

## A · A person, in an editor

1. Lay the sound exactly as the brief's sound table says (in/out times, each splice in its listed gap, 2–3 frame crossfades).
2. Lay the picture shot by shot from the brief's picture table (clip number = file name).
3. Words on screen, captions and the end card exactly as the brief lists them; nothing it forbids.
4. Export {', '.join(rec['deliver'])} into `returned/`.

## B · An agent (your Claude), step by step

Work from this folder. Read `BRIEF.md` and `run.json` first.

1. Get every file in `run.json` `on_drive` and `refs` (the shared drive is mounted, or use the Drive connector) into a
   local work folder. Never edit an original; never delete anything on the Drive.
2. Sound: cut each row of the brief's sound table from its source at its in/out times (ffmpeg `-ss/-to`) and join them
   with a 2–3 frame crossfade (`acrossfade`). Every splice must land inside its listed gap; never cut inside a word.
3. Picture: cut each row of the picture table from its clip for the row's length, scale/pad to 1080x1920, and join in
   order on the same clock as the sound.
4. Words: the captions in the brief's caption style and the headlines and end-card words at the times it lists,
   spelled exactly as written.
5. Mix to -14 LUFS integrated (`loudnorm`), export H.264 1080x1920 as `{rec['deliver'][0]}` into `returned/`.
6. {('Hook versions: for each hook the brief names, swap only the opening shot for that hook, sound untouched, and export ' + ', '.join(hooks) + '.') if hooks else 'No hook versions for this brief.'}
7. Watch each file start to end: every word whole, captions off faces, the product only where the brief puts it, no
   claim the brief forbids. Then say it is in `returned/`.

Never regenerate a clip for a re-edit: a flaw is covered in the edit (reframe, trim) or listed for a person.
"""
