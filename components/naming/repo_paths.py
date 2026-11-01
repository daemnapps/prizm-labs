#!/usr/bin/env python3
"""Stored paths that open from anywhere — builder card rule 4 (stored data references).

A file reference written into a record, layout, card, brief or run file is a
repo-relative path or a "Shared Assets/…" label, never an absolute machine path.
This tool finds the ones that are not, and rewrites the two kinds that have one
true portable form:

    /Users/<anyone>/Projects/workspace/<rest>                     -> <rest>
    ~/Projects/workspace/<rest>                                   -> <rest>
    <anything>/GoogleDrive-<account>/Shared drives/Shared Assets/<rest> -> Shared Assets/<rest>

Everything else is REPORTED, never rewritten:
    scratch  /private/tmp, /tmp, /var/folders, /private/var/folders — the file is
             gone; no target is ever invented for it
    other    any other machine path (/Users/…, /Volumes/…, another shared drive,
             a worktree copy, file:///…)

    repo_paths.py scan [roots...]            report (default roots: runs components)
    repo_paths.py fix  [roots...] [--apply]  rewrite in place; dry run without --apply

Only .json .jsonl .md .yaml .yml .csv text files are touched. The rewrite is a
string replacement on the raw text, so a JSON file keeps its exact formatting.
Never written, only reported: brands/ (read-only to machines), lab/, tests and
fixtures, a component's prompts/ and templates/, CLAUDE.md / README.md / SKILL.md / AGENTS.md, and
runs/system-integration/ (reviews that quote a bad path as evidence), runs/notify/
(a watcher outside this repo compares its seen-list as raw strings).
A file that changes while it is being rewritten is left alone and reported.

Python 3.9.6, stdlib only.
"""
import argparse, os, re, sys, tempfile, shutil
from pathlib import Path

TEXT_EXT = {".json", ".jsonl", ".md", ".yaml", ".yml", ".csv"}
MAX_BYTES = 20 * 1024 * 1024
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
DOC_NAMES = {"CLAUDE.md", "README.md", "SKILL.md", "AGENTS.md"}
REPORT_ONLY_DIRS = {"tests", "fixtures"}                      # any folder of this name
COMPONENT_ONLY_DIRS = {"prompts", "templates"}                # definitions, inside components/ only
# runs/notify/: Outlier's watcher (outside this repo) keeps a seen-list of absolute paths and
# re-announces anything not on it — rewriting it re-sent 37 "video back" notes on 2026-10-28.
REPORT_ONLY_TOP = ("brands/", "lab/", "runs/system-integration/", "runs/notify/")

_SEG = r"[^/\s\"'`<>|\\]"                                      # one path-segment character
_END = r"(?=/|[\s\"'`)\],}>\\]|$)"
_PREFIX_CH = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-@~/")
_BAD_BEFORE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:/~-@")

# Each rewrite is found by a LITERAL anchor (fast), then its path start is found by
# walking left — a regex lookbehind at every position was 8 MB/s.
_REPO_ANCHOR = re.compile(re.escape("/Projects/workspace/"))
_REPO_PREFIX = re.compile(r"(?:/Users/[\w.@-]+|/home/[\w.@-]+|~)\Z")
_DRIVE_ANCHOR = re.compile(r"/GoogleDrive(?:-%s+)?/Shared drives/Shared Assets" % _SEG + _END)
_DRIVE_PREFIX = re.compile(r"~?(?:/[\w.@ -]+)*\Z")

# what still counts as a machine path once those are rewritten
_ABS = re.compile(r"/Users/|/home/|/private/|/var/folders/|/tmp/|/Volumes/|~/Library/CloudStorage/|~/Projects/")
_SCRATCH = ("/private/tmp/", "/tmp/", "/var/folders/", "/private/var/folders/")
_SHOW = re.compile(r"[^\s\"'`<>|\\)\]}]*")


def _starts_path(text, i):
    """True when a path may begin at text[i]: start of text, after a delimiter, or after a
    JSON escape (\\n, \\t) — never mid-word or inside a URL."""
    if i == 0 or text[i - 1] not in _BAD_BEFORE:
        return True
    return i >= 2 and text[i - 2] == "\\" and text[i - 1] in "nt"


def _walk_left(text, i):
    """Where the path holding text[i] begins (a JSON escape's letter is not part of it)."""
    s = i
    while s > 0 and text[s - 1] in _PREFIX_CH:
        s -= 1
    if s > 0 and text[s - 1] == "\\" and s < i and text[s] in "nt":
        s += 1
    return s


def _rewrite(text, anchor, prefix_ok, repl):
    """Replace prefix+anchor with repl wherever prefix_ok(prefix) and the path starts cleanly.
    Returns (new text, count)."""
    out, last, n = [], 0, 0
    for m in anchor.finditer(text):
        s = _walk_left(text, m.start())
        if s < last or not prefix_ok(text[s:m.start()]) or not _starts_path(text, s):
            continue
        out.append(text[last:s])
        out.append(repl)
        last = m.end()
        n += 1
    if not n:
        return text, 0
    out.append(text[last:])
    return "".join(out), n


def _own_root(r):
    return re.compile(re.escape(r + "/"))


def _root():
    try:
        sys.path.append(str(Path(__file__).resolve().parent.parent / "run-kit"))
        from run_kit.paths import repo
        return repo(Path(__file__))
    except Exception:  # noqa: BLE001 — a stray copy of this file still works
        return None


_ROOT = None


def _roots(root):
    """Every spelling of this checkout's own root (a mini worktree sits in /private/tmp)."""
    global _ROOT
    if root is None:
        if _ROOT is None:
            _ROOT = _root() or ""
        root = _ROOT
    if not root:
        return []
    out = []
    for r in {str(root), os.path.realpath(str(root))}:
        r = r.rstrip("/")
        out.append(r)
        if r.startswith("/private/"):
            out.append(r[len("/private"):])
    return sorted(set(out), key=len, reverse=True)


def _portable(text, root=None):
    n = 0
    for r in _roots(root):
        if text == r:
            return ".", n + 1
        if r + "/" in text:
            text, k = _rewrite(text, _own_root(r), lambda p: p == "", "")
            n += k
    if "/Projects/workspace/" in text:
        text, k = _rewrite(text, _REPO_ANCHOR, lambda p: bool(_REPO_PREFIX.match(p)), "")
        n += k
    if "/Shared drives/Shared Assets" in text:
        text, k = _rewrite(text, _DRIVE_ANCHOR, lambda p: bool(_DRIVE_PREFIX.match(p)), "Shared Assets")
        n += k
    return text, n


def to_portable(s, root=None):
    """The portable spelling of `s` (a path, a Path, or any text holding paths).

    A clone of this workspace becomes repo-relative; a Drive mount of Shared Assets
    becomes "Shared Assets/…". This checkout's own root is stripped too, wherever it
    sits (a worktree in /private/tmp), so a writer can pass any path it built.
    Anything else comes back unchanged — see kind() to tell why."""
    if s is None:
        return s
    return _portable(str(s), root)[0]


_TOP = ("runs/", "components/", "brands/", "lab/", "platform/", "team/", "new-workflow-design/")


def to_local(obj, root=None, labels=None):
    """The reader's half of to_portable, for a record a running engine reads back (json-loaded
    dict/list/str): a repo-relative path under runs/ components/ brands/ lab/ platform/ … that
    exists in this checkout becomes absolute under it; a "Shared Assets/…" label goes through
    `labels(label)` when given (e.g. gdrive-creator's mount or readable()), else stays a label.
    Anything else is returned as it was, so a reader that joins with pathlib still works."""
    _roots(root)                                    # fills _ROOT on first use
    given = root if root is not None else _ROOT
    base = Path(str(given)) if given else None

    def one(v):
        if isinstance(v, dict):
            return {k: one(x) for k, x in v.items()}
        if isinstance(v, list):
            return [one(x) for x in v]
        if not isinstance(v, str) or not v or v.startswith("/") or "\n" in v:
            return v
        if labels is not None and (v == "Shared Assets" or v.startswith("Shared Assets/")):
            got = labels(v)
            return str(got) if got else v
        if base is not None and v.startswith(_TOP) and len(v) < 1024 and (base / v).exists():
            return str(base / v)
        return v
    return one(obj)


def kind(path):
    """'scratch' | 'other' for a machine path to_portable cannot fix; None when portable."""
    h = hits(str(path))
    return h[0][0] if h and str(path).startswith((h[0][1], "file://")) else None


def hits(text):
    """Every machine path left in `text`: [(kind, shown path)]. Run after to_portable."""
    out = []
    for m in _ABS.finditer(text):
        i = m.start()
        url = text[max(0, i - 7):i] == "file://"
        if not url and not _starts_path(text, i):
            continue
        shown = ("file://" if url else "") + m.group(0) + _SHOW.match(text, m.end()).group(0)
        p = m.group(0) + _SHOW.match(text, m.end()).group(0)
        out.append(("scratch" if p.startswith(_SCRATCH) else "other", shown[:200]))
    return out


def count_fixable(text, root=None):
    """How many references to_portable would rewrite in `text`."""
    return _portable(text, root)[1]


# ---- walking ------------------------------------------------------------------------------

def _rel(p, base):
    try:
        return Path(p).resolve().relative_to(base).as_posix()
    except ValueError:
        return Path(p).as_posix()


def report_only(rel):
    """True for a file this tool may report on but must never write."""
    parts = rel.split("/")
    if rel.startswith(REPORT_ONLY_TOP) or parts[-1] in DOC_NAMES or parts[-1].startswith("test_"):
        return True
    if any(d in REPORT_ONLY_DIRS for d in parts[:-1]):
        return True
    return rel.startswith("components/") and any(d in COMPONENT_ONLY_DIRS for d in parts[:-1])


def iter_files(paths, skip=(), base=None):
    """Text record files under `paths`, in the order given, each once."""
    base = Path(base or _root() or os.getcwd()).resolve()
    skip = [s.rstrip("/") for s in skip]
    seen = set()

    def skipped(rel):
        return any(rel == s or rel.startswith(s + "/") for s in skip)

    for p in paths:
        p = Path(p)
        if not p.is_absolute():
            p = base / p
        if p.is_file():
            cands = [p]
        elif p.is_dir():
            cands = None
        else:
            continue
        if cands is not None:
            for f in cands:
                rel = _rel(f, base)
                if f.suffix.lower() in TEXT_EXT and rel not in seen and not skipped(rel):
                    seen.add(rel)
                    yield f, rel
            continue
        for d, dirs, files in os.walk(p):
            rd = _rel(d, base)
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")
                             and not skipped((rd + "/" + x) if rd != "." else x))
            for name in sorted(files):
                if Path(name).suffix.lower() not in TEXT_EXT:
                    continue
                f = Path(d) / name
                rel = (rd + "/" + name) if rd != "." else name
                if rel in seen or skipped(rel):
                    continue
                seen.add(rel)
                yield f, rel


def _read(f):
    try:
        st = f.stat()
        if st.st_size > MAX_BYTES:
            return None, st, "over 20 MB"
        return f.read_bytes().decode("utf-8"), st, None
    except UnicodeDecodeError:
        return None, None, "not utf-8"
    except OSError as e:
        return None, None, str(e)


_QUICK = ("/Users/", "/home/", "/private/", "/var/folders/", "/tmp/", "/Volumes/", "~/Library/", "~/Projects/")


def _one(f, rel, root=None):
    text, st, err = _read(f)
    row = {"file": rel, "fixable": 0, "scratch": 0, "other": 0, "left": [], "error": err,
           "report_only": report_only(rel)}
    if text is None or not any(q in text for q in _QUICK):
        return row, text, st
    row["fixable"] = count_fixable(text, root)
    for k, shown in hits(to_portable(text, root)):
        row[k] += 1
        if len(row["left"]) < 5:
            row["left"].append(shown)
    return row, text, st


def _summary(rows):
    s = {"files_scanned": len(rows), "files_with_paths": 0, "fixable": 0, "scratch": 0, "other": 0,
         "files_fixable": 0, "files_left": 0}
    for r in rows:
        n = r["fixable"] + r["scratch"] + r["other"]
        if n:
            s["files_with_paths"] += 1
        s["fixable"] += r["fixable"]
        s["scratch"] += r["scratch"]
        s["other"] += r["other"]
        s["files_fixable"] += bool(r["fixable"])
        s["files_left"] += bool(r["scratch"] or r["other"])
    return s


def scan(paths, skip=(), base=None, root=None):
    """Report machine paths under `paths`. Returns {"summary", "files": [rows with any path]}."""
    rows = [_one(f, rel, root)[0] for f, rel in iter_files(paths, skip, base)]
    return {"summary": _summary(rows), "files": [r for r in rows if r["fixable"] or r["scratch"] or r["other"]]}


def _write_same(f, st, new):
    """Atomic in-place write; refuses when the file moved on since it was read."""
    now = f.stat()
    if (now.st_mtime_ns, now.st_size) != (st.st_mtime_ns, st.st_size):
        return False
    fd, tmp = tempfile.mkstemp(prefix="." + f.name + ".", dir=str(f.parent))
    try:
        with os.fdopen(fd, "wb") as h:
            h.write(new.encode("utf-8"))
        shutil.copymode(str(f), tmp)
        now = f.stat()
        if (now.st_mtime_ns, now.st_size) != (st.st_mtime_ns, st.st_size):
            os.unlink(tmp)
            return False
        os.replace(tmp, str(f))
        return True
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def fix(paths, apply=False, skip=(), base=None, root=None):
    """Rewrite the fixable references under `paths` (dry run unless apply=True).

    Returns scan()'s shape plus "rewritten" (files changed or, dry, that would be),
    "busy" (changed while being read — left alone) and "report_only" (would need it,
    may not be written: brands/, lab/, docs, tests)."""
    rows, rewritten, busy, held = [], [], [], []
    for f, rel in iter_files(paths, skip, base):
        row, text, st = _one(f, rel, root)
        rows.append(row)
        if not row["fixable"]:
            continue
        if row["report_only"]:
            held.append(rel)
            continue
        new = to_portable(text, root)
        if new == text:
            continue
        if apply and not _write_same(f, st, new):
            busy.append(rel)
            continue
        rewritten.append(rel)
    return {"summary": _summary(rows), "files": [r for r in rows if r["fixable"] or r["scratch"] or r["other"]],
            "rewritten": rewritten, "busy": busy, "report_only": held, "applied": bool(apply)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["scan", "fix"])
    ap.add_argument("roots", nargs="*", default=["runs", "components"])
    ap.add_argument("--apply", action="store_true", help="fix: write the files (default is a dry run)")
    ap.add_argument("--skip", action="append", default=[], help="repo-relative folder or file to leave alone")
    ap.add_argument("--json", help="write the full report as JSON here")
    ap.add_argument("--list", action="store_true", help="print one line per file with a machine path")
    a = ap.parse_args(argv)
    res = scan(a.roots, a.skip) if a.cmd == "scan" else fix(a.roots, a.apply, a.skip)
    if a.list:
        for r in res["files"]:
            print("%5d fixable %5d scratch %5d other  %s%s" % (r["fixable"], r["scratch"], r["other"], r["file"],
                                                              "  (report only)" if r["report_only"] else ""))
    s = res["summary"]
    print("scanned %(files_scanned)d files; %(files_with_paths)d hold machine paths: "
          "%(fixable)d fixable in %(files_fixable)d files, %(scratch)d scratch + %(other)d other "
          "left in %(files_left)d files" % s)
    if a.cmd == "fix":
        print("%s %d files; %d busy (changed while read, left alone); %d report-only"
              % ("rewrote" if a.apply else "would rewrite", len(res["rewritten"]), len(res["busy"]),
                 len(res["report_only"])))
    if a.json:
        import json
        Path(a.json).write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
