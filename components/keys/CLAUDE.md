# components/keys — load keys by name, never hold one

- `loader.py`: `key(NAME)` / `load()` — returns a key from the environment
  first, then the person's own key files. Never logs or prints a value.
- `pg_argv.py`: splits a Postgres URL into a password-free URL for psql's
  command line plus `PGPASSWORD` for the child process's environment.
- `checks.py`: names-only, report-only checks.

Walls: this folder and anything it writes never hold a key value. Each person
supplies their own keys; none are shared through the repo.
