#!/usr/bin/env python3
"""Ad workflows declared in format playbooks.

run <format> --brand B --label L       execute/resume; agent tasks return concrete requests
complete <format> ... --station ID    return evidence for the next agent task, or adopt checked output
run <format> ... --dry-run            inspect the resumable runner without writes/generation
list / show                          discover the available workflow definitions
status                               legacy artifact inventory (not execution or approval state)
pack                                 legacy local artifact handoff (does not upload/share files)

The execution loop is workflow_runner.py; components retain ownership of their work and reviews.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import playbook as PB  # noqa: E402

sys.path.insert(0, str(HERE.parents[1] / "run-kit"))
from run_kit.paths import repo
WS = repo(HERE)


def workflow(fmt):
    wf = (PB.own_file(fmt) or {}).get("workflow")
    if not wf:
        have = [p.stem for p in sorted(PB.root().glob("*.json")) if (PB._read(p) or {}).get("workflow")]
        raise SystemExit("format %r has no workflow — formats with one: %s" % (fmt, ", ".join(have) or "none"))
    return wf


def fill(text, values):
    """{name} filled from values; a name with no value stays {name} so the gap is visible."""
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), text or "")


def is_done(step, values):
    pat = fill(step.get("done_when") or "", values)
    if not pat or "{" in pat:
        return None                              # nothing on disk proves this station (a decision, or a gap)
    hits = glob.glob(str(WS / pat))
    if not hits:
        return False
    if step.get("same_as"):
        try:
            source = WS / fill(step["same_as"], values)
            if not any(Path(hit).is_file() and Path(hit).read_bytes() == source.read_bytes() for hit in hits):
                return False
        except OSError:
            return False
    check = step.get("run_check")
    if check:
        record = fill(check["file"], values)
        if "{" in record:
            return None
        try:
            data = json.loads((WS / record).read_text())
            stages = data.get("stages", {})
            if any(stages.get(k, {}).get("status") != "done" for k in check["stages"]):
                return False
            if check.get("reject_incomplete") and any(
                s.get("status") != "done" for s in stages.values()
            ):
                return False
        except (OSError, ValueError, AttributeError, TypeError):
            return False
    return True


def status(fmt, values):
    """[{id, name, done, gate, component, run}] for every station, in order."""
    out = []
    for s in workflow(fmt)["steps"]:
        out.append({"id": s["id"], "name": s["name"], "done": is_done(s, values), "gate": s.get("gate"),
                    "component": s["component"], "does": s["does"], "run": fill(s.get("run"), values)})
    return out


def next_station(rows):
    """Later artifacts never prove an earlier prerequisite or manual decision."""
    for r in rows:
        if r["done"] is not True:
            return r
    return None


def pack(fmt, values, rows):
    """The hand-off folder for a run at whatever station it has reached. Copies only small files (under 5 MB); a big
    file is named by its repo path. No upload or remote availability is implied."""
    import shutil
    wf = workflow(fmt)
    nxt = next_station(rows)
    brand, label = values.get("brand"), values.get("label")
    if not (brand and label):
        raise SystemExit("pack needs --brand and --label")
    d = WS / "runs" / "handoffs" / "workflow" / brand / label
    (d / "refs").mkdir(parents=True, exist_ok=True)
    (d / "returned").mkdir(exist_ok=True)
    files = {}
    for st, r in zip(wf["steps"], rows):
        pat = fill(st.get("done_when") or "", values)
        if r["done"] and pat and "{" not in pat:
            for hit in sorted(glob.glob(str(WS / pat))):
                h = Path(hit)
                rel = str(h.relative_to(WS))
                if h.is_file() and h.stat().st_size < 5 * 1024 * 1024:
                    shutil.copyfile(h, d / "refs" / (st["id"] + "-" + h.name))
                    files.setdefault(st["id"], []).append({"repo_path": rel, "copied_to": "refs/%s-%s" % (st["id"], h.name)})
                else:
                    files.setdefault(st["id"], []).append({"repo_path": rel, "copied_to": None})
    state = {"format": fmt, "workflow": wf["what"], "values": values,
             "stations": [{"id": st["id"], "name": st["name"], "done": r["done"], "gate": st.get("gate"),
                           "component": st["component"], "run": r["run"], "files": files.get(st["id"], [])}
                          for st, r in zip(wf["steps"], rows)],
             "next": ({"id": nxt["id"], "name": nxt["name"], "does": nxt["does"], "component": nxt["component"],
                       "run": nxt["run"], "gate": nxt["gate"]} if nxt else None),
             "resume": "python3 tools/video-production/machine/workflow.py status %s --from-state %s"
                       % (fmt, "runs/handoffs/workflow/%s/%s/state.json" % (brand, label))}
    (d / "state.json").write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    md = ["# Hand-off · %s · %s" % (fmt, label), "", wf["what"], "", "## Where it is", ""]
    for i, x in enumerate(state["stations"], 1):
        md.append("%d. [%s] **%s**%s" % (i, {True: "done", False: " ", None: "—"}[x["done"]], x["name"],
                                        (" — signs off: " + x["gate"]) if x["gate"] else ""))
    if nxt:
        md += ["", "## Next", "", "**%s** — %s" % (nxt["name"], nxt["does"]), "", "Component: %s" % nxt["component"]]
        if nxt["run"]:
            md += ["", "```", nxt["run"], "```"]
        if nxt["gate"]:
            md += ["", "Stops for: **%s**" % nxt["gate"]]
    else:
        md += ["", "Every station is done."]
    md += ["", "## How to pick this up (any app, any person)", "",
           "Open this folder in Claude Code with the team repo and say: *run the %s workflow from this hand-off*. It reads "
           "`state.json`, runs `%s`, and does the next station. Finished work goes in `returned/`." % (fmt, state["resume"])]
    (d / "HANDOFF.md").write_text("\n".join(md) + "\n")
    print("hand-off written:", d)
    print("next:", nxt["name"] if nxt else "none")
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("run", "complete"):
        import workflow_runner
        return workflow_runner.main(args)
    ap = argparse.ArgumentParser(description="Start a format's workflow by name; see where a run stands.")
    ap.add_argument("cmd", choices=["list", "show", "status", "pack", "run", "complete"])
    ap.add_argument("--from-state", dest="from_state", help="a hand-off's state.json: its values are used")
    ap.add_argument("format", nargs="?")
    ap.add_argument("--label")
    ap.add_argument("--brand")
    ap.add_argument("--brief-key", dest="brief_key")
    ap.add_argument("--set", action="append", default=[], help="name=value for any other {slot} a command needs")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for p in sorted(PB.root().glob("*.json")):
            pb = PB._read(p) or {}
            if pb.get("workflow"):
                print("%-16s %d stations  %s" % (p.stem, len(pb["workflow"]["steps"]), pb.get("name", "")))
        return 0
    if not a.format:
        ap.error("name the format")
    wf = workflow(a.format)
    if a.cmd == "show":
        print(wf["what"])
        for k, v in (wf.get("doors") or {}).items():
            print("  door %s: %s" % (k, v))
        for i, s in enumerate(wf["steps"], 1):
            print("%2d. %-22s %-48s %s" % (i, s["name"], s["component"][:48], ("gate: " + s["gate"]) if s.get("gate") else ""))
            print("    %s: %s" % (s.get("executor", "agent"), s["does"]))
        return 0
    values = {}
    if a.from_state:
        values.update((json.loads(Path(a.from_state).read_text()).get("values")) or {})
    values.update({k: v for k, v in {"label": a.label, "brand": a.brand, "brief_key": a.brief_key}.items()
                   if v is not None})
    for kv in a.set:
        k, sep, v = kv.partition("=")
        if not sep or not k.strip():
            ap.error("--set needs name=value")
        values[k.strip()] = v.strip()
    values = {k: v for k, v in values.items() if v}
    rows = status(a.format, values)
    if a.cmd == "pack":
        return pack(a.format, values, rows)
    print("Artifact status only; verify human sign-offs separately. Later files do not prove approval.")
    for i, r in enumerate(rows, 1):
        mark = {True: "done", False: "    ", None: "  - "}[r["done"]]
        print("%2d. [%s] %-22s %s" % (i, mark, r["name"], ("gate: " + r["gate"]) if r["gate"] else ""))
    n = next_station(rows)
    if not n:
        print("\nevery station is done")
        return 0
    print("\nNEXT: %s — %s\n  component: %s" % (n["name"], n["does"], n["component"]))
    if n["run"]:
        missing = sorted(set(re.findall(r"\{(\w+)\}", n["run"])))
        if missing:
            print("  needs values before command can run: %s" % ", ".join(missing))
            print("  template: %s" % n["run"])
        else:
            print("  run: %s" % n["run"])
    if n["gate"]:
        print("  stops for: %s" % n["gate"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
