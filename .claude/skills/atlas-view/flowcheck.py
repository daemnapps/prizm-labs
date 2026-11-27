#!/usr/bin/env python3
"""Check every claim in a component's flow file against the repo and the compiled atlas.

    python3 flowcheck.py <flows-dir> [<component> …] [--json]

A claim is a checkable field on a flow item (SCHEMA.md in the flows folder): `path` exists,
`node` is on the atlas, `component` exists, a refusal `code` appears in the component's non-test
code, a `cite` path has not moved since its sha, and the engine owner in `who` matches the
registry. States: agrees · stated · conflicts (a person-edited item fails) · draft-error (an
unedited drafted item fails) · stale (its cite moved). Reads only; writes nothing.
"""
import os
import json, re, subprocess, sys
from pathlib import Path


def root():
    try:
        return Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    except Exception:
        return Path.cwd()


ROOT = root()
DATA = Path(os.environ["ATLAS_DATA"]) if os.environ.get("ATLAS_DATA") else ROOT / "platform/data/atlas/data.json"  # ATL-53 (atlas daily): a fresh compile wins
PLACEHOLDER = re.compile(r"[<{*]")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)


def moved_since(path, sha):
    """True when `path` changed between `sha` and HEAD; None when the sha is unknown."""
    if git("cat-file", "-e", f"{sha}^{{commit}}").returncode:
        return None
    return git("diff", "--quiet", sha, "HEAD", "--", path).returncode == 1


def check_path(p):
    first = re.split(r"\s+·\s+|\s+\(|,\s+", str(p).strip())[0].strip().rstrip("/")
    m = PLACEHOLDER.search(first)
    probe = first[:m.start()].rsplit("/", 1)[0] if m else first
    if not probe:
        return None, "no checkable prefix"
    ok = (ROOT / probe).exists()
    return ok, f"{probe} {'exists' if ok else 'is not in the repo'}"


def code_files(component, extra=()):
    bases = [ROOT / "components" / component]
    for x in extra:
        m = PLACEHOLDER.search(x or "")
        x = (x[:m.start()] if m else (x or "")).strip().rstrip("/")
        if x and (ROOT / x).exists():
            bases.append(ROOT / x)
    seen = set()
    for f in (g for b in bases for g in ([b] if b.is_file() else b.rglob("*"))):
        if f in seen:
            continue
        seen.add(f)
        if f.is_file() and f.suffix in {".py", ".js", ".ts", ".sh", ".json", ".mjs"} \
                and not f.name.startswith("test_") and "tests" not in f.parts and "__pycache__" not in f.parts \
                and not (f.suffix == ".json" and f.name.startswith("flow")):
            # a flow file inside its own component restates the claims; it must never confirm them (2026-10-02)
            yield f


def check_code(component, code, extra=()):
    for f in code_files(component, extra):
        try:
            if code in f.read_text(errors="ignore"):
                return True, f"found in {f.relative_to(ROOT)}"
        except Exception:
            pass
    return False, f"`{code}` appears nowhere in components/{component}'s non-test code"


def owners(atlas, component):
    tools = {t["path"].split("/")[-1]: t for t in atlas["system"]["tools"] if t.get("station") == "components"}
    res = {c["name"]: c for c in atlas["system"]["components"]}
    return " ".join(x for x in [(tools.get(component) or {}).get("owner"), (res.get(component) or {}).get("owner")] if x)


def walk(o, where="flow"):
    """Yield (where, item) for every dict in the flow, the picture's fields only."""
    if isinstance(o, dict):
        yield where, o
        for k, v in o.items():
            if k in {"drafted", "review", "sources_read", "chart", "picture", "table", "facts", "drift", "facts_cite", "character", "issues", "howto", "issues_next", "stage", "target"}:
                continue
            yield from walk(v, f"{where}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{where}[{i}]")


def check_flow(flow, atlas):
    comp = flow["component"]
    nodes = {n["id"] for n in atlas["chain"]["nodes"]}
    out = []

    def add(where, item, field, claim, ok, fact):
        if ok is None:
            state = "stated"
        elif ok:
            state = "agrees"
        else:
            state = "conflicts" if item.get("edited") else "draft-error"
        out.append(dict(where=where, id=item.get("id") or item.get("code") or field, label=item.get("label") or item.get("means") or "",
                        field=field, claim=claim, state=state, fact=fact, edited=item.get("edited")))

    for where, it in walk(flow):
        if "path" in it and isinstance(it["path"], str):
            ok, fact = check_path(it["path"])
            add(where, it, "path", f'lives at {it["path"]}', ok, fact)
        if "node" in it:
            ok = it["node"] in nodes
            add(where, it, "node", f'is the atlas node {it["node"]}', ok, "on the atlas" if ok else "no such node on the atlas")
        if "component" in it and where != "flow":
            ok = (ROOT / "components" / it["component"]).is_dir()
            add(where, it, "component", f'is the component {it["component"]}', ok, "exists" if ok else "no such component folder")
        if ".refuses[" in where and it.get("code") and not it.get("proposed"):
            eng = flow.get("engine") or {}
            ok, fact = check_code(comp, it["code"], [it.get("path"), eng.get("path")] + list(eng.get("code_paths") or []))
            add(where, it, "code", f'refuses as `{it["code"]}`', ok, fact)
        if it.get("cite") and "@" not in str(it["cite"]):
            ok = (ROOT / str(it["cite"])).exists()   # SCHEMA §3: a file the same run wrote is cited without @sha
            add(where, it, "cite", f'restates {it["cite"]}', ok, "a file the run wrote; exists" if ok else "no such file")
            continue
        if it.get("cite"):
            p, _, sha = str(it["cite"]).rpartition("@")
            if p.startswith("platform/data/atlas/"):
                add(where, it, "cite", f'restates {it["cite"]}', None, "the atlas's own compiled output: not a source to check against")
                continue
            mv = moved_since(p, sha) if p and sha else None
            if mv is None:
                add(where, it, "cite", f'restates {it["cite"]}', False, "the cited sha is not a commit here")
            elif mv:
                out.append(dict(where=where, id=it.get("id") or "cite", label=it.get("label") or "", field="cite",
                                claim=f'restates {it["cite"]}', state="stale", fact=f"{p} changed after {sha}", edited=it.get("edited")))
            else:
                add(where, it, "cite", f'restates {it["cite"]}', True, f"{p} unchanged since {sha}")
    pic = flow.get("picture")
    if pic:
        ids = {it.get("id") for _, it in walk({k: v for k, v in flow.items() if k not in ("picture", "chart")}) if isinstance(it, dict) and it.get("id")}
        for g in pic.get("groups") or []:
            for n in g.get("items") or []:
                missing = [c for c in n.get("covers") or [] if c not in ids]
                ok = bool(n.get("covers")) and not missing
                add(f'flow.picture.{n.get("name")}', n, "covers", f'stands for {", ".join(n.get("covers") or []) or "nothing"}', ok,
                    "every covered item is in the flow" if ok else (f"not in the flow: {', '.join(missing)}" if missing else "a picture box must stand for at least one item"))
    if pic:
        covered = {c for g in pic.get("groups") or [] for n in g.get("items") or [] for c in n.get("covers") or []}
        omit = pic.get("omit") or {}
        for sec_ in ("feeds", "sources", "outputs", "used_by"):
            for g in flow.get(sec_) or []:
                for it in (g.get("items") if "items" in g else [g]):
                    if it.get("id") and it["id"] not in covered:
                        if flow.get("stage") == "fit" and not omit.get(it["id"]):
                            add(f"flow.{sec_}.{it['id']}", it, "drawn", f"{it['id']} is drawn in the picture", None, "a gap at the fit stage: no box yet")
                            continue
                        add(f"flow.{sec_}.{it['id']}", it, "drawn", f"{it['id']} is drawn in the picture", bool(omit.get(it["id"])),
                            f"left out on purpose: {omit[it['id']]}" if omit.get(it["id"]) else "no picture box stands for it and no reason is given")
    chart = flow.get("chart")
    if chart:
        ids = {it.get("id") for _, it in walk({k: v for k, v in flow.items() if k != "chart"}) if isinstance(it, dict) and it.get("id")}
        for n in chart.get("nodes") or []:
            missing = [c for c in n.get("covers") or [] if c not in ids]
            ok = bool(n.get("covers")) and not missing
            add(f'flow.chart.{n.get("id")}', n, "covers", f'summarises {", ".join(n.get("covers") or []) or "nothing"}', ok,
                "every covered item is in the flow" if ok else (f"not in the flow: {', '.join(missing)}" if missing else "a chart node must cover at least one item"))
        nids = {n.get("id") for n in chart.get("nodes") or []}
        for ed in chart.get("edges") or []:
            if ed[0] not in nids or ed[1] not in nids:
                add("flow.chart.edges", {"id": "edge"}, "edge", f"{ed[0]} → {ed[1]}", False, "an edge names a node the chart does not have")
    ns = [i.get("n") for i in flow.get("issues") or []]
    if ns:
        ok = all(isinstance(x, int) for x in ns) and len(set(ns)) == len(ns) and max(ns) < (flow.get("issues_next") or 0)
        add("flow.issues", {"id": "issues"}, "numbers", "every issue has a fixed, unique number below issues_next", ok,
            "numbers are unique" if ok else f"numbers {ns}, next {flow.get('issues_next')}")
    hs = (flow.get("howto") or {}).get("source")
    if hs and "@" not in hs:
        ok = (ROOT / hs).exists()   # SCHEMA §3: the run's own memo, cited without @sha
        add("flow.howto", {"id": "howto"}, "cite", f"restates {hs}", ok, "a file the run wrote; exists" if ok else "no such file")
        hs = None
    if hs:
        p_, _, sha_ = hs.rpartition("@")
        mv = moved_since(p_, sha_)
        if mv:
            out.append(dict(where="flow.howto", id="howto", label="How to use it", field="cite", claim=f"restates {hs}", state="stale", fact=f"{p_} changed after {sha_}", edited=None))
        else:
            add("flow.howto", {"id": "howto"}, "cite", f"restates {hs}", mv is not None, "unchanged" if mv is False else "the cited sha is not a commit here")
    who = flow.get("who") or []
    if who:
        reg = owners(atlas, comp)
        names = re.findall(r"\b(developer|designer|email_lead|owner|editor|creator)\b", str(who[0][1]))
        if not reg or not names:
            add("flow.who[0]", {"id": "who"}, "who", f"engine owner: {who[0][1]}", None, "no registry owner to compare")
        else:
            ok = names[0] in reg
            add("flow.who[0]", {"id": "who", "edited": (flow.get("who_edited"))}, "who", f"engine owner: {who[0][1]}", ok,
                f"registry says: {reg[:120]}")
    moved = []
    for s in flow.get("sources_read") or []:
        p, _, sha = str(s).rpartition("@")
        if p.startswith("platform/data/atlas/"):
            continue  # the atlas's own compiled output recompiles every few minutes; never a source of staleness
        if p and sha and moved_since(p, sha):
            moved.append(p)
    counts = {}
    for c in out:
        counts[c["state"]] = counts.get(c["state"], 0) + 1
    return dict(component=comp, claims=out, counts=counts, sources_moved=moved,
                review=flow.get("review") or {}, drafted=flow.get("drafted") or {})


def load_flows(flows_dir):
    return {p.stem: json.loads(p.read_text()) for p in sorted(Path(flows_dir).glob("*.json"))}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    atlas = json.loads(DATA.read_text())
    flows = load_flows(args[0])
    names = args[1:] or list(flows)
    res = {n: check_flow(flows[n], atlas) for n in names if n in flows}
    if "--json" in sys.argv:
        print(json.dumps(res, indent=1))
        return
    for n, r in res.items():
        print(f"{n}: " + " · ".join(f"{v} {k}" for k, v in sorted(r["counts"].items())) +
              (f" · {len(r['sources_moved'])} sources moved" if r["sources_moved"] else ""))
        for c in r["claims"]:
            if c["state"] not in ("agrees", "stated"):
                print(f"   {c['state']:<12} {c['where']}: {c['claim']} — {c['fact']}")


if __name__ == "__main__":
    main()
