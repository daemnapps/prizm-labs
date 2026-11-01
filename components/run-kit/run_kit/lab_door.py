"""The shared lab door — lab-run's `--name value` pairs become one component's
own command line, read off a small manifest the component keeps.

    lab-run → <component>/lab_entry.py --name value ...
            → lab_door.run(<component>/lab_door.json, argv, env)
            → <script> [subcommand] <positionals> --brand $BRAND <flags> <out> [--dry-run]

Why it exists (LD-1 (shared lab door), from the 2026-10-17 ad-line mini setup
list §5): VE-1 (video-edit mini door) wrote one door by hand
(tools/video-edit/machine/lab_entry.py); five more would have been copies
four to eight (O1). This is that door once, the definitions in each component
(components rule 5): a `lab_door.json` beside the component's CLI and a stub
`lab_entry.py` that calls `run()` with it — the stub is what a grant row names.

The manifest:

    status        draft | approved | deprecated (a deprecated door refuses)
    about         optional — one line for a reader
    script        the CLI, repo-relative
    subcommand    a word put first, or null
    positionals   [arg names, in order] — each value a repo-relative path that exists
    flags         {arg: "--flag"} — the value passed on as given
    bool_flags    {arg: "--flag"} — yes/true/1 → the bare flag; no/false/0 or empty → nothing
    brand_flag    "--brand" (given $BRAND) or null
    out           {"flag", "runs_root_flag", "run_dir"} — where the run lands:
                    flag            "--out": the CLI is handed $OUT/<label>/ and writes there
                    runs_root_flag  "--runs-root": the CLI is handed a fresh root under
                                    $OUT (`$OUT/.runs-*`); the folder it makes there,
                    run_dir         "runs/<machine>/<brand>/<label>" read with the root
                                    standing in for the checkout's runs/, is MOVED (not
                                    copied — one copy, same disk) to $OUT/<label>/ and the
                                    scaffold left behind is removed only if empty (rmdir,
                                    never a tree delete)
                    all null        the CLI writes where it always does, in this checkout
    refuse        [arg names never accepted] — a name, or a word of a name, is refused

Several routes, one door (LD-8 (teardown door routes)): a grant row names one
script, so a component with more than one subcommand to open keeps them in ONE
manifest. Instead of the single-route keys above it carries

    status, about   as above, for the whole door
    script          optional — when given, every route must run this script
    routes          {route name: a full single-route body — script, subcommand,
                    positionals, flags, bool_flags, brand_flag, out, refuse},
                    each checked exactly as a single-route manifest is
    default_route   the route taken when the request names none

and the request picks one with `--command <name>` (absent → default_route; a
name not in `routes` is refused). `command` is the door's own word: no flag,
bool flag or positional in any manifest may take it.

Refuses (exit 2, named, before anything runs): a missing $BRAND or $OUT; a
manifest that does not parse or carries a key it does not know; a `--command`
naming no route of a routed door; an argument not
in `--name value` pairs, given twice, refused, or unknown; a value starting
with `-` (it would read as a flag) or naming a Python file (the door runs one
script, the manifest's); a positional path with a `..` part, outside this
checkout, or not there; a missing or malformed label when the run needs one;
an existing `$OUT/<label>/`.

The child runs on sys.executable with the environment passed through untouched
apart from AI_WORKSPACE, which names this checkout. Reads no key.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

YES = {"yes", "true", "1"}
NO = {"no", "false", "0", ""}
KEYS = {"status", "about", "script", "subcommand", "positionals", "flags", "bool_flags",
        "brand_flag", "out", "refuse"}
ROUTE_KEYS = KEYS - {"status", "about"}
ROUTED_KEYS = {"status", "about", "script", "routes", "default_route"}
SELECTOR = "command"                 # --command <route>; --route is a component's own flag
OUT_KEYS = {"flag", "runs_root_flag", "run_dir"}
STATUSES = {"draft", "approved", "deprecated"}
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
PY_FILE = re.compile(r"\.py\b", re.IGNORECASE)


class Refused(ValueError):
    """Every refusal; run() prints it and returns 2."""


def words(name):
    return [w for w in re.split(r"[_\-.]+", name.lower()) if w]


def refused_by(name, refuse):
    """The refuse entry `name` hits — the whole name or one of its words — or None."""
    ws = words(name)
    for r in refuse:
        if name.lower() == r.lower() or r.lower() in ws:
            return r
    return None


def load(manifest_path):
    """The manifest, checked. Anything wrong in it is Refused.

    A routed manifest loads as its default route (with the door's status and
    about), plus `routes` — every route, checked and ready — and `default_route`."""
    p = Path(manifest_path)
    try:
        m = json.loads(p.read_text())
    except (OSError, ValueError) as e:
        raise Refused(f"manifest {p} does not read: {e}")
    if not isinstance(m, dict):
        raise Refused(f"manifest {p} is not an object")
    extra = sorted(set(m) - (ROUTED_KEYS if "routes" in m else KEYS))
    if extra:
        raise Refused(f"manifest {p}: unknown key(s) {', '.join(extra)}")
    if m.get("status") not in STATUSES:
        raise Refused(f"manifest {p}: status must be one of {sorted(STATUSES)}")
    if m["status"] == "deprecated":
        raise Refused(f"manifest {p} is deprecated — this door is closed")
    if "routes" not in m:
        return check_route(m, f"manifest {p}")
    routes = m["routes"]
    if not isinstance(routes, dict) or not routes:
        raise Refused(f"manifest {p}: routes must map route names to route bodies")
    door = {k: m[k] for k in ("status", "about") if k in m}
    checked = {}
    for name, body in routes.items():
        where = f"manifest {p} route {name}"
        if not NAME.fullmatch(name):
            raise Refused(f"{where}: a route name is a plain name")
        if not isinstance(body, dict):
            raise Refused(f"{where} is not an object")
        extra = sorted(set(body) - ROUTE_KEYS)
        if extra:
            raise Refused(f"{where}: unknown key(s) {', '.join(extra)}")
        route = check_route(dict(body), where)
        if m.get("script") is not None and route["script"] != m["script"]:
            raise Refused(f"{where}: script {route['script']} is not the door's script {m['script']}")
        checked[name] = dict(route, **door)
    default = m.get("default_route")
    if default not in checked:
        raise Refused(f"manifest {p}: default_route must name one of its routes "
                      f"({', '.join(sorted(checked))})")
    return dict(checked[default], routes=checked, default_route=default)


def check_route(m, where):
    """One route's body (a single-route manifest is one), checked; defaults filled."""
    script = m.get("script")
    if not isinstance(script, str) or not script or Path(script).is_absolute() \
            or ".." in Path(script).parts:
        raise Refused(f"{where}: script must be a repo-relative path")
    m.setdefault("subcommand", None)
    for k in ("positionals", "refuse"):
        m.setdefault(k, [])
        if not isinstance(m[k], list) or not all(isinstance(x, str) and x for x in m[k]):
            raise Refused(f"{where}: {k} must be a list of names")
    for k in ("flags", "bool_flags"):
        m.setdefault(k, {})
        if not isinstance(m[k], dict) or not all(
                isinstance(v, str) and v.startswith("--") for v in m[k].values()):
            raise Refused(f"{where}: {k} must map names to --flags")
    m.setdefault("brand_flag", None)
    hit = refused_by(Path(script).stem, m["refuse"])
    if hit:
        raise Refused(f"{where}: script {script} is named by its own refuse list ({hit})")
    names = list(m["positionals"]) + list(m["flags"]) + list(m["bool_flags"])
    twice = sorted({n for n in names if names.count(n) > 1})
    if twice:
        raise Refused(f"{where}: {', '.join(twice)} declared twice")
    if SELECTOR in names:
        raise Refused(f"{where}: {SELECTOR} is the door's own --{SELECTOR} (it picks the route); "
                      f"no flag or positional may take that name")
    for n in names:
        if refused_by(n, m["refuse"]):
            raise Refused(f"{where}: {n} is declared and refused")
    out = m.setdefault("out", {})
    if not isinstance(out, dict) or set(out) - OUT_KEYS:
        raise Refused(f"{where}: out takes only {sorted(OUT_KEYS)}")
    for k in OUT_KEYS:
        out.setdefault(k, None)
    if out["flag"] and out["runs_root_flag"]:
        raise Refused(f"{where}: out names both a flag and a runs root")
    if bool(out["runs_root_flag"]) != bool(out["run_dir"]):
        raise Refused(f"{where}: out.runs_root_flag and out.run_dir come together")
    if out["run_dir"]:
        rd = out["run_dir"]
        left = rd.replace("<brand>", "").replace("<label>", "")
        if not rd.startswith("runs/") or "<" in left or ">" in left or ".." in Path(rd).parts:
            raise Refused(f"{where}: out.run_dir must read runs/…, with only <brand> and <label>")
    return m


def find_repo(manifest_path):
    """This checkout: the first folder upward of the manifest holding components/
    and brands/. AI_WORKSPACE is not read — the door SETS it to this answer."""
    here = Path(manifest_path).resolve()
    for d in here.parents:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise Refused(f"no checkout found upward of {here}")


def repo_path(repo, name, value):
    """A positional's value, resolved inside `repo` (the VE-1 kit check)."""
    raw = Path(value)
    if ".." in raw.parts:
        raise Refused(f"--{name} {value} has a '..' part; name it from the repo root")
    p = (raw if raw.is_absolute() else repo / raw).resolve()
    if p != repo and repo not in p.parents:
        raise Refused(f"--{name} {value} is outside this checkout ({repo})")
    if not p.exists():
        raise Refused(f"--{name} {value} is not there ({p})")
    return p


def pairs(argv):
    """lab-run's `--name value` pairs as {name: value}; `-` in a name reads as `_`."""
    argv = list(argv)
    if len(argv) % 2:
        raise Refused(f"arguments come in --name value pairs; got {argv}")
    got = {}
    for i in range(0, len(argv), 2):
        key, value = argv[i], argv[i + 1]
        if not key.startswith("--") or len(key) < 3:
            raise Refused(f"{key!r} is not a --name")
        name = key[2:].replace("-", "_")
        if name in got:
            raise Refused(f"--{name} given twice")
        got[name] = value
    return got


def pick(m, args):
    """The route the request names with --command (absent → default_route) and
    the arguments left for it. A single-route manifest is its own route and its
    arguments pass untouched — there --command is as unknown as any other name."""
    if "routes" not in m:
        return m, args
    args = dict(args)
    name = args.pop(SELECTOR, m["default_route"])
    if name not in m["routes"]:
        raise Refused(f"--{SELECTOR} {name!r} is not a route of this door "
                      f"(its routes: {', '.join(sorted(m['routes']))})")
    return m["routes"][name], args


def needs_label(m):
    out = m["out"]
    return bool(out["flag"] or out["runs_root_flag"])


def command(m, args, repo, brand, dest, runs_root):
    """The child's argv (interpreter first). Refused when an argument does not fit."""
    known = set(m["positionals"]) | set(m["flags"]) | set(m["bool_flags"])
    if needs_label(m):
        known.add("label")
    for name in args:
        hit = refused_by(name, m["refuse"])
        if hit:
            raise Refused(f"--{name} is refused by this door ({hit})")
    unknown = sorted(set(args) - known)
    if unknown:
        why = " — $BRAND comes from lab-run" if "brand" in unknown and m["brand_flag"] else ""
        raise Refused(f"unknown argument(s) {', '.join('--' + u for u in unknown)}{why}")
    for name, value in args.items():
        if value.startswith("-"):
            raise Refused(f"--{name} {value!r} starts with '-' and would read as a flag")
        if PY_FILE.search(value):
            raise Refused(f"--{name} {value!r} names a Python file; this door runs {m['script']} only")
    script = repo / m["script"]
    if not script.is_file():
        raise Refused(f"{m['script']} is not in this checkout ({script})")
    cmd = [sys.executable, str(script)]
    if m["subcommand"]:
        cmd.append(m["subcommand"])
    for name in m["positionals"]:
        if not args.get(name):
            raise Refused(f"--{name} is required (a repo-relative path)")
        cmd.append(str(repo_path(repo, name, args[name])))
    if m["brand_flag"]:
        cmd += [m["brand_flag"], brand]
    for name, flag in m["flags"].items():
        if args.get(name):
            cmd += [flag, args[name]]
    for name, flag in m["bool_flags"].items():
        v = args.get(name, "").strip().lower()
        if v in YES:
            cmd.append(flag)
        elif v not in NO:
            raise Refused(f"--{name} {args[name]!r}: say yes or no")
    if m["out"]["flag"]:
        cmd += [m["out"]["flag"], str(dest)]
    if m["out"]["runs_root_flag"]:
        cmd += [m["out"]["runs_root_flag"], str(runs_root)]
    return cmd


def child_env(env, repo):
    env = dict(env)
    env["AI_WORKSPACE"] = str(repo)      # runs resolve against this checkout, not ~/Projects/workspace
    return env


def run(manifest_path, argv, env, run=subprocess.call, repo=None):
    """One door call: refusals return 2 before anything runs; else the child's code."""
    try:
        m = load(manifest_path)
        repo = Path(repo).resolve() if repo else find_repo(manifest_path)
        missing = [n for n in ("BRAND", "OUT") if not env.get(n)]
        if missing:
            raise Refused(f"${' and $'.join(missing)} not set — lab-run sets them; "
                          f"run {m['script']} directly by hand")
        brand, out = env["BRAND"], Path(env["OUT"])
        if not NAME.fullmatch(brand):
            raise Refused(f"$BRAND {brand!r} is not a plain name")
        m, args = pick(m, pairs(argv))
        dest = None
        if needs_label(m):
            label = args.get("label", "")
            if not NAME.fullmatch(label):
                raise Refused(f"--label {label!r}: a plain name is required — the run lands in $OUT/<label>/")
            dest = out / label
            if dest.exists():
                raise Refused(f"{dest} already exists — refusing to overwrite it")
        command(m, args, repo, brand, dest, Path("<runs-root>"))      # every refusal, before any mkdir
    except Refused as e:
        print(f"lab_door: {e}")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    runs_root = None
    if m["out"]["runs_root_flag"]:
        runs_root = Path(tempfile.mkdtemp(prefix=".runs-", dir=str(out)))
    cmd = command(m, args, repo, brand, dest, runs_root)
    print("running: " + " ".join(cmd))
    rc = run(cmd, env=child_env(env, repo))
    if runs_root is not None:
        rel = m["out"]["run_dir"].replace("<brand>", brand).replace("<label>", args["label"])
        made = runs_root.joinpath(*Path(rel).parts[1:])         # the root stands in for runs/
        if made.is_dir():
            shutil.move(str(made), str(dest))
            print(f"lab_door: run folder → {dest}")
        else:
            print(f"lab_door: {m['script']} made no run folder (exit {rc})")
        for d in [made.parent, *made.parent.parents]:           # the scaffold, only if empty
            if d != runs_root and runs_root not in d.parents:
                break
            try:
                d.rmdir()
            except OSError:
                pass
    elif dest is not None:
        print(f"lab_door: output → {dest}" if dest.exists()
              else f"lab_door: {m['script']} wrote nothing to {dest} (exit {rc})")
    else:
        print(f"lab_door: {m['script']} writes where it always does, in this checkout ({repo})")
    return rc
