#!/usr/bin/env python3
"""The copier: brings saved work from a source repo into this one, names stripped, and says how far behind it is.

    python3 tools/chain-mirror/mirror.py status            # per group: copied, behind, missing, not saved yet
    python3 tools/chain-mirror/mirror.py run <group> [--dry-run]
    python3 tools/chain-mirror/mirror.py check             # every copied file, swept for private names again

What it copies is the list in manifest.json (groups of files and folders). It reads only work that is SAVED in
the source (the source's `ref`, default origin/main), never a file still being edited there. Each copied file is
stripped (private names -> stand-ins, home paths -> ~/) and then checked with tools/safety_check.py's rules; a
file that still holds a private name, a key or a home path is refused and nothing of it is written.

Settings, all outside the public repo (so it works for anyone, in any copy):
  CHAIN_MIRROR_CONFIG  a JSON file {"source": "<source repo folder>", "ref": "origin/main",
                       "names": {"<private word>": "<stand-in>", ...}}
                       default: nucleus/home/chain-mirror.json inside this repo (ignored by git)
  CHAIN_MIRROR_SOURCE  overrides "source"
Standard library only.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import safety_check  # noqa: E402

MANIFEST = HERE / "manifest.json"
STAMPS = HERE / "stamps.json"
HOME_PATH = re.compile(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/")


def config():
    p = Path(os.environ.get("CHAIN_MIRROR_CONFIG") or REPO / "nucleus" / "home" / "chain-mirror.json")
    cfg = json.loads(p.read_text()) if p.is_file() else {}
    cfg["source"] = os.environ.get("CHAIN_MIRROR_SOURCE") or cfg.get("source")
    cfg.setdefault("ref", "origin/main")
    cfg.setdefault("names", {})
    if not cfg["source"]:
        sys.exit("chain-mirror: no source repo set (CHAIN_MIRROR_SOURCE or the config file's \"source\").")
    return cfg


def git(src, *args):
    return subprocess.run(["git", "-C", src, *args], capture_output=True, check=True).stdout


def saved_files(src, ref, path):
    out = git(src, "ls-tree", "-r", "--name-only", ref, "--", path).decode()
    return [f for f in out.splitlines() if f]


def last_commit(src, ref, path):
    return git(src, "log", "-1", "--format=%H", ref, "--", path).decode().strip()


def strip(text, names):
    """Private names to stand-ins (whole words, any case), home paths to ~/."""
    text = HOME_PATH.sub("~/", text)
    for word in sorted(names, key=len, reverse=True):
        text = re.sub(r"(?i)(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])", names[word], text)
    return text


def leaks(text):
    found = [("private name", n) for n in safety_check.private_names(text)]
    found += [("key-like text", m.group(0)[:6] + "…") for m in safety_check.KEYS.finditer(text)]
    found += [("home path", m.group(0)) for m in safety_check.PATHS.finditer(text)]
    return found


def targets(entry, src, ref):
    """(source file, repo file) pairs for one manifest entry, saved files only."""
    frm, to = entry["from"].rstrip("/"), entry["to"].rstrip("/")
    skip = [re.compile(x) for x in entry.get("exclude", [])]
    for f in saved_files(src, ref, frm):
        if any(s.search(f) for s in skip):
            continue
        rel = f[len(frm):].lstrip("/")
        yield f, (to + "/" + rel) if rel else to


def unsaved(entry, src, ref):
    """Files under the entry that exist in the source folder but are not saved there yet."""
    base = Path(src) / entry["from"]
    on_disk = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()] if base.is_dir() else []
    saved = set(saved_files(src, ref, entry["from"]))
    return [str(p.relative_to(src)) for p in on_disk
            if str(p.relative_to(src)) not in saved and "__pycache__" not in p.parts and p.name != ".DS_Store"]


def load_stamps():
    return json.loads(STAMPS.read_text()) if STAMPS.is_file() else {}


def status(cfg, groups):
    stamps, src, ref = load_stamps(), cfg["source"], cfg["ref"]
    print(f"source saved at {git(src, 'rev-parse', '--short', ref).decode().strip()} ({ref})")
    for name, entries in groups.items():
        copied = behind = missing = 0
        waiting = []
        for e in entries:
            for f, to in targets(e, src, ref):
                st = stamps.get(to)
                if not st:
                    missing += 1
                elif st["commit"] != last_commit(src, ref, f):
                    behind += 1
                else:
                    copied += 1
            waiting += unsaved(e, src, ref)
        line = f"{name}: {copied} current · {behind} behind · {missing} not copied"
        print(line + (f" · {len(waiting)} not saved in the source yet" if waiting else ""))
    return 0


def run(cfg, groups, group, dry):
    if group not in groups:
        sys.exit(f"chain-mirror: no group {group!r}. Groups: {', '.join(groups)}")
    stamps, src, ref = load_stamps(), cfg["source"], cfg["ref"]
    wrote, refused, same = [], [], 0
    for e in groups[group]:
        for f, to in targets(e, src, ref):
            raw = git(src, "show", f"{ref}:{f}")
            dest = REPO / to
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                out = raw                                  # pictures and other binaries go over as they are
            else:
                text = strip(text, cfg["names"])
                found = leaks(text)
                if found:
                    refused.append((to, found[:3]))
                    continue
                out = text.encode("utf-8")
            if dest.is_file() and dest.read_bytes() == out:
                same += 1
            elif not dry:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(out)
                wrote.append(to)
            else:
                wrote.append(to)
            if not dry:
                stamps[to] = {"from": f, "commit": last_commit(src, ref, f)}
    if not dry:
        STAMPS.write_text(json.dumps(dict(sorted(stamps.items())), indent=1) + "\n")
    verb = "would write" if dry else "wrote"
    print(f"{group}: {verb} {len(wrote)} · already the same {same} · refused {len(refused)}")
    for to in wrote:
        print(f"  + {to}")
    for to, found in refused:
        print(f"  ✗ {to}: " + ", ".join(f"{k} {w}" for k, w in found))
    return 1 if refused else 0


def check():
    bad = 0
    for to in load_stamps():
        p = REPO / to
        if p.is_file():
            try:
                found = leaks(p.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
            if found:
                bad += 1
                print(f"  ✗ {to}: " + ", ".join(f"{k} {w}" for k, w in found[:3]))
    print("chain-mirror check: " + ("OK" if not bad else f"{bad} files hold something private"))
    return 1 if bad else 0


def main(argv):
    groups = json.loads(MANIFEST.read_text())["groups"]
    cmd = argv[0] if argv else "status"
    if cmd == "check":
        return check()
    cfg = config()
    if cmd == "status":
        return status(cfg, groups)
    if cmd == "run" and len(argv) > 1:
        return run(cfg, groups, argv[1], "--dry-run" in argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
