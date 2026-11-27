"""`--profile` for any command-line tool that takes a person, without changing how the tool defines its arguments.

    argv = profile_arg.expand(argv, has=("avatar", "sub", "demographic"))      # right before parser.parse_args(...)

`--profile <avatar>[_<sub>][_<demographic>]` (naming/PEOPLE.md) is replaced by the tool's own `--avatar`, `--sub` and
`--demographic` as the brand folders spell them (people.folders), so a tool that requires `--avatar` still gets it and
nothing else about the tool changes. `has` names the flags the tool actually has; an explicit flag always wins over the
profile. Needs `--brand` in the same command. No profile on the command line: argv comes back untouched.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_P = {}


def _people():
    if "m" not in _P:
        spec = importlib.util.spec_from_file_location("naming_people", HERE / "people.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _P["m"] = m
    return _P["m"]


def _value(argv, flag):
    """(value, remaining argv) of `--flag v` or `--flag=v`; (None, argv) when absent."""
    out, val, i = [], None, 0
    while i < len(argv):
        x = argv[i]
        if x == flag and i + 1 < len(argv):
            val, i = argv[i + 1], i + 2
            continue
        if x.startswith(flag + "="):
            val, i = x[len(flag) + 1:], i + 1
            continue
        out.append(x)
        i += 1
    return val, out


def expand(argv=None, has=("avatar", "sub", "demographic")):
    argv = list(sys.argv[1:] if argv is None else argv)
    profile, rest = _value(argv, "--profile")
    if profile is None:
        return argv
    brand, _ = _value(rest, "--brand")
    if not brand:
        raise SystemExit("--profile needs --brand in the same command")
    given = {k: _value(rest, "--" + k)[0] for k in ("avatar", "sub", "demographic")}
    a, s, d = _people().folders(brand, profile, given["sub"] or "", given["demographic"] or "")
    add = {"avatar": a, "sub": s, "demographic": d}
    for k in ("avatar", "sub", "demographic"):
        if k in has and add[k] and given[k] is None:
            rest += ["--" + k, add[k]]
    return rest
