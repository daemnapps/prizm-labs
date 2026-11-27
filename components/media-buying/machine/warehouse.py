"""The warehouse, read-only: Meta's synced ad data and the store's order P&L, by SQL.

No Meta API calls — the warehouse (Supabase) already holds a daily copy of the ad
accounts, which is why this never touches the Meta usage meter.
"""
import csv, io, os, subprocess, sys
from pathlib import Path


def _keys_mod(fname, modname):
    """components/keys/<fname>, loaded by path (never on sys.path), found from this file."""
    import importlib.util
    mod = sys.modules.get(modname)
    if mod is None:
        here = Path(__file__).resolve()
        p = next(r / "components" / "keys" / fname for r in here.parents
                 if (r / "components" / "keys" / fname).is_file())
        spec = importlib.util.spec_from_file_location(modname, str(p))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
    return mod


def _url():
    """SUPABASE_DB_URL through the one key loader: the environment, then ~/.upright-keys.env."""
    return _keys_mod("loader.py", "upright_keys_loader").key("SUPABASE_DB_URL", required=False)


def rows(sql, **params):
    """One read-only query -> a list of dicts. Params are passed as psql variables (:'name')."""
    safe, child = _keys_mod("pg_argv.py", "upright_pg_argv").for_psql(_url())   # password in the env, not argv
    args = ["psql", safe, "--csv", "-q", "-v", "ON_ERROR_STOP=1", "-f", "-"]
    for k, v in params.items():
        args += ["-v", f"{k}={v}"]
    r = subprocess.run(args, input="set default_transaction_read_only = on;\n" + sql, capture_output=True, text=True, timeout=180,
                       env={**child, "PGCONNECT_TIMEOUT": "20"})
    if r.returncode:
        raise SystemExit(f"warehouse: {r.stderr.strip()[:600]}")
    return list(csv.DictReader(io.StringIO(r.stdout)))


def num(v, default=0.0):
    try:
        return float(v) if v not in (None, "") else default
    except ValueError:
        return default
