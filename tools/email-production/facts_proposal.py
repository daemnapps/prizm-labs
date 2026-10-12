#!/usr/bin/env python3
"""A brand fact this component makes, as a PROPOSAL — never a write into brands/.

    runs/email-production/<brand>/facts-<YYYY-MM-DD>/   (UTC day; --label overrides)
        <the proposed files, at their brand-relative paths>
        run.json      each target + its sha256 as the run saw it, plus removals
        PROPOSAL.md   one screen: one guarded cp per file, one guarded git rm
                      per removal; a person copies, checks and commits

K2 (brands write wall), SI-21 2026-10-07: the pullers, the offer and store
readers, the sweep — every email-production script that used to write into
brands/<brand>/ — writes here instead, and the brand editor folds. Several writers share
one day's run, so run.json is merged, never replaced. The shape is MET-C39
(ledger as proposal)'s, copied from components/metrics/domains/pnl/clean.py
`write_note` (another component's internals: copied, not imported).

Readers keep reading brands/ — a proposal is not a fact until it is folded.
"""
import datetime
import hashlib
import json
import os
import shlex
from pathlib import Path

from paths import refuse_brand_write, workspace

MACHINE = "email-production"
RECORD = "run.json"
NOTE = "PROPOSAL.md"


def default_label():
    return "facts-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _root(root=None):
    return (Path(root) if root else workspace()).resolve()


def _rel(rel):
    return Path(rel).as_posix()


def sha256_of(path):
    path = Path(path)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_record(run):
    f = Path(run) / RECORD
    if not f.is_file():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def _save_record(run, brand, record):
    run = Path(run)
    record.update(machine=MACHINE, brand=brand, label=run.name,
                  made=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    record.setdefault("files", {})
    record.setdefault("remove", {})
    f = refuse_brand_write(run / RECORD)
    f.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_dir(brand, label=None, root=None):
    """This brand's run for the day (or for --label), made if absent."""
    d = refuse_brand_write(_root(root) / "runs" / MACHINE / brand / (label or default_label()), root)
    d.mkdir(parents=True, exist_ok=True)
    return d


def write(run, brand, rel, data, root=None):
    """Put one proposed file in the run at its brand-relative path, and record
    the brands/ file it would replace as this run saw it (None: absent)."""
    rel = _rel(rel)
    out = refuse_brand_write(Path(run) / rel, root)
    out.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        out.write_bytes(data)
    else:
        out.write_text(data, encoding="utf-8")
    record = load_record(run)
    record.setdefault("files", {})[rel] = sha256_of(_root(root) / "brands" / brand / rel)
    record.setdefault("remove", {}).pop(rel, None)
    _save_record(run, brand, record)
    return out


def remove(run, brand, rel, root=None):
    """Propose deleting one brands/ file. Records its sha256 as the run saw
    it; a file already absent has nothing to remove, and one another writer
    proposes in this run is kept, so neither is recorded."""
    rel = _rel(rel)
    base = sha256_of(_root(root) / "brands" / brand / rel)
    record = load_record(run)
    if base is None or rel in record.get("files", {}):
        return None
    record.setdefault("remove", {})[rel] = base
    _save_record(run, brand, record)
    return None


def note(run, brand, root=None):
    """PROPOSAL.md: every file in the run, its brands/ target, and one command
    each that refuses when the target is not what the run saw — so two
    proposals made from one base never overwrite each other."""
    run, root = Path(run), _root(root)
    record = load_record(run)
    brand_dir = root / "brands" / brand
    rel = lambda p: os.path.relpath(str(p), str(root))
    q = lambda p: shlex.quote(rel(p))
    table, cmds, dirs, stale = [], [], set(), 0
    for name in sorted(record.get("files", {})):
        here, there = run / name, brand_dir / name
        if not here.is_file():
            continue
        base, now = record["files"][name], sha256_of(there)
        if now == sha256_of(here):
            table.append((name, rel(there), "already in brands/"))
            continue
        if base != now:
            stale += 1
            table.append((name, rel(there), "STALE: target changed since this run; re-run the writer"))
            continue
        table.append((name, rel(there), "new" if base is None else "replaces"))
        if base is None:
            guard = "test ! -e %s" % q(there)
            if not there.parent.is_dir():
                dirs.add(there.parent)
        else:
            guard = 'test "$(shasum -a 256 < %s | cut -c1-64)" = %s' % (q(there), base)
        cmds.append('%s && cp %s %s || echo "STALE: %s changed since this run; re-run the writer"'
                    % (guard, q(here), q(there), rel(there)))
    for name in sorted(record.get("remove", {})):
        there, base = brand_dir / name, record["remove"][name]
        now = sha256_of(there)
        if now is None:
            table.append(("—", rel(there), "remove: already gone"))
            continue
        if now != base:
            stale += 1
            table.append(("—", rel(there), "STALE: target changed since this run; re-run the writer"))
            continue
        table.append(("—", rel(there), "remove"))
        cmds.append('test "$(shasum -a 256 < %s | cut -c1-64)" = %s && git rm -q %s '
                    '|| echo "STALE: %s changed since this run; re-run the writer"'
                    % (q(there), base, q(there), rel(there)))
    lines = [
        "# Email-production facts proposal — %s · %s" % (brand, record.get("label", run.name)),
        "",
        "Made %s by tools/email-production (facts_proposal.py)." % record.get("made", "—"),
        "Nothing here is in brands/ yet: email-production never writes there (K2",
        "(brands write wall), SI-21 2026-10-07). A person checks these files, copies",
        "them with the commands below, and commits them as their own.",
        "",
        "| File in this run | Target | State |",
        "|---|---|---|",
    ]
    lines += ["| %s | %s | %s |" % row for row in table] or ["| (none) | | |"]
    lines += ["", "Copy, from the workspace root. Each line acts only while the target is",
              "still what this run saw, and prints STALE otherwise:", "", "```sh"]
    lines += ["mkdir -p %s" % q(d) for d in sorted(dirs)]
    lines += cmds + ["```", "",
                     "Then commit as yourself: `git add %s && git commit`" % q(brand_dir)]
    if stale:
        lines += ["", "%d file(s) STALE: re-run the writer that made them, then fold again." % stale]
    path = refuse_brand_write(run / NOTE, root)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
