# Chain mirror

**Keys this tool needs:** none.

Brings saved work from a source repo (a team workspace, or any repo that builds the same tools) into this one, keeps
it in step, and says how far behind this copy is. It is how the video, static, email and page lines arrive here
without anyone copying files by hand.

You don't run it by hand. Tell Claude "how far behind is Prizm", "bring in the micro-drama line" or "mirror
everything".

| Command | What it does |
|---|---|
| `mirror.py status` | per group: current, behind, not copied yet, not saved in the source yet |
| `mirror.py run <group> --dry-run` | lists what would be written and what would be refused |
| `mirror.py run <group>` | copies the group and stamps each file with the source version it came from |
| `mirror.py check` | sweeps every copied file for private names, keys and home paths again |

## What it promises

- **Only saved work.** It reads the source's saved version (`origin/main` by default), never a file still being
  edited there. A file that exists but is not saved is reported, not copied.
- **Nothing private gets through.** Each file is stripped (private names to stand-ins, home paths to `~/`), then
  checked with `tools/safety_check.py`'s rules. A file that still holds a private name, a key or a home path is
  refused whole and named in the report.
- **No brand, person or machine in this repo.** The source folder and the private names list live in a settings
  file outside the repo (`CHAIN_MIRROR_CONFIG`, default `nucleus/home/chain-mirror.json`, which git ignores).

## The parts

| File | What it is |
|---|---|
| `mirror.py` | the copier |
| `manifest.json` | what it copies, by group, in the order the plan moves them |
| `stamps.json` | written by a run: each copied file and the source version it came from |
| `test_mirror.py` | tests (`python3 tools/chain-mirror/test_mirror.py`) |

Neighbours: [safety check](../safety_check.py) (the leak rules), [client copies](../client-copies/) (passes this repo
on to each person's own copy).
