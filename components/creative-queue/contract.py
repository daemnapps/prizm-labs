"""The production contract, QB-5 (production contract): one adapter manifest per production component.

    contract.py check <adapter.json>   exit 0 valid · 1 invalid, one "<field>: why" line per problem
    contract.py find [--root R]        every components/*/adapter.json and components/*/*/adapter.json (a component's
                                       own adapter folder), repo-relative, one a line — found the way the page kit
                                       finds _templates/<family>.sources.json: by its fixed name, never registered

The shape and the word lists are contract.schema.json (definitions, the team's). An adapter.json names its `kind` (a
components/naming/stages.json `types` id), the argv of `report`, `detail` and `apply` (argv[0] a file under
components/: no lab code, builder card rule 12) and the change `words` it takes — the shared ones, plus any
kind-specific word it lists in `kind_words`. go / schedule / send / approve and any paid or outbound effect are never
change words: they stay approvals (a queue decision plus a press on the tool's machine, with a receipt).
Optional, LD-83 (picture try first): a `try` argv (the same args as apply; makes preview results, commits nothing)
with `try_words`, the change words it accepts — each already in `words`, none refused. `try` is a verb, never a
change word.

Callers: `load(path)` (a valid manifest, or ValueError naming the field) and `command(manifest, verb, args)` (the
argv to run, a .py under sys.executable). Stdlib only, Python 3.9.6.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402

SCHEMA = json.loads((HERE / "contract.schema.json").read_text())
SHARED = tuple(SCHEMA["shared_words"])
REFUSED = tuple(SCHEMA["refused_words"])
VERBS = ("report", "detail", "apply")
OPTIONAL_VERBS = ("try",)       # LD-83 (picture try first): preview results, nothing committed
FIELDS = ("schema", "kind") + VERBS + ("words",)
OPTIONAL = ("kind_words", "_what", "_about", "status") + OPTIONAL_VERBS + ("try_words",)
KILL_AT = 3


def _repo(repo=None):
    return Path(repo) if repo else paths.repo(HERE)


def kinds(repo=None):
    """{type id: [its old words]} from the naming standard (components/naming/stages.json `types`)."""
    d = json.loads((_repo(repo) / "components" / "naming" / "stages.json").read_text())
    return {t["id"]: list(t.get("from") or []) for t in d["types"]}


def _argv(v, verb, repo):
    if not isinstance(v, list) or not v or not all(isinstance(x, str) and x for x in v):
        return "%s: must be a non-empty list of strings (argv)" % verb
    a0 = v[0].replace("\\", "/")
    if a0.startswith("/") or ".." in a0.split("/"):
        return "%s: argv[0] must be a repo-relative path, got %r" % (verb, v[0])
    if a0.startswith("lab/") or "/lab/" in a0:
        return "%s: argv[0] is lab code (%s) — builder card rule 12: no component runs lab code" % (verb, v[0])
    if not a0.startswith("components/"):
        return "%s: argv[0] must be under components/, got %r" % (verb, v[0])
    if not (repo / a0).is_file():
        return "%s: argv[0] %s is not on disk" % (verb, v[0])
    return None


def check(m, repo=None):
    """Every problem with a manifest (a dict), each "<field>: why"; [] = valid."""
    repo = _repo(repo)
    if not isinstance(m, dict):
        return ["file: an adapter.json is one JSON object"]
    out = []
    for f in FIELDS:
        if f not in m:
            out.append("%s: missing" % f)
    for f in sorted(set(m) - set(FIELDS) - set(OPTIONAL)):
        out.append("%s: not a contract field (fields: %s)" % (f, ", ".join(FIELDS + ("kind_words",))))
    if "schema" in m and m["schema"] != 1:
        out.append("schema: must be 1, got %r" % (m["schema"],))
    if "kind" in m:
        ks = kinds(repo)
        if m["kind"] not in ks:
            hint = next((k for k, old in ks.items() if str(m["kind"]).lower() in (w.lower() for w in old)), None)
            out.append("kind: %r is not a components/naming/stages.json types id (%s)%s"
                       % (m["kind"], " | ".join(ks), "; the naming standard maps it to %r" % hint if hint else ""))
    for verb in VERBS + OPTIONAL_VERBS:
        if verb in m:
            why = _argv(m[verb], verb, repo)
            if why:
                out.append(why)
    if "try_words" in m:
        tw, ws = m["try_words"], m.get("words") if isinstance(m.get("words"), list) else []
        if "try" not in m:
            out.append("try_words: listed without a `try` verb")
        if not isinstance(tw, list) or not tw or not all(isinstance(w, str) and w for w in tw):
            out.append("try_words: must be a non-empty list of change words")
        else:
            for w in tw:
                if w.lower() in REFUSED:
                    out.append("try_words: %r is refused — %s" % (w, SCHEMA["refused_why"]))
                elif w not in ws:
                    out.append("try_words: %r is not in words — a try takes only change words this adapter lists" % w)
    kw = m.get("kind_words", {})
    if not isinstance(kw, dict) or not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in kw.items()):
        out.append("kind_words: must be {word: what it does}")
        kw = {}
    for w in sorted(kw):
        if w in SHARED:
            out.append("kind_words: %r is a shared word; list it in words only" % w)
        if w.lower() in REFUSED:
            out.append("kind_words: %r is refused — %s" % (w, SCHEMA["refused_why"]))
    if "words" in m:
        ws = m["words"]
        if not isinstance(ws, list) or not ws or not all(isinstance(w, str) for w in ws):
            out.append("words: must be a non-empty list of change words")
        else:
            if len(set(ws)) != len(ws):
                out.append("words: a word is listed twice")
            for w in ws:
                if w.lower() in REFUSED:
                    out.append("words: %r is refused — %s" % (w, SCHEMA["refused_why"]))
                elif w not in SHARED and w not in kw:
                    out.append("words: %r is unknown — the shared words are %s; a kind-specific word is listed in "
                               "kind_words first" % (w, " · ".join(SHARED)))
    return out


def warnings(m):
    kw = m.get("kind_words") if isinstance(m, dict) else None
    if isinstance(kw, dict) and len(kw) > KILL_AT:
        return ["kind_words: %d kind-specific words (more than %d): the spec's kill — the shared level may be wrong; "
                "tell the team" % (len(kw), KILL_AT)]
    return []


def read(path):
    """(manifest, None) or (None, "file: why")."""
    try:
        return json.loads(Path(path).read_text()), None
    except OSError as e:
        return None, "file: %s cannot be read (%s)" % (path, e.strerror or e)
    except ValueError as e:
        return None, "file: %s is not JSON (%s)" % (path, e)


def load(path, repo=None):
    """The manifest at path when it is valid; ValueError naming every problem otherwise."""
    m, why = read(path)
    problems = [why] if why else check(m, repo)
    if problems:
        raise ValueError("%s: %s" % (path, "; ".join(problems)))
    return m


def command(m, verb, args=(), repo=None):
    """The argv that runs one verb of a (valid) manifest, from the repo root, with `args` appended."""
    has = VERBS + tuple(v for v in OPTIONAL_VERBS if v in m)
    if verb not in has:
        raise ValueError("verb must be one of %s" % ", ".join(has))
    argv = list(m[verb])
    a0 = str(_repo(repo) / argv[0])
    head = [sys.executable, a0] if a0.endswith(".py") else [a0]
    return head + argv[1:] + [str(a) for a in args]


def find(root=None):
    """Every adapter.json at components/<c>/ or components/<c>/<folder>/, repo-relative, sorted."""
    root = Path(root) if root else _repo()
    got = set()
    for pat in ("components/*/adapter.json", "components/*/*/adapter.json"):
        got |= {p.relative_to(root).as_posix() for p in root.glob(pat) if p.is_file()}
    return sorted(got)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("adapter")
    f = sub.add_parser("find")
    f.add_argument("--root")
    x = ap.parse_args(argv)
    if x.cmd == "find":
        for p in find(x.root):
            print(p)
        return 0
    m, why = read(x.adapter)
    problems = [why] if why else check(m)
    for p in problems:
        print(p)
    if problems:
        return 1
    for w in warnings(m):
        print("warning: " + w, file=sys.stderr)
    print("ok: %s (%s, %d words)" % (x.adapter, m["kind"], len(m["words"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
