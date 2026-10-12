# keys

A small library that loads API keys for the tools in this repo.

- A tool asks for a key by name (for example `GEMINI_API_KEY`); the loader
  finds it in your environment or in your own `.env` file and hands it over.
- **Everyone sets up their own keys.** Nothing here contains a key, and no key
  is shared through this repo. If a tool needs a key you have not set, it
  stops and tells you the name.
- `pg_argv.py` keeps a database password out of the command line when a tool
  calls `psql`.
- `checks.py` is a report-only check that compares key *names* (never values).

Never commit a key, a `.env` file, or a screenshot of one.
