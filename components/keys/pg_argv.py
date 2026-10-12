"""The one way a psql caller keeps the password off its command line.

WM-108b (other argv sites). argv is readable by anyone running `ps`, so a
Postgres URL carrying its password must never ride in it: psql gets the URL
minus its password, and the password goes in PGPASSWORD on a COPY of the
child's environment.

    from pg_argv import for_psql
    safe, child = for_psql(url)
    subprocess.run(["psql", safe, ...], env=child, ...)

Stdlib only. No I/O, prints nothing, reads no environment variable itself —
`for_psql(url)` with no `env` copies `os.environ` as the child's base, which
is what a subprocess would have inherited anyway. `split_password` moved here
unchanged from `platform/workers/mini-worker/plane_loader.py` (WM-108 (no argv
credential)), which re-exports it.
"""
import os
import re
from urllib.parse import unquote

_URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


def split_password(url):
    """`(safe_url, password or None)` — WM-108's pure split, prints nothing.

    Two places a libpq URL can carry the password: the userinfo
    (`user:PW@creator`) and a `password=` query parameter. Both are taken out
    and the DECODED value returned; the userinfo one wins if both are set.
    Everything else stays byte-for-byte as written — the username, host,
    port, path, fragment and every other query pair in its order — so the
    string is cut rather than parsed and re-assembled (urlunsplit would
    re-spell a `postgresql:///db?host=…` URL and re-encode other pairs).
    The netloc and userinfo are split the way urlsplit splits them: netloc
    ends at the first `/`, the host follows the LAST `@`, and the password
    follows the FIRST `:`. No password anywhere → the input, unchanged."""
    if not url:
        return url, None
    head, hash_, fragment = url.partition("#")
    head, qmark, query = head.partition("?")
    password = None
    m = _URL_SCHEME.match(head)
    if m:
        start = m.end()
        end = head.find("/", start)
        end = len(head) if end < 0 else end
        userinfo, at, hostport = head[start:end].rpartition("@")
        user, colon, raw = userinfo.partition(":")
        if at and colon and raw:
            password = unquote(raw)
            head = head[:start] + user + "@" + hostport + head[end:]
    kept, in_query = [], None
    for pair in (query.split("&") if query else []):
        key, _eq, value = pair.partition("=")
        if unquote(key) == "password":
            in_query = unquote(value)
        else:
            kept.append(pair)
    if password is None and in_query:
        password = in_query
    if password is None:
        return url, None
    rest = ("?" + "&".join(kept)) if kept else ""
    return head + rest + hash_ + fragment, password


def for_psql(url, env=None):
    """`(safe_url, child_env)` for one psql spawn.

    `child_env` is a NEW dict — `os.environ` when `env` is None, else `env` —
    plus PGPASSWORD when the URL carried a password. The caller's dict is
    never touched. A password-free URL comes back unchanged and PGPASSWORD is
    not set (an inherited one rides along, as it would have before)."""
    safe_url, password = split_password(url)
    child = dict(os.environ if env is None else env)
    if password is not None:
        child["PGPASSWORD"] = password
    return safe_url, child
