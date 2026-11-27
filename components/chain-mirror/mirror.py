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
                       "names": {"<private word>": "<stand-in>", ...},
                       "suffixes": {"-<tag>": "-owner", ...},   file-name tags, renamed in paths and text
                       "drop_lines": ["<regex>", ...]}          lines that only work inside the source's company
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
    cfg.setdefault("suffixes", {})
    cfg.setdefault("drop_lines", [])
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


ALWAYS_SKIP = [re.compile(r"(^|/)archive/"), re.compile(r"__pycache__"), re.compile(r"\.DS_Store$"),
               re.compile(r"(^|/)(runs|_work|output)/"), re.compile(r"\.(mp4|mov|m4a|wav|mp3|zip|glb|blend)$", re.I)]
MAX_BYTES = 2_000_000


def rename(text, suffixes):
    """Name tags on file names (e.g. a person's tag on a prompt file) to the copy's tag, in paths and in text."""
    for old in sorted(suffixes, key=len, reverse=True):
        text = re.sub(re.escape(old) + r"(?=[.\-_/]|$)", suffixes[old], text)
    return text


CODE = (".py", ".js", ".sh", ".mjs", ".ts")


def slug(stand_in):
    """A stand-in that is safe inside code: one lower-case word (the owner -> owner, Brand A -> brand_a)."""
    words = re.sub(r"[^A-Za-z0-9]+", " ", stand_in).split()
    if words and words[0].lower() in ("the", "a", "an") and len(words) > 1:
        words = words[1:]
    return "_".join(w.lower() for w in words)


def strip(text, names, suffixes=None, drop_lines=(), code=False):
    """Lines that only make sense inside the source's own company go; then file-name tags, private names
    (whole words, any case) and home paths."""
    if drop_lines:
        text = "".join(l for l in text.splitlines(keepends=True) if not any(re.search(d, l) for d in drop_lines))
    text = rename(text, suffixes or {})
    text = HOME_PATH.sub("~/", text)
    for word in sorted(names, key=len, reverse=True):
        new = slug(names[word]) if code else names[word]
        text = re.sub(r"(?i)(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])", new, text)
    return text


def allowed_email(email):
    return any(text.lower() in email.lower() for _, text in safety_check.allowed())


def leaks(text):
    found = [("private name", n) for n in safety_check.private_names(text)]
    found += [("key-like text", m.group(0)[:6] + "…") for m in safety_check.KEYS.finditer(text)]
    found += [("home path", m.group(0)) for m in safety_check.PATHS.finditer(text)]
    found += [("personal email", m.group(0)) for m in safety_check.EMAIL.finditer(text)
              if not safety_check.EMAIL_OK.search(m.group(0)) and not allowed_email(m.group(0))]
    return found


VERSIONED = re.compile(r"^(?P<stem>.*?)-v(?P<n>\d+)(?P<tail>-[^/]*)?\.(?P<ext>md|txt|json)$")


def older_versions(files, src, ref):
    """Prompt files with a newer -vN- beside them that no code file in the source still names."""
    newest = {}
    for f in files:
        m = VERSIONED.match(f)
        if m:
            key = (m["stem"], m["tail"], m["ext"])
            newest[key] = max(newest.get(key, 0), int(m["n"]))
    old = {f for f in files if (m := VERSIONED.match(f)) and int(m["n"]) < newest[(m["stem"], m["tail"], m["ext"])]}
    if not old:
        return set()
    named = git(src, "grep", "-h", "-o", "-I", "-E", r"[A-Za-z0-9_.-]+-v[0-9]+[A-Za-z0-9_.-]*", ref, "--",
                "*.py", "*.json", "*.js", "*.html", "*.sh").decode(errors="ignore") if old else ""
    named = {line.split(":", 1)[-1] for line in named.splitlines()}
    return {f for f in old if f.rsplit("/", 1)[-1] not in named}


def targets(entry, src, ref, suffixes=None):
    """(source file, repo file) pairs for one manifest entry, saved files only, newest prompt versions only."""
    frm, to = entry["from"].rstrip("/"), entry["to"].rstrip("/")
    skip = ALWAYS_SKIP + [re.compile(x) for x in entry.get("exclude", [])]
    files = [f for f in saved_files(src, ref, frm) if not any(s.search(f) for s in skip)]
    stale = older_versions(files, src, ref)
    for f in files:
        if f in stale:
            continue
        rel = f[len(frm):].lstrip("/")
        yield f, rename((to + "/" + rel) if rel else to, suffixes or {})


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
            for f, to in targets(e, src, ref, cfg.get("suffixes", {})):
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
    wrote, refused, same, removed = [], [], 0, []
    for e in groups[group]:
        produced = set()
        for f, to in targets(e, src, ref, cfg.get("suffixes", {})):
            produced.add(to)
            named = safety_check.private_names(to)
            if named:                                   # a file named after a brand or person is that brand's data
                refused.append((to, [("brand or person in the file name", named[0])]))
                continue
            raw = git(src, "show", f"{ref}:{f}")
            if len(raw) > MAX_BYTES:
                continue
            dest = REPO / to
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                out = raw                                  # pictures and other binaries go over as they are
            else:
                text = strip(text, cfg["names"], cfg.get("suffixes", {}), cfg.get("drop_lines", ()),
                             code=f.endswith(CODE))
                found = leaks(text)
                if f.endswith(".py") and not found:
                    try:
                        compile(text, to, "exec")
                    except SyntaxError as err:
                        found = [("breaks the code at line", str(err.lineno))]
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
                stamps[to] = {"commit": last_commit(src, ref, f)}   # the source path is not kept: it can name people
        if e.get("replace") and (REPO / e["to"]).is_dir():
            # files here that the source no longer has: the stale copy goes, so the folder matches the source
            for p in sorted((REPO / e["to"]).rglob("*")):
                rel = str(p.relative_to(REPO))
                if p.is_file() and rel not in produced and "__pycache__" not in p.parts and not any(
                        k in rel for k in ("/runs/", "/_work/", "/output/")) and refused_path(rel, refused) is None:
                    removed.append(rel)
                    if not dry:
                        p.unlink()
                        stamps.pop(rel, None)
    if not dry:
        STAMPS.write_text(json.dumps(dict(sorted(stamps.items())), indent=1) + "\n")
    verb = "would write" if dry else "wrote"
    print(f"{group}: {verb} {len(wrote)} · already the same {same} · refused {len(refused)} · "
          f"{'would remove' if dry else 'removed'} {len(removed)} stale")
    for rel in removed:
        print(f"  - {rel}")
    for to in wrote:
        print(f"  + {to}")
    for to, found in refused:
        print(f"  ✗ {to}: " + ", ".join(f"{k} {w}" for k, w in found))
    return 1 if refused else 0


def refused_path(rel, refused):
    return next((r for r, _ in refused if r == rel), None)


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
