#!/usr/bin/env python3
"""Is a stage hand-off ready for whoever holds the role? One folder in; every check pass/fail with its evidence out.

    python3 components/video-edit/handoff/check.py <brief number or key> --role <role> [--brand b] [--json] [--no-drive]
    python3 components/video-edit/handoff/check.py --all --role <role> [--brand b] [--json] [--no-drive]

The stage's own list is declared in chains/<chain>.json (what the hand-off INTO the stage must carry) plus what every
hand-off carries (HANDOFF.json, START.md, returned/). A stage may name its own checker instead: the video-editor stage
keeps the 24 checks of components/video-edit/handoff_check.py, run as they are. Reads only. Exit 0 when every
hand-off passes, 1 otherwise.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage_handoff as SH  # noqa: E402


def _own_checker(path):
    """A stage's own checker, loaded from its declared path (its module's check() is its public surface)."""
    p = SH.repo() / path
    spec = importlib.util.spec_from_file_location("own_checker_%s" % p.stem, str(p))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(p.parent))
    spec.loader.exec_module(mod)
    return mod


def check(f, st, drive=True, root=None):
    """Every declared check for a hand-off folder `f` into stage `st`."""
    f = Path(f)
    root = Path(root or SH.repo())
    key, brand, role = f.name, f.parent.name, f.parent.parent.name
    out = []

    def add(group, name, ok, evidence=""):
        out.append({"group": group, "check": name, "ok": bool(ok), "evidence": evidence})

    rec = st.get("receives") or {}
    have = SH.files(f)
    man = SH.manifest(f) or {}

    # what every hand-off carries
    if st.get("numbered"):
        add("Hand-off", "Named by its brief number", re.search(r"_brief-\d{4}$", key), key)
    else:
        add("Hand-off", "Named by its run label", key == (man.get("key") or ""), key)
    for row in SH.chain(man.get("chain") or "video").get("every_handoff", {}).get("files", []):
        _file_check(add, "Hand-off", f, have, row)
    add("Hand-off", "Record says this stage and role", man.get("schema") == SH.SCHEMA and man.get("stage") == st["id"]
        and man.get("role") == role, "%s · %s · %s" % (man.get("schema"), man.get("stage"), man.get("role")))
    add("Hand-off", "Record names the brand and brief", man.get("brand") == brand and man.get("key") == key,
        "%s · %s" % (man.get("brand"), man.get("key")))
    act = man.get("activate") or {}
    start = (f / "START.md").read_text(encoding="utf-8", errors="ignore") if (f / "START.md").is_file() else ""
    add("Hand-off", "Says how to switch the stage on", act.get("say") and act.get("say") in start,
        act.get("skill") or "no activation line")
    refs = [s for s in man.get("sources") or [] if isinstance(s, dict)]
    bad = [s.get("path") or s.get("label") for s in refs
           if str(s.get("path") or s.get("label") or "").startswith(("/", "~")) or "/Users/" in json.dumps(s)]
    add("Hand-off", "Sources named by repo path or Drive label only", not bad, ", ".join(bad[:3]))

    # what this stage needs
    if man.get("packet_kind") == "grouped-video-brief":
        import group
        out.extend(group.checks(f, man))
        for variant in man.get("variants") or []:
            try:
                variant_id = group.safe(variant["id"])
            except (KeyError, ValueError):
                continue  # group.checks records the invalid structure
            child = f / "variants" / variant_id
            child_have = SH.files(child)
            for row in rec.get("files") or []:
                _file_check(add, "Stage " + variant_id, child, child_have, row)
    else:
        for row in rec.get("files") or []:
            _file_check(add, "Stage", f, have, row)
    for k in rec.get("manifest_present") or []:
        add("Stage", "Record names the %s" % k, man.get(k), str(man.get(k) or "missing"))
    for k, v in (rec.get("manifest") or {}).items():
        add("Stage", "%s is %s" % (k.replace("_", " ").capitalize(), json.dumps(v)), man.get(k) == v,
            json.dumps(man.get(k)))

    stu = man.get("studio")
    if isinstance(stu, dict) and stu.get("brief_key"):
        add("Stage", "The Studio production carries this brief's number", SH.number(stu["brief_key"]) == SH.number(key),
            "%s says %s" % (stu.get("production"), stu["brief_key"]))

    # who can pull it
    hs = SH.holders(role)
    add("Role", "Someone holds the role", hs, ", ".join(hs) or "roles.json names nobody")
    add("Role", "The stage is live", st.get("state") == "live", st.get("state") or "")

    # the system's records
    if st.get("numbered"):
        reg = SH._json(root / "components" / "image-teardown" / "briefs.json") or {}
        add("Register", "In the brief register", key in (reg.get("briefs") or {}), "components/image-teardown/briefs.json")
        twins = [k.name for k in SH.handoffs(role, brand, root) if k != f and SH.number(k.name) == SH.number(key)]
        add("Register", "Only one hand-off for this brief", not twins, ", ".join(twins))

    # the Drive copy
    if drive:
        label = SH.label_of(f, root)
        try:
            d = SH.drive_files(label)
        except RuntimeError as e:
            add("Drive", "Shared drive reachable", False, str(e))
        else:
            add("Drive", "On the Drive under the same path", d is not None, label if d is not None else "missing")
            if d is not None:
                miss = [k for k in have if k not in d]
                add("Drive", "Drive copy has every file", not miss, ("missing: " + ", ".join(miss[:5])) if miss else
                    "%d files" % len(have))
                add("Drive", "returned/ on the Drive", "returned/" in d, "")

    nxt = None
    if st.get("next") and st.get("numbered"):
        ns = SH.stage(st["next"], man.get("chain") or "video")
        nf = SH.find(SH.number(key), ns["role"], brand, root)
        nxt = {"stage": ns["id"], "role": ns["role"], "filed": str(nf.relative_to(root)) if nf else None}
    return {"key": key, "brand": brand, "role": role, "stage": st["id"], "number": SH.number(key),
            "title": man.get("title") or "", "checks": out, "passed": sum(c["ok"] for c in out), "total": len(out),
            "next": nxt}


def _file_check(add, group, f, have, row):
    p = row["path"]
    if row.get("dir"):
        add(group, "%s (%s/)" % (row["what"], p), (f / p).is_dir(), "")
        return
    n = have.get(p, 0)
    add(group, "%s (%s)" % (row["what"], p), n >= int(row.get("min_bytes") or 1), ("%d bytes" % n) if n else "missing")


def run(role, brief=None, brand=None, drive=True, chain_name="video"):
    st = SH.stage_of_role(role, chain_name)
    if not st:
        raise SystemExit("No stage in the %s chain is held by %r" % (chain_name, role))
    rec = st.get("receives") or {}
    root = SH.repo()
    folders = [k for k in SH.handoffs(role, brand, root)
               if not brief or brief in (k.name, SH.number(k.name), SH.number(k.name).lstrip("0"))]
    if rec.get("checker"):                                          # the stage keeps its own proven checks
        own = _own_checker(rec["checker"])
        dr = own._drive_root() if drive else None
        recs = own._studio_records()
        res = []
        for k in folders:
            r = own.check(k, root, dr, recs)
            r.update({"role": role, "stage": st["id"], "next": None})
            res.append(r)
        return res
    out = []
    for k in folders:                                               # a role may hold two stages: the record says which
        m = SH.manifest(k) or {}
        out.append(check(k, SH.stage(m["stage"], chain_name) if m.get("stage") else st, drive, root))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", nargs="?")
    ap.add_argument("--role", required=True)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--brand")
    ap.add_argument("--chain", default="video")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-drive", action="store_true")
    a = ap.parse_args()
    if not a.brief and not a.all:
        ap.error("name a brief, or --all")
    res = run(a.role, None if a.all else a.brief, a.brand, not a.no_drive, a.chain)
    if not res:
        raise SystemExit("No %s hand-off found for %s" % (a.role, a.brief or a.brand or "any brand"))
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        for r in res:
            print("%s · %s · %s · %d/%d" % (r["role"], r["number"], r["title"] or r["key"], r["passed"], r["total"]))
            for c in r["checks"]:
                if not c["ok"]:
                    print("  ✗ %s · %s%s" % (c["group"], c["check"], (" — " + c["evidence"]) if c["evidence"] else ""))
    sys.exit(0 if all(r["passed"] == r["total"] for r in res) else 1)


if __name__ == "__main__":
    main()
