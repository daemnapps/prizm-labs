"""The two gates intake runs — both through `marketing_chain_checks.hold`
(components/marketing-chain-checks), so `check.json` is keyed by gate like every chain.

    inputs     before anything is read into an index
               both pools are where they live and hold something; every pool
               file a reader opens is readable (an unreadable one is named);
               with `--source own`, the own-ads cache is on this machine; the
               brand is a real folder under brands/                ALWAYS HOLDS
               (a default run without the own-ads cache skips that lane and
               says so in one line — OWN_SKIPPED — it does not hold)
    elements   after every swipe is normalised
               no swipe carries a format (or an organic structure) that is not
               a real row in the element library (components/elements)
               mode hold | warn — DEFAULT warn

WHY THE ELEMENTS GATE DEFAULTS TO WARN: today's pools carry labels the library
has never seen (organic structure reads that were merged away, a judged paid
format). On `hold` the index could not be built at all until those are fixed
at their source or signed into the library — both the owner's call. On `warn` the
index still files, every such swipe is marked `unknown-format` /
`unknown-structure` with the real ids beside it, and `check.json` still says
HELD for the elements gate. Nothing is passed silently, nothing is invented.
"""
import paths as P

MODES = ("hold", "warn")
# The own lane reads a rebuilt cache (components/swipe-paid/own/<account>/ads.json)
# that is not in git, so off the machine that rebuilt it the lane is empty (intake#5).
OWN_REBUILD = "python3 components/swipe-paid/own/ingest.py"
OWN_SKIPPED = ("! own lane skipped — this index holds no ad we ran, because the own-ads cache "
               f"is not on this machine; rebuild it with `{OWN_REBUILD}`")


def own_missing(found):
    """No own-ads cache here: no readable ads.json, and none that is there but broken."""
    return found["own"]["files"] == 0 and not found["own"]["unreadable"]


def quality():
    P.shared("marketing-chain-checks")
    import marketing_chain_checks as Q
    return Q


def library():
    """The element library's lookup — components/elements/machine/elements.py.
    The CODE comes from this repo; the built lists come from the workspace the
    pools are read from, so a test workspace brings its own tiny library."""
    P.shared("elements", "machine")
    import elements as E
    lib = P.workspace() / "components" / "elements" / "library"
    if lib.is_dir() and lib != E.LIBRARY:
        E.use(lib)
    return E


def inputs_problems(brand, found, source=None):
    problems = []
    real = P.brands()
    if brand not in real:
        problems.append(f"`{brand}` is not a brand folder under brands/ — real brands: {', '.join(real) or 'none'}")
    for name in ("paid", "organic"):
        f = found[name]
        if not f["there"]:
            problems.append(f"the {name} swipe pool is not at {f['path']}")
        elif not f["files"]:
            problems.append(f"the {name} swipe pool at {f['path']} holds no swipe file this tool can read")
    for lane in ("paid", "own", "organic"):                 # intake#4: a broken file holds, by name
        for path in found[lane]["unreadable"]:
            problems.append(f"the {lane} swipe pool file {path} cannot be read — repair or rebuild it; nothing was indexed")
    if source == "own" and own_missing(found):              # intake#5: asked for, not here
        problems.append(f"--source own: the own-ads cache is not on this machine (no "
                        f"{found['own']['path']}/<account>/ads.json) — rebuild it with `{OWN_REBUILD}`")
    return problems


def label_elements(records):
    """Check every carried label against its own list. Marks each record's
    `format_state` / `structure_state`; returns the gate's problems, one line
    per unknown VALUE (with how many swipes carry it), not one per swipe."""
    import pools
    E = library()
    verdict, counts = {}, {}

    def ask(element, asset, value):
        key = (element, asset, value)
        if key not in verdict:
            verdict[key] = E.check({(element, asset): value})
        counts[key] = counts.get(key, 0) + 1
        return verdict[key]

    for r in records:
        for field, lst in (("format", pools.FORMAT_LIST.get(r["kind"])),
                           ("structure", pools.STRUCTURE_LIST if r["kind"] == "video" else None)):
            value = r.get(field) or ""
            if not value:
                r[f"{field}_state"] = "empty"
                continue
            if not lst:
                r[f"{field}_state"] = f"unknown-{field}"
                r[f"{field}_problem"] = f"a {r['kind']} swipe has no {field} list to be checked against"
                counts[(field, r["kind"], value)] = counts.get((field, r["kind"], value), 0) + 1
                verdict[(field, r["kind"], value)] = [r[f"{field}_problem"]]
                continue
            bad = ask(lst[0], lst[1], value)
            r[f"{field}_list"] = "/".join(lst)
            r[f"{field}_state"] = f"unknown-{field}" if bad else "known"
            if bad:
                r[f"{field}_problem"] = bad[0]
    return [f"{n} swipe(s): {msgs[0]}" for (key, msgs), n in
            ((kv, counts[kv[0]]) for kv in sorted(verdict.items())) if msgs]


def run_gate(name, problems, run_dir, mode="hold"):
    """hold → raises Held. warn → same check.json (still says HELD), prints why, carries on.
    With no run_dir (a dry run) nothing is written."""
    Q = quality()
    try:
        Q.hold(name, problems, run_dir)
        return True
    except Q.Held as e:
        print(f"  ✗ {e}")
        if mode == "hold":
            raise
        print(f"  (the {name} gate is on warn — the index still files; check.json says HELD)")
        return False
